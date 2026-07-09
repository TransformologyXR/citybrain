# ENTRY PROMPT — MAIN-CITYBRAIN-METROPOLIS-VSS-NARRATION-RUNTIME-INTEGRATION-R4

You are implementing the next bounded CityBrain Metropolis/VSS media lane task.

Create:

```text
scripts/run_main_citybrain_metropolis_vss_narration_runtime_integration_r4.py
```

Output to:

```text
outputs/main_citybrain_metropolis_vss_narration_runtime_integration_r4
```

Final freeze ZIP:

```text
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip
```

## Mission

Promote the R3 guarded partial into an execution-capable VSS narration runtime integration gate.

R3 closed as:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_BLOCKED_GUARDRAILS_READY
```

The blocker was not a boundary or package failure. VSS simply was not configured.

Your job is to implement the R4 adapter and validation package so that:

- if a real VSS command/endpoint is configured, R4 executes it and captures guarded narration;
- if VSS is still unconfigured, R4 closes honestly as a guarded partial;
- if VSS output violates the boundary, R4 fails.

## Required CLI

Implement CLI options:

```text
--input-r3-zip <path>
--output-root <path>
--vss-command <command string>              # optional
--vss-endpoint <http endpoint>              # optional
--timeout-sec <seconds>                     # default 120
--max-narration-records <n>                 # default 1 or small bounded value
--dry-run                                  # optional, validates package/adapter without executing
```

Environment fallback:

```text
CITYBRAIN_VSS_COMMAND
CITYBRAIN_VSS_ENDPOINT
CITYBRAIN_VSS_TIMEOUT_SEC
```

## Runtime execution rules

### Command mode

If `--vss-command` or `CITYBRAIN_VSS_COMMAND` is provided:

1. Build the R4 VSS input packet.
2. Run the command with bounded timeout.
3. Pass the input packet path as an environment variable:

```text
CITYBRAIN_VSS_INPUT_PACKET=<path>
```

4. Capture stdout/stderr to files.
5. Parse stdout as either JSON or JSONL if possible.
6. Normalize to R4 narration sidecar records.

### Endpoint mode

If `--vss-endpoint` or `CITYBRAIN_VSS_ENDPOINT` is provided:

1. POST the R4 VSS input packet JSON to the endpoint.
2. Use bounded timeout.
3. Capture HTTP status and response body.
4. Parse JSON/JSONL if possible.
5. Normalize to R4 narration sidecar records.

### No configured runtime

If neither command nor endpoint is provided:

- do not fabricate narration;
- emit zero narration records;
- mark runtime status as `NOT_CONFIGURED`;
- final status must be:

```text
PARTIAL_METROPOLIS_VSS_NARRATION_RUNTIME_NOT_CONFIGURED_R4_GUARDRAILS_READY
```

## Input packet

Build a VSS input packet that includes only bounded evidence context:

- media reference
- candidate event ref
- EvidenceBundle ref
- R2 object metadata summary
- R2 candidate observation refs
- candidate label
- forbidden claim list
- source-class rules
- human-review requirement

Do not include secrets.

## Narration sidecar schema

Each emitted VSS narration sidecar record must include:

```text
narration_id
source_class = model_generated_narrative
input_candidate_event_ref
input_evidence_bundle_ref
supported_candidate_observation_refs
narration_text
uncertainty_notes
claim_boundary_label
vss_runtime_ref
runtime_mode
created_at
guardrail_status
unsupported_claims
conflict_flags
human_review_required = true
official_record_created = false
no_action_taken = true
```

## Guardrails

Fail on any of:

- VSS claims it is a sensor/fact source
- VSS creates a confirmed violation/finding
- VSS identifies person/face/plate/biometric
- VSS creates or implies official case/ticket
- VSS commands dispatch/routing/control/enforcement/action
- VSS says sample video is live CCTV or production monitoring
- VSS invents object classes not present in R2
- VSS overrides the R2 object count
- VSS adds wall-clock timestamp not present in R2
- VSS modifies the candidate event

## Required output files

At minimum create:

```text
README.md
INPUT_R3_PACKAGE_VALIDATION_R4.json
VSS_RUNTIME_ADAPTER_CONFIG_R4.json
VSS_INPUT_PACKET_R4.json
VSS_RUNTIME_EXECUTION_REPORT_R4.json
VSS_NARRATION_SIDECARS_R4.jsonl
VSS_NARRATION_NORMALIZATION_REPORT_R4.json
VSS_NARRATION_GUARDRAIL_REPORT_R4.json
VSS_PROSE_VS_DETECTION_CONFLICT_AUDIT_R4.json
SOURCE_CLASS_SEPARATION_AUDIT_R4.json
CLAIM_BOUNDARY_AUDIT_R4.json
NO_ACTION_AUDIT_R4.json
SECRET_AUDIT_R4.json
CHECK_NARRATION_SUFFICIENCY_REPORT_R4.json
HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE_R4.json
MEDIA_EVIDENCEBUNDLE_WITH_VSS_NARRATION_R4.json
JSON_PARSE_REPORT_R4.json
HASH_MANIFEST.json
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_DECISION.json
METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_CLOSEOUT_DECISION.json
```

## Package checks

Before freezing the ZIP:

- parse all JSON
- parse all JSONL
- verify hash manifest
- run source-class separation audit
- run claim-boundary audit
- run no-action audit
- run VSS guardrail audit
- run secret audit

## Final response expected from Codex

Report:

```text
Final status: <status>
Runner: scripts/run_main_citybrain_metropolis_vss_narration_runtime_integration_r4.py
Output root: outputs/main_citybrain_metropolis_vss_narration_runtime_integration_r4
Freeze ZIP: outputs/main_citybrain_metropolis_vss_narration_runtime_integration_r4/METROPOLIS_VSS_NARRATION_RUNTIME_INTEGRATION_R4_PACKAGE.zip
VSS runtime attempted/executed: <true/false>/<true/false>
VSS narration records emitted: <n>
Audits: <PASS/PARTIAL/FAIL summary>
Known limitations: <bounded limitations>
Next recommended task: <task id>
```
