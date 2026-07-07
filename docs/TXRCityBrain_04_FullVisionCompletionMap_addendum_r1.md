# TXR City Brain — Full Vision Completion Map

**Document 4 of 4** · *Companion docs: 01 Current Certified State · 02 Application Snapshot DoD · 03 Platform v1 DoD*

**Document purpose:** Define the outer boundary — what *everything* in the architecture and the original Vision/Roadmap looks like fully realized. This is the **longest horizon**, not the near target. The Application Snapshot (doc 02) and Platform v1 (doc 03) are the credible product finish lines; this doc is the architecture's outermost ambition with claim labels honest about which components are unbuilt today.

**How to read this document:**
- This is a *map*, not a *plan*. Items here are listed for architectural completeness, not for immediate scheduling.
- Every item is labelled with its current state (mostly `[P]` today) and the level at which it would normally close (Platform v1, Platform v2, or Full Vision).
- The dependency-ordered build sequence at the end is the *technical* ordering — not a timeline commitment.
- The boundary between this doc and doc 03 is load-bearing. If something belongs in Platform v1, it lives in doc 03, not here.

**What this document is NOT:**
- It is NOT a near-term roadmap.
- It is NOT a definition of done for the application snapshot or the platform.
- It is NOT a commitment that all 7 flows will be built. The original roadmap's G4 explicitly does not require all 7 flows.
- It IS an honest mapping of every architecture promise to its current state, so nothing claimed in the architecture goes invisibly unbuilt.

---

## 1. Reading guide — which level does each item close at

| Level | Definition |
|---|---|
| App Snapshot | Doc 02 — the near-term shippable finish line |
| Platform v1 | Doc 03 — the credible product finish line (2–3 cities, 3–4 flows, multi-mode, one simulator, one persona set, live event fabric, approval lifecycle) |
| Platform v2 | A future credible platform expansion — broader flow coverage, broader simulator coverage, deeper perception, federated cross-city |
| Full Vision | The outer boundary — full 7-flow portfolio, all named NVIDIA components, advanced frontier capabilities |

Most items in this doc close at Platform v2 or Full Vision. Items that close at App Snapshot or Platform v1 appear here only for completeness and are cross-referenced.

---

## 2. Layer-by-layer — every architecture promise mapped

### L1 · Ingestion & adapters

| Capability | Current state | Closes at |
|---|---|---|
| NYC adapters (PLUTO, DOB, footprints, 11 datasets) | `[I]` per doc 01 | App Snapshot |
| London adapters (UPRN, TOID, USRN, PLD, LIDS, Local Plan, TOID geometry, EV context, enforcement-identity) | `[I]` accepted Flow 2 city core — full London-scale chain D4-D13c + LON-HERO | App Snapshot |
| Chicago city-core adapters and Flow 1/7 public-source line | `[I]` accepted with capped-source limitations (CHI-F1F7-D5) | Platform v1 |
| Overture Maps base-layer adapter | `[P]` | Platform v2 |
| Microsoft Building Footprints (global) adapter | `[P]` | Platform v2 |
| WorldPop adapter | `[P]` | Platform v2 |
| ERA5 weather/climate adapter | `[P]` | Platform v2 |
| GTFS transit-feed adapter | `[P]` | Platform v1 (for Flow 3 / mobility flows) |
| BIM / IFC building-interior adapter | `[P]` | Full Vision |
| Document-text adapter (permit PDFs, regulations) | `[P]` | Platform v2 |
| Per-flow sub-cartridge adapters for London Flow 3/4/5 and future Flow 6 | `[P]` | Platform v1 → Full Vision |

**Honest note on base layers:** Overture, MS footprints, WorldPop, ERA5 are cross-city base layers. They become valuable when 4+ cities exist and a shared global grounding is needed. They are not blockers for the App Snapshot or Platform v1.

---

### L2 · Canonical entity registry

