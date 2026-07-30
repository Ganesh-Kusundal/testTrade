"""Unit tests for DhanWebSocket MarketFeed segment mapping (v2.2).

Verifies that wire segments are correctly translated to dhanhq MarketFeed
v2 numeric exchange codes for quote subscriptions, and that FullDepth
correctly rejects unsupported segments.
"""
from __future__ import annotations

import pytest

from scalpr.adapters.dhan._resolver import (
    wire_segment_to_full_depth_numeric,
    wire_segment_to_market_feed_numeric,
)
from scalpr.adapters.dhan._ws import DhanWebSocket


@pytest.fixture
def ws() -> DhanWebSocket:
    return DhanWebSocket(access_token="test_token", client_id="test_client")


# ── MarketFeed segment mapping ───────────────────────────────────────


class TestMarketFeedSegmentMapping:
    @pytest.mark.parametrize(
        "segment,expected",
        [
            ("IDX_I", 0),
            ("NSE_EQ", 1),
            ("NSE_FNO", 2),
            ("NSE_CURRENCY", 3),
            ("BSE_EQ", 4),
            ("MCX_COMM", 5),
            ("BSE_CURRENCY", 7),
            ("BSE_FNO", 8),
        ],
    )
    def test_wire_segment_to_market_feed_code(self, segment: str, expected: int) -> None:
        assert wire_segment_to_market_feed_numeric(segment) == expected

    def test_unknown_segment_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown wire segment"):
            wire_segment_to_market_feed_numeric("INVALID_SEG")


# ── FullDepth segment mapping ────────────────────────────────────────


class TestFullDepthSegmentMapping:
    @pytest.mark.parametrize(
        "segment,expected",
        [
            ("NSE_EQ", 1),
            ("IDX_I", 1),
            ("NSE_FNO", 2),
        ],
    )
    def test_supported_segments(self, segment: str, expected: int) -> None:
        assert wire_segment_to_full_depth_numeric(segment) == expected

    @pytest.mark.parametrize(
        "segment",
        ["MCX_COMM", "BSE_EQ", "BSE_FNO", "BSE_CURRENCY", "NSE_CURRENCY"],
    )
    def test_unsupported_segments_raise(self, segment: str) -> None:
        with pytest.raises(ValueError, match="does not support wire segment"):
            wire_segment_to_full_depth_numeric(segment)


# ── _to_sdk_instruments (quote path) ─────────────────────────────────


class TestToSdkInstruments:
    def test_nse_eq_maps_to_code_1(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("12345", "NSE_EQ")])
        assert result == [(1, "12345", 17)]

    def test_nse_fno_maps_to_code_2(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("12345", "NSE_FNO")])
        assert result == [(2, "12345", 17)]

    def test_mcx_comm_maps_to_code_5(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("99999", "MCX_COMM")])
        assert result == [(5, "99999", 17)]

    def test_bse_eq_maps_to_code_4(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("67890", "BSE_EQ")])
        assert result == [(4, "67890", 17)]

    def test_idx_i_maps_to_code_0(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("100", "IDX_I")])
        assert result == [(0, "100", 17)]

    def test_unknown_segment_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown wire segment"):
            DhanWebSocket._to_sdk_instruments([("100", "INVALID")])

    def test_mode_full_uses_code_21(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("100", "NSE_EQ")], mode="full")
        assert result == [(1, "100", 21)]

    def test_mode_ltp_uses_code_15(self) -> None:
        result = DhanWebSocket._to_sdk_instruments([("100", "NSE_EQ")], mode="ltp")
        assert result == [(1, "100", 15)]


# ── subscribe_depth validation ───────────────────────────────────────


class TestSubscribeDepthValidation:
    def test_subscribe_depth_rejects_mcx(self, ws: DhanWebSocket) -> None:
        with pytest.raises(ValueError, match="does not support wire segment"):
            ws.subscribe_depth([("100", "MCX_COMM")])

    def test_subscribe_depth_rejects_bse(self, ws: DhanWebSocket) -> None:
        with pytest.raises(ValueError, match="does not support wire segment"):
            ws.subscribe_depth([("100", "BSE_EQ")])

    def test_subscribe_depth_accepts_nse_eq(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("100", "NSE_EQ")])
        assert ws.depth_subscription_count_20 == 1

    def test_subscribe_depth_accepts_nse_fno(self, ws: DhanWebSocket) -> None:
        ws.subscribe_depth([("100", "NSE_FNO")])
        assert ws.depth_subscription_count_20 == 1
