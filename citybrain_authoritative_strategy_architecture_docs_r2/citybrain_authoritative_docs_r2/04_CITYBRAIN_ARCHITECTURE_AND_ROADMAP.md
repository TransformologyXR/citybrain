# CityBrain Architecture and Roadmap
## From Prototype Spine to Governed Operations Platform

**Status:** Authoritative architecture and roadmap document v2  
**Date:** 2026-07-05  
**Scope:** Describes the target architecture, current state, component gaps, maturity model, and roadmap to evolve CityBrain from governed prototype into a city intelligence and operations platform.


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

## 1. Architecture thesis

CityBrain is an intelligence harness for cities. It is not a single application, model, graph, database, UI, or digital twin. It is a layered platform that coordinates data, identity, graph context, events, agents, evidence, CHECK validation, planning, workflow, spatial interfaces, perception, and authority.

The architecture should be designed around one core principle:

```text
Truth is managed deterministically; intelligence is assembled through governed flows; models help read and write, but do not own facts or authority.
```

The long-term product is a governed city intelligence and operations platform with progressive authority.

---

## 2. North-star architecture loop

```text
Sources / Events / Media / Spatial Interaction
→ Ingestion and Source Registry
→ Canonical Entity Registry
→ Semantic Entity Graph
→ Event Fabric and Operational State
→ Agentic Intelligence Layer
→ Orchestrator / Flow Runtime
→ EvidencePacket + CheckReport
→ Operator / Operations Modes
→ Web / Omniverse / API / Brief Surfaces
→ Workflow / Authority / Governance Trace
→ Approved Execution / Monitoring later
```

This loop is reusable across:

```text
ASK
WATCH
CHECK
BRIEF
RECALL
DIFF
INCIDENT
PERCEPTION
SPATIAL
PLAN
SCHEDULE
SIMULATE
QUALITY
FEDERATION
```

---

## 3. Architecture layers

## 3.1 L1 — Source and ingestion layer

### Purpose

Bring retained records, media, spatial data, events, simulation inputs, and human actions into CityBrain with provenance.

### Components

```text
source registry
ingestion adapters
file/API/connectors
snapshot manager
media source registry
camera registry
event append interface
source class assignment
provenance capture
```

### Required source classes

```text
official_record
source_record
sensor_inferred
model_inferred
derived_field
integrated_external
synthetic
replay
operator_input
approved_workflow_output
```

### Current gap

Ingestion exists in parts, but the source-class model and event/snapshot cadence are not yet a unified layer.

---

## 3.2 L2 — Canonical Entity Registry

### Purpose

Create the confidence-aware identity spine.

### Components

```text
canonical_entities
source_entities
entity_aliases
entity_type_definitions
attribute_assertions
attribute_conflicts
match_candidates
match_decisions
entity_quality_scores
review_state
```

### Rule

The registry owns identity truth. It does not overwrite source truth. It preserves source links, confidence, and conflicts.

### Current gap

Architecture is strong; full engine is incomplete.

---

## 3.3 L3 — Semantic Entity Graph

### Purpose

Project the registry into relationships and dependencies.

### Components

```text
canonical_relationships
source_relationships
relationship_evidence
relationship ontology
edge confidence
edge review state
path explanations
cross-domain dependency graph
```

### Rule

Graph owns traversal and relationship projection, not identity truth. It consumes registry contracts.

### Current gap

Graph/context capability exists, but cross-domain dependency breadth is incomplete.

---

## 3.4 L4 — Event fabric and operational state

### Purpose

Give the city a local operational nervous system.

### Components

```text
append-only event log
event schema
event validation
event-to-entity resolver
unresolved event queue
quarantine store
state materializer
state query API
event replay
expiry / supersession rules
```

### Rule

Temporally stamped records are not enough. Event fabric requires append, replay, materialize, query, trace.

### Current gap

Thin. Must be built before Incident/Plan mode becomes truly operational.

---

## 3.5 L5 — Orchestrator / cognition engine

### Purpose

Coordinate gates, agents, tools, evidence, CHECK, rendering, and authority.

### Components

```text
flow registry
gate contracts
agent runtime
boundary screen
intent/context resolver
execution compiler
tool runner
evidence assembler
CHECK gate
rendering gate
clarify/refusal/gap sinks
trace store
```

