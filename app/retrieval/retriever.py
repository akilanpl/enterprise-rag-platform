from qdrant_client import QdrantClient

from app.core.config import DEFAULT_TENANT, QDRANT_COLLECTION, QDRANT_URL, TOP_K
from app.core.security import has_access
from app.core.tenant import get_tenant

client = QdrantClient(url=QDRANT_URL)


def _tenant_collection() -> str:
    tenant = get_tenant() or DEFAULT_TENANT
    return f"{QDRANT_COLLECTION}_{tenant}"


def _doc_role(hit) -> str:
    payload = getattr(hit, "payload", None) or {}
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    return metadata.get("role") or payload.get("role") or "public"


def retrieve(query_embedding, user_role):
    hits = client.search(
        collection_name=_tenant_collection(),
        query_vector=query_embedding,
        limit=TOP_K,
    )

    return [hit for hit in hits if has_access(user_role, _doc_role(hit))]
