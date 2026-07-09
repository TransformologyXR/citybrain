# CityBrain source acquisition cart R1

This pack turns the section 6 “other data” acquisition list into a sample-ready and Codex-ready acquisition handover.

## What is included

- Source inventory: `manifests/source_inventory.csv`
- JSON source inventory: `manifests/source_inventory.json`
- Sample manifests/templates: `samples/*`
- Harvester scaffold: `scripts/harvest_sources.py`
- Codex handover: `codex/CODEX_HANDOVER.md`

## Important network note

The container available here could not resolve external hosts directly, so full raw download execution was not possible in this session. I used current web verification for the official source paths and created the runnable package for Codex to execute in the networked repo/dev environment.

## P0 sources covered

- Overture Maps
- OpenStreetMap / Geofabrik
- Microsoft Global ML Building Footprints
- WorldPop
- Open-Meteo
- OpenAQ
- JRC Global Surface Water
- Open Power System Data
- Dubai DLD
- Dubai Municipality / Dubai Pulse
- Makani
- GeoDubai

## P1 credentialed sources covered

- TfL Unified API
- Singapore LTA DataMall
- Copernicus CDS ERA5
