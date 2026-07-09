# MAIN-CITYBRAIN-D8-ACTUAL-RECORD-UI-GROUNDING-PREFLIGHT

## Objective

Open the current D8 Web+Kit live surface baseline and assert that the next work is a **data-grounded UI remediation**, not a generic human-readable rewrite.

## Required inputs

Find and record:

- latest D8 Web+Kit live surface milestone freeze root
- `apps/web-control-room`
- `packages/fixtures/mobility_access/runtime_bundle`
- current generated/served HTML evidence if available
- one-truth index / runtime bundle authority files
- D8 scoreboard / moment list

## Preflight checks

Write `ACTUAL_RECORD_UI_GROUNDING_PREFLIGHT_DECISION.json` with:

- `current_surface_status`
- `current_problem_statement`
- `runtime_bundle_root`
- `web_source_root`
- `one_truth_authority_ref`
- `no_new_substrate_authorized: true`
- `no_fact_invention_authorized: true`
- `technical_ids_allowed_only_in_details: true`
- `raw_counts_are_not_demo_content: true`

## Required finding

The preflight must explicitly detect whether the UI currently renders generic labels/counts instead of actual records. If it does, record:

```json
{
  "ui_problem": "generic_system_narration_not_actual_city_records",
  "remediation_required": true
}
```

## Audits

Produce:

- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

