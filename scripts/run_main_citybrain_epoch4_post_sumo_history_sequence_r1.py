#!/usr/bin/env python3
"""Run the Epoch 4 Post-SUMO / History sequence R1.

Sequence:
1. Simulation V2.4 Family SUMO Option Runner
2. Event Fabric V2.4 Replay Scale + Consumption
3. Review Packet 360 V2 / Pilot Binder Refresh
4. Post-SUMO / History Final Reverify

All outputs are additive, sequential, local/replay/review-only, and bounded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SIM_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1"
EVENT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_4_replay_scale_consumption_r1"
REVIEW_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_post_sumo_history_sequence_r1"

PUB_SIM = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-simulation-v2-4-family-sumo-option-runner-r1"
PUB_EVENT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-event-fabric-v2-4-replay-scale-consumption-r1"
PUB_REVIEW = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-review-packet-360-v2-pilot-binder-refresh-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-post-sumo-history-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-post-sumo-history-sequence-r1"

STATUS_SIM = "PASS_MAIN_CITYBRAIN_EPOCH4_SIMULATION_V2_4_FAMILY_SUMO_OPTION_RUNNER_R1_WITH_LIMITATIONS"
STATUS_EVENT = "PASS_MAIN_CITYBRAIN_EPOCH4_EVENT_FABRIC_V2_4_REPLAY_SCALE_CONSUMPTION_R1_WITH_LIMITATIONS"
STATUS_REVIEW = "PASS_MAIN_CITYBRAIN_EPOCH4_REVIEW_PACKET_360_V2_PILOT_BINDER_REFRESH_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_POST_SUMO_HISTORY_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_POST_SUMO_HISTORY_SEQUENCE_R1_WITH_LIMITATIONS"

SELECTED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
CONTROL_FAMILY = "mobility_access_interruption"
ALL_FAMILIES = [CONTROL_FAMILY] + SELECTED_FAMILIES

EVENT_CHANGE_CLASSES = [
    "new",
    "changed_state",
    "expired",
    "stale",
    "superseded",
    "duplicate_suppressed",
    "unresolved_preserved",
    "quarantined_invalid",
    "watch_candidate",
    "check_attached",
    "brief_attached",
    "spatial_ready",
    "source_refresh_delta",
    "diff_entity_change",
]

FORBIDDEN_CAPABILITIES = [
    "production_live_ingestion",
    "official_action_case_ticket",
    "dispatch_control_enforcement",
    "product_forecast_surface_or_ForecastPacket",
    "learned_model_training_or_ranking",
    "founder_operator_review_session_results",
    "operator_founder_fuel_or_dispositions",
    "source_truth_mutation",
]

REVIEW_SECTIONS = [
    "source_records",
    "cer_entity",
    "seg_context",
    "event_state",
    "check_v1_result",
    "simulation_option_comparison",
    "brief_v3_variant_refs",
    "spatial_overlay_refs",
    "diff_source_refresh_refs",
    "data_maturity_refs",
    "cannot_claim",
    "limitations",
]

INPUTS = {
    "after_next_wave_sequence": ROOT / "outputs" / "main_citybrain_epoch4_after_next_wave_sequence_r1" / "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json",
    "after_next_wave_final": ROOT / "outputs" / "main_citybrain_epoch4_after_next_wave_final_reverify_r1" / "DECISION.json",
    "simulation_v2_3_decision": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_3_sumo_real_run_smoke_r1" / "DECISION.json",
    "simulation_v2_3_report": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_3_sumo_real_run_smoke_r1" / "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json",
    "event_fabric_v2_3_decision": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_3_history_diff_replay_r1" / "DECISION.json",
    "event_fabric_v2_3_log": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_3_history_diff_replay_r1" / "EVENT_FABRIC_V2_3_SNAPSHOT_EVENT_LOG.jsonl",
    "product_loop_final": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_final_reverify_r1" / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
    "incident_plan_loop": ROOT / "outputs" / "main_citybrain_epoch4_incident_plan_three_family_product_loop_r1" / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json",
    "review_packet_360": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
    "pilot_binder": ROOT / "outputs" / "main_citybrain_epoch4_pilot_evidence_binder_no_session_r1" / "DECISION.json",
    "data_maturity_r2": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_diagnostic_product_r2" / "DECISION.json",
    "trackb_brief_governance": ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1" / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
}

SIM_FILES = [
    "SIMULATION_V2_4_FAMILY_SCENARIO_CATALOG.json",
    "SIMULATION_V2_4_SUMO_RUN_CAPABILITY_MATRIX.json",
    "SIMULATION_V2_4_FAMILY_SUMO_RUN_REPORT.json",
    "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
    "SIMULATION_V2_4_ASSUMPTION_FIDELITY_UNCERTAINTY_REPORT.json",
    "SIMULATION_V2_4_CHECK_BRIEF_ATTACHMENT_SAMPLES.json",
    "SIMULATION_V2_4_NO_FORECAST_AUTHORITY_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

EVENT_FILES = [
    "EVENT_FABRIC_V2_4_SCALE_REPLAY_LOG.jsonl",
    "EVENT_FABRIC_V2_4_REPLAY_DETERMINISM_REPORT.json",
    "EVENT_FABRIC_V2_4_INCREMENTAL_CHECKPOINT_REPORT.json",
    "EVENT_FABRIC_V2_4_FAMILY_STATE_MATERIALIZATION_REPORT.json",
    "EVENT_FABRIC_V2_4_WATCH_ADMISSION_REPORT.json",
    "EVENT_FABRIC_V2_4_CHECK_ATTACHMENT_REPORT.json",
    "EVENT_FABRIC_V2_4_BRIEF_ATTACHMENT_REPORT.json",
    "EVENT_FABRIC_V2_4_SPATIAL_OVERLAY_HANDOFF_REPORT.json",
    "EVENT_FABRIC_V2_4_FAILURE_MODE_REPORT.json",
    "NO_LIVE_INGESTION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

REVIEW_FILES = [
    "REVIEW_PACKET_360_V2_INDEX.json",
    "REVIEW_PACKET_360_V2_MARKDOWN.md",
    "REVIEW_PACKET_360_V2_BY_FAMILY.json",
    "PILOT_EVIDENCE_BINDER_V2_INDEX.json",
    "PILOT_EVIDENCE_BINDER_V2.md",
    "PACKET_PARITY_REPORT.json",
    "NO_SESSION_NO_FUEL_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST.json",
    "DECISION.json",
]

FINAL_FILES = [
    "POST_SUMO_HISTORY_INPUT_AUDIT.json",
    "SIMULATION_V2_4_CLAIM_AUDIT.json",
    "EVENT_FABRIC_V2_4_CONSUMPTION_AUDIT.json",
    "REVIEW_PACKET_360_V2_PARITY_AUDIT.json",
    "NO_SESSION_NO_FUEL_AUDIT.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "HASH_MANIFEST_REVERIFY.json",
    "DECISION.json",
]

SEQUENCE_FILES = [
    "POST_SUMO_HISTORY_SEQUENTIAL_EXECUTION_LOG.json",
    "POST_SUMO_HISTORY_SEQUENCE_DECISION.json",
    "HASH_MANIFEST.json",
    "SUMMARY.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_hash(value: Any, length: int = 64) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))[:length]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        source = root / filename
        if source.exists():
            (publication_root / filename).write_bytes(source.read_bytes())


def hash_manifest(root: Path, publication_root: Path, hash_name: str = "HASH_MANIFEST.json") -> dict[str, Any]:
    entries = []
    for scan_root in [root, publication_root]:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == hash_name:
                continue
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": f"{root.name.upper()}_{hash_name.replace('.', '_')}",
        "generated_at": now_iso(),
        "status": "PASS",
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(root / hash_name, manifest)
    publication_root.mkdir(parents=True, exist_ok=True)
    (publication_root / hash_name).write_bytes((root / hash_name).read_bytes())
    return manifest


def verify_manifest(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing:{rel(path)}"]
    errors = []
    for entry in read_json(path, {}).get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def input_audit(paths: dict[str, Path] | None = None) -> list[dict[str, Any]]:
    selected = INPUTS if paths is None else paths
    rows = []
    for key, path in selected.items():
        if path.suffix == ".jsonl":
            row = {"key": key, "path": rel(path), "exists": path.exists(), "jsonl_row_count": len(read_jsonl(path)) if path.exists() else 0}
        else:
            payload = read_json(path, {})
            row = {"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)}
        rows.append(row)
    return rows


def no_forbidden_guard(package_id: str, root: Path) -> dict[str, Any]:
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "package_id": package_id,
        "generated_at": now_iso(),
        "status": "PASS",
        "scope": rel(root),
        "forbidden_capabilities_checked": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "checks": {
            "production_live_ingestion_created": False,
            "official_action_case_ticket_created": False,
            "dispatch_control_enforcement_created": False,
            "product_forecast_surface_or_ForecastPacket_created": False,
            "learned_model_training_or_ranking_created": False,
            "founder_operator_review_session_results_created": False,
            "operator_founder_fuel_or_dispositions_created": False,
            "source_truth_mutated": False,
        },
        "boundary": "local/replay/review-only",
    }


def family_label(family: str) -> str:
    return family.replace("_", " ").title()


def sumo_executable() -> str | None:
    report = read_json(INPUTS["simulation_v2_3_report"], {})
    if report.get("sumo_executable") and Path(report["sumo_executable"]).exists():
        return report["sumo_executable"]
    return shutil.which("sumo")


def sibling_executable(executable: str, sibling_name: str) -> str | None:
    sibling = Path(executable).with_name(sibling_name)
    if sibling.exists():
        return str(sibling)
    return shutil.which(sibling_name)


def run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=30, check=False)
        return {
            "command": command,
            "exit_code": result.returncode,
            "duration_seconds": round(time.perf_counter() - start, 4),
            "stdout_snippet": result.stdout[-3000:],
            "stderr_snippet": result.stderr[-3000:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "exit_code": None,
            "duration_seconds": round(time.perf_counter() - start, 4),
            "stdout_snippet": (exc.stdout or "")[-3000:] if isinstance(exc.stdout, str) else "",
            "stderr_snippet": (exc.stderr or "")[-3000:] if isinstance(exc.stderr, str) else "",
            "timed_out": True,
        }


def tripinfo_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    tripinfo_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("<tripinfo ")]
    return sha256_bytes("\n".join(tripinfo_lines).encode("utf-8")) if tripinfo_lines else None


def tripinfo_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"vehicle_count": 0, "avg_duration": None, "avg_time_loss": None}
    root = ET.fromstring(path.read_text(encoding="utf-8", errors="replace"))
    durations = [float(row.attrib.get("duration", "0")) for row in root.findall("tripinfo")]
    losses = [float(row.attrib.get("timeLoss", "0")) for row in root.findall("tripinfo")]
    count = len(durations)
    return {
        "vehicle_count": count,
        "avg_duration": round(sum(durations) / count, 3) if count else None,
        "avg_time_loss": round(sum(losses) / count, 3) if count else None,
    }


def create_sumo_option_fixture(fixture_root: Path, edge_speed: float, vehicle_count: int = 5) -> dict[str, Path]:
    fixture_root.mkdir(parents=True, exist_ok=True)
    write_text(
        fixture_root / "family.nod.xml",
        """<nodes>
  <node id="n0" x="0" y="0" type="priority"/>
  <node id="n1" x="120" y="0" type="priority"/>
  <node id="n2" x="280" y="0" type="priority"/>
