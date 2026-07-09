# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1

Readable name: **Seed R3 Loop Convergence / Factory-as-Event-Fabric Adapter**.

Purpose: make the synthetic factory play its intended role in the main CityBrain loop by emitting Seed R3 outputs as **Event Fabric source-adapter feeds**, not as a parallel standalone fixture universe.

This package consumes the Seed R3 cross-city domain fuel preflight and the existing Seed R2 product-consumption pack read-only, then produces adapter-ready source feeds aligned to the product loop's four families:

1. mobility_access
2. building_compliance
3. permit_inspection_delay
4. asset_infrastructure

The output remains local/replay/synthetic/donor-context only. It does not claim Dubai official truth, live monitoring, dispatch, control, enforcement, legal/certified conclusions, or product readiness.

## Expected lock status

```text
PASS_SYNTHETIC_FACTORY_SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_R1_WITH_LIMITATIONS
```

## Why this exists

Seed R1/R2 proved the factory can produce WATCH/ASK/CHECK/BRIEF/SPATIAL fixtures and D5/D6 surfaces. The convergence risk is that factory fixtures bypass Event Fabric. This task moves the factory through the front door: source-adapter event feed → resolver stress cases → expected unresolved/quarantine → cadence replay plan.

## Codex command

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r3_loop_convergence_event_adapter_r1.py `
  --seed-r3-preflight outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1
```

Optional if the built-environment/civic/compliance refresh has already run:

```powershell
  --seed-r3-refresh outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1
```

Then run:

```powershell
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r3_loop_convergence_event_adapter_r1.py -q
```

## What it produces

- `SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_DECISION.json`
- `LOOP_FAMILY_ALIGNMENT_REPORT.json`
- `EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl`
- `SOURCE_ADAPTER_MANIFEST_R1.json`
- `RESOLVER_STRESS_CASES_R1.jsonl`
- `EXPECTED_UNRESOLVED_AND_QUARANTINE_CASES_R1.jsonl`
- `CADENCE_REPLAY_PLAN_R1.json`
- `EVENT_FABRIC_INGESTION_CONTRACT_R1.json`
- `AI_DIAGNOSTIC_REVIEW_GATE_R1.md`
- `BOUNDARY_AND_NO_ACTION_AUDIT.json`
- `SECRET_SCAN_REPORT.json`
- `HASH_MANIFEST.json`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

- Four product-loop families are present exactly: mobility_access, building_compliance, permit_inspection_delay, asset_infrastructure.
- Factory output is emitted as Event Fabric source-adapter feed rows, not only product fixtures.
- Every event row carries `source_class`, `truth_layer`, `donor_refs`, `limitation_refs`, `expected_resolution_state`, and `loop_family`.
- Dirty/challenge cases intentionally exercise resolver ambiguity and quarantine.
- Cadence replay plan exists but remains local/replay-only.
- Seed R3 preflight and Seed R2 product consumption are consumed read-only.
- No raw provider payloads, secrets, credentials, or person-level records are packaged.
- No Dubai official truth, live monitoring, public API, production frontend, dispatch/control/enforcement/legal/certified claim.
