# ASK v1.1 App Fixture Vendoring R1 Limitations

## Package Limitations

- The loader still supports the old ignored `outputs/ask_v11_app_handoff_preflight/` path as an optional local fallback. The committed app fixture path is the default and is sufficient for fresh clone use.
- This package did not run a browser or visual smoke test.
- This package did not stage, commit, push, or open a PR.

## Non-Scope Preserved

- No Kit handoff was implemented.
- No production ASK API was implemented.
- No live retrieval was added.
- No citation URL fetching was added.
- No official action, ticket, dispatch, enforcement, legal, certified, or autonomous workflow behavior was added.
- No LLM call was added.
- No WATCH, BRIEF, DIFF, INCIDENT, PLAN, or future-flow runtime was added.
