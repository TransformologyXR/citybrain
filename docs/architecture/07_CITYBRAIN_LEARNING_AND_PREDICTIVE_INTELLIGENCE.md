# 07 — CITYBRAIN LEARNING AND PREDICTIVE INTELLIGENCE

**Release:** R3 candidate (enters the R3 docs release alongside the operating agreement and cadence spec)
**Status:** Authoritative draft — extends Docs 01–06; modifies no sealed contract
**Date:** 2026-07-05
**Supersedes:** Nothing. This is the first document of the learning epoch.
**Depends on:** Doc 02 (intelligence modes), Doc 03 (agentic layer), Doc 04 (architecture/roadmap), Doc 05 (technical contracts), Doc 06 (certified-state ledger and crosswalk), Standalone Sprint Roadmap v1.0 (Pushes 2–7).

---

## 0. Position of this document

Docs 01–06 define a governed knowing-and-proposing machine: it ingests, resolves identity, watches, explains, checks its own claims, sees, locates, and (from Push 6) proposes under approval. When Pushes 2–7 close, that machine is architecturally complete — and architecturally static. Every mode computes from current state. Nothing learns, predicts, remembers across episodes, or improves. The system is exactly as intelligent on day 1000 as on day 1.

This document defines the next epoch: the five learning loops that turn the platform from a static evaluator into a compounding intelligence, without moving any learned output above its place on the authority ladder.

The core observation:

```text
The platform already built is secretly a learning substrate with the loops left open.

The event fabric's replay        → a backtesting engine.
Operator dispositions            → labels.
CheckReports                     → calibration targets.
CER attribute conflicts          → identity-resolution training pairs.
The approval lifecycle           → a preference dataset.
```

None of these components were designed as ML infrastructure. That is what they are. The learning epoch does not add a new system — it closes five loops the current architecture already implies, in dependency order.

### 0.1 Binding rules of this document

```text
R7.1  No learned output ever changes claim status, review state, or authority level.
      Learned outputs RANK, SCORE, FORECAST, RETRIEVE, and PROPOSE. They never CLAIM or ACT.

R7.2  Every learned output is a packet with source_class = model_inferred or derived_field,
      carries a CheckReport, and carries model/version/evaluation references.

R7.3  No model ships without a consuming decision surface AND a published evaluation
      (the data acceptance rule of Doc 05 §25, extended to models — see §13).

R7.4  Every loop closes with a ledger row, a hash manifest, and regression corpus fixtures,
      under the same cadence (PREFLIGHT → BUILD → CLOSEOUT → COMMIT/PUSH → PUBLISH)
      and stop conditions as all other work.

R7.5  Operator behavioral data (dispositions, workflow transitions) is governed data:
      pseudonymous at rest, aggregate for learning, individual-level access admin-scoped.

R7.6  Deterministic gates still own truth and authority. Learning lives below the gates,
      LLMs remain readers/writers, and CHECK remains the arbiter of what may be said.
```

---

## 1. Purpose and thesis

### 1.1 What "10X intelligence" means here

Not a bigger model. Not more modes. Four specific capabilities the current architecture cannot express:

```text
1. The system gets BETTER with use.        (Loop 1 — outcome learning)
2. The system sees AHEAD, not just now.    (Loop 2 — prediction)
3. The system reasons about WHAT-IF.       (Loop 3 — causal / counterfactual)
4. The system REMEMBERS and TRANSFERS.     (Loop 4 — institutional memory)
```

And one capability that composes the other four:

```text
5. The system can INVESTIGATE — chain modes autonomously, under budget and
   authority, to answer questions no single mode can.   (Loop 5 — compound reasoning)
```

### 1.2 Why review-only makes learning MORE valuable, not less

A review-only system's entire value is the quality of its ranking: which items deserve operator attention first, which claims deserve trust, which situations deserve anticipation. Learning is precisely the mechanism that improves ranking, trust calibration, and anticipation. The authority ladder is untouched; the *quality of what reaches human judgment* compounds.

---

## 2. Governance foundation — learning below the authority ladder

### 2.1 Where learned outputs sit

```text
Authority ladder (Doc 01/04):   0 Observe · 1 Explain · 2 Validate · 3 Propose ·
                                4 Approve-gated execute · 5 Execute · 6 Conditional autonomy

Learned outputs occupy NO rung. They are inputs to rungs 0–3:
  - ranking of review items            → feeds Observe/Explain surfaces
  - calibration of CheckReports        → feeds Validate
  - forecasts and counterfactuals      → feed Propose (as evidence, with uncertainty)
  - precedents and investigations      → feed all of the above
```

