#!/usr/bin/env python3
"""Run D7 fixture source scout R1."""

from run_main_citybrain_d7_perception_candidate_observation_preflight import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("fixture_source_scout_r1")["status"] == "PASS" else 1)
