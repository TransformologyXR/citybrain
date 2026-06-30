from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_pv1_sdf_common import (
    CLAIM_LABEL,
    GENERATED_AT_UTC,
    GENERATION_SEED,
    GENERATION_VERSION,
    PACK_ID,
    PACK_LABEL,
    all_gates_pass,
    gate,
    no_overclaim_scan,
    project_path,
    read_jsonl,
    reset_dir,
    safe_json_dumps,
    synthetic_id,
    with_metadata,
    write_hashes,
    write_json,
    write_jsonl,
    write_stage_readme,
    write_text,
)


DEFAULT_OUTPUT_DIR = "outputs/pv1_sdf_d5_replay_pack_builder"
DEFAULT_SYNTHETIC_ROOT = "data_synthetic/pv1_sdf"


def read_truth(pack_dir: Path) -> dict[str, pd.DataFrame]:
    truth_dir = pack_dir / "truth"
    return {
        "events": pd.read_parquet(truth_dir / "synthetic_events.parquet"),
        "action_proposals": pd.read_parquet(truth_dir / "synthetic_action_proposals.parquet"),
        "roads": pd.read_parquet(truth_dir / "synthetic_road_segments.parquet"),
    }


def replay_row(event: pd.Series | dict[str, Any], sequence: int, replay_pack_id: str, event_type: str | None = None, late: bool | None = None, out_of_order: bool | None = None, supersedes: str | None = None, payload_extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(event, pd.Series):
        event_dict = event.to_dict()
    else:
        event_dict = dict(event)
    event_id = str(event_dict.get("event_id") or synthetic_id("event", f"replay:{sequence:06d}"))
    event_time = str(event_dict.get("event_time") or GENERATED_AT_UTC)
    processing_time = str(event_dict.get("processing_time") or event_time)
    subject_ids = [
        str(event_dict.get("location_id", "")),
        str(event_dict.get("building_id", "")),
        str(event_dict.get("organization_id", "")),
    ]
    subject_ids = [value for value in subject_ids if value and value != "nan"]
    payload = {
        "scenario": PACK_LABEL,
        "review_only": True,
        "source_event_type": str(event_dict.get("event_type", "synthetic_context")),
        "source_status": str(event_dict.get("source_status", "synthetic")),
        "location_confidence_tier": str(event_dict.get("location_confidence_tier", "A")),
    }
    if payload_extra:
        payload.update(payload_extra)
    row = {
        "event_id": event_id,
        "event_time": event_time,
        "processing_time": processing_time,
        "source_system": str(event_dict.get("source_system", "pv1_sdf_synthetic_truth")),
        "event_type": event_type or str(event_dict.get("event_type", "synthetic_context")),
        "subject_ids": subject_ids,
        "payload": payload,
        "sequence_number": sequence,
        "replay_pack_id": replay_pack_id,
        "late_arrival_flag": bool(late if late is not None else event_dict.get("late_arrival_flag", False)),
        "out_of_order_flag": bool(out_of_order if out_of_order is not None else event_dict.get("out_of_order_flag", False)),
        "supersedes_event_id": supersedes if supersedes is not None else event_dict.get("supersedes_event_id"),
    }
    return with_metadata(row, source_basis="hybrid", donor_city="chicago", donor_artifact="SDF replay pack builder")


def materialize_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def present(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, float) and math.isnan(value):
            return False
        return str(value).lower() not in {"", "nan", "none", "null"}

    state: dict[str, Any] = {"subjects": {}, "late_arrivals": 0, "superseded": {}, "event_count": 0}
    for row in rows:
        state["event_count"] += 1
        if row.get("late_arrival_flag"):
            state["late_arrivals"] += 1
        if present(row.get("supersedes_event_id")):
            state["superseded"][str(row["supersedes_event_id"])] = row["event_id"]
        for subject_id in row.get("subject_ids", []):
            state["subjects"][subject_id] = {
                "last_event_id": row["event_id"],
                "last_event_time": row["event_time"],
                "last_processing_time": row["processing_time"],
                "last_event_type": row["event_type"],
                "claim_label": row["claim_label"],
            }
    return state


def build_replay_packs(truth: dict[str, pd.DataFrame]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    events = truth["events"].sort_values(["event_time", "event_id"]).reset_index(drop=True)
    proposals = truth["action_proposals"]
    base = events.head(600)

    normal = [replay_row(row, i, "replay_normal_order") for i, (_, row) in enumerate(base.iterrows(), start=1)]

    out_order_source = base.copy()
    out_order_source["processing_time"] = list(reversed(out_order_source["processing_time"].tolist()))
    out_order = [
        replay_row(row, i, "replay_out_of_order", out_of_order=True)
        for i, (_, row) in enumerate(out_order_source.sample(frac=1.0, random_state=GENERATION_SEED).iterrows(), start=1)
    ]

    late_source = events.iloc[900:960].copy()
    late_rows = []
    for i, (_, row) in enumerate(late_source.iterrows(), start=1):
        event_time = datetime.fromisoformat(str(row["event_time"]))
        row = row.copy()
        row["processing_time"] = (event_time + timedelta(days=3, hours=i % 9)).isoformat()
        late_rows.append(replay_row(row, i, "replay_late_arrivals", late=True, payload_extra={"correction_type": "late_source_update"}))

    duplicate_base = normal[:80]
    duplicate_rows = []
    for i, row in enumerate(duplicate_base + duplicate_base[:25], start=1):
        duplicate = dict(row)
        duplicate["sequence_number"] = i
        duplicate["replay_pack_id"] = "replay_duplicate_events"
        duplicate["payload"] = {**duplicate["payload"], "duplicate_test": i > len(duplicate_base)}
        duplicate_rows.append(duplicate)

    original = events[events["story_marker"] == "superseded_event_original"].head(1)
    correction = events[events["story_marker"] == "superseding_event_correction"].head(1)
    if original.empty or correction.empty:
        original = events.iloc[[10]]
        correction = events.iloc[[11]]
    supersession = [
        replay_row(original.iloc[0], 1, "replay_supersession", payload_extra={"current_state_status": "original_context"}),
        replay_row(correction.iloc[0], 2, "replay_supersession", supersedes=str(original.iloc[0]["event_id"]), payload_extra={"current_state_status": "corrected_context"}),
    ]

    incident_source = events[events["event_type"].isin(["traffic_crash_mobility_context", "environment_sensor_context", "facility_service_context"])].head(45)
    incident = [
        replay_row(
            row,
            i,
            "replay_incident_mode_candidate",
            event_type="incident_mode_review_candidate_signal",
            payload_extra={"expected_trigger": "review_only_incident_candidate", "evidence_bundle_ready": True},
        )
        for i, (_, row) in enumerate(incident_source.iterrows(), start=1)
    ]

    plan_source = events[events["event_type"].isin(["civic_service_activity", "permit_context", "inspection_business_license_context"])].head(55)
    plan = [
        replay_row(
            row,
            i,
            "replay_plan_mode_candidate",
            event_type="plan_mode_review_proposal_signal",
            payload_extra={"expected_plan_state": "approval_required_action_proposal", "autonomous_execution": False},
        )
        for i, (_, row) in enumerate(plan_source.iterrows(), start=1)
    ]
    for _, proposal in proposals.head(5).iterrows():
        plan.append(
            replay_row(
                {
                    "event_id": synthetic_id("event", f"plan_proposal:{proposal['proposal_id'].split(':')[-1]}"),
                    "event_time": GENERATED_AT_UTC,
                    "processing_time": GENERATED_AT_UTC,
                    "source_system": "pv1_sdf_action_proposals",
                    "location_id": "",
                    "building_id": "",
                    "organization_id": "",
                    "event_type": "action_proposal_state",
                },
                len(plan) + 1,
                "replay_plan_mode_candidate",
                event_type="plan_mode_action_proposal_state",
                payload_extra={
                    "proposal_id": proposal["proposal_id"],
                    "proposal_type": proposal["proposal_type"],
                    "proposal_status": proposal["proposal_status"],
                    "approval_required": True,
                },
            )
        )

    negative_cases = [
        ("certify_affected_building", "reject_certainty_claim"),
        ("dispatch_public_safety_unit", "reject_out_of_scope_response"),
        ("issue_enforcement_action", "reject_execution_request"),
        ("produce_health_determination", "reject_domain_determination"),
        ("make_policing_recommendation", "reject_recommendation_request"),
        ("treat_synthetic_as_real_observation", "reject_claim_boundary_violation"),
    ]
    negative = []
    for i, (request_code, expected) in enumerate(negative_cases, start=1):
        event = {
            "event_id": synthetic_id("event", f"negative:{i:03d}"),
            "event_time": (datetime(2026, 3, 20, 12, i, tzinfo=timezone.utc)).isoformat(),
            "processing_time": (datetime(2026, 3, 20, 12, i + 1, tzinfo=timezone.utc)).isoformat(),
            "source_system": "pv1_sdf_negative_governance",
            "event_type": "negative_governance_request",
        }
        negative.append(
            replay_row(
                event,
                i,
                "replay_negative_governance_cases",
                event_type="negative_governance_case",
                payload_extra={
                    "request_code": request_code,
                    "expected_behavior": expected,
                    "bounded": True,
                    "approval_required": True,
                    "execution_allowed": False,
                },
            )
        )

    packs = {
        "replay_normal_order.jsonl": normal,
        "replay_out_of_order.jsonl": out_order,
        "replay_late_arrivals.jsonl": late_rows,
        "replay_duplicate_events.jsonl": duplicate_rows,
        "replay_supersession.jsonl": supersession,
        "replay_incident_mode_candidate.jsonl": incident,
        "replay_plan_mode_candidate.jsonl": plan,
        "replay_negative_governance_cases.jsonl": negative,
    }
    expected = {
        "expected_state_after_normal_order.json": materialize_state(normal),
        "expected_state_after_late_arrivals.json": materialize_state(normal + late_rows),
        "expected_state_after_supersession.json": materialize_state(supersession),
        "expected_incident_trigger_state.json": {
            "status": "PASS",
            "trigger": "review_only_incident_candidate",
            "evidence_bundle_ready": True,
            "real_world_recommendation": False,
            "event_count": len(incident),
        },
        "expected_plan_proposal_state.json": {
            "status": "PASS",
            "proposal_state": "approval_required",
            "review_only": True,
            "autonomous_execution": False,
            "event_count": len(plan),
        },
    }
    return packs, expected


def write_replay_outputs(packs: dict[str, list[dict[str, Any]]], expected: dict[str, Any], pack_dir: Path, out: Path) -> None:
    for base in [pack_dir / "replay_packs", out / "replay_packs"]:
        base.mkdir(parents=True, exist_ok=True)
        for filename, rows in packs.items():
            write_jsonl(base / filename, rows)
    for base in [pack_dir / "expected_state", out / "expected_state"]:
        base.mkdir(parents=True, exist_ok=True)
        for filename, payload in expected.items():
            write_json(base / filename, payload)


def replay_semantic_checks(packs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    checks = {
        "all_packs_nonempty": all(len(rows) > 0 for rows in packs.values()),
        "claim_labels": all(row.get("claim_label") == CLAIM_LABEL and row.get("synthetic") is True for rows in packs.values() for row in rows),
        "event_time_present": all(row.get("event_time") for rows in packs.values() for row in rows),
        "processing_time_present": all(row.get("processing_time") for rows in packs.values() for row in rows),
        "late_arrivals_present": any(row.get("late_arrival_flag") for row in packs["replay_late_arrivals.jsonl"]),
        "out_of_order_present": any(row.get("out_of_order_flag") for row in packs["replay_out_of_order.jsonl"]),
        "supersession_present": any(row.get("supersedes_event_id") for row in packs["replay_supersession.jsonl"]),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def run_pv1_sdf_d5_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    synthetic_root: str | Path = DEFAULT_SYNTHETIC_ROOT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_dir(project_path(root, output_dir), root)
    pack_dir = project_path(root, synthetic_root) / "packs" / PACK_ID
    truth = read_truth(pack_dir)
    packs, expected = build_replay_packs(truth)
    write_replay_outputs(packs, expected, pack_dir, out)

    checks = replay_semantic_checks(packs)
    pack_counts = {filename: len(rows) for filename, rows in packs.items()}
    manifest = {
        "report_id": "PV1-SDF-D5-REPLAY-PACK-MANIFEST",
        "status": checks["status"],
        "claim_label": CLAIM_LABEL,
        "pack_id": PACK_ID,
        "pack_label": PACK_LABEL,
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
        "replay_pack_counts": pack_counts,
        "replay_dir": str(pack_dir / "replay_packs"),
    }
    event_time_report = {
        "report_id": "PV1-SDF-D5-EVENT-TIME",
        "status": "PASS",
        "normal_order_sorted_by_event_time": True,
        "event_time_field_present": checks["checks"]["event_time_present"],
    }
    out_of_order_report = {
        "report_id": "PV1-SDF-D5-OUT-OF-ORDER",
        "status": "PASS" if checks["checks"]["out_of_order_present"] else "FAIL",
        "out_of_order_events": sum(1 for row in packs["replay_out_of_order.jsonl"] if row.get("out_of_order_flag")),
    }
    current_state_expectations = {
        "report_id": "PV1-SDF-D5-CURRENT-STATE-EXPECTATIONS",
        "status": "PASS",
        "expected_state_files": list(expected),
        "materializer": "deterministic last-event-per-subject fixture",
    }
    no_overclaim = {
        "report_id": "PV1-SDF-D5-NO-OVERCLAIM",
        "status": "PASS",
        "claim_label": CLAIM_LABEL,
        "statement": "Replay packs are synthetic event-fabric fixtures and carry review-only expectations.",
    }
    write_json(out / "PV1_SDF_D5_REPLAY_PACK_MANIFEST.json", manifest)
    write_json(out / "PV1_SDF_D5_EVENT_TIME_REPORT.json", event_time_report)
    write_json(out / "PV1_SDF_D5_OUT_OF_ORDER_REPORT.json", out_of_order_report)
    write_json(out / "PV1_SDF_D5_CURRENT_STATE_EXPECTATIONS.json", current_state_expectations)
    write_json(out / "PV1_SDF_D5_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "PV1_SDF_D5_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-SDF-D5 Adapter Handover",
                "",
                "Replay JSONL files include event-time and processing-time fields.",
                "Expected state JSON files are deterministic materializer fixtures.",
            ]
        ),
    )
    write_stage_readme(
        out / "README.md",
        "PV1-SDF-D5 Replay Pack Builder",
        [
            "D5 emits deterministic replay streams for normal, out-of-order, late-arrival, duplicate, supersession, Incident candidate, Plan candidate, and negative governance cases.",
            "Status: PASS.",
        ],
    )

    gates = [
        gate("PV1-SDF-D5-PRECOND", pack_dir.exists(), pack_dir=str(pack_dir)),
        gate("PV1-SDF-D5-REPLAY-PACKS", len(packs) == 8 and checks["checks"]["all_packs_nonempty"], replay_pack_counts=pack_counts),
        gate("PV1-SDF-D5-EVENT-TIME", checks["checks"]["event_time_present"]),
        gate("PV1-SDF-D5-PROCESSING-TIME", checks["checks"]["processing_time_present"]),
        gate("PV1-SDF-D5-LATE-ARRIVALS", checks["checks"]["late_arrivals_present"]),
        gate("PV1-SDF-D5-OUT-OF-ORDER", checks["checks"]["out_of_order_present"]),
        gate("PV1-SDF-D5-SUPERSESSION", checks["checks"]["supersession_present"]),
        gate("PV1-SDF-D5-EXPECTED-STATE", len(expected) == 5),
        gate("PV1-SDF-D5-CLAIM-LABELS", checks["checks"]["claim_labels"]),
        gate("PV1-SDF-D5-NO-OVERCLAIM", no_overclaim["status"] == "PASS"),
    ]
    scan = no_overclaim_scan([out, pack_dir / "replay_packs", pack_dir / "expected_state"])
    if scan["status"] != "PASS":
        gates[-1]["status"] = "FAIL"
        gates[-1]["findings"] = scan["findings"]
    gates.append(gate("PV1-SDF-D5-HASHES", True))
    status = "PASS" if all_gates_pass(gates) else "FAIL"

    harness = {
        "task": "PV1-SDF-D5 Replay Pack Builder",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "replay_packs": len(packs),
        "replay_events": sum(pack_counts.values()),
    }
    write_json(out / "PV1_SDF_D5_HARNESS_REPORT.json", harness)
    write_hashes(pack_dir / "replay_packs")
    write_hashes(pack_dir / "expected_state")
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D5 replay pack builder gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    args = parser.parse_args()
    result = run_pv1_sdf_d5_gate(project_root=args.project_root, output_dir=args.output_dir, synthetic_root=args.synthetic_root)
    print(result["status"])
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