### 2.2 Source-class discipline for learned artifacts

Every learned artifact declares its source class per Doc 05 §3:

```text
model_inferred   — forecasts, scores, match suggestions, anomaly flags, surrogate outputs
derived_field    — aggregations over dispositions/outcomes, calibration statistics
synthetic        — scenario-generated training/eval data (never mixed silently with real)
```

A learned artifact can never carry `official_record`, `source_record`, or `sensor_inferred`. CHECK enforces this at packet validation. A negative test for each learned packet type (attempting to claim a higher source class) is a mandatory fixture.

### 2.3 Universal non-claims of the learning epoch

```text
- No learned score, forecast, or retrieval result is a finding, violation,
  determination, or official fact.
- No forecast is presented without horizon, calibration reference, and backtest ref.
- No counterfactual is presented as what WOULD have happened — only as model output
  under stated assumptions.
- No disposition or operator-behavior data identifies an individual operator in any
  product surface, brief, export, or learned artifact.
- No learned component silently updates itself: every model version is a ledgered,
  hash-manifested release with a published evaluation.
- No cross-city learned transfer until federation exists (inherits the Doc 05/roadmap
  non-claim; city-scoped learning remains city-scoped).
```

---

## 3. The five loops — overview and dependency order

| Loop | Name | What it closes | Consumes | Produces | Earliest start |
|---|---|---|---|---|---|
| 1 | Outcome learning | Feedback: did operators confirm what we surfaced? | DispositionEvents, CheckReports, WatchItems | OutcomeRecords, ScoreAdjustments, CalibrationReports | Seed in Push 2 (disposition capture); learning after Push 3 |
| 2 | Prediction | Time: what happens next? | Event fabric history, replay, Loop 1 labels | ForecastPackets, BacktestReports | After Event Fabric v1 + Loop 1 ledger has depth (post-Push 4) |
| 3 | Causal / counterfactual | Intervention: what if we act / don't act? | Semantic Graph v2 dependency edges, simulators, ForecastPackets | InterventionQueries, CounterfactualPackets | After Push 4 (graph v2) + Push 6 (simulators) |
| 4 | Institutional memory | Episodes: have we seen this before, what worked? | OutcomeRecords, closed cases, RECALL | CasePackets, PrecedentSets | After Loop 1 ledger has closed episodes (post-Push 5) |
| 5 | Compound reasoning | Composition: multi-step governed investigation | All modes + Loops 1–4 outputs | InvestigationPackets | Last — after Loops 1–4 have real outputs |

Dependency chain, stated once:

```text
DispositionEvents (Push 2)
  → Outcome ledger (Loop 1)
      → labels for Loop 2 backtesting, cases for Loop 4
Event Fabric replay (Push 1/2 substrate)
  → backtest harness (Loop 2)
Semantic Graph v2 + simulators (Pushes 4/6)
  → intervention engine (Loop 3)
Loops 1–4 outputs
  → investigation agent (Loop 5)
```

This ordering is a dependency map, not permission to build all loops in parallel. Same rule as Doc 04 §7.

---

## 4. Loop 1 — Outcome learning (the label factory)

### 4.1 What it is

The loop that joins what the system surfaced to what humans decided about it, and feeds the join back into ranking and calibration.

### 4.2 Why it exists

Without it, WATCH families that operators dismiss 95% of the time keep firing at full priority forever; CHECK's confidence language never meets reality; every other loop has no labels. Loop 1 is cheap to build and is the prerequisite label supply for Loops 2 and 4 — which is exactly why disposition capture was pulled forward into Push 2 (Sprint Roadmap v1.0 §5 Lane C): every month it is absent is training signal permanently lost.

### 4.3 Components

```text
1. Outcome ledger
   Append-only join of trigger packet → disposition(s) → final state.
   One OutcomeRecord per review item that reaches a terminal disposition.
   Built as event-fabric materialization, not a new store.

2. Feedback-weighted scoring (ranking layer)
   Per-watch-family and per-item scoring adjusted by historical confirm/dismiss
   rates and context features. Output: ScoreAdjustment attached to WatchItems
   as a ranking hint. Never filters items out entirely (suppression is an
   operator/workflow decision, not a model decision).

3. CHECK calibration
   Where CHECK said SUPPORTED and the operator disposition contradicted it
   (or vice versa), emit calibration points. Periodic CalibrationReport per
   check-type: reliability curve, drift vs. previous period.
```

