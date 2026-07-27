---
type: community
cohesion: 0.09
members: 29
---

# Dhan Broker Integration

**Cohesion:** 0.09 - loosely connected
**Members:** 29 nodes

## Members
- [[.__init__()_4]] - code - scalpr/brokers/dhan/http_client.py
- [[.__init__()_5]] - code - scalpr/brokers/dhan/http_client.py
- [[._backoff_delay()]] - code - scalpr/brokers/dhan/http_client.py
- [[._match_rate_limit()]] - code - scalpr/brokers/dhan/http_client.py
- [[._request()]] - code - scalpr/brokers/dhan/http_client.py
- [[._throttle()]] - code - scalpr/brokers/dhan/http_client.py
- [[._try_refresh_token()]] - code - scalpr/brokers/dhan/http_client.py
- [[.allow_request()]] - code - scalpr/brokers/dhan/http_client.py
- [[.delete()]] - code - scalpr/brokers/dhan/http_client.py
- [[.get()]] - code - scalpr/brokers/dhan/http_client.py
- [[.post()]] - code - scalpr/brokers/dhan/http_client.py
- [[.put()]] - code - scalpr/brokers/dhan/http_client.py
- [[.record_failure()]] - code - scalpr/brokers/dhan/http_client.py
- [[.record_success()]] - code - scalpr/brokers/dhan/http_client.py
- [[.update_token()]] - code - scalpr/brokers/dhan/http_client.py
- [[Any_6]] - code
- [[Apply rate limiting for endpoint.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Attempt token refresh. Returns True if successful.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[CircuitBreaker]] - code - scalpr/brokers/dhan/http_client.py
- [[DELETE request to Dhan API.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Execute HTTP request with retry, rate limiting, and circuit breaker.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Exponential backoff 500ms, 1s, 2s, 4s... capped at 5s.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[GET request from Dhan API.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Match endpoint against rate limit keys using prefix matching.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[POST request to Dhan API.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[PUT request to Dhan API.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Session]] - code
- [[Simple circuit breaker for fault isolation.]] - rationale - scalpr/brokers/dhan/http_client.py
- [[Update access token in session headers.]] - rationale - scalpr/brokers/dhan/http_client.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dhan_Broker_Integration
SORT file.name ASC
```

## Connections to other communities
- 21 edges to [[_COMMUNITY_Tests UnitTesting]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers]]
- 1 edge to [[_COMMUNITY_Tests UnitBrokers_3]]
- 1 edge to [[_COMMUNITY_Dhan Broker Integration_10]]

## Top bridge nodes
- [[CircuitBreaker]] - degree 15, connects to 4 communities
- [[._request()]] - degree 17, connects to 1 community
- [[.get()]] - degree 5, connects to 1 community
- [[._throttle()]] - degree 5, connects to 1 community
- [[.delete()]] - degree 4, connects to 1 community