# MAIN-CITYBRAIN-D14-DOUBLE-LABEL-FAILURE-ANALYSIS-R1

Inspect the prior double-label audit.

Required outputs:
- `D14_DOUBLE_LABEL_FAILURE_ANALYSIS_R1.json`
- `D14_DOUBLE_LABEL_FAILURE_ANALYSIS_R1.md`

Analyze:
1. Route/refusal disagreements by pair, e.g. `entity_360` vs `what_supports`.
2. Questions where Codex used refusal but an answerable negative/cannot-claim response exists.
3. Questions where aggregate/list/filter requests were treated as refusal instead of patch-board query gaps.
4. Questions where `gap:general operator question needs taxonomy review` must become a precise gap ID.
5. Context-dependency disagreements and why the boolean is ambiguous.

Do not adjudicate by smoothing labels. The purpose is to identify rule ambiguity.

Use the 20 disagreement rows as evidence. Include each raw question and the disagreement pair.
