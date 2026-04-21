import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_ALL_TARIFFS = [
    {"tariff_code": 136, "tariff_name": "Посылка склад-склад", "mode": 2},
    {"tariff_code": 137, "tariff_name": "Посылка склад-дверь", "mode": 3},
]
MOCK_TARIFF_RESULT = {"delivery_sum": 350.0, "period_min": 2, "period_max": 5, "currency": "RUB"}
MOCK_TARIFFLIST_RESULT = {
    "tariff_codes": [
        {"tariff_code": 136, "delivery_sum": 300.0, "period_min": 3, "period_max": 5},
        {"tariff_code": 137, "delivery_sum": 450.0, "period_min": 2, "period_max": 4},
    ],
}
MOCK_TARIFF_SERVICE_RESULT = {
    "tariff_codes": [
        {"tariff_code": 136, "delivery_sum": 300.0, "services": [{"code": "INSURANCE", "sum": 50.0}]},
    ],
}


@pytest.mark.anyio
async def test_cdek_all_tariffs():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_all_tariffs.return_value = MOCK_ALL_TARIFFS
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_all_tariffs", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["count"] == 2


@pytest.mark.anyio
async def test_cdek_calculate_tariff():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = [44, 270]
        instance.calculate_tariff.return_value = MOCK_TARIFF_RESULT
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_calculate_tariff", {
                "tariff_code": 136, "from_city": "Москва", "to_city": "Новосибирск", "weight_kg": 1.0,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["delivery_sum"] == 350.0


@pytest.mark.anyio
async def test_cdek_calculate_tarifflist():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = [44, 137]
        instance.calculate_tarifflist.return_value = MOCK_TARIFFLIST_RESULT
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_calculate_tarifflist", {
                "from_city": "Москва", "to_city": "Санкт-Петербург", "weight_kg": 0.5,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert len(data["tariff_codes"]) == 2


@pytest.mark.anyio
async def test_cdek_calculate_tariff_and_service():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = [44, 43]
        instance.calculate_tariff_and_service.return_value = MOCK_TARIFF_SERVICE_RESULT
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_calculate_tariff_and_service", {
                "from_city": "Москва", "to_city": "Казань", "weight_kg": 2.0,
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["tariff_codes"][0]["services"][0]["code"] == "INSURANCE"
