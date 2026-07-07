# TXR City Brain — Application Snapshot Definition of Done

**Document 2 of 4** · *Companion docs: 01 Current Certified State · 03 Platform v1 DoD · 04 Full Vision Completion Map*

**Snapshot tag (target):** `txr-citybrain-app-snapshot-v1`
**Acceptance gate (target):** G1
**Document purpose:** Define exactly what ships as the Application Snapshot — the near-term, defensible finish line for the NVIDIA Urban AI application, Dubai Phase-2 conversation, GITEX showcase, building-violation-monitoring RFI, and Crossover/BP roles. This is the line that says "this is real, here is what is in it, here is what is honestly out of scope."

**How to maintain this document:** This is a *target* document. Items here are not yet all green. Each item has a specific acceptance criterion and a specific test. When all criteria pass and the snapshot is taken, this doc's status flips from "target" to "achieved-on-{date}" and items move into doc 01.

**What the Application Snapshot is NOT:** It is not "everything in the architecture." That is doc 04. It is the credible, reviewable artifact a hiring manager / procurement reviewer / Phase-2 sponsor can read in 20 minutes and verify in 2 hours. It deliberately closes some doors (perception, twin, additional flows) and leaves them honestly labelled `[Planned]`.

---

## 1. The five audiences this snapshot serves

| Audience | What they read first | What they need from this snapshot |
|---|---|---|
| NVIDIA Urban AI Solution Architect application | Stack mapping + governance pattern | Every NVIDIA component used is real and visible; claim labels are honest; the governance pattern is the differentiator |
| Dubai Phase-2 conversation | Lineage from Phase-1 + governance continuity | "I re-platformed and generalized the Phase-1 City Brain onto NVIDIA's stack — here is the second city" |
| GITEX showcase (October) | Live, clickable demo | The face layer must render in a browser with a real DOB cascade, narrated by Spark, in front of an audience |
| Building-violation-monitoring RFI | Specific construction-compliance workflows with citable provenance | The system answers the RFI's actual question; provenance + claim boundaries protect the procurement scrutiny |
| Crossover / BP roles | Engineering quality + architecture | Clean code, real gates, snapshotted state, honest scope discipline |

All five read the same artifact. The snapshot's job is to land all five at once without grafting any one of them on artificially.

---

## 2. The Application Snapshot in one sentence

A reproducible, governed, end-to-end demonstration that takes any block in NYC, or accepted London Flow 2 hero subjects (full citywide identity + planning backbone, live face, live NIM narration, and LON-HERO dual scenarios proven), and produces a cross-domain compliance briefing with grounded narration over real data, an explainable inspection-review routing plan (NYC) or a connected identity→context cascade (London), and a clickable web operating surface — running on NVIDIA NIM, NeMo, RAPIDS, cuGraph, and cuOpt — with provenance, confidence, and claim labels on every claim it makes.

---

## 3. Acceptance criteria — what must be true to snapshot

### 3.1 Spine criteria — all must hold

**SP-1. NYC Flow 2 spine end-to-end green at citywide scale**
- ✅ Already in doc 01. Acceptance: harness reports green on all of a1, a2, a3, a3·D2, a4·D1–D3b, a5·D1–D7b, a6·D1, a7, a8·D1–D3b.

**SP-2. London second-city proof — accepted Flow 2 city core**
- ✅ Closed. LON·D4 through D13c all green: full London-scale identity (5.31M UPRN / 2.30M TOID / 69.7K USRN), 58,867 normalized PLD applications, official PLD API UPRN recovery (zero fuzzy joins), accepted graph 7,734,960 nodes / 10,664,896 edges (0 missing endpoints), planning-context enrichment, Local Plan semantic certification (444/1,139 layers), TOID generalised-location geometry (40,803/40,804), EV charging context (156 sites), 190 certified enforcement-identity edges, deterministic + live-grounded NeMo wrapper, live face layer (`/london`, `/api/london/*`) — all reconciled into one accepted composite (LON·D13c), re-smoked live, not just file-merged
- The same a2 harness pattern that gates NYC, gates London (compatibility-harness treatment for `on_street` is honest and documented; cross-city ontology v2 is explicitly out-of-scope for this snapshot and tracked in doc 03)
- ✅ LON-HERO dual scenarios are accepted and should be treated as the London Flow 2 hero/freeze proof. Future London work mounts as `LON-F3X-*`, `LON-F4X-*`, or `LON-F5X-*` sub-cartridges and does not inherit acceptance from Flow 2.

