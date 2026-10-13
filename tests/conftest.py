import os
import uuid
from types import SimpleNamespace

import fakeredis
import pytest
import redis
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.core.config import Settings, hash_key
from app.core.database import Ledger
from app.generation.generator import Generator
from app.ingestion.indexer import initialize_collection
from app.main import create_app
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Embedder


@pytest.fixture
def service(tmp_path):
    suffix = uuid.uuid4().hex[:12]
    credentials = []
    for key, tenant, role in [
        ("admin-a", "a", "admin"),
        ("employee-a", "a", "employee"),
        ("manager-a", "a", "manager"),
        ("admin-b", "b", "admin"),
    ]:
        credentials.append(
            {
                "key_sha256": hash_key(key),
                "tenant": tenant + suffix,
                "subject": key + suffix,
                "role": role,
            }
        )
    settings = Settings(
        _env_file=None,
        api_keys=credentials,
        database_url=os.getenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path}/ledger.db"),
        qdrant_collection="test_" + suffix,
        embedding_dimensions=64,
    )
    ledger = Ledger(settings.database_url)
    ledger.create_schema()
    qdrant = (
        QdrantClient(url=os.environ["TEST_QDRANT_URL"])
        if os.getenv("TEST_QDRANT_URL")
        else QdrantClient(":memory:")
    )
    cache = (
        redis.Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        if os.getenv("TEST_REDIS_URL")
        else fakeredis.FakeRedis(decode_responses=True)
    )
    initialize_collection(qdrant, settings)
    resources = SimpleNamespace(
        settings=settings,
        ledger=ledger,
        redis=cache,
        qdrant=qdrant,
        embedder=Embedder(settings),
        reranker=Reranker(),
        generator=Generator(settings),
    )
    with TestClient(create_app(settings, resources)) as client:
        yield client, resources
    resources.generator.close()
    qdrant.delete_collection(settings.collection_name)
    qdrant.close()
    cache.close()
    ledger.engine.dispose()


def headers(key="admin-a"):
    return {"X-API-Key": key}


def ingest(
    client,
    text="Vacation policy provides twenty paid days annually.",
    role="employee",
    key="admin-a",
):
    result = client.post(
        "/v1/documents", headers=headers(key), json={"title": "Policy", "text": text, "role": role}
    )
    assert result.status_code == 201, result.text
    return result.json()