### Rule

LLMs may read and write, but deterministic gates own truth and authority.

### Current status

ASK v1.1 is closed/published and moving to app handoff. The general orchestrator should now become the reusable runtime for other modes.

---

## 3.6 L6 — Evidence and CHECK layer

### Purpose

Normalize evidence and validate claimability before output.

### Components

```text
EvidencePacket
CheckReport
source-class evaluator
freshness checker
coverage checker
claim-to-evidence mapper
contradiction detector
detection sufficiency checker
authority checker
abstain policy
```

### Current gap

Evidence packet thinking is strong. CHECK implementation is thin and must become a first-class engine.

---

## 3.7 L7 — Agentic intelligence layer

### Purpose

Activate intelligence modes through governed background and task agents.

### Components

```text
Watch Scout Agent
Event Agent
Perception Agent
Diff Scout Agent
ASK Resolver Agent
CHECK Agent
Briefing Agent
Recall Agent
Plan Agent
Schedule Agent
Simulation Agent
Spatial Agent
Data Quality Agent
Synthetic Scenario Agent
Authority/Governance Agents
```

### Current gap

Agentic concept is clear but not fully implemented as a coherent layer.

---

## 3.8 L8 — Experience layer

### Purpose

Serve intelligence through web, spatial, brief, API, and future operations surfaces.

### Components

```text
web cockpit
operator workspace
map/GIS view
Omniverse Kit panel
WebRTC streamed scene
brief exports
workflow state UI
approval UI later
API/local served runtime
```

### Current status

Web cockpit improved but not final. Omniverse/WebRTC functional proof closed, but spatial product UX still requires dedicated work.

---

## 3.9 L9 — Authority and governance layer

### Purpose

Control what CityBrain is allowed to say and do.

### Components

```text
AuthorityEnvelope
boundary classification
no-action / proposal / approval / execution states
forbidden command rejection
claim audit
workflow audit
approval lifecycle
execution adapter policy
monitoring / rollback later
RBAC/security later
```

### Current status

No-action and boundary discipline are strong. Progressive authority beyond proposal is future work.

---

## 4. Current certified-state snapshot — R2

This section is now a proof ledger, not a qualitative maturity paragraph. If a row lacks a gate, commit, runner, or package, it should not be treated as certified truth.

