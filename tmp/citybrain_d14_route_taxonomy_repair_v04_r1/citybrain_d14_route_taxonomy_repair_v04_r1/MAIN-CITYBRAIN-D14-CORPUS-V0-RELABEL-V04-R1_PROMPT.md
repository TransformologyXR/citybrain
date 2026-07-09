# MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04-R1

Relabel the full 150-row synthetic corpus under v0.4.

Inputs:
- v0.3 labeled full corpus.
- `ROUTE_TAXONOMY_V04_CONTRACT.json`.
- `ROUTE_TAXONOMY_V04_DECISION_TREE.md`.
- `ROUTE_TAXONOMY_V04_ANCHOR_SET.json`.

Rules:
- Preserve `raw_question`, `source_type`, `source_session_id`, persona, provenance.
- Preserve `source_type = synthetic_v0_clean_ai` on every row.
- Fill/refresh `normalized_question`, `requires_selected_item_context`, `expected_route_label`, and `expected_refusal_class` under v0.4.
- For anchor rows, use the anchor canonical labels.
- Assert no deprecated v0.2/v0.3 labels remain.
- Assert no non-closed labels remain.
- Do not delete rows.

Outputs:
- `operator_question_corpus_synthetic_v0_labeled_v04_codex_prelim.jsonl`
- `CORPUS_V0_LABEL_DISTRIBUTION_V04_REPORT.json`
- `CORPUS_V0_TEMPLATE_GAP_V04_REPORT.json`
- `CORPUS_V0_V03_TO_V04_LABEL_CHANGE_REPORT.json`
- `V04_RELABEL_AUDIT.json`