### 4.4 Governance notes specific to Loop 1

```text
- ScoreAdjustments RANK; they never change claim status or hide items (R7.1).
- Dispositions are noisy labels: operators dismiss for workload reasons, not only
  correctness. OutcomeRecords therefore carry disposition_context (queue depth at
  disposition time, time-to-disposition) so learning can control for triage noise.
- Per-operator learning is forbidden. Aggregation floor: no learned statistic is
  computed or displayed for a cell smaller than N operators (N set in Track 0
  freshness/privacy policy; default N=3).
```

### 4.5 Maturity and roadmap

Current maturity: **M0** (nothing exists) — moving to **M1** at Push 2 closeout (dispositions flowing, no learning yet).

```text
L1.R1  Outcome ledger materializer + OutcomeRecord packet + fixtures        (post-Push 3)
L1.R2  First CalibrationReport for CHECK v0 freshness/claimability checks   (post-Push 3)
L1.R3  Feedback-weighted ranking for 2 WATCH families, offline eval first   (post-Push 3)
L1.R4  Ranking live in review route, A/B against static ranking, ledgered   (Push 5 window)
L1.R5  Calibration feedback into CHECK v1 confidence language                (post-Push 4)
```

Closure bar for "Loop 1 exists": WatchItems in the review route are ordered by a ledgered, versioned, backtested ranking model, and CHECK ships quarterly CalibrationReports.

---

## 5. Loop 2 — Prediction (from watching to anticipating)

### 5.1 What it is

Temporal models over event-fabric history that emit calibrated, horizoned, backtested forecasts: which permits will stall, which sites drift toward non-compliance, which assets trend toward failure, which review queues will spike.

### 5.2 Why it exists

This is where review-only becomes strictly more valuable than any dashboard: the system surfaces situations *before* they are findable by query. A WATCH family driven by a forecast ("likely to stall within 30 days") is categorically different intelligence from one driven by current state ("stalled").

### 5.3 Components

```text
1. Backtest harness on replay
   Train on events to time T, score against outcomes in (T, T+h], entirely on the
   local/replay fabric. The harness is the FIRST deliverable of Loop 2 — no forecast
   model may exist before the harness that evaluates it (R7.3).

2. Forecast models v1
   Start boring: survival/hazard models and gradient-boosted baselines on
   engineered features from fabric + CER + graph. Neural/temporal-graph models
   only after baselines are beaten on the harness.

3. ForecastPacket emission + WATCH integration
   Forecasts enter the product ONLY as WATCH items of a forecast family,
   carrying the full packet contract of §10.5. Never as standalone assertions.

4. External forecast feeds (re-entry point)
   Earth-2 / CorrDiff enters here as an environmental forecast source
   (source_class integrated_external + model_inferred), feeding flood/heat/wind
   context features — per the parked register re-entry mapping.
```

### 5.4 Maturity and roadmap

Current maturity: **M0**.

```text
L2.R1  Backtest harness on replay fabric + BacktestReport packet + fixtures
L2.R2  Forecast v1 for ONE target (permit-stall is the recommended first target:
       clean labels, business-legible, dense history) — offline only
L2.R3  Forecast WATCH family live, ranked by Loop 1, disposition-labeled
L2.R4  Calibration monitoring (forecast CalibrationReports) + drift alarms
L2.R5  Second and third targets; Earth-2/CorrDiff feature feed
```

Closure bar: at least one forecast family live in review, with published BacktestReports, calibration within declared tolerance, and dispositions flowing back into Loop 1.

---

## 6. Loop 3 — Causal and counterfactual reasoning

### 6.1 What it is

An intervention engine over the semantic graph plus simulator ensembles, answering "if X fails / closes / is expedited, what propagates" and "what would have happened under the alternative."

### 6.2 Why it exists

Push 4's cross-domain dependency edges are a causal skeleton currently used only for traversal. Push 6's do-nothing baseline is a single hard-coded counterfactual. Loop 3 generalizes both: every proposal compared against modeled alternatives, not just inaction. This is the difference between "here is a plan" and "here is why this plan beats the other three."

### 6.3 Components

