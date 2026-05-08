import os

import pytest

os.environ.setdefault("CDEK_CLIENT", "test-fake-client")
os.environ.setdefault("CDEK_SECRET", "test-fake-secret")
os.environ.setdefault("CDEK_SENDER_COMPANY", "Test Company")
os.environ.setdefault("CDEK_SENDER_NAME", "Test Name")
os.environ.setdefault("CDEK_SENDER_FULL_NAME", "Test Full Name")
os.environ.setdefault("CDEK_SENDER_EMAIL", "test@example.com")
os.environ.setdefault("CDEK_SENDER_PHONE", "+70001234567")


@pytest.fixture(autouse=True)
def _reset_api_singleton():
    """Reset cached API instance between tests."""
    import mcp_server_cdek.server as srv
    srv._api_instance = None
    yield
    srv._api_instance = None