**SP-3. The formal a9 wire**
- A single `a9_wire_e2e.py` (or equivalent) that runs the full Flow 2 path end-to-end on a fresh checkout, on a clean environment, against a frozen data snapshot, and exits 0 on green
- Same script runs against the same data and produces byte-stable outputs across two consecutive runs (determinism check)
- The output of the a9 run is the artifact that is tagged as `txr-citybrain-app-snapshot-v1`

**SP-4. G1 gate formally promoted to green**
- G1 is currently `[P]` pending behind a9. After a9 runs green, G1 flips to `[I]` and is recorded in this doc and in Mission Control.

### 3.2 Governance criteria — all must hold

**GV-1. Claim-boundary audit, dated, signed-off**
- Every `[I]` claim in the snapshot has runnable evidence in the repo
- Every `[A]` claim names the NVIDIA component and a runnable adapter contract
- Every `[S]` claim names what is simulated and what is honest about it
- Every `[P]` claim is clearly out-of-scope for the snapshot and tracked in doc 03 or doc 04
- No claim in the snapshot is unlabelled

**GV-2. Live guardrail gate (the audit item the critique flagged)**
- A dedicated test that proves NeMo Guardrails is *actually active* on both accepted and rejected paths
- Test: send a request that should be accepted → guardrail logs ACCEPT; send a request that should be rejected (out-of-vocabulary action, off-task query, attempted exfiltration) → guardrail logs REJECT with reason
- Without this gate, the `[I]` claim on NeMo Guardrails is incomplete

**GV-3. Negative-path tests for every governed surface**
- Invalid block key → 404 with honest message
- Invalid query (no subject, ambiguous subject, off-domain) → rejected before deterministic execution, traceable reason logged
- Drift test on the canonical graph (forked vocabulary) → 5 gates fire red as expected

**GV-4. Round-trip portability of every accepted artifact**
- 3090 outputs read on laptop, gates still pass
- Spark outputs read on dev box, gates still pass
- 4070-served artifacts match what 3090/Spark produced (hash-verified manifests preserved)

**GV-5. Honest evidence labels on illustrative content**
- All Pexels/Pixabay clips labelled `[Illustrative · Pexels/Pixabay]` with explicit non-evidence boundary
- The `/briefing` page's clip panel carries the boundary statement: "Illustrative stock footage only. Not evidence from parcel X, not evidence from the NYC DOB record, and not used to assert a real-world violation."

### 3.3 Reproducibility criteria — all must hold

**RP-1. Pinned environment manifest**
- `requirements.txt` (Python, pinned including `pydantic==2.13.4`)
- Container image digests for: NIM Llama-3.1-8B, NeMo Agent Toolkit, RAPIDS 26.06, cuOpt 26.6.0
- Hardware manifest: Spark / 3090 / 4070 / laptop with drivers, CUDA versions, OS versions

**RP-2. Clean-room runbook**
- A single `RUNBOOK.md` that takes a new operator from "fresh machines" to "demo running"
- Includes: SSH key setup, container pulls, NGC auth steps, data sync paths, service start commands, health checks, browser URLs
- Tested by attempting a clean-room run on at least one fresh machine before snapshotting

**RP-3. Frozen data snapshot**
- All NYC source datasets pinned to specific harvest dates / Socrata version IDs
- London source datasets pinned similarly
- A `data_manifest.json` lists every input source with its hash, vintage, and license

**RP-4. Backup video of the demo running**
- 3–5 minute screen capture of the live demo (map → click → briefing → narration → routes → trace) running end-to-end on real data
- Captures the live narration loop (Spark in the loop)
- Recorded against the snapshotted state, not a pre-snapshot state
- This is the nuclear backup for travel demos where network or hardware is hostile

### 3.4 Application wrapper criteria — all must hold

