# MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-STATUS-R1

## Purpose

Start or report DIFF snapshot cadence/status honestly. DIFF remains unavailable until comparable source-record snapshots exist.

## Product goal

Prepare for future "what changed?" without faking change review.

## Required actions

1. Inspect existing snapshot/cadence artifacts.
2. Define source-record snapshot contract if not already defined:
   - snapshot_id
   - source_id
   - captured_at
   - record_count
   - record IDs
   - stable record hash/fingerprint
   - entity projection keys
3. If a current baseline snapshot can be created over retained source records, create it.
4. If two comparable snapshots exist, run a minimal source-record diff; otherwise report not ready.
5. Ensure UI/status language says change review is not available until comparable snapshots exist.

## Output

Write:

`outputs/main_citybrain_d10_diff_snapshot_cadence_status_r1/DIFF_SNAPSHOT_CADENCE_STATUS.json`

Minimum schema:

```json
{
  "task": "MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-STATUS-R1",
  "status": "PASS_DIFF_CADENCE_STATUS_WITH_LIMITATIONS" ,
  "snapshot_contract_defined": true,
  "baseline_snapshot_created": true,
  "comparable_snapshot_count": 0,
  "diff_ready": false,
  "diff_run_performed": false,
  "reason_not_ready": "...",
  "ui_claim_language": "Comparable source-record snapshots are not ready for change review.",
  "limitations": []
}
```

## Acceptance

- DIFF readiness/status is precise.
- No artifact hash churn is presented as city change.
- If not ready, reason is explicit and non-blocking.

## Fail if

- DIFF is greened without comparable source-record snapshots.
- The product says live change review or monitoring.
