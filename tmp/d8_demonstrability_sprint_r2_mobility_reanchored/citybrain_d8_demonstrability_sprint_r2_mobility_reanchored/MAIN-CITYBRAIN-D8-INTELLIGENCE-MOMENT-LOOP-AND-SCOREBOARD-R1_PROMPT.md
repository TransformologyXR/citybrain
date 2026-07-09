# MAIN-CITYBRAIN-D8-INTELLIGENCE-MOMENT-LOOP-AND-SCOREBOARD-R1

Goal: run the D8 moment loop for every committed moment and produce the demonstrability scoreboard.

For each committed moment:
0. Re-check that the moment's `data_basis` resolves to a certified-tip ref; fail-safe or mark `documented_partial` if missing.
1. Select beat.
2. Wire/update if needed.
3. Drive live surface.
4. Test viewer-legibility if possible; otherwise mark `internal_proxy_pending_naive_viewer`.
5. Patch front-end/wiring/label defects.
6. Re-drive and regression-check prior green moments.
7. Capture clip or mark capture pending.
8. Score all five checks.

Five checks:
- certified_data_basis_resolved
- renders_live
- legible_unaided
- insight_lands
- boundary_visible
- captured_clean

Produce:
- `D8_DEMONSTRABILITY_SCOREBOARD.json`
- `D8_DEMONSTRABILITY_SCOREBOARD.md`
- `D8_MOMENT_LOOP_RESULTS.jsonl`
- `D8_FRONTEND_PATCH_LOG.json`
- `D8_PARKING_LOT.md`
- `D8_REGRESSION_REPORT.json`

Pass status:
`PASS_MAIN_CITYBRAIN_D8_INTELLIGENCE_MOMENT_LOOP_AND_SCOREBOARD_R1_WITH_LIMITATIONS`
