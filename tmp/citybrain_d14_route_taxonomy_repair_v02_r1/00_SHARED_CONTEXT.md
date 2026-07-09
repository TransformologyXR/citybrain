# Shared Context — D14 Route Taxonomy Repair v0.2

Current state:
- D14 synthetic corpus v0 assembly/first labeling completed.
- Raw rows: 480.
- Assembled rows: 150.
- Blind double-label sample: 34 rows / 22.67%.
- Independent labels were provided and verified.
- Double-label disagreement: 20/34 = 58.82%.
- Split/Seal R3 was correctly blocked.
- Router preflight was not opened.
- Real operator validation remains unclaimed.

Diagnosis:
The corpus is healthy; the taxonomy is not. The main ambiguity is not dirty data. It is route overlap:
- `entity_360` vs `what_supports`
- `what_supports` vs `what_is_uncertain`
- `cannot_claim` vs `insufficient_source_depth`
- `gap:*` vs refusal
- `ui_help` vs boundary/cannot-claim
- aggregate/list/comparison questions treated as refusal rather than patch-board query gaps

D14 must repair the taxonomy before router training.

Boundary:
- Synthetic rows remain `source_type = synthetic_v0_clean_ai` forever.
- Synthetic corpus can unblock router V0 engineering only with `_REAL_OPERATOR_REVALIDATION_PENDING` status.
- Real operator claim remains blocked until >=2 non-builder sessions produce a sealed real corpus.
