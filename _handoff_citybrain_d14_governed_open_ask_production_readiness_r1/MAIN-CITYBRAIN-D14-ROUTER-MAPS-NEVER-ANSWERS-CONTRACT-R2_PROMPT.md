# MAIN-CITYBRAIN-D14-ROUTER-MAPS-NEVER-ANSWERS-CONTRACT-R2

Define final Open ASK router contract.

Router input:
- raw operator question
- selected item/entity context
- available template registry

Router output exactly one:
1. `{template_id, args, confidence, route_reason}`
2. `{refusal_reason, nearest_supported_questions[], confidence, route_reason}`

Forbidden router output:
- answer text
- facts
- citations not produced by template runner
- action recommendation
- legal/certified finding

Router trace must log:
- raw question
- parsed intent
- selected context
- route/refusal
- template output id or refusal card id

Deliverables:
- `OPEN_ASK_ROUTER_CONTRACT_R2.json`
- `ROUTER_TRACE_SCHEMA.json`
- `ROUTER_FORBIDDEN_OUTPUT_NEGATIVE_TESTS.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
