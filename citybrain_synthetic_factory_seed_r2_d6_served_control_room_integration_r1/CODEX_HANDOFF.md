# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1

## Goal

Promote the D5 served-runtime integration result into a D6 served-control-room integration pack that is locally viewable and traceable.

This is a product-surface integration smoke, not a production frontend. It should prove that the six served runtime responses and synthetic Seed R2 product feeds can be represented as bounded D6 review cards with limitations, traceability, and no-action boundaries.

## Inputs

Required:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1
```

Optional read-only context:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1
```

## Required outputs

```text
D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_DECISION.json
D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl
D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html
D6_RUNTIME_RESPONSE_BINDING_REPORT_R1.json
D6_ROUTE_LINK_VALIDATION_R1.json
D6_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json
SECRET_SCAN_REPORT_R1.json
HASH_MANIFEST.json
CODEX_CLOSEOUT.md
```

## Acceptance criteria

- D5 served runtime integration consumed read-only.
- Product Consumption R1 and D5/D6 smoke roots, if provided, consumed read-only.
- Six served runtime responses become D6 control-room cards.
- Local HTML index generated and structurally validated.
- Every card preserves limitation refs and no-action boundary.
- No public API or production frontend claim.
- No external network calls.
- No raw provider payloads packaged.
- No credentials written.
- No human/person-level records.
- No LTA/TfL/OPSD donor-context feed treated as Dubai truth.
- No dispatch/control/enforcement/legal/certified claim.
- Hash manifest verifies packaged files.

## Suggested commands

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_d6_served_control_room_integration_r1.py `
  --d5-served-runtime outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1 `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --d5d6-smoke outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1
```

```powershell
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r2_d6_served_control_room_integration_r1.py -q
```
