# MAIN-CITYBRAIN-R7-COMMIT-AND-PUSH

Status: SOURCE-CONTROL ONLY - DO NOT IMPLEMENT RUNTIME CHANGES

Context:
- R7 local/replay perception-to-review workflow is closed with `PASS_MAIN_CITYBRAIN_R7_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_WITH_LIMITATIONS`.
- Scope: R7 preflight, R7A, R7B, R7C, R7D, and R7E scripts/tests/output artifacts only.

Do not:
- change runtime behavior
- change ASK runtime, schemas, registries, CHECK, renderer, eval, or app handoff logic
- add live camera/media/retrieval/API/URL/LLM behavior
- add official submission, dispatch, control, enforcement, legal/certified claims, full citywide twin, or live Kit control
- stage unrelated dirty files

Pre-commit checks:
```powershell
git status --short --branch
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7e_perception_review_workflow_closeout
.venv\Scripts\python.exe -m unittest discover
```

Recommended commit message:
```text
Close R7 local replay perception review workflow
```
