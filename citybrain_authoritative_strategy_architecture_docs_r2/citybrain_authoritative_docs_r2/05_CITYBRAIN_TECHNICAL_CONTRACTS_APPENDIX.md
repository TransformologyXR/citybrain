# CityBrain Technical Contracts Appendix
## Packets, Entities, Evidence, Authority, Agent Runs, and Data Requirements

**Status:** Authoritative technical appendix v2  
**Date:** 2026-07-05  
**Scope:** Provides implementation-facing contracts for CityBrain packets, source classes, entity specs, agent runs, authority envelopes, CHECK reports, and integration contracts.


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

## 1. Contract principles

All CityBrain components should follow these principles:

```text
1. Packets over prose.
2. Evidence before synthesis.
3. Source class always explicit.
4. Authority level always explicit.
5. Model outputs are proposals or renderings, never facts.
6. CHECK validates claimability before outputs become operator-facing.
7. Every packet has provenance and trace.
8. Every cross-surface interaction consumes the same packet chain.
9. A data source is not onboarded until it has a consumer: WATCH, ASK, CHECK, RECALL, DIFF, EVENT, SPATIAL, BRIEF, PLAN, SCHEDULE, or QUALITY.
```

---

## 2. Common packet fields

Every packet should include:

```json
{
  "packet_id": "...",
  "packet_type": "...",
  "schema_version": "...",
  "created_at": "ISO-8601",
  "valid_as_of": "ISO-8601 or date",
  "source_class": "official_record|source_record|sensor_inferred|model_inferred|derived|synthetic|replay|operator_input|approved_workflow_output",
  "authority_level": 0,
  "execution_state": "not_executed|proposal_only|approval_requested|approved|executed|monitored|failed|rolled_back",
  "provenance_refs": [],
  "evidence_refs": [],
  "check_report_ref": null,
  "trace_ref": "...",
  "limitations": [],
  "confidence": {
    "value": null,
    "class": "unknown|low|medium|high|verified",
    "basis": "..."
  }
}
```

---



## 2A. Canonical entity ID format — R2 restatement

Canonical IDs should remain city-scoped and source-aware unless a future contract deliberately changes them.

Recommended format:

```text
{entity_type}:{country}-{city}:{id_system}:{native_or_generated_id}
```

Examples:

```text
building:us-nyc:bin:3395389
parcel:uk-london:uprn:5006082
road_segment:es-barcelona:local_roadlink:...
camera:ae-dubai:dm_camera_registry:...
```

Rules:

```text
Do not replace native authoritative IDs with global vendor IDs.
Keep native jurisdiction IDs as aliases/source links.
Use generated IDs only when no stable native ID exists.
Every generated ID requires provenance, matching method, confidence, and review_state.
```

Open mappings:

```text
old resource entity type → map to resource, component, crew/resource, or keep as dedicated type before engineering.
old development entity type → re-add as Project/Development if development-tracking use cases return.
```

## 3. Source class taxonomy

| Source class | Meaning | Example | Can support factual claim? |
|---|---|---|---|
| `official_record` | Record from authoritative official source. | permit, parcel, transaction, roadwork feed | Yes, within scope and freshness. |
| `source_record` | Retained record from known source, not necessarily official authority. | CSV row, public dataset row | Yes, with source limitations. |
| `sensor_inferred` | Sensor output such as detection, telemetry, camera-derived signal. | bounding box, meter reading | Only as sensor observation. |
| `model_inferred` | Model-generated classification/description. | VSS caption, RT-VLM description | Candidate only; needs CHECK. |
| `derived` | Deterministically computed from retained sources. | diff, rank, distance join | Yes, if derivation cited. |
| `integrated_external` | Known external source integrated with cadence metadata. | live operator system feed | Yes, if cadence and ownership valid. |
| `synthetic` | Generated test/demo data. | synthetic scenario | Only as synthetic truth, never real-world claim. |
| `replay` | Replay snapshot/event. | replay road incident | Yes for replay context, not live claim. |
| `operator_input` | Human-entered note or state. | local review note | Yes as operator input, not source truth. |
| `approved_workflow_output` | Result of approved execution adapter. | work order status | Yes within workflow authority. |

