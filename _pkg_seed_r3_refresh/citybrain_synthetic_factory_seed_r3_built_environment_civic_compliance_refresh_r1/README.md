# MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1

Readable name: **Seed R3 Built Environment + Civic + Compliance Refresh**

This package turns the locked Seed R3 cross-city domain fuel preflight into a bounded Seed R3 synthetic-factory refresh.

It is a **generation package**, not a result package. It expects Codex to run it inside the CityBrain repo against:

- `outputs/MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT`
- existing Seed R1 / Seed R2 / Product Consumption outputs, read-only if present

## Why this exists

Seed R2 was intentionally mobility-heavy because R2E deepened LTA/TfL mobility feeds. The Seed R3 preflight confirmed large non-mobility fuel exists across Barcelona, NYC, Chicago, and London.

This task generates the next refresh using:

- property / planning
- built environment
- building compliance
- civic service / 311 / CRM
- environment / resilience
- data quality / maturity
- identity / graph evaluation

## Hard boundaries

- Cross-city material is donor/context only.
- Nothing becomes official Dubai truth.
- No raw bulky source data is packaged.
- No person-level or human-level records.
- No live monitoring.
- No dispatch, routing, control, enforcement, legal, or certified claim.
- Seed R1, Seed R2, Product Consumption, and the R3 preflight are consumed read-only.

## Codex command

```powershell
python scripts\run_main_citybrain_synthetic_factory_seed_r3_built_environment_civic_compliance_refresh_r1.py `
  --seed-r3-preflight outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-CROSS-CITY-DOMAIN-FUEL-PREFLIGHT `
  --product-consumption outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1 `
  --out outputs\MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1
```

Then:

```powershell
python -m pytest tests\test_main_citybrain_synthetic_factory_seed_r3_built_environment_civic_compliance_refresh_r1.py -q
```

Expected lock status:

```text
PASS_SYNTHETIC_FACTORY_SEED_R3_BUILT_ENVIRONMENT_CIVIC_COMPLIANCE_REFRESH_R1_WITH_LIMITATIONS
```
