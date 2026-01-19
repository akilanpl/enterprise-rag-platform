import time

CALLS = {}

def rate_limit(user_id: str, limit=60):
    now = time.time()
    window = CALLS.get(user_id, [])
    window = [t for t in window if now - t < 60]

    if len(window) >= limit:
        raise Exception("Rate limit exceeded")

    window.append(now)
    CALLS[user_id] = window
