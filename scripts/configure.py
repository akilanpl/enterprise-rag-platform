"""Generate local secrets with only the Python standard library. Never overwrites .env."""

import argparse
import hashlib
import json
import re
import secrets
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--tenant", default="acme")
parser.add_argument("--subject", default="admin")
arguments = parser.parse_args()
if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", arguments.tenant):
    parser.error("Invalid tenant identifier")
if not 1 <= len(arguments.subject) <= 128:
    parser.error("Subject must contain 1–128 characters")
key = secrets.token_urlsafe(32)
password = secrets.token_urlsafe(32)
credential = {
    "key_sha256": hashlib.sha256(key.encode()).hexdigest(),
    "tenant": arguments.tenant,
    "subject": arguments.subject,
    "role": "admin",
}
source = Path(".env.example").read_text()
source = source.replace("API_KEYS=[]", "API_KEYS='" + json.dumps([credential]) + "'")
source = source.replace("replace-with-a-random-secret", password)
with Path(".env").open("x") as target:
    target.write(source)
Path(".env").chmod(0o600)
print("Created .env. Store this API key securely; it is shown only once:")
print(key)
