# ASK v1.1 App Handoff R1 Test Report

## Command

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

## Result

```text
Ran 16 tests in 0.046s
OK
```

## Coverage

The focused test suite verifies:

- fixture selector/loader exposes 8 local scenarios
- `cannot_claim` entries are visible
- no-data state is visible
- `not_executed` entries are visible
- CHECK details and claimability are visible
- citations and source refs are visible
- trace hops and packet refs are visible
- clarification prompt is visible
- boundary/action refusal is visible
- degraded render validation errors are visible
- proximity case does not display unsupported causal language as a known fact
- external context case does not display live availability as a known fact
- no action/ticket/dispatch/enforcement UI affordance appears in the ASK handoff panel
- adapter/view do not fetch citation URLs
- adapter/view/loader do not invoke ASK runtime or LLM
- fixture payloads have no `raw_query` key

## Scoped Runtime Diff Check

Command:

```powershell
git diff --name-only -- packages\ask_v11 packages\contracts scripts\emit_ask_v11_packet_schema.py scripts\run_ask_v11_sealed_eval.py scripts\run_ask_v11_real_corpus_eval_r1.py scripts\run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```

Result:

```text
<no output>
```

No ASK runtime, packet schema, registry, CHECK, renderer, or eval-runner file was modified.
