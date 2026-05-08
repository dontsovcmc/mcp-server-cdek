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

    number: str = Field(description="Phone number")
    additional: Optional[str] = Field(default=None, description="Extension number")


class Money(CdekBaseModel):
    """Денежная сумма (оплата, сбор)."""

    value: float = Field(description="Amount value")
    vat_sum: Optional[float] = Field(default=None, description="VAT amount")
    vat_rate: Optional[int] = Field(default=None, description="VAT rate percentage")


class Location(CdekBaseModel):
    """Населённый пункт / адрес."""

    code: Optional[int] = Field(default=None, description="CDEK city code")
    fias_guid: Optional[str] = Field(default=None, description="FIAS GUID of the location")
    postal_code: Optional[str] = Field(default=None, description="Postal code")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    country_code: Optional[str] = Field(default=None, description="Country code ISO 3166-1 alpha-2")
    region: Optional[str] = Field(default=None, description="Region name")
    region_code: Optional[int] = Field(default=None, description="Region code")
    sub_region: Optional[str] = Field(default=None, description="Sub-region name")
    city: Optional[str] = Field(default=None, description="City name")
    city_code: Optional[int] = Field(default=None, description="CDEK city code (alias)")
    address: Optional[str] = Field(default=None, description="Full address string")


class Threshold(CdekBaseModel):
    """Порог доп. сбора за доставку (ДСД)."""

    threshold: int = Field(description="Order value threshold in currency units")
    sum: float = Field(description="Additional delivery fee amount")
    vat_sum: Optional[float] = Field(default=None, description="VAT amount")
    vat_rate: Optional[int] = Field(default=None, description="VAT rate percentage")


class Error(CdekBaseModel):
    """Ошибка API."""

    code: str = Field(description="Error code")
    message: str = Field(description="Error message")


class Service(CdekBaseModel):
    """Дополнительная услуга."""

    code: str = Field(description="Service code (e.g. INSURANCE, COURIER_PACKAGE)")
    parameter: Optional[str] = Field(default=None, description="Service parameter value")


# ── Building Blocks ────────────────────────────────────────────────


class Contact(CdekBaseModel):
    """Контакт (отправитель / получатель)."""

    name: str = Field(description="Full name of the contact person")
    company: Optional[str] = Field(default=None, description="Company name")
    email: Optional[str] = Field(default=None, description="Email address")
    phones: list[Phone] = Field(default=[], description="List of phone numbers")
    contragent_type: Optional[str] = Field(default=None, description="Contragent type: SELLER, BUYER, LEGAL_ENTITY")
    passport_series: Optional[str] = Field(default=None, description="Passport series")
    passport_number: Optional[str] = Field(default=None, description="Passport number")
    passport_date_of_issue: Optional[str] = Field(default=None, description="Passport issue date")
    passport_organization: Optional[str] = Field(default=None, description="Passport issuing authority")
    passport_date_of_birth: Optional[str] = Field(default=None, description="Date of birth")
    tin: Optional[str] = Field(default=None, description="Taxpayer identification number (INN)")
    passport_requirements_satisfied: Optional[bool] = Field(default=None, description="Whether passport requirements are met")


class Seller(CdekBaseModel):
    """Реквизиты истинного продавца."""

    name: Optional[str] = Field(default=None, description="Seller name")
    inn: Optional[str] = Field(default=None, description="Seller INN (tax ID)")
    phone: Optional[str] = Field(default=None, description="Seller phone number")
    ownership_form: Optional[int] = Field(default=None, description="Ownership form code")
    address: Optional[str] = Field(default=None, description="Seller legal address")


class Item(CdekBaseModel):
    """Товар в упаковке."""

    name: str = Field(description="Product name")
    ware_key: str = Field(description="Unique item identifier within the package")
    payment: Money = Field(description="Payment amount for the item")
    cost: float = Field(description="Declared value per unit")
    weight: int = Field(description="Weight per unit in grams")
    amount: int = Field(description="Quantity of items")
    weight_gross: Optional[int] = Field(default=None, description="Gross weight in grams")
    name_i18n: Optional[str] = Field(default=None, description="Product name in English")
    brand: Optional[str] = Field(default=None, description="Product brand")
    country_code: Optional[str] = Field(default=None, description="Country of origin ISO 3166-1 alpha-2")
    material: Optional[int] = Field(default=None, description="Material code for customs")
    wifi_gsm: Optional[bool] = Field(default=None, description="Whether item contains WiFi/GSM module")
    url: Optional[str] = Field(default=None, description="Product URL")


