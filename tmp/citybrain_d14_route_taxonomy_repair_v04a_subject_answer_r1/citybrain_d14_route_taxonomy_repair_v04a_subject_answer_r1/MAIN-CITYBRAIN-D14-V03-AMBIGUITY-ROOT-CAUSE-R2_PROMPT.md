# MAIN-CITYBRAIN-D14-V03-AMBIGUITY-ROOT-CAUSE-R2

Analyze the v0.3 double-label audit and remaining ambiguity report.

Inputs:
- `outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1/D14_DOUBLE_LABEL_V03_AUDIT.json`
- `outputs/main_citybrain_d14_route_taxonomy_repair_v03_r1/D14_ROUTE_TAXONOMY_V03_REMAINING_AMBIGUITY_REPORT.md`
- v0.3 blind sample and independent labels if needed

Produce `D14_V03_AMBIGUITY_ROOT_CAUSE_R2.md`.

Required conclusions to verify or correct with evidence from the rows:

1. The remaining disagreement is concentrated, not random.
2. Many hard questions legitimately ask for multiple sections of one subject answer.
3. `what_supports`, `what_is_uncertain`, and `cannot_claim` are better modeled as lenses over one answer object than as competing route targets.
4. `source_record_360` should remain a separate gap only for questions about fields/details/contents of a specific source row.
5. Board capability vs imperative external action remains a true route/refusal boundary and must be gated separately.

Do not adjudicate rows into a pass. This step is explanatory only.
