---
type: community
cohesion: 0.25
members: 8
---

# Tests: Unit/Config

**Cohesion:** 0.25 - loosely connected
**Members:** 8 nodes

## Members
- [[.test_main_py_usage_pattern()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_secrets_manager_instantiation()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_secrets_manager_with_project_root()]] - code - tests/unit/config/test_secrets_manager.py
- [[SecretsManager should accept custom project root.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[SecretsManager should instantiate without arguments.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestIntegrationPattern]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify SecretsManager works as expected in main.py usage pattern.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Verify the exact usage pattern from main.py works.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 2 edges to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[.test_secrets_manager_with_project_root()]] - degree 4, connects to 2 communities
- [[TestIntegrationPattern]] - degree 5, connects to 1 community
- [[.test_main_py_usage_pattern()]] - degree 3, connects to 1 community
- [[.test_secrets_manager_instantiation()]] - degree 3, connects to 1 community