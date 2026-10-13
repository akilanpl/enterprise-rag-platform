import argparse
import os

import httpx

from app.ingestion.loader import load_pdf

parser = argparse.ArgumentParser()
parser.add_argument("path")
parser.add_argument("--title", required=True)
parser.add_argument(
    "--role", choices=["public", "employee", "manager", "admin"], default="employee"
)
parser.add_argument("--url", default="http://localhost:8000")
arguments = parser.parse_args()
response = httpx.post(
    arguments.url + "/v1/documents",
    headers={"X-API-Key": os.environ["RAG_API_KEY"]},
    json={"title": arguments.title, "text": load_pdf(arguments.path), "role": arguments.role},
    timeout=60,
)
response.raise_for_status()
print(response.json())
