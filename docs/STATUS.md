# Status

Rule: a claim lives here only if it links to a passing test or a live-verification script.
No test/script link → the claim doesn't exist.

| Claim | Evidence |
|---|---|
| WebSocket full-mode feed streams real ticks (string SecurityId, instrument-based segments) | `tests/unit/brokers/dhan/test_websocket.py` (`.venv/bin/python -m pytest tests/unit/brokers/dhan/test_websocket.py`) |
| 20-level depth verified live | `test_live_full_depth.py` (manual, market hours) — captured live 2025 |
| Event-store round-trip reconstructs Fill/Order (not raw dicts) | `tests/unit/observability/test_event_store_roundtrip.py` |
| Import-layer contracts enforced (5 contracts) | `lint-imports --config pyproject.toml` via pre-commit hook |
| Trade.exchange populated from broker segment ("" = honest unknown) | `tests/unit/brokers/test_gateway_trades.py` |
| One source of segment truth; F&O mapping unchanged | `tests/unit/brokers/test_mapper_fno.py` |
| Gateway→WS bridge delivers ticks to callbacks (resolver wired, exchange preserved) | `tests/unit/brokers/test_gateway_streaming.py` |
| Broker outage never fabricates empty book: adapters raise, routers 503/502, /health truthful | `tests/unit/brokers/dhan/test_adapters.py::TestPortfolioAdapter`, `tests/unit/api/test_routers_fail_closed.py` |
| Strategy feeds real daily_loss/portfolio_value to risk gates; blocks without risk data | `tests/unit/strategy/test_scalpr_amt_risk_inputs.py` |
| 401 triggers forced token refresh + retry (wired end-to-end from Gateway config) | `tests/unit/brokers/dhan/test_http_client_refresh.py`, `tests/unit/brokers/dhan/test_auth.py::TestEnsureFreshToken::test_force_regenerates_despite_fresh_cache` |
| Composition root wires tick→strategy→risk→OMS→broker chain | `tests/unit/api/test_bootstrap.py::TestWire`, `tests/unit/integration/test_e2e_paper_smoke.py` |
| Live 30s Gateway.stream smoke: 34 RELIANCE ticks in 30s, ltp=1279.30, tz-aware exchange ts, clean stop_stream teardown | manual `Gateway().stream("RELIANCE", callback=...)` # captured live 2026-07-27 |
| Fund limits endpoint is `/fundlimit` (plural 404s live — was silently masked pre-C3) | `tests/unit/brokers/dhan/test_adapters.py::TestPortfolioAdapter::test_should_return_fund_limits_dict` + live `/portfolio/margins` 200 # captured live 2026-07-27 |
| API contract tests (health truthful, fail-closed 5xx, route contract) uploaded to TestSprite cloud | `testsprite_tests/*.py`, project Trade_XV2_AMT_Scalper (`testsprite test list --project dea56fca-...`); verified locally against uvicorn on 8787 |
| `/health/live` + `/health/ready` probes (live always 200; ready 503 w/ JSON shape when gateway down) | `tests/unit/api/test_routers_fail_closed.py::TestProbes`; all 4 TradeX V2 TestSprite cloud tests pass locally |
| DH-906 "Invalid Token" (HTTP 400) triggers forced token refresh + retry, same as 401 | `tests/unit/brokers/dhan/test_http_client_refresh.py::test_dh906_400_triggers_refresh_and_retry_succeeds`; stale token → 200 # captured live 2026-07-27 |

## Known-unwired / deferred

- EventStore/replay is NOT wired into production (leadership decision pending: wire or delete).
