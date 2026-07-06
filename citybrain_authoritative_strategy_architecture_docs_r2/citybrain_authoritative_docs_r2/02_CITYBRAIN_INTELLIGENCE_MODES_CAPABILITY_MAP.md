# CityBrain Intelligence Modes
## Capability, Data, Maturity, Gap Analysis, and Roadmap

**Status:** Authoritative capability map v2  
**Date:** 2026-07-05  
**Scope:** Defines every major CityBrain intelligence mode, how intelligence is calculated, what data/functions are needed, current maturity, gaps, and roadmap.


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

## 1. How to read this document

CityBrain has many “modes,” but they are not all the same kind of thing.

This document groups them into three layers:

### Operator / operations-facing modes

```text
WATCH       candidate attention queue
ASK         bounded cited question answering
CHECK       evidence sufficiency and claimability validation
BRIEF       evidence packet generation
RECALL      precedent and memory
DIFF        change review
PLAN        option and decision-support intelligence
SCHEDULE    resource and workflow sequencing
SPATIAL     map / Omniverse / GIS selection and overlay
WORKFLOW    human and governed workflow state
```

### System / reasoning modes

```text
IDENTITY      canonical entity resolution
GRAPH         semantic relationship and dependency reasoning
EVENT         event ingestion, state, and incident handling
PERCEPTION    media → candidate observations
SIMULATE      scenario/counterfactual modeling
OPTIMIZE      constrained option or schedule generation
GOVERN        authority, refusal, claim audit, trace
```

### Platform / commercial modes

```text
QUALITY / MATURITY    data quality and readiness diagnostics
FEDERATION            cross-city / cross-department intelligence
SYNTHETIC             gold/dirty/challenge/scenario test factory
PERSONA               evidence rendering for different users
```

Each mode below uses the same structure:

```text
1. What it is
2. Purpose
3. Why it is intelligence
4. How intelligence is calculated / decided
5. How it is served
6. Data and functions needed
7. Current maturity
8. Gaps
9. Roadmap
```

Maturity scale:

| Level | Meaning |
|---:|---|
| M0 | Concept only |
| M1 | Spec/artifact exists |
| M2 | Prototype proof works |
| M3 | Integrated into runtime/cockpit |
| M4 | Operator-useful in one real workflow |
| M5 | Production-ready / governed deployment |
| M6 | Approved execution and monitoring in live operations |

---



## 1A. R2 maturity corrections

R2 corrects several maturity claims:

- **ASK v1.1** is not merely “in design.” The sealed ASK v1.1 core and retained-real-corpus baseline are closed/published; the near-term work is app consumption and UX integration, not ASK core extension.
- **Perception / VSS / Metropolis** is not deferred anymore. It is a bounded local/replay candidate-observation lane with DeepStream runtime ready on `txr-4070`, VSS narrative smoke on Spark, and candidate review artifacts. It is still not production live CCTV.
- **Spatial / Omniverse** has a functional WebRTC/object-event review-loop proof, but finished native Kit UI and product UX remain incomplete.
- **CHECK** is the top dependency but must be split into v0 and v1.
- **Event fabric** must be split into v0/v1/v2 so the roadmap stays buildable.

## 2. IDENTITY Intelligence — “what is this thing?”

### What it is

IDENTITY is the Canonical Entity Registry and entity-resolution layer. It resolves messy source records into confidence-aware entities such as community, address, parcel, building, unit, road segment, service point, camera, incident, asset, party, organization, department, facility, system, component, and instrument.

### Purpose

Identity is the hard spine of CityBrain. Every other mode depends on it. If entity identity is unstable, graph reasoning, event resolution, spatial overlays, recall, scheduling, and CHECK all become unreliable.

### Why it is intelligence

Identity resolution is reasoning under ambiguity. It must operate when:

- IDs do not align.
- Names differ across Arabic/English/transliterations.
- Addresses are incomplete.
- Geometries conflict.
- Records duplicate.
- Source systems know different pieces of the same reality.
- Source IDs are not reliable enough to be absolute truth.

### How intelligence is calculated / decided

Identity scoring should combine:

```text
deterministic keys
  official IDs, plot IDs, meter IDs, permit numbers, camera IDs

alias and name logic
  normalized names, Arabic/English variants, transliteration variants, abbreviations

spatial relationships
  point-in-polygon, footprint overlap, centroid proximity, road adjacency

temporal relationships
  active windows, permit/inspection order, event/source freshness

probabilistic similarity
  fuzzy address match, name match, geometry similarity, co-occurrence

human review state
  verified, inferred, candidate, disputed, unresolved
```

A canonical entity should not be just one clean row. It should carry source links, aliases, attribute assertions, provenance, confidence, conflicts, candidate matches, evidence, quality score, and review state.

### How it is served

