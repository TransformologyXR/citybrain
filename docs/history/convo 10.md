Below is the chronological CityBrain build summary from this thread. I’m treating the dates as the reported run/acceptance dates in this project thread, not as an independent filesystem audit. The latest board/docs state was captured in the Mission Control and To-Do surfaces we updated.  

## Chronological build timeline

### 2026-06-14 — CityBrain scope widened from property twin to full city brain

The project direction expanded beyond DLD/DM land, building, permit, and compliance data into a broader **graph-based city intelligence system**. The working model became: city entities, networks, events, observations, and time-aware relationships across roads, transit, power, water, communications, environment, civic services, and economy.

Key outcome:

```text
CityBrain became a multi-network, multi-rate, graph-based digital twin brain,
not only a property or planning analytics tool.
```

This is also where the long-term CER/SEG thinking matured: **Canonical Entity Registry first, Semantic Entity Graph on top**, because the core problem is identity under ambiguity rather than simple data integration. 

---

### 2026-06-24 to 2026-06-25 — GPU foundation built

Two GPU boxes were established as the physical runtime foundation.

Built:

```text
txr-3090
- RTX 3090
- RAPIDS / cuDF / cuGraph capable
- SSH working
- Docker GPU working
- real-data RAPIDS probe passed
- CityBrain data/scripts synced under /data/citybrain

txr-4070
- RTX 4070
- Node/npm/pnpm working
- Caddy working
- web routes served successfully
- /, /map, /trace, /briefing, /status.json all HTTP 200
```

Key outcome:

```text
3090 became the data/graph/GPU compute box.
4070 became the face/dashboard/trace/briefing box.
```

---

### 2026-06-27 — Singapore source/API scout built, but LTA auth blocked

Built a Singapore D1 source/API scout.

Result:

```text
Final status: FAIL due to LTA DataMall HTTP 401
```

But public data worked:

```text
NEA / data.gov.sg public sources landed
OneMap partially usable but token-limited
LTA endpoints probed: 25
LTA endpoints pulled: 0
```

Key outcome:

```text
Singapore split into:
SG-F4-public = usable public context path
SG-F4-LTA-mobility = blocked by auth
```

This later became important because Singapore was not abandoned; it was split into a public route and an LTA-auth-blocked route.

---

### 2026-06-28 — Track 1 D2 integrated runtime smoke completed

Built and passed:

```text
MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE
PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS
```

Inputs verified:

```text
Event Fabric D2
Perception D2
SUMO D2
```

Produced a unified local/replay review runtime, joining multiple event sources into one bounded event stream.

Key outcome:

```text
Track 1 proved an integrated runtime smoke path with Event Fabric,
Perception, and SUMO context joined into review-only outputs.
```

---

### 2026-06-28 — Track 1 D2 closeout and D3 roadmap built

Built and passed:

```text
MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP
PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS
```

Key outcome:

```text
D2 was closed with an explicit D3 roadmap,
preserving source limits and review-only boundaries.
```

---

### 2026-06-28 — D6 control-room closeout refresh built

Built and passed:

```text
MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH-R2
PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS
```

It confirmed:

```text
Omniverse Kit / Composer = primary spatial control-room surface
web = companion evidence / episode / executive surface
local/replay context only
no autonomous monitoring, alert push, routing, control, dispatch, enforcement, or legal claim
```

Key outcome:

```text
The project got a clean control-room reference framing:
Omniverse for spatial surface, web for evidence and review.
```

---

### 2026-06-30 — D6 control-room reference demo pack built

Built and passed:

```text
MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1
PASS_WITH_LIMITATIONS
```

Artifacts included:

```text
master decision
closeout decision
local open index
operator/executive scripts
acceptance matrices
evidence walkthrough
Omniverse supporting sequence
audit reports
```

Key outcome:

```text
A self-contained control-room reference demo pack was frozen,
but frontend visual acceptance remained not done.
```

---

### 2026-06-30 — NYC cascade scenario layer built

Built and passed:

```text
PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_CLOSEOUT_WITH_LIMITATIONS
PASS_MAIN_CITYBRAIN_D8_NYC_CASCADE_SCENARIO_LAYER_MILESTONE_FREEZE_WITH_LIMITATIONS
```

Created the second distinct primary story after Wood Lane:

```text
story:nyc:cascade:mvc_crash_4463710
subject: MVC crash 4463710 near Howard Avenue with Engine 227 context
```

