# CityBrain Outputs Day-by-Day Forensic Chronology

Generated: 2026-06-30
Workspace: `C:\Users\hazem\Documents\CityBrain`

## Method

This report is based on the generated output ledger under `outputs/`, not just top-level source timestamps. I inspected output roots by day, file counts, sizes, decision JSONs, harness reports, snapshot reports, and representative summaries. I deliberately avoided reading large raw datasets, parquet bodies, CSV bodies, shapefiles, and bulk generated block-level briefings except through their manifests/reports.

Important update since the first lineage report: after the earlier scan, the newest observed output root is now:

```text
outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2
PASS_MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_WITH_LIMITATIONS
local latest file time: 2026-06-30 00:34:00
```

That does not change the Git commit we made; it means the live workspace output ledger has advanced by one Track2C Omniverse bridge step.

## Update Since Last Report

Anchor: previous forensic report write time was 2026-06-30 00:44:45 local.

New output roots after that anchor:

| Latest local time | Output root | Files | Approx. size |
|---|---|---:|---:|
| 00:59:11 | `main_track1_d4y_r5_cer_seg_implementation_slice` | 57 | 1.20 MB |
| 01:03:48 | `main_track1_d4y_r5_first_domain_pack_selection_and_slice_preflight` | 21 | 0.04 MB |
| 01:03:49 | `main_track1_d4y_r5_building_asset_identity_domain_pack_preflight` | 23 | 0.06 MB |
| 01:03:50 | `main_track1_d4y_r5_second_domain_civic_service_context_preflight` | 23 | 0.05 MB |
| 01:12:46 | `main_track1_d4y_r4_domain_pack_runtime_slice_smoke_and_closeout` | 63 | 0.79 MB |
| 01:25:33 | `main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice` | 52 | 1.42 MB |
| 01:41:02 | `main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice_smoke` | 44 | 1.48 MB |
| 01:49:32 | `main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end` | 48 | 0.55 MB |
| 01:53:28 | `main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end` | 39 | 0.54 MB |
| 01:55:51 | `main_track2b_d4x_city_episode_pack_end_to_end` | 54 | 1.76 MB |
| 02:06:24 | `main_track2c_d4x_omniverse_kit_extension_camera_capture_r2` | 22 | 0.13 MB |
| 02:27:17 | `main_track1_d4y_r6_incident_event_mode_end_to_end` | 58 | 1.23 MB |
| 02:36:10 | `main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end` | 36 | 0.97 MB |
| 02:41:51 | `main_track2c_d4x_omniverse_viewport_bridge_r1` | 46 | 24.37 MB |
| 06:50:09 | `main_track2c_d4x_kit_first_city_episode_control_room_r1` | 55 | 1.96 MB |
| 07:02:25 | `main_citybrain_d4x_integrated_city_first_demo_and_road_to_running_handover` | 37 | 0.51 MB |
| 07:06:24 | `main_citybrain_d4x_live_source_crossing_preflight` | 8 | 0.02 MB |
| 07:08:21 | `main_track2a_d4x_omniverse_asset_overlay_demo_smoke` | 13 | 0.07 MB |
| 07:15:44 | `main_track1_d4y_r3_live_orchestrator_runtime_slice` | 103 | 0.50 MB |
| 07:18:10 | `main_citybrain_d5_local_served_runtime_preflight` | 13 | 0.06 MB |
| 07:23:43 | `main_citybrain_d4x_live_event_fabric_implementation_preflight` | 11 | 0.02 MB |
| 07:25:12 | `main_track2a_d4x_omniverse_asset_binding_r1` | 16 | 0.09 MB |
| 07:31:04 | `main_citybrain_d5_local_served_runtime_hardening_r1` | 16 | 0.11 MB |
| 07:54:49 | `main_track2a_d4x_omniverse_kit_interaction_smoke_r1` | 14 | 0.04 MB |
| 08:03:17 | `main_citybrain_d5_local_served_runtime_app_integration_preflight_r1` | 15 | 0.08 MB |
| 08:13:52 | `main_citybrain_d5_local_served_runtime_app_integration_slice_r1` | 15 | 0.14 MB |
| 08:15:10 | `main_track2a_d4x_omniverse_kit_selection_extension_preflight_r1` | 18 | 0.04 MB |
| 08:16:14 | `main_citybrain_d4x_live_event_fabric_minimal_local_slice` | 14 | 0.03 MB |
| 08:58:06 | `main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1` | 88 | 0.16 MB |

### What Changed

The workspace moved through four additional arcs after the previous report:

1. Track 1 D4Y advanced from R4 contract smoke into R5/R6 domain and incident/event proofs.
2. Track2A/Track2B/Track2C advanced the D4X product/Omniverse branch: city asset contracts, city episode packs, viewport/camera bridge work, object picking, USD-to-CER bridge, Kit interaction, asset binding, and control-room scene work.
3. A D5 local-served runtime branch appeared: local served runtime preflight, hardening, app-integration preflight/slice, and live event fabric minimal local slice.
4. A consolidated finishing handover closed a three-track reference spine: live event fabric, local served runtime, and Omniverse/Track2A.

### New Main Track 1 Findings

Decision files after the anchor report:

