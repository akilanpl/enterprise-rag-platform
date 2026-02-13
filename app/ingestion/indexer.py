from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Qdrant
from qdrant_client import QdrantClient

from app.core.config import EMBEDDING_MODEL, QDRANT_COLLECTION, QDRANT_URL

client = QdrantClient(url=QDRANT_URL)

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def index_documents(docs):
    Qdrant.from_documents(
        docs,
        embeddings,
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION,
    )