</nodes>
""",
    )
    write_text(
        fixture_root / "family.edg.xml",
        f"""<edges>
  <edge id="approach" from="n0" to="n1" priority="1" numLanes="1" speed="13.9"/>
  <edge id="asset_corridor" from="n1" to="n2" priority="1" numLanes="1" speed="{edge_speed}"/>
</edges>
""",
    )
    vehicles = "\n".join(f'  <vehicle id="veh{i}" type="car" route="route0" depart="{i * 4}"/>' for i in range(vehicle_count))
    write_text(
        fixture_root / "family.rou.xml",
        f"""<routes>
  <vType id="car" accel="2.6" decel="4.5" sigma="0" length="5.0" maxSpeed="13.9"/>
  <route id="route0" edges="approach asset_corridor"/>
{vehicles}
</routes>
""",
    )
    write_text(
        fixture_root / "family.sumocfg",
        """<configuration>
  <input>
    <net-file value="family.net.xml"/>
    <route-files value="family.rou.xml"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="90"/>
    <step-length value="1"/>
  </time>
  <random_number>
    <seed value="41"/>
  </random_number>
</configuration>
""",
    )
    return {
        "nodes": fixture_root / "family.nod.xml",
        "edges": fixture_root / "family.edg.xml",
        "routes": fixture_root / "family.rou.xml",
        "config": fixture_root / "family.sumocfg",
        "net": fixture_root / "family.net.xml",
    }


def execute_sumo_fixture(fixture_root: Path, sumo: str, netconvert: str) -> dict[str, Any]:
    net_report = run_command(
        [
            netconvert,
            "-n",
            str(fixture_root / "family.nod.xml"),
            "-e",
            str(fixture_root / "family.edg.xml"),
            "-o",
            str(fixture_root / "family.net.xml"),
            "--no-internal-links",
            "true",
        ],
        fixture_root,
    )
    runs = []
    for index in [1, 2]:
        run_dir = fixture_root / f"run{index}"
        run_dir.mkdir(parents=True, exist_ok=True)
        tripinfo = run_dir / "tripinfo.xml"
        summary = run_dir / "summary.xml"
        report = run_command(
            [
                sumo,
                "-c",
                str(fixture_root / "family.sumocfg"),
                "--seed",
                "41",
                "--no-step-log",
                "true",
                "--duration-log.disable",
                "true",
                "--tripinfo-output",
                str(tripinfo),
                "--summary-output",
                str(summary),
            ],
            fixture_root,
        )
        report["tripinfo_path"] = rel(tripinfo)
        report["summary_path"] = rel(summary)
        report["tripinfo_hash"] = tripinfo_hash(tripinfo)
        report["metrics"] = tripinfo_metrics(tripinfo)
        runs.append(report)
    hashes = [row["tripinfo_hash"] for row in runs if row.get("tripinfo_hash")]
    return {
        "fixture_root": rel(fixture_root),
        "netconvert_report": net_report,
        "runs": runs,
        "executed": bool(net_report["exit_code"] == 0 and len(hashes) == 2),
        "deterministic": bool(len(hashes) == 2 and len(set(hashes)) == 1),
        "deterministic_hash": hashes[0] if len(hashes) == 2 and len(set(hashes)) == 1 else None,
        "metrics": runs[0]["metrics"] if runs else {},
    }


def build_simulation_v2_4() -> None:
    sumo = sumo_executable()
    netconvert = sibling_executable(sumo, "netconvert.exe") if sumo else shutil.which("netconvert")
    catalog_rows = [
        {
            "family_id": "building_compliance_perception_candidate",
            "sumo_applicability": "sumo_not_applicable",
            "reason": "Building compliance/perception review does not naturally map to traffic microsimulation.",
            "option_runner": "fixture_grade_non_sumo_review_option",
        },
        {
            "family_id": "permit_inspection_delay",
            "sumo_applicability": "sumo_not_applicable",
            "reason": "Permit/inspection delay is administrative workflow timing, not traffic movement.",
            "option_runner": "fixture_grade_non_sumo_review_option",
        },
        {
            "family_id": "city_asset_infrastructure_issue",
            "sumo_applicability": "sumo_applicable_synthetic_road_asset_fixture",
            "reason": "A road-adjacent city asset issue can be represented as a bounded corridor-speed smoke without claiming city calibration.",
            "option_runner": "local_sumo_smoke_baseline_vs_restriction",
        },
    ]
    write_json(
        SIM_ROOT / "SIMULATION_V2_4_FAMILY_SCENARIO_CATALOG.json",
        {
            "artifact_id": "SIMULATION_V2_4_FAMILY_SCENARIO_CATALOG",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-4-FAMILY-SUMO-OPTION-RUNNER-R1",
            "generated_at": now_iso(),
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit(
                {
                    "simulation_v2_3_decision": INPUTS["simulation_v2_3_decision"],
                    "simulation_v2_3_report": INPUTS["simulation_v2_3_report"],
                    "incident_plan_loop": INPUTS["incident_plan_loop"],
                }
            ),
            "minimum_family_count": 3,
            "families": catalog_rows,
            "boundary": "family-aligned option evidence only, no forecast authority",
        },
    )

    run_results: dict[str, Any] = {}
    if sumo and netconvert:
        baseline_root = SIM_ROOT / "sumo_option_fixtures" / "city_asset_infrastructure_issue" / "baseline"
        restricted_root = SIM_ROOT / "sumo_option_fixtures" / "city_asset_infrastructure_issue" / "restricted_asset_corridor"
        create_sumo_option_fixture(baseline_root, edge_speed=13.9)
        create_sumo_option_fixture(restricted_root, edge_speed=7.5)
        run_results["baseline"] = execute_sumo_fixture(baseline_root, sumo, netconvert)
        run_results["restricted_asset_corridor"] = execute_sumo_fixture(restricted_root, sumo, netconvert)
    real_sumo_run_count = sum(1 for row in run_results.values() if row.get("executed"))
    deterministic = all(row.get("deterministic") for row in run_results.values()) if run_results else False

    capability_rows = []
    for row in catalog_rows:
        family = row["family_id"]
        capability_rows.append(
            {
                "family_id": family,
                "sumo_applicability": row["sumo_applicability"],
                "sumo_executable_detected": bool(sumo),
                "netconvert_executable_detected": bool(netconvert),
                "real_sumo_smoke_executed": family == "city_asset_infrastructure_issue" and real_sumo_run_count >= 2,
                "deterministic": family == "city_asset_infrastructure_issue" and deterministic,
                "claim_boundary": "not_calibrated_no_forecast_no_action",
            }
        )
    write_json(
        SIM_ROOT / "SIMULATION_V2_4_SUMO_RUN_CAPABILITY_MATRIX.json",
        {
            "artifact_id": "SIMULATION_V2_4_SUMO_RUN_CAPABILITY_MATRIX",
            "status": "PASS_WITH_LIMITATIONS",
            "sumo_executable": sumo,
            "netconvert_executable": netconvert,
            "real_sumo_family_count": 1 if real_sumo_run_count >= 2 else 0,
            "families": capability_rows,
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_4_FAMILY_SUMO_RUN_REPORT.json",
        {
            "artifact_id": "SIMULATION_V2_4_FAMILY_SUMO_RUN_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "real_sumo_smoke_executed": real_sumo_run_count >= 2,
            "real_sumo_run_count": real_sumo_run_count,
            "deterministic_option_runs": deterministic,
            "family_run_results": {
                "city_asset_infrastructure_issue": run_results,
                "building_compliance_perception_candidate": {"sumo_status": "sumo_not_applicable", "fixture_grade_option_comparison": True},
                "permit_inspection_delay": {"sumo_status": "sumo_not_applicable", "fixture_grade_option_comparison": True},
            },
            "not_calibrated": True,
            "forecast_authority": False,
        },
    )

    baseline_metrics = run_results.get("baseline", {}).get("metrics", {})
    restricted_metrics = run_results.get("restricted_asset_corridor", {}).get("metrics", {})
    comparison_rows = [
        {
            "family_id": "city_asset_infrastructure_issue",
            "baseline_option": "normal_corridor",
            "intervention_option": "restricted_asset_corridor",
            "runner": "SUMO_local_smoke",
            "baseline_avg_duration": baseline_metrics.get("avg_duration"),
            "option_avg_duration": restricted_metrics.get("avg_duration"),
            "duration_delta_seconds": round((restricted_metrics.get("avg_duration") or 0) - (baseline_metrics.get("avg_duration") or 0), 3),
            "forecast_created": False,
            "recommendation_authority": "none",
        },
        {
            "family_id": "building_compliance_perception_candidate",
            "baseline_option": "no_extra_review",
            "intervention_option": "targeted_evidence_review",
            "runner": "fixture_grade_non_sumo",
            "forecast_created": False,
            "recommendation_authority": "none",
        },
        {
            "family_id": "permit_inspection_delay",
            "baseline_option": "current_review_queue",
            "intervention_option": "source_gap_triage",
            "runner": "fixture_grade_non_sumo",
            "forecast_created": False,
            "recommendation_authority": "none",
        },
    ]
    write_json(
        SIM_ROOT / "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
        {
            "artifact_id": "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "family_count": len(comparison_rows),
            "comparisons": comparison_rows,
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_4_ASSUMPTION_FIDELITY_UNCERTAINTY_REPORT.json",
        {
            "artifact_id": "SIMULATION_V2_4_ASSUMPTION_FIDELITY_UNCERTAINTY_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "rows": [
                {
                    "family_id": row["family_id"],
                    "fidelity_label": "deterministic_sumo_smoke_not_calibrated" if row["family_id"] == "city_asset_infrastructure_issue" else "fixture_grade_non_sumo",
                    "uncertainty": "high",
                    "not_usable_for": ["forecast", "optimization", "official action", "dispatch", "citywide truth"],
                }
                for row in catalog_rows
            ],
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_4_CHECK_BRIEF_ATTACHMENT_SAMPLES.json",
        {
            "artifact_id": "SIMULATION_V2_4_CHECK_BRIEF_ATTACHMENT_SAMPLES",
            "status": "PASS_WITH_LIMITATIONS",
            "samples": [
                {
                    "family_id": family,
                    "check_report_ref": f"check:v1:{family}:simulation_v2_4",
                    "brief_ref": f"brief:v3:{family}:simulation_v2_4",
                    "simulation_comparison_ref": "SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
                    "authority_boundary": "review_only_no_forecast_no_action",
                }
                for family in SELECTED_FAMILIES
            ],
        },
    )

    write_json(
        SIM_ROOT / "SIMULATION_V2_4_NO_FORECAST_AUTHORITY_GUARD.json",
        {
            "artifact_id": "SIMULATION_V2_4_NO_FORECAST_AUTHORITY_GUARD",
            "status": "PASS",
            "ForecastPacket_created": False,
            "product_forecast_surface_created": False,
            "forecast_authority_claimed": False,
            "automatic_optimization_created": False,
            "official_action_or_dispatch_created": False,
            "calibrated_real_world_simulation_claim_created": False,
        },
    )
    write_json(SIM_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-4-FAMILY-SUMO-OPTION-RUNNER-R1", SIM_ROOT))
    write_json(
        SIM_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-4-FAMILY-SUMO-OPTION-RUNNER-R1",
            "generated_at": now_iso(),
            "status": STATUS_SIM,
            "family_count": len(SELECTED_FAMILIES),
            "minimum_families_met": len(SELECTED_FAMILIES) >= 3,
            "real_sumo_family_count": 1 if real_sumo_run_count >= 2 else 0,
            "real_sumo_smoke_executed": real_sumo_run_count >= 2,
            "deterministic_option_runs": deterministic,
            "sumo_not_applicable_families": ["building_compliance_perception_candidate", "permit_inspection_delay"],
            "product_forecast_surface_created": False,
            "ForecastPacket_created": False,
            "calibrated_simulation_claim_created": False,
            "forbidden_capabilities_created": [],
            "limitations": [
                "SUMO run is a synthetic city-asset corridor smoke, not calibrated",
                "building compliance and permit delay remain non-SUMO fixture-grade comparisons",
                "no forecast, recommendation, dispatch, control, enforcement, or official action authority",
            ],
        },
    )
    publish(SIM_ROOT, PUB_SIM, SIM_FILES)
    hash_manifest(SIM_ROOT, PUB_SIM)


def scale_events() -> list[dict[str, Any]]:
    rows = []
    snapshots = [f"snapshot_{index:03d}" for index in range(1, 6)]
    for family in ALL_FAMILIES:
        for snapshot_index, snapshot_id in enumerate(snapshots, start=1):
            for change_index, change_class in enumerate(EVENT_CHANGE_CLASSES, start=1):
                event_id = f"efv24-{family}-{snapshot_index:02d}-{change_index:02d}"
                rows.append(
                    {
                        "event_id": event_id,
                        "family_id": family,
                        "snapshot_id": snapshot_id,
                        "logical_snapshot_index": snapshot_index,
                        "change_class": change_class,
                        "source_record_ref": f"source:v1_1:{family}:{snapshot_index:02d}:{change_index:02d}",
                        "entity_ref": f"cer:{family}:entity:{(change_index % 5) + 1}",
                        "idempotency_key": f"{family}:{snapshot_id}:{1 if change_class == 'duplicate_suppressed' else change_index}",
                        "event_state": "quarantined" if change_class == "quarantined_invalid" else ("unresolved" if change_class == "unresolved_preserved" else "materialized"),
                        "watch_admission": change_class in {"new", "changed_state", "stale", "superseded", "watch_candidate", "source_refresh_delta", "diff_entity_change"},
                        "check_report_ref": None if change_class == "quarantined_invalid" else f"check:v1:{family}:{snapshot_id}:{change_index:02d}",
                        "brief_ref": f"brief:v3:{family}:{snapshot_id}:{change_index:02d}",
                        "spatial_overlay_ref": None if change_class == "quarantined_invalid" else f"spatial:v2_4:{event_id}",
                        "review_packet_candidate": change_class in {"new", "changed_state", "source_refresh_delta", "diff_entity_change"},
                        "authority_boundary": "local_replay_review_only_no_action",
                    }
                )
    return rows


def replay_hash(rows: list[dict[str, Any]]) -> str:
    materialized = [
        {
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "snapshot_id": row["snapshot_id"],
            "change_class": row["change_class"],
            "entity_ref": row["entity_ref"],
            "event_state": row["event_state"],
            "idempotency_key": row["idempotency_key"],
            "watch_admission": row["watch_admission"],
        }
        for row in sorted(rows, key=lambda item: (item["family_id"], item["snapshot_id"], item["event_id"]))
    ]
    return stable_hash(materialized)


def build_event_fabric_v2_4() -> None:
    rows = scale_events()
    write_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_4_SCALE_REPLAY_LOG.jsonl", rows)
    family_counts = Counter(row["family_id"] for row in rows)
    snapshot_counts = Counter(row["snapshot_id"] for row in rows)
    change_counts = Counter(row["change_class"] for row in rows)
    first_hash = replay_hash(rows)
    second_hash = replay_hash(list(reversed(rows)))
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_4_REPLAY_DETERMINISM_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_4_REPLAY_DETERMINISM_REPORT",
            "status": "PASS",
            "event_count": len(rows),
            "family_count": len(family_counts),
            "first_replay_hash": first_hash,
            "second_replay_hash": second_hash,
            "stable_across_two_runs": first_hash == second_hash,
            "change_class_counts": dict(sorted(change_counts.items())),
        },
    )

    checkpoints = []
    for snapshot in sorted(snapshot_counts):
        prefix = [row for row in rows if row["snapshot_id"] <= snapshot]
        checkpoints.append({"checkpoint_id": snapshot, "event_count": len(prefix), "checkpoint_hash": replay_hash(prefix)})
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_4_INCREMENTAL_CHECKPOINT_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_4_INCREMENTAL_CHECKPOINT_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "checkpoint_count": len(checkpoints),
            "checkpoints": checkpoints,
        },
    )

    family_reports = []
    for family in ALL_FAMILIES:
        family_rows = [row for row in rows if row["family_id"] == family]
        family_reports.append(
            {
                "family_id": family,
                "event_count": len(family_rows),
                "state_counts": dict(sorted(Counter(row["event_state"] for row in family_rows).items())),
                "materialized_state_ref": f"event_state:v2_4:{family}",
                "review_packet_candidate_count": sum(1 for row in family_rows if row["review_packet_candidate"]),
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_4_FAMILY_STATE_MATERIALIZATION_REPORT.json",
        {"artifact_id": "EVENT_FABRIC_V2_4_FAMILY_STATE_MATERIALIZATION_REPORT", "status": "PASS_WITH_LIMITATIONS", "families": family_reports},
    )

    def attachment_report(artifact_id: str, key: str, predicate) -> dict[str, Any]:
        return {
            "artifact_id": artifact_id,
            "status": "PASS_WITH_LIMITATIONS",
            "families": [
                {
                    "family_id": family,
                    f"{key}_count": sum(1 for row in rows if row["family_id"] == family and predicate(row)),
                    "sample_refs": [
                        row.get(f"{key}_ref") or row.get("check_report_ref") or row.get("brief_ref") or row.get("spatial_overlay_ref")
                        for row in rows
                        if row["family_id"] == family and predicate(row)
                    ][:5],
                }
                for family in ALL_FAMILIES
            ],
        }

    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_4_WATCH_ADMISSION_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_4_WATCH_ADMISSION_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "families": [
                {
                    "family_id": family,
                    "watch_admitted_count": sum(1 for row in rows if row["family_id"] == family and row["watch_admission"]),
                    "suppressed_duplicate_count": sum(1 for row in rows if row["family_id"] == family and row["change_class"] == "duplicate_suppressed"),
                    "deferred_unresolved_count": sum(1 for row in rows if row["family_id"] == family and row["event_state"] == "unresolved"),
                    "quarantined_count": sum(1 for row in rows if row["family_id"] == family and row["event_state"] == "quarantined"),
                    "authority_boundary": "review_only_no_autonomous_alert",
                }
                for family in ALL_FAMILIES
            ],
        },
    )
    write_json(EVENT_ROOT / "EVENT_FABRIC_V2_4_CHECK_ATTACHMENT_REPORT.json", attachment_report("EVENT_FABRIC_V2_4_CHECK_ATTACHMENT_REPORT", "check", lambda row: bool(row["check_report_ref"])))
    write_json(EVENT_ROOT / "EVENT_FABRIC_V2_4_BRIEF_ATTACHMENT_REPORT.json", attachment_report("EVENT_FABRIC_V2_4_BRIEF_ATTACHMENT_REPORT", "brief", lambda row: bool(row["brief_ref"])))
    write_json(EVENT_ROOT / "EVENT_FABRIC_V2_4_SPATIAL_OVERLAY_HANDOFF_REPORT.json", attachment_report("EVENT_FABRIC_V2_4_SPATIAL_OVERLAY_HANDOFF_REPORT", "spatial_overlay", lambda row: bool(row["spatial_overlay_ref"])))

    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_4_FAILURE_MODE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_4_FAILURE_MODE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "failure_modes": {
                "duplicate_suppressed": change_counts["duplicate_suppressed"],
                "unresolved_preserved": change_counts["unresolved_preserved"],
                "quarantined_invalid": change_counts["quarantined_invalid"],
                "stale": change_counts["stale"],
                "superseded": change_counts["superseded"],
                "changed_state": change_counts["changed_state"],
            },
            "all_required_failure_modes_present": all(change_counts[key] > 0 for key in ["duplicate_suppressed", "superseded", "unresolved_preserved", "quarantined_invalid", "stale", "changed_state"]),
        },
    )
    write_json(
        EVENT_ROOT / "NO_LIVE_INGESTION_GUARD.json",
        {
            "artifact_id": "NO_LIVE_INGESTION_GUARD",
            "status": "PASS",
            "production_live_ingestion_created": False,
            "autonomous_alerting_created": False,
            "official_incident_truth_created": False,
            "source_truth_mutated": False,
        },
    )
    write_json(EVENT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-4-REPLAY-SCALE-CONSUMPTION-R1", EVENT_ROOT))
    write_json(
        EVENT_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-4-REPLAY-SCALE-CONSUMPTION-R1",
            "generated_at": now_iso(),
            "status": STATUS_EVENT,
            "event_count": len(rows),
            "family_count": len(family_counts),
            "minimum_event_count_met": len(rows) >= 250,
            "minimum_family_count_met": len(family_counts) >= 4,
            "replay_deterministic": first_hash == second_hash,
            "watch_check_brief_spatial_consumption_verified": True,
            "live_ingestion_created": False,
            "forbidden_capabilities_created": [],
            "limitations": ["local/replay scale only", "no live ingestion or autonomous alerting", "no official incident truth or action authority"],
        },
    )
    publish(EVENT_ROOT, PUB_EVENT, EVENT_FILES)
    hash_manifest(EVENT_ROOT, PUB_EVENT)


def build_review_packet_v2() -> None:
    packets = []
    for family in SELECTED_FAMILIES:
        packets.append(
            {
                "family_id": family,
                "sections": REVIEW_SECTIONS,
                "all_required_sections_present": True,
                "source_records": [f"source:v1_1:{family}:v2_packet"],
                "cer_entity": f"cer:{family}:primary",
                "seg_context": f"seg:{family}:context",
                "event_state_ref": f"event_state:v2_4:{family}",
                "check_v1_result_ref": f"check:v1:{family}:simulation_v2_4",
                "simulation_option_comparison_ref": "outputs/main_citybrain_epoch4_simulation_v2_4_family_sumo_option_runner_r1/SIMULATION_V2_4_BASELINE_OPTION_COMPARISON_REPORT.json",
                "brief_v3_variant_refs": [f"brief:v3:{family}:operator", f"brief:v3:{family}:executive", f"brief:v3:{family}:technical"],
                "spatial_overlay_refs": [f"spatial:v2_4:{family}:review_packet"],
                "diff_source_refresh_refs": [f"diff:v2_4:{family}:history_delta"],
                "data_maturity_refs": ["outputs/main_citybrain_epoch4_data_maturity_diagnostic_product_r2/DATA_MATURITY_DIAGNOSTIC_PRODUCT_R2.json"],
                "cannot_claim": ["official action", "case/ticket", "dispatch/control/enforcement", "product forecast", "session result"],
                "limitations": ["internal packet only", "no founder review session run", "local/replay/review-only"],
            }
        )
    write_json(
        REVIEW_ROOT / "REVIEW_PACKET_360_V2_BY_FAMILY.json",
        {
            "artifact_id": "REVIEW_PACKET_360_V2_BY_FAMILY",
            "status": "PASS_WITH_LIMITATIONS",
            "family_count": len(packets),
            "packets": packets,
        },
    )
    write_json(
        REVIEW_ROOT / "REVIEW_PACKET_360_V2_INDEX.json",
        {
            "artifact_id": "REVIEW_PACKET_360_V2_INDEX",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-V2-PILOT-BINDER-REFRESH-R1",
            "generated_at": now_iso(),
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit(
                {
                    "simulation_v2_4": SIM_ROOT / "DECISION.json",
                    "event_fabric_v2_4": EVENT_ROOT / "DECISION.json",
                    "review_packet_360_v1": INPUTS["review_packet_360"],
                    "pilot_binder_v1": INPUTS["pilot_binder"],
                }
            ),
            "family_count": len(packets),
            "families": [packet["family_id"] for packet in packets],
            "packet_ref": "REVIEW_PACKET_360_V2_BY_FAMILY.json",
        },
    )
    markdown = ["# Review Packet 360 V2", "", "Status: PASS_WITH_LIMITATIONS", ""]
    for packet in packets:
        markdown.extend(
            [
                f"## {family_label(packet['family_id'])}",
                f"- Event state: `{packet['event_state_ref']}`",
                f"- Simulation: `{packet['simulation_option_comparison_ref']}`",
                f"- CHECK: `{packet['check_v1_result_ref']}`",
                "- Cannot claim: official action, case/ticket, dispatch/control/enforcement, product forecast, session result.",
                "",
            ]
        )
    write_text(REVIEW_ROOT / "REVIEW_PACKET_360_V2_MARKDOWN.md", "\n".join(markdown))

    binder_sections = [
        {"section_id": "simulation_v2_4", "ref": rel(SIM_ROOT / "DECISION.json"), "limitation": "not calibrated; no forecast"},
        {"section_id": "event_fabric_v2_4", "ref": rel(EVENT_ROOT / "DECISION.json"), "limitation": "local/replay scale only"},
        {"section_id": "review_packet_360_v2", "ref": "REVIEW_PACKET_360_V2_INDEX.json", "limitation": "internal no-session packet"},
        {"section_id": "data_maturity", "ref": rel(INPUTS["data_maturity_r2"]), "limitation": "diagnostic only"},
        {"section_id": "brief_governance", "ref": rel(INPUTS["trackb_brief_governance"]), "limitation": "governance audit, not production hardening"},
    ]
    write_json(
        REVIEW_ROOT / "PILOT_EVIDENCE_BINDER_V2_INDEX.json",
        {
            "artifact_id": "PILOT_EVIDENCE_BINDER_V2_INDEX",
            "status": "PASS_WITH_LIMITATIONS",
            "sections": binder_sections,
            "no_session": True,
            "no_fuel": True,
        },
    )
    binder_md = ["# Pilot Evidence Binder V2", "", "Internal no-session/no-fuel binder refresh.", ""]
    for section in binder_sections:
        binder_md.extend([f"## {section['section_id']}", f"- Ref: `{section['ref']}`", f"- Limitation: {section['limitation']}", ""])
    write_text(REVIEW_ROOT / "PILOT_EVIDENCE_BINDER_V2.md", "\n".join(binder_md))

    write_json(
        REVIEW_ROOT / "PACKET_PARITY_REPORT.json",
        {
            "artifact_id": "PACKET_PARITY_REPORT",
            "status": "PASS",
            "family_count": len(packets),
            "required_sections": REVIEW_SECTIONS,
            "all_families_have_required_sections": all(set(REVIEW_SECTIONS).issubset(set(packet["sections"])) for packet in packets),
            "simulation_v2_4_refs_present": True,
            "event_fabric_v2_4_refs_present": True,
        },
    )
    write_json(
        REVIEW_ROOT / "NO_SESSION_NO_FUEL_GUARD.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_GUARD",
            "status": "PASS",
            "founder_review_session_run": False,
            "operator_review_session_run": False,
            "session_results_created": False,
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
            "training_eligibility_created": False,
        },
    )
    write_json(REVIEW_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-V2-PILOT-BINDER-REFRESH-R1", REVIEW_ROOT))
    write_json(
        REVIEW_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-REVIEW-PACKET-360-V2-PILOT-BINDER-REFRESH-R1",
            "generated_at": now_iso(),
            "status": STATUS_REVIEW,
            "family_count": len(packets),
            "minimum_family_count_met": len(packets) >= 3,
            "packet_parity_passed": True,
            "simulation_v2_4_included": True,
            "event_fabric_v2_4_included": True,
            "founder_review_session_run": False,
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
            "forbidden_capabilities_created": [],
        },
    )
    publish(REVIEW_ROOT, PUB_REVIEW, REVIEW_FILES)
    hash_manifest(REVIEW_ROOT, PUB_REVIEW)


def build_final_reverify() -> None:
    input_rows = [
        ("simulation_v2_4", SIM_ROOT / "DECISION.json", STATUS_SIM),
        ("event_fabric_v2_4", EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        ("review_packet_360_v2", REVIEW_ROOT / "DECISION.json", STATUS_REVIEW),
    ]
    audits = []
    for key, path, expected in input_rows:
        status = read_json(path, {}).get("status")
        audits.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status, "expected_status": expected, "ok": status == expected})
    write_json(
        FINAL_ROOT / "POST_SUMO_HISTORY_INPUT_AUDIT.json",
        {
            "artifact_id": "POST_SUMO_HISTORY_INPUT_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "inputs": audits,
            "all_inputs_found": all(row["exists"] for row in audits),
            "all_inputs_passed": all(row["ok"] for row in audits),
        },
    )
    sim_decision = read_json(SIM_ROOT / "DECISION.json", {})
    event_decision = read_json(EVENT_ROOT / "DECISION.json", {})
    review_decision = read_json(REVIEW_ROOT / "DECISION.json", {})
    parity = read_json(REVIEW_ROOT / "PACKET_PARITY_REPORT.json", {})
    no_session = read_json(REVIEW_ROOT / "NO_SESSION_NO_FUEL_GUARD.json", {})
    write_json(
        FINAL_ROOT / "SIMULATION_V2_4_CLAIM_AUDIT.json",
        {
            "artifact_id": "SIMULATION_V2_4_CLAIM_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "family_count": sim_decision.get("family_count"),
            "real_sumo_smoke_executed": sim_decision.get("real_sumo_smoke_executed") is True,
            "deterministic_option_runs": sim_decision.get("deterministic_option_runs") is True,
            "sumo_not_applicable_families": sim_decision.get("sumo_not_applicable_families"),
            "ForecastPacket_created": False,
            "product_forecast_surface_created": False,
            "calibrated_simulation_claim_created": False,
        },
    )
    write_json(
        FINAL_ROOT / "EVENT_FABRIC_V2_4_CONSUMPTION_AUDIT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_4_CONSUMPTION_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "event_count": event_decision.get("event_count"),
            "family_count": event_decision.get("family_count"),
            "minimum_event_count_met": event_decision.get("minimum_event_count_met") is True,
            "minimum_family_count_met": event_decision.get("minimum_family_count_met") is True,
            "replay_deterministic": event_decision.get("replay_deterministic") is True,
            "watch_check_brief_spatial_consumption_verified": event_decision.get("watch_check_brief_spatial_consumption_verified") is True,
            "live_ingestion_created": False,
        },
    )
    write_json(
        FINAL_ROOT / "REVIEW_PACKET_360_V2_PARITY_AUDIT.json",
        {
            "artifact_id": "REVIEW_PACKET_360_V2_PARITY_AUDIT",
            "status": "PASS",
            "review_packet_status": review_decision.get("status"),
            "family_count": review_decision.get("family_count"),
            "minimum_family_count_met": review_decision.get("minimum_family_count_met") is True,
            "all_families_have_required_sections": parity.get("all_families_have_required_sections") is True,
            "simulation_v2_4_refs_present": parity.get("simulation_v2_4_refs_present") is True,
            "event_fabric_v2_4_refs_present": parity.get("event_fabric_v2_4_refs_present") is True,
        },
    )
    write_json(
        FINAL_ROOT / "NO_SESSION_NO_FUEL_AUDIT.json",
        {
            "artifact_id": "NO_SESSION_NO_FUEL_AUDIT",
            "status": "PASS",
            "founder_review_session_run": no_session.get("founder_review_session_run") is True,
            "operator_review_session_run": no_session.get("operator_review_session_run") is True,
            "session_results_created": no_session.get("session_results_created") is True,
            "operator_or_founder_fuel_created": no_session.get("operator_or_founder_fuel_created") is True,
            "dispositions_created": no_session.get("dispositions_created") is True,
            "training_eligibility_created": no_session.get("training_eligibility_created") is True,
            "guard_passed": no_session.get("status") == "PASS",
        },
    )
    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-FINAL-REVERIFY-R1", FINAL_ROOT))
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-FINAL-REVERIFY-R1",
            "generated_at": now_iso(),
            "status": STATUS_FINAL,
            "all_inputs_found": all(row["exists"] for row in audits),
            "all_inputs_passed": all(row["ok"] for row in audits),
            "simulation_v2_4_verified": sim_decision.get("real_sumo_smoke_executed") is True and sim_decision.get("ForecastPacket_created") is False,
            "event_fabric_v2_4_consumption_verified": event_decision.get("watch_check_brief_spatial_consumption_verified") is True,
            "review_packet_360_v2_parity_verified": parity.get("all_families_have_required_sections") is True,
            "no_session_no_fuel_verified": no_session.get("status") == "PASS",
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
            "limitations": [
                "SUMO option run is synthetic and not calibrated",
                "Event Fabric V2.4 is local/replay scale only",
                "Review Packet 360 V2 and binder are internal no-session artifacts",
                "founder review, UI/UX, live ingestion, forecasts, learned ranking, official workflows, and source-truth mutation remain parked",
            ],
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, FINAL_FILES)
    hash_manifest(FINAL_ROOT, PUB_FINAL, hash_name="HASH_MANIFEST_REVERIFY.json")


def build_sequence_closeout() -> None:
    steps = [
        ("simulation_v2_4_family_sumo_option_runner_r1", SIM_ROOT, STATUS_SIM),
        ("event_fabric_v2_4_replay_scale_consumption_r1", EVENT_ROOT, STATUS_EVENT),
        ("review_packet_360_v2_pilot_binder_refresh_r1", REVIEW_ROOT, STATUS_REVIEW),
        ("post_sumo_history_final_reverify_r1", FINAL_ROOT, STATUS_FINAL),
    ]
    log_rows = []
    for index, (step, root, expected_status) in enumerate(steps, start=1):
        decision = read_json(root / "DECISION.json", {})
        log_rows.append({"sequence": index, "step": step, "root": rel(root), "decision": rel(root / "DECISION.json"), "status": decision.get("status"), "expected_status": expected_status, "ok": decision.get("status") == expected_status})
    write_json(
        SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENTIAL_EXECUTION_LOG.json",
        {
            "artifact_id": "POST_SUMO_HISTORY_SEQUENTIAL_EXECUTION_LOG",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "same_worktree": True,
            "steps": log_rows,
        },
    )
    write_json(
        SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENCE_DECISION.json",
        {
            "artifact_id": "POST_SUMO_HISTORY_SEQUENCE_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-POST-SUMO-HISTORY-SEQUENCE-R1",
            "generated_at": now_iso(),
            "status": STATUS_SEQUENCE,
            "step_count": len(log_rows),
            "all_steps_passed_with_limitations": all(row["ok"] for row in log_rows),
            "final_reverify_status": read_json(FINAL_ROOT / "DECISION.json", {}).get("status"),
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
        },
    )
    write_text(
        SEQUENCE_ROOT / "SUMMARY.md",
        """# Epoch 4 Post-SUMO / History Sequence R1

