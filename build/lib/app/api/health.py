import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health/live")
def liveness(request: Request):
    return {"status": "alive", "uptime_seconds": int(time.monotonic() - request.app.state.started)}


@router.get("/health/ready")
def readiness(request: Request):
    resources = request.app.state
    checks = {}
    probes = {
        "redis": resources.redis.ping,
        "database": resources.ledger.ping,
        "qdrant": lambda: resources.qdrant.get_collection(resources.settings.collection_name),
    }
    for name, probe in probes.items():
        try:
            probe()
            checks[name] = True
        except Exception:
            checks[name] = False
    ready = all(checks.values())
    return JSONResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status_code=200 if ready else 503,
    )
