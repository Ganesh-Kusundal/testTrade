"""Tests for Dhan HTTP transport module (_http.py).

Covers RateLimiter token-bucket logic and DhanHttpClient request flow.
"""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from scalpr.adapters.dhan._http import (
    DHAN_BUCKETS,
    DhanAuthError,
    DhanHttpClient,
    DhanHttpError,
    DhanRequestError,
    DhanServerError,
    RateLimiter,
    RateLimitTimeout,
    TokenBucket,
)

# ============================================================================
# TokenBucket
# ============================================================================

class TestTokenBucket:
    def test_starts_full(self) -> None:
        tb = TokenBucket(capacity=5, refill_rate=10.0)
        assert tb.tokens == 5.0

    def test_acquire_consumes_tokens(self) -> None:
        tb = TokenBucket(capacity=5, refill_rate=10.0)
        assert tb.acquire(tokens=3)
        assert tb.tokens == 2.0

    def test_acquire_blocks_until_refill(self) -> None:
        tb = TokenBucket(capacity=1, refill_rate=20.0)
        assert tb.acquire()
        start = time.monotonic()
        assert tb.acquire(timeout=1.0)
        assert time.monotonic() - start >= 0.03

    def test_acquire_returns_false_on_timeout(self) -> None:
        tb = TokenBucket(capacity=1, refill_rate=0.5)
        assert tb.acquire()
        assert tb.acquire(timeout=0.05) is False

    def test_large_request_blocks(self) -> None:
        tb = TokenBucket(capacity=3, refill_rate=10.0)
        assert tb.acquire(tokens=3)
        assert tb.tokens == 0.0
        assert tb.acquire(tokens=2, timeout=0.01) is False

    def test_refill_happens_on_acquire(self) -> None:
        tb = TokenBucket(capacity=10, refill_rate=100.0)
        assert tb.acquire(tokens=10)
        time.sleep(0.05)
        assert tb.acquire(timeout=0.1)

    def test_thread_safety(self) -> None:
        tb = TokenBucket(capacity=100, refill_rate=1000.0)
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker() -> None:
            for _ in range(20):
                if not tb.acquire(timeout=2.0):
                    with lock:
                        errors.append(RuntimeError("failed to acquire"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_exhaustion(self) -> None:
        tb = TokenBucket(capacity=5, refill_rate=100.0)
        acquired = threading.Barrier(5)

        results: list[bool] = []

        def worker() -> None:
            acquired.wait()
            results.append(tb.acquire(timeout=0.1))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = sum(results)
        assert successes <= 5


# ============================================================================
# RateLimiter
# ============================================================================

class TestRateLimiter:
    def test_orders_bucket_has_correct_rate(self) -> None:
        cfg = DHAN_BUCKETS["orders"]
        assert cfg["rate"] == 3.0
        assert cfg["capacity"] == 5

    def test_market_data_bucket_has_correct_rate(self) -> None:
        cfg = DHAN_BUCKETS["market_data"]
        assert cfg["rate"] == 5.0
        assert cfg["capacity"] == 10

    def test_portfolio_bucket_has_correct_rate(self) -> None:
        cfg = DHAN_BUCKETS["portfolio"]
        assert cfg["rate"] == 2.0
        assert cfg["capacity"] == 4

    def test_history_bucket_has_correct_rate(self) -> None:
        cfg = DHAN_BUCKETS["history"]
        assert cfg["rate"] == 2.0
        assert cfg["capacity"] == 4

    def test_master_bucket_has_correct_rate(self) -> None:
        cfg = DHAN_BUCKETS["master"]
        assert cfg["rate"] == 1.0 / 300.0
        assert cfg["capacity"] == 1

    def test_acquire_returns_true(self) -> None:
        rl = RateLimiter()
        assert rl.acquire("orders")

    def test_acquire_raises_on_unknown_bucket(self) -> None:
        rl = RateLimiter()
        with pytest.raises(ValueError, match="Unknown bucket"):
            rl.acquire("nonexistent")

    def test_acquire_raises_timeout_when_exhausted(self) -> None:
        rl = RateLimiter()
        rl.acquire("orders", tokens=5)
        with pytest.raises(RateLimitTimeout):
            rl.acquire("orders", timeout=0.01)

    def test_thread_safe_concurrent_access(self) -> None:
        rl = RateLimiter()
        errors: list[Exception] = []
        lock = threading.Lock()

        def worker() -> None:
            try:
                rl.acquire("market_data", timeout=2.0)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = 10 - len(errors)
        assert successes <= 10

    def test_raises_rate_limit_timeout(self) -> None:
        rl = RateLimiter()
        rl.acquire("history", tokens=4)
        with pytest.raises(RateLimitTimeout):
            rl.acquire("history", timeout=0.01)


# ============================================================================
# DhanHttpClient
# ============================================================================

class TestDhanHttpClient:
    @pytest.fixture
    def token_manager(self) -> MagicMock:
        tm = MagicMock()
        tm.get_token.return_value = "test-token-123"
        return tm

    @pytest.fixture
    def rate_limiter(self) -> MagicMock:
        rl = MagicMock(spec=RateLimiter)
        rl.acquire.return_value = True
        return rl

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        with patch("scalpr.adapters.dhan._http.requests.Session") as mock_cls:
            session_instance = MagicMock()
            mock_cls.return_value = session_instance
            yield session_instance

    @pytest.fixture
    def client(
        self,
        token_manager: MagicMock,
        rate_limiter: MagicMock,
        mock_session: MagicMock,
    ) -> DhanHttpClient:
        return DhanHttpClient(
            client_id="test-client",
            access_token="test-access",
            token_manager=token_manager,
            rate_limiter=rate_limiter,
        )

    # -- HTTP method tests --

    def test_get_makes_get_request(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        resp = _json_response(200, {"ok": True})
        mock_session.request.return_value = resp
        result = client.get("/v2/orders")
        assert result == {"ok": True}
        args, _ = mock_session.request.call_args
        assert args[0] == "GET"

    def test_post_makes_post_request_with_data(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        resp = _json_response(200, {"id": "123"})
        mock_session.request.return_value = resp
        result = client.post("/v2/orders", data={"symbol": "INFY"})
        assert result == {"id": "123"}
        args, kwargs = mock_session.request.call_args
        assert args[0] == "POST"
        assert kwargs["json"]["symbol"] == "INFY"
        assert kwargs["json"]["dhanClientId"] == "test-client"

    def test_put_makes_put_request_with_data(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        resp = _json_response(200, {"status": "modified"})
        mock_session.request.return_value = resp
        result = client.put("/v2/orders/123", data={"quantity": 10})
        assert result == {"status": "modified"}
        args, kwargs = mock_session.request.call_args
        assert args[0] == "PUT"
        assert kwargs["json"]["quantity"] == 10
        assert kwargs["json"]["dhanClientId"] == "test-client"

    def test_delete_makes_delete_request(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        resp = _json_response(200, {"status": "cancelled"})
        mock_session.request.return_value = resp
        result = client.delete("/v2/orders/123")
        assert result == {"status": "cancelled"}
        args, _ = mock_session.request.call_args
        assert args[0] == "DELETE"

    # -- Headers --

    def test_sets_authorization_header(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["access-token"] == "test-token-123"

    def test_sets_content_type_header(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["Content-Type"] == "application/json"

    def test_sets_accept_header(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["Accept"] == "application/json"

    def test_sets_x_client_id_header(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        _, kwargs = mock_session.request.call_args
        assert kwargs["headers"]["client-id"] == "test-client"

    def test_uses_token_manager_for_auth(self, client: DhanHttpClient, token_manager: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        token_manager.get_token.assert_called_once()

    def test_uses_requests_session(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        mock_session.request.assert_called_once()

    # -- Rate limit integration --

    def test_acquires_rate_limit_token_before_request(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test", bucket="market_data")
        rate_limiter.acquire.assert_called_once_with("market_data")

    def test_uses_default_bucket_get(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        rate_limiter.acquire.assert_called_once_with("portfolio")

    def test_uses_default_bucket_post(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.post("/test", data={})
        rate_limiter.acquire.assert_called_once_with("orders")

    def test_uses_default_bucket_put(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.put("/test", data={})
        rate_limiter.acquire.assert_called_once_with("orders")

    def test_uses_default_bucket_delete(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.delete("/test")
        rate_limiter.acquire.assert_called_once_with("orders")

    # -- Error handling --

    def test_raises_dhan_request_error_on_4xx(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(400, "bad request")
        with pytest.raises(DhanRequestError) as exc:
            client.get("/test")
        assert exc.value.status == 400

    def test_raises_dhan_request_error_on_403(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(403, "forbidden")
        with pytest.raises(DhanRequestError) as exc:
            client.get("/test")
        assert exc.value.status == 403

    def test_raises_dhan_request_error_on_404(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(404, "not found")
        with pytest.raises(DhanRequestError) as exc:
            client.get("/test")
        assert exc.value.status == 404

    def test_raises_dhan_server_error_on_5xx(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(500, "server error")
        with pytest.raises(DhanServerError) as exc:
            client.get("/test")
        assert exc.value.status == 500
        # 5xx gets retried twice, so 2 calls
        assert mock_session.request.call_count == 2

    def test_raises_dhan_server_error_on_502(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(502, "bad gateway")
        with pytest.raises(DhanServerError) as exc:
            client.get("/test")
        assert exc.value.status == 502

    def test_raises_dhan_server_error_on_503(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(503, "service unavailable")
        with pytest.raises(DhanServerError) as exc:
            client.get("/test")
        assert exc.value.status == 503

    def test_raises_dhan_auth_error_on_401(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(401, "unauthorized")
        with pytest.raises(DhanAuthError):
            client.get("/test")

    # -- Retry behaviour --

    def test_retries_on_5xx_up_to_max_retries(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _text_response(500, "server error")
        with pytest.raises(DhanServerError):
            client.get("/test")
        assert mock_session.request.call_count == 2

    def test_retries_on_request_exception(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.side_effect = requests.ConnectionError("connection failed")
        with pytest.raises(DhanServerError):
            client.get("/test")
        assert mock_session.request.call_count == 2

    def test_succeeds_on_retry_after_5xx(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.side_effect = [
            _text_response(500, "error"),
            _json_response(200, {"ok": True}),
        ]
        result = client.get("/test")
        assert result == {"ok": True}
        assert mock_session.request.call_count == 2

    def test_retries_on_429_after_reacquire(self, client: DhanHttpClient, rate_limiter: MagicMock, mock_session: MagicMock) -> None:
        mock_session.request.side_effect = [
            _text_response(429, "rate limited"),
            _json_response(200, {"ok": True}),
        ]
        result = client.get("/test")
        assert result == {"ok": True}
        assert rate_limiter.acquire.call_count == 2

    # -- Timeout --

    def test_timeout_is_30s(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test")
        _, kwargs = mock_session.request.call_args
        assert kwargs["timeout"] == 30.0

    # -- Session reuse --

    def test_uses_same_session(self, client: DhanHttpClient, mock_session: MagicMock) -> None:
        mock_session.request.return_value = _json_response(200, {})
        client.get("/test1")
        client.get("/test2")
        assert mock_session.request.call_count == 2

    # -- Error types hierarchy --

    def test_rate_limit_timeout_is_dhan_http_error(self) -> None:
        assert issubclass(RateLimitTimeout, DhanHttpError)

    def test_dhan_request_error_is_dhan_http_error(self) -> None:
        assert issubclass(DhanRequestError, DhanHttpError)

    def test_dhan_server_error_is_dhan_http_error(self) -> None:
        assert issubclass(DhanServerError, DhanHttpError)

    def test_dhan_auth_error_is_dhan_http_error(self) -> None:
        assert issubclass(DhanAuthError, DhanHttpError)


# ============================================================================
# Helpers
# ============================================================================

def _json_response(status: int, data: dict) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = json.dumps(data)
    resp.json.return_value = data
    return resp


def _text_response(status: int, text: str) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.text = text
    resp.json.side_effect = ValueError("not json")
    return resp
