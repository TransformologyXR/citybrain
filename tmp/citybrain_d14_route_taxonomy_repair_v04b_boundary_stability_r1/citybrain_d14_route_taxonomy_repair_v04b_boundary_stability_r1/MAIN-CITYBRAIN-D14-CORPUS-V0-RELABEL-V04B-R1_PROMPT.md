# MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04B-R1

Relabel the full 150-row synthetic corpus under v0.4B.

Inputs:
- v0.4A relabeled full corpus
- `ROUTE_TAXONOMY_V04B_CONTRACT.json`
- `D14_V04B_CANONICAL_BOUNDARY_ANCHORS.json`

Tasks:
1. Apply the v0.4B first-match decision tree.
2. Apply canonical anchors exactly for matching row IDs and raw questions.
3. Keep `source_type = synthetic_v0_clean_ai` on every row.
4. Fill:
   - normalized_question
   - requires_selected_item_context
   - expected_route_label
   - expected_refusal_class only for refusal labels
5. Ensure deprecated labels = 0:
   - direct `what_supports`
   - direct `what_is_uncertain`
   - direct `cannot_claim`
   - `template:ask:entity_360@v1`
   - non-v0.4B gap labels
6. Ensure non-closed labels = 0.

Outputs:
- `operator_question_corpus_synthetic_v0_labeled_v04b.jsonl`
- `CORPUS_V0_LABEL_DISTRIBUTION_V04B_REPORT.json`
- `CORPUS_V0_TEMPLATE_GAP_V04B_REPORT.json`
- `D14_V04B_RELABEL_REPORT.json`

Do not split/seal. Do not train.
