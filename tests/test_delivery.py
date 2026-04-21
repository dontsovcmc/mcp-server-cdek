import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_DELIVERY = {"entity": {"uuid": "del-001"}, "requests": [{"type": "CREATE", "state": "SUCCESSFUL"}]}
MOCK_DELIVERY_INFO = {"entity": {"uuid": "del-001", "date": "2026-04-26"}}
MOCK_INTERVALS = {"intervals": [{"date": "2026-04-26", "time_from": "10:00", "time_to": "14:00"}]}
MOCK_ESTIMATED = {"intervals": [{"date": "2026-04-28"}], "calendar_min": 3, "calendar_max": 5}


@pytest.mark.anyio
async def test_cdek_create_delivery():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_delivery.return_value = MOCK_DELIVERY
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_delivery", {
                "cdek_number": "1400567890", "date": "2026-04-26",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["uuid"] == "del-001"


@pytest.mark.anyio
async def test_cdek_create_delivery_missing_date():
    with patch("mcp_server_cdek.server.CdekAPI"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_delivery", {"cdek_number": "1400567890"})
            assert result.isError


@pytest.mark.anyio
async def test_cdek_get_delivery():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_delivery.return_value = MOCK_DELIVERY_INFO
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_get_delivery", {"uuid": "del-001"})
            assert not result.isError
        instance.get_delivery.assert_called_once_with("del-001")


@pytest.mark.anyio
async def test_cdek_delivery_intervals():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_delivery_intervals.return_value = MOCK_INTERVALS
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delivery_intervals", {"cdek_number": "1400567890"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data["intervals"]) == 1


@pytest.mark.anyio
async def test_cdek_delivery_intervals_missing():
    with patch("mcp_server_cdek.server.CdekAPI"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delivery_intervals", {})
            assert result.isError


@pytest.mark.anyio
async def test_cdek_estimated_intervals():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = lambda n: {"Москва": 44, "Новосибирск": 270}[n]
        instance.get_estimated_intervals.return_value = MOCK_ESTIMATED
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_estimated_intervals", {
                "from_city": "Москва", "to_city": "Новосибирск", "tariff_code": 136,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["calendar_min"] == 3


@pytest.mark.anyio
async def test_cdek_estimated_intervals_missing():
    with patch("mcp_server_cdek.server.CdekAPI"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_estimated_intervals", {})
            assert result.isError
