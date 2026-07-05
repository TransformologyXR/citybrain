#!/usr/bin/env python3
"""Run D7 perception candidate observation closeout."""

from run_main_citybrain_d7_perception_candidate_observation_preflight import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("closeout")["status"] == "PASS" else 1)
