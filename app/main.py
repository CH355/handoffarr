"""Handoffarr FastAPI application.

Read-only dashboard tracing the Seerr -> Radarr -> qBittorrent handoff. A
background task polls the configured services on an interval; the dashboard and
JSON APIs read the correlated results out of SQLite.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from . import db, timeline
from .collectors import (
    cleanup as cleanup_collector,
    decision as decision_collector,
    filesystem,
    library as library_collector,
    lidarr_imports,
    qbittorrent,
    radarr,
    radarr_imports,
    seerr,
    sonarr_imports,
)
from .cleanup import cleanup_response, media_cleanup_response, run_cleanup_visibility
from .cleanup_review import (
    build_cleanup_review,
    cleanup_action_plan_response,
    cleanup_action_plan_text,
    cleanup_review_response,
    media_cleanup_checklist,
    media_cleanup_review_response,
)
from .config import Config, load_config
from .correlation import correlation_report, run_correlation
from .cleanup_execution import (
    batch_dry_run as cleanup_execution_batch_dry_run,
    batch_execute as cleanup_execution_batch_execute,
    config_status as cleanup_execution_config_status,
    dry_run as cleanup_execution_dry_run,
    execute as cleanup_execute,
)
from .decision import (
    decisions_response,
    media_decision_response,
    run_decisions,
)
from .imports import imports_response, media_import_response, run_import_visibility
from .import_debug import inspect_imports
from .library import (
    library_response,
    media_library_response,
    run_library_visibility,
)
from .recommendations import (
    run_recommendations,
    summarize_recommendations,
    top_cleanup_candidates,
)
from .responsibility import (
    build_storage_summary,
    run_responsibility,
    summarize_assessments,
)
from .validation import run_validation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("handoffarr")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Built React assets are copied into <repo>/frontend_dist by the Docker build.
# For local non-Docker runs the Vite build emits to <repo>/frontend/dist; pick
# whichever exists, with an env var as a final override.
_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_DEFAULT_DIST = os.path.join(_REPO_ROOT, "frontend_dist")
if not os.path.isdir(_DEFAULT_DIST):
    _local_dist = os.path.join(_REPO_ROOT, "frontend", "dist")
    if os.path.isdir(_local_dist):
        _DEFAULT_DIST = _local_dist
FRONTEND_DIST_DIR = os.environ.get("HANDOFFARR_FRONTEND_DIST", _DEFAULT_DIST)
FRONTEND_INDEX = os.path.join(FRONTEND_DIST_DIR, "index.html")
FRONTEND_ASSETS_DIR = os.path.join(FRONTEND_DIST_DIR, "assets")

# Module-level state, set during startup.
_config: Config | None = None
_poll_lock = asyncio.Lock()


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def poll_once() -> dict[str, int]:
    """Run all collectors then correlation. Safe to call repeatedly."""
    config = get_config()
    results: dict[str, int] = {}
    if not config.is_present:
        logger.warning("Skipping poll: config not present")
        return {
            "seerr": 0,
            "radarr": 0,
            "qbittorrent": 0,
            "filesystem": 0,
            "sonarr_imports": 0,
            "radarr_imports": 0,
            "lidarr_imports": 0,
            "imports": 0,
            "library_collector": 0,
            "library": 0,
            "cleanup_collector": 0,
            "cleanup": 0,
            "traces": 0,
            "decision_collector": 0,
            "decisions": 0,
            "responsibility": 0,
            "recommendations": 0,
            "timeline": 0,
        }

    for name, fn in (
        ("seerr", seerr.collect),
        ("radarr", radarr.collect),
        ("sonarr_imports", sonarr_imports.collect),
        ("radarr_imports", radarr_imports.collect),
        ("lidarr_imports", lidarr_imports.collect),
        ("qbittorrent", qbittorrent.collect),
        ("filesystem", filesystem.collect),
    ):
        try:
            results[name] = fn(config)
        except Exception as exc:  # noqa: BLE001 - one bad service must not kill poll
            logger.error("Collector %s crashed: %s", name, exc)
            results[name] = 0

    try:
        results["imports"] = run_import_visibility(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Import visibility crashed: %s", exc)
        results["imports"] = 0
    try:
        results["library_collector"] = library_collector.collect(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Library collector crashed: %s", exc)
        results["library_collector"] = 0
    try:
        results["library"] = run_library_visibility(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Library visibility crashed: %s", exc)
        results["library"] = 0
    try:
        results["cleanup_collector"] = cleanup_collector.collect(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cleanup collector crashed: %s", exc)
        results["cleanup_collector"] = 0
    try:
        results["cleanup"] = run_cleanup_visibility(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Cleanup visibility crashed: %s", exc)
        results["cleanup"] = 0
    try:
        results["traces"] = run_correlation(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Correlation crashed: %s", exc)
        results["traces"] = 0
    try:
        results["decision_collector"] = decision_collector.collect(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Decision collector crashed: %s", exc)
        results["decision_collector"] = 0
    try:
        results["decisions"] = run_decisions(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Decision interpreter crashed: %s", exc)
        results["decisions"] = 0
    try:
        results["responsibility"] = run_responsibility(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Responsibility crashed: %s", exc)
        results["responsibility"] = 0
    try:
        results["recommendations"] = run_recommendations(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Recommendations crashed: %s", exc)
        results["recommendations"] = 0
    try:
        results["timeline"] = timeline.run_timeline()
    except Exception as exc:  # noqa: BLE001
        logger.error("Timeline crashed: %s", exc)
        results["timeline"] = 0
    return results


async def _poll_loop() -> None:
    config = get_config()
    interval = int(config.app.get("poll_interval_seconds", 15))
    while True:
        async with _poll_lock:
            await asyncio.to_thread(poll_once)
        await asyncio.sleep(max(5, interval))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    config = get_config()
    if config.is_present:
        # Kick off an immediate poll, then run the loop in the background.
        task = asyncio.create_task(_poll_loop())
    else:
        logger.warning(
            "Config missing at %s; dashboard will show setup message", config.path
        )
        task = None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(title="Handoffarr", lifespan=lifespan)


@app.get("/api/health")
async def health() -> JSONResponse:
    config = get_config()
    return JSONResponse({"status": "ok", "config_present": config.is_present})


@app.get("/timeline", response_class=HTMLResponse)
async def timeline_view(request: Request) -> HTMLResponse:
    config = get_config()
    traces = db.all_traces() if config.is_present else []
    view = timeline.build_timeline(traces)
    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "config_present": config.is_present,
            "config_path": config.path,
            "summary": view["summary"],
            "pipelines": view["pipelines"],
        },
    )


@app.get("/api/traces")
async def api_traces() -> JSONResponse:
    return JSONResponse({"traces": db.all_traces()})


@app.get("/api/timeline")
async def api_timeline() -> JSONResponse:
    return JSONResponse(timeline.timeline_response(db.all_timeline_events()))


@app.get("/api/timeline/pipelines")
async def api_timeline_pipelines() -> JSONResponse:
    """Legacy pipeline projection (kept so the existing /timeline HTML page works)."""
    return JSONResponse(timeline.build_timeline(db.all_traces()))


@app.get("/api/timeline/{media_id}")
async def api_timeline_media(media_id: str) -> JSONResponse:
    return JSONResponse(
        timeline.media_timeline_response(media_id, db.all_timeline_events(media_id))
    )


@app.get("/api/events")
async def api_events(source: str | None = None, limit: int = 200) -> JSONResponse:
    return JSONResponse({"events": db.recent_events(source=source, limit=limit)})


@app.get("/api/storage")
async def api_storage() -> JSONResponse:
    return JSONResponse(build_storage_summary(get_config()))


@app.get("/api/imports")
async def api_imports() -> JSONResponse:
    return JSONResponse(imports_response(db.all_import_events()))


@app.get("/api/imports/{media_id}")
async def api_import_media(media_id: str) -> JSONResponse:
    return JSONResponse(media_import_response(media_id, db.all_import_events(media_id)))


@app.get("/api/library")
async def api_library() -> JSONResponse:
    return JSONResponse(library_response(db.all_library_artifacts(), get_config()))


@app.get("/api/library/{media_id}")
async def api_library_media(media_id: str) -> JSONResponse:
    return JSONResponse(
        media_library_response(media_id, db.all_library_artifacts(media_id), get_config())
    )


@app.get("/api/cleanup")
async def api_cleanup() -> JSONResponse:
    return JSONResponse(cleanup_response(db.all_cleanup_events()))


def _cleanup_review_items() -> list[dict]:
    return build_cleanup_review(
        db.all_cleanup_events(),
        db.all_import_events(),
        db.all_library_artifacts(),
        db.all_traces(),
        get_config(),
    )


@app.get("/api/cleanup/action-plan")
async def api_cleanup_action_plan(
    review_class: str | None = "Safe Review Candidate",
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> JSONResponse:
    return JSONResponse(
        cleanup_action_plan_response(
            _cleanup_review_items(),
            review_class=review_class,
            match_strength=match_strength,
            min_recoverable_bytes=min_recoverable_bytes,
            source_application=source_application,
            media_type=media_type,
            limit=limit,
            offset=offset,
        )
    )


@app.get("/api/cleanup/action-plan.txt")
async def api_cleanup_action_plan_text(
    review_class: str | None = "Safe Review Candidate",
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> PlainTextResponse:
    plan = cleanup_action_plan_response(
        _cleanup_review_items(),
        review_class=review_class,
        match_strength=match_strength,
        min_recoverable_bytes=min_recoverable_bytes,
        source_application=source_application,
        media_type=media_type,
        limit=limit,
        offset=offset,
    )
    return PlainTextResponse(cleanup_action_plan_text(plan))


@app.get("/api/cleanup/executions")
async def api_cleanup_executions(limit: int = 100) -> JSONResponse:
    config = get_config()
    return JSONResponse(
        {
            "config": cleanup_execution_config_status(config),
            "executions": db.all_cleanup_executions(limit=max(1, min(limit, 500))),
            "batches": db.all_cleanup_execution_batches(limit=max(1, min(limit, 500))),
        }
    )


@app.post("/api/cleanup/execute/dry-run")
async def api_cleanup_execute_dry_run(payload: dict) -> JSONResponse:
    result = cleanup_execution_dry_run(
        media_id=str(payload.get("media_id") or ""),
        qbit_hash=str(payload.get("qbit_hash") or ""),
        confirmation=str(payload.get("confirmation") or ""),
        cleanup_events=db.all_cleanup_events(),
        import_events=db.all_import_events(),
        library_artifacts=db.all_library_artifacts(),
        traces=db.all_traces(),
        config=get_config(),
    )
    return JSONResponse(result)


@app.post("/api/cleanup/execute/batch-dry-run")
async def api_cleanup_execute_batch_dry_run(payload: dict) -> JSONResponse:
    raw_items = payload.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    result = cleanup_execution_batch_dry_run(
        items=items,
        confirmation=str(payload.get("confirmation") or ""),
        cleanup_events=db.all_cleanup_events(),
        import_events=db.all_import_events(),
        library_artifacts=db.all_library_artifacts(),
        traces=db.all_traces(),
        config=get_config(),
    )
    return JSONResponse(result)


@app.post("/api/cleanup/execute/batch")
async def api_cleanup_execute_batch(payload: dict) -> JSONResponse:
    result = cleanup_execution_batch_execute(
        plan_id=str(payload.get("plan_id") or ""),
        confirmation=str(payload.get("confirmation") or ""),
        config=get_config(),
        post_execute_poll=poll_once,
    )
    return JSONResponse(result)


@app.post("/api/cleanup/execute")
async def api_cleanup_execute(payload: dict) -> JSONResponse:
    result = cleanup_execute(
        media_id=str(payload.get("media_id") or ""),
        qbit_hash=str(payload.get("qbit_hash") or ""),
        confirmation=str(payload.get("confirmation") or ""),
        cleanup_events=db.all_cleanup_events(),
        import_events=db.all_import_events(),
        library_artifacts=db.all_library_artifacts(),
        traces=db.all_traces(),
        config=get_config(),
        post_execute_poll=poll_once,
    )
    return JSONResponse(result)


@app.get("/api/cleanup/review")
async def api_cleanup_review(
    review_class: str | None = None,
    match_strength: str | None = None,
    min_recoverable_bytes: int | None = None,
    source_application: str | None = None,
    media_type: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    sort: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        cleanup_review_response(
            _cleanup_review_items(),
            review_class=review_class,
            match_strength=match_strength,
            min_recoverable_bytes=min_recoverable_bytes,
            source_application=source_application,
            media_type=media_type,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    )


@app.get("/api/cleanup/review/{media_id}/checklist")
async def api_cleanup_review_checklist(media_id: str) -> PlainTextResponse:
    checklist = media_cleanup_checklist(
        media_id,
        _cleanup_review_items(),
    )
    if checklist is None:
        return PlainTextResponse(
            f"No cleanup review evidence exists for media_id {media_id}.",
            status_code=404,
        )
    return PlainTextResponse(checklist)


@app.get("/api/cleanup/review/{media_id}")
async def api_cleanup_review_media(media_id: str) -> JSONResponse:
    return JSONResponse(
        media_cleanup_review_response(
            media_id,
            _cleanup_review_items(),
        )
    )


@app.get("/api/cleanup/{media_id}")
async def api_cleanup_media(media_id: str) -> JSONResponse:
    return JSONResponse(media_cleanup_response(media_id, db.all_cleanup_events(media_id)))


@app.get("/api/decisions")
async def api_decisions() -> JSONResponse:
    return JSONResponse(decisions_response(db.all_decision_assessments()))


@app.get("/api/decisions/{media_id}")
async def api_decisions_media(media_id: str) -> JSONResponse:
    return JSONResponse(
        media_decision_response(media_id, db.all_decision_assessments(media_id))
    )


@app.get("/api/responsibility")
async def api_responsibility() -> JSONResponse:
    assessments = db.all_responsibility_assessments()
    summary = summarize_assessments(assessments)
    return JSONResponse(
        {
            "assessments": assessments,
            "top_responsible_domains": summary["top_responsible_domains"],
            "top_diagnosis": summary["top_diagnosis"],
            "top_responsible_domain": summary["top_responsible_domain"],
            "summary": summary,
        }
    )


@app.get("/api/responsibility/{assessment_id}")
async def api_responsibility_detail(assessment_id: str) -> JSONResponse:
    for assessment in db.all_responsibility_assessments():
        if str(assessment.get("assessment_id")) == assessment_id:
            return JSONResponse(
                {
                    "assessment_id": assessment.get("assessment_id"),
                    "diagnosis": assessment.get("diagnosis"),
                    "responsible_domain": assessment.get("responsible_domain"),
                    "confidence": assessment.get("confidence"),
                    "evidence": assessment.get("evidence") or {},
                    "impact": assessment.get("impact") or {},
                    "recommended_action": assessment.get("recommended_action"),
                    "observed_at": assessment.get("observed_at"),
                }
            )
    return JSONResponse({"error": "assessment not found"}, status_code=404)


@app.get("/api/recommendations")
async def api_recommendations() -> JSONResponse:
    recommendations = db.all_recommendations()
    summary = summarize_recommendations(recommendations)
    return JSONResponse(
        {
            "summary": summary,
            "recommendations": recommendations,
            "top_priority": summary["top_priority"],
            "total_expected_impact": {
                "recoverable_bytes": summary["total_recoverable_bytes"],
                "affected_items": summary["total_affected_items"],
            },
            "top_cleanup_candidates": top_cleanup_candidates(db.all_cleanup_events()),
        }
    )


@app.get("/api/recommendations/{recommendation_id}")
async def api_recommendation_detail(recommendation_id: str) -> JSONResponse:
    for rec in db.all_recommendations():
        if str(rec.get("recommendation_id")) == recommendation_id:
            related_assessment = None
            related_id = rec.get("related_assessment_id")
            if related_id:
                for assessment in db.all_responsibility_assessments():
                    if str(assessment.get("assessment_id")) == str(related_id):
                        related_assessment = assessment
                        break
            return JSONResponse(
                {
                    "recommendation": rec,
                    "evidence": rec.get("evidence") or {},
                    "expected_impact": rec.get("expected_impact") or {},
                    "related_assessment": related_assessment,
                }
            )
    return JSONResponse({"error": "recommendation not found"}, status_code=404)


@app.post("/api/poll-now")
async def api_poll_now() -> JSONResponse:
    config = get_config()
    if not config.is_present:
        return JSONResponse(
            {"status": "skipped", "reason": "config not present"}, status_code=409
        )
    async with _poll_lock:
        results = await asyncio.to_thread(poll_once)
    return JSONResponse({"status": "ok", "results": results})


# --- Debug inspection endpoints (read-only) -------------------------------
# These hit the live service APIs (or recompute correlation from stored events)
# to expose raw payloads, normalized objects, extraction diagnostics and
# missing-field warnings. Intended for diagnosing real-world payload mismatches.


@app.get("/api/debug/radarr")
async def debug_radarr() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(radarr.inspect, get_config()))


@app.get("/api/debug/qbit")
async def debug_qbit() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(qbittorrent.inspect, get_config()))


@app.get("/api/debug/seerr")
async def debug_seerr() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(seerr.inspect, get_config()))


@app.get("/api/debug/states")
async def debug_states() -> JSONResponse:
    return JSONResponse(
        await asyncio.to_thread(qbittorrent.states_report, get_config())
    )


@app.get("/api/debug/queue")
async def debug_queue() -> JSONResponse:
    return JSONResponse(
        await asyncio.to_thread(qbittorrent.queue_report, get_config())
    )


@app.get("/api/debug/torrent/{torrent_hash}")
async def debug_torrent(torrent_hash: str) -> JSONResponse:
    result = await asyncio.to_thread(
        qbittorrent.torrent_report, get_config(), torrent_hash
    )
    if result.get("ok"):
        status_code = 200
    elif "no torrent found" in (result.get("error") or ""):
        status_code = 404
    else:
        status_code = 502
    return JSONResponse(result, status_code=status_code)


@app.get("/api/debug/correlation")
async def debug_correlation() -> JSONResponse:
    config = get_config()
    if not config.is_present:
        return JSONResponse({"error": "config not present"}, status_code=409)
    matches = await asyncio.to_thread(correlation_report, config)
    return JSONResponse({"matches": matches})


@app.get("/api/debug/radarr-fields")
async def debug_radarr_fields() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(radarr.discover_fields, get_config()))


@app.get("/api/debug/library")
async def debug_library() -> JSONResponse:
    return JSONResponse(
        await asyncio.to_thread(library_collector.inspect, get_config())
    )


@app.get("/api/debug/imports")
async def debug_imports() -> JSONResponse:
    return JSONResponse(await asyncio.to_thread(inspect_imports, get_config()))


@app.get("/api/validation")
async def api_validation() -> JSONResponse:
    config = get_config()
    result = await asyncio.to_thread(run_validation, config)
    status_code = 200 if result["status"] != "FAIL" else 200
    return JSONResponse(result, status_code=status_code)


@app.get("/api/debug/export")
async def api_debug_export() -> JSONResponse:
    """Bundle the current persisted lifecycle state into a portable package.

    Goal: snapshot Handoffarr's view of production so future debugging does
    not require live Sonarr / Radarr / qBittorrent access. The shape mirrors
    the per-domain APIs so a fixture can be replayed against an offline copy
    of the dashboard or `app/validation.py`.
    """
    config = get_config()
    artifacts = db.all_library_artifacts()
    cleanup_events = db.all_cleanup_events()
    import_events = db.all_import_events()
    recommendations = db.all_recommendations()
    assessments = db.all_responsibility_assessments()
    decisions = db.all_decision_assessments()
    timeline_events = db.all_timeline_events()
    storage = build_storage_summary(config) if config.is_present else {}
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "config_present": config.is_present,
        "imports": imports_response(import_events),
        "library": library_response(artifacts, config),
        "cleanup": cleanup_response(cleanup_events),
        "responsibility": {
            "assessments": assessments,
            "summary": summarize_assessments(assessments),
        },
        "recommendations": {
            "summary": summarize_recommendations(recommendations),
            "recommendations": recommendations,
        },
        "timeline": timeline.timeline_response(timeline_events),
        "decisions": decisions_response(decisions),
        "storage": storage,
        "validation": await asyncio.to_thread(run_validation, config),
    }
    return JSONResponse(payload)


# --- React SPA static hosting --------------------------------------------
# Built assets are produced by `npm run build` in /frontend and copied into
# FRONTEND_DIST_DIR by the Docker image. The /assets mount serves hashed JS/CSS
# referenced by index.html; the catch-all below returns index.html for any
# non-API route so React Router can resolve client-side paths (/, /recover,
# /library, /library/123, /health, ...).

if os.path.isdir(FRONTEND_ASSETS_DIR):
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_ASSETS_DIR),
        name="frontend-assets",
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        raise HTTPException(status_code=404)
    # Serve top-level static files emitted by Vite (favicon, vite.svg, etc.)
    # before falling through to the SPA shell.
    if full_path:
        candidate = os.path.normpath(os.path.join(FRONTEND_DIST_DIR, full_path))
        if (
            candidate.startswith(os.path.normpath(FRONTEND_DIST_DIR) + os.sep)
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)
    if not os.path.isfile(FRONTEND_INDEX):
        raise HTTPException(
            status_code=503,
            detail="Frontend build is missing. Run `npm run build` in /frontend.",
        )
    return FileResponse(FRONTEND_INDEX)
