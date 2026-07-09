# Boundary policy

Seed R2 mobility-depth refresh is a **synthetic addendum**, not a new fact source.

## Allowed

- Use LTA/TfL depth data to shape synthetic mobility distributions.
- Generate local/replay-only mobility events.
- Generate WATCH/ASK/CHECK/BRIEF/SPATIAL fixtures.
- Reference Seed R1 entities and R2E donor records by ID.
- Preserve donor/source-class and limitations.

## Forbidden

- Treat LTA/TfL as Dubai operational truth.
- Treat any generated replay row as live monitoring.
- Issue or imply alerts, dispatch, routing, control, enforcement, or legal/certified findings.
- Store or package credentials, raw bulky data, rejected provider response bodies, or person-level data.
- Mutate Seed R1, R2, R2A, R2B, or R2E output roots.

## Required limitation refs

Generated records should include these or stricter equivalents:

- `LIM_R2_MOBILITY_DEPTH_REFRESH_NOT_DUBAI_TRUTH`
- `LIM_R2_MOBILITY_DEPTH_REFRESH_LOCAL_REPLAY_ONLY`
- `LIM_R2_MOBILITY_DEPTH_REFRESH_DONOR_CONTEXT_ONLY`
- `LIM_R2_MOBILITY_DEPTH_REFRESH_NO_ACTION_OR_CERTIFIED_CLAIM`
- `LIM_R2_MOBILITY_DEPTH_REFRESH_NO_HUMAN_PERSON_LEVEL_RECORDS`
