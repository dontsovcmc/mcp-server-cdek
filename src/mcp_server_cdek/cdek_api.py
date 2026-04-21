"""Клиент для API СДЭК v2.

Docs: https://api-docs.cdek.ru/29923741.html
"""

import time
import logging
import sys

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

BASE_URL = "https://api.cdek.ru/v2"

TARIFF_WAREHOUSE_WAREHOUSE = 136
TARIFF_WAREHOUSE_DOOR = 137


class CdekAPI:
    """Синхронный клиент API СДЭК v2."""

    def __init__(self, client_id: str, client_secret: str):
        self.session = requests.Session()
        self._auth(client_id, client_secret)

    def _auth(self, client_id: str, client_secret: str):
        resp = self.session.post(
            f"{BASE_URL}/oauth/token",
            params={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        if not resp.ok:
            raise RuntimeError(f"CDEK auth error {resp.status_code}: {resp.text}")
        token = resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        log.info("СДЭК авторизация OK")

    def _get(self, path: str, **kwargs) -> requests.Response:
        resp = self.session.get(f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp

    def _post(self, path: str, payload: dict, **kwargs) -> dict:
        resp = self.session.post(f"{BASE_URL}{path}", json=payload, timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("requests"):
            for req in data["requests"]:
                if "errors" in req:
                    raise RuntimeError(f"CDEK API error: {req['errors']}")
        return data

    def _patch(self, path: str, payload: dict, **kwargs) -> dict:
        resp = self.session.patch(f"{BASE_URL}{path}", json=payload, timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"PATCH {path} -> {resp.status_code}: {resp.text}")
        data = resp.json()
        if data.get("requests"):
            for req in data["requests"]:
                if "errors" in req:
                    raise RuntimeError(f"CDEK API error: {req['errors']}")
        return data

    def _delete(self, path: str, **kwargs) -> dict:
        resp = self.session.delete(f"{BASE_URL}{path}", timeout=30, **kwargs)
        if not resp.ok:
            raise RuntimeError(f"DELETE {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    # --- Заказы ---

    def create_order(self, payload: dict) -> str:
        """Создать заказ, вернуть UUID."""
        data = self._post("/orders", payload)
        uuid = data["entity"]["uuid"]
        log.info("Заказ отправлен, uuid=%s", uuid)
        return uuid

    def get_order(self, uuid: str) -> dict:
        """Получить информацию о заказе по UUID."""
        return self._get(f"/orders/{uuid}").json()

    def poll_order(self, uuid: str, timeout: float = 15.0) -> dict:
        """Дождаться создания заказа, вернуть данные заказа с cdek_number."""
        start = time.time()
        order = None
        while time.time() - start < timeout:
            order = self.get_order(uuid)
            statuses = {s["code"] for s in order["entity"]["statuses"]}
            if "ACCEPTED" in statuses and "CREATED" in statuses:
                cdek_number = order["entity"]["cdek_number"]
                log.info("Заказ создан! СДЭК номер: %s", cdek_number)
                return order["entity"]
            time.sleep(2.0)

        messages = []
        if order:
            for r in order.get("requests", []):
                for err in r.get("errors", []):
                    messages.append(err.get("message", ""))
        raise RuntimeError(f"Заказ не создался uuid={uuid}. Ошибки: {messages}")

    # --- Штрихкод ---

    def start_barcode(self, cdek_number: int) -> str:
        """Запросить генерацию штрихкода, вернуть UUID задачи."""
        data = self._post("/print/barcodes", {
            "orders": [{"cdek_number": int(cdek_number)}],
            "format": "A7",
        })
        return data["entity"]["uuid"]

    def get_barcode_url(self, uuid: str, timeout: float = 10.0) -> str:
        """Дождаться генерации штрихкода и вернуть URL на PDF."""
        start = time.time()
        while time.time() - start < timeout:
            resp = self._get(f"/print/barcodes/{uuid}")
            entity = resp.json()["entity"]
            if entity.get("url"):
                return entity["url"]
            last_status = entity["statuses"][-1]["code"] if entity.get("statuses") else ""
            if last_status == "INVALID":
                raise RuntimeError(f"Ошибка генерации штрихкода: {entity['statuses']}")
            time.sleep(1.0)
            log.info("Штрихкод ещё не готов, ждём...")
        raise RuntimeError(f"Штрихкод не готов за {timeout} секунд")

    def download_barcode(self, cdek_number: int) -> bytes:
        """Сгенерировать и скачать PDF штрихкода."""
        barcode_uuid = self.start_barcode(cdek_number)
        url = self.get_barcode_url(barcode_uuid)
        resp = self.session.get(url, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Ошибка скачивания штрихкода: {resp.status_code}")
        return resp.content

    # --- Этикетка ---

    def start_label(self, cdek_number: int, fmt: str = "A6") -> str:
        """Запросить генерацию этикетки, вернуть UUID задачи."""
        data = self._post("/print/barcodes", {
            "orders": [{"cdek_number": int(cdek_number)}],
            "format": fmt,
        })
        return data["entity"]["uuid"]

    def download_label(self, cdek_number: int, fmt: str = "A6") -> bytes:
        """Сгенерировать и скачать PDF этикетки."""
        label_uuid = self.start_label(cdek_number, fmt)
        url = self.get_barcode_url(label_uuid)
        resp = self.session.get(url, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Ошибка скачивания этикетки: {resp.status_code}")
        return resp.content

    # --- Накладная ---

    def start_waybill(self, cdek_number: int) -> str:
        """Запросить генерацию накладной, вернуть UUID задачи."""
        data = self._post("/print/orders", {
            "orders": [{"cdek_number": int(cdek_number)}],
            "format": "A4",
        })
        return data["entity"]["uuid"]

    def get_waybill_url(self, uuid: str, timeout: float = 10.0) -> str:
        """Дождаться генерации накладной и вернуть URL на PDF."""
        start = time.time()
        while time.time() - start < timeout:
            resp = self._get(f"/print/orders/{uuid}")
            entity = resp.json()["entity"]
            if entity.get("url"):
                return entity["url"]
            last_status = entity["statuses"][-1]["code"] if entity.get("statuses") else ""
            if last_status == "INVALID":
                raise RuntimeError(f"Ошибка генерации накладной: {entity['statuses']}")
            time.sleep(1.0)
            log.info("Накладная ещё не готова, ждём...")
        raise RuntimeError(f"Накладная не готова за {timeout} секунд")

    def download_waybill(self, cdek_number: int) -> bytes:
        """Сгенерировать и скачать PDF накладной."""
        waybill_uuid = self.start_waybill(cdek_number)
        url = self.get_waybill_url(waybill_uuid)
        resp = self.session.get(url, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Ошибка скачивания накладной: {resp.status_code}")
        return resp.content

    # --- Города и ПВЗ ---

    def find_cities(self, city_name: str, size: int = 5) -> list:
        """Поиск городов по названию."""
        resp = self._get("/location/cities", params={"city": city_name, "size": size})
        return resp.json()

    def find_city_code(self, city_name: str) -> int:
        """Найти код города по названию."""
        cities = self.find_cities(city_name)
        if not cities:
            raise RuntimeError(f"Город «{city_name}» не найден в СДЭК")
        code = cities[0]["code"]
        log.info("Город «%s» → code=%s", city_name, code)
        return code

    def find_delivery_points(self, city_code: int) -> list:
        """Получить ПВЗ по коду города."""
        resp = self._get("/deliverypoints", params={"city_code": city_code})
        return resp.json()

    # --- Трекинг ---

    def get_order_by_cdek_number(self, cdek_number: int) -> dict:
        """Получить информацию о заказе по номеру СДЭК."""
        resp = self._get("/orders", params={"cdek_number": cdek_number})
        return resp.json()

    def get_order_by_im_number(self, im_number: str) -> dict:
        """Получить информацию о заказе по номеру ИМ."""
        resp = self._get("/orders", params={"im_number": im_number})
        return resp.json()

    def update_order(self, payload: dict) -> dict:
        """Обновить заказ (PATCH)."""
        return self._patch("/orders", payload)

    def delete_order(self, uuid: str) -> dict:
        """Удалить заказ по UUID."""
        return self._delete(f"/orders/{uuid}")

    def client_return(self, uuid: str, tariff_code: int) -> dict:
        """Создать возврат клиента."""
        return self._post(f"/orders/{uuid}/clientReturn", {"tariff_code": tariff_code})

    def order_refusal(self, uuid: str) -> dict:
        """Отказ от заказа."""
        return self._post(f"/orders/{uuid}/refusal", {})

    def get_order_intakes(self, order_uuid: str) -> dict:
        """Получить заборы по заказу."""
        resp = self._get(f"/orders/{order_uuid}/intakes")
        return resp.json()

    # --- Регионы и локации ---

    def find_regions(self, country_codes: str | None = None, size: int = 5, page: int = 0) -> list:
        """Поиск регионов."""
        params: dict = {"size": size, "page": page}
        if country_codes:
            params["country_codes"] = country_codes
        resp = self._get("/location/regions", params=params)
        return resp.json()

    def find_postalcodes(self, city_code: int) -> list:
        """Получить почтовые индексы по коду города."""
        resp = self._get("/location/postalcodes", params={"city_code": city_code})
        return resp.json()

    def find_by_coordinates(self, latitude: float, longitude: float) -> list:
        """Поиск населённого пункта по координатам."""
        resp = self._get("/location/coordinates", params={"latitude": latitude, "longitude": longitude})
        return resp.json()

    def suggest_cities(self, name: str, country_code: str = "") -> list:
        """Подсказки по городам (автокомплит)."""
        params: dict = {"name": name}
        if country_code:
            params["country_code"] = country_code
        resp = self._get("/location/suggest/cities", params=params)
        return resp.json()

    # --- Калькулятор ---

    def get_all_tariffs(self, lang: str = "rus") -> list:
        """Получить спи��ок всех тарифов."""
        resp = self._get("/calculator/alltariffs", params={"lang": lang})
        return resp.json()

    def calculate_tariff(self, payload: dict) -> dict:
        """Рассчитать стоимость по конкретному тарифу."""
        return self._post("/calculator/tariff", payload)

    def calculate_tarifflist(self, payload: dict) -> dict:
        """Рассчитать стоимость по всем доступным тарифам."""
        return self._post("/calculator/tarifflist", payload)

    def calculate_tariff_and_service(self, payload: dict) -> dict:
        """Рассчитать стоимость по всем тарифам с доп. услугами."""
        return self._post("/calculator/tariffAndService", payload)

    # --- Вызов курьера ---

    def create_intake(self, payload: dict) -> dict:
        """Создать заявку на вызов курьера."""
        return self._post("/intakes", payload)

    def update_intake(self, uuid: str, status_code: str) -> dict:
        """Обновить статус заявки на вызов курьера."""
        return self._patch("/intakes", {"uuid": uuid, "status": {"code": status_code}})

    def get_intake(self, uuid: str) -> dict:
        """Получить и��формацию о заявке на вызов курьера."""
        return self._get(f"/intakes/{uuid}").json()

    def delete_intake(self, uuid: str) -> dict:
        """Удалить заявку на вызов курьера."""
        return self._delete(f"/intakes/{uuid}")

    def get_intake_available_days(self, city_code: int, date: str = "") -> dict:
        """Получить доступные дни для вызова курьера."""
        payload: dict = {"from_location": {"city_code": city_code}}
        if date:
            payload["date"] = date
        return self._post("/intakes/availableDays", payload)

    # --- Доставка ---

    def create_delivery(self, payload: dict) -> dict:
        """Зарегистрировать договорённость о доставке."""
        return self._post("/delivery", payload)

    def get_delivery(self, uuid: str) -> dict:
        """Получить информацию о доставке."""
        return self._get(f"/delivery/{uuid}").json()

    def get_delivery_intervals(self, cdek_number: str = "", order_uuid: str = "") -> dict:
        """Получить интервалы доставки для заказа."""
        params = {}
        if cdek_number:
            params["cdek_number"] = cdek_number
        if order_uuid:
            params["order_uuid"] = order_uuid
        return self._get("/delivery/intervals", params=params).json()

    def get_estimated_intervals(self, payload: dict) -> dict:
        """Получить предварительные интервалы доставки до создания заказа."""
        return self._post("/delivery/estimatedIntervals", payload)

    # --- Вебхуки ---

    def create_webhook(self, webhook_type: str, url: str) -> dict:
        """Создать подписку на вебхук."""
        return self._post("/webhooks", {"type": webhook_type, "url": url})

    def list_webhooks(self) -> dict:
        """Получить список подписок на вебхуки."""
        return self._get("/webhooks").json()

    def get_webhook(self, uuid: str) -> dict:
        """Получить подписку на вебхук по UUID."""
        return self._get(f"/webhooks/{uuid}").json()

    def delete_webhook(self, uuid: str) -> dict:
        """Удалить подписку на вебхук."""
        return self._delete(f"/webhooks/{uuid}")

    # --- Чеки ---

    def get_checks(self, order_uuid: str = "", cdek_number: str = "", date: str = "") -> dict:
        """Получить информацию о чеках."""
        params = {}
        if order_uuid:
            params["order_uuid"] = order_uuid
        if cdek_number:
            params["cdek_number"] = cdek_number
        if date:
            params["date"] = date
        return self._get("/check", params=params).json()

    # --- Паспортные данные ---

    def get_passport(self, cdek_number: str = "", order_uuid: str = "", client: str = "") -> dict:
        """Получить паспортные данные по заказу."""
        params = {}
        if cdek_number:
            params["cdek_number"] = cdek_number
        if order_uuid:
            params["order_uuid"] = order_uuid
        if client:
            params["client"] = client
        return self._get("/passport", params=params).json()

    # --- Фото-документы ---

    def request_photo_documents(self, payload: dict) -> dict:
        """Запросить фото-документы."""
        return self._post("/photoDocument", payload)

    def download_photo_archive(self, uuid: str) -> bytes:
        """Скачать архив фото-документов по UUID."""
        resp = self.session.get(f"{BASE_URL}/photoDocument/{uuid}", timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Ошибка скачивания фото-архива: {resp.status_code}: {resp.text}")
        return resp.content

    # --- Преалерт ---

    def create_prealert(self, planned_date: str, shipment_point: str, orders: list) -> dict:
        """Создать преалерт."""
        return self._post("/prealert", {
            "planned_date": planned_date,
            "shipment_point": shipment_point,
            "orders": orders,
        })

    def get_prealert(self, uuid: str) -> dict:
        """Получить информацию о преалерте."""
        return self._get(f"/prealert/{uuid}").json()

    # --- Обратная доставка ---

    def check_reverse_availability(self, payload: dict) -> dict:
        """Проверить доступность обратной доставки."""
        return self._post("/reverse/availability", payload)

    # --- Реестры ---

    def get_registries(self, date: str) -> dict:
        """Получить информацию о реестрах за дату."""
        return self._get("/registries", params={"date": date}).json()

    # --- Международные ограничения ---

    def get_international_restrictions(self, payload: dict) -> dict:
        """Получить международные ограничения на посылки."""
        return self._post("/international/package/restrictions", payload)
