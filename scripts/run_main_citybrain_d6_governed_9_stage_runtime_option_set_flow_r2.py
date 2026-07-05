#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_governed_9_stage_runtime_thin_slice_common import run_option_set_flow_r2


if __name__ == "__main__":
    print(json.dumps(run_option_set_flow_r2(), indent=2, sort_keys=True))
