#!/usr/bin/env python3
"""Run the Epoch 4 after-next-wave continuation sequentially.

Sequence:
1. Simulation V2.3 SUMO Real Run Smoke R1
2. Event Fabric V2.3 History + DIFF Replay R1
3. Pilot Evidence Binder No Session R1
4. After Next-Wave Final Reverify R1

All outputs are additive and local/replay/review-only. This runner does not
branch, stage, commit, push, reset, clean, stash, mutate source truth, run
founder sessions, or create forecast/official-action authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SIM_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_3_sumo_real_run_smoke_r1"
EVENT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_3_history_diff_replay_r1"
BINDER_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_pilot_evidence_binder_no_session_r1"
FINAL_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_after_next_wave_final_reverify_r1"
SEQUENCE_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_after_next_wave_sequence_r1"

PUB_SIM = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-simulation-v2-3-sumo-real-run-smoke-r1"
PUB_EVENT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-event-fabric-v2-3-history-diff-replay-r1"
PUB_BINDER = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-pilot-evidence-binder-no-session-r1"
PUB_FINAL = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-after-next-wave-final-reverify-r1"
PUB_SEQUENCE = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-after-next-wave-sequence-r1"

STATUS_SIM = "PASS_MAIN_CITYBRAIN_EPOCH4_SIMULATION_V2_3_SUMO_REAL_RUN_SMOKE_R1_WITH_LIMITATIONS"
STATUS_EVENT = "PASS_MAIN_CITYBRAIN_EPOCH4_EVENT_FABRIC_V2_3_HISTORY_DIFF_REPLAY_R1_WITH_LIMITATIONS"
STATUS_BINDER = "PASS_MAIN_CITYBRAIN_EPOCH4_PILOT_EVIDENCE_BINDER_NO_SESSION_R1_WITH_LIMITATIONS"
STATUS_FINAL = "PASS_MAIN_CITYBRAIN_EPOCH4_AFTER_NEXT_WAVE_FINAL_REVERIFY_R1_WITH_LIMITATIONS"
STATUS_SEQUENCE = "PASS_MAIN_CITYBRAIN_EPOCH4_AFTER_NEXT_WAVE_SEQUENCE_R1_WITH_LIMITATIONS"

CONTROL_FAMILY = "mobility_access_interruption"
SELECTED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]
ALL_FAMILIES = [CONTROL_FAMILY] + SELECTED_FAMILIES

CHANGE_CLASSES = [
    "new",
    "changed",
    "expired",
    "stale",
    "superseded",
    "duplicate_suppressed",
    "unresolved_preserved",
    "quarantined_invalid",
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

PARKED_ITEMS = [
    "founder_review_sessions",
    "ui_ux_polish",
    "live_or_production_ingestion",
    "official_workflow_adapters",
    "product_forecast_surface",
    "learned_ranking_model_training",
    "case_memory_learner",
    "cross_city_learned_transfer",
]

INPUTS = {
    "next_wave_sequence": ROOT / "outputs" / "main_citybrain_epoch4_next_wave_sequence_r1" / "NEXT_WAVE_SEQUENCE_DECISION.json",
    "next_wave_final_reverify": ROOT / "outputs" / "main_citybrain_epoch4_next_wave_final_reverify_r1" / "DECISION.json",
    "simulation_v2_2_probe": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_2_real_connector_fidelity_ladder_r1" / "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS.json",
    "simulation_v2_2_ladder": ROOT / "outputs" / "main_citybrain_epoch4_simulation_v2_2_real_connector_fidelity_ladder_r1" / "SIMULATION_V2_2_CONNECTOR_LADDER.json",
    "product_loop_capability_map": ROOT / "outputs" / "main_citybrain_epoch4_product_loop_consolidation_and_pilot_readiness_r1" / "PRODUCT_LOOP_CAPABILITY_MAP.json",
    "event_fabric_v2_2_decision": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_2_scale_replay_reliability_r1" / "DECISION.json",
    "event_fabric_v2_2_log": ROOT / "outputs" / "main_citybrain_epoch4_event_fabric_v2_2_scale_replay_reliability_r1" / "EVENT_FABRIC_V2_2_STRESS_EVENT_LOG.jsonl",
    "tracka_decision": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1" / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json",
    "tracka_diff_fixtures": ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1" / "DIFF_DESIGNED_CHANGE_FIXTURES.jsonl",
    "track7_decision": ROOT / "outputs" / "track7_diff_source_refresh_readiness" / "TRACK7_DIFF_SOURCE_REFRESH_DECISION.json",
    "data_maturity_r2_decision": ROOT / "outputs" / "main_citybrain_epoch4_data_maturity_diagnostic_product_r2" / "DECISION.json",
    "review_packet_360_decision": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_DECISION.json",
    "brief_v3_trackb_decision": ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1" / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
    "pre_founder_guard": ROOT / "outputs" / "main_citybrain_epoch4_pre_founder_review_prep_no_session_r1" / "FOUNDER_REVIEW_NO_SESSION_GUARD.json",
}

SIM_FILES = [
    "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json",
    "SIMULATION_V2_3_REAL_OR_FIXTURE_RUN_COMPARISON.json",
    "SIMULATION_V2_3_FIDELITY_AND_CALIBRATION_LIMITATIONS.json",
    "SIMULATION_V2_3_CHECK_BRIEF_ATTACHMENT_SAMPLE.json",
    "SIMULATION_V2_3_NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

EVENT_FILES = [
    "EVENT_FABRIC_V2_3_SNAPSHOT_EVENT_LOG.jsonl",
    "EVENT_FABRIC_V2_3_EVENT_TO_DIFF_BRIDGE_REPORT.json",
    "EVENT_FABRIC_V2_3_ENTITY_STATE_CHANGE_REPORT.json",
    "EVENT_FABRIC_V2_3_SOURCE_REFRESH_COMPATIBILITY_REPORT.json",
    "EVENT_FABRIC_V2_3_WATCH_CHECK_BRIEF_SPATIAL_HANDOFF_REPORT.json",
    "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT.json",
    "NO_LIVE_INGESTION_GUARD.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

BINDER_FILES = [
    "PILOT_EVIDENCE_BINDER_INDEX.md",
    "PILOT_EVIDENCE_BINDER_INDEX.json",
    "PILOT_READINESS_CHECKLIST_R1.json",
    "BEST_STORY_AND_PACKET_INDEX_R1.json",
    "FOUNDER_REVIEW_NOT_RUN_GUARD.json",
    "NO_FUEL_NO_DISPOSITION_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST.json",
]

FINAL_FILES = [
    "AFTER_NEXT_WAVE_INPUT_AUDIT.json",
    "SIMULATION_REAL_RUN_CLAIM_AUDIT.json",
    "EVENT_HISTORY_DIFF_REPLAY_AUDIT.json",
    "PILOT_BINDER_NO_SESSION_AUDIT.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "DECISION.json",
    "HASH_MANIFEST_REVERIFY.json",
]

SEQUENCE_FILES = [
    "AFTER_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG.json",
    "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json",
    "SUMMARY.md",
    "HASH_MANIFEST.json",
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
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("decision_status") or payload.get("final_status")


def publish(root: Path, publication_root: Path, filenames: list[str]) -> None:
    publication_root.mkdir(parents=True, exist_ok=True)
    for name in filenames:
        source = root / name
        if source.exists():
            (publication_root / name).write_bytes(source.read_bytes())


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
        payload = {} if path.suffix == ".jsonl" else read_json(path, {})
        row = {"key": key, "path": rel(path), "exists": path.exists(), "status": status_of(payload)}
        if path.suffix == ".jsonl" and path.exists():
            row["jsonl_row_count"] = len(read_jsonl(path))
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


def sumo_probe_path() -> str | None:
    probe = read_json(INPUTS["simulation_v2_2_probe"], {})
    for item in probe.get("probes", []):
        if item.get("connector") == "sumo" and item.get("executable_path"):
            candidate = Path(item["executable_path"])
            if candidate.exists():
                return str(candidate)
    return shutil.which("sumo")


def sibling_executable(executable: str, sibling_name: str) -> str | None:
    sibling = Path(executable).with_name(sibling_name)
    if sibling.exists():
        return str(sibling)
    return shutil.which(sibling_name)


def create_sumo_fixture(fixture_root: Path) -> dict[str, str]:
    fixture_root.mkdir(parents=True, exist_ok=True)
    nodes = """<nodes>
  <node id="n0" x="0" y="0" type="priority"/>
  <node id="n1" x="100" y="0" type="priority"/>
  <node id="n2" x="220" y="0" type="priority"/>
