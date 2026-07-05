#!/usr/bin/env python3
import argparse
from pathlib import Path

from citybrain_d8_web_kit_live_surface_common import output_root, run_bridge_smoke


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root")
    args = parser.parse_args()
    target = Path(args.output_root) if args.output_root else output_root("bridge_sync")
    run_bridge_smoke(target)
