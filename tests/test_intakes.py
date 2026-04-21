import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_INTAKE = {"entity": {"uuid": "int-001"}, "requests": [{"type": "CREATE", "state": "SUCCESSFUL"}]}
MOCK_INTAKE_INFO = {"entity": {"uuid": "int-001", "intake_date": "2026-04-25", "intake_time_from": "09:00"}}
MOCK_AVAILABLE = {"date_next": "2026-04-22", "days": [{"date": "2026-04-22", "is_available": True}]}


@pytest.mark.anyio
async def test_cdek_create_intake():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_intake.return_value = MOCK_INTAKE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_intake", {
                "cdek_number": "1400567890", "intake_date": "2026-04-25",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["uuid"] == "int-001"


@pytest.mark.anyio
async def test_cdek_create_intake_missing_date():
    with patch("mcp_server_cdek.server.CdekAPI"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_intake", {"cdek_number": "1400567890"})
            assert result.isError


@pytest.mark.anyio
async def test_cdek_update_intake():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.update_intake.return_value = MOCK_INTAKE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_update_intake", {"uuid": "int-001", "status_code": "CANCELLED"})
            assert not result.isError
        instance.update_intake.assert_called_once_with("int-001", "CANCELLED")


@pytest.mark.anyio
async def test_cdek_get_intake():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_intake.return_value = MOCK_INTAKE_INFO
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_get_intake", {"uuid": "int-001"})
            assert not result.isError
        instance.get_intake.assert_called_once_with("int-001")


@pytest.mark.anyio
async def test_cdek_delete_intake():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.delete_intake.return_value = {"entity": {"uuid": "int-001"}}
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delete_intake", {"uuid": "int-001"})
            assert not result.isError
        instance.delete_intake.assert_called_once_with("int-001")


@pytest.mark.anyio
async def test_cdek_intake_available_days():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.return_value = 44
        instance.get_intake_available_days.return_value = MOCK_AVAILABLE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_intake_available_days", {"city": "Москва"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["date_next"] == "2026-04-22"
