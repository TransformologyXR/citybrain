# MAIN-CITYBRAIN-D8-WEB-SOURCE-RECORD-CARDS-R2

## Goal
Patch `apps/web-control-room` so the default page renders actual city/source-derived records from the integrated bundle.

## Required UI behavior
Default visible page must show:
1. Real/source-derived London mobility cards for situation/access context.
2. Real/source-backed Chicago similar-case cards for M02.
3. Real/source-backed Helsinki semantic building/prim cards for M10 / visual entity pick.
4. Honest blocker cards for M13/M07/M08 if still missing source records.
5. Collapsed technical details containing raw CityBrain IDs and runtime labels.

## Default UI must not show these as primary content
- `Hero Lon Corridor`
- `Hero Main Eastbound`
- `Hero Blocked Lane`
- `Observation 001`
- `Similar case 001`
- `option packet 1`
- `Execution: Not Executed` as the main city fact
- `Track D`, `D7`, `M02`, `M13`, `CityBrain connected`, `runtime bundle`, `trace stage` as default section labels.

These may appear inside technical details or small provenance notes only.

## Required copy style
Use concrete record fields first. Examples:
- Road/disruption/source/date/place/value.
- Chicago case source/city/address/category/match reason/outcome/limitation.
- Helsinki building ID/GMLID/RATU/VTJ_PRT/usage/height/year/prim path.
- Only then explain review boundary.

If a source card lacks a human field, show a data-depth blocker, not generic prose.

## Required DOM assertions
Create selectors/assertions that prove actual source facts render:
- at least one London source dataset/name/value.
- at least one Chicago case city/category/summary/match reason.
- at least one Helsinki building identifier and prim path.
- zero forbidden fixture labels in default visible panels.

## Outputs
Create `outputs/main_citybrain_d8_web_source_record_cards_r2` with:
- `WEB_SOURCE_RECORD_CARDS_DECISION.json`
- `WEB_SOURCE_RECORD_RENDERING_PATCH_REPORT.json`
- `DEFAULT_UI_FORBIDDEN_LABEL_AUDIT.json`
- `WEB_SOURCE_RECORD_DOM_ASSERTION_PLAN.json`
- audits and hashes.

## Status rules
PASS only if the default UI renders source records from the integrated bundle and quarantines fixture-only labels.
PARTIAL if the web app renders blocker cards because source fields are still insufficient.
FAIL if default UI still presents fixture labels as city facts.
