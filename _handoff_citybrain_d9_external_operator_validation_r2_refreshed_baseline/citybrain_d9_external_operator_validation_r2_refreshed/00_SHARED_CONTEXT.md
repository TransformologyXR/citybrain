# CityBrain D9 External Operator Validation R2 — Refreshed Baseline

Purpose: validate the D9 product-mode cockpit after pre-validation hardening, not the earlier D9 R1 baseline.

Validated baseline facts to preserve:
- D9 Ask/Watch/Brief/Check runtime closed green with limitations.
- Pre-validation hardening closed green with limitations.
- Recall hardening is now available as `PASS_RECALL_HARDENED_WITH_LIMITATIONS`.
- DIFF remains deferred: `DEFERRED_DIFF_NO_COMPARABLE_SOURCE_RECORD_SNAPSHOTS`.
- Open ASK router is contract-locked only: `CONTRACT_LOCKED_NOT_IMPLEMENTED`.
- D9 validation baseline refresh is green.
- Execution state remains `not_executed`.
- No production/public API, no monitoring/alerts, no dispatch/routing/control/enforcement, no official ticket/case, no legal/certified finding, no automated action.

Validation objective:
A non-builder operator/reviewer uses the D9 cockpit to complete task-based review workflows and produces a session record. This track imports the session, scores task success, extracts external questions as a corpus for future Open ASK implementation, and closes honestly.

Critical distinction:
This track does not implement Open ASK. It validates the current template-based cockpit and captures the operator's spontaneous questions for later router implementation.
