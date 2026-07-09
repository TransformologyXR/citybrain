# MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V03-R1

Relabel the full surviving 150-row synthetic corpus under route taxonomy v0.3.

Inputs:
- Prefer the latest assembled corpus before v0.2 relabeling if available.
- It is acceptable to start from `operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl` as the row source, but discard all v0.2 route labels and relabel from `raw_question`.

Rules:
- Use only v0.3 closed labels.
- Remove all deprecated v0.2 labels.
- Preserve `source_type = synthetic_v0_clean_ai`.
- Preserve provenance fields.
- Preserve `raw_question`.
- Fill `normalized_question`, `requires_selected_item_context`, `expected_route_label`, `expected_refusal_class`.
- Add `taxonomy_version = route_taxonomy_v03`.
- Do not delete rows.
- Do not train router.
- Do not split/seal.

Outputs:
- `operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl`
- `CORPUS_V0_LABEL_DISTRIBUTION_V03_REPORT.json`
- `CORPUS_V0_TEMPLATE_GAP_V03_REPORT.json`
- `CORPUS_V0_V02_TO_V03_LABEL_CHANGE_REPORT.json`

The v0.3 label distribution report must flag any deprecated label hit as a blocker.