| Component | Current status | Proof / artifact | Proven | Not proven / limitation | Next lane |
|---|---|---|---|---|---|
| ASK v1.1 core | Closed / published | `3907bc1`, `1eab1d9` | Canonical packet flow, sealed eval, retained real-corpus eval. | Broad open ASK / arbitrary operator-question router. | Do not extend core; consume packets. |
| ASK app handoff | Passed | `1f92044`; `ASK-V11-APP-FIXTURE-VENDORING-R1 = PASS` | Stable committed handoff fixtures, fresh-clone fixture loading, app-side safety tests. | Browser visual smoke and full UX polish. | App consumption polish only. |
| R7 local/replay perception-to-review | Closed / pushed | `840f784 Add R7 local replay perception-to-review workflow` | Candidate-only perception-to-review workflow, WebUI/Kit parity, ASK runtime untouched. | Production perception, live CCTV, official cases, enforcement, dispatch. | Perception app-route integration after CHECK v0. |
| Metropolis / DeepStream | Internal alpha / bounded runtime ready | DeepStream 8 runtime proof on `txr-4070`; sample pipeline PASS. | Native Ubuntu host, RTX 4070 visible in Docker, DeepStreamSDK 8.0.0, sample file pipeline exit 0. | Live RTSP camera registry, production deployment, legal/violation findings. | R9 local/replay bounded runtime lane. |
| VSS | Narrative review context only | Spark VSS connectivity/runtime narration smoke; narration sidecar joined to evidence bundle. | VSS can produce review-assist narration. | VSS quality at scale, VSS as evidence/fact source. | Keep as model-generated narrative with CHECK. |
| Metropolis candidate-review lane | Closed at bounded product proof | Candidate observations/events, EvidenceBundles, human-review packets, static cockpit cards. | Offline/sample media to candidate-review product objects. | Live CCTV, reviewer disposition lifecycle, privacy/legal production policy. | App-route integration and privacy policy. |
| Omniverse / WebRTC R5 | Closed functional proof | `PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS` | Live stream, real Barcelona scene refs, prim selection parity, event overlay parity, packet truth, `not_executed`. | Finished Kit UI/UX, side rail, visual fidelity, full spatial workflow. | Later spatial UX lane. |
| CHECK | Concept and thin checks only | Existing claim-boundary/source-depth checks; R2 v0/v1 split. | The need and packet location are clear. | Full claim-to-evidence, contradiction, detection sufficiency. | CHECK v0 immediately. |
| Event fabric | Thin / not operational fabric | Source/replay crossing and event concepts. | Need is defined. | Append/query/materialize/replay fabric. | Event Fabric v0. |
| WATCH | Small prototype | Existing queue and D9/D10 app surface. | Ranked attention can be rendered. | Rich query library, event/diff/perception-driven queue. | Watch Scout v1. |
| BRIEF | Prototype | Wood Lane and non-story EV brief patterns. | Evidence packet can be rendered as review brief. | Export/product polish; deep CHECK integration. | Brief v2 after CHECK v0. |
| RECALL | Partial | Hardened recall artifacts, but match reasons still limited. | Precedent concept exists. | Field-computed similarity at scale. | Recall matcher packs later. |
| DIFF | Limited | Zero-change diff and cadence work. | No false positives direction. | Designed-change positive test and real cadence. | Designed-change golden test. |
| CER / SEG | Architecture strong, engine partial | CER/SEG contracts, crosswalk, entity drafts. | Doctrine is stable: CER owns identity, SEG projects relationships. | Full cross-domain registry, relation engine, ID format enforcement. | CER/SEG v2 after immediate app/CHECK work. |
| Workflow | Prototype | Local notes, review state, sandbox draft patterns. | Local review states exist. | Real operator sessions and official workflow integration. | Operator sessions later. |
| Production authority | Future | Authority ladder in docs. | Progressive model is defined. | Auth/RBAC, adapters, approval lifecycle, live execution. | Deferred. |

### 4.1 DeepStream R9 local/replay readiness note

DeepStream runtime is confirmed ready for CityBrain R9 local/replay use on `txr-4070`:

```text
Host: native Ubuntu Linux, Ubuntu 26.04 LTS, kernel 7.0.0-22-generic.
GPU visibility: PASS, RTX 4070 visible via nvidia-smi on host and inside Docker.
Docker: PASS, Docker 29.6.0, Compose v5.2.0.
NVIDIA Container Toolkit: PASS, nvidia-container-toolkit 1.19.1.
DeepStream image: PASS, nvcr.io/nvidia/deepstream:8.0-samples-multiarch.
deepstream-app --version-all: PASS, DeepStreamSDK 8.0.0, CUDA driver 13.2, CUDA runtime 12.9, TensorRT 10.9, cuDNN 9.8.
Sample file pipeline: PASS, exit code 0, Received EOS and App run successful.
```

This upgrades the perception lane from “image/runtime pending” to “runtime ready for bounded local/replay.” It does **not** create a production live CCTV claim.

## 5. Main architecture gaps

## 5.1 Intelligence packet standard

The biggest cross-component risk is each mode inventing its own payload shape. Every mode must consume/produce shared packet types:

```text
EntityPacket
SourceRecordPacket
GraphContextPacket
EventPacket
CandidateObservation
EvidencePacket
CheckReport
AnswerPacket
BriefPacket
RecallPacket
DiffPacket
PlanPacket
SchedulePacket
SpatialSelectionPacket
ReviewState
AuthorityEnvelope
Trace
```

## 5.2 Event fabric

Without event fabric, CityBrain is static. Build append/replay/materialize/query.

## 5.3 CHECK engine

Without CHECK, perception, spatial, plan, and open ASK will overclaim.

## 5.4 CER/SEG engine

Without identity and relationships, agentic intelligence will drift.

## 5.5 Agent runtime

Without agents, modes remain passive features.

## 5.6 Progressive authority

Without an authority ladder, the product remains stuck at evidence/review level.

---

## 6. Roadmap phases

## Phase 1 — Stabilize intelligence contracts

### Goal

