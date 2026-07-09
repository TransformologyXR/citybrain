# MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V02-R1

Relabel the full 150-row assembled corpus from scratch using `ROUTE_TAXONOMY_V02_CONTRACT.json`.

Do not preserve the old Codex labels except as an input for audit comparison. The v0.1 labels are known unstable.

Input:
- `operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl`
- `ROUTE_TAXONOMY_V02_CONTRACT.json`
- `TEMPLATE_GAP_REGISTRY_V02.json`

Output:
- `operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl`
- `CORPUS_V0_LABEL_DISTRIBUTION_V02_REPORT.json`
- `CORPUS_V0_TEMPLATE_GAP_V02_REPORT.json`
- `CORPUS_V0_LABEL_CHANGE_FROM_V01_REPORT.json`

Rules:
- Preserve `source_type = synthetic_v0_clean_ai`.
- Do not open router preflight.
- Do not split/seal.
- Use exact closed route labels from v0.2.
- Use precise gap IDs; no generic gaps.
- Fill `requires_selected_item_context` using Rule 8 from the taxonomy.
- Keep `raw_question` untouched.

Status if successful:
`PASS_D14_CORPUS_V0_RELABELED_V02_PENDING_DOUBLE_LABEL`.
