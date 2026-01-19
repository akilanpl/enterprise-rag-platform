import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "enterprise_docs"

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"
RERANK_MODEL = "BAAI/bge-reranker-large"

TOP_K = 8
RERANK_TOP_K = 4