Make all modes speak the same packet language.

### Work

```text
ASK v1.1 app handoff
CHECK contract v1
EvidencePacket v2
SourceClass taxonomy
Concept-binding registry seed
Mode output packet standard
AuthorityEnvelope v1
```

### Exit criteria

```text
ASK packets render in app without changing ASK logic.
CHECK runs as explicit validation gate.
All mode outputs carry EvidencePacket, CheckReport, AuthorityEnvelope, Trace.
```

---

## Phase 2 — Build the local operational nervous system

### Goal

Make CityBrain respond to events and changes, not only static questions.

### Work

```text
event fabric append/replay
event validation/quarantine
event-to-entity resolver
state materializer
event-state query API
WATCH from event state
DIFF designed-change golden test
```

### Exit criteria

```text
An event enters, resolves or quarantines, updates materialized state, produces evidence, and can be queried or surfaced as WATCH candidate.
```

---

## Phase 3 — Deepen identity and graph

### Goal

Make the registry and graph real enough for cross-domain intelligence.

### Work

```text
CER engine
source entity links
attribute assertions
attribute conflicts
relationship evidence
confidence/review-state model
semantic graph v2
cross-domain dependency edges
```

### Exit criteria

```text
CityBrain can explain what an entity is, what sources say, what conflicts exist, and how it relates to other entities.
```

---

## Phase 4 — Productize cockpit and workflow

### Goal

Make the web/operator surface useful, not merely better worded.

### Work

```text
selected-item workspace
source-record profiles
ASK app handoff
CHECK everywhere
brief export
review/workflow state
watch query expansion
operator usability sessions
```

### Exit criteria

```text
Operator can work a patch end-to-end: select, ask, check, brief, recall/diff/spatial, hold/abstain/propose/export.
```

---

## Phase 5 — Spatial and perception integration

### Goal

Make CityBrain see and locate candidate observations safely.

### Work

```text
native Kit entity/evidence panel
WebRTC scene integration
spatial overlay manager
event overlays
Metropolis/VSS candidate observations
media evidence bundles
CHECK detection sufficiency
```

### Exit criteria

```text
Candidate observation becomes evidence packet, links to entity/event, appears in web/spatial surfaces, and remains candidate-only unless authority/review changes state.
```

---

## Phase 6 — Plan, schedule, simulate, optimize

### Goal

Move from explaining situations to proposing and comparing governed operational responses.

### Work

```text
Plan mode
OptionSet v2
do-nothing baseline
abstain/no-safe-option
cuOpt scheduling
SUMO first simulator
scenario packets
simulation CHECK
approval workflow
```

### Exit criteria

```text
CityBrain can produce candidate plans/schedules with constraints, assumptions, evidence, risks, and required approvals.
```

---

## Phase 7 — Federation, synthetic factory, and production readiness

### Goal

Make CityBrain reusable across cities/departments and prepare production authority.

### Work

```text
Dubai anchored synthetic pack
gold/dirty/challenge/scenario data
data maturity dashboard
department-local nodes
federated query
cross-city recall
production security/RBAC/audit/observability
authorized execution adapters
```

### Exit criteria

```text
CityBrain can support department-local intelligence, cross-domain federation, synthetic validation, and governed deployment planning.
```

---

## 7. Immediate sequencing recommendation

R2 immediate sequence:

```text
1. Certified-state ledger + crosswalk patch to docs
2. AuthorityEnvelope v1 + common packet fields
3. CHECK v0
4. ASK v1.1 app consumption polish, not ASK core extension
5. Event Fabric v0
6. Watch Scout v1 with 3–4 query families
7. Perception-to-review app-route integration
8. Omniverse UI/UX lane later, not now
```

This roadmap is a dependency map, not permission to build all agents or modes in parallel.



### Short-term

```text
1. ASK-V11-APP-HANDOFF-PREFLIGHT
2. CHECK-CONTRACT-V1
3. EVENT-FABRIC-R1
4. CER/SEG shared packet standard
5. WATCH Scout Agent v1
6. Metropolis/VSS EvidenceBundle integration
7. Spatial UI / Omniverse product lane continuation
```

### Medium-term

```text
1. selected-item workspace
2. source-record 360
3. patch queue query answers
4. real event state
5. diff positive-change detection
6. recall computed matchers
7. plan/schedule proposal packets
```

