# CityBrain RTX — Roadmap, Plan & Rules

*NVIDIA Urban AI demonstration · execution document*
*Status: DRAFT v0.1 — for review. Companion docs: Vision · Architecture · Exec Summary · Synthetic-Data Stream.*

> This is the *how we build it* doc. Read **Vision** for the thesis and **Architecture** for the structure. Here: the rules, the scope, the day-by-day, the gates, and who builds what.

---

## 1. Operating principles

Five principles govern every decision in the sprint:

1. **Golden path first.** Flow 2 (construction compliance cascade) is built and certified end-to-end *before* any breadth. A working spine + one certified flow is already a demo; everything else is additive.
2. **Two parallel streams.** Stream A (the spine / brain) and Stream B (the data factory) run concurrently, meeting at the ingestion boundary. Stream B has its own deep doc.
3. **Gate, don't guess.** Every artifact has an objective acceptance gate (a test the harness runs). "Done" means "passes its gate," not "looks finished."
4. **Single source of truth.** This Drive folder holds the canonical schema, scenario scripts, gate specs and these docs. Every agent re-reads from here. Tests decide truth, not audit prose.
5. **Time-box the wow.** Cinematic polish (Omniverse control room) is capped. The web map + agent-trace panel carry the Must-have story; 3D is upside.

---

## 2. The build rules (invariants)

These hold across every layer, cartridge and agent. They are scar tissue from prior builds — break them and the sprint slips.

| # | Rule | Why |
|---|------|-----|
| 1 | **Generate broadly, certify narrowly.** | Breadth is cheap to draft, expensive to trust. Certify a thin slice fully before widening. |
| 2 | **Every output has an acceptance gate.** | Without a gate, "done" is subjective and regressions are invisible. |
| 3 | **Kill generic / placeholder content.** | Generic output ("lorem", stub names, fake-but-plausible numbers) is the #1 credibility killer and the hardest bug to spot late. |
| 4 | **Claim boundary is a feature.** | Label every capability [Implemented] / [Simulated] / [Adapter] / [Planned]. Honesty reads as competence. |
| 5 | **One golden path fully certified before breadth.** | Flow 2 green first. Then cartridges. |
| 6 | **Learn the gate rules before mass-generating.** | Understand what "correct" means for an artifact type before producing many of them. |
| 7 | **Build the eval/acceptance harness on Day 1.** | The harness is the spine of the spine. It must exist before the code it judges. |
| 8 | **Single source of truth for multi-agent codegen.** | Many agents → one canonical spec + tests. Let tests arbitrate, not audit docs or agent memory. |
| 9 | **Snapshot every green state + pin the environment.** | `docker cp` weights out before `docker rm`; persist `HF_TOKEN`; `--enforce-eager` for CUDA-graph failures; pin versions; tag every green commit + image. |
| 10 | **Time-box the wow.** | Omniverse polish eats days. Cap it; protect the Must-haves. |

---

## 3. Scope (MoSCoW)

**Must** (no demo without these):
- Canonical schema + entity registry (identity, provenance, confidence).
- cuGraph semantic graph; one NIM agent on the action core; cuOpt optimisation.
- **Flow 2 end-to-end, certified** on synthetic data, with an evidence-backed briefing.
- The acceptance harness (Rule 7) and claim-labelling (Rule 4).
- One master donor city (NYC) + Dubai DM–DLD pack for Flow 2.
- Web map face + the visible agent-trace panel.
- A clean demo video of Flow 2 (Scene 0–6).

**Should** (strongly want; the "wow"):
- OpenUSD twin + the object-tagging 3D bridge + eVTOL dispatch visual.
- Real vision pipeline (Metropolis / VSS) on Cosmos-generated frames.
- 2–3 more flows as cartridges (Flows 1, 3, 7 — the cheap, flat-file ones).
- SOUL personas; GitHub repo + technical blog.

**Could** (upside if time):
- Flow 5 (flood / asset-dependency) at depth with Cosmos long-tail.
- Flow 6 (oil-rig cartridge) — the domain-swap flourish.
- LangGraph deep integration; Earth-2 / CorrDiff weather; more donor cities; Omniverse control-room polish.

**Won't** (explicitly out, this sprint):
- Production integration; live non-synthetic city data; full multi-city foundation; model fine-tuning (NeMo Curator) beyond a stub. All labelled [Planned].

---

## 4. The sprint (≈10 working days / 2 weeks, two streams)

### Phase 0 — Foundations & harness (Days 0–1)
- **Stream A:** repo + environment (Docker, NGC, NIM, pinned versions); canonical schema v1; spine skeleton (empty layers wired); **the acceptance harness** (Rule 7).
- **Stream B:** harvest donor city #1 (NYC); validation-harness skeleton; first canonical-schema mapping.
- **Gate G0:** harness runs and reports red/green on an empty Flow 2 stub; schema validates; environment snapshotted.

### Phase 1 — Golden path vertical slice (Days 2–4)
- **Stream A:** ingestion → registry → cuGraph → event fabric → cognition (NIM agent + action core) → cuOpt → briefing, wired for **Flow 2**. A vision-event *stub* emits the construction/lane-blockage detection.
- **Stream B:** NYC + Dubai DM–DLD synthetic for Flow 2; events/docs generated against schema; validation passes.
- **Gate G1 (the big one):** Flow 2 runs end-to-end on synthetic data — resolves the correct parcel/permit/developer, predicts a non-trivial mobility + safety impact, produces a cuOpt route, emits a briefing with provenance — all asserted by the harness. **Golden path certified.**

