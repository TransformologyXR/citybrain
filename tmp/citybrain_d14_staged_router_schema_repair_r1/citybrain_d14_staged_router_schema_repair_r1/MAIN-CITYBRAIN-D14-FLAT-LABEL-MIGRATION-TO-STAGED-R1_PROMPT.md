# MAIN-CITYBRAIN-D14-FLAT-LABEL-MIGRATION-TO-STAGED-R1

## Goal
Mechanically migrate the 150 v0.4B-labeled rows into staged schema, flagging only ambiguous migrations for human review.

## Mapping examples
- `refuse:action_shaped` → A=`action_shaped`, B=`meta_product_question` or relevant onward family, C=`refusal`, D=`not_applicable`.
- `refuse:prediction_or_finding` → A=`prediction_or_finding`, C=`refusal`.
- `refuse:identity_or_person` → A=`identity_or_person`, B=`identity_person_question`, C=`refusal`.
- `ui_help` → A=`clear`, B=`meta_product_question`, C=`ui_help`, D=`not_applicable`.
- `gap:patch_queue_query_needed` → A=`clear`, B=`patch_queue_question`, C=`patch_queue_query_gap`, D=`not_applicable`.
- `gap:source_record_360_needed` → A=`clear`, B=`source_record_question`, C=`source_record_360_gap`, D=`not_applicable`.
- `gap:external_context_source_needed` → A=`clear`, B=`external_context_question`, C=`external_context_source_gap`, D=`not_applicable`.
- `template:ask:entity_360@v2` → A=`clear`, B=`city_subject_question`, C=`entity_360`, D=`not_applicable`.
- `template:ask:subject_answer@v1:lens=support` → A=`clear`, B=`city_subject_question`, C=`subject_answer`, D=`support`.
- `template:ask:subject_answer@v1:lens=uncertainty` → A=`clear`, B=`city_subject_question`, C=`subject_answer`, D=`uncertainty`.
- `template:ask:subject_answer@v1:lens=claimability` → A=`clear`, B=`city_subject_question`, C=`subject_answer`, D=`claimability`.
- `template:ask:subject_answer@v1:lens=summary` → A=`clear`, B=`city_subject_question`, C=`subject_answer`, D=`summary`.

## Ambiguous migration flag
Flag rows where the flat label does not determine Stage A/B/C confidently, especially:
- capability phrased as possible external communication/action;
- product/security/compliance questions;
- “prove/verify/establish” with source-row language;
- “can we tell drivers…” style multi-valent rows;
- source details vs claim support;
- supported negative answer vs refusal.

Do not silently resolve these. Mark `migration_confidence = ambiguous` and include reasons.

## Outputs
- `STAGED_CORPUS_V0_MIGRATED_PRELIM.jsonl`
- `STAGED_MIGRATION_REPORT_R1.json`
- `STAGED_AMBIGUOUS_MIGRATION_ROWS.jsonl`
- `STAGED_PREDICTED_HARD_SAMPLE_SEED.jsonl`

## Status
`PASS_D14_FLAT_LABEL_MIGRATION_TO_STAGED_R1_WITH_AMBIGUITIES_RECORDED`
