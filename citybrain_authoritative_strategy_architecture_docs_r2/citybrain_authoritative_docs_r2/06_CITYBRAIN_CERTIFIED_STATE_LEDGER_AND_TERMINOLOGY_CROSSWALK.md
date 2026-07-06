# CityBrain Certified-State Ledger and Terminology Crosswalk
## R2 companion to the authoritative docs

**Status:** Authoritative companion document v2  
**Date:** 2026-07-05  
**Purpose:** Prevent strategy-document drift by connecting the new product vocabulary to the old proof vocabulary and the current running-track ledger.

---

## 1. Why this companion exists

The v1 authoritative docs improved the strategic framing, but they did not sufficiently cite the old gates, D/R labels, commits, and closeouts that earned current maturity claims. This companion restores that proof discipline.

Rules:

```text
No maturity claim without proof.
No old artifact treated as obsolete until mapped.
No dataset accepted without a consuming capability.
No future authority claim without an AuthorityEnvelope and proof.
```

---

## 2. Current running-track ledger — R2

| Track | Status | Proof | Interpretation |
|---|---|---|---|
| ASK v1.1 core | CLOSED / PUBLISHED | `3907bc1`, `1eab1d9` | Canonical ASK packet flow and retained real-corpus eval are closed. |
| ASK app handoff | PASS / bounded app integration | `1f92044`; `ASK-V11-APP-FIXTURE-VENDORING-R1 = PASS` | App can consume committed ASK fixtures; do not extend ASK core now. |
| R7 perception-to-review | CLOSED / pushed | `840f784` | Local/replay perception-to-review workflow preserved candidate-only boundaries and did not mutate ASK runtime. |
| DeepStream runtime | READY for R9 local/replay | `txr-4070` runtime proof | Native Ubuntu + Docker + NVIDIA Toolkit + DeepStream 8 sample file pipeline all pass. |
| Metropolis / VSS lane | Internal alpha / bounded candidate-review | R7/R8/R22 family artifacts | Media candidate-review lane exists; not production surveillance. |
| VSS | Review-assist narrative only | Spark VSS smoke and evidence-bundle join | Narration sidecars can assist review; they are not truth. |
| Omniverse/WebRTC R5 | CLOSED functional proof | `PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS` | WebRTC stream/object-event review loop works; UI/UX remains parked. |
| CHECK | Highest-priority dependency | R2 split | CHECK v0 is next; CHECK v1 remains deeper engine. |
| Event fabric | Thin | Prior source/replay crossing | Event Fabric v0 still needed. |

---

## 3. DeepStream runtime proof — R2

```text
Host type: native Ubuntu Linux, not WSL2.
Observed: Ubuntu 26.04 LTS, kernel 7.0.0-22-generic.
GPU visible inside runtime: PASS, RTX 4070 visible via nvidia-smi on host and inside Docker.
Docker installed/working: PASS, Docker 29.6.0, Compose v5.2.0.
NVIDIA Container Toolkit: PASS, nvidia-container-toolkit 1.19.1.
DeepStream image pulled: PASS, nvcr.io/nvidia/deepstream:8.0-samples-multiarch.
deepstream-app --version-all: PASS, DeepStreamSDK 8.0.0, CUDA driver 13.2, CUDA runtime 12.9, TensorRT 10.9, cuDNN 9.8.
Sample file pipeline: PASS, exit code 0, Received EOS and App run successful.
```

Claim boundary: this proves local/replay runtime readiness, not production live CCTV.

---

## 4. Crosswalk summary

The full crosswalk follows below. The most important decisions are:

```text
Old Flow 1–7 survives as flows/cartridges packaging.
New modes are cross-cutting capabilities.
Old D/R/G gate names remain proof references.
Old [I]/[S]/[A]/[P] labels are not source_class or maturity; they are a third axis.
D13/R5 should be expressed as proof reference plus M-level.
Canonical entity ID format must stay explicit.
Cosmos, Earth-2/CorrDiff, Triton, NGC/Docker are deferred unless mapped by a future sprint.
```

---

# CityBrain Terminology Crosswalk
## Old (RTX/NVIDIA sprint docs, City Brain / TXR City Brain) ↔ New (2026-07-04 Authoritative Strategy Set)

