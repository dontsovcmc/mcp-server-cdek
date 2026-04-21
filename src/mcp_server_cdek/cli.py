"""CLI interface for CDEK tools.

Usage: mcp-server-cdek <command> [options]
Without arguments starts MCP server (stdio transport).
"""

import argparse
import sys

from . import __version__
from . import server


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="mcp-server-cdek",
        description="СДЭК: MCP-сервер и CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command")

    # create-order
    p_order = sub.add_parser("create-order", help="Создать заказ на доставку")
    p_order.add_argument("--direction", required=True, choices=["from_me", "to_me"],
                         help="Направление: from_me (от меня) или to_me (ко мне)")
    p_order.add_argument("--name", required=True, help="ФИО получателя/отправителя")
    p_order.add_argument("--phone", required=True, help="Телефон")
    p_order.add_argument("--pvz", default="", help="Код ПВЗ или адрес для поиска")
    p_order.add_argument("--address", default="", help="Адрес доставки до двери")
    p_order.add_argument("--email", default="", help="Email получателя")
    p_order.add_argument("--product-name", default="", help="Название товара")
    p_order.add_argument("--weight", type=float, default=0, help="Вес единицы в кг")
    p_order.add_argument("--height", type=int, default=0, help="Высота в см")
    p_order.add_argument("--width", type=int, default=0, help="Ширина в см")
    p_order.add_argument("--length", type=int, default=0, help="Длина в см")
    p_order.add_argument("--quantity", type=int, default=1, help="Количество")
    p_order.add_argument("--price", type=float, default=0, help="Объявленная стоимость")

    # track
    p_track = sub.add_parser("track", help="Отследить заказ по номеру СДЭК")
    p_track.add_argument("cdek_number", type=int, help="Номер отслеживания СДЭК")

    # barcode
    p_barcode = sub.add_parser("barcode", help="Скачать штрихкод (PDF)")
    p_barcode.add_argument("cdek_number", type=int, help="Номер СДЭК")
    p_barcode.add_argument("--output", required=True, help="Путь для сохранения PDF")

    # label
    p_label = sub.add_parser("label", help="Скачать этикетку (PDF)")
    p_label.add_argument("cdek_number", type=int, help="Номер СДЭК")
    p_label.add_argument("--output", required=True, help="Путь для сохранения PDF")
    p_label.add_argument("--format", default="A6", choices=["A4", "A5", "A6", "A7"],
                         help="Формат: A4 (4 шт), A5 (2 шт), A6 (~70x120мм, по умолчанию), A7 (маленькая)")

    # waybill
    p_waybill = sub.add_parser("waybill", help="Скачать накладную (PDF)")
    p_waybill.add_argument("cdek_number", type=int, help="Номер СДЭК")
    p_waybill.add_argument("--output", required=True, help="Путь для сохранения PDF")

    # delivery-points
    p_pvz = sub.add_parser("delivery-points", help="Поиск ПВЗ в городе")
    p_pvz.add_argument("city", help="Название города")
    p_pvz.add_argument("--search", default="", help="Подстрока адреса для фильтрации")

    # cities
    p_cities = sub.add_parser("cities", help="Поиск городов СДЭК")
    p_cities.add_argument("city", help="Название или часть названия города")

    # goods
    p_goods = sub.add_parser("goods", help="Справочник товаров")
    goods_sub = p_goods.add_subparsers(dest="goods_command")
    goods_sub.add_parser("list", help="Список товаров")
    p_goods_add = goods_sub.add_parser("add", help="Добавить товар")
    p_goods_add.add_argument("--name", required=True, help="Название товара")
    p_goods_add.add_argument("--weight", type=float, required=True, help="Вес в кг")
    p_goods_add.add_argument("--height", type=int, required=True, help="Высота в см")
    p_goods_add.add_argument("--width", type=int, required=True, help="Ширина в см")
    p_goods_add.add_argument("--length", type=int, required=True, help="Длина в см")
    p_goods_add.add_argument("--price", type=float, default=100.0, help="Стоимость")
    p_goods_remove = goods_sub.add_parser("remove", help="Удалить товар")
    p_goods_remove.add_argument("--name", required=True, help="Название товара")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "create-order": lambda: server.cdek_create_order(
            direction=args.direction,
            recipient_name=args.name,
            recipient_phone=args.phone,
            pvz=args.pvz,
            address=args.address,
            recipient_email=args.email,
            product_name=args.product_name,
            weight=args.weight,
            height=args.height,
            width=args.width,
            length=args.length,
            quantity=args.quantity,
            price=args.price,
        ),
        "track": lambda: server.cdek_track(args.cdek_number),
        "barcode": lambda: server.cdek_barcode(args.cdek_number, args.output),
        "label": lambda: server.cdek_label(args.cdek_number, args.output, args.format),
        "waybill": lambda: server.cdek_waybill(args.cdek_number, args.output),
        "delivery-points": lambda: server.cdek_delivery_points(args.city, args.search),
        "cities": lambda: server.cdek_cities(args.city),
    }

    if args.command == "goods":
        if args.goods_command == "list":
            handler = lambda: server.goods_list()
        elif args.goods_command == "add":
            handler = lambda: server.goods_add(
                args.name, args.weight, args.height, args.width, args.length, args.price,
            )
        elif args.goods_command == "remove":
            handler = lambda: server.goods_remove(args.name)
        else:
            p_goods.print_help()
            sys.exit(1)
    else:
        handler = handlers[args.command]

    print(handler())
