# MAIN-CITYBRAIN-D14-V04A-BOUNDARY-FAILURE-ANALYSIS-R1

Analyze the v0.4A failure report with focus on the 13 non-lens family disagreements and 5 refusal-boundary hard errors.

Inputs:
- v0.4A audit JSON
- v0.4A comparison report
- v0.4A blind sample and independent labels

Output:
`D14_V04A_BOUNDARY_FAILURE_ANALYSIS_R1.json`

Required contents:
- exact route disagreement count and rate
- family disagreement excluding lens-only count/rate
- refusal-boundary hard error count/rate
- table of the 13 non-lens disagreement rows with:
  - row_id
  - raw_question
  - selected_item_context
  - Codex label
  - independent label
  - disagreement bucket
  - recommended v0.4B canonical label
  - reason
- table of context-dependency disagreements with recommended v0.4B flag

Important interpretation:
- v0.4A subject-answer lens-only disagreement is non-blocking and should not drive a new repair.
- Do not add more route labels to solve boundary instability.
- The repair must tighten first-match rules.
