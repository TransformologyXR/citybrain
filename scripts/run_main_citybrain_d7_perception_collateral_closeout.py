#!/usr/bin/env python3
"""Run D7 perception collateral closeout."""

from run_collateral_d7_perception_candidate_observation_after_freeze import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("closeout")["status"] == "PASS" else 1)
