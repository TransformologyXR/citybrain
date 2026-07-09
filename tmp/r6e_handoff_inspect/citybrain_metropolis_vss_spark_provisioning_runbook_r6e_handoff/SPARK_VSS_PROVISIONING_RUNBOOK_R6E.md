# Spark VSS Provisioning Runbook — R6E

## Goal

Make Spark expose one safe VSS invocation path:

- HTTP endpoint, or
- command wrapper

The path must accept bounded evidence context from R2 and return text that is classified as `model_generated_narrative` only.

## Required installation facts to capture

- Spark host name/IP or alias
- VSS service/container/process name
- serving mode: endpoint or command
- model/runtime version if available
- port/path if endpoint
- command path if wrapper
- auth mode, with secrets redacted
- reachable from orchestrator: yes/no
- health probe result
- bounded sample probe result

## Endpoint shape

The endpoint should accept JSON and return JSON. Minimal request:

```json
{
  "request_id": "vss-r6e-probe-001",
  "mode": "bounded_narration_probe",
  "evidence_context": {
    "candidate_event_id": "...",
    "candidate_observation_count": 24,
    "source_class": "sensor_inferred",
    "allowed_narration_role": "model_generated_narrative_only"
  }
}
```

Minimal response:

```json
{
  "request_id": "vss-r6e-probe-001",
  "status": "ok",
  "source_class": "model_generated_narrative",
  "text": "Bounded narration text here",
  "limitations": ["Narration is not a fact source"]
}
```

## Command wrapper shape

The command should read JSON input from a file or stdin and write JSON output to stdout or an output file. It must exit non-zero on failure.

## R7 gate

Only open R7 if:

- health probe succeeds
- bounded sample probe succeeds
- output source_class is `model_generated_narrative`
- forbidden claim scan passes
- secret audit passes
