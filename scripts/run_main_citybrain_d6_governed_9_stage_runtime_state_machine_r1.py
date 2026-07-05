#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_governed_9_stage_runtime_thin_slice_common import run_state_machine_r1


if __name__ == "__main__":
    print(json.dumps(run_state_machine_r1(), indent=2, sort_keys=True))
