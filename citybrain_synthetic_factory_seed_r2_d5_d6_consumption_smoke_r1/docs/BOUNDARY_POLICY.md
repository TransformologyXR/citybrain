# Boundary Policy

This package proves local consumption of already-generated synthetic/replay product fixtures.

Allowed:
- Count and parse Product Consumption R1 fixtures.
- Generate synthetic/replay D5 response fixtures.
- Validate and package a D6 local index.
- Preserve limitation/source-class flags.
- Generate local-only smoke artifacts.

Forbidden:
- Mutating Seed R1, Seed R2, Product Consumption R1, R2/R2A/R2B/R2E, or raw roots.
- Writing credentials.
- Packaging raw provider payloads.
- Treating LTA/TfL/OPSD donor/context feeds as Dubai facts.
- Treating Overture/OSM/Microsoft seed geometry as official Dubai identity.
- Claiming live monitoring, alerts, dispatch, control, enforcement, legal findings, certified findings, or official tickets.


Explicit boundary phrases for tests and reviewers:
- No raw provider payloads.
- No credentials.
- Not official Dubai identity.