```text
1. Graph intervention engine (fast path)
   Deterministic propagation over Semantic Graph v2 dependency edges with declared
   propagation rules per edge type. Milliseconds, coarse, always available.

2. Simulator ensemble (fidelity path)
   SUMO (traffic, from Push 6), then pandapower (energy) and EPANET (water) —
   their parked-register re-entry point is exactly here. Scenario packets from
   Push 6 are the input contract.

3. CounterfactualPacket + PLAN integration
   OptionSet v2 (Push 6) extends so every option carries counterfactual references:
   do-nothing, each alternative, with uncertainty bands (§9).

4. Surrogates (late)
   NVIDIA Cosmos re-enters here per the parked register: learned world-model
   surrogates so simulation becomes interactive-speed. Surrogates are
   model_inferred, are always labeled as surrogate outputs, and every surrogate
   ships with a fidelity report against the simulator it approximates.
```

### 6.4 Maturity and roadmap

Current maturity: **M0** (graph edges arrive in Push 4; simulators in Push 6).

```text
L3.R1  Propagation rule registry per dependency edge type + fixtures
L3.R2  Graph intervention engine v1 + InterventionQuery/CounterfactualPacket contracts
L3.R3  PLAN OptionSet counterfactual integration (extends, does not modify, the
       sealed Push 6 approval flow)
L3.R4  SUMO-backed counterfactuals for mobility scenarios
L3.R5  pandapower/EPANET domains; ensemble disagreement surfaced as uncertainty
L3.R6  Cosmos surrogate evaluation (fidelity report gate before any product use)
```

Closure bar: PLAN proposals carry counterfactual comparisons with uncertainty, backed by either graph propagation or simulator runs, each with a CheckReport.

---

## 7. Loop 4 — Institutional memory

### 7.1 What it is

Case-based reasoning over closed episodes: RECALL upgraded from similarity search to precedent retrieval — "three similar cascades since 2024; two resolved by X; here is how this one differs."

### 7.2 Why it exists

Cities re-learn what they already learned every time staff rotate. The outcome ledger (Loop 1) accumulates exactly the episodes — situation → evidence → decisions → outcome — that make precedent retrieval possible. Post-federation, cross-city pattern transfer is the actual intelligence payoff of federation, beyond distributed querying.

### 7.3 Components

```text
1. Case builder
   Materializes CasePackets from OutcomeRecords when an episode reaches terminal
   state (resolved / dismissed / superseded). A case is a governed summary with
   refs, never a copy of raw packets.

2. Precedent retriever
   RECALL computed matchers (Push 3) extended with case-level features:
   situation type, entity classes involved, graph neighborhood shape,
   disposition trajectory, outcome. Returns PrecedentSets with computed
   match reasons (never bare similarity scores).

3. Difference explainer
   For each precedent: what is materially different about the current situation.
   LLM-rendered, evidence-grounded, CHECK-validated (LLM writes, gates own truth).

4. Cross-city transfer (post-federation only)
   Parked until the federation layer exists. City-scoped IDs remain authoritative;
   transfer operates on case abstractions, never raw entities (per non-claims §2.3).
```

### 7.4 Maturity and roadmap

Current maturity: **M0** (RECALL v1 computed matchers arrive in Push 3; ledger depth arrives with Loop 1).

```text
L4.R1  CasePacket contract + case builder from outcome ledger + fixtures
L4.R2  Precedent retrieval over cases (extends RECALL, read-only)
L4.R3  Difference explainer with CHECK validation
L4.R4  Precedents surfaced in BRIEF and PLAN as evidence refs
L4.R5  (post-federation) cross-city case abstraction transfer
```

Closure bar: an operator viewing any review item or plan can pull governed precedents with computed match reasons and stated differences.

---

## 8. Loop 5 — Compound reasoning (the investigation agent)

### 8.1 What it is

The multi-step governed investigation the old 9-stage RECALL→COMPLETE orchestrator was reaching for and never generalized (Doc 06 crosswalk §2). Given "why is this block degrading," the agent autonomously chains ASK → GRAPH → DIFF → forecast → counterfactual → precedent under a budget and an AuthorityEnvelope, and emits an InvestigationPacket in which every intermediate claim carries its own CheckReport.

### 8.2 Why it is last

Loop 5 *composes* Loops 1–4. Built earlier, it is an expensive way to chain shallow answers. Built after, it is deep research over a city — governed.

### 8.3 Components

