import hashlib
import json

import redis

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


def _key(*args):
    raw = "::".join(args)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(namespace, key):
    raw_value = redis_client.get(_key(namespace, key))
    if raw_value is None:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def set_cached(namespace, key, value, ttl=300):
    redis_client.setex(_key(namespace, key), ttl, json.dumps(value))
