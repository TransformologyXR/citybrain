# CityBrain D14 — Route Taxonomy Repair v0.4A: Subject-Answer Consolidation

This pack supersedes the previously prepared `citybrain_d14_route_taxonomy_repair_v04_r1.zip`.

Reason: v0.1/v0.2/v0.3 double-label gates repeatedly failed, but the remaining disagreement pattern is no longer just a labeling problem. The hardest rows legitimately map to multiple lenses of the same subject answer. A good answer to “can we claim EV asset 87 is blocked?” contains both claimability and missing-evidence content; forcing a single route among `what_supports`, `what_is_uncertain`, and `cannot_claim` creates arbitrary disagreement.

## Prior state

- Six clean synthetic generations created 480 raw rows.
- Assembly R1 validated and merged 150 rows.
- v0.1 double-label disagreement: 20/34 = 58.82%.
- v0.2 double-label disagreement: 35/63 = 55.56%.
- v0.3 double-label disagreement: 21/60 = 35%.
- Split/Seal R3 has not run.
- Router preflight/training has not opened.
- Real operator validation remains unclaimed.

## Durable product rules

- Review/query/context only.
- No autonomous action.
- No dispatch, routing/control, enforcement, approval, official ticket/case, legal/certified finding, or alert publication.
- A supported negative answer is not a refusal.
- Refusal is only for questions outside supported scope or requests for action/finding/prediction/identity/out-of-scope domain.
- Router maps question -> route + args or refusal; router never answers.
- Synthetic corpus can unblock router V0 engineering only with `_REAL_OPERATOR_REVALIDATION_PENDING` status.
- Real D14 remains blocked until real non-builder corpus exists.

## Main v0.4A change

Introduce a consolidated route family:

`template:ask:subject_answer@v1(subject, lens)`

Lenses:
- `support`
- `uncertainty`
- `claimability`
- `summary`

The lens controls which section renders first, not which answer is assembled. The answer object still contains knowns, source support, uncertainty/missing evidence, cannot-claim, citations, and coverage/status notes.

This collapses most ambiguity among:
- `template:ask:what_supports@v1`
- `template:ask:what_is_uncertain@v1`
- `template:ask:cannot_claim@v1`

These legacy labels should not be targets for v0.4A relabeling except as preserved historical references.
