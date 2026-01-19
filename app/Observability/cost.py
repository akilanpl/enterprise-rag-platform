import time
from app.core.tenant import get_tenant

# 🔧 Adjust based on model pricing
COST_PER_1K_TOKENS = {
    "gpt-4o": 0.01,   # example
    "gpt-4": 0.03
}

def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    total_tokens = prompt_tokens + completion_tokens
    price = COST_PER_1K_TOKENS.get(model, 0.01)
    return (total_tokens / 1000) * price


def record_cost(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    model: str,
    query: str
):
    """
    Enterprise-grade cost capture.
    Later this can be replaced with:
    - Postgres insert
    - ClickHouse
    - Billing pipeline
    """

    tenant = get_tenant() or "default"

    cost = estimate_cost(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=model
    )

    record = {
        "timestamp": time.time(),
        "tenant": tenant,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": round(cost, 6),
        "query_preview": query[:200]
    }

    
    print("[LLM_COST]", record)

    return cost
