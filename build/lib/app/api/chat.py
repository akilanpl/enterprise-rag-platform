from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import Principal, administrator, authenticate
from app.core.config import IDENTIFIER
from app.core.rate_limit import rate_limit
from app.ingestion.indexer import delete_document, index_document
from app.orchestration.rag_pipeline import run_rag

router = APIRouter()


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=4000)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=1000000)
    role: Literal["public", "employee", "manager", "admin"] = "employee"


class FeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    rating: int = Field(ge=1, le=5)


@router.post("/chat")
def chat(payload: Query, request: Request, principal: Principal = Depends(authenticate)):
    if not payload.query.strip():
        raise HTTPException(422, "Query must contain non-whitespace text")
    return run_rag(request.app.state, principal, payload.query, request.state.trace_id)


@router.post("/documents", status_code=201)
def ingest(payload: DocumentInput, request: Request, principal: Principal = Depends(administrator)):
    resources = request.app.state
    rate_limit(resources.redis, principal, resources.settings.rate_limit_per_minute)
    if len(payload.text) > resources.settings.max_document_characters:
        raise HTTPException(413, "Document exceeds configured character limit")
    return index_document(
        resources.qdrant, resources.embedder, resources.settings, principal, payload
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete(document_id: str, request: Request, principal: Principal = Depends(administrator)):
    if not IDENTIFIER.fullmatch(document_id):
        raise HTTPException(422, "Invalid document ID")
    resources = request.app.state
    rate_limit(resources.redis, principal, resources.settings.rate_limit_per_minute)
    delete_document(resources.qdrant, resources.settings, principal, document_id)


@router.get("/usage")
def usage(request: Request, principal: Principal = Depends(administrator)):
    result = request.app.state.ledger.usage(principal)
    result["monthly_budget_usd"] = request.app.state.settings.monthly_budget_usd
    return result


@router.post("/feedback", status_code=201)
def feedback(
    payload: FeedbackInput, request: Request, principal: Principal = Depends(authenticate)
):
    resources = request.app.state
    rate_limit(resources.redis, principal, resources.settings.rate_limit_per_minute)
    resources.ledger.feedback(principal, str(payload.request_id), payload.rating)
    return {"status": "recorded"}
