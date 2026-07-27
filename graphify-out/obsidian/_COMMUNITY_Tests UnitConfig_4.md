---
type: community
cohesion: 0.20
members: 10
---

# Tests: Unit/Config

**Cohesion:** 0.20 - loosely connected
**Members:** 10 nodes

## Members
- [[.test_auth_mode_default_static()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_auth_mode_from_env()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_environment_default_live()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_environment_from_env()]] - code - tests/unit/config/test_secrets_manager.py
- [[Auth mode should be loaded from DHAN_AUTH_MODE env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Auth mode should default to STATIC when not set.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Environment should be loaded from DHAN_ENVIRONMENT env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Environment should default to LIVE when not set.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestAuthModeAndEnvironment]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify auth mode and environment configuration.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[TestAuthModeAndEnvironment]] - degree 6, connects to 1 community
- [[.test_auth_mode_default_static()]] - degree 3, connects to 1 community
- [[.test_auth_mode_from_env()]] - degree 3, connects to 1 community
- [[.test_environment_default_live()]] - degree 3, connects to 1 community
- [[.test_environment_from_env()]] - degree 3, connects to 1 community