**Purpose:** The new authoritative doc set (Docs 01–05) renames most of the system's vocabulary. This crosswalk exists so that work already certified under the old names doesn't get silently re-derived, re-explained, or treated as unbuilt by anyone — human or agent — who only reads the new docs.

**How to use this doc:** find the old term on the left, read what it now maps to on the right, and note the "Status carries forward?" column — it tells you whether the *proof* still counts under the new framing or whether the new framing changes what counts as done.

---

## 1. Layers — old 9-layer spine ↔ new 9-layer architecture

The layer *count* stayed at nine, and the sequence is nearly identical, but two things changed: L5 was split, and L9 was renamed from a single governance layer into two layers (agentic + authority).

| # | Old (Architecture doc) | New (Doc 04) | Status carries forward? |
|---|---|---|---|
| L1 | Ingestion & adapters | Source and ingestion layer | Yes — same purpose, now adds the `source_class` taxonomy requirement (official_record / source_record / sensor_inferred / model_inferred / derived_field / integrated_external / synthetic / replay / operator_input / approved_workflow_output) on top of the old adapter model. |
| L2 | Canonical entity registry | Canonical Entity Registry (CER) | Yes, directly. New doc adds explicit `attribute_assertions` / `attribute_conflicts` / `match_candidates` as first-class objects — these were implicit in the old confidence/provenance model, now made explicit. |
| L3 | Multiplex semantic graph (cuGraph) | Semantic Entity Graph (SEG) | Yes, directly. cuGraph is now referenced as a *tool*, not the layer name. |
| L4 | Observation / event fabric | Event fabric and operational state | Yes, same purpose. New doc is more specific: requires append-only log, quarantine, state materializer, replay, expiry/supersession — capabilities the old doc named but didn't spec this granularly. |
| L5 | Cognition engine — the action core (9-stage orchestration + one action core: simulate → optimize → act → monitor, entered via Query / Incident / Plan) | Split into two layers: **L5 Orchestrator/cognition engine** (gates, agent runtime, ASK flow) + **L7 Agentic intelligence layer** (the agents themselves) | Partial. The *orchestrator* concept survives (now generalized from the "9-gate ASK flow" as the reusable runtime). The *action core* (simulate → optimize → act → monitor) survives conceptually inside PLAN/SCHEDULE/SIMULATE modes, but is no longer named as a single core — it's decomposed into separate modes with separate maturity levels. |
| L6 | Simulation & optimisation (twin, SUMO/pandapower/EPANET, Cosmos, cuOpt) | Evidence and CHECK layer | **No — these are different layers now.** Old L6 (simulation/twin) maps forward to the new **SIMULATE and SCHEDULE/OPTIMIZE intelligence modes** (Doc 02 §14–15), not to new L6. New L6 is a brand-new layer (Evidence/CHECK) that didn't exist as a named layer in the old spine at all — see §4 below. |
| L7 | Perception / vision | Agentic intelligence layer | **No — different layers.** Old L7 (perception/vision) maps forward to the **PERCEPTION intelligence mode** (Doc 02 §11) and the **Perception/Media Agent** (Doc 03 §6.5), not to new L7. |
| L8 | Experience & personas | Experience layer | Yes, directly — same purpose (web, Omniverse, briefs, API surfaces). PERSONA is now formalized as its own "platform/commercial mode" rather than a component of L8. |
| L9 | Governance (single layer: provenance, confidence, HITL, NeMo Guardrails, claim-boundary labels) | Split into **L9 Authority and governance layer** (this is the direct descendant) — with the **Agentic layer (L7)** absorbing the old agent-roster content that used to live partly in L9's "guardrail/governance agent." | Partial — the governance *content* survives and is more detailed (AuthorityEnvelope, authority ladder 0–6), but note the layer numbers no longer line up 1:1 (old L9 ≠ new L9 in scope; new L9 is narrower, authority-specific). |

**Correction flag:** because L5–L9 were reshuffled rather than renamed 1:1, do not assume "new L6" = "old L6" or "new L7" = "old L7." Layer numbers 1–4 and 8 carry forward directly; 5–7 and 9 do not.

---

## 2. The cognition engine / 9-stage orchestration ↔ ASK flow + orchestrator

