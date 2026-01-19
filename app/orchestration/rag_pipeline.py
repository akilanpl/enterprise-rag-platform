from app.core.cache import get_cached, set_cached
from app.observability.latency import track_latency

def run_rag(query, embedding, user_role):
    timings = {}

    with track_latency(timings, "retrieval"):
        docs = retrieve(embedding, user_role)

    with track_latency(timings, "generation"):
        answer = generate_answer(query, docs)

    return answer, timings
