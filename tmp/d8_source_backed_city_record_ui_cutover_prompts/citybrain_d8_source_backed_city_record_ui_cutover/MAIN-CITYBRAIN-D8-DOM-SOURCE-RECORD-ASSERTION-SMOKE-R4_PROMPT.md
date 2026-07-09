# MAIN-CITYBRAIN-D8-DOM-SOURCE-RECORD-ASSERTION-SMOKE-R4

Launch the web surface and assert rendered DOM contains actual source-record fields.

Required assertions:
- At least one visible default card contains source_system or dataset_name.
- At least one visible default card contains city and external/source id if available.
- No default visible card title is only `Hero...`, `Observation 001`, `Similar case 001`, `inv_option_*`, `d7_candidate_observation:*`, or an enum label, except inside DATA DEPTH BLOCKER or closed technical details.
- DATA DEPTH BLOCKER cards explicitly list missing fields.

Required files:
- WEB_SOURCE_RECORD_DOM_ASSERTION_REPORT.json
- WEB_SOURCE_RECORD_DOM_CAPTURE.html
- WEB_SOURCE_RECORD_SCREENSHOT_OR_TEXT_CAPTURE.txt

Status rules:
- PASS only if source records render.
- PARTIAL_SOURCE_RECORD_DEPTH_INSUFFICIENT if no eligible source records exist and blockers render honestly.
- FAIL if generic/fixture labels are presented as city facts.