| Old | New | Status carries forward? |
|---|---|---|
| 9-stage governed orchestration: `RECALL → PLAN → VALIDATE_PLAN → EXECUTE → NORMALIZE → SYNTHESIZE → RESOLVE_ACTIONS → SUGGEST → COMPLETE` | ASK canonical flow (Doc 05 §21): `G1 boundary_screen → G2 intent_and_concept_binding_resolver → G3 execution_contract_compiler → G4 argument_resolution → G5 template/tool_execute → G6 CHECK evidence_sufficiency_and_claimability → G7 answer_assemble → G8 render` | **Renamed and re-scoped, not identical.** The new G1–G8 is specifically the ASK question-answering flow. The old 9-stage RECALL→COMPLETE was meant to generalize across Query/Incident/Plan entry points. The new docs explicitly say "the old 9-gate orchestrator pattern should become the reusable flow runtime for task agents" (Doc 03 §8) — meaning the *generalization* the old 9-stage design was reaching for is still an open task, not something the new ASK-specific G1–G8 flow has already delivered for Incident/Plan. |
| "Governed deterministic oracle" (code computes, model narrates) | "Deterministic gates own truth and authority; LLMs read and write" (Doc 04 §3.5 rule) | Yes — same principle, same discipline, restated. |
| EvidenceBundle | EvidencePacket | Yes, direct rename. New EvidencePacket schema (Doc 05 §10) is the formalized version of what EvidenceBundle already did (subset-grounded / anti-echo / min-coverage / subject-isolated narration). |
| Action core: *simulate → optimise → act → monitor* | Split across SIMULATE, SCHEDULE/OPTIMIZE, PLAN modes + the authority ladder's Execute/Monitor levels (4–5) | Conceptually yes, structurally no — no single "action core" module exists in the new framing; it's decomposed into modes with independent maturity. |
| Query / Incident / Plan (three entry modes into the action core) | ASK (≈Query), EVENT/INCIDENT mode (≈Incident), PLAN mode (≈Plan) | Yes, direct conceptual mapping, now as three separate intelligence modes rather than three entry points into one shared core. |
| Action resolver (closed enum) | Not explicitly named in new docs — closest equivalent is the `allowed_next_steps` / `forbidden_steps` fields in AuthorityEnvelope (Doc 05 §4) | Partial — same intent (constrain what the system can actually do), different mechanism name. |
| Multi-oracle registry / orchestrator | Not explicitly named — closest equivalent is the general Orchestrator (Doc 04 §3.5, Doc 03 §8) | Not carried forward by name; treat as unbuilt/renamed-away unless deliberately revived. |

---

## 3. Gates and proof status ↔ maturity levels

The old docs used two different status systems that don't map cleanly onto the new M0–M6 scale. Do not treat these as interchangeable without translation.

| Old system | What it meant | New system | Translation note |
|---|---|---|---|
| Sprint gates `G0–G4` (Roadmap doc) | G0 = harness+schema+env exist; G1 = Flow 2 end-to-end certified (golden path); G2 = twin+vision+3D bridge play; G3 = 3–4 flows run as cartridges; G4 = definition of done (video, repo, blog, claim audit, snapshot) | No direct equivalent — these were sprint-specific milestones, not a maturity scale | These gates are **specific to the original 10-day sprint plan** and don't reappear in the new docs at all. If G1 (Flow 2 certified) actually passed, that fact needs to be re-stated in M-scale terms (likely M3–M4 for whatever modes Flow 2 touched) or it will look unbuilt. |
| Claim labels `[I]` / `[S]` / `[A]` / `[P]` (Implemented / Simulated-with-generated-data / NVIDIA-compatible-adapter / Planned) | Per-capability claim boundary, audited at G4 | `source_class` taxonomy (`official_record`, `source_record`, `sensor_inferred`, `model_inferred`, `synthetic`, etc. — Doc 05 §3) + M0–M6 maturity scale | **These are two different axes, not a rename.** Old `[I]/[S]/[A]/[P]` answered "is this real or a placeholder for the demo." New `source_class` answers "what kind of evidence is this." New M0–M6 answers "how mature/integrated is this component." A `[S]`-labeled old capability could map to `source_class: synthetic` **and** any M-level, depending on how far its *engine* (not just its data) has progressed. |
| D-numbered gates (e.g. `D4–D13c` for the London identity/planning chain, `a3·D2`, `a6·D1`, `a9`) | Fine-grained per-artifact certification IDs, specific to the London/NYC build | No direct equivalent | These are the most granular proof references in the old corpus and currently have **no home** in the new docs at all. Recommend keeping a short appendix (or this crosswalk) as the permanent index, since the new maturity table (Doc 04 §4) only says things like "CER: strong architecture, incomplete engine" — it does not cite D4–D13c as the evidence for that claim. |
| "Closed pre-hero" / "closed" (per flow/city) | A flow/chain is fully certified except for final hero-subject selection | "Closed at bounded proof level" / "closed in current ledger" / "closed at functional proof level" (used for ASK v1.1, Metropolis/VSS, Omniverse/WebRTC R5) | Same rhetorical shape, but the new docs use "closed" more loosely across bigger units (whole subsystems like Metropolis/VSS) than the old docs did (specific chains like D4–D13c). When you see "closed" in the new docs, ask which old D-numbered gate(s) it's actually resting on. |
| **Documentation inconsistency to fix:** Doc 03 §6.14 (Spatial Agent) states maturity as `"D13/R5 functional proof closed"` | Should be expressed on the M0–M6 scale like every other agent in the same document | — | This is a leftover from the old naming convention that slipped into the new doc. Recommend correcting to something like `M2/M3 — functional proof closed (formerly tracked as D13/R5); product UI still needed`, so the document is internally consistent with its own maturity scale. |

