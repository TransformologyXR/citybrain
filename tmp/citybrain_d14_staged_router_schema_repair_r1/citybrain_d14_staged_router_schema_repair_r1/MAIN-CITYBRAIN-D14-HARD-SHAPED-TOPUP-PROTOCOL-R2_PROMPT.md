# MAIN-CITYBRAIN-D14-HARD-SHAPED-TOPUP-PROTOCOL-R2

## Goal
Prepare targeted clean-session top-up generation for the hard buckets, without contaminating clean sessions with router taxonomy or labels.

## Hard-shaped target buckets
- action-adjacent communication: “can we tell drivers…”, “should we notify…”, “can the board alert…”
- product-meta/security/compliance: “does this software comply…”, “is this official…”, “can this be shared externally…”
- source support vs source-row details: “what does record 87 say” vs “what does record 87 prove/support”
- EV live/blocked/availability claimability
- weather/live/external context gaps
- patch queue aggregate/list/filter questions

## Output
Create a paste-clean prompt and run log template. Do not run the clean sessions unless explicitly requested or available.

The prompt must:
- show only `DEFAULT_VISIBLE_TEXT.txt` stimulus and plain operator-world instructions;
- never mention templates, stages, labels, router, gaps, or taxonomy;
- request JSONL rows with `normalized_question`, route fields, and refusal fields null;
- mark source type as `synthetic_v0_clean_ai_hard_topup` or equivalent, never real;
- require fresh sessions and stimulus SHA.

## Outputs
- `HARD_SHAPED_TOPUP_CLEAN_SESSION_PROMPT_R2.md`
- `HARD_SHAPED_TOPUP_RUN_LOG_TEMPLATE.json`
- `HARD_SHAPED_TOPUP_PROTOCOL_DECISION.json`

## Status
- `PASS_D14_HARD_SHAPED_TOPUP_PROTOCOL_READY_NOT_RUN`
- or `PASS_D14_HARD_SHAPED_TOPUP_ROWS_IMPORTED` if real clean top-up rows are already present and validated.