---

## 4. Authority envelope

`AuthorityEnvelope` is required for every output that could influence action.

```json
{
  "authority_envelope_id": "auth:...",
  "authority_level": 0,
  "authority_state": "observe|explain|validate|propose|approval_requested|approved|executed|monitored|blocked",
  "allowed_next_steps": ["ask", "check", "brief", "hold", "abstain"],
  "forbidden_steps": ["dispatch", "enforce", "certify", "create_official_case"],
  "approval_required": true,
  "approval_ref": null,
  "adapter_ref": null,
  "execution_state": "not_executed",
  "policy_refs": [],
  "audit_refs": []
}
```

Authority principle:

```text
Current builds may be no-action/proposal-only.
Future builds may execute approved workflows.
No system action occurs without explicit, scoped, auditable authority.
```

---

## 5. EntityPacket

```json
{
  "packet_id": "entity:...",
  "packet_type": "EntityPacket",
  "canonical_entity_id": "...",
  "entity_type": "building|parcel|road_segment|service_point|camera|incident|...",
  "canonical_name": "...",
  "status": "active|inactive|candidate|retired|unknown",
  "review_state": "verified|inferred|candidate|pending_review|disputed|unresolved",
  "source_links": [],
  "aliases": [],
  "attributes": {},
  "attribute_assertions": [],
  "attribute_conflicts": [],
  "geometry_refs": [],
  "relationships_summary": [],
  "quality_score": null,
  "confidence": {},
  "provenance_refs": []
}
```

---

## 6. SourceRecordPacket

```json
{
  "packet_id": "source_record:...",
  "packet_type": "SourceRecordPacket",
  "source_system": "...",
  "source_record_id": "...",
  "source_class": "official_record|source_record|sensor_inferred|model_inferred|...",
  "record_time": "ISO-8601",
  "ingested_at": "ISO-8601",
  "valid_as_of": "ISO-8601",
  "fields": {},
  "normalized_fields": {},
  "linked_entities": [],
  "source_owner": "...",
  "freshness_policy": "...",
  "provenance_refs": []
}
```

---

## 7. GraphContextPacket

```json
{
  "packet_id": "graph_context:...",
  "packet_type": "GraphContextPacket",
  "subject_entity_id": "...",
  "relationships": [
    {
      "relationship_id": "...",
      "relationship_type": "contains|served_by|adjacent_to|managed_by|observed_by|occurred_on|candidate_affects",
      "from_entity_id": "...",
      "to_entity_id": "...",
      "confidence": {},
      "review_state": "verified|inferred|candidate|disputed",
      "source_refs": [],
      "valid_from": null,
      "valid_to": null
    }
  ],
  "paths": [],
  "candidate_affected_entities": [],
  "limitations": []
}
```

---

## 8. EventPacket

```json
{
  "packet_id": "event:...",
  "packet_type": "EventPacket",
  "event_type": "roadwork|incident|outage|complaint|camera_observation|inspection|violation|weather|alarm|workflow",
  "event_time": "ISO-8601",
  "processing_time": "ISO-8601",
  "status": "new|active|resolved|expired|quarantined|unresolved",
  "location": {},
  "source_record_refs": [],
  "candidate_entity_refs": [],
  "resolved_entity_refs": [],
  "resolution_state": "resolved|unresolved|candidate|quarantined",
  "event_payload": {},
  "limitations": [],
  "trace_ref": "..."
}
```

---

## 8A. Event Fabric v0 / v1 / v2 contracts

### Event Fabric v0

```json
{
  "event_id": "event:...",
  "event_type": "one_closed_enum_for_v0",
  "source_class": "replay|source_record|sensor_inferred|model_inferred",
  "valid_as_of": "ISO-8601",
  "subject_refs": [],
  "evidence_refs": [],
  "append_trace_ref": "trace:..."
}
```

Capabilities:

```text
append
validate basic schema
query by event_id / time / subject
trace
```

### Event Fabric v1

Adds:

```text
unresolved event ledger
invalid-event quarantine
basic materialized state
bounded replay
event-to-WATCH admission
```

### Event Fabric v2

Adds:

