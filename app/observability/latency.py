import time
from contextlib import contextmanager

@contextmanager
def track_latency(bucket: dict, key: str):
    start = time.time()
    yield
    bucket[key] = time.time() - start
