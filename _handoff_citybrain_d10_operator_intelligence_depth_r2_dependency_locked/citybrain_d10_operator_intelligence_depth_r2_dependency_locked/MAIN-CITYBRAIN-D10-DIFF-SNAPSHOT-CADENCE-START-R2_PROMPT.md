# MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-START-R2

## Purpose
Start the DIFF source-record snapshot clock now.

This does not implement or claim live DIFF. It creates the cadence foundation D12 will need.

## Requirements
- Define snapshot contract at source-record/entity projection level.
- Record baseline snapshot now if possible.
- If prior comparable snapshot exists, register it; otherwise mark baseline as first comparable snapshot.
- Record cadence schedule recommendation.
- Separate artifact/runtime hash change from city source-record change.
- Write cadence ledger with:
  - source families covered
  - fields included
  - entity projection keys
  - snapshot timestamp
  - comparability constraints
  - next snapshot due
  - blocked/missing source families

## Output
`DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json`
and snapshot files under a clear output root.

## Hard boundary
Do not claim:
- live monitoring
- live change detection
- operational alerts
- real DIFF mode pass unless two comparable snapshots actually exist and record-level change is computed.
