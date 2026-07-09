# MAIN-CITYBRAIN-D8-NYC-CASCADE-SCENARIO-LAYER-PREFLIGHT

Create a preflight output root:
`outputs/main_citybrain_d8_nyc_cascade_scenario_layer_preflight`

Verify:
1. D8 deep story inventory freeze exists and is green.
2. D8 scenario authoring R1 exists and is green.
3. It lists `story-query:incident_to_affected_asset_response_cascade@v1` as a distinct story-query.
4. NYC cascade candidate is not already concrete; current status should be `authoring_plan_only` or equivalent.
5. Existing NYC Flow 3 / affected-asset / hero package outputs are discoverable.
6. No UI/capture/viewer work is in scope.

Produce:
- `NYC_CASCADE_PREFLIGHT_DECISION.json`
- `INPUT_ARTIFACT_INDEX.json`
- `CANDIDATE_QUERY_LOCK.json`
- `NO_MUTATION_AUDIT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`

Fail/partial if the required prior handoffs are missing. Do not invent them.
