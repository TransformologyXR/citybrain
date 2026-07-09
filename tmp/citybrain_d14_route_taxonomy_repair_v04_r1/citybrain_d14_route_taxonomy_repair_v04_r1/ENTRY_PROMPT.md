# ENTRY — MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04-R1

Run the D14 route taxonomy v0.4 repair pass.

## Inputs

Use the existing v0.3 output root:
`outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1`

Required files:
- `D14_DOUBLE_LABEL_V03_AUDIT.json`
- `D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md/json`
- `operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl`
- `ROUTE_TAXONOMY_V03_CONTRACT.json`
- `ROUTE_TAXONOMY_V03_DECISION_TREE.md`

## Output root

Create:
`outputs/main_citybrain_d14_route_taxonomy_repair_v04_r1`

## Sequence

1. Run `MAIN-CITYBRAIN-D14-V03-AMBIGUITY-ANCHOR-ADJUDICATION-V04-R1`.
2. Run `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04-CONTRACT-R1`.
3. Run `MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04-R1`.
4. Run `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04-SAMPLE-R1`.
5. Run `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04-CLOSEOUT-R1`.

## Stop condition

Stop at:
`PAUSED_D14_ROUTE_TAXONOMY_V04_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Do not run Split/Seal R3. Do not open router preflight/training. Do not claim real operator validation.
