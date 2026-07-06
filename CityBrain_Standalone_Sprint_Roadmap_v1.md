# CityBrain Standalone Sprint Roadmap v1.0

**Remaining Work, Sprint Sequencing, Parallel Tracks, Gates, and Parked Full-Vision Register**

## 1. Purpose and status

This is a standalone roadmap. It replaces the earlier "Remaining Work" document plus the v0.2 amendment as the working sprint plan. It includes the residual dependency fixes: regression corpus growth, DispositionEvent shape, parked item re-entry points, corpus timing at the INFRA gate, Watch family sequencing, source freshness policy, and explicit no-cross-city-claims discipline.

The next runnable sprint remains **Push 2 - CHECK / WATCH / App Review Route**, but it must start only after the INFRA gate completes and publishes Regression Corpus v1.

## 2. Current baseline

| Area | Current status | Notes |
|---|---|---|
| ASK v1.1 core | Sealed / published | Deterministic G1-G8 path remains protected. |
| ASK real-corpus eval R2 | Passed with limitation | Contradiction real-corpus coverage waived until retained same-claim pair exists. |
| ASK app surface | Branch-published / closeout done | Fixture vendoring and deterministic render-state smoke closed; no live LLM/retrieval. |
| Event Fabric R0.1 | Branch-published / corrected | Imports Doc 05 shapes; owns only new Event Fabric shapes; shared validator exists. |
| Spatial Review Surface | Branch-published | Local review bundle, WebUI fixture, Kit marker export, marker-only USDA, parity report. |
| Perception-to-Event | Branch-published | 6 samples through R0.1-compatible CandidateObservation/EventEnvelope/query/overlay path. |
| Event Fabric Runtime Spine | Branch-published | Local/replay append, replay, materialize, query and overlay helpers. |
| Cross-track compatibility sync | INFRA pushed integration branch | Not canonical merged; canonical merge/PR prep is INFRA-owned. |

## 3. Global gates and non-claims

### 3.1 INFRA gate before Push 2

Push 2 must not start until INFRA completes the event-contract compatibility sync gate and publishes Regression Corpus v1.

Required order:

1. INFRA compatibility sync branch exists and passes.
2. Regression Corpus v1 is published and hashed.
3. Source-of-truth matrix is updated.
4. Push 2 lanes may start.

### 3.2 Universal non-claims

- No official case/ticket submission, dispatch, control, enforcement, or execution until approval/execution lanes authorize it.
- No legal finding, certified violation, or final determination in review/watch/spatial/perception output.
- No live Kit control, full citywide twin claim, live camera, production API, URL fetch, or live retrieval until explicitly introduced in a governed sprint.
- No LLM may source facts, compute claimability, or grant authority.
- No cross-city operational claims until federation exists.
- No forced global canonical entity identity across cities; city-scoped IDs remain authoritative until federation packages explicitly map them.

## 4. Track 0 - continuous INFRA / ledger / regression discipline

Track 0 is continuous and does not count as a product lane. It rides alongside every push.

Responsibilities:

- Branch hygiene, canonical integration, PR prep, merge/cherry-pick, and staged-scope audit.
- Master published ledger, source-of-truth matrix, and hash manifests.
- Regression corpus versioning and keep-green rule.
- Source freshness/ingestion maintenance policy and last-refreshed ledger.
- Parked/full-vision register.
- Documentation debt: D13/R5 label fix, resource/development entity-type mapping, executive one-pager, R3 docs release with operating agreement and cadence.
- Ledger row per closeout.

### 4.1 Regression corpus rule

Regression Corpus v1 is an INFRA gate deliverable before Push 2 lanes open.

Each later push closeout must append newly sealed fixtures to the corpus:

- Push 2 closeout appends v2.
- Push 3 closeout appends v3.
- Push 4 closeout appends v4.
- Each corpus version has its own manifest hash and release note.

The corpus must grow, not remain static.

Minimum v1 contents:

- ASK sealed questions and expected bounded answers.
- Watch scenarios.
- Perception samples and expected candidate outputs.
- Spatial parity fixtures.
- R0.1 valid/invalid contract fixtures.
- Negative boundary examples.

### 4.2 Source freshness policy

CHECK v0 will honestly mark stale sources. That must be treated as a source-maintenance signal, not a system failure.

Track 0 must define:

- freshness thresholds by source class;
- stale flag interpretation for local/replay demos;
- source last-refreshed ledger;
- refresh rider before Push 3 Flow 1 packaging, or explicit stale evidence labeling.

### 4.3 Source-of-truth matrix columns

