---
type: community
cohesion: 0.24
members: 11
---

# Tests: Unit/Config

**Cohesion:** 0.24 - loosely connected
**Members:** 11 nodes

## Members
- [[.test_pin_env_priority_over_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_pin_from_env()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_pin_from_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_pin_returns_none_when_missing()]] - code - tests/unit/config/test_secrets_manager.py
- [[Env var should take priority over file._3]] - rationale - tests/unit/config/test_secrets_manager.py
- [[PIN should be loaded from DHAN_PIN env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[PIN should fallback to file when env var missing.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[PIN should return None when neither env nor file exists.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[SecretsManager]] - code
- [[TestPINLoading]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify PIN loading with None fallback.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitConfig]]
- 4 edges to [[_COMMUNITY_Tests UnitConfig_2]]
- 4 edges to [[_COMMUNITY_Tests UnitConfig_4]]
- 4 edges to [[_COMMUNITY_Tests UnitConfig_5]]
- 4 edges to [[_COMMUNITY_Tests UnitConfig_3]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_7]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_6]]
- 2 edges to [[_COMMUNITY_Tests UnitConfig_9]]
- 2 edges to [[_COMMUNITY_Tests UnitConfig_8]]

## Top bridge nodes
- [[SecretsManager]] - degree 33, connects to 9 communities
- [[TestPINLoading]] - degree 6, connects to 1 community
- [[.test_pin_env_priority_over_file()]] - degree 4, connects to 1 community
- [[.test_pin_from_file()]] - degree 4, connects to 1 community