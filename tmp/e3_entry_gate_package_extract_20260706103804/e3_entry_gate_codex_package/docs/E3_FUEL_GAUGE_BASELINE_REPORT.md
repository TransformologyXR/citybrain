# E3 Fuel Gauge Baseline Report

Gate: `MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE`  
Status: `PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS`  
Corpus version: `<corpus_version>`  
Hash manifest: `<hash_manifest_ref>`

## 1. Gate status

This gate does not create a new epoch and does not recertify Epoch 2. It measures empirical fuel available at Epoch 3 entry, verifies synthetic/source-class separation, validates bounded scenario reality, activates exposure/propensity logging and exploration-floor infrastructure, and publishes machine-evaluable arming thresholds.

## 2. Corpus/hash manifest

| Artifact | Ref | Hash |
|---|---|---|
| Corpus | `<corpus_ref>` | `<sha256>` |
| Source manifest | `<source_manifest_ref>` | `<sha256>` |
| Synthetic manifest | `<synthetic_manifest_ref>` | `<sha256>` |
| Scenario manifest | `<scenario_manifest_ref>` | `<sha256>` |
| Arming manifest | `epoch3_arming_manifest.json` | `<sha256>` |
| Baseline report | `E3_FUEL_GAUGE_BASELINE_REPORT.md` | `<sha256>` |

## 3. Arming evaluator status

| Field | Value |
|---|---|
| Evaluator | `epoch3_arming_status` |
| Component kind | `watch_family` |
| Dashboard panel | `epoch3_arming_status` |
| Ledger event on crossing | `EPOCH3_ARMING_THRESHOLD_CROSSED` |
| Arming semantics | `MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW_NOT_STARTED` |

## 4. Outcome/disposition fuel gauge

| Metric | Value | Notes |
|---|---:|---|
| Terminal dispositions, post-validation-fix, propensity known | `<n>` | `<notes>` |
| Confirmed | `<n>` | `<notes>` |
| Dismissed | `<n>` | `<notes>` |
| Needs more | `<n>` | `<notes>` |
| WATCH families represented | `<n>` | `<notes>` |
| Domain packs represented | `<n>` | `<notes>` |

## 5. Operator diversity / aggregation-floor status

| Metric | Value | Pass? |
|---|---:|---|
| Distinct operator refs | `<n>` | `<yes/no>` |
| Minimum terminal dispositions per operator | `<n>` | `<yes/no>` |
| Aggregation floor satisfied | `<true/false>` | `<yes/no>` |

## 6. Exposure and propensity logging status

| Metric | Value | Notes |
|---|---|---|
| Coverage | `<coverage>` | `<notes>` |
| Propensity unknown records | `<n>` | `<policy>` |
| Counted toward R3 thresholds | `<n>` | Must exclude unknown unless override ledger row exists |

## 7. Calibration sample-depth table

| Check type | Source class | Sample count | Compared to operator disposition? | Notes |
|---|---|---:|---|---|
| `<check_type>` | `<source_class>` | `<n>` | `<yes/no>` | `<notes>` |

## 8. Watch telemetry and throttling table

| Metric | Value | Notes |
|---|---:|---|
| Items/day | `<n>` | `<notes>` |
| Items/run | `<n>` | `<notes>` |
| Dominant family | `<family>` | `<notes>` |
| Dismissed % | `<pct>` | `<notes>` |
| Needs-more % | `<pct>` | `<notes>` |
| Throttled/deferred % | `<pct>` | `<notes>` |
| Queue depth | `<n>` | `<notes>` |

## 9. Exploration floor / holdout readiness

| Requirement | Status | Notes |
|---|---|---|
| Exploration floor enabled | `<true/false>` | `<notes>` |
| Static holdout families enabled | `<true/false>` | `<notes>` |
| Ranker-off replay available | `<true/false>` | `<notes>` |
| Operator throttle compatibility | `<true/false>` | `<notes>` |

## 10. LLM seat metrics

| Seat | Acceptance rate | Fallback rate | Unsafe proposal rate | Schema failure rate | CHECK rejection rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| G2 resolver proposal | `<pct>` | `<pct>` | `<pct>` | `<pct>` | `<pct>` | `<notes>` |
| G8/writer seat | `<pct>` | `<pct>` | `<pct>` | `<pct>` | `<pct>` | `<notes>` |

