import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import redis
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from qdrant_client import QdrantClient

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.core.auth import administrator
from app.core.body_limit import BodyLimitMiddleware
from app.core.config import Settings
from app.core.database import Ledger
from app.generation.generator import Generator
from app.ingestion.indexer import initialize_collection
from app.observability.metrics import LATENCY, REQUEST_COUNT
from app.observability.tracing import log_request
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Embedder

logging.basicConfig(level=logging.INFO)


def build_resources(settings):
    if settings.database_url.startswith("sqlite:///./data/"):
        Path("data").mkdir(exist_ok=True)
    ledger = Ledger(settings.database_url)
    # Production schema creation is an explicit release step.
    if settings.environment == "development":
        ledger.create_schema()
    ledger.ping()
    cache = redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.dependency_timeout_seconds,
        socket_connect_timeout=settings.dependency_timeout_seconds,
    )
    cache.ping()
    qdrant = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
        timeout=settings.dependency_timeout_seconds,
    )
    initialize_collection(qdrant, settings, create=settings.environment == "development")
    return SimpleNamespace(
        settings=settings,
        ledger=ledger,
        redis=cache,
        qdrant=qdrant,
        embedder=Embedder(settings),
        reranker=Reranker(settings.rerank_model, settings.rerank_revision),
        generator=Generator(settings),
    )


def create_app(settings=None, resources=None):
    @asynccontextmanager
    async def lifespan(application):
        state = resources or build_resources(settings or Settings())
        for key, value in vars(state).items():
            setattr(application.state, key, value)
        application.state.started = time.monotonic()
        try:
            yield
        finally:
            if resources is None:
                state.generator.close()
                state.redis.close()
                state.qdrant.close()
                state.ledger.engine.dispose()

    application = FastAPI(title="Enterprise RAG Platform", version="0.2.0", lifespan=lifespan)

    application.add_middleware(BodyLimitMiddleware)

    @application.middleware("http")
    async def observe(request: Request, call_next):
        identifier = str(uuid.uuid4())
        request.state.trace_id = identifier
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            # Never expose provider messages, credentials, queries, or source text.
            response = JSONResponse(
                {"detail": "Dependency unavailable", "request_id": identifier}, status_code=503
            )
        duration = time.monotonic() - started
        route = request.scope.get("route")
        route_name = route.path if route else "unmatched"
        REQUEST_COUNT.labels(route_name, request.method, str(response.status_code)).inc()
        LATENCY.labels(route_name).observe(duration)
        log_request(identifier, route_name, response.status_code, duration)
        response.headers["X-Request-ID"] = identifier
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    application.include_router(chat_router, prefix="/v1")
    application.include_router(health_router)

    @application.get("/metrics", dependencies=[Depends(administrator)], include_in_schema=False)
    def metrics():
        return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})

    return application


app = create_app()
