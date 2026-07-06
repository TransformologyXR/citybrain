# CityBrain Product Definition and Vision
## Governed City Intelligence and Operations Platform

**Status:** Authoritative strategy document v2  
**Date:** 2026-07-05  
**Scope:** Product definition, positioning, authority model, users, value proposition, current state, and north-star product loop.  
**Companion documents:**

1. `02_CITYBRAIN_INTELLIGENCE_MODES_CAPABILITY_MAP.md`
2. `03_CITYBRAIN_AGENTIC_INTELLIGENCE_LAYER.md`
3. `04_CITYBRAIN_ARCHITECTURE_AND_ROADMAP.md`
4. `05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md`


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

## 1. Executive thesis

CityBrain is a **governed city intelligence and operations platform**.

It exists to turn fragmented city records, media signals, spatial assets, operational events, and human workflow into an evidence-backed intelligence loop that can observe, explain, validate, brief, propose, schedule, and eventually execute approved workflows under explicit authority.

CityBrain should not be defined as a dashboard, an Omniverse scene, a VSS pipeline, a graph database, an ASK router, or a chatbot. Those are components. The product is the integrated intelligence loop.

The north-star loop is:

```text
PERCEPTION / EVENT / DIFF / SOURCE RECORDS
→ IDENTITY
→ GRAPH
→ WATCH
→ SELECT
→ ASK
→ CHECK
→ BRIEF
→ RECALL / PLAN / SCHEDULE / SPATIAL / SIMULATE
→ HUMAN / GOVERNED WORKFLOW STATE
→ GOVERNANCE TRACE
```

The platform starts by helping operators and analysts understand what is happening and what can honestly be claimed. It should evolve beyond review support into governed operations: proposing plans, generating schedules, preparing action packets, executing approved workflows through adapters, monitoring outcomes, and escalating exceptions. The permanent principle is not “review-only.” The permanent principle is **no authority without an explicit, scoped, auditable authority grant**.

---

## 2. Product definition

CityBrain is a system that:

- Resolves fragmented city data into confidence-aware canonical entities.
- Builds semantic graph context around those entities.
- Watches for review-worthy city situations.
- Lets users ask bounded questions over retained evidence.
- Validates claimability, sufficiency, freshness, contradiction, and boundary risk.
- Generates evidence-backed briefs.
- Recalls similar prior cases.
- Detects changes between snapshots.
- Ingests candidate observations from media without treating them as findings.
- Grounds selections in spatial surfaces such as GIS, web maps, Omniverse Kit, and WebRTC-streamed scenes.
- Supports workflow states such as hold, needs-source, abstain, reviewed, proposal, approved, executed, monitored.
- Emits traces and authority records for every consequential output.

CityBrain is not:

- A generic chatbot.
- A passive dashboard of city records.
- A pure master-data-management system.
- A graph database demo.
- A CCTV detection system that turns boxes into truth.
- A 3D scene viewer pretending to be intelligence.
- A production command system before authority, audit, security, and workflow adapters exist.

The product should be described as:

```text
A governed city intelligence and operations platform that resolves fragmented city records into evidence-backed entities, detects review-worthy situations, answers bounded questions, validates what can and cannot be claimed, generates briefings, supports planning and scheduling, grounds decisions in space and time, and executes only under explicit authority.
```

---

## 3. The correction to “review-only”

Earlier work used “review-only” as a protective boundary. That was useful while the system was immature and while media, graph, Omniverse, and ASK outputs could easily be overread as truth. However, the product vision should not be trapped there.

The correct authority model is progressive:

| Level | Authority stage | Product meaning | Current suitability |
|---:|---|---|---|
| 0 | Observe | Ingest records, media, spatial selections, events, and snapshots. | Current / near-term |
| 1 | Explain | Resolve identity, retrieve evidence, answer questions, show context. | Current / near-term |
| 2 | Validate | CHECK evidence sufficiency, claimability, source depth, contradictions, and boundaries. | Current / near-term |
| 3 | Propose | Produce option sets, briefs, schedules, recommended next checks, and action proposals. | Emerging |
| 4 | Approve | Human approves, modifies, rejects, or delegates a proposed workflow. | Future governed workflow |
| 5 | Execute approved workflow | Execute through adapter under policy, trace, rollback, and monitoring. | Future production lane |
| 6 | Conditional autonomy | Narrow, low-risk, pre-approved autonomous workflows with monitoring and escalation. | Long-term only |

