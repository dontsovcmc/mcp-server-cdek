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

    # regions
    p_regions = sub.add_parser("regions", help="Поиск регионов СДЭК")
    p_regions.add_argument("--country-codes", default="", help="Коды стран (например RU)")
    p_regions.add_argument("--size", type=int, default=5, help="Количество результатов")

    # postalcodes
    p_postalcodes = sub.add_parser("postalcodes", help="Почтовые индексы по коду города")
    p_postalcodes.add_argument("city_code", type=int, help="Код города СДЭК")

    # coordinates
    p_coords = sub.add_parser("coordinates", help="Поиск по координатам")
    p_coords.add_argument("latitude", type=float, help="Широта")
    p_coords.add_argument("longitude", type=float, help="Долгота")

    # suggest-cities
    p_suggest = sub.add_parser("suggest-cities", help="Подсказки городов (автокомплит)")
    p_suggest.add_argument("name", help="Название или начало названия города")
    p_suggest.add_argument("--country-code", default="", help="Код страны (например RU)")

    # all-tariffs
    p_alltariffs = sub.add_parser("all-tariffs", help="Список всех тарифов СДЭК")
    p_alltariffs.add_argument("--lang", default="rus", help="Язык: rus или eng")

    # calculate-tariff
    p_calctariff = sub.add_parser("calculate-tariff", help="Расчёт стоимости по тарифу")
    p_calctariff.add_argument("tariff_code", type=int, help="Код тарифа")
    p_calctariff.add_argument("--from", dest="from_city", required=True, help="Город отправления")
    p_calctariff.add_argument("--to", dest="to_city", required=True, help="Город назначения")
    p_calctariff.add_argument("--weight", type=float, required=True, help="Вес в кг")
    p_calctariff.add_argument("--length", type=int, default=10, help="Длина в см")
    p_calctariff.add_argument("--width", type=int, default=10, help="Ширина в см")
    p_calctariff.add_argument("--height", type=int, default=10, help="Высота в см")

    # calculate-tarifflist
    p_calclist = sub.add_parser("calculate-tarifflist", help="Расчёт по всем тарифам")
    p_calclist.add_argument("--from", dest="from_city", required=True, help="Город отправления")
    p_calclist.add_argument("--to", dest="to_city", required=True, help="Город назначения")
    p_calclist.add_argument("--weight", type=float, required=True, help="Вес в кг")
    p_calclist.add_argument("--length", type=int, default=10, help="Длина в см")
    p_calclist.add_argument("--width", type=int, default=10, help="Ширина в см")
    p_calclist.add_argument("--height", type=int, default=10, help="Высота в см")

    # calculate-tariff-service
    p_calcservice = sub.add_parser("calculate-tariff-service", help="Расчёт по тарифам с услугами")
    p_calcservice.add_argument("--from", dest="from_city", required=True, help="Город отправления")
    p_calcservice.add_argument("--to", dest="to_city", required=True, help="Город назначения")
    p_calcservice.add_argument("--weight", type=float, required=True, help="Вес в кг")
    p_calcservice.add_argument("--length", type=int, default=10, help="Длина в см")
    p_calcservice.add_argument("--width", type=int, default=10, help="Ширина в см")
    p_calcservice.add_argument("--height", type=int, default=10, help="Высота в см")

    # update-order
    p_update = sub.add_parser("update-order", help="Обновить заказ")
    p_update.add_argument("--uuid", default="", help="UUID заказа")
    p_update.add_argument("--cdek-number", default="", help="Номер СДЭК")
    p_update.add_argument("--comment", default="", help="Новый комментарий")
    p_update.add_argument("--delivery-point", default="", help="Новый код ПВЗ")

    # delete-order
    p_delorder = sub.add_parser("delete-order", help="Удалить (отменить) заказ")
    p_delorder.add_argument("uuid", help="UUID заказа")

    # client-return
    p_return = sub.add_parser("client-return", help="Возврат клиента")
    p_return.add_argument("uuid", help="UUID заказа")
    p_return.add_argument("--tariff-code", type=int, required=True, help="Код тарифа возврата")

    # order-refusal
    p_refusal = sub.add_parser("order-refusal", help="Отказ от заказа")
    p_refusal.add_argument("uuid", help="UUID заказа")

    # order-intakes
    p_ointakes = sub.add_parser("order-intakes", help="Заборы по заказу")
    p_ointakes.add_argument("order_uuid", help="UUID заказа")

    # create-intake
    p_create_intake = sub.add_parser("create-intake", help="Создать заявку на вызов курьера")
    p_create_intake.add_argument("--cdek-number", default="", help="Номер заказа СДЭК")
    p_create_intake.add_argument("--order-uuid", default="", help="UUID заказа")
    p_create_intake.add_argument("--date", required=True, help="Дата забора YYYY-MM-DD")
    p_create_intake.add_argument("--time-from", default="09:00", help="Время от (по умолчанию 09:00)")
    p_create_intake.add_argument("--time-to", default="18:00", help="Время до (по умолчанию 18:00)")
    p_create_intake.add_argument("--comment", default="", help="Комментарий")
    p_create_intake.add_argument("--name", default="", help="Контактное лицо")

    # update-intake
    p_update_intake = sub.add_parser("update-intake", help="Обновить статус заявки курьера")
    p_update_intake.add_argument("uuid", help="UUID заявки")
    p_update_intake.add_argument("--status", required=True, help="Код статуса")

    # get-intake
    p_get_intake = sub.add_parser("get-intake", help="Информация о заявке курьера")
    p_get_intake.add_argument("uuid", help="UUID заявки")

    # delete-intake
    p_delete_intake = sub.add_parser("delete-intake", help="Удалить заявку курьера")
    p_delete_intake.add_argument("uuid", help="UUID заявки")

    # intake-available-days
    p_intake_days = sub.add_parser("intake-available-days", help="Доступные дни для вызова курьера")
    p_intake_days.add_argument("city", help="Название города")
    p_intake_days.add_argument("--date", default="", help="Фильтр по дате YYYY-MM-DD")

    # create-delivery
    p_create_delivery = sub.add_parser("create-delivery", help="Договорённость о доставке")
    p_create_delivery.add_argument("--cdek-number", default="", help="Номер заказа СДЭК")
    p_create_delivery.add_argument("--order-uuid", default="", help="UUID заказа")
    p_create_delivery.add_argument("--date", required=True, help="Дата доставки YYYY-MM-DD")
    p_create_delivery.add_argument("--time-from", default="", help="Время от HH:MM")
    p_create_delivery.add_argument("--time-to", default="", help="Время до HH:MM")
    p_create_delivery.add_argument("--comment", default="", help="Комментарий")
    p_create_delivery.add_argument("--delivery-point", default="", help="Код пункта доставки")

    # get-delivery
    p_get_delivery = sub.add_parser("get-delivery", help="Информация о доставке")
    p_get_delivery.add_argument("uuid", help="UUID доставки")

    # delivery-intervals
    p_dintervals = sub.add_parser("delivery-intervals", help="Интервалы доставки")
    p_dintervals.add_argument("--cdek-number", default="", help="Номер заказа СДЭК")
    p_dintervals.add_argument("--order-uuid", default="", help="UUID заказа")

    # estimated-intervals
    p_estimated = sub.add_parser("estimated-intervals", help="Предварительные интервалы доставки")
    p_estimated.add_argument("--from", dest="from_city", default="", help="Город отправителя")
    p_estimated.add_argument("--to", dest="to_city", required=True, help="Город получателя")
    p_estimated.add_argument("--tariff-code", type=int, default=136, help="Код тарифа")
    p_estimated.add_argument("--date-time", default="", help="Дата-время ISO формат")
    p_estimated.add_argument("--shipment-point", default="", help="Код пункта отправки")

    # create-webhook
    p_create_wh = sub.add_parser("create-webhook", help="Создать подписку на вебхук")
    p_create_wh.add_argument("--type", required=True, help="Тип: ORDER_STATUS, PRINT_FORM, и т.д.")
    p_create_wh.add_argument("--url", required=True, help="URL для получения событий")

    # list-webhooks
    sub.add_parser("list-webhooks", help="Список подписок на вебхуки")

    # get-webhook
    p_get_wh = sub.add_parser("get-webhook", help="Получить подписку на вебхук")
    p_get_wh.add_argument("uuid", help="UUID подписки")

    # delete-webhook
    p_del_wh = sub.add_parser("delete-webhook", help="Удалить подписку на вебхук")
    p_del_wh.add_argument("uuid", help="UUID подписки")

    # checks
    p_checks = sub.add_parser("checks", help="Информация о чеках")
    p_checks.add_argument("--order-uuid", default="", help="UUID заказа")
    p_checks.add_argument("--cdek-number", default="", help="Номер СДЭК")
    p_checks.add_argument("--date", default="", help="Дата (YYYY-MM-DD)")

    # passport
    p_passport = sub.add_parser("passport", help="Паспортные данные по заказу")
    p_passport.add_argument("--cdek-number", default="", help="Номер СДЭК")
    p_passport.add_argument("--order-uuid", default="", help="UUID заказа")

    # request-photos
    p_req_photos = sub.add_parser("request-photos", help="Запросить фото-документы")
    p_req_photos.add_argument("--period-begin", default="", help="Дата начала (YYYY-MM-DD)")
    p_req_photos.add_argument("--period-end", default="", help="Дата конца (YYYY-MM-DD)")
    p_req_photos.add_argument("--cdek-numbers", default="", help="Номера СДЭК через запятую")

    # download-photos
    p_dl_photos = sub.add_parser("download-photos", help="Скачать архив фото-документов")
    p_dl_photos.add_argument("uuid", help="UUID запроса фото-документов")
    p_dl_photos.add_argument("--output", required=True, help="Путь для сохранения архива")

    # create-prealert
    p_prealert = sub.add_parser("create-prealert", help="Создать преалерт")
    p_prealert.add_argument("--date", required=True, help="Планируемая дата (YYYY-MM-DD)")
    p_prealert.add_argument("--shipment-point", required=True, help="Код пункта отгрузки")
    p_prealert.add_argument("--cdek-numbers", required=True, help="Номера СДЭК через запятую")

    # get-prealert
    p_get_prealert = sub.add_parser("get-prealert", help="Информация о преалерте")
    p_get_prealert.add_argument("uuid", help="UUID преалерта")

    # reverse-availability
    p_reverse = sub.add_parser("reverse-availability", help="Проверить доступность реверса")
    p_reverse.add_argument("--tariff-code", type=int, required=True, help="Код тарифа")
    p_reverse.add_argument("--from", dest="from_city", default="", help="Город отправления")
    p_reverse.add_argument("--to", dest="to_city", default="", help="Город получения")

    # registries
    p_registries = sub.add_parser("registries", help="Реестры за дату")
    p_registries.add_argument("date", help="Дата (YYYY-MM-DD)")

    # international-restrictions
    p_intl = sub.add_parser("international-restrictions", help="Международные ограничения")
    p_intl.add_argument("--tariff-code", type=int, default=0, help="Код тарифа")
    p_intl.add_argument("--from", dest="from_city", default="", help="Город отправления")
    p_intl.add_argument("--to", dest="to_city", default="", help="Город получения")

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
        "regions": lambda: server.cdek_regions(args.country_codes, args.size),
        "postalcodes": lambda: server.cdek_postalcodes(args.city_code),
        "coordinates": lambda: server.cdek_coordinates(args.latitude, args.longitude),
        "suggest-cities": lambda: server.cdek_suggest_cities(args.name, args.country_code),
        "all-tariffs": lambda: server.cdek_all_tariffs(args.lang),
        "calculate-tariff": lambda: server.cdek_calculate_tariff(
            args.tariff_code, args.from_city, args.to_city, args.weight,
            args.length, args.width, args.height,
        ),
        "calculate-tarifflist": lambda: server.cdek_calculate_tarifflist(
            args.from_city, args.to_city, args.weight, args.length, args.width, args.height,
        ),
        "calculate-tariff-service": lambda: server.cdek_calculate_tariff_and_service(
            args.from_city, args.to_city, args.weight, args.length, args.width, args.height,
        ),
        "update-order": lambda: server.cdek_update_order(
            args.uuid, args.cdek_number, args.comment, args.delivery_point,
        ),
        "delete-order": lambda: server.cdek_delete_order(args.uuid),
        "client-return": lambda: server.cdek_client_return(args.uuid, args.tariff_code),
        "order-refusal": lambda: server.cdek_order_refusal(args.uuid),
        "order-intakes": lambda: server.cdek_order_intakes(args.order_uuid),
        "create-intake": lambda: server.cdek_create_intake(
            cdek_number=args.cdek_number, order_uuid=args.order_uuid,
            intake_date=args.date, intake_time_from=args.time_from,
            intake_time_to=args.time_to, comment=args.comment, name=args.name,
        ),
        "update-intake": lambda: server.cdek_update_intake(args.uuid, args.status),
        "get-intake": lambda: server.cdek_get_intake(args.uuid),
        "delete-intake": lambda: server.cdek_delete_intake(args.uuid),
        "intake-available-days": lambda: server.cdek_intake_available_days(args.city, args.date),
        "create-delivery": lambda: server.cdek_create_delivery(
            cdek_number=args.cdek_number, order_uuid=args.order_uuid,
            date=args.date, time_from=args.time_from, time_to=args.time_to,
            comment=args.comment, delivery_point=args.delivery_point,
        ),
        "get-delivery": lambda: server.cdek_get_delivery(args.uuid),
        "delivery-intervals": lambda: server.cdek_delivery_intervals(
            cdek_number=args.cdek_number, order_uuid=args.order_uuid,
        ),
        "estimated-intervals": lambda: server.cdek_estimated_intervals(
            from_city=args.from_city, to_city=args.to_city, tariff_code=args.tariff_code,
            date_time=args.date_time, shipment_point=args.shipment_point,
        ),
        "create-webhook": lambda: server.cdek_create_webhook(args.type, args.url),
        "list-webhooks": lambda: server.cdek_list_webhooks(),
        "get-webhook": lambda: server.cdek_get_webhook(args.uuid),
        "delete-webhook": lambda: server.cdek_delete_webhook(args.uuid),
        "checks": lambda: server.cdek_checks(
            order_uuid=args.order_uuid, cdek_number=args.cdek_number, date=args.date,
        ),
        "passport": lambda: server.cdek_passport(
            cdek_number=args.cdek_number, order_uuid=args.order_uuid,
        ),
        "request-photos": lambda: server.cdek_request_photos(
            period_begin=args.period_begin, period_end=args.period_end,
            cdek_numbers=args.cdek_numbers,
        ),
        "download-photos": lambda: server.cdek_download_photos(args.uuid, args.output),
        "create-prealert": lambda: server.cdek_create_prealert(
            planned_date=args.date, shipment_point=args.shipment_point,
            cdek_numbers=args.cdek_numbers,
        ),
        "get-prealert": lambda: server.cdek_get_prealert(args.uuid),
        "reverse-availability": lambda: server.cdek_reverse_availability(
            tariff_code=args.tariff_code, from_city=args.from_city, to_city=args.to_city,
        ),
        "registries": lambda: server.cdek_registries(args.date),
        "international-restrictions": lambda: server.cdek_international_restrictions(
            tariff_code=args.tariff_code, from_city=args.from_city, to_city=args.to_city,
        ),
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
