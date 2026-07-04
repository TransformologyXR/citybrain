# ASK v1.1 App Handoff R1 Next Steps

## Recommended Next Package

```text
ASK-V11-APP-HANDOFF-R1-COMMIT-AND-PUSH
```

## Commit Scope Guidance

Include only:

- `apps/web-control-room/src/askV11/askV11FixtureLoader.js`
- `apps/web-control-room/src/askV11/askV11HandoffAdapter.js`
- `apps/web-control-room/src/views/askV11Handoff.js`
- `apps/web-control-room/src/runtimeBundle.js`
- `apps/web-control-room/src/renderApp.js`
- `apps/web-control-room/styles.css`
- `tests/test_ask_v11_app_handoff_r1.py`
- `docs/ask-v11/ask-v11-app-handoff-r1.md`
- `outputs/ask_v11_app_handoff_preflight/`
- `outputs/ask_v11_app_handoff_r1/`

Exclude unrelated dirty files and unrelated untracked app, handoff, script, input, corpus, tmp, and output files.

## Suggested Commit Subject

```text
Add ASK v1.1 local app handoff panel
```

## Later Work

- Add a Kit extension ASK handoff panel after web R1 is reviewed.
- Add a non-fixture local request path only after a separate package defines the app/API boundary.
- Add real retained contradiction UI coverage when a valid same-claim retained conflict pair exists.