| Capability | Current state | Closes at |
|---|---|---|
| Schema v1 (8 core + 5 reserved entities, identity triad, ID format) | `[I]` complete | App Snapshot |
| NYC + London + Chicago city-core identity/source coverage | `[I]` with Chicago source limitations carried forward | App Snapshot → Platform v1 |
| Cross-city ontology v2 reconciliation | `[P]` — addressable_location / parcel / building / unit distinction, RoadLink relationships, federated query contract | Platform v1 |
| Authoritative jurisdictional IDs preserved as primaries with aliases for Overture / cross-source IDs | `[P]` — design decided, not implemented | Platform v2 |
| Federated query layer across cities (city-scoped IDs preserved, not a forced global master) | `[P]` | Platform v2 |
| Activation of 5 reserved entities with real data: | | |
| — Unit (residential dataset) | `[P]` | Platform v1 (for Flow 7 / residential-driven flows) |
| — Development | `[P]` | Platform v2 |
| — Sensor (IoT / camera feed) | `[P]` | Platform v1 (for Flow 7 / sensor fusion) |
| — InfrastructureAsset (utility GIS) | `[P]` | Platform v1 (for Flow 5 / asset cascade) |
| — TransitNode (GTFS) | `[P]` | Platform v1 (for Flow 3 / mobility) |

**Critical correction (from the critique):** Cross-city completion does **not** mean "the same building has one ID across cities" (those are physically different buildings). It means same entity contract, same identity rules, same provenance envelope, same confidence policy, same resolution semantics, with city-scoped canonical IDs and a federated query layer. The architecture explicitly favours department-local and city-local intelligence with federation, not a forced global master database.

---

### L3 · Multiplex semantic graph (cuGraph)

| Capability | Current state | Closes at |
|---|---|---|
| Citywide cuGraph projection (NYC, 7.3M nodes / 9.6M edges) | `[I]` | App Snapshot |
| London graph projection | `[I]` closed — accepted graph 7,734,960 nodes / 10,664,896 edges, 0 missing endpoints | App Snapshot |
| Third-city graph projection | `[P]` | Platform v1 |
| Energy dependency edges | `[P]` | Platform v2 |
| Water dependency edges | `[P]` | Platform v2 |
| Transport dependency edges | `[P]` | Platform v1 (for Flow 3) |
| Asset-to-asset dependency edges | `[P]` | Platform v2 (for Flow 5 / asset cascade) |
| Service-point relationships | `[P]` | Platform v2 |
| Operational-state change tracking on graph | `[P]` | Platform v1 (depends on live event fabric) |
| Cross-domain impact propagation reasoning | `[P]` — promised by architecture, requires dependency edges first | Platform v2 |
| Centrality + shortest-path queries at production scale | `[I]` for connectivity + SSSP per doc 01; broader use cases `[P]` | Platform v1 |

**Honest framing:** The graph engine is strong; the graph's *semantic breadth* is what's missing. Construction-compliance semantics are deep. Cross-domain (energy, water, transport, asset) semantics are largely absent because the data isn't ingested yet.

---

### L4 · Observation / event fabric

| Capability | Current state | Closes at |
|---|---|---|
| Historical events (DOB complaints, permits) as Events | `[I]` (but these are records, not a fabric) | App Snapshot |
| Append/replay event stream with event-time + processing-time semantics | `[P]` | Platform v1 |
| Current-state materialization | `[P]` | Platform v1 |
| One continuous signal stream (traffic OR meters OR air quality) | `[P]` | Platform v1 |
| All three continuous signal streams | `[P]` | Platform v2 |
| Late / out-of-order event handling | `[P]` | Platform v1 |
| Event-to-entity resolution against L2 canonical IDs | `[P]` | Platform v1 |
| Event expiry / supersession logic | `[P]` | Platform v1 |
| Replayable scenario packs | `[P]` | Platform v1 |
| Multi-stream / multi-region event distribution | `[P]` | Platform v2 |
| Live real-time IoT integration | `[P]` | Full Vision |

---

### L5 · Cognition engine

