---
source_file: "tests/unit/brokers/dhan/test_gateway_connection.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L188"
tags:
  - graphify/code
  - graphify/INFERRED
  - community/Tests_Unit/Brokers
---

# TestDhanConnectionConfigValidation

## Connections
- [[.test_should_accept_config_with_all_optional_keys()]] - `method` [EXTRACTED]
- [[.test_should_accept_valid_minimal_config()]] - `method` [EXTRACTED]
- [[.test_should_raise_configuration_error_when_access_token_is_empty_string()]] - `method` [EXTRACTED]
- [[.test_should_raise_configuration_error_when_access_token_missing()]] - `method` [EXTRACTED]
- [[.test_should_raise_configuration_error_when_both_required_keys_missing()]] - `method` [EXTRACTED]
- [[.test_should_raise_configuration_error_when_client_id_is_empty_string()]] - `method` [EXTRACTED]
- [[.test_should_raise_configuration_error_when_client_id_missing()]] - `method` [EXTRACTED]
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
- [[Validate that DhanConnection rejects invalid configurations immediately.]] - `rationale_for` [EXTRACTED]
- [[test_gateway_connection.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/INFERRED #community/Tests_Unit/Brokers