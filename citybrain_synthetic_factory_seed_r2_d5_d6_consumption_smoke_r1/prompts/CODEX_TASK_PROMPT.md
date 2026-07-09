# CODEX TASK PROMPT — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1

Run the D5/D6 product consumption smoke over the locked Seed R2 Product Consumption R1 output.

Use:

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py -q
```

Close with status:

```text
PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS
```

Do not mutate upstream roots. Do not package raw provider payloads or secrets. Preserve synthetic/replay/donor-context-only boundaries.
