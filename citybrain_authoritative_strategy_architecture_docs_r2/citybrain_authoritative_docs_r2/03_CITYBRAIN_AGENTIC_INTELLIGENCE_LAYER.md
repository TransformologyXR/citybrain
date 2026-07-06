# CityBrain Agentic Intelligence Layer
## Agents, Flows, Authority, and Orchestration

**Status:** Authoritative agentic architecture document v2  
**Date:** 2026-07-05  
**Scope:** Defines CityBrain agents, agentic flows, authority levels, orchestration model, agent run envelope, and how agents activate intelligence modes.


---

## R2 update note — certified-state alignment

This R2 patch keeps the v1 product and architecture framing but adds the missing proof discipline: the authoritative docs now distinguish **strategy**, **current certified state**, **bounded proof**, **functional proof**, and **future roadmap**. A component is not treated as mature merely because it appears in the vision; it must cite a concrete gate, commit, runner, package, or acceptance artifact.

R2 also records the latest running-track truth:

- **ASK v1.1** is closed/published at core and retained-real-corpus levels, with app handoff R1 and app fixture vendoring R1 passed. Further work should consume existing sealed packets rather than extend ASK core.
- **Metropolis / VSS / DeepStream** is closed at bounded local/replay candidate-review level. DeepStream runtime is ready for CityBrain R9 local/replay on `txr-4070`; VSS remains narrative review assistance, not a fact source.
- **Omniverse / WebRTC** is closed at functional proof level for live scene/object-event review loop; UI/UX polish and native-product experience remain parked for a later lane.
- **CHECK** is split into CHECK v0 and CHECK v1 so dependent modes can move without waiting for the full contradiction/source-depth engine.
- **Event fabric** is split into Event Fabric v0/v1/v2 so the project does not accidentally build a full event-sourcing platform before one event type proves value.
- **Flows/cartridges** survive as packaging on top of modes; modes are capabilities, flows are product/scenario bundles that compose multiple capabilities.

## 1. Core thesis

CityBrain’s intelligence modes define **what the platform can do**. Agents define **how those capabilities become active**.

```text
Modes = product capabilities.
Agents = governed workers that activate capabilities.
Flows = bounded sequences of gates/tools/packets.
Orchestrator = the runtime that governs agents, validates outputs, enforces authority, and records trace.
```

CityBrain should not treat agents as free-form autonomous chatbots. Agents are scoped workers with missions, tools, evidence contracts, authority limits, and traces.

The desired architecture is:

```text
trigger
→ scoped agent mission
→ orchestrator validates scope and authority
→ agent gathers / computes / proposes through tools
→ EvidencePacket emitted
→ CHECK validates
→ output packet produced
→ authority gate decides next allowed step
→ trace recorded
```

---

## 2. What “agentic” means in CityBrain

A CityBrain agent is not an unbounded LLM loop. A valid CityBrain agent has:

```text
1. scoped mission
2. declared triggers
3. bounded tools
4. input/output contracts
5. evidence output
6. CHECK validation
7. authority level
8. trace
9. stop condition
10. failure/clarify/refusal/gap behavior
```

An agent may use an LLM in two bounded roles:

```text
reader / resolver
  help interpret messy input, detect intent, bind concepts, or classify ambiguity

writer / renderer
  convert assembled evidence into human-readable text
```

An agent may not use an LLM as the source of facts, authority, record state, execution state, or claimability.

---

## 3. Agent classes

### 3.1 Background scouting agents

These run on schedules, snapshots, new events, new records, or new media. They make CityBrain proactive.

Examples:

```text
Watch Scout Agent
Diff Scout Agent
Event / Incident Agent
Perception / Media Agent
Data Quality / Maturity Agent
Recall / Precedent Scout Agent
Spatial Consistency Agent
Synthetic Challenge Agent
```

### 3.2 Task agents

These run when a user or another agent selects an item, asks a question, requests a brief, or proposes a plan.

Examples:

