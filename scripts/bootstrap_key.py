"""Print a new API key once, and its credential entry for API_KEYS."""

import argparse
import json
import secrets

from app.core.config import Credential, hash_key

parser = argparse.ArgumentParser()
parser.add_argument("--tenant", required=True)
parser.add_argument("--subject", required=True)
parser.add_argument(
    "--role", choices=["public", "employee", "manager", "admin"], default="employee"
)
arguments = parser.parse_args()
key = secrets.token_urlsafe(32)
credential = Credential(
    key_sha256=hash_key(key),
    tenant=arguments.tenant,
    subject=arguments.subject,
    role=arguments.role,
)
print("API key (store in your secret manager):", key)
print("API_KEYS='" + json.dumps([credential.model_dump()]) + "'")
