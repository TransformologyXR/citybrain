# ENTRY PROMPT — MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-REPAIR-V04A-SUBJECT-ANSWER-R1

You are Codex operating in `C:\Users\hazem\Documents\CityBrain`.

Run the D14 Route Taxonomy Repair v0.4A sequence. This supersedes the earlier v0.4 package. Do not run router training. Do not run Split/Seal R3 until independent labels and the new gates pass. Do not claim real operator validation.

## Required input roots

Use the latest available D14 synthetic corpus artifacts:

- `outputs/main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate/`
- `outputs/main_citybrain_d14_route_taxonomy_repair_v02_r1/`
- `outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1/`

If required files are missing, stop with a clear blocked decision.

## Run sequence

1. `MAIN-CITYBRAIN-D14-V03-AMBIGUITY-ROOT-CAUSE-R2`
2. `MAIN-CITYBRAIN-D14-SUBJECT-ANSWER-ARCHITECTURE-DECISION-R1`
3. `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04A-CONTRACT-R1`
4. `MAIN-CITYBRAIN-D14-HARD-SHAPED-TOPUP-CORPUS-PROTOCOL-R1`
5. `MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V04A-R1`
6. `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V04A-SAMPLE-R1`
7. `MAIN-CITYBRAIN-D14-REFUSAL-BOUNDARY-BUCKET-GATES-R1`
8. `MAIN-CITYBRAIN-D14-COLD-LABELER-PROBE-PACKET-R1`
9. `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V04A-CLOSEOUT-R1`

## Required stop

Stop before final adjudication, Split/Seal R3, or router preflight. The expected decision is:

`PAUSED_D14_ROUTE_TAXONOMY_V04A_AWAITING_INDEPENDENT_DOUBLE_LABELS`

## Deliverables

At minimum produce:

- `D14_V03_AMBIGUITY_ROOT_CAUSE_R2.md`
- `SUBJECT_ANSWER_ARCHITECTURE_DECISION_R1.json`
- `ROUTE_TAXONOMY_V04A_CONTRACT.json`
- `ROUTE_TAXONOMY_V04A_DECISION_TREE.md`
- `HARD_SHAPED_TOPUP_CORPUS_PROTOCOL.md`
- `operator_question_corpus_synthetic_v0_labeled_v04a_codex_prelim.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04A_BLIND_SAMPLE.jsonl`
- `CORPUS_V0_DOUBLE_LABEL_V04A_INSTRUCTIONS.md`
- `REFUSAL_BOUNDARY_BUCKET_GATES_R1.json`
- `COLD_LABELER_PROBE_PACKET_R1.jsonl`
- `D14_ROUTE_TAXONOMY_V04A_CLOSEOUT_DECISION.json`
- validation package ZIP and hash manifests

## Non-negotiable rules

- `template:ask:subject_answer@v1(subject,lens)` replaces direct routing to `what_supports`, `what_is_uncertain`, and `cannot_claim` for v0.4A relabeling.
- Lens controls section priority only; it does not change the underlying assembled answer object.
- Do not add new narrow labels for every wording nuance.
- Do not treat supported negative answers as refusals.
- Refuse only out-of-scope/action/prediction/finding/identity cases.
- Keep gap labels product-facing and backlog-oriented.
- Preserve all synthetic provenance.
