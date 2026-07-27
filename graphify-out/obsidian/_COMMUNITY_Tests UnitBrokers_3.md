---
type: community
cohesion: 0.04
members: 46
---

# Tests: Unit/Brokers

**Cohesion:** 0.04 - loosely connected
**Members:** 46 nodes

## Members
- [[.connection()]] - code - scalpr/brokers/dhan/gateway.py
- [[.http_client()]] - code - scalpr/brokers/dhan/connection.py
- [[.is_connected()_1]] - code - scalpr/brokers/dhan/connection.py
- [[.test_connect_warns_on_inactive_data_plan()]] - code - tests/unit/brokers/dhan/test_critical_fixes.py
- [[.test_should_accept_config_with_all_optional_keys()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_cleanup_on_connect_failure()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_handle_concurrent_connect_calls_safely()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_pass_enable_retry_false_when_specified()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_pass_token_refresh_fn_to_http_client()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_broker_error_when_historical_accessed_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_broker_error_when_http_client_accessed_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_broker_error_when_orders_accessed_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_broker_error_when_portfolio_accessed_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_configuration_error_when_access_token_is_empty_string()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_raise_configuration_error_when_client_id_missing()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_report_disconnected_after_failed_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_report_disconnected_before_connect()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_start_as_not_connected()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_use_custom_base_url_when_specified()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_use_custom_timeout_when_specified()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[.test_should_use_default_base_url_when_not_specified()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Access the underlying DhanConnection.          Use this when you need direct acc]] - rationale - scalpr/brokers/dhan/gateway.py
- [[Access the underlying HTTP client.          Raises             BrokerError If]] - rationale - scalpr/brokers/dhan/connection.py
- [[Accessing .historical before connect() must raise BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Accessing .http_client before connect() must raise BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Accessing .orders before connect() must raise BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Accessing .portfolio before connect() must raise BrokerError.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[After a failed connect attempt, state must remain disconnected.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Check if the connection is active.          Returns             True if connect]] - rationale - scalpr/brokers/dhan/connection.py
- [[Config with optional keys should be accepted without error.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Connection should warn if dataPlan is not active.]] - rationale - tests/unit/brokers/dhan/test_critical_fixes.py
- [[Create a DhanConnection with all internal steps mocked for isolation.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Custom base_url from config must override the default.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Custom timeout from config must be used.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[DhanConnection]] - code - scalpr/brokers/dhan/connection.py
- [[Empty string access_token should be treated as missing.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[If _verify_connection fails, connection must clean up partial state.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Initial state must be disconnected.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Missing client_id should raise ConfigurationError at construction.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Multiple threads calling connect() simultaneously must not corrupt state.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[New connection must report is_connected() == False before connect().]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[Orchestrates all Dhan broker adapters behind a single connection.      Responsib]] - rationale - scalpr/brokers/dhan/connection.py
- [[When base_url is missing, Dhan.REST_BASE must be used.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[enable_retry=False must be passed through.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py
- [[fully_mocked_connection()]] - code - tests/unit/brokers/dhan/test_gateway_connection.py
- [[token_refresh_fn from config must be passed to DhanHttpClient.]] - rationale - tests/unit/brokers/dhan/test_gateway_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 50 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 6 edges to [[_COMMUNITY_Tests UnitTesting]]
- 6 edges to [[_COMMUNITY_Dhan Broker Integration_10]]
- 4 edges to [[_COMMUNITY_Scripts - Test - Dhan]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_5]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_14]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_9]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 2 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_19]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_4]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_7]]
- 1 edge to [[_COMMUNITY_Oms - Order]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_2]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_15]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_44]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_45]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_35]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_32]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_33]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_34]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_54]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_53]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_36]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_41]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_48]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_52]]

## Top bridge nodes
- [[DhanConnection]] - degree 95, connects to 27 communities
- [[.http_client()]] - degree 4, connects to 1 community
- [[.connection()]] - degree 3, connects to 1 community
- [[.test_connect_warns_on_inactive_data_plan()]] - degree 3, connects to 1 community
- [[fully_mocked_connection()]] - degree 3, connects to 1 community