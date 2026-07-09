# MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V03-CONTRACT-R1

Write the v0.3 taxonomy artifacts:

- `ROUTE_TAXONOMY_V03_DECISION_TREE.md`
- `ROUTE_TAXONOMY_V03_CONTRACT.json`

Use the v0.3 contract included in this prompt pack as source. The closed labels are:

- `template:ask:entity_360@v2`
- `template:ask:what_supports@v1`
- `template:ask:what_is_uncertain@v1`
- `template:ask:cannot_claim@v1`
- `ui_help`
- `gap:patch_queue_query_needed`
- `gap:evidence_gap_template_needed`
- `gap:source_record_360_needed`
- `gap:external_context_source_needed`
- `refuse:action_shaped`
- `refuse:prediction_or_finding`
- `refuse:identity_or_person`
- `refuse:out_of_scope_entity`

Important:
- Deprecated v0.2 labels are invalid.
- Existing entity profile route should be v2, not v1.
- Refusal rows must fill `expected_refusal_class`.
- Non-refusal rows must have `expected_refusal_class: null`.
