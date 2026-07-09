# Codex Handoff — Seed R3 Loop Convergence / Event Adapter R1

## Task

`MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1`

## Goal

Make the synthetic factory a first-class **Event Fabric source adapter** for the main product loop. The factory must stop being a parallel fixture universe. It should emit adapter-feed rows that Event Fabric can append/replay/resolve/quarantine/materialize.

## Inputs

Required:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT`
- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1`

Optional:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1`
- current Event Fabric V2/V2.5 roots if present
- current 4-family loop roots if present

## Product loop families

The output must align to these four families exactly:

```text
mobility_access
building_compliance
permit_inspection_delay
asset_infrastructure
```

## Required outputs

Write to:

`outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-LOOP-CONVERGENCE-EVENT-ADAPTER-R1`

Required files:

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

## Implementation requirements

1. Read the Seed R3 preflight domain fuel ledger and summary.
2. Read Seed R2 product consumption counts for prior product fixtures.
3. Select representative count-bearing rows across the seven non-mobility domains, but map them into the four product-loop families.
4. Generate Event Fabric source-adapter rows with event-like envelopes.
5. Include gold, dirty-source, challenge, and scenario rows.
6. Add deliberately ambiguous resolver stress cases.
7. Add expected unresolved and quarantine rows.
8. Produce a cadence replay plan: batch, 10x, 60x, and wall-clock simulation are all allowed as replay-only modes.
9. Produce an AI diagnostic review gate: this is diagnostic only, never training fuel or human review fuel.
10. Preserve read-only behavior for all inputs.
11. Run exact secret scans against output root and package.
12. Append progress.md entry.

## Boundary

This task is not a live-source task and not a control task. It must keep all outputs labelled local/replay/synthetic/donor-context only.

No:

- production live ingestion claim
- official Dubai truth claim
- live monitoring claim
- public API claim
- dispatch/control/enforcement claim
- legal/certified finding
- person-level data
- credentials or raw provider payloads in package

## Expected final status

`PASS_SYNTHETIC_FACTORY_SEED_R3_LOOP_CONVERGENCE_EVENT_ADAPTER_R1_WITH_LIMITATIONS`
