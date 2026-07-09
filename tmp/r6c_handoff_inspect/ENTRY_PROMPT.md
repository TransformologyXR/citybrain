# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-RUNTIME-PROVISIONING-AND-CONFIGURATION-R6C

You are implementing the R6C provisioning/configuration gate for the CityBrain Metropolis/VSS lane.

Create:

```text
scripts/run_main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c.py
```

Output root:

```text
outputs/main_citybrain_metropolis_vss_runtime_provisioning_and_configuration_r6c
```

Freeze ZIP:

```text
METROPOLIS_VSS_RUNTIME_PROVISIONING_AND_CONFIGURATION_R6C_PACKAGE.zip
```

## Task

Implement a runner that determines whether a real VSS runtime command or endpoint is configured and safely reachable.

Do not run a narration task. Do not emit VSS prose. Do not fabricate narration.

## Required CLI

Support:

```text
--input-r6b-zip PATH
--vss-endpoint URL
--vss-command COMMAND
--health-path PATH
--timeout-seconds N
--output-root PATH
```

Also support environment variables:

```text
CITYBRAIN_VSS_ENDPOINT
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_HEALTH_PATH
CITYBRAIN_VSS_TIMEOUT_SECONDS
```

CLI values override environment values.

## Required outputs

Write these files:

```text
VSS_RUNTIME_PROVISIONING_R6C.json
VSS_RUNTIME_CONNECTIVITY_PROBE_R6C.json
R7_READINESS_GATE_R6C.json
R6C_CLOSEOUT_DECISION.json
RUNTIME_CONFIGURATION_AUDIT_R6C.json
SOURCE_CLASS_SEPARATION_AUDIT_R6C.json
CLAIM_BOUNDARY_AUDIT_R6C.json
NO_ACTION_AUDIT_R6C.json
SECRET_AUDIT_R6C.json
R6C_JSON_PARSE_REPORT.json
HASH_MANIFEST.json
README.md
```

## Required logic

1. Validate R6B lineage if an input package is provided.
2. Select runtime mode:
   - endpoint if endpoint is configured;
   - command if command is configured;
   - none if neither is configured.
3. Redact all command/endpoint values before writing artifacts.
4. Probe runtime only if configured.
5. Mark R7 readiness true only on successful bounded probe.
6. Preserve the hard boundary:
   - DeepStream/Metropolis = `sensor_inferred`
   - VSS = `model_generated_narrative_only_not_fact_source`
7. Produce a freeze ZIP and hash manifest.

## Do not

- Do not generate narration records.
- Do not modify R2 candidate observations/events.
- Do not create official record/action/ticket/alert.
- Do not leak endpoint tokens, API keys, credentials, or local secrets.
