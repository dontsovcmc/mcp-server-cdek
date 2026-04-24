"""Тесты Pydantic-моделей CDEK API."""

import pytest

from mcp_server_cdek.models import (
    City,
    Contact,
    DeliveryPoint,
    DeliveryRequest,
    EntityResponse,
    Error,
    IntakeRequest,
    Item,
    Location,
    Money,
    OrderInfo,
    OrderRef,
    OrderRequest,
    OrderUpdateRequest,
    Package,
    Phone,
    PrealertRequest,
    PrintRequest,
    Region,
    RequestStatus,
    Seller,
    Service,
    Status,
    Tariff,
    TariffRequest,
    TariffResult,
    Threshold,
    WebhookRequest,
)


# ── Shared models ──────────────────────────────────────────────────


class TestPhone:
    def test_required_fields(self):
        p = Phone(number="+79001234567")
        assert p.number == "+79001234567"
        assert p.additional is None

    def test_all_fields(self):
        p = Phone(number="+79001234567", additional="123")
        assert p.additional == "123"


class TestMoney:
    def test_minimal(self):
        m = Money(value=100.0)
        assert m.value == 100.0
        assert m.vat_sum is None

    def test_full(self):
        m = Money(value=100.0, vat_sum=20.0, vat_rate=20)
        assert m.vat_rate == 20


class TestLocation:
    def test_empty(self):
        loc = Location()
        assert loc.code is None
        assert loc.city is None

    def test_by_code(self):
        loc = Location(code=44)
        assert loc.code == 44

    def test_by_address(self):
        loc = Location(city="Москва", address="Тверская 1")
        assert loc.city == "Москва"


class TestError:
    def test_fields(self):
        e = Error(code="ERR_001", message="Something went wrong")
        assert e.code == "ERR_001"


class TestService:
    def test_minimal(self):
        s = Service(code="INSURANCE")
        assert s.parameter is None

    def test_with_param(self):
        s = Service(code="INSURANCE", parameter="5000")
        assert s.parameter == "5000"


# ── Building blocks ───────────────────────────────────────────────


class TestContact:
    def test_minimal(self):
        c = Contact(name="Иванов", phones=[Phone(number="+79001234567")])
        assert c.name == "Иванов"
        assert len(c.phones) == 1
        assert c.company is None

    def test_full(self):
        c = Contact(
            name="Иванов",
            company="ООО Тест",
            email="test@example.com",
            phones=[Phone(number="+79001234567")],
            contragent_type="LEGAL_ENTITY",
            tin="1234567890",
        )
        assert c.company == "ООО Тест"
        assert c.tin == "1234567890"


class TestSeller:
    def test_empty(self):
        s = Seller()
        assert s.name is None

    def test_full(self):
        s = Seller(name="ООО Рога", inn="1234567890", phone="+79001234567")
        assert s.inn == "1234567890"


class TestItem:
    def test_required(self):
        item = Item(
            name="Товар",
            ware_key="item1",
            payment=Money(value=0),
            cost=100.0,
            weight=170,
            amount=1,
        )
        assert item.weight == 170
        assert item.brand is None

    def test_with_optionals(self):
        item = Item(
            name="Модем",
            ware_key="modem",
            payment=Money(value=0),
            cost=500.0,
            weight=170,
            amount=2,
            brand="TP-Link",
            url="https://example.com",
        )
        assert item.brand == "TP-Link"


class TestPackage:
    def test_minimal(self):
        pkg = Package(number="1", weight=1000)
        assert pkg.length is None
        assert pkg.items is None

    def test_with_items(self):
        item = Item(
            name="Товар", ware_key="i", payment=Money(value=0),
            cost=100, weight=500, amount=1,
        )
        pkg = Package(number="1", weight=500, length=10, width=10, height=10, items=[item])
        assert len(pkg.items) == 1
        assert pkg.items[0].name == "Товар"


class TestOrderRef:
    def test_by_cdek_number(self):
        ref = OrderRef(cdek_number="1400567890")
        assert ref.cdek_number == "1400567890"

    def test_by_uuid(self):
        ref = OrderRef(order_uuid="aaa-bbb-ccc")
        assert ref.order_uuid == "aaa-bbb-ccc"


# ── Request models ────────────────────────────────────────────────


