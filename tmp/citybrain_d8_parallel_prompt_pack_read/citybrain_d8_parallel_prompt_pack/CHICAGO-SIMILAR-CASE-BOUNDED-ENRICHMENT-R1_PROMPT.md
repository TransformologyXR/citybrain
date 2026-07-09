# CHICAGO-SIMILAR-CASE-BOUNDED-ENRICHMENT-R1

## Mission

Create a small bounded Chicago “city remembers” enrichment packet using accessible sample data from violations, 311, and Array of Things, without making Chicago a main blocker or claiming full citywide ingestion.

This is a bounded enrichment/sample task.

## Starting context

Known current state:

- Chicago similar-case data is ready for bounded enrichment.
- Status is green for small samples.
- Violations, 311, and Array of Things are accessible enough for a bounded “city remembers” packet.
- This is not a main blocker.
- The purpose is to produce a small cross-source memory/context sample that can support similarity, recurrence, and evidence-bound narrative behavior.

## Inputs to inspect

Use available local sources or small API/sample pulls only if already supported by the repo’s source-access policy.

Prefer local data/output files if present:

- any existing Chicago Data Portal sample files
- any Chicago violations sample
- any 311 service request sample
- any Array of Things sample
- any prior CityBrain Chicago cartridge or civic/sensor fusion outputs
- data gap ledger/source access status for Chicago

If remote access is used, keep sample size small and record exact URLs/queries. Do not start large downloads.

## Required output root

Create:

`outputs/chicago_similar_case_bounded_enrichment_r1/`

## Required artifacts

1. `CHICAGO_SOURCE_ACCESS_SMOKE.json`
   - Classify each source:
     - violations
     - 311
     - Array of Things
   - Include:
     - access method
     - sample size
     - status
     - limitations
     - no-large-download confirmation

2. `CHICAGO_BOUNDED_SAMPLE_LEDGER.json`
   - Source rows collected or referenced.
   - Include:
     - source family
     - source record ID
     - timestamp/date
     - location fields
     - category/type
     - short description
     - evidence_ref
     - limitation_ref

3. `CHICAGO_CITY_REMEMBERS_PACKET.json`
   - Build a small memory-style packet:
     - place/context anchor
     - related prior violations
     - related 311 cases
     - related sensor/environment observations if available
     - temporal hints
     - similarity explanation
     - missing data
     - safe next-look suggestions

4. `CHICAGO_SIMILAR_CASE_ENTITY_CANDIDATES.jsonl`
   - Candidate canonical entities:
     - location/place
     - case/request
     - violation
     - sensor/observation
   - Include:
     - source refs
     - confidence
     - review_state
     - no canonical acceptance claim

5. `CHICAGO_SIMILAR_CASE_LIMITATIONS.md`
   - Explain limitations:
     - sample only
     - not citywide
     - no legal/compliance conclusion
     - no production ingestion
     - no real-time monitoring
     - no autonomous action
     - no full Flow 7 claim unless broader civic/sensor fusion is completed

6. `CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_DECISION.json`
   - Final decision:
     - task_id
     - status
     - sources_checked
     - sample_rows
     - city_remembers_packet_created
     - hard_errors
     - limitations
     - next_recommended_task

7. `LOCAL_OPEN_INDEX.md`
   - Links to all created artifacts.

8. Hash/audit outputs:
   - `HASH_MANIFEST.json`
   - `hashes.sha256`
   - `JSON_PARSE_AUDIT.json`
   - `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
   - `SECRET_AUDIT.json`
   - `CLAIM_BOUNDARY_AUDIT.json`

## Acceptance criteria

The task passes if:

- Chicago source access is classified for small samples.
- At least one bounded memory packet is created from violations/311/AoT if accessible.
- The sample remains explicitly bounded and not a main blocker.
- No large download is started.
- No citywide, production, live, legal, compliance, or autonomous-action claim is made.
- JSON artifacts parse clean.
- Hashes verify.

## Expected status

Use:

`PASS_CHICAGO_SIMILAR_CASE_BOUNDED_ENRICHMENT_R1_WITH_LIMITATIONS`

unless no source sample can be accessed or referenced.

## Forbidden claims

Do not claim:

- full Chicago cartridge complete
- Flow 7 complete
- citywide ingestion
- live sensor monitoring
- legal/compliance conclusion
- production readiness
- autonomous action or dispatch