```text
multi-source event fabric
expiry / supersession
late and out-of-order handling
operational state API
Omniverse/WebRTC event overlays
runtime integration
```

## 9. CandidateObservation

Used by Metropolis/VSS/perception.

```json
{
  "packet_id": "candidate_observation:...",
  "packet_type": "CandidateObservation",
  "source_class": "sensor_inferred|model_inferred",
  "media_source_id": "camera_or_file_id",
  "model_id": "model@version",
  "observation_type": "vehicle_presence|ppe_candidate|restricted_zone_entry|camera_health|...",
  "timestamp": "ISO-8601",
  "frame_ref": "...",
  "clip_ref": "...",
  "location_ref": "...",
  "zone_ref": "...",
  "confidence": {
    "value": 0.0,
    "class": "low|medium|high",
    "threshold_ref": "..."
  },
  "tracking_refs": [],
  "candidate_entity_refs": [],
  "false_positive_classes": [],
  "human_review_required": true,
  "not_a_finding": true,
  "limitations": []
}
```

Hard rule:

```text
CandidateObservation never equals violation, finding, enforcement fact, identity, or dispatch signal.
```

---



## 9A. Perception / VSS privacy and candidate-observation policy

Perception has the highest overclaim risk in the platform. The following policy is mandatory for any Metropolis, DeepStream, RT-VLM, or VSS output.

```text
No identity / biometric inference.
No face recognition.
No person identification.
No legal violation label.
No enforcement language.
No dispatch/control/action claim.
CandidateObservation only until reviewed or corroborated under an authority policy.
```

Every perception output must carry:

```text
source_class = sensor_inferred or model_inferred or model_generated_narrative
model_id@version
confidence
frame_ref / clip_ref
timestamp
camera/source ID if available
zone/context if available
false_positive_class where known
privacy_boundary
retention_policy_ref if raw frames/clips are retained
```

VSS outputs are narrative review context. They may summarize what appears in media, but they are not source truth and cannot override DeepStream metadata, official records, or CHECK.

### R2 DeepStream runtime proof note

DeepStream runtime is ready for CityBrain R9 local/replay on `txr-4070` with DeepStreamSDK 8.0.0, CUDA runtime 12.9, TensorRT 10.9, cuDNN 9.8, NVIDIA Container Toolkit 1.19.1, Docker 29.6.0, and a passing sample file pipeline. This proof supports bounded local/replay candidate-observation work only; it does not authorize live CCTV production claims.

## 10. EvidencePacket

```json
{
  "packet_id": "evidence:...",
  "packet_type": "EvidencePacket",
  "subject_ref": "...",
  "source_records": [],
  "candidate_observations": [],
  "graph_context_refs": [],
  "diff_refs": [],
  "recall_refs": [],
  "derived_features": [],
  "knowns": [],
  "unknowns": [],
  "cannot_claim": [],
  "coverage_note": "...",
  "provenance_refs": [],
  "limitations": []
}
```

EvidencePacket is the truth object for downstream answer, brief, CHECK, plan, spatial, and workflow outputs.

---

## 11. CheckReport

```json
{
  "packet_id": "check:...",
  "packet_type": "CheckReport",
  "subject_ref": "...",
  "claim_refs": [],
  "result_class": "SUPPORTED|SUPPORTED_WITH_LIMITATIONS|INSUFFICIENT_EVIDENCE|CANNOT_CLAIM|CONTRADICTION_FOUND|STALE_OR_UNKNOWN_FRESHNESS|CANDIDATE_ONLY|MODEL_INFERRED_ONLY|ABSTAIN_RECOMMENDED|AUTHORITY_BLOCKED",
  "findings": [
    {
      "finding_type": "source_depth|freshness|contradiction|candidate_only|proximity_only|model_confidence|authority_boundary|coverage_gap",
      "text": "...",
      "evidence_refs": [],
      "severity": "info|caution|blocker",
      "recommended_downgrade": "none|cannot_claim|clarify|abstain|refuse"
    }
  ],
  "missing_evidence": [],
  "cannot_claim": [],
  "abstain_recommended": false,
  "authority_envelope_ref": "..."
}
```

---



