"""Route contract: documented routes exist; unknown routes are 404.

Guards against accidental route removal or a catch-all that silently
serves garbage. Route list mirrors scalpr/api/routers/* as of 2026-07-27.
"""
import requests

TARGET_URL = __TARGET_URL__
HEADERS = __AUTH_HEADERS__

KNOWN_GET = (
    "/health",
    "/health/live",
    "/health/ready",
    "/portfolio/positions",
    "/portfolio/margins",
    "/orders/",
    "/orders/fills",
    "/market/ltp/RELIANCE",
)

for path in KNOWN_GET:
    r = requests.get(f"{TARGET_URL}{path}", headers={**HEADERS}, timeout=15)
    assert r.status_code != 404, f"{path} vanished (404) — route contract broken"
    assert r.status_code != 500, f"{path} crashed (500): {r.text[:200]}"
    print(f"{path} -> {r.status_code} routed OK")

missing = requests.get(f"{TARGET_URL}/definitely-not-a-route", headers={**HEADERS}, timeout=10)
assert missing.status_code == 404, f"unknown route must 404, got {missing.status_code}"

print("route contract OK")
