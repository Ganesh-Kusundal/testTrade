from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from scalpr.domain.fill import Fill
from scalpr.domain.instrument import Exchange
from scalpr.domain.order import Order, OrderSide, OrderState, OrderType
from scalpr.domain.position import Position, PositionSide, PositionState


class OmsRepository:
    """SQLite persistence layer for Order Management System state, with WAL mode enabled."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and enable Write-Ahead Logging (WAL) mode."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")

            # Orders Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    exchange TEXT,
                    side TEXT,
                    order_type TEXT,
                    quantity INTEGER,
                    price TEXT,
                    trigger_price TEXT,
                    state TEXT,
                    filled_quantity INTEGER,
                    avg_price TEXT,
                    timestamp TEXT,
                    product_type TEXT,
                    validity TEXT,
                    reject_reason TEXT,
                    correlation_id TEXT
                )
            """)

            # Fills Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fills (
                    fill_id TEXT PRIMARY KEY,
                    order_id TEXT,
                    symbol TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price TEXT,
                    timestamp TEXT
                )
            """)

            # Positions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    exchange TEXT,
                    quantity INTEGER,
                    avg_price TEXT,
                    ltp TEXT,
                    unrealised_pnl TEXT,
                    realised_pnl TEXT,
                    position_side TEXT,
                    state TEXT
                )
            """)

            # General state table (e.g. daily PnL, balance)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oms_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            conn.commit()
        finally:
            conn.close()

    def save_order(self, order: Order) -> None:
        """Persist or update an order in the database."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO orders (
                    order_id, symbol, exchange, side, order_type, quantity, price, 
                    trigger_price, state, filled_quantity, avg_price, timestamp, 
                    product_type, validity, reject_reason, correlation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.symbol,
                    order.exchange.value,
                    order.side.value,
                    order.order_type.value,
                    order.quantity,
                    str(order.price),
                    str(order.trigger_price),
                    order.state.value,
                    order.filled_quantity,
                    str(order.avg_price),
                    order.timestamp.isoformat() if order.timestamp else None,
                    order.product_type,
                    order.validity,
                    order.reject_reason,
                    order.correlation_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_fill(self, fill: Fill) -> None:
        """Persist an execution fill."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO fills (
                    fill_id, order_id, symbol, side, quantity, price, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill.fill_id,
                    fill.order_id,
                    fill.symbol,
                    fill.side.value,
                    fill.quantity,
                    str(fill.price),
                    fill.timestamp.isoformat() if fill.timestamp else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_position(self, position: Position) -> None:
        """Persist open position parameters."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO positions (
                    symbol, exchange, quantity, avg_price, ltp, unrealised_pnl, realised_pnl, position_side, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.symbol,
                    position.exchange.value,
                    position.quantity,
                    str(position.avg_price),
                    str(position.ltp),
                    str(position.unrealised_pnl),
                    str(position.realised_pnl),
                    position.position_side.value,
                    position.state.value,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def restore_orders(self) -> dict[str, Order]:
        """Restore all order records from database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders")
            orders = {}
            for row in cursor.fetchall():
                ts = datetime.fromisoformat(row[11]) if row[11] else None
                order = Order(
                    order_id=row[0],
                    symbol=row[1],
                    exchange=Exchange(row[2]),
                    side=OrderSide(row[3]),
                    order_type=OrderType(row[4]),
                    quantity=row[5],
                    price=Decimal(row[6]),
                    trigger_price=Decimal(row[7]),
                    state=OrderState(row[8]),
                    filled_quantity=row[9],
                    avg_price=Decimal(row[10]),
                    timestamp=ts,
                    product_type=row[12],
                    validity=row[13],
                    reject_reason=row[14],
                    correlation_id=row[15],
                )
                orders[order.order_id] = order
            return orders
        finally:
            conn.close()

    def restore_positions(self) -> dict[str, Position]:
        """Restore all position records from database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions")
            positions = {}
            for row in cursor.fetchall():
                pos = Position(
                    symbol=row[0],
                    exchange=Exchange(row[1]),
                    quantity=row[2],
                    avg_price=Decimal(row[3]),
                    ltp=Decimal(row[4]),
                    unrealised_pnl=Decimal(row[5]),
                    realised_pnl=Decimal(row[6]),
                    position_side=PositionSide(row[7]),
                    state=PositionState(row[8]),
                )
                positions[pos.symbol] = pos
            return positions
        finally:
            conn.close()