class TestOrderRequest:
    def test_minimal(self):
        order = OrderRequest(
            tariff_code=136,
            recipient=Contact(name="Петров", phones=[Phone(number="+79007654321")]),
            packages=[Package(number="1", weight=1000)],
        )
        assert order.tariff_code == 136
        assert order.sender is None
        assert order.print_type is None

    def test_with_print_alias(self):
        data = {
            "tariff_code": 136,
            "recipient": {"name": "Петров", "phones": [{"number": "+79007654321"}]},
            "packages": [{"number": "1", "weight": 1000}],
            "print": "barcode",
        }
        order = OrderRequest(**data)
        assert order.print_type == "barcode"

    def test_dump_with_alias(self):
        order = OrderRequest(
            tariff_code=136,
            recipient=Contact(name="Петров", phones=[Phone(number="+79007654321")]),
            packages=[Package(number="1", weight=1000)],
            print_type="barcode",
        )
        d = order.model_dump(by_alias=True, exclude_none=True)
        assert d["print"] == "barcode"
        assert "print_type" not in d

    def test_full(self):
        order = OrderRequest(
            tariff_code=137,
            type=2,
            number="IM-12345",
            comment="Тест",
            recipient=Contact(name="Петров", phones=[Phone(number="+79007654321")]),
            sender=Contact(name="Иванов", phones=[Phone(number="+79001234567")]),
            seller=Seller(name="ООО Рога"),
            from_location=Location(city="Москва"),
            to_location=Location(address="СПб, Невский 1"),
            packages=[Package(number="1", weight=1000, length=10, width=10, height=10)],
            services=[Service(code="INSURANCE", parameter="5000")],
            delivery_recipient_cost=Money(value=0),
        )
        assert order.type == 2
        assert order.seller.name == "ООО Рога"


class TestOrderUpdateRequest:
    def test_with_uuid(self):
        r = OrderUpdateRequest(uuid="aaa-bbb", comment="test")
        assert r.uuid == "aaa-bbb"

    def test_with_cdek_number(self):
        r = OrderUpdateRequest(cdek_number="1400567890", delivery_point="MSK005")
        assert r.delivery_point == "MSK005"

    def test_missing_identifier(self):
        with pytest.raises(ValueError, match="uuid or cdek_number"):
            OrderUpdateRequest(comment="test")


class TestIntakeRequest:
    def test_minimal(self):
        r = IntakeRequest(
            intake_date="2026-04-25",
            cdek_number="1400567890",
        )
        assert r.intake_time_from == "09:00"
        assert r.intake_time_to == "18:00"

    def test_missing_identifier(self):
        with pytest.raises(ValueError, match="cdek_number or order_uuid"):
            IntakeRequest(intake_date="2026-04-25")

    def test_with_order_uuid(self):
        r = IntakeRequest(intake_date="2026-04-25", order_uuid="uuid-123")
        assert r.order_uuid == "uuid-123"


class TestDeliveryRequest:
    def test_minimal(self):
        r = DeliveryRequest(date="2026-04-26", cdek_number="1400567890")
        assert r.time_from is None

    def test_missing_identifier(self):
        with pytest.raises(ValueError, match="cdek_number or order_uuid"):
            DeliveryRequest(date="2026-04-26")


class TestTariffRequest:
    def test_minimal(self):
        r = TariffRequest(
            from_location=Location(code=44),
            to_location=Location(code=270),
            packages=[Package(number="1", weight=1000)],
        )
        assert r.tariff_code is None  # optional for tarifflist

    def test_with_tariff(self):
        r = TariffRequest(
            tariff_code=136,
            from_location=Location(code=44),
            to_location=Location(code=270),
            packages=[Package(number="1", weight=1000)],
        )
        assert r.tariff_code == 136


class TestWebhookRequest:
    def test_fields(self):
        r = WebhookRequest(type="ORDER_STATUS", url="https://example.com/hook")
        assert r.type == "ORDER_STATUS"


class TestPrintRequest:
    def test_fields(self):
        r = PrintRequest(
            orders=[OrderRef(cdek_number="1400567890")],
            format="A6",
        )
        assert r.format == "A6"
        assert len(r.orders) == 1


class TestPrealertRequest:
    def test_fields(self):
        r = PrealertRequest(
            planned_date="2026-04-25",
            shipment_point="MSK005",
            orders=[OrderRef(cdek_number="1400567890")],
        )
        assert r.shipment_point == "MSK005"


# ── Response models ───────────────────────────────────────────────


class TestRequestStatus:
    def test_fields(self):
        rs = RequestStatus(
            request_uuid="req-1",
            type="CREATE",
            state="SUCCESSFUL",
            date_time="2026-04-25T12:00:00",
        )
        assert rs.state == "SUCCESSFUL"

    def test_with_errors(self):
        rs = RequestStatus(
            type="CREATE",
            state="INVALID",
            errors=[Error(code="ERR", message="fail")],
        )
        assert len(rs.errors) == 1


class TestEntityResponse:
    def test_parse(self):
        data = {
            "entity": {"uuid": "aaa-bbb"},
            "requests": [{"type": "CREATE", "state": "ACCEPTED"}],
        }
        r = EntityResponse(**data)
        assert r.entity["uuid"] == "aaa-bbb"
        assert r.requests[0].state == "ACCEPTED"

    def test_empty(self):
        r = EntityResponse()
        assert r.entity is None


