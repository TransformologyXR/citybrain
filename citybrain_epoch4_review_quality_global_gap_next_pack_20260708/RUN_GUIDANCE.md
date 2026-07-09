# Run Guidance

Prefer the sequence package.

Do not run these in parallel in one dirty worktree. They both consume the same audit outputs and write Epoch 4 publication artifacts.

Safe order:

```text
1. Review Pack Quality Upgrade R4/R5
2. Data Estate Gap Routing R1
3. Final Reverify
```

If you must parallelize, use isolated worktrees and run the final reverify only after merging/reconciling both outputs.
