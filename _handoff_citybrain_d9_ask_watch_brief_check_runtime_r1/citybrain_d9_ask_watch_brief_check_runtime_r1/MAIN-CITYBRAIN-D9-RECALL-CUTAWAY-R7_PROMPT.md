# MAIN-CITYBRAIN-D9-RECALL-CUTAWAY-R7

Implement Recall only as a bounded cutaway, not a full product mode.

## Acceptance

- Use Chicago precedent/similar-case records only when source ID and match reason are visible.
- Every recall item must carry a non-inference note:
  - not causality
  - not instruction
  - not prediction
  - not enforcement
  - not recommendation
- If match reasons are generic, mark the recall item partial.

## Required artifacts

- `D9_RECALL_CUTAWAY_PACKET.json`
- `D9_RECALL_MATCH_REASON_QUALITY_REPORT.json`
- `D9_RECALL_CUTAWAY_R7_DECISION.json`
- audits + hash manifest

Expected status:
`PASS_MAIN_CITYBRAIN_D9_RECALL_CUTAWAY_R7_WITH_LIMITATIONS`
or
`PARTIAL_MAIN_CITYBRAIN_D9_RECALL_CUTAWAY_R7_MATCH_REASONS_TOO_GENERIC`