- `MAIN-TRACK1-D4Y-R5-CER-SEG-IMPLEMENTATION-SLICE`: `PASS_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_WITH_LIMITATIONS`; next was first domain-pack selection/preflight.
- `MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-SELECTION-AND-SLICE-PREFLIGHT`: `PASS_MAIN_TRACK1_D4Y_R5_FIRST_DOMAIN_PACK_SELECTION_AND_SLICE_PREFLIGHT_WITH_LIMITATIONS`.
- `MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-PREFLIGHT`: `PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_PREFLIGHT_WITH_LIMITATIONS`.
- `MAIN-TRACK1-D4Y-R5-SECOND-DOMAIN-CIVIC-SERVICE-CONTEXT-PREFLIGHT`: `PASS_MAIN_TRACK1_D4Y_R5_SECOND_DOMAIN_CIVIC_SERVICE_CONTEXT_PREFLIGHT_WITH_LIMITATIONS`.
- `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE-SMOKE-AND-CLOSEOUT`: `PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_AND_CLOSEOUT_WITH_LIMITATIONS`; next was building-asset identity runtime slice.
- `MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE`: `PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_WITH_LIMITATIONS`; next was runtime-slice smoke.
- `MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE-SMOKE`: `PASS_MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_SMOKE_WITH_LIMITATIONS`.
- `MAIN-TRACK1-D4Y-R5-DOMAIN-PACK-FIRST-TWO-DOMAIN-PROOF-END-TO-END`: `PASS_MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_WITH_LIMITATIONS`.
- `MAIN-TRACK1-D4Y-R6-INCIDENT-EVENT-MODE-END-TO-END`: `PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS`.

The R6 incident/event decision reported:

- 100 event inputs.
- 100 event-to-entity results.
- 100 incident context packets.
- 100 app handoff packets.
- 100 traces and 100 audit entries.
- 30 building-asset events.
- 50 civic-service events.
- 10 late/out-of-order events.
- 10 replay simulation events.
- 5 synthetic events.
- 5 limitation-only events.
- 16 current-state rows.
- negative tests, no-mutation, secret audit, and hash validation all passed.
- no external LLM truth path, no public API, no live agents, no dispatch/enforcement/routing/control/legal/certified output.

### New D5 / Local Served Runtime Findings

`outputs/main_citybrain_d4x_live_event_fabric_minimal_local_slice/MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_MINIMAL_LOCAL_SLICE_DECISION.json` reports `PASS_WITH_LIMITATIONS` and created a local/replay-only event-fabric slice:

- storage mode: append-only JSONL plus derived JSON.
- 3/3 append cases passed.
- 2/2 replay cases passed.
- 4/4 query cases passed.
- created event log, quarantine log, unresolved queue, and current state.
- created D5 handoff contract and Track2A handoff contract.
- resolved events: 1; unresolved events: 1; quarantined events: 1.
- explicitly not production live ingestion, not real-time streaming, not public service, and no heavy streaming infrastructure.

`outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1/MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_INTEGRATION_SLICE_R1_DECISION.json` reports `PASS_WITH_LIMITATIONS`:

- bind host: `127.0.0.1`; bind port: `62749`.
- packet types validated: 12/12.
- app response fixtures, session context, evidence trace, governed answer, health status, insight, limitation, Track2 handoff, and safe-next-look packets passed.
- no frontend implemented.
- event fabric and asset overlay availability were checked but not integrated.
- local-only boundary preserved.
- no production auth/RBAC, no public API, no autonomous action.

### New Track2A / Track2B / Track2C Findings

New decision statuses include:

- `MAIN-TRACK2A-D4X-CITY-ASSET-CONTRACT-AND-CROSSCITY-REGISTRY-END-TO-END`: `PASS_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_WITH_LIMITATIONS`.
- `MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-END-TO-END`: `PASS_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_WITH_LIMITATIONS`.
- `MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-BRIDGE-R1`: `PASS_MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1_WITH_LIMITATIONS`; next recommended task was viewport streaming R3.
- `MAIN-TRACK2C-D4X-OMNIVERSE-KIT-EXTENSION-CAMERA-CAPTURE-R2`: `PASS_MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_WITH_LIMITATIONS`; next recommended task remained viewport streaming R3.
- `MAIN-TRACK2A-D4X-OMNIVERSE-OBJECT-PICKING-AND-USD-TO-CER-BRIDGE-END-TO-END`: `PASS_MAIN_TRACK2A_D4X_OMNIVERSE_OBJECT_PICKING_AND_USD_TO_CER_BRIDGE_END_TO_END_WITH_LIMITATIONS`.
- `MAIN-TRACK2C-D4X-KIT-FIRST-CITY-EPISODE-CONTROL-ROOM-R1`: `PASS_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_WITH_LIMITATIONS`.
- Additional small `PASS_WITH_LIMITATIONS` roots cover source crossing preflight, Omniverse asset overlay demo smoke, asset binding R1, Kit interaction smoke, and Kit selection extension preflight.

### New Integrated Finishing Handover

The newest observed root is:

```text
outputs/main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1
MAIN-CITYBRAIN-D4X-D5-TRACK2A-INTEGRATED-FINISHING-HANDOVER-R1
status: PASS_WITH_LIMITATIONS
run_timestamp_utc: 2026-06-30T07:58:06Z
```

`MAIN_CITYBRAIN_D4X_D5_TRACK2A_INTEGRATED_FINISHING_HANDOVER_R1_DECISION.json` reports:

