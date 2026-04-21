import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_WH = {"entity": {"uuid": "wh-001", "type": "ORDER_STATUS", "url": "https://example.com/hook"}}
MOCK_WH_LIST = [
    {"uuid": "wh-001", "type": "ORDER_STATUS", "url": "https://example.com/hook"},
    {"uuid": "wh-002", "type": "PRINT_FORM", "url": "https://example.com/print"},
]


@pytest.mark.anyio
async def test_cdek_create_webhook():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_webhook.return_value = MOCK_WH
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_webhook", {
                "type": "ORDER_STATUS", "url": "https://example.com/hook",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["type"] == "ORDER_STATUS"
        instance.create_webhook.assert_called_once_with("ORDER_STATUS", "https://example.com/hook")


@pytest.mark.anyio
async def test_cdek_list_webhooks():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.list_webhooks.return_value = MOCK_WH_LIST
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_list_webhooks", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data) == 2


@pytest.mark.anyio
async def test_cdek_get_webhook():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_webhook.return_value = MOCK_WH
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_get_webhook", {"uuid": "wh-001"})
            assert not result.isError
        instance.get_webhook.assert_called_once_with("wh-001")


@pytest.mark.anyio
async def test_cdek_delete_webhook():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.delete_webhook.return_value = {"entity": {"uuid": "wh-001"}}
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delete_webhook", {"uuid": "wh-001"})
            assert not result.isError
        instance.delete_webhook.assert_called_once_with("wh-001")
