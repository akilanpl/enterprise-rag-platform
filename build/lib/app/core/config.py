import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROLES = {"public": 0, "employee": 1, "manager": 2, "admin": 3}
IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class Credential(BaseModel):
    key_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tenant: str = Field(pattern=IDENTIFIER.pattern)
    subject: str = Field(min_length=1, max_length=128)
    role: Literal["public", "employee", "manager", "admin"] = "employee"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Literal["development", "production"] = "development"
    api_keys: list[Credential] = Field(default_factory=list)
    database_url: str = "sqlite:///./data/rag.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    qdrant_collection: str = "enterprise_docs_v2"
    embedding_backend: Literal["hash", "sentence-transformer"] = "hash"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_revision: str | None = None
    rerank_revision: str | None = None
    embedding_dimensions: int = Field(default=1024, ge=8, le=4096)
    rerank_model: str | None = None
    generation_backend: Literal["extractive", "openai"] = "extractive"
    allow_remote_generation: bool = False
    openai_api_key: SecretStr | None = None
    generation_model: str = "gpt-4o"
    input_usd_per_million: float = Field(default=0, ge=0, allow_inf_nan=False)
    output_usd_per_million: float = Field(default=0, ge=0, allow_inf_nan=False)
    monthly_budget_usd: float = Field(default=10, gt=0, allow_inf_nan=False)
    max_output_tokens: int = Field(default=600, ge=1, le=4096)
    top_k: int = Field(default=8, ge=1, le=50)
    rerank_top_k: int = Field(default=4, ge=1, le=20)
    rate_limit_per_minute: int = Field(default=60, ge=1)
    dependency_timeout_seconds: float = Field(default=10, gt=0, le=60)
    max_document_characters: int = Field(default=100000, ge=600, le=1000000)
    embedding_cache_ttl: int = Field(default=300, ge=1, le=86400)

    @property
    def collection_name(self) -> str:
        identity = json.dumps(
            [
                self.embedding_backend,
                self.embedding_model,
                self.embedding_revision,
                self.embedding_dimensions,
            ]
        )
        fingerprint = hashlib.sha256(identity.encode()).hexdigest()[:12]
        return f"{self.qdrant_collection}_{fingerprint}"

    @model_validator(mode="after")
    def validate_deployment(self):
        if not self.api_keys:
            raise ValueError("API_KEYS must contain at least one hashed credential")
        if len({c.key_sha256 for c in self.api_keys}) != len(self.api_keys):
            raise ValueError("API key hashes must be unique")
        if self.generation_backend == "openai":
            if not self.allow_remote_generation or not self.openai_api_key:
                raise ValueError("Remote generation requires opt-in and OPENAI_API_KEY")
            if not self.input_usd_per_million or not self.output_usd_per_million:
                raise ValueError(
                    "Configure current input and output prices before remote generation"
                )
        if self.environment == "production":
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL")
            if self.embedding_backend == "hash":
                raise ValueError("Production requires semantic embeddings")
        return self


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()
