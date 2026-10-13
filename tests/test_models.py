"""Explicit opt-in: downloads small public models and validates real inference adapters."""

import os

import pytest

from app.core.config import Settings, hash_key
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Document, Embedder


@pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "1", reason="Opt-in model downloads/inference")
def test_semantic_embeddings_and_cross_encoder():
    settings = Settings(
        _env_file=None,
        api_keys=[
            {"key_sha256": hash_key("test"), "tenant": "test", "subject": "test", "role": "admin"}
        ],
        embedding_backend="sentence-transformer",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_dimensions=384,
    )
    embedder = Embedder(settings)
    vectors = embedder.encode(["vacation policy", "twenty days paid vacation"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert sum(value * value for value in vectors[0]) == pytest.approx(1, abs=0.001)
    reranker = Reranker("cross-encoder/ms-marco-TinyBERT-L-2-v2")
    ranked = reranker.rerank(
        "How many vacation days?",
        [
            Document("The weather is rainy.", {"document_id": "weather"}, 0.9),
            Document(
                "Employees receive twenty paid vacation days annually.",
                {"document_id": "policy"},
                0.1,
            ),
        ],
        1,
    )
    assert ranked[0].metadata["document_id"] == "policy"