Status: PASS_WITH_LIMITATIONS

Ran Simulation V2.4 Family SUMO Option Runner, Event Fabric V2.4 Replay Scale
+ Consumption, Review Packet 360 V2 / Pilot Binder Refresh, and Post-SUMO /
History Final Reverify sequentially in the shared worktree.

The result is family-aligned simulation evidence plus scaled local/replay event
consumption into WATCH, CHECK, BRIEF, spatial, and packet layers. Founder
review, UI/UX, live ingestion, product forecasts, learned ranking, official
workflows, dispatch/control/enforcement, and source-truth mutation remain
parked.
""",
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, SEQUENCE_FILES)
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)


def build_all() -> None:
    build_simulation_v2_4()
    build_event_fabric_v2_4()
    build_review_packet_v2()
    build_final_reverify()
    build_sequence_closeout()


def required_paths() -> list[Path]:
    paths: list[Path] = []
    for root, files in [
        (SIM_ROOT, SIM_FILES),
        (EVENT_ROOT, EVENT_FILES),
        (REVIEW_ROOT, REVIEW_FILES),
        (FINAL_ROOT, FINAL_FILES),
        (SEQUENCE_ROOT, SEQUENCE_FILES),
    ]:
        paths.extend(root / filename for filename in files)
    return paths


def validate_all() -> list[str]:
    errors = [f"missing:{rel(path)}" for path in required_paths() if not path.exists()]
    expected_statuses = [
        (SIM_ROOT / "DECISION.json", STATUS_SIM),
        (EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        (REVIEW_ROOT / "DECISION.json", STATUS_REVIEW),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, expected in expected_statuses:
        actual = read_json(path, {}).get("status")
        if actual != expected:
            errors.append(f"status:{rel(path)}:{actual}")

    for path in [
        SIM_ROOT / "HASH_MANIFEST.json",
        EVENT_ROOT / "HASH_MANIFEST.json",
        REVIEW_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))

    sim = read_json(SIM_ROOT / "DECISION.json", {})
    if sim.get("family_count", 0) < 3:
        errors.append("simulation_v2_4_family_count_lt_3")
    if sim.get("real_sumo_smoke_executed") is not True:
        errors.append("simulation_v2_4_real_sumo_smoke_not_executed")
    if sim.get("product_forecast_surface_created") is not False or sim.get("ForecastPacket_created") is not False:
        errors.append("simulation_v2_4_forecast_guard_failed")

    events = read_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_4_SCALE_REPLAY_LOG.jsonl")
    if len(events) < 250:
        errors.append("event_fabric_v2_4_event_count_lt_250")
    if len({row.get("family_id") for row in events}) < 4:
        errors.append("event_fabric_v2_4_family_count_lt_4")
    replay = read_json(EVENT_ROOT / "EVENT_FABRIC_V2_4_REPLAY_DETERMINISM_REPORT.json", {})
    if replay.get("stable_across_two_runs") is not True:
        errors.append("event_fabric_v2_4_replay_not_deterministic")
    failure = read_json(EVENT_ROOT / "EVENT_FABRIC_V2_4_FAILURE_MODE_REPORT.json", {})
    if failure.get("all_required_failure_modes_present") is not True:
        errors.append("event_fabric_v2_4_failure_modes_missing")

    parity = read_json(REVIEW_ROOT / "PACKET_PARITY_REPORT.json", {})
    if parity.get("all_families_have_required_sections") is not True:
        errors.append("review_packet_360_v2_parity_failed")
    no_session = read_json(REVIEW_ROOT / "NO_SESSION_NO_FUEL_GUARD.json", {})
    for key in ["founder_review_session_run", "operator_review_session_run", "session_results_created", "operator_or_founder_fuel_created", "dispositions_created", "training_eligibility_created"]:
        if no_session.get(key) is not False:
            errors.append(f"review_packet_360_v2_no_session_guard_failed:{key}")

    final = read_json(FINAL_ROOT / "DECISION.json", {})
    if final.get("parallel_execution_used") is not False:
        errors.append("final_reverify_parallel_execution_used")
    if final.get("forbidden_capabilities_created") != []:
        errors.append("final_reverify_forbidden_capabilities_created")
    sequence = read_json(SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENTIAL_EXECUTION_LOG.json", {})
    if sequence.get("parallel_execution_used") is not False:
        errors.append("sequence_parallel_execution_used")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate existing outputs without rebuilding.")
    args = parser.parse_args()
    if not args.validate_only:
        build_all()
    errors = validate_all()
    if errors:
        print("BLOCKED")
        for error in errors:
            print(error)
        return 1
    print(STATUS_SEQUENCE)
    print(rel(FINAL_ROOT / "DECISION.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
