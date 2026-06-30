#!/usr/bin/env python3
"""Run MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-SELECTION-AND-SLICE-PREFLIGHT."""

from __future__ import annotations

import json

from run_main_track1_d4y_r5_preflight_common import run_task


def main() -> int:
    result = run_task("r5_1")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
