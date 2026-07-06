#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.citybrain_epoch_2_0_common import run_registry_audit


if __name__ == "__main__":
    raise SystemExit(run_registry_audit())
