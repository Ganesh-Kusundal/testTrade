---
type: community
cohesion: 0.20
members: 10
---

# Tests: Unit/Config

**Cohesion:** 0.20 - loosely connected
**Members:** 10 nodes

## Members
- [[.test_totp_env_priority_over_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_totp_from_env()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_totp_from_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_totp_returns_none_when_missing()]] - code - tests/unit/config/test_secrets_manager.py
- [[Env var should take priority over file._2]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TOTP secret should be loaded from DHAN_TOTP_SECRET env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TOTP secret should fallback to file when env var missing.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TOTP secret should return None when neither env nor file exists.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestTOTPSecretLoading]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify TOTP secret loading with None fallback.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[.test_totp_env_priority_over_file()]] - degree 4, connects to 2 communities
- [[.test_totp_from_file()]] - degree 4, connects to 2 communities
- [[TestTOTPSecretLoading]] - degree 6, connects to 1 community
- [[.test_totp_from_env()]] - degree 3, connects to 1 community
- [[.test_totp_returns_none_when_missing()]] - degree 3, connects to 1 community