---

## 4. Simulation/optimization/perception — old L6/L7 ↔ new intelligence modes

| Old (Architecture doc, L6/L7) | New (Doc 02 intelligence modes) | Status carries forward? |
|---|---|---|
| Twin / world (Omniverse/OpenUSD scene) | SPATIAL / Omniverse / GIS intelligence mode (Doc 02 §12) | Yes. Old "hero-neighbourhood NYC OpenUSD twin" plan maps to the SPATIAL roadmap's R1 (native Kit panel) through R7 (hero-neighbourhood twin) — same sequencing logic, same "hero-neighbourhood before citywide" discipline, just re-homed under SPATIAL instead of L6. |
| Domain simulators (SUMO, pandapower, EPANET) | SIMULATE intelligence mode (Doc 02 §15) | Yes, directly. Same tool list (SUMO first, then pandapower/EPANET), same M0/M1 maturity assessment. |
| World-model rollouts (Cosmos Predict/Transfer) | Not present in the new docs at all | **Dropped from near-term scope.** Cosmos isn't mentioned anywhere in Docs 01–05. It still exists in the old Full Vision Completion Map as a Full-Vision-tier item — treat it as still-valid-but-far-future unless deliberately re-added. |
| Optimisation (cuOpt) | SCHEDULE / OPTIMIZE intelligence mode (Doc 02 §14) | Yes, directly — cuOpt is named as the tool inside the new mode's "data and functions needed" and the Schedule/Optimization Agent's tool list. |
| Perception / vision (Metropolis, DeepStream, VSS, grounding-dino) | PERCEPTION / VSS / Metropolis intelligence mode (Doc 02 §11) | Yes, directly — same tools, same "candidate observation, never a finding" governance principle, now formalized as the `CandidateObservation` packet with a hard rule (Doc 05 §9) that it can never equal a violation/finding/enforcement fact/identity/dispatch signal. |

---

## 5. Flows / cartridges ↔ new modes (important gap)

**This is the biggest structural gap in the new doc set.** The old "Flow 1–7" cartridge model (one spine + seven pluggable scenario cartridges, each with its own entity schema, data sources, optional simulator, scenario script, and narrative) has **no equivalent concept anywhere in the new authoritative docs.** The new docs are organized entirely around cross-cutting intelligence modes (WATCH, ASK, CHECK, etc.), not vertical scenario cartridges.

