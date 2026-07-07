# TXR City Brain — Platform v1 Definition of Done

**Document 3 of 4** · *Companion docs: 01 Current Certified State · 02 Application Snapshot DoD · 04 Full Vision Completion Map*

**Acceptance gate:** `PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT` achieved 2026-06-28
**Document purpose:** Record the Platform v1 definition of done and the achieved review-only snapshot. Platform v1 makes TXR City Brain a *platform* rather than only a demonstration: it exercises every review-only layer of the architecture at least once on a connected runtime path and surfaces multiple cognition modes/personas through the same governance discipline.

**How to maintain this document:** This document is now achieved for the review-only PV1 snapshot. Future changes should be recorded as post-PV1 addenda or a deliberately named Platform v1 R1/R2 snapshot, not by silently rewriting the original D19-D22 freeze. Items that are *beyond* Platform v1 live in doc 04 — the boundary between this doc and doc 04 is the load-bearing line that prevents over-scoping.

**Important framing:** Platform v1 ≠ "everything in the architecture." Platform v1 = "every layer of the architecture has at least one real, connected, gated path; every flow family the original roadmap requires is represented; the governance discipline holds at scale." It is the **G4 bar from the original roadmap**, made explicit and testable.

---


## 0. Status update — Platform v1 achieved as review-only snapshot

```text
PV1-D19/D20/D21/D22  GREEN
PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT
```

PV1 is now closed as a **review-only platform snapshot**.

**Final D19–D22 counters:**

```text
D19 action policy: PASS
D20 guardrail harness: PASS
D21 composite snapshot: PASS
D22 final audit: PASS

Forbidden actions blocked: 20/20
Allowed review actions allowed: 4/4
Claim misuse blocked: 4/4

Accepted flows indexed: 8
Review-route-ready flows indexed: 5
Candidate-only flows indexed: 3
Data-route-ready rows indexed: 7

No-overclaim: PASS
No-mutation: PASS
Hashes: PASS
```

**Newly load-bearing D19/D20 rule:**

```text
No LLM controls actuators.
No model emits operational commands.
No review route becomes control.
Only deterministic, policy-bound, certified adapters may ever sit near actuators,
and only inside a future safety case.
```

**PV1 boundary:** this is not production control, autonomous operation, emergency dispatch, public-safety instruction, enforcement, utility/traffic/transit/port/airport control, health determination, or certified affected-asset/building truth.

**Track 2 status consumed by PV1:** `FLOWX-DATA-ROUTE-CATALOG-R1 + TARGETED D3-R2` is green. The snapshot indexes 7 data-route-ready rows and 5 review-route-ready-not-accepted lanes. New Track 2 accepted flows remain 0. BARC-F7 remains candidate-only and blocked by Barcelona city-core.

**Optional post-PV1 addendum:** `FLOWX-REVIEW-FLOW-ACCEPTANCE-D1` may later resolve the 5 review-route-ready lanes into `ACCEPTED_REVIEW_FLOW` or `ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS`; it must not mutate this PV1 freeze.


## 1. The seven completion criteria

Platform v1 was considered done when all seven of these held:

| # | Criterion | Single sentence |
|---|---|---|
| 1 | **Multi-city** | 2–3 accepted city cores with native IDs, source ledgers, face/NIM routes, and limitations preserved |
| 2 | **Multi-flow** | 3–4 flow families certified as sub-cartridges mounted onto accepted city cores |
| 3 | **Multi-mode cognition** | Query mode strong; Incident mode and Plan mode each demonstrated end-to-end at least once |
| 4 | **Persona surfaces** | 4 SOUL personas (executive / planner / operator / analyst) rendering the same EvidenceBundle |
| 5 | **Live event fabric** | L4 is a real append/replay event stream with at least one live or simulated temporal input |
| 6 | **At least one domain simulator** | One of SUMO / pandapower / EPANET genuinely wired into the cognition loop |
| 7 | **Approval lifecycle** | HITL approval gates surfaced in the UI with full approve/reject/modify lifecycle on consequential actions |

Each criterion expands below with specific acceptance tests.

---

## 2. Criterion 1 — Multi-city (2–3 cities)

**Target:** Accepted city cores for NYC, London, and Chicago. Singapore remains a planned Flow 4/API donor until authenticated live API proof clears. Barcelona is a fresh city-core scout candidate, not a mounted expansion yet.

