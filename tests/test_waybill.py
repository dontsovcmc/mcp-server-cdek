import json
import pytest
from unittest.mock import patch, mock_open

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


@pytest.mark.anyio
async def test_cdek_label():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.download_label.return_value = b"%PDF-fake-label"

        m = mock_open()
        with patch("builtins.open", m):
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("cdek_label", {
                    "cdek_number": 1234567890,
                    "output_path": "/tmp/test_label.pdf",
                })
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["cdek_number"] == 1234567890
                assert "path" in data

        instance.download_label.assert_called_once_with(1234567890, "A6")
        m.assert_called_once_with("/tmp/test_label.pdf", "wb")


@pytest.mark.anyio
async def test_cdek_label_error():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.download_label.side_effect = RuntimeError("Ошибка скачивания этикетки: 500")

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_label", {
                "cdek_number": 1234567890,
                "output_path": "/tmp/test_label.pdf",
            })
            assert result.isError


@pytest.mark.anyio
async def test_cdek_waybill():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.download_waybill.return_value = b"%PDF-fake-waybill"

        m = mock_open()
        with patch("builtins.open", m):
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("cdek_waybill", {
                    "cdek_number": 1234567890,
                    "output_path": "/tmp/test_waybill.pdf",
                })
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["cdek_number"] == 1234567890
                assert "path" in data

        instance.download_waybill.assert_called_once_with(1234567890)
        m.assert_called_once_with("/tmp/test_waybill.pdf", "wb")


@pytest.mark.anyio
async def test_cdek_waybill_error():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        instance = MockAPI.return_value
        instance.download_waybill.side_effect = RuntimeError("Ошибка скачивания накладной: 500")

        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("cdek_waybill", {
                "cdek_number": 1234567890,
                "output_path": "/tmp/test_waybill.pdf",
            })
            assert result.isError
