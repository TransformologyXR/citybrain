# Run Guidance

Recommended run from repo root:

```powershell
cd C:\Users\hazem\Documents\CityBrain
python scripts\run_main_citybrain_epoch4_eval_representativeness_audit_r1.py
python -m pytest tests\test_main_citybrain_epoch4_eval_representativeness_audit_r1.py -q
python scripts\run_main_citybrain_epoch4_eval_representativeness_audit_r1.py --validate-only
```

Expected status:

```text
PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS
```

This package is safe to run before founder review. It should not require live data, external operators, UI work, model training, or source mutation.

If a required root is missing, the package should create `MISSING_INPUTS.json` and continue best-effort unless the eval/founder material cannot be located at all.