```text
1. Investigation planner
   Deterministic plan compiler (the G3 execution-contract pattern generalized):
   decomposes an investigation question into a bounded DAG of mode invocations.
   LLM may PROPOSE decompositions (a G2-style proposal seat, per the Push 5
   offline LLM hooks); the compiler validates and owns the executed plan.

2. Budgeted executor
   Runs the DAG under hard budgets (steps, wall clock, tool calls) inside one
   AgentRunEnvelope. Budget exhaustion is a stop condition producing a partial
   InvestigationPacket marked incomplete — never a silent truncation.

3. Claim assembler
   Assembles findings where every claim carries: supporting packet refs,
   CheckReport, and the DAG path that produced it. Contradictions between
   branches are surfaced, not resolved silently.
```

### 8.4 Maturity and roadmap

Current maturity: **M0**.

```text
L5.R1  Investigation plan contract + compiler + fixture DAGs (offline)
L5.R2  Budgeted executor over read-only modes (ASK/GRAPH/DIFF/RECALL)
L5.R3  Forecast + counterfactual + precedent steps enter the step registry
L5.R4  LLM decomposition proposal seat (offline eval, then live under gates)
L5.R5  InvestigationPacket in BRIEF/cockpit as a first-class review artifact
```

Closure bar: a named investigation question type runs end-to-end under budget, produces an InvestigationPacket with per-claim CheckReports, and its cost/quality is ledgered.

---

## 9. Cross-cutting — uncertainty propagation

Confidence today is a scalar that lives per-entity and stops there. Once forecasts and counterfactuals exist, uncertainty must *travel*: through graph traversals, through simulator ensembles, into OptionSets — so a plan carries a calibrated distribution, not a point claim.

### 9.1 Packet-standard extension (additive, does not reopen sealed contracts)

```text
uncertainty:                       # optional block, additive to any packet
  kind: point | interval | distribution | ensemble
  value: <number>                  # if point
  interval: {lo, hi, coverage}     # if interval  (e.g. 0.10, 0.60, 0.80)
  distribution_ref: <artifact>     # if distribution (stored artifact, not inline)
  ensemble: {n, agreement}         # if ensemble (simulator/model ensemble)
  method_ref: <model/version>      # what produced it
  calibration_ref: <CalibrationReport>   # how trustworthy the numbers are
```

Rules:

```text
- Any packet MAY carry uncertainty; ForecastPacket and CounterfactualPacket MUST.
- Composition: when packets combine (investigation, plan), uncertainty combines by
  declared rules per combinator — never by silent averaging.
- Rendering: LLM writers render uncertainty in calibrated language bands defined
  once in a rendering table (e.g. "likely" = declared interval), not ad hoc prose.
- CHECK gains an uncertainty-honesty check: a packet whose prose implies more
  certainty than its uncertainty block supports fails CHECK.
```

This is arguably the single deepest upgrade to the truth layer in the learning epoch, and it is a contract change, so it enters through the same delta process as any frozen-shape amendment (R0.x-style, ledgered).

---

## 10. Packet contracts

Doc 05 style. All packets carry the common fields of Doc 05 (packet id, schema_version, source_class, evidence refs, trace refs, check_report_ref, authority metadata) — restated here only where the loop adds fields. All new shapes below are new contracts; none amends a frozen R0.1 shape. DispositionEvent (§10.1) is the sole item binding on Push 2; all others activate with their loop.

### 10.1 DispositionEvent — authoritative spec (binding for Push 2 Lane C)

Not a new top-level frozen contract. A new EventTypeRegistry entry, so it does not reopen the R0.1 freeze.

```text
event_type: review_item.disposition_recorded
schema_version: 1

payload:
  target_ref:       ref → WatchItem | CandidateObservation   (required)
  disposition:      confirmed | dismissed | needs_more        (required)
  operator_ref:     local pseudonymous operator/session ref   (required)
  timestamp:        ISO-8601                                  (required)
  note:             free text                                 (optional; high-value signal)
  disposition_context:                                        (optional but recommended)
    queue_depth_at_disposition: int
    seconds_since_surfaced: int
    route_ref: which surface/route the disposition came from

supersession:
  A later DispositionEvent for the same target_ref + operator_ref supersedes the
  earlier one (operator changed their mind). The outcome ledger materializes the
  LATEST per operator and the full history remains in the fabric (append-only).

handling policy (restates Sprint Roadmap v1.0 §5 Lane C, binding):
  - Dispositions are local/replay review feedback, not official actions.
  - Individual operator-level visibility is local/admin-scoped.
  - Aggregated dispositions may feed product quality, CHECK/WATCH evaluation,
    and later training signal (Loop 1), subject to the aggregation floor (§4.4).
  - No disposition creates an official case, dispatch, enforcement, legal
    finding, or certified truth.

negative fixtures (mandatory):
  - disposition on a nonexistent target_ref → rejected
  - disposition attempting to set claim/review/authority state → rejected
  - payload claiming source_class official_record → rejected
```