```text
ASK Resolver Agent
Selected Item Investigation Agent
Evidence Sufficiency / CHECK Agent
Briefing Agent
Plan / Option Agent
Schedule / Optimization Agent
Simulation Agent
Spatial Selection Agent
```

### 3.3 Governance agents

These are not product features. They wrap the others.

Examples:

```text
Authority Gate Agent
Claim Audit Agent
Trace Auditor
Policy Evaluator
Approval Lifecycle Agent
```

---

## 4. Authority ladder for agents

Agents must declare their maximum authority level.

| Level | Name | Agent may do | Agent may not do |
|---:|---|---|---|
| 0 | Observe | Read records, events, media, state. | Emit operational recommendation. |
| 1 | Surface | Create candidate items, gaps, checks, summaries. | Propose an operational action. |
| 2 | Propose | Generate options, schedules, briefs, recommended next checks. | Execute or create official artifacts. |
| 3 | Request approval | Prepare approval packet, send to human workflow. | Execute before approval. |
| 4 | Execute approved workflow | Execute an approved adapter action under policy. | Expand scope beyond approval. |
| 5 | Monitor | Monitor execution outcome, detect exceptions, escalate. | Hide failure or self-approve remediation. |
| 6 | Conditional autonomy | Execute narrow pre-approved low-risk workflows. | Act outside pre-approved policy envelope. |

Current CityBrain agents should mostly run at Levels 0–2. Future production agents can move into Levels 3–5 only after authority contracts, workflow integration, audit, security, and rollback are implemented.

---

## 5. Agent run envelope

Every agent run should emit an `AgentRunEnvelope`.

```json
{
  "agent_run_id": "agent_run:...",
  "agent_id": "watch_scout@v1",
  "trigger": {
    "trigger_type": "snapshot|event|user_action|schedule|media|diff|manual",
    "trigger_ref": "..."
  },
  "scope": {
    "city": "...",
    "domain": "...",
    "entities": [],
    "time_window": "...",
    "authority_level_max": 2
  },
  "inputs": {
    "source_refs": [],
    "selected_item_ref": null,
    "event_refs": [],
    "snapshot_refs": []
  },
  "tools_used": [],
  "evidence_refs": [],
  "check_report_ref": "...",
  "output_packet_ref": "...",
  "authority_envelope_ref": "...",
  "outcome": "emitted|clarify|refused|gap|blocked|failed",
  "trace_ref": "..."
}
```

The envelope is the minimum unit of audit, replay, and agent usefulness measurement.

---

## 6. Core agent roster

## 6.1 Identity Resolution Agent

### Mission

Continuously improve canonical entity resolution.

### Triggers

```text
new source records
new GIS geometry
failed entity lookup
operator asks about unknown entity
duplicate candidate appears
conflicting attributes detected
```

### Inputs

```text
source entities
canonical entities
aliases
geometry
temporal assertions
source confidence
human review decisions
```

### Tools / skills

```text
deterministic key matcher
name/alias normalizer
spatial joiner
probabilistic matcher
attribute conflict detector
match candidate scorer
review queue emitter
```

### Outputs

```text
MatchCandidatePacket
EntityResolutionProposal
AttributeConflictReport
EntityQualityUpdate
UnresolvedIdentityQueueItem
```

### Intelligence value

This agent reasons under ambiguity. It turns fragmented source identity into a confidence-aware canonical entity layer.

### Authority

Level 1 initially: propose candidates and quality updates. Future Level 3/4 only for approved low-risk deterministic merges.

### Maturity

M1/M2: architecture defined, full engine not complete.

---

## 6.2 Graph Context Agent

### Mission

Build and refresh relationship context around entities.

### Triggers

```text
entity selected
new event
new relationship evidence
new source records
scheduled graph refresh
```

### Inputs

```text
EntityPacket
source relationships
spatial relationships
event relationships
service/dependency relationships
role assignments
```

### Tools / skills

```text
relationship ontology validator
spatial relationship builder
dependency path finder
graph traversal
edge confidence scorer
path explainer
```

### Outputs

```text
GraphContextPacket
CandidateAffectedEntityPacket
DependencyPathPacket
RelationshipGapReport
```

