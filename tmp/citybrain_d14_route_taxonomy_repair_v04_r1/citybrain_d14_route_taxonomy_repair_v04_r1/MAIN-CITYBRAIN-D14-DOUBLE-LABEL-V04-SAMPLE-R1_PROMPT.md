# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04-SAMPLE-R1

Create a new independent double-label sample.

Rules:
- Exclude the 21 adjudicated v0.4 anchor rows from the disagreement denominator.
- Select at least 20% of non-anchor rows, preferably 40–50 rows, stratified by preliminary v0.4 route label and persona.
- Do not include Codex labels in the blind sample.
- Include raw question, row id, persona, selected item context, and source/provenance fields needed for independent labeling.
- Include v0.4 instructions/decision tree for labelers, but do not include Codex preliminary labels.

Outputs:
- `CORPUS_V0_DOUBLE_LABEL_V04_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04_INSTRUCTIONS.md`
- `D14_DOUBLE_LABEL_V04_SAMPLE_DECISION.json`

Expected next file from independent labeler:
`CORPUS_V0_DOUBLE_LABEL_V04_INDEPENDENT_LABELS.jsonl`
