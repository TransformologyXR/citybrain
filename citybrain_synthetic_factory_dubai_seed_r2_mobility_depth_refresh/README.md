# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH package

Status: `READY_FOR_CODEX_SYNTHETIC_FACTORY_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_NO_SECRETS`

This is a Codex handoff package, not a completed run. It provides a runner, static tests,
contracts, and a task prompt for refreshing the already-locked `MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1`
with the deeper `R2E` LTA/TfL mobility donor/context distributions.

## Purpose

Use `R2E` read-only to create a **Seed R2 mobility-depth addendum**:

- richer local/replay Event Fabric mobility rows,
- updated WATCH mobility queue fixtures,
- ASK entity/profile fixtures for mobility donor context,
- CHECK claimability fixtures that reject Dubai/live/action overclaims,
- BRIEF packet fixtures,
- SPATIAL overlay fixtures,
- distribution/profile manifests,
- source-class, secret-scan, and no-action audits.

## Hard boundary

`R2E` LTA/TfL data is **donor/context only**. It must not become Dubai truth, live monitoring,
dispatch/control/enforcement, certified, or legal evidence.

Seed R1 is read-only. Do not mutate, overwrite, or silently relabel Seed R1 outputs.

## Default Codex command

```powershell
python scripts/run_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py `
  --seed-r1 outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1 `
  --r2e outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL `
  --out outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R2-MOBILITY-DEPTH-REFRESH

python -m pytest tests/test_main_citybrain_synthetic_factory_dubai_seed_r2_mobility_depth_refresh.py -q
```

## Expected final status

`PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS`

Example logging policy: TfL URLs in logs must be redacted as `app_key=REDACTED`.
