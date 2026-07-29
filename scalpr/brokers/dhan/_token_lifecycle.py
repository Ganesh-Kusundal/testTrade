"""Token broadcast + background refresh scheduler.

TokenBroadcast notifies live connections (e.g. WebSocket) when the token
changes, so they reconnect with the fresh token instead of discovering
the stale one on their next operation.

TokenRefreshScheduler is a daemon thread that calls ensure_token() on an
interval. Since ensure_token() is probe-before-mint, a tick that finds
the token still valid is a no-op — this never mints proactively, only
checks. Broadcasts only when the token actually changed.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class TokenBroadcast:
    """Registry of token receivers + broadcast.

    One instance per broker token manager. Strong references — a token
    manager lives exactly as long as its broker connection, with at most
    a couple of receivers registered once for that same lifetime.
    """

    def __init__(self) -> None:
        self._receivers: list[Callable[[str], None]] = []

    def register(self, receiver: Callable[[str], None]) -> Callable[[str], None]:
        """Idempotent: registering the same callable twice is a no-op."""
        if receiver not in self._receivers:
            self._receivers.append(receiver)
        return receiver

    def unregister(self, receiver: Callable[[str], None]) -> None:
        if receiver in self._receivers:
            self._receivers.remove(receiver)

    def unregister_all(self) -> int:
        """Remove all receivers. Returns count removed."""
        count = len(self._receivers)
        self._receivers.clear()
        return count

    def broadcast(self, new_token: str) -> int:
        """Push new_token to every receiver; isolate per-receiver failures."""
        if not new_token:
            return 0
        delivered = 0
        for receiver in list(self._receivers):
            try:
                receiver(new_token)
                delivered += 1
            except Exception as exc:
                logger.warning(
                    "token_receiver_failed",
                    extra={
                        "receiver": getattr(receiver, "__qualname__", repr(receiver)),
                        "error": str(exc),
                    },
                )
        return delivered

    @property
    def receiver_count(self) -> int:
        return len(self._receivers)


class TokenRefreshScheduler:
    """Background daemon that calls ensure_token() on an interval.

    Non-forcing: ensure_token() is probe-before-mint, so a tick that finds
    the current token still valid is a no-op. Broadcasts only when the
    token actually changed.
    """

    def __init__(
        self,
        broker_id: str,
        ensure_token_fn: Callable[[], str],
        current_token_fn: Callable[[], str],
        *,
        broadcast: TokenBroadcast | None = None,
        interval_seconds: float = 300.0,
    ) -> None:
        self.broker_id = broker_id
        self._ensure_token_fn = ensure_token_fn
        self._current_token_fn = current_token_fn
        self._broadcast = broadcast
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._refresh_count = 0
        self._error_count = 0

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"token-refresh-{self.broker_id}")
        self._thread.start()

    def stop(self, timeout_seconds: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop_event.wait(self._interval):
            self.refresh_now()

    def refresh_now(self) -> bool:
        before = self._current_token_fn()
        try:
            after = self._ensure_token_fn()
            self._refresh_count += 1
            if self._broadcast is not None and after and after != before:
                self._broadcast.broadcast(after)
            return True
        except Exception as exc:
            self._error_count += 1
            logger.warning(
                "token_refresh_scheduler_failed",
                extra={"broker_id": self.broker_id, "error": str(exc)},
            )
            return False

    @property
    def refresh_count(self) -> int:
        return self._refresh_count

    @property
    def error_count(self) -> int:
        return self._error_count