| Old Flow | Old status (per Full Vision Completion Map) | Nearest new-doc equivalent |
|---|---|---|
| Flow 1 — Situational status (descriptive query) | `[P]` — cheapest new cartridge | ASK mode (subject/entity/patch-queue answer families) + WATCH mode |
| Flow 2 — Construction-compliance cascade (NYC) | `[I]` certified — the golden path, Gate G1 | No single mode owns this; it would now be expressed as a combination of EVENT/INCIDENT + GRAPH + CHECK + BRIEF + PLAN outputs over a specific entity scope |
| Flow 2-London — same cascade, second city | `[I]` closed pre-hero (D4–D13c chain) | Same as above, scoped to London entities |
| Flow 3 — Resilient city (fire + road + air, London) | `[P]` | EVENT/INCIDENT + GRAPH cross-domain dependency edges (still a gap in new docs too — Doc 02 §3 lists "energy/water/transport dependencies" as a GRAPH gap) |
| Flow 4 — Crowd surge / major event | `[P]`, Platform v2 | No mode explicitly covers crowd dynamics; would fall under SIMULATE + EVENT |
| Flow 5 — Flood / asset-dependency cascade | `[P]`, Platform v2 | SIMULATE mode (Doc 02 §15 lists EPANET/weather-flood simulator as a data need) |
| Flow 6 — Planned shutdown sequencing (oil & gas) | `[P]`, Full Vision | SCHEDULE/OPTIMIZE mode |
| Flow 7 — Civic service + sensor fusion | `[P]`, Platform v1 | PERCEPTION + EVENT + QUALITY modes |

**Recommendation:** decide explicitly whether "flows/cartridges" survive as a *packaging* concept layered on top of the new modes (a flow = a named bundle of mode configurations + entity scope + data sources for one scenario), or whether the mode-based framing fully replaces cartridges. The new docs are silent on this, which risks quietly losing a genuinely useful packaging idea (how the system demos and sells one scenario at a time) in the shift to mode-first architecture.

---

## 6. Agent roster — old ↔ new

| Old (Architecture doc §4 + Full Vision Completion Map §3) | New (Doc 03 agent roster) | Status carries forward? |
|---|---|---|
| Supervisor / orchestrator | Orchestrator (Doc 04 §3.5) — no longer called an "agent," now the governing runtime itself | Renamed and re-scoped: no longer one agent among many, it's the thing that governs all agents. |
| Domain agents (per cartridge: land/permits, mobility, utilities, public-safety, oil-rig) | No direct equivalent — replaced by cross-cutting agents (Watch Scout, Event/Incident, etc.) that aren't domain-scoped | **Dropped as a concept.** Domain-specific reasoning is now expected to live inside entity/relationship ontologies and constraints, not in dedicated per-domain agents. |
| Tool agents: cuGraph query | Graph Context Agent (§6.2) | Yes, folded in as one of its tools. |
| Tool agents: retrieval (cuVS / NeMo Retriever) | Not named as a distinct agent — implicit inside RECALL's "optional embedding index" | Present but demoted from "agent" to "data/function needed." |
| Tool agents: simulation | Simulation Agent (§6.13) | Yes, directly. |
| Tool agents: cuOpt | Schedule / Optimization Agent (§6.12) | Yes, directly. |
| Tool agents: vision/VSS | Perception / Media Agent (§6.5) | Yes, directly. |
| Tool agents: forecasting | No direct equivalent named | Not carried forward explicitly — closest fit would be SIMULATE or a future PLAN sub-capability. |
| Object-tagging agent (3D↔graph bridge) | Spatial Agent (§6.14) — "entity↔prim resolver" tool | Yes, folded in as one of Spatial Agent's tools rather than its own named agent. |
| Persona / briefing agents | Briefing Agent (§6.8) — persona rendering is now a tool ("persona renderer") inside Briefing Agent, plus PERSONA listed as its own platform/commercial mode (Doc 02 intro) | Mostly yes — persona rendering survives, no longer a separate agent per persona. |
| Guardrail / governance agent | Split into: Authority Gate Agent, Claim Audit Agent, Trace Auditor, Policy Evaluator, Approval Lifecycle Agent (§3.3, "governance agents") | Yes, and now more granular — one old agent became five specialized governance agents. |
| *(new, no old equivalent)* | Identity Resolution Agent (§6.1) | New — the old docs didn't have a dedicated identity-resolution agent; entity resolution was treated as part of L2 ingestion, not an active agent. |
| *(new, no old equivalent)* | Watch Scout Agent, Diff Scout Agent, Data Quality/Maturity Agent, Synthetic/Scenario Agent | New — these background "scouting" agents are the most genuinely novel addition; nothing in the old roster proactively watched for review-worthy situations. |
| *(new, no old equivalent)* | Evidence Sufficiency / CHECK Agent (§6.6) | New — CHECK didn't exist as a concept in the old docs at all (see §7 below). |

---

## 7. CHECK — genuinely new, no old equivalent

