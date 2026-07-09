# CityBrain Epoch 3 Entry Gate Codex Package

Package ID: `MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE`

This is a Codex-ready implementation package for the Epoch 3 entry gate. It does **not** define a new epoch and does **not** re-certify Epoch 2. It implements a bounded fuel-gauge gate that:

1. measures learning fuel at Epoch 3 entry,
2. verifies source/synthetic separation,
3. validates bounded scenario reality,
4. activates day-one exposure/propensity logging and exploration-floor infrastructure,
5. publishes machine-evaluable arming thresholds,
6. emits arming ledger rows when thresholds are crossed, and
7. keeps trained ranking, forecasting, counterfactuals, institutional memory, dynamic investigation, and cross-city learned transfer blocked until their own thresholds are met.

## Core artifacts

```text
CODEX_TASK_PROMPT.md                         Codex execution prompt
IMPLEMENTATION_PLAN.md                       Implementation sequence
ACCEPTANCE_CRITERIA.md                       Done definition and gates
specs/e3_entry_gate_spec.md                  Human-readable gate spec
specs/loop_numbering_crosswalk.md            Loop numbering guardrail
specs/arming_semantics.md                    Arming semantics and ledger behavior
specs/exposure_propensity_logging.md         Day-one exposure/propensity policy
specs/exploration_floor_spec.md              Exploration floor and holdout design
specs/machine_evaluable_thresholds.md        Threshold evaluation rules
specs/ledger_publication_spec.md             Atomic publication rules
manifests/epoch3_arming_manifest.json        Canonical machine-readable arming manifest
manifests/epoch3_arming_evaluator_spec.yaml  WATCH/dashboard/evaluator spec
manifests/gate_ledger_row.template.json      Atomic ledger row template
manifests/hash_manifest.template.json        Hash manifest template
schemas/*.schema.json                        JSON Schemas for integration
fixtures/*.json                              Pass/fail metric fixtures
scripts/evaluate_arming_status.py            Reference evaluator
scripts/build_hash_manifest.py               Local hash manifest generator
tests/*.py                                   Reference pytest tests
```

## Expected closeout

```text
PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS

ARMED_NOW:
  L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING
  L1.R0_WATCH_EXPLORATION_FLOOR_INFRA
  L1.R1_OUTCOME_LEDGER_HARDENING
  L1.R2_CALIBRATION_REPORT_HARDENING
  L2.R1_BACKTEST_HARNESS_BUILD
  E3.ARMING_STATUS_WATCH_FAMILY

NOT_ARMED:
  L1.R3A_OFFLINE_RANKER_EXPERIMENT
  L1.R3B_OPERATOR_FACING_LEARNED_RANKING
  L2.R2_FORECAST_MODEL
  L3_COUNTERFACTUAL
  L4_CASE_MEMORY
  DYNAMIC_INVESTIGATION_AGENT
  CROSS_CITY_LEARNED_TRANSFER
```

## Local smoke commands

From this package root:

```bash
python scripts/evaluate_arming_status.py \
  --manifest manifests/epoch3_arming_manifest.json \
  --metrics fixtures/metrics_day_one.json \
  --out /tmp/e3_arming_status_day_one.json

python scripts/evaluate_arming_status.py \
  --manifest manifests/epoch3_arming_manifest.json \
  --metrics fixtures/metrics_pass_l1_r3a.json \
  --out /tmp/e3_arming_status_l1_r3a.json

python scripts/build_hash_manifest.py --root . --out /tmp/e3_hash_manifest.json

pytest -q tests
```

## Non-claims

This package must not be implemented as:

- a new epoch,
- a model launch,
- a learned ranking release,
- a forecasting release,
- a production-live ingestion claim,
- an official action / dispatch / enforcement workflow,
- a legal, certified, or authority-finding system.

Threshold crossing means `MAY_BEGIN_UNDER_CADENCE_AFTER_LEDGER_ROW`; it never means work starts silently.