| Capability | Current state | Closes at |
|---|---|---|
| Governed deterministic oracle (code computes, model narrates) | `[I]` per doc 01 | App Snapshot |
| EvidenceBundle + grounded narration (subset-grounded / anti-echo / min-coverage / subject-isolated) | `[I]` | App Snapshot |
| Live NIM in the loop with NeMo wrapper | `[I]` | App Snapshot |
| Citywide live + precomputed briefings | `[I]` | App Snapshot |
| Query mode | `[I]` | App Snapshot |
| Incident mode (reactive: detect → understand → alert → action core → fix) | `[P]` | Platform v1 |
| Plan mode (proactive: plan → execute → monitor) | `[P]` | Platform v1 |
| Forward dynamics (predict what happens next) | `[P]` | Platform v1 (in Plan mode with simulator) |
| Inverse dynamics (given desired state, search for action) | `[P]` | Platform v1 (in Plan mode with simulator + cuOpt) |
| Monitor loop (track actual vs planned outcomes) | `[P]` | Platform v1 |
| Full 9-stage orchestration (RECALL → PLAN → VALIDATE_PLAN → EXECUTE → NORMALIZE → SYNTHESIZE → RESOLVE_ACTIONS → SUGGEST → COMPLETE) | `[P]` | Platform v1 — built **when** Incident and Plan modes create real stage responsibilities |
| Action resolver (closed enum) | `[P]` | Platform v1 (only when briefing recommends actions beyond review) |
| Multi-oracle registry / orchestrator | `[P]` | Platform v1 (only after 2nd oracle family exists) |

**Important sequencing note (from the critique):** the full 9-stage runtime is built when L4, L6, and L7 provide real things to plan, simulate, and monitor. Building it ahead of time to satisfy the architecture diagram is exactly the over-engineering the lean-narrator decision was rejecting.

---

### L6 · Simulation & optimisation

| Capability | Current state | Closes at |
|---|---|---|
| cuOpt operational review optimizer (a6·D1) | `[I]` | App Snapshot |
| Hero-neighbourhood NYC OpenUSD twin (MN-1060) with BIN binding | `[P]` | Platform v1 |
| Selective expansion of NYC twin (additional districts) | `[P]` | Platform v2 |
| Citywide NYC OpenUSD twin | `[P]` | Full Vision |
| Object-tagging agent (3D ↔ graph bridge) | `[P]` | Platform v1 |
| One domain simulator wired (recommended: SUMO) | `[P]` | Platform v1 |
| All three domain simulators (SUMO + pandapower + EPANET) | `[P]` | Platform v2 |
| Cosmos Predict (rollouts) integration | `[P]` — needs LoRA post-training per NVIDIA cookbook, or cloud-pull pipeline | Full Vision |
| Cosmos Transfer (augmenting rare conditions) | `[P]` | Full Vision |
| Multiple cuOpt problem families (dispatch, kerbside, shutdown sequencing) | `[P]` | Platform v2 |
| Closed-loop simulation (simulate → propose → approve → execute → simulate-next) | `[P]` | Platform v1 |
| Per-cartridge custom domain simulators (oil-rig dynamics, crowd dynamics) | `[P]` | Full Vision |

**Critical sequencing correction (from the critique):** the NYC OpenUSD twin progresses hero-neighbourhood → BIN binding → graph-to-USD overlay → one event animation → performance gate → selective expansion. Citywide-first would be expensive visual mass without enough intelligence value. This is the same Rule-5 discipline that gated three-district before citywide on the graph layer.

---

### L7 · Perception / vision (the 15%)

| Capability | Current state | Closes at |
|---|---|---|
| Illustrative video assets `[Illustrative · Pexels/Pixabay]` attached to briefings | `[Illustrative]` | App Snapshot |
| Off-the-shelf PPE detection (YOLO via Triton on 4070) → structured event JSON → canonical Event → EvidenceBundle | `[P]` | Platform v1 |
| Person + PPE + restricted-zone entry + camera-health state | `[P]` | Platform v1 |
| Full Metropolis / DeepStream pipeline over synthetic camera streams | `[P]` | Platform v2 |
| VSS (Video Search & Summarization) | `[P]` | Platform v2 |
| grounding-dino open-vocabulary detection | `[P]` | Platform v2 |
| Multi-camera tracking | `[P]` | Platform v2 |
| Vision events as candidate observations, never final legal violations | `[P]` — governance principle decided | Platform v1 |
| Officer review gate between AI detection and any official action | `[P]` — governance principle decided | Platform v1 (with approval lifecycle) |

