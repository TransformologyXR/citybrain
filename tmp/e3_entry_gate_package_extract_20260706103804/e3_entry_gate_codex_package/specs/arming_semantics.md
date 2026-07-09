# Arming Semantics

## Meaning of armed

`armed` means:

```text
MAY_BEGIN_UNDER_CADENCE_AFTER_ARMING_LEDGER_ROW
```

It does not mean:

```text
started
running
released
operator-facing
production
approved for official action
```

## Arming transition

When an increment changes from `not_armed` to `armed`, the evaluator emits:

```text
EPOCH3_ARMING_THRESHOLD_CROSSED
```

The ledger row must include:

```text
gate_id
increment_id
previous_state
new_state
satisfied_requirements
failed_requirements if any
metrics_snapshot_ref
manifest_ref
report_ref
hash_manifest_ref
created_at
```

## No silent start

No task runner, deployment, workflow, agent, or model may automatically start because a threshold crossed. Work begins only through the normal project cadence after the arming ledger row exists.

## Status vocabulary

```text
armed_now
conditionally_armed
blocked_until
not_armed
failed
pass_with_limitations
```
