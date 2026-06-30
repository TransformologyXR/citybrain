# CityBrain RTX — Architecture

*NVIDIA Urban AI demonstration · architecture document*
*Status: DRAFT v0.1 — for review. Companion docs: Vision · Exec Summary · Roadmap/Rules · Synthetic-Data Stream.*

> Read the **Vision** doc first for the thesis and the demo flows. This doc is the *how*: the spine, the cartridges, the agents, the NVIDIA mapping, the 3D pipeline, the data factory, serving, and governance.

---

## 1. Architecture in one picture

CityBrain RTX is a **spine** (built once) plus **cartridges** (slot-in scenarios). The spine is nine layers; a cartridge is a bundle of {entity schema, data sources, optional domain simulator, scenario script, narrative}.

![Nine-layer spine](CityBrain_RTX_diagram_spine.svg)

*Figure 1 — the nine-layer spine. Blue = data foundation, amber = the cognition core, grey = platform layers; governance (L9) wraps all layers, and the data factory feeds in from below.*

---

## 2. The spine — nine layers

### L1 · Ingestion & adapters
Per-source adapters normalise heterogeneous inputs (GIS, BIM, CSV, GTFS, APIs, document text) into the canonical schema. GPU-accelerated with **RAPIDS cuDF** for tabular at scale and **cuSpatial** for geospatial joins (point-in-polygon, nearest-asset, buffer queries). Each adapter is small, testable, and owned by the cartridge it serves; the spine ships the base-layer adapters (Overture, MS footprints, WorldPop, ERA5).

### L2 · Canonical entity registry
The heart of "the city understands the same thing across silos." Every parcel, building, unit, road segment, permit, inspection, asset, sensor and event resolves to a **canonical entity** with: a stable ID (Overture-grounded where possible), **provenance** (which source, when, how derived), and a **confidence** score. This is the layer that turns a DLD record + a DM permit + a 311 complaint + a camera detection into *one* building.

### L3 · Multiplex semantic graph (cuGraph)
A typed, multi-relationship graph over the registry: `parcel → building → unit`, `permit → developer → inspector`, `road → segment → asset`, `building → energy → water`, `asset → depends-on → asset`. **cuGraph / nx-cugraph** run the traversals, impact propagation, centrality and shortest-path queries that power contextualisation and cascade analysis. The graph is the contextualisation layer of the digital twin.

### L4 · Observation / event fabric
The time-aware layer: events (vision detections, sensor crossings, permit filings, dispatch records), signals (traffic speeds, smart-meter curves, air quality), and their temporal state. Feeds the cognition engine with "what is happening now" and feeds the graph with state changes.

### L5 · Cognition engine — the action core
A generalised version of the existing **9-stage governed orchestration** (RECALL → … → COMPLETE) wrapped around **one action core**: *simulate → optimise → act → monitor*, entered three ways:

- **Query** (descriptive): situational awareness over the live graph.
- **Incident** (reactive): detect → understand → alert → action core → fix.
- **Plan** (proactive): plan → action core → execute → monitor.

Built on **NeMo Agent Toolkit + NIM** for the agents and model serving, with **forward dynamics** (predict what happens next) and **inverse dynamics** (given a desired state, what action produces it). A no-LLM deterministic path exists for the parts that must be exact (identity, constraint checks), matching the existing City Brain design.

### L6 · Simulation & optimisation
- **Twin / world:** Omniverse / OpenUSD scene of the city.
- **Domain simulators:** SUMO (traffic), pandapower (grid), EPANET (water) — calibrated to harvested donor-city data.
- **World-model rollouts & long-tail:** Cosmos (Predict for rollouts, Transfer for augmenting rare conditions).
- **Optimisation:** **cuOpt** for dispatch, routing, kerbside allocation, shutdown sequencing.

### L7 · Perception / vision (the 15%)
The blueprint's home turf, consumed as an input: **Metropolis / DeepStream** pipelines and **VSS** (Video Search & Summarization) turn synthetic camera streams into structured events, with **grounding-dino**-style open-vocabulary detection where useful. Output is event JSON that lands in L4 and resolves through L2.

### L8 · Experience & personas
Two faces plus a conversational layer:
- **Omniverse 3D control room** — the cinematic twin; entities light up, eVTOLs dispatch, cascades render.
- **Web map** — the operational view.
- **SOUL personas** — executive / planner / operator / analyst framings of the same evidence chain.
- **Visible agent-trace panel** — *the* differentiator: which agents fired, what tools they called, the plan they followed, what awaits human approval.