| Column | Meaning |
|---|---|
| Frozen shape / packet / artifact | Contracted object or package. |
| Owning doc or contract path | Authoritative source. |
| Owning branch/package | Where it was sealed. |
| Validator/test owner | Test suite or validator package. |
| Hash manifest | Current immutable manifest. |
| Current published status | Branch-published, integrated, canonical, parked. |
| Downstream consumers | ASK, Event Fabric, WATCH, Kit, Perception, etc. |

## 5. Push 2 - CHECK / WATCH / App Review Route

### Sprint purpose

Turn the existing event fabric and review packets into a checked, proactive, operator-visible product loop.

Product exit statement:

> CityBrain can ingest candidate/review events, evaluate claimability and authority, proactively surface review prompts, and show them in a single operator review surface with evidence, limitations, trace, dispositions, and no-action boundaries.

### Lane A - CHECK v0 + AuthorityEnvelope v1

Purpose: Build the first real claimability and authority layer.

Scope:

- CHECK v0.
- AuthorityEnvelope v1.
- CheckReport schema/output.
- authority-level stamping, levels 0-2.
- source-class validation.
- freshness checks.
- candidate-vs-verified checks.
- boundary/non-claim checks.
- negative tests.
- quarantine substrate decision.

Applies to:

- CandidateObservation.
- EventEnvelope.
- QueryResultPacket.
- OverlayPacket.
- WatchItem.
- ASK AnswerPacket/rendered ASK surface where available.

Quarantine decision:

- First check whether runtime materialized state already includes quarantine.
- If yes, WATCH family 2 can consume quarantined_or_boundary_blocked items.
- If not, either add a small Event Fabric quarantine increment in Push 2 or swap the family to boundary_test_failed_packets emitted by CHECK v0.
- Expiry and supersession move to Push 4 unless a smaller quarantine-only increment is required now.

Closure:

- All accepted review-facing outputs carry real CheckReports, not `not_evaluated`.
- AuthorityEnvelope v1 stamps packets consistently.
- Unclaimable claims fail CHECK.
- Stale source status is honest and interpretable.

### Lane B - WATCH Scout v1

Purpose: First proactive consumer of Event Fabric materialized review state.

Initial families:

1. unresolved_candidate_observations.
2. quarantined_or_boundary_test_failed_items.
3. stale_or_low_authority_review_items.
4. new_review_events_since_last_snapshot.

Sequencing rule:

- Families 1, 3, and 4 may scaffold against materialized state.
- Family 2 must run last because it depends either on quarantine substrate or CHECK v0 boundary-test-failed packets.
- Lane B cannot close until Lane A CheckReports and AuthorityEnvelope exist.

WatchItem must include:

- watch_item_id;
- watch_family;
- event_refs;
- candidate_observation_refs;
- evidence_refs;
- limitation_refs;
- trace_refs;
- check_report_ref;
- authority_envelope_ref;
- authority_level;
- review_required;
- not_official;
- not_executed;
- safe_next_looks;
- cannot_claim.

Closure:

- 3-4 WATCH families run against materialized review state.
- WatchItems are review prompts, never findings.
- Each WatchItem carries evidence, limitations, trace, CheckReport and AuthorityEnvelope.

### Lane C - App Review Route Closure + Disposition Capture

Purpose: One operator route/workspace for perception and WATCH review prompts.

Scope:

- review route / workspace;
- selected item view;
- candidate observations;
- WatchItems;
- evidence refs;
- limitation refs;
- trace refs;
- CheckReport display;
- AuthorityEnvelope display;
- source class display;
- not_executed display;
- cannot_claim display;
- safe next looks;
- spatial overlay reference where available;
- operator disposition capture.

DispositionEvent shape decision:

DispositionEvent is **not** a new top-level frozen packet contract. It is a new EventTypeRegistry entry, so it does not reopen the R0.1 freeze.

Event type:

```text
review_item.disposition_recorded
```

Minimum payload:

```text
target_ref: WatchItem or CandidateObservation being dispositioned
disposition: confirmed | dismissed | needs_more
operator_ref: local pseudonymous operator/session reference
timestamp: ISO timestamp
note: optional free-text note
```

Handling policy:

- Dispositions are local/replay review feedback, not official actions.
- Individual operator-level visibility is local/admin-scoped.
- Aggregated dispositions may be used for product quality, CHECK/WATCH evaluation, and later training signal.
- No disposition creates an official case, dispatch, enforcement, legal finding, or certified truth.

Closure:

