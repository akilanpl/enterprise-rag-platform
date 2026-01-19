from fastapi import APIRouter
from qdrant_client import QdrantClient
import redis
import os
import time

router = APIRouter()

START_TIME = time.time()

# External dependencies
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

qdrant = QdrantClient(url=QDRANT_URL)
redis_client = redis.Redis(host=REDIS_HOST, port=6379)


@router.get("/health/live")
def liveness():
    """
    Kubernetes liveness probe.
    If this fails, pod will be restarted.
    """
    return {
        "status": "alive",
        "uptime_seconds": int(time.time() - START_TIME)
    }



@router.get("/health/ready")
def readiness():
    """
    Kubernetes readiness probe.
    If this fails, pod will be removed from service.
    """

    checks = {
        "qdrant": False,
        "redis": False
    }

    # Check Qdrant
    try:
        qdrant.get_collections()
        checks["qdrant"] = True
    except Exception:
        checks["qdrant"] = False

    # Check Redis
    try:
        redis_client.ping()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    ready = all(checks.values())

    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks
    }
