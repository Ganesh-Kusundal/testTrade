---
type: community
cohesion: 0.17
members: 16
---

# Qoder

**Cohesion:** 0.17 - loosely connected
**Members:** 16 nodes

## Members
- [[Append an order record to the trade journal.      Args         order_params di]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Generate a summary of recent trading activity.      Returns         dict with t]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Get all orders logged today.      Returns         list of order records from to]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Get order history for the last N days.      Args         days Number of days t]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Get the stable path for trade log storage.]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Print today's orders in a human-readable format.]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Read all records from the trade log.]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[Trade journal for logging and reviewing DhanHQ orders.  Persists trade data to $]] - rationale - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[_get_log_path()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[_read_all_records()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[get_today_orders()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[get_trade_history()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[get_trade_summary()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[log_order()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[print_today_orders()]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py
- [[trade_logger.py]] - code - .qoder/skills/dhanhq/scripts/trade_logger.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Qoder
SORT file.name ASC
```
