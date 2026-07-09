# Implementation Plan — MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1 v2

## Preflight

1. Load prior output roots from `outputs/` if available.
2. Verify the final known Epoch 3 chain statuses.
3. Confirm no-model/no-product-surface invariants.
4. Create `publications/epoch3/` if absent.
5. Add/verify `.gitattributes` LF rules for publications.

## Lane A — Publication-home sweep

- Copy or synthesize durable governance artifacts from each prior Epoch 3 package.
- Record missing artifacts as limitation rows; do not fail if bulk output is intentionally ignored.
- Emit `E3_PUBLICATION_HOME_SWEEP_REPORT.json`.

## Lane B — Master ledger and learned registry snapshot

- Emit `E3_MASTER_LEDGER.json` listing every package and publication path.
- Emit `E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json` with exactly one allowed experimental component.

## Lane C — Loop closeout synthesis

- Emit final loop status table and deferred capability accounting.
- Confirm full Epoch 3 closeout type is minimum acceptable with limitations.

## Lane D — Forecast and city-divergence framing

- Encode offline forecast result and limitations in a row.
- Encode London/NYC divergence as empirical reason to keep cross-city learned transfer parked.

## Lane E — Epoch 4 handoff

- Emit inherited arming/evaluator handoff.
- Emit fuel reality finding.
- Emit Epoch 4 fork row.

## Final integration

- Emit closeout decision, limitations, ledger row.
- Emit no-forbidden-capability audit.
- Emit hash manifest and LF report.
- Run focused tests.

## Expected outputs

```text
E3_CLOSEOUT_DECISION.json
E3_PUBLICATION_HOME_SWEEP_REPORT.json
E3_MASTER_LEDGER.json
E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json
E3_LOOP_CLOSEOUT_TABLE.json
E3_FORECAST_RESULT_FRAMING_ROW.json
E3_CITY_DIVERGENCE_WARNING_ROW.json
E3_ARMING_HANDOFF_TO_EPOCH4.json
E3_EPOCH4_FORK_DECISION_ROW.json
E3_FUEL_REALITY_FINDING_ROW.json
E3_NO_FORBIDDEN_CAPABILITY_AUDIT.json
E3_CLOSEOUT_LIMITATIONS.json
E3_CLOSEOUT_LEDGER_ROW.json
HASH_MANIFEST.json
LINE_ENDING_REPORT.json
```
