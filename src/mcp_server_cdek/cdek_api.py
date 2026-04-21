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
