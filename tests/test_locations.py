import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_REGIONS = [
    {"region": "Московская область", "country_code": "RU", "country": "Россия"},
    {"region": "Ленинградская область", "country_code": "RU", "country": "Россия"},
]
MOCK_POSTALCODES = [{"postalcode": "101000"}, {"postalcode": "101001"}]
MOCK_COORDINATES = [{"code": 44, "city": "Москва", "region": "Москва"}]
MOCK_SUGGEST = [
    {"code": 44, "city": "Москва", "country": "Россия"},
    {"code": 137, "city": "Московский", "country": "Россия"},
]


@pytest.mark.anyio
async def test_cdek_regions():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_regions.return_value = MOCK_REGIONS
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_regions", {"country_codes": "RU", "size": 5})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["count"] == 2
            assert data["regions"][0]["region"] == "Московская область"


@pytest.mark.anyio
async def test_cdek_postalcodes():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_postalcodes.return_value = MOCK_POSTALCODES
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_postalcodes", {"city_code": 44})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["city_code"] == 44
            assert len(data["postalcodes"]) == 2


@pytest.mark.anyio
async def test_cdek_coordinates():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_by_coordinates.return_value = MOCK_COORDINATES
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_coordinates", {"latitude": 55.7558, "longitude": 37.6173})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data["results"]) == 1


@pytest.mark.anyio
async def test_cdek_suggest_cities():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.suggest_cities.return_value = MOCK_SUGGEST
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_suggest_cities", {"name": "Моск"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["query"] == "Моск"
            assert data["count"] == 2
