from __future__ import annotations

import datetime
import logging
from typing import Any

import mibian

logger = logging.getLogger(__name__)


class GreeksCalculationError(Exception):
    """Raised when options greeks calculation fails."""


class GreeksCalculator:
    """Options greeks calculator using mibian's Black-Scholes implementation.

    Wraps mibian.BS to compute delta, gamma, theta, vega, rho, and
    implied volatility for equity/index options.

    mibian conventions:
    - volatility: percentage (15 = 15%)
    - interestRate: decimal (0.1 = 10%)
    - daysToExpiration: calendar days
    """

    def __init__(
        self,
        http_client: Any = None,
        option_chain: Any = None,
    ) -> None:
        self._http = http_client
        self._option_chain = option_chain

    def calculate_greeks(
        self,
        underlying_price: float,
        strike: float,
        days_to_expiry: int,
        option_type: str,
        interest_rate: float = 0.1,
        volatility: float | None = None,
    ) -> dict[str, float]:
        """Calculate options greeks using Black-Scholes.

        Args:
            underlying_price: Current price of the underlying asset.
            strike: Option strike price.
            days_to_expiry: Calendar days until expiry (>= 1).
            option_type: "CE"/"CALL"/"C" or "PE"/"PUT"/"P".
            interest_rate: Risk-free rate as decimal (default 0.1 = 10%).
            volatility: Implied volatility as decimal (default 0.15 = 15%).
                        Pass ``None`` to use the default 15 %.

        Returns:
            Dict with keys: delta, gamma, theta, vega, rho, iv,
            call_price, put_price.
        """
        dte = max(int(days_to_expiry), 1)
        vol_dec = volatility if volatility is not None else 0.15
        mibian_vol = max(vol_dec, 0.0001) * 100

        bs = mibian.BS(
            [underlying_price, strike, interest_rate, dte],
            volatility=mibian_vol,
        )

        is_call = option_type.upper() in ("CE", "CALL", "C")

        return {
            "delta": bs.callDelta if is_call else bs.putDelta,
            "gamma": bs.gamma,
            "theta": bs.callTheta if is_call else bs.putTheta,
            "vega": bs.vega,
            "rho": bs.callRho if is_call else bs.putRho,
            "iv": mibian_vol,
            "call_price": bs.callPrice,
            "put_price": bs.putPrice,
        }

    def calculate_from_chain(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        option_type: str,
        exchange: str = "NSE",
    ) -> dict[str, float] | None:
        """Calculate greeks using live data from the Dhan option chain.

        Fetches the option chain and underlying LTP, then computes
        greeks locally via mibian.

        Args:
            symbol: Underlying symbol (e.g. "NIFTY", "RELIANCE").
            expiry: Expiry date string (ISO format, e.g. "2024-12-26").
            strike: Strike price to evaluate.
            option_type: "CE" or "PE".

        Returns:
            Greeks dict, or ``None`` on any error.
        """
        try:
            if self._option_chain is None:
                return None

            chain = self._option_chain.get_option_chain(
                symbol, exchange, expiry=expiry
            )
            side = option_type.lower()

            # First try: use greeks directly from Dhan API (real market greeks)
            for entry in chain.get("strikes", []):
                if abs(entry["strike"] - strike) < 0.001:
                    leg = entry.get(side)
                    if leg is not None:
                        chain_greeks = {
                            "delta": leg.get("delta"),
                            "gamma": leg.get("gamma"),
                            "theta": leg.get("theta"),
                            "vega": leg.get("vega"),
                            "rho": leg.get("rho", 0),
                            "iv": leg.get("iv"),
                            "ltp": leg.get("ltp"),
                            "source": "chain",
                        }
                        if all(chain_greeks[k] is not None for k in ("delta", "gamma", "theta", "vega", "iv")):
                            return chain_greeks
                    break

            # Second try: compute locally via Black-Scholes if LTP available
            underlying_price: float | None = None
            try:
                underlying_price = self._option_chain._ltp_for(symbol, exchange)
            except Exception:
                pass

            if underlying_price is not None:
                days = self._days_to_expiry(expiry)
                market_price: float | None = None
                chain_iv: float | None = None

                for entry in chain.get("strikes", []):
                    if abs(entry["strike"] - strike) < 0.001:
                        leg = entry.get(side)
                        if leg is not None:
                            ltp = leg.get("ltp", 0)
                            market_price = float(ltp) if ltp else None
                            civ = leg.get("iv")
                            chain_iv = float(civ) if civ else None
                        break

                if market_price is not None and market_price > 0:
                    vol = self.implied_volatility(
                        underlying_price, strike, days, option_type, market_price,
                    )
                elif chain_iv is not None:
                    vol = chain_iv
                else:
                    vol = None

                return self.calculate_greeks(
                    underlying_price=underlying_price,
                    strike=strike,
                    days_to_expiry=days,
                    option_type=option_type,
                    volatility=(vol / 100) if vol is not None else None,
                )

            return None
        except Exception:
            logger.exception("calculate_from_chain_failed")
            return None

    def implied_volatility(
        self,
        underlying_price: float,
        strike: float,
        days_to_expiry: int,
        option_type: str,
        market_price: float,
        interest_rate: float = 0.1,
    ) -> float:
        """Compute implied volatility from market price.

        Uses mibian's iterative solver to find the volatility that
        matches the option's market price.

        Args:
            underlying_price: Current underlying price.
            strike: Strike price.
            days_to_expiry: Calendar days to expiry (>= 1).
            option_type: "CE"/"CALL" or "PE"/"PUT".
            market_price: Observed market price of the option.
            interest_rate: Risk-free rate as decimal.

        Returns:
            Implied volatility as a percentage (e.g. 15.0 for 15 %).

        Raises:
            GreeksCalculationError: If the solver cannot converge.
        """
        dte = max(int(days_to_expiry), 1)
        is_call = option_type.upper() in ("CE", "CALL", "C")

        if is_call:
            bs = mibian.BS(
                [underlying_price, strike, interest_rate, dte],
                callPrice=market_price,
            )
        else:
            bs = mibian.BS(
                [underlying_price, strike, interest_rate, dte],
                putPrice=market_price,
            )

        iv = bs.impliedVolatility
        if iv is None:
            raise GreeksCalculationError(
                f"Could not compute IV for {option_type} @ {strike}"
            )
        return iv

    @staticmethod
    def _days_to_expiry(expiry: str) -> int:
        """Calculate calendar days from today to the expiry date."""
        try:
            exp = datetime.datetime.strptime(expiry, "%Y-%m-%d").date()
            days = (exp - datetime.date.today()).days
            return max(days, 1)
        except (ValueError, TypeError):
            return 1
