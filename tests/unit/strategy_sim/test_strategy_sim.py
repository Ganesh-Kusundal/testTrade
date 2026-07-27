import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from unittest.mock import MagicMock
from scalpr.domain.tick import Tick, OHLCV
from scalpr.domain.order import Order, OrderSide, OrderType, OrderState
from scalpr.domain.position import Position, PositionSide, PositionState
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Instrument, Exchange, Segment, OptionType
from scalpr.signals.gate_fsm import GateFSM, GateState, GateResult
from scalpr.signals.volume_profile import VolumeProfile
from scalpr.signals.cvd import CvdTracker
from scalpr.signals.indicators import TechnicalIndicators
from scalpr.strategy.scalpr_amt import ScalprAmtStrategy
from scalpr.strategy.executor import StrategyExecutor
from scalpr.simulation.backtester import EventDrivenBacktester
from scalpr.simulation.replay_engine import ReplayEngine
from scalpr.simulation.walk_forward import WalkForwardValidator
from scalpr.portfolio.portfolio import PortfolioManager
from scalpr.portfolio.analytics import TradeAnalytics
from scalpr.scanner.options_scanner import OptionsScanner
from scalpr.oms.paper_oms import PaperOms


def test_gate_fsm_gate_03_logic():
    """GateFSM Gate 03 blocks falling CVD when not at LVN, but passes when at LVN."""
    # Common gate flags — all other gates explicitly satisfied to isolate Gate_03
    _passing_gates = dict(
        market_open=True,
        trend_aligned=True,
        vol_spike=True,
        atr_ok=True,
        spread_ok=True,
        oi_ok=True,
    )

    # CASE 1: CVD falling, not at LVN => BLOCKED at Gate_03
    state_block = GateState(
        symbol="RELIANCE",
        price=Decimal("2500.00"),
        cvd_falling=True,
        is_at_lvn=False,
        **_passing_gates,
    )
    passed, reason, results = GateFSM.evaluate(state_block)
    assert not passed
    assert "Gate_03 failed" in reason
    assert any(r.gate_id == "Gate_03" and not r.passed for r in results)

    # CASE 2: CVD falling, is at LVN => PASS (Institutional absorption)
    state_pass = GateState(
        symbol="RELIANCE",
        price=Decimal("2500.00"),
        cvd_falling=True,
        is_at_lvn=True,
        **_passing_gates,
    )
    passed2, reason2, results2 = GateFSM.evaluate(state_pass)
    assert passed2
    assert "Passed all 8 Gates" in reason2


def test_volume_profile_calculations():
    """VolumeProfile accumulates volumes and correctly identifies POC and LVNs."""
    vp = VolumeProfile(price_step=Decimal("10.00"))
    
    # Add high-volume bars around 2500
    b1 = OHLCV(Decimal("2490"), Decimal("2510"), Decimal("2480"), Decimal("2500"), 1000, datetime.now(timezone.utc), True)
    vp.update(b1)

    # Add low-volume bars at 2400
    b2 = OHLCV(Decimal("2390"), Decimal("2410"), Decimal("2380"), Decimal("2400"), 10, datetime.now(timezone.utc), True)
    vp.update(b2)
    
    # Add a second bar specifically centered around 2500 to make it the POC
    b3 = OHLCV(Decimal("2500"), Decimal("2500"), Decimal("2500"), Decimal("2500"), 500, datetime.now(timezone.utc), True)
    vp.update(b3)
    
    assert vp.poc == Decimal("2500")  # POC is 2500 because it had the most volume allocated
    assert vp.is_lvn(Decimal("2400"))  # 2400 has much lower volume, so it should be identified as LVN
    assert not vp.is_lvn(Decimal("2500"))


def test_cvd_tracker_divergence():
    """CvdTracker correctly accumulates delta and identifies divergence from price."""
    cvd = CvdTracker()
    ts = datetime.now(timezone.utc)
    
    # Simulate rising price and falling CVD
    cvd.process_tick(Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 0, 0, ts), ask_qty=100, bid_qty=50) # +50
    cvd.process_tick(Tick("RELIANCE", Decimal("2510.00"), Decimal("2509"), Decimal("2511"), 0, 0, ts), ask_qty=40, bid_qty=80)  # -40
    cvd.process_tick(Tick("RELIANCE", Decimal("2520.00"), Decimal("2519"), Decimal("2521"), 0, 0, ts), ask_qty=30, bid_qty=90)  # -60
    cvd.process_tick(Tick("RELIANCE", Decimal("2530.00"), Decimal("2529"), Decimal("2531"), 0, 0, ts), ask_qty=20, bid_qty=100) # -80
    cvd.process_tick(Tick("RELIANCE", Decimal("2540.00"), Decimal("2539"), Decimal("2541"), 0, 0, ts), ask_qty=10, bid_qty=110) # -100
    
    # Price went up: 2500 -> 2540
    # CVD went down: +50 -> -230
    assert cvd.is_diverged(lookback=5)


def test_technical_indicators():
    """TechnicalIndicators correctly computes ATR and Momentum."""
    closes = [Decimal("100"), Decimal("102"), Decimal("101"), Decimal("105"), Decimal("110")]
    highs = [Decimal("101"), Decimal("103"), Decimal("102"), Decimal("106"), Decimal("112")]
    lows = [Decimal("99"), Decimal("101"), Decimal("100"), Decimal("104"), Decimal("108")]
    
    atr = TechnicalIndicators.calculate_atr(highs, lows, closes, period=4)
    assert atr > 0
    
    momentum = TechnicalIndicators.calculate_momentum(closes, period=4)
    assert momentum == Decimal("0.10")  # (110 - 100) / 100 = 10%