Identity is served as:

```text
EntityPacket
Entity360 answer
source-link panel
identity confidence report
match candidate queue
entity-quality score
spatial selection packet
```

### Data and functions needed

- CER tables/collections.
- Source entity registry.
- Alias resolver.
- Geometry resolver.
- Attribute assertions and conflicts.
- Confidence scoring.
- Match candidate queue.
- Review workflow.
- Entity quality tests.

### Current maturity

```text
M2 / M3 pattern maturity.
```

There are strong identity/provenance patterns and some city-specific entity work, but not yet a full cross-domain canonical registry engine across DM/DLD/RTA/DEWA or all target cities.

### Gaps

- Full canonical entity store across domains.
- Source entity and alias model.
- Attribute assertion model.
- Attribute conflict model.
- Human review lifecycle for entity matches.
- Entity quality scoring.
- Department-local registry slices.

### Roadmap

```text
R1  canonical entity contract v1
R2  source entity and alias model
R3  attribute assertion / conflict engine
R4  matching engine: deterministic + probabilistic
R5  match review workflow
R6  entity quality scorecards
R7  department-local slices
R8  federated entity registry
```

---

## 3. GRAPH Intelligence — “how is this connected?”

### What it is

GRAPH is the Semantic Entity Graph on top of the Canonical Entity Registry. It expresses relationships, dependencies, containment, adjacency, role assignments, and event/context links.

### Purpose

It lets CityBrain answer:

```text
What is nearby?
What depends on this?
What may be affected?
Why is this record connected?
Which paths explain the relationship?
```

### Why it is intelligence

A city record alone is shallow. A city record connected to building, parcel, road, service point, facility, responsible department, camera, event, and previous cases becomes actionable context.

### How intelligence is calculated / decided

Graph intelligence uses:

```text
containment edges
  community contains parcel, parcel contains building, building contains unit

adjacency edges
  road segment adjacent to parcel, work zone near access asset

service edges
  service point serves building, feeder supplies area

operational edges
  incident occurred_on road, camera observes zone, event affects candidate asset

role edges
  department manages road, organization operates facility, party owns unit

temporal validity
  active_from, active_to, superseded_by, current flag

confidence and review state
  direct, inferred, candidate, disputed, verified
```

### How it is served

```text
GraphContextPacket
relationship path explanation
candidate affected entities
dependency path
neighborhood summary
edge confidence report
spatial overlay context
```

### Data and functions needed

- Relationship ontology.
- Edge provenance.
- Edge confidence model.
- Temporal validity.
- Graph projection from CER.
- Path traversal.
- Cross-domain dependency rules.

### Current maturity

```text
M2.
```

Graph/context capability exists in parts, but semantic breadth is incomplete.

### Gaps

- Energy/water/transport dependencies.
- Service-point relationships.
- Asset-to-asset dependencies.
- Operational state edges.
- Cross-domain impact propagation.
- Shared confidence/review-state vocabulary.

### Roadmap

```text
R1  relationship ontology v1
R2  edge evidence and confidence model
R3  spatial relationship builder
R4  service/dependency builder
R5  event-to-entity edge builder
R6  GraphContextPacket v1
R7  cross-domain path explanation
R8  graph-to-spatial overlay
```

---

## 4. WATCH Intelligence — “what needs attention?”

### What it is

WATCH is a proactive attention queue. It surfaces candidate city situations for human or governed workflow review.

### Purpose

WATCH makes CityBrain active. It prevents the operator from having to ask first.

### Why it is intelligence

WATCH converts retained records, events, diffs, graph relationships, and candidate observations into salience: “this combination deserves attention.”

### How intelligence is calculated / decided

WATCH should run named query families such as:

```text
works_near_access_asset
incident_near_candidate_asset
source_depth_gap
low_confidence_link
stale_record
cross_source_conflict
similar_pattern_review
event_unresolved
perception_candidate_review
diff_changed_record_needs_review
```

Ranking should use:

```text
recency
source severity if present
evidence strength
corroborating record count
uncertainty class
affected asset count
source-depth gap severity
operator review state
authority level
```

### How it is served

```text
WatchCandidatePacket
ranked queue
why this needs attention
why ranked here
records on file
what may be nothing
suggested human check
attached CheckReport
```

### Data and functions needed

- Source records.
- Event state.
- DIFF outputs.
- Graph context.
- CHECK results.
- Perception candidate observations.
- Review state.
- Ranker.

### Current maturity

```text
M2 / shallow M3.
```

A small queue exists, but it remains shallow and demo-oriented.

### Gaps

- More query families.
- Event-driven queue items.
- Perception-driven queue items.
- DIFF-driven queue items.
- Multi-domain scoring.
- Operator feedback loop.

### Roadmap