### Phase 2 — Twin, vision & 3D bridge (Days 5–7)
- **Stream A:** OpenUSD scene; **object-tagging agent** binds prims → entities; status overlay; eVTOL dispatch visual; agent-trace panel live.
- **Stream B:** real Metropolis / VSS pipeline on Cosmos-generated frames (replaces the Flow 2 vision stub).
- **Gate G2:** the hero demo (Scene 0–6) plays with the 3D twin + agent-trace; vision events flow from synthetic video through to the briefing.

### Phase 3 — Breadth via cartridges (Days 8–9)
- **Stream A:** onboard Flows 1, 3, 7 as cartridges (schema + adapters + script + narrative); Flow 5 / Flow 6 if Could-time appears.
- **Stream B:** donor packs for the new flows (London, Chicago; Melbourne/Singapore as needed).
- **Gate G3:** portfolio zoom-out (split-screen) runs for 3–4 flows on the same spine; each new flow passes its own gate.

### Phase 4 — Polish & collateral (Day 10)
- Demo video, technical blog, GitHub repo, README; **claim-label audit** (every surfaced capability correctly tagged); final environment snapshot; time-box the Omniverse polish.
- **Gate G4 (definition of done):** see §10.

---

## 5. Acceptance gates (summary)

| Gate | Certifies |
|------|-----------|
| G0 | Harness + schema + environment exist and run |
| G1 | **Flow 2 end-to-end on synthetic data, evidence + briefing** (golden path) |
| G2 | Twin + vision + 3D bridge + agent-trace play the hero demo |
| G3 | 3–4 flows run as cartridges on one spine; portfolio zoom-out works |
| G4 | Video, blog, repo, claim audit, snapshot complete |

Per-artifact gates (schema, each adapter, each agent, each flow, each synthetic dataset) live next to the artifact in the repo and are run by the harness. No artifact merges red.

---

## 6. Dependencies

![Critical-path dependencies](CityBrain_RTX_diagram_dependencies.svg)

*Figure — the critical path. The data factory feeds the registry; vision events feed cognition; the twin's object-tagging also binds into the registry. Schema and Flow 2 (G1) are the blocking items.*

- The **harness** blocks nothing but gates everything — build first.
- **Schema** blocks the registry, the graph and Stream B — freeze v1 early.
- **Flow 2 (G1)** blocks Phase 2 and Phase 3 — golden path is the critical path.
- The **twin** can develop in parallel but its *value* (the 3D bridge) depends on the registry existing.

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Omniverse polish eats the sprint | Rule 10: web map is the Must; 3D is Should; cap the hours |
| Synthetic data is unconvincing | Stream B's validation harness; transplant real distributions, don't invent |
| CUDA / Docker / weights infra pain | Rule 9: pin, snapshot, `enforce-eager`, `docker cp` before `rm`, persist `HF_TOKEN` |
| Scope sprawl across flows | Golden-path-first; cartridges additive; MoSCoW discipline |
| Multi-agent codegen drift | Rule 8: single source of truth (this folder) + gate-based verification |
| Over-claiming in the demo | Rule 4: claim labels audited at G4 |
| Time lost re-explaining context to agents | These canonical docs in Drive; agents re-read, don't re-derive |

---

## 8. Division of labour

- **Source of truth (this folder):** the canonical schema, scenario scripts, gate specs and these planning docs. Maintained as the single reference all agents read. *(Produced here; you place them in the folder.)*
- **Build agents (Claude Code / Codex / Antigravity):** implement spine services, adapters, the harness, the agents, the dashboard, the twin and the cartridges — against the canonical spec, gated by the harness.
- **You (orchestrator):** run the rig (dual DGX Spark + RTX 5090), make the judgment calls (final golden path, polish depth, donor-pack order), drive the agents, and record the demo.

The loop per task: read the canonical spec → implement → run the gate → snapshot green → update status in Mission Control.

---

## 9. Donor-pack harvest order

Recommended sequence (depth before breadth, value-weighted):

1. **NYC** — master operational donor (Flow 2 + Flow 1 + Flow 5 base).
2. **Dubai DM–DLD** — the real-data scenario spine for Flow 2.
3. **Helsinki / Amsterdam** — 3D for the twin.
4. **Singapore** — perception "eyes" for the vision pipeline.
5. **London** — Flow 3 + Flow 5 resilience.
6. **Chicago / Melbourne** — Flow 7 + Flow 4 specialists.

---

## 10. Definition of done (G4)

The demo is "done" when:
- **Flow 2** plays end-to-end (Scene 0–6) on synthetic data, with an evidence-backed briefing and the visible agent trace.
- At least **two more flows** run as cartridges on the same spine.
- Every surfaced capability carries a correct **claim label**.
- There is a **demo video**, a **GitHub repo** with README, and a **technical blog** post.
- The environment is **snapshotted and reproducible**.
- The positioning line holds on screen: *"I took NVIDIA's Smart City AI Blueprint and extended it into a full city-operations brain."*

> Next: the **Mission Control** tracker — this plan rendered as a live task/scope/gate board, plus the **Synthetic-Data Stream** deep doc for Stream B.
