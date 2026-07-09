# MAIN-CITYBRAIN-D14-OPERATOR-CORPUS-AUDIT-AND-LABELING-R1

Audit and label real operator questions.

Label categories:
- supported existing template
- supported with new template needed
- unsupported data-depth refusal
- action/dispatch/control refusal
- legal/certified finding refusal
- prediction refusal
- identity/privacy refusal
- ambiguous/multi-intent clarification/refusal

Each labeled row must include:
- raw question
- selected context
- expected route or refusal reason
- nearest supported questions, if refusal
- evidence/source families needed

Deliverables:
- `LABELED_OPERATOR_QUESTION_CORPUS.jsonl`
- `CORPUS_TEMPLATE_COVERAGE_REPORT.json`
- `CORPUS_REFUSAL_TAXONOMY_REPORT.json`
## Non-negotiable boundary

Do not claim production readiness, public API readiness, live monitoring, operational alerts, autonomous action, dispatch, routing/control, enforcement, official case/ticket creation, legal/certified finding, certified affected asset/building, certified physical geometry, identity/biometric inference, or action execution.

All verbs are review-local only unless this prompt explicitly says otherwise. Local notes/exports/session summaries are not official city records and must not mint IDs that could be mistaken for official case/ticket numbers.
