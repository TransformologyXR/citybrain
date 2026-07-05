#!/usr/bin/env python3
"""Run D7 human review handoff R4."""

from run_main_citybrain_d7_perception_candidate_observation_preflight import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("human_review_handoff_r4")["status"] == "PASS" else 1)