```text
R1  WATCH query registry
R2  deterministic ranker v2
R3  event-driven WATCH
R4  CHECK-driven WATCH
R5  DIFF-driven WATCH
R6  perception-driven WATCH
R7  workflow feedback into ranker
R8  approved workflow trigger candidates
```

---

## 5. ASK Intelligence — “what do we know?”

### What it is

ASK is bounded question handling over retained evidence. It is not a generic chatbot.

### Purpose

ASK lets operators, analysts, agents, and future workflows request context, support, uncertainty, claimability, entity details, source records, queue state, and boundary answers.

### Why it is intelligence

ASK interprets messy language and maps it into a governed evidence path. The LLM may help as a reader/resolver and writer/renderer, but not as the truth engine.

### How intelligence is calculated / decided

The correct ASK architecture is an orchestrated flow:

```text
G1  boundary screen
G2  intent + concept binding resolver
G3  execution contract compiler
G4  argument resolution
G5  deterministic template/tool execution
G6  CHECK / evidence sufficiency
G7  answer assembly
G8  model-gated rendering
sinks: clarify / refusal / gap
```

ASK answer families include:

```text
subject answer
  support / uncertainty / claimability / summary lenses

entity profile
  entity_360

source record profile
  source_record_360

patch queue query
  counts / lists / filters / comparisons

external context need
  weather / live feed / external source missing

board/meta help
  what the board can and cannot do

refusal/boundary
  action, prediction, legal, identity, out-of-scope
```

### How it is served

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

### Data and functions needed

- Entity registry.
- Graph context.
- Source records.
- Template registry.
- Concept-binding registry.
- Evidence packet.
- CHECK.
- Clarify path.
- Refusal path.
- Trace store.

### Current maturity

```text
M3 for ASK v1.1 sealed implementation.
M2 for broader open/natural ASK.
```

Current ledger: ASK v1.1 is implemented, sealed, real-corpus evaluated, committed/published, and moving to app handoff preflight.

### Gaps

- ASK packets must be wired into the app/cockpit.
- CHECK must become explicit in the flow.
- Source-record profile questions need implementation.
- Patch queue query questions need implementation.
- Real operator corpus still needed for broader open ASK.

### Roadmap

```text
R1  ASK v1.1 app handoff preflight
R2  concept-binding registry seed
R3  CHECK gate integrated
R4  source-record profile answers
R5  patch queue query answers
R6  clarify UI
R7  broader natural router from real operator corpus
R8  ASK flow becomes reusable gate pattern for other modes
```

---

## 6. CHECK Intelligence — “is this supported enough to say?”

### What it is

CHECK is the evidence sufficiency, claimability, contradiction, freshness, source-class, and boundary validator for any output.

### Purpose

CHECK prevents CityBrain from sounding more certain than its evidence allows.

### Why it is intelligence

CHECK reasons about claims, evidence, source quality, temporal freshness, detection confidence, and authority. It is meta-intelligence over city intelligence.

### How intelligence is calculated / decided

CHECK evaluates:

```text
claim-to-evidence mapping
source class
source freshness
source ownership
confidence
corroboration
contradiction
coverage
inference class
candidate vs verified
single-frame vs corroborated detection
proximity vs causality
authority class
```

Useful result classes:

```text
SUPPORTED
SUPPORTED_WITH_LIMITATIONS
INSUFFICIENT_EVIDENCE
CANNOT_CLAIM
CONTRADICTION_FOUND
STALE_OR_UNKNOWN_FRESHNESS
CANDIDATE_ONLY
MODEL_INFERRED_ONLY
ABSTAIN_RECOMMENDED
AUTHORITY_BLOCKED
```

### How it is served

CHECK attaches to:

```text
ASK answers
WATCH items
BRIEF packets
RECALL matches
DIFF outputs
PERCEPTION candidate observations
SPATIAL selections
PLAN options
SCHEDULE proposals
SIMULATION outputs
```

### Data and functions needed

- EvidencePacket.
- Source class taxonomy.
- Provenance.
- Confidence metrics.
- Freshness metadata.
- Detection metadata.
- Contradiction pairs.
- Coverage metadata.
- Claim taxonomy.
- Authority envelope.

### Current maturity

```text
M1 / M2.
```

The idea is strong, but current implementation is thin.

### Gaps

- No full claim-to-evidence map.
- No robust contradiction engine.
- No detection-sufficiency checks.
- No universal source-class policy.
- No abstain policy.
- No mode-wide CHECK integration.

### Roadmap

```text
R1  CHECK contract v1
R2  source-class taxonomy
R3  claim-to-evidence mapper
R4  freshness and coverage checks
R5  contradiction detection
R6  perception/detection sufficiency checks
R7  abstain policy
R8  CHECK attached to all mode outputs
```

---



