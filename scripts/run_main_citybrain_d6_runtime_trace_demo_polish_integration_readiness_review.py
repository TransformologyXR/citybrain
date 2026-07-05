#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_runtime_trace_demo_polish_closeout_common import run_integration_readiness_review


if __name__ == "__main__":
    print(json.dumps(run_integration_readiness_review(), indent=2, sort_keys=True))