The durable rule is:

```text
CityBrain never acts without explicit authority.
```

The current implementation may be “no-action / proposal-only.” The product ambition is broader: governed operation, not permanent passivity.

---

## 4. Why CityBrain exists

City operations suffer from a context and coordination problem:

- Records are scattered across departments and systems.
- Identity is ambiguous: the same thing appears under different IDs, names, coordinates, addresses, and source conventions.
- Operators manually stitch context from maps, permits, complaints, inspections, asset lists, event feeds, spreadsheets, and dashboards.
- Dashboards show records but do not decide what needs attention.
- Media systems detect objects but do not know what the city can claim.
- 3D scenes show place but not evidence, authority, or consequences.
- AI systems often overclaim because they blur records, inference, model output, and narrative.
- Cities need escalating capability, but risk teams reject systems that appear autonomous without audit and authority controls.

CityBrain’s value is to provide **context on demand with receipts**, and over time to add **governed operational capability**.

---

## 5. Product users and jobs

### 5.1 Duty operator / operations officer

**Needs:** Know what deserves attention, what evidence supports it, what is missing, what to do next, and what can be safely escalated.

**CityBrain gives:** WATCH queue, selected item workspace, ASK answers, CHECK validation, BRIEF packets, event state, spatial context, workflow state.

### 5.2 Case officer / inspector

**Needs:** Review a suspected issue, inspect evidence, determine whether more data is needed, prepare a packet, and hand off under policy.

**CityBrain gives:** source records, media evidence, entity context, claimability checks, action proposal packets, review notes.

### 5.3 Planner / analyst

**Needs:** Understand area, parcel, permit, development, service, mobility, and precedent context.

**CityBrain gives:** entity 360, graph context, recall, diff, data quality, scenario simulation, planning briefs.

### 5.4 Executive / decision owner

**Needs:** Reliable summary, risk, tradeoffs, constraints, options, approvals required, and confidence.

**CityBrain gives:** executive brief, option set, risk and limitations, proposed actions, authority trace.

### 5.5 Data / digital twin engineer

**Needs:** Know data quality, identity conflicts, missing relationships, source freshness, spatial binding issues, and what to fix.

**CityBrain gives:** CER/SEG diagnostics, data maturity intelligence, synthetic challenge tests, spatial binding reports, source gap ledgers.

### 5.6 Governance / risk reviewer

**Needs:** Verify what the system did, why it did it, where evidence came from, and whether authority boundaries were respected.

**CityBrain gives:** trace, source provenance, no-action / authority envelope, refusal logs, approved workflow audit, CHECK results.

---

## 6. Product pillars

### 6.1 Evidence-first intelligence

No factual claim should exist without a traceable source, derived rule, model output label, or explicit limitation. Evidence can come from official records, source records, sensor/model inference, simulations, or synthetic scenarios — but the source class must be visible to the engine and auditable.

### 6.2 Identity under ambiguity

The core product challenge is not generic data integration. It is resolving real-world city identity under ambiguity: source IDs do not align, names differ, geometries conflict, records duplicate, and systems only know partial truths.

### 6.3 Graph context over stable identity

The semantic graph is only valuable if identity is stable enough. The Canonical Entity Registry is the hard spine; the Semantic Entity Graph is the reasoning projection on top.

### 6.4 Event-state nervous system

A real city brain must respond to events and changes. Temporally stamped records are not enough; CityBrain needs an event fabric with append, replay, resolution, quarantine, materialized state, query, and trace.

### 6.5 Governed agents, not free-form autonomy

Agents are workers with bounded missions, tools, evidence outputs, authority levels, and traces. They activate intelligence modes; they do not replace the orchestrator or invent truth.

### 6.6 Progressive authority

The product should evolve from observe/explain/validate into propose/schedule/execute approved workflows. Authority is explicit and auditable, never implicit.

### 6.7 One truth, many surfaces

The web cockpit, Omniverse/Kit, WebRTC stream, VSS observation view, and exported briefs must consume the same packets. A new surface must not invent a separate truth.

---

## 7. Current reported state

This status is a strategic snapshot, not a full code audit.

