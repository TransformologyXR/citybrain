# Donor Alignment Limitations

Status: `PASS_MAIN_CITYBRAIN_SIMULATION_DISTRIBUTION_CHECKED_FIXTURES_R1_WITH_LIMITATIONS`

## Mobility

- The mobility fixture is labeled `donor_distribution_aligned_fixture` because it has a named donor distribution id, source refs, sample counts, and a visible `category_distribution_l1_distance` metric.
- The donor profile uses LTA/TfL endpoint row estimates as event-type proxy buckets. This is useful for fixture audit, but it is not city calibration and not a forecast.
- The checked fixture has only four Seed R3 adapter rows, so representativeness remains limited.

## Permit Inspection Delay

- Permit-delay is parked as `not_distribution_checked_due_to_missing_comparable_donor_fields`.
- The local artifacts expose source refs and one NYC permit-to-complaint example, but not a comparable permit-created-to-inspection or inspection-completed donor distribution.
- The permit option engine remains review-only and is not distribution checked in this run.

## Boundaries

- no_ForecastPacket
- not_city_calibrated
- not_forecast
- not_operational_prediction
- no source-truth mutation
- no official workflow, case, dispatch, control, enforcement, legal, or certified finding
