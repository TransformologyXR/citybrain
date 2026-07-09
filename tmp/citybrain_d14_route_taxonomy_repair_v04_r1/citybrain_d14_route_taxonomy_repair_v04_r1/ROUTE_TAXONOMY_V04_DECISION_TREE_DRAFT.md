# Route Taxonomy v0.4 Decision Tree Draft

## v0.4 design goal

The router needs stable destinations, not a perfect ontology. v0.4 turns the known hard rows into adjudicated anchors and applies an ordered first-match tree to the remaining corpus.

## First-match rules

### 0. External-action imperative vs board-capability question

Use `ui_help` when the question asks whether the **board/screen/software/operator workflow** has a capability or boundary:
- “Can this board alert someone?”
- “Can we call someone from this screen?”
- “If I mark reviewed, does it create a case?”
- “What prevents treating this replay as live monitoring?”
- “Can an operator certify a legal finding based on these local notes?”

Use `refuse:action_shaped` only when the user asks the system/operator to initiate an external outcome:
- “Alert the charger team.”
- “Create a case.”
- “Dispatch someone.”
- “Tell drivers.”
- “Call the police now.”

Capability question = `ui_help`. Imperative external action = `refuse:action_shaped`.

### 1. Queue/patch-board query

Use `gap:patch_queue_query_needed` for any question about queue counts, lists, filters, comparisons, rank, item number relationships, open counts, city/date summaries, “show all,” or “which item is highest ranked.”

Examples:
- “What is the total number of records currently on file for the entire patch?”
- “Is item #3 separate from item #1?”
- “Show all London items.”

### 2. Evidence-source retrieval

Use `template:ask:what_supports@v1` when the question asks for sources/evidence/citations/records that support a selected item, brief, or claim.

Examples:
- “What source supports EV 87 being near the review context?”
- “List the evidence and uncertainty in the EV asset 87 source brief.”
- “Which source records indicate a lack of live service availability details?”

If the wording asks what evidence is **missing** or what would **confirm** a claim, use `gap:evidence_gap_template_needed` instead.

### 3. Missing-evidence/source-depth question

Use `gap:evidence_gap_template_needed` when the question asks what evidence is missing, what source would be needed, why verification is absent, why something remains candidate-only, or what would confirm blocked/affected/access-impact status.

Examples:
- “What evidence is missing before saying EV asset 87 was unavailable?”
- “Is there any missing access-impact evidence that could confirm a blockage?”

### 4. Claimability / live / blocked / proof boundary

Use `template:ask:cannot_claim@v1` for supported negative answers about city/evidence claimability:
- “Is EV 87 blocked/live/available/unavailable/down/working now?”
- “What does this source record prove/establish/verify?”
- “Can this be treated as affected/certified/unavailable?”
- “Can the asset row prove it existed but not operational status?”
- “What does this not prove?”
- “Is the EV asset row static registry rather than live status?”

This is not a refusal. It is a supported negative answer.

### 5. Named source-record profile

Use `gap:source_record_360_needed` only when the question asks for the fields/details/contents of a named source record itself.

Examples:
- “What does TIMS-219173 say?”
- “Show the fields in charging-site record 87.”
- “What exactly is in the London Datastore row?”

Do not use this for prove/establish/verify wording. Those go to `cannot_claim`.

### 6. Entity profile

Use `template:ask:entity_360@v2` only for neutral profile/facts/attributes of a named visible entity or selected entity, without evidence/proof/live/blockage/missing-evidence wording.

Examples:
- “What do we know about EV asset 87?”
- “Show the profile for UPRN 5006082.”

### 7. General uncertainty

Use `template:ask:what_is_uncertain@v1` only for broad uncertainty/unknowns questions that do not ask missing evidence, source support, claimability, queue counts, or board capability.

Example:
- “What is uncertain here?”

### 8. External context / unrelated source

Use `gap:external_context_source_needed` for external data not on the board that is reasonable context but not currently connected.

Examples:
- “What was the weather at Wood Lane?”
- “Are there other charging sites nearby not shown here?”

### 9. Refusals

Use `refuse:prediction_or_finding` for legal/certified/official findings, predictions, compliance determinations, or outcome judgments not framed as a supported “what can/cannot be claimed” question.

Use `refuse:identity_or_person` for person/contact/owner/department identity requests not present in records.

Use `refuse:out_of_scope_entity` for entities/places/domains unrelated to the board.

## `requires_selected_item_context` rule

Set `requires_selected_item_context = true` only when the question cannot be interpreted without the current selected item, such as:
- pronouns/ellipsis: “what about this?”, “run the check”, “what does it prove?”, “what is missing here?”
- action/help requests tied to the currently selected item: “mark this reviewed”, “generate the brief for this.”

Set it to `false` when the row names a visible entity/item/record/city/board capability explicitly, even if selected context would help.

## Closed labels

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

No other labels are allowed.
