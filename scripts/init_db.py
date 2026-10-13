"""Explicit, idempotent v0.2 schema bootstrap. Run once as a release job."""

from app.core.config import Settings
from app.core.database import Ledger

ledger = Ledger(Settings().database_url)
ledger.create_schema()
ledger.engine.dispose()
