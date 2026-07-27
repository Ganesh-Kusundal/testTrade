---
type: community
cohesion: 0.16
members: 15
---

# Tests: Unit/Config

**Cohesion:** 0.16 - loosely connected
**Members:** 15 nodes

## Members
- [[.test_custom_client_id_file_path()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_custom_token_file_path()]] - code - tests/unit/config/test_secrets_manager.py
- [[Clean up DHAN_ environment variables before and after tests.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Comprehensive tests for SecretsManager credential loading.  Tests verify - All]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Create a SecretsManager instance with temporary project root.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Create a temporary project root for testing file-based secrets.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Path_1]] - code
- [[Should use custom file path from DHAN_ACCESS_TOKEN_FILE env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[Should use custom file path from DHAN_CLIENT_ID_FILE env var.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestCustomFilePaths]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify custom file path configuration via env vars.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[env_cleanup()]] - code - tests/unit/config/test_secrets_manager.py
- [[secrets_manager()]] - code - tests/unit/config/test_secrets_manager.py
- [[temp_project_root()]] - code - tests/unit/config/test_secrets_manager.py
- [[test_secrets_manager.py]] - code - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Tests UnitConfig_1]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_2]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_5]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_9]]
- 3 edges to [[_COMMUNITY_Tests UnitConfig_3]]
- 2 edges to [[_COMMUNITY_Tests UnitConfig_7]]
- 1 edge to [[_COMMUNITY_Logging System]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig_4]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig_6]]
- 1 edge to [[_COMMUNITY_Tests UnitConfig_8]]

## Top bridge nodes
- [[test_secrets_manager.py]] - degree 15, connects to 10 communities
- [[Path_1]] - degree 15, connects to 6 communities
- [[secrets_manager()]] - degree 4, connects to 1 community
- [[.test_custom_client_id_file_path()]] - degree 4, connects to 1 community
- [[.test_custom_token_file_path()]] - degree 4, connects to 1 community