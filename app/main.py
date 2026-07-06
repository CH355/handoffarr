"""Handoffarr FastAPI application.

Read-only dashboard tracing the Seerr -> Radarr -> qBittorrent handoff. A
background task polls the configured services on an interval; the dashboard and
JSON APIs read the correlated results out of SQLite.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from . import db, recovery, timeline
from . import torrents as torrent_projection
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
    library_response_from_enriched,
    media_library_response,
    run_library_visibility,
)
from .projections import (
    cleanup_review_projection,
    cleanup_review_projection_summary,
    library_enriched_projection,
    rebuild_cleanup_review_projection,
    rebuild_library_enriched_projection,
)
from .recommendations import (
    run_recommendations,
    summarize_recommendations,
    top_cleanup_candidates,
)
from .perf import timed
from .recovery_agent import RecoveryAgent
from .recovery_agent.comparison import compare_plans
from .responsibility import (
    build_storage_summary,
    run_responsibility,
    summarize_assessments,
)
from .validation import run_validation
from .execution_engine.executor import ExecutionEngine
from .execution_engine.queue import ExecutionQueue
from .execution_engine.locks import is_locked, lock_holder

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
_recovery_agent = RecoveryAgent()
_execution_engine: ExecutionEngine | None = None
_database_ready = False
_startup_error: str | None = None
_legacy_timeline_cache: dict = {
    "summary": {},
    "pipelines": [],
}
_response_cache: dict[str, tuple[float, object]] = {}
_response_cache_lock = threading.Lock()
_response_refreshing: set[str] = set()
_response_cache_versions: dict[str, int] = {}
_priority_two_slots = asyncio.Semaphore(4)
_priority_three_slots = asyncio.Semaphore(2)


def _get_execution_engine() -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine(get_config())
    return _execution_engine


def _cache_value(key: str) -> object | None:
    with _response_cache_lock:
        entry = _response_cache.get(key)
    return entry[1] if entry else None


def _store_cache_value(
    key: str, value: object, expected_version: int | None = None
) -> object:
    with _response_cache_lock:
        if (
            expected_version is not None
            and _response_cache_versions.get(key, 0) != expected_version
        ):
            _response_refreshing.discard(key)
            return value
        _response_cache[key] = (time.monotonic(), value)
        _response_refreshing.discard(key)
    return value


def _invalidate_cache(*keys: str) -> None:
    with _response_cache_lock:
        for key in keys:
            _response_cache.pop(key, None)
            _response_refreshing.discard(key)
            _response_cache_versions[key] = _response_cache_versions.get(key, 0) + 1


async def _cached_response(key: str, builder, ttl_seconds: int = 60):
    with _response_cache_lock:
        entry = _response_cache.get(key)
        version = _response_cache_versions.get(key, 0)
        stale = entry is not None and time.monotonic() - entry[0] >= ttl_seconds
        should_refresh = stale and key not in _response_refreshing
        if should_refresh:
            _response_refreshing.add(key)
    if entry is not None:
        if should_refresh:
            async def refresh() -> None:
                try:
                    value = await asyncio.to_thread(builder)
                    _store_cache_value(key, value, version)
                except Exception:  # noqa: BLE001
                    with _response_cache_lock:
                        _response_refreshing.discard(key)
                    logger.exception("Background response cache refresh failed key=%s", key)
            asyncio.create_task(refresh())
        return entry[1]
    return _store_cache_value(
        key, await asyncio.to_thread(builder), version
    )


def _refresh_response_snapshots() -> None:
    """Materialize expensive read models after a poll, outside request paths."""
    builders = {
        "storage": lambda: build_storage_summary(get_config()),
        "imports": lambda: imports_response(db.all_import_events()),
        "cleanup": lambda: cleanup_response(db.all_cleanup_events()),
        "validation": _validation_payload,
        "timeline": lambda: timeline.timeline_response(db.all_timeline_events()),
        "torrents": _torrents_payload,
        "health.torrents": lambda: torrent_projection.torrent_response(
            db.all_qbittorrent_torrents()
        ),
        "recovery_agent.status": _recovery_agent_status,
        "execution_engine.status": _execution_engine_status,
    }
    for key, builder in builders.items():
        try:
            with _response_cache_lock:
                version = _response_cache_versions.get(key, 0)
            _store_cache_value(key, builder(), version)
        except Exception:  # noqa: BLE001
            logger.exception("Response snapshot generation failed key=%s", key)


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
            "cleanup_review_projection": 0,
            "library_projection": 0,
            "recovery_agent": 0,
            "execution_engine": 0,
        }

    collectors = (
        ("seerr", seerr.collect),
        ("radarr", radarr.collect),
        ("sonarr_imports", sonarr_imports.collect),
        ("radarr_imports", radarr_imports.collect),
        ("lidarr_imports", lidarr_imports.collect),
        ("qbittorrent", qbittorrent.collect),
        ("filesystem", filesystem.collect),
    )
    # Connector requests are independent. Their collectors retain their existing
    # timeouts and database writes remain serialized by the database layer.
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="collector") as executor:
        pending = {
            executor.submit(fn, config): name for name, fn in collectors
        }
        for future in as_completed(pending):
            name = pending[future]
            try:
                results[name] = future.result()
            except Exception as exc:  # noqa: BLE001
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
        projection = rebuild_library_enriched_projection(config)
        results["library_projection"] = len(projection["artifacts"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Library projection crashed: %s", exc)
        results["library_projection"] = 0
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
        projection = rebuild_cleanup_review_projection(config)
        results["cleanup_review_projection"] = len(projection["items"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Cleanup review projection crashed: %s", exc)
        results["cleanup_review_projection"] = 0
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
        global _legacy_timeline_cache
        _legacy_timeline_cache = timeline.build_timeline(db.all_traces())
    except Exception as exc:  # noqa: BLE001
        logger.error("Timeline crashed: %s", exc)
        results["timeline"] = 0
    try:
        results["recovery_agent"] = _recovery_agent.tick(
            config,
            db.all_qbittorrent_torrents(),
            db.events_for_torrent,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Recovery Agent crashed: %s", exc)
        results["recovery_agent"] = 0
    try:
        engine = _get_execution_engine()
        results["execution_engine"] = engine.status()["total_jobs"]
    except Exception as exc:  # noqa: BLE001
        logger.error("Execution Engine status failed: %s", exc)
        results["execution_engine"] = 0
    _refresh_response_snapshots()
    return results


async def _poll_loop() -> None:
    config = get_config()
    interval = int(config.app.get("poll_interval_seconds", 15))
    while True:
        async with _poll_lock:
            await asyncio.to_thread(poll_once)
        await asyncio.sleep(max(5, interval))


async def _initialize_runtime() -> None:
    global _database_ready, _startup_error
    try:
        started = time.perf_counter()
        await asyncio.to_thread(db.init_db)
        _database_ready = True
        logger.info(
            "Startup database initialization completed duration_ms=%.2f",
            (time.perf_counter() - started) * 1000,
        )
        asyncio.create_task(_warm_render_caches())
        if get_config().is_present:
            await _poll_loop()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        _startup_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Background runtime initialization failed")


async def _warm_render_caches() -> None:
    global _legacy_timeline_cache
    try:
        view, _template = await asyncio.gather(
            asyncio.to_thread(lambda: timeline.build_timeline(db.all_traces())),
            asyncio.to_thread(templates.env.get_template, "timeline.html"),
        )
        _legacy_timeline_cache = view
    except Exception:  # noqa: BLE001
        logger.exception("Non-critical render cache warmup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    task = asyncio.create_task(_initialize_runtime())
    if not config.is_present:
        logger.warning(
            "Config missing at %s; dashboard will show setup message", config.path
        )
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Handoffarr", lifespan=lifespan)


def _request_priority(request: Request) -> int:
    explicit = request.headers.get("X-Handoffarr-Priority")
    if explicit in {"1", "2", "3"}:
        return int(explicit)
    path = request.url.path
    if not path.startswith("/api/"):
        return 1
    if path.startswith(("/api/health", "/api/imports", "/api/torrents")):
        return 1
    if path.startswith(("/api/debug/qbit", "/api/debug/radarr", "/api/debug/seerr")):
        return 1
    if path.startswith(("/api/storage", "/api/cleanup", "/api/recovery-agent/queue")):
        return 2
    return 3


@app.middleware("http")
async def request_performance_middleware(request: Request, call_next):
    started = time.perf_counter()
    priority = _request_priority(request)
    if (
        request.url.path.startswith("/api/")
        and request.url.path != "/api/readiness"
        and not _database_ready
    ):
        response = JSONResponse(
            {
                "error": "Handoffarr is initializing",
                "ready": False,
                "startup_error": _startup_error,
            },
            status_code=503,
            headers={"Retry-After": "1"},
        )
    elif priority == 2:
        async with _priority_two_slots:
            response = await call_next(request)
    elif priority == 3:
        async with _priority_three_slots:
            response = await call_next(request)
    else:
        response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
    logger.info(
        "route method=%s path=%s status=%s priority=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        priority,
        duration_ms,
    )
    return response


@app.get("/api/readiness")
async def api_readiness() -> JSONResponse:
    return JSONResponse(
        {"ready": _database_ready, "startup_error": _startup_error},
        status_code=200 if _database_ready else 503,
    )


@app.get("/api/health")
async def health() -> JSONResponse:
    config = get_config()
    torrent_status = await _cached_response(
        "health.torrents",
        lambda: torrent_projection.torrent_response(db.all_qbittorrent_torrents()),
    )
    return JSONResponse(
        {
            "status": "ok",
            "config_present": config.is_present,
            **torrent_status["summary"],
            "dead_torrents_health": torrent_status["health"],
        }
    )


@app.get("/timeline", response_class=HTMLResponse)
async def timeline_view(request: Request) -> HTMLResponse:
    config = get_config()
    view = _legacy_timeline_cache
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
    return JSONResponse({"traces": await asyncio.to_thread(db.all_traces)})


@app.get("/api/timeline")
async def api_timeline() -> JSONResponse:
    return JSONResponse(
        await _cached_response(
            "timeline",
            lambda: timeline.timeline_response(db.all_timeline_events()),
        )
    )


@app.get("/api/timeline/pipelines")
async def api_timeline_pipelines() -> JSONResponse:
    """Legacy pipeline projection (kept so the existing /timeline HTML page works)."""
    return JSONResponse(
        await asyncio.to_thread(lambda: timeline.build_timeline(db.all_traces()))
    )


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
    return JSONResponse(
        await _cached_response(
            "storage", lambda: build_storage_summary(get_config())
        )
    )


@app.get("/api/imports")
async def api_imports() -> JSONResponse:
    return JSONResponse(
        await _cached_response(
            "imports", lambda: imports_response(db.all_import_events())
        )
    )


@app.get("/api/imports/{media_id}")
async def api_import_media(media_id: str) -> JSONResponse:
    return JSONResponse(media_import_response(media_id, db.all_import_events(media_id)))


@app.get("/api/library")
async def api_library() -> JSONResponse:
    config = get_config()
    projection = library_enriched_projection(config)
    artifacts = projection["artifacts"]
    if artifacts:
        return JSONResponse(
            library_response_from_enriched(
                artifacts,
                projection=projection["projection"],
            )
        )
    payload = library_response(db.all_library_artifacts(), config)
    payload["projection"] = projection["projection"]
    return JSONResponse(payload)


@app.get("/api/library/{media_id}")
async def api_library_media(media_id: str) -> JSONResponse:
    return JSONResponse(
        media_library_response(media_id, db.all_library_artifacts(media_id), get_config())
    )


@app.get("/api/cleanup")
async def api_cleanup() -> JSONResponse:
    return JSONResponse(
        await _cached_response(
            "cleanup", lambda: cleanup_response(db.all_cleanup_events())
        )
    )


def _cleanup_review_snapshot() -> dict:
    return cleanup_review_projection(get_config())


def _cleanup_review_items() -> list[dict]:
    return _cleanup_review_snapshot()["items"]


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
    snapshot = _cleanup_review_snapshot()
    return JSONResponse(
        cleanup_review_response(
            snapshot["items"],
            review_class=review_class,
            match_strength=match_strength,
            min_recoverable_bytes=min_recoverable_bytes,
            source_application=source_application,
            media_type=media_type,
            limit=limit,
            offset=offset,
            sort=sort,
            projection=snapshot["projection"],
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


@app.get("/api/torrents")
async def api_torrents() -> JSONResponse:
    return JSONResponse(await _cached_response("torrents", _torrents_payload))


def _torrents_payload() -> dict:
    torrents = db.all_qbittorrent_torrents()
    evaluations = {
        torrent_hash: evaluation
        for torrent in torrents
        if (torrent_hash := str(torrent.get("hash") or "").lower())
        if (evaluation := recovery.cached_evaluation(torrent_hash)) is not None
    }
    response = torrent_projection.torrent_response(torrents, evaluations=evaluations)
    plans = db.latest_recovery_plans_by_torrent()
    for torrent in response["torrents"]:
        plan = plans.get(str(torrent.get("hash") or "").lower())
        torrent["agent_evaluated_at"] = (plan or {}).get("created_at")
        torrent["agent_confidence"] = (plan or {}).get("confidence")
        torrent["agent_recommendation"] = (plan or {}).get("recommendation")
        torrent["agent_reasoning"] = (plan or {}).get("reasoning") or []
    return response


@app.get("/api/torrents/{torrent_hash}")
async def api_torrent(torrent_hash: str) -> JSONResponse:
    torrent = torrent_projection.torrent_detail(
        torrent_hash,
        db.all_qbittorrent_torrents(),
        evaluation=recovery.cached_evaluation(torrent_hash),
    )
    if torrent is None:
        return JSONResponse({"error": "torrent not found"}, status_code=404)
    plan = db.latest_recovery_plans_by_torrent().get(torrent_hash.lower())
    torrent["agent_evaluated_at"] = (plan or {}).get("created_at")
    torrent["agent_confidence"] = (plan or {}).get("confidence")
    torrent["agent_recommendation"] = (plan or {}).get("recommendation")
    torrent["agent_reasoning"] = (plan or {}).get("reasoning") or []
    return JSONResponse(torrent)


@app.post("/api/torrents/remove-dead")
async def api_remove_selected_torrents(payload: dict) -> JSONResponse:
    raw_hashes = payload.get("hashes")
    if not isinstance(raw_hashes, list):
        return JSONResponse({"error": "hashes must be a list"}, status_code=422)
    hashes = list(
        dict.fromkeys(
            str(value or "").strip().lower()
            for value in raw_hashes
            if str(value or "").strip()
        )
    )
    current = {
        str(torrent.get("hash") or "").lower(): torrent
        for torrent in db.all_qbittorrent_torrents()
    }
    invalid = [torrent_hash for torrent_hash in hashes if torrent_hash not in current]
    if not hashes or invalid:
        return JSONResponse(
            {
                "error": "only torrents in the current snapshot may be removed",
                "invalid_hashes": invalid,
            },
            status_code=400,
        )

    # Preserve the original endpoint's keep-files behavior for older clients.
    delete_files = payload.get("delete_files", False)
    if not isinstance(delete_files, bool):
        return JSONResponse(
            {"error": "delete_files must be a boolean"}, status_code=422
        )
    result = await asyncio.to_thread(
        qbittorrent.delete_torrents,
        get_config(),
        hashes,
        delete_files=delete_files,
    )
    if not result.get("ok"):
        return JSONResponse(result, status_code=502)
    db.remove_qbittorrent_torrents(hashes)
    _invalidate_cache("torrents", "health.torrents", "recovery_agent.status")
    return JSONResponse(
        {
            "ok": True,
            "removed": len(hashes),
            "hashes": hashes,
            "delete_files": delete_files,
        }
    )


@app.post("/api/torrents/retry-dead")
async def api_retry_dead_torrents(payload: dict) -> JSONResponse:
    return JSONResponse(
        {
            "error": (
                "Automatic failed-download/blocklist and search integration "
                "is not available."
            )
        },
        status_code=501,
    )


@app.post("/api/torrents/{torrent_hash}/alternatives")
async def api_torrent_alternatives(
    torrent_hash: str, payload: dict | None = None
) -> JSONResponse:
    target = torrent_hash.strip().lower()
    torrent = next(
        (
            item
            for item in db.all_qbittorrent_torrents()
            if str(item.get("hash") or "").lower() == target
        ),
        None,
    )
    if torrent is None:
        return JSONResponse({"error": "torrent not found"}, status_code=404)
    projected = torrent_projection.enrich_torrent(torrent)
    if projected["recovery_status"] == "healthy":
        return JSONResponse(
            {"error": "healthy torrents do not need alternative evaluation"},
            status_code=400,
        )
    force = (payload or {}).get("force", False)
    if not isinstance(force, bool):
        return JSONResponse({"error": "force must be a boolean"}, status_code=422)
    try:
        evaluation = await asyncio.to_thread(
            recovery.evaluate_torrent,
            get_config(),
            torrent,
            db.events_for_torrent(target),
            force=force,
        )
    except recovery.RecoveryProviderError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    _invalidate_cache("torrents")
    return JSONResponse(evaluation)


def _recovery_agent_status() -> dict:
    config = get_config().section("recovery_agent")
    settings = db.recovery_agent_settings(
        default_enabled=bool(config.get("enabled", True)),
        default_interval=int(config.get("evaluation_interval_minutes", 15)),
    )
    aggregates = db.recovery_agent_aggregates()
    plans = db.recovery_plans(5)
    history = db.recovery_history(5)
    torrents = torrent_projection.torrent_response(db.all_qbittorrent_torrents())
    return {
        **settings,
        "jobs_evaluated": aggregates["queue_counts"]["completed"],
        "dead_torrents": torrents["summary"]["dead_torrents"],
        "plans_generated": aggregates["plans_generated"],
        "average_confidence": aggregates["average_confidence"],
        "evaluation_duration_ms": aggregates["evaluation_duration_ms"],
        "queue_counts": aggregates["queue_counts"],
        "recent_plans": plans[:5],
        "recent_decisions": history[:5],
        "recent_errors": aggregates["recent_errors"],
    }


@app.get("/api/recovery-agent/status")
async def api_recovery_agent_status() -> JSONResponse:
    return JSONResponse(
        await _cached_response("recovery_agent.status", _recovery_agent_status)
    )


@app.patch("/api/recovery-agent/settings")
async def api_recovery_agent_settings(payload: dict) -> JSONResponse:
    interval = payload.get("interval_minutes")
    if interval not in {5, 10, 15, 30, 60}:
        return JSONResponse({"error": "invalid evaluation interval"}, status_code=422)
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return JSONResponse({"error": "enabled must be a boolean"}, status_code=422)
    db.recovery_agent_settings()
    settings = db.update_recovery_agent_settings(
            enabled=enabled,
            interval_minutes=interval,
            next_evaluation_at=None,
        )
    _invalidate_cache("recovery_agent.status")
    return JSONResponse(settings)


@app.get("/api/recovery-agent/plans")
async def api_recovery_plans(
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    recommendation: str | None = None,
    sort: str = "created",
) -> JSONResponse:
    bounded = min(max(limit, 1), 1000)
    offset = max(offset, 0)
    plans, total = await asyncio.to_thread(
        db.recovery_plans_page,
        bounded,
        offset,
        search,
        recommendation,
        sort,
    )
    return JSONResponse(
        {
            "plans": plans,
            "pagination": {
                "limit": bounded,
                "offset": offset,
                "total": total,
                "has_more": offset + len(plans) < total,
            },
        }
    )


def _recovery_plan(plan_id: str) -> dict | None:
    return db.recovery_plan(plan_id)


@app.get("/api/recovery-agent/plans/{plan_id}")
async def api_recovery_plan(plan_id: str) -> JSONResponse:
    plan = await asyncio.to_thread(_recovery_plan, plan_id)
    if not plan:
        return JSONResponse({"error": "recovery plan not found"}, status_code=404)
    return JSONResponse(plan)


@app.get("/api/recovery-agent/plans/{plan_id}/comparison")
async def api_recovery_plan_comparison(plan_id: str) -> JSONResponse:
    current = await asyncio.to_thread(_recovery_plan, plan_id)
    if not current:
        return JSONResponse({"error": "recovery plan not found"}, status_code=404)
    previous = await asyncio.to_thread(
        db.previous_recovery_plan,
        current["torrent_hash"],
        current["created_at"],
    )
    changes = compare_plans(previous, current)
    return JSONResponse({"previous": previous, "current": current, "changes": changes})


@app.get("/api/recovery-agent/plans/{plan_id}/export")
async def api_recovery_plan_export(plan_id: str) -> JSONResponse:
    plan = _recovery_plan(plan_id)
    if not plan:
        return JSONResponse({"error": "recovery plan not found"}, status_code=404)
    return JSONResponse(plan, headers={"Content-Disposition": f'attachment; filename="{plan_id}.json"'})


@app.get("/api/recovery-agent/plans/{plan_id}/timeline/export")
async def api_recovery_timeline_export(plan_id: str) -> JSONResponse:
    plan = _recovery_plan(plan_id)
    if not plan:
        return JSONResponse({"error": "recovery plan not found"}, status_code=404)
    return JSONResponse({"plan_id": plan_id, "timeline": plan["timeline"]},
                        headers={"Content-Disposition": f'attachment; filename="{plan_id}-timeline.json"'})


@app.get("/api/recovery-agent/history")
async def api_recovery_history(
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    media_type: str | None = None,
    recommendation: str | None = None,
    min_confidence: float | None = None,
    health: str | None = None,
    date: str | None = None,
    status: str | None = None,
) -> JSONResponse:
    bounded = min(max(limit, 1), 1000)
    offset = max(offset, 0)
    history, total = await asyncio.to_thread(
        db.recovery_history_page,
        bounded,
        offset,
        search,
        media_type,
        recommendation,
        min_confidence,
        health,
        date,
        status,
    )
    return JSONResponse(
        {
            "history": history,
            "pagination": {
                "limit": bounded,
                "offset": offset,
                "has_more": offset + len(history) < total,
            },
        }
    )


@app.get("/api/recovery-agent/history/export")
async def api_recovery_history_export() -> PlainTextResponse:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "torrent", "health", "recommendation", "confidence",
                     "selected_candidate", "duration_ms", "candidate_count", "decision"])
    for entry in db.recovery_history(10000):
        writer.writerow([
            entry["timestamp"], entry["torrent_hash"], entry["health"].get("status"),
            entry["recommendation"], entry["confidence"],
            (entry.get("selected_candidate") or {}).get("release_name"),
            entry["evaluation_duration_ms"], entry["candidate_count"], entry["decision"],
        ])
    return PlainTextResponse(output.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="recovery-history.csv"'})


@app.get("/api/recovery-agent/queue")
async def api_recovery_queue(
    limit: int = 100, offset: int = 0, status: str | None = None
) -> JSONResponse:
    bounded = min(max(limit, 1), 1000)
    offset = max(offset, 0)
    jobs, total = await asyncio.to_thread(
        db.recovery_jobs_page, bounded, offset, status
    )
    return JSONResponse(
        {
            "jobs": jobs,
            "pagination": {
                "limit": bounded,
                "offset": offset,
                "total": total,
                "has_more": offset + len(jobs) < total,
            },
        }
    )


# --- Execution Engine API ---------------------------------------------------


def _execution_engine_status() -> dict:
    engine = _get_execution_engine()
    return engine.status()


@app.get("/api/execution-engine/status")
async def api_execution_engine_status() -> JSONResponse:
    return JSONResponse(
        await _cached_response("execution_engine.status", _execution_engine_status)
    )


@app.get("/api/execution-engine/jobs")
async def api_execution_jobs(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    engine = _get_execution_engine()
    jobs, total = await asyncio.to_thread(
        engine.queue.list_jobs, status, max(1, min(limit, 1000)), max(offset, 0)
    )
    return JSONResponse(
        {
            "jobs": [j.to_dict() for j in jobs],
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total,
                "has_more": offset + len(jobs) < total,
            },
        }
    )


@app.get("/api/execution-engine/jobs/{execution_id}")
async def api_execution_job_detail(execution_id: str) -> JSONResponse:
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.queue.get_job, execution_id)
    if not job:
        return JSONResponse({"error": "execution job not found"}, status_code=404)
    return JSONResponse(job.to_dict())


@app.get("/api/execution-engine/jobs/{execution_id}/timeline")
async def api_execution_job_timeline(execution_id: str) -> JSONResponse:
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.queue.get_job, execution_id)
    if not job:
        return JSONResponse({"error": "execution job not found"}, status_code=404)
    return JSONResponse({
        "execution_id": execution_id,
        "timeline": [t.to_dict() for t in job.timeline],
    })


@app.post("/api/execution-engine/jobs")
async def api_execution_submit(payload: dict) -> JSONResponse:
    """Submit a recovery plan for execution. Creates a Pending job."""
    plan_id = str(payload.get("plan_id") or "")
    torrent_hash = str(payload.get("torrent_hash") or "").strip().lower()
    if not plan_id or not torrent_hash:
        return JSONResponse(
            {"error": "plan_id and torrent_hash are required"}, status_code=422
        )
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.submit, plan_id, torrent_hash)
    _invalidate_cache("execution_engine.status")
    return JSONResponse({"job": job.to_dict()})


@app.post("/api/execution-engine/jobs/{execution_id}/approve")
async def api_execution_approve(execution_id: str) -> JSONResponse:
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.approve, execution_id)
    if not job:
        return JSONResponse(
            {"error": "execution job not found or not pending"}, status_code=404
        )
    _invalidate_cache("execution_engine.status")
    # Run the job in background — manual mode still requires explicit approval,
    # but execution happens asynchronously after approval.
    asyncio.create_task(asyncio.to_thread(engine.run_job, execution_id))
    return JSONResponse({"job": job.to_dict()})


@app.post("/api/execution-engine/jobs/{execution_id}/cancel")
async def api_execution_cancel(execution_id: str) -> JSONResponse:
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.cancel, execution_id)
    if not job:
        return JSONResponse(
            {"error": "execution job not found or already terminal"}, status_code=404
        )
    _invalidate_cache("execution_engine.status")
    return JSONResponse({"job": job.to_dict()})


@app.post("/api/execution-engine/jobs/{execution_id}/retry")
async def api_execution_retry(execution_id: str) -> JSONResponse:
    engine = _get_execution_engine()
    job = await asyncio.to_thread(engine.retry, execution_id)
    if not job:
        return JSONResponse(
            {"error": "execution job not found or not retryable"}, status_code=404
        )
    _invalidate_cache("execution_engine.status")
    return JSONResponse({"job": job.to_dict()})


@app.get("/api/execution-engine/locks")
async def api_execution_locks() -> JSONResponse:
    """List currently held torrent locks."""
    from .execution_engine.locks import _active_locks
    locks = []
    for torrent_hash, info in _active_locks.items():
        locks.append({
            "torrent_hash": torrent_hash,
            "execution_id": info["execution_id"],
            "acquired_at": info["acquired_at"],
        })
    return JSONResponse({"locks": locks})


# --- Debug inspection endpoints (read-only) ---------------------------------
# These hit the live service APIs (or recompute correlation from stored events)
# to expose raw payloads, normalized objects, extraction diagnostics and
# missing-field warnings. Intended for diagnosing real-world payload mismatches.


@app.get("/api/debug/radarr")
async def debug_radarr() -> JSONResponse:
    with timed("external_api", service="radarr", route="debug"):
        result = await asyncio.to_thread(radarr.inspect, get_config())
    return JSONResponse(result)


@app.get("/api/debug/qbit")
async def debug_qbit() -> JSONResponse:
    with timed("external_api", service="qbittorrent", route="debug"):
        result = await asyncio.to_thread(qbittorrent.inspect, get_config())
    return JSONResponse(result)


@app.get("/api/debug/seerr")
async def debug_seerr() -> JSONResponse:
    with timed("external_api", service="seerr", route="debug"):
        result = await asyncio.to_thread(seerr.inspect, get_config())
    return JSONResponse(result)


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
    elif "no torrent found" in (result.get("error") or "").lower():
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


@app.get("/api/debug/raw-event-dedup-audit")
async def debug_raw_event_dedup_audit() -> JSONResponse:
    return JSONResponse(db.raw_event_dedup_audit_snapshot())


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
    result = await _cached_response("validation", _validation_payload)
    return JSONResponse(result, status_code=200)


def _validation_payload() -> dict:
    config = get_config()
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="validation") as executor:
        cleanup_future = executor.submit(cleanup_review_projection_summary, config)
        library_future = executor.submit(library_enriched_projection, config)
        cleanup_projection = cleanup_future.result()
        library_projection = library_future.result()
    return run_validation(
        config,
        artifacts=library_projection["artifacts"] or None,
        review_items=None,
        projection={
            "cleanup_review": cleanup_projection,
            "library": library_projection["projection"],
        },
    )


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
