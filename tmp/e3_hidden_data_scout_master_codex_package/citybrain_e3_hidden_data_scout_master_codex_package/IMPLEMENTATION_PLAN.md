# Implementation plan

## Parent orchestrator

1. Load latest Epoch 3 foundation/master/backfill/forecast-preflight outputs if present.
2. Build an artifact-root inventory.
3. Dispatch lanes A-E in parallel after inventory.
4. Track 0 rider runs in parallel and consolidates all additional scout opportunities.
5. Final integration normalizes all candidate catalogs, checks boundaries, emits no-model guard, corpus delta, limitations, ledger row, hash manifest, and line-ending report.

## Dependency rules

- Lanes may run in parallel after global inventory.
- No lane may mark a candidate as training fuel.
- Any lane that finds enough evidence for a materialization package must output a follow-on package recommendation, not materialize silently.
- Final integration must deduplicate candidates across lanes and assign a recommended next package for each top candidate.

## Output folders

Write final artifacts to:

```text
outputs/epoch3_hidden_data_scout_master_r1/
```

## Expected final status

```text
PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS
```

Acceptable limitations:
- Some artifact roots inaccessible.
- Some source refs point to missing local files.
- Some candidate families have counts but insufficient lineage.
- Some reports only support descriptive usefulness, not learning fuel.
- Perception remains candidate-only.