- 10 phases total.
- 10 phases passed with limitations.
- 0 failed phases.
- live event fabric closed.
- D5 served runtime closed.
- Omniverse Track2A closed.
- integrated reference spine closed.
- control room scene pack present.
- D5 event-state packets present.
- local event fabric present.
- Omniverse event overlay present.
- no-mutation audit passed.
- boundary audit passed.
- no production readiness claim, no production live claim, no public API claim, no real-time streaming claim, no citywide twin claim, no full mesh binding claim, no physical accuracy claim, no legal/enforcement claim, no autonomous action.

The handover recommendations after close are:

- `MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-PREFLIGHT`
- `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-PREFLIGHT`
- `MAIN-CITYBRAIN-D6-INCIDENT-MODE-PREFLIGHT`
- `MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-R1`
- `MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`

## Daily Output Volume

| Date | Output roots | Files | Approx. size | Largest roots |
|---|---:|---:|---:|---|
| 2026-06-24 | 2 | 18 | 0.26 MB | `a5_dob_district_enrichment`, `a4_mn_block_1060` |
| 2026-06-25 | 23 | 84,756 | 1,468.62 MB | `a5d7_citywide_briefings_v1`, `a3d2_footprints_geometry_v1`, `a4d2b_district_discovery` |
| 2026-06-26 | 41 | 1,272 | 150.99 MB | `lon_d10b_local_plan_semantic_certification`, `lon_d9d2_pld_api_uprn_recovery` |
| 2026-06-27 | 45 | 1,151 | 2,906.04 MB | `chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b`, `chi_d3_civic_event_ingest_flow_readiness` |
| 2026-06-28 | 121 | 5,076 | 10,101.16 MB | `chi_allflows_data_landing_r1`, `nyc_allflows_data_landing_r1`, `barc_allflows_data_landing_r1` |
| 2026-06-29 | 78 | 3,939 | 9,346.58 MB | `d4_3d_nyc_2025_full_i3s_export_r1`, `d4_3d_barc_lod2_full_i3s_export_r1` |
| 2026-06-30 | 5 | 194 | 1.01 MB | `main_track1_d4y_r4_live_runtime_hardening`, `main_track1_d4y_r4_cer_seg_shared_contracts_smoke` |

## 2026-06-24: First Runnable NYC Graph/Evidence Proof

Output roots:

- `outputs/a4_mn_block_1060`
- `outputs/a5_dob_district_enrichment`

What actually happened:

- `a4_mn_block_1060` proved the first A4 graph projection over Manhattan block 1060.
- `outputs/a4_mn_block_1060/harness_report_a4.json` reports `a4_status: PASS`.
- A2 preflight was green: `all_green`, `invariants_green`, and `flow2_green` were true.
- The district graph had 56 nodes and 4 projected edges.
- The hero traversal was explicitly checked:
  - DOB complaint `1366080`
  - resolves to building `BIN 1026676`
  - reaches parcel `BBL 1010607502`, label `425 WEST 50 STREET`
  - reaches permit `121912591`
  - reaches party `S&E BRIDGE & SCAFFOLD LLC`
- Confidence preservation was verified: 4 canonical edges, 4 projected edges, 4 preserved.
- Drift testing was present and passed by failing the expected bad cases.

The same day, `a5_dob_district_enrichment` added richer DOB context:

- `outputs/a5_dob_district_enrichment/a5_enrichment_summary.json` says this was a capped/deduped subset, not full NYC DOB history.
- It read raw rows from local harvested DOB subsets:
  - 205,000 DOB Permit Issuance rows
  - 355,000 DOB NOW filings rows
  - 355,000 DOB complaints rows
- It attached:
  - 17 DOB Permit Issuance rows
  - 44 DOB NOW filings rows
  - 51 complaints
- It produced:
  - 27 buildings
  - 51 events
  - 52 parcels
  - 111 parties
  - 61 permits
- The hero parcel `1010607502` had 1 issuance record, 12 DOB NOW job filings, and 9 DOB complaints.

Lineage meaning: June 24 is the shift from conceptual docs into a concrete graph/evidence proof: an official-record complaint-to-building-to-parcel-to-permit-to-party path, with confidence and drift gates.

## 2026-06-25: NYC Scales From Hero Block to Citywide Briefings; London Begins

Output roots completed or touched that day include:

- `a5d2_spark_portability_pack`
- `a5d1_operator_query`
- `a5d4_hardcode_audit`
- `a5d4a_evidence_grounding_core`
- `a5d4b_request_trace_core`
- `a5d5_nemo_oracle_wrapper`
- `a5d6_live_nemo_nim_replay`
- `nyc_harvest_prep_v0_2`
- `a4d2b_district_discovery`
- `a5d6b_narration_surface`
- `a4d3a_multidistrict_projection`
- `a4d3a_live_nemo_nim_briefings`
- `a8d1_face_layer_v1`
- `a4d3b_citywide_roundtrip_borough5`
- `a8d2_citywide_map_roundtrip_borough5`
- `a8d2_face_layer_citywide_v1`
- `a8d3_route_overlay_v1`
- `a5d7_citywide_briefings_v1`
- `a5d7b_live_citywide_query_v1`
- `a3d2_footprints_geometry_v1`
- `lon_d4_identity_backbone_ingest`
- `lon_d5_pld_planning_ingest`
- `lon_d5b_pld_uprn_backfill`

What actually happened:

- The NYC line moved from one hero block to multiple districts, then borough/citywide graph projections, then map and briefing surfaces.
- `outputs/a4d3b_citywide_roundtrip_borough5/gpu_projection_report.json` reports `status: PASS`, with cuDF parquet reads and cuGraph graph operations.
- For the inspected borough-5 roundtrip:
  - graph operations passed for components, degree, neighborhood sample, and SSSP.
  - peak GPU memory was 847 MB.
  - wall time for the graph operation report was 0.548 seconds.
