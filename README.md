# Enterprise RAG Platform

**Authenticated, tenant-isolated retrieval with grounded answers, persistent usage governance, and deployable infrastructure.**

A modular Python service for enterprise knowledge retrieval. Documents are chunked, embedded, stored in Qdrant, filtered by tenant and access level, optionally reranked, and returned as cited evidence. PostgreSQL records usage and reserves tenant budgets before a hosted generation call; Redis coordinates rate limits across API replicas.

The platform can keep documents and inference on your infrastructure. The default development configuration uses deterministic lexical embeddings and extractive answers so the complete request path runs without downloading models or sending documents to a provider. Production mode requires semantic embeddings and PostgreSQL. Hosted generation is separately enabled and explicitly permits authorized context to leave your environment.

## Contents

- [Capabilities](#capabilities)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [API](#api)
- [Configuration](#configuration)
- [Security and tenant isolation](#security-and-tenant-isolation)
- [Cost governance](#cost-governance)
- [Testing and evaluation](#testing-and-evaluation)
- [Deployment and operations](#deployment-and-operations)
- [Repository layout](#repository-layout)
- [Compatibility and limitations](#compatibility-and-limitations)

## Capabilities

| Area | Implemented behavior |
| --- | --- |
| Identity | Hashed service API keys bind a subject to exactly one tenant and role. Clients cannot select their own tenant or role. |
| Authorization | Qdrant filters tenant and permitted document roles **before** returning candidate text. Tenant administrators control ingestion and deletion. |
| Ingestion | Bounded text ingestion, local PDF extraction utility, overlapping chunks, deterministic content/version IDs, and retry-safe upserts. |
| Retrieval | Cosine vector search, model-specific collections, tenant-scoped embedding cache, and optional cross-encoder reranking. |
| Generation | Local cited excerpts, on-premises Ollama, or opt-in hosted generation; no-authorized-evidence requests return an insufficient-information response. |
| Governance | Atomic monthly budget reservations, separate input/output prices, persistent token usage, and conservative handling of ambiguous provider failures. |
| Reliability | Dependency timeouts, startup validation, actual request-byte limits, distributed Redis limits, safe error responses, and separate live/ready probes. |
| Observability | Low-cardinality Prometheus counters/histograms, correlated structured request logs, durable usage/citation records, and owned feedback. |
| Delivery | Non-root container, persistent development Compose services, Kubernetes rollout/probe/resource configuration, pinned runtime dependencies, and CI. |
| Evaluation | Labeled retrieval-recall CLI, security regression tests, and an optional RAGAS adapter. |

These are application capabilities. An actual production deployment also needs the environment controls and validation described in [operations](docs/operations.md), including TLS, private storage networks, backups, model provisioning, and workload-specific evaluation. No compliance certification, latency benchmark, or retrieval-quality score is implied.

## Architecture

```mermaid
flowchart LR
    Client[Authenticated client] --> API[FastAPI /v1]
    API --> Identity[Key → tenant / subject / role]
    Identity --> Rate[Redis rate admission]
    Rate --> Ingest[Chunk / embed / upsert]
    Ingest --> Qdrant[(Qdrant: tenant + role payloads)]
    Rate --> Embed[Query embedding / tenant cache]
    Embed --> Search[Filtered cosine search]
    Qdrant --> Search
    Search --> Rank[Optional cross encoder]
    Rank --> Budget[Atomic budget reservation]
    Budget --> PG[(PostgreSQL usage + budgets)]
    Budget --> Answer[Local excerpts or opted-in provider]
    Answer --> Settle[Settle usage / sources]
    Settle --> PG
    Settle --> Client
    API --> Observe[Metrics / structured logs]
```

The authenticated principal is passed explicitly to storage operations. There is no default tenant and no mutable global tenant context. Collections are partitioned by an embedding-configuration fingerprint; tenant and role are additional mandatory filters inside each collection. The API process is horizontally scalable when replicas share PostgreSQL, Redis, Qdrant, credentials, and model configuration.

See [architecture and failure semantics](docs/architecture.md) for request sequences, storage contracts, and tradeoffs.

## Quick start

Requirements: Git, Python 3.11+ for the secret-generation utility, and Docker with Compose v2.20+.

```bash
git clone https://github.com/akilanpl/enterprise-rag-platform.git
cd enterprise-rag-platform
python3 scripts/configure.py --tenant acme --subject admin
```

The utility creates a permission-restricted `.env` with a random database password and a hashed tenant administrator credential. It prints the actual API key once. Store it securely, then set it in your shell:

```bash
export RAG_API_KEY='paste-the-generated-key-here'
docker compose up --build -d
docker compose logs -f api
```

Wait for the API to be healthy, then check readiness:

```bash
curl --fail http://localhost:8000/health/ready
```

Ingest a document and query it:

```bash
curl --fail-with-body http://localhost:8000/v1/documents \
  -H "X-API-Key: $RAG_API_KEY" -H 'Content-Type: application/json' \
  -d '{"title":"Leave policy","text":"Employees receive twenty paid vacation days annually.","role":"employee"}'

curl --fail-with-body http://localhost:8000/v1/chat \
  -H "X-API-Key: $RAG_API_KEY" -H 'Content-Type: application/json' \
  -d '{"query":"How many paid vacation days do employees receive?"}'
```

The chat response includes the answer, tenant, request ID, citation mapping, token usage, and cost. The development backend returns cited source excerpts rather than synthesized prose. Its lexical embeddings are for smoke tests, not semantic quality evaluation.

Open [API documentation](http://localhost:8000/docs). `docker compose down` stops the stack while preserving data volumes. Deleting volumes deletes stored data.

### Local Python development and tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install -e '.[test]'
pytest -q
ruff check app scripts tests
ruff format --check app scripts tests
```

The default test suite uses embedded Qdrant, fake Redis executing the actual Lua limiter, and a temporary SQLite ledger. No provider key, model download, or external service is needed. To run the API directly, provide reachable dependency URLs in `.env` and run `uvicorn app.main:app --no-access-log`; Compose's service hostnames resolve only inside its network.

### Enable semantic retrieval and reranking

Set these values in `.env` and rebuild the image:

```dotenv
INSTALL_MODELS=true
EMBEDDING_BACKEND=sentence-transformer
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSIONS=1024
RERANK_MODEL=BAAI/bge-reranker-large
```

```bash
docker compose up --build -d
```

Model loading happens at startup. Provision enough memory and allow the initial download in a controlled environment, or populate the model cache before starting an offline deployment. Set model revisions or use local model paths for reproducibility. Changing embedding backend, model, revision, or dimensions selects a different collection; **reingest documents** for that configuration. Reranking is optional; without it, vector scores determine ordering.

### Enable an on-premises generative model

With a separately provisioned Ollama server and approved local model:

```dotenv
GENERATION_BACKEND=ollama
OLLAMA_URL=http://your-private-ollama-service:11434
GENERATION_MODEL=your-provisioned-local-model
```

The server must be reachable from the API container and already have the model available. Requests use nonstreaming generation and the output-token cap. Input/output token counts are persisted; provider-dollar cost is zero, and local hardware/energy costs are outside this ledger. Restrict the model-server endpoint to your private network. This backend does not require hosted-provider data-egress consent.

### Enable hosted generation

Keep local retrieval and explicitly configure:

```dotenv
GENERATION_BACKEND=openai
ALLOW_REMOTE_GENERATION=true
OPENAI_API_KEY=your-provider-secret
GENERATION_MODEL=your-approved-model
INPUT_USD_PER_MILLION=your-verified-input-price
OUTPUT_USD_PER_MILLION=your-verified-output-price
```

The last two entries must be numeric prices, not the explanatory placeholders above. Startup rejects hosted generation without consent, credentials, and positive prices. Choose a model compatible with the chat-completions request parameters in the generator. Each call sends the question and authorized retrieved excerpts to the configured provider implementation. The application makes no automatic generation retries.

## API

All `/v1/*` routes require `X-API-Key`. Inputs are JSON; additional identity fields in request bodies are rejected. Admin means administrator **within the key's tenant**.

| Method | Route | Access | Purpose |
| --- | --- | --- | --- |
| `POST` | `/v1/documents` | Tenant admin | Ingest `{title, text, role}`; returns immutable document ID and chunk count. |
| `DELETE` | `/v1/documents/{id}` | Tenant admin | Idempotent deletion restricted to the authenticated tenant. |
| `POST` | `/v1/chat` | Any authenticated role | Query `{query}` against authorized documents. |
| `GET` | `/v1/usage` | Tenant admin | Current UTC month spend, reservations, and configured ceiling. |
| `POST` | `/v1/feedback` | Request owner | Submit `{request_id, rating}` where rating is 1–5. |
| `GET` | `/health/live` | Public | Process liveness; independent of storage availability. |
| `GET` | `/health/ready` | Public | Qdrant, Redis, and schema/database checks; returns `503` when unready. |
| `GET` | `/metrics` | Tenant admin | Service-wide Prometheus metrics; contains no tenant labels or document text. |

Example chat response shape:

```json
{
  "request_id": "9a213416-b5ee-4684-b116-d808688a0da1",
  "answer": "Employees receive twenty paid vacation days annually. [DOC 0]",
  "tenant": "acme",
  "citations": [{
    "label": "DOC 0",
    "document_id": "<content-version-id>",
    "chunk_id": "<uuid>",
    "title": "Leave policy",
    "score": 0.8
  }],
  "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0}
}
```

Scores and identifiers above are illustrative. `X-Request-ID` matches the chat usage record ID. Hosted model citation labels are instructions to the model; they are not a formal guarantee that every claim is supported. The citation list always identifies the actual retrieved chunks supplied to generation.

| Status | Meaning |
| --- | --- |
| `401` | Missing or invalid key. |
| `402` | Monthly tenant budget has insufficient unreserved allowance. |
| `403` | Authenticated principal lacks the required role. |
| `404` | Feedback request is absent or not owned by this principal. |
| `413` | Request bytes or configured document character limit exceeded. |
| `422` | Invalid input, empty query/document, unknown role, or extra body fields. |
| `429` | Distributed rate allowance exhausted; see `Retry-After`. |
| `503` | A required dependency failed; errors omit internal provider details. |

### PDF ingestion

PDF parsing is an operator-side utility, not a server endpoint accepting filesystem paths or remote URLs:

```bash
python scripts/ingest_pdf.py ./policy.pdf --title 'Leave policy' --role employee
```

It uses `RAG_API_KEY`. Scanned documents need a separate OCR step. Content updates create new immutable document IDs; delete the previous ID after verifying the replacement.

## Configuration

Settings come from environment variables or `.env`, validated before serving traffic. See [.env.example](.env.example).

| Variable | Default / requirement |
| --- | --- |
| `API_KEYS` | Required JSON array of `{key_sha256, tenant, subject, role}` credentials. |
| `ENVIRONMENT` | `development`; `production` requires PostgreSQL and semantic embeddings. |
| `DATABASE_URL` | SQLite for standalone development; Compose supplies PostgreSQL. |
| `REDIS_URL` | `redis://localhost:6379/0`; use authenticated/TLS connections outside isolated development. |
| `QDRANT_URL`, `QDRANT_API_KEY` | Local URL default; API key optional for a secured deployment. |
| `QDRANT_COLLECTION` | `enterprise_docs_v2`; the embedding fingerprint is appended internally. |
| `EMBEDDING_BACKEND` | `hash` for development; `sentence-transformer` for semantic retrieval. |
| `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` | `BAAI/bge-large-en-v1.5`, `1024`; dimensions checked at startup. |
| `EMBEDDING_REVISION`, `RERANK_REVISION` | Optional model commit revisions. |
| `RERANK_MODEL` | Unset; optional cross encoder. |
| `GENERATION_BACKEND` | `extractive`; `ollama` for private local inference, or `openai` with separate consent and prices. |
| `OLLAMA_URL` | `http://localhost:11434`; private model-server URL for Ollama generation. |
| `ALLOW_REMOTE_GENERATION` | `false`; required `true` for hosted generation. |
| `MONTHLY_BUDGET_USD` | `10` independently enforced for each tenant in each UTC month. |
| `MAX_OUTPUT_TOKENS` | `600`; hosted generation output cap. |
| `TOP_K`, `RERANK_TOP_K` | `8`, `4`. |
| `RATE_LIMIT_PER_MINUTE` | `60` per tenant/subject, shared across replicas and protected write routes. |
| `MAX_DOCUMENT_CHARACTERS` | `100000`; API also caps received request bytes at 4,100,000. |
| `DEPENDENCY_TIMEOUT_SECONDS` | `10` for Qdrant, Redis, and hosted generation. |
| `EMBEDDING_CACHE_TTL` | `300` seconds; tenant/model-scoped query vectors only. |

Use `python scripts/bootstrap_key.py --tenant acme --subject employee-1 --role employee` after installing dependencies to generate another credential. Merge credential objects into one `API_KEYS` array and roll the deployment. Keep actual keys in a secret manager. API key rotation and revocation take effect when each process reloads configuration.

## Security and tenant isolation

Access levels are ordered `public < employee < manager < admin`, within each tenant. Even a `public` document remains tenant-private. A tenant admin can access all document levels in that tenant, and cannot access another tenant's data.

Authentication happens before document operations. Query requests contain no authoritative tenant or role. Both tenant and role predicates are included in vector search, and deletion always includes the tenant predicate. Query-vector cache keys include tenant and model identity; answers and source documents are never cached in Redis.

The prompt filter is an additional heuristic that withholds some instruction-like excerpts. It is **not** an authorization boundary or comprehensive prompt-injection defense. Retrieved content remains untrusted even when no pattern matches. Source text and questions are omitted from application logs; usage records retain source identifiers and titles, which still require access-controlled storage.

Read the [security model](docs/security.md) before deploying with sensitive data.

## Cost governance

Before a hosted call, the ledger atomically reserves a conservative upper bound based on prompt byte length, message overhead, configured input prices, output-token cap, and output prices. Admission succeeds only if `spent + reserved + new reservation <= monthly budget`. The transaction commits before the network call, so parallel replicas see the reservation.

Successful calls settle against reported input/output tokens and release unused allowance. Ambiguous provider failures charge the reserved amount rather than permitting unaccounted retries. A process crash can leave a reservation pending; it remains unavailable until operator reconciliation. Usage and feedback survive API restarts. Extractive mode records requests with zero token spend.

Prices are deployment inputs, not a hardcoded example. Provider invoices remain authoritative. Reservations, failed-call accounting, UTC month boundaries, and recovery procedures are documented in [operations](docs/operations.md).

## Testing and evaluation

Tests exercise the full API path, tenant and role isolation, spoofed identity rejection, deterministic ingestion, deletion, feedback ownership, rate limits, concurrent budget reservations, provider failure accounting, request size limits, startup configuration, and logging privacy.

CI runs the suite with both embedded/fake services and real PostgreSQL, Redis, and Qdrant, then builds the container. Run real-service tests yourself with dedicated disposable services:

```bash
TEST_DATABASE_URL='postgresql+psycopg://rag:password@localhost:5432/rag_test' \
TEST_REDIS_URL='redis://localhost:6379/15' \
TEST_QDRANT_URL='http://localhost:6333' pytest -q
```

An opt-in smoke test validates real semantic embeddings and cross-encoder inference with small public models:

```bash
pip install -e '.[models]'
RUN_MODEL_TESTS=1 pytest tests/test_models.py -q
```

This downloads model weights unless already cached. It verifies the inference adapters and a simple ranking case; it does not establish production retrieval quality or benchmark the larger default models.

Use a labeled JSONL dataset to measure retrieval recall on your documents:

```json
{"query":"How many vacation days?","expected_document_ids":["<ingested-document-id>"]}
```

```bash
python scripts/evaluate.py dataset.jsonl --minimum-recall 0.8
```

The CLI reports mean recall, latency, and generation cost; it fails if recall misses your threshold. It makes real API requests that consume rate allowance and may incur hosted generation charges. Evaluate each access role and tenant separately, including negative cases. The optional RAGAS adapter requires a separately validated RAGAS installation and evaluation-provider configuration; it is not part of the default runtime.

## Deployment and operations

Compose is a persistent local stack. PostgreSQL, Redis, and Qdrant are not published on host ports; the API binds loopback. It does not provide production TLS, database HA, or a complete cluster network policy.

The [Kubernetes manifest](app/infra/k8s/deployment.yaml) supplies an API Deployment, Service, disruption budget, autoscaler, startup/readiness/liveness probes, resource limits, read-only filesystem, and a non-root security context. It expects managed dependency endpoints, secrets, a preprovisioned offline model cache, and an explicit storage-initialization release job. Replace the sample image with your registry digest.

Follow [deployment, backup, incident, and rollback procedures](docs/operations.md). Production activation requires verified tenant tests, real-service integration, a model-quality baseline, capacity/load measurements, and restore rehearsal for the target environment.

## Repository layout

```text
app/
  api/              Authenticated document, chat, usage, feedback, health routes
  core/             Settings, principals, authorization, byte limits, cache, ledger
  ingestion/        Local PDF loading, chunking, collection setup, upsert/delete
  retrieval/        Embeddings, filtered vector search, optional reranking
  generation/       Local excerpts and opt-in hosted generation
  orchestration/    Retrieval → reservation → generation → settlement
  observability/    Prometheus metrics, structured logs, timing
  evaluation/       Retrieval recall and optional RAGAS adapter
  infra/            Compose compatibility entry point and Kubernetes resources
scripts/            Secret bootstrap, storage initialization, PDF ingest, evaluation
tests/              API/security/governance regression and service integration tests
docs/               Architecture, operations, and security model
compose.yaml        Persistent local dependency stack
Dockerfile          Non-root runtime image
requirements.lock   Pinned runtime dependency resolution
```

## Compatibility and limitations

This release replaces the scaffold's `POST /chat?query=...&tenant_id=...&user_role=...` interface with authenticated `POST /v1/chat` JSON. Ingestion and retrieval now share one collection contract. Existing scaffold collections are not migrated automatically; reingest approved source documents into the new model-specific collection.

The platform implements service API-key identity, not end-user SSO/OIDC or an organization provisioning UI. Document authorization uses tenant-local role levels, not per-user ACLs. Ingestion is synchronous and bounded; background queues, OCR, connector sync, and transactional multi-document publication are future extensions. Multi-point Qdrant writes are retry-safe but do not promise all-or-nothing document visibility. Kubernetes manifests are deployment building blocks, not a claim that your cluster is already production-certified.

No license file is currently supplied. Obtain the owner's permission before relying on a redistribution license.
