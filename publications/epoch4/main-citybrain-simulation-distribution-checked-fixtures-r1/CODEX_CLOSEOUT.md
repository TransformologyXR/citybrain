# Distribution-Checked Simulation Fixtures R1 Closeout

Status: `PASS_MAIN_CITYBRAIN_SIMULATION_DISTRIBUTION_CHECKED_FIXTURES_R1_WITH_LIMITATIONS`

Discovered donor distributions:
- `donor_distribution:mobility_access_interruption_v0:lta_tfl_event_type_proxy_counts:r1` using `outputs/MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2B-BASE-CITY-PLUS-KEYED-MOBILITY-MERGE/R2B_MOBILITY_DONOR_REPORT.json`.

Fixtures checked:
- `fixture:seed_r3:mobility_access_interruption_v0:event_type_mix:r1` with `category_distribution_l1_distance`.

Fixtures parked:
- `fixture:permit_inspection_delay:non_sumo_option_engine:r1` because comparable permit service-time donor fields were not found.

This remains a read-only donor-distribution fixture audit. It is not city calibrated, not a forecast, not an operational prediction, and it creates no ForecastPacket or action authority.
