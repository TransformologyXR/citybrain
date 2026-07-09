# PROMPT — MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-INTERFACE-PREFLIGHT

You are Codex continuing CityBrain Track S after the option-set contract preflight.

## Task

Create the governed 9-stage runtime interface preflight.

Task name:

`MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-INTERFACE-PREFLIGHT`

Expected status on success:

`PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_INTERFACE_PREFLIGHT_WITH_LIMITATIONS`

Expected output root:

`outputs/main_citybrain_d6_governed_9_stage_runtime_interface_preflight/`

Expected runner:

`scripts/run_main_citybrain_d6_governed_9_stage_runtime_interface_preflight.py`

## Purpose

Define the future runtime as a governed deterministic state machine, not as nine autonomous LLM gates.

The stage chain is:

`RECALL → PLAN → VALIDATE_PLAN → EXECUTE → NORMALIZE → SYNTHESIZE → RESOLVE_ACTIONS → SUGGEST → COMPLETE`

## Load-bearing architecture rule

This is not nine gated LLMs.

Most stages are deterministic code/interface stages.
Only `SYNTHESIZE` is the single grounded narration stage.

Motto:

`code computes, model narrates`

## Required stage definitions

For each stage define:

- `stage_name`
- `stage_purpose`
- `input_contract`
- `output_contract`
- `allowed_execution_kind`
- `model_allowed`
- `deterministic_required`
- `boundary_rules`
- `failure_modes`
- `audit_events`
- `trace_fields`

Required semantics:

### RECALL
Retrieve relevant state, evidence, scenario, graph, option-set, prior case, and limitation context.

### PLAN
Select a review-safe plan shape for local simulation/optimizer/retrieval work. No real-world plan execution.

### VALIDATE_PLAN
Deterministically validate schema, allowed action enums, boundaries, and preconditions.

### EXECUTE
Run local simulator, optimizer, retrieval, or fixture only. No external action, no dispatch, no enforcement, no production call.

### NORMALIZE
Convert outputs into `reviewed_option_set` format.

### SYNTHESIZE
The only grounded narration stage. It narrates evidence and option-set facts. It does not invent truth.

### RESOLVE_ACTIONS
Map eligible options to Track D HITL proposal references. Does not approve or execute.

### SUGGEST
Produces safe next-look or human-reviewable option summaries only.

### COMPLETE
Writes trace, audit, limitations, hashes, and final status.

## Expected files

- `MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_INTERFACE_PREFLIGHT_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `GOVERNED_9_STAGE_RUNTIME_INTERFACE_SCHEMA.json`
- `STAGE_IO_CONTRACTS.json`
- `STATE_MACHINE_TRANSITION_RULES.json`
- `MODEL_USAGE_POLICY.json`
- `STAGE_BOUNDARY_RULES.json`
- `TRACE_AUDIT_CONTRACT.json`
- `SYNTHESIS_STAGE_GROUNDING_POLICY.md`
- `INTERFACE_VALIDATION_REPORT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Validation

Pass only if:

- All nine stages are defined.
- `SYNTHESIZE` is the only model/narration stage.
- `EXECUTE` is local sim/optimizer/retrieval only.
- No real-world action state exists.
- `NORMALIZE` outputs `reviewed_option_set`.
- `RESOLVE_ACTIONS` maps to Track D proposal refs without owning lifecycle.
- Boundary audits pass.
- Hash validation passes.

## Boundary

Contract-only. Do not build a full runtime loop yet. Do not run SUMO. Do not generate reviewed options. Do not execute actions.
