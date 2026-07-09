# CityBrain Metropolis/VSS — Spark VSS Provisioning Runbook R6E Handoff

Task: `MAIN-CITYBRAIN-METROPOLIS-VSS-SPARK-PROVISIONING-RUNBOOK-R6E`

This handoff prepares the Spark-side VSS provisioning/configuration runbook while the actual VSS runtime is being installed. It does **not** run VSS, does **not** generate narration, and does **not** open R7.

Current locked truth:

- DeepStream / Metropolis lane runs on `txr-4070` and is `sensor_inferred`, proven by R2.
- VSS lane is intended to run on Spark / DGX Spark but is not configured yet.
- `txr-3090` is not active for this Metropolis/VSS chain.
- R7 narration smoke remains blocked until a Spark VSS command or endpoint passes the R6D/R6E connectivity gate.

Use `ENTRY_PROMPT.md` as the implementation prompt.