- `outputs/a4d3b_citywide_roundtrip_borough5/graph_metrics.json` reports:
  - 572,201 nodes
  - 634,495 edges
  - 68,314 components
  - largest component size 386,978
  - degree rows 572,201
- This was still bounded by the explicit source caveat: counts reflect the current local harvested dataset, not complete NYC history unless marked full in inventory.

The most important artifact by file count is `a5d7_citywide_briefings_v1`:

- `outputs/a5d7_citywide_briefings_v1/A5D7_GENERATION_REPORT.json` reports:
  - task: `A5-D7 citywide block EvidenceBundles and governed briefings`
  - status: `PASS`
  - 27,997 active blocks
  - 0 grounding failures
  - 0 non-hero leaks
  - geometry caveat: block geometries are adapter bbox polygons from MapPLUTO representative points, not official tax-block boundaries.
- `outputs/a5d7_citywide_briefings_v1/A5D7_HARNESS_REPORT.json` reports API smoke passes for generated briefings, traces, and block APIs over sampled block IDs, all HTTP 200 in the inspected section.

Other actual output movements that day:

- `a3d2_footprints_geometry_v1` added real footprint geometry and map-cache artifacts.
- `a8d1`, `a8d2`, and `a8d3` created the face/map/route overlay line.
- Late-day London work began with `lon_d4_identity_backbone_ingest`, `lon_d5_pld_planning_ingest`, and `lon_d5b_pld_uprn_backfill`.

Lineage meaning: June 25 is the day CityBrain became a scalable NYC graph/narration/map system and began cloning the pattern into London.

## 2026-06-26: London Becomes the Second-City Core; NYC Flow 3 Starts

Output roots include the dense London chain:

- `lon_d5c_lids_confirmed_identity_bridge`
- `lon_d6_enforcement_building_control`
- `lon_d7_london_graph_query_smoke`
- `lon_d8_london_operator_query_contract`
- `lon_d9_datastore_context_download`
- `lon_d9a_london_raw_inventory`
- `lon_d9_sitemap_discovery`
- `lon_d9b_london_identity_build`
- `lon_d9c_pld_normalization_dedupe`
- `lon_d9d_pld_identity_alignment`
- `lon_d9e_london_serious_graph`
- `lon_d9f_london_serious_query_contract`
- `lon_d9d2_pld_api_uprn_recovery`
- `lon_d9z_d9d2_accepted_snapshot`
- `lon_d10_planning_context_enrichment`
- `lon_d10z_d10_accepted_snapshot`
- `lon_d6x_borough_enforcement_source_scout`
- `lon_d10b_local_plan_semantic_certification`
- `lon_d6b2_havering_enforcement_graph_integration`
- `lon_d11_london_face_layer`
- `lon_d12_london_nemo_nim_wrapper`
- `lon_d6b3_havering_enforcement_identity_recovery`
- `lon_d12b_live_spark_nim_replay`
- `lon_d13_london_composite_accepted_snapshot`
- `lon_d6b4_havering_enforcement_identity_expansion`
- `lon_d11c_live_london_face_route_fix`
- `lon_d11a_toid_generalised_location_recovery`
- `lon_d10ev_ev_charging_source_recovery`
- `lon_d13b_london_composite_d6b3_refresh`
- `lon_d13c_london_final_prehero_closure`
- `lon_hero_dual_scenario_package`

What actually happened:

- London’s output chain moved from planning/identity ingest to accepted pre-hero closure with live face and live NIM re-smokes.
- `outputs/lon_d13c_london_final_prehero_closure/LON_D13C_FINAL_PREHERO_SNAPSHOT.json` reports headline:
  - `London cartridge: GREEN_WITH_LIVE_FACE_LIVE_NIM_AND_DECLARED_LIMITATIONS`
- The accepted counts in that snapshot include:
  - D10 context: 186,180 context nodes and 232,101 context edges.
  - D10 PLD applications with context: 53,751.
  - D10B Local Plan candidate layers: 1,139.
  - D10B certified Local Plan layers: 444.
  - D10B manual-review Local Plan layers: 695.
  - D10B borough Local Plan coverage: 33/33.
  - D10EV official rapid-charging sites emitted: 156 across 31/33 boroughs.
  - D11A matched accepted TOIDs with generalized location: 40,803 of 40,804.
  - D11C live endpoints attempted/passed: 10/10.
  - D12B public tools exposed: 1.
  - D12B sample requests: 9/9.
  - D6B4 total certified enforcement identity edges: 190.
  - PLD applications considered: 58,867.
  - exact API matches: 57,796.
  - PLD-to-UPRN edges: 53,753.
- `outputs/lon_d13c_london_final_prehero_closure/LON_D13C_HARNESS_REPORT.json` reports all key gates as `PASS`, including:
  - 4070 sync
  - board update
  - count reconciliation
  - scope limitation preserved
  - live face preserved and re-smoked
  - live NIM preserved and re-smoked
  - no mutation
  - no overclaim
  - hashes

The limitations are central:

- planning context is not a legal planning determination.
- UPRN is not BBL.
- TOID is not BIN.
- PLD is not DOB.
- OS Open TOID gives generalized point locations, not exact building polygons.
- EV context is rapid-charging context only, not complete infrastructure or live availability.
- most enforcement identity links remain unjoined/candidate-only outside exact evidence.

