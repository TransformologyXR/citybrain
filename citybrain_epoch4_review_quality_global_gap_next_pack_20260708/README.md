# CityBrain Epoch 4 — Review Quality + Global Gap Next Pack

Purpose: act on the deep data estate audit without locally patching the founder cards while ignoring global data gaps.

The deep audit's top move was `FIX_REVIEW_PACK_QUALITY_FIRST`, but it also exposed global data estate gaps:

- 273 sources with no consuming flow
- 462 unknown freshness
- 430 unknown source class
- 456 unknown schema
- 526 missing/unknown geometry

This pack therefore has two lanes:

1. **Review Pack Quality Upgrade R4/R5** — improve the founder/eval review pack evidence layer, classify diagnostic vs product-review readiness, and avoid overreading the 16 cards.
2. **Data Estate Gap Routing R1** — route the global source/freshness/schema/geometry/consuming-flow gaps into candidate remediation queues and crosswalk them back to review-card gaps.

Then a final reverify confirms both lanes stayed read-only and did not fabricate session/fuel/product claims.

## Recommended run

Run the sequence package:

```powershell
cd C:\Users\hazem\Documents\CityBrain
python scripts\run_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py
python -m pytest tests\test_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py -q
python scripts\run_main_citybrain_epoch4_review_quality_global_gap_sequence_r1.py --validate-only
```

## Packages

- `main-citybrain-epoch4-review-pack-quality-upgrade-r4-r1.zip`
- `main-citybrain-epoch4-data-estate-gap-routing-r1.zip`
- `main-citybrain-epoch4-review-quality-global-gap-final-reverify-r1.zip`
- `main-citybrain-epoch4-review-quality-global-gap-sequence-r1.zip`


## Hard boundaries

This package is read-only / additive unless explicitly writing new derived candidate artifacts under `outputs/` and `publications/`.

Do not create or claim:
- founder session results unless a real response input file is supplied for a later package; this package must not run a session.
- operator fuel, training rows, learned arming, learned ranking, model training, or calibration fuel.
- live ingestion, production monitoring, public API, alerting, dispatch, control, enforcement, official case/ticket, legal/certified finding, or source-truth mutation.
- product forecast surface, ForecastPacket, prediction authority, or calibrated simulator claim.
- mutation of raw/provider/source-truth payloads or canonical truth tables.

All fixes must be either:
- review-pack presentation/evidence assembly fixes, or
- derived/candidate overlays, queues, diagnostics, or recommendations.

