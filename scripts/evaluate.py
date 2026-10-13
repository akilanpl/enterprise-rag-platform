"""Run a labeled retrieval regression dataset through the authenticated API."""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import httpx

from app.evaluation.ragas_eval import retrieval_recall

parser = argparse.ArgumentParser()
parser.add_argument("dataset", help='JSONL: {"query": "...", "expected_document_ids": ["..."]}')
parser.add_argument("--url", default="http://localhost:8000")
parser.add_argument("--minimum-recall", type=float, default=0.8)
arguments = parser.parse_args()
recalls, latencies = [], []
cost = 0
with httpx.Client(
    base_url=arguments.url, headers={"X-API-Key": os.environ["RAG_API_KEY"]}, timeout=60
) as client:
    for line in Path(arguments.dataset).read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        started = time.monotonic()
        response = client.post("/v1/chat", json={"query": case["query"]})
        response.raise_for_status()
        data = response.json()
        latencies.append(time.monotonic() - started)
        recalls.append(retrieval_recall(case["expected_document_ids"], data["citations"]))
        cost += data["usage"]["cost_usd"]
if not recalls:
    parser.error("Dataset has no cases")
report = {
    "cases": len(recalls),
    "mean_recall": statistics.mean(recalls),
    "mean_latency_seconds": statistics.mean(latencies),
    "cost_usd": cost,
}
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["mean_recall"] >= arguments.minimum_recall else 1)
