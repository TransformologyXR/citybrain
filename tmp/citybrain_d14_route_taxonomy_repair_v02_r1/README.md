# CityBrain D14 Route Taxonomy Repair v0.2 R1

Purpose: repair the D14 synthetic corpus route taxonomy after the double-label gate found >15% disagreement. This pack does not train the router and does not open Split/Seal R3 until taxonomy stability is re-proven.

Run from `ENTRY_PROMPT.md`.

Expected safe statuses:
- `PASS_D14_ROUTE_TAXONOMY_V02_STABLE_READY_FOR_RELABELED_DOUBLE_LABEL`
- `PAUSED_D14_ROUTE_TAXONOMY_V02_AWAITING_INDEPENDENT_DOUBLE_LABELS`
- `PAUSED_D14_ROUTE_TAXONOMY_V02_STILL_AMBIGUOUS`

Hard rule: no router training, no sealed split, and no real-operator claim until the revised double-label disagreement is <= 15%.
