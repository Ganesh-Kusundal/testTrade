"""Integration tests for OMS persistence wiring."""

import os
import tempfile
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from scalpr.oms.persistence import OmsRepository
from scalpr.oms.order_manager import OrderManager
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange


class TestOMSPersistenceWiring:
    """Test OMS persistence integration with OrderManager."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def repository(self, temp_db):
        """Create OmsRepository instance."""
        return OmsRepository(temp_db)

    @pytest.fixture
    def order_manager_with_persistence(self, repository):
        """Create OrderManager with persistence."""
        return OrderManager(repository=repository)

    @pytest.fixture
    def sample_order(self):
        """Create a sample order for testing."""
        return Order(
            order_id="TEST-001",
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
            price=Decimal("2500.00"),
            trigger_price=Decimal("0"),
            state=OrderState.PENDING,
            filled_quantity=0,
            avg_price=Decimal("0"),
            timestamp=datetime.now(timezone.utc),
            product_type="MIS",
            validity="DAY",
        )

    @pytest.fixture
    def sample_fill(self, sample_order):
        """Create a sample fill."""
        return Fill(
            fill_id="FILL-001",
            order_id=sample_order.order_id,
            symbol=sample_order.symbol,
            side=sample_order.side,
            quantity=100,
            price=Decimal("2500.50"),
            timestamp=datetime.now(timezone.utc),
        )

    def test_order_persisted_on_add(self, order_manager_with_persistence, sample_order):
        """Verify order is persisted to database when added."""
        order_manager_with_persistence.add_order(sample_order)
        
        # Verify in-memory
        assert sample_order.order_id in order_manager_with_persistence.orders
        
        # Verify in database
        restored = order_manager_with_persistence._repository.restore_orders()
        assert sample_order.order_id in restored
        assert restored[sample_order.order_id].symbol == "RELIANCE"

    def test_fill_persisted_on_process(self, order_manager_with_persistence, sample_order, sample_fill):
        """Verify fill is persisted when processed."""
        # Add order first
        order_manager_with_persistence.add_order(sample_order)
        
        # Process fill
        updated_order = order_manager_with_persistence.process_fill(sample_fill)
        
        # Verify fill persisted
        fills = order_manager_with_persistence.fills[sample_order.order_id]
        assert len(fills) == 1
        assert fills[0].fill_id == "FILL-001"
        
        # Verify order updated in DB
        restored = order_manager_with_persistence._repository.restore_orders()
        restored_order = restored[sample_order.order_id]
        assert restored_order.filled_quantity == 100
        assert restored_order.state == OrderState.FILLED

    def test_crash_recovery(self, order_manager_with_persistence, sample_order, sample_fill, temp_db):
        """Test that orders survive process restart (crash recovery)."""
        # Simulate: Add order and process fill
        order_manager_with_persistence.add_order(sample_order)
        order_manager_with_persistence.process_fill(sample_fill)
        
        # Simulate crash: Create new OrderManager with same DB
        repository2 = OmsRepository(temp_db)
        order_manager2 = OrderManager(repository=repository2)
        
        # Restore state
        order_manager2.restore_state()
        
        # Verify order recovered
        assert sample_order.order_id in order_manager2.orders
        recovered_order = order_manager2.orders[sample_order.order_id]
        assert recovered_order.symbol == "RELIANCE"
        assert recovered_order.filled_quantity == 100

    def test_persistence_failure_doesnt_break_order_flow(self, sample_order):
        """Verify that persistence failure doesn't break order submission."""
        # Create OrderManager without repository (simulates persistence failure)
        order_manager = OrderManager(repository=None)
        
        # Should still work
        order_manager.add_order(sample_order)
        assert sample_order.order_id in order_manager.orders

    def test_multiple_orders_persisted(self, order_manager_with_persistence):
        """Test multiple orders are all persisted."""
        orders = []
        for i in range(5):
            order = Order(
                order_id=f"TEST-{i:03d}",
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=100,
                price=Decimal("2500.00"),
                trigger_price=Decimal("0"),
                state=OrderState.PENDING,
                filled_quantity=0,
                avg_price=Decimal("0"),
                timestamp=datetime.now(timezone.utc),
                product_type="MIS",
                validity="DAY",
            )
            orders.append(order)
            order_manager_with_persistence.add_order(order)
        
        # Verify all persisted
        restored = order_manager_with_persistence._repository.restore_orders()
        assert len(restored) == 5
        
        for order in orders:
            assert order.order_id in restored

    def test_get_orders_returns_list(self, order_manager_with_persistence, sample_order):
        """Test get_orders returns list of orders."""
        order_manager_with_persistence.add_order(sample_order)
        
        orders_list = order_manager_with_persistence.get_orders()
        assert isinstance(orders_list, list)
        assert len(orders_list) == 1
        assert orders_list[0].order_id == sample_order.order_id

    def test_restore_state_with_empty_database(self, temp_db):
        """Test restore_state works with empty database."""
        repository = OmsRepository(temp_db)
        order_manager = OrderManager(repository=repository)
        
        # Should not raise
        order_manager.restore_state()
        
        # Should have empty orders
        assert len(order_manager.orders) == 0

    def test_order_update_persisted(self, order_manager_with_persistence, sample_order):
        """Test that order state transitions are persisted."""
        order_manager_with_persistence.add_order(sample_order)
        
        # Update state
        order_manager_with_persistence.update_order_state(
            sample_order.order_id,
            OrderState.OPEN
        )
        
        # Verify persisted
        restored = order_manager_with_persistence._repository.restore_orders()
        restored_order = restored[sample_order.order_id]
        assert restored_order.state == OrderState.OPEN