class Package(CdekBaseModel):
    """Место (упаковка) в заказе."""

    number: str = Field(description="Package number (unique within the order)")
    weight: int = Field(description="Total package weight in grams")
    length: Optional[int] = Field(default=None, description="Length in cm")
    width: Optional[int] = Field(default=None, description="Width in cm")
    height: Optional[int] = Field(default=None, description="Height in cm")
    comment: Optional[str] = Field(default=None, description="Package comment")
    items: Optional[list[Item]] = Field(default=None, description="List of items in the package")


class OrderRef(CdekBaseModel):
    """Ссылка на заказ (для print/prealert)."""

    cdek_number: Optional[Union[int, str]] = Field(default=None, description="CDEK tracking number")
    order_uuid: Optional[str] = Field(default=None, description="Order UUID in CDEK system")


# ── Request Models ─────────────────────────────────────────────────


class OrderRequest(CdekBaseModel):
    """Регистрация заказа (POST /v2/orders)."""

    tariff_code: int = Field(description="CDEK tariff code (e.g. 136, 137)")
    recipient: Contact = Field(description="Recipient contact information")
    packages: list[Package] = Field(description="List of packages in the order")
    type: Optional[int] = Field(default=None, description="Order type: 1 (online store) or 2 (delivery)")
    additional_order_types: Optional[list[int]] = Field(default=None, description="Additional order type codes")
    number: Optional[str] = Field(default=None, description="Order number in client system")
    comment: Optional[str] = Field(default=None, description="Order comment")
    shipment_point: Optional[str] = Field(default=None, description="Shipment point code (for from-warehouse tariffs)")
    delivery_point: Optional[str] = Field(default=None, description="Delivery point code (for to-warehouse tariffs)")
    sender: Optional[Contact] = Field(default=None, description="Sender contact information")
    seller: Optional[Seller] = Field(default=None, description="True seller details")
    from_location: Optional[Location] = Field(default=None, description="Sender location (for from-door tariffs)")
    to_location: Optional[Location] = Field(default=None, description="Recipient location (for to-door tariffs)")
    services: Optional[list[Service]] = Field(default=None, description="Additional services")
    delivery_recipient_cost: Optional[Money] = Field(default=None, description="Delivery cost charged to recipient")
    delivery_recipient_cost_adv: Optional[list[Threshold]] = Field(default=None, description="Tiered recipient delivery cost thresholds")
    print_type: Optional[str] = Field(default=None, alias="print", description="Print form type: barcode or waybill")
    is_client_return: Optional[bool] = Field(default=None, description="Whether this is a client return order")
    has_reverse_order: Optional[bool] = Field(default=None, description="Whether a reverse order should be created")
    developer_key: Optional[str] = Field(default=None, description="Developer key for partner integrations")


class OrderUpdateRequest(CdekBaseModel):
    """Изменение заказа (PATCH /v2/orders)."""

    uuid: Optional[str] = Field(default=None, description="Order UUID in CDEK system")
    cdek_number: Optional[str] = Field(default=None, description="CDEK tracking number")
    type: Optional[int] = Field(default=None, description="Order type: 1 (online store) or 2 (delivery)")
    number: Optional[str] = Field(default=None, description="Order number in client system")
    tariff_code: Optional[int] = Field(default=None, description="CDEK tariff code")
    comment: Optional[str] = Field(default=None, description="Order comment")
    shipment_point: Optional[str] = Field(default=None, description="Shipment point code")
    delivery_point: Optional[str] = Field(default=None, description="Delivery point code")
    sender: Optional[Contact] = Field(default=None, description="Sender contact information")
    seller: Optional[Seller] = Field(default=None, description="True seller details")
    recipient: Optional[Contact] = Field(default=None, description="Recipient contact information")
    from_location: Optional[Location] = Field(default=None, description="Sender location")
    to_location: Optional[Location] = Field(default=None, description="Recipient location")
    services: Optional[list[Service]] = Field(default=None, description="Additional services")
    packages: Optional[list[Package]] = Field(default=None, description="List of packages")
    delivery_recipient_cost: Optional[Money] = Field(default=None, description="Delivery cost charged to recipient")

    @model_validator(mode="after")
    def check_identifier(self) -> "OrderUpdateRequest":
        if not self.uuid and not self.cdek_number:
            raise ValueError("Either uuid or cdek_number must be provided")
        return self


