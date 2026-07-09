# Publication Home Retroactive Sweep Spec

Problem: `outputs/` is gitignored, so governance artifacts produced during Epoch 3 are not durable unless published somewhere tracked.

Required solution:

- Create `publications/epoch3/` or equivalent.
- Publish governance-only artifacts for every Epoch 3 package.
- Track decisions, ledger rows, limitations, hash manifests, LF reports, summary/status artifacts.
- Exclude bulk data, large JSONL, raw source dumps, and model binaries.
- Add LF pinning to `.gitattributes`, especially for JSON/JSONL/YAML/MD under publications.

Output: `E3_PUBLICATION_HOME_SWEEP_REPORT.json`.
