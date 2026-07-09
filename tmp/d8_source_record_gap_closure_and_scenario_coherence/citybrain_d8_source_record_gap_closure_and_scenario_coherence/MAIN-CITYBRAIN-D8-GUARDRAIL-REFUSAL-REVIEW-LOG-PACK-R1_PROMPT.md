# MAIN-CITYBRAIN-D8-GUARDRAIL-REFUSAL-REVIEW-LOG-PACK-R1

Goal: produce a viewer-ready M07 refusal record from real guardrail/bridge/runtime logs, if present.

Search bounded inputs:
- option-set promotion guardrail smoke outputs.
- bridge forbidden-command rejection logs.
- runtime trace negative gate outputs.
- web/bridge command audit outputs.

A valid M07 refusal record requires:
- refused_command_type
- attempted_action_shape (e.g. dispatch/route/approve/enforce/create_ticket/send_alert)
- timestamp or run_id
- rejection_reason
- boundary basis
- execution_state = not_executed
- visible human-readable wording
- technical evidence refs
- not_a_finding / no action created

If only generic PASS_BLOCKED_OR_CONTEXT_ONLY packet fields are available, keep PARTIAL.

Produce:
- `GUARDRAIL_REFUSAL_REVIEW_LOG_PACK_R1_DECISION.json`
- `guardrail_refusal_review_records.json`
- `GUARDRAIL_REFUSAL_DATA_DEPTH_GAPS.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `HASH_MANIFEST.json`
