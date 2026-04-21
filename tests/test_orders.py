import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_UPDATE = {"entity": {"uuid": "aaa-bbb-ccc"}, "requests": [{"type": "UPDATE", "state": "ACCEPTED"}]}
MOCK_DELETE = {"entity": {"uuid": "aaa-bbb-ccc"}, "requests": [{"type": "DELETE", "state": "ACCEPTED"}]}
MOCK_RETURN = {"entity": {"uuid": "ret-uuid"}, "requests": [{"type": "CREATE", "state": "ACCEPTED"}]}
MOCK_REFUSAL = {"entity": {"uuid": "aaa-bbb-ccc"}, "requests": [{"type": "CREATE", "state": "ACCEPTED"}]}
MOCK_INTAKES = {"entity": {"uuid": "aaa-bbb-ccc", "intakes": [{"intake_uuid": "i-001"}]}}


@pytest.mark.anyio
async def test_cdek_update_order():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.update_order.return_value = MOCK_UPDATE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_update_order", {"uuid": "aaa-bbb-ccc", "comment": "test"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["uuid"] == "aaa-bbb-ccc"


@pytest.mark.anyio
async def test_cdek_update_order_no_id():
    with patch("mcp_server_cdek.server.CdekAPI"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_update_order", {"comment": "test"})
            assert result.isError


@pytest.mark.anyio
async def test_cdek_delete_order():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.delete_order.return_value = MOCK_DELETE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delete_order", {"uuid": "aaa-bbb-ccc"})
            assert not result.isError
        instance.delete_order.assert_called_once_with("aaa-bbb-ccc")


@pytest.mark.anyio
async def test_cdek_client_return():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.client_return.return_value = MOCK_RETURN
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_client_return", {"uuid": "aaa-bbb-ccc", "tariff_code": 136})
            assert not result.isError
        instance.client_return.assert_called_once_with("aaa-bbb-ccc", 136)


@pytest.mark.anyio
async def test_cdek_order_refusal():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.order_refusal.return_value = MOCK_REFUSAL
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_order_refusal", {"uuid": "aaa-bbb-ccc"})
            assert not result.isError
        instance.order_refusal.assert_called_once_with("aaa-bbb-ccc")


@pytest.mark.anyio
async def test_cdek_order_intakes():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_order_intakes.return_value = MOCK_INTAKES
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_order_intakes", {"order_uuid": "aaa-bbb-ccc"})
            assert not result.isError
        instance.get_order_intakes.assert_called_once_with("aaa-bbb-ccc")
