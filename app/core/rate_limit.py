import hashlib

from fastapi import HTTPException

SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


def rate_limit(client, principal, limit):
    identity = hashlib.sha256(f"{principal.tenant}:{principal.subject}".encode()).hexdigest()
    count, ttl = client.eval(SCRIPT, 1, f"rate:{identity}", 60)
    if count > limit:
        raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(max(ttl, 1))})