**Why a third city matters:** Two cities prove the spine can take a different identity backbone. A third city proves the spine handles a *third structurally different* data ecosystem — different native IDs, civic sources, source limitations, face routes, and claim boundaries.

**Acceptance tests:**
- Each city core has its own canonical adapter set, same schema v1, same harness pattern
- Each city's identity backbone is preserved as authoritative primary (BBL/BIN for NYC, UPRN/TOID/USRN for London, Chicago-native civic/geographic IDs for Chicago)
- Each city core has at least one accepted hero/freeze package with named real-world or bounded public-source subjects
- Each city has its own face-layer instance (or shared face layer with city selector)
- The same a2 harness runs on each city's canonical entities — with documented and gated compatibility-harness treatment where ontology v2 is needed
- Cross-city federated query *contract* exists (federated, not unified — city-scoped IDs preserved per the architecture's intent)
- New flow work uses `{CITY}-F{FLOW}X-D{DAY}` when it mounts onto an accepted city core

**Out of scope for Platform v1 (in doc 04):** all 7 cities the original roadmap names, full Overture-grounded aliasing across cities, advanced cross-city analytics, and treating Barcelona as accepted before a core exists

---

## 3. Criterion 2 — Multi-flow (3–4 flow families)

**Accepted flow coverage:**

| Flow slot | Domain | City core | Current status |
|---|---|---|---|
| Flow 2 | Construction compliance cascade | NYC | Accepted deep, citywide (doc 01) |
| Flow 2 | Construction compliance cascade, second city | London | Accepted with D13C + LON-HERO (doc 01) |
| Flow 3 | Incident / response / affected-context | NYC | Accepted with full-source inputs and stage limitations (F3-NYC-D9FULL) |
| Flow 1 | Situational status | Chicago | Accepted as part of CHI-F1F7-D5 with capped-source limitations |
| Flow 7 | Civic service + sensor fusion | Chicago | Accepted as part of CHI-F1F7-D5 with capped-source limitations |

**Next flow sub-cartridge expansion lane:**

| Expansion scout | Domain | City core | Candidate strength |
|---|---|---|---|
| `LON-F3X-D1` | Resilience / fire-incident context | London | Very high |
| `LON-F4X-D1` | Mobility / environment | London | Very high |
| `LON-F5X-D1` | Flood / climate risk context | London | High |

**Why this order:** The platform has enough accepted breadth to stop rebuilding city cartridges. The highest-leverage next work is to mount new flow sub-cartridges onto the accepted London core. Flow 3 adds LFB incident/mobilisation, TfL status/disruption, London Air, and affected-context EvidenceBundles. Flow 4 adds mobility/environment context over TfL and air-quality feeds. Flow 5 adds flood/water-level/climate-risk context with explicit no-overclaim boundaries.

**Acceptance tests:**
- Each flow has its own scenario script and narrative
- Each flow uses the same EvidenceBundle pattern, the same grounded-narration gates, the same provenance + confidence discipline
- Each flow has at least one real hero/freeze scenario with named or bounded public-source subjects and a credible cascade
- The city-core + flow-sub-cartridge pattern is demonstrated as the only thing that changes between mounted flows
- A new flow can be scoped by a description in plain English, then implemented by following the documented slotting pattern
- Expansion names use `{CITY}-F{FLOW}X-D{DAY}` when the city core already exists

**Honest framing:** London is accepted today as Flow 2, not Flow 3/4/5. `LON-F3X-D1`, `LON-F4X-D1`, and `LON-F5X-D1` are expansion scouts that must add their own source ledgers, joins, EvidenceBundles, replay/live proof, and hero/freeze gates. They inherit London's IDs, geography, evidence style, face/NIM conventions, and limitations; they do not inherit acceptance.

**Out of scope for Platform v1 (in doc 04):** Flow 6, oil & gas cartridge, all 7 cities, certified infrastructure failure propagation, autonomous emergency dispatch, public-order instruction, and any Singapore Flow 4 acceptance before authenticated live API proof clears

---

## 4. Criterion 3 — Multi-mode cognition

**Target:** Query mode, Incident mode, and Plan mode each demonstrated end-to-end at least once.

### 4.1 Query mode — already strong
Per doc 01. No further work needed for Platform v1.

### 4.2 Incident mode — reactive: detect → understand → alert → action core → fix

**What this requires:**
- A real-time or simulated event input (from L4 or L7 — see criteria 5 and the perception path below)
- An event-to-canonical-entity resolver
- A trigger that fires when an event matches a category of concern (e.g., a PPE-missing detection at a building with an active scaffold permit)
- A briefing that says: *"At {time}, a {category-91} site condition was detected at {building} via {perception source}. The building has an active permit {permit_id} issued to {contractor}. Recommend: dispatch a review."*
- A routing recommendation from cuOpt for the review
- The same governed narration discipline as Query mode

**Acceptance test:** an event drops in, the briefing is produced within bounded latency, the recommended review is routable, the trace shows what fired and why, the governance gates hold throughout.

### 4.3 Plan mode — proactive: plan → action core → execute → monitor

**What this requires:**
- A planning agent that takes a goal (e.g., "next week's optimal review schedule given current open complaints, contractor patterns, and team capacity") and produces a multi-step plan
- The plan is executed through the existing optimiser (cuOpt) + the new approval lifecycle (criterion 7)
- A monitor loop that compares actual outcomes against planned outcomes and surfaces drift
- The monitor loop feeds back into the cognition core for the next planning cycle

**Acceptance test:** a planning request produces a multi-step plan with explicit dependencies, the plan executes through approved actions, the monitor surfaces what happened against what was planned.

### 4.4 The full 9-stage orchestration (RECALL → … → COMPLETE)

**Important sequencing decision:** the full 9-stage runtime is built *when* Incident and Plan modes create real stage responsibilities — not built ahead of time to satisfy the architecture diagram. The migration from the current lean oracle to the full stage machine is a deliberate architectural move, not organic complexity creep.

**The 9 stages, when they earn their place:**
- RECALL — retrieve canonical entities + history relevant to subject
- PLAN — produce candidate plan
- VALIDATE_PLAN — gates fire before execution
- EXECUTE — call the right deterministic tool
- NORMALIZE — canonical-form the outputs
- SYNTHESIZE — combine evidence
- RESOLVE_ACTIONS — closed-enum action resolver (a5·D8a)
- SUGGEST — produce briefing
- COMPLETE — emit trace, log, hand off

**Acceptance test:** every stage has real work in at least Incident or Plan mode (not ceremonial pass-through).

### 4.5 Forward and inverse dynamics

**Forward dynamics** (predict what happens next): integrated when a domain simulator (criterion 6) is wired and Plan mode uses it for rollouts.

**Inverse dynamics** (given a desired state, what action produces it): integrated when cuOpt + the simulator are wired together in a "given goal state, search backward over action space" pattern.

**Acceptance test:** at least one demonstrated forward rollout ("if we do this, the model predicts that") and one demonstrated inverse search ("we want this outcome, the system proposes this action") within Plan mode.

---

## 5. Criterion 4 — Persona surfaces (4 SOUL personas)

**Target:** Executive, Planner, Operator, and Analyst renderings of the same EvidenceBundle.

**Implementation pattern (per the architecture critique):** Personas are *rendering policies* over a single EvidenceBundle, not four autonomous agents. This keeps governance in one place and avoids over-decomposition.

**Acceptance tests:**
- The same hero cascade narrated by each of the four personas produces four distinct briefings with distinct tone, distinct depth, and distinct action emphasis
- Each persona's briefing passes the same subset-grounded / anti-echo / min-coverage / subject-isolated gates
- The boundary statement appears in every persona's briefing in form appropriate to that persona
- A reviewer can switch personas in the UI and see the same evidence rendered four ways

**Personas concretely:**
- **Executive** — 3–5 sentences, high-level impact, focused on what to approve, dollar / risk framing
- **Planner** — district-level patterns, capacity implications, week-ahead recommendations
- **Operator** — block-level specifics, names, contractor history, immediate review candidates
- **Analyst** — full evidence chain, statistical context, dataset boundaries, comparable cases

---

## 6. Criterion 5 — Live event fabric (L4 made real)

**Target:** L4 is a real append/replay event stream with at least one live or simulated temporal input.

**What "real" means here:**
- Append/replay event stream with event-time and processing-time semantics
- Current-state materialization (the system can answer "what is the state of this entity now")
- At least one continuous-signal stream (traffic OR meter curves OR air quality — one is enough for Platform v1)
- Late/out-of-order event handling
- Event-to-entity resolution against L2 canonical IDs
- Event expiry / supersession logic
- Replayable scenario packs (the synthetic-data documents describe these — they are the test-and-demo input)

**Acceptance tests:**
- A scenario pack replays into the system, events resolve to canonical entities, the system's view of "current state" updates correctly
- Out-of-order events handled correctly (verified by a deliberately-shuffled replay)
- The same scenario pack can be replayed twice and produces byte-stable outputs (determinism)
- At least one Incident-mode demonstration uses this fabric as its input

**Out of scope for Platform v1 (in doc 04):** full multi-stream signal ingestion, real-time IoT integration, multi-region event distribution

---

## 7. Criterion 6 — At least one domain simulator wired

**Target:** SUMO (traffic), pandapower (grid), or EPANET (water) wired into the cognition loop and calibrated to donor-city data.

**Recommended choice: SUMO.** It directly strengthens Flow 2 (construction-compliance impacts traffic), Flow 3 (resilient city: fire + road + air — road is SUMO), and Flow 4 (crowd surge). Highest leverage per simulator-wired.

**Acceptance tests:**
- SUMO (or chosen simulator) runs calibrated to at least one city's real road network (NYC or London)
- The simulator's output (e.g., predicted travel times, congestion patterns) flows into the cognition core as an input alongside graph and event-fabric data
- At least one demonstrated forward rollout uses the simulator
- The simulator's outputs are honestly labelled `[S]` (simulated) in every briefing that uses them
- The simulator integration follows the cartridge pattern — adding a different simulator (pandapower, EPANET) follows the same shape

**Out of scope for Platform v1 (in doc 04):** all three simulators wired, Cosmos rollouts, custom domain simulators per flow

---

## 8. Criterion 7 — Approval lifecycle and HITL

**Target:** Explicit approval object, approve/reject/modify lifecycle, surfaced in the UI on consequential actions.

**Why this matters:** the current system is review-only — it suggests reviews, never enforces. As soon as Incident mode or Plan mode produces *consequential* action proposals (e.g., dispatch a crew, issue a notice, reroute traffic), the architecture requires a HITL gate. Platform v1 makes this real.

**Acceptance tests:**
- An action-proposal data model exists with states {proposed, under_review, approved, rejected, modified, executed, monitored}
- The UI surfaces pending action proposals with full context (the EvidenceBundle that produced them)
- Approving a proposal triggers execution through an adapter (initially: write to a workflow system, not autonomous enforcement)
- Rejecting or modifying logs the reason, the proposal returns to the cognition core for re-planning
- An audit log records every approval, rejection, modification, and execution outcome
- NeMo Guardrails are proven active on consequential-action paths (extension of the live guardrail gate from doc 02)
- Monitor loop: after approved action, the system tracks the actual outcome against the predicted one

**Honest framing of "act":** "Act" never means autonomous enforcement. It means *create action proposal → request approval → execute approved workflow through adapter → monitor outcome*. The architecture explicitly preserves human review between AI proposal and official action.

---

## 9. Cross-cutting work for Platform v1

### 9.1 Cross-city ontology v2 (L2 reconciliation)

**Target:** A v2 ontology that resolves the differences exposed by multi-city work:
- Durable distinction among `addressable_location / parcel / building / unit`
- RoadLink relationship (London exposed it, NYC didn't need it; v2 includes it)
- Federated query contract (city-scoped IDs preserved, cross-city queries possible)
- Authoritative jurisdictional IDs preserved as primary; Overture / cross-source IDs added as **aliases** (never replacements)

### 9.2 Object-tagging agent + Omniverse twin (hero-neighbourhood)

**Target:** A hero-neighbourhood OpenUSD scene with BIN-tagged objects bound to canonical entities — the 3D ↔ graph bridge.

**Why hero-neighbourhood, not citywide:** Per the architecture critique, citywide twin first would be expensive visual mass without enough intelligence value. Hero-neighbourhood first proves the binding contract, then selective expansion follows.

**Progression:**
1. Hero-neighbourhood (MN-1060) OpenUSD scene from real footprints + heights
2. BIN/entity binding (each OpenUSD prim carries its canonical_id)
3. Graph-to-USD status overlay (color a building by compliance state)
4. One event/route animation (cuOpt route renders in the 3D scene)
5. Performance and authoring gate
6. Selective district/city expansion

### 9.3 Minimum perception path (L7 runtime)

**Target:** The off-the-shelf PPE-detection path scoped earlier:
- Pre-trained YOLO/PPE model (Apache 2.0)
- Triton Inference Server on the 4070
- Detections: person, no-hardhat, no-vest, person-count-on-scaffold
- Output: structured event JSON
- Event JSON resolves to canonical Event in L2
- Event lands in L4 event fabric
- Event triggers Incident mode in L5

**Governance principle:** Perception produces *candidate observations*, never final legal violations. Officer review remains between AI detection and any official action.

### 9.4 Agent roster expansion (per the architecture critique's pragmatic shape)

**Target architecture:**
- 1 supervisor
- 1 governed oracle runtime (extended for Incident + Plan)
- 1 domain-policy registry per cartridge
- Tool functions/services (graph query, retrieval, simulation, vision, optimiser, forecasting)
- 1 briefing renderer with persona policies
- 1 governance middleware

Not "one independently autonomous model instance per architecture row." LangGraph is introduced when inspectable multi-step branching genuinely exceeds what the oracle's state machine can express — not to tick a box.

### 9.5 Retrieval layer (cuVS / NeMo Retriever)

**Target:** A retrieval layer the cognition core can call as a tool. Used for: regulation/document retrieval, similar-case lookup, comparable-cascade pattern matching. `[I]` or `[A]` per architecture mapping.

---

## 10. What Platform v1 does NOT include

To be read alongside this doc — every item below is honestly beyond Platform v1 and tracked in doc 04:

- Flows 4, 5, 6
- Dubai re-anchor cartridge (Phase-2 work)
- Oil & gas cartridge
- 4–7 cities (Platform v1 caps at 2–3)
- Cosmos rollouts (Predict + Transfer) — note: minimum viable Cosmos integration via post-training or cloud pipeline could fit Platform v1 if scoped tightly; full long-tail integration is doc 04
- NeMo Curator
- Full Metropolis / DeepStream / VSS pipeline (Platform v1 has the minimum viable PPE path)
- grounding-dino open-vocabulary detection
- Earth-2 / CorrDiff
- Citywide OpenUSD twin (Platform v1 has hero-neighbourhood + selective expansion)
- All three domain simulators wired (Platform v1 has one)
- Asset-dependency edges in the graph at full architecture scope
- Full multi-region / multi-tenant operational concerns
- Per-flow custom domain simulators beyond the one in criterion 6

---

## 11. Acceptance: how to know Platform v1 is done

A simple, multi-test:

**The sub-cartridge author test:**
A new cartridge author, given a flow description in plain English and an accepted city core, can produce a green city-flow sub-cartridge by following the documented slotting pattern, in under 2 weeks of focused work. If they have to rebuild the city core, the spine is not a platform yet.

**The cognition-mode test:**
A reviewer can pick any of the 3–4 certified flows, and within each flow ask:
- "Tell me what's going on" (Query) → grounded briefing
- "An event just happened — what should we do" (Incident) → resolution + recommended action + cuOpt routing
- "Plan our next week's reviews given current open complaints" (Plan) → multi-step plan with simulator-informed rollout

…and all three respond with the same governance discipline.

**The persona test:**
The same hero cascade rendered through Executive, Planner, Operator, Analyst — four distinct briefings, same evidence, same gates, same boundary statements.

**The city-core test:**
A reviewer can pick NYC, London, or Chicago and verify: same a2 harness pattern, different native identity backbone, accepted source ledger, face/NIM route convention, and mounted flow evidence that carries limitations forward.

Those tests are now represented in the D19-D22 review-only snapshot. Any later acceptance-flow changes should be captured as post-PV1 addenda or a deliberate PV1 R1/R2 snapshot.

---

## 12. The honest framing for reviewers post-Platform-v1

After Platform v1, the elevator pitch shifts from:

> "Here is a re-platformed and generalized City Brain on NVIDIA's stack, demonstrated on NYC and London construction-compliance."

to:

> "TXR City Brain is a governed cross-domain reasoning platform. It runs on NVIDIA's stack, exercises every layer of the architecture on real data, supports query / incident / plan modes through one governance discipline, renders evidence to four operational personas, and is deployed across accepted city cores with mounted flow sub-cartridges. Adding a fifth flow means mounting a sub-cartridge, not rebuilding the city."

That sentence is the Platform v1 elevator pitch. It is materially different from the Application Snapshot pitch in doc 02 — and that difference is the point.

---

*End of doc 03. See doc 04 for the full vision completion map — the outer boundary of the architecture's ambition, explicitly framed as the longest horizon.*
