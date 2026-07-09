# MAIN-CITYBRAIN-D8-BRAIN-SURFACE-STORY-QUEUE-PREFLIGHT

Verify prerequisites and freeze points before touching UI.

Inputs to locate:
- London Wood Lane scenario layer and source bundle.
- NYC cascade scenario layer and freeze.
- Scenario Authoring R1 distinct queue result.
- Deep Story Inventory role portfolio result.
- Current web control room source under `apps/web-control-room`.
- Current runtime/source fixtures under `packages/fixtures`.

Assertions:
- Wood Lane story exists and is green.
- NYC cascade story exists and is green or clearly unavailable.
- Distinct story-query count >= 2 if NYC is available.
- Current UI is allowed to change only as maintained app source; certified outputs are read-only.
- No new city data landing or source fabrication is allowed.

Produce:
- `BRAIN_SURFACE_PREFLIGHT_DECISION.json`
- `BRAIN_SURFACE_INPUT_INDEX.json`
- `SOURCE_SCENARIO_FREEZE_STATUS.json`
- `NO_MUTATION_PLAN.json`
