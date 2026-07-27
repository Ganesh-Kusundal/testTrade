"""Gateway capability declarations for broker feature discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayCapabilities:
    """Declares supported operations and features for a broker gateway.

    Each gateway implementation should define its capabilities to allow
    consumers to discover available features at runtime.
    """

    # Trading capabilities
    live_trading: bool = False
    modify_order: bool = True
    cancel_order: bool = True
    square_off: bool = True
    slice_orders: bool = False
    bracket_orders: bool = False
    cover_orders: bool = False

    # Market data capabilities
    streaming: bool = False
    depth_20: bool = False
    depth_200: bool = False
    option_chain: bool = False
    future_chain: bool = False
    historical_data: bool = True
    max_intraday_days: int = 1
    max_daily_days: int = 365

    # Portfolio capabilities
    get_holdings: bool = True
    get_positions: bool = True
    get_fund_limits: bool = True
    get_tradebook: bool = True

    # Advanced features
    conditional_triggers: bool = False
    super_orders: bool = False
    forever_orders: bool = False
    amo: bool = False
    market_protection: bool = False
    ledger: bool = False
    user_profile: bool = False
    ip_management: bool = False
    edis: bool = False
    exit_all: bool = False
    trade_pnl: bool = False
    convert_position: bool = False
    ipo: bool = False
    mutual_funds: bool = False
    fundamentals: bool = False
    payments: bool = False

    # Rate limits
    rate_limit_per_second: int = 25
    rate_limit_per_minute: int = 1500
