# Route Taxonomy v0.3 Decision Tree

## v0.3 design goal

The router v0 needs stable destinations, not a perfect ontology. Use the first matching rule below. Do not use deprecated v0.2 labels.

## Closed route labels

### Existing deterministic template routes

1. `template:ask:entity_360@v2`
   - Use when the question asks for profile/facts/attributes of a named visible entity, address, UPRN, source-linked entity, or selected entity.
   - Use for entity-specific fields visible in the entity answer, such as confidence value or planning-context linkage.
   - Do not use for "what evidence supports this claim" or "is it blocked/live/unavailable?"

2. `template:ask:what_supports@v1`
   - Use when the question asks for evidence, citations, source records, support, records on file, or what backs a selected item/brief/claim.
   - If a question asks for "evidence and uncertainty" together, choose `what_supports` because evidence/source retrieval is primary.
   - Use for "what source supports EV 87 being near the review context?"

3. `template:ask:what_is_uncertain@v1`
   - Use for broad uncertainty/unknowns questions about the selected item when the user does not ask claimability, live status, missing evidence, or source support.
   - Example: "what is uncertain here?"

4. `template:ask:cannot_claim@v1`
   - Use for selected-item/entity claimability questions:
     - "can we claim..."
     - "does this prove..."
     - "is EV 87 blocked/live/available/unavailable?"
     - "can this be treated as affected/certified/unavailable?"
     - "what does this not prove?"
   - This is a supported negative answer, not a refusal.
   - Also use for "is the EV row live status or static registry?" unless the user asks for a specific field from the source row.

### Static/help routes

5. `ui_help`
   - Use for how-to and board-capability questions answerable from the visible UI/boundary:
     - how to export, run check, mark reviewed, add note
     - whether local notes create an official case
     - whether the board dispatches/routes/alerts/creates cases as a capability
     - whether the board is local review only
   - Do not use `ui_help` when the user asks the system to actually perform an external action; use `refuse:action_shaped`.

### Product gap routes

6. `gap:patch_queue_query_needed`
   - Use for any patch-board queue count, list, filter, comparison, ranking, open-count, city/date summary, "show all", "which item is highest ranked", or "compare queue items" request.
   - This collapses v0.2 `patch_queue_open_count`, `patch_queue_aggregate_counts`, `patch_queue_filter_by_city`, `patch_queue_filtering_and_summary_by_city_date`, and `patch_queue_update_date_comparison`.

7. `gap:evidence_gap_template_needed`
   - Use when the user asks what evidence is missing, what source would be needed, why the item remains candidate-only, why verification is absent, or what would confirm a blocked/affected/access-impact claim.
   - Do not use for the simple claim "is it blocked/live/unavailable?" Use `cannot_claim`.
   - Do not use for "what source supports..." Use `what_supports`.

8. `gap:source_record_360_needed`
   - Use only when the question asks what a named source record itself says, contains, or lists, or asks for a field-level source-record profile.
   - Examples: "what does TIMS-219173 say?", "show me record 87 details".
   - Do not use for source support/citation questions; use `what_supports`.

9. `gap:external_context_source_needed`
   - Use for questions about external data or broader sources not connected to the current cockpit, such as weather data, other charging sites outside the visible item, or external data sources not on the board.

### Refusals

10. `refuse:action_shaped`
    - Use when the user asks the system or operator to initiate an external/action-shaped outcome:
      - alert someone
      - dispatch
      - route
      - enforce
      - approve
      - create a case
      - email/send externally
      - tell drivers/public
      - get something fixed
    - If the user asks whether the board has this capability, use `ui_help`.

11. `refuse:prediction_or_finding`
    - Use when the user asks for a future prediction, legal/certified finding, official determination, or outcome judgment not framed as a supported "what can/cannot be claimed" question.

12. `refuse:identity_or_person`
    - Use for "who" / "which person or department" / "who do I call" / ownership/contact questions not present in visible records.

13. `refuse:out_of_scope_entity`
    - Use for entities/places/domains unrelated to the current local board and not visible in the supplied records.

## Deprecated v0.2 labels

Do not use:
- `gap:boundary_status_template_needed`
- `gap:charging_site_source_depth_scan`
- `gap:external_sharing_guidance`
- `gap:human_review_timestamp_status`
- `gap:local_note_visibility_guidance`
- `gap:patch_queue_aggregate_counts`
- `gap:patch_queue_filter_by_city`
- `gap:patch_queue_filtering_and_summary_by_city_date`
- `gap:patch_queue_open_count`
- `gap:patch_queue_update_date_comparison`
- `gap:planning_context_boundary_template_needed`

Map them to v0.3 labels according to the decision tree above.
