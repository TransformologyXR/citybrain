# MAIN-CITYBRAIN-D14-CANONICAL-BOUNDARY-ANCHORS-V04B-R1

Create `D14_V04B_CANONICAL_BOUNDARY_ANCHORS.json`.

Hard-code the canonical v0.4B adjudication for the 13 v0.4A non-lens family disagreements. These are not hidden labels for router training; they are explicit taxonomy examples that must appear in the v0.4B contract and labeler instructions.

Canonical anchors:

1. `syn-v0-0020`
Raw: `Can an operator certify a legal finding based on these local notes?`
Canonical: `ui_help`
Reason: capability/boundary question about local notes and legal finding; not a command to certify.
requires_selected_item_context: false

2. `syn-v0-0029`
Raw: `Does the asset 87 record include connector counts or power ratings?`
Canonical: `gap:source_record_360_needed`
Reason: asks for fields/details of a source row.
requires_selected_item_context: false

3. `syn-v0-0035`
Raw: `charger status??`
Canonical: `template:ask:subject_answer@v1:lens=claimability`
Reason: messy selected-EV status question; supported negative answer about no live availability.
requires_selected_item_context: true

4. `syn-v0-0037`
Raw: `List the evidence and uncertainty in the EV asset 87 source brief.`
Canonical: `template:ask:subject_answer@v1:lens=support`
Reason: asks for evidence/uncertainty in a named brief, not patch-board query.
requires_selected_item_context: false

5. `syn-v0-0041`
Raw: `What specific TfL TIMS records are currently linked to the Wood Lane item?`
Canonical: `template:ask:subject_answer@v1:lens=support`
Reason: asks which supporting records are linked to a selected city item.
requires_selected_item_context: false

6. `syn-v0-0050`
Raw: `Can this board alert someone if there is a problem?`
Canonical: `ui_help`
Reason: board capability question; not an instruction to alert.
requires_selected_item_context: false

7. `syn-v0-0060`
Raw: `Does any part of this patch certify a legal or official finding?`
Canonical: `ui_help`
Reason: board/patch boundary question; not a request to certify.
requires_selected_item_context: false

8. `syn-v0-0062`
Raw: `Can I tell others this is urgent?`
Canonical: `ui_help`
Reason: sharing/urgency-boundary guidance; not an external command. It should explain ranking is review order, not urgency.
requires_selected_item_context: false

9. `syn-v0-0070`
Raw: `Is there weather data available for this patch area?`
Canonical: `gap:external_context_source_needed`
Reason: asks for weather/external context not in the local cockpit.
requires_selected_item_context: false

10. `syn-v0-0071`
Raw: `is it rapid charging?`
Canonical: `template:ask:entity_360@v2`
Reason: selected EV entity attribute/profile question.
requires_selected_item_context: true

11. `syn-v0-0076`
Raw: `Is the ranking an urgency finding or just review order?`
Canonical: `ui_help`
Reason: board semantics and ranking boundary.
requires_selected_item_context: false

12. `syn-v0-0128`
Raw: `Why is there no live availability source in this bundle at all?`
Canonical: `gap:external_context_source_needed`
Reason: asks why external/live source coverage is absent, not merely whether current subject is blocked.
requires_selected_item_context: false

13. `syn-v0-0142`
Raw: `Can we call the police department directly from this screen?`
Canonical: `ui_help`
Reason: board capability question; not an instruction to call.
requires_selected_item_context: false

Output:
- JSON array with fields: row_id, raw_question, canonical_route_label, canonical_refusal_class, requires_selected_item_context, canonical_reason.
- Include a markdown summary `D14_V04B_CANONICAL_BOUNDARY_ANCHORS.md`.