NYC Flow 3 also starts late that day:

- `f3_nyc_d1_source_inventory_schema_mapping`
- `f3_nyc_d2_fdny_incident_response_slice_ingest`

Lineage meaning: June 26 is the London proof day. CityBrain stops being "NYC plus docs" and becomes a serious second-city cartridge with explicit cross-jurisdiction boundaries.

## 2026-06-27: NYC Flow 3, Chicago Flow 1/7, A9, and Synthetic Data Factory

Output roots include:

- NYC Flow 3 chain: `f3_nyc_d3_affected_asset_response_context` through `f3_nyc_d10full_full_source_propagation_refresh`.
- `sg_d1_singapore_source_api_scout`.
- `a9_g1_board_reconciliation`.
- `a9_wire_e2e_g1_snapshot`.
- Chicago chain: `chi_d1_chicago_deep_source_api_scout`, D2/D2B/D3/D3B/D4, F1/F7 dual flow, live Spark/NIM replay, face layer, hero package, accepted snapshot.
- PV1 SDF chain: `pv1_sdf_d1_factory_contract` through `pv1_sdf_synthetic_data_factory`.

What actually happened:

NYC Flow 3:

- `outputs/f3_nyc_d10full_full_source_propagation_refresh/F3_NYC_D10FULL_REFRESH_DECISION.json` says:
  - decision: `rerun_d3full_through_d9full`
  - status: `PASS`
  - reason: legacy D3-D9 were historical artifacts and not byte-equivalent to full-source D1/D2C inputs.
  - rerun stages: D3FULL, D4FULL, D5FULL, D6FULL, D8FULL, D9FULL.

Chicago:

- `outputs/chi_f1f7_d5_dual_flow_accepted_snapshot/CHI_F1F7_D5_ACCEPTED_SNAPSHOT_REPORT.json` reports:
  - accepted status: `GREEN_WITH_CAPPED_SOURCE_LIMITATIONS`
  - headline: Chicago Flow 1 + Flow 7 accepted as live-NIM green over an expanded, materially stronger, still source-limited public-data base.
- Counts include:
  - 5,901,178 311 events.
  - 1,069,048 traffic crashes.
  - 4,585,860 traffic tracker rows.
  - 21,712,174 D1B landed rows.
  - 11,279,337 F1 citywide total signal rows.
  - 16,529,370 D3B context edges.
  - 193 F7 fusion candidates, 8 selected candidates.
  - 3 D4 heroes.
- The accepted snapshot explicitly says:
  - Flow 1 is situational status evidence, not an operational recommendation.
  - Flow 7 is civic/sensor signal-fusion evidence, not policing, dispatch, enforcement, health, emergency, or public-safety recommendation.
  - Chicago is still source-limited: Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.
- Live routes were available under `/api/chicago/...` and `/chicago` route families.

PV1 Synthetic Data Factory:

- `outputs/pv1_sdf_synthetic_data_factory/PV1_SDF_UMBRELLA_HARNESS_REPORT.json` reports:
  - status: `PASS_SYNTHETIC_DATA_FACTORY_D1_D6`
  - all D1-D6 stage statuses: `PASS`
  - 12,000 synthetic events.
  - 24,000 synthetic observations.
  - 39,531 synthetic truth entities.
  - 11 source projections.
  - 13 dirty variants.
  - 8 replay packs.
  - 10 validation tests.
  - governance checks passed: claim labels, hashes, negative governance, no overclaim, no real ID reuse.

Lineage meaning: June 27 is the multi-flow replication day. NYC Flow 3 is corrected to full-source-derived outputs, Chicago becomes an accepted source-limited dual-flow cartridge, and synthetic replay/data factory scaffolding becomes available.

## 2026-06-28: Platform v1, Barcelona, Cross-City FlowX/XData, Track 1 D1, Track 2

This is the largest output-root day: 121 roots.

Major output families:

- PV1 infra and gates: `pv1_infra_*`, `pv1_d3_*` through `pv1_d22_*`.
- Cross-city and FlowX/XData: `xflow_*`, `xdata_*`, `flowx_*`, `d3_refresh_*`, `d4_batch_*`, `d5_batch_*`, `d6_promotion_*`.
- Barcelona: `barc_*`, `main_spine_barcelona_*`, `barc_allflows_*`, `barc_f1f6_flow_acceptance_closeout_r1`.
- All-flows landing/prep: NYC, Barcelona, Chicago, London.
- Main platform / Track 1 / Track 2: event fabric D1, perception candidate event D1, SUMO simulation D1, integrated smoke, flow consumption, oracle bridge, limitation cleanup, promotion gate runner, promotion batch.

What actually happened:

Platform v1:

- `outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate/PV1_D19D20D21D22_FINAL_DECISION.json` reports:
  - `final_status: PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT`
  - `review_context_only: true`
  - `operational_actions_enabled: false`
- This is the formal review-only PV1 freeze, not an operational/autonomous product.

Barcelona:

