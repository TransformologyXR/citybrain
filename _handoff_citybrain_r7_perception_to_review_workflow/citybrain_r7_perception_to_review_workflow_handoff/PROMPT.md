# PROMPT — MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT

You are implementing the next CityBrain sprint:

```text
MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT
```

## Context

R6 is closed:

```text
PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS
```

R7 now introduces perception/VSS/Metropolis/DeepStream-style inputs and official workflow draft/proposal handling.

Do not implement autonomous dispatch/control/enforcement. Do not claim official legal/certified findings.

## Required architecture

Implement R7 as gated lanes:

```text
R7A: perception candidate observation ingress
R7B: human review promotion gate
R7C: case/ticket draft workflow adapter
R7D: action proposal and approval boundary
R7E: integrated local/replay smoke
```

## Create runner

```text
scripts/run_main_citybrain_r7_perception_to_review_workflow_preflight.py
```

Output root:

```text
outputs/main_citybrain_r7_perception_to_review_workflow_preflight
```

## Implement lane A

Create candidate observation fixtures or ingest real local/replay perception output if available.

Required:

- candidate observation schema
- source/camera/media registry fixture
- frame/clip evidence refs
- confidence metadata
- zone/source provenance
- candidate observation -> event packet bridge
- CHECK report
- WebUI/Kit review packet export

## Implement lane B

Create human review promotion gate.

Required states:

- candidate
- hold
- needs_source
- rejected
- reviewed_candidate
- promote_to_draft

Promotion must require reviewer note.

## Implement lane C

Create draft case/ticket packet.

Required:

- draft only
- local/sandbox adapter only
- no official submission
- evidence and limitations included
- `submission_status = draft_not_submitted`

## Implement lane D

Create action proposal object.

Required:

- proposal only
- human approval required
- no execution
- `execution_status = not_executed`
- prohibited autonomy audit

## Implement lane E

End-to-end smoke:

```text
candidate observation
→ event packet
→ WebUI/Kit review packet
→ human review state
→ draft case/ticket packet
→ action proposal remains not_executed
```

## Required reports

Write:

```text
ENTRY_PROMPT.md
README.md
DECISION.json
CANDIDATE_OBSERVATION_INGRESS_AUDIT.json
PERCEPTION_SOURCE_PROVENANCE_AUDIT.json
CHECK_CLAIMABILITY_AUDIT.json
HUMAN_REVIEW_PROMOTION_GATE_AUDIT.json
CASE_TICKET_DRAFT_ADAPTER_AUDIT.json
ACTION_PROPOSAL_BOUNDARY_AUDIT.json
WEBUI_KIT_REVIEW_SURFACE_AUDIT.json
ONE_TRUTH_PACKET_AUDIT.json
BOUNDARY_AUDIT.json
TEST_LOG.txt
LIMITATIONS.md
HASH_MANIFEST.txt
```

Suggested folders:

```text
fixtures/
candidate_observations/
draft_workflow_packets/
action_proposals/
webui_evidence/
kit_evidence/
source_refs/
```

## Tests

Add tests for:

- candidate observation schema
- perception-to-event packet mapping
- review promotion gate
- draft case/ticket creation
- action proposal no-execution boundary
- forbidden claims
- R6 WebUI regression if relevant

Run full discovery.

## Decision

Use PASS only if the lane actually satisfies the acceptance criteria. Otherwise use partial.

Fail if any official submission, live enforcement, autonomous action, or unsupported legal/certified claim appears.
