# Epoch 3 Master Ledger Spec

Emit one rollup ledger covering the full Epoch 3 chain. The ledger must be readable without opening every package folder.

Each row must include:

- package_id
- status
- closeout_type
- output_root
- publication_path
- proof_artifacts
- key_findings
- armed_now
- still_blocked
- no_model_guard_status
- limitations_ref

Output: `E3_MASTER_LEDGER.json`.
