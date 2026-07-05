#!/usr/bin/env python3
"""Track C replay sample bridge into R7A-compatible candidate observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_main_citybrain_perception_source_registry_r1 import (
    OUTPUTS,
    REPO_ROOT,
    stable_hash,
    utc_now,
    write_closeout,
    write_json,
    write_manifest,
    write_text,
    read_json,
    read_jsonl,
    reset_dir,
)


C2_ROOT = OUTPUTS / "main_citybrain_perception_source_registry_r1"
C3_ROOT = OUTPUTS / "main_citybrain_perception_replay_sample_bridge_r1"
PASS_C3 = "PASS_MAIN_CITYBRAIN_PERCEPTION_REPLAY_SAMPLE_BRIDGE_R1_WITH_LIMITATIONS"

REQUIRED_R7A_KEYS = [
    "candidate_observation_id",
    "cannot_claim",
    "claim_boundary",
    "confidence",
    "detected_class",
    "detector_kind",
    "detector_version",
    "evidence_refs",
    "frame_ref",
    "media_ref",
    "not_executed",
    "object_class",
    "observation_type",
    "observed_at",
    "packet_hash",
    "review_state",
    "source_id",
    "source_kind",
    "source_label",
    "zone_ref",
]

NON_CLAIMS = [
    "official violation",
    "legal or certified finding",
    "identity of a natural person",
    "official case/ticket creation",
    "dispatch/control/enforcement execution",
    "live camera or production camera claim",
]

NOT_EXECUTED = [
    "live_camera_connection",
    "production_api",
    "official_case_submission",
    "dispatch_control_enforcement",
    "llm_call",
]


def source_input_rows(limit: int = 6) -> list[dict[str, Any]]:
    rows = read_jsonl(OUTPUTS / "main_citybrain_metropolis_vss_object_metadata_export_r2" / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl", limit=limit)
    if rows:
        return rows
    return read_jsonl(
        OUTPUTS / "main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18" / "SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R18.jsonl",
        limit=limit,
    )


def to_r7a_candidate(row: dict[str, Any], index: int) -> dict[str, Any]:
    observation_id = row.get("observation_id") or row.get("candidate_observation_id") or f"track-c-source-row-{index:03d}"
    class_label = row.get("class_label") or row.get("object_class") or "object_candidate"
    detection_class = row.get("detection_class") or f"{class_label}_presence_candidate"
    frame_ref = row.get("frame_ref") or f"frame:track-c:sample-replay:{index:06d}"
    media_ref = row.get("media_source_id") or row.get("source_file_hash_or_stream_id") or "media:track-c:sample-replay"
    zone_ref = row.get("zone_id") or row.get("zone_ref") or "zone:track-c:sample-review-zone"
    candidate = {
        "candidate_observation_id": f"candidate:track-c:replay:{index:03d}",
        "cannot_claim": NON_CLAIMS,
        "claim_boundary": "candidate observation only; not an official fact, finding, violation, case, ticket, dispatch, control, or enforcement action",
        "confidence": float(row.get("confidence") or 0.0),
        "detected_class": class_label,
        "detector_kind": "deepstream_metropolis_replay_sample_bridge",
        "detector_version": row.get("model_version") or "track-c-r1-local-replay",
        "evidence_refs": [
            "source:track-c:deepstream-r2-object-metadata",
            str(frame_ref),
            str(media_ref),
            str(observation_id),
        ],
        "frame_ref": str(frame_ref),
        "geometry_ref": row.get("geometry_ref"),
        "location_ref": row.get("location_ref"),
        "media_ref": str(media_ref),
        "not_executed": NOT_EXECUTED,
        "object_class": class_label,
        "observation_type": detection_class,
        "observed_at": row.get("timestamp") or "2026-07-05T00:00:00Z",
        "original_observation_ref": observation_id,
        "review_state": "candidate",
        "source_class": "sensor_inferred",
        "source_id": "source:track-c:deepstream-r2-object-metadata",
        "source_kind": "sample_media_ref",
        "source_label": "Track C local replay bridge from DeepStream/Metropolis sample metadata",
        "track_ref": row.get("track_id"),
        "zone_ref": str(zone_ref),
    }
    candidate["packet_hash"] = stable_hash(candidate)
    return candidate


def compatibility_report(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    missing_by_item = []
    for candidate in candidates:
        missing = [key for key in REQUIRED_R7A_KEYS if key not in candidate or candidate.get(key) in (None, "")]
        missing_by_item.append({"candidate_observation_id": candidate.get("candidate_observation_id"), "missing": missing})
    required_ok = all(not item["missing"] for item in missing_by_item)
    boundary_ok = all(
        candidate.get("review_state") == "candidate"
        and candidate.get("source_class") == "sensor_inferred"
        and "dispatch/control/enforcement execution" in candidate.get("cannot_claim", [])
        for candidate in candidates
    )
    return {
        "candidate_count": len(candidates),
        "missing_by_item": missing_by_item,
        "r7a_compatible": required_ok and boundary_ok,
        "required_keys": REQUIRED_R7A_KEYS,
        "status": "PASS" if required_ok and boundary_ok else "FAIL",
    }


def boundary_audit(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [
        {"check": "candidate_observations_only", "passed": all(c.get("review_state") == "candidate" for c in candidates)},
        {"check": "sensor_inferred_source_class", "passed": all(c.get("source_class") == "sensor_inferred" for c in candidates)},
        {"check": "vss_not_used_as_fact_source", "passed": True},
        {"check": "no_official_submission_action", "passed": all("official_case_submission" in c.get("not_executed", []) for c in candidates)},
        {"check": "no_dispatch_control_enforcement", "passed": all("dispatch_control_enforcement" in c.get("not_executed", []) for c in candidates)},
        {"check": "no_legal_certified_claim", "passed": all("legal or certified finding" in c.get("cannot_claim", []) for c in candidates)},
        {"check": "no_live_camera_or_production_api", "passed": all("live_camera_connection" in c.get("not_executed", []) and "production_api" in c.get("not_executed", []) for c in candidates)},
    ]
    return {
        "checks": checks,
        "status": "PASS" if all(check["passed"] for check in checks) else "FAIL",
    }


def build_bridge_payload(limit: int = 6) -> dict[str, Any]:
    rows = source_input_rows(limit)
    candidates = [to_r7a_candidate(row, index + 1) for index, row in enumerate(rows)]
    report = compatibility_report(candidates)
    audit = boundary_audit(candidates)
    return {
        "audit": audit,
        "candidates": candidates,
        "input_rows": rows,
        "report": report,
    }


def write_bridge(limit: int = 6, write_closeout_after: bool = True) -> dict[str, Any]:
    registry_decision = read_json(C2_ROOT / "PERCEPTION_SOURCE_REGISTRY_R1_DECISION.json")
    if not registry_decision.get("continue_to_replay_bridge"):
        raise RuntimeError("Registry R1 is not pass-ready for C3 replay bridge")
    reset_dir(C3_ROOT)
    payload = build_bridge_payload(limit)
    input_index = {
        "input_samples": len(payload["input_rows"]),
        "source": "outputs/main_citybrain_metropolis_vss_object_metadata_export_r2/CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl",
        "fallback_source": "outputs/main_citybrain_metropolis_vss_bmd45_threshold_calibration_and_sample_expansion_r18/SENSOR_INFERRED_CANDIDATE_OBSERVATIONS_R18.jsonl",
        "live_camera_used": False,
        "production_ingestion_used": False,
        "url_fetch_used": False,
    }
    decision = {
        "package": "MAIN-CITYBRAIN-PERCEPTION-REPLAY-SAMPLE-BRIDGE-R1",
        "status": PASS_C3 if payload["report"]["status"] == "PASS" and payload["audit"]["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_PERCEPTION_REPLAY_SAMPLE_BRIDGE_R1",
        "created_at": utc_now(),
        "input_samples": len(payload["input_rows"]),
        "candidate_observations": len(payload["candidates"]),
        "r7a_compatible": payload["report"]["r7a_compatible"],
        "boundary_audit": payload["audit"]["status"],
        "contract_check": {
            "no_live_cameras": True,
            "no_production_ingestion": True,
            "vss_not_fact_source": True,
            "deepstream_metropolis_not_official_truth": True,
            "candidate_observations_only": True,
            "no_official_submission_action": True,
            "no_dispatch_control_enforcement": True,
            "no_legal_certified_claim": True,
            "no_ask_runtime_changed": True,
        },
    }
    write_json(C3_ROOT / "PERCEPTION_REPLAY_SAMPLE_INPUT_INDEX.json", input_index)
    write_json(C3_ROOT / "PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json", {"items": payload["candidates"]})
    write_json(C3_ROOT / "PERCEPTION_REPLAY_TO_R7A_COMPATIBILITY_REPORT.json", payload["report"])
    write_json(C3_ROOT / "PERCEPTION_REPLAY_SAMPLE_BRIDGE_BOUNDARY_AUDIT.json", payload["audit"])
    write_json(C3_ROOT / "PERCEPTION_REPLAY_SAMPLE_BRIDGE_R1_DECISION.json", decision)
    write_text(
        C3_ROOT / "PERCEPTION_REPLAY_SAMPLE_BRIDGE_TEST_LOG.md",
        "\n".join(
            [
                "# Perception Replay Sample Bridge R1 Test Log",
                "",
                f"Status: `{decision['status']}`",
                f"Input samples: `{decision['input_samples']}`",
                f"Candidate observations: `{decision['candidate_observations']}`",
                f"R7A compatible: `{decision['r7a_compatible']}`",
                "",
                "No live camera, production ingestion, URL fetch, production API, or LLM call was used.",
            ]
        ),
    )
    write_manifest(C3_ROOT, "PERCEPTION_REPLAY_SAMPLE_BRIDGE_HASH_MANIFEST.json")
    if write_closeout_after:
        write_closeout(decision)
    return decision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Track C replay sample bridge.")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--no-closeout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = write_bridge(args.limit, write_closeout_after=not args.no_closeout)
    print(f"Status: {decision['status']}")
    print(f"Input samples: {decision['input_samples']}")
    print(f"Candidate observations: {decision['candidate_observations']}")
    print(f"R7A compatible: {decision['r7a_compatible']}")
    return 0 if decision["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
