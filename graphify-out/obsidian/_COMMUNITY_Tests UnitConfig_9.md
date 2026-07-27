---
type: community
cohesion: 0.33
members: 6
---

# Tests: Unit/Config

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.test_file_content_stripped()]] - code - tests/unit/config/test_secrets_manager.py
- [[.test_file_with_newlines()]] - code - tests/unit/config/test_secrets_manager.py
- [[File content should be stripped of leadingtrailing whitespace.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[File with newlines should return clean value.]] - rationale - tests/unit/config/test_secrets_manager.py
- [[TestFileContentHandling]] - code - tests/unit/config/test_secrets_manager.py
- [[Verify file content is properly stripped of whitespace.]] - rationale - tests/unit/config/test_secrets_manager.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Tests_Unit/Config
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Tests UnitConfig]]
- 2 edges to [[_COMMUNITY_Tests UnitConfig_1]]

## Top bridge nodes
- [[.test_file_content_stripped()]] - degree 4, connects to 2 communities
- [[.test_file_with_newlines()]] - degree 4, connects to 2 communities
- [[TestFileContentHandling]] - degree 4, connects to 1 community