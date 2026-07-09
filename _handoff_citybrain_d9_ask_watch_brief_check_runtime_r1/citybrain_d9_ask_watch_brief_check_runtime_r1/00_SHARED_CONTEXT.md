# CityBrain D9 — Ask / Watch / Brief / Check Runtime R1

## Purpose

Implement the first daily-use product modes over the certified CityBrain records and story queue.

This is **not** a story-authoring sprint and **not** a UI-only sprint. It turns the data-readiness scouts into an operator-facing local/replay review cockpit.

## Source decisions consumed

- Narrow D9 data scout: `GO_D9_ASK_WATCH_BRIEF_WITH_LIMITATIONS`
- Broad D9 data scout: `SPLIT_D9_INTO_ASK_WATCH_BRIEF_AND_CHECK_DIFF`

Reconciled build decision:

- Build: `ASK`, `WATCH`, `BRIEF`, `CHECK`
- Allow: `RECALL` as a bounded cutaway only
- Defer: `DIFF`, `PERCEPTION/VSS`

## Durable boundary

Local/LAN/replay/review/query context only.

No production/public API, autonomous monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified finding, certified impact, or automated action.

Everything must preserve `execution_state = not_executed` and human-review authority.

## Key input assets expected

- Brain surface story queue bundle
- London Wood Lane scenario/source records
- NYC MVC cascade scenario/source records
- Chicago similar-case/precedent records
- Helsinki visual-pick source records
- D9 data scout closeouts and readiness matrices
- D8 limitations, no-action, claim-boundary, no-mutation, and no-fact-invention ledgers

## Product modes

### ASK
Cited answers to bounded questions. Every answer must include:
- answer summary
- source refs
- knowns
- unknowns
- explicit cannot-claim items
- limitation / boundary block

### WATCH
Manual review queue from named queries. This is not live monitoring or alerting.

### BRIEF
Evidence-backed brief packets for London Wood Lane and NYC MVC cascade.

### CHECK
Source-depth, claim-boundary, limitation, no-action, and no-fact-invention checks.

### RECALL cutaway
Chicago precedent memory only when match reasons and non-inference limits are visible.
