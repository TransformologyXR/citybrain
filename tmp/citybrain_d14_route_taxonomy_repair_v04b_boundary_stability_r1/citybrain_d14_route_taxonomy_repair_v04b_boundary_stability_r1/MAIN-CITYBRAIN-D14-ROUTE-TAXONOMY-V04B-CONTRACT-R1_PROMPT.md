# MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04B-CONTRACT-R1

Create `ROUTE_TAXONOMY_V04B_CONTRACT.json` and `ROUTE_TAXONOMY_V04B_DECISION_TREE.md`.

v0.4B preserves the v0.4A subject-answer architecture. Closed route labels are:

- `template:ask:subject_answer@v1:lens=support`
- `template:ask:subject_answer@v1:lens=uncertainty`
- `template:ask:subject_answer@v1:lens=claimability`
- `template:ask:subject_answer@v1:lens=summary`
- `template:ask:entity_360@v2`
- `ui_help`
- `gap:patch_queue_query_needed`
- `gap:source_record_360_needed`
- `gap:external_context_source_needed`
- `refuse:action_shaped`
- `refuse:prediction_or_finding`
- `refuse:identity_or_person`

## v0.4B first-match rules

Apply these in order.

### Rule 1 — Identity/person questions
If a question asks to identify a person, infer identity, find who someone is, use biometric/identity inference, or determine a person’s identity, label:
`refuse:identity_or_person`.

### Rule 2 — Imperative external action
If a question commands or asks the system to perform an external action, label:
`refuse:action_shaped`.

Examples:
- “Alert the charger team.”
- “Create a case.”
- “Call the police.”
- “Dispatch someone.”
- “Route traffic.”
- “Tell drivers now.”
- “Approve this.”
- “Send this to the operator.”

Do not use this label merely because the question mentions an action word. Capability questions go to Rule 3.

### Rule 3 — Board capability, workflow, and boundary help
If the question asks whether the board/cockpit/screen/operator can do something, how to use a board feature, whether notes/export create an official case, whether ranking means urgency, whether the screen can call/alert/dispatch, or whether local notes can certify anything, label:
`ui_help`.

Examples:
- “Can this board alert someone if there is a problem?”
- “Can we call the police department directly from this screen?”
- “Does any part of this patch certify a legal or official finding?”
- “Can an operator certify a legal finding based on these local notes?”
- “Is the ranking an urgency finding or just review order?”
- “How do I export this?”

### Rule 4 — Requested official/legal finding about the world
If the user asks the system to determine, certify, predict, or legally find something about the world or the situation, label:
`refuse:prediction_or_finding`.

Examples:
- “Is this legally non-compliant?”
- “Will this cause disruption tomorrow?”
- “Certify that this is blocked.”
- “Make an official finding.”

Capability questions about whether the board can certify remain `ui_help` under Rule 3.

### Rule 5 — Patch-board query gap
If the question asks to list, count, compare, filter, summarize, rank, sort, show open items, show all London/NYC items, show items updated today/yesterday, or compare queue items, label:
`gap:patch_queue_query_needed`.

Examples:
- “Show all items updated yesterday and today.”
- “Which city has more review items?”
- “List the three queue items.”
- “How many open items are there?”

### Rule 6 — Source-row profile gap
If the question asks for the contents, fields, columns, connector counts, power ratings, raw values, or detailed profile of one named source record or row, label:
`gap:source_record_360_needed`.

Examples:
- “Does the asset 87 record include connector counts or power ratings?”
- “What fields are in TIMS-219173?”
- “Show me the London Datastore row for asset 87.”

If the question asks what the record proves/supports/establishes, use subject_answer claimability/support, not source_record_360.

### Rule 7 — External context/source gap
If the question asks for weather, live service-status feeds, external contacts, real-time data, why a source is absent, or where to get unavailable outside context, label:
`gap:external_context_source_needed`.

Examples:
- “Is there weather data available for this patch area?”
- “Why is there no live availability source in this bundle at all?”
- “Where do we get the live charger status?”

If the question asks whether EV 87 is blocked/live/working now, use subject_answer claimability under Rule 9.

### Rule 8 — Entity profile
If the question asks for basic facts about a named entity/asset/place/UPRN/item and the entity itself is the subject, label:
`template:ask:entity_360@v2`.

Examples:
- “Is it rapid charging?” (selected context = EV asset 87)
- “What do we know about UPRN 5006082?”
- “What is EV asset 87?”

### Rule 9 — Subject answer
All remaining supported questions about a selected subject/item/packet/brief route to:
`template:ask:subject_answer@v1` with a lens.

Lens rules:
- `support`: evidence, source support, backing records, why it matters, linked records.
- `uncertainty`: what is missing, unclear, unknown, stale, absent from local records.
- `claimability`: can/cannot claim, prove, establish, verify, legal/official/certified wording, blocked/live/available status for EV asset 87.
- `summary`: what is going on, explain this item, brief overview.

Supported negative answers are not refusals.

## Context dependency flag
`requires_selected_item_context = true` only if the raw question cannot be interpreted without the selected item or prior context.

True examples:
- “what about this?”
- “is it rapid charging?”
- “charger status??”
- “is it working right now?”

False examples:
- question names Wood Lane, NYC MVC, EV asset 87, TIMS-219173, the patch board, ranking, notes, export, police, legal finding, weather, or all/open items.

Output must include examples and non-examples for each rule.