### CHECK v0 / CHECK v1 split

CHECK should not be delivered as one monolithic engine. R2 defines two increments:

**CHECK v0 — dependency unblocker**

```text
source_class present
valid_as_of / freshness present
candidate_vs_verified classification
sensor_inferred / model_inferred / official_record distinction
basic cannot-claim reason
basic missing-evidence reason
```

CHECK v0 is enough to attach a simple but honest CheckReport to ASK answers, WATCH items, BRIEF packets, VSS candidate observations, and Omniverse selections.

**CHECK v1 — full evidence engine**

```text
claim-to-evidence mapping
source-depth scoring
contradiction detection
multi-source conflict handling
coverage analysis
abstain recommendation
detection-confidence and false-positive class reasoning
```

Every dependent mode should state whether it requires CHECK v0 or CHECK v1. Most near-term app work should depend only on CHECK v0.

## 7. BRIEF Intelligence — “can I package this?”

### What it is

BRIEF composes evidence into a human-readable and machine-traceable packet.

### Purpose

BRIEF saves time and preserves auditability when operators, analysts, or decision owners need a packet.

### Why it is intelligence

BRIEF transforms raw evidence into structured operational understanding without inventing facts.

### How intelligence is calculated / decided

BRIEF should assemble:

```text
selected subject
EvidencePacket
CheckReport
GraphContextPacket
Recall snippets
Diff changes
Spatial references
Plan/Option packet
authority envelope
```

### How it is served

```text
operator brief
planner brief
executive brief
analyst appendix
local export packet
future approved-workflow attachment
```

### Data and functions needed

- Evidence bundle.
- CHECK report.
- Source records.
- Citations.
- Graph context.
- Recall snippets.
- Diff outputs.
- Review options.
- Renderer/persona templates.

### Current maturity

```text
M2 / early M3.
```

It works for some demo and non-story subjects but needs richer content and export quality.

### Gaps

- Briefs are too thin.
- Export is immature.
- Persona versions missing.
- CHECK not deeply integrated.
- Source-record profile sections incomplete.

### Roadmap

```text
R1  BriefPacket v2
R2  CHECK-integrated brief
R3  SourceRecordProfile section
R4  persona renderers
R5  local export + session link
R6  proposal/approval attachment later
```

---

## 8. RECALL Intelligence — “have we seen this before?”

### What it is

RECALL retrieves similar cases, events, observations, or prior decisions.

### Purpose

RECALL turns institutional memory into an active capability.

### Why it is intelligence

It identifies comparable prior situations using field-computed reasons, not generic semantic similarity alone.

### How intelligence is calculated / decided

Recall scoring should combine:

```text
issue type
asset type
source class
location/community/ward
building/road/parcel class
time proximity
source-depth similarity
review outcome
operator action/outcome if available
embedding similarity as secondary
```

### How it is served

```text
RecallPacket
similar cases
match reasons
weak-match warnings
prior cannot-claim
prior outcome / decision / action if available
```

### Data and functions needed

- Prior cases.
- Prior briefs.
- Prior watch candidates.
- Operator review states.
- Field-computed matchers.
- Optional embedding index.

### Current maturity

```text
M1 / M2.
```

Partial and promising, but generic match reasons are not enough.

### Gaps

- Precedent datasets thin.
- Match reasons not consistently field-computed.
- Weak-match labeling incomplete.
- Cross-city recall limited.

### Roadmap

```text
R1  Recall matcher contract
R2  Chicago/NYC/London precedent packs
R3  field-computed match reasons
R4  weak-match tests
R5  Recall inside ASK/BRIEF/WATCH
R6  cross-city recall
```

---

## 9. DIFF Intelligence — “what changed?”

### What it is

DIFF compares source-record and entity snapshots.

### Purpose

DIFF turns static records into temporal awareness.

### Why it is intelligence

It detects what deserves renewed attention because the underlying evidence changed.

### How intelligence is calculated / decided

```text
snapshot A vs snapshot B
record-level comparison
entity projection
change classification
CHECK freshness update
WATCH admission if important
```

Change classes:

```text
new_record
changed_record
removed_record
expired_record
status_changed
link_added
link_removed
evidence_strengthened
evidence_weakened
stale_source
```

### How it is served

```text
DiffPacket
change summary
changed records
changed entities
freshness warnings
WATCH candidates
brief section
```

### Data and functions needed

- Snapshot cadence.
- Comparable snapshots.
- Record versioning.
- Field-level diff rules.
- Entity projection.
- Designed-change golden tests.

### Current maturity

```text
M1 / M2.
```

Limited DIFF exists, but zero-change runs are not enough.

### Gaps

- Need positive designed-change test.
- Need real cadence.
- Need entity-level diff projection.
- Need Diff-to-WATCH and Diff-to-BRIEF integration.

