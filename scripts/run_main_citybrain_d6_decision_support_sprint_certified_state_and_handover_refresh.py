#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_after_parallel_decision_support_closeout_common import run_sprint_certified_state_and_handover_refresh


if __name__ == "__main__":
    print(json.dumps(run_sprint_certified_state_and_handover_refresh(), indent=2, sort_keys=True))
