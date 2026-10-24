import hashlib
import uuid

from fastapi import HTTPException
from qdrant_client import models

from app.ingestion.chunker import chunk_text
from app.retrieval.retriever import tenant_filter


def initialize_collection(client, settings, create=True):
    name = settings.collection_name
    if create and not client.collection_exists(name):
        client.create_collection(
            name,
            vectors_config=models.VectorParams(
                size=settings.embedding_dimensions,
                distance=models.Distance.COSINE,
            ),
        )
    info = client.get_collection(name)
    vector = info.config.params.vectors
    if not isinstance(vector, models.VectorParams) or vector.size != settings.embedding_dimensions:
        raise ValueError("Collection vector configuration does not match embedding dimensions")
    if create:
        for field in ("tenant", "role", "document_id"):
            client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD, wait=True)


def index_document(client, embedder, settings, principal, document):
    # Content-addressed document IDs make retries deterministic. A changed document
    # is a new version; delete the old ID explicitly after publishing its replacement.
    digest = hashlib.sha256(document.text.encode()).hexdigest()
    document_id = hashlib.sha256(
        f"{document.title}\0{document.role}\0{digest}".encode()
    ).hexdigest()
    chunks = chunk_text(document.text)
    if not chunks:
        raise HTTPException(422, "Document must contain non-whitespace text")
    vectors = embedder.encode(chunks)
    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{principal.tenant}:{document_id}:{index}")),
            vector=vector,
            payload={
                "tenant": principal.tenant,
                "role": document.role,
                "document_id": document_id,
                "title": document.title,
                "text": chunk,
                "chunk_index": index,
                "content_sha256": digest,
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    client.upsert(settings.collection_name, points=points, wait=True)
    return {"document_id": document_id, "chunks": len(points), "tenant": principal.tenant}


def delete_document(client, settings, principal, document_id):
    client.delete(
        settings.collection_name,
        points_selector=models.FilterSelector(
            filter=tenant_filter(principal, document_id),
        ),
        wait=True,
    )
