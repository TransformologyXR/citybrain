# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1

## Objective

Consume the locked Product Consumption R1 output and prove a bounded local product-smoke path:

```text
Seed R1 + Seed R2 product fixtures
→ combined WATCH / EVENT / ASK / CHECK / BRIEF / SPATIAL feeds
→ D5 runtime packet smoke responses
→ D6 local control-room index validation
→ no-action / boundary / secret audits
```

This is **not** production runtime, not live monitoring, and not a real Dubai operational claim.

## Run

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1
```

Then:

```powershell
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py -q
```

## Required outputs

- `D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json`
- `PRODUCT_FEED_COUNTS_R1.json`
- `D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl`
- `D6_LOCAL_INDEX_VALIDATION_R1.json`
- `D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html`
- `BOUNDARY_AND_NO_ACTION_AUDIT_R1.json`
- `SECRET_SCAN_REPORT_R1.json`
- `HASH_MANIFEST.json`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

1. Product Consumption R1 is consumed read-only.
2. Input Product Consumption R1 status is accepted.
3. Combined feed counts are preserved:
   - EVENT = 55
   - WATCH/ASK/CHECK/BRIEF/SPATIAL = 11 each
   - D5 runtime packet fixtures = 6
4. D5 smoke emits one safe response per D5 runtime packet.
5. D6 local index validates present and is copied/augmented as local-only consumption index.
6. Secret scan passes.
7. Boundary audit passes.
8. No raw provider payloads, credentials, human/person-level data, official Dubai truth, live monitoring, dispatch/control/enforcement/legal/certified claim.
