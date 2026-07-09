# ENTRY PROMPT — MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04B-BOUNDARY-STABILITY-R1

Run the D14 route taxonomy v0.4B boundary-stability repair.

Use the current CityBrain workspace. Inputs are the v0.4A output root and existing synthetic corpus artifacts:

- `outputs/main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1/D14_DOUBLE_LABEL_V04A_AUDIT.json`
- `outputs/main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1/D14_ROUTE_TAXONOMY_V04A_COMPARISON_REPORT.md`
- `outputs/main_citybrain_d14_route_taxonomy_repair_v04a_subject_answer_r1/ROUTE_TAXONOMY_V04A_CONTRACT.json`
- the current 150-row synthetic corpus labeled under v0.4A.

Run the prompts in this order:

1. `MAIN-CITYBRAIN-D14-V04A-BOUNDARY-FAILURE-ANALYSIS-R1_PROMPT.md`
2. `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04B-CONTRACT-R1_PROMPT.md`
3. `MAIN-CITYBRAIN-D14-CANONICAL-BOUNDARY-ANCHORS-V04B-R1_PROMPT.md`
4. `MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04B-R1_PROMPT.md`
5. `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04B-SAMPLE-R1_PROMPT.md`
6. `MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-V04B-R1_PROMPT.md`
7. `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04B-CLOSEOUT-R1_PROMPT.md`

Stop at:
`PAUSED_D14_ROUTE_TAXONOMY_V04B_AWAITING_INDEPENDENT_DOUBLE_LABELS`

Do not run Split/Seal R3. Do not open router preflight. Do not train a router. Do not claim real operator validation.
