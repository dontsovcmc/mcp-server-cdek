"""Pydantic-модели для API СДЭК v2.

Использование:
    from mcp_server_cdek.models import OrderRequest, Location, Phone
"""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Base ───────────────────────────────────────────────────────────


class CdekBaseModel(BaseModel):
    """Базовая модель. extra='allow' сохраняет недокументированные поля API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


# ── Shared / Primitive ─────────────────────────────────────────────


class Phone(CdekBaseModel):
    """Телефон контакта."""

    number: str
    additional: Optional[str] = None


class Money(CdekBaseModel):
    """Денежная сумма (оплата, сбор)."""

    value: float
    vat_sum: Optional[float] = None
    vat_rate: Optional[int] = None


class Location(CdekBaseModel):
    """Населённый пункт / адрес."""

    code: Optional[int] = None
    fias_guid: Optional[str] = None
    postal_code: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    region_code: Optional[int] = None
    sub_region: Optional[str] = None
    city: Optional[str] = None
    city_code: Optional[int] = None
    address: Optional[str] = None


class Threshold(CdekBaseModel):
    """Порог доп. сбора за доставку (ДСД)."""

    threshold: int
    sum: float
    vat_sum: Optional[float] = None
    vat_rate: Optional[int] = None


class Error(CdekBaseModel):
    """Ошибка API."""

    code: str
    message: str


class Service(CdekBaseModel):
    """Дополнительная услуга."""

    code: str
    parameter: Optional[str] = None


# ── Building Blocks ────────────────────────────────────────────────


class Contact(CdekBaseModel):
    """Контакт (отправитель / получатель)."""

    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phones: list[Phone] = []
    contragent_type: Optional[str] = None
    passport_series: Optional[str] = None
    passport_number: Optional[str] = None
    passport_date_of_issue: Optional[str] = None
    passport_organization: Optional[str] = None
    passport_date_of_birth: Optional[str] = None
    tin: Optional[str] = None
    passport_requirements_satisfied: Optional[bool] = None


class Seller(CdekBaseModel):
    """Реквизиты истинного продавца."""

    name: Optional[str] = None
    inn: Optional[str] = None
    phone: Optional[str] = None
    ownership_form: Optional[int] = None
    address: Optional[str] = None


class Item(CdekBaseModel):
    """Товар в упаковке."""

    name: str
    ware_key: str
    payment: Money
    cost: float
    weight: int  # граммы
    amount: int
    weight_gross: Optional[int] = None
    name_i18n: Optional[str] = None
    brand: Optional[str] = None
    country_code: Optional[str] = None
    material: Optional[int] = None
    wifi_gsm: Optional[bool] = None
    url: Optional[str] = None


class Package(CdekBaseModel):
    """Место (упаковка) в заказе."""

    number: str
    weight: int  # граммы
    length: Optional[int] = None  # см
    width: Optional[int] = None
    height: Optional[int] = None
    comment: Optional[str] = None
    items: Optional[list[Item]] = None


class OrderRef(CdekBaseModel):
    """Ссылка на заказ (для print/prealert)."""

    cdek_number: Optional[Union[int, str]] = None
    order_uuid: Optional[str] = None


# ── Request Models ─────────────────────────────────────────────────


class OrderRequest(CdekBaseModel):
    """Регистрация заказа (POST /v2/orders)."""

    tariff_code: int
    recipient: Contact
    packages: list[Package]
    type: Optional[int] = None
    additional_order_types: Optional[list[int]] = None
    number: Optional[str] = None
    comment: Optional[str] = None
    shipment_point: Optional[str] = None
    delivery_point: Optional[str] = None
    sender: Optional[Contact] = None
    seller: Optional[Seller] = None
    from_location: Optional[Location] = None
    to_location: Optional[Location] = None
    services: Optional[list[Service]] = None
    delivery_recipient_cost: Optional[Money] = None
    delivery_recipient_cost_adv: Optional[list[Threshold]] = None
    print_type: Optional[str] = Field(default=None, alias="print")
    is_client_return: Optional[bool] = None
    has_reverse_order: Optional[bool] = None
    developer_key: Optional[str] = None


class OrderUpdateRequest(CdekBaseModel):
    """Изменение заказа (PATCH /v2/orders)."""

    uuid: Optional[str] = None
    cdek_number: Optional[str] = None
    type: Optional[int] = None
    number: Optional[str] = None
    tariff_code: Optional[int] = None
    comment: Optional[str] = None
    shipment_point: Optional[str] = None
    delivery_point: Optional[str] = None
    sender: Optional[Contact] = None
    seller: Optional[Seller] = None
    recipient: Optional[Contact] = None
    from_location: Optional[Location] = None
    to_location: Optional[Location] = None
    services: Optional[list[Service]] = None
    packages: Optional[list[Package]] = None
    delivery_recipient_cost: Optional[Money] = None

    @model_validator(mode="after")
    def check_identifier(self) -> "OrderUpdateRequest":
        if not self.uuid and not self.cdek_number:
            raise ValueError("Either uuid or cdek_number must be provided")
        return self


class IntakeRequest(CdekBaseModel):
    """Заявка на вызов курьера (POST /v2/intakes)."""

    intake_date: str
    intake_time_from: str = "09:00"
    intake_time_to: str = "18:00"
    cdek_number: Optional[str] = None
    order_uuid: Optional[str] = None
    comment: Optional[str] = None
    name: Optional[str] = None
    weight: Optional[int] = None
    length: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    lunch_time_from: Optional[str] = None
    lunch_time_to: Optional[str] = None
    sender: Optional[Contact] = None
    from_location: Optional[Location] = None

    @model_validator(mode="after")
    def check_identifier(self) -> "IntakeRequest":
        if not self.cdek_number and not self.order_uuid:
            raise ValueError("Either cdek_number or order_uuid must be provided")
        return self


class DeliveryRequest(CdekBaseModel):
    """Договорённость о доставке (POST /v2/delivery)."""

    date: str
    cdek_number: Optional[str] = None
    order_uuid: Optional[str] = None
    time_from: Optional[str] = None
    time_to: Optional[str] = None
    comment: Optional[str] = None
    delivery_point: Optional[str] = None
    to_location: Optional[Location] = None

    @model_validator(mode="after")
    def check_identifier(self) -> "DeliveryRequest":
        if not self.cdek_number and not self.order_uuid:
            raise ValueError("Either cdek_number or order_uuid must be provided")
        return self


class TariffRequest(CdekBaseModel):
    """Расчёт стоимости доставки (POST /v2/calculator/tariff[list])."""

    from_location: Location
    to_location: Location
    packages: list[Package]
    tariff_code: Optional[int] = None
    services: Optional[list[Service]] = None
    additional_order_types: Optional[list[int]] = None
    date: Optional[str] = None
    type: Optional[int] = None
    currency: Optional[str] = None
    lang: Optional[str] = None


class WebhookRequest(CdekBaseModel):
    """Подписка на вебхуки (POST /v2/webhooks)."""

    type: str
    url: str


class PrintRequest(CdekBaseModel):
    """Формирование печатной формы (POST /v2/print/barcodes или /v2/print/orders)."""

    orders: list[OrderRef]
    copy_count: Optional[int] = None
    format: Optional[str] = None
    lang: Optional[str] = None


class PrealertRequest(CdekBaseModel):
    """Регистрация преалерта (POST /v2/prealert)."""

    planned_date: str
    shipment_point: str
    orders: list[OrderRef]


class PhotoDocumentRequest(CdekBaseModel):
    """Запрос фото документов (POST /v2/photoDocument)."""

    period_begin: Optional[str] = None
    period_end: Optional[str] = None
    orders: Optional[list[OrderRef]] = None


# ── Response Models ────────────────────────────────────────────────


class RequestStatus(CdekBaseModel):
    """Статус обработки запроса."""

    request_uuid: Optional[str] = None
    type: Optional[str] = None  # CREATE, UPDATE, DELETE
    date_time: Optional[str] = None
    state: Optional[str] = None  # ACCEPTED, SUCCESSFUL, INVALID
    errors: Optional[list[Error]] = None


class EntityResponse(CdekBaseModel):
    """Стандартный ответ API (entity + requests + related_entities)."""

    entity: Optional[dict] = None
    requests: Optional[list[RequestStatus]] = None
    related_entities: Optional[list] = None


class Status(CdekBaseModel):
    """Статус заказа."""

    code: str
    name: str
    date_time: str
    city: Optional[str] = None


class OrderInfo(CdekBaseModel):
    """Информация о заказе (из GET /v2/orders)."""

    uuid: Optional[str] = None
    cdek_number: Optional[Union[int, str]] = None
    number: Optional[str] = None
    statuses: Optional[list[Status]] = None
    delivery_point: Optional[str] = None
    recipient: Optional[Contact] = None
    sender: Optional[Contact] = None
    packages: Optional[list[Package]] = None
    from_location: Optional[Location] = None
    to_location: Optional[Location] = None


class City(CdekBaseModel):
    """Населённый пункт (из GET /v2/location/cities)."""

    code: int
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None


class Region(CdekBaseModel):
    """Регион (из GET /v2/location/regions)."""

    region: Optional[str] = None
    country_code: Optional[str] = None
    country: Optional[str] = None


class DeliveryPoint(CdekBaseModel):
    """Офис / ПВЗ / постамат (из GET /v2/deliverypoints)."""

    code: str
    name: Optional[str] = None
    location: Optional[Location] = None
    work_time: Optional[str] = None
    type: Optional[str] = None
    phones: Optional[list[Phone]] = None
    email: Optional[str] = None


class TariffResult(CdekBaseModel):
    """Результат расчёта тарифа (из POST /v2/calculator/tariff)."""

    delivery_sum: Optional[float] = None
    period_min: Optional[int] = None
    period_max: Optional[int] = None
    weight_calc: Optional[int] = None
    total_sum: Optional[float] = None
    currency: Optional[str] = None
    services: Optional[list] = None


class Tariff(CdekBaseModel):
    """Тариф (из GET /v2/calculator/alltariffs)."""

    tariff_code: int
    tariff_name: Optional[str] = None
    tariff_description: Optional[str] = None
    delivery_mode: Optional[int] = None
    delivery_sum: Optional[float] = None
    period_min: Optional[int] = None
    period_max: Optional[int] = None


# ── Exports ────────────────────────────────────────────────────────

__all__ = [
    # Base
    "CdekBaseModel",
    # Shared
    "Phone",
    "Money",
    "Location",
    "Threshold",
    "Error",
    "Service",
    # Building blocks
    "Contact",
    "Seller",
    "Item",
    "Package",
    "OrderRef",
    # Requests
    "OrderRequest",
    "OrderUpdateRequest",
    "IntakeRequest",
    "DeliveryRequest",
    "TariffRequest",
    "WebhookRequest",
    "PrintRequest",
    "PrealertRequest",
    "PhotoDocumentRequest",
    # Responses
    "RequestStatus",
    "EntityResponse",
    "Status",
    "OrderInfo",
    "City",
    "Region",
    "DeliveryPoint",
    "TariffResult",
    "Tariff",
]
