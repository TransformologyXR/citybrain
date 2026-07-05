# ASK v1.1 App Fixture Vendoring R1

Package: `ASK-V11-APP-FIXTURE-VENDORING-R1`

Final decision: `PASS_ASK_V11_APP_FIXTURE_VENDORING_R1`

## What Changed

The eight ASK v1.1 app handoff fixtures are now vendored under the web-control-room app:

```text
apps/web-control-room/src/askV11/fixtures/askV11AppHandoffFixtures.json
```

The fixture loader now defaults to the committed app fixture path:

```text
/apps/web-control-room/src/askV11/fixtures/askV11AppHandoffFixtures.json
```

The previous ignored output fixture path remains only as an optional legacy fallback:

```text
/outputs/ask_v11_app_handoff_preflight/ASK_V11_APP_HANDOFF_FIXTURES.json
```

This makes the local/demo ASK panel reproducible from a fresh clone without relying on local preflight outputs.

The vendored app fixture preserves the eight scenario payloads and adds app-local vendoring metadata:

```text
package: ASK-V11-APP-FIXTURE-VENDORING-R1
fixture_kind: app_handoff_vendored_fixture
vendored_from: outputs/ask_v11_app_handoff_preflight/ASK_V11_APP_HANDOFF_FIXTURES.json
```

## Vendored Scenarios

- `board_meta_safe_help`
- `entity_profile_supported`
- `external_context_cannot_claim`
- `no_data_answer`
- `proximity_not_causality`
- `clarification_required`
- `boundary_action_refusal`
- `render_validator_degraded`

## Verification

Focused app handoff test:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

Result: `PASS`, 18 tests.

Fixture source check:

```text
source fixture hash: 905BF77855AAB1CD5C27B359F5FF6FB775082AD23070265CF53A73FC81E1123D
committed fixture hash: F0D8340E45F9F0D8F81EB9209579EC0B923200C487A2E11C521B7B7511E48510
semantic delta: vendoring metadata only
```

ASK runtime scoped diff:

```powershell
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```

Result: empty diff.

## Preserved Boundaries

- No ASK runtime behavior changed.
- No G1-G8 behavior changed.
- No packet schema changed.
- No registry, CHECK, or render rule changed.
- No future-flow runtime added.
- No live or production retrieval added.
- No citation URL fetch added.
- No official action, ticket, dispatch, or enforcement behavior added.
- No LLM call added.
- No unrelated dirty files were touched.
