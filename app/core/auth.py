import hmac
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from app.core.config import hash_key

key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@dataclass(frozen=True)
class Principal:
    tenant: str
    subject: str
    role: str


def authenticate(request: Request, key: str | None = Depends(key_header)) -> Principal:
    if key and len(key) <= 512:
        digest = hash_key(key)
        for credential in request.app.state.settings.api_keys:
            if hmac.compare_digest(digest, credential.key_sha256):
                return Principal(credential.tenant, credential.subject, credential.role)
    raise HTTPException(401, "Invalid API key")


def administrator(principal: Principal = Depends(authenticate)) -> Principal:
    if principal.role != "admin":
        raise HTTPException(403, "Tenant administrator required")
    return principal
