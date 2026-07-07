Below is the **chronological CityBrain ledger for this thread**, treating “built” as either **implemented/gated** or **formally designed/scoped into a reusable artifact**. I’ve marked the difference where important.

## Chronological summary

### **2026-05-02 — Dubai Municipality CCTV / Building Violation AI architecture**

Built a proposal architecture for an **AI-powered Building Violation Intelligence Platform**. The key decision was to treat the RFI not as a monitoring-room fit-out, but as a deployable AI use case: **DeepStream/Metropolis for video detection**, **DGX Spark for agentic review**, **Omniverse/OpenUSD for future synthetic data and construction-site simulation**, and a strict **human-in-the-loop** boundary where AI produces candidate violations, not official legal violations. 

### **2026-06-14 — CityBrain strategic expansion**

CityBrain was reframed from a Dubai/DLD/DM-focused digital twin into a broader **city-scale intelligence system**: graph-based, multi-network, multi-rate, and able to reason across roads, utilities, buildings, permits, incidents, sensors, social/economic context, and time scales from operational events to long-term patterns. This is where the “city brain” direction became broader than a dashboard or map.

### **2026-06-25 — GPU foundation and local hardware split**

Built the two-box hardware foundation:

* **txr-3090** became the data/graph/RAPIDS box.
* **txr-4070** became the face/dashboard/trace/briefing/DeepStream-facing box.
* SSH, Docker GPU, RAPIDS probe, Node/npm/pnpm, Caddy, and local web endpoints were validated.
* CityBrain data and code were synced across the machines.

This gave the project a real local compute substrate instead of being only a design.

### **2026-06-26 — Full Vision Completion Map**

Produced the major **CityBrain completion map** and corrected the definition of done. The thread separated four finish lines: **application snapshot**, **reference spine**, **platform v1**, and **full vision portfolio**. It also clarified that the project already had a strong governed path through ingestion, registry, graph, query core, cuOpt slice, web face, and governance — but not yet live event fabric, runtime perception, full simulation/twin, full personas, or consequential HITL action lifecycle. 

### **2026-06-27 — Singapore D1 Source/API Scout**

Ran the **SG-D1 Singapore Source/API Scout**. Final status was **FAIL** because LTA DataMall returned HTTP `401` for the SDK key, across the authenticated LTA endpoints. However, it still produced a useful landing manifest with **85 files**, hashes, lineage, NEA/data.gov.sg public snapshots, and OneMap docs/search artifacts. NEA current public endpoints such as PM2.5, rainfall, wind speed, wind direction, air temperature, and relative humidity landed with HTTP 200, while LTA records were zero-byte 401 placeholders and some public forecast endpoints hit 429. 

### **2026-06-27 — F3-NYC live-replay sequence**

The NYC Flow 3 chain moved through:

* **F3-NYC-D6**: green live Spark/NIM replay over capped D2C evidence.
* **F3-NYC-D8**: four heroes emitted; three positive; subject-alignment fix preserved.
* **F3-NYC-D9**: passed with capped-source limitation.
* Later same day, Fire Dispatch and EMS became fully downloaded, so the path moved from capped-source evidence toward full-source propagation.

This was one of the first strong “reactive city incident” paths.

### **2026-06-28 — Control Room Reference Demo R1 / R2**

Built and validated the **D6 Control Room Reference Demo** line. R1 produced a self-contained demo pack with master decision, closeout decision, local open index, manifests, operator/executive scripts, acceptance matrices, evidence walkthrough, and Omniverse supporting sequence. R2 refreshed/polished the closeout and locked the truth that:

* Omniverse Kit/Composer is the primary spatial control-room surface.
* Web is the companion evidence/episode/executive surface.
* Event/current-state context is local/replay review context only.
* No production live/public API, autonomous routing, dispatch, enforcement, legal, or certified claims.

### **2026-06-28 — Track 1 D2 integrated runtime smoke**

Built the integrated Track 1 D2 smoke combining **Event Fabric D2**, **Perception D2**, and **SUMO D2** into a unified runtime path. It produced **91 unified events** and closed with a D2 closeout plus D3 roadmap. This established early integration between event, perception, and simulation lanes.

### **2026-06-29 — Perception D3 DeepStream bridge**

DeepStream moved from “waiting on infra” to **PASS with limitations**. The txr-4070 DeepStream container, Docker GPU runtime, GStreamer smoke, and DeepStream smoke passed. It produced normalized runtime observations and candidate/review events. This was the first practical perception bridge before the later full product runtime smoke.

### **2026-06-29 — Track 2 Omniverse breakthrough**

Barcelona and NYC opened in Omniverse as real LOD2/I3S-derived spatial scenes. This established that CityBrain could carry real city geometry into an Omniverse/Kit direction, rather than only using web maps.

### **2026-06-29 — Track 1 D4Y R1 Intelligence Substrate closeout**

Closed **D4Y R1** as the intelligence substrate. It established memory/state foundations: situations, graph, evidence, deterministic query. The recorded state included:

* 169 runtime situations
* 1,884 graph nodes
* 5,420 graph edges
* 19 query types
* 18 QA intents
* 10 answer packet examples
* 5 narrator templates

