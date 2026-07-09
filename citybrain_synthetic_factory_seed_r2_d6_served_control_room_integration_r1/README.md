# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1-PACKAGE

Status: `READY_FOR_CODEX_SYNTHETIC_FACTORY_SEED_R2_D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_WITH_NO_SECRETS`

Purpose: consume the locked D5 served-runtime integration output as a read-only input and create a bounded D6 served control-room integration pack.

This package does **not** create a production frontend, public API, live monitoring surface, dispatch/control surface, enforcement workflow, legal/certified finding, or official Dubai truth claim.

## Inputs

Required:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1`

Optional, read-only context:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1`
- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1`

## Run

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_d6_served_control_room_integration_r1.py `
  --d5-served-runtime outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1 `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --d5d6-smoke outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1
```

Then run the output regression test Codex should create or copy into the repo.

## Expected lock status

`PASS_SYNTHETIC_FACTORY_SEED_R2_D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_WITH_LIMITATIONS`

## Boundary

All outputs must remain:

- synthetic/replay/donor-context only
- not Dubai official truth
- localhost/local-file only
- no live monitoring
- no dispatch/control/enforcement/legal/certified claim
- no human/person-level records
- no credentials or raw provider payloads