Included:

```text
1 source record
6 affected/context records
5 review options
5 beats
```

Boundary preserved:

```text
candidate tax-lot context ≠ certified affected-building truth
response-resource context ≠ dispatched-unit truth
review itinerary ≠ action instruction
```

---

### 2026-07-01 — D8 final demo capture and certified handoff built

Built and passed:

```text
PASS_MAIN_CITYBRAIN_D8_FINAL_DEMO_CAPTURE_AND_CERTIFIED_HANDOFF_R1_WITH_LIMITATIONS
```

Frozen demo state included:

```text
Helsinki: 20 pending pick packets
Chicago: 15 reviewed cases, 45 bounded matches, 1 abstain case
VSS sample ingest gate: CLOSED
7-step final demo route
```

Key outcome:

```text
The final demo route was certified as a bounded review demo,
not an action/control product.
```

---

### 2026-07-01 — D9 demo polish / review loop built

Built and passed:

```text
PASS_MAIN_CITYBRAIN_D9_DEMO_POLISH_AND_REVIEW_LOOP_R1_WITH_LIMITATIONS
```

Scorecard:

```text
6 PASS
2 PASS_WITH_LIMITATIONS
1 NEEDS_REVIEW
```

Remaining gap:

```text
screenshot/video capture not completed
```

---

### 2026-07-03 — DeepStream product runtime smoke built

Built and passed:

```text
PASS_R9_DEEPSTREAM_PRODUCT_RUNTIME_EXECUTION_SMOKE_WITH_LIMITATIONS
```

Runtime facts:

```text
NVIDIA DeepStream 8.0.0
container: nvcr.io/nvidia/deepstream:8.0-samples-multiarch
GPU visible: true
pipeline status: PASS
exit code: 0
Received EOS
App run successful
```

Detected:

```text
29,686 total detections
21,446 car
7,569 person
668 bicycle
3 road_sign
1,443 raw metadata files
```

Key outcome:

```text
DeepStream was proven as real product runtime execution,
not just planned perception architecture.
```

---

### 2026-07-03 — Metropolis / VSS cockpit integration smoke built

Built and passed:

```text
PASS_METROPOLIS_VSS_BMD45_COCKPIT_REVIEW_INTEGRATION_SMOKE_R21_WITH_LIMITATIONS
```

Produced:

```text
cockpit tile
cockpit app fixture
8 cockpit review cards
8 external media refs
0 packaged media files
```

Boundary preserved:

```text
BMD-45 = dataset_annotation
DeepStream/Metropolis = sensor_inferred
VSS = model_generated_narrative_not_fact_source
```

Key outcome:

```text
Metropolis/VSS could feed a cockpit review surface,
but not become a fact source or action authority.
```

---

### 2026-07-03 — Push 1–7 full-stack validation completed

Built and passed:

```text
PASS_MAIN_CITYBRAIN_PUSH1_TO_PUSH7_FULL_STACK_VALIDATION_WITH_LIMITATIONS
```

Validated:

```text
artifact inventory
hash manifests
schemas/contracts
end-to-end refs
boundary scans
security staged scan
focused validation tests
protected ASK/R7 runtime diff
```

Limitations remained:

```text
broader discovery still affected by older fixture assumptions
444 tests: 22 errors, 1 failure, 21 skips
```

Key outcome:

```text
A large full-stack validation pass was completed,
with known older-test limitations explicitly preserved.
```

---

### 2026-07-06 — Epoch 3 Hidden Data Scout Master built

Built and passed:

```text
PASS_E3_HIDDEN_DATA_SCOUT_MASTER_R1_WITH_LIMITATIONS
```

Candidate counts found:

```text
A: 10 hidden transition targets
B: 9 CHECK calibration candidates
C: 8 L4 case-memory candidates
D: 8 identity/graph eval candidates
E: 8 LLM/perception usefulness candidates
TRACK0: 12 global backlog candidates
```

Key outcome:

```text
Epoch 3 produced a governed backlog of hidden data / calibration / eval candidates.
```

---

### 2026-07-06 — Post-E3 / Epoch 4 fork preflight built

Built and passed:

```text
PASS_POST_E3_EPOCH4_FORK_PREFLIGHT_R1_WITH_LIMITATIONS
```

Created:

```text
runner
tests
E4 schemas
durable governance publication
```

Key outcome:

