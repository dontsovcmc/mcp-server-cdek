"""Конфиг пользователя. Хранится в ~/.config/mcp-server-cdek/config.json."""

import json
import os

CONFIG_PATH = os.path.expanduser("~/.config/mcp-server-cdek/config.json")

VALID_SECTIONS = ("sender", "my_pvz", "product_defaults")

SENDER_KEYS = ("company", "name", "full_name", "email", "phone")
PRODUCT_KEYS = ("name", "weight", "height", "width", "length")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_sender() -> dict:
    """Получить данные отправителя из конфига."""
    config = load_config()
    return config.get("sender", {})


def get_my_pvz() -> str:
    """Получить код ПВЗ из конфига."""
    config = load_config()
    return config.get("my_pvz", "")


def get_product_defaults() -> dict:
    """Получить дефолты товара из конфига."""
    config = load_config()
    return config.get("product_defaults", {})


def set_value(section: str, key: str, value: str) -> dict:
    """Установить значение в конфиге. Возвращает обновлённый конфиг."""
    if section not in VALID_SECTIONS:
        raise RuntimeError(f"Invalid section '{section}'. Valid: {', '.join(VALID_SECTIONS)}")

    config = load_config()

    if section == "my_pvz":
        config["my_pvz"] = value
    elif section == "sender":
        if key not in SENDER_KEYS:
            raise RuntimeError(f"Invalid sender key '{key}'. Valid: {', '.join(SENDER_KEYS)}")
        config.setdefault("sender", {})[key] = value
    elif section == "product_defaults":
        if key not in PRODUCT_KEYS:
            raise RuntimeError(f"Invalid product_defaults key '{key}'. Valid: {', '.join(PRODUCT_KEYS)}")
        # Конвертируем числовые значения
        if key == "weight":
            config.setdefault("product_defaults", {})[key] = float(value)
        elif key in ("height", "width", "length"):
            config.setdefault("product_defaults", {})[key] = int(value)
        else:
            config.setdefault("product_defaults", {})[key] = value

    save_config(config)
    return config
