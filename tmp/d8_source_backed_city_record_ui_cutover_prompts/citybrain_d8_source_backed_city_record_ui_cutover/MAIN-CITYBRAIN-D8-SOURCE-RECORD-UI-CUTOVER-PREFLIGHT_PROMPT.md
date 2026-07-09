# MAIN-CITYBRAIN-D8-SOURCE-RECORD-UI-CUTOVER-PREFLIGHT

Inspect current Web UI and runtime bundle. Confirm the failure mode: live page renders CityBrain fixture labels/counts rather than official/source-derived city records.

Inputs:
- apps/web-control-room/
- packages/fixtures/mobility_access/runtime_bundle/
- latest D8 actual-record-grounded UI outputs if present

Output:
- SOURCE_RECORD_UI_CUTOVER_PREFLIGHT_DECISION.json
- CURRENT_UI_SOURCE_RECORD_FAILURE_REPORT.md
- DEFAULT_UI_CARD_CLASSIFICATION.json

Hard gates:
- Must identify whether default UI contains fixture-only cards such as `Hero Lon Corridor`, `Observation 001`, `Similar case 001`, `inv_option_*`, or similar.
- Must not call the surface viewer-ready unless default cards display source-derived city record content.
