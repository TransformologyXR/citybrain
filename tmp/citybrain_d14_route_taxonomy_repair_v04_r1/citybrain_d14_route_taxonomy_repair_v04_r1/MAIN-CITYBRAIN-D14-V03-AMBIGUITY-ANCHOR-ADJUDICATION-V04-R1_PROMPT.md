# MAIN-CITYBRAIN-D14-V03-AMBIGUITY-ANCHOR-ADJUDICATION-V04-R1

Read `D14_DOUBLE_LABEL_V03_AUDIT.json` and the remaining ambiguity report.

Create `ROUTE_TAXONOMY_V04_ANCHOR_SET.json` using `ROUTE_TAXONOMY_V04_ANCHOR_SET_DRAFT.json` from this prompt pack as the canonical adjudication for the 21 v0.3 disagreement rows.

Requirements:
- Verify every anchor `row_id` exists in the full 150-row corpus.
- Verify the raw question for each anchor matches the v0.3 audit row.
- Apply the canonical route/refusal class in v0.4 relabeling.
- Mark anchors as `adjudicated_anchor_v04=true` in a sidecar ledger, not necessarily in the corpus row unless your schema supports it.
- Anchors are not counted in the next independent double-label disagreement denominator.

Output:
- `ROUTE_TAXONOMY_V04_ANCHOR_SET.json`
- `V04_ANCHOR_SET_VALIDATION_REPORT.json`