## 11. Perception shadow metrics

| Metric | Value | Notes |
|---|---|---|
| Feed count | `<n>` | candidate-only |
| Shadow duration | `<duration>` | `<notes>` |
| Candidate rate | `<rate>` | `<notes>` |
| Privacy/boundary failures | `<n>` | must be zero to arm further use |
| Evidence clip validity | `<pct>` | hash/timestamp/frame index |

## 12. Scenario replay coverage

| Mode | Scenario count | Passed | Failed | Fixture refs |
|---|---:|---:|---:|---|
| ASK | `<n>` | `<n>` | `<n>` | `<refs>` |
| WATCH | `<n>` | `<n>` | `<n>` | `<refs>` |
| CHECK | `<n>` | `<n>` | `<n>` | `<refs>` |
| BRIEF | `<n>` | `<n>` | `<n>` | `<refs>` |
| DIFF | `<n>` | `<n>` | `<n>` | `<refs>` |
| RECALL | `<n>` | `<n>` | `<n>` | `<refs>` |
| SPATIAL | `<n>` | `<n>` | `<n>` | `<refs>` |
| PERCEPTION shadow | `<n>` | `<n>` | `<n>` | `<refs>` |
| PLAN/SCHEDULE/SIMULATE fixed DAG | `<n>` | `<n>` | `<n>` | `<refs>` |

## 13. Synthetic/source-class separation

| Dataset tier | Exists? | Regenerable? | Training eligible? | Evaluation eligible? | Notes |
|---|---|---|---|---|---|
| Gold | `<yes/no>` | `<yes/no>` | no unless manifest-promoted real | yes | `<notes>` |
| Dirty source | `<yes/no>` | `<yes/no>` | no unless manifest-promoted real | yes | `<notes>` |
| Challenge | `<yes/no>` | `<yes/no>` | no | yes | `<notes>` |
| Scenario/replay | `<yes/no>` | `<yes/no>` | no | yes | `<notes>` |

## 14. Prediction preconditions

| Requirement | Status | Notes |
|---|---|---|
| First forecast target selected | `<true/false>` | `<target>` |
| Labels/history sufficient | `<true/false>` | `<notes>` |
| Frozen eval slice tooling ready | `<true/false>` | `<notes>` |
| Baseline/do-nothing comparator defined | `<true/false>` | `<notes>` |
| Uncertainty schema delta process ready | `<true/false>` | `<notes>` |
| BacktestReport exists | `<true/false>` | required before L2.R2 |

## 15. L3 counterfactual blocked path

`L3_COUNTERFACTUAL` remains blocked until propagation rules, simulator/fidelity gate, assumptions schema, uncertainty schema, and CHECK coverage exist.

## 16. L4 case memory blocked path

`L4_CASE_MEMORY` remains blocked until retention, deletion/privacy, operator aggregation floor, source-class coverage, and outcome lineage are enforced.

## 17. Q1–Q6 disposition-policy status

| Question | Status | Owner | Due | Enforcement fixture | Notes |
|---|---|---|---|---|---|
| Q1 aggregation floor | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |
| Q2 first forecast target | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |
| Q3 label imbalance policy | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |
| Q4 operator feedback weighting | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |
| Q5 case retention/deletion | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |
| Q6 uncertainty schema delta | `<status>` | `<owner>` | `<date>` | `<ref>` | `<notes>` |

## 18. Limitations

Use `docs/LIMITATIONS_TEMPLATE.md`.

## 19. Day-one Epoch 3 slate

```text
L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING
L1.R0_WATCH_EXPLORATION_FLOOR_INFRA
L1.R1_OUTCOME_LEDGER_HARDENING
L1.R2_CALIBRATION_REPORT_HARDENING
L2.R1_BACKTEST_HARNESS_BUILD
E3.ARMING_STATUS_WATCH_FAMILY
```

## 20. Not-armed capabilities

```text
L1.R3A_OFFLINE_RANKER_EXPERIMENT
L1.R3B_OPERATOR_FACING_LEARNED_RANKING
L2.R2_FORECAST_MODEL
L3_COUNTERFACTUAL
L4_CASE_MEMORY
DYNAMIC_INVESTIGATION_AGENT
CROSS_CITY_LEARNED_TRANSFER
```