### L9 · Governance
Cross-cutting, not a final step: provenance and confidence travel with every claim; **human-in-the-loop** approval gates on consequential actions; **NeMo Guardrails** constrain agent behaviour; and the **claim-boundary labels** (below) are enforced as metadata on every capability the demo surfaces.

---

## 3. The cartridge model

The cartridge model now has two slots:

```text
one city = one city core cartridge
each flow = one flow sub-cartridge mounted onto that city core
```

A **city core cartridge** turns the spine into a reusable city foundation. It contains the city's native IDs, geography/boundaries, source ledger, base EvidenceBundle style, face/NIM route conventions, and accepted limitations. NYC, London, and Chicago should not be rebuilt from zero when a new flow is added.

A **city-flow sub-cartridge** adds only the flow-specific material:

| Part | What it is |
|------|------------|
| Flow sources | Extra sources required by the flow, beyond the accepted city core |
| Flow joins | New joins from flow records into the city's native IDs and geography |
| EvidenceBundles | Flow-specific evidence contract and claim boundaries |
| Replay/live proof | Deterministic replay, live NIM proof, face route, or equivalent runtime gate |
| Hero/freeze gate | A bounded proof package that carries source limitations forward |

**Adding a flow to an accepted city** = mount a sub-cartridge, do not rebuild the city. The naming convention is `{CITY}-F{FLOW}X-D{DAY}`; the `X` means extension on an already-existing city core. For example, `LON-F3X-D1` is a London Flow 3 expansion scout, not a fresh London build. See `TXRCityBrain_CityCore_Subcartridge_Model.md` for the live slotting ledger.

---

## 4. Agent architecture

**Framework:** NVIDIA-native core (**NeMo Agent Toolkit + NIM + NeMo Guardrails**) with a mature orchestration framework (**LangGraph**) integrated for graph-structured, inspectable agent flows. This satisfies the NVIDIA-native requirement *and* shows fluency with the wider agent ecosystem.

**Roster:**

| Agent | Role |
|-------|------|
| Supervisor / orchestrator | Routes the request to the right entry point and domain; owns the plan |
| Domain agents (per cartridge) | Land/permits, mobility, utilities, public-safety, oil-rig — domain reasoning |
| Tool agents | cuGraph query · retrieval (cuVS / NeMo Retriever) · simulation · cuOpt · vision/VSS · forecasting |
| Object-tagging agent | Names OpenUSD prims and binds them to canonical entities (the 3D ↔ graph bridge) |
| Persona / briefing agents | Render the evidence chain per SOUL persona |
| Guardrail / governance agent | Enforces NeMo Guardrails, provenance, confidence and human-approval gates |

**Agent-trace panel:** every agent step is emitted as a structured trace (agent, tool, inputs, outputs, confidence, approval-required flag) and streamed to L8. It is a feature, not debug output — "watch the agents reason."

---

## 5. NVIDIA stack mapping

Each capability maps to a specific NVIDIA component and carries a **claim label**: **[I]** Implemented · **[S]** Simulated-with-generated-data · **[A]** NVIDIA-compatible-adapter · **[P]** Planned.

| Capability | NVIDIA component | Claim (target) |
|------------|------------------|----------------|
| City digital twin | Omniverse / OpenUSD | [S] |
| Synthetic video / long-tail | Cosmos (Transfer, Predict, Reason) | [S] |
| Procedural / agent-based data | Custom + base layers | [I] |
| Vision events | Metropolis / DeepStream / VSS | [S] |
| Open-vocabulary detection | grounding-dino | [S] |
| Agents & orchestration | NeMo Agent Toolkit + NIM | [I] |
| Guardrails | NeMo Guardrails | [I] |
| Data curation / fine-tuning | NeMo Curator | [P] |
| GPU tabular | RAPIDS cuDF | [I] |
| GPU geospatial | cuSpatial | [I] |
| GPU graph | cuGraph / nx-cugraph | [I] |
| Vector / retrieval | cuVS / NeMo Retriever | [I]/[A] |
| Optimisation | cuOpt | [I] |
| Model serving | NIM / Triton | [I]/[A] |
| Packaging / registry | Docker / NGC | [I] |
| Weather / flood (advanced) | Earth-2 / CorrDiff | [P] |

Labels are targets for the sprint; the Roadmap doc tracks actual status per artifact, and the Mission Control tracker shows it live.

---

## 6. The 3D pipeline (twin ↔ graph)