### Roadmap

```text
R1  snapshot contract
R2  designed-change golden test
R3  record-level diff
R4  entity-level diff
R5  Diff-to-WATCH
R6  Diff-to-BRIEF
R7  real cadence
```

---

## 10. EVENT / INCIDENT Intelligence — “what happened?”

### What it is

EVENT/INCIDENT mode handles new events, current state, unresolved items, and candidate effects.

### Purpose

It moves CityBrain from static query to operational intelligence.

### Why it is intelligence

It links a new occurrence to entities, graph context, evidence, candidate impact, and response options.

### How intelligence is calculated / decided

```text
event append
schema validation
entity resolution
graph expansion
state materialization
CHECK validation
WATCH admission
BRIEF generation
PLAN/SCHEDULE trigger if authority allows
```

### How it is served

```text
EventPacket
IncidentPacket
active state view
unresolved event queue
quarantine queue
event overlay
incident brief
```

### Data and functions needed

- Event fabric.
- Event schema.
- Event-to-entity resolver.
- State materializer.
- Graph context.
- Evidence bundle.
- CHECK.
- Watch queue.

### Current maturity

```text
M1 / M2.
```

Missing/thin. Needs local event fabric.

### Gaps

- No complete append-only event log.
- No materialized current state.
- No event expiry/supersession.
- No event-state query API.
- Thin incident orchestration.

### Roadmap

```text
R1  EventPacket + append log
R2  event validation/quarantine
R3  event-to-entity resolver
R4  state materializer
R5  event query API
R6  event-driven WATCH
R7  incident mode orchestrator
R8  event-to-plan/schedule later
```

---



### Event Fabric v0 / v1 / v2 split

Event fabric is too large to ship as one deliverable.

**Event Fabric v0 — minimal operational nerve**

```text
one event type
append
basic schema validation
query by ID / time / subject
trace
no full materialized state yet
```

**Event Fabric v1 — local/replay event fabric**

```text
unresolved preservation
invalid-event quarantine
simple materialized state
replay over a bounded log
event-to-WATCH candidate admission
```

**Event Fabric v2 — operational state fabric**

```text
multi-source event ingestion
expiry/supersession
late/out-of-order handling
state API
runtime integration
Omniverse/WebRTC event overlays
```

Near-term work should aim at v0 first.

## 11. PERCEPTION / VSS / Metropolis Intelligence — “what does media suggest?”

### What it is

PERCEPTION converts media into candidate observations and candidate events.

### Purpose

Detect possible visual signals for human/agentic review without claiming a finding.

### Why it is intelligence

It extracts candidate signals from pixels and binds them to evidence, source, time, location, confidence, and review state.

### How intelligence is calculated / decided

```text
media source registry
frame/clip ingest
model inference / RT-VLM / DeepStream / Metropolis
zone logic
object/event candidate
confidence
source_class = sensor_inferred or model_inferred
CandidateObservation
EvidenceClip
CHECK detection sufficiency
CandidateEvent
```

### How it is served

```text
candidate observation card
evidence frame/clip
model provenance
confidence
human review state
event candidate
spatial overlay later
```

### Data and functions needed

- Licensed video/image.
- Camera registry.
- Timestamps.
- Location/camera calibration.
- Zone definitions.
- Model ID/version.
- Detection output.
- Clip/frame store.
- CHECK detection rules.

### Current maturity

```text
Current ledger: Metropolis/VSS closed at bounded proof level.
M2 / early M3 depending on exact runtime artifact.
```

Closed does not mean “citywide perception product.” It means the bounded candidate-observation lane has a proof and should now be integrated through EvidenceBundle/CHECK/Event/Spatial contracts.

### Gaps

- Broader class taxonomy.
- More video sources.
- Camera registry maturity.
- Zone calibration.
- Detection sufficiency CHECK.
- Privacy/identity boundary.
- Event fabric integration.
- Operator workflow integration.

### Roadmap

```text
R1  CandidateObservation contract
R2  one feed / one zone / one class proof
R3  evidence frame/clip retention
R4  detection sufficiency CHECK
R5  CandidateEvent handoff
R6  event fabric integration
R7  spatial overlay integration
R8  class/source expansion under guardrails
```

---



### R2 status update — bounded media lane and DeepStream runtime

Current state should be treated as **M2/M3 internal alpha for local/replay candidate-review**, not as production perception.

Latest proven facts:

