#!/usr/bin/env python3
from __future__ import annotations

import json

from citybrain_track_d_option_set_promotion_common import run_closeout


if __name__ == "__main__":
    print(json.dumps(run_closeout(), indent=2, sort_keys=True))