**Governance principle (load-bearing):** Perception produces *candidate observations*, not final legal violations. Officer review remains between AI detection and any official action. This is consistent with the building-violation-monitoring RFI's framing.

---

### L8 · Experience & personas

| Capability | Current state | Closes at |
|---|---|---|
| Web map (citywide, LOD, heatmap, route overlay, click-to-drill) | `[I]` | App Snapshot |
| Real building polygons on map (a3·D2) | `[I]` | App Snapshot |
| Briefing + trace + why_selected + illustrative clip | `[I]` | App Snapshot |
| Citywide live + precomputed briefings | `[I]` | App Snapshot |
| Hero-neighbourhood Omniverse 3D control room | `[P]` | Platform v1 |
| Citywide Omniverse 3D control room (full cinematic twin) | `[P]` | Full Vision |
| 4 SOUL personas (executive / planner / operator / analyst) as rendering policies | `[P]` | Platform v1 |
| Approval UI for HITL gates | `[P]` | Platform v1 |
| Multi-agent trace panel as polished product feature | `[P]` | Platform v1 |
| Conversational layer over personas | `[P]` | Platform v2 |

**Persona implementation correction (from the critique):** Personas are rendering policies over the same EvidenceBundle, not 4 autonomous agents. This keeps governance centralized and avoids over-decomposition.

---

### L9 · Governance

| Capability | Current state | Closes at |
|---|---|---|
| Provenance + confidence on every claim | `[I]` | App Snapshot |
| Claim-boundary labels enforced as metadata | `[I]` | App Snapshot |
| Grounded narration gates (subset-grounded / anti-echo / min-coverage / subject-isolated) | `[I]` | App Snapshot |
| Operator-safe wording (review, not enforce; recommend, not act) | `[I]` | App Snapshot |
| Drift gates discriminating good from broken on demand | `[I]` | App Snapshot |
| NeMo Guardrails active in wrapper | `[I]` partial — needs dedicated live gate (GV-2 in doc 02) | App Snapshot |
| Live guardrail gate proving ACCEPT and REJECT paths | `[P]` | App Snapshot |
| Explicit approval object / state | `[P]` | Platform v1 |
| Approve / reject / modify lifecycle | `[P]` | Platform v1 |
| Consequential-action policy | `[P]` | Platform v1 |
| Audit log for action proposals | `[P]` | Platform v1 |
| Monitor loop after approved action | `[P]` | Platform v1 |
| Guardrails proven across full agent roster | `[P]` | Platform v2 |

---

## 3. Agent roster — pragmatic shape (per critique)

| Component | Current state | Closes at |
|---|---|---|
| Supervisor / orchestrator | `[I]` thin | Platform v1 (expand for Incident + Plan) |
| Governed oracle runtime | `[I]` | App Snapshot |
| Domain-policy registry per cartridge | `[P]` | Platform v1 |
| Tool functions/services: cuGraph query | `[I]` | App Snapshot |
| Tool functions/services: cuOpt | `[I]` | App Snapshot |
| Tool functions/services: retrieval (cuVS / NeMo Retriever) | `[P]` | Platform v1 |
| Tool functions/services: simulation | `[P]` | Platform v1 |
| Tool functions/services: vision / VSS | `[P]` | Platform v1 (minimal) → Platform v2 (full VSS) |
| Tool functions/services: forecasting | `[P]` | Platform v2 |
| Object-tagging agent (3D ↔ graph) | `[P]` | Platform v1 |
| Briefing renderer with persona policies | `[I]` operator-only; 4 personas `[P]` | Platform v1 |
| Governance middleware | `[I]` | App Snapshot |
| LangGraph integration | `[P]` — built when inspectable multi-step branching genuinely exceeds current oracle state machine | Platform v2 |

**Pragmatic shape (from the critique):** the architecture's roster table is a *capability decomposition*, not a requirement to instantiate one long-running agent process per row. The above is the implementation-friendly version that preserves the capability list while keeping operational complexity bounded.

---

## 4. Cartridge ledger — the 7 flows

The original roadmap names seven flow families. Here is every one with its status:

