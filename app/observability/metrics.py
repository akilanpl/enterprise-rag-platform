from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("rag_requests_total", "HTTP requests", ["route", "method", "status"])
LATENCY = Histogram("rag_latency_seconds", "HTTP request latency", ["route"])
STAGE_LATENCY = Histogram("rag_stage_latency_seconds", "Pipeline stage latency", ["stage"])
GENERATION_COST = Counter("rag_generation_cost_usd", "Completed generation cost")