```text
DeepStream runtime ready for CityBrain R9 local/replay on txr-4070.
Host: native Ubuntu Linux, Ubuntu 26.04 LTS, kernel 7.0.0-22-generic.
GPU visible on host and inside Docker: PASS, RTX 4070.
Docker: PASS, Docker 29.6.0, Compose v5.2.0.
NVIDIA Container Toolkit: PASS, nvidia-container-toolkit 1.19.1.
DeepStream image: PASS, nvcr.io/nvidia/deepstream:8.0-samples-multiarch.
deepstream-app --version-all: PASS, DeepStreamSDK 8.0.0, CUDA driver 13.2, CUDA runtime 12.9, TensorRT 10.9, cuDNN 9.8.
Sample file pipeline: PASS, exit code 0, Received EOS and App run successful.
```

Product interpretation:

```text
DeepStream = perception metadata engine.
Metropolis lane = governed media inference / candidate observation / evidence packet product lane.
VSS = narrative review assistance only, source_class model_generated_narrative, never truth by itself.
```

Still not proven:

```text
live RTSP camera onboarding
production camera registry
reviewer disposition lifecycle
validated privacy/legal posture
VSS quality benchmark at scale
full app-route integration
operational alerting/action loop
```

## 12. SPATIAL / Omniverse / GIS Intelligence — “where is it?”

### What it is

SPATIAL intelligence binds web, GIS, Omniverse, USD, scene objects, and event overlays to the same evidence truth.

### Purpose

Let operators reason about space without the spatial surface becoming a separate truth.

### Why it is intelligence

It joins geometry, selection, identity, source evidence, CHECK, and review state.

### How intelligence is calculated / decided

```text
object or map selection
entity/prim binding
canonical entity lookup
GraphContextPacket
EvidencePacket
CheckReport
ReviewState
SpatialSelectionPacket
overlay state
```

### How it is served

```text
web map
native Kit panel
WebRTC scene view
entity/evidence card
overlay labels
event markers
camera bookmarks
spatial brief section
```

### Data and functions needed

- GIS layers.
- USD/OpenUSD prims.
- Entity↔prim binding.
- Evidence packets.
- Event overlays.
- Review state.
- Web↔Kit/WebRTC sync.

### Current maturity

```text
Omniverse/WebRTC R5 closed at functional proof level.
M2/M3 for seam and stream proof.
M1/M2 for product-grade spatial UI.
```

### Gaps

- Native Kit panel product UI.
- Spatial workflow polish.
- Event overlays productized.
- Scene fidelity.
- Spatial CHECK labels.
- Operator task flow.

### Roadmap

```text
R1  native Kit entity/evidence panel
R2  overlay manager
R3  WebRTC embedded stream with selection sync
R4  event overlay integration
R5  spatial CHECK visibility
R6  operator spatial workflow
R7  hero-neighbourhood twin
```

---



### R2 status update — functional proof versus product UX

Spatial/Omniverse maturity must distinguish **functional proof** from **finished product UX**.

Closed proof:

```text
PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS
live WebRTC stream
real Barcelona scene references
scene prim selection parity
event overlay parity
object-event review loop
packet truth preserved
not_executed boundary preserved
```

Still parked:

```text
native Kit UI polish
overlay sizing / side rail / inspector layout
scene visual fidelity
operator workflow polish
production spatial UX
```

Spatial intelligence should now consume the same packet chain as web: EntityPacket, EvidencePacket, CheckReport, AuthorityEnvelope, and Trace. It should not invent a separate spatial truth model.

## 13. PLAN / Option Intelligence — “what could we do?”

### What it is

PLAN generates structured options and proposals.

### Purpose

Move from description to decision support and eventually approved execution.

### Why it is intelligence

It transforms evidence, constraints, risks, and goals into alternatives.

### How intelligence is calculated / decided

```text
situation state
constraints
allowed actions
do-nothing baseline
option generation
tradeoff axes
CHECK
approval requirement
authority envelope
```

### How it is served

```text
OptionSet
tradeoff table
proposal packet
abstain/no-safe-option
approval workflow
```

### Data and functions needed

- EvidencePacket.
- Graph context.
- Event state.
- Constraints.
- Policy rules.
- Simulation/optimization outputs.
- Authority model.

### Current maturity

```text
M1 / M2.
```

Some option-set/promotion work exists, but Plan mode is not mature.

### Gaps

- Option-set v2.
- Authority-aware proposal model.
- Simulation/optimization integration.
- Approval lifecycle.
- Monitoring after approved execution.

### Roadmap

```text
R1  Plan mode contract
R2  option generator from evidence
R3  abstain/no-safe-option policy
R4  simulation/optimization attachment
R5  approval workflow
R6  approved execution adapter later
```

---

## 14. SCHEDULE / OPTIMIZE Intelligence — “how should resources be sequenced?”

### What it is

SCHEDULE/OPTIMIZE sequences tasks, crews, closures, inspections, routes, or resources.

### Purpose

Support feasible planning and approved operational workflows.

### Why it is intelligence

It reasons over constraints, time windows, resource capacity, dependencies, and tradeoffs.

### How intelligence is calculated / decided

