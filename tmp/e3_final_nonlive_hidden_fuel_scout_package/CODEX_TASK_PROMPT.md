# Codex task prompt — MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1

You are operating in the CityBrain repository on `main`.

Implement and run the final pre-closeout non-live hidden-fuel scout.

## Goal

Run one bounded, final scout over non-live corpus evidence before Epoch 3 closeout. The system is not live, so do not wait on or simulate live operator fuel. Instead, verify which hidden-data candidates already in the corpus are content-backed enough to influence closeout, and classify everything else into backlog.

## Expected status

```text
PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS
```

## Required global invariants

- No model training.
- No learned registry entries.
- No new training rows.
- No ranker.
- No forecast model.
- No operator-facing forecast or ranking.
- No counterfactual learner.
- No case-memory learner.
- No dynamic investigation.
- No cross-city learned transfer.
- No promotion of candidate inventory into fuel without a separate explicit package.
- No new scout backlog that requires another pre-closeout scout.

## Required lanes

### Lane A — L4 case-stub content verification scout

Verify whether L4 candidate artifacts from the previous scout are content-backed or only path/name-lineage.

Output:

```text
E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json
```

Classify candidates:

```text
content_verified
path_only
needs_manual_review
not_promotable_before_closeout
```

No case-memory rows are materialized in this package.

### Lane B — CHECK calibration join readiness scout

Determine whether CHECK/Watch/Outcome/Brief/limitation artifacts can support a descriptive CHECK scorecard before closeout.

Output:

```text
E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json
```

Classify:

```text
ready_for_descriptive_scorecard
fixture_only
operator_resolved_pairs_absent
epoch4_candidate
```

### Lane C — Workflow/review-state history scout

Scout review-state artifacts for usable non-live workflow history.

Output:

```text
E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json
```

### Lane D — Watch ranking descriptive signal scout

Scout non-live Watch ranking signals, but do not convert them into R3 fuel.

Output:

```text
E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json
```

Must state:

```text
verified exposure required for primary R3 fuel
historical unverified signals are descriptive only
```

### Lane E — Simulation/backtest input scout

Scout event-duration, backlog, stale-source, closure, and other backtestable histories.

Output:

```text
E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json
```

### Lane F — Identity/graph evaluation fuel scout

Scout candidate CER/SEG ambiguity and graph-edge-eval fixtures.

Output:

```text
E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json
```

### Track 0 rider — final backlog + publication home + no-model guard

Output:

```text
E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json
E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json
E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json
E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json
E3_FINAL_NONLIVE_HIDDEN_FUEL_LEDGER_ROW.json
HASH_MANIFEST.json
LINE_ENDING_REPORT.json
```

## Publication-home recommendation

Because `outputs/` may be gitignored, recommend a durable publication home for governance artifacts before full closeout:

```text
publications/epoch3/...
```

or equivalent repo-tracked path for decisions, ledger rows, limitations, hash manifests, and summaries. Bulk data may remain ignored.

## Deliverable

A single output root:

```text
outputs/epoch3_final_nonlive_hidden_fuel_scout_r1
```

With runner and tests:

```text
scripts/run_epoch3_final_nonlive_hidden_fuel_scout_r1.py
tests/test_epoch3_final_nonlive_hidden_fuel_scout_r1.py
```
