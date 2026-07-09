# ACCEPTANCE CHECKS — R6C

## PASS

R6C may PASS only if all are true:

```text
runtime_configured = true
probe_attempted = true
probe_executed = true
probe_status = SUCCESS
r7_ready = true
secret_audit = PASS
source_class_separation = PASS
claim_boundary = PASS
no_action = PASS
json_parse = PASS
hash_manifest = PASS
```

## PARTIAL

Use a partial when:

```text
runtime_configured = false
```

or when:

```text
runtime_configured = true
probe_status != SUCCESS
```

## FAIL

Use FAIL if any of these occur:

```text
secret leak detected
candidate event modified
VSS treated as fact source
official record/action/ticket/alert created
claim boundary broken
unsafe command execution pattern detected
```

## R7 gate

`MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-SMOKE-R7` may open only after an R6C/R6B PASS with `r7_ready=true`.
