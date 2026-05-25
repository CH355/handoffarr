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

from . import db
from .collectors import qbittorrent, radarr, seerr
from .config import Config, load_config
from .correlation import run_correlation

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
        return {"seerr": 0, "radarr": 0, "qbittorrent": 0, "traces": 0}

    for name, fn in (
        ("seerr", seerr.collect),
        ("radarr", radarr.collect),
        ("qbittorrent", qbittorrent.collect),
    ):
        try:
            results[name] = fn(config)
        except Exception as exc:  # noqa: BLE001 - one bad service must not kill poll
            logger.error("Collector %s crashed: %s", name, exc)
            results[name] = 0

    try:
        results["traces"] = run_correlation(config)
    except Exception as exc:  # noqa: BLE001
        logger.error("Correlation crashed: %s", exc)
        results["traces"] = 0
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


@app.get("/api/traces")
async def api_traces() -> JSONResponse:
    return JSONResponse({"traces": db.all_traces()})


@app.get("/api/events")
async def api_events(source: str | None = None, limit: int = 200) -> JSONResponse:
    return JSONResponse({"events": db.recent_events(source=source, limit=limit)})


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
