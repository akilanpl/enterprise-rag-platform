# Deployment and operations

## Release preparation

1. Run unit/security tests, real-service integration, dependency audits, and container build checks. Validate optional semantic/reranker dependencies and models in the target image too.
2. Build with `--build-arg INSTALL_MODELS=true` for semantic inference. Publish to your registry and record the immutable image digest.
3. Provision private PostgreSQL, Redis, and Qdrant with backups, storage authentication, and the required TLS/network controls. Compose's single instances are local development services.
4. Provision approved model weights into a model volume or image. Pin revisions or immutable local paths. Verify dimensions and sufficient CPU/RAM. Kubernetes sets `HF_HUB_OFFLINE=1` and mounts a prepopulated `rag-models` claim; it does not download weights at runtime.
5. Supply `rag-config` for nonsecret settings and `rag-secrets` for `API_KEYS`, `DATABASE_URL`, Redis/Qdrant credentials/URLs as appropriate, and optional provider credentials. Never commit the real secret manifests.
6. Run `python scripts/init_storage.py` once as a controlled release job using the same image, settings, and secret references as the API. It bootstraps the v0.2 schema and model-specific Qdrant collection/indexes. Production replicas validate existing storage rather than race to create it.
7. Replace the manifest image with your registry digest, apply the API resources, and wait for readiness. Configure TLS ingress, request timeouts/limits, private monitoring, and platform-specific network policies before opening traffic.
8. Verify two distinct tenants and every access role with representative data; test provider/storage failure behavior and restore procedures. Start with a canary and review error rates, latency, and pending reservations.

`create_all` is an idempotent initial-schema bootstrap, not a schema migration system. Future schema changes need explicit reviewed migration scripts and rolling-version compatibility before deployment. Do not assume rerunning the bootstrap alters existing columns.

## Kubernetes prerequisites

The supplied manifest expects these preexisting names in its namespace:

| Resource | Contents |
| --- | --- |
| `rag-config` ConfigMap | Model IDs/revisions/dimensions, collection prefix, generation backend, budgets, timeouts, rate limits, and other nonsecret settings. |
| `rag-secrets` Secret | Credential JSON, private PostgreSQL/Redis/Qdrant connection configuration, optional provider key. |
| `rag-models` PVC | Preseeded model cache readable by UID/GID 10001; support the access mode required by replicas across nodes. |
| Managed dependencies | Reachable PostgreSQL schema and Qdrant collection initialized before API rollout; shared Redis. |
| Ingress/metrics setup | TLS routing and authenticated/private Prometheus scraping. |

Production settings require PostgreSQL and semantic embeddings. The sample API uses one Uvicorn worker per container; scale pods to isolate model memory and keep per-process Prometheus counters understandable. The HPA assumes cluster metrics-server is available. CPU-based scaling is a starting configuration, not a measured capacity recommendation.

The default generation backend is local extractive mode. Hosted mode must be opted into and allowed by your egress policy. Local deployments can deny internet egress after models and dependencies are provisioned.

## Health and telemetry

`/health/live` reports process uptime and must stay independent of storage. `/health/ready` checks Redis, PostgreSQL/schema access, and the configured Qdrant collection. A failed readiness check returns `503`; Kubernetes removes the pod from ready service endpoints. Startup probes allow local models time to load. These checks validate storage connectivity, not semantic quality or provider quota.

Database connections use driver defaults unless tuned by your connection URL/platform. Set appropriate connection and statement timeouts in PostgreSQL configuration or connection parameters; account for pool pre-ping and outage behavior when configuring probe timeouts.

Metrics:

- `rag_requests_total{route,method,status}` and `rag_latency_seconds{route}`.
- `rag_stage_latency_seconds{stage}` for completed retrieval/generation stages.
- `rag_generation_cost_usd_total` for successful settled hosted cost in each process.

Scrape `/metrics` with an admin API key on a private path. Metrics intentionally have no tenant, subject, request-ID, or raw-query labels. Cost counters reset when a process restarts; PostgreSQL is the durable accounting authority. Failed/pending reservations are visible in the ledger rather than this success-only counter.

Suggested alert conditions should be calibrated to your SLOs: sustained `5xx`, all replicas unready, high p95 latency, rising `429`, budget `402` spikes, old pending reservations, PostgreSQL/Qdrant backup failures, and Redis memory exhaustion. No universal latency or throughput target has been measured for this repository.

## Budget and provider reconciliation

