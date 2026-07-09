# 03 — Inputs

## Required read-only context roots

Use if present:

```text
outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh
outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration
outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight
outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity
outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end
outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2
outputs/main_track2a_d4x_omniverse_asset_binding_r1
outputs/main_track2b_d4x_city_episode_pack_end_to_end
outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1
outputs/main_track1_d4y_r6_incident_event_mode_end_to_end
outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end
```

## Optional mobility-specific roots

Use if present:

```text
outputs/*sumo*
outputs/*mobility*
outputs/*traffic*
outputs/*road*
outputs/*route*
outputs/*transport*
outputs/*replay*
outputs/*scenario*
```

Do not require these roots to exist if enough mobility-relevant context can be found in existing R6/Track2A/Track2B outputs.
