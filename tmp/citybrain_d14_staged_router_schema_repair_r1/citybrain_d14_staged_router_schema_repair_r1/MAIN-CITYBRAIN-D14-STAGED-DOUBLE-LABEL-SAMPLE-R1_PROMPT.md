# MAIN-CITYBRAIN-D14-STAGED-DOUBLE-LABEL-SAMPLE-R1

## Goal
Create a staged blind double-label sample that honestly tests the hard buckets without a denominator trick.

## Sample composition
Include:
- all v0.4B refusal-boundary hard-error rows;
- all v0.4B canonical-anchor disagreement rows;
- all ambiguous migration rows;
- a stratified sample from the remaining migrated corpus;
- fresh hard-shaped top-up rows if present;
- enough non-hard rows to test normal distribution.

Target sample size: 50–80 rows.

## Blind sample fields
Include only:
- row_id
- raw_question
- persona if present
- selected_item_context if present
- source_type
- source_session_id / provenance

Do not include Codex staged labels, flat labels, route hints, previous labels, or expected answers.

## Independent-label instructions
Export instructions containing:
- Stage A/B/C/D/E vocabularies.
- Composition rules.
- Per-stage gates.
- Requirement to label all stages independently.
- Requirement to set Stage D = `not_applicable` unless Stage C = `subject_answer`.
- Requirement to set downstream stages even for non-clear Stage A when possible as diagnostic, but make clear gates are on-policy.

## Outputs
- `CORPUS_V0_STAGED_DOUBLE_LABEL_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_STAGED_DOUBLE_LABEL_INSTRUCTIONS.md`
- `CORPUS_V0_STAGED_DOUBLE_LABEL_SAMPLE_REPORT.json`

## Status
`PAUSED_D14_STAGED_ROUTER_SCHEMA_AWAITING_INDEPENDENT_DOUBLE_LABELS`
