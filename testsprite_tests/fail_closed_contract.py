"""Fail-closed contract: no endpoint ever fabricates an empty book.

Every data endpoint must answer with real data (200), broker unavailable
(503), broker error (502), or honest not-implemented (501) — never a
silent empty [] while the broker is down, and never 500.
"""
import requests

TARGET_URL = __TARGET_URL__
HEADERS = __AUTH_HEADERS__

ENDPOINTS = {
    "/portfolio/positions": (200, 502, 503),
    "/portfolio/margins": (200, 502, 503),
    "/orders/": (200, 502, 503),
    "/market/ltp/RELIANCE": (200, 502, 503),
}

for path, allowed in ENDPOINTS.items():
    r = requests.get(f"{TARGET_URL}{path}", headers={**HEADERS}, timeout=15)
    assert r.status_code in allowed, (
        f"{path}: {r.status_code} violates fail-closed contract "
        f"(allowed {allowed}): {r.text[:200]}"
    )
    if r.status_code in (502, 503):
        detail = r.json().get("detail", "")
        assert "broker" in detail.lower(), f"{path}: 5xx must name the broker: {detail!r}"
    print(f"{path} -> {r.status_code} OK")

# /orders/fills is deliberately unimplemented: 501 is honest, [] is not.
fills = requests.get(f"{TARGET_URL}/orders/fills", headers={**HEADERS}, timeout=10)
assert fills.status_code == 501, f"/orders/fills must be 501, got {fills.status_code}"

print("fail-closed contract OK")
