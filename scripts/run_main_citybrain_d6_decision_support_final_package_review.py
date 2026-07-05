#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_after_parallel_decision_support_closeout_common import run_final_package_review


if __name__ == "__main__":
    print(json.dumps(run_final_package_review(), indent=2, sort_keys=True))
