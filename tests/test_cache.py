import sys
import types


class FakeRedisModuleClient:
    def __init__(self, *args, **kwargs):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value


def _install_redis_stub():
    redis_module = types.ModuleType("redis")
    redis_module.Redis = FakeRedisModuleClient
    sys.modules["redis"] = redis_module


def test_cache_round_trip_json(monkeypatch):
    _install_redis_stub()
    from app.core import cache

    fake = FakeRedisModuleClient()
    monkeypatch.setattr(cache, "redis_client", fake)

    cache.set_cached("ns", "k", {"a": 1})
    assert cache.get_cached("ns", "k") == {"a": 1}