| # | Flow | Domain / framing | City slot | Status | Closes at |
|---|---|---|---|---|---|
| 1 | Situational status (descriptive query) | Civic / status context | Chicago core | `[I]` accepted as part of CHI-F1F7-D5, with source limitations | Platform v1 |
| 2 | Construction-compliance cascade (reactive golden path) | Land / planning | NYC core | `[I]` certified | App Snapshot |
| 2-London | Construction-compliance cascade — second city | Land / planning | London core | `[I]` accepted — D13C + LON-HERO | App Snapshot |
| 3 | Incident / response / affected-context | Public safety + response context | NYC core | `[I]` accepted with full-source inputs and stage limitations (F3-NYC-D9FULL) | Platform v1 |
| 3X-London | Resilience / fire-incident context expansion | Public safety + mobility + environment | `LON-F3X-D1` | `[P]` — strongest next London sub-cartridge | Platform v1 |
| 4X-London | Mobility / environment expansion | Mobility + environment | `LON-F4X-D1` | `[P]` — high-confidence London expansion | Platform v1 |
| 4-Singapore | Crowd surge / transport / environment | Mobility + environment | Singapore core candidate | `[P]` — planned, authenticated API proof blocked | Platform v2 |
| 5X-London | Flood / climate risk context expansion | Resilience + climate risk | `LON-F5X-D1` | `[P]` — risk context only, no utility-control claim | Platform v2 |
| 6 | Planned shutdown sequencing | Oil & gas | TBD donor | `[P]` | Full Vision |
| 7 | Civic service + sensor fusion | Civic / IoT | Chicago core | `[I]` accepted as part of CHI-F1F7-D5, with source limitations | Platform v1 |
| Bonus | Barcelona city-core scout | Fresh city-core candidate | Barcelona | `[P]` | Platform v2 |
| Bonus | Dubai re-anchor cartridge | Phase-2 anchor | Dubai | `[P]` — needs blocked export | Platform v2 |
| Bonus | Oil & gas cartridge (production-environment slice) | Industrial | TBD | `[P]` | Full Vision |

**Slotting correction:** The long-horizon map now distinguishes **city cores** from **flow sub-cartridges**. London is accepted today as Flow 2, not Flow 3/4/5. The right next move is to mount `LON-F3X-D1`, `LON-F4X-D1`, and `LON-F5X-D1` onto the accepted London core, each with its own source ledger, joins, EvidenceBundles, replay/live proof, and hero/freeze gate.

---

## 5. NVIDIA stack — every named component's status

| Component | Architecture target | Current state | Closes at |
|---|---|---|---|
| NIM (model serving) | `[I]` | `[I]` Llama-3.1-8B on Spark | App Snapshot |
| NeMo Agent Toolkit | `[I]` | `[I]` wrapper on Spark | App Snapshot |
| NeMo Guardrails | `[I]` | `[I]` partial; live gate needed | App Snapshot |
| RAPIDS cuDF | `[I]` | `[I]` | App Snapshot |
| cuSpatial | `[I]` | `[I]` via footprint joins | App Snapshot |
| RAPIDS cuGraph / nx-cugraph | `[I]` | `[I]` citywide on 3090 | App Snapshot |
| cuOpt | `[I]` | `[I]` operational review use case | App Snapshot |
| Docker / NGC packaging | `[I]` | `[I]` | App Snapshot |
| Omniverse / OpenUSD | `[S]` | `[S]` partial (Dubai scene, no NYC twin) | Platform v1 (hero-neighbourhood) → Full Vision (citywide) |
| Cosmos Predict | `[S]` | `[P]` parked (needs LoRA per NVIDIA cookbook) | Full Vision |
| Cosmos Transfer | `[S]` | `[P]` | Full Vision |
| Cosmos Reason | `[S]` | `[P]` | Full Vision |
| Metropolis / DeepStream | `[S]` | `[P]` | Platform v1 (minimal) → Platform v2 (full) |
| VSS (Video Search & Summarization) | `[S]` | `[P]` | Platform v2 |
| grounding-dino | `[S]` | `[P]` | Platform v2 |
| Triton (model serving) | `[I]`/`[A]` | `[P]` — 4070 ready, no model loaded yet | Platform v1 |
| NeMo Curator | `[P]` | `[P]` | Full Vision |
| cuVS / NeMo Retriever | `[I]`/`[A]` | `[P]` | Platform v1 |
| Earth-2 / CorrDiff | `[P]` | `[P]` | Full Vision |

