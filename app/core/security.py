def has_access(user_role: str, doc_role: str) -> bool:
    role_hierarchy = {
        "public": 0,
        "employee": 1,
        "manager": 2,
        "admin": 3
    }
    return role_hierarchy[user_role] >= role_hierarchy[doc_role]
