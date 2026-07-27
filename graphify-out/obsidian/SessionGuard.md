---
source_file: "scalpr/risk/session_guard.py"
type: "code"
community: "Risk - Session"
location: "L13"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Risk_-_Session
---

# SessionGuard

## Connections
- [[.__init__()_32]] - `method` [EXTRACTED]
- [[.check_market_cutoff()]] - `method` [EXTRACTED]
- [[.record_pnl()]] - `method` [EXTRACTED]
- [[.reset_guard()]] - `method` [EXTRACTED]
- [[.test_cutoff_window_minutes()_1]] - `calls` [EXTRACTED]
- [[.test_cutoff_window_minutes()]] - `calls` [EXTRACTED]
- [[.test_no_action_before_15_00()]] - `calls` [EXTRACTED]
- [[.test_no_action_before_23_00()]] - `calls` [EXTRACTED]
- [[.test_profit_resets_counter()]] - `calls` [EXTRACTED]
- [[.test_reset_clears_consecutive_losses()]] - `calls` [EXTRACTED]
- [[.test_reset_clears_halt()]] - `calls` [EXTRACTED]
- [[.test_reset_clears_warnings()]] - `calls` [EXTRACTED]
- [[.test_square_off_fires_at_15_15()]] - `calls` [EXTRACTED]
- [[.test_square_off_fires_at_15_16()]] - `calls` [EXTRACTED]
- [[.test_square_off_fires_at_15_30()]] - `calls` [EXTRACTED]
- [[.test_square_off_fires_at_23_15()]] - `calls` [EXTRACTED]
- [[.test_square_off_fires_at_23_16()]] - `calls` [EXTRACTED]
- [[.test_three_losses_trigger_halt()]] - `calls` [EXTRACTED]
- [[.test_warning_and_cutoff_sequence()]] - `calls` [EXTRACTED]
- [[.test_warning_fires_at_15_00()]] - `calls` [EXTRACTED]
- [[.test_warning_fires_at_15_14()]] - `calls` [EXTRACTED]
- [[.test_warning_fires_at_23_00()]] - `calls` [EXTRACTED]
- [[.test_warning_fires_only_once()_1]] - `calls` [EXTRACTED]
- [[.test_warning_fires_only_once()]] - `calls` [EXTRACTED]
- [[.test_warning_window_minutes()_1]] - `calls` [EXTRACTED]
- [[.test_warning_window_minutes()]] - `calls` [EXTRACTED]
- [[.test_zero_pnl_resets_counter()]] - `calls` [EXTRACTED]
- [[IBrokerGateway]] - `uses` [INFERRED]
- [[TestSessionGuardConsecutiveLosses]] - `uses` [INFERRED]
- [[TestSessionGuardMCX]] - `uses` [INFERRED]
- [[TestSessionGuardNSE]] - `uses` [INFERRED]
- [[TestSessionGuardReset]] - `uses` [INFERRED]
- [[Tracks consecutive session losses and manages IST intraday square-off times.]] - `rationale_for` [EXTRACTED]
- [[session_guard.py]] - `contains` [EXTRACTED]
- [[test_oms_risk.py]] - `imports` [EXTRACTED]
- [[test_session_guard.py]] - `imports` [EXTRACTED]
- [[test_session_guard_loss_tripping()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Risk_-_Session