#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_decision_support_demo_polish_common import run_polish_r1


if __name__ == "__main__":
    print(json.dumps(run_polish_r1(), indent=2, sort_keys=True))
