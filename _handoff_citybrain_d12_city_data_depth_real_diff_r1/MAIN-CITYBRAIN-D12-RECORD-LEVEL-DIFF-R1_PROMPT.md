# MAIN-CITYBRAIN-D12-RECORD-LEVEL-DIFF-R1

Compute DIFF only if comparable snapshots exist.

Allowed DIFF outputs:
- new source record
- removed/expired source record
- changed field/status
- changed relationship edge
- stronger/weaker evidence class
- stale source marker

Forbidden:
- artifact hash churn as city change
- live monitoring claim
- alerting/notification
- predicted impact

If fewer than two comparable snapshots exist, output `DEFERRED_NO_COMPARABLE_SOURCE_RECORD_SNAPSHOTS` and do not fail D12 data-depth work.

Deliverables:
- `RECORD_LEVEL_DIFF_REPORT.json` or `DIFF_DEFERRED_COMPARABILITY_DECISION.json`
- `DIFF_FALSE_POSITIVE_CHURN_AUDIT.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
