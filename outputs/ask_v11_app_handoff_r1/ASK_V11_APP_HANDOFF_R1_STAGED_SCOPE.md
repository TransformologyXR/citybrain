# ASK v1.1 App Handoff R1 Staged Scope

## Branch

`ask-v11-canonical-implementation-sprint`

## Staged Files

- `apps/web-control-room/src/askV11/askV11FixtureLoader.js`
- `apps/web-control-room/src/askV11/askV11HandoffAdapter.js`
- `apps/web-control-room/src/views/askV11Handoff.js`
- `apps/web-control-room/src/runtimeBundle.js`
- `apps/web-control-room/src/renderApp.js`
- `apps/web-control-room/styles.css`
- `tests/test_ask_v11_app_handoff_r1.py`
- `docs/ask-v11/ask-v11-app-handoff-r1.md`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_DECISION.json`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_SUMMARY.md`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_TEST_REPORT.md`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_LIMITATIONS.md`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_NEXT_STEPS.md`
- `outputs/ask_v11_app_handoff_r1/ASK_V11_APP_HANDOFF_R1_STAGED_SCOPE.md`

## Files Intentionally Excluded

- Whole `apps/` tree and unrelated app files.
- Kit handoff files.
- ASK runtime files under `packages/ask_v11/`.
- Packet schemas under `packages/contracts/`.
- ASK eval writers and real-corpus harness files.
- Local sealed eval drift under `outputs/ask_v11_sealed_eval/`.
- Unrelated chronology, forensic, handoff, Metropolis/VSS, Omniverse/WebRTC, input, corpus, tmp, and loose text files.
- Preflight artifacts under `outputs/ask_v11_app_handoff_preflight/`; R1 commit scope follows the source-control prompt and commits the R1 closeout artifacts only.

## Test Command and Result

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_app_handoff_r1
```

Result:

```text
Ran 16 tests in 0.048s
OK
```

## ASK Runtime Check

Scoped runtime diff command:

```powershell
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```

Result: no output.

ASK runtime was unchanged.

## Commit Message

Subject:

```text
Add ASK v1.1 app handoff R1
```

Body:

```text
Wire sealed ASK v1.1 local/demo fixture packets into the web control room.

Add ASK fixture loader, handoff adapter, cockpit renderer, and fixture-driven UI tests.

Expose answer, knowns, unknowns, cannot-claim, CHECK details, citations, trace, clarification, boundary/refusal, not-executed, and degraded-render state.

Preserve ASK runtime boundaries: no G1-G8 changes, no schema changes, no registry/CHECK/render changes, no live retrieval, no citation URL fetching, no production API, no official action/ticket/dispatch, and no LLM call.

Limit scope to web-control-room; Kit handoff remains future work.
```

## Limitations

- Web-control-room only; Kit handoff remains future work.
- The ASK panel renders only when the local preflight fixture JSON exists.
- `apps/` is untracked in this workspace, so only the exact R1 files were staged.
- `outputs/` is ignored, so R1 artifacts were force-added explicitly.
