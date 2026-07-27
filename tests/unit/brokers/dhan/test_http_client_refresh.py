"""W7b: a 401 from Dhan must trigger token refresh + one retry.

Dhan also signals a stale token as HTTP 400 + errorCode DH-906 ("Invalid
Token") — captured live 2026-07-27 — so that path must refresh too.
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


def _client(session, refresh_fn):
    session.headers = {}
    return DhanHttpClient(
        client_id="cid", access_token="stale",
        token_refresh_fn=refresh_fn, session=session,
    )


def test_401_triggers_refresh_and_retry_succeeds():
    session = MagicMock()
    session.request.side_effect = [_resp(401), _resp(200, {"ok": True})]
    refresh_fn = MagicMock(return_value="fresh-token")

    client = _client(session, refresh_fn)
    assert client.get("/positions") == {"ok": True}

    refresh_fn.assert_called_once()
    assert client.access_token == "fresh-token"
    assert session.headers["access-token"] == "fresh-token"


def test_401_without_refresh_fn_raises():
    session = MagicMock()
    session.request.return_value = _resp(401)

    client = _client(session, refresh_fn=None)
    with pytest.raises(AuthenticationError, match="401"):
        client.get("/positions")


def test_401_after_refresh_still_raises():
    session = MagicMock()
    session.request.side_effect = [_resp(401), _resp(401)]
    refresh_fn = MagicMock(return_value="fresh-token")

    client = _client(session, refresh_fn)
    with pytest.raises(AuthenticationError, match="401"):
        client.get("/positions")
    refresh_fn.assert_called_once()


def test_dh906_400_triggers_refresh_and_retry_succeeds():
    session = MagicMock()
    session.request.side_effect = [_dh906(), _resp(200, {"ok": True})]
    refresh_fn = MagicMock(return_value="fresh-token")

    client = _client(session, refresh_fn)
    assert client.get("/positions") == {"ok": True}

    refresh_fn.assert_called_once()
    assert client.access_token == "fresh-token"
    assert session.headers["access-token"] == "fresh-token"


def test_dh906_after_refresh_raises_authentication_error():
    session = MagicMock()
    session.request.side_effect = [_dh906(), _dh906()]
    refresh_fn = MagicMock(return_value="fresh-token")

    client = _client(session, refresh_fn)
    with pytest.raises(AuthenticationError, match="DH-906"):
        client.get("/positions")
    refresh_fn.assert_called_once()
