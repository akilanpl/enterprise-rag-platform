"""
Application entry point for the Enterprise RAG Platform.

Initializes configuration, sets up ingestion, retrieval,
generation, and evaluation components, and orchestrates
the end-to-end RAG request lifecycle.
"""

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router

app = FastAPI(title="Enterprise RAG System")
app.include_router(chat_router)
app.include_router(health_router)