---

## 6. The data factory (synthetic-data stream)

| Capability | Current state | Closes at |
|---|---|---|
| Real-data harvest (NYC 11 datasets, London sources) | `[I]` | App Snapshot |
| Procedural / agent-based base-layer data | `[I]` partial | Platform v1 |
| Replayable scenario packs (live event simulation input) | `[P]` | Platform v1 |
| Cosmos Transfer for rare-condition augmentation | `[P]` | Full Vision |
| NeMo Curator for data curation / fine-tuning | `[P]` | Full Vision |
| Cross-city donor-data pack format | `[P]` | Platform v2 |

---

## 7. Cross-city + federated capabilities

| Capability | Current state | Closes at |
|---|---|---|
| City-scoped canonical IDs preserved per city | `[I]` | App Snapshot |
| Authoritative jurisdictional IDs as primaries (BBL, BIN, UPRN, TOID) | `[I]` | App Snapshot |
| Aliases for Overture / cross-source IDs added to canonical entities | `[P]` | Platform v2 |
| Cross-city ontology v2 reconciliation (addressable_location, parcel, building, unit distinction; RoadLink relationships) | `[P]` | Platform v1 |
| Federated query layer (city-scoped IDs, cross-city queries) | `[P]` | Platform v2 |
| Cross-city pattern matching (similar-case lookup across cities) | `[P]` | Platform v2 |
| 4+ cities in the portfolio | `[P]` | Platform v2 |

---

## 8. Dependency-ordered build sequence (technical ordering)

This is the order in which work *would* happen if everything were built. It is the *technical* ordering — what depends on what. It is **not** a timeline.

### Tier A — Close the App Snapshot
1. London Flow 2 city core accepted (LON·D4–D13c: identity, planning, Local Plan, TOID geometry, EV context, enforcement-identity, live wrapper, live face, composite reconciliation) — done
2. LON-HERO dual scenarios — done
3. City-core / flow-sub-cartridge model documented — done
4. a9 — Wire E2E + G1 + snapshot
5. Live guardrail gate (GV-2)
6. Executive Summary, rename pass, repo, README, demo video, travel bundle
7. Snapshot tagged

### Tier B — Open the Platform v1 path
8. Cross-city ontology v2 design (addressable_location, parcel, building, unit, RoadLink)
9. Minimum perception path (YOLO/PPE on Triton, 4070) → events
10. Hero-neighbourhood NYC OpenUSD twin from real footprints
11. BIN/entity binding for OpenUSD prims (object-tagging agent foundation)
12. Graph-to-USD status overlay (color a building by compliance state)
13. One event/route animation in the 3D scene

### Tier C — Live event fabric + simulation
14. Append/replay event-stream contract
15. Event-time / processing-time semantics, late/out-of-order handling
16. One continuous-signal stream (recommended: traffic via GTFS + sensor data)
17. Replayable scenario packs
18. SUMO wired and calibrated for NYC or London
19. Forward dynamics demonstrated (Plan mode with SUMO rollout)

### Tier D — Cognition expansion (driven by Tier C providing real work)
20. Incident mode end-to-end
21. Plan mode end-to-end with monitor loop
22. Full 9-stage orchestration (RECALL → … → COMPLETE) — built when each stage has real work
23. Action resolver (closed enum)
24. Inverse dynamics demonstrated (Plan + cuOpt + simulator)

### Tier E — Governance expansion
25. Explicit approval object and lifecycle (approve / reject / modify / execute / monitor)
26. Approval UI surfaced in face layer
27. Audit log for action proposals
28. Guardrails proven on consequential-action paths

### Tier F — Persona + retrieval + agent roster
29. 4 SOUL personas as rendering policies over the same EvidenceBundle
30. cuVS / NeMo Retriever as retrieval tool
31. Domain-policy registry per cartridge
32. Tool functions: simulation, vision, forecasting