### 10.2 OutcomeRecord (Loop 1)

```text
outcome_record_id
target_ref                    # the review item
trigger_packet_refs           # WatchItem/CandidateObservation + its CheckReport at surface time
disposition_history_refs      # all DispositionEvents, latest-per-operator materialized
terminal_state: confirmed | dismissed | needs_more_expired | superseded
time_to_terminal_seconds
disposition_context_summary   # aggregated triage-noise controls
source_class: derived_field
```

### 10.3 ScoreAdjustment (Loop 1)

```text
score_adjustment_id
target_ref                    # WatchItem
watch_family
model_ref                     # model + version (ledgered release)
score: float                  # ranking hint only
feature_summary_ref           # top contributing features (artifact, not inline)
source_class: model_inferred
non_claims: [ranking_hint_only, no_suppression, no_claim_change]
```

### 10.4 CalibrationReport (Loops 1, 2)

```text
calibration_report_id
subject: check_type | forecast_model | surrogate
model_ref / check_ref
period: {from, to}
reliability_curve_ref         # stored artifact
headline: {expected_calibration_error, drift_vs_previous}
sample_size
aggregation_floor_respected: bool
source_class: derived_field
```

### 10.5 ForecastPacket (Loop 2)

```text
forecast_id
target_ref                    # entity/event/queue being forecast
forecast_type                 # e.g. permit_stall, asset_degradation, queue_spike
horizon: {duration, as_of}
uncertainty: REQUIRED         # §9 block; point forecasts without intervals fail CHECK
model_ref                     # ledgered model version
backtest_ref                  # REQUIRED BacktestReport; no backtest, no forecast (R7.3)
calibration_ref
feature_snapshot_ref
source_class: model_inferred
non_claims: [not_a_finding, not_official, model_output_under_stated_assumptions]
```

### 10.6 BacktestReport (Loop 2)

```text
backtest_id
model_ref
harness_version
train_window / eval_window    # replay-fabric time slices
targets, n
metrics: {discrimination, calibration, lead_time}
baseline_comparison           # must beat declared baseline to ship
fixtures_ref                  # frozen eval slice, hash-manifested
source_class: derived_field
```

### 10.7 InterventionQuery and CounterfactualPacket (Loop 3)

```text
InterventionQuery:
  query_id
  intervention: {target_ref, action, parameters}     # e.g. close(road_segment X)
  scope: {graph_neighborhood | scenario_ref}
  engine: graph_propagation | simulator | surrogate
  budget

CounterfactualPacket:
  counterfactual_id
  query_ref
  baseline: do_nothing | option_ref
  effects: [ {affected_ref, effect_type, magnitude, uncertainty} ]
  propagation_trace_ref        # path through edges / simulator run ref
  engine_ref + fidelity_ref    # for surrogates: fidelity report vs. source simulator
  assumptions: [ ... ]         # explicit, rendered with the packet
  uncertainty: REQUIRED
  source_class: model_inferred
  non_claims: [not_what_would_happen, model_output_under_stated_assumptions]
```

### 10.8 CasePacket and PrecedentSet (Loop 4)

```text
CasePacket:
  case_id
  situation_signature          # typed features: situation class, entity classes,
                               # graph neighborhood shape, city scope
  episode_refs                 # OutcomeRecords, key packets (refs, not copies)
  trajectory_summary           # surfaced → dispositions → terminal state
  outcome_summary
  city_scope                   # city-scoped; no cross-city identity (§2.3)
  source_class: derived_field

PrecedentSet:
  precedent_set_id
  query_ref                    # current situation
  precedents: [ {case_ref, match_reasons[], differences[], match_score} ]
  retriever_model_ref
  source_class: model_inferred
```

### 10.9 InvestigationPacket (Loop 5)

