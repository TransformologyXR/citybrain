# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04B-SAMPLE-R1

Create a new v0.4B blind double-label sample and instructions.

Inputs:
- `operator_question_corpus_synthetic_v0_labeled_v04b.jsonl`
- `ROUTE_TAXONOMY_V04B_DECISION_TREE.md`
- `D14_V04B_CANONICAL_BOUNDARY_ANCHORS.md`

Sample requirements:
- 50–60 rows total.
- Include all 13 v0.4A non-lens disagreement rows as explicit stress/anchor rows.
- Include at least 10 additional rows from the same hard buckets if available.
- Include fresh hard-shaped top-up rows if available locally; if none exist, log `NO_FRESH_HARD_SHAPED_TOPUP_ROWS_AVAILABLE` as limitation.
- Stratify by persona and route family.
- Do not include Codex labels, lenses, route hints, refusal classes, or canonical answers in the blind sample.

Blind sample fields:
- row_id
- raw_question
- persona
- selected_item_context
- source_type
- source_session_id
- original_question_id if available

Outputs:
- `CORPUS_V0_DOUBLE_LABEL_V04B_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04B_INSTRUCTIONS.md`

The instructions must include the v0.4B decision tree and canonical examples, but must not include Codex labels for sample rows.

Stop for independent labels after this. Expected next file:
`CORPUS_V0_DOUBLE_LABEL_V04B_INDEPENDENT_LABELS.jsonl`
