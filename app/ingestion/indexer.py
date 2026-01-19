from qdrant_client import QdrantClient
from langchain.vectorstores import Qdrant
from langchain.embeddings import HuggingFaceEmbeddings
from app.core.config import *

client = QdrantClient(url=QDRANT_URL)

embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def index_documents(docs):
    Qdrant.from_documents(
        docs,
        embeddings,
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION
    )
