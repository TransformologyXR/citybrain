# ASK v1.1 Real-Corpus Eval R2 Next Steps

## Recommended Next Package

`ASK-V11-REAL-CORPUS-EVAL-R2-COMMIT-AND-PUSH`

## Scope

Stage and commit only the real-corpus eval files and artifacts:

- eval-only harness module,
- R1/R2 real-corpus eval scripts,
- R1/R2 real-corpus eval tests,
- preflight artifacts,
- R1 artifacts,
- contradiction scout artifacts,
- R2 artifacts,
- R2 closeout artifacts.

## Do Not

- Do not change G1-G8 runtime.
- Do not change packet schemas.
- Do not change registries, CHECK, or renderer rules.
- Do not rerun the sealed eval writer.
- Do not include unrelated dirty files.
- Do not include unrelated chronology, Omniverse, VSS, or generic CityBrain artifacts.
- Do not add live retrieval, production API, official action, ticket, dispatch, enforcement, legal, or certified behavior.

## Suggested Commit Message

```text
Add ASK v1.1 real-corpus eval R2 closeout
```

## Required Commit Checks

- Verify branch is `ask-v11-canonical-implementation-sprint`.
- Verify staged files are only ASK v1.1 real-corpus eval files/artifacts.
- Verify R2 decision is `PASS_ASK_V11_REAL_CORPUS_EVAL_R2_WITH_LIMITATIONS`.
- Verify hash manifest reports `HASH_MANIFEST_OK`.
- Leave unrelated dirty files untouched.
