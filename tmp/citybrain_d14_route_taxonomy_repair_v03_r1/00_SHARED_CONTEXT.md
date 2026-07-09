# D14 Route Taxonomy Repair v0.3 — Shared Context

Generated: 2026-07-03
Project: CityBrain D14 governed Open ASK / synthetic corpus v0

## Current state

D14 synthetic corpus assembly and labeling is paused. v0.1 and v0.2 double-label gates both failed because the route taxonomy remained ambiguous:

- v0.1 disagreement: 20 / 34 = 58.82%
- v0.2 disagreement: 35 / 63 = 55.56%

Do not run Split/Seal R3. Do not open router preflight. Do not train or implement router.

## Root issue

The taxonomy is mixing three different things into one label:

1. Existing deterministic template route.
2. Product backlog gap / missing deterministic consumer.
3. Conceptual answer type.

v0.3 must reduce label granularity and make the decision tree routeable. The goal is not maximum nuance. The goal is stable labels that a router can learn and that two labelers can apply consistently.

## Hard boundary

- Synthetic rows remain `source_type = synthetic_v0_clean_ai`.
- No real-operator validation claim.
- No Open ASK real-corpus claim.
- Router may open only after double-label disagreement is <= 15% and Split/Seal R3 is complete.
- Real operator corpus remains required to drop the `_PENDING` suffix later.
