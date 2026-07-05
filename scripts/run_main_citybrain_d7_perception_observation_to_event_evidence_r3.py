#!/usr/bin/env python3
"""Run D7 observation to event/evidence R3."""

from run_main_citybrain_d7_perception_candidate_observation_preflight import run_task


if __name__ == "__main__":
    raise SystemExit(0 if run_task("observation_to_event_evidence_r3")["status"] == "PASS" else 1)
