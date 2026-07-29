"""W7b: http_client no longer refreshes on 401 — it raises immediately.

The http_client is the transport layer. On 401 or DH-906 it raises
AuthenticationError and lets the caller (DhanConnection._verify_connection)
handle refresh+retry. This avoids double-refresh and TOTP cooldown spirals.
"""
from unittest.mock import MagicMock

import pytest

from scalpr.brokers.dhan.exceptions import AuthenticationError
from scalpr.brokers.dhan.http_client import DhanHttpClient


def _resp(status_code, payload=None, text=""):
    resp = MagicMock(status_code=status_code, text=text)
    resp.json.return_value = payload if payload is not None else {}
    return resp


def _dh906():
    return _resp(
        400,
        payload={"errorType": "Order_Error", "errorCode": "DH-906",
                 "errorMessage": "Invalid Token"},
        text='{"errorType":"Order_Error","errorCode":"DH-906","errorMessage":"Invalid Token"}',
    )


def test_401_raises_immediately():
    session = MagicMock()
    session.request.return_value = _resp(401)
    client = DhanHttpClient(client_id="cid", access_token="stale", session=session)
    with pytest.raises(AuthenticationError, match="401"):
        client.get("/positions")


def test_401_no_refresh_attempt():
    session = MagicMock()
    session.request.return_value = _resp(401)
    refresh_fn = MagicMock()
    client = DhanHttpClient(
        client_id="cid", access_token="stale",
        token_refresh_fn=refresh_fn, session=session,
    )
    with pytest.raises(AuthenticationError):
        client.get("/positions")
    refresh_fn.assert_not_called()


def test_dh906_raises_immediately():
    session = MagicMock()
    session.request.return_value = _dh906()
    client = DhanHttpClient(client_id="cid", access_token="stale", session=session)
    with pytest.raises(AuthenticationError, match="DH-906"):
        client.get("/positions")


def test_200_does_not_refresh():
    session = MagicMock()
    session.request.return_value = _resp(200, {"ok": True})
    refresh_fn = MagicMock()
    client = DhanHttpClient(
        client_id="cid", access_token="good",
        token_refresh_fn=refresh_fn, session=session,
    )
    assert client.get("/positions") == {"ok": True}
    refresh_fn.assert_not_called()
