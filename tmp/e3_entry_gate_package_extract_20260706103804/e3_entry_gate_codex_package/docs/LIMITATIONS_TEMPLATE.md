# Limitation Rows Template

Use one row for every item the fixed-budget gate cannot measure.

| Limitation ID | Area | What was not measured | Why not measured | Consequence | Blocks? | Owner | Next check |
|---|---|---|---|---|---|---|---|
| LIM-001 | `<area>` | `<measurement>` | `<reason>` | `<impact>` | `<yes/no>` | `<owner>` | `<date/ref>` |

Rules:

- Unmeasured items become limitation rows, not gate extensions.
- Limitation rows must distinguish descriptive work limitations from trained/predictive blockers.
- Synthetic-only Dubai geography is a limitation row unless it contaminates training manifests.
