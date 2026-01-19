from sentence_transformers import CrossEncoder
from app.core.config import *

reranker = CrossEncoder(RERANK_MODEL)

def rerank(query, docs):
    pairs = [[query, d.page_content] for d in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, docs), reverse=True)
    return [doc for _, doc in ranked[:RERANK_TOP_K]]

