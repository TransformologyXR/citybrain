# TXR City Brain — Project Onboarding (for Codex / ChatGPT)

*Context brief, current as of this build session. You may already have the original project handover plus the schema (`txr_citybrain_schema_v1.py`), the ER diagram, and the acceptance harness (`txr_citybrain_harness.py`). **This document does not repeat those** — it captures the decisions and current state that those files don't contain, so you can work without re-deriving the project's direction.*

---

## 1. What this is, in one breath

**TXR City Brain** is a governed, cross-domain *city operations brain* that sits **on top of** NVIDIA's own **Omniverse Blueprint for Smart City AI**. NVIDIA's blueprint gives you the digital twin (Omniverse), synthetic data (Cosmos), trained perception (NeMo Curator + TAO), and narrow video-analytics agents (Metropolis/VSS) — *the twin and the eyes*. It deliberately does **not** do cross-domain reasoning, causal/predictive simulation, optimisation/dispatch, governance/provenance, or general agentic cognition. **That gap is the brain. This project builds the brain.**

It is **not a from-scratch concept.** A working predecessor — **City Brain Phase 1** — was already shipped (a 5-day sprint, April 2026): a real, governed executive-intelligence system for Dubai (DLD real-estate transactions + DM structural/permits), built as a deterministic 9-stage pipeline where *code computes every number and the LLM only narrates and routes.* TXR City Brain takes that proven pattern, re-platforms it onto NVIDIA's native AI stack, and generalises it from one city to many. It is the portfolio piece for an **NVIDIA Urban AI Solution Architect** application.

**The pitch:** *"NVIDIA's blueprint gives you the twin and the eyes. I built the brain — and I'd already shipped a working version of it once, for one city, before generalising it onto NVIDIA's native stack."*

---

## 2. The plan we're executing (this is the part not in the other files)

### Two tracks, one spine
The whole system is a **9-layer spine** (ingestion → canonical registry → semantic graph → event fabric → cognition → simulation/optimisation → perception → experience → governance). We are building it via **two parallel tracks that join at defined points**:

- **Track A — the application slice.** A single thin vertical thread through the spine, end to end, shown as *one connected story*: an event flows in → canonical registry → graph → the agent reasons across domains → optimiser proposes an action → an evidence briefing comes out with provenance. This is the **descoped deliverable for the NVIDIA application.**
- **Track B — the continuing build.** Widening and deepening that same spine (synthetic data pipeline, brain deepening, 3D bridge, the dedicated GPU machines). Runs alongside; **never gates the application snapshot.**

### The slice is scoped hard
- **Flow 2 — the construction-compliance cascade**, on **real NYC data**, end to end.
- **NYC is the running city. Dubai is the re-anchoring *narrative*** ("here it is on real NYC shapes; here's how it re-anchors onto Dubai geometry, the production target"). This takes the blocked Dubai manual export **off the critical path**.
- Everything else — the full Metropolis/VSS vision pipeline, the 3D click-through bridge, the other flows, Cosmos, the dedicated 3090/4070 — is **Track B, labelled honestly in the demo, not hidden.**

### Cartridge order = validation order
The headline architectural claim is *"one spine, many cartridges — add a scenario without touching the spine."* You don't assert that; you demonstrate it. The build order is **NYC → London → Dubai → oil & gas**. NYC certifies the spine; each later cartridge that slots in *without reopening the spine* is a live proof. **London is the real test.** Oil & gas is a branch with a single trigger: *the city slice certifies green with time to spare.*

---

## 3. Architecture (only what you need for adapter/registry/graph work)

The spine layers that matter for the current work:

| Layer | Role | Stack |
|---|---|---|
| **L1 Ingestion & adapters** | harvest + map multi-source records to canonical form | cuDF / cuSpatial; per-source adapters |
| **L2 Canonical entity registry** | identity, provenance, confidence — "the city understands the same thing across silos" | the canonical schema |
| **L3 Semantic graph** | multiplex relations over the registry | cuGraph |
| L4 Event fabric | real-time signals / triggers | — |
| L5 Cognition | action-core agent (NeMo Agent Toolkit + NIM) | proven on the DGX Spark |
| L6 Sim/optimise | domain simulators + cuOpt | — |
| L9 Governance (wraps all) | provenance, human-in-loop, guardrails | NeMo Guardrails |

