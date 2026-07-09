# D14 Route Taxonomy Repair v0.4 R1

Run `ENTRY_PROMPT.md` in Codex.

Expected status:
`PAUSED_D14_ROUTE_TAXONOMY_V04_AWAITING_INDEPENDENT_DOUBLE_LABELS`

This package exists because v0.3 reduced disagreement from 55.56% to 35%, but still failed the 15% gate. v0.4 does not add nuance. It removes ambiguity.

Core changes:
1. Treat the 21 v0.3 disagreement rows as an adjudicated anchor set.
2. Exclude anchors from the next disagreement denominator.
3. Tighten first-match routing rules.
4. Define `requires_selected_item_context` deterministically.
5. Relabel all 150 rows under v0.4.
6. Export a fresh blind sample from non-anchor rows.