```text
investigation_id
question                       # the operator's investigation question
plan_ref                       # compiled DAG (deterministic artifact)
budget: {allocated, consumed}
status: complete | partial_budget_exhausted | blocked
findings: [ {claim, supporting_packet_refs[], check_report_ref, dag_path_ref} ]
contradictions: [ {branch_a_ref, branch_b_ref, description} ]   # surfaced, not resolved
agent_run_envelope_ref
uncertainty                    # composed per §9 rules
source_class: model_inferred (findings assembled) over mixed-class evidence refs
```

### 10.10 LearnedComponentRegistry (cross-cutting)

Every model, retriever, surrogate, and ranking function is a registered, ledgered component:

```text
component_id, kind, version
training_data_manifest_ref     # what it learned from (hash-manifested)
evaluation_refs                # BacktestReport / CalibrationReport / fidelity report
consuming_surfaces             # where it is used (R7.3: must be non-empty to ship)
release_ledger_row_ref
rollback_ref                   # previous version; rollback is one registry flip
```

---

## 11. Maturity model

Same M0–M6 scale as Docs 02–04, interpreted for loops:

```text
M0 nothing exists
M1 contract + fixtures exist (shapes, negative tests, harness where applicable)
M2 offline capability (runs on replay/fixtures; no product surface)
M3 product-integrated read-only (visible in review surfaces, ledgered releases)
M4 evaluated in use (calibration/backtest monitoring live, Loop 1 labels flowing back)
M5 compounding (retraining cadence established, measurable quality improvement over time)
M6 federated/production-hardened (post-Push 7 concerns)
```

Current and target state:

| Loop | Now | After Push 2 | Learning-epoch target |
|---|---|---|---|
| 1 Outcome learning | M0 | M1 (dispositions flowing) | M5 |
| 2 Prediction | M0 | M0 | M4–M5 (one to three targets) |
| 3 Causal/counterfactual | M0 | M0 | M3–M4 (graph engine M4; simulators M3) |
| 4 Institutional memory | M0 | M0 | M3–M4 |
| 5 Compound reasoning | M0 | M0 | M3 (one investigation type end-to-end) |
| Uncertainty propagation | M0 | M0 | M3 across Forecast/Counterfactual/Plan |

No loop may claim a maturity level without the ledger row and fixtures that evidence it (Doc 06 discipline).

---

## 12. Sequencing — integration with Sprint Roadmap v1.0

### 12.1 What is binding NOW (Push 2)

Exactly one item from this document is binding on Push 2: **the DispositionEvent spec of §10.1**, which is the authoritative elaboration of Sprint Roadmap v1.0 §5 Lane C. Nothing else in this document may start before its earliest-start condition.

### 12.2 Earliest-start conditions

```text
Loop 1 build      after Push 3 closes   (needs disposition history + stable review route)
Loop 2 harness    after Push 4 opens    (needs Event Fabric v1 replay + Loop 1 ledger depth)
Loop 3 engine     after Push 4 closes   (needs Semantic Graph v2); simulators after Push 6
Loop 4 build      after Push 5 opens    (needs closed episodes + RECALL matchers from Push 3)
Loop 5 build      after Loops 1–4 emit real packets
Uncertainty ext.  contract delta any time after Push 4; enforcement with Loop 2
```

### 12.3 The learning-epoch push sequence (indicative, 3-lane discipline preserved)

```text
Push L1 — Label factory:        Lane A outcome ledger + OutcomeRecord
                                Lane B CHECK CalibrationReport v1
                                Lane C feedback ranking offline eval
Push L2 — Anticipation:         Lane A backtest harness
                                Lane B forecast v1 (permit-stall) offline
                                Lane C forecast WATCH family + ranking live
Push L3 — What-if:              Lane A propagation registry + intervention engine
                                Lane B counterfactual/PLAN integration
                                Lane C uncertainty extension enforcement
Push L4 — Memory:               Lane A case builder
                                Lane B precedent retrieval + difference explainer
                                Lane C precedents in BRIEF/PLAN
Push L5 — Investigation:        Lane A plan compiler + executor
                                Lane B step registry over all modes/loops
                                Lane C InvestigationPacket in cockpit
```

These pushes interleave with Pushes 5–7 of the sprint roadmap rather than strictly following them; the earliest-start conditions of §12.2 are the binding constraint, not the push labels. Track 0/INFRA discipline (ledger, corpus growth, hash manifests, source-of-truth matrix) applies unchanged.

### 12.4 Regression corpus interaction

