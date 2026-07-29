from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scalpr.adapters.dhan._mapper import (
    InvalidValueError,
    kill_switch_to_dhan,
    order_to_dhan_request_v2,
    product_type_from_domain,
)
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderType

# =========================================================================
# order_to_dhan_request_v2 — product types
# =========================================================================

class TestOrderToDhanRequestV2ProductTypes:
    def make_order(self, **kwargs: Any) -> Order:
        defaults = {
            "order_id": "o1",
            "symbol": "RELIANCE",
            "exchange": Exchange.NSE,
            "side": OrderSide.BUY,
            "order_type": OrderType.MARKET,
            "quantity": 10,
            "price": Decimal("0"),
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_intraday_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="INTRADAY")
        assert result["productType"] == "INTRADAY"

    def test_cnc_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="CNC")
        assert result["productType"] == "CNC"

    def test_margin_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="MARGIN")
        assert result["productType"] == "MARGIN"

    def test_mtf_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="MTF")
        assert result["productType"] == "MTF"

    def test_co_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="CO")
        assert result["productType"] == "CO"

    def test_bo_product_type(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1", product_type="BO")
        assert result["productType"] == "BO"

    def test_default_product_type_is_intraday(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "11536", "NSE_EQ", "c1")
        assert result["productType"] == "INTRADAY"


# =========================================================================
# order_to_dhan_request_v2 — order types
# =========================================================================

class TestOrderToDhanRequestV2OrderTypes:
    @pytest.mark.parametrize("order_type,dhan_type", [
        (OrderType.LIMIT, "LIMIT"),
        (OrderType.MARKET, "MARKET"),
        (OrderType.STOP_LOSS, "SL"),
        (OrderType.STOP_LOSS_MARKET, "SL-M"),
    ])
    def test_all_order_types(self, order_type, dhan_type):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=order_type,
            quantity=1, price=Decimal("100") if order_type != OrderType.MARKET else Decimal("0"),
            trigger_price=Decimal("90") if "STOP" in order_type.value else Decimal("0"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert result["orderType"] == dhan_type

    def test_invalid_order_type_raises(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type="FAKE",  # type: ignore[arg-type]
            quantity=1, price=Decimal("100"),
        )
        with pytest.raises(InvalidValueError):
            order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")


# =========================================================================
# order_to_dhan_request_v2 — after market / AMO
# =========================================================================

class TestOrderToDhanRequestV2AMO:
    def make_order(self, **kwargs: Any) -> Order:
        defaults = {
            "order_id": "o1", "symbol": "RELIANCE", "exchange": Exchange.NSE,
            "side": OrderSide.BUY, "order_type": OrderType.LIMIT,
            "quantity": 10, "price": Decimal("2500"),
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_after_market_sets_flag(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=True)
        assert result["afterMarketOrder"] is True

    def test_after_market_default_false(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert result["afterMarketOrder"] is False

    def test_after_market_includes_amo_time(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=True, amo_time="OPEN_30")
        assert result["amoTime"] == "OPEN_30"

    def test_after_market_default_amo_time(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=True)
        assert result["amoTime"] == "OPEN"

    def test_after_market_no_amo_time_when_false(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=False)
        assert "amoTime" not in result

    def test_invalid_amo_time_raises(self):
        order = self.make_order()
        with pytest.raises(InvalidValueError):
            order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=True, amo_time="CLOSE")

    def test_amo_open_60(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", after_market=True, amo_time="OPEN_60")
        assert result["amoTime"] == "OPEN_60"


# =========================================================================
# order_to_dhan_request_v2 — BO / CO
# =========================================================================

class TestOrderToDhanRequestV2BOCO:
    def make_order(self, **kwargs: Any) -> Order:
        defaults = {
            "order_id": "o1", "symbol": "RELIANCE", "exchange": Exchange.NSE,
            "side": OrderSide.BUY, "order_type": OrderType.LIMIT,
            "quantity": 10, "price": Decimal("2500"),
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_bo_with_profit(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", bo_profit=100.0)
        assert result["boProfitValue"] == 100.0

    def test_bo_with_stop_loss(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", bo_stop_loss=50.0)
        assert result["boStopLossValue"] == 50.0

    def test_bo_with_both_profit_and_stop_loss(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(
            order, "s", "NSE_EQ", "c1",
            bo_profit=200.0, bo_stop_loss=75.0,
        )
        assert result["boProfitValue"] == 200.0
        assert result["boStopLossValue"] == 75.0

    def test_bo_no_profit_stop_loss_by_default(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert "boProfitValue" not in result
        assert "boStopLossValue" not in result

    def test_bo_profit_as_float(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", bo_profit=150.50)
        assert isinstance(result["boProfitValue"], float)
        assert result["boProfitValue"] == 150.50

    def test_bo_stop_loss_as_float(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", bo_stop_loss=45.75)
        assert isinstance(result["boStopLossValue"], float)
        assert result["boStopLossValue"] == 45.75


# =========================================================================
# order_to_dhan_request_v2 — tag field
# =========================================================================

class TestOrderToDhanRequestV2Tag:
    def make_order(self, **kwargs: Any) -> Order:
        defaults = {
            "order_id": "o1", "symbol": "RELIANCE", "exchange": Exchange.NSE,
            "side": OrderSide.BUY, "order_type": OrderType.LIMIT,
            "quantity": 10, "price": Decimal("2500"),
        }
        defaults.update(kwargs)
        return Order(**defaults)

    def test_tag_included(self):
        order = self.make_order()
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", tag="my-tag-001")
        assert result["correlationId"] == "my-tag-001"

    def test_tag_overrides_correlation_id(self):
        order = self.make_order(correlation_id="orig-corr")
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", tag="override-tag")
        assert result["correlationId"] == "override-tag"

    def test_tag_none_uses_order_correlation_id(self):
        order = self.make_order(correlation_id="orig-corr")
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", tag=None)
        assert result["correlationId"] == "orig-corr"

    def test_tag_empty_uses_order_correlation_id(self):
        order = self.make_order(correlation_id="orig-corr")
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", tag="")
        assert result["correlationId"] == "orig-corr"

    def test_tag_empty_and_no_correlation_id(self):
        order = self.make_order(correlation_id=None)
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", tag="")
        assert result["correlationId"] == ""


# =========================================================================
# order_to_dhan_request_v2 — other fields
# =========================================================================

class TestOrderToDhanRequestV2Other:
    def test_disclosed_quantity(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=100, price=Decimal("100"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1", disclosed_qty=50)
        assert result["disclosedQuantity"] == 50

    def test_disclosed_quantity_defaults_zero(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=100, price=Decimal("100"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert result["disclosedQuantity"] == 0

    def test_client_id_in_request(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "my-client")
        assert result["dhanClientId"] == "my-client"

    def test_security_id_in_request(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"),
        )
        result = order_to_dhan_request_v2(order, "sec999", "NSE_EQ", "c1")
        assert result["securityId"] == "sec999"

    def test_exchange_segment_in_request(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_FNO", "c1")
        assert result["exchangeSegment"] == "NSE_FNO"

    def test_quantity_in_request(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=75, price=Decimal("0"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert result["quantity"] == 75

    def test_validity_from_order(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"), validity="IOC",
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert result["validity"] == "IOC"

    def test_price_as_string(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("1234.56"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert isinstance(result["price"], str)
        assert result["price"] == "1234.56"

    def test_trigger_price_as_string(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.STOP_LOSS,
            quantity=10, price=Decimal("100"), trigger_price=Decimal("95.50"),
        )
        result = order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")
        assert isinstance(result["triggerPrice"], str)
        assert result["triggerPrice"] == "95.50"


# =========================================================================
# order_to_dhan_request_v2 — invalid inputs
# =========================================================================

class TestOrderToDhanRequestV2Invalid:
    def test_invalid_side_raises(self):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side="HOLD", order_type=OrderType.MARKET,  # type: ignore[arg-type]
            quantity=1, price=Decimal("0"),
        )
        with pytest.raises(InvalidValueError):
            order_to_dhan_request_v2(order, "s", "NSE_EQ", "c1")


# =========================================================================
# kill_switch_to_dhan
# =========================================================================

class TestKillSwitchToDhan:
    def test_on_maps_to_activate(self):
        result = kill_switch_to_dhan("ON")
        assert result == {"action": "ACTIVATE"}

    def test_off_maps_to_deactivate(self):
        result = kill_switch_to_dhan("OFF")
        assert result == {"action": "DEACTIVATE"}

    def test_activate_maps_to_activate(self):
        result = kill_switch_to_dhan("ACTIVATE")
        assert result == {"action": "ACTIVATE"}

    def test_deactivate_maps_to_deactivate(self):
        result = kill_switch_to_dhan("DEACTIVATE")
        assert result == {"action": "DEACTIVATE"}

    def test_lowercase_on(self):
        result = kill_switch_to_dhan("on")
        assert result == {"action": "ACTIVATE"}

    def test_lowercase_off(self):
        result = kill_switch_to_dhan("off")
        assert result == {"action": "DEACTIVATE"}

    def test_invalid_action_raises(self):
        with pytest.raises(InvalidValueError):
            kill_switch_to_dhan("TOGGLE")

    def test_empty_action_raises(self):
        with pytest.raises(InvalidValueError):
            kill_switch_to_dhan("")

    def test_none_action_raises(self):
        with pytest.raises(InvalidValueError):
            kill_switch_to_dhan(None)  # type: ignore[arg-type]


# =========================================================================
# product_type_from_domain
# =========================================================================

class TestProductTypeFromDomain:
    @pytest.mark.parametrize("input_val,expected", [
        ("MIS", "INTRADAY"),
        ("CNC", "CNC"),
        ("MARGIN", "MARGIN"),
        ("MTF", "MTF"),
        ("CO", "CO"),
        ("BO", "BO"),
        ("mis", "INTRADAY"),
        ("Cnc", "CNC"),
    ])
    def test_valid_product_types(self, input_val, expected):
        assert product_type_from_domain(input_val) == expected

    def test_invalid_product_type_raises(self):
        with pytest.raises(InvalidValueError):
            product_type_from_domain("UNKNOWN")

    def test_empty_product_type_raises(self):
        with pytest.raises(InvalidValueError):
            product_type_from_domain("")


# =========================================================================
# DhanClient place_order delegation
# =========================================================================

class TestDhanClientPlaceOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.order_to_dhan_request_v2") as mock_v2,
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock(datetime(2024, 6, 15, 10, 30))
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._token_manager = MagicMock()
            c._http_client = MagicMock()
            c._resolver = MagicMock()

            resolved = MagicMock()
            resolved.security_id = "12345"
            resolved.wire_segment = "NSE_EQ"
            c._resolver.resolve_full.return_value = resolved

            mock_v2.return_value = {"dhanClientId": "c1", "securityId": "12345"}
            c._mock_v2 = mock_v2

            yield c

    def test_place_order_posts_to_orders(self, client):
        order = Order(
            order_id="o1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"),
        )
        client._http_client.post.return_value = {"orderId": "ORD-001"}
        result = client.place_order(order)
        client._http_client.post.assert_called_once_with(
            "/orders", data=client._mock_v2.return_value,
        )
        assert result == "ORD-001"

    def test_place_order_with_should_slice(self, client):
        order = Order(
            order_id="o1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"),
        )
        client._http_client.post.return_value = {"orderId": "SLICE-001"}
        result = client.place_order(order, should_slice=True)
        client._http_client.post.assert_called_once_with(
            "/orders/slicing", data=client._mock_v2.return_value,
        )
        assert result == "SLICE-001"

    def test_place_order_acquires_rate_limit(self, client):
        order = Order(
            order_id="o1", symbol="X", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"),
        )
        client.place_order(order)

    def test_place_order_resolves_symbol(self, client):
        order = Order(
            order_id="o1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.MARKET,
            quantity=1, price=Decimal("0"),
        )
        client.place_order(order)
        client._resolver.resolve_full.assert_called_once_with("RELIANCE", "NSE")

    def test_place_order_passes_all_params_to_v2_mapper(self, client):
        order = Order(
            order_id="o1", symbol="RELIANCE", exchange=Exchange.NSE,
            side=OrderSide.BUY, order_type=OrderType.LIMIT,
            quantity=10, price=Decimal("2500"),
        )
        client._http_client.post.return_value = {"orderId": "ORD-001"}
        client.place_order(
            order,
            product_type="CNC",
            after_market=True,
            amo_time="OPEN_30",
            bo_profit=100.0,
            bo_stop_loss=50.0,
            tag="my-tag",
            should_slice=False,
        )
        client._mock_v2.assert_called_once_with(
            order, "12345", "NSE_EQ", "c1",
            product_type="CNC",
            after_market=True,
            amo_time="OPEN_30",
            bo_profit=100.0,
            bo_stop_loss=50.0,
            disclosed_qty=0,
            tag="my-tag",
        )


# =========================================================================
# DhanClient modify_order delegation
# =========================================================================

class TestDhanClientModifyOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock(datetime(2024, 6, 15, 10, 30))
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_modify_order_puts_to_orders_endpoint(self, client):
        result = client.modify_order("ORD-001", quantity=15, price="2550")
        client._http_client.put.assert_called_once_with(
            "/orders/ORD-001", data={"quantity": 15, "price": "2550"},
        )
        assert result is True

    def test_modify_order_acquires_rate_limit(self, client):
        client.modify_order("ORD-001", quantity=10)


# =========================================================================
# DhanClient cancel_order delegation
# =========================================================================

class TestDhanClientCancelOrder:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock(datetime(2024, 6, 15, 10, 30))
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            yield c

    def test_cancel_order_deletes_orders_endpoint(self, client):
        result = client.cancel_order("ORD-001")
        client._http_client.delete.assert_called_once_with("/orders/ORD-001")
        assert result is True

    def test_cancel_order_acquires_rate_limit(self, client):
        client.cancel_order("ORD-001")


# =========================================================================
# DhanClient kill_switch delegation
# =========================================================================

class TestDhanClientKillSwitch:
    @pytest.fixture
    def client(self):
        with (
            patch("scalpr.adapters.dhan.client.TokenManager"),
            patch("scalpr.adapters.dhan.client.DhanHttpClient"),
            patch("scalpr.adapters.dhan.client.RateLimiter"),
            patch("scalpr.adapters.dhan.client.DhanWebSocket"),
            patch("scalpr.adapters.dhan.client.SymbolResolver"),
            patch("scalpr.adapters.dhan.client.kill_switch_to_dhan") as mock_ks,
        ):
            from scalpr.adapters.dhan.client import DhanClient
            from scalpr.engine.clock import StaticClock
            from scalpr.engine.message_bus import RecordingBus

            bus = RecordingBus()
            clock = StaticClock(datetime(2024, 6, 15, 10, 30))
            config = {"client_id": "c1", "access_token": "tok", "totp_secret": "sec"}

            c = DhanClient(bus, clock, config)
            c._rate_limiter = MagicMock()
            c._http_client = MagicMock()
            c._mock_ks = mock_ks
            yield c

    def test_kill_switch_posts_to_endpoint(self, client):
        client._mock_ks.return_value = {"action": "ACTIVATE"}
        client._http_client.post.return_value = {"killSwitchStatus": "ACTIVATED"}
        result = client.kill_switch("ON")
        client._http_client.post.assert_called_once_with(
            "/killswitch", data={"action": "ACTIVATE"},
        )
        assert result == "ACTIVATED"

    def test_kill_switch_maps_via_kill_switch_to_dhan(self, client):
        client._mock_ks.return_value = {"action": "DEACTIVATE"}
        client._http_client.post.return_value = {"killSwitchStatus": "DEACTIVATED"}
        result = client.kill_switch("OFF")
        client._mock_ks.assert_called_once_with("OFF")
        assert result == "DEACTIVATED"

    def test_kill_switch_acquires_rate_limit(self, client):
        client._mock_ks.return_value = {"action": "ACTIVATE"}
        client._http_client.post.return_value = {"killSwitchStatus": "ACTIVATED"}
        client.kill_switch("ON")

    def test_kill_switch_missing_status_returns_empty(self, client):
        client._mock_ks.return_value = {"action": "ACTIVATE"}
        client._http_client.post.return_value = {}
        result = client.kill_switch("ON")
        assert result == ""