**WR-1. Executive Summary written**
- Plain-English, 2–4 pages
- Lineage statement (Phase-1 City Brain → re-platformed on NVIDIA's stack → generalized across cities)
- Real blueprint mapping (which NVIDIA components are used and how, with honest claim labels)
- Spine-vs-blueprint statement: what TXR City Brain adds beyond Omniverse Smart City Blueprint (twin + eyes from blueprint, brain + governance from us)
- Reads as a single document a hiring manager / procurement reviewer / Phase-2 sponsor can absorb in 20 minutes

**WR-2. Rename pass complete**
- `CityBrain RTX` → `TXR City Brain` across all files, internal references, board copy, code comments
- One pass, mechanical, verified by grep

**WR-3. Repo + README**
- Public-facing or shareable repository
- README is a single-read entry point: what this is, who it's for, how to verify it, links to the four canonical docs (this set)
- Repo is reproducible from the runbook (RP-2)

**WR-4. Demo video captured**
- Per RP-4, but framed for distribution (audio narration, captions where appropriate, clear scene markers)
- Available as both a "long form" 5–10 minute demo and a "short form" 60–90 second hook

**WR-5. Travel bundle**
- Per the discussion already on the boards: laptop + Spark portable demo for situations where 3090/4070 cannot travel
- Same disciplined form as the a5·D2 portability pack — clean-room run gates, hash verification, no-mutation checks
- Backup video (RP-4) bundled in
- Tested by running the travel bundle on a fresh laptop before any actual travel

### 3.5 Audience-specific criteria

**AU-NVIDIA. Stack visibility**
- The Executive Summary and the live demo both make the NVIDIA stack genuinely visible: NIM is named where NIM is used; NeMo is named where NeMo is used; RAPIDS / cuGraph / cuOpt / Container Toolkit / NGC / OpenUSD all surface in honest claim-labelled places

**AU-Dubai. Phase-1 lineage**
- The Executive Summary's lineage statement is specific about Phase-1 (DLD/DM, the 9-stage orchestration, code-computes-truth/model-narrates), and is clear that TXR City Brain is the re-platformed and generalized successor
- The Dubai Creek USD scene on the 5090 is mentioned honestly as "different city, demonstrates Omniverse capability, not wired to this snapshot's NYC graph"

**AU-GITEX. Live demo legibility**
- A reviewer with no prior context can walk up to the demo, click a block, read the briefing, see the route plan, see the trace, in under 2 minutes, and understand what the system did
- The why_selected tooltips are the load-bearing legibility surface

**AU-RFI. Building-violation framing**
- The RFI's specific question is answered in the Executive Summary in plain procurement language: "TXR City Brain is a governed cross-domain reasoning system for construction-compliance monitoring. The current snapshot demonstrates [specific RFI capabilities] on real NYC DOB data with citable provenance."
- The cascade (`complaint → building → permit → contractor → parcel`) is the literal answer to the RFI's monitoring question

**AU-Crossover/BP. Engineering quality**
- Code is clean and reviewable
- Gates are not self-validating (the drift test discriminates good from broken on demand)
- Snapshot discipline is documented and demonstrably real (every accepted state is pinned, hash-verified, and round-trip-tested)
- Honest scope discipline visible in the four-doc structure

---

## 4. Scope statement — what the Application Snapshot deliberately does NOT include

To be read alongside this doc — every item below is honestly out-of-scope for the snapshot and tracked in doc 03 or doc 04. Putting them out-of-scope is a feature, not a limitation; the snapshot's credibility comes partly from showing scope discipline.

**Out of scope but tracked for Platform v1 (doc 03):**
- Live event fabric (L4)
- Domain simulators — SUMO, pandapower, EPANET (L6)
- Runtime perception pipeline — Metropolis, DeepStream, VSS, grounding-dino (L7)
- Omniverse / OpenUSD city twin (L6/L8)
- Incident and Plan cognition modes (L5)
- Persona layer — 4 SOUL personas (L8)
- Full agent roster — object-tagging, retrieval, forecasting (architecture §4)
- Approval UI + HITL gates (L8/L9)
- Cross-city ontology v2 (L2)
- Additional cuOpt problem families (dispatch, kerbside, shutdown sequencing)
- Asset-dependency graph edges (energy / water / infrastructure)

**Out of scope but tracked for full vision (doc 04):**
- Flows 1, 3, 4, 5, 6, 7
- Dubai re-anchor cartridge
- Oil & gas cartridge
- Cosmos rollouts (Predict + Transfer)
- NeMo Curator
- cuVS / NeMo Retriever
- Earth-2 / CorrDiff
- 3-4 city minimum for portfolio

---

## 5. Acceptance test — how to know the snapshot is done

A simple, falsifiable test: a person with the runbook can, in under 4 hours on a fresh environment, produce a green run of the snapshot from scratch.

Specifically:
1. Clone the repo on a fresh machine
2. Follow the runbook (RP-2)
3. Pull the pinned container images (RP-1)
4. Sync the frozen data snapshot (RP-3)
5. Start the services (Spark NIM, 3090 cuGraph, 4070 face layer)
6. Run `a9_wire_e2e.py`
7. Open the browser to the face layer, click a block, see the briefing
8. Run the drift test, see gates fire red
9. Run the live guardrail gate (GV-2), see ACCEPT and REJECT logged correctly

Each step has a single-command verification. If any step fails, the snapshot is not done.

---

## 6. Open items before snapshotting — checklist

Tracked here so they don't go missing. Status as of 2026-06-27:

- [x] LON·D4–D13c full chain green (identity, planning, context, Local Plan, geometry, EV, enforcement-identity, live wrapper, live face, composite reconciliation)
- [x] LON·hero subject selected and packaged as dual scenarios
- [x] `LON-HERO` acceptance gate written and green
- [x] London hero live-narration smoke / no cross-subject leakage carried in the accepted London hero line
- [ ] `a9_wire_e2e.py` written and green on two consecutive runs (determinism)
- [ ] G1 formally flipped from `[P]` to `[I]` in Mission Control
- [ ] Claim-boundary audit run, dated, signed-off (GV-1)
- [ ] Live guardrail gate added (GV-2)
- [ ] Round-trip portability tested for every accepted artifact (GV-4)
- [ ] `requirements.txt` and container digests frozen (RP-1)
- [ ] `RUNBOOK.md` written and clean-room tested (RP-2)
- [ ] `data_manifest.json` produced (RP-3)
- [ ] Demo video captured against the snapshotted state (RP-4)
- [ ] Executive Summary written (WR-1)
- [ ] Rename pass complete (WR-2)
- [ ] Repo + README produced (WR-3)
- [ ] Travel bundle tested on fresh laptop (WR-5)

When every box is checked, snapshot. After snapshotting, this doc's status flips and the items move into doc 01.

---

## 7. What lives where after snapshotting

| Artifact | Location |
|---|---|
| Snapshot tag | `txr-citybrain-app-snapshot-v1` in repo |
| Pinned data | Frozen Parquet + manifests on each box's `/data/citybrain/` |
| Pinned container images | Recorded in `requirements.txt` and `RUNBOOK.md` |
| Live demo URLs | Documented in `RUNBOOK.md` and Executive Summary |
| Backup video | In repo + on backup drive + on travel laptop |
| Travel bundle | Self-contained directory bootable on fresh laptop |
| Four canonical docs (this set) | In repo at `docs/01_current_state.md`, `docs/02_app_snapshot_dod.md`, `docs/03_platform_v1_dod.md`, `docs/04_full_vision.md` |

---

## 8. The honest framing for reviewers

When any of the five audiences asks "is this done?" the answer is:

> "The Application Snapshot is done. It is what's in doc 02. The system answers cross-domain compliance questions on real NYC DOB data, narrated by NIM on the Spark, with cuGraph projecting the citywide graph on the 3090, cuOpt producing an explainable inspection-review routing plan, all served through a clickable web operating surface on the 4070, with provenance and claim boundaries on every claim. Doc 01 lists exactly what is certified. Docs 03 and 04 list what's next and what's outermost — those are honestly out of scope for this snapshot, deliberately, because scope discipline is part of why this snapshot is credible."

That sentence is the snapshot's elevator pitch.

---

*End of doc 02. See doc 03 for Platform v1 — the next credible product finish line.*