Each UTC month has one budget row per tenant. The configured monthly ceiling is shared configuration but enforced independently for each tenant. Separate input/output prices must match the selected provider model and rate schedule. Zero-price hosted generation is rejected to avoid presenting free accounting as enforced governance.

Usage states:

| State | Accounting |
| --- | --- |
| `reserved` | Allowance is held before generation. A long-lived record may indicate a crash or failed settlement. |
| `completed` | Reported provider token usage is charged; unused reservation released. |
| `failed_reserved` | Provider outcome was ambiguous or failed; full reservation charged conservatively. |

Reservations include a conservative input-byte bound and the configured output-token cap. This can reject a request whose eventual bill would be smaller, especially near a budget limit. That is deliberate admission conservatism. Model pricing changes, provider-side billing rules, and incompatible model responses require reconciliation with provider records.

To investigate outstanding reservations, query by age using a read-only operator identity:

```sql
SELECT id, tenant, subject, created_at, model, reservation, status
FROM usage
WHERE status IN ('reserved', 'failed_reserved')
ORDER BY created_at;
```

Never release a reservation just because a process restarted. First verify the request cannot still be running and check provider billing/outcome. Preserve an operator record of any adjustment. A reviewed adjustment must update usage state and the matching tenant/month budget in one transaction with row locks, then verify that reserved totals agree with still-pending requests. There is deliberately no automatic TTL refund or public refund endpoint.

## Common incidents

| Symptom | Investigation / response |
| --- | --- |
| API fails startup | Check hashed credential JSON, model assets/dimensions, production backend requirements, storage initialization, and reachable endpoints. |
| Queries return no evidence | Check credential tenant/role, ingest response, model fingerprint, old/new collection, score threshold, and representative retrieval evaluation. |
| `402` unexpectedly | Inspect current UTC month spend and outstanding reservations; verify configured prices and limits match across replicas. |
| `429` unexpectedly | Check shared tenant/subject mapping and the 60-second first-request window. Ingestion, deletion, chat, and feedback consume that subject's allowance. |
| `503` after provider call | Correlate `X-Request-ID` with usage status; inspect provider status privately. Avoid automatic client retries that may duplicate billable calls. |
| Storage outage | Readiness removes pods; restore storage connectivity. API restart is not a substitute for recovering dependency service. |
| Redis memory errors | Cache/rate admission fails closed; expand capacity or reduce TTL/corpus query load. Preserve limits rather than bypassing Redis. |
| Changed ACL still appears accessible | A restrictive replacement is a new version; explicitly delete the older, less restrictive content version. |

Application exception responses intentionally omit secret/provider internals. Use controlled infrastructure diagnostics to investigate dependencies without turning on raw request/source logging.

## Backup and restore

Back up PostgreSQL budgets, usage, and feedback with a retention and point-in-time recovery policy. Snapshot Qdrant collections and preserve source/version provenance. Protect both with equivalent tenant data controls. Retain approved source files so collections can be reindexed if model assets change.

Redis stores short-lived query vectors and rate counters. Its AOF volume helps preserve counters across service restarts, but it is not the accounting authority. Model artifacts and their revisions also need a reproducible provisioning record.

Restore rehearsal:

1. Stop writes and generation admission in an isolated recovery environment.
2. Restore PostgreSQL and Qdrant from compatible recovery points; document any differences.
3. Restore matching model assets/configuration and secret references.
4. Validate schema, collection fingerprint/dimensions, and tenant/role isolation.
5. Reconcile pending provider reservations against provider records before permitting spend.
6. Reingest approved missing document versions and remove stale versions if necessary.
7. Run representative retrieval/answer evaluation, then restore traffic gradually.

Define and rehearse RPO/RTO for your deployment; this code does not establish those values.

## Rollback and capacity

Keep the previous immutable image and configuration. Roll back application images only when schema/model/collection compatibility has been verified. The original unauthenticated scaffold is not a safe rollback target. For a model change, preserve the old collection and configuration, reindex and evaluate the new collection, then switch traffic. Reverting the model settings selects the previous fingerprinted collection.

Measure model startup duration, resident memory, batch ingestion latency, query concurrency, Qdrant latency, Redis capacity, database lock contention, and hosted-provider quotas on the intended hardware. Ingestion is synchronous; choose request limits and timeouts accordingly. Larger corpora or sustained bulk ingestion should move to a tenant-authenticated background ingestion service with bounded queues and explicit publication states.
