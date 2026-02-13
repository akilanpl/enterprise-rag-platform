from pathlib import Path


def test_main_wires_health_router():
    source = Path("app/main.py").read_text()
    assert "health_router" in source
    assert "include_router(health_router)" in source
