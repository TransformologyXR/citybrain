# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1

## Goal

Turn the locked Seed R2 product-consumption fixtures and D5/D6 consumption smoke into a bounded localhost-served D5 runtime integration.

This task should prove:

1. Product Consumption R1 and D5/D6 Consumption Smoke R1 are consumed read-only.
2. A localhost-only served D5 runtime contract can respond to the six synthetic D5 runtime packet fixtures.
3. The D6 local control-room index can reference or consume the served packet responses.
4. The whole integration remains synthetic/replay/donor-context only.

## Inputs

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1
```

Required files from Product Consumption R1:

```text
D5_RUNTIME_PACKET_FIXTURES_R1.jsonl
WATCH_QUEUE_COMBINED_R1.jsonl
EVENT_REPLAY_COMBINED_R1.jsonl
ASK_FIXTURE_INDEX_R1.jsonl
CHECK_FIXTURE_INDEX_R1.jsonl
BRIEF_FIXTURE_INDEX_R1.jsonl
SPATIAL_OVERLAY_INDEX_R1.jsonl
```

Required files from D5/D6 Consumption Smoke R1:

```text
D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl
D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html
D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json
BOUNDARY_AND_NO_ACTION_AUDIT_R1.json
```

## Required implementation

Create or update:

```text
scripts/run_main_citybrain_synthetic_factory_seed_r2_d5_served_runtime_integration_r1.py
tests/test_main_citybrain_synthetic_factory_seed_r2_d5_served_runtime_integration_r1.py
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1/
```

The runner should support:

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_d5_served_runtime_integration_r1.py `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --d5d6-smoke outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1
```

Optional `--serve-smoke` mode may start an ephemeral localhost server bound to `127.0.0.1` only. If implemented, it must not bind `0.0.0.0`, must not call external URLs, and must shut down after the smoke test.

## Required outputs

```text
D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json
D5_LOCAL_SERVER_CONTRACT_R1.json
D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl
D5_RUNTIME_ENDPOINT_AUDIT_R1.json
D6_SERVED_CONTROL_ROOM_INDEX_R1.html
D6_SERVED_INDEX_VALIDATION_R1.json
RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json
SECRET_SCAN_REPORT_R1.json
HASH_MANIFEST.json
CODEX_CLOSEOUT.md
```

## Acceptance criteria

- Final status is `PASS_SYNTHETIC_FACTORY_SEED_R2_D5_SERVED_RUNTIME_INTEGRATION_R1_WITH_LIMITATIONS`.
- Product Consumption R1 is read-only.
- D5/D6 Consumption Smoke R1 is read-only.
- Six D5 runtime packet fixtures produce six served-runtime responses.
- Runtime contract is localhost-only.
- No external API/network call is made.
- D6 served index is generated and validates locally.
- No credentials are written.
- No raw provider payloads are packaged.
- No human/person-level records are introduced.
- All records remain synthetic/replay/donor-context only, not Dubai truth.
- No live monitoring, alerting, dispatch, control, enforcement, legal, certified, or production claim.
- Hash manifest verifies packaged outputs.

## Do not do

- Do not mutate Seed R1, Seed R2, Product Consumption R1, or D5/D6 Consumption Smoke R1.
- Do not call LTA, TfL, Open-Meteo, Overture, OSM, or any external provider.
- Do not store or print credential values.
- Do not treat LTA/TfL/OPSD donor data as Dubai facts.
- Do not claim production readiness or public API readiness.
