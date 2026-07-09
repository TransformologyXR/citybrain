# ENTRY PROMPT — MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V03-R1

You are Codex working in the CityBrain workspace.

Run the v0.3 route-taxonomy repair. Do not train a router, do not open router preflight, and do not run Split/Seal R3.

## Inputs

Use the prior v0.2 output root if available:

`outputs/main_citybrain_d14_route_taxonomy_repair_v02_r1/`

Required prior files:
- `D14_DOUBLE_LABEL_V02_AUDIT.json`
- `CORPUS_V0_DOUBLE_LABEL_V02_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V02_INDEPENDENT_LABELS.jsonl`
- `operator_question_corpus_synthetic_v0_labeled_v02_codex_prelim.jsonl`

If prior files are missing, stop with a clear blocker. Do not reconstruct labels from memory.

## Sequence

1. Run `MAIN-CITYBRAIN-D14-V02-AMBIGUITY-ROOT-CAUSE-R1`.
2. Run `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V03-CONTRACT-R1`.
3. Run `MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V03-R1`.
4. Run `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V03-SAMPLE-R1`.
5. Run `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V03-CLOSEOUT-R1`.

## Required final status

`PAUSED_D14_ROUTE_TAXONOMY_V03_AWAITING_INDEPENDENT_DOUBLE_LABELS`

## Required next file after this pack

`outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1/CORPUS_V0_DOUBLE_LABEL_V03_INDEPENDENT_LABELS.jsonl`

## Do not

- Do not use the previous independent labels as labels for v0.3.
- Do not expose Codex labels in the blind sample.
- Do not reduce the double-label sample below 20%.
- Do not run Split/Seal R3.
- Do not open router preflight.
- Do not claim real operator validation.
