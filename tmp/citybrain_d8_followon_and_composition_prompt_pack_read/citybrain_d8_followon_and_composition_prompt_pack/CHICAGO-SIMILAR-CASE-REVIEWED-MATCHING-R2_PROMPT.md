# TASK: CHICAGO-SIMILAR-CASE-REVIEWED-MATCHING-R2

## Purpose
Upgrade the Chicago bounded “city remembers” sample from raw enrichment rows into a reviewed similar-case matching packet with explicit matching rules, candidate explanations, and limitation labels.

## Context
D8 parallel prompt pack produced a bounded Chicago sample:
- 15 sample rows landed
- sources include violations, 311, and Array of Things
- purpose is a bounded similar-case memory packet, not a main blocker and not a citywide Chicago build

This R2 task should make the sample useful for retrieval/briefing by classifying and explaining similar-case matches without overclaiming causal inference or production memory.

## Inputs
Use existing outputs if present:
- outputs/chicago_similar_case_bounded_enrichment_r1/
- CITYBRAIN_D8_PARALLEL_PROMPT_PACK_CLOSEOUT.json
- Chicago R1 source ledger / sample JSON / sample CSV / memory packet artifacts

## Hard boundaries
- Do not download large Chicago datasets.
- Do not claim complete Chicago coverage.
- Do not claim causal findings.
- Do not claim predictive enforcement, legal decisions, certified conclusions, production memory, or live monitoring.
- Do not mutate prior certified outputs.

## Required work

### 1. Review R1 sample rows
Load the bounded 15-row sample. For each row classify:
- source family: violation / 311 / Array of Things / other
- spatial anchor availability
- temporal anchor availability
- issue/event type
- candidate entity anchor: building / parcel / block / street / community / sensor / unknown
- evidence completeness
- safe-to-use-in-memory status

### 2. Define similar-case matching rules
Create a transparent matching rule set using only bounded, auditable features:
- event/issue type similarity
- spatial proximity or same named area if available
- temporal proximity/window
- source-family compatibility
- repeated condition/type
- sensor/environment context, if applicable

Do not use black-box semantic similarity as the only explanation. If embeddings are used, they must be secondary and labelled.

### 3. Build reviewed match candidates
For each eligible sample row, generate up to 3 similar-case candidates from within the bounded sample only.

Each match must include:
- source_case_id
- candidate_case_id
- match_score
- score_breakdown
- matched_features
- unmatched_features
- explanation
- confidence
- review_state
- limitations

### 4. Create “city remembers” packet v2
Produce a compact retrieval packet suitable for later demo use:
- case summary
- why it is remembered
- similar cases
- evidence refs
- confidence/limitations
- safe answer snippets
- forbidden claims

### 5. Demo query fixtures
Create 5–8 bounded demo query fixtures that this packet can answer safely, such as:
- “Have we seen a similar complaint pattern nearby?”
- “Are there prior cases of this type in the sample?”
- “What context should an analyst check next?”

Every fixture must have expected safe-answer behavior and limitation language.

## Required outputs
Create output root:
`outputs/chicago_similar_case_reviewed_matching_r2/`

Required files:
- `CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_DECISION.json`
- `CHICAGO_REVIEWED_CASES.jsonl`
- `CHICAGO_SIMILAR_CASE_MATCHES.jsonl`
- `CHICAGO_SIMILAR_CASE_MATCHING_RULES.json`
- `CHICAGO_CITY_REMEMBERS_PACKET_V2.json`
- `CHICAGO_DEMO_QUERY_FIXTURES.json`
- `CHICAGO_LIMITATIONS_AND_FORBIDDEN_CLAIMS.md`
- `CHICAGO_R2_SCOREBOARD.json`
- `HASH_MANIFEST.sha256`
- `RUN_AUDIT.json`

## Audits
Must run and record:
- JSON/JSONL parse audit
- bounded-sample-only audit
- no prior output mutation audit
- secret scan
- claim boundary audit
- no causality/prediction/legal/production/live/autonomous claim audit
- hash manifest verification

## Acceptance criteria
Pass with limitations if:
- all R1 rows are reviewed or explicitly excluded
- similar-case rules are transparent
- reviewed matches are bounded to the sample
- city-remembers packet v2 exists
- demo fixtures exist with safe expected behavior
- all audits pass

Expected final status:
`PASS_CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_WITH_LIMITATIONS`