- `outputs/barc_f1f6_flow_acceptance_closeout_r1/BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1_DECISION.json` reports:
  - final task status: `PASS_BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1`
  - accepted flows: BARC-F1 through BARC-F6.
  - all phase gates passed: current state, source landing audit, flow bundle prep, per-flow acceptance, generated platform state apply, resolver smoke, EvidenceBundle smoke, platform regression, claim boundary, privacy/license, secret redaction, no-mutation, PV1-R3 addendum.
  - per-flow decisions:
    - BARC-F1: accepted review flow with limitations.
    - BARC-F2: accepted context flow with limitations.
    - BARC-F3: accepted context flow with limitations.
    - BARC-F4: accepted review flow with limitations.
    - BARC-F5: accepted context flow with limitations.
    - BARC-F6: accepted context flow with limitations.
- The limitations are substantive: context-only permits/licensing, not compliance; mobility/environment context, not traffic or transit control; port/logistics context, not operational sequencing; flood/climate context, not flood prediction or warning.

Track 2 promotion:

- `outputs/main_platform_flow_promotion_batch_r1/MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json` reports:
  - status: `PASS_MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1`
  - addendum: `PV1-SNAPSHOT-ADDENDUM-R4`
  - applied flows: `LON-F7X`, `CHI-F2X`, `CHI-F5X`.
  - no-op regression flows included NYC Flow2, NYC-F5X, LON-F3X/F4X/F5X, CHI-Flow7.
  - resolver/oracle recheck, claim-boundary audit, no-mutation audit, negative tests, and secret audit passed.

Track 1 D1:

- `main_platform_event_fabric_d1`, `main_perception_candidate_event_d1`, `main_sumo_simulation_d1`, and `main_track1_integrated_event_perception_sumo_smoke_r1` were all produced late in the day.
- The D1 lineage builds the first runtime/body layer: event fabric plus candidate perception events plus SUMO simulation events plus an integrated smoke.

Lineage meaning: June 28 is the official platformization day. PV1 becomes a review-only snapshot, Barcelona and FlowX/Track2 mature, and Track 1 runtime begins.

## 2026-06-29: D2, D3, D4, D4X, D4Y

This day has two very different halves: early runtime hardening and later product/orchestration expansion.

### Track 1 D2 and Track 2 R5

Output roots:

- `main_event_fabric_d2`
- `main_perception_d2`
- `main_sumo_d2`
- `main_track1_d2_integrated_runtime_smoke`
- `main_track1_d2_closeout_and_d3_roadmap`
- `chi_f2x_f5x_data_strengthening_r1`
- `chi_f2x_f5x_recheck_for_r5_addendum_r1`

What actually happened:

- `outputs/main_event_fabric_d2/MAIN_EVENT_FABRIC_D2_DECISION.json` reports:
  - final status: `PASS_MAIN_EVENT_FABRIC_D2`
  - 45 events appended.
  - 6 observations appended.
  - 45 duplicates detected in idempotency checks.
  - 4 cities represented.
  - 3 event families represented.
  - 7 real polling adapters passed.
  - checks passed for durable cursor store, idempotent append, current-state DuckDB, API smoke, replay from cursor, EvidenceBundle smoke, producer compatibility, claim boundary, no mutation, secret audit, hashes, and negative tests.
- Limitations: bounded runtime polling smoke only, no heavy streaming infrastructure or daemon, read-only review/context current state, no action taken.

- `outputs/main_track1_d2_closeout_and_d3_roadmap/MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json` reports:
  - final status: `PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS`
  - D2 gate statuses:
    - event fabric D2: pass.
    - perception D2: pass.
    - SUMO D2: pass with limitations.
    - integrated runtime smoke: pass with limitations.
  - 43 evidence entries indexed.
  - no D3 work started in that closeout.
  - recommended next task: `MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING`.
- The carried-forward SUMO limitation is important: official Barcelona traffic-section points are city-derived but not a complete routable street graph; connector edges are bounded routeability equivalents; simulation is context-only.

### Track 1 D3

Output roots:

- `main_event_fabric_d3_service_hardening`
- `main_event_fabric_d3_multicity_adapters`
- `main_perception_d3_deepstream_bridge_preflight_r1`
- `main_perception_d3_deepstream_bridge`
- `main_perception_d3_review_api`
- `main_sumo_d3_network_extraction_hardening_preflight_r1`
- `main_sumo_d3_network_extraction_hardening`
- `main_sumo_d3_scenario_catalog`
- `main_track1_d3_integrated_service_smoke`
- `main_track1_d3_closeout_and_d4_roadmap`

What actually happened:

- `outputs/main_event_fabric_d3_service_hardening/MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json` reports:
  - final status: `PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING`
  - events appended: 24.
  - duplicates: 10.
  - current-state rows: 24.
  - API requests: 10.
  - service architecture, API contract, cursor recovery, observability, retention policy, replay API hardening, error-budget health, deployment profile, service-mode smoke, producer compatibility, negative tests, claim boundary, no mutation, secret audit, hashes all passed.

- `outputs/main_track1_d3_closeout_and_d4_roadmap/MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_DECISION.json` reports:
  - status: `PASS_MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_WITH_LIMITATIONS`
  - capabilities indexed:
    - Event Fabric D3 service hardening.
    - MultiCity D3 adapters.
    - DeepStream runtime bridge.
    - Perception review API contract smoke.
    - SUMO D3 network hardening.
    - SUMO D3 scenario catalog.
    - Synthetic replay overlay.
    - Integrated D3 service smoke.
  - D4 roadmap was written but not yet started in that closeout.
  - recommended next task: `MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT`.

### Track 1 D4 and 3D/Omniverse

Output roots:

