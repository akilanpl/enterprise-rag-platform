from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Qdrant

from app.core.config import DEFAULT_TENANT, EMBEDDING_MODEL, QDRANT_COLLECTION, QDRANT_URL

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def _tenant_collection(tenant_id: str) -> str:
    return f"{QDRANT_COLLECTION}_{tenant_id or DEFAULT_TENANT}"


def index_documents(docs, tenant_id: str = DEFAULT_TENANT):
    Qdrant.from_documents(
        docs,
        embeddings,
        url=QDRANT_URL,
        collection_name=_tenant_collection(tenant_id),
    )
