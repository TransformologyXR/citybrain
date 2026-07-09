#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    'README.md','CODEX_TASK_PROMPT.md','IMPLEMENTATION_PLAN.md','ACCEPTANCE_CRITERIA.md','NON_GOALS_AND_BOUNDARIES.md',
    'specs/01_publication_home_retroactive_sweep_spec.md',
    'specs/02_epoch3_master_ledger_spec.md',
    'specs/03_learned_component_registry_snapshot_spec.md',
    'specs/04_loop_closeout_and_forecast_framing_spec.md',
    'specs/05_arming_handoff_to_epoch4_spec.md',
    'specs/06_epoch4_fork_roadmap_spec.md',
    'specs/07_no_forbidden_capability_audit_spec.md',
]
missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    raise SystemExit(f"Missing required files: {missing}")
for path in ROOT.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
for path in ROOT.rglob('*'):
    if path.is_file() and b'\r\n' in path.read_bytes():
        raise SystemExit(f"CRLF found in {path}")
print('PASS_E3_CLOSEOUT_V2_CODEX_PACKAGE_SELF_CHECK')