```text
task model
resource model
calendar/time windows
constraints
objective function
optimizer
CHECK
proposal / approval / execution state
```

### How it is served

```text
candidate schedule
constraint explanation
tradeoff summary
approval packet
execution plan under authority
```

### Data and functions needed

- Work orders.
- Inspections.
- Crews/resources.
- Road closures.
- Asset capacity.
- Calendars.
- cuOpt/scheduler.
- Authority envelope.

### Current maturity

```text
M1 / M2.
```

One optimization use case exists. Operational scheduling is not yet productized.

### Gaps

- Task/resource schema.
- Calendar integration.
- Constraint library.
- Approval model.
- Execution adapter.

### Roadmap

```text
R1  task/resource schema
R2  constraint contract
R3  cuOpt/scheduler integration
R4  schedule CHECK
R5  review/approval packet
R6  approved workflow execution later
```

---

## 15. SIMULATE Intelligence — “what might happen under assumptions?”

### What it is

SIMULATE runs counterfactual or scenario models.

### Purpose

Support Plan/Schedule decisions with modeled evidence.

### Why it is intelligence

It lets CityBrain compare possible futures under assumptions, while labeling uncertainty.

### How intelligence is calculated / decided

```text
scenario state
input parameters
simulator execution
calibration note
uncertainty
baseline comparison
CHECK
```

### How it is served

```text
SimulationResult
assumption sheet
uncertainty label
scenario chart/map
effect on options/schedule
```

### Data and functions needed

- SUMO / traffic.
- pandapower / energy.
- EPANET / water.
- Weather/flood.
- Asset dependency graph.
- Scenario state.

### Current maturity

```text
M0 / M1.
```

Mostly absent beyond limited optimization proof.

### Gaps

- No simulator stack integrated.
- No calibration contracts.
- No counterfactual CHECK.
- No simulation-to-plan integration.

### Roadmap

```text
R1  scenario contract
R2  SUMO first simulator
R3  energy/water later
R4  simulation-to-plan
R5  simulation-to-brief
R6  counterfactual CHECK
```

---

## 16. WORKFLOW / Operations State Intelligence

### What it is

Workflow state tracks how humans or governed agents process work.

### Purpose

Turn intelligence into accountable operations without losing state.

### Why it is intelligence

Workflow intelligence knows what was reviewed, what was asked, what was refused, what gaps remain, what was approved, what was executed, and what must be monitored.

### How intelligence is calculated / decided

```text
review verbs
agent run outcomes
mode-run traces
approval state
proposal state
execution state
monitoring state
abstain/hold/needs-source
```

### How it is served

```text
ReviewState
local notes
session summary
workflow timeline
proposal lifecycle
approval queue
execution/monitoring log later
```

### Data and functions needed

- Operator actions.
- Agent actions.
- Trace store.
- Authority envelope.
- Review state model.
- Workflow adapters later.

### Current maturity

```text
M2.
```

Prototype local state exists; real operator sessions and approved workflow model are pending.

### Gaps

- Real user workflow validation.
- Official/non-official boundary clarity.
- Approval lifecycle.
- Execution/monitoring states.
- Integration with official systems later.

### Roadmap

```text
R1  review state contract
R2  local notes/session summary
R3  non-official export
R4  real operator gate
R5  proposal/approval state
R6  approved execution adapter later
```

---

## 17. DATA QUALITY / Maturity Intelligence

### What it is

QUALITY/MATURITY diagnoses source data, entity fragmentation, relationship coverage, and readiness.

### Purpose

Turn CityBrain into a transformation engine for departments.

### Why it is intelligence

It tells a city why certain intelligence is blocked and what data improvement unlocks it.

### How intelligence is calculated / decided

```text
schema completeness
required field presence
duplicate detection
identity fragmentation
relationship coverage
spatial validity
temporal validity
freshness
source-system linkage
synthetic challenge performance
```

### How it is served

```text
maturity scorecard
gap dashboard
identity fragmentation report
relationship coverage report
source improvement backlog
```

### Data and functions needed

- All source systems.
- CER/SEG.
- Ingestion runs.
- Validation results.
- Synthetic gold/dirty/challenge sets.

### Current maturity

```text
M1 / M2 conceptually, weak product surface.
```

### Gaps

- No mature quality dashboard.
- No standard maturity scores.
- No department-specific improvement backlog.

### Roadmap

```text
R1  quality score model
R2  identity fragmentation report
R3  relationship coverage report
R4  freshness/coverage report
R5  department maturity dashboard
R6  improvement recommendation engine
```

---

## 18. FEDERATION Intelligence

### What it is

FEDERATION lets city-local and department-local intelligence nodes cooperate.

### Purpose

Enable cross-city and cross-department intelligence without forcing one global master database.

