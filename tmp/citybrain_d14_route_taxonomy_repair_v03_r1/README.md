# CityBrain D14 Route Taxonomy Repair v0.3 R1

Use this pack after v0.2 double-label disagreement remains >15%.

Run `ENTRY_PROMPT.md`.

This pack tightens the taxonomy by:
- removing overly fine gap labels,
- making board-capability/local-workspace questions `ui_help`,
- separating imperative external actions from capability questions,
- routing selected-item claimability/live/blocked/availability questions to `cannot_claim`,
- collapsing patch-board count/filter/summary questions into one queue-query gap,
- keeping only a small set of product-gap route labels.

Expected output:
`PAUSED_D14_ROUTE_TAXONOMY_V03_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Do not run Split/Seal R3 in this pack.
