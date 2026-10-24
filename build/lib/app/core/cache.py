import hashlib
import json


def query_embedding(client, embedder, settings, tenant, query):
    identity = json.dumps(
        [
            tenant,
            settings.embedding_backend,
            settings.embedding_model,
            settings.embedding_revision,
            settings.embedding_dimensions,
            query,
        ],
        separators=(",", ":"),
    )
    key = "embedding:" + hashlib.sha256(identity.encode()).hexdigest()
    cached = client.get(key)
    if cached:
        return json.loads(cached)
    vector = embedder.encode([query])[0]
    client.setex(key, settings.embedding_cache_ttl, json.dumps(vector))
    return vector