### Long-term

```text
1. approved workflow adapters
2. simulation stack
3. real production security/RBAC
4. department-local nodes
5. federated city brain
6. conditional autonomy for narrow low-risk tasks
```

---

## 8. Dependencies

### ASK app handoff depends on

```text
sealed ASK v1.1 packets
web/app packet adapter
CHECK contract awareness
```

### WATCH maturity depends on

```text
query library
event fabric
DIFF
CHECK
CER/SEG
```

### Perception maturity depends on

```text
media source registry
CandidateObservation
CHECK detection sufficiency
event resolver
spatial overlay
```

### Spatial maturity depends on

```text
Entity↔prim binding
EvidencePacket
CheckReport
ReviewState
EventOverlay
scene UX
```

### Plan/Schedule maturity depends on

```text
event state
graph dependencies
CHECK
simulation/optimization
progressive authority
approval workflow
```

### Execution authority depends on

```text
authority model
approval lifecycle
workflow adapter
audit/security/RBAC
monitoring/rollback
```

---



## 8A. Legacy terminology crosswalk — required companion

The new docs intentionally rename much of the older RTX/NVIDIA sprint vocabulary. The crosswalk is now a required companion because certified work under old names must not be silently treated as unbuilt.

Key rules:

```text
Modes are capabilities.
Agents are workers.
Flows/cartridges are product/scenario packaging over multiple modes.
D-numbered gates and G0–G4 gates remain proof references, not maturity labels.
Old [I]/[S]/[A]/[P] claim labels are not the same axis as source_class or M0–M6 maturity.
```

The crosswalk also makes six open items explicit:

```text
1. Flows/cartridges need a home as packaging over modes.
2. D-numbered gates and G0–G4 gates must be cited by any new maturity claim.
3. D13/R5 naming should be normalized into M-scale plus proof reference.
4. Canonical entity ID format must be restated.
5. Cosmos, Earth-2/CorrDiff, Triton, NGC/Docker must be explicitly deferred or mapped.
6. resource and development entity types need explicit mapping.
```

R2 decision: **flows/cartridges survive as packaging**. A flow is a named bundle of mode configurations, entity scope, data sources, scenario constraints, packets, and demo/product narrative. For example:

```text
Flow 2 construction-compliance cascade
= EVENT/INCIDENT + GRAPH + CHECK + BRIEF + PLAN over a construction-compliance cartridge.
```


## 9. Architecture anti-patterns to avoid

```text
1. More datasets without consuming modes.
2. Omniverse scene as a separate truth.
3. VSS language treated as evidence/finding.
4. CHECK reduced to caution text.
5. Agents as autonomous chatbots.
6. Graph built directly over messy source tables.
7. LLM planner generating execution truth.
8. UI passes without deeper intelligence.
9. Simulation presented as prediction.
10. Authority hidden behind “AI recommendation.”
```

---

## 10. Platform v1 definition of done

CityBrain Platform v1 is done when:

```text
1. CER resolves core city entities with provenance/confidence.
2. SEG expresses key cross-domain relationships.
3. Event fabric handles append/replay/materialize/query.
4. WATCH surfaces meaningful review candidates.
5. ASK answers through sealed packets in the app.
6. CHECK validates every output type.
7. BRIEF exports evidence-backed packets.
8. RECALL retrieves field-computed precedent.
9. DIFF detects real source changes.
10. PERCEPTION emits candidate observations safely.
11. SPATIAL surfaces consume the same evidence packets.
12. PLAN/SCHEDULE propose options under authority.
13. Workflow supports hold/abstain/propose/approve states.
14. Governance trace and authority envelopes exist throughout.
```

---

## 11. Full vision completion map

Beyond Platform v1, the full portfolio includes:

```text
all core flows
multiple cities
department-local intelligence nodes
VSS/Metropolis production-grade media pipeline
Omniverse/OpenUSD hero-neighbourhood and larger twins
SUMO, energy, water, flood simulators
approved workflow adapters
cross-city federation
synthetic data factory
production security/RBAC
audit/observability
conditional autonomous workflows under policy
```

This is the long-term portfolio, not the near-term definition of done.

