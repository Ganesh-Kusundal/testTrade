"""GateFSM must default to fail-safe — all guards default to blocked."""
from decimal import Decimal
from scalpr.signals.gate_fsm import GateFSM, GateState


def test_gate_state_should_default_to_all_guards_blocked():
    """Default GateState must fail all guards except market_open."""
    state = GateState(symbol="RELIANCE", price=Decimal("2500"), cvd_falling=False, is_at_lvn=False)
    passed, reason, results = GateFSM.evaluate(state)
    assert not passed, "Default state should NOT pass — gates must fail-safe"


def test_only_explicitly_satisfied_gates_should_pass():
    """Only gates explicitly set to True should pass."""
    state = GateState(
        symbol="RELIANCE", price=Decimal("2500"),
        cvd_falling=False, is_at_lvn=True,
        market_open=True, trend_aligned=True,
        vol_spike=True, atr_ok=True,
        spread_ok=True, oi_ok=True,
        under_daily_cap=True,
    )
    passed, reason, results = GateFSM.evaluate(state)
    assert passed, "All gates explicitly satisfied — should pass"
    assert len(results) == 8
    assert all(r.passed for r in results)
