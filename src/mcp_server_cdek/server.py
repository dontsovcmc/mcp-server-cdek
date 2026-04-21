"""MCP server for CDEK delivery service API."""

import json
import logging
import os
import re
import sys
import time

from mcp.server.fastmcp import FastMCP

from .cdek_api import CdekAPI, TARIFF_WAREHOUSE_WAREHOUSE, TARIFF_WAREHOUSE_DOOR
from .goods import add_good, find_good, list_goods, remove_good

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

mcp = FastMCP("cdek")


def _get_api() -> CdekAPI:
    client_id = os.getenv("CDEK_CLIENT")
    client_secret = os.getenv("CDEK_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("CDEK_CLIENT and CDEK_SECRET environment variables are required")
    return CdekAPI(client_id, client_secret)


def _get_sender() -> dict:
    """Собрать данные отправителя из переменных окружения."""
    company = os.getenv("CDEK_SENDER_COMPANY", "")
    name = os.getenv("CDEK_SENDER_NAME", "")
    full_name = os.getenv("CDEK_SENDER_FULL_NAME", "")
    email = os.getenv("CDEK_SENDER_EMAIL", "")
    phone = os.getenv("CDEK_SENDER_PHONE", "")

    missing = []
    if not company:
        missing.append("CDEK_SENDER_COMPANY")
    if not name:
        missing.append("CDEK_SENDER_NAME")
    if not full_name:
        missing.append("CDEK_SENDER_FULL_NAME")
    if not email:
        missing.append("CDEK_SENDER_EMAIL")
    if not phone:
        missing.append("CDEK_SENDER_PHONE")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

    sender = {
        "company": company,
        "name": name,
        "contragent_type": "LEGAL_ENTITY",
        "email": email,
        "phones": [{"number": phone}],
        "passport_requirements_satisfied": False,
    }
    seller = {"name": full_name}
    recipient_self = {
        "company": company,
        "name": full_name,
        "email": email,
        "phones": [{"number": phone}],
        "passport_requirements_satisfied": False,
    }
    return sender, seller, recipient_self


def _get_product_defaults() -> dict:
    """Дефолтные параметры товара из env."""
    return {
        "product_name": os.getenv("CDEK_DEFAULT_PRODUCT_NAME", "Товар"),
        "weight": float(os.getenv("CDEK_DEFAULT_WEIGHT", "0.17")),
        "height": int(os.getenv("CDEK_DEFAULT_HEIGHT", "8")),
        "width": int(os.getenv("CDEK_DEFAULT_WIDTH", "7")),
        "length": int(os.getenv("CDEK_DEFAULT_LENGTH", "10")),
    }


def _build_items(product_name: str, weight_kg: float, quantity: int, price: float = 100.0) -> list:
    return [{
        "ware_key": "item",
        "name": product_name,
        "cost": price,
        "amount": quantity,
        "weight": int(weight_kg * 1000),
        "payment": {"value": 0},
    }]


# ── Goods (local catalog) ───────────────────────────────────────────


@mcp.tool()
def goods_list() -> str:
    """List all goods from local catalog (~/.config/mcp-server-cdek/goods.json).

    Returns JSON array of goods with name, weight (kg), height/width/length (cm), price.
    """
    return json.dumps(list_goods(), ensure_ascii=False)


@mcp.tool()
def goods_add(name: str, weight: float, height: int, width: int, length: int, price: float = 100.0) -> str:
    """Add a new good to local catalog.

    Args:
        name: Product name (e.g. "Wi-Fi модем")
        weight: Weight per unit in kg (e.g. 0.17)
        height: Height in cm (e.g. 8)
        width: Width in cm (e.g. 7)
        length: Length in cm (e.g. 10)
        price: Declared value per unit in rubles (default 100.0)
    """
    item = add_good(name, weight, height, width, length, price)
    return json.dumps(item, ensure_ascii=False)


@mcp.tool()
def goods_remove(name: str) -> str:
    """Remove a good from local catalog by exact name.

    Args:
        name: Exact product name to remove
    """
    item = remove_good(name)
    return json.dumps({"removed": item}, ensure_ascii=False)


# ── Create Order ────────────────────────────────────────────────────


@mcp.tool()
def cdek_create_order(
    direction: str,
    recipient_name: str,
    recipient_phone: str,
    pvz: str = "",
    address: str = "",
    recipient_email: str = "",
    product_name: str = "",
    weight: float = 0,
    height: int = 0,
    width: int = 0,
    length: int = 0,
    quantity: int = 1,
    price: float = 0,
) -> str:
    """Create a CDEK delivery order.

    Two directions:
    - "from_me": send package from my warehouse/PVZ to recipient's PVZ or door
    - "to_me": receive package from sender to my PVZ (returns)

    For "from_me": specify either pvz (delivery point code or address) or address (door delivery).
    For "to_me": specify address (sender's address), package goes to CDEK_MY_PVZ.

    If product parameters are not specified, defaults from env or goods catalog are used.

    Args:
        direction: "from_me" or "to_me"
        recipient_name: Recipient/sender full name
        recipient_phone: Phone number (e.g. "+79001234567")
        pvz: PVZ code (e.g. "MSK005") or address for PVZ search (e.g. "Москва, Тверская"). For from_me warehouse delivery.
        address: Full delivery address for door delivery (from_me) or sender address (to_me)
        recipient_email: Email (optional)
        product_name: Product name (overrides defaults)
        weight: Weight per unit in kg (overrides defaults)
        height: Height in cm (overrides defaults)
        width: Width in cm (overrides defaults)
        length: Length in cm (overrides defaults)
        quantity: Number of items (default 1)
        price: Declared value per unit in rubles (overrides defaults)
    """
    if direction not in ("from_me", "to_me"):
        raise RuntimeError("direction must be 'from_me' or 'to_me'")

    api = _get_api()
    sender, seller, recipient_self = _get_sender()

    # Resolve product params: explicit > goods catalog > env defaults
    defaults = _get_product_defaults()
    p_name = product_name or defaults["product_name"]
    p_weight = weight or defaults["weight"]
    p_height = height or defaults["height"]
    p_width = width or defaults["width"]
    p_length = length or defaults["length"]
    p_price = price or 100.0

    # Try to find product in goods catalog for better defaults
    if not product_name:
        goods = list_goods()
        if goods:
            g = goods[0]
            p_name = g["name"]
            p_weight = g["weight"]
            p_height = g["height"]
            p_width = g["width"]
            p_length = g["length"]
            p_price = g.get("price", 100.0)

    items = _build_items(p_name, p_weight, quantity, p_price)
    weight_g = int(p_weight * quantity * 1000)
    number = str(int(time.time() * 1000))

    if direction == "from_me":
        if pvz and address:
            raise RuntimeError("Specify either pvz or address, not both")
        if not pvz and not address:
            raise RuntimeError("For from_me specify pvz or address")

        # Resolve PVZ: code or address search
        delivery_point = None
        if pvz:
            if not re.match(r"^[A-Za-z0-9_]+$", pvz):
                delivery_point = _resolve_pvz(api, pvz)
            else:
                delivery_point = pvz

        payload = {
            "number": number,
            "delivery_recipient_cost": {"value": 0.0, "vat_sum": 0.0},
            "from_location": {"city": "Москва"},
            "sender": sender,
            "seller": seller,
            "recipient": {
                "name": recipient_name,
                "phones": [{"number": recipient_phone}],
            },
            "packages": [{
                "number": number,
                "comment": "Упаковка",
                "items": items,
                "height": p_height,
                "length": p_length,
                "width": p_width,
                "weight": weight_g,
            }],
            "print": "barcode",
        }

        if recipient_email:
            payload["recipient"]["email"] = recipient_email

        if delivery_point:
            payload["delivery_point"] = delivery_point
            payload["tariff_code"] = TARIFF_WAREHOUSE_WAREHOUSE
        else:
            payload["to_location"] = {"address": address}
            payload["tariff_code"] = TARIFF_WAREHOUSE_DOOR

    else:  # to_me
        if not address:
            raise RuntimeError("For to_me specify sender address")
        my_pvz = os.getenv("CDEK_MY_PVZ")
        if not my_pvz:
            raise RuntimeError("CDEK_MY_PVZ environment variable is required for to_me orders")

        payload = {
            "number": number,
            "delivery_recipient_cost": {"value": 0.0, "vat_sum": 0.0},
            "sender": {
                "name": recipient_name,
                "phones": [{"number": recipient_phone}],
            },
            "from_location": {"address": address},
            "delivery_point": my_pvz,
            "recipient": recipient_self,
            "packages": [{
                "number": number,
                "comment": "Упаковка",
                "items": items,
                "height": p_height,
                "length": p_length,
                "width": p_width,
                "weight": weight_g,
            }],
            "print": "barcode",
            "tariff_code": TARIFF_WAREHOUSE_WAREHOUSE,
        }

    uuid = api.create_order(payload)
    entity = api.poll_order(uuid)

    result = {
        "uuid": uuid,
        "cdek_number": entity["cdek_number"],
        "number": number,
        "direction": direction,
        "status": "created",
    }
    return json.dumps(result, ensure_ascii=False)


# ── Track Order ─────────────────────────────────────────────────────


@mcp.tool()
def cdek_track(cdek_number: int) -> str:
    """Track a CDEK order by its CDEK number.

    Returns current order status, statuses history, and delivery details.

    Args:
        cdek_number: CDEK tracking number (e.g. 1234567890)
    """
    api = _get_api()
    data = api.get_order_by_cdek_number(cdek_number)
    entity = data.get("entity", {})

    result = {
        "cdek_number": entity.get("cdek_number"),
        "number": entity.get("number"),
        "statuses": [
            {"code": s["code"], "name": s["name"], "date": s["date_time"]}
            for s in entity.get("statuses", [])
        ],
        "delivery_point": entity.get("delivery_point"),
        "recipient": entity.get("recipient", {}).get("name"),
    }
    return json.dumps(result, ensure_ascii=False)


# ── Barcode ─────────────────────────────────────────────────────────


@mcp.tool()
def cdek_barcode(cdek_number: int, output_path: str) -> str:
    """Download barcode label PDF for a CDEK order.

    Args:
        cdek_number: CDEK tracking number
        output_path: Absolute path to save PDF (e.g. /tmp/1234567890.pdf)
    """
    api = _get_api()
    pdf = api.download_barcode(cdek_number)
    with open(output_path, "wb") as f:
        f.write(pdf)
    return json.dumps({"path": os.path.abspath(output_path), "cdek_number": cdek_number}, ensure_ascii=False)


# ── Delivery Points ─────────────────────────────────────────────────


@mcp.tool()
def cdek_delivery_points(city: str, search: str = "") -> str:
    """Search CDEK delivery points (PVZ) in a city.

    Args:
        city: City name (e.g. "Москва", "Санкт-Петербург")
        search: Optional address substring to filter (e.g. "Тверская")
    """
    api = _get_api()
    city_code = api.find_city_code(city)
    points = api.find_delivery_points(city_code)

    if search:
        search_lower = search.lower()
        points = [
            p for p in points
            if search_lower in p.get("location", {}).get("address", "").lower()
        ]

    result = []
    for p in points[:50]:
        result.append({
            "code": p["code"],
            "address": p.get("location", {}).get("address", ""),
            "work_time": p.get("work_time", ""),
            "type": p.get("type", ""),
            "city": city,
        })

    return json.dumps({"city": city, "city_code": city_code, "count": len(result), "points": result}, ensure_ascii=False)


# ── Cities ──────────────────────────────────────────────────────────


@mcp.tool()
def cdek_cities(city: str) -> str:
    """Search CDEK cities by name. Returns city codes needed for other operations.

    Args:
        city: City name or part of it (e.g. "Новосиб")
    """
    api = _get_api()
    cities = api.find_cities(city, size=10)
    result = [
        {
            "code": c["code"],
            "city": c.get("city", ""),
            "region": c.get("region", ""),
            "country": c.get("country", ""),
        }
        for c in cities
    ]
    return json.dumps({"query": city, "count": len(result), "cities": result}, ensure_ascii=False)


# ── Helper ──────────────────────────────────────────────────────────


def _resolve_pvz(api: CdekAPI, address: str) -> str:
    """Найти ПВЗ по текстовому адресу (город, улица)."""
    parts = [p.strip() for p in address.split(",")]
    city_name = parts[0]
    search_parts = [p.lower() for p in parts[1:]] if len(parts) > 1 else []

    city_code = api.find_city_code(city_name)
    points = api.find_delivery_points(city_code)

    if not points:
        raise RuntimeError(f"ПВЗ в городе «{city_name}» не найдены")

    if search_parts:
        filtered = []
        for p in points:
            addr_lower = p.get("location", {}).get("address", "").lower()
            if any(part in addr_lower for part in search_parts):
                filtered.append(p)
        if filtered:
            points = filtered

    if len(points) == 1:
        return points[0]["code"]

    # Return the best match (first one)
    descriptions = []
    for p in points[:10]:
        descriptions.append(f"{p['code']}: {p.get('location', {}).get('address', '')}")
    raise RuntimeError(
        f"Найдено {len(points)} ПВЗ, уточните адрес или используйте код:\n" +
        "\n".join(descriptions)
    )
