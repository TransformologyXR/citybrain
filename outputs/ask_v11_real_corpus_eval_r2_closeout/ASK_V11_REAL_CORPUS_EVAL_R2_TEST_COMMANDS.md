# ASK v1.1 Real-Corpus Eval R2 Test Commands

## Commands Run

```powershell
git branch --show-current
git log -1 --oneline
git status --short --branch
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_real_corpus_eval_r1
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_real_corpus_eval_r2_mapping_expansion
.venv\Scripts\python.exe scripts\run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```

## Results

- R1 real-corpus eval tests: 11 passed
- R2 mapping expansion tests: 6 passed
- R2 CLI writer: `PASS_ASK_V11_REAL_CORPUS_EVAL_R2_WITH_LIMITATIONS`

## Commands Not Run

- Sealed eval writer was not rerun.
- No live retrieval command was run.
- No production API command was run.
- No git commit, push, or PR command was run.

## R2 Expected Values Verified

- final_decision: `PASS_ASK_V11_REAL_CORPUS_EVAL_R2_WITH_LIMITATIONS`
- total_cases: 19
- evaluated_cases: 18
- pass_count: 18
- fail_count: 0
- excluded_cases: 1
- sev_4_real_failure_count: 0
- boundary_action_sev4_count: 0
- raw_query_leak_count: 0
- official_action_claim_count: 0
- future_flow_runtime_violation_count: 0
- live_retrieval_attempt_count: 0
- contradiction_case_status: `waived_no_retained_same_claim_pair`
