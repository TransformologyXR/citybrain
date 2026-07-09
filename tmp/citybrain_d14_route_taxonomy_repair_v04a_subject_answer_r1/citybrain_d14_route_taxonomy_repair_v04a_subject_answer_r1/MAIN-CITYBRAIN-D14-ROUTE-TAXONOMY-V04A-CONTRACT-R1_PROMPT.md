# MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04A-CONTRACT-R1

Create the closed v0.4A taxonomy contract and decision tree.

Outputs:
- `ROUTE_TAXONOMY_V04A_CONTRACT.json`
- `ROUTE_TAXONOMY_V04A_DECISION_TREE.md`

Closed route labels:

## Templates

- `template:ask:subject_answer@v1:lens=support`
- `template:ask:subject_answer@v1:lens=uncertainty`
- `template:ask:subject_answer@v1:lens=claimability`
- `template:ask:subject_answer@v1:lens=summary`
- `template:ask:entity_360@v2`

## UI help

- `ui_help`

## Refusals

- `refuse:action_shaped`
- `refuse:prediction_or_finding`
- `refuse:identity_or_person`
- `refuse:out_of_scope_entity`

## Gaps

Use only these gap labels unless the root-cause analysis proves a missing category:

- `gap:patch_queue_query_needed`
- `gap:source_record_360_needed`
- `gap:evidence_gap_template_needed`
- `gap:external_context_source_needed`

Decision tree must use first-match order:

1. If imperative/request asks the system to do an external action — alert, dispatch, route, enforce, approve, create/send official case, contact someone, publish, fix — route `refuse:action_shaped`.
2. If question asks for prediction, official/legal/certified finding, causality conclusion, or certainty the data does not provide — route `refuse:prediction_or_finding`, unless it is asking whether the board can claim something; those route to subject_answer claimability.
3. If question asks to identify a person, owner, driver, personal identity, or biometric/identity inference — route `refuse:identity_or_person`.
4. If question asks about board usage/capability — how to export, mark reviewed, add note, whether notes/clicks create case, whether board can alert/dispatch, where activity is saved — route `ui_help`.
5. If question asks count/list/filter/compare/summarize queue items across the patch — route `gap:patch_queue_query_needed`.
6. If question asks for fields/details/contents of a specific source record — route `gap:source_record_360_needed`.
7. If question asks about a specific entity/address/asset/case profile — route `template:ask:entity_360@v2`.
8. If question asks what supports/evidences/backs a subject — route `template:ask:subject_answer@v1:lens=support`.
9. If question asks what is missing/uncertain/not known/what evidence is lacking — route `template:ask:subject_answer@v1:lens=uncertainty`, unless it is asking for a missing external data type not present as a deterministic consumer; then route `gap:evidence_gap_template_needed`.
10. If question asks can we claim/prove/establish/verify/certify/live/blocked/available/affected/caused — route `template:ask:subject_answer@v1:lens=claimability` when the board has enough local subject context to answer with limits. Refuse only if it asks for an official/legal finding.
11. If question asks “what is going on,” “what do we know,” or general summary of selected subject — route `template:ask:subject_answer@v1:lens=summary`.
12. If question requires outside context such as weather/ownership/traffic/live service source not in the board — route `gap:external_context_source_needed`, unless framed as an action/finding.

`requires_selected_item_context`:

- true only if the question cannot be interpreted without selected item/pronoun context.
- false if it names Wood Lane, EV asset 87, NYC MVC, a source record, a board capability, or a city/queue scope.

Also define deprecated labels that must have 0 hits after v0.4A relabel:

- `template:ask:what_supports@v1`
- `template:ask:what_is_uncertain@v1`
- `template:ask:cannot_claim@v1`
- `gap:boundary_status_template_needed`
- `gap:patch_queue_open_count`
- `gap:patch_queue_aggregate_counts`
- `gap:patch_queue_filter_by_city`
- `gap:patch_queue_filtering_and_summary_by_city_date`
- `gap:patch_queue_update_date_comparison`
- other v0.2/v0.3 split labels collapsed into v0.4A categories
