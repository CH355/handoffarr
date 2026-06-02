"""Controlled cleanup execution workflow.

Execution is disabled by default and limited to one Safe Review Candidate. The
only allowed mutation path is qBittorrent's torrent delete endpoint with
deleteFiles=true; Handoffarr never deletes filesystem paths directly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from . import db
from .cleanup_review import SAFE_REVIEW, build_cleanup_review
from .collectors import qbittorrent
from .config import Config

COMPLETED = "Completed"
FAILED = "Failed"
BLOCKED = "Blocked"
DRY_RUN = "Dry Run"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execution_config(config: Config) -> dict[str, Any]:
    section = config.section("cleanup_execution")
    return {
        "enabled": bool(section.get("enabled", False)),
        "allow_single_item_execution": bool(
            section.get("allow_single_item_execution", False)
        ),
        "allow_batch_execution": bool(section.get("allow_batch_execution", False)),
        "require_confirmation_phrase": bool(
            section.get("require_confirmation_phrase", True)
        ),
        "require_batch_dry_run": bool(section.get("require_batch_dry_run", True)),
        "max_items_per_request": int(section.get("max_items_per_request", 1)),
        "max_batch_items": int(section.get("max_batch_items", 5)),
        "allowed_review_class": section.get("allowed_review_class", SAFE_REVIEW),
        "allowed_match_strengths": list(
            section.get(
                "allowed_match_strengths",
                [
                    "Exact Hash/DownloadId Match",
                    "Exact Library Path Match",
                    "Filename + Size Match",
                ],
            )
        ),
    }


def config_status(config: Config) -> dict[str, Any]:
    cfg = _execution_config(config)
    return {
        **cfg,
        "warning": (
            "Execution is disabled by default. Handoffarr only allows one Safe "
            "Review Candidate at a time."
        ),
    }


def _find_candidate(
    *,
    media_id: str,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
) -> dict[str, Any] | None:
    for candidate in build_cleanup_review(
        cleanup_events,
        import_events,
        library_artifacts,
        traces,
        config,
    ):
        if str(candidate.get("media_id")) == str(media_id):
            return candidate
    return None


def _live_torrent_present(config: Config, qbit_hash: str) -> tuple[bool, dict[str, Any]]:
    ok, error, torrents = qbittorrent.fetch_torrents_raw(config)
    if not ok:
        return False, {"ok": False, "error": error}
    target = str(qbit_hash or "").lower()
    for torrent in torrents:
        if str(torrent.get("hash") or "").lower() == target:
            return True, {
                "ok": True,
                "hash": target,
                "name": torrent.get("name"),
                "state": torrent.get("state"),
                "save_path": torrent.get("save_path"),
            }
    return False, {"ok": True, "hash": target, "error": "torrent not present"}


def _precheck(
    *,
    action: str,
    media_id: str,
    qbit_hash: str,
    confirmation: str,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
    expected_confirmation: str | None = None,
) -> dict[str, Any]:
    cfg = _execution_config(config)
    candidate = _find_candidate(
        media_id=media_id,
        cleanup_events=cleanup_events,
        import_events=import_events,
        library_artifacts=library_artifacts,
        traces=traces,
        config=config,
    )
    reasons: list[str] = []
    blocking: list[str] = []

    phrase = expected_confirmation or (
        f"DRY RUN CLEANUP {media_id}"
        if action == DRY_RUN
        else f"DELETE SAFE CANDIDATE {media_id}"
    )
    if cfg["require_confirmation_phrase"] and confirmation != phrase:
        blocking.append(f"Confirmation phrase must be exactly '{phrase}'.")

    if cfg["max_items_per_request"] != 1:
        blocking.append("Configuration must limit cleanup execution to one item per request.")

    if candidate is None:
        blocking.append("No cleanup review candidate exists for the supplied media_id.")
        return {
            "allowed": False,
            "reasons": reasons,
            "blocking_reasons": blocking,
            "candidate": None,
            "qbit_live": {},
            "config": cfg,
        }

    candidate_hash = str(candidate.get("torrent_hash") or "").lower()
    supplied_hash = str(qbit_hash or "").lower()
    if not supplied_hash or supplied_hash != candidate_hash:
        blocking.append("Supplied qbit_hash does not match the candidate torrent hash.")

    if candidate.get("review_class") != cfg["allowed_review_class"]:
        blocking.append(
            f"Candidate review_class is {candidate.get('review_class')}; only "
            f"{cfg['allowed_review_class']} is allowed."
        )
    else:
        reasons.append("Candidate is a Safe Review Candidate.")

    if candidate.get("match_strength") not in cfg["allowed_match_strengths"]:
        blocking.append(
            f"Match strength {candidate.get('match_strength')} is not allowed for execution."
        )
    else:
        reasons.append(f"Match strength {candidate.get('match_strength')} is allowed.")

    if not candidate.get("library_file_exists"):
        blocking.append("Library file is not verified as present.")
    else:
        reasons.append("Library file is verified present.")

    qbit_present, qbit_live = _live_torrent_present(config, supplied_hash)
    if not qbit_present:
        blocking.append("Retained qBittorrent item is not currently present.")
    else:
        reasons.append("Retained qBittorrent item is currently present.")

    if candidate.get("risk_reasons"):
        blocking.append("Candidate has risk reasons and cannot be executed.")

    return {
        "allowed": not blocking,
        "reasons": reasons,
        "blocking_reasons": blocking,
        "candidate": candidate,
        "qbit_live": qbit_live,
        "config": cfg,
    }


def _log_execution(
    *,
    execution_id: str,
    status: str,
    action: str,
    confirmation: str,
    precheck: dict[str, Any],
    batch_id: str | None = None,
    completed_at: str | None = None,
    extra_evidence: dict[str, Any] | None = None,
) -> None:
    candidate = precheck.get("candidate") or {}
    evidence = {
        "precheck": precheck,
        **(extra_evidence or {}),
    }
    row = {
        "execution_id": execution_id,
        "batch_id": batch_id,
        "media_id": candidate.get("media_id"),
        "media_title": candidate.get("media_title"),
        "qbit_hash": candidate.get("torrent_hash"),
        "review_class": candidate.get("review_class"),
        "match_strength": candidate.get("match_strength"),
        "requested_action": action,
        "execution_status": status,
        "recoverable_bytes": candidate.get("recoverable_bytes"),
        "confirmation_phrase": confirmation,
        "blocking_reasons": precheck.get("blocking_reasons") or [],
        "evidence": evidence,
        "created_at": _utcnow(),
        "completed_at": completed_at,
    }
    db.insert_cleanup_execution(row)


def dry_run(
    *,
    media_id: str,
    qbit_hash: str,
    confirmation: str,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
) -> dict[str, Any]:
    execution_id = f"dry-run:{uuid4()}"
    precheck = _precheck(
        action=DRY_RUN,
        media_id=media_id,
        qbit_hash=qbit_hash,
        confirmation=confirmation,
        cleanup_events=cleanup_events,
        import_events=import_events,
        library_artifacts=library_artifacts,
        traces=traces,
        config=config,
    )
    _log_execution(
        execution_id=execution_id,
        status=DRY_RUN if precheck["allowed"] else BLOCKED,
        action=DRY_RUN,
        confirmation=confirmation,
        precheck=precheck,
        completed_at=_utcnow(),
    )
    candidate = precheck.get("candidate") or {}
    paths = candidate.get("paths") or {}
    return {
        "execution_id": execution_id,
        "allowed": precheck["allowed"],
        "reasons": precheck["reasons"],
        "blocking_reasons": precheck["blocking_reasons"],
        "media_title": candidate.get("media_title"),
        "qbit_hash": candidate.get("torrent_hash"),
        "retained_save_path": paths.get("download_path"),
        "library_path": paths.get("library_path"),
        "recoverable_bytes": candidate.get("recoverable_bytes"),
        "would_perform": (
            "POST /api/v2/torrents/delete hashes=<qbit_hash> deleteFiles=true"
        ),
        "warning": "Dry run only. No deletion happened.",
    }


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def batch_dry_run(
    *,
    items: list[dict[str, Any]],
    confirmation: str,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
) -> dict[str, Any]:
    cfg = _execution_config(config)
    plan_id = f"batch-plan:{uuid4()}"
    blocking: list[str] = []
    if confirmation != "DRY RUN BATCH CLEANUP":
        blocking.append("Confirmation phrase must be exactly 'DRY RUN BATCH CLEANUP'.")
    if not items:
        blocking.append("Batch dry-run requires at least one item.")
    if len(items) > cfg["max_batch_items"]:
        blocking.append(
            f"Batch contains {len(items)} item(s); max_batch_items is {cfg['max_batch_items']}."
        )

    seen: set[tuple[str, str]] = set()
    per_item: list[dict[str, Any]] = []
    total_recoverable = 0
    for raw in items:
        media_id = str(raw.get("media_id") or "")
        qbit_hash = str(raw.get("qbit_hash") or "").lower()
        key = (media_id, qbit_hash)
        if key in seen:
            item_result = {
                "media_id": media_id,
                "qbit_hash": qbit_hash,
                "allowed": False,
                "blocking_reasons": ["Duplicate media_id/qbit_hash in batch plan."],
            }
            per_item.append(item_result)
            blocking.extend(item_result["blocking_reasons"])
            continue
        seen.add(key)
        precheck = _precheck(
            action=DRY_RUN,
            media_id=media_id,
            qbit_hash=qbit_hash,
            confirmation=confirmation,
            cleanup_events=cleanup_events,
            import_events=import_events,
            library_artifacts=library_artifacts,
            traces=traces,
            config=config,
            expected_confirmation="DRY RUN BATCH CLEANUP",
        )
        candidate = precheck.get("candidate") or {}
        recoverable = _to_int(candidate.get("recoverable_bytes"))
        if precheck["allowed"]:
            total_recoverable += recoverable
        item_result = {
            "media_id": media_id,
            "media_title": candidate.get("media_title"),
            "qbit_hash": candidate.get("qbit_hash") or candidate.get("torrent_hash") or qbit_hash,
            "review_class": candidate.get("review_class"),
            "match_strength": candidate.get("match_strength"),
            "recoverable_bytes": recoverable,
            "allowed": precheck["allowed"],
            "reasons": precheck["reasons"],
            "blocking_reasons": precheck["blocking_reasons"],
        }
        per_item.append(item_result)
        if not precheck["allowed"]:
            blocking.extend(precheck["blocking_reasons"])

    allowed = not blocking
    if allowed:
        db.insert_cleanup_execution_batch(
            {
                "batch_id": plan_id,
                "status": DRY_RUN,
                "item_count": len(per_item),
                "completed_count": 0,
                "failed_count": 0,
                "planned_recoverable_bytes": total_recoverable,
                "actual_recovered_bytes": 0,
                "evidence": {
                    "allowed": True,
                    "items": per_item,
                    "confirmation": confirmation,
                    "config": cfg,
                },
            }
        )

    return {
        "allowed": allowed,
        "plan_id": plan_id if allowed else None,
        "item_count": len(per_item),
        "total_recoverable_bytes": total_recoverable if allowed else 0,
        "per_item": per_item,
        "blocking_reasons": sorted(set(blocking)),
        "warning": "Batch dry run only. No deletion happened.",
    }


def execute(
    *,
    media_id: str,
    qbit_hash: str,
    confirmation: str,
    cleanup_events: list[dict[str, Any]],
    import_events: list[dict[str, Any]],
    library_artifacts: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    config: Config,
    post_execute_poll: Callable[[], Any],
    batch_id: str | None = None,
    bypass_single_gate: bool = False,
) -> dict[str, Any]:
    execution_id = f"execute:{uuid4()}"
    precheck = _precheck(
        action="Execute",
        media_id=media_id,
        qbit_hash=qbit_hash,
        confirmation=confirmation,
        cleanup_events=cleanup_events,
        import_events=import_events,
        library_artifacts=library_artifacts,
        traces=traces,
        config=config,
    )
    cfg = precheck["config"]
    gate_blocks = []
    if not cfg["enabled"]:
        gate_blocks.append("cleanup_execution.enabled is false.")
    if not cfg["allow_single_item_execution"] and not bypass_single_gate:
        gate_blocks.append("cleanup_execution.allow_single_item_execution is false.")
    precheck["blocking_reasons"].extend(gate_blocks)
    precheck["allowed"] = precheck["allowed"] and not gate_blocks

    if not precheck["allowed"]:
        _log_execution(
            execution_id=execution_id,
            status=BLOCKED,
            action="Execute",
            confirmation=confirmation,
            precheck=precheck,
            batch_id=batch_id,
            completed_at=_utcnow(),
        )
        return {
            "execution_id": execution_id,
            "execution_status": BLOCKED,
            "precheck_evidence": precheck,
            "qbittorrent_api_result": None,
            "postcheck_evidence": {},
            "qbittorrent_item_disappeared": False,
            "library_file_still_exists": None,
            "estimated_recoverable_bytes": (
                (precheck.get("candidate") or {}).get("recoverable_bytes")
            ),
            "actual_verification_status": "Blocked before qBittorrent call.",
        }

    _log_execution(
        execution_id=execution_id,
        status="Started",
        action="Execute",
        confirmation=confirmation,
        precheck=precheck,
        batch_id=batch_id,
    )
    qbit_result = qbittorrent.delete_torrent_with_files(config, qbit_hash)
    post_poll_result = None
    postcheck: dict[str, Any] = {}
    try:
        post_poll_result = post_execute_poll()
        qbit_present, qbit_live = _live_torrent_present(config, qbit_hash)
        post_candidate = _find_candidate(
            media_id=media_id,
            cleanup_events=db.all_cleanup_events(),
            import_events=db.all_import_events(),
            library_artifacts=db.all_library_artifacts(),
            traces=db.all_traces(),
            config=config,
        )
        postcheck = {
            "poll_result": post_poll_result,
            "qbit_live": qbit_live,
            "qbit_item_disappeared": not qbit_present,
            "library_file_still_exists": bool(
                post_candidate and post_candidate.get("library_file_exists")
            ),
            "post_candidate": post_candidate,
        }
    except Exception as exc:  # noqa: BLE001
        postcheck = {"error": f"{type(exc).__name__}: {exc}"}

    status = COMPLETED if qbit_result.get("ok") and postcheck.get("qbit_item_disappeared") else FAILED
    if not postcheck.get("library_file_still_exists"):
        status = FAILED
    db.update_cleanup_execution(
        execution_id,
        {
            "execution_status": status,
            "blocking_reasons": [] if status == COMPLETED else ["Postcheck failed."],
            "evidence": {
                "precheck": precheck,
                "qbit_result": qbit_result,
                "postcheck": postcheck,
            },
            "completed_at": _utcnow(),
        },
    )
    return {
        "execution_id": execution_id,
        "execution_status": status,
        "precheck_evidence": precheck,
        "qbittorrent_api_result": qbit_result,
        "postcheck_evidence": postcheck,
        "qbittorrent_item_disappeared": bool(postcheck.get("qbit_item_disappeared")),
        "library_file_still_exists": postcheck.get("library_file_still_exists"),
        "estimated_recoverable_bytes": (
            (precheck.get("candidate") or {}).get("recoverable_bytes")
        ),
        "actual_verification_status": (
            "Verified" if status == COMPLETED else "Failed verification"
        ),
    }


def batch_execute(
    *,
    plan_id: str,
    confirmation: str,
    config: Config,
    post_execute_poll: Callable[[], Any],
) -> dict[str, Any]:
    cfg = _execution_config(config)
    batch = db.cleanup_execution_batch(plan_id)
    blocking: list[str] = []
    if confirmation != "EXECUTE BATCH CLEANUP":
        blocking.append("Confirmation phrase must be exactly 'EXECUTE BATCH CLEANUP'.")
    if not cfg["enabled"]:
        blocking.append("cleanup_execution.enabled is false.")
    if not cfg["allow_batch_execution"]:
        blocking.append("cleanup_execution.allow_batch_execution is false.")
    if batch is None:
        blocking.append("No successful batch dry-run plan exists for this plan_id.")

    plan_items = []
    if batch:
        evidence = batch.get("evidence") or {}
        if batch.get("status") != DRY_RUN or not evidence.get("allowed"):
            blocking.append("Batch plan is not a successful dry run.")
        try:
            created = datetime.fromisoformat(str(batch.get("created_at")))
            age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
            if age_seconds > 1800:
                blocking.append("Batch dry-run plan is older than 30 minutes.")
        except (TypeError, ValueError):
            blocking.append("Batch dry-run plan timestamp is invalid.")
        plan_items = evidence.get("items") if isinstance(evidence.get("items"), list) else []
        if len(plan_items) > cfg["max_batch_items"]:
            blocking.append(
                f"Batch plan contains {len(plan_items)} item(s); max_batch_items is {cfg['max_batch_items']}."
            )

    if blocking:
        if batch:
            db.update_cleanup_execution_batch(
                plan_id,
                {
                    "status": BLOCKED,
                    "completed_count": 0,
                    "failed_count": 0,
                    "actual_recovered_bytes": 0,
                    "evidence": {
                        **(batch.get("evidence") or {}),
                        "execute_blocking_reasons": blocking,
                    },
                    "completed_at": _utcnow(),
                },
            )
        return {
            "batch_status": BLOCKED,
            "plan_id": plan_id,
            "completed_count": 0,
            "failed_count": 0,
            "total_recovered_bytes": 0,
            "per_item": [],
            "blocking_reasons": blocking,
        }

    completed = 0
    failed = 0
    recovered = 0
    per_item_results: list[dict[str, Any]] = []
    status = COMPLETED
    for planned in plan_items:
        media_id = str(planned.get("media_id") or "")
        qbit_hash = str(planned.get("qbit_hash") or "").lower()
        result = execute(
            media_id=media_id,
            qbit_hash=qbit_hash,
            confirmation=f"DELETE SAFE CANDIDATE {media_id}",
            cleanup_events=db.all_cleanup_events(),
            import_events=db.all_import_events(),
            library_artifacts=db.all_library_artifacts(),
            traces=db.all_traces(),
            config=config,
            post_execute_poll=post_execute_poll,
            batch_id=plan_id,
            bypass_single_gate=True,
        )
        per_item_results.append(result)
        if result.get("execution_status") == COMPLETED:
            completed += 1
            recovered += _to_int(result.get("estimated_recoverable_bytes"))
            continue
        failed += 1
        status = "Partially Completed" if completed else FAILED
        break

    db.update_cleanup_execution_batch(
        plan_id,
        {
            "status": status,
            "completed_count": completed,
            "failed_count": failed,
            "actual_recovered_bytes": recovered,
            "evidence": {
                **(batch.get("evidence") or {}),
                "execution_results": per_item_results,
                "stopped_on_first_failure": failed > 0,
            },
            "completed_at": _utcnow(),
        },
    )
    return {
        "batch_status": status,
        "plan_id": plan_id,
        "completed_count": completed,
        "failed_count": failed,
        "total_recovered_bytes": recovered,
        "per_item": per_item_results,
        "blocking_reasons": [],
    }
