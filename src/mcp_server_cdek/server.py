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


# ── Label ──────────────────────────────────────────────────────────


@mcp.tool()
def cdek_label(cdek_number: int, output_path: str, format: str = "A6") -> str:
    """Download shipping label (этикетка) PDF for a CDEK order.

    Args:
        cdek_number: CDEK tracking number
        output_path: Absolute path to save PDF (e.g. /tmp/1234567890_label.pdf)
        format: Label format — A4 (4 per page), A5 (2 per page), A6 (1 per page, ~70x120мм, default), A7 (small)
    """
    api = _get_api()
    pdf = api.download_label(cdek_number, format)
    with open(output_path, "wb") as f:
        f.write(pdf)
    return json.dumps({"path": os.path.abspath(output_path), "cdek_number": cdek_number, "format": format}, ensure_ascii=False)


# ── Waybill ────────────────────────────────────────────────────────


@mcp.tool()
def cdek_waybill(cdek_number: int, output_path: str) -> str:
    """Download waybill (накладная) PDF for a CDEK order.

    Args:
        cdek_number: CDEK tracking number
        output_path: Absolute path to save PDF (e.g. /tmp/1234567890_waybill.pdf)
    """
    api = _get_api()
    pdf = api.download_waybill(cdek_number)
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


# ── Regions & Locations ────────────────────────────────────────────


@mcp.tool()
def cdek_regions(country_codes: str = "", size: int = 5) -> str:
    """Search CDEK regions.

    Args:
        country_codes: Country codes filter (e.g. "RU", "KZ"). Empty for all.
        size: Max number of results (default 5)
    """
    api = _get_api()
    regions = api.find_regions(country_codes=country_codes or None, size=size)
    result = [
        {"region": r.get("region", ""), "country_code": r.get("country_code", ""), "country": r.get("country", "")}
        for r in regions
    ]
    return json.dumps({"country_codes": country_codes, "count": len(result), "regions": result}, ensure_ascii=False)


@mcp.tool()
def cdek_postalcodes(city_code: int) -> str:
    """Get postal codes for a city by its CDEK city code.

    Args:
        city_code: CDEK city code (use cdek_cities to find it)
    """
    api = _get_api()
    data = api.find_postalcodes(city_code)
    return json.dumps({"city_code": city_code, "postalcodes": data}, ensure_ascii=False)


@mcp.tool()
def cdek_coordinates(latitude: float, longitude: float) -> str:
    """Find CDEK location by geographic coordinates.

    Args:
        latitude: Latitude (e.g. 55.7558)
        longitude: Longitude (e.g. 37.6173)
    """
    api = _get_api()
    data = api.find_by_coordinates(latitude, longitude)
    return json.dumps({"latitude": latitude, "longitude": longitude, "results": data}, ensure_ascii=False)


@mcp.tool()
def cdek_suggest_cities(name: str, country_code: str = "") -> str:
    """Autocomplete city name suggestions.

    Args:
        name: City name or prefix (e.g. "Моск")
        country_code: Country code filter (e.g. "RU"). Empty for all.
    """
    api = _get_api()
    suggestions = api.suggest_cities(name, country_code=country_code)
    return json.dumps({"query": name, "count": len(suggestions), "suggestions": suggestions}, ensure_ascii=False)


# ── Calculator ─────────────────────────────────────────────────────


@mcp.tool()
def cdek_all_tariffs(lang: str = "rus") -> str:
    """Get list of all available CDEK tariffs.

    Args:
        lang: Language for tariff names — "rus" or "eng" (default "rus")
    """
    api = _get_api()
    tariffs = api.get_all_tariffs(lang=lang)
    return json.dumps({"count": len(tariffs), "tariffs": tariffs}, ensure_ascii=False)


