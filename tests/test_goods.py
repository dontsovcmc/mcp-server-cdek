import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp


@pytest.mark.anyio
async def test_goods_add_and_list():
    with patch("mcp_server_cdek.goods._load", return_value=[]):
        with patch("mcp_server_cdek.goods._save") as mock_save:
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("goods_add", {
                    "name": "Тестовый товар",
                    "weight": 0.5,
                    "height": 10,
                    "width": 20,
                    "length": 30,
                    "price": 500.0,
                })
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["name"] == "Тестовый товар"
                assert data["weight"] == 0.5
                assert data["height"] == 10

                mock_save.assert_called_once()


@pytest.mark.anyio
async def test_goods_list_empty():
    with patch("mcp_server_cdek.goods._load", return_value=[]):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("goods_list", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data == []


@pytest.mark.anyio
async def test_goods_remove():
    existing = [{"name": "Товар1", "weight": 0.1, "height": 5, "width": 5, "length": 5, "price": 100.0}]
    with patch("mcp_server_cdek.goods._load", return_value=existing):
        with patch("mcp_server_cdek.goods._save"):
            async with create_connected_server_and_client_session(mcp._mcp_server) as session:
                result = await session.call_tool("goods_remove", {"name": "Товар1"})
                assert not result.isError
                data = json.loads(result.content[0].text)
                assert data["removed"]["name"] == "Товар1"
