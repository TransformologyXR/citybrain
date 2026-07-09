# Publication home recommendation

Problem: if `outputs/` is gitignored, governance artifacts may exist only on local disk.

Recommendation: use a repo-tracked publication path for small governance artifacts, e.g.:

```text
publications/epoch3/<package_id>/
```

Include:
- decisions
- ledger rows
- limitations
- hash manifests
- summaries
- small schemas/manifests needed to prove closeout

Exclude or separately archive:
- bulk data
- large JSONL rows
- model files
- raw source dumps

This package emits a recommendation row only; it does not change gitignore policy unless Codex explicitly chooses to implement a safe additive publication path.