### Intelligence value

It converts isolated entities into city context and dependency reasoning.

### Authority

Level 1: context/candidate only.

### Maturity

M2: some graph capability exists, breadth incomplete.

---

## 6.3 Watch Scout Agent

### Mission

Populate the review/attention queue with candidate city situations.

### Triggers

```text
new snapshot
new event
new diff
new perception observation
scheduled scan
operator scope change
```

### Inputs

```text
source records
event state
diff outputs
GraphContextPacket
CheckReport
review state
perception candidates
```

### Tools / skills

```text
named query library
ranker
source-depth checker
graph adjacency checker
staleness checker
event-to-watch candidate emitter
```

### Outputs

```text
WatchCandidatePacket
RankedQueueUpdate
AttentionReason
SuggestedHumanCheck
```

### Intelligence value

It turns data into salience: what deserves attention now.

### Authority

Level 1 initially. Future Level 2 can propose next checks; Level 3+ only through approved workflow.

### Maturity

M2/M3 shallow. Needs more query families and event/state inputs.

---

## 6.4 Event / Incident Agent

### Mission

Handle new events, resolve them to entities, and assemble incident context.

### Triggers

```text
event fabric append
candidate observation emitted
road incident
outage
complaint
alarm
weather/crowd event
```

### Inputs

```text
EventPacket
CandidateObservation
EntityRegistry
GraphContext
source records
current state
```

### Tools / skills

```text
event validator
event-to-entity resolver
state materializer
graph expansion
evidence assembler
watch admission checker
brief generator
```

### Outputs

```text
IncidentPacket
CandidateAffectedEntityPacket
EvidencePacket
WatchCandidatePacket
IncidentBrief
UnresolvedEventQueueItem
```

### Intelligence value

It turns new happenings into operational context.

### Authority

Level 1/2 initially: surface and brief. Later propose response package under authority.

### Maturity

M1/M2. Event fabric is still thin.

---

## 6.5 Perception / Media Agent

### Mission

Convert media into candidate observations and evidence clips.

### Triggers

```text
new video/frame
camera health change
Metropolis/DeepStream output
RT-VLM output
operator loads media
```

### Inputs

```text
media source
camera registry
timestamp
location
zone definition
model output
frame/clip references
```

### Tools / skills

```text
detector / RT-VLM / DeepStream
tracker
zone evaluator
frame/clip extractor
model provenance logger
detection sufficiency checker
```

### Outputs

```text
CandidateObservation
CandidateEvent
EvidenceClip
ModelInferenceRecord
DetectionCheckReport
```

### Intelligence value

It extracts possible signals from pixels while preserving candidate-only semantics.

### Authority

Level 0/1 only until reviewed/corroborated. No direct action from detection.

### Maturity

Current ledger: Metropolis/VSS bounded proof closed. Product integration still needed.

---

## 6.6 Evidence Sufficiency / CHECK Agent

### Mission

Validate whether candidate outputs are supportable.

### Triggers

```text
ASK answer produced
WATCH item emitted
BRIEF generated
RECALL match produced
DIFF output produced
CandidateObservation emitted
Plan/Schedule proposal produced
SpatialSelection produced
```

### Inputs

```text
claim candidate
EvidencePacket
source class
confidence
freshness
coverage
model metadata
edge confidence
authority envelope
```

### Tools / skills

```text
claim-to-evidence mapper
source-class evaluator
freshness checker
coverage checker
contradiction detector
detection sufficiency checker
authority checker
abstain policy evaluator
```

### Outputs

```text
CheckReport
CannotClaimSection
MissingEvidenceReport
ContradictionReport
AbstainRecommendation
ClaimDowngradeInstruction
```

### Intelligence value

This is meta-intelligence over evidence and claims.

### Authority

Can block or downgrade claims. Can force clarify/refusal/abstain. Cannot create action.

### Maturity

M1/M2. Critical next foundation.

---

## 6.7 ASK Resolver Agent

### Mission

Interpret operator questions and produce governed answers.

### Triggers

```text
user question
follow-up question
selected item action
agent asks for context
```

