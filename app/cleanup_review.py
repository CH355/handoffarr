"""Read-only cleanup review queue.

Builds a manual cleanup review projection from persisted import, library,
cleanup, trace, qBittorrent torrent, and bounded qBittorrent file evidence.
Nothing in this module mutates services or files.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any

from . import db
from .cleanup import CLEANUP_COMPLETED, CLEANUP_FAILED, CLEANUP_PENDING
from .config import Config
from .imports import IMPORT_SUCCESS
from .library import LIBRARY_MISSING, LIBRARY_PRESENT, LIBRARY_UNKNOWN

SAFE_REVIEW = "Safe Review Candidate"
RISKY_REVIEW = "Risky Review Candidate"
MISSING_LIBRARY = "Missing Library Candidate"
UNKNOWN_EVIDENCE = "Unknown Evidence Candidate"
ALREADY_CLEANED = "Already Cleaned"

EXACT_HASH = "Exact Hash/DownloadId Match"
EXACT_LIBRARY_PATH = "Exact Library Path Match"
FILENAME_SIZE = "Filename + Size Match"
PACK_PARTIAL = "Multi-file Pack Partial Match"
TITLE_ONLY = "Title Only Match"
NO_MATCH = "No Match"

REVIEW_CLASSES = (
    SAFE_REVIEW,
    RISKY_REVIEW,
    MISSING_LIBRARY,
    UNKNOWN_EVIDENCE,
    ALREADY_CLEANED,
)

SAFE_MATCH_STRENGTHS = {EXACT_HASH, EXACT_LIBRARY_PATH, FILENAME_SIZE}
VIDEO_EXTENSIONS = {
    ".avi",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".wmv",
    ".iso",
}
COMPLETED_STATES = {
    "completed",
    "seeding",
    "uploading",
    "forcedup",
    "stalledup",
    "pausedup",
    "stoppedup",
    "queuedup",
}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_payload(event: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(event.get("payload_json") or "{}")
    except Exception:  # noqa: BLE001
        return {}


def _norm_path(path: str | None) -> str:
    return (path or "").replace("\\", "/").rstrip("/").lower()


def _basename(path: str | None) -> str:
    return os.path.basename((path or "").replace("\\", "/")).lower()


def _file_size(file_info: dict[str, Any]) -> int:
    for key in ("size", "total_size"):
        value = _to_int(file_info.get(key))
        if value > 0:
            return value
    return 0


def _is_video(path: str | None) -> bool:
    return os.path.splitext(path or "")[1].lower() in VIDEO_EXTENSIONS


def _by_media(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        media_id = item.get("media_id")
        if media_id is not None and str(media_id) not in out:
            out[str(media_id)] = item
    return out


def _latest_file_evidence() -> dict[str, dict[str, Any]]:
    events = [
        event
        for event in db.recent_events(source="cleanup", limit=5000)
        if event.get("event_type") == "file_evidence"
    ]
    out: dict[str, dict[str, Any]] = {}
    for event in events:
        torrent_hash = str(event.get("torrent_hash") or "").lower()
        if not torrent_hash or torrent_hash in out:
            continue
        payload = _parse_payload(event)
        payload.setdefault("observed_at", event.get("observed_at"))
        out[torrent_hash] = payload
    return out


def _download_copy_present(cleanup_event: dict[str, Any]) -> bool:
    evidence = cleanup_event.get("evidence") or {}
    return bool(evidence.get("torrent_present")) or _to_int(
        cleanup_event.get("retained_bytes")
    ) > 0


def _dedupe_key(cleanup_event: dict[str, Any], import_event: dict[str, Any] | None) -> str:
    torrent_hash = str(cleanup_event.get("torrent_hash") or "").lower()
    if torrent_hash:
        return f"torrent_hash:{torrent_hash}"
    import_evidence = (import_event or {}).get("evidence") or {}
    download_id = (
        cleanup_event.get("download_id")
        or import_evidence.get("download_id")
        or import_evidence.get("torrent_hash")
    )
    if download_id:
        return f"download_id:{str(download_id).lower()}"
    cleanup_id = cleanup_event.get("cleanup_id")
    if cleanup_id:
        return f"cleanup_id:{cleanup_id}"
    return f"media_id:{cleanup_event.get('media_id')}"


def _library_status(
    cleanup_event: dict[str, Any],
    library_artifact: dict[str, Any] | None,
    trace: dict[str, Any] | None,
) -> str | None:
    evidence = cleanup_event.get("evidence") or {}
    status = (
        evidence.get("library_status")
        or (library_artifact or {}).get("library_status")
        or (trace or {}).get("library_status")
    )
    if not status and (
        evidence.get("library_file_exists")
        or (library_artifact or {}).get("file_exists")
        or cleanup_event.get("cleanup_status")
        in {CLEANUP_COMPLETED, CLEANUP_PENDING, CLEANUP_FAILED}
    ):
        status = LIBRARY_PRESENT
    return status


def _library_size(library_artifact: dict[str, Any] | None) -> int:
    return _to_int((library_artifact or {}).get("file_size"))


def _library_path(
    cleanup_event: dict[str, Any],
    import_event: dict[str, Any] | None,
    library_artifact: dict[str, Any] | None,
) -> str | None:
    evidence = cleanup_event.get("evidence") or {}
    return (
        evidence.get("library_path")
        or (library_artifact or {}).get("library_path")
        or (import_event or {}).get("destination_path")
    )


def _retained_files(file_evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not file_evidence or not isinstance(file_evidence.get("files"), list):
        return []
    return [item for item in file_evidence["files"] if isinstance(item, dict)]


def _full_retained_path(file_evidence: dict[str, Any] | None, file_info: dict[str, Any]) -> str:
    name = str(file_info.get("name") or "")
    content_path = (file_evidence or {}).get("content_path")
    save_path = (file_evidence or {}).get("save_path")
    if save_path:
        return f"{str(save_path).rstrip('/')}/{name}".replace("\\", "/")
    if content_path:
        return str(content_path).replace("\\", "/")
    return name.replace("\\", "/")


def _match_files(
    *,
    cleanup_event: dict[str, Any],
    import_event: dict[str, Any] | None,
    library_artifact: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    file_evidence: dict[str, Any] | None,
    tolerance: int,
) -> dict[str, Any]:
    evidence = cleanup_event.get("evidence") or {}
    files = _retained_files(file_evidence)
    video_files = [f for f in files if _is_video(str(f.get("name") or ""))]
    retained_total = sum(_file_size(f) for f in files)
    retained_video_total = sum(_file_size(f) for f in video_files)
    library_path = _library_path(cleanup_event, import_event, library_artifact)
    library_size = _library_size(library_artifact)
    library_base = _basename(library_path)
    import_source_base = _basename((import_event or {}).get("source_path"))
    match_source = evidence.get("match_source") or (trace or {}).get("match_source")

    matched: list[dict[str, Any]] = []
    path_matches: list[dict[str, Any]] = []
    filename_size_matches: list[dict[str, Any]] = []

    for file_info in files:
        retained_path = _full_retained_path(file_evidence, file_info)
        size = _file_size(file_info)
        item = {
            "name": file_info.get("name"),
            "size": size,
            "retained_path": retained_path,
        }
        if library_path and _norm_path(retained_path) == _norm_path(library_path):
            path_matches.append({**item, "match_method": "exact_path"})
        if (
            (library_base or import_source_base)
            and _basename(str(file_info.get("name") or "")) in {library_base, import_source_base}
            and library_size > 0
            and abs(size - library_size) <= tolerance
        ):
            filename_size_matches.append({**item, "match_method": "filename_size"})

    if path_matches:
        matched = path_matches
        strength = EXACT_LIBRARY_PATH
    elif filename_size_matches:
        matched = filename_size_matches
        strength = FILENAME_SIZE
    elif match_source in {"torrent_hash", "download_id"}:
        strength = EXACT_HASH
    elif match_source == "title_match":
        strength = TITLE_ONLY
    else:
        strength = NO_MATCH

    if matched and len(video_files) > len(matched):
        strength = PACK_PARTIAL

    confidence = {
        EXACT_HASH: 0.85,
        EXACT_LIBRARY_PATH: 1.0,
        FILENAME_SIZE: 0.95,
        PACK_PARTIAL: 0.55,
        TITLE_ONLY: 0.35,
        NO_MATCH: 0.0,
    }[strength]

    return {
        "match_strength": strength,
        "confidence_score": confidence,
        "matched_retained_files": matched,
        "retained_file_count": len(files),
        "retained_video_file_count": len(video_files),
        "retained_total_bytes": retained_total or _to_int(cleanup_event.get("retained_bytes")),
        "retained_video_total_bytes": retained_video_total,
        "library_file_size": library_size,
        "library_path": library_path,
        "file_evidence_ok": bool(file_evidence and file_evidence.get("ok")),
    }


def _evidence_strength(match_strength: str, confidence: float) -> str:
    if match_strength in {EXACT_LIBRARY_PATH, FILENAME_SIZE}:
        return "Strong"
    if match_strength == EXACT_HASH:
        return "Strong" if confidence >= 0.8 else "Moderate"
    if match_strength == PACK_PARTIAL:
        return "Partial"
    if match_strength == TITLE_ONLY:
        return "Weak"
    return "Unknown"


def _classify_item(
    *,
    cleanup_event: dict[str, Any],
    import_event: dict[str, Any] | None,
    library_artifact: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    file_evidence: dict[str, Any] | None,
    imports_by_hash: dict[str, set[str]],
    tolerance: int,
) -> dict[str, Any]:
    evidence = cleanup_event.get("evidence") or {}
    import_status = (
        evidence.get("import_status")
        or cleanup_event.get("import_status")
        or (import_event or {}).get("import_status")
    )
    import_success = import_status == IMPORT_SUCCESS
    library_status = _library_status(cleanup_event, library_artifact, trace)
    library_present = library_status == LIBRARY_PRESENT
    library_missing = library_status == LIBRARY_MISSING
    library_unknown = library_status == LIBRARY_UNKNOWN or library_status is None
    download_present = _download_copy_present(cleanup_event)
    torrent_state = str(evidence.get("torrent_state") or "").lower()
    state_completed = torrent_state in COMPLETED_STATES
    cleanup_recoverable = _to_int(cleanup_event.get("recoverable_bytes"))
    retained_bytes = _to_int(cleanup_event.get("retained_bytes"))
    match_source = evidence.get("match_source") or (trace or {}).get("match_source")
    torrent_hash = str(cleanup_event.get("torrent_hash") or "").lower()
    media_id = str(cleanup_event.get("media_id") or "")
    linked_media = imports_by_hash.get(torrent_hash, set()) if torrent_hash else set()
    media_mismatch = bool(linked_media and linked_media != {media_id})

    file_match = _match_files(
        cleanup_event=cleanup_event,
        import_event=import_event,
        library_artifact=library_artifact,
        trace=trace,
        file_evidence=file_evidence,
        tolerance=tolerance,
    )
    match_strength = file_match["match_strength"]
    library_size = file_match["library_file_size"]
    retained_video_count = file_match["retained_video_file_count"]
    matched_count = len(file_match["matched_retained_files"])

    risk_reasons: list[str] = []
    safe_reasons: list[str] = []
    if import_success:
        safe_reasons.append("Import Success exists.")
    else:
        risk_reasons.append("Import success evidence is incomplete.")
    if library_present:
        safe_reasons.append("Library Present exists.")
    if library_missing:
        risk_reasons.append("Library Missing contradicts safe cleanup.")
    if library_unknown:
        risk_reasons.append("Library evidence is missing or unknown.")
    if download_present:
        safe_reasons.append("Download copy still exists.")
    else:
        risk_reasons.append("No retained qBittorrent/download copy remains.")
    if state_completed:
        safe_reasons.append("qBittorrent state is completed/seeding/stoppedUP/queuedUP.")
    else:
        risk_reasons.append("qBittorrent state is not a completed retained-download state.")
    if cleanup_recoverable > 0:
        safe_reasons.append("recoverable_bytes is greater than zero.")
    else:
        risk_reasons.append("No recoverable bytes are reported for this cleanup item.")
    if match_strength in SAFE_MATCH_STRENGTHS:
        safe_reasons.append(f"Match strength is {match_strength}.")
    elif match_strength == PACK_PARTIAL:
        risk_reasons.append("Retained download is a multi-file pack with only partial library-file evidence.")
    elif match_strength == TITLE_ONLY:
        risk_reasons.append("Only weak title correlation links the retained download.")
    else:
        risk_reasons.append("No strong retained-file match was found.")
    if media_mismatch:
        risk_reasons.append("The torrent hash is linked to a different media_id.")

    expected_library_path = (import_event or {}).get("destination_path")
    observed_library_path = file_match["library_path"]
    destination_mismatch = bool(
        expected_library_path
        and observed_library_path
        and _norm_path(expected_library_path) != _norm_path(observed_library_path)
    )
    if destination_mismatch:
        risk_reasons.append("Import destination path and observed library path do not agree.")

    if library_size > 0 and file_match["matched_retained_files"]:
        for matched in file_match["matched_retained_files"]:
            if abs(_to_int(matched.get("size")) - library_size) > tolerance:
                risk_reasons.append("Retained file size and library file size do not agree.")
                break

    if retained_video_count > 1 and matched_count < retained_video_count:
        risk_reasons.append(
            "Retained download has multiple video files but only one library artifact is confirmed."
        )

    if import_success and library_present and not download_present:
        review_class = ALREADY_CLEANED
        reason = "Library is present and the qBittorrent/download copy is gone."
        cleanup_recoverable = 0
    elif import_success and library_missing and download_present:
        review_class = MISSING_LIBRARY
        reason = "Import succeeded, but the expected library path is missing while the download copy remains."
    elif risk_reasons:
        review_class = RISKY_REVIEW
        reason = risk_reasons[0]
    elif (
        import_success
        and library_present
        and download_present
        and state_completed
        and cleanup_recoverable > 0
        and match_strength in SAFE_MATCH_STRENGTHS
    ):
        review_class = SAFE_REVIEW
        reason = "Import, library, retained-download, state, bytes, and match-strength evidence agree."
    else:
        review_class = UNKNOWN_EVIDENCE
        reason = "There is not enough evidence to decide safely."

    checks = {
        "import_success": import_success,
        "library_status": library_status,
        "download_copy_present": download_present,
        "qbittorrent_completed_state": state_completed,
        "cleanup_recoverable_bytes": cleanup_recoverable,
        "match_source": match_source,
        "match_strength": match_strength,
        "media_id_mismatch": media_mismatch,
        "destination_path_mismatch": destination_mismatch,
        "file_evidence_available": file_match["file_evidence_ok"],
    }

    return {
        "cleanup_id": cleanup_event.get("cleanup_id"),
        "media_id": cleanup_event.get("media_id"),
        "media_title": cleanup_event.get("media_title"),
        "source_application": cleanup_event.get("source_application"),
        "torrent_hash": cleanup_event.get("torrent_hash"),
        "download_id": evidence.get("download_id") or (import_event or {}).get("download_id"),
        "dedupe_key": "",
        "excluded_by_dedupe": False,
        "review_class": review_class,
        "reason": reason,
        "risk_reasons": risk_reasons,
        "safe_reasons": safe_reasons,
        "match_strength": match_strength,
        "confidence_score": file_match["confidence_score"],
        "evidence_strength": _evidence_strength(
            match_strength, file_match["confidence_score"]
        ),
        "recoverable_bytes": cleanup_recoverable,
        "retained_bytes": retained_bytes,
        "retained_total_bytes": file_match["retained_total_bytes"],
        "retained_file_count": file_match["retained_file_count"],
        "retained_video_file_count": retained_video_count,
        "matched_retained_files": file_match["matched_retained_files"],
        "library_file_exists": bool(library_present),
        "library_file_size": library_size,
        "cleanup_status": cleanup_event.get("cleanup_status"),
        "library_status": library_status,
        "import_status": import_status,
        "torrent_state": evidence.get("torrent_state"),
        "paths": {
            "import_source_path": (import_event or {}).get("source_path"),
            "expected_library_path": expected_library_path,
            "library_path": file_match["library_path"],
            "download_path": evidence.get("download_path"),
            "content_path": evidence.get("content_path")
            or (file_evidence or {}).get("content_path"),
        },
        "checks": checks,
        "evidence": {
            "import": import_event or {},
            "library": library_artifact or {},
            "cleanup": evidence,
            "qbittorrent_torrent": {
                "torrent_hash": cleanup_event.get("torrent_hash"),
                "torrent_name": evidence.get("torrent_name")
                or (file_evidence or {}).get("torrent_name"),
                "save_path": evidence.get("download_path")
                or (file_evidence or {}).get("save_path"),
                "content_path": evidence.get("content_path")
                or (file_evidence or {}).get("content_path"),
                "state": evidence.get("torrent_state"),
                "match_source": match_source,
            },
            "qbittorrent_files": file_evidence or {},
            "trace": trace or {},
        },
    }


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    strength_rank = {
        EXACT_LIBRARY_PATH: 6,
        FILENAME_SIZE: 5,
        EXACT_HASH: 4,
        PACK_PARTIAL: 3,
        TITLE_ONLY: 2,
        NO_MATCH: 1,
    }

    for item in items:
        key = item["dedupe_key"]
        current = kept.get(key)
        if current is None:
            kept[key] = item
            order.append(key)
            continue
        candidate_rank = (
            strength_rank.get(item.get("match_strength"), 0),
            _to_int(item.get("recoverable_bytes")),
            _to_int(item.get("retained_bytes")),
        )
        current_rank = (
            strength_rank.get(current.get("match_strength"), 0),
            _to_int(current.get("recoverable_bytes")),
            _to_int(current.get("retained_bytes")),
        )
        if candidate_rank > current_rank:
            current["excluded_by_dedupe"] = True
            current["dedupe_exclusion_reason"] = (
                f"Excluded from totals because {key} is represented by stronger evidence."
            )
            item.setdefault("deduped_items", []).append(
                {
                    "media_id": current.get("media_id"),
                    "media_title": current.get("media_title"),
                    "reason": current["dedupe_exclusion_reason"],
                }
            )
            kept[key] = item
        else:
            item["excluded_by_dedupe"] = True
            item["dedupe_exclusion_reason"] = (
                f"Excluded from totals because {key} is already represented by stronger or equal evidence."
            )
            current.setdefault("deduped_items", []).append(
                {
                    "media_id": item.get("media_id"),
                    "media_title": item.get("media_title"),
                    "reason": item["dedupe_exclusion_reason"],
                }
            )

    return sorted(
        kept.values(),
        key=lambda item: (
            _to_int(item.get("recoverable_bytes")),
            _to_int(item.get("retained_bytes")),
        ),
        reverse=True,
    )


def build_cleanup_review(
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
) -> list[dict[str, Any]]:
    imports_by_media = _by_media(import_events)
    library_by_media = _by_media(library_artifacts)
    traces_by_media = _by_media(traces)
    file_evidence_by_hash = _latest_file_evidence()
    review_config = config.section("cleanup_review")
    tolerance = int(review_config.get("file_size_tolerance_bytes", 10485760))

    imports_by_hash: dict[str, set[str]] = {}
    for event in import_events:
        evidence = event.get("evidence") or {}
        torrent_hash = str(evidence.get("torrent_hash") or "").lower()
        media_id = str(event.get("media_id") or "")
        if torrent_hash and media_id:
            imports_by_hash.setdefault(torrent_hash, set()).add(media_id)

    items: list[dict[str, Any]] = []
    for cleanup_event in cleanup_events:
        media_id = str(cleanup_event.get("media_id") or "")
        import_event = imports_by_media.get(media_id)
        torrent_hash = str(cleanup_event.get("torrent_hash") or "").lower()
        item = _classify_item(
            cleanup_event=cleanup_event,
            import_event=import_event,
            library_artifact=library_by_media.get(media_id),
            trace=traces_by_media.get(media_id),
            file_evidence=file_evidence_by_hash.get(torrent_hash),
            imports_by_hash=imports_by_hash,
            tolerance=tolerance,
        )
        item["dedupe_key"] = _dedupe_key(cleanup_event, import_event)
        items.append(item)

    return _dedupe(items)


def summarize_cleanup_review(items: list[dict[str, Any]]) -> dict[str, Any]:
    active = [item for item in items if not item.get("excluded_by_dedupe")]
    counts = Counter(item.get("review_class") for item in active)
    return {
        "total": len(active),
        "recoverable_bytes": sum(_to_int(item.get("recoverable_bytes")) for item in active),
        "safe_recoverable_bytes": sum(
            _to_int(item.get("recoverable_bytes"))
            for item in active
            if item.get("review_class") == SAFE_REVIEW
        ),
        "deduped_excluded_count": sum(
            len(item.get("deduped_items") or []) for item in active
        ),
        "safe_candidate_count": counts.get(SAFE_REVIEW, 0),
        "risky_candidate_count": counts.get(RISKY_REVIEW, 0),
        "missing_library_count": counts.get(MISSING_LIBRARY, 0),
        "unknown_evidence_count": counts.get(UNKNOWN_EVIDENCE, 0),
        "already_cleaned_count": counts.get(ALREADY_CLEANED, 0),
        "by_review_class": {name: counts.get(name, 0) for name in REVIEW_CLASSES},
        "by_match_strength": dict(Counter(item.get("match_strength") for item in active)),
    }


def cleanup_review_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    active = [item for item in items if not item.get("excluded_by_dedupe")]
    return {
        "summary": summarize_cleanup_review(active),
        "top_candidates": active[:10],
        "candidates": active,
    }


def media_cleanup_review_response(media_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [item for item in items if str(item.get("media_id")) == str(media_id)]
    if not matching:
        return {
            "media_id": media_id,
            "review_class": UNKNOWN_EVIDENCE,
            "reason": "No cleanup review evidence exists for this media_id.",
            "candidates": [],
        }
    latest = matching[0]
    return {
        "media_id": media_id,
        "review_class": latest.get("review_class"),
        "reason": latest.get("reason"),
        "match_strength": latest.get("match_strength"),
        "confidence_score": latest.get("confidence_score"),
        "import_evidence": latest.get("evidence", {}).get("import") or {},
        "library_evidence": latest.get("evidence", {}).get("library") or {},
        "cleanup_evidence": latest.get("evidence", {}).get("cleanup") or {},
        "qbittorrent_torrent_evidence": latest.get("evidence", {}).get("qbittorrent_torrent") or {},
        "qbittorrent_file_evidence": latest.get("evidence", {}).get("qbittorrent_files") or {},
        "risk_reasons": latest.get("risk_reasons") or [],
        "safe_reasons": latest.get("safe_reasons") or [],
        "candidates": matching,
    }
