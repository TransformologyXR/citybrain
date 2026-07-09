# Codex Handoff — MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT

## Purpose

The previous synthetic-factory refresh emphasized mobility because R2E was the fresh keyed depth pull. This task audits the broader existing CityBrain city corpora so Seed R3 can incorporate non-mobility domains instead of overfitting the factory to transport patterns.

## Inputs

Read these roots if present; fail closed and report missing roots rather than inventing counts:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1
outputs/barc_allflows_data_landing_r1
outputs/barc_allflows_consumption_prep_r1
outputs/nyc_allflows_data_landing_r1
outputs/nyc_flow_consumption_prep_r1
outputs/chi_allflows_data_landing_r1
outputs/chi_allflows_consumption_prep_r1
outputs/lon_allflows_data_landing_r1
outputs/lon_allflows_consumption_prep_r1
outputs/chi_f2x_f5x_data_strengthening_r1
outputs/chi_f2x_f5x_recheck_for_r5_addendum_r1
outputs/main_platform_flowpack_limitation_cleanup_r1
```

Also search `outputs/` for city prefixes if exact roots differ:

```text
barc*
nyc*
chi*
lon*
```

## Required audit domains

Classify source material into these fuel families:

```text
property_planning
built_environment
building_compliance
civic_service_311_crm
mobility_transport
environment_resilience
public_safety_incident
utilities_energy_water
population_demand
economy_logistics
data_quality_maturity
identity_graph_eval
```

## What to produce

Output root:

```text
outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT
```

Required files:

```text
SEED_R3_CROSS_CITY_DOMAIN_FUEL_PREFLIGHT_DECISION.json
CITY_CORPUS_DISCOVERY_LEDGER.csv
DOMAIN_FUEL_LEDGER.csv
DOMAIN_FUEL_SUMMARY.json
CROSS_CITY_DONOR_POLICY.json
SEED_R3_RECOMMENDED_REFRESH_PLAN.json
SEED_R3_PRODUCT_FIXTURE_REQUIREMENTS.json
SEED_R3_BOUNDARY_AND_SOURCE_CLASS_AUDIT.json
SEED_R3_NO_MUTATION_AUDIT.json
SEED_R3_SECRET_SCAN_REPORT.json
HASH_MANIFEST.json
CODEX_CLOSEOUT.md
```

## Acceptance criteria

- Consume all inputs read-only.
- Do not mutate Seed R1, Seed R2, Product Consumption R1, D5, D6, R2, R2A, R2B, or R2E outputs.
- Report actual discovered counts from files/manifests; do not copy assumed counts into PASS unless verified from local artifacts.
- Separate source truth, donor/context, synthetic/replay, derived, and model/sensor-inferred classes.
- Explicitly include Barcelona, NYC, Chicago, and London if roots exist.
- Mark missing city roots as `ROOT_MISSING_FAIL_CLOSED`, not failure of the task.
- Propose Seed R3 built-environment/civic/compliance refresh only after audit.
- Do not include human/person-level data. Strip or exclude personal names, emails, phone numbers, and direct individual records.
- Keep party/organization fields only as non-person entity context where already governed.
- No official Dubai truth claim.
- No live monitoring claim.
- No dispatch/control/enforcement/legal/certified claim.
- No raw bulky data packaged.
- No credentials written.

## Recommended Seed R3 after this preflight

```text
MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1
```

It should use verified domain fuel from this preflight to refresh WATCH, ASK, CHECK, BRIEF, SPATIAL, and Event replay fixtures across building/property/compliance/civic-service domains.