### Inputs

```text
raw question
selected item context
session state
EntityRegistry
GraphContext
source records
concept-binding registry
```

### Tools / skills

```text
boundary screen
deterministic resolver
LLM resolver fallback
concept binder
execution compiler
argument resolver
template executor
CHECK
renderer
```

### Outputs

```text
FlowEnvelope
IntentPacket
ExecutionContract
EvidencePacket
CheckReport
AnswerPacket
ClarificationPacket
RenderedResponse
```

### Intelligence value

It maps messy operator language into deterministic evidence execution.

### Authority

Reader/writer only; deterministic middle owns truth.

### Maturity

ASK v1.1 closed/published; app handoff next. Broader open/natural ASK still requires real operator corpus.

---

## 6.8 Briefing Agent

### Mission

Assemble evidence into human-useful briefs.

### Triggers

```text
operator generate brief
automated incident packet closes
watch item reaches threshold
scheduled shift brief
plan proposal created
```

### Inputs

```text
EvidencePacket
CheckReport
GraphContext
RecallPacket
DiffPacket
SpatialSelection
PlanPacket
AuthorityEnvelope
```

### Tools / skills

```text
brief assembler
citation formatter
persona renderer
exporter
section completeness checker
```

### Outputs

```text
BriefPacket
OperatorBrief
ExecutiveBrief
PlannerBrief
AnalystAppendix
ExportPackage
```

### Intelligence value

It composes evidence into operational communication.

### Authority

Level 1/2: communicate and propose. No official artifact unless authority permits.

### Maturity

M2/early M3.

---

## 6.9 Recall / Precedent Agent

### Mission

Find similar prior situations.

### Triggers

```text
selected watch item
new incident
operator asks “seen before?”
plan proposal needs precedent
```

### Inputs

```text
selected entity/situation
prior cases
review states
briefs
field matchers
embeddings if available
```

### Tools / skills

```text
field-computed matcher
weak-match classifier
embedding retriever
case comparer
prior outcome extractor
```

### Outputs

```text
RecallPacket
SimilarCaseCandidate
MatchReason
WeakMatchWarning
PriorCannotClaim
```

### Intelligence value

It makes institutional memory operational.

### Authority

Context only. No prediction.

### Maturity

M1/M2.

---

## 6.10 Diff Scout Agent

### Mission

Detect changes between snapshots.

### Triggers

```text
new snapshot
scheduled cadence
source update
```

### Inputs

```text
snapshot A
snapshot B
entity projection
source record hashes
field-level rules
```

### Tools / skills

```text
record differ
entity projector
change classifier
freshness updater
watch emitter
```

### Outputs

```text
DiffPacket
ChangeRecord
StalenessReport
WatchCandidatePacket
```

### Intelligence value

It converts source change into attention and freshness intelligence.

### Authority

Level 1.

### Maturity

M1/M2.

---

## 6.11 Plan / Option Agent

### Mission

Generate human-review options and proposed operational plans.

### Triggers

```text
incident packet
watch item selected
operator asks “what can we do?”
mission/goal submitted
```

### Inputs

```text
EvidencePacket
GraphContext
constraints
policy
CheckReport
SimulationResult
OptimizationResult
AuthorityEnvelope
```

### Tools / skills

```text
option generator
constraint evaluator
tradeoff builder
abstain/no-safe-option evaluator
proposal assembler
```

### Outputs

```text
OptionSet
PlanPacket
TradeoffReport
ProposalPacket
ApprovalRequest
```

### Intelligence value

It turns situation evidence into possible operational responses under constraints.

### Authority

Level 2 initially; Level 3+ after approval workflow exists.

### Maturity

M1/M2.

---

## 6.12 Schedule / Optimization Agent

### Mission

Sequence tasks, resources, closures, crews, inspections, or operational steps.

### Triggers

```text
plan needs schedule
resource constraint detected
incident backlog
inspection queue
operator scheduling question
```

### Inputs

```text
tasks
resources
calendars
constraints
time windows
objectives
```

### Tools / skills

