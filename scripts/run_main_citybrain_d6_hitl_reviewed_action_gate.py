#!/usr/bin/env python3
"""Gate wrapper for the D6 HITL reviewed-action Track D lane."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_main_citybrain_d6_hitl_reviewed_action import main


if __name__ == "__main__":
    raise SystemExit(main())