This became the “brain has memory/state” phase.

### **2026-06-29 / 2026-06-30 — Track 1 D4Y R2 and R3**

Closed the next Track 1 progression:

* **D4Y R2**: orchestration fabric — router, tools, harnesses, agent contracts.
* **D4Y R3**: local callable runtime + insight slice — request in, typed packet out, insight packets out.

The PM decision after R3 was that Track 1 should next become **domain-extensible**, through `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-PREFLIGHT`, not jump straight into a Dubai-specific agent or production hardening. 

### **2026-06-29 / 2026-06-30 — Domain-pack / CER / SEG direction**

Defined the next platform direction: a generic **domain-pack framework** that plugs into runtime, orchestrator, tools, insight engine, canonical entities, semantic graph, app handoff, and guardrails. The domain-pack R4 roadmap includes canonical entity bridge, semantic graph bridge, runtime slice, and first-domain-pack selection. 

### **2026-06-30 — Current three-track phase defined**

The active three-track phase became clear:

1. **Live source / event fabric track** — the city gets a local/replay nervous system.
2. **D5 local served runtime track** — the brain becomes locally callable and stable.
3. **Track 2A Omniverse/OpenUSD asset-binding track** — the 3D/control-room body gets entity-aware overlays.

At that point, all three were **PASS_WITH_LIMITATIONS** preflight-level achievements: live source crossing, local served runtime, and Omniverse overlay smoke with 12 Barcelona Eixample overlay items bound to canonical/evidence/graph/runtime refs. 

### **2026-06-30 — D8 final demo capture and certified handoff**

Built the D8 final demo capture and certified handoff pack. It locked the demo state:

* Helsinki: 20 pending pick packets
* Chicago: 15 reviewed cases, 45 bounded matches, 1 abstain
* VSS sample ingest gate: CLOSED
* 7-step final demo route

This moved the demo from architecture into a certified operator walkthrough state.

### **2026-06-30 — D9 demo polish / review loop R1**

Built the D9 demo polish and review-loop package. It passed with limitations. The remaining main gap was screenshot/video capture not yet complete, but the review loop and scorecard moved forward.

### **2026-07-01 — D8 Web + Kit Live Surface Implementation R2**

Built the web + Kit live surface milestone freeze. It passed with limitations:

* Web live launch passed.
* DOM certified-value assertions passed.
* Candidate options rendered: 7.
* Reviewed option sets: 3.
* Trace stages: 9.
* D7 observations: 6.
* Moment parity: 10/10.
* One-truth drift check passed.
* Forbidden-command rejection/logging passed.
* Kit source validation passed, but Kit runtime was not run because Kit runtime was unavailable.

This was a major “web cockpit + spatial control-room seam” step.

### **2026-07-01 — Baseline hash reconciliation**

Completed baseline hash reconciliation:

* 40 maintained source files clean.
* 11 runtime bundle files clean.
* 9 volatile bridge artifacts classified.
* 10 prior-stage hash mismatches explained as runtime artifacts.

This helped separate real source drift from expected runtime/generated artifacts.

### **2026-07-03 — Push 1–7 full-stack validation**

Completed the Push 1–7 full-stack validation with limitations. It validated artifact inventory, hash manifests, schema/contracts, end-to-end references, boundary scans, security staged scan, focused validation tests, and protected ASK/R7 runtime diff. The broader test suite still had older fixture/lane-discovery failures, but the validation-induced drift was clean.

### **2026-07-03 — Learning substrate collection**

Built the learning-substrate addendum as a future-track collection, not as an active learning runtime. It captured seeds for later loops but did **not** build a learning model, live API, official control, legal, or certified claim.

### **2026-07-03 — R9 DeepStream product runtime execution smoke**

Built and validated the DeepStream product runtime execution smoke on txr-4070. It used NVIDIA DeepStream 8.0.0 and produced a large runtime evidence bundle:

* 1,474 ZIP entries
* 12/12 JSON clean
* 4/4 JSONL clean
* 29,716 JSONL records
* 29,686 total detections
* Class counts: 21,446 cars, 7,569 people, 668 bicycles, 3 road signs
* Runtime status: PASS with limitations

This proved DeepStream could run as a real product runtime on the local GPU box.

### **2026-07-03 — Metropolis/VSS BMD45 cockpit review integration smoke R21**

Built and validated the Metropolis/VSS BMD45 cockpit review integration smoke R21 package:

* 19 ZIP entries
* 15/15 JSON parse clean
* 8 cockpit review cards
* 8 external media refs
* 0 packaged media files
* Boundary preserved: BMD-45 as dataset annotation, DeepStream/Metropolis as sensor-inferred, VSS as model-generated narrative, not fact source

This connected video/perception outputs to cockpit review without overclaiming.

### **2026-07-03 / 2026-07-04 — Intelligence cockpit mode map**

Defined the product as a **review-only city intelligence cockpit**, not a dashboard. The intelligence loop became:

`WATCH → SELECT → ASK → CHECK → BRIEF → RECALL / DIFF / SPATIAL → HUMAN REVIEW STATE`

