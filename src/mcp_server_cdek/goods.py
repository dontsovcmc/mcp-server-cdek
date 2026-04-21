"""Локальный справочник товаров. Хранится в ~/.config/mcp-server-cdek/goods.json."""

import json
import os

GOODS_PATH = os.path.expanduser("~/.config/mcp-server-cdek/goods.json")


def _load() -> list:
    if not os.path.exists(GOODS_PATH):
        return []
    with open(GOODS_PATH) as f:
        return json.load(f)


def _save(goods: list):
    os.makedirs(os.path.dirname(GOODS_PATH), exist_ok=True)
    with open(GOODS_PATH, "w") as f:
        json.dump(goods, f, ensure_ascii=False, indent=2)


def list_goods() -> list:
    return _load()


def add_good(name: str, weight: float, height: int, width: int, length: int, price: float = 100.0) -> dict:
    """Добавить товар. weight в кг, height/width/length в см."""
    goods = _load()
    for g in goods:
        if g["name"] == name:
            raise RuntimeError(f"Товар '{name}' уже существует")
    item = {
        "name": name,
        "weight": weight,
        "height": height,
        "width": width,
        "length": length,
        "price": price,
    }
    goods.append(item)
    _save(goods)
    return item


def remove_good(name: str) -> dict:
    goods = _load()
    found = [g for g in goods if g["name"] == name]
    if not found:
        raise RuntimeError(f"Товар '{name}' не найден")
    goods = [g for g in goods if g["name"] != name]
    _save(goods)
    return found[0]


def find_good(query: str) -> dict:
    """Найти товар по подстроке. Ошибка если 0 или >1 совпадений."""
    goods = _load()
    query_lower = query.lower()
    matches = [g for g in goods if query_lower in g["name"].lower()]
    if len(matches) == 0:
        names = "\n".join(f"  - {g['name']}" for g in goods)
        raise RuntimeError(f"Товар '{query}' не найден.\nДоступные:\n{names}")
    if len(matches) > 1:
        names = "\n".join(f"  - {g['name']}" for g in matches)
        raise RuntimeError(f"Несколько совпадений для '{query}':\n{names}")
    return matches[0]
