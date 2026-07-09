# TASK PROMPT — CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3

## Goal

Prove that the bounded Chicago “city remembers” packet can support small, demo-safe similar-case queries without claiming citywide operational memory.

This is a query smoke task over the R2 reviewed matching output.

## Upstream context

Use the most recent Chicago R2 output, expected around:

- `outputs/chicago_similar_case_reviewed_matching_r2/`
- `outputs/chicago_similar_case_bounded_enrichment_r1/`
- D8 parallel/follow-on closeout outputs that reference Chicago

Known upstream facts:
- Chicago R1 landed 15 bounded sample rows from violations, 311, and Array of Things.
- Chicago R2 produced 15 reviewed cases and 45 bounded similar-case matches.
- This is a small bounded sample, not a citywide memory layer.

Discover actual roots from closeout/decision JSONs if path names differ.

## Required behavior

1. Load reviewed Chicago cases and bounded similar-case matches.
2. Build a small local query smoke harness over the sample.
3. Run a fixed set of demo-safe query fixtures.
4. Return cited case IDs/evidence refs for every answer.
5. Preserve no-data behavior when the sample cannot support a query.
6. Produce a small “city remembers” demo card set for D8 final demo integration.

## Required query fixtures

Run at least these query families:

1. Similar violation/case lookup  
   Example intent: “Show cases similar to this violation pattern.”

2. 311-context lookup  
   Example intent: “What nearby civic complaints look related in the bounded sample?”

3. Sensor/context lookup  
   Example intent: “What Array of Things context is attached to this reviewed sample?”

4. Cross-source memory lookup  
   Example intent: “Which reviewed cases connect violation, 311, and sensor-style context?”

5. No-data/abstain query  
   Example intent: “Find citywide trends across Chicago.”  
   Expected result: abstain/no-data because this is only a bounded 15-case sample.

## Required outputs

Output root:

`outputs/chicago_similar_case_demo_query_smoke_r3/`

Files:

- `CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json`
- `CHICAGO_DEMO_QUERY_FIXTURES.json`
- `CHICAGO_DEMO_QUERY_RESULTS.jsonl`
- `CHICAGO_CITY_REMEMBERS_DEMO_CARDS.jsonl`
- `CHICAGO_QUERY_ABSTAIN_CASES.jsonl`
- `CHICAGO_SIMILAR_CASE_DEMO_SUMMARY.md`
- `CHICAGO_SIMILAR_CASE_LIMITATIONS.md`
- `REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json`
- `JSON_PARSE_AUDIT.json`
- `SECRET_SCAN_AUDIT.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
- `HASH_MANIFEST.sha256`

## Decision JSON schema

Include at least:

```json
{
  "task": "CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3",
  "status": "PASS_WITH_LIMITATIONS",
  "upstream_roots": [],
  "reviewed_cases_loaded": 0,
  "similar_matches_loaded": 0,
  "query_fixtures_run": 0,
  "queries_answered": 0,
  "queries_abstained": 0,
  "demo_cards_created": 0,
  "citywide_memory_claim": false,
  "audits": {},
  "limitations": [],
  "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1"
}
```

## Acceptance criteria

Pass with limitations if:
- R2 reviewed cases and matches load cleanly.
- At least 5 query fixtures run.
- Results cite bounded case/evidence refs.
- Unsupported citywide/general queries abstain cleanly.
- Demo cards are generated for D8 final demo route.
- All audits pass.

Fail if:
- Upstream R2 outputs cannot be located.
- Query results invent evidence beyond the bounded sample.
- The task claims citywide Chicago memory or operational completeness.
- Prior certified outputs are mutated.

## Claim boundary

Allowed:
- “A bounded 15-case Chicago similar-case demo memory supports small query smoke tests.”
- “45 reviewed bounded matches are available for demo-safe retrieval if present upstream.”

Forbidden:
- “Chicago city memory is complete.”
- “The model can search all Chicago violations/311/sensor history.”
- “This is production civic analytics.”
