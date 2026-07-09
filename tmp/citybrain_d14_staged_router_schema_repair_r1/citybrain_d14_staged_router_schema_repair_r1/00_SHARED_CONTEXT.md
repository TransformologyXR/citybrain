# CityBrain D14 — Staged Router Schema Repair R1

## Current state

D14 synthetic corpus work has intentionally refused to seal an unstable flat route taxonomy.

Known sequence:
- Six clean synthetic generations produced 480 raw rows.
- Assembly R1 produced 150 assembled synthetic rows with `source_type = synthetic_v0_clean_ai` preserved.
- Flat route taxonomy attempts failed double-label gates:
  - v0.1/v0 baseline: 58.82% disagreement.
  - v0.2: 55.56% disagreement.
  - v0.3: 35% disagreement.
  - v0.4A subject-answer consolidation: exact 28%, family 26%, lens-only mostly fixed.
  - v0.4B boundary stability: exact 38.18%, family 32.73%, refusal-boundary hard errors 2, gap-vs-template 10.91%.

Conclusion: the flat `expected_route_label` task is under-dimensional. It forces one label to encode boundary, intent family, template/gap/refusal target, lens, and selected-context dependency. Refining flat labels further is not productive.

## Accepted architectural decision

Replace the flat route-label decision with a staged router schema:

1. Stage A — Boundary / guard class.
2. Stage B — Intent family.
3. Stage C — Route target within family.
4. Stage D — Subject-answer lens, if applicable.
5. Stage E — Context requirement.

The stage design preserves the successful v0.4A subject-answer consolidation:

`template:ask:subject_answer@v1(subject, lens)`

`support`, `uncertainty`, `claimability`, and `summary` are lenses over one assembled subject answer. Lens disagreement is not equivalent to route-family failure.

## Non-negotiables

- Stage A is a guard, not a peer. Any non-clear Stage A routes to refusal or boundary-explanation path regardless of later stages.
- `ambiguous_boundary` is a legitimate Stage A output.
- Gap rows are in-scope, safe, unanswerable-today; they are template/product backlog, not refusals.
- Supported negative answers are not refusals.
- Real operator validation remains unclaimed.
- Split/Seal R3 must not run until staged double-label gates pass.
- Router preflight/training must not open until staged schema is stable and sealed.
