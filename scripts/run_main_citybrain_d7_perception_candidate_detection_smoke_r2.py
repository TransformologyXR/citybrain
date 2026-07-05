#!/usr/bin/env python3
"""Run D7 candidate detection smoke R2."""

from run_main_citybrain_d7_perception_candidate_observation_preflight import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("candidate_detection_smoke_r2")["status"] == "PASS" else 1)
