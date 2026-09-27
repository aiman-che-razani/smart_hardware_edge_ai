import asyncio
import logging
from pathlib import Path
import sys
from fastapi import APIRouter, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sentinel.storage.database import Store
from sentinel.storage.queries import measurements, query, status

LOG = logging.getLogger(__name__)
# The API is read-only and unauthenticated, so it answers only to its own loopback names: a web
# page that rebinds its DNS to 127.0.0.1 arrives with a foreign Host header and is refused.
# IPv4 loopback only: the server binds 127.0.0.1, and Starlette cannot match a bracketed IPv6 Host.
LOCAL_HOSTS = ("127.0.0.1", "localhost")


def create_app(root="data", allowed_hosts=LOCAL_HOSTS):
    if sys.version_info[:3] == (3, 9, 0):
        LOG.warning("Python 3.9.0 cannot build /openapi.json (nested Literal bug); use Python >= 3.9.1")
    Store(root).close()
    app = FastAPI(title="SentinelDAQ", version="0.1.0")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))
    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health():
        return {"service": "ok", "daq": status(root)}

    @api.get("/system/status")
    def system_status():
        return status(root)

    @api.get("/machines")
    def machines():
        return query(root, "SELECT DISTINCT machine_id FROM experiment_run")

    @api.get("/experiments")
    def experiments(limit: int = Query(100, ge=1, le=1000)):
        return query(root, "SELECT * FROM experiment_run ORDER BY started_at DESC LIMIT ?", (limit,))

    @api.get("/measurements")
    def raw(run_id: str = None, limit: int = Query(800, ge=1, le=3200)):
        try:
            return measurements(root, run_id, limit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    @api.get("/features")
    def features(run_id: str = None, limit: int = Query(100, ge=1, le=1000)):
        run_id = run_id or None
        return query(root, "SELECT * FROM feature_window WHERE (? IS NULL OR run_id=?) ORDER BY timestamp DESC LIMIT ?", (run_id, run_id, limit))

    @api.get("/predictions")
    def predictions(run_id: str = None, limit: int = Query(100, ge=1, le=1000)):
        run_id = run_id or None
        return query(root, "SELECT p.*, f.run_id, f.timestamp FROM prediction p JOIN feature_window f USING(window_id) WHERE (? IS NULL OR f.run_id=?) ORDER BY timestamp DESC LIMIT ?", (run_id, run_id, limit))

    @api.get("/events")
    def events(run_id: str = None, limit: int = Query(100, ge=1, le=1000)):
        run_id = run_id or None
        return query(root, "SELECT * FROM event WHERE (? IS NULL OR run_id=?) ORDER BY started_at DESC LIMIT ?", (run_id, run_id, limit))

    @api.websocket("/live")
    async def live(socket: WebSocket):
        # Browsers do not apply the same-origin policy to WebSockets, so require it here.
        origin = socket.headers.get("origin")
        if origin and origin.split("://", 1)[-1] != socket.headers.get("host"):
            await socket.close(code=1008)
            return
        await socket.accept()
        try:
            while True:
                await socket.send_json(status(root))
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass

    app.include_router(api)

    dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    else:
        LOG.info("frontend/dist not found; serving /api/* JSON only. "
                 "Run `npm install && npm run build` in frontend/ to enable the web UI.")
    return app