class IntakeRequest(CdekBaseModel):
    """Заявка на вызов курьера (POST /v2/intakes)."""

    intake_date: str = Field(description="Pickup date YYYY-MM-DD")
    intake_time_from: str = Field(default="09:00", description="Pickup time from HH:MM (not earlier than 09:00)")
    intake_time_to: str = Field(default="18:00", description="Pickup time to HH:MM (not later than 22:00)")
    cdek_number: Optional[str] = Field(default=None, description="CDEK tracking number")
    order_uuid: Optional[str] = Field(default=None, description="Order UUID in CDEK system")
    comment: Optional[str] = Field(default=None, description="Comment for the courier")
    name: Optional[str] = Field(default=None, description="Cargo description")
    weight: Optional[int] = Field(default=None, description="Cargo weight in grams")
    length: Optional[int] = Field(default=None, description="Cargo length in cm")
    width: Optional[int] = Field(default=None, description="Cargo width in cm")
    height: Optional[int] = Field(default=None, description="Cargo height in cm")
    lunch_time_from: Optional[str] = Field(default=None, description="Lunch break start HH:MM")
    lunch_time_to: Optional[str] = Field(default=None, description="Lunch break end HH:MM")
    sender: Optional[Contact] = Field(default=None, description="Sender contact information")
    from_location: Optional[Location] = Field(default=None, description="Pickup location")

    @model_validator(mode="after")
    def check_identifier(self) -> "IntakeRequest":
        if not self.cdek_number and not self.order_uuid:
            raise ValueError("Either cdek_number or order_uuid must be provided")
        return self


class DeliveryRequest(CdekBaseModel):
    """Договорённость о доставке (POST /v2/delivery)."""

    date: str = Field(description="Agreed delivery date YYYY-MM-DD")
    cdek_number: Optional[str] = Field(default=None, description="CDEK tracking number")
    order_uuid: Optional[str] = Field(default=None, description="Order UUID in CDEK system")
    time_from: Optional[str] = Field(default=None, description="Delivery time from HH:MM")
    time_to: Optional[str] = Field(default=None, description="Delivery time to HH:MM")
    comment: Optional[str] = Field(default=None, description="Comment for delivery")
    delivery_point: Optional[str] = Field(default=None, description="Delivery point code")
    to_location: Optional[Location] = Field(default=None, description="Delivery address location")

    @model_validator(mode="after")
    def check_identifier(self) -> "DeliveryRequest":
        if not self.cdek_number and not self.order_uuid:
            raise ValueError("Either cdek_number or order_uuid must be provided")
        return self


class TariffRequest(CdekBaseModel):
    """Расчёт стоимости доставки (POST /v2/calculator/tariff[list])."""

    from_location: Location = Field(description="Sender location")
    to_location: Location = Field(description="Recipient location")
    packages: list[Package] = Field(description="List of packages for calculation")
    tariff_code: Optional[int] = Field(default=None, description="Specific tariff code (omit for tarifflist)")
    services: Optional[list[Service]] = Field(default=None, description="Additional services to include")
    additional_order_types: Optional[list[int]] = Field(default=None, description="Additional order type codes")
    date: Optional[str] = Field(default=None, description="Planned shipment date YYYY-MM-DD")
    type: Optional[int] = Field(default=None, description="Order type: 1 (online store) or 2 (delivery)")
    currency: Optional[str] = Field(default=None, description="Currency code (e.g. RUB)")
    lang: Optional[str] = Field(default=None, description="Language: rus, eng, or zho")


class WebhookRequest(CdekBaseModel):
    """Подписка на вебхуки (POST /v2/webhooks)."""

    type: str = Field(description="Webhook type (e.g. ORDER_STATUS, PRINT_FORM)")
    url: str = Field(description="URL to receive webhook events")


class PrintRequest(CdekBaseModel):
    """Формирование печатной формы (POST /v2/print/barcodes или /v2/print/orders)."""

    orders: list[OrderRef] = Field(description="List of orders for print form generation")
    copy_count: Optional[int] = Field(default=None, description="Number of copies")
    format: Optional[str] = Field(default=None, description="Print format: A4, A5, A6, A7")
    lang: Optional[str] = Field(default=None, description="Language: rus, eng, or zho")


class PrealertRequest(CdekBaseModel):
    """Регистрация преалерта (POST /v2/prealert)."""

    planned_date: str = Field(description="Planned transfer date YYYY-MM-DD")
    shipment_point: str = Field(description="Shipment point code")
    orders: list[OrderRef] = Field(description="List of orders in the prealert")


class PhotoDocumentRequest(CdekBaseModel):
    """Запрос фото документов (POST /v2/photoDocument)."""

    period_begin: Optional[str] = Field(default=None, description="Period start date YYYY-MM-DD")
    period_end: Optional[str] = Field(default=None, description="Period end date YYYY-MM-DD")
    orders: Optional[list[OrderRef]] = Field(default=None, description="Filter by specific orders")


# ── Response Models ────────────────────────────────────────────────