```text
cuOpt/scheduler
constraint solver
feasibility checker
tradeoff summarizer
```

### Outputs

```text
SchedulePacket
ResourcePlan
FeasibilityReport
ConstraintViolationReport
ApprovalPacket
```

### Intelligence value

It reasons over time, capacity, and dependencies.

### Authority

Level 2/3 depending on approval state.

### Maturity

M1/M2.

---

## 6.13 Simulation Agent

### Mission

Run scenario and counterfactual models.

### Triggers

```text
plan option requires simulation
operator asks “what if?”
scenario pack runs
incident impact estimate required
```

### Inputs

```text
scenario state
parameters
calibration notes
GraphContext
EventState
PlanPacket
```

### Tools / skills

```text
SUMO
pandapower
EPANET
asset dependency simulator
weather/flood simulator
counterfactual checker
```

### Outputs

```text
SimulationResult
AssumptionSheet
UncertaintyReport
ScenarioComparison
```

### Intelligence value

It reasons under assumptions.

### Authority

Scenario evidence only unless tied to approved Plan/Schedule.

### Maturity

M0/M1.

---

## 6.14 Spatial Agent

### Mission

Keep spatial surfaces aligned with CityBrain truth.

### Triggers

```text
web selection
Kit selection
WebRTC scene interaction
event overlay update
scene load
spatial binding refresh
```

### Inputs

```text
SpatialSelection
EntityPacket
GraphContext
EvidencePacket
CheckReport
ReviewState
EventOverlay
```

### Tools / skills

```text
entity↔prim resolver
geometry lookup
overlay manager
scene receipt logger
one-truth parity checker
```

### Outputs

```text
SpatialSelectionPacket
OverlayPacket
SceneReceipt
OneTruthParityReport
CameraBookmark
```

### Intelligence value

It makes space a governed evidence surface instead of decoration.

### Authority

Spatial context only unless paired with approved workflow.

### Maturity

D13/R5 functional proof closed; product UI still needs work.

---

## 6.15 Data Quality / Maturity Agent

### Mission

Assess data readiness and improvement opportunities.

### Triggers

```text
ingestion batch
registry update
failed match
operator source gap
synthetic challenge run
scheduled maturity scan
```

### Inputs

```text
source systems
entities
relationships
quality tests
ingestion batches
validation results
operator gap logs
```

### Tools / skills

```text
schema validator
coverage scorer
duplicate detector
relationship coverage tester
freshness checker
source maturity scorer
```

### Outputs

```text
MaturityScorecard
DataGapBacklog
IdentityFragmentationReport
RelationshipCoverageReport
ImprovementRecommendation
```

### Intelligence value

It converts data quality into operational and commercial insight.

### Authority

Recommendations only.

### Maturity

M1 concept, product surface underbuilt.

---

## 6.16 Synthetic / Scenario Agent

### Mission

Generate gold, dirty, challenge, and scenario datasets.

### Triggers

```text
new domain pack
missing source data
regression failure
new demo target
entity-resolution test need
```

### Inputs

```text
real anchors
canonical entity spec
relationship ontology
scenario requirements
test gaps
```

### Tools / skills

```text
gold data generator
dirty source projector
challenge case generator
event scenario generator
validation harness
```

### Outputs

```text
GoldDataPack
DirtySourcePack
ChallengePack
ScenarioPack
ValidationSuite
```

### Intelligence value

It creates known-truth worlds to test and demonstrate intelligence before production data is complete.

### Authority

Test/demo only, source_class synthetic.

### Maturity

M1.

---

## 7. Agent-to-mode map

