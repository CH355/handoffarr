"""Read-only cleanup review queue.

Builds a manual cleanup review projection from persisted import, library,
cleanup, trace, qBittorrent torrent, and bounded qBittorrent file evidence.
Nothing in this module mutates services or files.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from . import db
from .cleanup import CLEANUP_COMPLETED, CLEANUP_FAILED, CLEANUP_PENDING
from .cleanup_reconciliation import (
    latest_completed_execution_index,
    matching_completed_execution,
)
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
SORT_RECOVERABLE = "recoverable_bytes desc"
SORT_CONFIDENCE = "confidence_score desc"
SORT_TITLE = "media_title asc"

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


def _candidate_hash(item: dict[str, Any]) -> str | None:
    evidence = item.get("evidence") or {}
    qbit = evidence.get("qbittorrent_torrent") or {}
    files = evidence.get("qbittorrent_files") or {}
    execution = evidence.get("cleanup_execution") or {}
    value = (
        item.get("qbit_hash")
        or item.get("torrent_hash")
        or execution.get("qbit_hash")
        or qbit.get("torrent_hash")
        or files.get("torrent_hash")
    )
    return str(value).lower() if value else None


def _with_qbit_hash(item: dict[str, Any]) -> dict[str, Any]:
    qbit_hash = _candidate_hash(item)
    if qbit_hash:
        item["torrent_hash"] = qbit_hash
        item["qbit_hash"] = qbit_hash
    else:
        item.setdefault("qbit_hash", None)
    return item


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


def _file_evidence_says_absent(file_evidence: dict[str, Any] | None) -> bool:
    if not file_evidence:
        return False
    if file_evidence.get("ok") is not False:
        return False
    error = str(file_evidence.get("error") or "").lower()
    return "404" in error or "not present" in error or "not found" in error


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
    completed_execution: dict[str, Any] | None,
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
    execution_reconciled = completed_execution is not None
    live_absence_override = _file_evidence_says_absent(file_evidence)
    download_present = _download_copy_present(cleanup_event)
    torrent_state = str(evidence.get("torrent_state") or "").lower()
    state_completed = torrent_state in COMPLETED_STATES
    cleanup_recoverable = _to_int(cleanup_event.get("recoverable_bytes"))
    retained_bytes = _to_int(cleanup_event.get("retained_bytes"))
    if execution_reconciled or live_absence_override:
        download_present = False
        cleanup_recoverable = 0
        retained_bytes = 0
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
        reason = (
            "Controlled cleanup execution removed the qBittorrent item and preserved the library file."
            if execution_reconciled
            else "Library is present and the qBittorrent/download copy is gone."
        )
        cleanup_recoverable = 0
        risk_reasons = []
        safe_reasons = [
            "Import Success exists.",
            "Library Present exists.",
            "qBittorrent/download copy is no longer present.",
        ]
        if execution_reconciled:
            safe_reasons.append("Completed cleanup execution verified qBittorrent item disappeared.")
            safe_reasons.append("Completed cleanup execution verified library file still exists.")
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
        "post_execution_reconciled": execution_reconciled,
        "live_absence_override": live_absence_override,
        "qbittorrent_completed_state": state_completed,
        "cleanup_recoverable_bytes": cleanup_recoverable,
        "match_source": match_source,
        "match_strength": match_strength,
        "media_id_mismatch": media_mismatch,
        "destination_path_mismatch": destination_mismatch,
        "file_evidence_available": file_match["file_evidence_ok"],
    }

    item_hash = torrent_hash or str((completed_execution or {}).get("qbit_hash") or "").lower()
    return _with_qbit_hash({
        "cleanup_id": cleanup_event.get("cleanup_id"),
        "media_id": cleanup_event.get("media_id"),
        "media_type": (import_event or {}).get("media_type")
        or (library_artifact or {}).get("media_type"),
        "media_title": cleanup_event.get("media_title"),
        "source_application": cleanup_event.get("source_application"),
        "torrent_hash": item_hash or cleanup_event.get("torrent_hash"),
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
        "cleanup_status": CLEANUP_COMPLETED
        if execution_reconciled and library_present
        else cleanup_event.get("cleanup_status"),
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
            "cleanup_execution": completed_execution or {},
            "qbittorrent_torrent": {
                "torrent_hash": item_hash or cleanup_event.get("torrent_hash"),
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
    })


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
    completed_execution_index = latest_completed_execution_index(
        db.all_cleanup_executions(limit=5000)
    )
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
        completed_execution = matching_completed_execution(
            cleanup_event, completed_execution_index
        )
        item = _classify_item(
            cleanup_event=cleanup_event,
            import_event=import_event,
            library_artifact=library_by_media.get(media_id),
            trace=traces_by_media.get(media_id),
            file_evidence=file_evidence_by_hash.get(torrent_hash),
            completed_execution=completed_execution,
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


def _apply_filters(
    items: list[dict[str, Any]],
    *,
    review_class: str | None = None,
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
) -> list[dict[str, Any]]:
    active = [item for item in items if not item.get("excluded_by_dedupe")]
    if review_class:
        active = [item for item in active if item.get("review_class") == review_class]
    if match_strength:
        active = [item for item in active if item.get("match_strength") == match_strength]
    if min_recoverable_bytes is not None:
        active = [
            item
            for item in active
            if _to_int(item.get("recoverable_bytes")) >= min_recoverable_bytes
        ]
    if source_application:
        expected = source_application.lower()
        active = [
            item
            for item in active
            if str(item.get("source_application") or "").lower() == expected
        ]
    if media_type:
        expected = media_type.lower()
        active = [
            item
            for item in active
            if str(item.get("media_type") or "").lower() == expected
        ]
    return active


def _sort_items(items: list[dict[str, Any]], sort: str | None) -> list[dict[str, Any]]:
    selected = sort or SORT_RECOVERABLE
    if selected == SORT_CONFIDENCE:
        return sorted(
            items,
            key=lambda item: (
                float(item.get("confidence_score") or 0),
                _to_int(item.get("recoverable_bytes")),
            ),
            reverse=True,
        )
    if selected == SORT_TITLE:
        return sorted(items, key=lambda item: str(item.get("media_title") or "").lower())
    return sorted(
        items,
        key=lambda item: _to_int(item.get("recoverable_bytes")),
        reverse=True,
    )


def cleanup_review_response(
    items: list[dict[str, Any]],
    *,
    review_class: str | None = None,
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort: str | None = None,
) -> dict[str, Any]:
    active = [_with_qbit_hash(item) for item in items if not item.get("excluded_by_dedupe")]
    filtered = _apply_filters(
        active,
        review_class=review_class,
        match_strength=match_strength,
        min_recoverable_bytes=min_recoverable_bytes,
        source_application=source_application,
        media_type=media_type,
    )
    sorted_items = _sort_items(filtered, sort)
    safe_offset = max(0, offset)
    safe_limit = 100 if limit is None else max(0, min(limit, 500))
    page = sorted_items[safe_offset : safe_offset + safe_limit]
    return {
        "summary": summarize_cleanup_review(filtered),
        "filters": {
            "review_class": review_class,
            "match_strength": match_strength,
            "min_recoverable_bytes": min_recoverable_bytes,
            "source_application": source_application,
            "media_type": media_type,
            "limit": safe_limit,
            "offset": safe_offset,
            "sort": sort or SORT_RECOVERABLE,
        },
        "pagination": {
            "total": len(filtered),
            "limit": safe_limit,
            "offset": safe_offset,
            "returned": len(page),
        },
        "top_candidates": page[:10],
        "candidates": page,
    }


def _format_bytes(value: Any) -> str:
    size = float(_to_int(value))
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while size >= 1024 and idx < len(units) - 1:
        size /= 1024
        idx += 1
    return f"{size:.1f} {units[idx]}" if idx >= 3 else f"{size:.0f} {units[idx]}"


def cleanup_checklist_text(item: dict[str, Any]) -> str:
    item = _with_qbit_hash(item)
    evidence = item.get("evidence") or {}
    qbit = evidence.get("qbittorrent_torrent") or {}
    execution = evidence.get("cleanup_execution") or {}
    files = evidence.get("qbittorrent_files") or {}
    paths = item.get("paths") or {}
    matched_files = item.get("matched_retained_files") or []
    retained_files = files.get("files") if isinstance(files.get("files"), list) else []
    retained_paths = [
        _full_retained_path(files, f)
        for f in retained_files
        if isinstance(f, dict) and _is_video(str(f.get("name") or ""))
    ]
    if not retained_paths:
        retained_paths = [f.get("retained_path") for f in matched_files if f.get("retained_path")]

    matched_lines = []
    for matched in matched_files:
        matched_lines.append(
            f"- {matched.get('retained_path')} "
            f"({ _format_bytes(matched.get('size')) })"
        )
    if not matched_lines:
        matched_lines.append("- No retained file was strongly matched.")

    reason_lines = item.get("risk_reasons") or item.get("safe_reasons") or [item.get("reason")]
    reason_lines = [line for line in reason_lines if line]

    lines = [
            "Handoffarr Cleanup Manual Review Checklist",
            "",
            "WARNING: Handoffarr does not delete files.",
            "Use this as a manual review aid.",
            "Bulk deletion is unsafe while risky candidates remain.",
            "",
            f"Item title: {item.get('media_title') or 'unknown'}",
            f"Media ID: {item.get('media_id') or 'unknown'}",
            f"Media type: {item.get('media_type') or 'unknown'}",
            f"Review class: {item.get('review_class') or 'unknown'}",
            f"Match strength: {item.get('match_strength') or 'unknown'}",
            f"Confidence score: {item.get('confidence_score')}",
            f"Recoverable bytes: {item.get('recoverable_bytes')} ({_format_bytes(item.get('recoverable_bytes'))})",
            "",
            "qBittorrent retained download:",
            f"- Name: {qbit.get('torrent_name') or files.get('torrent_name') or 'unknown'}",
            f"- qBittorrent hash: {item.get('qbit_hash') or item.get('torrent_hash') or qbit.get('torrent_hash') or 'unknown'}",
            f"- Save path: {qbit.get('save_path') or files.get('save_path') or paths.get('download_path') or 'unknown'}",
    ]
    if item.get("review_class") == ALREADY_CLEANED:
        postcheck = (execution.get("evidence") or {}).get("postcheck") or {}
        lines.extend(
            [
                "",
                "Completed execution evidence:",
                f"- Execution status: {execution.get('execution_status') or 'Completed'}",
                f"- qBittorrent item removed: {postcheck.get('qbit_item_disappeared')}",
                f"- Library file preserved: {postcheck.get('library_file_still_exists')}",
                "",
                "No cleanup action is recommended for this item because Handoffarr already verified it was cleaned.",
                "",
                "Handoffarr does not delete files directly.",
            ]
        )
        return "\n".join(lines)

    return "\n".join(
        [
            *lines,
            "",
            "Retained file path(s):",
            *(f"- {path}" for path in retained_paths),
            "",
            "Library evidence:",
            f"- Library path: {paths.get('library_path') or 'unknown'}",
            f"- Library file exists: {item.get('library_file_exists')}",
            f"- Library file size: {item.get('library_file_size')} ({_format_bytes(item.get('library_file_size'))})",
            "",
            "Matched retained file(s):",
            *matched_lines,
            "",
            "Why Handoffarr classified it this way:",
            *(f"- {line}" for line in reason_lines),
            "",
            "Manual verification steps before deleting outside Handoffarr:",
            "1. Open qBittorrent and find the torrent by name or hash.",
            "2. Confirm the retained save path and retained file path(s) match this checklist.",
            "3. Confirm the library path exists and plays/opens correctly.",
            "4. Confirm the retained media file size matches the library file size within the configured tolerance.",
            "5. Confirm this is not a multi-file pack, season pack, or partial retained download unless every retained media file is accounted for.",
            "6. Only then decide manually whether to delete outside Handoffarr.",
            "",
            "Handoffarr does not delete files.",
        ]
    )


def manual_review_packet(item: dict[str, Any]) -> dict[str, Any]:
    item = _with_qbit_hash(item)
    evidence = item.get("evidence") or {}
    return {
        "media_title": item.get("media_title"),
        "media_id": item.get("media_id"),
        "media_type": item.get("media_type"),
        "torrent_hash": item.get("torrent_hash"),
        "qbit_hash": item.get("qbit_hash"),
        "review_class": item.get("review_class"),
        "recoverable_bytes": item.get("recoverable_bytes"),
        "match_strength": item.get("match_strength"),
        "confidence_score": item.get("confidence_score"),
        "cleanup_status": item.get("cleanup_status"),
        "checks": item.get("checks") or {},
        "reason": item.get("reason"),
        "risk_reasons": item.get("risk_reasons") or [],
        "safe_reasons": item.get("safe_reasons") or [],
        "import_evidence": evidence.get("import") or {},
        "library_evidence": evidence.get("library") or {},
        "cleanup_evidence": evidence.get("cleanup") or {},
        "cleanup_execution_evidence": evidence.get("cleanup_execution") or {},
        "retained_download_evidence": {
            "paths": item.get("paths") or {},
            "retained_file_count": item.get("retained_file_count"),
            "retained_video_file_count": item.get("retained_video_file_count"),
            "retained_total_bytes": item.get("retained_total_bytes"),
            "matched_retained_files": item.get("matched_retained_files") or [],
        },
        "qbittorrent_torrent_evidence": evidence.get("qbittorrent_torrent") or {},
        "qbittorrent_file_evidence": evidence.get("qbittorrent_files") or {},
        "manual_checklist_text": cleanup_checklist_text(item),
        "candidate": item,
    }


def media_cleanup_review_response(media_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [
        _with_qbit_hash(item)
        for item in items
        if str(item.get("media_id")) == str(media_id)
    ]
    if not matching:
        return {
            "media_id": media_id,
            "review_class": UNKNOWN_EVIDENCE,
            "reason": "No cleanup review evidence exists for this media_id.",
            "candidates": [],
        }
    latest = matching[0]
    packet = manual_review_packet(latest)
    packet["candidates"] = matching
    return packet


def media_cleanup_checklist(media_id: str, items: list[dict[str, Any]]) -> str | None:
    matching = [item for item in items if str(item.get("media_id")) == str(media_id)]
    if not matching:
        return None
    return cleanup_checklist_text(matching[0])


def _action_plan_candidate(item: dict[str, Any]) -> dict[str, Any]:
    item = _with_qbit_hash(item)
    evidence = item.get("evidence") or {}
    qbit = evidence.get("qbittorrent_torrent") or {}
    paths = item.get("paths") or {}
    reasons = item.get("risk_reasons") or item.get("safe_reasons") or [item.get("reason")]
    return {
        "media_id": item.get("media_id"),
        "media_title": item.get("media_title"),
        "media_type": item.get("media_type"),
        "review_class": item.get("review_class"),
        "match_strength": item.get("match_strength"),
        "confidence_score": item.get("confidence_score"),
        "recoverable_bytes": item.get("recoverable_bytes"),
        "qbit_name": qbit.get("torrent_name"),
        "qbit_hash": item.get("qbit_hash") or item.get("torrent_hash") or qbit.get("torrent_hash"),
        "torrent_hash": item.get("torrent_hash"),
        "retained_save_path": qbit.get("save_path") or paths.get("download_path"),
        "library_path": paths.get("library_path"),
        "checklist_url": f"/api/cleanup/review/{item.get('media_id')}/checklist",
        "manual_action": (
            "Review manually outside Handoffarr. Handoffarr does not delete files."
        ),
        "reasons": [reason for reason in reasons if reason],
    }


def cleanup_action_plan_response(
    items: list[dict[str, Any]],
    *,
    review_class: str | None = SAFE_REVIEW,
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict[str, Any]:
    filtered = _apply_filters(
        items,
        review_class=review_class,
        match_strength=match_strength,
        min_recoverable_bytes=min_recoverable_bytes,
        source_application=source_application,
        media_type=media_type,
    )
    sorted_items = _sort_items(filtered, SORT_RECOVERABLE)
    safe_limit = max(0, min(limit, 500))
    safe_offset = max(0, offset)
    included = sorted_items[safe_offset : safe_offset + safe_limit]
    filters = {
        "review_class": review_class,
        "match_strength": match_strength,
        "min_recoverable_bytes": min_recoverable_bytes,
        "source_application": source_application,
        "media_type": media_type,
        "limit": safe_limit,
        "offset": safe_offset,
        "sort": SORT_RECOVERABLE,
    }
    return {
        "summary": {
            "total_candidates": len(filtered),
            "included_candidates": len(included),
            "total_recoverable_bytes": sum(
                _to_int(item.get("recoverable_bytes")) for item in filtered
            ),
            "included_recoverable_bytes": sum(
                _to_int(item.get("recoverable_bytes")) for item in included
            ),
            "filters_applied": filters,
            "warning_read_only": (
                "Handoffarr does not delete files. Use this as a manual review aid. "
                "Do not bulk delete risky candidates."
            ),
        },
        "candidates": [_action_plan_candidate(item) for item in included],
    }


def cleanup_action_plan_text(plan: dict[str, Any]) -> str:
    summary = plan.get("summary") or {}
    filters = summary.get("filters_applied") or {}
    lines = [
        "Handoffarr Cleanup Action Plan",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "READ-ONLY WARNING: Handoffarr does not delete files.",
        "Use this as a manual review aid. Do not bulk delete risky candidates.",
        "",
        "Filter summary:",
    ]
    for key in (
        "review_class",
        "match_strength",
        "min_recoverable_bytes",
        "source_application",
        "media_type",
        "limit",
        "offset",
        "sort",
    ):
        lines.append(f"- {key}: {filters.get(key)}")
    lines.extend(
        [
            "",
            f"Total candidates matching filters: {summary.get('total_candidates')}",
            f"Included candidates: {summary.get('included_candidates')}",
            "Total included recoverable space: "
            f"{summary.get('included_recoverable_bytes')} "
            f"({_format_bytes(summary.get('included_recoverable_bytes'))})",
            "",
        ]
    )

    for index, candidate in enumerate(plan.get("candidates") or [], start=1):
        reasons = candidate.get("reasons") or []
        lines.extend(
            [
                f"Candidate {index}",
                f"Title: {candidate.get('media_title')}",
                f"Media ID: {candidate.get('media_id')}",
                f"Media type: {candidate.get('media_type')}",
                "Recoverable size: "
                f"{candidate.get('recoverable_bytes')} "
                f"({_format_bytes(candidate.get('recoverable_bytes'))})",
                f"Review class: {candidate.get('review_class')}",
                f"Match strength: {candidate.get('match_strength')}",
                f"Confidence score: {candidate.get('confidence_score')}",
                f"qBittorrent name: {candidate.get('qbit_name')}",
                f"qBittorrent hash: {candidate.get('qbit_hash')}",
                f"Retained save path: {candidate.get('retained_save_path')}",
                f"Library path: {candidate.get('library_path')}",
                f"Checklist: {candidate.get('checklist_url')}",
                "Why Handoffarr classified it this way:",
            ]
        )
        if reasons:
            lines.extend(f"- {reason}" for reason in reasons)
        else:
            lines.append("- No reason recorded.")
        lines.extend(
            [
                "Manual verification steps:",
                "1. Open qBittorrent and find the torrent by name or hash.",
                "2. Confirm the retained save path matches this plan.",
                "3. Open the per-item checklist and verify retained file paths and sizes.",
                "4. Confirm the library path exists and the library file works.",
                "5. Confirm this is not a partial pack or risky candidate before deleting outside Handoffarr.",
                "",
            ]
        )

    lines.extend(
        [
            "Final warning:",
            "Handoffarr does not delete files. Do not bulk delete risky candidates.",
        ]
    )
    return "\n".join(lines)
