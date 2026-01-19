from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "rag_requests_total",
    "Total RAG queries"
)

LATENCY = Histogram(
    "rag_latency_seconds",
    "End-to-end latency"
)

RETRIEVAL_SCORE = Histogram(
    "retrieval_confidence",
    "Average retrieval relevance"
)
