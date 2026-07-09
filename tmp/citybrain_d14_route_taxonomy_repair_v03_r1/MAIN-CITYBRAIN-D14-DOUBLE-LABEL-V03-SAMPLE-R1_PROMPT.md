# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V03-SAMPLE-R1

Create the v0.3 blind double-label sample.

Requirements:
- Minimum sample size: 40% of the 150 rows, unless corpus size differs; must be >= 60 rows.
- Include all prior v0.2 disagreement rows from `D14_DOUBLE_LABEL_V02_AUDIT.json`.
- Stratify across v0.3 preliminary label, persona, and source session.
- Export no Codex route labels.
- Include only:
  - row_id
  - raw_question
  - persona
  - selected_item_context
  - source_type
  - source_session_id
- Write:
  - `CORPUS_V0_DOUBLE_LABEL_V03_BLIND_SAMPLE.jsonl`
  - `CORPUS_V0_DOUBLE_LABEL_V03_INSTRUCTIONS.md`

Instructions must tell the independent labeler:
- use only v0.3 labels;
- do not consult Codex preliminary labels;
- fill `normalized_question`, `requires_selected_item_context`, `expected_route_label`, `expected_refusal_class`;
- use deprecated labels never;
- return `CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl`.

Stop after exporting the blind sample.
