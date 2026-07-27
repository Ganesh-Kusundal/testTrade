---
type: community
cohesion: 0.14
members: 14
---

# Configuration

**Cohesion:** 0.14 - loosely connected
**Members:** 14 nodes

## Members
- [[.__init__()_49]] - code - test_dhan_connection.py
- [[.auth_dialog_url()_1]] - code - config/endpoints.py
- [[.get()_2]] - code - test_dhan_connection.py
- [[.production()]] - code - config/endpoints.py
- [[.sandbox()]] - code - config/endpoints.py
- [[Build the OAuth authorization dialog URL without an instance.]] - rationale - config/endpoints.py
- [[Central broker endpoints registry.  Consolidates all Dhan and Upstox API URLs]] - rationale - config/endpoints.py
- [[Return a frozen URL resolver for the production environment.]] - rationale - config/endpoints.py
- [[Return a frozen URL resolver for the sandbox environment.]] - rationale - config/endpoints.py
- [[SimpleHttpClient]] - code - test_dhan_connection.py
- [[Upstox]] - code - config/endpoints.py
- [[Upstox broker endpoint registry.      Provides both production and sandbox clas]] - rationale - config/endpoints.py
- [[endpoints.py]] - code - config/endpoints.py
- [[test_dhan_connection.py_1]] - code - test_dhan_connection.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Configuration
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Tests UnitBrokers]]
- 3 edges to [[_COMMUNITY_Configuration]]
- 2 edges to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_7]]
- 1 edge to [[_COMMUNITY_Scripts - Test - Dhan]]

## Top bridge nodes
- [[endpoints.py]] - degree 9, connects to 5 communities
- [[SimpleHttpClient]] - degree 4, connects to 1 community
- [[.production()]] - degree 3, connects to 1 community
- [[.sandbox()]] - degree 3, connects to 1 community
- [[test_dhan_connection.py_1]] - degree 3, connects to 1 community