- `main_track1_d4_omniverse_3d_subset_preflight`
- `main_track1_d4_usd_city_subset_binding`
- `main_track1_d4_control_room_experience_preflight`
- `main_track1_d4_review_ui_workflow`
- `main_track1_d4_event_feed_and_overlay_ui`
- `main_track1_d4_evidence_trace_panel`
- `main_track1_d4_scenario_replay_panel`
- `main_track1_d4_briefing_panel`
- `main_track1_d4_trace_and_persona_experience`
- `main_track1_d4_control_room_integration_smoke`
- `main_track1_d4_integrated_demo_smoke`
- `main_track1_d4_closeout_and_d5_roadmap`
- `d4_3d_*` asset/export roots.

What actually happened:

- `outputs/main_track1_d4_closeout_and_d5_roadmap/MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json` reports:
  - status: `PASS_MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_WITH_LIMITATIONS`
  - D4 task count: 11.
  - D4 pass count: 11.
  - all 11 D4 tasks passed with limitations.
  - control-room capability count: 10.
  - D5 acceptance gate count: 14.
  - D5 roadmap task count: 9.
  - lifecycle coverage count: 7.
  - limitation count: 24.
  - negative tests: 18.
  - required artifacts: 34 across 6 folders, none missing.
  - recommended next main task: `MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
- It also records runtime topology:
  - Omniverse host: local RTX 5090 Windows laptop.
  - Kit version: `110.1.1+production.305458.6312fa25.gl`.
  - USD scene path under `outputs/main_track1_d4_usd_city_subset_binding/D4_BARCELONA_USD_SCENE.usda`.

Large 3D roots were also produced:

- `d4_3d_nyc_2025_full_i3s_export_r1`: about 7.1 GB.
- `d4_3d_barc_lod2_full_i3s_export_r1`: about 1.8 GB.

### D4X / D4Y Product and Intelligence Lines

Output roots:

- D4X/Track2C app/demo: control-room app shell, NYC live city app, app UX redesign, demo capture, rich content, dashboard integration, story compiler, episode pack, city-first episode app rebuild.
- D4Y intelligence/orchestration: city situation model, runtime binding, situation graph/query, evidence-bound QA/narrator, intelligence substrate closeout, R2 router/harness/agent/decision-support/orchestration, R3 runtime and insight engine, R3 closeout, R4 preflights.

What actually happened:

- `outputs/main_track1_d4y_r3_closeout/MAIN_TRACK1_D4Y_R3_CLOSEOUT_DECISION.json` reports:
  - status: `PASS_MAIN_TRACK1_D4Y_R3_CLOSEOUT_WITH_LIMITATIONS`.
  - 20 app handoff packets.
  - 87 audit log entries.
  - 21 capabilities.
  - insight engine status: `PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_WITH_LIMITATIONS`.
  - insight smoke status: `PASS_MAIN_TRACK1_D4Y_R3_INSIGHT_ENGINE_SLICE_SMOKE_WITH_LIMITATIONS`.
  - 34 insight packets.
  - 15 insight types covered, including recurring situation pattern, evidence gap, limitation cluster, source freshness gap, review backlog signal, simulation/observed contrast, synthetic boundary signal, cross-city coverage contrast, graph neighborhood density, no-action audit signal, app handoff candidate, and domain-pack future gap.
  - claim boundary enforced; no external LLM called; no command/action output created.

Lineage meaning: June 29 is the main acceleration day. Track 1 reaches D2, D3, D4, and deep D4Y layers; Track2C product work and 3D exports run in parallel.

## 2026-06-30: R4 Hardening and Omniverse Camera Bridge

Output roots:

- `main_track1_d4y_r4_semantic_graph_bridge_preflight`
- `main_track2c_d4x_omniverse_viewport_bridge_r1`
- `main_track1_d4y_r4_live_runtime_hardening`
- `main_track1_d4y_r4_cer_seg_shared_contracts_smoke`
- `main_track2c_d4x_omniverse_kit_extension_camera_capture_r2`

What actually happened:

Runtime hardening:

- `outputs/main_track1_d4y_r4_live_runtime_hardening/D4Y_R4_RUNTIME_HARDENING_EXECUTIVE_SUMMARY.md` says:
  - status: `PASS_MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_WITH_LIMITATIONS`
  - R4 hardened the completed R3 local runtime before domain-pack runtime complexity.
  - produced 68 regression requests.
  - produced 16 adapter hardening inventories.
  - produced full trace/audit coverage.
  - produced 24 stable app handoff fixtures.
  - boundary validation, no-action validation, and closeout audits passed.
- `D4Y_R4_RUNTIME_HARDENING_COVERAGE_REPORT.json` reports:
  - regression input count: 68.
  - trace count: 68.
  - audit count: 68.
  - tool adapter count: 16.
  - app handoff fixture count: 24.
  - negative test count: 16.
  - lifecycle coverage includes observed/context, candidate/review, simulated/context, synthetic/context, limitation-only, late/out-of-order, expired/superseded.
  - boundary validation and no-action audit passed.

CER/SEG shared contract smoke:

- `outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke/MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json` reports:
  - status: `PASS_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_WITH_LIMITATIONS`.
  - compatibility matrix: pass with limitations.
  - relationship ontology comparison: pass with limitations.
  - entity catalog comparison: pass.
  - DTO field comparison: pass.
  - temporal model comparison: pass.
  - review state comparison: pass.
  - sample request/response comparison: pass.
  - negative tests: 31.
  - shared fixtures: 12.
  - no production CER, no production SEG, no graph DB runtime, no traversal service, no app integration, no public API, no live agents, no external LLM.
  - recommended next Track 1 task: `MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE`.

Omniverse / Track2C:

- `outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2/MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json` reports:
  - status: `PASS_MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_WITH_LIMITATIONS`.
  - smoke status: `PASS`.
  - created a local Kit/Composer extension bridge with extension ID `txr.citybrain.viewport_bridge`.
  - command path uses `outputs/main_track2c_d4x_omniverse_viewport_bridge_r1/runtime/kit_command.json`.
  - wrapper scripts exist for BARC and NYC starts.
  - recommended next task: `MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-STREAMING-R3`.
  - limitations: local Kit/Composer extension only, file-queue bridge rather than WebRTC/browser streaming, camera/focus commands frame USD prim paths rather than semantic IDs directly, screenshots are review/context captures, no production deployment, no dispatch/enforcement/control/certified affected-building claim.

Lineage meaning: June 30 moves from D4Y preflight and hardening into bridge mechanics: stable local runtime contracts, CER/SEG alignment, and Omniverse viewport/camera capture extension work.

## Current Continuation State

The latest observed output-ledger tip is now the integrated D4X/D5/Track2A finishing handover:

```text
MAIN-CITYBRAIN-D4X-D5-TRACK2A-INTEGRATED-FINISHING-HANDOVER-R1
PASS_WITH_LIMITATIONS
latest root: outputs/main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1
run timestamp: 2026-06-30T07:58:06Z
recommended next: MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-PREFLIGHT
```

The latest main Track 1 D4Y/R-series tip observed after the prior report is:

```text
MAIN-TRACK1-D4Y-R6-INCIDENT-EVENT-MODE-END-TO-END
PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS
```

The latest local-served runtime / D5-adjacent slice observed is:

```text
MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-SLICE-R1
PASS_WITH_LIMITATIONS
next: MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-CONSUMPTION-SMOKE-R1
```

The latest live-event-fabric implementation slice observed is:

```text
MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-MINIMAL-LOCAL-SLICE
PASS_WITH_LIMITATIONS
next: MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-APP-INTEGRATION-SLICE-R1
```

The previous parked D5 security boundary remains relevant as an option, but it is no longer the only visible continuation path:

```text
MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
```

## Invariant Across All Days

The output files repeatedly preserve the same boundary:

- review/context only unless a gate explicitly says otherwise.
- candidate/review for perception-like observations.
- simulated/context for SUMO and synthetic data.
- no production readiness.
- no autonomous monitoring.
- no public-safety command.
- no dispatch/enforcement/routing/control.
- no legal finding.
- no certified affected building/asset.
- no certified impact or certified traffic model.
- no identity/biometric inference.

This is the through-line from A4/A5, through London and PV1, through D2/D3/D4, into D4Y and Track2C.

## Files Inspected Directly

Representative inspected files include:

- `outputs/a4_mn_block_1060/harness_report_a4.json`
- `outputs/a5_dob_district_enrichment/a5_enrichment_summary.json`
- `outputs/a4d3b_citywide_roundtrip_borough5/gpu_projection_report.json`
- `outputs/a4d3b_citywide_roundtrip_borough5/graph_metrics.json`
- `outputs/a5d7_citywide_briefings_v1/A5D7_GENERATION_REPORT.json`
- `outputs/a5d7_citywide_briefings_v1/A5D7_HARNESS_REPORT.json`
- `outputs/lon_d13c_london_final_prehero_closure/LON_D13C_FINAL_PREHERO_SNAPSHOT.json`
- `outputs/lon_d13c_london_final_prehero_closure/LON_D13C_HARNESS_REPORT.json`
- `outputs/f3_nyc_d10full_full_source_propagation_refresh/F3_NYC_D10FULL_REFRESH_DECISION.json`
- `outputs/chi_f1f7_d5_dual_flow_accepted_snapshot/CHI_F1F7_D5_ACCEPTED_SNAPSHOT_REPORT.json`
- `outputs/pv1_sdf_synthetic_data_factory/PV1_SDF_UMBRELLA_HARNESS_REPORT.json`
- `outputs/main_platform_flow_promotion_batch_r1/MAIN_PLATFORM_FLOW_PROMOTION_BATCH_R1_DECISION.json`
- `outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate/PV1_D19D20D21D22_FINAL_DECISION.json`
- `outputs/barc_f1f6_flow_acceptance_closeout_r1/BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1_DECISION.json`
- `outputs/main_event_fabric_d2/MAIN_EVENT_FABRIC_D2_DECISION.json`
- `outputs/main_track1_d2_closeout_and_d3_roadmap/MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json`
- `outputs/main_event_fabric_d3_service_hardening/MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json`
- `outputs/main_track1_d3_closeout_and_d4_roadmap/MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_DECISION.json`
- `outputs/main_track1_d4_closeout_and_d5_roadmap/MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json`
- `outputs/main_track1_d4y_r3_closeout/MAIN_TRACK1_D4Y_R3_CLOSEOUT_DECISION.json`
- `outputs/main_track1_d4y_r4_live_runtime_hardening/D4Y_R4_RUNTIME_HARDENING_EXECUTIVE_SUMMARY.md`
- `outputs/main_track1_d4y_r4_live_runtime_hardening/D4Y_R4_RUNTIME_HARDENING_COVERAGE_REPORT.json`
- `outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke/MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json`
- `outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2/MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json`
