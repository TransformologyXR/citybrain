# MAIN CODEX TASK — TRACK 2A OMNIVERSE ASSET BINDING R1

Task name:
`MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1`

Target final status:
`PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS`

Goal:
Promote the stricter Omniverse asset overlay smoke into a stable asset-binding registry and Kit/Composer handoff package.

Required prerequisite root:
- outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke

Required supporting roots, read-only:
- outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end
- outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end
- outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1
- outputs/main_track2b_d4x_city_episode_pack_end_to_end
- outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end
- outputs/main_track1_d4y_r6_incident_event_mode_end_to_end

Optional context roots:
- outputs/main_track2c_d4x_omniverse_viewport_bridge_r1
- outputs/main_citybrain_d6_control_room_reference_demo_r1
- outputs/main_citybrain_d6_control_room_reference_demo_r2_polish

Output root:
`outputs/main_track2a_d4x_omniverse_asset_binding_r1/`

Runner:
`scripts/run_main_track2a_d4x_omniverse_asset_binding_r1.py`

Required artifacts:
- README.md
- MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1.md
- MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json
- OMNI_ASSET_BINDING_PREREQUISITE_REPORT.json
- OMNI_ASSET_BINDING_SOURCE_MAP.json
- OMNI_ASSET_BINDING_REGISTRY.json
- OMNI_ASSET_BINDING_RECORDS.jsonl
- OMNI_REAL_ASSET_BINDINGS_BARC_NYC.json
- OMNI_DATA_FIRST_PLACEHOLDER_BINDINGS.json
- OMNI_USD_PRIM_BINDING_VALIDATION_REPORT.json
- OMNI_USDA_SIDECAR_BINDING_VALIDATION_REPORT.json
- OMNI_BINDING_CONFIDENCE_REPORT.json
- OMNI_BINDING_REVIEW_QUEUE.json
- OMNI_SOURCE_ID_BOUNDARY_BINDING_REPORT.json
- OMNI_EVIDENCE_LIMITATION_BINDING_MAP.json
- OMNI_KIT_COMPOSER_HANDOFF_PACKETS.json
- OMNI_STAGE_HANDOFFS_R1.json
- OMNI_CAMERA_BOOKMARKS_R1.json
- OMNI_OPERATOR_HANDOFF_NOTES.md
- OMNI_EXECUTIVE_HANDOFF_NOTES.md
- OMNI_EVENT_OVERLAY_DEPENDENCY_REGISTER.md
- OMNI_R7_RELATIONSHIP_OVERLAY_DEPENDENCY_REGISTER.md
- OMNI_NEGATIVE_TEST_REPORT.json
- OMNI_NO_ACTION_AUDIT_REPORT.json
- CLAIM_BOUNDARY_AUDIT.md
- NO_MUTATION_AUDIT.md
- SECRET_REDACTION_AUDIT.md
- hashes.sha256

Instructions:
1. Read all prerequisite roots read-only.
2. Load the overlay smoke selected assets, overlay packets, USDA sidecar marker prims, Kit handoffs, and visual evidence.
3. Create stable asset-binding records for at least 24 assets.
4. Preserve at least 16 real BARC/NYC bindings.
5. Preserve cross-city DATA_FIRST placeholders without pretending prim/source truth exists.
6. Validate USD prim/path references where available.
7. Validate sidecar marker prim references.
8. Add confidence and review_state to every binding.
9. Add source-ID boundary labels to every binding.
10. Map evidence and limitations for every binding.
11. Produce Kit/Composer handoff packets and stage/camera/bookmark records.
12. Produce operator and executive handoff notes.
13. Do not implement event overlays yet.
14. Do not implement R7 relationship overlays yet.
15. Record dependency registers for event overlay and R7 relationship overlay.
16. Run no-action, claim-boundary, no-mutation, secret, and hash audits.

Allowed statuses:
- PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS
- WAITING_ON_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE
- WAITING_ON_REAL_ASSET_BINDING_INPUTS
- FAIL_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1

Decision JSON must include:
- status
- task_name
- timestamp
- overlay_smoke_prerequisite_status
- binding_record_count
- real_barc_nyc_binding_count
- data_first_placeholder_count
- usd_prim_validation_status
- usd_sidecar_validation_status
- kit_composer_handoff_packet_count
- stage_handoff_count
- camera_bookmark_count
- evidence_limitation_binding_status
- source_id_boundary_status
- binding_confidence_status
- review_state_status
- event_overlay_dependency_status
- r7_relationship_overlay_dependency_status
- no_action_audit_status
- claim_boundary_status
- no_mutation_status
- secret_audit_status
- hash_validation_status
- limitations
- recommended_next_track2a_task
- recommended_future_d6_task

Recommended next Track 2A task:
`MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2`

Future dependency tasks:
- `MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-R2-STATE-MATERIALIZATION`
- `MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY`
- `MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION`
