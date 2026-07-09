# CODEX HANDOVER — MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A

## Goal

Validate the newly provided LTA DataMall and TfL credentials in the networked CityBrain repo environment, then run a bounded keyed-mobility smoke/full-pull into external raw storage and normalized manifests for the synthetic data factory.

## Critical security instruction

The keys were provided out-of-band by the user. Do **not** write them into source files, manifests, logs, progress.md, tests, ZIPs, or committed artifacts.

Inject them only as environment variables or an untracked local `.env` file:

```powershell
$env:LTA_DATAMALL_ACCOUNT_KEY="<provided LTA DataMall API Account Key>"
$env:LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY="<provided Extended OBU SDK Account Key>"
$env:TFL_PRIMARY_KEY="<provided TfL primary key>"
$env:TFL_SECONDARY_KEY="<provided TfL secondary key>"
```

Run the packaged secret scan with the variables set before packaging results:

```powershell
python scripts\validate_package_no_secrets.py --root outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN
```

## Inputs

- R1 acquisition cart closeout: `outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R1-RESULTS/`
- This package: `MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A`
- External raw root: `C:\data\citybrain\raw\keyed_mobility_r2a`

## Smoke run

```powershell
python scripts\harvest_lta_tfl_keyed_sources.py `
  --out outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN `
  --raw-root C:\data\citybrain\raw\keyed_mobility_r2a `
  --smoke
```

## Full run after smoke passes

```powershell
python scripts\harvest_lta_tfl_keyed_sources.py `
  --out outputs\MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN `
  --raw-root C:\data\citybrain\raw\keyed_mobility_r2a `
  --full
```

## Expected source status handling

- LTA REST API AccountKey valid → `PASS_KEY_VALIDATED` or `PASS_SAMPLE_LANDED`.
- LTA SDK key present → `KEY_PRESENT_NOT_USED_FOR_STANDARD_REST` unless an Extended OBU SDK task is explicitly opened.
- TfL primary valid → use primary for run.
- TfL primary invalid and secondary valid → fallback to secondary and mark `PASS_WITH_SECONDARY_KEY`.
- DNS/TLS/network failure → `INFRA_BLOCKED_NOT_AUTH_FAILURE`.
- HTTP 401/403 → `AUTH_FAILED`.
- HTTP 429 → `RATE_LIMITED`.
- Unexpected schema → `SCHEMA_CHANGED_REVIEW_REQUIRED`.

## Required output root

`outputs/MAIN-CITYBRAIN-KEYED-MOBILITY-ACQUISITION-R2A-RUN`

Required files:

- `R2A_MASTER_DECISION.json`
- `SOURCE_STATUS_LEDGER_R2A.csv`
- `HARVEST_REPORT_R2A.json`
- `DOMAIN_FEED_MANIFEST_R2A.json`
- `SAMPLE_ROW_COUNTS_R2A.csv`
- `RAW_EXTERNAL_CHECKSUM_MANIFEST_R2A.json`
- `KNOWN_BLOCKERS_RUNTIME.md`
- `CODEX_CLOSEOUT.md`

## Acceptance criteria

- No credentials in repo/package/logs.
- At least one LTA endpoint validates or fail-closes with a specific reason.
- At least one TfL endpoint validates or fail-closes with a specific reason.
- Raw API payloads remain under external raw root.
- Packaged artifacts contain only manifests, status ledgers, sample counts, and checksums.
- LTA and TfL data are labelled live/current transport context, not official operational command authority.
- No human/person-level records are harvested.
- No dispatch, routing instruction, enforcement, alert, legal, or certified claim.

## Recommended next task if smoke passes

`MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-LTA-TFL-FULL-PULL-AND-DOMAIN-NORMALIZATION`

That task should normalize:

- Singapore bus stops/routes/services
- Singapore traffic incidents, road works, taxi availability, car parks, traffic images metadata only
- London line status, disruptions, road status, stop points, bike points, air quality
- domain feeds for Mobility, Public Safety/Resilience context, Environment context, and Event Fabric replay seeds
