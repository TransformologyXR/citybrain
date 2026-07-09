# Acceptance criteria — MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1

Expected status:

```text
PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS
```

## Required artifacts

```text
E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json
E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json
E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json
E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json
E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json
E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json
E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json
E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json
E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json
E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json
E3_FINAL_NONLIVE_HIDDEN_FUEL_LEDGER_ROW.json
HASH_MANIFEST.json
LINE_ENDING_REPORT.json
```

## Functional acceptance

1. The decision status is `PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS` or a justified failure.
2. The package states the system is not live and operator fuel is deferred.
3. Every lane emits an artifact.
4. L4 content verification classifies path-only vs content-backed candidates.
5. CHECK readiness distinguishes descriptive scorecard from true calibration.
6. Watch ranking signals remain descriptive unless verified exposure exists.
7. Simulation/backtest input scout identifies candidate targets but creates no model.
8. Identity/graph scout creates no canonical truth changes.
9. The backlog classifies items into:
   - closeout_affecting
   - epoch4_backlog
   - parking_lot
   - not_promotable
10. No training rows are created.
11. No learned registry entries are created.
12. No forbidden capability is armed.
13. Publication-home recommendation is emitted.
14. Hash manifest validates package artifacts.
15. LF stability has zero CRLF paths.
16. Package states this is the final pre-closeout scout unless a human explicitly reopens scouting.
