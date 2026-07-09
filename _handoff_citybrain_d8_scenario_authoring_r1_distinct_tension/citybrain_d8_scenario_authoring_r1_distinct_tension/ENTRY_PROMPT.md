# ENTRY PROMPT — D8 Scenario Authoring R1: Distinct Tension Queue

Run the scenario-authoring task in this pack.

Start with:

```text
MAIN-CITYBRAIN-D8-SCENARIO-AUTHORING-R1
```

Do not run UI redesign, capture/viewer validation, new data landing, or broad external source crawling from this pack.

Expected final output is a scenario-authoring package with a varied primary story queue:

```text
Wood Lane + up to 3 distinct-tension stories
```

Hard gate: no two counted primary stories may use the same `story_query_id@version`, unless one is explicitly marked `duplicate_shape_not_counted`.

If enough distinct-tension stories cannot be authored from existing evidence, return:

```text
PARTIAL_DISTINCT_PRIMARY_STORY_QUEUE_INSUFFICIENT
```

Do not pad the queue with same-shape London proximity stories.
