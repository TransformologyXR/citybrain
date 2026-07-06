# Ledger Publication Spec

## Atomic gate publication

The gate ledger row must publish these refs together:

```text
report_ref
arming_manifest_ref
evaluator_ref
hash_manifest_ref
```

The row is invalid if any referenced artifact is missing.

## Required row fields

```text
id
gate_id
status
report_ref
arming_manifest_ref
evaluator_ref
hash_manifest_ref
armed_now
not_armed
created_at
created_by
non_claims
```

## Hashing

The baseline report must be pinned to:

```text
corpus_version
corpus_hash
source_manifest_hash
synthetic_manifest_hash
scenario_manifest_hash
arming_manifest_hash
report_hash
```

## Status

Expected initial gate status:

```text
PASS_E3_ENTRY_FOR_DESCRIPTIVE_AND_HARNESS_WORK_WITH_LIMITATIONS
```
