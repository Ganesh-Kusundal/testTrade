---
type: community
cohesion: 0.20
members: 10
---

# Tests: Unit/Config

**Cohesion:** 0.20 - loosely connected
**Members:** 10 nodes

## Members
- [[.test_access_token_empty_when_missing()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_access_token_env_priority_over_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_access_token_from_env()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_access_token_from_file()]] - code - tests/unit/config/test_secrets_manager.py
- [[Access token should be loaded from DHAN_ACCESS_TOKEN env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Access token should fallback to file when env var missing.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Access token should return empty string when neither env nor file exists.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Env var should take priority over file._1]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestAccessTokenLoading]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify Dhan access token loading from env and file.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig]]

## Top bridge nodes
- [[.test_access_token_env_priority_over_file()]] - degree 4, connects to 2 communities
- [[.test_access_token_from_file()]] - degree 4, connects to 2 communities
- [[TestAccessTokenLoading]] - degree 6, connects to 1 community
- [[.test_access_token_empty_when_missing()]] - degree 3, connects to 1 community
- [[.test_access_token_from_env()]] - degree 3, connects to 1 community