**The adapters are L1→L2.** They are where the *real engineering core of L2* gets built: the **identity resolver** (the thing Phase 1 lacked — it used bare strings with fuzzy matching; the new system assigns real canonical IDs with provenance and a confidence score).

---

## 4. The canonical schema (summary — full definition is in `txr_citybrain_schema_v1.py`)

The contract is **core + provenance envelope**:
- **Canonical core** — a small, typed, city-agnostic field set. The *only* thing the graph and the agent read. This is the frozen contract.
- **Provenance envelope** — the raw source record(s), untouched, namespaced by source, with field-level `{source, time, derivation, confidence}`. All city-specific richness lives here.
- **Adapters** map native → core per (city, dataset). **Adding a city = writing adapters. The core never changes.**
- **Geometry is the universal resolver** — every spatial entity carries a typed geometry with a *guaranteed representative point*, so even key-less records resolve by spatial join (cuSpatial).
- **`ext` namespace** for city-specific-but-useful fields the core doesn't require (e.g. `ext['nyc.zonedist1']`).

**Identity triad on every entity:** `canonical_id` + `provenance[]` + `confidence`. Canonical ID format: `{entity_type}:{country}-{city}:{id_system}:{native_id}` (e.g. `building:us-nyc:bin:3395389`). Raw source keys live in `provenance[].source_id`, not as entity fields.

**Entities:** 8 core (Parcel, Building, Permit, Party, Inspection, RoadSegment, Event, Resource-minimal) + 5 reserved (Unit, Development, Sensor, InfrastructureAsset, TransitNode — *declared but not populated in v1; do not build these*).

**Two design choices that affect adapter code:**
- **Party-with-role.** One Party entity (person/org). The role (owner / contractor / applicant / inspector / buyer / seller) lives on the **edge**, never as a column. So a permit produces several Party nodes plus role-typed edges (`filed_by`, `performed_by`, `designed_by`), and a new city's role is just new edge data.
- **Event two-level taxonomy.** `category` (closed enum: observation / incident / request / transaction / planned) + `type` (open string, e.g. `"construction_complaint"`). **Resolution to entities is via EDGES** (`resolves_to` / `affects`) that carry their own confidence — because a geometry-only link is ~0.70 and that number must live on the relationship. Event is the workhorse: it absorbs complaints, 311, collisions, speed readings, dispatches, and DLD transactions.

---

## 5. The data

### Donor cities
NYC + Chicago harvested at 100% real. London / Helsinki / Melbourne have real datasets blocked by diagnosed, fixable non-credential bugs. Dubai needs manual export (the golden-path blocker *for the Dubai cartridge* — not for the NYC slice). Singapore + other cities: API keys obtained, not yet harvested (future "eyes"/sensor donors).

### NYC Flow 2 footprint (what the adapters consume)
Parcels/buildings: **PLUTO / MapPLUTO**. Permits/people: **DOB NOW filings**, **DOB permit issuance**. Construction events: **DOB complaints**. Broader signals: **311**, **DOT traffic speeds**, **motor vehicle collisions**. (EMS, fire, energy/water, events, restaurant inspections are *later cartridges* — out of scope for the slice.)

### The identity backbone (confirmed against the real harvest)
- **BBL** (Borough-Block-Lot) = parcel key. **BIN** (Building ID) = building key. **Neither is universal.**
- PLUTO is BBL-only (lot-level, no BIN). DOB sets are BIN-rich. **DOB permit issuance has BBL empty** (derive it from borough+block+lot). **Collisions and traffic speeds carry no land key at all** — they resolve by geometry only.
- The same entity wears different field names per dataset (`bin` vs `bin__`, `job_filing_number` vs `job__`, `latitude` vs `gis_latitude`) and different date formats (ISO, `MM/DD/YYYY`, and `YYYYMMDDHHMMSS`). **This is the adapter's job to absorb.**

