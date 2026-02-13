from app.core.security import has_access


def test_has_access_hierarchy():
    assert has_access("admin", "employee")
    assert has_access("employee", "public")
    assert not has_access("employee", "manager")


def test_has_access_unknown_role_denied():
    assert not has_access("unknown", "public")
