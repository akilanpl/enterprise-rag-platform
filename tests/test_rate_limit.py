import sys
import types

import pytest


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")
    fastapi.HTTPException = HTTPException
    sys.modules["fastapi"] = fastapi


def test_rate_limit_allows_under_threshold():
    _install_fastapi_stub()
    from app.core import rate_limit as rl

    rl.CALLS.clear()
    rl.rate_limit("u1", limit=2)
    rl.rate_limit("u1", limit=2)


def test_rate_limit_blocks_over_threshold():
    _install_fastapi_stub()
    from app.core import rate_limit as rl

    rl.CALLS.clear()
    rl.rate_limit("u1", limit=1)
    with pytest.raises(HTTPException) as exc:
        rl.rate_limit("u1", limit=1)
    assert exc.value.status_code == 429
