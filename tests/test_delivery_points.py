import json
import pytest
from unittest.mock import patch, MagicMock

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_CITIES = [{"code": 44, "city": "Москва", "region": "Москва", "country": "Россия"}]

MOCK_POINTS = [
    {
        "code": "MSK005",
        "location": {"address": "Тверская ул., 12"},
        "work_time": "Пн-Пт 09:00-21:00",
        "type": "PVZ",
    },
    {
        "code": "MSK010",
        "location": {"address": "Арбат ул., 1"},
        "work_time": "Пн-Вс 10:00-22:00",
        "type": "PVZ",
    },
]


@pytest.mark.anyio
async def test_cdek_delivery_points():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.return_value = 44
        instance.find_delivery_points.return_value = MOCK_POINTS

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_delivery_points", {
                "city": "Москва",
                "search": "Тверская",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["count"] == 1
            assert data["points"][0]["code"] == "MSK005"


@pytest.mark.anyio
async def test_cdek_cities():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_cities.return_value = MOCK_CITIES

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_cities", {"city": "Москва"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["count"] == 1
            assert data["cities"][0]["code"] == 44
