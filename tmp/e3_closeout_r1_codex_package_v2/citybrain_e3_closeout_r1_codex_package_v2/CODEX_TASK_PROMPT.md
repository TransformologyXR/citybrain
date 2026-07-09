# Codex Task Prompt — MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1 v2

You are working in the CityBrain repository on `main` unless instructed otherwise. Do not create branches, commit, push, reset, stash, delete, or clean the workspace unless explicitly asked by the user.

Implement and publish the Epoch 3 closeout as a closeout-only package.

## Required final status

```text
PASS_E3_CLOSEOUT_WITH_LIMITATIONS
```

## Non-negotiable framing

Epoch 3 is **not** closing as a perfect/product-live learning epoch. It closes as:

```text
MINIMUM_ACCEPTABLE_WITH_LOOP2_OFFLINE_EXPERIMENT
```

The closeout must state:

- Epoch 3 proved the governed learning/backtesting substrate.
- Epoch 3 found and used hidden historical forecast fuel.
- Epoch 3 registered one offline experimental forecast component.
- The offline forecast beat corrected no-model baseline on AP/Brier but is not product deployable.
- The system is not live; operator-paced fuel did not accumulate.
- Ranking, product forecasts, L4 case memory, dynamic investigation, and cross-city learned transfer remain deferred/blocked.

## Lane A — Publication home / durable governance sweep

Create/confirm a durable publication path such as:

```text
publications/epoch3/
```

Retroactively publish governance artifacts for the full Epoch 3 chain:

1. Entry Gate R1
2. Follow-up reconciliation R1
3. Day 1 instrumentation/harness R1
4. Phase 2 live exposure coverage R1
5. L1.R1/R2 outcome-calibration hardening R1
6. Pre-closeout convergence R1
7. Foundation closeout R1
8. Master Execution R1
9. L2 historical label backfill R1
10. L2.R2 forecast authority preflight R1
11. L2.R2 offline experimental forecast R1
12. Hidden data scout master R1
13. Final non-live hidden-fuel scout R1
14. Epoch 3 closeout R1

For each package, durable publication should include small governance artifacts only:

- decision
- ledger row
- limitations
- hash manifest
- line-ending report if present
- summary/status artifact

Do not publish bulk data, large JSONL outputs, raw source dumps, or model binaries.

Add or verify LF pinning for the publication path, e.g. `.gitattributes` rules for `publications/**`.

Emit:

```text
E3_PUBLICATION_HOME_SWEEP_REPORT.json
```

## Lane B — Master ledger and registry snapshot

Emit:

```text
E3_MASTER_LEDGER.json
E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json
```

The master ledger must list every Epoch 3 package, status, proof artifact, publication path, and boundary outcome.

The registry snapshot must show exactly one allowed experimental learned component:

```text
forecast.permit_stall_v0.r1
status = experimental
consuming_surfaces = []
frozen_replay_only = true
release_ledger_row = null
product_surface_created = false
```

No other learned/forecast/ranker/counterfactual/case-memory/dynamic/cross-city learned component is allowed.

## Lane C — Final status synthesis and loop closeout

Emit final loop table:

- L1 outcome/ranking: R0/R1/R2 foundation done; R3A/R3B not armed due to non-live/no operator fuel.
- L2 forecasting: offline experiment done; product forecast not armed.
- L3 counterfactual: minimum deterministic/replay-only path done; learned/simulation release not armed.
- L4 case memory: content candidates found; case memory not armed; deferred due to non-live/operator floor and policy/runtime limitations.

## Lane D — Forecast result and city-divergence framing

Emit:

```text
E3_FORECAST_RESULT_FRAMING_ROW.json
E3_CITY_DIVERGENCE_WARNING_ROW.json
```

Required language:

- The pipeline is validated; this specific model is not deployable.
- AP 0.191775 vs 0.107386 baseline proxy and Brier improvement are real offline results.
- Recall at fixed precision is weak, so no operator/product forecast surface is armed.
- London vs NYC label rates/performance diverge enough to make pooled/product claims unsafe.
- Cross-city learned transfer remains parked, with this result as empirical support.
- Epoch 4 L2 forecast improvement must be city-stratified from the start.

## Lane E — Arming/evaluator handoff and Epoch 4 fork

Emit:

```text
E3_ARMING_HANDOFF_TO_EPOCH4.json
E3_EPOCH4_FORK_DECISION_ROW.json
E3_FUEL_REALITY_FINDING_ROW.json
```

The handoff must state:

- Epoch 4 inherits the arming evaluator, threshold definitions, no-model guard cadence, and fuel-gauge snapshot chain.
- Deferred capabilities remain governed by the same thresholds; Epoch 4 does not relitigate the bar without an explicit governance delta.
- Since the system is not live, operator-paced fuel is deferred.

Epoch 4 fork:

1. If go-live / structured review pilot happens: run fuel sessions; R3A/R3B/L4 may arm as thresholds are met.
2. If not live: proceed with mechanical backlog only: city-stratified L2 improvement, additional transition target materialization, L4 content-backed stub work, CHECK descriptive scorecards, identity/graph eval fixtures.

## Global stop conditions

Do not create:

- new model training
- new learned registry entries
- ranker
- operator-facing forecast
- product ForecastPacket surface
- case-memory learner
- learned counterfactual
- dynamic investigation
- cross-city learned transfer
- official action/dispatch/enforcement/legal/certified claim
