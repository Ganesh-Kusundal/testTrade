---
type: community
cohesion: 0.14
members: 20
---

# Scanner - Options

**Cohesion:** 0.14 - loosely connected
**Members:** 20 nodes

## Members
- [[.__init__()_33]] - code - scalpr/scanner/options_scanner.py
- [[.__post_init__()_3]] - code - scalpr/domain/instrument.py
- [[.scan()]] - code - scalpr/scanner/options_scanner.py
- [[.test_historical_code_uses_security_id_field()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Any_17]] - code
- [[Decimal_18]] - code
- [[Historical data adapter should reference inst.security_id in source code.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Instrument]] - code - scalpr/domain/instrument.py
- [[Instrument definition for trading contracts.]] - rationale - scalpr/domain/instrument.py
- [[Instrument tick_size preserves exact Decimal precision.]] - rationale - tests/unit/domain/test_domain.py
- [[OptionsScanner]] - code - scalpr/scanner/options_scanner.py
- [[OptionsScanner filters liquid ATM options contracts based on deltaspot proximit]] - rationale - tests/unit/strategy_sim/test_strategy_sim.py
- [[Scan option chain data and return matching sorted instruments.]] - rationale - scalpr/scanner/options_scanner.py
- [[Scans option contracts at 0945 IST to filter for liquid ATM contracts.]] - rationale - scalpr/scanner/options_scanner.py
- [[Segment_2]] - code - scalpr/domain/instrument.py
- [[TestHistoricalSecurityIdUsage]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Verify historical data code uses inst.security_id, not inst.symbol.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[options_scanner.py]] - code - scalpr/scanner/options_scanner.py
- [[test_instrument_tick_size_decimal_precision()]] - code - tests/unit/domain/test_domain.py
- [[test_options_scanner()]] - code - tests/unit/strategy_sim/test_strategy_sim.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Scanner_-_Options
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Dhan Broker Integration_2]]
- 7 edges to [[_COMMUNITY_Dhan Broker Integration_6]]
- 7 edges to [[_COMMUNITY_Tests UnitBrokers_10]]
- 5 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 5 edges to [[_COMMUNITY_Signals - Gate]]
- 4 edges to [[_COMMUNITY_Tests UnitBrokers_11]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_12]]
- 3 edges to [[_COMMUNITY_Tests UnitBrokers_9]]
- 3 edges to [[_COMMUNITY_Oms - Order]]
- 2 edges to [[_COMMUNITY_Domain Events]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_11]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_1]]
- 1 edge to [[_COMMUNITY_Logging System]]

## Top bridge nodes
- [[Instrument]] - degree 24, connects to 10 communities
- [[Segment_2]] - degree 16, connects to 10 communities
- [[OptionsScanner]] - degree 17, connects to 7 communities
- [[TestHistoricalSecurityIdUsage]] - degree 10, connects to 4 communities
- [[options_scanner.py]] - degree 9, connects to 4 communities