@mcp.tool()
def cdek_calculate_tariff(
    tariff_code: int,
    from_city: str,
    to_city: str,
    weight_kg: float,
    length: int = 10,
    width: int = 10,
    height: int = 10,
) -> str:
    """Calculate delivery cost for a specific tariff.

    Args:
        tariff_code: CDEK tariff code (e.g. 136, 137)
        from_city: Sender city name (e.g. "Москва")
        to_city: Recipient city name (e.g. "Новосибирск")
        weight_kg: Package weight in kg
        length: Package length in cm (default 10)
        width: Package width in cm (default 10)
        height: Package height in cm (default 10)
    """
    api = _get_api()
    from_code = api.find_city_code(from_city)
    to_code = api.find_city_code(to_city)
    payload = {
        "tariff_code": tariff_code,
        "from_location": {"code": from_code},
        "to_location": {"code": to_code},
        "packages": [{"weight": int(weight_kg * 1000), "length": length, "width": width, "height": height}],
    }
    data = api.calculate_tariff(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_calculate_tarifflist(
    from_city: str,
    to_city: str,
    weight_kg: float,
    length: int = 10,
    width: int = 10,
    height: int = 10,
) -> str:
    """Calculate delivery cost for all available tariffs between two cities.

    Args:
        from_city: Sender city name
        to_city: Recipient city name
        weight_kg: Package weight in kg
        length: Package length in cm (default 10)
        width: Package width in cm (default 10)
        height: Package height in cm (default 10)
    """
    api = _get_api()
    from_code = api.find_city_code(from_city)
    to_code = api.find_city_code(to_city)
    payload = {
        "from_location": {"code": from_code},
        "to_location": {"code": to_code},
        "packages": [{"weight": int(weight_kg * 1000), "length": length, "width": width, "height": height}],
    }
    data = api.calculate_tarifflist(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_calculate_tariff_and_service(
    from_city: str,
    to_city: str,
    weight_kg: float,
    length: int = 10,
    width: int = 10,
    height: int = 10,
) -> str:
    """Calculate delivery cost for all tariffs with additional services info.

    Args:
        from_city: Sender city name
        to_city: Recipient city name
        weight_kg: Package weight in kg
        length: Package length in cm (default 10)
        width: Package width in cm (default 10)
        height: Package height in cm (default 10)
    """
    api = _get_api()
    from_code = api.find_city_code(from_city)
    to_code = api.find_city_code(to_city)
    payload = {
        "from_location": {"code": from_code},
        "to_location": {"code": to_code},
        "packages": [{"weight": int(weight_kg * 1000), "length": length, "width": width, "height": height}],
    }
    data = api.calculate_tariff_and_service(payload)
    return json.dumps(data, ensure_ascii=False)


# ── Order Management ───────────────────────────────────────────────


@mcp.tool()
def cdek_update_order(uuid: str = "", cdek_number: str = "", comment: str = "", delivery_point: str = "") -> str:
    """Update an existing CDEK order.

    Args:
        uuid: Order UUID
        cdek_number: CDEK tracking number (alternative to uuid)
        comment: New comment for the order
        delivery_point: New delivery point code
    """
    if not uuid and not cdek_number:
        raise RuntimeError("Specify either uuid or cdek_number")
    api = _get_api()
    payload: dict = {}
    if uuid:
        payload["uuid"] = uuid
    if cdek_number:
        payload["cdek_number"] = cdek_number
    if comment:
        payload["comment"] = comment
    if delivery_point:
        payload["delivery_point"] = delivery_point
    data = api.update_order(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_delete_order(uuid: str) -> str:
    """Delete (cancel) a CDEK order by UUID.

    Args:
        uuid: Order UUID to delete
    """
    api = _get_api()
    data = api.delete_order(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_client_return(uuid: str, tariff_code: int) -> str:
    """Create a client return for an order.

    Args:
        uuid: Order UUID
        tariff_code: Tariff code for return delivery (e.g. 136)
    """
    api = _get_api()
    data = api.client_return(uuid, tariff_code)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_order_refusal(uuid: str) -> str:
    """Refuse (reject) an order.

    Args:
        uuid: Order UUID to refuse
    """
    api = _get_api()
    data = api.order_refusal(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_order_intakes(order_uuid: str) -> str:
    """Get courier intakes (pickups) for an order.

    Args:
        order_uuid: Order UUID
    """
    api = _get_api()
    data = api.get_order_intakes(order_uuid)
    return json.dumps(data, ensure_ascii=False)


# ── Courier Intakes ────────────────────────────────────────────────


@mcp.tool()
def cdek_create_intake(
    cdek_number: str = "",
    order_uuid: str = "",
    intake_date: str = "",
    intake_time_from: str = "09:00",
    intake_time_to: str = "18:00",
    comment: str = "",
    name: str = "",
) -> str:
    """Create a courier intake request (заявка на вызов курьера).

    Args:
        cdek_number: CDEK order number
        order_uuid: Order UUID (alternative to cdek_number)
        intake_date: Pickup date YYYY-MM-DD (required)
        intake_time_from: Pickup time from HH:MM (default 09:00)
        intake_time_to: Pickup time to HH:MM (default 18:00)
        comment: Comment for the courier
        name: Contact name for the courier
    """
    if not intake_date:
        raise RuntimeError("intake_date is required (YYYY-MM-DD)")
    if not cdek_number and not order_uuid:
        raise RuntimeError("Either cdek_number or order_uuid is required")
    api = _get_api()
    payload: dict = {
        "intake_date": intake_date,
        "intake_time_from": intake_time_from,
        "intake_time_to": intake_time_to,
    }
    if cdek_number:
        payload["cdek_number"] = cdek_number
    if order_uuid:
        payload["order_uuid"] = order_uuid
    if comment:
        payload["comment"] = comment
    if name:
        payload["name"] = name
    data = api.create_intake(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_update_intake(uuid: str, status_code: str) -> str:
    """Update intake request status.

    Args:
        uuid: Intake request UUID
        status_code: New status code
    """
    api = _get_api()
    data = api.update_intake(uuid, status_code)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_get_intake(uuid: str) -> str:
    """Get intake request info by UUID.

    Args:
        uuid: Intake request UUID
    """
    api = _get_api()
    data = api.get_intake(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_delete_intake(uuid: str) -> str:
    """Delete an intake request.

    Args:
        uuid: Intake request UUID
    """
    api = _get_api()
    data = api.delete_intake(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_intake_available_days(city: str, date: str = "") -> str:
    """Get available days for courier intake in a city.

    Args:
        city: City name (e.g. "Москва")
        date: Optional date filter YYYY-MM-DD
    """
    api = _get_api()
    city_code = api.find_city_code(city)
    data = api.get_intake_available_days(city_code, date)
    return json.dumps(data, ensure_ascii=False)


# ── Delivery ───────────────────────────────────────────────────────


@mcp.tool()
def cdek_create_delivery(
    cdek_number: str = "",
    order_uuid: str = "",
    date: str = "",
    time_from: str = "",
    time_to: str = "",
    comment: str = "",
    delivery_point: str = "",
) -> str:
    """Register a delivery agreement (договорённость о доставке).

    Args:
        cdek_number: CDEK order number
        order_uuid: Order UUID (alternative to cdek_number)
        date: Delivery date YYYY-MM-DD (required)
        time_from: Delivery time from HH:MM
        time_to: Delivery time to HH:MM
        comment: Comment for delivery
        delivery_point: Delivery point code
    """
    if not date:
        raise RuntimeError("date is required (YYYY-MM-DD)")
    api = _get_api()
    payload: dict = {"date": date}
    if cdek_number:
        payload["cdek_number"] = cdek_number
    if order_uuid:
        payload["order_uuid"] = order_uuid
    if time_from:
        payload["time_from"] = time_from
    if time_to:
        payload["time_to"] = time_to
    if comment:
        payload["comment"] = comment
    if delivery_point:
        payload["delivery_point"] = delivery_point
    data = api.create_delivery(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_get_delivery(uuid: str) -> str:
    """Get delivery info by UUID.

    Args:
        uuid: Delivery UUID
    """
    api = _get_api()
    data = api.get_delivery(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_delivery_intervals(cdek_number: str = "", order_uuid: str = "") -> str:
    """Get delivery intervals for an order.

    Args:
        cdek_number: CDEK order number
        order_uuid: Order UUID
    """
    if not cdek_number and not order_uuid:
        raise RuntimeError("Either cdek_number or order_uuid is required")
    api = _get_api()
    data = api.get_delivery_intervals(cdek_number, order_uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_estimated_intervals(
    from_city: str = "",
    to_city: str = "",
    tariff_code: int = 136,
    date_time: str = "",
    shipment_point: str = "",
) -> str:
    """Get estimated delivery intervals before creating an order.

    Args:
        from_city: Sender city name (e.g. "Москва")
        to_city: Recipient city name (required)
        tariff_code: CDEK tariff code (default 136)
        date_time: Date-time ISO format
        shipment_point: Shipment point code
    """
    if not to_city:
        raise RuntimeError("to_city is required")
    api = _get_api()
    to_code = api.find_city_code(to_city)
    payload: dict = {"to_location": {"code": to_code}, "tariff_code": tariff_code}
    if from_city:
        payload["from_location"] = {"code": api.find_city_code(from_city)}
    if shipment_point:
        payload["shipment_point"] = shipment_point
    if date_time:
        payload["date_time"] = date_time
    data = api.get_estimated_intervals(payload)
    return json.dumps(data, ensure_ascii=False)


# ── Webhooks ───────────────────────────────────────────────────────


@mcp.tool()
def cdek_create_webhook(type: str, url: str) -> str:
    """Create a webhook subscription.

    Args:
        type: Webhook type — ORDER_STATUS, PRINT_FORM, DOWNLOAD_PHOTO, etc.
        url: URL to receive webhook events
    """
    api = _get_api()
    data = api.create_webhook(type, url)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_list_webhooks() -> str:
    """List all webhook subscriptions."""
    api = _get_api()
    data = api.list_webhooks()
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_get_webhook(uuid: str) -> str:
    """Get webhook subscription by UUID.

    Args:
        uuid: Webhook subscription UUID
    """
    api = _get_api()
    data = api.get_webhook(uuid)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_delete_webhook(uuid: str) -> str:
    """Delete a webhook subscription.

    Args:
        uuid: Webhook subscription UUID
    """
    api = _get_api()
    data = api.delete_webhook(uuid)
    return json.dumps(data, ensure_ascii=False)


# ── Checks ─────────────────────────────────────────────────────────


@mcp.tool()
def cdek_checks(order_uuid: str = "", cdek_number: str = "", date: str = "") -> str:
    """Get check/receipt info for a CDEK order.

    Args:
        order_uuid: Order UUID
        cdek_number: CDEK tracking number
        date: Date in YYYY-MM-DD format
    """
    api = _get_api()
    data = api.get_checks(order_uuid=order_uuid, cdek_number=cdek_number, date=date)
    return json.dumps(data, ensure_ascii=False)


# ── Passport ───────────────────────────────────────────────────────


@mcp.tool()
def cdek_passport(cdek_number: str = "", order_uuid: str = "", client: str = "") -> str:
    """Get passport data associated with a CDEK order.

    Args:
        cdek_number: CDEK tracking number
        order_uuid: Order UUID
        client: Client identifier
    """
    api = _get_api()
    data = api.get_passport(cdek_number=cdek_number, order_uuid=order_uuid, client=client)
    return json.dumps(data, ensure_ascii=False)


# ── Photo Documents ────────────────────────────────────────────────


@mcp.tool()
def cdek_request_photos(period_begin: str = "", period_end: str = "", cdek_numbers: str = "") -> str:
    """Request photo documents for orders.

    Args:
        period_begin: Start date (YYYY-MM-DD)
        period_end: End date (YYYY-MM-DD)
        cdek_numbers: Comma-separated CDEK numbers (e.g. "1234567890,9876543210")
    """
    payload: dict = {}
    if period_begin:
        payload["period_begin"] = period_begin
    if period_end:
        payload["period_end"] = period_end
    if cdek_numbers:
        payload["orders"] = [{"cdek_number": n.strip()} for n in cdek_numbers.split(",")]
    api = _get_api()
    data = api.request_photo_documents(payload)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_download_photos(uuid: str, output_path: str) -> str:
    """Download photo documents archive (zip) by UUID.

    Args:
        uuid: Photo document request UUID
        output_path: Absolute path to save the zip archive
    """
    api = _get_api()
    content = api.download_photo_archive(uuid)
    with open(output_path, "wb") as f:
        f.write(content)
    return json.dumps({"path": os.path.abspath(output_path), "uuid": uuid, "size": len(content)}, ensure_ascii=False)


# ── Prealert ───────────────────────────────────────────────────────


@mcp.tool()
def cdek_create_prealert(planned_date: str, shipment_point: str, cdek_numbers: str) -> str:
    """Register a prealert for upcoming shipments.

    Args:
        planned_date: Planned date (YYYY-MM-DD)
        shipment_point: Shipment point code (e.g. "MSK005")
        cdek_numbers: Comma-separated CDEK numbers
    """
    orders = [{"cdek_number": n.strip()} for n in cdek_numbers.split(",")]
    api = _get_api()
    data = api.create_prealert(planned_date, shipment_point, orders)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def cdek_get_prealert(uuid: str) -> str:
    """Get prealert info by UUID.

    Args:
        uuid: Prealert UUID
    """
    api = _get_api()
    data = api.get_prealert(uuid)
    return json.dumps(data, ensure_ascii=False)


# ── Reverse Availability ──────────────────────────────────────────


@mcp.tool()
def cdek_reverse_availability(
    tariff_code: int,
    from_city: str = "",
    to_city: str = "",
    shipment_point: str = "",
    delivery_point: str = "",
) -> str:
    """Check reverse delivery availability.

    Args:
        tariff_code: CDEK tariff code (e.g. 136)
        from_city: Sender city name
        to_city: Recipient city name
        shipment_point: Shipment point code
        delivery_point: Delivery point code
    """
    api = _get_api()
    payload: dict = {"tariff_code": tariff_code}
    if from_city:
        payload["from_location"] = {"code": api.find_city_code(from_city)}
    if to_city:
        payload["to_location"] = {"code": api.find_city_code(to_city)}
    if shipment_point:
        payload["shipment_point"] = shipment_point
    if delivery_point:
        payload["delivery_point"] = delivery_point
    data = api.check_reverse_availability(payload)
    return json.dumps(data, ensure_ascii=False)


# ── Registries ─────────────────────────────────────────────────────


@mcp.tool()
def cdek_registries(date: str) -> str:
    """Get registries info for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
    """
    api = _get_api()
    data = api.get_registries(date)
    return json.dumps(data, ensure_ascii=False)


# ── International Restrictions ─────────────────────────────────────


@mcp.tool()
def cdek_international_restrictions(tariff_code: int = 0, from_city: str = "", to_city: str = "") -> str:
    """Check international package restrictions.

    Args:
        tariff_code: CDEK tariff code (0 to omit)
        from_city: Origin city name
        to_city: Destination city name
    """
    api = _get_api()
    payload: dict = {}
    if tariff_code:
        payload["tariff_code"] = tariff_code
    if from_city:
        payload["from_location"] = {"code": api.find_city_code(from_city)}
    if to_city:
        payload["to_location"] = {"code": api.find_city_code(to_city)}
    data = api.get_international_restrictions(payload)
    return json.dumps(data, ensure_ascii=False)


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
