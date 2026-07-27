---
type: community
cohesion: 0.33
members: 6
---

# Tests: Unit/Config

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.test_get_methods_do_not_log_secrets()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_require_does_not_log_secret_value()]] - code - tests/unit/config/test_secrets_manager.py
- [[Getter methods should not log secret values.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestSecretsNotLogged]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify secrets are never logged in plaintext.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[require() error message should not log the secret value.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[TestSecretsNotLogged]] - degree 4, connects to 1 community
- [[.test_get_methods_do_not_log_secrets()]] - degree 3, connects to 1 community
- [[.test_require_does_not_log_secret_value()]] - degree 3, connects to 1 community