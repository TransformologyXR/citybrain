#!/usr/bin/env python3
import json

from citybrain_d8_human_readable_web_ux_common import run_all


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, sort_keys=True))
