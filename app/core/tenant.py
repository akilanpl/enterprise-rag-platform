from contextvars import ContextVar

_current_tenant: ContextVar[str] = ContextVar(
    "current_tenant",
    default="default"
)

def set_tenant(tenant_id: str):
    _current_tenant.set(tenant_id)

def get_tenant() -> str:
    return _current_tenant.get()
