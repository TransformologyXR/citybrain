# R7E Test Commands

## Results

- R7E runner: PASS
- R7E focused tests: PASS, 11 tests
- R7D focused tests: PASS, 17 tests
- R7C focused tests: PASS, 15 tests
- R7B focused tests: PASS, 12 tests
- R7A focused tests: PASS, 13 tests
- Full unittest discovery: PASS, 332 tests
- ASK runtime scoped diff: empty

## Commands

```powershell
.venv\Scripts\python.exe scripts\run_main_citybrain_r7e_perception_review_workflow_closeout.py
```

```powershell
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7e_perception_review_workflow_closeout
```

```powershell
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7d_webui_kit_event_state_smoke
```

```powershell
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff
```

```powershell
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7b_perception_to_event_fabric_local_replay
```

```powershell
.venv\Scripts\python.exe -m unittest tests.test_main_citybrain_r7a_perception_candidate_observation_ingress
```

```powershell
.venv\Scripts\python.exe -m unittest discover
```

```powershell
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
```
