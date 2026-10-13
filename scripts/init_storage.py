"""One-time release job for the v0.2 schema and versioned Qdrant collection."""

from qdrant_client import QdrantClient

from app.core.config import Settings
from app.core.database import Ledger
from app.ingestion.indexer import initialize_collection

settings = Settings()
ledger = Ledger(settings.database_url)
ledger.create_schema()
with QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
    timeout=settings.dependency_timeout_seconds,
) as client:
    initialize_collection(client, settings)
ledger.engine.dispose()
