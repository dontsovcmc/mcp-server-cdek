import json
import pytest
from unittest.mock import patch

from mcp.shared.memory import create_connected_server_and_client_session
from mcp_server_cdek.server import mcp
from mcp_server_cdek import config


@pytest.fixture
def empty_config(tmp_path):
    path = tmp_path / "config.json"
    with patch.object(config, "CONFIG_PATH", str(path)):
        yield path


@pytest.fixture
def filled_config(tmp_path):
    path = tmp_path / "config.json"
    data = {
        "sender": {
            "company": "Test LLC",
            "name": "Ivanov I.",
            "full_name": "Ivanov Ivan Ivanovich",
            "email": "test@example.com",
            "phone": "+70001234567",
        },
        "my_pvz": "MSK005",
        "product_defaults": {
            "name": "Widget",
            "weight": 0.5,
            "height": 10,
            "width": 20,
            "length": 30,
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False))
    with patch.object(config, "CONFIG_PATH", str(path)):
        yield path


def test_load_config_empty(empty_config):
    assert config.load_config() == {}


def test_load_config_filled(filled_config):
    cfg = config.load_config()
    assert cfg["sender"]["company"] == "Test LLC"
    assert cfg["my_pvz"] == "MSK005"
    assert cfg["product_defaults"]["weight"] == 0.5


def test_set_value_sender(empty_config):
    result = config.set_value("sender", "company", "New Company")
    assert result["sender"]["company"] == "New Company"
    # Verify persisted
    loaded = config.load_config()
    assert loaded["sender"]["company"] == "New Company"


def test_set_value_my_pvz(empty_config):
    result = config.set_value("my_pvz", "", "SPB010")
    assert result["my_pvz"] == "SPB010"


def test_set_value_product_defaults_numeric(empty_config):
    config.set_value("product_defaults", "weight", "1.5")
    config.set_value("product_defaults", "height", "15")
    loaded = config.load_config()
    assert loaded["product_defaults"]["weight"] == 1.5
    assert loaded["product_defaults"]["height"] == 15


def test_set_value_invalid_section(empty_config):
    with pytest.raises(RuntimeError, match="Invalid section"):
        config.set_value("invalid", "key", "val")


def test_set_value_invalid_sender_key(empty_config):
    with pytest.raises(RuntimeError, match="Invalid sender key"):
        config.set_value("sender", "bad_key", "val")


def test_set_value_invalid_product_key(empty_config):
    with pytest.raises(RuntimeError, match="Invalid product_defaults key"):
        config.set_value("product_defaults", "bad_key", "val")


def test_get_sender(filled_config):
    sender = config.get_sender()
    assert sender["company"] == "Test LLC"
    assert sender["phone"] == "+70001234567"


def test_get_my_pvz(filled_config):
    assert config.get_my_pvz() == "MSK005"


def test_get_product_defaults(filled_config):
    defaults = config.get_product_defaults()
    assert defaults["name"] == "Widget"
    assert defaults["weight"] == 0.5


# ── MCP tool tests ────────────────────────────────────────────────


@pytest.mark.anyio
async def test_config_show_empty():
    with patch.object(config, "CONFIG_PATH", "/tmp/_mcp_test_nonexistent.json"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("config_show", {})
            assert not result.isError
            data = json.loads(result.content[0].text)
            assert data == {}


@pytest.mark.anyio
async def test_config_show_filled(filled_config):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("config_show", {})
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["sender"]["company"] == "Test LLC"
        assert data["my_pvz"] == "MSK005"


@pytest.mark.anyio
async def test_config_set_tool(empty_config):
    async with create_connected_server_and_client_session(mcp._mcp_server) as session:
        result = await session.call_tool("config_set", {
            "section": "sender", "key": "company", "value": "My Company",
        })
        assert not result.isError
        data = json.loads(result.content[0].text)
        assert data["sender"]["company"] == "My Company"


@pytest.mark.anyio
async def test_config_set_tool_invalid():
    with patch.object(config, "CONFIG_PATH", "/tmp/_mcp_test_cfg.json"):
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            result = await session.call_tool("config_set", {
                "section": "bad", "key": "x", "value": "y",
            })
            assert result.isError
