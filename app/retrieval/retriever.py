import hashlib
import math
import re
from dataclasses import dataclass

from qdrant_client import models

from app.core.security import accessible_roles


@dataclass(frozen=True)
class Document:
    page_content: str
    metadata: dict
    score: float


class Embedder:
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        if settings.embedding_backend == "sentence-transformer":
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                settings.embedding_model,
                revision=settings.embedding_revision,
                trust_remote_code=False,
            )
            if self.model.get_sentence_embedding_dimension() != settings.embedding_dimensions:
                raise ValueError("Embedding dimensions do not match model")

    def encode(self, texts):
        if self.model:
            return self.model.encode(texts, normalize_embeddings=True).tolist()
        # Deterministic lexical smoke-test backend. Production rejects this backend.
        vectors = []
        for text in texts:
            vector = [0.0] * self.settings.embedding_dimensions
            for token in re.findall(r"\w+", text.lower()):
                digest = hashlib.sha256(token.encode()).digest()
                index = int.from_bytes(digest[:4], "big") % len(vector)
                vector[index] += 1 if digest[4] & 1 else -1
            norm = math.sqrt(sum(value * value for value in vector)) or 1
            vectors.append([value / norm for value in vector])
        return vectors


def tenant_filter(principal, document_id=None):
    conditions = [
        models.FieldCondition(key="tenant", match=models.MatchValue(value=principal.tenant)),
        models.FieldCondition(
            key="role", match=models.MatchAny(any=accessible_roles(principal.role))
        ),
    ]
    if document_id is not None:
        conditions.append(
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))
        )
    return models.Filter(must=conditions)


def retrieve(client, settings, principal, embedding):
    hits = client.query_points(
        collection_name=settings.collection_name,
        query=embedding,
        query_filter=tenant_filter(principal),
        limit=settings.top_k,
        with_payload=True,
        score_threshold=0.05,
    ).points
    return [
        Document(
            page_content=hit.payload["text"],
            metadata={
                "document_id": hit.payload["document_id"],
                "chunk_id": str(hit.id),
                "title": hit.payload["title"],
            },
            score=hit.score,
        )
        for hit in hits
    ]
