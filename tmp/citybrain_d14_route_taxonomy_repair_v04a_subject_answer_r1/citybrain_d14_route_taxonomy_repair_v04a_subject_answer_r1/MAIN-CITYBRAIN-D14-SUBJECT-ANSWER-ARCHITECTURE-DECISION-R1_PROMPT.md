# MAIN-CITYBRAIN-D14-SUBJECT-ANSWER-ARCHITECTURE-DECISION-R1

Create a product-architecture decision for consolidated subject answering.

Output: `SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.json` plus a short markdown summary.

Required decision:

Introduce:

`template:ask:subject_answer@v1(subject, lens)`

Allowed lenses:

- `support`
- `uncertainty`
- `claimability`
- `summary`

Route behavior:

- Router chooses subject and lens.
- Deterministic answer assembly produces the same full answer object regardless of lens.
- Lens only controls visible section ordering and answer framing.
- All answers include, where supported: subject summary, knowns, source support, uncertainty/missing evidence, cannot-claim, citations, and coverage/status notes.

Superseded route targets for v0.4A relabeling:

- `template:ask:what_supports@v1`
- `template:ask:what_is_uncertain@v1`
- `template:ask:cannot_claim@v1`

These remain as historical D9 templates, but new v0.4A router/corpus labels should target `subject_answer` instead.

Must preserve:

- `template:ask:entity_360@v2` for explicit entity/profile lookups.
- `ui_help` for board usage/capability questions.
- `refuse:*` for action/prediction/finding/identity/out-of-scope cases.
- `gap:*` for reasonable supported product needs without a deterministic consumer.

Claim discipline:

- This is a taxonomy and answer-architecture decision, not real operator validation.
- It does not implement Open ASK yet.
- It does not create new source facts.
