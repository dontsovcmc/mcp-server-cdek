import json
import pytest
from unittest.mock import patch, mock_open

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


MOCK_CHECKS = {"entity": {"cdek_number": "1400567890", "type": "SALE"}}
MOCK_PASSPORT = {"entity": {"cdek_number": "1400567890", "status": "VERIFIED"}}
MOCK_PHOTO_REQ = {"entity": {"uuid": "ph-001"}, "requests": [{"type": "CREATE", "state": "ACCEPTED"}]}
MOCK_PREALERT = {"entity": {"uuid": "pre-001"}, "requests": [{"type": "CREATE", "state": "ACCEPTED"}]}
MOCK_PREALERT_INFO = {"entity": {"uuid": "pre-001", "shipment_point": "MSK005"}}
MOCK_REVERSE = {"available": True, "tariff_code": 136, "delivery_sum": 350.0}
MOCK_REGISTRIES = {"items": [{"uuid": "reg-001", "date": "2025-06-15", "orders_count": 5}]}
MOCK_INTL = {"restricted": False, "restrictions": []}


@pytest.mark.anyio
async def test_cdek_checks():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_checks.return_value = MOCK_CHECKS
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_checks", {"cdek_number": "1400567890"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["type"] == "SALE"


@pytest.mark.anyio
async def test_cdek_passport():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_passport.return_value = MOCK_PASSPORT
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_passport", {"cdek_number": "1400567890"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["status"] == "VERIFIED"


@pytest.mark.anyio
async def test_cdek_request_photos():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.request_photo_documents.return_value = MOCK_PHOTO_REQ
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_request_photos", {
                "period_begin": "2025-06-01", "cdek_numbers": "1400567890,1400567891",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["entity"]["uuid"] == "ph-001"
        payload = instance.request_photo_documents.call_args[0][0]
        assert len(payload["orders"]) == 2


@pytest.mark.anyio
async def test_cdek_download_photos():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.download_photo_archive.return_value = b"PK-fake-zip"
        m = mock_open()
        with patch("builtins.open", m):
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("cdek_download_photos", {
                    "uuid": "ph-001", "output_path": "/tmp/photos.zip",
                })
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["size"] > 0


@pytest.mark.anyio
async def test_cdek_create_prealert():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.create_prealert.return_value = MOCK_PREALERT
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_create_prealert", {
                "planned_date": "2025-06-20", "shipment_point": "MSK005", "cdek_numbers": "1400567890",
            })
            assert not result.isError
        instance.create_prealert.assert_called_once_with(
            "2025-06-20", "MSK005", [{"cdek_number": "1400567890"}],
        )


@pytest.mark.anyio
async def test_cdek_get_prealert():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_prealert.return_value = MOCK_PREALERT_INFO
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_get_prealert", {"uuid": "pre-001"})
            assert not result.isError
        instance.get_prealert.assert_called_once_with("pre-001")


@pytest.mark.anyio
async def test_cdek_reverse_availability():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = [44, 137]
        instance.check_reverse_availability.return_value = MOCK_REVERSE
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_reverse_availability", {
                "tariff_code": 136, "from_city": "Москва", "to_city": "Новосибирск",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["available"] is True


@pytest.mark.anyio
async def test_cdek_registries():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.get_registries.return_value = MOCK_REGISTRIES
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_registries", {"date": "2025-06-15"})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["items"][0]["orders_count"] == 5


@pytest.mark.anyio
async def test_cdek_international_restrictions():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.find_city_code.side_effect = [44, 9999]
        instance.get_international_restrictions.return_value = MOCK_INTL
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_international_restrictions", {
                "tariff_code": 7, "from_city": "Москва", "to_city": "Алматы",
            })
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data["restricted"] is False
