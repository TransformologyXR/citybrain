# Task Prompt — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1

Build a read-only product-consumption layer from the accepted Synthetic Factory Dubai Seed R1 and Seed R2 mobility-depth refresh.

Run:

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_product_consumption_r1.py `
  --seed-r1 outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1 `
  --seed-r2 outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
```

Then create/ensure a repo test:

```powershell
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r2_product_consumption_r1.py -q
```

Do not package raw provider payloads, secrets, failed response bodies, or any human/person-level records.

Final expected status:

`PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS`
