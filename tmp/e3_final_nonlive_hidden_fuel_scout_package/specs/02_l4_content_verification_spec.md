# L4 content verification spec

L4 candidates from the prior scout may have weak lineage (`path_or_name_lineage_only`). This package must verify content before any future materialization is recommended.

## Classification

- `content_verified`: file content contains case-like subject, source refs, outcome/review state or evidence refs.
- `path_only`: candidate came from filename/path only.
- `needs_manual_review`: ambiguous but potentially useful.
- `not_promotable_before_closeout`: insufficient for Epoch 3 closeout upgrade.

No rows are materialized here.
