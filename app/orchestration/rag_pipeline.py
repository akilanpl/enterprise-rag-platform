from app.generation.generator import generate_answer
from app.observability.latency import track_latency
from app.retrieval.retriever import retrieve


def run_rag(query, embedding, user_role):
    timings = {}

    with track_latency(timings, "retrieval"):
        docs = retrieve(embedding, user_role)

    with track_latency(timings, "generation"):
        answer = generate_answer(query, docs)

    return answer, timings
