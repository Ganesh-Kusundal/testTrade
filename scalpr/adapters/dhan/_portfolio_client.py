from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from scalpr.domain.position import Position

logger = logging.getLogger(__name__)


class PortfolioClient:
    def __init__(
        self,
        http_provider,
        token_provider,
        portfolio: Any,
    ) -> None:
        self._http_provider = http_provider
        self._token_provider = token_provider
        self._portfolio = portfolio

    @property
    def _http(self):
        return self._http_provider()

    @property
    def _token_manager(self):
        return self._token_provider()

    # ── Portfolio ──────────────────────────────────────────────────────

    def get_positions(self, as_df: bool = False, debug: bool = False) -> list[Position] | pd.DataFrame:
        from scalpr.adapters.dhan.client import to_position

        if debug:
            logger.info("get_positions")
        data = self._http.get("/positions", bucket="portfolio")
        if isinstance(data, list):
            positions = [to_position(item) for item in data]
        else:
            positions = [to_position(data)]
        return self._portfolio._positions_to_df(positions) if as_df else positions

    def get_holdings(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        if debug:
            logger.info("get_holdings")
        data = self._http.get("/holdings", bucket="portfolio")
        if as_df:
            if isinstance(data, list):
                return pd.DataFrame(data)
            if isinstance(data, dict):
                return pd.DataFrame([data])
        return data

    def get_funds(self, as_df: bool = False, debug: bool = False) -> dict[str, Any] | pd.DataFrame:
        if debug:
            logger.info("get_funds")
        data = self._http.get("/fundlimit", bucket="portfolio")
        return pd.DataFrame([data]) if as_df else data

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
        from scalpr.adapters.dhan.client import margin_calc_to_dhan_request

        req = margin_calc_to_dhan_request(
            security_id, exchange_segment, transaction_type,
            quantity, product_type, price, trigger_price,
        )
        return self._http.post("/margincalculator", data=req, bucket="portfolio")

    def get_expired_option_data(
        self,
        security_id: str,
        exchange_segment: str,
        instrument_type: str,
        expiry_flag: str,
        expiry_code: int,
        strike: str,
        drv_option_type: str,
        required_data: list[str],
        from_date: str,
        to_date: str,
        interval: int = 1,
    ) -> dict[str, Any]:
        payload = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "expiryFlag": expiry_flag,
            "expiryCode": expiry_code,
            "strike": strike,
            "drvOptionType": drv_option_type,
            "requiredData": required_data,
            "fromDate": from_date,
            "toDate": to_date,
            "interval": interval,
        }
        return self._http.post("/charts/rollingoption", data=payload, bucket="history")

    def get_live_pnl(self) -> float:
        return self._portfolio.get_live_pnl()

    def get_positions_summary(self) -> dict[str, Any]:
        return self._portfolio.get_positions_summary()

    def get_exchange_time(self) -> str:
        data = self._http.get("/exchange/time", bucket="portfolio")
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            return data.get("exchangeTime", data.get("time", data.get("dateTime", "")))
        return str(data)
