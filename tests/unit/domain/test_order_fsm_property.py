"""Property-based tests for Order state machine."""
from decimal import Decimal

import pytest

from scalpr.domain.instrument import Exchange
from scalpr.domain.order import ORDER_STATE_TRANSITIONS, Order, OrderSide, OrderState, OrderType


def _make_order(state=OrderState.PENDING):
    return Order(
        order_id="prop_test", symbol="RELIANCE", exchange=Exchange.NSE,
        side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=10, price=Decimal("2500"), state=state,
    )


class TestOrderFSMProperties:
    """Property-based verification of order state machine invariants."""

    def test_terminal_states_have_no_valid_transitions(self):
        """Terminal states must have no outgoing transitions."""
        terminal_states = {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED}
        for state in terminal_states:
            valid_targets = ORDER_STATE_TRANSITIONS.get(state, frozenset())
            assert len(valid_targets) == 0, f"Terminal state {state} has transitions to {valid_targets}"

    def test_invalid_transition_always_raises(self):
        """Any transition not in ORDER_STATE_TRANSITIONS must raise ValueError."""
        order = _make_order(OrderState.PENDING)
        for target in OrderState:
            if target in ORDER_STATE_TRANSITIONS.get(OrderState.PENDING, frozenset()):
                result = order.transition_to(target)
                assert result.state == target
            else:
                with pytest.raises(ValueError, match="Invalid transition"):
                    order.transition_to(target)

    def test_transition_returns_new_order(self):
        """transition_to must return a new Order, not mutate the original."""
        order = _make_order(OrderState.PENDING)
        new_order = order.transition_to(OrderState.OPEN)
        assert new_order is not order
        assert order.state == OrderState.PENDING  # Original unchanged
        assert new_order.state == OrderState.OPEN

    def test_all_non_terminal_states_can_reach_a_terminal(self):
        """Every non-terminal state must have a path to at least one terminal state."""
        terminal_states = {OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED}

        def can_reach_terminal(state, visited=None):
            if state in terminal_states:
                return True
            if visited is None:
                visited = set()
            if state in visited:
                return False
            visited.add(state)
            for target in ORDER_STATE_TRANSITIONS.get(state, frozenset()):
                if can_reach_terminal(target, visited):
                    return True
            return False

        for state in OrderState:
            if state not in terminal_states:
                assert can_reach_terminal(state), f"State {state} cannot reach any terminal state"
