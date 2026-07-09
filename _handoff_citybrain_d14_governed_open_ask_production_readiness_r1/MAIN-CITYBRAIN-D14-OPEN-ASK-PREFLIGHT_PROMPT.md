# MAIN-CITYBRAIN-D14-OPEN-ASK-PREFLIGHT

Inputs:
- `inputs/d14_open_ask_operator_corpus/operator_question_corpus.jsonl` from D11 real operator gate.
- D10 deterministic city-data search contract.
- D11 review workspace handoff.
- D12 data/DIFF handoff if available.
- D13 spatial handoff if available.
- Current template registry.

Hard blocker:
- If corpus is missing, empty, synthetic-only, or builder-only, stop as `BLOCKED_NO_REAL_OPERATOR_QUESTION_CORPUS`.

Preflight must report:
- number of real sessions
- number of spontaneous questions
- selected-item contexts covered
- unsupported/action/legal/dispatch/prediction questions present
- template coverage estimate

Deliverables:
- `D14_OPEN_ASK_PREFLIGHT_DECISION.json`
- `OPERATOR_CORPUS_PROVENANCE_AUDIT.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
