# Codex handover — CityBrain source acquisition cart R1

Date: 2026-07-07

## Task name

`MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R1-SAMPLE-TO-FULL-PULL`

## Objective

Turn the section 6 “other data” source list into actual repo data harvesters. Start with smoke/sample pulls, then full-pull the no-key sources and prepare manual/keyed sources so they are unblocked the moment credentials/exports arrive.

## Current result of this pack

I verified the source access paths through current web documentation and created a source inventory, sample manifests, and executable harvester scaffold.

Direct container downloads could not be executed here because the execution container has no DNS resolution. Treat this package as a ready-to-run Codex handover, not as a completed full harvest. Some metadata samples are captured from web-accessible official pages; large raw files are intentionally not packaged.

## Files to use

- `manifests/source_inventory.csv`
- `manifests/source_inventory.json`
- `samples/*`
- `scripts/harvest_sources.py`

## First Codex command

```bash
cd <repo-or-this-package-root>
python scripts/harvest_sources.py \
  --inventory manifests/source_inventory.csv \
  --out /data/citybrain/raw \
  --smoke
```

Expected behaviour:

- no-key APIs/files either fetch small samples or create large-download plans;
- missing-key sources fail closed with explicit `MISSING_ENV` / `FAIL_CLOSED`;
- manual Dubai exports create import stubs and schema folders;
- report is written to `/data/citybrain/raw/_citybrain_acquisition_cart_r1_report.json`.

## Full-pull order

### P0 immediate

1. `open_meteo_dubai_weather`
2. `osm_geofabrik_gcc_states`
3. `worldpop_are_population`
4. `ms_buildings_planetary_computer`
5. `overture_maps_dubai_aoi`
6. `jrc_global_surface_water_dubai_tile`
7. `opsd_time_series`
8. `dubai_municipality_open_data`
9. `makani_open_data`
10. `dld_real_estate_data`

### P1 credential/manual

1. `openaq_air_quality` with `OPENAQ_API_KEY`
2. `tfl_unified_api` with `TFL_APP_KEY`
3. `lta_datamall` with `LTA_ACCOUNT_KEY`
4. `copernicus_cds_era5` with `CDSAPI_URL` and `CDSAPI_KEY`
5. `geodubai_gis_services` after human access/export

## Required repo rules

- Do not commit raw datasets.
- Do not run `git add .`.
- Write raw files under `/data/citybrain/raw/...`.
- Write normalized smoke outputs under `outputs/data_acquisition_cart_r1/...` or a similar governed artifact folder.
- Preserve source-class labels:
  - `official_open_data`
  - `global_base_layer`
  - `donor_distribution`
  - `manual_export_pending`
  - `api_key_required`
  - `synthetic_fill_candidate`
- For image/media/tiles: external media refs only unless licence explicitly permits packaging.
- For Dubai DLD / DM / GeoDubai / Makani: do not claim completeness until human-supplied official exports are ingested and audited.

## Acceptance criteria

### Smoke gate

- Inventory parses cleanly.
- Every source has one of:
  - downloaded sample,
  - captured metadata/sample schema,
  - key-required template,
  - manual-export stub,
  - large-download plan.
- No credentials are written to disk.
- A report JSON is emitted.
- No raw file larger than 100 MB is copied into the repo.

### Full pull gate

- No-key P0 sources are pulled or deliberately skipped with a clear blocker.
- DLD/DM/Makani/GeoDubai importers are ready even if human export is pending.
- Each source produces:
  - raw landing folder,
  - source manifest,
  - license/attribution note,
  - checksum manifest,
  - normalized sample rows or layer index,
  - source-class label.
- The synthetic factory receives a `domain_feed_manifest.json` mapping source → domain pack → generated/synthetic use.

## Source-specific instructions

### Overture

Use `samples/overture_dubai_duckdb.sql`; update release to latest if needed. Pull only bbox-filtered Dubai AOI.

### OSM / Geofabrik

Download `.poly` for smoke. Full run downloads GCC PBF/GPKG and clips to Dubai AOI. Convert roads to SUMO-ready network later.

### Microsoft Building Footprints

Use Planetary Computer STAC/Delta. Filter by Dubai bbox/quadkeys. Treat as geometry gap fill.

### WorldPop

Start with the tiny UAE 2020 100m file. Then pull 2015–2030 series where needed. Aggregate to communities.

### Open-Meteo

Pull Dubai weather for centroid and later community centroids. Normalize to weather observation records.

### OpenAQ

Requires `OPENAQ_API_KEY`. Try Dubai bbox; if sparse, use donor-city air-quality distributions.

### JRC Global Surface Water

Download only layers needed for Dubai tile first. Clip to AOI before any downstream usage.

### OPSD

Use as energy-curve donor, not local Dubai truth.

### TfL / LTA / CDS

Prepare credentialed smoke. Do not block P0 synthetic city feed.

### DLD / Dubai Municipality / Makani / GeoDubai

Build importers first. Human exports or official access will land later. DLD form fields are captured in `samples/dld_real_estate_schema_manifest.json`.

## Expected deliverable back from Codex

Create a result package named:

`MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R1-RESULTS`

containing:

- `HARVEST_REPORT.json`
- `SOURCE_STATUS_LEDGER.csv`
- `CHECKSUM_MANIFEST.json`
- `DOMAIN_FEED_MANIFEST.json`
- `SAMPLE_ROW_COUNTS.csv`
- `KNOWN_BLOCKERS.md`
- `CODEX_CLOSEOUT.md`

Final status should be one of:

- `PASS_SOURCE_ACQUISITION_CART_R1_WITH_LIMITATIONS`
- `PARTIAL_SOURCE_ACQUISITION_CART_R1_KEYED_AND_MANUAL_BLOCKERS`
- `FAIL_SOURCE_ACQUISITION_CART_R1`
