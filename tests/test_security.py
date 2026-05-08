"""Security tests: path traversal and API error handling."""

import os

import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


# ── Path traversal — unsafe paths ─────────────────────────────────


@pytest.mark.anyio
async def test_cdek_barcode_unsafe_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_barcode.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_barcode", {
                "cdek_number": 1234567890,
                "output_path": "/etc/evil.pdf",
            })
            assert r.isError
            assert "home or temp" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_label_unsafe_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_label.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_label", {
                "cdek_number": 1234567890,
                "output_path": "/var/evil.pdf",
            })
            assert r.isError
            assert "home or temp" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_waybill_unsafe_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_waybill.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_waybill", {
                "cdek_number": 1234567890,
                "output_path": "/etc/evil.pdf",
            })
            assert r.isError
            assert "home or temp" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_download_photos_unsafe_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_photo_archive.return_value = b"PK"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_download_photos", {
                "uuid": "ph-001",
                "output_path": "/etc/evil.zip",
            })
            assert r.isError
            assert "home or temp" in r.content[0].text.lower()


# ── Path traversal — hidden files ─────────────────────────────────


@pytest.mark.anyio
async def test_cdek_barcode_hidden_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_barcode.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            home = os.path.expanduser("~")
            r = await s.call_tool("cdek_barcode", {
                "cdek_number": 1234567890,
                "output_path": f"{home}/.ssh/evil.pdf",
            })
            assert r.isError
            assert "hidden" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_label_hidden_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_label.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            home = os.path.expanduser("~")
            r = await s.call_tool("cdek_label", {
                "cdek_number": 1234567890,
                "output_path": f"{home}/.config/evil.pdf",
            })
            assert r.isError
            assert "hidden" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_waybill_hidden_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_waybill.return_value = b"%PDF"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            home = os.path.expanduser("~")
            r = await s.call_tool("cdek_waybill", {
                "cdek_number": 1234567890,
                "output_path": f"{home}/.ssh/evil.pdf",
            })
            assert r.isError
            assert "hidden" in r.content[0].text.lower()


@pytest.mark.anyio
async def test_cdek_download_photos_hidden_path():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.download_photo_archive.return_value = b"PK"
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            home = os.path.expanduser("~")
            r = await s.call_tool("cdek_download_photos", {
                "uuid": "ph-001",
                "output_path": f"{home}/.config/evil.zip",
            })
            assert r.isError
            assert "hidden" in r.content[0].text.lower()


# ── API error handling ────────────────────────────────────────────


@pytest.mark.anyio
async def test_cdek_get_order_api_error():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.get_order.side_effect = RuntimeError("GET /orders/xxx -> 500")
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_get_order", {"uuid": "xxx"})
            assert r.isError
            assert "500" in r.content[0].text


@pytest.mark.anyio
async def test_cdek_track_api_error():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.get_order_by_cdek_number.side_effect = RuntimeError("GET /orders -> 403")
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_track", {"cdek_number": 1234567890})
            assert r.isError
            assert "403" in r.content[0].text


@pytest.mark.anyio
async def test_cdek_cities_api_error():
    with patch("mcp_server_cdek.server.CdekAPI") as MockAPI:
        MockAPI.return_value.find_cities.side_effect = RuntimeError("GET /location/cities -> 401")
        async with create_connected_server_and_client_session(mcp._mcp_server) as s:
            r = await s.call_tool("cdek_cities", {"city": "Test"})
            assert r.isError
            assert "401" in r.content[0].text
