# ENTRY PROMPT — CityBrain D8 Actual-Record-Grounded UI Remediation

Run this as one dependency-ordered Codex lane. The goal is not to make the Web UI sound nicer. The goal is to make the live Mobility Access control room render **actual certified data records, entities, relationships, observations, cases, options, and trace evidence** instead of narrating CityBrain mechanics.

## Current problem

The current page is technically live, but it still says things like:

- "Mobility Access, D7, similar cases, cascade, trace, and Track D are shown together."
- "Cross-city memory provides 4 similar cases as context."
- "6 D7 candidate observations are visible as possible evidence."
- "Some links are qualitative and context-only."

That is softer jargon, not a product demo. A viewer needs to see:

- the actual corridor / place / access context
- actual entity refs and friendly names where available
- actual observations, not just observation counts
- actual similar cases, not just “4 similar cases”
- actual links/relationships and confidence/limitations
- actual review options with tradeoff values/axes
- actual Track D stop packets rendered as human-review cards

## Hard rule

Do not invent facts. If the runtime bundle lacks a human-readable value, preserve the raw ID in technical details and create a `DATA_DEPTH_GAP` row. Do not replace missing data with generic prose.

## Required sequence

1. `MAIN-CITYBRAIN-D8-ACTUAL-RECORD-UI-GROUNDING-PREFLIGHT`
2. `MAIN-CITYBRAIN-D8-RUNTIME-BUNDLE-DATA-DEPTH-AUDIT-R1`
3. `MAIN-CITYBRAIN-D8-HUMAN-FACT-CARD-MODEL-R2`
4. `MAIN-CITYBRAIN-D8-WEB-ACTUAL-RECORD-RENDERING-PATCH-R3`
5. `MAIN-CITYBRAIN-D8-MOMENT-TO-RECORD-PARITY-SMOKE-R4`
6. `MAIN-CITYBRAIN-D8-ACTUAL-RECORD-UI-HUMAN-SMOKE-R5`
7. `MAIN-CITYBRAIN-D8-ACTUAL-RECORD-GROUNDED-UI-CLOSEOUT`
8. `MAIN-CITYBRAIN-D8-ACTUAL-RECORD-GROUNDED-UI-MILESTONE-FREEZE`

## Boundary

Preserve all durable CityBrain boundaries:

- local/replay/review/query context only
- no production/public API claim
- no autonomous monitoring, alerts, dispatch, routing/control, enforcement
- no official ticket/case
- no legal/certified finding
- no automated action
- `execution_state = not_executed`
- Track D remains authoritative for human-review promotion/proposal lifecycle