| Area | Reported state | Meaning |
|---|---|---|
| ASK v1.1 | Closed / published; moving to app handoff preflight | ASK core should stop expanding and wire sealed packets into cockpit/app surfaces. |
| Metropolis / VSS | Closed in current ledger | Candidate-observation lane has a closed proof, but product scope remains candidate observations, not findings. |
| Omniverse / WebRTC R5 | Closed at functional proof | Live stream, object/event review loop, parity, and not-executed boundary were proven; UI/UX polish is parked. |
| Web cockpit | Improved but not final | Operator projection is better but still needs product-grade workspace, richer data, and workflow. |
| CHECK | Concept strong; implementation thin | Needs explicit evidence sufficiency and claimability engine. |
| Event fabric | Thin | Needs real append/replay/materialize/query model. |
| CER/SEG | Strong direction, partial implementation | Needs registry engine, relationship ontology, shared contracts, confidence/review-state model. |
| Plan/Schedule/Simulate | Early | Needs option, scheduling, simulation, and approval models. |
| Production authority/security | Future | Not ready to claim production operation. |

---



## 7A. Current certified-state ledger — R2 summary

The product vision is broader than any single sprint, but current claims must rest on certified artifacts. The table below is the R2 product-level ledger.

| Component | Current status | Proof / artifact | What is proven | What is not proven |
|---|---|---|---|---|
| ASK v1.1 core | **Closed / published** | `3907bc1 Implement ASK v1.1 canonical packet flow and sealed eval`; `1eab1d9 Add ASK v1.1 retained real-corpus eval R2 closeout` | Canonical packet flow, sealed eval, retained real-corpus eval with accepted contradiction-coverage limitation. | Broad open ASK over arbitrary operator questions; production natural-language router. |
| ASK app handoff | **Passed bounded app handoff** | `1f92044 Add ASK v1.1 app handoff R1`; `ASK-V11-APP-FIXTURE-VENDORING-R1 = PASS` | Web-control-room can consume committed ASK handoff fixtures from a stable app path; fresh-clone fixture loading and safety-boundary tests pass. | Browser visual polish; broader app-route UX; live retrieval. |
| Metropolis / VSS / DeepStream | **Closed at bounded local/replay candidate-review level** | R7 local/replay perception-to-review workflow; DeepStream 8 runtime proof on `txr-4070`; VSS smoke on Spark; static review-surface artifacts. | Offline/sample media can produce candidate observations and evidence/review packets; DeepStream runtime is ready for R9 local/replay; VSS is reachable as narrative context. | Production live CCTV, live RTSP registry, official findings, legal/violation claims, identity, dispatch/control/enforcement. |
| Omniverse / WebRTC | **Closed at functional proof level** | `PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS` | Live WebRTC stream, real Barcelona scene references, scene prim selection parity, event overlay parity, object-event review loop, packet truth and `not_executed` preserved. | Finished native Kit UI, polished spatial UX, side rail/inspector polish, scene visual fidelity, production spatial workflow. |
| CHECK | **Concept strong; implementation split required** | Existing caution/source-depth checks; R2 doc split. | Need and shape are clear. | Full claim-to-evidence mapper, contradiction engine, detection-sufficiency engine, abstain policy. |
| Event fabric | **Thin / pre-v0** | Prior event/source crossing and replay artifacts. | Need is clear; source/replay crossing patterns exist. | Event fabric v0 append/query; v1 quarantine/materialization/replay; v2 multi-source operational state. |

This ledger should be updated whenever a published commit, closeout, or milestone changes the maturity of a component. It is the bridge between product narrative and engineering truth.

## 8. Product maturity levels

CityBrain should use a common maturity model for all components:

| Level | Meaning |
|---:|---|
| M0 | Concept only. |
| M1 | Spec/artifact exists. |
| M2 | Deterministic/prototype proof works. |
| M3 | Integrated into runtime/cockpit. |
| M4 | Operator-useful in one real workflow. |
| M5 | Production-ready, governed deployment. |
| M6 | Approved execution and monitoring in live operations. |

Current overall maturity is approximately **M2.5–M3**: strong proofs and architecture, several real primitives, but not yet an operator-grade governed operations product.

---

## 9. Product north-star loop

### 9.1 Observe

Sources arrive from official records, event feeds, snapshots, spatial surfaces, media, synthetic scenarios, and human input.

### 9.2 Resolve

Identity and relationships are resolved through CER and SEG.

### 9.3 Scout

Agents run WATCH, DIFF, PERCEPTION, EVENT, DATA QUALITY, and RECALL scouts.

### 9.4 Select and investigate

