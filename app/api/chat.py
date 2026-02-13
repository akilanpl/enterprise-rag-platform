from fastapi import APIRouter, HTTPException
from langchain.embeddings import HuggingFaceEmbeddings

from app.core.config import EMBEDDING_MODEL
from app.core.tenant import set_tenant
from app.generation.generator import generate_answer
from app.retrieval.reranker import rerank
from app.retrieval.retriever import retrieve

router = APIRouter()
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


@router.post("/chat")
def chat(query: str, tenant_id: str, user_role: str = "employee"):
    if not tenant_id:
        raise HTTPException(400, "tenant_id is required")

    # 🔐 Bind tenant to request
    set_tenant(tenant_id)

    query_embedding = embeddings.embed_query(query)
    docs = retrieve(query_embedding, user_role)
    docs = rerank(query, docs)

    answer = generate_answer(query, docs)

    return {"answer": answer, "tenant": tenant_id}
