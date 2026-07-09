# Clean-session Codex task prompt — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH

Use this package to create the Seed R2 mobility-depth refresh addendum.

Do not ask for more data before running. Use only the existing repo outputs and external raw roots.
Do not mutate Seed R1 or any acquisition output roots.

Run:

```powershell
python scripts/run_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py `
  --seed-r1 outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1 `
  --r2e outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL `
  --out outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH
```

Then add/keep a repo test:

```powershell
python -m pytest tests/test_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py -q
```

Expected final status:

`PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS`

Append `progress.md` after passing tests.