The pipeline that makes "every visible object resolves to an entity" real:

![Twin-to-graph 3D pipeline](CityBrain_RTX_diagram_3dbridge.svg)

*Figure 2 — the twin↔graph pipeline: geometry → OpenUSD scene → object-tagging agent (binds prims to entity IDs) → status overlay.*

- **Geometry in:** donor-city 3D (NYC 3D Building Model, Netherlands 3DBAG, Helsinki semantic model) + Microsoft ML footprints + heights for gap-fill.
- **Scene:** authored to **OpenUSD** (Unreal as an optional authoring/render path into Omniverse). Helsinki's "visual twin vs semantic twin" split is the model: pretty mesh for view, semantic model for reasoning.
- **Bind:** the **object-tagging agent** walks the USD stage, names prims, and binds each to a canonical entity in L2 — this is the bridge that lets a click in the 3D twin open the graph neighbourhood, and lets a graph event light up the right building.
- **Runtime:** status overlays driven by L4/L5 — congestion, risk, dispatch, cascade.

---

## 7. The data factory (parallel stream — summary)

The spine consumes the factory's output; the factory is its own workstream (full detail in the **Synthetic-Data Stream** doc). Pipeline:

![Data factory pipeline](CityBrain_RTX_diagram_datafactory.svg)

*Figure 3 — the data factory: 8 donor cities normalised, simulated, validated, then fed into ingestion.*

Donor strengths (one line each): **NYC** master operational · **London** UK resilience/energy · **Helsinki** semantic 3D · **Amsterdam/NL** 3D+traffic+kerbside · **Dubai** DM–DLD real-estate-gov · **Singapore** real-time API + camera "eyes" · **Chicago** civic sensor fusion · **Melbourne** crowd/kerbside. Base layers everywhere: Overture, MS footprints, WorldPop, ERA5/Open-Meteo.

**Core principle:** don't invent distributions — transplant real ones, then validate against them.

---

## 8. Serving & deployment

- **Runtime hardware:** dual-node **DGX Spark + RTX 5090** (the existing City Brain rig). vLLM + Gemma for generation, Ollama `nomic-embed-text` for embeddings; an **RTX-only path** exists for portability.
- **Serving:** **NIM** microservices for models where available, **Triton** for custom serving, behind a thin API the dashboard and agents call.
- **Packaging:** **Docker** images, pulled/pushed via **NGC**. Pin versions; snapshot every green state.
- **Infra scars to respect (from prior builds):** `docker cp` model weights out *before* `docker rm`; persist `HF_TOKEN` in `~/.bashrc`; use `--enforce-eager` for CUDA-graph failures.

---

## 9. Governance & guardrails

Governance is woven through, not bolted on:

- **Provenance** — every entity and claim records source, time, and derivation.
- **Confidence** — every resolved entity and prediction carries a confidence score, surfaced in the UI.
- **Human-in-the-loop** — consequential actions (dispatch, enforcement, shutdown changes) are *recommended*, with an explicit approval gate; the agent-trace panel flags what awaits sign-off.
- **NeMo Guardrails** — constrain agent tool use and output.
- **Claim-boundary enforcement** — the [I]/[S]/[A]/[P] label is metadata on every surfaced capability, so the demo never implies more than it does.

---

## 10. Build invariants (carried from the Rules)

These hold across every layer and cartridge (full list + rationale in the Roadmap/Rules doc):

1. Generate broadly, certify narrowly.
2. Every output has an acceptance gate.
3. Kill generic / placeholder content.
4. Claim boundary is a feature.
5. One golden path fully certified before breadth (Flow 2).
6. Learn the gate rules before mass-generating.
7. Build the eval/acceptance harness on day 1.
8. Single source of truth for multi-agent codegen — let tests decide truth.
9. Snapshot every green state + pin the environment.
10. Time-box the wow (Omniverse polish eats days).

---

## 11. Open decisions

- Final golden-path scenario confirmation (current working example: Flow 2).
- Depth of the Omniverse 3D control room vs the web map for the first cut (time-box per Rule 10).
- Which donor-city packs land in the first harvest (recommended order: NYC → London → Helsinki/Amsterdam 3D → Singapore perception → Dubai DM–DLD → Chicago/Melbourne specialist).
- Extent of Cosmos use in v1 (Flow 5 is the natural showcase).

> Next doc: **Roadmap / Plan / Rules / Workflow** — the day-by-day sprint across the spine and the data factory, with gates, dependencies, risks and the division of labour between you and your agents.
