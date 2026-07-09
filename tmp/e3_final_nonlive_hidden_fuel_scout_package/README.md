# MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1

Final pre-closeout non-live hidden-fuel scout for CityBrain Epoch 3.

This package exists because the live/operator fuel program cannot run while the system is not live. It performs one final, bounded scout over non-live corpus evidence before moving all remaining candidates into backlog.

Expected closeout:

```text
PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS
```

Core rule:

```text
This is the last pre-closeout scout. It may verify candidate evidence and classify backlog, but it must not materialize new training rows, create models, or spawn follow-on scouts before Epoch 3 closeout.
```

## Parent shape

One parent package with six scout lanes and one Track 0 rider:

```text
Lane A — L4 case-stub content verification scout
Lane B — CHECK calibration join readiness scout
Lane C — Workflow/review-state history scout
Lane D — Watch ranking descriptive signal scout
Lane E — Simulation/backtest input scout
Lane F — Identity/graph evaluation fuel scout
Track 0 rider — final backlog classification + publication-home recommendation + no-model guard
```

## Why this exists

The master scout catalog has already drawn the map. This package does not broaden the map indefinitely. It answers one question:

```text
Which non-live candidates are content-backed enough to influence Epoch 3 closeout, and which should be parked as Epoch 4 backlog?
```

## Non-live constraint

Because the system is not live:

```text
operator-paced disposition fuel is deferred
R3A/R3B operator-fuel thresholds cannot be expected to arm in Epoch 3
L4 aggregation-floor fuel cannot be expected to arm from live sessions
non-live corpus mining can still support L2/L3/L4/CHECK/identity/backlog planning
```