The thread clarified the maturity of each mode: WATCH working but shallow; ASK in staged-router design; CHECK strong but needing broader rules; BRIEF functional; RECALL partial; DIFF limited; SPATIAL/Omniverse seam passed; workflow prototype exists; perception/VSS deferred unless media/source/privacy are ready. 

### **2026-07-04 — D11 / D12 / D13 / D14 product state**

The cockpit intelligence state was clarified:

* **D11**: workflow/review state exists but real human gate pending.
* **D12**: DIFF exists in limited form with zero city changes; useful for no-false-positive proof, not yet mature.
* **D13**: web ↔ Kit live seam passed, including one-truth parity and forbidden-command rejection.
* **D14**: ASK taxonomy/staged router design in progress; router training not opened; real operator validation not claimed. 

### **2026-07-04 — North-star product loop**

Defined the fuller official mode taxonomy:

* Operator-facing: WATCH, ASK, CHECK, BRIEF, RECALL, DIFF, PLAN, SCHEDULE, SPATIAL, WORKFLOW.
* System/reasoning: IDENTITY, GRAPH, EVENT, PERCEPTION, SIMULATE, OPTIMIZE, GOVERN.
* Platform/commercial: QUALITY/MATURITY, FEDERATION, SYNTHETIC, PERSONA.

The north-star loop became: source records/events/media/spatial selections → identity → graph → evidence → CHECK → human-facing modes → human review state → governance trace.

### **2026-07-05 — Epoch 2.x / Epoch 3 governance plan**

Built the corrected epoch roadmap. The key correction was that **Epoch 2.0 is not “build agents”; it is “make the existing agent-shaped system governable under one runtime contract.”**

The Epoch 2.0 closure bar became: every existing agent-shaped capability must be registered, permissioned, replay-tested, budgeted, traced, and ledgered under one runtime contract. Deliverables include ComponentRegistry v1, AgentRunEnvelope v1, ToolPermissionPolicy v1, LLM seat registry, budget/stop policy, ModeInvocationRegistry, replay harness, and mode-level eval harness. 

### **2026-07-05 — ComponentRegistry direction**

The thread decided not to create separate AgentRegistry, LearnedComponentRegistry, LLMRegistry, and ToolRegistry silos. Instead, it converged on one **ComponentRegistry** with component kinds such as agent, LLM seat, tool adapter, retriever, renderer, ranker, forecast model, surrogate model, simulator connector, and validator. 

### **2026-07-06 — Epoch 3 foundation / learning and backtesting line**

The Epoch 3 line closed multiple non-live learning/backtesting artifacts:

* E3 foundation for learning/backtesting
* E3 master execution R1
* L2 historical label backfill R1
* L2 R2 forecast authority preflight
* offline experimental forecast R1
* hidden data scout master R1
* final non-live hidden fuel scout R1

All remained bounded as non-live/future-track learning fuel, not production prediction.

### **2026-07-06 — Epoch 3 Hidden Data Scout Master R1**

Built and accepted the hidden data scout master package:

* 17 ZIP entries
* 15/15 JSON parse clean
* 0 JSONL
* 0 CRLF paths
* Hash manifest clean
* Final status: `PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS`

It identified hidden candidate fuel across transition targets, CHECK calibration, L4 case memory, identity/graph eval, LLM/perception usefulness, and global backlog.

### **2026-07-06 — Post-E3 / Epoch 4 fork preflight**

Built the Post-E3 / Epoch 4 fork preflight:

* Runner added
* Tests added
* E4 schemas added
* Durable governance publication added
* Final status: `PASS_POST_E3_EPOCH4_FORK_PREFLIGHT_R1_WITH_LIMITATIONS`

This prepared the fork from Epoch 3 learning/backtesting into Epoch 4 governance/expansion work.

### **2026-07-07 — Singapore D1 interpretation locked**

The Singapore run was classified correctly as **completed but not green**: valid negative auth evidence, not a wasted run. The correct label is `FAIL_AUTH_LTA`, while NEA/data.gov.sg and OneMap docs/search artifacts remain useful landed evidence. The manifest confirms the mix of LTA 401 zero-byte placeholders, NEA successful current snapshots, OneMap docs/search success, and OneMap protected endpoint 401s. 

---

## What exists now, in plain terms

CityBrain now has a real **identity / graph / governed query / evidence / web cockpit** core. The completion-map document summarizes the certified state as strong in canonical identity/provenance, NYC ingestion and graph scale, deterministic query core, evidence/grounding/governance, web operational face, and one optimization use case; weaker areas remain live event fabric, simulation/twin, runtime perception, full Incident/Plan cognition, personas, and broader flow portfolio. 

The product direction is no longer “show city data.” It is now a **review-only city intelligence loop**: WATCH what deserves review, ASK bounded questions, CHECK claimability, BRIEF evidence, RECALL similar cases, DIFF changes, SPATIAL ground the same truth in Omniverse/web, and keep humans responsible for review state. 

The next natural build path is still the three-track finish: **local event fabric**, **hardened served runtime**, and **Omniverse/OpenUSD asset binding**, then compose them into a **Control Room Reference Demo**. 
