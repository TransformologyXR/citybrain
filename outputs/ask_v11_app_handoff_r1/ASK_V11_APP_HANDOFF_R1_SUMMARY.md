# ASK v1.1 App Handoff R1 Summary

## Decision

`PASS_ASK_V11_APP_HANDOFF_R1_WITH_LIMITATIONS`

## What Changed

R1 adds local/demo web cockpit consumption of ASK v1.1 app handoff fixtures.

The web control room now optionally loads:

```text
outputs/ask_v11_app_handoff_preflight/ASK_V11_APP_HANDOFF_FIXTURES.json
```

When present, the cockpit renders an ASK v1.1 handoff panel with the 8 preflight scenarios:

- `board_meta_safe_help`
- `entity_profile_supported`
- `external_context_cannot_claim`
- `no_data_answer`
- `proximity_not_causality`
- `clarification_required`
- `boundary_action_refusal`
- `render_validator_degraded`

## App Files Added or Updated

- `apps/web-control-room/src/askV11/askV11FixtureLoader.js`
- `apps/web-control-room/src/askV11/askV11HandoffAdapter.js`
- `apps/web-control-room/src/views/askV11Handoff.js`
- `apps/web-control-room/src/runtimeBundle.js`
- `apps/web-control-room/src/renderApp.js`
- `apps/web-control-room/styles.css`
- `tests/test_ask_v11_app_handoff_r1.py`
- `docs/ask-v11/ask-v11-app-handoff-r1.md`

## UI State Covered

- answer panel
- knowns and unknowns
- cannot-claim warnings
- coverage notes
- citations and source refs
- CHECK details and claimability
- downgrades, abstains, contradictions, and staleness when present
- safe next looks
- not-executed entries
- clarification prompts
- boundary/refusal routes
- degraded render validation errors
- trace hops and packet refs

## Runtime Boundary

No ASK runtime, G1-G8, packet schema, concept registry, template registry, CHECK rule, renderer rule, retrieval behavior, eval artifact writer, future-flow runtime, production API, live retrieval, citation URL fetch, LLM call, official action, ticket, dispatch, enforcement, legal finding, or certified finding was added.

## Test Result

```text
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

Result:

```text
Ran 16 tests
OK
```

## Limitations

- This is web-control-room local/demo handoff only.
- The Kit extension is inventoried but not wired in R1.
- The fixture file lives under ignored `outputs/`; later source-control packaging must force-add intended outputs if needed.
- The existing `apps/` tree is untracked in this workspace, so the commit package must include only the intended R1 app files.
