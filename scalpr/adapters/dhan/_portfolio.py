from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

import pandas as pd

from scalpr.adapters.dhan._http import DhanHttpClient
from scalpr.adapters.dhan._mapper_portfolio import margin_calc_to_dhan_request, to_position
from scalpr.domain.position import Position
from scalpr.domain.values import ZERO

logger = logging.getLogger(__name__)


class PortfolioError(Exception):
    """Base for portfolio-related errors."""


class PnLCalculationError(PortfolioError):
    """Raised when P&L calculation fails."""


class PortfolioAdapter:
    def __init__(self, http_client: DhanHttpClient) -> None:
        self._http = http_client

    def get_live_pnl(self, positions: list[Position] | None = None) -> float:
        try:
            if positions is None:
                raw = self._fetch_raw_positions()
            else:
                raw = self._positions_to_raw(positions)
            if not raw:
                return 0.0

            ltps = self._fetch_ltp_batch(raw)

            total = ZERO
            for r in raw:
                day_buy_val = r["day_buy_avg"] * Decimal(r["day_buy_qty"])
                day_sell_val = r["day_sell_avg"] * Decimal(r["day_sell_qty"])
                ltp = ltps.get(r["security_id"], r.get("ltp", ZERO))
                if not isinstance(ltp, Decimal):
                    ltp = Decimal(str(ltp))
                mtm = (day_sell_val - day_buy_val) + Decimal(r["net_qty"]) * ltp * Decimal(r["multiplier"])
                total += mtm

            return float(round(total, 2))
        except Exception as exc:
            logger.warning("get_live_pnl_failed: %s", exc)
            return 0.0

    def get_positions_summary(self, as_df: bool = False) -> dict[str, Any] | pd.DataFrame:
        try:
            raw = self._fetch_raw_positions()
        except Exception as exc:
            logger.warning("get_positions_summary_failed: %s", exc)
            result = {"total_investment": 0.0, "current_value": 0.0, "unrealized_pnl": 0.0, "realized_pnl": 0.0}
            return pd.DataFrame([result]) if as_df else result

        total_investment = ZERO
        total_unrealized = ZERO
        total_realized = ZERO

        for r in raw:
            qty = r["net_qty"]
            avg = r.get("buy_avg") if qty > 0 else r.get("sell_avg")
            if avg is None or avg == ZERO:
                avg = r.get("buy_avg", ZERO) or r.get("sell_avg", ZERO)
            total_investment += Decimal(abs(qty)) * avg
            total_realized += r.get("realized_pnl", ZERO)

        current_value = ZERO
        ltps = self._fetch_ltp_batch(raw)
        for r in raw:
            ltp = ltps.get(r["security_id"], r.get("ltp", ZERO))
            if not isinstance(ltp, Decimal):
                ltp = Decimal(str(ltp))
            current_value += Decimal(abs(r["net_qty"])) * ltp

        for pos in raw:
            qty = pos["net_qty"]
            ltp_val = ltps.get(pos["security_id"], pos.get("ltp", ZERO))
            if not isinstance(ltp_val, Decimal):
                ltp_val = Decimal(str(ltp_val))
            avg_val = pos.get("buy_avg") if qty > 0 else pos.get("sell_avg")
            if avg_val is None or avg_val == ZERO:
                avg_val = pos.get("buy_avg", ZERO) or pos.get("sell_avg", ZERO)
            if qty > 0:
                total_unrealized += Decimal(qty) * (ltp_val - avg_val)
            elif qty < 0:
                total_unrealized += Decimal(abs(qty)) * (avg_val - ltp_val)

        result = {
            "total_investment": float(round(total_investment, 2)),
            "current_value": float(round(current_value, 2)),
            "unrealized_pnl": float(round(total_unrealized, 2)),
            "realized_pnl": float(round(total_realized, 2)),
        }
        return pd.DataFrame([result]) if as_df else result

    def get_funds(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        """Fetch fund limits from the broker."""
        if debug:
            logger.info("get_funds")
        data = self._http.get("/fundlimit", bucket="portfolio")
        return pd.DataFrame([data]) if as_df else data


    def get_positions(self, as_df: bool = False, debug: bool = False) -> list[Position] | pd.DataFrame:
        """Fetch current broker positions."""
        if debug:
            logger.info("get_positions")
        data = self._http.get("/positions", bucket="portfolio")
        if isinstance(data, list):
            positions = [to_position(item) for item in data]
        else:
            positions = [to_position(data)]
        return self._positions_to_df(positions) if as_df else positions

    def get_holdings(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        """Fetch current broker holdings."""
        if debug:
            logger.info("get_holdings")
        data = self._http.get("/holdings", bucket="portfolio")
        if as_df:
            if isinstance(data, list):
                return pd.DataFrame(data)
            if isinstance(data, dict):
                return pd.DataFrame([data])
        return data

    def margin_calculator(
        self,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        product_type: str,
        price: float,
        trigger_price: float = 0,
    ) -> dict[str, Any]:
        """Calculate margin requirements for an order."""
        # Normalize segment: API requires NSE_EQ not NSE for equity
        if exchange_segment.upper() == "NSE":
            exchange_segment = "NSE_EQ"
        req = margin_calc_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, product_type, price, trigger_price,
        )
        return self._http.post("/margincalculator", data=req, bucket="portfolio")

    def get_expired_option_data(
        self,
        security_id: str,
        exchange_segment: str = "NSE_FNO",
        instrument_type: str = "OPT",
        expiry_flag: str = "MONTH",
        expiry_code: int = 1,
        strike: str = "ATM",
        drv_option_type: str = "CE",
        required_data: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        interval: int = 1,
    ) -> dict[str, Any]:
        """Get expired option data with sensible defaults."""
        if required_data is None:
            required_data = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME", "OI"]
        payload = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "expiryFlag": expiry_flag,
            "expiryCode": expiry_code,
            "strike": strike,
            "drvOptionType": drv_option_type,
            "requiredData": required_data,
            "fromDate": from_date or "",
            "toDate": to_date or "",
            "interval": interval,
        }
        return self._http.post("/charts/rollingoption", data=payload, bucket="history")

    def get_exchange_time(self) -> str:
        """Fetch current exchange time."""
        try:
            data = self._http.get("/exchange/time", bucket="portfolio")
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return data.get("exchangeTime", data.get("time", data.get("dateTime", "")))
            return str(data)
        except Exception as exc:
            logger.warning("exchange_time_endpoint_unavailable: %s", exc)
            from datetime import datetime, timedelta, timezone
            ist = timezone(timedelta(hours=5, minutes=30))
            return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

    def _fetch_raw_positions(self) -> list[dict[str, Any]]:
        data = self._http.get("/positions", bucket="portfolio")
        raw_list: list[dict[str, Any]] = data if isinstance(data, list) else [data]
        result: list[dict[str, Any]] = []
        for r in raw_list:
            qty = self._safe_int(r.get("netQty", r.get("quantity", 0)))
            if qty == 0:
                continue
            result.append({
                "security_id": str(r.get("securityId", "")),
                "exchange_segment": str(r.get("exchangeSegment", "NSE_EQ")),
                "symbol": str(r.get("tradingSymbol", r.get("symbol", ""))),
                "net_qty": qty,
                "day_buy_qty": self._safe_int(r.get("dayBuyQty", 0)),
                "day_sell_qty": self._safe_int(r.get("daySellQty", 0)),
                "day_buy_avg": self._safe_decimal(r.get("dayBuyAvg", 0)),
                "day_sell_avg": self._safe_decimal(r.get("daySellAvg", 0)),
                "buy_avg": self._safe_decimal(r.get("buyAvg", 0)),
                "sell_avg": self._safe_decimal(r.get("sellAvg", 0)),
                "multiplier": self._safe_int(r.get("multiplier", 1)),
                "ltp": self._safe_decimal(r.get("ltp", 0)),
                "realized_pnl": self._safe_decimal(r.get("realizedPnl", 0)),
            })
        return result

    def _positions_to_raw(self, positions: list[Position]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for pos in positions:
            if pos.quantity == 0:
                continue
            result.append({
                "security_id": pos.symbol,
                "exchange_segment": "NSE_EQ",
                "symbol": pos.symbol,
                "net_qty": pos.quantity,
                "day_buy_qty": 0,
                "day_sell_qty": 0,
                "day_buy_avg": ZERO,
                "day_sell_avg": ZERO,
                "buy_avg": pos.avg_price if pos.quantity > 0 else ZERO,
                "sell_avg": pos.avg_price if pos.quantity < 0 else ZERO,
                "multiplier": 1,
                "ltp": pos.ltp,
                "realized_pnl": pos.realised_pnl,
            })
        return result

    @staticmethod
    def _positions_to_df(positions: list[Position]) -> pd.DataFrame:
        rows = []
        for p in positions:
            rows.append({
                "symbol": p.symbol,
                "exchange": p.exchange.value,
                "quantity": p.quantity,
                "avg_price": float(p.avg_price),
                "ltp": float(p.ltp),
                "unrealised_pnl": float(p.unrealised_pnl),
                "realised_pnl": float(p.realised_pnl),
                "position_side": p.position_side.value,
            })
        return pd.DataFrame(rows)

    def _fetch_ltp_batch(self, raw_positions: list[dict[str, Any]]) -> dict[str, Decimal]:
        ltps: dict[str, Decimal] = {}
        by_segment: dict[str, list[str]] = defaultdict(list)
        for r in raw_positions:
            sid = r["security_id"]
            seg = r["exchange_segment"]
            if sid:
                by_segment[seg].append(sid)

        for segment, security_ids in by_segment.items():
            try:
                resp = self._http.post(
                    "/marketfeed/quote",
                    data={"security_ids": security_ids, "exchangeSegment": segment},
                    bucket="market_data",
                )
                parsed = self._parse_ltp_response(resp, security_ids)
                ltps.update(parsed)
            except Exception as exc:
                logger.warning("ltp_fetch_failed segment=%s: %s", segment, exc)

        return ltps

    @staticmethod
    def _parse_ltp_response(resp: dict[str, Any] | list[Any], security_ids: list[str]) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        if isinstance(resp, list):
            for item in resp:
                if isinstance(item, dict):
                    sid = str(item.get("securityId", ""))
                    raw = item.get("ltp") or item.get("last_price") or item.get("LTP")
                    if sid and raw is not None:
                        try:
                            result[sid] = Decimal(str(raw))
                        except Exception:
                            logger.debug("portfolio_op_failed", exc_info=True)
            return result
        records = resp.get("data") or resp.get("records") or resp
        if isinstance(records, dict):
            for sid in security_ids:
                record = records.get(sid) or records.get(str(sid))
                if record is None:
                    continue
                if isinstance(record, dict):
                    raw = record.get("ltp") or record.get("last_price") or record.get("LTP")
                else:
                    raw = record
                if raw is not None:
                    try:
                        result[sid] = Decimal(str(raw))
                    except Exception:
                        logger.debug("portfolio_op_failed", exc_info=True)
        elif isinstance(records, list):
            for item in records:
                if isinstance(item, dict):
                    sid = str(item.get("securityId", ""))
                    raw = item.get("ltp") or item.get("last_price") or item.get("LTP")
                    if sid and raw is not None:
                        try:
                            result[sid] = Decimal(str(raw))
                        except Exception:
                            logger.debug("portfolio_op_failed", exc_info=True)
        return result

    @staticmethod
    def _safe_int(val: Any, default: int = 0) -> int:
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_decimal(val: Any) -> Decimal:
        try:
            return Decimal(str(val))
        except (TypeError, ValueError):
            return ZERO
