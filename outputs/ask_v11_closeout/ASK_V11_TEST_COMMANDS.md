# ASK v1.1 Test Commands

## Required Regression Commands

```powershell
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_packets
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_registries
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_g1_g5_spine
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_g6_g8_check_answer_render
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_eval_sealing
.venv\Scripts\python.exe -m unittest tests.test_ask_v11_future_flow_skeletons
.venv\Scripts\python.exe scripts\run_ask_v11_sealed_eval.py
```

## Recorded Passing Counts

- P0 packets: 14 passed.
- P1 registries: 19 passed.
- P2 spine: 32 passed.
- P3 CHECK/answer/render: 40 passed.
- P4 eval sealing: 22 passed.
- P4 skeleton flows: 13 passed.
- Sealed eval CLI: PASS.

## Sealed Eval Artifact Outputs

```text
outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json
outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_SUMMARY.md
```
