"""Cleanup reconciliation helpers for completed controlled executions."""

from __future__ import annotations

from typing import Any


def _norm_hash(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text or None


def completed_execution_confirmed(execution: dict[str, Any]) -> bool:
    if execution.get("execution_status") != "Completed":
        return False
    evidence = execution.get("evidence") or {}
    postcheck = evidence.get("postcheck") or evidence.get("postcheck_evidence") or {}
    return bool(postcheck.get("qbit_item_disappeared")) and bool(
        postcheck.get("library_file_still_exists")
    )


def latest_completed_execution_index(
    executions: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Index confirmed completed executions by media_id and qBittorrent hash."""
    by_media: dict[str, dict[str, Any]] = {}
    by_hash: dict[str, dict[str, Any]] = {}
    for execution in executions:
        if not completed_execution_confirmed(execution):
            continue
        media_id = str(execution.get("media_id") or "")
        qbit_hash = _norm_hash(execution.get("qbit_hash"))
        if media_id and media_id not in by_media:
            by_media[media_id] = execution
        if qbit_hash and qbit_hash not in by_hash:
            by_hash[qbit_hash] = execution
    return {"by_media": by_media, "by_hash": by_hash}


def matching_completed_execution(
    item: dict[str, Any],
    index: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    media_id = str(item.get("media_id") or "")
    qbit_hash = _norm_hash(
        item.get("qbit_hash")
        or item.get("torrent_hash")
        or ((item.get("evidence") or {}).get("qbittorrent_torrent") or {}).get(
            "torrent_hash"
        )
    )
    by_media = index.get("by_media") or {}
    by_hash = index.get("by_hash") or {}
    if media_id and media_id in by_media:
        return by_media[media_id]
    if qbit_hash and qbit_hash in by_hash:
        return by_hash[qbit_hash]
    return None


def completed_execution_hashes(executions: list[dict[str, Any]]) -> set[str]:
    index = latest_completed_execution_index(executions)
    return set(index["by_hash"])
