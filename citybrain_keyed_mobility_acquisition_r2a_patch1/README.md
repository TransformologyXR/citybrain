# CityBrain Keyed Mobility Acquisition R2A — LTA DataMall + TfL

Status: `READY_FOR_CODEX_KEYED_SMOKE_WITH_SANDBOX_DNS_LIMITATION`

This package promotes the R1 acquisition cart into a keyed-mobility acquisition smoke/full-pull handoff for:

- Singapore LTA DataMall keyed APIs
- TfL Unified API keyed requests

The current ChatGPT sandbox could not resolve `datamall2.mytransport.sg` or `api.tfl.gov.uk`, so key validity is **not confirmed here**. The included scripts are designed for the networked Codex/local repo environment.

## Security rule

No API keys are stored in this package. Use environment variables or an untracked local `.env` file based on `secrets/lta_tfl.env.template`.

## Smoke command

```powershell
cd C:\Users\hazem\Documents\CityBrain
python outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A\scripts\harvest_lta_tfl_keyed_sources.py `
  --out C:\Users\hazem\Documents\CityBrain\outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN `
  --raw-root C:\data\citybrain\raw\keyed_mobility_r2a `
  --smoke
```

## Full-pull command

```powershell
python outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A\scripts\harvest_lta_tfl_keyed_sources.py `
  --out C:\Users\hazem\Documents\CityBrain\outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN `
  --raw-root C:\data\citybrain\raw\keyed_mobility_r2a `
  --full
```

## Expected package output after Codex run

- `R2A_MASTER_DECISION.json`
- `SOURCE_STATUS_LEDGER_R2A.csv`
- `HARVEST_REPORT_R2A.json`
- `DOMAIN_FEED_MANIFEST_R2A.json`
- `SAMPLE_ROW_COUNTS_R2A.csv`
- `RAW_EXTERNAL_CHECKSUM_MANIFEST_R2A.json`
- `KNOWN_BLOCKERS_RUNTIME.md`
- `CODEX_CLOSEOUT.md`

Raw API payloads must remain under `C:\data\citybrain\raw`, not committed into the repo.


## Patch 1 endpoint confirmation

- LTA base remains `https://datamall2.mytransport.sg/ltaodataservice`.
- TfL swagger is `https://api.tfl.gov.uk/swagger/docs/v1`.
- TfL road status endpoint has been normalized to `/Road/all/Status`.
- Sandbox DNS/fetch failure is not treated as an auth failure or obsolete endpoint.