class RequestStatus(CdekBaseModel):
    """Статус обработки запроса."""

    request_uuid: Optional[str] = Field(default=None, description="Request UUID")
    type: Optional[str] = Field(default=None, description="Request type: CREATE, UPDATE, DELETE")
    date_time: Optional[str] = Field(default=None, description="Request timestamp ISO 8601")
    state: Optional[str] = Field(default=None, description="State: ACCEPTED, SUCCESSFUL, INVALID")
    errors: Optional[list[Error]] = Field(default=None, description="List of errors if state is INVALID")


class EntityResponse(CdekBaseModel):
    """Стандартный ответ API (entity + requests + related_entities)."""

    entity: Optional[dict] = Field(default=None, description="Response entity data")
    requests: Optional[list[RequestStatus]] = Field(default=None, description="Request processing statuses")
    related_entities: Optional[list] = Field(default=None, description="Related entity references")


class Status(CdekBaseModel):
    """Статус заказа."""

    code: str = Field(description="Status code (e.g. CREATED, ACCEPTED, DELIVERED)")
    name: str = Field(description="Human-readable status name")
    date_time: str = Field(description="Status timestamp ISO 8601")
    city: Optional[str] = Field(default=None, description="City where status was set")


class OrderInfo(CdekBaseModel):
    """Информация о заказе (из GET /v2/orders)."""

    uuid: Optional[str] = Field(default=None, description="Order UUID in CDEK system")
    cdek_number: Optional[Union[int, str]] = Field(default=None, description="CDEK tracking number")
    number: Optional[str] = Field(default=None, description="Order number in client system")
    statuses: Optional[list[Status]] = Field(default=None, description="Order status history")
    delivery_point: Optional[str] = Field(default=None, description="Delivery point code")
    recipient: Optional[Contact] = Field(default=None, description="Recipient contact")
    sender: Optional[Contact] = Field(default=None, description="Sender contact")
    packages: Optional[list[Package]] = Field(default=None, description="List of packages")
    from_location: Optional[Location] = Field(default=None, description="Sender location")
    to_location: Optional[Location] = Field(default=None, description="Recipient location")


class City(CdekBaseModel):
    """Населённый пункт (из GET /v2/location/cities)."""

    code: int = Field(description="CDEK city code")
    city: Optional[str] = Field(default=None, description="City name")
    region: Optional[str] = Field(default=None, description="Region name")
    country: Optional[str] = Field(default=None, description="Country name")
    country_code: Optional[str] = Field(default=None, description="Country code ISO 3166-1 alpha-2")


class Region(CdekBaseModel):
    """Регион (из GET /v2/location/regions)."""

    region: Optional[str] = Field(default=None, description="Region name")
    country_code: Optional[str] = Field(default=None, description="Country code ISO 3166-1 alpha-2")
    country: Optional[str] = Field(default=None, description="Country name")


class DeliveryPoint(CdekBaseModel):
    """Офис / ПВЗ / постамат (из GET /v2/deliverypoints)."""

    code: str = Field(description="Delivery point code (e.g. MSK005)")
    name: Optional[str] = Field(default=None, description="Office name")
    location: Optional[Location] = Field(default=None, description="Office location")
    work_time: Optional[str] = Field(default=None, description="Working hours description")
    type: Optional[str] = Field(default=None, description="Point type: PVZ, POSTAMAT")
    phones: Optional[list[Phone]] = Field(default=None, description="Contact phones")
    email: Optional[str] = Field(default=None, description="Contact email")


class TariffResult(CdekBaseModel):
    """Результат расчёта тарифа (из POST /v2/calculator/tariff)."""

    delivery_sum: Optional[float] = Field(default=None, description="Delivery cost")
    period_min: Optional[int] = Field(default=None, description="Minimum delivery period in days")
    period_max: Optional[int] = Field(default=None, description="Maximum delivery period in days")
    weight_calc: Optional[int] = Field(default=None, description="Calculated weight in grams")
    total_sum: Optional[float] = Field(default=None, description="Total cost including services")
    currency: Optional[str] = Field(default=None, description="Currency code")
    services: Optional[list] = Field(default=None, description="Applied additional services")


class Tariff(CdekBaseModel):
    """Тариф (из GET /v2/calculator/alltariffs)."""

    tariff_code: int = Field(description="CDEK tariff code")
    tariff_name: Optional[str] = Field(default=None, description="Tariff name")
    tariff_description: Optional[str] = Field(default=None, description="Tariff description")
    delivery_mode: Optional[int] = Field(default=None, description="Delivery mode code")
    delivery_sum: Optional[float] = Field(default=None, description="Delivery cost")
    period_min: Optional[int] = Field(default=None, description="Minimum delivery period in days")
    period_max: Optional[int] = Field(default=None, description="Maximum delivery period in days")


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
