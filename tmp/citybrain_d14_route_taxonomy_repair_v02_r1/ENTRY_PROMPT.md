# ENTRY PROMPT — D14 Route Taxonomy Repair v0.2 R1

You are repairing the D14 synthetic corpus route taxonomy after the double-label gate failed with 58.82% disagreement.

Do not treat this as a corpus failure. Treat it as a taxonomy failure.

Inputs:
- `outputs/main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate/CORPUS_V0_DOUBLE_LABEL_AUDIT.json`
- `outputs/main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate/operator_question_corpus_synthetic_v0_labeled_codex_prelim.jsonl`
- `outputs/main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate/operator_question_corpus_synthetic_v0_assembled_unlabeled.jsonl`
- `outputs/main_citybrain_d14_synthetic_corpus_v0_assembly_labeling_split_gate/CORPUS_V0_TEMPLATE_GAP_REPORT.json`

Run the prompts in this order:

1. `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-FAILURE-ANALYSIS-R1_PROMPT.md`
2. `MAIN-CITYBRAIN-D14-ROUTE-TAXONOMY-V02-CONTRACT-R1_PROMPT.md`
3. `MAIN-CITYBRAIN-D14-TEMPLATE-GAP-REGISTRY-V02-R1_PROMPT.md`
4. `MAIN-CITYBRAIN-D14-CORPUS-V0-RELABEL-V02-R1_PROMPT.md`
5. `MAIN-CITYBRAIN-D14-DOUBLE-LABEL-V02-GATE-R1_PROMPT.md`
6. `MAIN-CITYBRAIN-D14-TAXONOMY-REPAIR-CLOSEOUT-R1_PROMPT.md`

Stop after producing the new blind double-label sample. Do not run Split/Seal R3 until independent v0.2 labels are returned and disagreement is <= 15%.
