# MAIN-CITYBRAIN-D8-CITY-FACT-DOM-ASSERTION-SMOKE-R4

## Goal
Launch/smoke the web page and assert city facts render in the DOM.

## Required launch
Use the existing local web launch approach from the Web+Kit live-surface sprint. If live launch is unavailable, perform static DOM smoke against generated/saved HTML and mark accordingly. Do not pass "live" without launch evidence.

## Required assertions
1. A London mobility source record appears in default DOM.
2. A Chicago source-backed similar case appears in default DOM.
3. A Helsinki semantic building/prim mapping appears in default DOM.
4. Data-depth blockers appear for still-missing M13/M07/M08 if not source-backed.
5. Forbidden fixture labels do not appear in default visible content:
   - `Hero Lon Corridor`
   - `Observation 001`
   - `Similar case 001`
   - `option packet`
   - `mobility_access:`
   - `d7_candidate_observation:`
   - `inv_option_`
   - `track-d-`
6. Technical details may include raw refs but must be collapsed by default.

## Outputs
Create `outputs/main_citybrain_d8_city_fact_dom_assertion_smoke_r4` with:
- `CITY_FACT_DOM_ASSERTION_SMOKE_DECISION.json`
- `CITY_FACT_DOM_ASSERTION_REPORT.json`
- `FORBIDDEN_FIXTURE_LABEL_DOM_AUDIT.json`
- `WEB_LAUNCH_EVIDENCE.json` or `STATIC_DOM_SMOKE_EVIDENCE.json`
- screenshot/DOM capture if available.
- audits and hash manifest.

## Status rules
PASS only if actual/source-derived city facts are visible and forbidden fixture labels are absent from default content.
PARTIAL if only static smoke was possible.
FAIL if default UI still shows fixture labels as primary city story.