- One app route shows perception candidate observations and WatchItems.
- Selected item shows evidence, limitations, trace, CheckReport, AuthorityEnvelope, source class, cannot_claim and not_executed.
- Disposition events write back to the local/replay event fabric.
- No official action affordance appears.

## 6. Push 3 - First packaged product: Phase 4 core + Flow 1

### Purpose

Move from internal tracks to a packaged product experience.

### Lane A - BRIEF v2 + Flow 1 packaging

- CHECK-integrated briefs with export.
- Flow 1: situational status.
- Composes ASK + WATCH + BRIEF + spatial over one entity scope.
- Demo narrative and package manifest.

### Lane B - Cockpit selected-item workspace + source-record 360

- Select a subject and inspect every source record.
- Surface every conflict, packet, evidence ref, limitation and trace about it.
- Make selected item the operator's working surface.

### Lane C - DIFF Scout v1 + RECALL computed matchers

- DIFF change-driven items.
- RECALL computed match reasons.
- DIFF feeds WATCH.
- Read-only mode family becomes ASK / WATCH / DIFF / RECALL.

### Exit

An operator works one patch end-to-end:

```text
select → ask → watch → diff → brief → export
```

Everything carries CheckReports.

## 7. Push 4 - Deepen truth: CER / Semantic Graph / CHECK v1

### Dependency rule

Push 4 has the same intra-sprint dependency pattern as Push 2:

- Lane A CER engine defines attribute assertions, conflicts, match candidates and review state.
- Lane B Semantic Graph v2 may scaffold dependency edges but must align to CER entity/assertion IDs before closeout.
- Lane C CHECK v1 may scaffold early but cannot close until it consumes CER assertion outputs.

### Lane A - CER engine

- Attribute assertions.
- Attribute conflicts.
- Match candidates.
- Confidence/review-state as first-class runtime objects.
- Entity identity becomes executable engine, not architecture only.

### Lane B - Semantic Graph v2 + cross-domain dependency edges

- Energy, water, transport dependencies.
- Asset-to-asset and service-point edges.
- Graph edges aligned to CER entity/assertion IDs.

### Lane C - CHECK v1

- Claim-to-evidence mapping.
- Contradiction detection.
- Source-depth.
- Consumes CER assertions.

### Exit

CityBrain can say what an entity is, what sources disagree on, and prove every claim traces to evidence.

Expiry and supersession belong here unless a small Push 2 quarantine-only increment was required.

## 8. Push 5 - Spatial / perception product depth + validation

### Lane A - Omniverse UI/UX lane un-parked

- Native Kit entity/evidence panel.
- Spatial overlay manager.
- Event overlays.
- Still no live control claim.

### Lane B - Perception expansion

- Source-registry growth.
- CHECK detection-sufficiency.
- Media evidence bundles.
- Still local/replay and candidate-only unless a later production sprint changes that.

### Lane C - WATCH expansion + workflow states

- More Watch families.
- hold / abstain / propose states.
- Review workflow state transitions.

### Track 0 / human-owned validation

- Operator usability sessions run across Push 5, not inside Lane C.
- LLM hooks are a slip candidate, not required Push 5 closure.

### LLM proposal hooks slip candidate

If time/safety allow:

- G2 resolver proposal offline tests.
- G8 writer proposal offline tests.
- No live LLM authority.

## 9. Push 6 - Proposals and authority level 3

### Lane A - Approval workflow + Approval Lifecycle Agent

- Approval object.
- approve / reject / modify states.
- Audit log.
- Ships before PLAN/SCHEDULE/SIMULATE proposals.

### Lane B - PLAN mode

- OptionSet v2.
- Do-nothing baseline.
- Abstain / no-safe-option state.
- Assumptions, risks, constraints, approval requirements.

### Lane C - SCHEDULE + SIMULATE v1

- cuOpt scheduling families.
- SUMO as first simulator.
- Scenario packets.
- Simulation CHECK.

### Exit

Candidate plans with constraints, assumptions, risks and required approvals. Proposed, never executed.

## 10. Push 7 - Scale-out

Do not lane-plan Push 7 until Push 6 closes. Its shape depends on customer/demo pressure.

Potential areas:

- federation;
- Dubai synthetic pack and gold/dirty/challenge data;
- data maturity dashboard;
- department-local nodes;
- cross-city recall;
- production RBAC/audit/observability;
- authorized execution adapters levels 4-5;
- conditional autonomy level 6.

## 11. Parked / Full Vision Register with re-entry points