### Why it is intelligence

It reuses contracts and patterns while preserving local truth, provenance, confidence, and ownership.

### How intelligence is calculated / decided

```text
city-scoped canonical IDs
shared entity/relationship contracts
crosswalks
federated query envelopes
cross-city recall
maturity comparison
local-to-federated promotion rules
```

### How it is served

```text
federated query
cross-city recall
shared maturity dashboard
domain-pack portability report
```

### Data and functions needed

- Department-local registries.
- City-local graph slices.
- Shared ontology.
- Confidence/review-state compatibility.
- Cross-city source mappings.

### Current maturity

```text
M1 / M2.
```

Conceptually strong, implementation partial.

### Gaps

- Shared cross-city v2 contract.
- Federated query envelope.
- Domain-pack portability gates.

### Roadmap

```text
R1  city-scoped ID policy
R2  shared entity/relationship contract
R3  federated query envelope
R4  cross-city recall
R5  department-local node pattern
R6  city federation layer
```

---

## 19. SYNTHETIC / Scenario Intelligence

### What it is

SYNTHETIC provides gold, dirty source, challenge, and scenario data.

### Purpose

Develop, validate, demonstrate, and pressure-test CityBrain before real departmental data is complete.

### Why it is intelligence

It creates controlled worlds where truth is known and messiness is intentional.

### How intelligence is calculated / decided

```text
real spatial anchors
canonical gold truth
source-shaped projections
injected errors
challenge cases
scenario timelines
agent usefulness tests
```

### How it is served

```text
SyntheticDataPack
ScenarioPack
ChallengePack
validation suite
demo scenario
```

### Data and functions needed

- Real anchors where possible.
- Synthetic history generator.
- Source projection generator.
- Event/scenario generator.
- Validation harness.

### Current maturity

```text
M1.
```

Strategically defined, not yet complete as a full factory.

### Gaps

- No full gold/dirty/challenge/scenario packs.
- No mode-wide synthetic validation.
- No Dubai anchored pack fully assembled.

### Roadmap

```text
R1  real spatial anchors
R2  gold canonical dataset
R3  dirty departmental projections
R4  entity-resolution challenge set
R5  scenario packs
R6  full mode validation suite
R7  Spark/RTX performance pack
```

---

## 20. GOVERNANCE / Authority Intelligence

### What it is

GOVERNANCE manages authority, trace, refusal, approval, and execution boundaries.

### Purpose

Make CityBrain safe enough to evolve from evidence review into approved operations.

### Why it is intelligence

It lets the system know not only what is true, but what it is allowed to do.

### How intelligence is calculated / decided

```text
boundary classification
authority level
action-shaped command detection
claimability check
approval state
execution adapter policy
monitoring and rollback requirements
```

### How it is served

```text
AuthorityEnvelope
refusal
clarify
proposal
approval record
execution trace
monitoring state
```

### Data and functions needed

- Authority policies.
- Role/permission model.
- Workflow adapters.
- Approval lifecycle.
- Trace store.
- Audit logs.
- Guardrail tests.

### Current maturity

```text
M3 for no-action/boundary discipline.
M1/M2 for progressive authority and approved execution.
```

### Gaps

- Authority levels not yet implemented end-to-end.
- Approval/modify/reject lifecycle missing.
- Execution/monitoring adapters missing.
- Production auth/RBAC later.

### Roadmap

```text
R1  unified authority envelope
R2  no-action / proposal / approval states
R3  forbidden command rejection everywhere
R4  approval lifecycle
R5  approved execution adapter pattern
R6  monitoring and rollback
R7  production RBAC/security
```

---

## 21. Cross-mode dependencies

The modes should not invent separate packet shapes. The shared chain is:

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

Every mode should either consume or produce one of these.

---

## 22. Highest-priority gaps

### 22.1 CHECK contract

Without a real CHECK engine, CityBrain will overclaim as soon as data, media, and spatial complexity grows.

### 22.2 Event fabric

Without event state, the system remains a query/review prototype rather than operational intelligence.

### 22.3 CER/SEG v2

Without a stable identity and relationship spine, agents and modes will drift.

### 22.4 Agentic scout layer

Without agents, modes remain passive features rather than active intelligence.

### 22.5 App handoff

ASK v1.1 must now be wired into cockpit/app surfaces rather than extended in isolation.

### 22.6 Progressive authority

Without authority model, the system is trapped in review/proposal mode.

---

## 23. Final intelligence definition

CityBrain intelligence is the composition of:

```text
identity under ambiguity
+ semantic relationships
+ operational events and changes
+ candidate media observations
+ evidence packets
+ CHECK claimability
+ governed orchestration
+ specialist agents
+ spatial grounding
+ planning/scheduling/simulation
+ progressive authority
```

That is the complete capability map.

