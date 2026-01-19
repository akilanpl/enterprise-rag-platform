from app.core.tenant import get_tenant
from app.core.config import QDRANT_COLLECTION, TOP_K

def retrieve(query_embedding, user_role):
    tenant = get_tenant()

    hits = client.search(
        collection_name=f"{QDRANT_COLLECTION}_{tenant}",
        query_vector=query_embedding,
        limit=TOP_K
    )

    return hits
