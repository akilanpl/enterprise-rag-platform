import time
from contextlib import contextmanager


@contextmanager
def track_latency(bucket: dict, key: str):
    start = time.monotonic()
    try:
        yield
    finally:
        bucket[key] = time.monotonic() - start
