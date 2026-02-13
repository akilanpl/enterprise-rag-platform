from qdrant_client import QdrantClient

from app.core.config import QDRANT_COLLECTION, QDRANT_URL, TOP_K
from app.core.tenant import get_tenant

client = QdrantClient(url=QDRANT_URL)


def retrieve(query_embedding, user_role):
    tenant = get_tenant()

    # user_role intentionally accepted for role-aware filtering extensions.
    _ = user_role

    hits = client.search(
        collection_name=f"{QDRANT_COLLECTION}_{tenant}",
        query_vector=query_embedding,
        limit=TOP_K,
    )

    return hits
