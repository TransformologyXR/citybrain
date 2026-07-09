# ACCEPTANCE CHECKS — MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-SPLIT-HOST-READINESS-R6D

## Required PASS checks for handoff package

- All JSON parses cleanly.
- Hash manifest verifies every non-ZIP package file.
- Host allocation locks DeepStream/Metropolis to `txr-4070`.
- Host allocation records Spark / DGX Spark as intended VSS host, not yet a fact source.
- Host allocation records `txr-3090` as not active for this chain.
- R7 readiness remains false unless a real Spark VSS runtime probe succeeds.
- No VSS narration records are emitted.
- No candidate event is modified.
- No official record, ticket, alert, route, dispatch, enforcement, or legal finding is created.
- Secret audit passes.

## Runtime PASS checks for later R7 unlock

```text
spark_vss_runtime_configured = true
spark_vss_probe_attempted = true
spark_vss_probe_executed = true
spark_vss_probe_status = SUCCESS
r7_ready = true
```

## Required partial status when unconfigured

```text
PARTIAL_METROPOLIS_VSS_SPARK_RUNTIME_NOT_CONFIGURED_R6D_READINESS_CONTRACT_READY
```
