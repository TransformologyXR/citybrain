# Codex Handoff — MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL

## Goal

Run a deeper keyed mobility acquisition over LTA DataMall and TfL after R2A/R2B proved access. R2E should increase mobility donor/context depth while keeping R2/R2A/R2B and `SYNTHETIC-FACTORY-DUBAI-SEED-R1` immutable.

## Inputs

```text
outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE
outputs/MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN
C:\data\citybrainaw\keyed_mobility_r2a
```

## Runtime credentials

Use environment variables or an untracked env file. Do not write credentials into repo, output package, or logs.

## Required command

```powershell
python citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull\scriptsun_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py `
  --out outputs\MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL `
  --raw-root C:\data\citybrainaw\keyed_mobility_r2e `
  --mode depth `
  --max-lta-pages 2000 `
  --tfl-modes tube,dlr,elizabeth-line,overground,tram,national-rail,bus `
  --include-optional
```

Optional bus-arrival sampling after bus stops land:

```powershell
  --bus-arrival-sample-size 100
```

## Required tests

```powershell
python -m pytest citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull	ests	est_r2e_package_static.py -q
python -m pytest tests	est_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py -q
```

## Acceptance criteria

- LTA full paginated endpoints are fetched until short/empty page, repeated hash, provider failure, or `--max-lta-pages`.
- TfL expanded mode matrix is fetched using explicit `User-Agent` and `Accept` headers.
- Only successful `200/201` payloads are persisted under external raw root.
- No failed response bodies are written.
- All request URLs in reports redact `app_key`.
- Extended OBU SDK key remains key-present-not-used-for-standard-REST.
- R2/R2A/R2B/Synthetic Factory R1 outputs are consumed read-only or only referenced, never mutated.
- LTA/TfL feeds are donor/context only, not Dubai facts.
- No human/person-level, dispatch/control/enforcement/legal/certified claims.
- Exact secret scan passes across package, output root, and external raw root.

## Expected final status

```text
PASS_R2E_KEYED_MOBILITY_DEPTH_PULL_WITH_LIMITATIONS
```
