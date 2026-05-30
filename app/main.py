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

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
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
from .config import Config, load_config
from .correlation import correlation_report, run_correlation
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("handoffarr")

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

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


@app.get("/health")
async def health() -> JSONResponse:
    config = get_config()
    return JSONResponse({"status": "ok", "config_present": config.is_present})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    config = get_config()
    traces = db.all_traces() if config.is_present else []
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "config_present": config.is_present,
            "config_path": config.path,
            "traces": traces,
        },
    )


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
