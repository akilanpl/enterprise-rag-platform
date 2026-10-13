import time

from app.core.cache import query_embedding
from app.core.rate_limit import rate_limit
from app.observability.metrics import GENERATION_COST, STAGE_LATENCY
from app.retrieval.retriever import retrieve


def run_rag(resources, principal, query, request_id=None):
    settings = resources.settings
    rate_limit(resources.redis, principal, settings.rate_limit_per_minute)
    start = time.monotonic()
    vector = query_embedding(resources.redis, resources.embedder, settings, principal.tenant, query)
    docs = retrieve(resources.qdrant, settings, principal, vector)
    docs = resources.reranker.rerank(query, docs, settings.rerank_top_k)
    STAGE_LATENCY.labels("retrieval").observe(time.monotonic() - start)
    prompt = resources.generator.prepare(query, docs)
    reservation = resources.generator.reservation(prompt) if docs else 0
    model = (
        settings.generation_model if settings.generation_backend != "extractive" else "extractive"
    )
    identifier = resources.ledger.reserve(
        principal, model, reservation, settings.monthly_budget_usd, request_id=request_id
    )
    citations = [
        {"label": f"DOC {i}", **doc.metadata, "score": doc.score} for i, doc in enumerate(docs)
    ]
    start = time.monotonic()
    try:
        generated = resources.generator.generate(query, docs, prompt)
    except Exception:
        resources.ledger.settle(identifier, 0, 0, 0, [], failed=True)
        raise
    resources.ledger.settle(
        identifier, generated.cost, generated.prompt_tokens, generated.completion_tokens, citations
    )
    GENERATION_COST.inc(generated.cost)
    STAGE_LATENCY.labels("generation").observe(time.monotonic() - start)
    return {
        "request_id": identifier,
        "answer": generated.answer,
        "tenant": principal.tenant,
        "citations": citations,
        "usage": {
            "prompt_tokens": generated.prompt_tokens,
            "completion_tokens": generated.completion_tokens,
            "cost_usd": generated.cost,
        },
    }
