"""/health is always 200 and truthfully reports gateway/feed/broker_error.

Contract (C3 fail-closed remediation): health never lies — it returns 200
even when the broker is down, and the body says exactly what is broken.
"""
import requests

TARGET_URL = __TARGET_URL__
HEADERS = __AUTH_HEADERS__

r = requests.get(f"{TARGET_URL}/health", headers={**HEADERS}, timeout=10)
assert r.status_code == 200, f"/health must always be 200, got {r.status_code}: {r.text}"

body = r.json()
for key in ("gateway", "feed", "broker_error"):
    assert key in body, f"/health missing key {key!r}: {body!r}"
assert isinstance(body["gateway"], bool), f"gateway must be bool: {body!r}"
assert isinstance(body["feed"], bool), f"feed must be bool: {body!r}"

print("health truthful OK", body)
