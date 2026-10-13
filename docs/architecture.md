# Architecture and contracts

## Trust boundaries

The API is the only supported document access path. PostgreSQL, Qdrant, and Redis must be accessible only to trusted service identities. Qdrant administrators and database administrators can read data across tenants: application filtering is logical isolation, not physical isolation from storage operators.

`Principal(tenant, subject, role)` comes from a matched API key hash. Callers never supply authoritative identity in a query body. All public data-access routes declare an authentication dependency. Internal storage functions require a principal explicitly; no default tenant is available.

## Query sequence

1. Validate the bounded JSON body and authenticate `X-API-Key`.
2. Increment a Redis subject/tenant rate counter using one atomic Lua operation. The first request starts a 60-second expiring window. Excess requests receive `429` and a retry interval.
3. Read or create the tenant/model/query-specific embedding cache entry. Only vectors are cached; no generated answer or retrieved source is cached.
4. Search the model-specific Qdrant collection with both tenant and permitted-role filters. Convert scored points into the internal `Document` contract.
5. Optionally score query/document pairs with a cross encoder, preserving stable behavior when scores tie. Otherwise retain cosine ordering. Return at most `RERANK_TOP_K` candidates.
6. Build a prompt that identifies source excerpts as untrusted. A pattern filter may withhold suspicious source text, but never grants or denies document authorization.
7. Calculate a conservative generation reservation and atomically update the tenant/month budget row. The same transaction inserts a `reserved` usage record, correlated with `X-Request-ID`.
8. Generate local excerpts or make one explicit hosted-provider call. If no authorized candidates exist, return insufficient information without calling a provider.
9. Settle usage and citation metadata in PostgreSQL before returning success. The API response maps source labels to document/chunk IDs and titles.

If a provider call fails ambiguously, the reservation becomes a `failed_reserved` charge. If the process dies or settlement storage fails after generation, the reservation remains pending. Neither case silently creates free retry allowance. See the reconciliation runbook.

## Ingestion and versioning

The ingestion API accepts text, title, and a document role from a tenant admin. PDFs are extracted by an operator utility and submitted as text; the server does not fetch arbitrary URLs or open caller-provided paths.

Whitespace is normalized and text is split into 600-character chunks with 120-character overlap. These are character counts, not token counts. The input text hash, title, and role determine a content-version ID. A UUID derived from tenant, version ID, and chunk index identifies each point. Retrying the same document upserts the same points, including across replicas.

Qdrant point payload:

| Field | Purpose |
| --- | --- |
| `tenant` | Mandatory tenant isolation predicate. |
| `role` | Minimum tenant-local role required to retrieve the chunk. |
| `document_id` | Immutable content/version identifier. |
| `title` | Human-readable citation title. |
| `text` | Chunk text supplied only after authorization filtering. |
| `chunk_index` | Stable ordering within the content version. |
| `content_sha256` | Original text digest for version provenance. |

Publishing new content, a changed title, or a changed role produces a new version ID. Verify the new version, then delete the old ID. Keeping both versions intentionally exposes both to authorized searches. An ACL tightening therefore requires deleting the old, less restrictive version; uploading a new restrictive version alone does not revoke the old one.

Multi-point writes are deterministic and retry-safe, but are not a transaction spanning the entire document. A failed upsert may leave partially visible chunks until a retry completes. Large corpora and atomic release publication need a staging/version activation layer or background ingestion service; neither is claimed by the current synchronous API.

## Model identity and retrieval

The physical collection name is `QDRANT_COLLECTION` plus a fingerprint of embedding backend, model identifier, revision, and vector dimensions. The query-vector cache uses the same identity inputs. This prevents switching the development hash backend to a semantic model and searching incompatible old vectors of the same dimensionality.

Semantic model dimensions are verified at startup. Existing Qdrant collection dimensions are checked as well. Changing the configuration starts a distinct collection and requires ingestion for that model. Pin model revisions or use immutable local model assets. Updating weights in place at an unchanged local path is not detectable from the path string; provision a new path/revision and collection identity when changing weights.

A low cosine threshold removes clearly unrelated/zero-similarity candidates; it is not a calibrated confidence measure. Reranker scores are used for ordering, while citation scores report the original vector score. No probability or universal relevance guarantee should be inferred from either.

## Durable accounting

PostgreSQL tables are defined by the v0.2 SQLAlchemy schema:

- `budgets`: composite tenant/month key, spent amount, reserved amount.
- `usage`: request ID, tenant, subject, UTC month, timestamps, model, state, reservation, settled cost, input/output token counts, and citation metadata.
- `feedback`: unique feedback record, request ID, tenant, subject, rating, and timestamp.

Money is stored with fixed decimal precision. Budget admission uses a conditional database update, not a read-then-write allowance calculation. PostgreSQL serializes conflicting updates; settlement locks the usage row and ignores already-settled records. Transactions end before inference begins. SQLite is a development fallback and is rejected in production mode.

The budget ceiling is deployment-wide configuration applied independently to every tenant. It does not support negotiated per-tenant plans or prepaid top-ups. The monthly key uses UTC and a request is charged to the month in which its reservation began.

## Failure behavior

| Failure | Behavior |
| --- | --- |
| Missing/invalid credential | `401`, no retrieval. |
| Unauthorized document write | `403`, no vector mutation. |
| Redis unavailable | Protected rate-admitted operations fail closed with `503`. |
| Qdrant unavailable | Query or ingestion fails with `503`; no generation admission occurs if retrieval failed. |
| PostgreSQL unavailable | Budget admission/settlement fails with `503`; outstanding reservations remain conserved. |
| Provider timeout/rejection/invalid response | Safe `503`, conservative reserved charge if settlement succeeds. |
| No authorized evidence | Insufficient-information answer, zero provider spend. |
| Budget exhausted | `402` before the provider call. |
| Crash after reservation | Pending reservation persists for reconciliation. |
| Readiness dependency failure | `503`; liveness remains independent so a database outage does not create a restart loop. |

## Extension points

Implement other generators behind `prepare`, `reservation`, and `generate`; preserve conservative charging and explicit data-egress controls. Introduce OIDC by replacing the principal-resolution dependency while retaining the same tenant/role filtering contracts. New ingestion connectors must derive tenant identity from trusted provisioning, never document contents. Per-user ACLs require new search predicates, not post-generation redaction.
