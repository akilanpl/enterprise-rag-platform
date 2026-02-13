def has_access(user_role: str, doc_role: str) -> bool:
    role_hierarchy = {
        "public": 0,
        "employee": 1,
        "manager": 2,
        "admin": 3,
    }
    user_level = role_hierarchy.get(user_role, -1)
    doc_level = role_hierarchy.get(doc_role, 0)
    return user_level >= doc_level
