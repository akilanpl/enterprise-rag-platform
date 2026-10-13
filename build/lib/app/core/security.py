from app.core.config import ROLES


def accessible_roles(role: str) -> list[str]:
    return [name for name, level in ROLES.items() if level <= ROLES[role]]


def has_access(user_role: str, doc_role: str) -> bool:
    return doc_role in accessible_roles(user_role)