```text
Epoch 4 fork readiness was captured without turning it into active uncontrolled work.
```

---

## Current thread: PV1 closure and post-PV1 addendum

### 2026-07-07 — PV1-D13/D14/D15 HITL Approval Lifecycle built

Built and passed:

```text
PV1-D13/D14/D15
PASS_HITL_APPROVAL_LIFECYCLE
```

Created:

```text
txr_citybrain_pv1_d13d14d15_hitl_approval_lifecycle.py
scripts/run_pv1_d13d14d15_hitl_gate.py
outputs/pv1_d13_hitl_approval_contract
outputs/pv1_d14_hitl_workflow_runner
outputs/pv1_d15_hitl_integration_proof
outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate
```

Results:

```text
D13 approval contract/state machine: PASS
D14 workflow runner/audit ledger/determinism: PASS
D15 Incident/Plan/SUMO/review-route integration: PASS
audit records: 14
hash chain verified
operational actions: 0
dispatch/control/enforcement actions: 0
```

---

### 2026-07-07 — PV1-D16/D17/D18 Persona Renderings built

Built and passed:

```text
PV1-D16/D17/D18
PASS_PERSONA_RENDERINGS
```

Created:

```text
persona rendering contract
persona rendering generator
persona rendering integration proof
umbrella gate
```

Results:

```text
6 personas rendered
same evidence base across personas: true
unsupported claim classes suppressed: 5
D17 determinism: PASS
Incident/Plan/SUMO/HITL/Track2 rendering: PASS
traceability: PASS
operational/dispatch/control/enforcement actions: 0
```

Key outcome:

```text
Personas became rendering policies over the same evidence,
not separate agents inventing different truths.
```

---

### 2026-07-07 — Chicago and NYC bulk source completions landed

Chicago:

```text
Cook County parcels:
22,860,605 / 22,860,605 FULL

Open Air individual:
8,961,666 / 8,961,666 FULL

Chicago total:
60,439,885 rows
30,861,397,596 bytes
```

NYC:

```text
NYC 311 2020-present recent window:
created_date >= 2022-06-28
13,924,344 / 13,924,344 WINDOWED_COMPLETE

NYC total:
17,689,310 rows
10,675,710,829 bytes
```

Key outcome:

```text
The previous Track 2 bulk backlog was materially strengthened,
but not converted into flow acceptance by data volume alone.
```

---

### 2026-07-07 — XDATA-BULK-SWEEP-D1 built

Built and passed:

```text
XDATA-BULK-SWEEP-D1
PASS_BULK_SWEEP
```

Verified:

```text
Chicago Cook parcels: FULL
Chicago Open Air individual: FULL
NYC 311 recent window: WINDOWED_COMPLETE
no .part files
no failed downloads
```

Impact:

```text
NYC-F1X strengthened by completed 311 recent window
CHI-F4X strengthened by full Cook parcels + full Open Air individual
data-route catalog refresh recommended
D3 refresh recommended for NYC-F1X-D3-R1 and CHI-F4X-D3-R1
```

---

### 2026-07-07 — FLOWX-DATA-ROUTE-CATALOG-R1 + Targeted D3-R2 built

Built and passed:

```text
FLOWX-DATA-ROUTE-CATALOG-R1 + TARGETED D3-R2
PASS_TARGETED_D3_R2_AND_DATA_ROUTE_CATALOG_R1
```

Created:

```text
NYC-F1X-D3-R2
CHI-F4X-D3-R2
FLOWX-DATA-ROUTE-CATALOG-R1
Track 2 Closeout R2 addendum
umbrella gate
```

Results:

```text
NYC-F1X-D3-R2: PASS
CHI-F4X-D3-R2: PASS
data-route-ready rows: 7
review-route-ready not accepted: 5
new Track 2 accepted flows: 0
D4/D5/D6 rerun: NOT_REQUIRED
whole Track 2 rerun: false
```

Key outcome:

```text
Track 2 became closed, strengthened, source-updated, data-route-catalogued,
review-route-ready, and still not acceptance-complete.
```

---

### 2026-07-07 — DOC-POST-PV1-FORK-D1 built

Built and passed:

```text
DOC-POST-PV1-FORK-D1
PASS_DOC_POST_PV1_FORK_CAPTURED
```

Updated:

```text
TXRCityBrain_03_PlatformV1DoD.md
TXRCityBrain_04_FullVisionCompletionMap.md
```

