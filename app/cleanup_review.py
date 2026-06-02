"""Read-only cleanup review queue.

This module turns persisted cleanup evidence into a manual review queue. It
never deletes torrents, files, or remote service state.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .cleanup import CLEANUP_COMPLETED, CLEANUP_FAILED, CLEANUP_PENDING
from .imports import IMPORT_SUCCESS
from .library import LIBRARY_MISSING, LIBRARY_PRESENT, LIBRARY_UNKNOWN

SAFE_REVIEW = "Safe Review Candidate"
RISKY_REVIEW = "Risky Review Candidate"
MISSING_LIBRARY = "Missing Library Candidate"
UNKNOWN_EVIDENCE = "Unknown Evidence Candidate"
ALREADY_CLEANED = "Already Cleaned"

REVIEW_CLASSES = (
    SAFE_REVIEW,
    RISKY_REVIEW,
    MISSING_LIBRARY,
    UNKNOWN_EVIDENCE,
    ALREADY_CLEANED,
)

COMPLETED_STATES = {
    "completed",
    "seeding",
    "uploading",
    "forcedup",
    "stalledup",
    "stalledUP".lower(),
    "pausedup",
    "stoppedup",
    "queuedup",
}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _by_media(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        media_id = item.get("media_id")
        if media_id is not None and str(media_id) not in out:
            out[str(media_id)] = item
    return out


def _download_copy_present(cleanup_event: dict[str, Any]) -> bool:
    evidence = cleanup_event.get("evidence") or {}
    return bool(evidence.get("torrent_present")) or _to_int(
        cleanup_event.get("retained_bytes")
    ) > 0


def _paths_mismatch(
    cleanup_event: dict[str, Any],
    import_event: dict[str, Any] | None,
    library_artifact: dict[str, Any] | None,
) -> bool:
    evidence = cleanup_event.get("evidence") or {}
    library_path = (
        evidence.get("library_path")
        or (library_artifact or {}).get("library_path")
        or (import_event or {}).get("destination_path")
    )
    expected_library_path = (import_event or {}).get("destination_path")
    if library_path and expected_library_path and library_path != expected_library_path:
        return True
    return False


def _ambiguous_download_path(cleanup_event: dict[str, Any]) -> bool:
    evidence = cleanup_event.get("evidence") or {}
    return _download_copy_present(cleanup_event) and not bool(evidence.get("download_path"))


def _media_id_mismatch(
    cleanup_event: dict[str, Any],
    imports_by_hash: dict[str, set[str]],
) -> bool:
    torrent_hash = str(cleanup_event.get("torrent_hash") or "").lower()
    media_id = str(cleanup_event.get("media_id") or "")
    if not torrent_hash or not media_id:
        return False
    linked_media = imports_by_hash.get(torrent_hash, set())
    return bool(linked_media and linked_media != {media_id})


def _evidence_strength(
    *,
    import_success: bool,
    library_status: str | None,
    match_source: str | None,
    download_present: bool,
    state_completed: bool,
) -> str:
    if import_success and library_status == LIBRARY_PRESENT and match_source == "torrent_hash":
        if download_present and state_completed:
            return "Strong"
        return "Moderate"
    if match_source in {"download_id", "torrent_hash"}:
        return "Moderate"
    if match_source == "title_match":
        return "Weak"
    return "Unknown"


def _reason(review_class: str, reasons: list[str]) -> str:
    if reasons:
        return reasons[0]
    defaults = {
        SAFE_REVIEW: "Import, library, download-copy, and completed-state evidence agree.",
        RISKY_REVIEW: "One or more evidence checks make cleanup review risky.",
        MISSING_LIBRARY: "Import succeeded, but the expected library path is missing.",
        UNKNOWN_EVIDENCE: "There is not enough evidence to decide safely.",
        ALREADY_CLEANED: "Import and library are present, and no download copy remains.",
    }
    return defaults[review_class]


def _classify_item(
    cleanup_event: dict[str, Any],
    import_event: dict[str, Any] | None,
    library_artifact: dict[str, Any] | None,
    trace: dict[str, Any] | None,
    imports_by_hash: dict[str, set[str]],
) -> dict[str, Any]:
    evidence = cleanup_event.get("evidence") or {}
    import_status = (
        evidence.get("import_status")
        or cleanup_event.get("import_status")
        or (import_event or {}).get("import_status")
    )
    import_success = import_status == IMPORT_SUCCESS
    library_status = (
        evidence.get("library_status")
        or (library_artifact or {}).get("library_status")
        or (trace or {}).get("library_status")
    )
    if not library_status and (
        evidence.get("library_file_exists")
        or cleanup_event.get("cleanup_status")
        in {CLEANUP_COMPLETED, CLEANUP_PENDING, CLEANUP_FAILED}
    ):
        library_status = LIBRARY_PRESENT
    download_present = _download_copy_present(cleanup_event)
    torrent_state = str(evidence.get("torrent_state") or "").lower()
    state_completed = torrent_state in COMPLETED_STATES
    recoverable_bytes = _to_int(cleanup_event.get("recoverable_bytes"))
    match_source = evidence.get("match_source") or (trace or {}).get("match_source")
    path_mismatch = _paths_mismatch(cleanup_event, import_event, library_artifact)
    title_only = match_source == "title_match"
    media_mismatch = _media_id_mismatch(cleanup_event, imports_by_hash)
    ambiguous_path = _ambiguous_download_path(cleanup_event)

    reasons: list[str] = []
    checks = {
        "import_success": import_success,
        "library_status": library_status,
        "download_copy_present": download_present,
        "qbittorrent_completed_state": state_completed,
        "recoverable_bytes": recoverable_bytes,
        "match_source": match_source,
        "path_mismatch": path_mismatch,
        "media_id_mismatch": media_mismatch,
        "download_path_ambiguous": ambiguous_path,
    }

    if import_success and library_status == LIBRARY_PRESENT and not download_present:
        review_class = ALREADY_CLEANED
        reasons.append("Library is present and the qBittorrent/download copy is gone.")
    elif import_success and library_status == LIBRARY_MISSING and download_present:
        review_class = MISSING_LIBRARY
        reasons.append("Import succeeded, but the expected library path is missing while the download copy remains.")
    else:
        if library_status == LIBRARY_MISSING:
            reasons.append("Library status is missing.")
        if library_status == LIBRARY_UNKNOWN:
            reasons.append("Library status is unknown.")
        if not import_success:
            reasons.append("Import success evidence is incomplete.")
        if path_mismatch:
            reasons.append("Import, library, and download paths do not agree.")
        if title_only:
            reasons.append("Only weak title correlation links the download copy.")
        if media_mismatch:
            reasons.append("The torrent hash is linked to a different media_id.")
        if ambiguous_path:
            reasons.append("Download copy path is ambiguous.")

        if reasons:
            review_class = RISKY_REVIEW
        elif (
            import_success
            and library_status == LIBRARY_PRESENT
            and download_present
            and state_completed
            and recoverable_bytes > 0
        ):
            review_class = SAFE_REVIEW
            reasons.append(
                "Import, library, download-copy, completed-state, and recoverable-byte evidence agree."
            )
        else:
            review_class = UNKNOWN_EVIDENCE
            reasons.append("There is not enough evidence to decide safely.")

    return {
        "cleanup_id": cleanup_event.get("cleanup_id"),
        "media_id": cleanup_event.get("media_id"),
        "media_title": cleanup_event.get("media_title"),
        "source_application": cleanup_event.get("source_application"),
        "torrent_hash": cleanup_event.get("torrent_hash"),
        "review_class": review_class,
        "reason": _reason(review_class, reasons),
        "reasons": reasons,
        "evidence_strength": _evidence_strength(
            import_success=import_success,
            library_status=library_status,
            match_source=match_source,
            download_present=download_present,
            state_completed=state_completed,
        ),
        "recoverable_bytes": recoverable_bytes if review_class == SAFE_REVIEW else 0,
        "retained_bytes": _to_int(cleanup_event.get("retained_bytes")),
        "cleanup_status": cleanup_event.get("cleanup_status"),
        "library_status": library_status,
        "import_status": import_status,
        "torrent_state": evidence.get("torrent_state"),
        "paths": {
            "import_source_path": (import_event or {}).get("source_path"),
            "expected_library_path": (import_event or {}).get("destination_path"),
            "library_path": evidence.get("library_path")
            or (library_artifact or {}).get("library_path"),
            "download_path": evidence.get("download_path"),
        },
        "checks": checks,
        "evidence": {
            "cleanup": evidence,
            "import": import_event or {},
            "library": library_artifact or {},
            "trace": trace or {},
        },
    }


def build_cleanup_review(
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    imports_by_media = _by_media(import_events)
    library_by_media = _by_media(library_artifacts)
    traces_by_media = _by_media(traces)
    imports_by_hash: dict[str, set[str]] = {}
    for event in import_events:
        evidence = event.get("evidence") or {}
        torrent_hash = str(evidence.get("torrent_hash") or "").lower()
        media_id = str(event.get("media_id") or "")
        if torrent_hash and media_id:
            imports_by_hash.setdefault(torrent_hash, set()).add(media_id)

    review = []
    for cleanup_event in cleanup_events:
        media_id = str(cleanup_event.get("media_id") or "")
        review.append(
            _classify_item(
                cleanup_event,
                imports_by_media.get(media_id),
                library_by_media.get(media_id),
                traces_by_media.get(media_id),
                imports_by_hash,
            )
        )
    return sorted(
        review,
        key=lambda item: (
            _to_int(item.get("retained_bytes")),
            _to_int(item.get("recoverable_bytes")),
        ),
        reverse=True,
    )


def summarize_cleanup_review(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item.get("review_class") for item in items)
    safe_recoverable = sum(_to_int(item.get("recoverable_bytes")) for item in items)
    reviewable_bytes = sum(
        _to_int(item.get("retained_bytes"))
        for item in items
        if item.get("review_class")
        in {SAFE_REVIEW, RISKY_REVIEW, MISSING_LIBRARY, UNKNOWN_EVIDENCE}
    )
    return {
        "total": len(items),
        "recoverable_bytes": reviewable_bytes,
        "safe_recoverable_bytes": safe_recoverable,
        "manual_review_bytes": reviewable_bytes,
        "safe_candidate_count": counts.get(SAFE_REVIEW, 0),
        "risky_candidate_count": counts.get(RISKY_REVIEW, 0),
        "missing_library_count": counts.get(MISSING_LIBRARY, 0),
        "unknown_evidence_count": counts.get(UNKNOWN_EVIDENCE, 0),
        "already_cleaned_count": counts.get(ALREADY_CLEANED, 0),
        "by_review_class": {name: counts.get(name, 0) for name in REVIEW_CLASSES},
    }


def cleanup_review_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "summary": summarize_cleanup_review(items),
        "top_candidates": items[:10],
        "candidates": items,
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
    return {
        "media_id": media_id,
        "review_class": matching[0].get("review_class"),
        "reason": matching[0].get("reason"),
        "candidates": matching,
    }
