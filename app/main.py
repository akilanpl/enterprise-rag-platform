"""
Application entry point for the Enterprise RAG Platform.

Initializes configuration, sets up ingestion, retrieval,
generation, and evaluation components, and orchestrates
the end-to-end RAG request lifecycle.
"""


from fastapi import FastAPI
from app.api.chat import router

app = FastAPI(title="Enterprise RAG System")
app.include_router(router)
