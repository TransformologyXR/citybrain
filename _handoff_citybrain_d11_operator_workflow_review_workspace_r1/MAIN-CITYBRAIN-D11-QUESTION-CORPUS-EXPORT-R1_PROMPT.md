# MAIN-CITYBRAIN-D11-QUESTION-CORPUS-EXPORT-R1

Export the D14 input corpus from real operator sessions.

Required artifact:
- `inputs/d14_open_ask_operator_corpus/operator_question_corpus.jsonl`

Each row:
- `session_id`
- `task_id`
- `raw_question`
- `selected_item_context`
- `operator_intent_guess` (if obvious, nullable)
- `was_answered_by_current_template` true/false/unknown
- `expected_route_if_known` nullable
- `notes`

Rules:
- Only real non-builder spontaneous questions count for D14 preflight.
- Template/synthetic questions may be kept in a separate file but do not satisfy D14.

Deliverables:
- `operator_question_corpus.jsonl` or `CORPUS_PENDING_NO_REAL_SESSIONS.json`
- `D14_CORPUS_READINESS_DECISION.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
