# D9 External Operator Validation R2 — Refreshed Baseline

Use this instead of the older R1 packet after D9 pre-validation hardening.

Why R2:
- The validation baseline has changed.
- Recall is now hardened enough to test.
- DIFF is explicitly deferred.
- Open ASK router is contract-only, not implemented.
- The external question corpus from this session becomes input to future Open ASK router implementation.

Place completed non-builder session records under:

`inputs/d9_external_operator_sessions/`

Suggested files:
- `operator_session_001.json`
- `operator_session_001_tasks.csv`

Do not claim external validation without a real non-builder session.