### Tier G — Accepted city cores + mounted flow expansions (Platform v1 portfolio criterion)
33. Chicago Flow 1 + Flow 7 accepted snapshot (CHI-F1F7-D5) — done with capped-source limitations
34. `LON-F3X-D1` London resilience / fire-incident context scout
35. `LON-F4X-D1` London mobility / environment scout
36. `LON-F5X-D1` London flood / climate risk context scout

### Tier H — Platform v1 snapshot

### Tier I — Platform v2 expansion (beyond Platform v1)
37. Selective expansion of OpenUSD twin to additional districts
38. All three domain simulators wired (pandapower + EPANET added to SUMO)
39. Full Metropolis / DeepStream pipeline
40. VSS (Video Search & Summarization)
41. grounding-dino open-vocabulary detection
42. Energy / water / asset-dependency graph edges
43. Cross-domain impact propagation
44. Federated query layer across cities
45. Aliases for Overture and cross-source IDs on canonical entities
46. 4+ cities
47. LangGraph integration where inspectable multi-step branching exceeds the oracle state machine

### Tier J — Full Vision (beyond Platform v2)
48. Flow 4 (crowd surge)
49. Flow 5 (flood / asset cascade)
50. Flow 6 (oil & gas shutdown sequencing)
51. Dubai re-anchor cartridge (Phase-2 anchor)
52. Oil & gas cartridge (production-environment slice)
53. Citywide NYC OpenUSD twin (after selective expansion proves the binding contract)
54. Cosmos Predict / Transfer / Reason integration (post-training or full cloud pipeline)
55. NeMo Curator for data curation / fine-tuning
56. Earth-2 / CorrDiff weather / flood
57. BIM / IFC building-interior adapter
58. Live real-time IoT integration
59. Multi-stream / multi-region event distribution
60. Per-cartridge custom domain simulators (oil-rig dynamics, crowd dynamics)

---

## 9. The boundary between Platform v1 and Full Vision

This is the load-bearing distinction the critique surfaced. Stated explicitly:

**Platform v1 needs:**
- 2–3 cities (not 4+)
- 3–4 flow families (not 7)
- Query + Incident + Plan modes (not the full 9-stage orchestration unless each stage has real work)
- One simulator (not all three)
- Hero-neighbourhood twin (not citywide twin)
- Minimum viable perception (not full Metropolis / VSS / grounding-dino)
- 4 personas as rendering policies (not 4 autonomous agents)
- Live event fabric with one continuous signal (not multi-stream)
- HITL approval lifecycle (consequential actions exist for the first time)

**Full Vision adds:**
- 4+ cities
- All 7 flows
- Cosmos / NeMo Curator / Earth-2 / cuVS expansions
- All three simulators
- Full Metropolis / VSS / grounding-dino
- Citywide OpenUSD twin
- BIM, document, live IoT, multi-region

The Platform v1 bar is set deliberately at the lowest point that is still credible as a *platform*. Going further than Platform v1 toward Full Vision is real work and real value — but it is past the credibility threshold, not before it.

---


## 10. Post-PV1 strategic fork

## Post-PV1 addendum R1 — review-flow acceptance policy

```text
FLOWX-REVIEW-FLOW-ACCEPTANCE-D1  GREEN
PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS
```

This is a **post-PV1 addendum**. It does not mutate the frozen `PV1-D19/D20/D21/D22` review-only snapshot.

**Accepted review flows with limitations:**

```text
NYC-F1X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F5X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F6X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F3X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F4X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
```

**Preserved blocker:**

```text
BARC-F7  CANDIDATE_ONLY_NOT_ACCEPTED / BLOCKED_BY_CITY_CORE
```

**Boundary:** accepted review flow means governed review use only. It does **not** mean production control, autonomous operation, dispatch, public-safety instruction, traffic/transit/utility/port/airport command, enforcement, health determination, or certified affected-asset/building truth.

Verification: no-overclaim PASS, no-mutation PASS, hashes PASS; `PV1-D19/D20/D21/D22` frozen outputs unchanged.


PV1 now freezes as a **review-only platform**. The next decision is not "turn on autonomy." The next decision is which value track should use the proof engine first.

### 10.1 Seven alternatives before autonomous control

