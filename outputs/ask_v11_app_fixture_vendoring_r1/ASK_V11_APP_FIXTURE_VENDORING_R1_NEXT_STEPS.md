# ASK v1.1 App Fixture Vendoring R1 Next Steps

## Recommended Next Package

`ASK-V11-APP-FIXTURE-VENDORING-R1-COMMIT-AND-PUSH`

Purpose:

- Stage only the vendored fixture package scope.
- Commit the app fixture vendoring changes.
- Push the branch.
- Avoid staging unrelated dirty worktree files.

Recommended commit subject:

```text
Vendor ASK v1.1 app handoff fixtures
```

## Candidate Scope For Commit

- `apps/web-control-room/src/askV11/fixtures/askV11AppHandoffFixtures.json`
- `apps/web-control-room/src/askV11/askV11FixtureLoader.js`
- `tests/test_ask_v11_app_handoff_r1.py`
- `outputs/ask_v11_app_fixture_vendoring_r1/`
- `docs/ask-v11/ask-v11-app-fixture-vendoring-r1.md`

## Guardrails For Commit Package

- Do not stage unrelated dirty files.
- Do not change ASK runtime.
- Do not rerun sealed eval writers.
- Do not add live retrieval, production API, citation URL fetch, official actions, or LLM calls.
- Do not start Kit handoff in the commit package.
