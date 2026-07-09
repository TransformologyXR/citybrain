# PACKAGE CONTRACT — R6E

Expected final implementation package root:

`outputs/main_citybrain_metropolis_vss_spark_provisioning_runbook_r6e`

Expected freeze ZIP:

`METROPOLIS_VSS_SPARK_PROVISIONING_RUNBOOK_R6E_PACKAGE.zip`

## Required files

```text
SPARK_VSS_PROVISIONING_RUNBOOK_R6E.md
SPARK_VSS_ENDPOINT_CHECKLIST_R6E.md
SPARK_VSS_COMMAND_WRAPPER_CHECKLIST_R6E.md
SPARK_VSS_RUNTIME_CONFIG_TEMPLATE.env.example
RUNTIME_HOST_ALLOCATION_R6E.json
SPARK_VSS_PROVISIONING_STATUS_R6E.json
SPARK_VSS_CONNECTIVITY_PROBE_PLAN_R6E.json
R7_READINESS_GATE_R6E.json
R6E_CLOSEOUT_DECISION.json
JSON_PARSE_REPORT_R6E.json
HASH_MANIFEST.json
```

## Required audits

- JSON parse audit
- hash manifest audit
- host allocation audit
- secret redaction audit
- no-action audit
- claim-boundary audit
- VSS fact-source audit