| Mode | Primary agents |
|---|---|
| WATCH | Watch Scout, Diff Scout, Event Agent, Perception Agent, CHECK Agent |
| ASK | ASK Resolver, Identity Agent, Graph Agent, CHECK Agent |
| CHECK | Evidence Sufficiency Agent |
| BRIEF | Briefing Agent, CHECK Agent, Recall Agent, Diff Scout |
| RECALL | Recall / Precedent Agent |
| DIFF | Diff Scout Agent |
| EVENT / INCIDENT | Event / Incident Agent, Graph Agent, CHECK Agent |
| PERCEPTION | Perception / Media Agent, CHECK Agent, Event Agent |
| SPATIAL | Spatial Agent, Graph Agent, CHECK Agent |
| PLAN | Plan Agent, Simulation Agent, Optimization Agent, CHECK Agent |
| SCHEDULE | Schedule / Optimization Agent, CHECK Agent, Authority Gate |
| SIMULATE | Simulation Agent, CHECK Agent |
| QUALITY | Data Quality / Maturity Agent, Identity Agent |
| SYNTHETIC | Synthetic / Scenario Agent |
| GOVERNANCE | Authority Gate, Claim Audit, Trace Auditor |

---

## 8. Orchestrator-to-agent relationship

The orchestrator is not a single agent. It is the governed runtime that sequences gates, validates proposals, invokes tools, and controls authority.

For each agent:

```text
Agent mission enters orchestrator
→ scope/authority validated
→ deterministic or hybrid gates run
→ tools execute
→ evidence assembled
→ CHECK validates
→ packet emitted
→ authority gate decides allowed next actions
→ trace recorded
```

The old 9-gate orchestrator pattern should become the reusable flow runtime for task agents. Background agents should still output through the same packet and CHECK contracts.

---

## 9. When to use a multi-agent framework

Do not introduce LangGraph or similar frameworks just to say “multi-agent.”

Use a state-machine/gated runtime first.

Introduce a graph-based agent framework only when:

```text
multi-step branching exceeds current orchestrator clarity
multiple specialist agents must negotiate shared state
long-running flows require resumability
approval/execution/monitoring loops need explicit graph state
simulation/optimization branches need compare/merge behavior
```

Until then, CityBrain agents should be services/workers with packet contracts, not dramatic autonomous personalities.

---

## 10. What agents change about the product

Without agents, CityBrain is:

```text
a cockpit that answers when asked
```

With agents, CityBrain becomes:

```text
a governed city intelligence system that scouts, detects, investigates, validates, briefs, proposes, schedules, executes approved workflows, and monitors outcomes.
```

That is the shift from dashboard/assistant to city brain.

---



## 10A. R2 near-term agent sequencing discipline

Do not build the full roster in parallel. The roster is a capability map, not a near-term work queue.

Near-term agent order:

```text
1. Evidence Sufficiency / CHECK Agent v0
2. ASK app handoff consumer, not ASK core
3. Watch Scout Agent v1 with 3–4 query families
4. Event / Incident Agent v0 over one event type
5. Diff Scout designed-change test and cadence
6. Spatial Agent packet-consumer polish after R5/WebRTC proof
7. Perception / Media Agent app-route integration after bounded DeepStream proof
```

Hold until later:

```text
Simulation Agent
Data Quality / Maturity Agent
Synthetic / Scenario Agent
Federation Agent
full Plan/Schedule execution agents
production authority / approval lifecycle agents
```

R2 also updates the Perception / Media Agent: it is no longer pure concept. It has bounded local/replay evidence through DeepStream on `txr-4070` and VSS on Spark, but remains candidate-only and not production surveillance.

## 11. Near-term agent implementation order

Recommended first agent build order:

```text
1. CHECK Agent
2. ASK app handoff / resolver integration
3. Watch Scout Agent
4. Event / Incident Agent
5. Diff Scout Agent
6. Spatial Agent
7. Perception / Media Agent integration
8. Briefing Agent v2
9. Recall Agent
10. Plan / Schedule Agents
```

Reasoning:

- CHECK must wrap everything.
- ASK must be in the app.
- WATCH and EVENT make the system active.
- DIFF and Spatial deepen context.
- Perception and Briefs integrate evidence.
- Recall, Plan, Schedule follow once evidence and state are richer.

---

## 12. Final agent principle

Every agent must answer five questions:

```text
What did you look at?
What did you infer or compute?
What evidence supports it?
What can you not claim?
What authority do you have to act next?
```

If an agent cannot answer those, it should not exist in CityBrain.