| Order | Track | Purpose | Boundary |
|---:|---|---|---|
| 1 | Product / demo / narrative pack | Make the proof engine legible: demo script, operator journey, executive story, screenshots/video, product one-pager, capability matrix | No new control claims |
| 2 | Compliance / planning vertical depth pack | Deepen the strongest accepted vertical: NYC Flow 2 + London Flow 2 planning/compliance context | Review/compliance context only |
| 3 | Omniverse visual twin / scene binding | Bind grey-city + textured hero-location assets to CityBrain evidence, routes, replays, and persona panels | Assets are manual/external until a binding gate runs |
| 4 | Production review-only hardening | RBAC, API contracts, observability, SLOs, secrets, backups, source freshness, dev/stage/prod | Still no actuators |
| 5 | Data moat / XDATA freshness layer | Incremental updates, source monitors, selective source expansion where it improves accepted/review value | No breadth for breadth's sake |
| 6 | Agent / NIM / NeMo briefing layer | Tool registry, evidence-only narration, retrieval over route evidence, evals, hallucination/no-overclaim tests | LLM narrates/routes; code owns truth |
| 7 | Autonomy / operational control | Deferred safety-critical future program | Not a PV1 continuation |

### 10.2 Production/autonomous-control ladder

```text
PV1 = review-only platform snapshot
P1 = production review-only platform
P2 = production advisory platform
P3 = supervised action platform
P4 = bounded closed-loop automation
P5 = autonomous control in narrow certified domains
```

**Critical fence:**

```text
No LLM controls actuators.
No model emits operational commands.
No review route becomes control.
Only deterministic, policy-bound, certified adapters may ever sit near actuators,
and only inside a future safety case.
```

Autonomy requires real-world partner access, shadow mode, safety case, certified adapters, manual override, legal/operational authority, and formal risk governance. It should not be added to the active build lane merely because PV1 is complete.

### 10.3 Omniverse asset-lane boundary

The user is progressing the grey-city / textured hero-location asset lane manually:

```text
NYC, London, Chicago, Barcelona grey-city assets
selected textured hero-location models
global geolocation
USD / Omniverse readiness
```

Codex should not treat those assets as available until a future `CITY-SCENE-BINDING-D1` gate exists. That binding gate should define CRS/geolocation anchors, USD prim path conventions, city/flow/entity-to-asset IDs, route overlay schema, replay-time overlay schema, evidence panel binding, and asset provenance/licensing.

### 10.4 Rule for adding more cities or data

Before adding more cities or expanding more data, ask whether the missing layer is:

```text
legibility
vertical depth
scene binding
production review-only hardening
freshness/incremental update
agent/briefing quality
acceptance policy
```

If none of those improves, more breadth is lower priority.

---

## 11. What this document is for, and what it is not for

**Use this doc for:**
- Architectural completeness checks ("did we forget anything in L6?")
- Long-horizon planning conversations ("when does Cosmos fit?")
- Stakeholder questions about the outer ambition ("how big does this get?")
- Onboarding new collaborators to the full vision
- Maintaining the boundary between Platform v1 and beyond

**Do NOT use this doc for:**
- Estimating the application's completion percentage (use docs 01 + 02 instead)
- Scheduling near-term work (use docs 02 + 03 instead)
- Deciding what to ship (that's doc 02)
- Inferring that the project is "15% done" (the App Snapshot in doc 02 is much closer to its finish line than this map suggests)

---

## 12. The honest framing for the outer horizon

> "The Application Snapshot (doc 02) is a real, governed, citywide, end-to-end NYC + London demonstration that earns its claims. Platform v1 (doc 03) is now a green review-only platform snapshot — multi-city, multi-flow, multi-mode cognition, one simulator, persona renderings, event fabric, HITL approval, and guardrail/action policy. Full Vision (this doc) is the architecture's outer ambition with every named NVIDIA component, every flow, every simulator, every advanced frontier capability. The first is shippable. The second is buildable. The third is mappable — and we maintain it honestly so nothing in the architecture goes invisibly unbuilt."

---

*End of doc 04. The four documents together — Current State, Application Snapshot DoD, Platform v1 DoD, Full Vision Completion Map — are the canonical reference set. They are designed to be read in order (01 → 02 → 03 → 04), each one widening the horizon, each one with its own claim labels and its own definition of done.*
