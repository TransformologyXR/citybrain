# Acceptance Criteria — MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1 v2

The package passes only if all criteria hold.

## Publication durability

- `publications/epoch3/` exists or an equivalent durable path is created.
- `.gitattributes` or equivalent LF-stability rule covers publication artifacts.
- `E3_PUBLICATION_HOME_SWEEP_REPORT.json` covers the full Epoch 3 chain.
- Every ledgered PASS has a durable governance publication path or an explicit limitation row.

## Master ledger

- `E3_MASTER_LEDGER.json` lists every Epoch 3 package and status.
- The ledger includes proof artifact refs and publication paths.
- The ledger distinguishes foundation closeout, execution packages, scout packages, and final closeout.

## Learned component snapshot

- Snapshot includes exactly one allowed experimental learned component: `forecast.permit_stall_v0.r1`.
- It has `status=experimental`, `consuming_surfaces=[]`, `frozen_replay_only=true`, and no release row.
- No ranker/product forecast/counterfactual/case-memory/dynamic/cross-city learned component exists.

## Forecast framing

- AP/Brier improvement is stated as real offline evidence.
- Absolute weakness and recall-at-fixed-precision limitation are stated.
- The row explicitly says the pipeline is validated but the model is not deployable.
- London/NYC divergence is cited as empirical support for city-stratified Epoch 4 work and parked cross-city learned transfer.

## Arming/evaluator handoff

- Epoch 4 inherits the arming evaluator, threshold definitions, fuel snapshot chain, and no-model guard cadence.
- Deferred capabilities remain governed by inherited thresholds.
- Epoch 4 cannot relitigate thresholds without explicit governance delta.

## Fuel reality

- Closeout states that the system is not live and operator-paced fuel is deferred.
- Ranking and L4 memory did not arm because the system refused to fabricate fuel.
- This is framed as correct governance, not failure.

## Epoch 4 fork

- Go-live/review-pilot path is defined.
- Non-live mechanical backlog path is defined.
- P0/P1/P2 backlog items are classified.

## Boundaries

- No new model training.
- No new learned registry entries.
- No operator-facing ranking or forecast.
- No product ForecastPacket surface.
- No case-memory learner.
- No learned counterfactual.
- No dynamic investigation.
- No cross-city learned transfer.
- No official action/dispatch/enforcement/legal/certified claim.

Expected final status:

```text
PASS_E3_CLOSEOUT_WITH_LIMITATIONS
```
