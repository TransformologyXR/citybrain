# MAIN-CITYBRAIN-D8-SCENARIO-AUTHORING-R1

## Mission

Author a **varied primary story queue** for the CityBrain D8 brain surface from the already-mined story inventory.

Do **not** create another UI. Do **not** simply rank records. Do **not** author four London proximity stories that all use the same tension shape. The output should define which stories the future situation board will show and why each story adds a distinct kind of intelligence.

## Why this task exists

The deep story inventory correctly found that the top four primary story candidates are London mobility candidates. However, the first review revealed a product risk: they are all effectively the same story shape — TfL/works near rapid-EV access asset, distance-bounded proximity, review-only, no causality claim.

A situation board that contains four same-shape proximity stories will feel like a repeated query, not a city brain. The authoring task must produce breadth of **tension**, not just count of cards.

## Required inputs

Use existing workspace outputs only unless a referenced source pack already exists locally.

Look for:

```text
outputs/main_citybrain_d8_deep_story_inventory_milestone_freeze/
outputs/main_citybrain_d8_deep_story_inventory_closeout/
outputs/main_citybrain_d8_cross_city_story_role_portfolio_r8/
outputs/main_citybrain_d8_story_scenario_layer_milestone_freeze/
packages/fixtures/story_first_demo/story_scenario_layer.json
packages/fixtures/source_record_ui_integrated/source_record_ui_integrated_bundle.json
packages/fixtures/london_mobility_source_records/
packages/fixtures/chicago_similar_case_records/
packages/fixtures/helsinki_visual_entity_pick/
```

Also inspect older candidate roots when useful, but do not perform broad new data landing:

```text
outputs/f3_nyc_*
outputs/chi_*
outputs/barc_*
outputs/main_citybrain_d6_*
outputs/main_track2a_*
```

## Definitions

### Story
A story is not a row, a flow, or a card. A story must have:

```text
specific subject/place/object
specific tension
source-backed evidence
intelligence beat
review-only options or honest no-safe-option path
human-review stop
explicit limitations
```

### Story query
A story-query is the named logic pattern that makes a story intelligible.

Examples:

```text
story-query:proximity_works_to_access@v1
story-query:construction_to_response_cascade@v1
story-query:civic_signal_fusion_review@v1
story-query:visual_object_to_semantic_entity@v1
story-query:similar_case_precedent_memory@v1
story-query:perception_candidate_to_evidence@v1
```

You may create better names, but every primary story must declare exactly one primary `story_query_id` and may declare supporting `capability_query_ids`.

## Non-negotiable gate: distinct story-query rule

No two counted primary stories may share the same `story_query_id@version`.

If two candidates use the same story-query version, only the best one counts as a primary story. Mark the others:

```text
duplicate_shape_not_counted
```

They may be parked as future queue examples, but do not count them toward the varied primary queue.

## Target portfolio shape

Author:

```text
1 required baseline primary story: Wood Lane
up to 3 additional distinct-tension primary stories
woven trust moments
capability cutaways
parked backlog
```

Preferred queue target:

```text
1. London proximity/access review story — Wood Lane exemplar
2. NYC cascade or affected-asset response story, if source-backed enough
3. Chicago civic/sensor/fusion or precedent-memory primary, if source-backed enough
4. One additional distinct story shape from Barcelona, London, or Helsinki only if true tension exists
```

If fewer are supportable, be honest. A queue of two distinct real stories is better than four duplicate-shaped stories.

## Role assignments

Every candidate must be assigned one role:

```text
primary_story
trust_moment
capability_cutaway
parked_backlog
data_gap
duplicate_shape_not_counted
```

A capability cutaway should usually be woven into a primary story rather than shown as a standalone queue item. Examples:

```text
Helsinki visual pick → capability_cutaway, unless tied to a real tension.
Chicago precedent → capability_cutaway / trust_memory unless promoted by specific tension.
M07 refusal logs → trust_moment woven at story boundary.
M08 review stop → trust_moment woven at story boundary.
```

## Required output artifacts

Create a new output root:

```text
outputs/main_citybrain_d8_scenario_authoring_r1/
```

Required files:

```text
SCENARIO_AUTHORING_R1_DECISION.json
STORY_QUERY_REGISTRY.json
DISTINCT_PRIMARY_STORY_QUEUE.json
DUPLICATE_SHAPE_AUDIT.json
SCENARIO_LAYER_AUTHORING_PLAN.json
STORY_TO_SOURCE_EVIDENCE_MAP.json
WOVEN_CAPABILITY_CUTAWAY_PLAN.json
TRUST_MOMENT_WEAVING_PLAN.json
PARKED_STORY_BACKLOG.json
NO_OVERCLAIM_AUDIT.json
NO_ACTION_AUDIT.json
NO_MUTATION_AUDIT.json
SECRET_AUDIT.json
HASH_MANIFEST.json
LOCAL_OPEN_INDEX.md
README.md
```

Optional if you author concrete scenario JSONs:

```text
packages/fixtures/story_queue_scenario_layers/<story_id>.json
packages/fixtures/story_queue_scenario_layers/STORY_QUEUE_INDEX.json
```

## Required fields per authored primary story

Each row in `DISTINCT_PRIMARY_STORY_QUEUE.json` must include:

```json
{
  "story_id": "story:...",
  "title": "",
  "role": "primary_story",
  "city": "",
  "specific_subject": "",
  "tension": "",
  "story_query_id": "story-query:...@v1",
  "source_record_ids": [],
  "intelligence_beat": "",
  "review_options": [],
  "human_stop": "",
  "limitations": [],
  "overclaim_risks": [],
  "status": "authored|authoring_plan_only|partial",
  "why_distinct_from_wood_lane": ""
}
```

## Scenario authoring rules

Allowed:

```text
compose existing source records into a bounded review premise
state proximity / similarity / candidate status as review context
create options as review-only human considerations
include no-safe-option / abstain if evidence is insufficient
```

Forbidden:

```text
claim causality not proved by records
claim operational impact not in source records
claim EV availability/blockage/access impact unless source proves it
claim live monitoring/alerting
claim dispatch/routing/control/enforcement
claim official ticket/case creation
claim legal/certified finding
claim automated action
```

## Success statuses

Use one of:

```text
PASS_MAIN_CITYBRAIN_D8_SCENARIO_AUTHORING_R1_WITH_LIMITATIONS
PARTIAL_DISTINCT_PRIMARY_STORY_QUEUE_INSUFFICIENT
FAIL_MAIN_CITYBRAIN_D8_SCENARIO_AUTHORING_R1
```

PASS requires:

```text
Wood Lane retained as first authored story
at least 2 distinct primary story-query versions in queue or plan
duplicate-shape audit complete
no overclaim hits
source-evidence map complete for every authored primary story
UI build explicitly deferred
```

If you cannot author 3–4 distinct primary stories, do not fail automatically. Return partial or pass-with-limitations depending on whether the next scenario-authoring plan is concrete and source-backed.

## Explicit non-goals

```text
No UI redesign.
No capture/viewer validation.
No broad data landing.
No VSS/Metropolis build.
No production/public API/security/RBAC.
No mutation of existing certified outputs.
```
