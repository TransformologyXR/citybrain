# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1

Codex package to consume the locked Synthetic Factory Dubai Seed R1 plus Seed R2 mobility-depth refresh into a bounded product-feed layer.

This is a handoff package, not a run result. It must not mutate Seed R1, Seed R2, R2E, or acquisition outputs.

## Purpose

Turn existing synthetic factory artifacts into product-consumable fixtures for WATCH, ASK, CHECK, BRIEF, SPATIAL, Event Fabric local/replay, D5 local served runtime packet smoke, and D6 control-room companion index.

## Run

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r2_product_consumption_r1.py `
  --seed-r1 outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1 `
  --seed-r2 outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
```

## Boundary

This consumes synthetic/replay/donor-context fixtures only. It creates no official Dubai truth, no live monitoring, no dispatch/control/enforcement/legal/certified claim, and no human/person-level records.
