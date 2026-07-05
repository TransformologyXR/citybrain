# ASK v1.1 App Fixture Vendoring R1

The ASK v1.1 web-control-room handoff now uses a committed local/demo fixture bundle by default:

```text
apps/web-control-room/src/askV11/fixtures/askV11AppHandoffFixtures.json
```

This vendors the eight R1 handoff scenarios into the app source tree so the panel no longer depends on ignored preflight output artifacts for fresh clone use.

The loader still has an optional legacy fallback for local development, but the committed app fixture path is the default.

Focused verification:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

Result: 18 tests passed.

No ASK runtime, G1-G8, packet schema, registry, CHECK, renderer, retrieval, future-flow runtime, citation URL fetch, official action workflow, or LLM behavior was changed.