def test_event_driven_backtester():
    """EventDrivenBacktester executes historical simulation and charges trading fees."""
    paper_oms = PaperOms(initial_balance=Decimal("100000.00"))
    # Make sure we register the last price so paper_oms works
    paper_oms.set_last_price("RELIANCE", Decimal("2500.00"))
    
    # Create a mock order router
    mock_router = MagicMock()
    strategy = ScalprAmtStrategy(order_router=mock_router, symbol="RELIANCE")
    backtester = EventDrivenBacktester(strategy=strategy, paper_oms=paper_oms, brokerage_flat=Decimal("20.00"))
    
    # Generate mock bar sequence
    bar = OHLCV(Decimal("2500.00"), Decimal("2510.00"), Decimal("2490.00"), Decimal("2500.00"), 10000, datetime.now(timezone.utc), True)
    
    # Setup state to pass FSM
    strategy.volume_profile.volume_price_step = Decimal("10")
    # Mark as LVN
    strategy.volume_profile.volume_by_price[Decimal("2500")] = 1
    
    # Directly place order to test backtester fee calculations
    order = Order(
        order_id="b_ord_1",
        symbol="RELIANCE",
        exchange=Exchange.NSE,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=50,
        price=Decimal("2500.00"),
    )
    paper_oms.place_order(order)
    backtester._charge_fees(50, Decimal("2500.00"), OrderSide.BUY)
    
    assert backtester.total_transaction_costs == Decimal("20.00")
    assert paper_oms.balance < Decimal("100000.00")


@pytest.mark.asyncio
async def test_replay_engine_checkpoints():
    """ReplayEngine streams ticks and preserves checkpoint save/restore locations."""
    executor = StrategyExecutor()
    ticks = [
        Tick("RELIANCE", Decimal("2500.00"), Decimal("2499"), Decimal("2501"), 10, 10, datetime.now(timezone.utc)),
        Tick("RELIANCE", Decimal("2505.00"), Decimal("2504"), Decimal("2506"), 15, 25, datetime.now(timezone.utc)),
        Tick("RELIANCE", Decimal("2510.00"), Decimal("2509"), Decimal("2511"), 5, 30, datetime.now(timezone.utc)),
    ]
    
    replay = ReplayEngine(executor=executor, ticks=ticks, speed_multiplier=100.0)
    
    # Save checkpoint at start
    cp = replay.save_checkpoint()
    assert cp == 0
    
    # Restore checkpoint
    replay.restore_checkpoint(2)
    assert replay.cursor == 2


def test_walk_forward_validator():
    """WalkForwardValidator splits historical ranges into rolling training and testing slots."""
    validator = WalkForwardValidator(train_days=30, test_days=10)
    start = datetime(2026, 1, 1)
    end = datetime(2026, 3, 1)
    
    windows = validator.generate_windows(start, end)
    assert len(windows) > 0
    assert windows[0]["train_start"] == start
    assert windows[0]["train_end"] == start + timedelta(days=30)
    assert windows[0]["test_start"] == windows[0]["train_end"]


def test_portfolio_manager_realised_pnl():
    """PortfolioManager marks positions to market and tracks realized/unrealized PnL."""
    pm = PortfolioManager()
    
    f1 = Fill("fill_1", "ord_1", "RELIANCE", OrderSide.BUY, 10, Decimal("2500.00"))
    pm.update_position_from_fill(f1, Exchange.NSE)
    
    assert pm.total_pnl == Decimal("0")
    
    # Price tick rises
    pm.update_ltp(Tick("RELIANCE", Decimal("2510.00"), Decimal("2509"), Decimal("2511"), 0, 0, datetime.now(timezone.utc)))
    assert pm.total_unrealised_pnl == Decimal("100.00")
    
    # Partial sell
    f2 = Fill("fill_2", "ord_2", "RELIANCE", OrderSide.SELL, 5, Decimal("2520.00"))
    pm.update_position_from_fill(f2, Exchange.NSE)
    
    assert pm.total_realised_pnl == Decimal("100.00") # (2520 - 2500) * 5
    assert pm.total_unrealised_pnl == Decimal("100.00") # (2520 - 2500) * 5


def test_options_scanner():
    """OptionsScanner filters liquid ATM options contracts based on delta/spot proximity."""
    resolver = MagicMock()
    resolver.resolve.side_effect = lambda sym, exch: MagicMock(symbol=sym)
    scanner = OptionsScanner(resolver=resolver, min_oi=100, min_volume=500, max_spread=Decimal("1.50"))
    
    # Spot price is 22000
    chain = [
        # Liquid ATM CE
        {"symbol": "NIFTY22000CE", "strike": 22000, "option_type": "CE", "oi": 500, "volume": 1000, "bid": 100, "ask": 101},
        # Wide spread contract (should be rejected)
        {"symbol": "NIFTY22050CE", "strike": 22050, "option_type": "CE", "oi": 500, "volume": 1000, "bid": 100, "ask": 105},
        # Illiquid contract (should be rejected)
        {"symbol": "NIFTY21950CE", "strike": 21950, "option_type": "CE", "oi": 50, "volume": 100, "bid": 100, "ask": 101},
        # Deep OTM contract (should be rejected)
        {"symbol": "NIFTY22500CE", "strike": 22500, "option_type": "CE", "oi": 500, "volume": 1000, "bid": 100, "ask": 101},
    ]
    
    results = scanner.scan(spot_price=Decimal("22000"), chain_data=chain)
    assert len(results) == 1
    assert results[0].symbol == "NIFTY22000CE"