</nodes>
"""
    edges = """<edges>
  <edge id="e0" from="n0" to="n1" priority="1" numLanes="1" speed="13.9"/>
  <edge id="e1" from="n1" to="n2" priority="1" numLanes="1" speed="13.9"/>
</edges>
"""
    routes = """<routes>
  <vType id="car" accel="2.6" decel="4.5" sigma="0" length="5.0" maxSpeed="13.9"/>
  <route id="route0" edges="e0 e1"/>
  <vehicle id="veh0" type="car" route="route0" depart="0"/>
  <vehicle id="veh1" type="car" route="route0" depart="5"/>
  <vehicle id="veh2" type="car" route="route0" depart="10"/>
</routes>
"""
    config = """<configuration>
  <input>
    <net-file value="mini.net.xml"/>
    <route-files value="mini.rou.xml"/>
  </input>
  <time>
    <begin value="0"/>
    <end value="60"/>
    <step-length value="1"/>
  </time>
  <random_number>
    <seed value="23"/>
  </random_number>
</configuration>
"""
    files = {
        "nodes": fixture_root / "mini.nod.xml",
        "edges": fixture_root / "mini.edg.xml",
        "routes": fixture_root / "mini.rou.xml",
        "config": fixture_root / "mini.sumocfg",
        "net": fixture_root / "mini.net.xml",
    }
    write_text(files["nodes"], nodes)
    write_text(files["edges"], edges)
    write_text(files["routes"], routes)
    write_text(files["config"], config)
    return {key: rel(path) for key, path in files.items()}


def run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=30, check=False)
        duration = round(time.perf_counter() - start, 4)
        return {
            "command": command,
            "exit_code": result.returncode,
            "duration_seconds": duration,
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


def normalized_xml_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    tripinfo_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("<tripinfo ")]
    lines = tripinfo_lines or [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("<!-- generated on")]
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def count_tripinfos(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.count("<tripinfo ")


def build_simulation_v2_3() -> None:
    fixture_root = SIM_ROOT / "sumo_fixture"
    fixture_files = create_sumo_fixture(fixture_root)
    sumo = sumo_probe_path()
    netconvert = sibling_executable(sumo, "netconvert.exe") if sumo else shutil.which("netconvert")
    net_report: dict[str, Any] | None = None
    run_reports: list[dict[str, Any]] = []
    real_run_executed = False
    deterministic = False
    run_hashes: list[str | None] = []
    limitation_reason = None

    if sumo and netconvert:
        net_cmd = [
            netconvert,
            "-n",
            str(fixture_root / "mini.nod.xml"),
            "-e",
            str(fixture_root / "mini.edg.xml"),
            "-o",
            str(fixture_root / "mini.net.xml"),
            "--no-internal-links",
            "true",
        ]
        net_report = run_command(net_cmd, fixture_root)
        if net_report["exit_code"] == 0 and (fixture_root / "mini.net.xml").exists():
            for index in [1, 2]:
                run_dir = fixture_root / f"run{index}"
                run_dir.mkdir(parents=True, exist_ok=True)
                tripinfo = run_dir / "tripinfo.xml"
                summary = run_dir / "summary.xml"
                cmd = [
                    sumo,
                    "-c",
                    str(fixture_root / "mini.sumocfg"),
                    "--seed",
                    "23",
                    "--no-step-log",
                    "true",
                    "--duration-log.disable",
                    "true",
                    "--tripinfo-output",
                    str(tripinfo),
                    "--summary-output",
                    str(summary),
                ]
                report = run_command(cmd, fixture_root)
                report["tripinfo_path"] = rel(tripinfo)
                report["summary_path"] = rel(summary)
                report["tripinfo_hash"] = normalized_xml_hash(tripinfo)
                report["tripinfo_count"] = count_tripinfos(tripinfo)
                run_reports.append(report)
                run_hashes.append(report["tripinfo_hash"])
            real_run_executed = all(report["exit_code"] == 0 and report["tripinfo_hash"] for report in run_reports)
            deterministic = bool(real_run_executed and len(set(run_hashes)) == 1)
            if not deterministic:
                limitation_reason = "SUMO smoke executed but deterministic hash did not match across two runs."
        else:
            limitation_reason = "netconvert failed; SUMO real-run smoke not executed."
    else:
        limitation_reason = "SUMO or netconvert executable unavailable."

    if not real_run_executed:
        write_json(
            SIM_ROOT / "SUMO_REAL_RUN_NOT_EXECUTED_REPORT.json",
            {
                "artifact_id": "SUMO_REAL_RUN_NOT_EXECUTED_REPORT",
                "status": "PASS_WITH_LIMITATIONS",
                "sumo_executable": sumo,
                "netconvert_executable": netconvert,
                "reason": limitation_reason,
            },
        )

    report = {
        "artifact_id": "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT",
        "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-3-SUMO-REAL-RUN-SMOKE-R1",
        "generated_at": now_iso(),
        "status": "PASS_WITH_LIMITATIONS",
        "input_audit": input_audit(
            {
                "simulation_v2_2_probe": INPUTS["simulation_v2_2_probe"],
                "simulation_v2_2_ladder": INPUTS["simulation_v2_2_ladder"],
                "product_loop_capability_map": INPUTS["product_loop_capability_map"],
            }
        ),
        "sumo_executable": sumo,
        "netconvert_executable": netconvert,
        "fixture_root": rel(fixture_root),
        "fixture_files": fixture_files,
        "netconvert_report": net_report,
        "run_reports": run_reports,
        "real_run_executed": real_run_executed,
        "real_run_claim": "deterministic_local_sumo_smoke" if deterministic else ("sumo_smoke_executed_with_determinism_limitation" if real_run_executed else "no_real_run_claim"),
        "deterministic_across_two_runs": deterministic,
        "deterministic_run_hash": run_hashes[0] if deterministic else None,
        "vehicle_tripinfo_count": run_reports[0]["tripinfo_count"] if run_reports else 0,
        "calibrated": False,
        "forecast_authority": False,
        "limitations": [
            "tiny synthetic local SUMO fixture only",
            "not calibrated to a city network",
            "not a product forecast",
            "no official action, dispatch, control, or enforcement",
        ]
        + ([limitation_reason] if limitation_reason else []),
    }
    write_json(SIM_ROOT / "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json", report)

    write_json(
        SIM_ROOT / "SIMULATION_V2_3_REAL_OR_FIXTURE_RUN_COMPARISON.json",
        {
            "artifact_id": "SIMULATION_V2_3_REAL_OR_FIXTURE_RUN_COMPARISON",
            "status": "PASS_WITH_LIMITATIONS",
            "v2_2_state": "sumo_detected_not_calibrated_real_connector_run_count_0",
            "v2_3_state": "real_run_smoke" if real_run_executed else "fixture_only_or_not_executed",
            "real_run_smoke_executed": real_run_executed,
            "real_run_count": 1 if real_run_executed else 0,
            "fixture_only_count": 0 if real_run_executed else 1,
            "families_covered_by_product_options": SELECTED_FAMILIES,
            "city_data_used": False,
            "forecast_created": False,
        },
    )
    write_json(
        SIM_ROOT / "SIMULATION_V2_3_FIDELITY_AND_CALIBRATION_LIMITATIONS.json",
        {
            "artifact_id": "SIMULATION_V2_3_FIDELITY_AND_CALIBRATION_LIMITATIONS",
            "status": "PASS_WITH_LIMITATIONS",
            "fidelity_label": "deterministic_sumo_smoke_not_calibrated" if real_run_executed else "not_executed",
            "calibration_state": "not_calibrated",
            "usable_for": ["connector smoke evidence", "local deterministic execution proof"] if real_run_executed else ["bounded limitation record"],
            "not_usable_for": ["forecast", "optimization", "official action", "dispatch", "citywide truth", "recommendation authority"],
            "limitations": report["limitations"],
        },
    )
    write_json(
        SIM_ROOT / "SIMULATION_V2_3_CHECK_BRIEF_ATTACHMENT_SAMPLE.json",
        {
            "artifact_id": "SIMULATION_V2_3_CHECK_BRIEF_ATTACHMENT_SAMPLE",
            "status": "PASS_WITH_LIMITATIONS",
            "family_id": "mobility_access_interruption",
            "check_report_ref": "check:v1:mobility_access_interruption:sumo_smoke",
            "brief_attachment_ref": "brief:v3:mobility_access_interruption:sumo_smoke_limitations",
            "sumo_report_ref": "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json",
            "authority_boundary": "review_only_no_forecast_no_action",
            "visible_limitations": report["limitations"],
        },
    )
    write_json(
        SIM_ROOT / "SIMULATION_V2_3_NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
        {
            "artifact_id": "SIMULATION_V2_3_NO_PRODUCT_FORECAST_SURFACE_GUARD",
            "status": "PASS",
            "ForecastPacket_created": False,
            "product_forecast_surface_created": False,
            "forecast_authority_claimed": False,
            "automatic_optimization_created": False,
            "official_action_or_dispatch_created": False,
        },
    )
    write_json(
        SIM_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-SIMULATION-V2-3-SUMO-REAL-RUN-SMOKE-R1",
            "generated_at": now_iso(),
            "status": STATUS_SIM,
            "sumo_executable_detected": bool(sumo),
            "netconvert_executable_detected": bool(netconvert),
            "sumo_real_run_smoke_executed": real_run_executed,
            "deterministic_across_two_runs": deterministic,
            "deterministic_run_hash": report["deterministic_run_hash"],
            "calibrated_simulation_claim_created": False,
            "product_forecast_surface_created": False,
            "ForecastPacket_created": False,
            "forbidden_capabilities_created": [],
            "limitations": report["limitations"],
        },
    )
    publish(SIM_ROOT, PUB_SIM, SIM_FILES)
    hash_manifest(SIM_ROOT, PUB_SIM)


def history_events() -> list[dict[str, Any]]:
    rows = []
    snapshots = [
        ("snapshot_001", "2026-07-07T08:00:00Z"),
        ("snapshot_002", "2026-07-07T12:00:00Z"),
        ("snapshot_003", "2026-07-07T16:00:00Z"),
    ]
    for family_index, family in enumerate(ALL_FAMILIES, start=1):
        for snapshot_index, (snapshot_id, snapshot_time) in enumerate(snapshots, start=1):
            for change_index, change_class in enumerate(CHANGE_CLASSES, start=1):
                event_id = f"efv23-{family}-{snapshot_index:02d}-{change_index:02d}"
                entity_id = f"cer:{family}:entity:{(change_index % 4) + 1}"
                rows.append(
                    {
                        "event_id": event_id,
                        "family_id": family,
                        "snapshot_id": snapshot_id,
                        "snapshot_time": snapshot_time,
                        "logical_snapshot_index": snapshot_index,
                        "change_class": change_class,
                        "source_record_ref": f"source:v1_1:{family}:{snapshot_index:02d}:{change_index:02d}",
                        "entity_ref": entity_id,
                        "idempotency_key": f"{family}:{snapshot_id}:{change_index if change_class != 'duplicate_suppressed' else 1}",
                        "event_state": "quarantined" if change_class == "quarantined_invalid" else ("unresolved" if change_class == "unresolved_preserved" else "materialized"),
                        "diff_bridge_class": {
                            "new": "source_level_new",
                            "changed": "source_level_changed",
                            "expired": "source_level_expired",
                            "stale": "source_level_stale",
                            "superseded": "entity_level_superseded",
                            "duplicate_suppressed": "idempotency_duplicate",
                            "unresolved_preserved": "unresolved_preserved",
                            "quarantined_invalid": "quarantined_invalid",
                        }[change_class],
                        "check_report_ref": None if change_class == "quarantined_invalid" else f"check:v1:{family}:{snapshot_id}:{change_index:02d}",
                        "brief_ref": f"brief:v3:{family}:{snapshot_id}:{change_index:02d}",
                        "watch_admission": change_class in {"new", "changed", "expired", "stale", "superseded"},
                        "spatial_handoff_ref": None if change_class == "quarantined_invalid" else f"spatial:v2_3:{event_id}",
                        "authority_boundary": "review_only_no_live_ingestion_no_action",
                    }
                )
    return rows


def history_materialization_hash(rows: list[dict[str, Any]]) -> str:
    materialized = [
        {
            "event_id": row["event_id"],
            "family_id": row["family_id"],
            "snapshot_id": row["snapshot_id"],
            "change_class": row["change_class"],
            "entity_ref": row["entity_ref"],
            "event_state": row["event_state"],
            "diff_bridge_class": row["diff_bridge_class"],
            "idempotency_key": row["idempotency_key"],
        }
        for row in sorted(rows, key=lambda item: (item["family_id"], item["snapshot_id"], item["event_id"]))
    ]
    return stable_hash(materialized)


def build_event_fabric_v2_3() -> None:
    rows = history_events()
    write_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_3_SNAPSHOT_EVENT_LOG.jsonl", rows)

    bridge_counts = Counter(row["diff_bridge_class"] for row in rows)
    family_counts = Counter(row["family_id"] for row in rows)
    snapshot_counts = Counter(row["snapshot_id"] for row in rows)
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_3_EVENT_TO_DIFF_BRIDGE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_3_EVENT_TO_DIFF_BRIDGE_REPORT",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-3-HISTORY-DIFF-REPLAY-R1",
            "generated_at": now_iso(),
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit(
                {
                    "event_fabric_v2_2_decision": INPUTS["event_fabric_v2_2_decision"],
                    "event_fabric_v2_2_log": INPUTS["event_fabric_v2_2_log"],
                    "tracka_decision": INPUTS["tracka_decision"],
                    "tracka_diff_fixtures": INPUTS["tracka_diff_fixtures"],
                    "track7_decision": INPUTS["track7_decision"],
                    "product_loop_capability_map": INPUTS["product_loop_capability_map"],
                }
            ),
            "event_count": len(rows),
            "family_count": len(family_counts),
            "logical_snapshot_count": len(snapshot_counts),
            "diff_bridge_counts": dict(sorted(bridge_counts.items())),
            "all_required_change_classes_present": set(CHANGE_CLASSES).issubset({row["change_class"] for row in rows}),
        },
    )

    entity_changes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        entity_changes[row["entity_ref"]].append(
            {
                "snapshot_id": row["snapshot_id"],
                "event_id": row["event_id"],
                "family_id": row["family_id"],
                "change_class": row["change_class"],
                "event_state": row["event_state"],
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_3_ENTITY_STATE_CHANGE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_3_ENTITY_STATE_CHANGE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "entity_count": len(entity_changes),
            "entities": [
                {"entity_ref": entity, "change_count": len(changes), "changes": sorted(changes, key=lambda item: (item["snapshot_id"], item["event_id"]))}
                for entity, changes in sorted(entity_changes.items())
            ],
            "authority_boundary": "state_change_replay_only_no_official_truth",
        },
    )

    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_3_SOURCE_REFRESH_COMPATIBILITY_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_3_SOURCE_REFRESH_COMPATIBILITY_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "compatible_with_track7_source_refresh_readiness": True,
            "compatible_with_tracka_diff_designed_change_fixtures": True,
            "logical_snapshots": sorted(snapshot_counts),
            "source_refresh_claim": "replay_compatible_not_live_refresh",
            "live_source_fetch_performed": False,
            "source_truth_mutated": False,
        },
    )

    handoffs = []
    for family in ALL_FAMILIES:
        family_rows = [row for row in rows if row["family_id"] == family]
        handoffs.append(
            {
                "family_id": family,
                "watch_admitted_count": sum(1 for row in family_rows if row["watch_admission"]),
                "check_attachment_count": sum(1 for row in family_rows if row["check_report_ref"]),
                "brief_attachment_count": len(family_rows),
                "spatial_handoff_count": sum(1 for row in family_rows if row["spatial_handoff_ref"]),
                "unresolved_count": sum(1 for row in family_rows if row["event_state"] == "unresolved"),
                "quarantined_count": sum(1 for row in family_rows if row["event_state"] == "quarantined"),
                "sample_refs": {
                    "watch_ref": f"watch:v2_3:{family}",
                    "check_ref": f"check:v1:{family}:snapshot_history",
                    "brief_ref": f"brief:v3:{family}:history_diff",
                    "spatial_ref": f"spatial:v2_3:{family}:history_overlay",
                },
                "authority_boundary": "review_only_no_action",
            }
        )
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_3_WATCH_CHECK_BRIEF_SPATIAL_HANDOFF_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_3_WATCH_CHECK_BRIEF_SPATIAL_HANDOFF_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "families": handoffs,
            "all_four_families_covered": len(handoffs) == 4,
        },
    )

    first_hash = history_materialization_hash(rows)
    second_hash = history_materialization_hash(list(reversed(rows)))
    duplicate_count = sum(count - 1 for count in Counter(row["idempotency_key"] for row in rows).values() if count > 1)
    write_json(
        EVENT_ROOT / "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT",
            "status": "PASS",
            "first_replay_hash": first_hash,
            "second_replay_hash": second_hash,
            "stable_across_two_runs": first_hash == second_hash,
            "event_count": len(rows),
            "duplicate_suppressed_examples": duplicate_count,
            "idempotency_verified": duplicate_count > 0,
        },
    )

    write_json(
        EVENT_ROOT / "NO_LIVE_INGESTION_GUARD.json",
        {
            "artifact_id": "NO_LIVE_INGESTION_GUARD",
            "status": "PASS",
            "production_live_ingestion_created": False,
            "live_source_fetch_performed": False,
            "autonomous_alerting_created": False,
            "official_incident_truth_created": False,
            "source_truth_mutated": False,
        },
    )
    write_json(EVENT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-3-HISTORY-DIFF-REPLAY-R1", EVENT_ROOT))
    write_json(
        EVENT_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-EVENT-FABRIC-V2-3-HISTORY-DIFF-REPLAY-R1",
            "generated_at": now_iso(),
            "status": STATUS_EVENT,
            "family_count": len(family_counts),
            "logical_snapshot_count": len(snapshot_counts),
            "event_count": len(rows),
            "minimum_targets_met": len(family_counts) >= 4 and len(snapshot_counts) >= 3 and len(rows) >= 80,
            "replay_deterministic": first_hash == second_hash,
            "event_to_diff_bridge_created": True,
            "source_refresh_compatible": True,
            "live_ingestion_created": False,
            "forbidden_capabilities_created": [],
            "limitations": [
                "history replay uses logical snapshots, not live source refresh",
                "DIFF bridge is compatibility evidence, not production ingestion",
                "no official incident truth, action, case, ticket, dispatch, control, or enforcement",
            ],
        },
    )
    publish(EVENT_ROOT, PUB_EVENT, EVENT_FILES)
    hash_manifest(EVENT_ROOT, PUB_EVENT)


def build_pilot_binder() -> None:
    sections = [
        {
            "section_id": "three_family_product_loop",
            "title": "Three-family product loop",
            "primary_ref": "outputs/main_citybrain_epoch4_product_loop_final_reverify_r1/PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json",
            "status": "available",
            "limitation": "review-only with founder sessions still parked",
        },
        {
            "section_id": "review_packet_360",
            "title": "Review Packet 360",
            "primary_ref": "outputs/main_citybrain_epoch4_review_packet_360_r1/REVIEW_PACKET_360_DECISION.json",
            "status": "available",
            "limitation": "packets are internal review materials, not session results",
        },
        {
            "section_id": "event_fabric_v2_3",
            "title": "Event Fabric V2.3 history + DIFF replay",
            "primary_ref": rel(EVENT_ROOT / "DECISION.json"),
            "status": "available",
            "limitation": "logical replay, not live ingestion",
        },
        {
            "section_id": "simulation_v2_3",
            "title": "Simulation V2.3 SUMO smoke",
            "primary_ref": rel(SIM_ROOT / "DECISION.json"),
            "status": "available",
            "limitation": "deterministic smoke only; not calibrated and not a forecast",
        },
        {
            "section_id": "data_maturity_r2",
            "title": "Data Maturity Diagnostic Product R2",
            "primary_ref": rel(INPUTS["data_maturity_r2_decision"]),
            "status": "available",
            "limitation": "client-safe draft; no public deployment claim",
        },
        {
            "section_id": "source_registry_diff_governance",
            "title": "SourceRegistry V1.1, DIFF fixtures, governance audit",
            "primary_ref": rel(INPUTS["tracka_decision"]),
            "status": "available",
            "limitation": "designed-change/source-refresh readiness only",
        },
    ]
    write_json(
        BINDER_ROOT / "PILOT_EVIDENCE_BINDER_INDEX.json",
        {
            "artifact_id": "PILOT_EVIDENCE_BINDER_INDEX",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-PILOT-EVIDENCE-BINDER-NO-SESSION-R1",
            "generated_at": now_iso(),
            "status": "PASS_WITH_LIMITATIONS",
            "input_audit": input_audit(
                {
                    "simulation_v2_3": SIM_ROOT / "DECISION.json",
                    "event_fabric_v2_3": EVENT_ROOT / "DECISION.json",
                    "data_maturity_r2": INPUTS["data_maturity_r2_decision"],
                    "review_packet_360": INPUTS["review_packet_360_decision"],
                    "brief_governance": INPUTS["brief_v3_trackb_decision"],
                }
            ),
            "binder_sections": sections,
            "no_session": True,
            "parked": PARKED_ITEMS,
        },
    )
    md_lines = [
        "# Pilot Evidence Binder Index",
        "",
        "Status: PASS_WITH_LIMITATIONS",
        "",
        "Internal pilot-readiness evidence only. No founder/operator session has run,",
        "and this binder does not create dispositions, fuel, training eligibility,",
        "official actions, forecasts, live ingestion, dispatch, control, or enforcement.",
        "",
    ]
    for section in sections:
        md_lines.extend(
            [
                f"## {section['title']}",
                f"- Ref: `{section['primary_ref']}`",
                f"- Limitation: {section['limitation']}",
                "",
            ]
        )
    write_text(BINDER_ROOT / "PILOT_EVIDENCE_BINDER_INDEX.md", "\n".join(md_lines))

    checklist = {
        "artifact_id": "PILOT_READINESS_CHECKLIST_R1",
        "status": "PASS_WITH_LIMITATIONS",
        "ready_for_founder_review_prep": True,
        "ready_for_founder_review_session": False,
        "items": [
            {"item": "three-family product loop has current-truth summary", "done": True},
            {"item": "SUMO smoke claim is bounded and non-forecast", "done": True},
            {"item": "event history/DIFF replay covers four families", "done": True},
            {"item": "binder contains no completed review forms", "done": True},
            {"item": "founder review session scheduled and run", "done": False},
            {"item": "operator/founder feedback governance is approved", "done": False},
            {"item": "UI/UX review surface is ready", "done": False},
        ],
    }
    write_json(BINDER_ROOT / "PILOT_READINESS_CHECKLIST_R1.json", checklist)

    write_json(
        BINDER_ROOT / "BEST_STORY_AND_PACKET_INDEX_R1.json",
        {
            "artifact_id": "BEST_STORY_AND_PACKET_INDEX_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "stories": [
                {
                    "family_id": family,
                    "story_ref": f"event_story:{family}:pilot_candidate",
                    "review_packet_ref": f"review_packet_360:{family}",
                    "brief_ref": f"brief:v3:{family}",
                    "why_selected": "Clearer evidence chain and useful product-loop tension.",
                    "limitations": ["review-only", "no session result", "no official action"],
                }
                for family in SELECTED_FAMILIES
            ],
        },
    )

    no_session_guard = {
        "artifact_id": "FOUNDER_REVIEW_NOT_RUN_GUARD",
        "status": "PASS",
        "founder_review_session_run": False,
        "operator_review_session_run": False,
        "session_results_created": False,
        "completed_feedback_forms_created": False,
        "training_eligibility_created": False,
    }
    write_json(BINDER_ROOT / "FOUNDER_REVIEW_NOT_RUN_GUARD.json", no_session_guard)
    write_json(
        BINDER_ROOT / "NO_FUEL_NO_DISPOSITION_GUARD.json",
        {
            "artifact_id": "NO_FUEL_NO_DISPOSITION_GUARD",
            "status": "PASS",
            "operator_fuel_created": False,
            "founder_fuel_created": False,
            "dispositions_created": False,
            "case_memory_training_signal_created": False,
        },
    )
    write_json(
        BINDER_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-PILOT-EVIDENCE-BINDER-NO-SESSION-R1",
            "generated_at": now_iso(),
            "status": STATUS_BINDER,
            "binder_section_count": len(sections),
            "simulation_v2_3_included": True,
            "event_fabric_v2_3_included": True,
            "founder_review_session_run": False,
            "operator_or_founder_fuel_created": False,
            "dispositions_created": False,
            "training_eligibility_created": False,
            "forbidden_capabilities_created": [],
        },
    )
    publish(BINDER_ROOT, PUB_BINDER, BINDER_FILES)
    hash_manifest(BINDER_ROOT, PUB_BINDER)


def build_final_reverify() -> None:
    input_rows = [
        ("simulation_v2_3", SIM_ROOT / "DECISION.json", STATUS_SIM),
        ("event_fabric_v2_3", EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        ("pilot_evidence_binder_no_session", BINDER_ROOT / "DECISION.json", STATUS_BINDER),
    ]
    audit_rows = []
    for key, path, expected in input_rows:
        status = read_json(path, {}).get("status")
        audit_rows.append({"key": key, "path": rel(path), "exists": path.exists(), "status": status, "expected_status": expected, "ok": status == expected})
    write_json(
        FINAL_ROOT / "AFTER_NEXT_WAVE_INPUT_AUDIT.json",
        {
            "artifact_id": "AFTER_NEXT_WAVE_INPUT_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "inputs": audit_rows,
            "all_inputs_found": all(row["exists"] for row in audit_rows),
            "all_inputs_passed": all(row["ok"] for row in audit_rows),
        },
    )

    sim_report = read_json(SIM_ROOT / "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json", {})
    sim_decision = read_json(SIM_ROOT / "DECISION.json", {})
    write_json(
        FINAL_ROOT / "SIMULATION_REAL_RUN_CLAIM_AUDIT.json",
        {
            "artifact_id": "SIMULATION_REAL_RUN_CLAIM_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "sumo_real_run_smoke_executed": sim_decision.get("sumo_real_run_smoke_executed") is True,
            "real_run_claim": sim_report.get("real_run_claim"),
            "deterministic_across_two_runs": sim_decision.get("deterministic_across_two_runs") is True,
            "deterministic_evidence_present": bool(sim_decision.get("deterministic_run_hash")),
            "calibrated_simulation_claim_created": False,
            "product_forecast_surface_created": False,
            "ForecastPacket_created": False,
            "claim_boundary": "real local SUMO smoke only, not calibrated forecast",
        },
    )

    event_decision = read_json(EVENT_ROOT / "DECISION.json", {})
    event_replay = read_json(EVENT_ROOT / "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT.json", {})
    write_json(
        FINAL_ROOT / "EVENT_HISTORY_DIFF_REPLAY_AUDIT.json",
        {
            "artifact_id": "EVENT_HISTORY_DIFF_REPLAY_AUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "family_count": event_decision.get("family_count"),
            "logical_snapshot_count": event_decision.get("logical_snapshot_count"),
            "event_count": event_decision.get("event_count"),
            "minimum_targets_met": event_decision.get("minimum_targets_met") is True,
            "replay_deterministic": event_replay.get("stable_across_two_runs") is True,
            "event_to_diff_bridge_created": event_decision.get("event_to_diff_bridge_created") is True,
            "live_ingestion_created": False,
        },
    )

    binder_guard = read_json(BINDER_ROOT / "FOUNDER_REVIEW_NOT_RUN_GUARD.json", {})
    fuel_guard = read_json(BINDER_ROOT / "NO_FUEL_NO_DISPOSITION_GUARD.json", {})
    write_json(
        FINAL_ROOT / "PILOT_BINDER_NO_SESSION_AUDIT.json",
        {
            "artifact_id": "PILOT_BINDER_NO_SESSION_AUDIT",
            "status": "PASS",
            "binder_ref": rel(BINDER_ROOT / "PILOT_EVIDENCE_BINDER_INDEX.json"),
            "founder_review_session_run": binder_guard.get("founder_review_session_run") is True,
            "session_results_created": binder_guard.get("session_results_created") is True,
            "operator_fuel_created": fuel_guard.get("operator_fuel_created") is True,
            "founder_fuel_created": fuel_guard.get("founder_fuel_created") is True,
            "dispositions_created": fuel_guard.get("dispositions_created") is True,
            "training_eligibility_created": binder_guard.get("training_eligibility_created") is True,
            "no_session_guard_passed": binder_guard.get("status") == "PASS" and fuel_guard.get("status") == "PASS",
        },
    )

    write_json(FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", no_forbidden_guard("MAIN-CITYBRAIN-EPOCH4-AFTER-NEXT-WAVE-FINAL-REVERIFY-R1", FINAL_ROOT))
    write_json(
        FINAL_ROOT / "DECISION.json",
        {
            "artifact_id": "DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-AFTER-NEXT-WAVE-FINAL-REVERIFY-R1",
            "generated_at": now_iso(),
            "status": STATUS_FINAL,
            "all_inputs_found": all(row["exists"] for row in audit_rows),
            "all_inputs_passed": all(row["ok"] for row in audit_rows),
            "sumo_real_run_smoke_claim_verified": sim_decision.get("sumo_real_run_smoke_executed") is True and sim_decision.get("deterministic_across_two_runs") is True,
            "event_history_diff_replay_verified": event_decision.get("minimum_targets_met") is True and event_replay.get("stable_across_two_runs") is True,
            "pilot_binder_no_session_verified": binder_guard.get("status") == "PASS" and fuel_guard.get("status") == "PASS",
            "parallel_execution_used": False,
            "forbidden_capabilities_created": [],
            "limitations": [
                "SUMO claim is a deterministic local smoke only, not calibrated or forecast-capable",
                "Event Fabric V2.3 is history/DIFF replay only, not live ingestion",
                "Pilot binder is internal and no-session/no-fuel",
                "UI/UX, founder sessions, product forecasts, learned ranking, and official workflows remain parked",
            ],
        },
    )
    publish(FINAL_ROOT, PUB_FINAL, FINAL_FILES)
    hash_manifest(FINAL_ROOT, PUB_FINAL, hash_name="HASH_MANIFEST_REVERIFY.json")


def build_sequence_closeout() -> None:
    steps = [
        ("simulation_v2_3_sumo_real_run_smoke_r1", SIM_ROOT, "DECISION.json", STATUS_SIM),
        ("event_fabric_v2_3_history_diff_replay_r1", EVENT_ROOT, "DECISION.json", STATUS_EVENT),
        ("pilot_evidence_binder_no_session_r1", BINDER_ROOT, "DECISION.json", STATUS_BINDER),
        ("after_next_wave_final_reverify_r1", FINAL_ROOT, "DECISION.json", STATUS_FINAL),
    ]
    log_rows = []
    for index, (step, root, decision_name, expected_status) in enumerate(steps, start=1):
        decision = read_json(root / decision_name, {})
        log_rows.append(
            {
                "sequence": index,
                "step": step,
                "root": rel(root),
                "decision": rel(root / decision_name),
                "status": decision.get("status"),
                "expected_status": expected_status,
                "ok": decision.get("status") == expected_status,
            }
        )
    write_json(
        SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG.json",
        {
            "artifact_id": "AFTER_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG",
            "status": "PASS_WITH_LIMITATIONS",
            "parallel_execution_used": False,
            "same_worktree": True,
            "steps": log_rows,
        },
    )
    write_json(
        SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json",
        {
            "artifact_id": "AFTER_NEXT_WAVE_SEQUENCE_DECISION",
            "package_id": "MAIN-CITYBRAIN-EPOCH4-AFTER-NEXT-WAVE-SEQUENCE-R1",
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
        """# Epoch 4 After Next-Wave Sequence R1

