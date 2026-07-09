# MAIN-CITYBRAIN-D9-OPERATOR-TASK-SCOREBOARD-R3

Score each usable non-builder session.

Metrics:
- minutes_to_context, if provided or derivable.
- questions_answered_with_citations.
- refusals_understood.
- briefs_generated_or_understood.
- watch_items_reviewed.
- check_mode_findings_understood.
- recall_usefulness_signal.
- operator_confusions.
- boundary_understood.

Output:
- `OPERATOR_TASK_SCOREBOARD_R3.json`
- `OPERATOR_TASK_SCOREBOARD_R3.md`

Do not invent timing or comprehension. If a field is absent, mark unknown.
