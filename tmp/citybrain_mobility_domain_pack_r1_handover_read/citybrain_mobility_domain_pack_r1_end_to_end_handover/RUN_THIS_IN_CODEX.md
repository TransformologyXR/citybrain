# MAIN CODEX TASK — MOBILITY DOMAIN PACK R1 END-TO-END

Task name:
MAIN-CITYBRAIN-D4X-MOBILITY-DOMAIN-PACK-R1-END-TO-END

Goal:
Build the first bounded Mobility Domain Pack R1 end-to-end. Do not stop at a standalone preflight unless core inputs are genuinely missing. Run preflight/inventory as Phase 0, then continue as far as available evidence/context allows.

Output root:
outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end/

Runner:
scripts/run_main_citybrain_d4x_mobility_domain_pack_r1_end_to_end.py

Required read-only context roots, use if present:
- outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh
- outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration
- outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight
- outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity
- outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end
- outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2
- outputs/main_track2a_d4x_omniverse_asset_binding_r1
- outputs/main_track2b_d4x_city_episode_pack_end_to_end
- outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1
- outputs/main_track1_d4y_r6_incident_event_mode_end_to_end
- outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end

Optional mobility-specific roots:
- outputs/*sumo*
- outputs/*mobility*
- outputs/*traffic*
- outputs/*road*
- outputs/*route*
- outputs/*transport*
- outputs/*replay*
- outputs/*scenario*

Phase 0 — input inventory:
Create MOBILITY_R1_PREREQUISITE_AND_INPUT_INVENTORY.json and MOBILITY_R1_SOURCE_MAP.json.

Classify available inputs:
- real mobility/road/route sources
- replay/simulation mobility context
- R6 mobility-like event context
- Track2A road/asset adjacency context
- Track2B mobility/replay episodes
- R7 edge/context opportunities
- DATA_FIRST only gaps

If no useful inputs exist, stop with WAITING_ON_MOBILITY_INPUT_ROOTS.

Phase 1 — domain scope:
Create MOBILITY_R1_DOMAIN_SCOPE.md.

Scope must include:
- bounded local domain pack only
- no certified traffic model
- no route/control/dispatch action
- no production mobility integration
- no live event ingestion
- no public API

Phase 2 — entity catalog:
Create MOBILITY_R1_ENTITY_CATALOG.json.

Minimum entity types:
- road_segment
- intersection / junction
- corridor
- route
- stop / station
- terminal / depot
- traffic_signal
- camera / detector / count point
- road_event
- traffic_incident
- closure / restriction
- mobility_observation
- mobility_scenario
- simulated_route
- affected_asset_context

Phase 3 — relationship catalog:
Create MOBILITY_R1_RELATIONSHIP_CATALOG.json.

Minimum relationship types:
- road_segment connects junction
- route serves stop/station
- incident occurred_on road_segment
- event affects corridor
- road_segment adjacent_to parcel/building
- stop/station serves community
- closure impacts route/corridor
- simulated_route traverses segment
- mobility_observation measured_at detector
- asset located_near road_segment

Phase 4 — event type catalog:
Create MOBILITY_R1_EVENT_TYPE_CATALOG.json.

Minimum event types:
- road_incident_context
- closure_context
- traffic_slowdown_context
- route_disruption_context
- station_or_stop_context
- simulated_route_context
- replay_mobility_context
- mobility_data_quality_limitation

Phase 5 — domain packet schema:
Create MOBILITY_R1_DOMAIN_PACKET_SCHEMA.json.

Fields must include:
- packet_id
- domain = mobility
- city_id
- entity_refs
- relationship_refs
- event_refs
- evidence_refs
- limitation_refs
- source_truth_level
- confidence
- review_state
- safe_next_looks
- forbidden_actions
- no_action_taken = true

Phase 6 — domain packets:
Create MOBILITY_R1_DOMAIN_PACKETS.json and .jsonl.

Target:
- at least 12 packets for full R1
- at least 6 DATA_FIRST packets for DATA_FIRST pass

Do not fabricate missing road/traffic state.

Phase 7 — episode candidates:
Create MOBILITY_R1_EPISODE_CANDIDATES.json.

Target:
- at least 8 candidates for full R1
- at least 4 for DATA_FIRST pass

Each candidate:
- title
- city
- mobility context
- asset/place context
- evidence refs
- limitation refs
- safe next-look
- no_action_taken = true

Phase 8 — R7 extension candidates:
Create MOBILITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json.

Target:
- at least 8 candidates for full R1
- at least 4 for DATA_FIRST pass

Do not promote to accepted R7 edges in this task. These are candidates for a later R7 widening task.

Phase 9 — CER/SEG bridge packets:
Create MOBILITY_R1_CER_SEG_BRIDGE_PACKETS.json.

Map mobility entities to candidate CER/SEG refs where available.
Missing links must produce limitations.

Phase 10 — event fabric bridge candidates:
Create MOBILITY_R1_EVENT_FABRIC_BRIDGE_CANDIDATES.json.

These are candidate mappings only. Do not implement event fabric.

Phase 11 — Track2A and D6 handoff candidates:
Create:
- MOBILITY_R1_TRACK2A_KIT_HANDOFF_CANDIDATES.json
- MOBILITY_R1_D6_PRODUCT_HANDOFF_CANDIDATES.json

These are candidate handoffs only, not product-surface integration.

Phase 12 — sample queries/responses:
Create:
- MOBILITY_R1_SAMPLE_QUERIES.json
- MOBILITY_R1_SAMPLE_RESPONSES.json

Every sample response must include evidence refs, limitation refs, and no_action_taken = true.

Phase 13 — limitation and DATA_FIRST registers:
Create:
- MOBILITY_R1_LIMITATION_REGISTER.md
- MOBILITY_R1_DATA_FIRST_REGISTER.md

Phase 14 — smoke and negative tests:
Smoke must prove:
- packet schema exists
- catalogs exist
- packets parse
- episode candidates parse
- R7 candidates parse
- Track2A/D6 candidates parse
- limitations present
- no_action_taken present
- audits pass

Negative tests:
- certified traffic model claim rejected
- route/control/dispatch claim rejected
- legal/certified claim rejected
- fabricated traffic state rejected
- simulation as observed truth rejected
- missing limitation rejected
- missing no_action rejected
- source mutation rejected
- public API claim rejected
- external LLM truth claim rejected

Phase 15 — audits:
Create:
- MOBILITY_R1_NO_ACTION_AUDIT.json
- CLAIM_BOUNDARY_AUDIT.md
- NO_MUTATION_AUDIT.md
- SECRET_REDACTION_AUDIT.md
- hashes.sha256

Allowed statuses:
- PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS
- PASS_MOBILITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS
- WAITING_ON_MOBILITY_INPUT_ROOTS
- FAIL_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END

Expected:
PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS
or, if source coverage is thin:
PASS_MOBILITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS

Final decision JSON must include:
- status
- task_name
- timestamp
- input_inventory_status
- source_map_status
- entity_type_count
- relationship_type_count
- event_type_count
- domain_packet_count
- episode_candidate_count
- r7_edge_extension_candidate_count
- cer_seg_bridge_packet_count
- event_fabric_bridge_candidate_count
- track2a_kit_handoff_candidate_count
- d6_product_handoff_candidate_count
- sample_query_count
- sample_response_count
- data_first_status
- limitation_status
- no_action_audit_status
- claim_boundary_status
- no_mutation_status
- secret_audit_status
- hash_validation_status
- limitations
- recommended_next_task

Recommended next task if full R1 passes:
MAIN-CITYBRAIN-D4X-MOBILITY-R7-EDGE-EXTENSION-R1

Recommended next task if DATA_FIRST:
MAIN-CITYBRAIN-D4X-DOMAIN-AVAILABILITY-COUNTS-SCOUT
