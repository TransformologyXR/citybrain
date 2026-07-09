# Acceptance Criteria

## Hard pass criteria

1. The gate is named `MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE`.
2. The gate is documented as an Epoch 3 entry gate, not a new epoch.
3. The arming manifest is machine-evaluable and uses structured requirements.
4. The evaluator is named `epoch3_arming_status`.
5. Threshold crossings emit ledger rows and do not silently start work.
6. Loop numbering is correct:
   - Loop 1: outcome/calibration/ranking
   - Loop 2: backtest/forecasting
   - Loop 3: causal/counterfactual
   - Loop 4: institutional memory
7. `L3_COUNTERFACTUAL` and `L4_CASE_MEMORY` both appear in the manifest.
8. Exposure/propensity logging is armed on day one.
9. Records without exposure logging are marked `propensity_unknown`.
10. Primary R3 thresholds require `propensity_status = known`.
11. Primary R3 thresholds require at least three distinct `operator_refs`.
12. L1.R3a offline ranker experiments require LearnedComponentRegistry registration.
13. L1.R3a has `consuming_surfaces: []`.
14. L1.R3b cannot arm without exploration floor, static holdouts, ranker-off replay, and CHECK regression green.
15. L2.R2 forecast model cannot arm without a BacktestReport.
16. L3 counterfactual cannot arm without propagation rules, fidelity/surrogate gate, assumptions, uncertainty, and CHECK on every packet.
17. L4 case memory cannot arm without retention/deletion/privacy/source/outcome lineage enforcement.
18. The gate publication is atomic: report ref + manifest ref + evaluator ref + hash manifest ref.
19. The baseline report is pinned to corpus and manifest hashes.
20. No official action, dispatch, enforcement, certified/legal finding, or autonomous workflow claim is introduced.

## Reference fixture expectations

| Fixture | Expected result |
|---|---|
| `metrics_day_one.json` | only day-one work armed; R3a/R3b not armed |
| `metrics_pass_l1_r3a.json` | R3a armed; R3b not armed |
| `metrics_pass_l1_r3b.json` | R3a and R3b armed |
| `metrics_fail_operator_diversity.json` | R3a/R3b blocked by operator diversity |
| `metrics_fail_propensity_unknown.json` | R3a/R3b blocked by known-propensity requirement |

## Non-acceptance conditions

Reject the implementation if any of these occur:

- `L3_CASE_MEMORY<underscore>LEARNING` appears anywhere as the institutional-memory ID.
- a ranker experiment runs without a registry entry.
- a forecasting model can start before `BacktestReport.exists == true`.
- threshold requirements are stored only as prose strings.
- arming starts work automatically.
- synthetic/replay records can silently enter training manifests.
- operator data can be used below the aggregation floor.