Captured:

```text
PV1-D19/D20 actuator / LLM / control boundary
post-PV1 strategic fork
platform gap map
Omniverse manual asset-lane boundary
autonomy deferral
```

Key outcome:

```text
The project explicitly fenced autonomy as a future safety-critical program,
not the next active build lane.
```

This fits the broader architecture principle that CityBrain is a review-only intelligence loop, not a control system; the north-star loop is source/media/events → identity → graph → WATCH/ASK/CHECK/BRIEF/RECALL/PLAN/SPATIAL → human workflow → governance trace. 

---

### 2026-07-07 — PV1-D19/D20/D21/D22 final snapshot built

Built and passed:

```text
PV1-D19/D20/D21/D22
PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT
```

Results:

```text
D19 action policy: PASS
D20 guardrail harness: PASS
D21 composite snapshot: PASS
D22 final audit: PASS

Forbidden actions blocked: 20/20
Allowed review actions allowed: 4/4
Claim misuse blocked: 4/4

Accepted flows indexed: 8
Review-route-ready flows indexed: 5
Candidate-only flows indexed: 3
Data-route-ready rows indexed: 7

No-overclaim: PASS
No-mutation: PASS
Hashes: PASS
```

Key outcome:

```text
PV1 closed as a governed, evidence-backed, review-only Platform v1 snapshot.
```

It preserved:

```text
no production control
no autonomous operation
no flow acceptance by implication
no LLM actuator authority
```

---

### 2026-07-07 — Post-PV1 board/doc update built

Created updated board/doc copies:

```text
Mission Control updated
To-Do updated
Current Certified State updated
Platform v1 DoD updated
Full Vision Completion Map updated
Codex/Claude Handoff updated
manifest
```

Captured:

```text
PV1 final review-only state
Track 2 strengthened state
7 post-PV1 alternatives
autonomy fence
manual Omniverse/grey-city asset lane
```

Key outcome:

```text
The boards were moved from “PV1 in progress” to “PV1 closed, choose post-PV1 path.”
```

---

### 2026-07-07 — FLOWX-REVIEW-FLOW-ACCEPTANCE-D1 built

Built and passed:

```text
FLOWX-REVIEW-FLOW-ACCEPTANCE-D1
PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS
```

Promoted five lanes:

```text
NYC-F1X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F5X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
NYC-F6X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F3X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
CHI-F4X  ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS
```

Preserved:

```text
BARC-F7  CANDIDATE_ONLY_NOT_ACCEPTED / BLOCKED_BY_CITY_CORE
```

Created:

```text
FLOWX output
PV1 snapshot addendum R1
```

Verification:

```text
py_compile passed
runner passed
no-overclaim PASS
no-mutation PASS
PV1 D19-D22 frozen outputs unchanged
hashes PASS
```

Key outcome:

```text
The five NYC/Chicago review-route-ready lanes became accepted review flows with limitations,
without mutating the frozen PV1 snapshot.
```

---

### 2026-07-07 — PV1 Addendum R1 board/doc capture built

Created addendum capture set:

```text
Mission Control — addendum R1
To-Do — addendum R1
Current Certified State — addendum R1
Platform v1 DoD — addendum R1
Full Vision Completion Map — addendum R1
Codex/Claude Handoff — addendum R1
manifest
```

Captured state:

```text
PV1-D19/D20/D21/D22 remains frozen.
PV1-SNAPSHOT-ADDENDUM-R1 records the post-PV1 flow acceptance update.
Five lanes accepted for governed review use with limitations.
No operational/control claims created.
```

---

## Final state at the end of this thread

```text
PV1:
  CLOSED
  PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT

Post-PV1 addendum:
  CREATED
  five review flows accepted with limitations

Track 2:
  CLOSED
  strengthened
  policy-resolved for NYC/Chicago review flows
  not operational
  Barcelona still blocked by city-core
  Singapore LTA still blocked by auth

Omniverse:
  manual grey-city / hero-location asset lane continues externally
  future binding contract needed

Autonomy:
  deferred
  separate safety-critical future program
```

The strongest one-line summary:

```text
This thread took CityBrain from a strong but still-open PV1 build into a frozen
review-only Platform v1 snapshot, then added a post-PV1 policy addendum that
accepted five NYC/Chicago review flows with limitations while preserving all
no-control, no-dispatch, no-autonomy boundaries.
```
