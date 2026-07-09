# MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04A-R1

Relabel the full 150-row synthetic corpus under v0.4A.

Inputs:

- Assembled synthetic corpus from prior Assembly R1.
- v0.4A contract and decision tree.
- Optional hard-shaped top-up raw rows if present and validated.

Outputs:

- `operator_question_corpus_synthetic_v0_labeled_v04a_codex_prelim.jsonl`
- `CORPUS_V0_LABEL_DISTRIBUTION_V04A_REPORT.json`
- `CORPUS_V0_TEMPLATE_GAP_V04A_REPORT.json`
- `CORPUS_V0_V04A_DEPRECATED_LABEL_AUDIT.json`

Rules:

- Preserve raw questions and provenance.
- Do not delete rows.
- Fill `normalized_question`.
- Fill `requires_selected_item_context` under v0.4A rule.
- Fill exactly one closed route label.
- No direct labels to deprecated v0.1/v0.2/v0.3 route targets.
- For subject-answer labels, include structured metadata fields if useful:
  - `subject_hint`
  - `lens`
  - `route_family = ask_subject_answer`
- For gap labels, make product backlog text precise.
- For refusals, fill `expected_refusal_class`.
- For non-refusals, `expected_refusal_class` must be null.

Important subject-answer mapping:

- support/evidence/back/source support -> `template:ask:subject_answer@v1:lens=support`
- missing/unknown/uncertain/no data -> `template:ask:subject_answer@v1:lens=uncertainty`
- can claim/prove/establish/verify/certify/blocked/live/available/affected/caused -> `template:ask:subject_answer@v1:lens=claimability`
- what is going on/what do we know/general selected item summary -> `template:ask:subject_answer@v1:lens=summary`

Report any rows where v0.4A remains hard to apply. Do not silently force a label without a note.
