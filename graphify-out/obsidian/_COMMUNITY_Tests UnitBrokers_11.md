---
type: community
cohesion: 0.33
members: 6
---

# Tests: Unit/Brokers

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.test_scanner_accepts_resolver_parameter()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[.test_scanner_code_resolves_instruments()]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[OptionsScanner scan method should use resolver to get instruments.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[OptionsScanner should accept resolver parameter.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[TestOptionsScannerSecurityIds]] - code - tests/unit/brokers/dhan/test_security_id_consistency.py
- [[Verify OptionsScanner resolves real security_ids via resolver.]] - rationale - tests/unit/brokers/dhan/test_security_id_consistency.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Brokers
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Scanner - Options]]
- 2 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_5]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_1]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_10]]

## Top bridge nodes
- [[TestOptionsScannerSecurityIds]] - degree 11, connects to 5 communities
- [[.test_scanner_accepts_resolver_parameter()]] - degree 3, connects to 1 community