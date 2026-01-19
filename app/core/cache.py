import redis
import json
import hashlib

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

def _key(*args):
    raw = "::".join(args)
    return hashlib.sha256(raw.encode()).hexdigest()

def get_cached(namespace, key):
    return redis_client.get(_key(namespace, key))

def set_cached(namespace, key, value, ttl=300):
    redis_client.setex(_key(namespace, key), ttl, json.dumps(value))
