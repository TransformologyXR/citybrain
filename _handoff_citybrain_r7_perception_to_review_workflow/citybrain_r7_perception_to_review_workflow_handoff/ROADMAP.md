# ROADMAP — MAIN-CITYBRAIN-R7-PERCEPTION-TO-REVIEW-WORKFLOW-PREFLIGHT

## Sprint theme

```text
From review cockpit to candidate-observation and workflow handoff
```

## Baseline

R6 is closed:

```text
PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS
```

R6 proved:

- live WebRTC stream
- packet-backed WebUI/Kit object and event review loop
- collapsible side rail
- better inspector layout
- local workflow states
- review notes
- JSON/Markdown export
- actions remain `not_executed`

## Recommended R7 lanes

### Lane A — Perception candidate observation ingress

Task:

```text
MAIN-CITYBRAIN-R7A-PERCEPTION-CANDIDATE-OBSERVATION-INGRESS
```

Goal:

Use Metropolis/DeepStream/VSS-style outputs as candidate observations, not truth.

Minimum scope:

- local/replay video source or existing sample clip
- camera/source registry fixture
- detection/candidate observation JSON
- frame/clip evidence references
- confidence and timestamp metadata
- zone/source provenance
- candidate observation -> CityBrain event packet
- CHECK claimability audit
- WebUI/Kit review surface integration

Expected status:

```text
PASS_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS
```

### Lane B — Human review promotion gate

Task:

```text
MAIN-CITYBRAIN-R7B-HUMAN_REVIEW_PROMOTION_GATE
```

Goal:

Convert candidate observation packets into reviewed outcomes only after human/operator state change.

Minimum scope:

- review states: candidate, hold, needs_source, rejected, reviewed_candidate, promote_to_draft
- no direct official action
- no autonomous ticket/case creation
- reviewer note required for promotion
- audit trail required

Expected status:

```text
PASS_R7B_HUMAN_REVIEW_PROMOTION_GATE_WITH_LIMITATIONS
```

### Lane C — Official case/ticket workflow draft adapter

Task:

```text
MAIN-CITYBRAIN-R7C_CASE_TICKET_DRAFT_WORKFLOW_ADAPTER
```

Goal:

Create a sandbox/mock official workflow object from a reviewed candidate.

Minimum scope:

- draft case/ticket packet
- source evidence refs
- limitations/cannot-claim text
- reviewer note
- proposed classification
- no official submission by default
- adapter status: sandbox/mock/local only

Expected status:

```text
PASS_R7C_CASE_TICKET_DRAFT_WORKFLOW_ADAPTER_WITH_LIMITATIONS
```

### Lane D — Dispatch/control/enforcement proposal layer

Task:

```text
MAIN-CITYBRAIN-R7D_ACTION_PROPOSAL_AND_APPROVAL_BOUNDARY
```

Goal:

Model dispatch/control/enforcement-adjacent options as review-only proposals, not execution.

Minimum scope:

- action proposal object
- allowed actions enum
- prohibited/autonomous action audit
- human approval state
- adapter stub only
- no real dispatch/control/enforcement call
- `execution_status = not_executed`

Expected status:

```text
PASS_R7D_ACTION_PROPOSAL_APPROVAL_BOUNDARY_WITH_LIMITATIONS
```

### Lane E — Integrated perception-to-workflow smoke

Task:

```text
MAIN-CITYBRAIN-R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE
```

Goal:

End-to-end local/replay smoke:

```text
sample media/perception output
→ candidate observation
→ event packet
→ WebUI/Kit review
→ human review state
→ draft case/ticket packet
→ action proposal remains not_executed
```

Expected status:

```text
PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS
```

## Execution order

```text
1. R7A perception candidate observation ingress
2. R7B human review promotion gate
3. R7C case/ticket draft workflow adapter
4. R7D action proposal and approval boundary
5. R7E integrated smoke
```

## Stop line

Do not implement real production integrations in R7 unless separately approved and sandboxed.

Do not claim:

- live monitoring
- automated violation detection as final truth
- official legal/certified finding
- autonomous dispatch/control/enforcement
- production case/ticket submission
- safety-critical control
- public/cloud deployment