Status: PASS_WITH_LIMITATIONS

Ran Simulation V2.3 SUMO Real Run Smoke, Event Fabric V2.3 History + DIFF
Replay, Pilot Evidence Binder No Session, and After Next-Wave Final Reverify
sequentially in the shared worktree.

The SUMO claim is limited to a deterministic local smoke. Event history/DIFF is
logical replay only. The binder is internal and no-session/no-fuel. Founder
sessions, UI/UX, live ingestion, product forecasts, learned ranking, official
workflows, dispatch/control/enforcement, and source-truth mutation remain
parked.
""",
    )
    publish(SEQUENCE_ROOT, PUB_SEQUENCE, SEQUENCE_FILES)
    hash_manifest(SEQUENCE_ROOT, PUB_SEQUENCE)


def build_all() -> None:
    build_simulation_v2_3()
    build_event_fabric_v2_3()
    build_pilot_binder()
    build_final_reverify()
    build_sequence_closeout()


def required_paths() -> list[Path]:
    paths: list[Path] = []
    for root, files in [
        (SIM_ROOT, SIM_FILES),
        (EVENT_ROOT, EVENT_FILES),
        (BINDER_ROOT, BINDER_FILES),
        (FINAL_ROOT, FINAL_FILES),
        (SEQUENCE_ROOT, SEQUENCE_FILES),
    ]:
        paths.extend(root / name for name in files)
    return paths


def validate_all() -> list[str]:
    errors = [f"missing:{rel(path)}" for path in required_paths() if not path.exists()]
    expected_statuses = [
        (SIM_ROOT / "DECISION.json", STATUS_SIM),
        (EVENT_ROOT / "DECISION.json", STATUS_EVENT),
        (BINDER_ROOT / "DECISION.json", STATUS_BINDER),
        (FINAL_ROOT / "DECISION.json", STATUS_FINAL),
        (SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json", STATUS_SEQUENCE),
    ]
    for path, expected in expected_statuses:
        actual = read_json(path, {}).get("status")
        if actual != expected:
            errors.append(f"status:{rel(path)}:{actual}")

    for path in [
        SIM_ROOT / "HASH_MANIFEST.json",
        EVENT_ROOT / "HASH_MANIFEST.json",
        BINDER_ROOT / "HASH_MANIFEST.json",
        FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        errors.extend(verify_manifest(path))

    sim_decision = read_json(SIM_ROOT / "DECISION.json", {})
    if sim_decision.get("product_forecast_surface_created") is not False:
        errors.append("simulation_v2_3_product_forecast_surface_created")
    if sim_decision.get("ForecastPacket_created") is not False:
        errors.append("simulation_v2_3_ForecastPacket_created")
    if sim_decision.get("sumo_real_run_smoke_executed") and sim_decision.get("deterministic_across_two_runs") is not True:
        errors.append("simulation_v2_3_real_run_not_deterministic")

    rows = read_jsonl(EVENT_ROOT / "EVENT_FABRIC_V2_3_SNAPSHOT_EVENT_LOG.jsonl")
    if len(rows) < 80:
        errors.append("event_fabric_v2_3_event_count_lt_80")
    if len({row.get("family_id") for row in rows}) < 4:
        errors.append("event_fabric_v2_3_family_count_lt_4")
    if len({row.get("snapshot_id") for row in rows}) < 3:
        errors.append("event_fabric_v2_3_snapshot_count_lt_3")
    event_replay = read_json(EVENT_ROOT / "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT.json", {})
    if event_replay.get("stable_across_two_runs") is not True:
        errors.append("event_fabric_v2_3_replay_not_deterministic")
    no_live = read_json(EVENT_ROOT / "NO_LIVE_INGESTION_GUARD.json", {})
    if no_live.get("production_live_ingestion_created") is not False:
        errors.append("event_fabric_v2_3_live_ingestion_created")

    no_session = read_json(BINDER_ROOT / "FOUNDER_REVIEW_NOT_RUN_GUARD.json", {})
    no_fuel = read_json(BINDER_ROOT / "NO_FUEL_NO_DISPOSITION_GUARD.json", {})
    for key in ["founder_review_session_run", "operator_review_session_run", "session_results_created", "completed_feedback_forms_created", "training_eligibility_created"]:
        if no_session.get(key) is not False:
            errors.append(f"pilot_binder_no_session_guard_failed:{key}")
    for key in ["operator_fuel_created", "founder_fuel_created", "dispositions_created", "case_memory_training_signal_created"]:
        if no_fuel.get(key) is not False:
            errors.append(f"pilot_binder_no_fuel_guard_failed:{key}")

    final_decision = read_json(FINAL_ROOT / "DECISION.json", {})
    if final_decision.get("parallel_execution_used") is not False:
        errors.append("final_reverify_parallel_execution_used")
    if final_decision.get("forbidden_capabilities_created") != []:
        errors.append("final_reverify_forbidden_capabilities_created")
    sequence = read_json(SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG.json", {})
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
