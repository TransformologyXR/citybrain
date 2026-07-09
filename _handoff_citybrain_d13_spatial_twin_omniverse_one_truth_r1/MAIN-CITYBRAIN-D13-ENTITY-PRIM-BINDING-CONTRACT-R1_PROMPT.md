# MAIN-CITYBRAIN-D13-ENTITY-PRIM-BINDING-CONTRACT-R1

Define a binding between spatial objects/prims and CityBrain source entities.

Fields:
- `prim_path`
- `entity_id`
- `entity_label`
- `source_record_ids`
- `binding_method`
- `confidence_or_limit`
- `geometry_certification_status` (must default non-certified unless proven)
- `review_state_ref`

Requirements:
- Binding must cite source records or prior accepted binding artifact.
- No object picking may imply legal/certified identity.
- Unbound objects must show `No CityBrain source entity linked`.

Deliverables:
- `ENTITY_PRIM_BINDING_CONTRACT.json`
- `ENTITY_PRIM_BINDING_SAMPLE.json`
- `UNBOUND_OBJECT_BEHAVIOR.md`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