Each loop closeout appends its fixtures to the corpus (harness eval slices, calibration fixtures, DAG fixtures, negative tests) under the corpus growth rule. Learned-component *releases* additionally pin their frozen eval slices so that later data changes cannot silently alter a published evaluation.

---

## 13. Model acceptance discipline (Doc 05 §25 extended)

The data acceptance rule generalizes:

```text
No dataset without a consuming capability.          (Doc 05 §25 — unchanged)
No model without a consuming decision surface       (R7.3 — new)
  AND a published evaluation on the shared harness
  AND a registered rollback path.
No evaluation without a frozen, hash-manifested eval slice.
No silent retraining: every version is a ledgered release.
```

Failure modes this exists to prevent: models built because they are interesting; evaluations on moving data; quality regressions with no rollback; "the model got worse and nobody can prove when."

---

## 14. Parked-register re-entry via loops

Confirms and refines the Sprint Roadmap v1.0 §11 re-entry column:

| Parked item | Re-enters at | As |
|---|---|---|
| Earth-2 / CorrDiff | Loop 2 (L2.R5) | environmental forecast feature feed |
| SUMO | Push 6 → Loop 3 (L3.R4) | first fidelity-path simulator |
| pandapower / EPANET | Loop 3 (L3.R5) | energy/water counterfactual domains |
| NVIDIA Cosmos | Loop 3 (L3.R6) | world-model surrogates, fidelity-gated |
| Cross-city intelligence | Loop 4 (L4.R5), post-federation | case-abstraction transfer |
| Citywide twin | unchanged | demand-driven; not a loop dependency |
| GNN stack (cuGraph-PyG) | Loops 1–2 feature/embedding layer; Loop 4 retrieval | link prediction, ER improvement, anomaly features — enters only via the model acceptance discipline of §13 |

---

## 15. Risks and failure modes

```text
1. Feedback loops (biggest structural risk)
   Ranking trained on dispositions of items the ranking itself surfaced → the
   system narrows what it shows, then learns from the narrowed view.
   Mitigations: exploration floor (a fixed fraction of items surfaced regardless
   of score), suppression forbidden at model level (R7.1/§4.3), periodic
   holdout families ranked statically.

2. Label noise and operator gaming
   Dismissals driven by workload, or operators learning to game queues.
   Mitigations: disposition_context controls, aggregation floor, calibration
   monitored per family, usability sessions (Track 0) reviewing queue behavior.

3. Silent drift
   Data distribution shifts; model quality decays invisibly.
   Mitigations: CalibrationReports with drift alarms as a standing WATCH family
   (the system watches its own models).

4. Uncertainty theater
   Intervals rendered but never calibrated; prose overclaiming under a fig-leaf
   interval. Mitigations: calibration_ref mandatory, CHECK uncertainty-honesty
   test (§9), rendering table for calibrated language.

5. Privacy creep on operator data
   Disposition data is the first operator-behavior dataset the system stores.
   Mitigations: R7.5, aggregation floor, admin-scoped individual visibility,
   policy note owned by Track 0 before Loop 1 build starts.

6. Loop 5 cost blowout
   Investigations consuming unbounded budget for marginal findings.
   Mitigations: hard budgets in the run envelope, cost/quality ledgered per
   investigation type, partial-result semantics instead of overruns.
```

---

## 16. Open questions (to resolve before each loop's build starts)

```text
Q1  Aggregation floor N and the operator-data policy note        (before Loop 1 build; Track 0)
Q2  First forecast target confirmation (permit-stall proposed)   (before L2.R2)
Q3  Propagation rule authorship: who declares per-edge-type
    rules, and how are they evidenced?                           (before L3.R1)
Q4  Calibrated-language rendering table ownership (CHECK vs
    BRIEF)                                                       (before §9 enforcement)
Q5  Case retention and right-to-forget interaction for
    CasePackets containing party-linked episodes                 (before L4.R1)
Q6  Whether the uncertainty extension enters as R0.2 delta or
    a new frozen contract set                                    (before Loop 2 ships)
```

---

## 17. Bottom line

```text
The current roadmap builds a system that is right.
This document builds the system that gets better.

Five loops, in dependency order:
  1. Learn from outcomes        (seeded in Push 2 by one small event type)
  2. Predict before querying
  3. Reason about interventions
  4. Remember and transfer
  5. Investigate autonomously — under budget, under authority, under CHECK

Everything learns. Nothing claims. Nothing acts.
The gates still own the truth.
```