## 11A. CHECK v0 / v1 contract split

CHECK must ship incrementally.

### CHECK v0 — minimum cross-mode unblocker

Required fields:

```json
{
  "check_version": "check_v0",
  "source_class_present": true,
  "freshness_present": true,
  "candidate_vs_verified": "candidate|verified|official_record|model_inferred|sensor_inferred|unknown",
  "basic_claimability": "supported|supported_with_limitations|cannot_claim|insufficient_evidence",
  "missing_evidence_reason": "string or null",
  "cannot_claim_reason": "string or null",
  "authority_level_checked": true
}
```

CHECK v0 is required before packets are surfaced in ASK app handoff, WATCH, BRIEF, Perception/VSS candidate review, and Spatial/Omniverse views.

### CHECK v1 — full evidence engine

Adds:

```text
claim-to-evidence mapping
source-depth scoring
contradiction detection
coverage analysis
multi-source conflict handling
abstain recommendation
detection-confidence / false-positive reasoning
source ownership / who-to-ask guidance
```

CHECK v1 should not block CHECK v0 adoption.

## 12. AnswerPacket

```json
{
  "packet_id": "answer:...",
  "packet_type": "AnswerPacket",
  "flow_run_id": "...",
  "question_raw": "...",
  "answer_family": "subject_answer|entity_360|source_record_360|patch_queue_query|ui_help|boundary_explanation|refusal|clarify",
  "subject_ref": "...",
  "lens": "support|uncertainty|claimability|summary|not_applicable",
  "knowns": [],
  "unknowns": [],
  "cannot_claim": [],
  "citations": [],
  "coverage_note": "...",
  "check_report_ref": "...",
  "rendered_response_ref": "..."
}
```

---

## 13. ClarificationPacket

```json
{
  "packet_id": "clarify:...",
  "packet_type": "ClarificationPacket",
  "flow_run_id": "...",
  "reason": "ambiguous_boundary|ambiguous_subject|multiple_candidates|missing_slot|low_confidence",
  "options": [
    {
      "option_id": "...",
      "label": "...",
      "route_preview": "...",
      "boundary_note": "..."
    }
  ],
  "selected_resolution": null,
  "trace_ref": "..."
}
```

---

## 14. BriefPacket

```json
{
  "packet_id": "brief:...",
  "packet_type": "BriefPacket",
  "subject_ref": "...",
  "brief_type": "operator|planner|executive|analyst|approval_packet",
  "summary": "...",
  "source_records": [],
  "knowns": [],
  "unknowns": [],
  "check_report_ref": "...",
  "cannot_claim": [],
  "review_options": [],
  "recall_refs": [],
  "diff_refs": [],
  "spatial_refs": [],
  "authority_envelope_ref": "...",
  "export_state": "local_only|approval_attachment|official_if_authorized"
}
```

---

## 15. RecallPacket

```json
{
  "packet_id": "recall:...",
  "packet_type": "RecallPacket",
  "subject_ref": "...",
  "similar_cases": [
    {
      "case_ref": "...",
      "match_strength": "weak|medium|strong",
      "match_reasons": [
        {
          "field": "...",
          "subject_value": "...",
          "case_value": "...",
          "evidence_refs": []
        }
      ],
      "what_was_considered": [],
      "what_was_not_claimed": []
    }
  ],
  "limitations": []
}
```

---

## 16. DiffPacket

```json
{
  "packet_id": "diff:...",
  "packet_type": "DiffPacket",
  "snapshot_a_ref": "...",
  "snapshot_b_ref": "...",
  "scope_ref": "...",
  "changes": [
    {
      "change_type": "new_record|changed_record|removed_record|expired_record|status_changed|link_added|link_removed|evidence_strengthened|evidence_weakened|stale_source",
      "record_ref": "...",
      "entity_ref": "...",
      "field_changes": [],
      "watch_candidate": false
    }
  ],
  "designed_change_test_ref": null,
  "limitations": []
}
```

---

## 17. PlanPacket and SchedulePacket

### PlanPacket