class TestStatus:
    def test_fields(self):
        s = Status(code="CREATED", name="Создан", date_time="2026-04-25T12:00:00")
        assert s.code == "CREATED"
        assert s.city is None


class TestOrderInfo:
    def test_minimal(self):
        o = OrderInfo(uuid="aaa-bbb")
        assert o.cdek_number is None

    def test_full(self):
        o = OrderInfo(
            uuid="aaa-bbb",
            cdek_number=1400567890,
            number="IM-12345",
            statuses=[Status(code="CREATED", name="Создан", date_time="2026-04-25T12:00:00")],
        )
        assert o.cdek_number == 1400567890
        assert len(o.statuses) == 1

    def test_cdek_number_as_str(self):
        o = OrderInfo(uuid="aaa", cdek_number="1400567890")
        assert o.cdek_number == "1400567890"


class TestCity:
    def test_fields(self):
        c = City(code=44, city="Москва", region="Московская обл.", country_code="RU")
        assert c.code == 44


class TestRegion:
    def test_fields(self):
        r = Region(region="Московская", country_code="RU", country="Россия")
        assert r.region == "Московская"


class TestDeliveryPoint:
    def test_fields(self):
        dp = DeliveryPoint(
            code="MSK005",
            name="Офис Москва",
            location=Location(city="Москва", address="Тверская 1"),
            work_time="09:00-18:00",
            type="PVZ",
        )
        assert dp.code == "MSK005"
        assert dp.location.city == "Москва"


class TestTariffResult:
    def test_fields(self):
        tr = TariffResult(delivery_sum=350.0, period_min=3, period_max=5, total_sum=350.0)
        assert tr.period_min == 3


class TestTariff:
    def test_fields(self):
        t = Tariff(tariff_code=136, tariff_name="Склад-склад", delivery_mode=1)
        assert t.tariff_code == 136


# ── Extra fields & round-trip ──────────────────────────────────────


class TestExtraFields:
    def test_extra_preserved(self):
        """extra='allow' сохраняет недокументированные поля."""
        data = {"code": "MSK005", "unknown_field": "value", "another": 42}
        dp = DeliveryPoint(**data)
        assert dp.code == "MSK005"
        assert dp.unknown_field == "value"  # type: ignore[attr-defined]
        assert dp.another == 42  # type: ignore[attr-defined]

    def test_extra_in_dump(self):
        data = {"code": "MSK005", "owner_code": "CDEK"}
        dp = DeliveryPoint(**data)
        d = dp.model_dump()
        assert d["owner_code"] == "CDEK"


class TestRoundTrip:
    def test_order_request_roundtrip(self):
        """dict → Model → dict совместим с текущим кодом server.py."""
        payload = {
            "tariff_code": 136,
            "delivery_recipient_cost": {"value": 0.0, "vat_sum": 0.0},
            "from_location": {"city": "Москва"},
            "sender": {
                "company": "ООО Тест",
                "name": "Иванов",
                "contragent_type": "LEGAL_ENTITY",
                "email": "test@example.com",
                "phones": [{"number": "+79001234567"}],
                "passport_requirements_satisfied": False,
            },
            "recipient": {
                "name": "Петров",
                "phones": [{"number": "+79007654321"}],
            },
            "packages": [{
                "number": "12345",
                "comment": "Упаковка",
                "items": [{
                    "ware_key": "item",
                    "name": "Товар",
                    "cost": 100.0,
                    "amount": 1,
                    "weight": 170,
                    "payment": {"value": 0},
                }],
                "height": 8,
                "length": 10,
                "width": 7,
                "weight": 170,
            }],
            "print": "barcode",
            "delivery_point": "MSK005",
        }
        order = OrderRequest(**payload)
        assert order.tariff_code == 136
        assert order.print_type == "barcode"
        assert order.sender.company == "ООО Тест"
        assert order.packages[0].items[0].name == "Товар"

        d = order.model_dump(by_alias=True, exclude_none=True)
        assert d["print"] == "barcode"
        assert d["tariff_code"] == 136
        assert d["packages"][0]["weight"] == 170

    def test_entity_response_roundtrip(self):
        data = {
            "entity": {"uuid": "aaa-bbb", "cdek_number": 1400567890},
            "requests": [
                {"type": "CREATE", "state": "SUCCESSFUL", "date_time": "2026-04-25T12:00:00"}
            ],
            "related_entities": [{"uuid": "rel-1", "type": "reverse_order"}],
        }
        r = EntityResponse(**data)
        d = r.model_dump(exclude_none=True)
        assert d["entity"]["uuid"] == "aaa-bbb"
        assert d["requests"][0]["state"] == "SUCCESSFUL"
