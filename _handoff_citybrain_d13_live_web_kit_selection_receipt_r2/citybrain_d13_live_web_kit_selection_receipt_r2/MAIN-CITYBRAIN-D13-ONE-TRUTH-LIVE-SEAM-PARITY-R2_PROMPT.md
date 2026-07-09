# MAIN-CITYBRAIN-D13-ONE-TRUTH-LIVE-SEAM-PARITY-R2

Compare live seam payloads across web and Kit.

For each successful live receipt, compare:
- entity_id
- display label
- evidence packet ref/hash
- source refs summary
- limitations/cannot-claim summary
- execution_state / no-action state
- review state, if present

Output:
`ONE_TRUTH_LIVE_SEAM_PARITY_REPORT.json`

PASS requires 0 field diffs except presentation-only fields explicitly labeled.
