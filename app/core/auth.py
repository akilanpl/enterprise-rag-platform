import os

from fastapi import Header, HTTPException

ALLOWED_API_KEYS = set(filter(None, os.getenv("ENTERPRISE_API_KEYS", "ENTERPRISE_KEY_1").split(",")))


def authenticate(api_key: str = Header(...)):
    if api_key not in ALLOWED_API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return api_key