### What folds into existing entities (do not create new entities for these)
EMS/fire dispatch, permitted events, and DLD transactions → **Event** subtypes. Energy/water → **Building** observations. Restaurant inspections validate that **Inspection** is polymorphic (target can be an establishment, not just a permit/building).

---

## 6. Build rules (carry forward — these govern how you work)

1. **Generate broadly, certify narrowly.**
2. **Every output has an acceptance gate.**
3. **Kill generic** — fake-but-plausible content is the hardest bug to catch late; ground everything in real fields.
4. **Claim boundary is a feature** — label everything: **Implemented / Simulated / Adapter / Planned**.
5. **One golden path fully certified before breadth.**
6. **Learn gate rules before mass-generating.**
7. **Build the eval harness Day 1** (done — it's `txr_citybrain_harness.py`).
8. **Single source of truth** — manifests/tests/the harness decide, not docs.
9. **Snapshot every green state + pin environment.**
10. **Time-box the wow.**

---

## 7. Conventions

- **Name:** the project is **TXR City Brain** (the older `CityBrain_RTX_*` filenames are pending a rename pass).
- **Claim labels** on every artifact/output: `[Implemented]` / `[Simulated]` / `[Adapter]` / `[Planned]`.
- **Canonical IDs** follow `{type}:{country}-{city}:{id_system}:{native}`; city-agnostic in structure.
- **"Green" is defined by the harness**, not by inspection — see §9.

---

## 8. The hardware rig (for situational awareness)

| Machine | Role | Status |
|---|---|---|
| **DGX Spark** (Blackwell, ARM64) | Brain — NIM, NeMo Agent Toolkit, Guardrails | ✅ NIM (Llama 3.1 8B) live; ReAct agent confirmed |
| **RTX 5090 laptop** (Blackwell) | Twin + demo driver + Cosmos | 🟢 twin live @60fps; 🟡 Cosmos parked (procedural `[Simulated]` fallback) |
| **RTX 3090 PC** (Ampere, x86) | Data/graph/optimise — RAPIDS · cuGraph · cuOpt | 🔵 native-Ubuntu wipe imminent |
| **RTX 4070 PC** (Ada, x86) | Perception / dashboard | 🔵 native-Ubuntu wipe imminent |

**Reframe worth knowing:** the 3090/4070 on native Ubuntu are x86 + mature architectures — the *easiest* CUDA-X targets in the rig, not the hardest. The adapters (current work) need **none** of this hardware; they run on the Spark or any dev box. cuGraph/cuOpt (L3/L6) land on the 3090 once it's up.

---

## 9. Current state & how "done" is measured

**Done:** the canonical schema (designed, red-penned, runnable, validated against real NYC rows) and the acceptance harness (two tiers — invariant gates + Flow 2 acceptance expectations; it provably discriminates good/empty/broken inputs).

**Next:** the **NYC adapters → registry** (see the companion *Adapter Handover* doc).

**The harness is the source of truth.** Fed nothing, it reports invariants-green / Flow-2-**red** (exit 1). Each adapter you write turns one Flow 2 row green. When `F2-CASCADE` goes green — a construction complaint connected through building → permit → contractor → parcel — the golden path is wired. **That red→green progression is the definition of done.** Always run the harness; a green means something only because the harness fails when it should.

**Artifacts you should have / can refer to:**
- `txr_citybrain_schema_v1.py` — Pydantic models (the contract; runnable, self-validating).
- `txr_citybrain_schema_v1.schema.json` — JSON Schema, generated from the models.
- `TXRCityBrain_Schema_ERD.svg` — entity-relationship diagram.
- `txr_citybrain_harness.py` — the acceptance harness (gate a2).
- *Adapter Handover* (companion doc) — the spec for the work in front of you.
