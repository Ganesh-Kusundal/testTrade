"""Async-safe trace context for SCALPR trading platform."""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone


# Async-safe trace context variables
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
current_tick_id: ContextVar[str] = ContextVar("tick_id", default="")


@dataclass
class TraceContext:
    """Trace context for correlating tick → signal → order → fill lifecycle."""
    
    trace_id: str
    tick_id: str
    symbol: str
    start_time: datetime
    
    @classmethod
    def start(cls, symbol: str) -> "TraceContext":
        """Start new trace context for a tick.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE-EQ")
            
        Returns:
            New TraceContext instance
        """
        ctx = cls(
            trace_id=str(uuid.uuid4())[:8],
            tick_id=str(uuid.uuid4()),
            symbol=symbol,
            start_time=datetime.now(timezone.utc)
        )
        current_trace_id.set(ctx.trace_id)
        current_tick_id.set(ctx.tick_id)
        return ctx
    
    def get_trace_id(self) -> str:
        """Get current trace ID from context."""
        return current_trace_id.get()
    
    def get_tick_id(self) -> str:
        """Get current tick ID from context."""
        return current_tick_id.get()