```json
{
  "packet_id": "plan:...",
  "packet_type": "PlanPacket",
  "subject_ref": "...",
  "goal": "...",
  "options": [
    {
      "option_id": "...",
      "option_type": "next_check|proposal|schedule|abstain|do_nothing|approved_workflow_candidate",
      "description": "...",
      "required_authority_level": 2,
      "evidence_refs": [],
      "check_report_ref": "...",
      "tradeoffs": [],
      "constraints": []
    }
  ],
  "do_nothing_baseline": {},
  "abstain_available": true,
  "authority_envelope_ref": "..."
}
```

### SchedulePacket

```json
{
  "packet_id": "schedule:...",
  "packet_type": "SchedulePacket",
  "plan_ref": "...",
  "tasks": [],
  "resources": [],
  "constraints": [],
  "time_windows": [],
  "candidate_sequences": [],
  "feasibility": "feasible|partial|infeasible|unknown",
  "optimizer_ref": null,
  "check_report_ref": "...",
  "authority_envelope_ref": "..."
}
```

---

## 18. SpatialSelectionPacket

```json
{
  "packet_id": "spatial_selection:...",
  "packet_type": "SpatialSelectionPacket",
  "surface": "web_map|omniverse_kit|webrtc_stream|gis",
  "selection_source": "user_pick|programmatic_focus|event_overlay|watch_item",
  "selected_prim_path": null,
  "selected_geometry_ref": null,
  "entity_ref": "...",
  "evidence_refs": [],
  "check_report_ref": "...",
  "review_state_ref": "...",
  "one_truth_parity_status": "pass|fail|not_checked",
  "limitations": []
}
```

---

## 19. Trace schema

```json
{
  "trace_id": "trace:...",
  "flow_run_id": "...",
  "agent_run_id": "...",
  "stages": [
    {
      "stage_id": "G1_boundary_screen@v1",
      "method": "deterministic|regex|llm_proposal|tool|hybrid",
      "input_hash": "...",
      "proposal": {},
      "decision": {},
      "tightened": false,
      "elapsed_ms": 0
    }
  ],
  "output_packet_refs": [],
  "authority_envelope_ref": "...",
  "audit_flags": []
}
```

---

## 20. Canonical entity spec format

Every canonical entity type should be defined with:

```text
1. Purpose
2. Minimum required fields
3. Optional fields
4. Primary matching keys
5. Core relationships
6. Data quality tests
7. Example source mappings
```

Initial entity families:

```text
Shared anchors:
  Community, Address, Site, Parcel, Building, Unit, Road Segment

Systems / operations:
  Facility, System, Component, Service Point, Instrument / Control Point

Events and workflow:
  Event, Incident, Work Order, Permit, Inspection, Violation, Transaction

Mobility and public realm:
  Route, Stop/Station, Terminal/Depot, Traffic Signal, Camera, Signage Asset, Bollard/Barrier

Party layer:
  Party, Person, Organization, Department, Role / Interest Assignment
```

---

## 21. Brain orchestrator flow contract

The ASK flow is the first implemented flow, but the General Flow Contract should support future flows.

### Gate contract

```text
gate_id@version
input_contract
output_contract
implementation_class: deterministic | model_proposal_gated | hybrid_cascade
monotonicity_class: none | tighten_only
trace_emission: required
golden_tests: positive + negative + adversarial if model-touched
```

### ASK v1 canonical flow

```text
G1 boundary_screen
G2 intent_and_concept_binding_resolver
G3 execution_contract_compiler
G4 argument_resolution
G5 template/tool_execute
G6 CHECK evidence_sufficiency_and_claimability
G7 answer_assemble
G8 render model_proposal_gated
sinks: clarify / refusal / gap
```

### Model roles

```text
LLM reader:
  intent/context/concept binding proposal

LLM writer:
  render prose from assembled evidence

LLM never:
  sources facts, computes metrics, retrieves data, grants authority, executes action
```

---

## 22. Concept-binding registry

Concepts in questions should bind to data reality:

```text
retained_field
  field exists in retained canonical/source model

derived_field
  computable from retained fields

integrated_from:<source>
  integrated external source with cadence/as-of

known_external_not_ingested
  known source exists but not retained

unknown_concept
  not recognized; clarify or gap
```

Example:

```text
Question: Can we tell drivers this charger is unavailable?
Concept: charger availability
Binding: known_external_not_ingested
Likely owner/source: charging network operator / transport authority
Answer: cannot claim current availability; asset record and nearby works are on file; no driver notification authority.
```

---

## 23. Integration contracts

## 23.1 ASK app handoff

The app should consume:

```text
FlowEnvelope
IntentPacket
ExecutionContract
EvidencePacket
CheckReport
AnswerPacket
ClarificationPacket
RenderedResponse
```

It should not change ASK logic.

## 23.2 Metropolis / VSS handoff

Metropolis/VSS should produce:

```text
CandidateObservation
EvidenceClip
CandidateEvent
DetectionCheckReport
```

It should not output:

```text
violation
finding
dispatch
enforcement
identity
legal/certified conclusion
```

## 23.3 Omniverse / Spatial handoff

Omniverse/WebRTC/Kit should consume:

```text
SpatialSelectionPacket
EntityPacket
EvidencePacket
CheckReport
ReviewState
AuthorityEnvelope
EventOverlay
```

It should not create a separate truth format.

## 23.4 Event fabric handoff

Event fabric should provide:

```text
append event
validate event
resolve or preserve unresolved
quarantine invalid
materialize state
query state
trace event lineage
```

## 23.5 Plan/Schedule handoff

Plan/Schedule outputs must include:

```text
option/schedule
constraints
tradeoffs
CheckReport
authority required
approval state
execution blocked unless approved
```

---



## 23.6 Flows / cartridges as packaging contract

Flows/cartridges survive as packaging over modes. A flow is not a separate intelligence mode. It is a named bundle of:

```json
{
  "flow_id": "flow:...",
  "cartridge_id": "cartridge:...",
  "city_or_domain_scope": "...",
  "modes_used": [],
  "required_entity_types": [],
  "required_sources": [],
  "watch_queries": [],
  "ask_templates": [],
  "check_rules": [],
  "brief_templates": [],
  "event_types": [],
  "spatial_layers": [],
  "authority_profile": "...",
  "demo_or_product_story": "..."
}
```

Examples:

```text
Flow 2 construction-compliance cascade = EVENT/INCIDENT + GRAPH + CHECK + BRIEF + PLAN over construction-compliance cartridge.
Flow 3 resilient city = EVENT/INCIDENT + GRAPH + SCHEDULE/OPTIMIZE + BRIEF over fire/road/air cartridge.
```

No flow/cartridge is considered current unless it cites its evidence artifacts and current maturity separately.

## 24. Validation requirements

Every new component must pass:

```text
schema validation
source-class validation
claim-boundary validation
authority-envelope validation
CHECK validation
no unsupported fact generation
trace completeness
negative tests
```

For perception:

```text
detection is candidate-only
model_id@version recorded
confidence recorded
frame/clip ref retained
no identity claim
no legal/finding claim
```

For spatial:

```text
same entity
same evidence
same CheckReport
same authority state
same limitations
no certified geometry claim unless proven
```

For agents:

```text
AgentRunEnvelope emitted
mission scoped
tools declared
CHECK run
authority level respected
trace emitted
```

---

## 25. Data acceptance rule

No dataset should be onboarded unless it has at least one consuming capability:

```text
WATCH query
ASK template
CHECK rule
RECALL matcher
DIFF comparison
EVENT resolver
SPATIAL overlay
BRIEF section
PLAN/SCHEDULE constraint
QUALITY diagnostic
SYNTHETIC validation test
```

This prevents record-gallery regressions.

---

## 26. Current priority contracts

The next contracts to harden should be:

```text
1. CHECK contract v1
2. EvidencePacket v2
3. SourceClass taxonomy v1
4. AuthorityEnvelope v1
5. ASK app handoff adapter
6. EventPacket + EventFabric v1
7. AgentRunEnvelope v1
8. SpatialSelectionPacket v1
9. CandidateObservation v1 integration
10. Plan/Schedule proposal packet v1
```

---

## 27. Final implementation principle

If a component cannot declare:

```text
input packet
output packet
source class
evidence refs
CHECK result
authority level
trace
```

then it is not ready to be a CityBrain component.

