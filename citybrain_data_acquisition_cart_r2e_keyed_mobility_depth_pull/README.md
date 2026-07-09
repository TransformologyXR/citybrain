# MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL

Status: `READY_FOR_CODEX_KEYED_MOBILITY_DEPTH_PULL_WITH_NO_SECRETS`

This package is a **handoff package**, not a completed harvest result. It turns the successful R2A/R2B keyed mobility proof into a deeper acquisition plan for:

- Singapore LTA DataMall keyed REST feeds
- Transport for London Unified API keyed REST feeds

R2E should run in parallel with, and must not mutate, the already locked synthetic factory seed:

```text
MAIN-CITYBRAIN-SYNTHETIC-FACTORY-DUBAI-SEED-R1
PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS
```

## Security rule

No API keys are stored in this package. Use environment variables or an untracked env file.

## Expected input state

```text
R2  = PASS_SOURCE_ACQUISITION_CART_R2_P0_FULL_PULL_AND_NORMALIZATION_WITH_LIMITATIONS
R2A = PASS_KEYED_FULL_WITH_LIMITATIONS
R2B = PASS_R2B_BASE_CITY_PLUS_KEYED_MOBILITY_MERGE_WITH_LIMITATIONS
```

## Smoke command

```powershell
python citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull\scriptsun_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py `
  --out outputs\MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL `
  --raw-root C:\data\citybrainaw\keyed_mobility_r2e `
  --mode smoke
```

## Depth command

```powershell
python citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull\scriptsun_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py `
  --out outputs\MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2E-KEYED-MOBILITY-DEPTH-PULL `
  --raw-root C:\data\citybrainaw\keyed_mobility_r2e `
  --mode depth `
  --max-lta-pages 2000 `
  --tfl-modes tube,dlr,elizabeth-line,overground,tram,national-rail,bus
```

## Expected run outputs

- `R2E_MASTER_DECISION.json`
- `SOURCE_STATUS_LEDGER_R2E.csv`
- `DEPTH_PULL_REPORT_R2E.json`
- `DOMAIN_FEED_MANIFEST_R2E.json`
- `RAW_EXTERNAL_CHECKSUM_MANIFEST_R2E.json`
- `SAMPLE_ROW_COUNTS_R2E.csv`
- `NORMALIZED_MOBILITY_DONOR_SAMPLE_R2E.jsonl`
- `HTTP_CLIENT_POLICY_REPORT_R2E.json`
- `SECRET_SCAN_REPORT_R2E.json`
- `KNOWN_BLOCKERS_RUNTIME_R2E.md`
- `CODEX_CLOSEOUT.md`

Raw payloads must remain under `C:\data\citybrainaw\keyed_mobility_r2e` and must not be packaged or committed.
