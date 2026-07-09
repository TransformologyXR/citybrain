# MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V02-CONTRACT-R1

Create a revised route taxonomy contract `ROUTE_TAXONOMY_V02_CONTRACT.json` and human-readable `ROUTE_TAXONOMY_V02_DECISION_TREE.md`.

The decision tree must resolve the observed ambiguity.

## Core rules

### Rule 1 — refusal is not the same as a supported negative answer
If a question is about a visible/current entity, selected item, source row, queue item, or board capability, and the system has enough retained evidence to say “not supported,” “not in local records,” or “cannot claim,” it must route to a template or precise gap, not `refuse:insufficient_source_depth`.

Use `refuse:*` only when the question itself is outside the allowed product boundary or unsupported domain, not when the answer is “we do not have that evidence.”

Examples:
- “EV 87 blocked?” → cannot-claim / evidence-gap answer, not refusal.
- “Do we have live service-status source for EV asset 87?” → evidence-gap/uncertainty answer, not refusal.
- “Is the charger definitely available now?” → cannot-claim answer, not refusal.

### Rule 2 — action command vs capability/boundary question
Distinguish imperatives from questions about capability.

- “Publish an alert now” / “Create a case” / “Dispatch someone” → `refuse:action_shaped`.
- “Can this board publish an alert?” / “Did it publish alerts today?” → boundary/cannot-claim/help answer or precise gap, not action refusal unless it asks to execute.

### Rule 3 — source row questions get source-record treatment
Questions asking what a named source row says, proves, does not say, or supports should route to a source-record evidence template or to a specific template gap.

Recommended new deterministic template candidate:
- `template:ask:source_record_360@v1`

If not implemented yet, label as:
- `gap:source_record_360_needed`

### Rule 4 — missing evidence is a product answer
Questions asking what evidence is missing, whether a live source exists, or why a claim is unsupported should route to missing-evidence/uncertainty handling, not refusal.

Recommended new deterministic template candidate:
- `template:ask:evidence_gap@v1`

If not implemented yet, label as:
- `gap:evidence_gap_template_needed`

### Rule 5 — patch-board list/count/filter/comparison questions are query gaps, not refusals
Questions such as “show all London items,” “how many review items are open,” and “updated today vs yesterday” are reasonable patch-board requests. If no template exists, label a precise gap, not `refuse:unsupported_aggregate_or_comparison`.

Recommended deterministic template candidate:
- `template:ask:patch_queue_summary@v1`

If not implemented yet, label specific gaps such as:
- `gap:patch_queue_filter_by_city`
- `gap:patch_queue_open_count`
- `gap:patch_queue_update_date_comparison`

### Rule 6 — board usage/boundary questions are ui_help or boundary-status templates
“How do I export this?” is `ui_help`.
“Who can see notes?” may be `ui_help` if covered; otherwise `gap:local_note_visibility_guidance`.
“Is this safe to share externally?” is `gap:external_sharing_guidance` unless explicit policy text exists.

Recommended deterministic template candidate:
- `template:ask:boundary_status@v1`

### Rule 7 — entity_360 is for entity facts, not every named-entity question
Use `template:ask:entity_360@v2` for questions asking attributes/facts/profile of an entity/asset/case.
Do not use it for “what does the source row prove?” or “what evidence is missing?” just because an entity ID appears.

### Rule 8 — requires_selected_item_context
Set `requires_selected_item_context = true` only when the raw question cannot identify its target without the currently selected item/session context.
Named entities like `EV asset 87`, `Wood Lane`, `NYC MVC 4463710`, and `London Datastore` generally do not require selected item context.
Pronouns/ellipsis like “this,” “it,” “here,” “that one,” “the charger” require context only if the target is otherwise ambiguous.
UI-help questions generally do not require selected item context unless they are about a selected packet/brief/export.

## Deliverables
- Closed route labels v0.2.
- Precise gap label vocabulary.
- Examples for each route.
- A “do not use” section for ambiguous old behavior.
- Version ID: `citybrain.d14.route_taxonomy_v0_2`.