| Parked item | Why parked | Re-entry point |
|---|---|---|
| SUMO traffic simulation | Needs checked event/plan substrate first | Push 6 Lane C |
| pandapower energy simulation | Needs CER/graph dependency depth | Post-Push 7 / Loop 3 |
| EPANET water simulation | Needs CER/graph dependency depth | Post-Push 7 / Loop 3 |
| NVIDIA Cosmos / world model path | Needs stable scenario/simulation strategy | Surrogate phase after Push 6/7 decision |
| Earth-2 / CorrDiff | Needs forecast/scenario phase and weather/flood requirements | Forecast phase |
| Citywide OpenUSD twin | Too large before demand and object-binding maturity | Demand-driven after hero-neighbourhood/product proof |
| Closed-loop simulation | Requires approval workflow and simulator CHECK | After Push 6 |
| Production federation / cross-city intelligence | Requires city-scoped identity, domain packs and governance | Push 7+ |
| Authorized execution adapters | Requires approval lifecycle, RBAC/audit, legal readiness | Push 7+ |
| Conditional autonomy | Requires proven approval/execution controls | Long-range post-Push 7 |

## 12. Original lane disposition

| Original lane | Status | New home |
|---|---|---|
| Event Fabric R1/R2 hardening | First local runtime spine done. | Remaining hardening folded into Push 2 CHECK/WATCH acceptance and later runtime hardening. |
| Perception replay bridge expansion | First R0.1-compatible slice done. | Deeper expansion in Push 5 after CHECK v0. |
| Spatial review polish / browser smoke | Spatial bundle and ASK render-state smoke done. | Operator route work becomes Push 2 Lane C. |
| Browser/operator demo smoke | Partially covered by ASK static render-state smoke. | Full operator-route smoke in Push 2 Lane C / Push 3 package. |

## 13. Remaining item register

| Item | Assigned sprint/lane | Closure signal |
|---|---|---|
| CHECK v0 | Push 2 Lane A | CheckReports on review packets. |
| AuthorityEnvelope v1 | Push 2 Lane A | Authority 0-2 stamped consistently. |
| Quarantine decision | Push 2 Lane A/B | Quarantine substrate exists or WATCH family uses boundary_test_failed_packets. |
| Freshness policy | Track 0 + Push 2 Lane A | Thresholds and stale interpretation recorded. |
| WATCH Scout v1 | Push 2 Lane B | 3-4 checked WatchItem families. |
| App review route | Push 2 Lane C | Perception and Watch items visible in one route. |
| Operator DispositionEvent | Push 2 Lane C | confirmed/dismissed/needs_more events written locally. |
| Regression corpus v1 | INFRA gate before Push 2 | Corpus v1 published with hash manifest. |
| Corpus growth rule | Track 0 ongoing | Each push adds v2/v3/etc. |
| BRIEF v2 | Push 3 Lane A | Exportable checked brief. |
| Flow 1 package | Push 3 Lane A | Situational status cartridge. |
| Selected-item workspace | Push 3 Lane B | 360 source record view. |
| DIFF Scout v1 | Push 3 Lane C | Change-driven review items. |
| RECALL computed matchers | Push 3 Lane C | Similar cases with computed reasons. |
| CER engine | Push 4 Lane A | Attribute assertions/conflicts/match candidates. |
| Semantic Graph v2 | Push 4 Lane B | Cross-domain dependency edges aligned to CER assertions. |
| CHECK v1 | Push 4 Lane C | Claim-to-evidence and contradiction detection. |
| Native Kit UX | Push 5 Lane A | Entity/evidence panel and overlay manager. |
| Perception expansion | Push 5 Lane B | More checked source/media samples. |
| Workflow states | Push 5 Lane C | hold/abstain/propose states. |
| Operator usability | Track 0 across Push 5 | Findings and fixes ledgered. |
| Offline LLM hooks | Push 5 slip candidate | G2/G8 offline proposal tests only. |
| Approval lifecycle | Push 6 Lane A | Approval object and audit log. |
| PLAN | Push 6 Lane B | OptionSet with do-nothing/abstain. |
| SCHEDULE/SIMULATE | Push 6 Lane C | cuOpt/SUMO scenario packets with CHECK. |
| Federation/scale-out | Push 7+ | To be lane-planned after Push 6. |

## 14. Recommended immediate order

1. Finish INFRA canonical merge / PR prep for the Sprint 2 compatibility sync.
2. Publish Regression Corpus v1 as an INFRA gate.
3. Start Push 2 Lane A first: CHECK v0 + AuthorityEnvelope v1.
4. Let Lane B and Lane C scaffold in parallel.
5. Do not close Lane B or Lane C until Lane A outputs are real.
6. By Push 2 closeout, operator disposition events must flow.
