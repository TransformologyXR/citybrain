# CityBrain D14 Route Taxonomy Repair v0.4 — Shared Context

Purpose: repair the remaining D14 synthetic corpus route-label ambiguity after v0.3 still failed the double-label gate (`21/60 = 35%`, threshold 15%).

Input root expected:
`outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1`

Key v0.3 files to consume:
- `D14_DOUBLE_LABEL_V03_AUDIT.json`
- `D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md/json`
- `operator_question_corpus_synthetic_v0_labeled_v03_codex_prelim.jsonl`
- `ROUTE_TAXONOMY_V03_DECISION_TREE.md`
- `ROUTE_TAXONOMY_V03_CONTRACT.json`

Hard boundary:
- Do not open router training/preflight.
- Do not run Split/Seal R3.
- Do not claim real operator validation.
- Every corpus row remains `source_type = synthetic_v0_clean_ai`.
- This pass is taxonomy/label repair only.

The v0.4 design principle: reduce ambiguity by adjudicating known hard rows into an anchor set, tightening first-match routing rules, and testing generalization on a fresh non-anchor blind sample.
