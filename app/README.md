# Application Architecture

This directory contains the **core implementation** of the Enterprise RAG Platform.  
Each module is designed with clear responsibility boundaries to support scalability, testing, and enterprise deployment.

---

##  Module Overview

### `api/`
- External interfaces (REST / service endpoints)
- Acts as the entry point for user or system queries

### `core/`
- Shared abstractions and base components
- Configuration loading, common utilities, and contracts

### `Ingestion/`
- Document loading and preprocessing
- Chunking strategies
- Embedding generation pipeline

### `Retrieval/`
- Vector similarity search
- Retriever abstractions
- Store-agnostic retrieval logic

### `Generation/`
- Prompt construction
- Context injection
- LLM response orchestration

### `Evaluation/`
- Hooks for retrieval and generation evaluation
- Designed for offline and online metrics
- Supports experimentation and benchmarking

### `Observability/`
- Logging, tracing, and monitoring hooks
- Designed for production diagnostics

### `Orchestration/`
- Coordinates ingestion → retrieval → generation flow
- Central control layer for pipeline execution

### `Infra/`
- Infrastructure-related configuration
- Deployment or environment abstractions

### `Scripts/`
- Utility and helper scripts
- One-off or administrative tasks

---

##  Entry Point

- `main.py` serves as the application entry point
- Initializes configuration and orchestrates the RAG pipeline

---

##  Design Principles

- Separation of concerns
- Backend-agnostic components
- Enterprise-first thinking (privacy, control, extensibility)