Operators or agents select a candidate. ASK, GRAPH, CHECK, RECALL, DIFF, and SPATIAL deepen context.

### 9.5 Validate

CHECK evaluates evidence sufficiency, source depth, freshness, contradiction, model inference confidence, and authority boundary.

### 9.6 Brief and propose

BRIEF assembles the evidence. PLAN and SCHEDULE generate reviewable options. SIMULATE estimates outcomes under assumptions.

### 9.7 Approve or abstain

Humans approve, modify, reject, abstain, hold, or request more sources.

### 9.8 Execute approved workflow

Only after explicit authority does the platform execute through adapters.

### 9.9 Monitor and learn

Outcomes, diffs, operator actions, source changes, data gaps, and new evidence feed back into the intelligence loop.

---

## 10. What makes CityBrain intelligent

CityBrain’s intelligence does not come from one model. It comes from the composition of:

```text
identity resolution under ambiguity
+ graph relationships
+ event/state changes
+ evidence packets
+ CHECK claimability
+ governed orchestrator
+ specialist agents
+ human authority workflow
+ spatial/perception surfaces
+ memory, recall, diff, and simulation
```

The LLM is important, but it is not the center. It is a bounded reader and writer inside a contracted intelligence harness.

---

## 11. Commercial positioning

CityBrain should not be sold as:

```text
AI dashboard
CCTV analytics
digital twin viewer
graph database
chatbot
master data management
```

It should be positioned as:

```text
A governed city intelligence and operations platform that lets departments turn fragmented records, spatial assets, events, and media into evidence-backed operational decisions and approved workflows.
```

The strongest commercial wedges are:

1. **City operations intelligence:** What needs attention and why?
2. **Evidence-backed briefing:** What can we claim and what is missing?
3. **Data maturity diagnostics:** What data quality gaps block intelligence?
4. **Perception-to-review:** How do media signals become candidate observations safely?
5. **Spatial one-truth cockpit:** How does 3D/GIS selection connect to real evidence?
6. **Progressive authority:** How does a city move from insight to approved action without unsafe autonomy?

---



## 11A. Today-vs-roadmap external language

The external product message must distinguish current capability from future authority.

**Today / current bounded product:**

```text
observe
resolve
explain
validate
brief
surface candidate review items
produce local/replay evidence packets
prepare proposal-only artifacts
```

**Roadmap / future governed operations:**

```text
approved workflow creation
approved execution through adapters
monitoring of outcomes
conditional autonomy for narrow, pre-approved, low-risk workflows
```

The phrase “governed city intelligence and operations platform” is correct, but customer-facing language must always make the current authority level visible. The permanent claim is not that CityBrain acts today; the permanent claim is that **any future action must be explicit, scoped, auditable, and authority-bound**.

## 12. Definition of success

A credible CityBrain product milestone exists when a user can:

1. Open a city patch or operating scope.
2. See review-worthy situations surfaced by agents, events, diffs, perception, or data quality scouts.
3. Select a situation and see identity, graph, evidence, and source records.
4. Ask bounded questions and receive cited answers or clarifications/refusals.
5. See CHECK results that validate or downgrade claims.
6. Generate a brief.
7. Recall similar cases.
8. See spatial context in web/Omniverse without a separate truth.
9. Compare options or schedules under assumptions.
10. Approve, reject, abstain, hold, or request more data.
11. If authority exists, execute an approved workflow through an adapter.
12. Trace every step.

That is the product.

---

## 13. Immediate product direction

The next product direction should not be another generic UI pass. It should be:

```text
1. ASK v1.1 app handoff: wire sealed packets into cockpit surfaces.
2. CHECK contract v1: make evidence sufficiency and claimability real.
3. Event fabric: give the city a local operational nervous system.
4. Agentic scout layer: start with WATCH, DIFF, EVENT, PERCEPTION, DATA QUALITY scouts.
5. Spatial/Perception integration: consume candidate observations and spatial selections through common packets.
6. Progressive authority model: define proposal, approval, execution, and monitoring contracts.
```

---

## 14. Language rules for future docs

Use:

```text
current authority level
proposal-only
approved workflow
candidate observation
evidence sufficiency
claimability
source class
progressive authority
governed execution
```

Avoid using “review-only” as the product identity. It may be used only as a current authority state for specific early builds.

Do not say:

```text
CityBrain never acts.
```

Say:

```text
CityBrain only acts under explicit, scoped, auditable authority.
```

