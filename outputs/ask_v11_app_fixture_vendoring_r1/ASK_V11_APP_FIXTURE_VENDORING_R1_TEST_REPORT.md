# ASK v1.1 App Fixture Vendoring R1 Test Report

## Commands Run

```powershell
git branch --show-current
git log -4 --oneline
git status --short --branch
```

Observed branch:

```text
ask-v11-canonical-implementation-sprint
```

Observed latest commit:

```text
840f784 Add R7 local replay perception-to-review workflow
```

Focused test:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

Observed result:

```text
Ran 18 tests
OK
```

ASK runtime drift check:

```powershell
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```

Observed result:

```text
empty diff
```

Fixture source comparison:

```powershell
node fixture semantic comparison
```

Observed result:

```text
semantic delta is limited to vendoring metadata: package, fixture_kind, vendored_from
```

## Added Test Coverage

- committed fixture file exists.
- fixture count is exactly 8.
- all required scenario IDs exist.
- loader can return committed fixtures without using `outputs/`.
- cannot-claim text remains visible.
- no-data state remains visible.
- external-context cannot-claim and not-executed state remain visible.
- proximity case does not promote blocked, caused, or confirmed impact as a known claim.
- boundary action refusal exposes no alert, dispatch, case, ticket, or enforcement affordance.
- clarification renders one targeted clarification.
- degraded render state remains visible.
- citation URL fetch is not attempted by adapter/view.
- ASK runtime is not invoked by the app handoff code.
- LLM calls are not invoked by the app handoff code.
