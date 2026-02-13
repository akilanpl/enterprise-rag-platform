import json

from app.core.cache import get_cached, set_cached
from app.observability.latency import track_latency
from app.retrieval.retriever import retrieve
from app.generation.generator import generate_answer


def _cache_key(query: str, embedding, user_role: str):
    return json.dumps({"q": query, "e": embedding, "r": user_role}, sort_keys=True)


def run_rag(query, embedding, user_role):
    timings = {}
    cache_key = _cache_key(query, embedding, user_role)
    cached = get_cached("rag_answer", cache_key)
    if cached:
        timings["cache"] = "hit"
        return cached["answer"], timings

    with track_latency(timings, "retrieval"):
        docs = retrieve(embedding, user_role)

    with track_latency(timings, "generation"):
        answer = generate_answer(query, docs)

    set_cached("rag_answer", cache_key, {"answer": answer})
    timings["cache"] = "miss"
    return answer, timings
