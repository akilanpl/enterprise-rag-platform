# Application implementation

Start with the [root README](../README.md) for setup, API examples, configuration, and deployment.

The application factory in `main.py` creates dependencies during lifespan startup, never at import time. It validates settings and storage before accepting requests, loads optional local models, exposes health probes, and closes production clients on shutdown. Tests inject resources into the same factory.

| Module | Responsibility |
| --- | --- |
| `api` | JSON contracts, authentication dependencies, tenant admin operations, feedback ownership, health probes. |
| `core` | Validated settings, immutable principals, role hierarchy, actual request-byte limits, Redis rate limits/cache, SQL ledger. |
| `ingestion` | Operator PDF extraction, normalized overlapping chunks, deterministic content-version IDs, vector upserts and tenant-filtered deletes. |
| `retrieval` | Semantic or development lexical embeddings, mandatory tenant/role filters, typed document conversion, optional cross encoder. |
| `generation` | Untrusted-source prompt construction, local extractive answers, explicitly enabled hosted inference. |
| `orchestration` | Admission, retrieval/rerank, conservative reservation, generation, durable settlement, citation response. |
| `observability` | Correlated structured logs, HTTP/pipeline metrics, monotonic timings. |
| `evaluation` | Labeled retrieval recall; optional RAGAS integration loaded only when invoked. |
| `infra` | Local Compose compatibility and Kubernetes API resources. |

Tenant identity is passed explicitly as `Principal`; there is no default tenant context. `Ledger` owns budgets, usage, and feedback. `Document` is the retrieval/generation contract, replacing incompatible raw Qdrant hit objects.

Read [architecture](../docs/architecture.md), [security](../docs/security.md), and [operations](../docs/operations.md) before extending these boundaries. Add regression coverage whenever a new path reads or changes tenant-owned data.
