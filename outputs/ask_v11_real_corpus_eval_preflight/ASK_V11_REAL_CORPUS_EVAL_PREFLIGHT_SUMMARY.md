# ASK v1.1 Real Corpus Eval Preflight Summary

Package: ASK-V11-REAL-CORPUS-EVAL-PREFLIGHT
Status: PASS_WITH_LIMITATIONS

## Decision

ASK v1.1 is ready for a real-corpus eval R1 package, but R1 should implement an eval harness/adapter only. It must not change G1-G8 runtime behavior.

Recommended next package:

```text
ASK-V11-REAL-CORPUS-EVAL-R1
```

## Baseline

- Branch: `ask-v11-canonical-implementation-sprint`
- Commit: `3907bc1665e4d02b1410a66146d59a32042d85b3`
- Commit subject: `Implement ASK v1.1 canonical packet flow and sealed eval`
- Published remote: `https://github.com/TransformologyXR/citybrain`
- Sealed eval baseline: `PASS_ASK_V11_SEALED_EVAL`
- Sealed eval cases: 21/21 passed
- Sev-4 real failures: 0

## Local Hygiene

- The local drift in `outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json` was restored to the committed version.
- The sealed eval writer was not rerun.
- No ASK runtime file was changed.
- Unrelated dirty files were left untouched.

## Corpus Inventory Result

Strong retained local corpus candidates exist for:

- London Wood Lane / Scrubbs Lane mobility access story and source records.
- London rapid EV charging source-record cards.
- NYC MVC cascade review story with candidate asset/resource context.
- Chicago similar-case memory records.
- Helsinki visual entity pick source records.
- Guardrail refusal review records.
- Human review stop records.
- Candidate observation records.
- D9 product-mode ASK contract and sample ASK answers.

## Case Matrix Result

- Total candidate cases: 19
- Ready cases: 10
- Needs-mapping cases: 8
- Excluded cases: 1
- Families with candidate entries: 19
- Families missing ready real-corpus coverage: contradiction

## Main Finding

The corpus is rich enough for ASK v1.1 real-corpus evaluation, but the current ASK G5 is intentionally fixture-only. R1 should add a non-runtime eval adapter that maps retained local artifacts into eval evidence inputs without modifying the canonical G1-G8 runtime.

## Hard Boundaries For R1

- Use retained local corpus only.
- No live retrieval.
- No production API.
- No official action, ticket, dispatch, route/control, enforcement, legal/certified finding, or autonomous workflow.
- Report Sev-4 separately.
- Any runtime fix must be deferred until R1 exposes a concrete failure.
