import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.auth import get_current_user
from app.main import app


@pytest.fixture(autouse=True)
def _override_auth_dependency():
    async def _fake_current_user():
        return {"sub": "test-user", "email": "test@example.com", "name": "Test User"}

    app.dependency_overrides[get_current_user] = _fake_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
