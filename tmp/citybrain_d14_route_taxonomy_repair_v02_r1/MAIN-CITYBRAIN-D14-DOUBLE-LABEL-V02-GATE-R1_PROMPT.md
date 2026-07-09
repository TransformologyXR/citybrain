# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V02-GATE-R1

Prepare the revised independent double-label gate under taxonomy v0.2.

Input:
- `operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl`
- `ROUTE_TAXONOMY_V02_CONTRACT.json`

Tasks:
1. Select a blind sample of >=20% of surviving rows, stratified by v0.2 route label and persona.
2. Include all 20 prior disagreement rows if they survive, plus additional rows as needed for stratification.
3. Export blind sample with row_id, raw_question, persona, selected_item_context only.
4. Do not include Codex labels.
5. Stop and wait for independent labels.

Output:
- `CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V02_INSTRUCTIONS.md`
- `D14_DOUBLE_LABEL_V02_GATE_DECISION.json`

Status:
`PAUSED_D14_ROUTE_TAXONOMY_V02_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Do not run Split/Seal R3 until the independent labels are returned and route/refusal disagreement <= 15%.