CHECK (evidence sufficiency / claimability / contradiction / freshness / boundary validation) has **no direct predecessor** in the old docs. The closest relatives were:

- The old **claim-boundary labels** `[I]/[S]/[A]/[P]` — but those were a documentation/demo-honesty convention, applied by the humans building the demo, not a runtime validation engine.
- The old **grounded narration gates** (subset-grounded / anti-echo / min-coverage / subject-isolated) mentioned in Doc 04's L9 governance table — these were narrower, LLM-output-specific guardrails, not a general evidence-sufficiency engine covering WATCH/BRIEF/RECALL/DIFF/PERCEPTION/SPATIAL/PLAN/SCHEDULE/SIMULATION outputs the way new CHECK does.
- **NeMo Guardrails** — old docs' agent-behavior constraint layer. CHECK is a superset in intent but is evidence/claim-specific rather than a general guardrail framework.

Treat CHECK as the one clean case of a real, new capability being introduced rather than an old capability being renamed — which is also why it's correctly flagged as the single highest-priority gap across both the old and new material.

---

## 8. Entity types — old schema enum ↔ new entity families

| Old (`txr_citybrain_schema_v1.py` `EntityType` enum) | New (Doc 05 §20 entity families) | Status carries forward? |
|---|---|---|
| `parcel` | Parcel (under "Shared anchors") | Yes, directly. |
| `building` | Building (under "Shared anchors") | Yes, directly. |
| `permit` | Permit (under "Events and workflow") | Yes, directly. |
| `party` | Party (under "Party layer") | Yes, directly — the old "party-with-role, role lives on the edge" design principle also survives unchanged into the new "Role / Interest Assignment" entity. |
| `inspection` | Inspection (under "Events and workflow") | Yes, directly. |
| `road_segment` | Road Segment (under "Shared anchors") | Yes, directly. |
| `event` | Event (under "Events and workflow") — now also formalized as `EventPacket` (Doc 05 §8) | Yes, and significantly more developed — the whole new Event Fabric layer (L4) exists to give this entity type real runtime semantics. |
| `resource` | No direct equivalent named — closest is the generic "Component" or "Instrument / Control Point" under "Systems / operations" | Ambiguous — worth explicitly confirming whether old `resource` (which covered eVTOL + crew) maps to a specific new entity type or needs to stay as its own type. |
| `unit` (reserved) | Unit (under "Shared anchors") | Yes — still listed, still not fully activated in either doc set. |
| `development` (reserved) | Not explicitly listed in Doc 05's initial entity families | Dropped from the initial list — may need re-adding if development-tracking use cases return. |
| `sensor` (reserved) | Instrument / Control Point (under "Systems / operations") — approximate match | Likely yes, but renamed; confirm before assuming equivalence. |
| `infrastructure_asset` (reserved) | Facility / System / Component / Service Point (under "Systems / operations") | Yes, but the old single `infrastructure_asset` type is now split across several more granular new types. |
| `transit_node` (reserved) | Stop/Station, Terminal/Depot (under "Mobility and public realm") | Yes, split into two more specific types. |
| *(new, no old equivalent)* | Community, Address, Site (under "Shared anchors") | New — broader geographic/administrative anchors than the old schema had. |
| *(new, no old equivalent)* | Route, Traffic Signal, Camera, Signage Asset, Bollard/Barrier (under "Mobility and public realm") | New — much more granular street-furniture/mobility asset coverage than the old 13-type enum. |
| *(new, no old equivalent)* | Work Order, Violation, Transaction (under "Events and workflow") | New. |
| *(new, no old equivalent)* | Organization, Department (under "Party layer") | New — the old schema only had `party`; organization/department are now split out. |

**Note:** the old canonical ID format (`{entity_type}:{country}-{city}:{id_system}:{native_id}`, e.g. `building:us-nyc:bin:3395389`) is not restated anywhere in the new docs. Confirm whether it still applies to `EntityPacket.canonical_entity_id` (Doc 05 §5) — the new packet schema doesn't specify an ID format, which is a gap worth closing explicitly rather than assuming.

---

## 9. NVIDIA stack components — where each one lives now

The new docs never mention NVIDIA products by a dedicated "stack mapping" section the way the old Architecture doc did. They're now scattered as "tools/skills" inside individual agents.

