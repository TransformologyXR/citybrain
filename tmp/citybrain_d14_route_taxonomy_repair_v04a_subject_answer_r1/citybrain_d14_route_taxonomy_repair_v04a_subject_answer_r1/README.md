# D14 Route Taxonomy Repair v0.4A — Subject-Answer Consolidation

Run from `ENTRY_PROMPT.md`.

This pack does not train a router. It repairs the route taxonomy and answer architecture before sealing a synthetic corpus.

Expected stop status:

`PAUSED_D14_ROUTE_TAXONOMY_V04A_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Possible later pass status after independent labels and gates:

`PASS_D14_ROUTE_TAXONOMY_V04A_STABLE_READY_FOR_SPLIT_SEAL_WITH_REAL_OPERATOR_REVALIDATION_PENDING`

Not allowed:

- `PASS_D14_OPEN_ASK_REAL_OPERATOR_VALIDATED`
- any router implementation using unsealed corpus
- any claim that synthetic corpus equals real operator validation

Core idea:

`what_supports`, `what_is_uncertain`, and `cannot_claim` become lenses of a single `subject_answer` route. The router chooses subject + lens; deterministic answer assembly produces the full answer object.
