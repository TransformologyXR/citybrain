# Non-goals and boundaries

This package scouts. It does not build models or promote data into training fuel.

## Non-goals

- No ranker.
- No forecast model.
- No learned predictor.
- No counterfactual learner.
- No case-memory learner.
- No dynamic investigation.
- No cross-city learned transfer.
- No production surface.
- No operator-facing learned output.
- No materialized training set unless a governed materialization artifact already exists.
- No official action, dispatch, enforcement, legal, or certified claim.

## Source-class rule

All scout candidates must keep source class explicit. Examples:
- official_record
- source_record
- derived_field
- sensor_inferred
- model_generated_narrative_not_fact_source
- synthetic
- replay
- candidate_inventory_only

## Promotion rule

Scout candidates are `candidate_inventory_only` until a future package materializes them under:
- schema
- source refs
- lineage
- no-fabrication audit
- censoring or observation-window policy if temporal
- hash manifest
- tests
- arming/authority decision if needed