| Old stack component | New home |
|---|---|
| NIM, NeMo Agent Toolkit | Implicit inside "LLM reader/writer" roles (Doc 03 §2) — not named as a specific product anywhere in the new docs |
| NeMo Guardrails | Implicit inside CHECK / Authority envelope — not named specifically |
| RAPIDS cuDF, cuSpatial | Not mentioned; implicit in L1/L2 ingestion and identity resolution |
| cuGraph / nx-cugraph | Graph Context Agent tools (Doc 03 §6.2) |
| cuOpt | Schedule/Optimization Agent tools (Doc 03 §6.12), SCHEDULE mode data needs (Doc 02 §14) |
| SUMO, pandapower, EPANET | Simulation Agent tools (Doc 03 §6.13), SIMULATE mode data needs (Doc 02 §15) |
| Omniverse / OpenUSD | Spatial Agent (Doc 03 §6.14), SPATIAL mode (Doc 02 §12) |
| Metropolis / DeepStream, VSS, grounding-dino | Perception/Media Agent (Doc 03 §6.5), PERCEPTION mode (Doc 02 §11) |
| Cosmos (Predict/Transfer/Reason) | **Not mentioned anywhere in the new docs.** Still valid per the old Full Vision Completion Map (Full Vision tier), but currently orphaned from the new roadmap entirely. |
| cuVS / NeMo Retriever | Not named; implicit in RECALL's "optional embedding index" (Doc 02 §8) |
| Triton, NGC/Docker | Not mentioned — infrastructure/serving detail the new strategy docs don't operate at this level of. This is expected (strategy vs. ops docs) but means these still live only in the old docs. |
| Earth-2 / CorrDiff | Not mentioned anywhere in the new docs — same as Cosmos, orphaned from current roadmap, still valid per old Full Vision map. |

---

## 10. Quick-reference glossary (old term → new term, one line each)

```text
Flow 2 (construction-compliance cascade)   → no single mode; ask/event/graph/check/brief/plan composite
Cognition engine / action core             → Orchestrator (L5) + PLAN/SCHEDULE/SIMULATE modes
9-stage orchestration (RECALL→COMPLETE)    → ASK G1–G8 flow (narrower scope; generalization still pending)
EvidenceBundle                             → EvidencePacket
Claim labels [I]/[S]/[A]/[P]               → source_class taxonomy + M0–M6 maturity (two separate axes)
SOUL personas                              → PERSONA mode / persona renderer (inside Briefing Agent)
Object-tagging agent                       → Spatial Agent (entity↔prim resolver tool)
Domain agents (per cartridge)              → dropped; replaced by cross-cutting agents
D4–D13c / D-numbered gates                 → no equivalent; needs explicit re-citation under new M-levels
G0–G4 sprint gates                         → no equivalent; sprint-specific, not restated
"Closed pre-hero"                          → "closed at bounded/functional proof level"
Metropolis/VSS (perception)                → PERCEPTION mode + Perception/Media Agent
Omniverse/WebRTC R5                        → SPATIAL mode + Spatial Agent
ASK v1.1 (as referenced in new docs)       → same name, now explicitly = the sealed G1–G8 flow implementation
NeMo Guardrails / grounded-narration gates → CHECK (broader, evidence/claim-specific superset)
governed deterministic oracle              → "deterministic gates own truth" (L5 rule, same principle)
```

---

## 11. Open items this crosswalk surfaces (not yet resolved by either doc set)

1. **Flows/cartridges have no home in the new framing** — decide if they survive as a packaging layer (§5).
2. **D-numbered gates and G0–G4 sprint gates have no new-doc citation** — the new "Current state snapshot" table (Doc 04 §4) makes claims ("ASK v1.1 closed") without pointing back to the specific old proof artifact that earned that claim.
3. **Doc 03 §6.14 still contains an old-style label (`D13/R5`)** inside an otherwise M-scale document — a direct inconsistency to fix (§3).
4. **Canonical entity ID format** (`{entity_type}:{country}-{city}:{id_system}:{native_id}`) is not restated in the new EntityPacket schema — confirm it still applies.
5. **Cosmos, Earth-2/CorrDiff, Triton, NGC/Docker** are absent from the new docs entirely — confirm these are intentionally deferred (Full Vision tier) rather than accidentally dropped.
6. **`resource` and `development` entity types** from the old schema don't have a confirmed 1:1 new-doc equivalent — resolve before the next entity-registry engineering pass.

