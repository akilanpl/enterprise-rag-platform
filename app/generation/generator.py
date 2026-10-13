import json
from dataclasses import dataclass

import httpx

from app.core.prompt_firewall import sanitize_context
from app.core.prompts import SYSTEM_PROMPT


@dataclass(frozen=True)
class Generation:
    answer: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0


class Generator:
    def __init__(self, settings):
        self.settings = settings
        self.client = httpx.Client(timeout=settings.dependency_timeout_seconds)

    def prepare(self, query, docs):
        sources = [
            {"label": f"DOC {i}", "text": sanitize_context(doc.page_content)}
            for i, doc in enumerate(docs)
        ]
        return json.dumps({"question": query, "sources": sources}, ensure_ascii=True)

    def reservation(self, prompt):
        if self.settings.generation_backend != "openai":
            return 0
        # Byte length conservatively bounds token count, plus message framing overhead.
        input_bound = len((prompt + SYSTEM_PROMPT).encode()) + 1024
        return (
            input_bound * self.settings.input_usd_per_million
            + self.settings.max_output_tokens * self.settings.output_usd_per_million
        ) / 1_000_000

    def generate(self, query, docs, prompt):
        if not docs:
            return Generation("Insufficient information in the authorized documents.")
        if self.settings.generation_backend == "extractive":
            excerpts = [
                f"{sanitize_context(doc.page_content)} [DOC {i}]" for i, doc in enumerate(docs)
            ]
            return Generation("\n\n".join(excerpts))
        response = self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + self.settings.openai_api_key.get_secret_value()},
            json={
                "model": self.settings.generation_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": self.settings.max_output_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        usage = data["usage"]
        input_tokens, output_tokens = usage["prompt_tokens"], usage["completion_tokens"]
        cost = (
            input_tokens * self.settings.input_usd_per_million
            + output_tokens * self.settings.output_usd_per_million
        ) / 1_000_000
        return Generation(
            data["choices"][0]["message"]["content"], input_tokens, output_tokens, cost
        )

    def close(self):
        self.client.close()
