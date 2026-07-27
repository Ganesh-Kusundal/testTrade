---
source_file: "scalpr/brokers/dhan/exceptions.py"
type: "code"
community: "Tests: Unit/Brokers"
location: "L14"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Tests_Unit/Brokers
---

# InstrumentNotFoundError

## Connections
- [[.resolve()]] - `calls` [EXTRACTED]
- [[.test_should_raise_instrument_not_found_when_resolver_fails()]] - `calls` [EXTRACTED]
- [[.test_should_raise_order_error_when_symbol_resolution_fails()]] - `calls` [EXTRACTED]
- [[.test_should_return_empty_dict_when_no_symbols_resolve()]] - `calls` [EXTRACTED]
- [[.test_should_skip_unresolvable_symbols_in_batch()]] - `calls` [EXTRACTED]
- [[BrokerError]] - `inherits` [EXTRACTED]
- [[Instrument not found in resolver cache.]] - `rationale_for` [EXTRACTED]
- [[SymbolResolver]] - `uses` [INFERRED]
- [[TestHistoricalDataAdapter]] - `uses` [INFERRED]
- [[TestMarketDataAdapter]] - `uses` [INFERRED]
- [[TestOrdersAdapter]] - `uses` [INFERRED]
- [[TestPortfolioAdapter]] - `uses` [INFERRED]
- [[exceptions.py]] - `contains` [EXTRACTED]
- [[resolver.py]] - `imports` [EXTRACTED]
- [[test_adapters.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Tests_Unit/Brokers