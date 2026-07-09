# MAIN-CITYBRAIN-D6-GOVERNED-RUNTIME-TRACE-HARNESS-R1

Objective:
Generate trace fixtures for the 9 governed stages over one decision-support option set.

Stages:
RECALL
PLAN
VALIDATE_PLAN
EXECUTE
NORMALIZE
SYNTHESIZE
RESOLVE_ACTIONS
SUGGEST
COMPLETE

Rules:
- EXECUTE may only mean local simulator/optimizer/retrieval/cascade fixture execution, never real-world action.
- SYNTHESIZE is the only permitted narration stage.
- RESOLVE_ACTIONS maps to Track D proposal candidates only; no approvals.
- COMPLETE emits trace/audit/limitations only.

Output:
- trace fixture JSON/JSONL
- stage matrix
- negative tests
- validation report
- audits
