---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L236"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestDhanConnectionLifecycle

## Connections
- [[.test_should_be_idempotent_when_connect_called_twice()]] - `method` [EXTRACTED]
- [[.test_should_be_safe_to_disconnect_when_already_disconnected()]] - `method` [EXTRACTED]
- [[.test_should_cleanup_on_connect_failure()]] - `method` [EXTRACTED]
- [[.test_should_create_http_client_on_connect()]] - `method` [EXTRACTED]
- [[.test_should_disconnect_clear_all_adapters()]] - `method` [EXTRACTED]
- [[.test_should_load_instruments_on_connect()]] - `method` [EXTRACTED]
- [[.test_should_mark_connection_as_connected_after_successful_connect()]] - `method` [EXTRACTED]
- [[.test_should_re_raise_authentication_error_without_wrapping()]] - `method` [EXTRACTED]
- [[.test_should_start_as_not_connected()]] - `method` [EXTRACTED]
- [[.test_should_verify_connection_via_profile_endpoint()]] - `method` [EXTRACTED]
- [[AuthenticationError]] - `uses` [INFERRED]
- [[BrokerError]] - `uses` [INFERRED]
- [[ConfigurationError]] - `uses` [INFERRED]
- [[Dhan]] - `uses` [INFERRED]
- [[DhanConnection]] - `uses` [INFERRED]
- [[DhanGateway]] - `uses` [INFERRED]
- [[Exchange_4]] - `uses` [INFERRED]
- [[Fill]] - `uses` [INFERRED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[Order]] - `uses` [INFERRED]
- [[OrderSide_1]] - `uses` [INFERRED]
- [[OrderState]] - `uses` [INFERRED]
- [[OrderType]] - `uses` [INFERRED]
- [[Position]] - `uses` [INFERRED]
- [[PositionSide]] - `uses` [INFERRED]
- [[Test the full connect → verify → disconnect lifecycle.]] - `rationale_for` [EXTRACTED]
- [[test_gateway_connection.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers