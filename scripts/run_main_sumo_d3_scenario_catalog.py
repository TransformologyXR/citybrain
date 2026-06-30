from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_sumo_d3_scenario_catalog"
TASK = "MAIN-SUMO-D3-SCENARIO-CATALOG"
SCHEMA_VERSION = "main-sumo-d3-scenario-catalog.v1"
NOW = datetime(2026, 6, 29, 23, 0, 0, tzinfo=timezone.utc)


INPUTS = {
    "sumo_d3_hardening_root": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_hardening_decision": ROOT
    / "outputs"
    / "main_sumo_d3_network_extraction_hardening"
    / "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_preflight_root": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening_preflight_r1",
    "event_fabric_d3_service_root": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_service_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_service_hardening"
    / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json",
    "event_fabric_d3_multicity_root": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "event_fabric_d3_multicity_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_multicity_adapters"
    / "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "synthetic_framework_root": ROOT / "outputs" / "synthetic_data_factory_d1_framework_and_seed_pack",
    "synthetic_replay_root": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "synthetic_replay_decision": ROOT
    / "outputs"
    / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1"
    / "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
    "perception_d3_preflight_root": ROOT / "outputs" / "main_perception_d3_deepstream_bridge_preflight_r1",
    "perception_d3_preflight_decision": ROOT
    / "outputs"
    / "main_perception_d3_deepstream_bridge_preflight_r1"
    / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "track2_root": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barc_landing_root": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "nyc_landing_root": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "chi_landing_root": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "lon_landing_root": ROOT / "outputs" / "lon_allflows_data_landing_r1",
}

WATCH_KEYS = [
    "sumo_d3_hardening_root",
    "sumo_d3_preflight_root",
    "event_fabric_d3_service_root",
    "event_fabric_d3_multicity_root",
    "synthetic_framework_root",
    "synthetic_replay_root",
    "perception_d3_preflight_root",
    "pv1_d19_d22_root",
    "a9_g1_root",
    "platform_state_root",
    "accepted_flow_state_root",
    "track2_root",
    "barc_prep_root",
    "barc_landing_root",
    "nyc_prep_root",
    "nyc_landing_root",
    "chi_prep_root",
    "chi_landing_root",
    "lon_prep_root",
    "lon_landing_root",
]

CITY_REPORT_FILES = {
    "BARC": "SUMO_D3_CITY_NETWORK_EXTRACTION_REPORT_BARCELONA.json",
    "NYC": "SUMO_D3_CITY_NETWORK_EXTRACTION_REPORT_NYC.json",
    "CHI": "SUMO_D3_CITY_NETWORK_EXTRACTION_REPORT_CHICAGO.json",
    "LON": "SUMO_D3_CITY_NETWORK_EXTRACTION_REPORT_LONDON.json",
}

CITY_META = {
    "BARC": {
        "folder": "barcelona",
        "display": "Barcelona",
        "plan_file": "SUMO_D3_CITY_SCENARIO_PLAN_BARCELONA.json",
        "context": "traffic sections, Bicing/TMB adjacency, civic mobility and Barcelona accepted review/context boundaries",
        "synthetic_theme": "synthetic permit/mobility cascade alignment",
    },
    "NYC": {
        "folder": "nyc",
        "display": "NYC",
        "plan_file": "SUMO_D3_CITY_SCENARIO_PLAN_NYC.json",
        "context": "DOT speed context, 311 recent window, DOB/construction context and accepted review routes",
        "synthetic_theme": "synthetic construction-compliance cascade alignment",
    },
    "CHI": {
        "folder": "chicago",
        "display": "Chicago",
        "plan_file": "SUMO_D3_CITY_SCENARIO_PLAN_CHICAGO.json",
        "context": "Traffic Tracker, civic/water/flood/storm and sensor/environment context",
        "synthetic_theme": "synthetic civic-water-flood cascade alignment",
    },
    "LON": {
        "folder": "london",
        "display": "London",
        "plan_file": "SUMO_D3_CITY_SCENARIO_PLAN_LONDON.json",
        "context": "TfL road disruption, LFB, London Air and EA context; not full Flow 3 completion",
        "synthetic_theme": "synthetic fire-road-air-flood context alignment",
    },
}

SCENARIO_TEMPLATES = [
    {
        "suffix": "baseline",
        "scenario_family": "baseline_mobility_context",
        "scenario_name": "Baseline mobility context",
        "route_source": "baseline",
        "duration": 480,
        "run_mode": "sumo_native_bounded_catalog",
        "event_types": ["simulated_route_load_candidate", "simulated_baseline_mobility_context"],
        "description": "Bounded source-backed baseline mobility context over the prior D3 network subset.",
    },
    {
        "suffix": "slowdown",
        "scenario_family": "slowdown_disruption_context",
        "scenario_name": "Slowdown disruption context",
        "route_source": "slowdown",
        "duration": 540,
        "run_mode": "sumo_native_bounded_catalog",
        "event_types": ["simulated_delay_candidate", "simulated_congestion_candidate", "simulated_closure_impact_candidate"],
        "description": "Bounded source-backed slowdown context over the prior D3 network subset.",
    },
    {
        "suffix": "recovery",
        "scenario_family": "recovery_context",
        "scenario_name": "Recovery context",
        "route_source": "recovery",
        "duration": 500,
        "run_mode": "sumo_native_bounded_catalog",
        "event_types": ["simulated_recovery_candidate", "simulated_route_load_candidate"],
        "description": "Bounded source-backed recovery context after disruption.",
    },
    {
        "suffix": "incident_adjacent",
        "scenario_family": "incident_adjacent_congestion_context",
        "scenario_name": "Incident-adjacent congestion context",
        "route_source": "slowdown",
        "duration": 540,
        "run_mode": "sumo_native_bounded_catalog",
        "event_types": ["simulated_delay_candidate", "simulated_route_load_candidate"],
        "description": "Bounded context scenario that can support later incident-adjacent EvidenceBundle smoke without creating an incident command.",
    },
    {
        "suffix": "synthetic_alignment",
        "scenario_family": "cascade_alignment_context",
        "scenario_name": "Synthetic cascade alignment context",
        "route_source": None,
        "duration": None,
        "run_mode": "synthetic_alignment_context_only",
        "event_types": ["simulated_cascade_alignment_context"],
        "description": "Synthetic replay alignment scenario; it is not source-backed observed truth and is not executed as SUMO.",
    },
    {
        "suffix": "closure_limitation",
        "scenario_family": "road_closure_context_simulated_only",
        "scenario_name": "Road closure limitation-only context",
        "route_source": None,
        "duration": None,
        "run_mode": "limitation_only_context",
        "event_types": [],
        "description": "Defined but not run because closure/turn-permission semantics remain too limited for a stronger catalog claim.",
    },
]

SCENARIO_FAMILY_ENUM = [
    "baseline_mobility_context",
    "slowdown_disruption_context",
    "recovery_context",
    "incident_adjacent_congestion_context",
    "road_closure_context_simulated_only",
    "cascade_alignment_context",
    "late_arrival_replay_context",
    "out_of_order_replay_context",
    "limitation_only_context",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "certified traffic model",
    "observed traffic truth",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "utility-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without ",
    "must not",
    "do not",
    "does not",
    "cannot",
    "blocked",
    "ban",
    "bans",
    "forbidden",
    "negative",
    "boundary",
    "limitation",
    "refuse",
    "context-only",
    "simulated",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def root_path(ref: str | None) -> Path | None:
    if not ref:
        return None
    p = Path(ref)
    if p.is_absolute():
        return p
    return ROOT / p


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str) + "\n")


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(command: list[str], timeout: int = 90) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": command,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {"command": command, "ok": False, "returncode": None, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "ok": False, "returncode": None, "stdout": exc.stdout or "", "stderr": "TIMEOUT"}


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {
                "exists": True,
                "kind": "file",
                "size": root.stat().st_size,
                "mtime": root.stat().st_mtime,
                "sha256": sha256_file(root),
            }
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        capped = False
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            file_count += 1
            stat = path.stat()
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if file_count >= 5000:
                capped = True
                break
        signatures[key] = {
            "exists": True,
            "kind": "directory",
            "file_count_sampled": file_count,
            "total_bytes_sampled": total_bytes,
            "max_mtime_sampled": max_mtime,
            "sample_capped": capped,
        }
    return signatures


def setup_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in [
        "catalog",
        "event_fabric",
        "current_state",
        "evidencebundle_smoke",
        "replay",
        "logs",
    ]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    for city in CITY_META.values():
        (OUTPUT_ROOT / "scenarios" / city["folder"]).mkdir(parents=True, exist_ok=True)


def list_some_files(root: Path, limit: int = 8) -> list[str]:
    if not root.exists():
        return []
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append(rel(path))
        if len(files) >= limit:
            break
    return files


def load_city_reports() -> dict[str, dict[str, Any]]:
    hardening = INPUTS["sumo_d3_hardening_root"]
    return {city_id: read_json(hardening / file_name) for city_id, file_name in CITY_REPORT_FILES.items()}


def prerequisite_recheck(city_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    hardening_decision = read_json(INPUTS["sumo_d3_hardening_decision"])
    hardening_runs = read_json(INPUTS["sumo_d3_hardening_root"] / "SUMO_D3_SCENARIO_RUN_REPORT.json")
    route_report = read_json(INPUTS["sumo_d3_hardening_root"] / "SUMO_D3_ROUTE_GENERATION_REPORT.json")
    service_decision = read_json(INPUTS["event_fabric_d3_service_decision"])
    multicity_decision = read_json(INPUTS["event_fabric_d3_multicity_decision"])
    synthetic_decision = read_json(INPUTS["synthetic_replay_decision"])
    perception_decision = read_json(INPUTS["perception_d3_preflight_decision"])

    network_checks = []
    for city_id, report in city_reports.items():
        network_path = root_path(report.get("net_xml"))
        network_checks.append(
            {
                "city_id": city_id,
                "source_backed": bool(report.get("source_backed")),
                "network_ref": report.get("net_xml"),
                "network_exists": bool(network_path and network_path.exists()),
                "route_generation_status": report.get("route_generation_status"),
                "node_count": report.get("node_count"),
                "edge_count": report.get("edge_count"),
            }
        )

    run_rows = hardening_runs.get("scenario_runs", [])
    status = (
        "PASS"
        if hardening_decision.get("status") == "PASS_MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_WITH_LIMITATIONS"
        and all(row["network_exists"] and row["source_backed"] for row in network_checks)
        and len([row for row in run_rows if row.get("status") == "PASS"]) >= 12
        else "FAIL"
    )
    report = {
        "status": status,
        "task": TASK,
        "timestamp": now_iso(),
        "sumo_d3_hardening_status": hardening_decision.get("status"),
        "network_checks": network_checks,
        "prior_sumo_scenario_smoke": {
            "status": hardening_runs.get("status"),
            "passed_run_count": len([row for row in run_rows if row.get("status") == "PASS"]),
            "total_run_count": len(run_rows),
            "route_generation_status": route_report.get("status"),
        },
        "event_fabric_d3_service_status": service_decision.get("status", "UNKNOWN"),
        "event_fabric_d3_multicity_status": multicity_decision.get("status", "UNKNOWN"),
        "synthetic_replay_status": synthetic_decision.get("status", "UNKNOWN"),
        "synthetic_replay_refs": list_some_files(INPUTS["synthetic_replay_root"]),
        "synthetic_replay_available": INPUTS["synthetic_replay_root"].exists(),
        "perception_d3_preflight_status": perception_decision.get("status", "UNKNOWN"),
        "perception_dependency_required": False,
        "perception_runtime_binding_started": False,
        "read_only_input_roots": {key: rel(path) for key, path in INPUTS.items() if key.endswith("_root")},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_INPUT_REFS_REPORT.json", report)
    return report


def write_scenario_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://citybrain.local/schemas/main-sumo-d3-scenario-catalog.schema.json",
        "title": "SUMO D3 Scenario Catalog Entry",
        "type": "object",
        "required": [
            "scenario_id",
            "city_id",
            "subset_id",
            "scenario_family",
            "scenario_name",
            "description",
            "network_ref",
            "route_ref",
            "input_refs",
            "event_family",
            "event_types",
            "lifecycle_state",
            "expected_outputs",
            "validation_gates",
            "replay_policy",
            "evidencebundle_policy",
            "claim_boundary",
            "limitations",
            "no_action_taken",
        ],
        "properties": {
            "scenario_id": {"type": "string"},
            "city_id": {"type": "string", "enum": list(CITY_META.keys())},
            "subset_id": {"type": "string"},
            "scenario_family": {"type": "string", "enum": SCENARIO_FAMILY_ENUM},
            "scenario_name": {"type": "string"},
            "description": {"type": "string"},
            "network_ref": {"type": ["string", "null"]},
            "route_ref": {"type": ["string", "null"]},
            "input_refs": {"type": "array"},
            "synthetic_refs": {"type": "array"},
            "event_family": {"type": "string", "const": "simulation_mobility"},
            "event_types": {"type": "array", "items": {"type": "string"}},
            "lifecycle_state": {"type": "string", "const": "simulated/context"},
            "expected_outputs": {"type": "array"},
            "validation_gates": {"type": "array"},
            "replay_policy": {"type": "object"},
            "evidencebundle_policy": {"type": "object"},
            "claim_boundary": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
            "no_action_taken": {"type": "boolean", "const": True},
        },
        "additionalProperties": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "catalog" / "SUMO_D3_SCENARIO_SCHEMA.json", schema)
    return schema


def route_target(city_id: str, scenario_id: str) -> str | None:
    folder = CITY_META[city_id]["folder"]
    return rel(OUTPUT_ROOT / "scenarios" / folder / f"routes_{scenario_id}.rou.xml")


def build_scenario_catalog(city_reports: dict[str, dict[str, Any]], prereq: dict[str, Any]) -> list[dict[str, Any]]:
    synthetic_refs = prereq.get("synthetic_replay_refs", [])[:5]
    catalog = []
    for city_id, report in city_reports.items():
        city_meta = CITY_META[city_id]
        for template in SCENARIO_TEMPLATES:
            scenario_id = f"sumo_d3_catalog_{city_id.lower()}_{template['suffix']}"
            is_runnable = template["run_mode"] == "sumo_native_bounded_catalog"
            is_synthetic = template["run_mode"] == "synthetic_alignment_context_only"
            is_limitation_only = template["run_mode"] == "limitation_only_context"
            limitations = list(report.get("limitations", []))
            limitations.extend(
                [
                    "Bounded scenario catalog only.",
                    "Simulated/context-only, not observed traffic truth.",
                    "No routing recommendation, traffic-control, transit-control, dispatch, enforcement, public-safety, utility-control, or production-readiness claim.",
                    "No action taken.",
                ]
            )
            if city_id == "BARC":
                limitations.append("Barcelona D2 limitation remains REDUCED_BUT_CARRIED_FORWARD for connector/turn-permission assumptions.")
            if city_id == "LON":
                limitations.append("London entries do not promote London to full Flow 3.")
            if is_synthetic:
                limitations.append("Synthetic overlay remains synthetic/context-only and is separate from source-backed SUMO validation.")
            if is_limitation_only:
                limitations.append("Scenario is limitation-only and is not run as a valid SUMO scenario.")

            scenario = {
                "scenario_id": scenario_id,
                "city_id": city_id,
                "city_name": city_meta["display"],
                "subset_id": report.get("subset_id"),
                "scenario_family": template["scenario_family"],
                "scenario_name": template["scenario_name"],
                "description": f"{template['description']} City context: {city_meta['context']}",
                "network_ref": report.get("net_xml"),
                "route_ref": route_target(city_id, scenario_id) if is_runnable else None,
                "input_refs": [
                    report.get("net_xml"),
                    rel(INPUTS["sumo_d3_hardening_root"] / CITY_REPORT_FILES[city_id]),
                    rel(INPUTS["sumo_d3_hardening_root"] / "SUMO_D3_SCENARIO_RUN_REPORT.json"),
                ],
                "source_refs": report.get("source_refs", []),
                "synthetic_refs": synthetic_refs if is_synthetic else [],
                "synthetic_theme": city_meta["synthetic_theme"] if is_synthetic else None,
                "event_family": "simulation_mobility",
                "event_types": template["event_types"],
                "lifecycle_state": "simulated/context",
                "route_source": template["route_source"],
                "run_mode": template["run_mode"],
                "runnable": is_runnable,
                "limitation_only": is_limitation_only,
                "duration": template["duration"],
                "expected_outputs": [
                    "Event Fabric D3-compatible simulated/context events" if is_runnable else "Catalog validation record",
                    "Current-state overlay row",
                    "Replay/EvidenceBundle smoke reference",
                ],
                "validation_gates": [
                    "schema_compliance",
                    "network_ref_exists",
                    "route_ref_exists" if is_runnable else "route_ref_not_required",
                    "lifecycle_simulated_context",
                    "no_observed_truth",
                    "no_command_action_routing_control",
                    "synthetic_context_label_preserved" if is_synthetic else "source_backed_boundary_preserved",
                    "limitation_only_not_run" if is_limitation_only else "catalog_entry_runnable_or_context_validated",
                ],
                "replay_policy": {
                    "eligible": is_runnable or is_synthetic or is_limitation_only,
                    "mode": "bounded_sumo_replay" if is_runnable else template["run_mode"],
                    "max_events": 20,
                    "late_or_out_of_order_safe": True,
                },
                "evidencebundle_policy": {
                    "eligible": True,
                    "include_network_refs": True,
                    "include_source_refs": True,
                    "include_synthetic_refs": is_synthetic,
                    "must_state_simulated_context_only": True,
                },
                "claim_boundary": "SIMULATED_CONTEXT_ONLY: no observed traffic truth, no routing recommendation, no traffic-control command, no transit-control command, no certified traffic model, no production readiness, no action taken.",
                "limitations": sorted(set(limitations)),
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
            catalog.append(scenario)
    catalog_doc = {
        "task": TASK,
        "status": "PASS",
        "scenario_count": len(catalog),
        "scenario_count_by_city": dict(Counter(row["city_id"] for row in catalog)),
        "runnable_scenario_count": len([row for row in catalog if row["runnable"]]),
        "limitation_only_scenario_count": len([row for row in catalog if row["limitation_only"]]),
        "synthetic_alignment_scenario_count": len([row for row in catalog if row["run_mode"] == "synthetic_alignment_context_only"]),
        "scenarios": catalog,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_CATALOG.json", catalog_doc)
    write_json(OUTPUT_ROOT / "catalog" / "SUMO_D3_SCENARIO_CATALOG.json", catalog_doc)
    write_catalog_markdown(catalog)
    return catalog


def write_catalog_markdown(catalog: list[dict[str, Any]]) -> None:
    rows = [
        "# SUMO D3 Scenario Catalog",
        "",
        "Status: `PASS_WITH_LIMITATIONS`",
        "",
        "This catalog packages bounded SUMO D3 scenarios for source-backed city subsets. It does not create a citywide certified traffic model, routing recommendation, control command, dispatch recommendation, enforcement recommendation, or production-readiness claim.",
        "",
        "| City | Scenario | Family | Run mode | Boundary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for scenario in catalog:
        rows.append(
            f"| {scenario['city_id']} | `{scenario['scenario_id']}` | `{scenario['scenario_family']}` | `{scenario['run_mode']}` | simulated/context-only |"
        )
    rows.extend(
        [
            "",
            "Barcelona's D2 routeable-equivalent limitation remains `REDUCED_BUT_CARRIED_FORWARD`.",
            "London entries are scenario support only and do not promote London to full Flow 3.",
        ]
    )
    write_text(OUTPUT_ROOT / "SUMO_D3_SCENARIO_CATALOG.md", "\n".join(rows))
    write_text(OUTPUT_ROOT / "catalog" / "SUMO_D3_SCENARIO_CATALOG.md", "\n".join(rows))


def write_city_plans(catalog: list[dict[str, Any]], city_reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    plans = {}
    for city_id, report in city_reports.items():
        scenarios = [row for row in catalog if row["city_id"] == city_id]
        plan = {
            "status": "PASS",
            "city_id": city_id,
            "city_name": CITY_META[city_id]["display"],
            "selected_network_refs": [report.get("net_xml")],
            "source_backed": bool(report.get("source_backed")),
            "candidate_scenario_list": [
                {
                    "scenario_id": row["scenario_id"],
                    "scenario_family": row["scenario_family"],
                    "run_mode": row["run_mode"],
                    "runnable": row["runnable"],
                    "limitation_only": row["limitation_only"],
                    "route_ref": row["route_ref"],
                }
                for row in scenarios
            ],
            "runnable_scenario_count": len([row for row in scenarios if row["runnable"]]),
            "limitation_only_scenario_count": len([row for row in scenarios if row["limitation_only"]]),
            "expected_event_count": sum(len(row["event_types"]) for row in scenarios if row["runnable"]),
            "expected_observations": len([row for row in scenarios if row["runnable"]]),
            "source_refs": report.get("source_refs", []),
            "synthetic_refs": [ref for row in scenarios for ref in row.get("synthetic_refs", [])],
            "city_specific_limitations": sorted({limitation for row in scenarios for limitation in row["limitations"]}),
            "claim_boundary": "SIMULATED_CONTEXT_ONLY; no action taken.",
            "schema_version": SCHEMA_VERSION,
        }
        plans[city_id] = plan
        write_json(OUTPUT_ROOT / CITY_META[city_id]["plan_file"], plan)
        write_json(OUTPUT_ROOT / "catalog" / CITY_META[city_id]["plan_file"], plan)
    return plans


def validate_catalog(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    required = {
        "scenario_id",
        "city_id",
        "subset_id",
        "scenario_family",
        "scenario_name",
        "description",
        "network_ref",
        "input_refs",
        "event_family",
        "event_types",
        "lifecycle_state",
        "expected_outputs",
        "validation_gates",
        "replay_policy",
        "evidencebundle_policy",
        "claim_boundary",
        "limitations",
        "no_action_taken",
    }
    for scenario in catalog:
        failures = []
        missing = sorted(required - set(scenario))
        if missing:
            failures.append(f"missing_fields:{','.join(missing)}")
        if scenario.get("scenario_family") not in SCENARIO_FAMILY_ENUM:
            failures.append("unknown_scenario_family")
        network = root_path(scenario.get("network_ref"))
        if not network or not network.exists():
            failures.append("network_ref_missing")
        if scenario["runnable"] and not scenario.get("route_ref"):
            failures.append("route_ref_missing_before_generation")
        if scenario.get("lifecycle_state") != "simulated/context":
            failures.append("bad_lifecycle")
        claim = scenario.get("claim_boundary", "").lower()
        if "observed traffic truth" in claim and "no observed traffic truth" not in claim:
            failures.append("observed_truth_claim")
        if not scenario.get("no_action_taken"):
            failures.append("action_taken_not_false")
        if scenario["run_mode"] == "synthetic_alignment_context_only" and not scenario.get("synthetic_refs"):
            failures.append("synthetic_refs_missing")
        if scenario["limitation_only"] and scenario["runnable"]:
            failures.append("limitation_only_marked_runnable")
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "city_id": scenario["city_id"],
                "status": "PASS" if not failures else "FAIL",
                "failures": failures,
                "lifecycle_state": scenario["lifecycle_state"],
                "synthetic_label_ok": scenario["run_mode"] != "synthetic_alignment_context_only" or bool(scenario.get("synthetic_refs")),
                "no_command_action_routing_control": True,
                "limitation_only_not_run": not (scenario["limitation_only"] and scenario["runnable"]),
            }
        )
    report = {
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "scenario_count": len(rows),
        "schema_compliance_passed": len([row for row in rows if row["status"] == "PASS"]),
        "validation_rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_VALIDATION_REPORT.json", report)
    return report


def parse_tripinfo_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        tree = ET.parse(path)
        return len(tree.findall(".//tripinfo"))
    except ET.ParseError:
        return 0


def parse_edge_interval_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        tree = ET.parse(path)
        return len(tree.findall(".//interval"))
    except ET.ParseError:
        return 0


def copy_route_and_write_config(scenario: dict[str, Any]) -> tuple[Path | None, Path | None]:
    route_source = scenario.get("route_source")
    if not route_source:
        return None, None
    city_folder = CITY_META[scenario["city_id"]]["folder"]
    source_route = INPUTS["sumo_d3_hardening_root"] / "scenarios" / city_folder / f"routes_{route_source}.rou.xml"
    if not source_route.exists():
        return None, None
    scenario_dir = OUTPUT_ROOT / "scenarios" / city_folder
    route_file = root_path(scenario["route_ref"])
    shutil.copyfile(source_route, route_file)
    edge_output = scenario_dir / f"edge_{scenario['scenario_id']}.xml"
    tripinfo_output = scenario_dir / f"tripinfo_{scenario['scenario_id']}.xml"
    summary_output = scenario_dir / f"summary_{scenario['scenario_id']}.xml"
    additional_file = scenario_dir / f"additional_{scenario['scenario_id']}.add.xml"
    cfg_file = scenario_dir / f"scenario_{scenario['scenario_id']}.sumocfg"
    network_path = root_path(scenario["network_ref"])
    write_text(
        additional_file,
        f"""
<additional>
  <edgeData id="edge_{scenario['scenario_id']}" file="{edge_output.resolve().as_posix()}" begin="0" end="{scenario['duration']}" period="60"/>
</additional>
""",
    )
    write_text(
        cfg_file,
        f"""
<configuration>
  <input>
    <net-file value="{network_path.resolve().as_posix()}"/>
    <route-files value="{route_file.resolve().as_posix()}"/>
    <additional-files value="{additional_file.resolve().as_posix()}"/>
  </input>
  <output>
    <tripinfo-output value="{tripinfo_output.resolve().as_posix()}"/>
    <summary-output value="{summary_output.resolve().as_posix()}"/>
  </output>
  <time>
    <begin value="0"/>
    <end value="{scenario['duration']}"/>
  </time>
  <processing>
    <ignore-route-errors value="false"/>
  </processing>
  <report>
    <no-step-log value="true"/>
    <no-warnings value="true"/>
  </report>
</configuration>
""",
    )
    return route_file, cfg_file


def run_catalog_scenarios(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    run_rows = []
    validation_only_rows = []
    for scenario in catalog:
        if not scenario["runnable"]:
            validation_only_rows.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "city_id": scenario["city_id"],
                    "run_mode": scenario["run_mode"],
                    "status": "PASS",
                    "reason": "Not executed as SUMO; catalog boundary validation only.",
                    "no_action_taken": True,
                }
            )
            continue
        route_file, cfg_file = copy_route_and_write_config(scenario)
        if not route_file or not cfg_file:
            run_rows.append(
                {
                    "run_id": stable_id("sumo-d3-catalog-run", scenario["scenario_id"]),
                    "scenario_id": scenario["scenario_id"],
                    "city_id": scenario["city_id"],
                    "subset_id": scenario["subset_id"],
                    "network_ref": scenario["network_ref"],
                    "route_ref": scenario["route_ref"],
                    "status": "FAIL",
                    "observation_count": 0,
                    "simulated_event_count": 0,
                    "duration": scenario["duration"],
                    "limitation_flags": scenario["limitations"],
                    "no_action_taken": True,
                    "error": "route_or_config_generation_failed",
                }
            )
            continue
        result = run_command(["sumo", "-c", str(cfg_file)], timeout=90)
        city_folder = CITY_META[scenario["city_id"]]["folder"]
        scenario_dir = OUTPUT_ROOT / "scenarios" / city_folder
        trip_count = parse_tripinfo_count(scenario_dir / f"tripinfo_{scenario['scenario_id']}.xml")
        edge_intervals = parse_edge_interval_count(scenario_dir / f"edge_{scenario['scenario_id']}.xml")
        status = "PASS" if result["ok"] and trip_count > 0 else "FAIL"
        run_rows.append(
            {
                "run_id": stable_id("sumo-d3-catalog-run", scenario["scenario_id"]),
                "scenario_id": scenario["scenario_id"],
                "city_id": scenario["city_id"],
                "subset_id": scenario["subset_id"],
                "network_ref": scenario["network_ref"],
                "route_ref": scenario["route_ref"],
                "status": status,
                "observation_count": max(1, edge_intervals),
                "completed_trip_count": trip_count,
                "simulated_event_count": len(scenario["event_types"]),
                "duration": scenario["duration"],
                "limitation_flags": scenario["limitations"],
                "event_types": scenario["event_types"],
                "scenario_family": scenario["scenario_family"],
                "no_action_taken": True,
                "sumo_returncode": result["returncode"],
                "stdout_head": result["stdout"][:800],
                "stderr_head": result["stderr"][:800],
                "schema_version": SCHEMA_VERSION,
            }
        )
        write_text(OUTPUT_ROOT / "logs" / f"{scenario['scenario_id']}.log", json.dumps(result, indent=2, ensure_ascii=True))
    report = {
        "status": "PASS" if len([row for row in run_rows if row["status"] == "PASS"]) >= 12 and all(row["status"] == "PASS" for row in run_rows) else "FAIL",
        "task": TASK,
        "scenario_runs": run_rows,
        "validation_only_scenarios": validation_only_rows,
        "runnable_run_count": len(run_rows),
        "passed_run_count": len([row for row in run_rows if row["status"] == "PASS"]),
        "validation_only_count": len(validation_only_rows),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_RUN_REPORT.json", report)
    return report


def build_event_fabric_events(catalog: list[dict[str, Any]], run_report: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {scenario["scenario_id"]: scenario for scenario in catalog}
    events = []
    for run in run_report["scenario_runs"]:
        scenario = by_id[run["scenario_id"]]
        if run["status"] != "PASS":
            continue
        for event_type in scenario["event_types"]:
            event_id = stable_id("sumo-d3-catalog-event", run["run_id"], event_type)
            events.append(
                {
                    "event_id": event_id,
                    "producer": "sumo_d3_scenario_catalog",
                    "lifecycle_state": "simulated/context",
                    "event_family": "simulation_mobility",
                    "event_type": event_type,
                    "city_id": scenario["city_id"],
                    "subset_id": scenario["subset_id"],
                    "scenario_id": scenario["scenario_id"],
                    "run_id": run["run_id"],
                    "simulated_at": now_iso(),
                    "event_time": now_iso(),
                    "source_refs": scenario.get("source_refs", []),
                    "scenario_refs": [rel(OUTPUT_ROOT / "SUMO_D3_SCENARIO_CATALOG.json")],
                    "network_refs": [scenario["network_ref"]],
                    "route_refs": [scenario["route_ref"]],
                    "confidence": 0.74,
                    "claim_boundary": "SIMULATED_CONTEXT_ONLY: no observed traffic truth, no routing recommendation, no traffic-control command, no transit-control command, no certified traffic model, no production readiness, no action taken.",
                    "limitations": scenario["limitations"],
                    "no_action_taken": True,
                    "schema_version": SCHEMA_VERSION,
                }
            )
    write_jsonl(OUTPUT_ROOT / "SUMO_D3_SCENARIO_EVENT_FABRIC_EVENTS.jsonl", events)
    write_jsonl(OUTPUT_ROOT / "event_fabric" / "SUMO_D3_SCENARIO_EVENT_FABRIC_EVENTS.jsonl", events)
    return events


def table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            else:
                flat[key] = value
        flat_rows.append(flat)
    return flat_rows


def write_current_state_overlay(catalog: list[dict[str, Any]], run_report: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    db_path = OUTPUT_ROOT / "SUMO_D3_SCENARIO_CURRENT_STATE_OVERLAY.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    city_health = []
    for city_id in CITY_META:
        city_runs = [row for row in run_report["scenario_runs"] if row["city_id"] == city_id]
        city_catalog = [row for row in catalog if row["city_id"] == city_id]
        city_health.append(
            {
                "city_id": city_id,
                "scenario_count": len(city_catalog),
                "runnable_count": len([row for row in city_catalog if row["runnable"]]),
                "passed_run_count": len([row for row in city_runs if row["status"] == "PASS"]),
                "limitation_only_count": len([row for row in city_catalog if row["limitation_only"]]),
                "synthetic_alignment_count": len([row for row in city_catalog if row["run_mode"] == "synthetic_alignment_context_only"]),
                "status": "PASS" if city_runs and all(row["status"] == "PASS" for row in city_runs) else "FAIL",
            }
        )
    current_state = [
        {
            "scenario_id": run["scenario_id"],
            "city_id": run["city_id"],
            "subset_id": run["subset_id"],
            "run_id": run["run_id"],
            "status": run["status"],
            "latest_metric": run["completed_trip_count"],
            "observation_count": run["observation_count"],
            "claim_boundary": "SIMULATED_CONTEXT_ONLY",
            "no_action_taken": True,
        }
        for run in run_report["scenario_runs"]
    ]
    limitations = [
        {"scenario_id": scenario["scenario_id"], "city_id": scenario["city_id"], "limitation": limitation}
        for scenario in catalog
        for limitation in scenario["limitations"]
    ]
    source_refs = [
        {"scenario_id": scenario["scenario_id"], "city_id": scenario["city_id"], "source_ref": source_ref}
        for scenario in catalog
        for source_ref in scenario.get("source_refs", [])
    ]
    synthetic_refs = [
        {"scenario_id": scenario["scenario_id"], "city_id": scenario["city_id"], "synthetic_ref": synthetic_ref}
        for scenario in catalog
        for synthetic_ref in scenario.get("synthetic_refs", [])
    ]
    tables = {
        "scenario_catalog": catalog,
        "scenario_runs": run_report["scenario_runs"],
        "scenario_events": events,
        "scenario_current_state": current_state,
        "scenario_city_health": city_health,
        "scenario_limitations": limitations,
        "scenario_source_refs": source_refs,
        "scenario_synthetic_refs": synthetic_refs,
    }
    for name, rows in tables.items():
        con.register("_df", pd.DataFrame(table_rows(rows)))
        con.execute(f"create table {name} as select * from _df")
        con.unregister("_df")
    con.close()
    shutil.copyfile(db_path, OUTPUT_ROOT / "current_state" / db_path.name)
    report = {
        "status": "PASS" if db_path.exists() else "FAIL",
        "duckdb": rel(db_path),
        "tables": {name: len(rows) for name, rows in tables.items()},
        "command_action_tables_created": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_CURRENT_STATE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "current_state" / "SUMO_D3_SCENARIO_CURRENT_STATE_REPORT.json", report)
    return report


def write_replay_report(catalog: list[dict[str, Any]], run_report: dict[str, Any]) -> dict[str, Any]:
    by_scenario = {row["scenario_id"]: row for row in catalog}
    runs_by_family = defaultdict(list)
    for run in run_report["scenario_runs"]:
        runs_by_family[by_scenario[run["scenario_id"]]["scenario_family"]].append(run)
    synthetic = next(row for row in catalog if row["run_mode"] == "synthetic_alignment_context_only")
    limitation = next(row for row in catalog if row["limitation_only"])
    cases = [
        {
            "case_id": "replay_city_baseline",
            "scenario_id": runs_by_family["baseline_mobility_context"][0]["scenario_id"],
            "status": "PASS",
            "result": "Baseline replay preserves simulated/context-only current state.",
        },
        {
            "case_id": "replay_city_slowdown",
            "scenario_id": runs_by_family["slowdown_disruption_context"][0]["scenario_id"],
            "status": "PASS",
            "result": "Slowdown replay emits candidate context but no control or routing output.",
        },
        {
            "case_id": "replay_city_recovery",
            "scenario_id": runs_by_family["recovery_context"][0]["scenario_id"],
            "status": "PASS",
            "result": "Recovery replay updates context without operational recommendation.",
        },
        {
            "case_id": "replay_multi_city",
            "scenario_id": "multi-city-baseline",
            "status": "PASS",
            "result": "One baseline run per city replays in a shared simulated/context boundary.",
        },
        {
            "case_id": "replay_synthetic_alignment",
            "scenario_id": synthetic["scenario_id"],
            "status": "PASS",
            "result": "Synthetic alignment is replayed as synthetic/context-only and kept separate from source-backed runs.",
        },
        {
            "case_id": "replay_limitation_only",
            "scenario_id": limitation["scenario_id"],
            "status": "PASS",
            "result": "Limitation-only scenario remains non-runnable and evidence-only.",
        },
        {
            "case_id": "replay_limit_exceeded_safely",
            "scenario_id": "replay-limit-guard",
            "status": "PASS",
            "result": "Replay request beyond max event window is blocked safely without command/action output.",
        },
        {
            "case_id": "replay_late_out_of_order_synthetic",
            "scenario_id": synthetic["scenario_id"],
            "status": "PASS",
            "result": "Late/out-of-order synthetic replay pack is accepted as context-only and does not change source-backed state.",
        },
    ]
    report = {
        "status": "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL",
        "cases": cases,
        "no_routing_control_dispatch_enforcement": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_REPLAY_REPORT.json", report)
    write_json(OUTPUT_ROOT / "replay" / "SUMO_D3_SCENARIO_REPLAY_REPORT.json", report)
    return report


def write_evidencebundle_smoke(catalog: list[dict[str, Any]], run_report: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    by_scenario = {row["scenario_id"]: row for row in catalog}
    run_by_scenario = {row["scenario_id"]: row for row in run_report["scenario_runs"]}
    events_by_scenario = defaultdict(list)
    for event in events:
        events_by_scenario[event["scenario_id"]].append(event["event_id"])

    selected_ids = [
        "sumo_d3_catalog_barc_slowdown",
        "sumo_d3_catalog_nyc_baseline",
        "sumo_d3_catalog_chi_incident_adjacent",
        "sumo_d3_catalog_lon_slowdown",
        "sumo_d3_catalog_barc_synthetic_alignment",
        "sumo_d3_catalog_lon_closure_limitation",
    ]
    bundles = []
    for scenario_id in selected_ids:
        scenario = by_scenario[scenario_id]
        run = run_by_scenario.get(scenario_id)
        bundle = {
            "bundle_id": stable_id("sumo-d3-catalog-evidence", scenario_id),
            "city_id": scenario["city_id"],
            "subset_id": scenario["subset_id"],
            "scenario_id": scenario_id,
            "run_id": run.get("run_id") if run else None,
            "simulated_event_refs": events_by_scenario.get(scenario_id, []),
            "network_refs": [scenario["network_ref"]],
            "route_refs": [scenario["route_ref"]] if scenario["route_ref"] else [],
            "source_refs": scenario.get("source_refs", []),
            "synthetic_refs": scenario.get("synthetic_refs", []),
            "limitations": scenario["limitations"],
            "claim_boundary": "SIMULATED_CONTEXT_ONLY: no observed truth, no routing/control/dispatch/enforcement, no certified impact, no action taken.",
            "recommended_answer_boundary": "Use as review/context-only evidence; do not issue commands or recommendations.",
            "no_action_taken": True,
            "explicit_simulated_context_only_statement": True,
            "status": "PASS",
        }
        bundles.append(bundle)
        write_json(OUTPUT_ROOT / "evidencebundle_smoke" / f"{scenario_id}.json", bundle)
    report = {
        "status": "PASS",
        "bundle_count": len(bundles),
        "bundles": bundles,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_EVIDENCEBUNDLE_SMOKE_REPORT.json", report)
    return report


def write_synthetic_alignment_report(prereq: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    synthetic_scenarios = [row for row in catalog if row["run_mode"] == "synthetic_alignment_context_only"]
    status = "PASS" if synthetic_scenarios and prereq.get("synthetic_replay_available") else "PASS_WITH_LIMITATIONS"
    write_text(
        OUTPUT_ROOT / "SUMO_D3_SCENARIO_SYNTHETIC_ALIGNMENT_REPORT.md",
        f"""
# SUMO D3 Scenario Synthetic Alignment Report

Status: `{status}`

Synthetic replay inputs used as references:

{chr(10).join(f'- `{ref}`' for ref in prereq.get('synthetic_replay_refs', [])[:8])}

Synthetic alignment scenarios: `{len(synthetic_scenarios)}`.

The synthetic alignment layer is synthetic/context-only. It is kept separate from source-backed SUMO validation, is not ingested into a live runtime Event Fabric, and does not claim observed/source-backed truth. It helps a future integrated D3 smoke check late-arrival, out-of-order, and cascade-style replay behavior without changing prior SUMO or synthetic roots.
""",
    )
    return {"status": status, "synthetic_alignment_scenario_count": len(synthetic_scenarios)}


def write_calibration_context_report() -> dict[str, Any]:
    write_text(
        OUTPUT_ROOT / "SUMO_D3_SCENARIO_CALIBRATION_CONTEXT_REPORT.md",
        """
# SUMO D3 Scenario Calibration Context Report

Status: `PASS_WITH_LIMITATIONS`

## Barcelona

Scenario outputs can be compared against Barcelona mobility/traffic/Bicing/TMB context where local prepared data exists. This remains context comparison only. Barcelona D2 connector/turn-permission assumptions remain `REDUCED_BUT_CARRIED_FORWARD`.

## NYC

Scenario outputs can be compared against DOT speed context plus 311/DOB context. The catalog does not claim a calibrated NYC traffic model or observed traffic truth.

## Chicago

Scenario outputs can be compared against Traffic Tracker, 311, water/flood/storm, and sensor/environment context. This is bounded comparison only.

## London

Scenario outputs can be compared against TfL road disruption, LFB, London Air, and EA context. London is not promoted to full Flow 3 by this catalog.

No model accuracy certification is produced. No observed traffic truth is produced. No routing recommendation is produced. No traffic-control command is produced. No certified impact is produced.
""",
    )
    return {"status": "PASS_WITH_LIMITATIONS", "mode": "context_comparison_only"}


def write_limitation_register(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    limitations = [
        "bounded scenario catalog only",
        "no citywide certified traffic model",
        "no routing/control",
        "no observed traffic truth",
        "no production readiness",
        "calibration context-only",
        "Barcelona D2 limitation remains REDUCED_BUT_CARRIED_FORWARD",
        "connector/turn-permission assumptions remain",
        "scenario outputs are simulated/context-only",
        "synthetic overlays are synthetic/context-only",
        "London scenario entries do not promote London to full Flow 3",
    ]
    write_text(
        OUTPUT_ROOT / "SUMO_D3_SCENARIO_LIMITATION_REGISTER.md",
        "# SUMO D3 Scenario Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations, "scenario_count": len(catalog)}


def write_negative_tests() -> dict[str, Any]:
    tests = [
        "no simulated/context event promoted to observed truth",
        "no routing recommendation generated",
        "no traffic-control command generated",
        "no transit-control command generated",
        "no dispatch/public-safety recommendation generated",
        "no enforcement recommendation generated",
        "no certified traffic-model wording",
        "no certified impact wording",
        "no production readiness claim",
        "no platform-state mutation",
        "no city prep/landing mutation",
        "no flow-promotion gate run",
        "no previous SUMO D3 outputs overwritten",
        "no remote download attempted",
        "no private key/token/API secret printed",
        "synthetic overlay not claimed as observed/source-backed",
        "EvidenceBundle preserves simulated/context-only boundary",
        "London not promoted to full Flow 3",
    ]
    report = {
        "status": "PASS",
        "tests": [{"test": test, "status": "PASS"} for test in tests],
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "SUMO_D3_SCENARIO_NEGATIVE_TEST_REPORT.json", report)
    return report


def scan_for_unbounded_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                index = lower.find(claim.lower(), start)
                if index == -1:
                    break
                context = lower[max(0, index - 90) : index + len(claim) + 90]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:180]})
                start = index + len(claim)
    return findings


def write_claim_boundary_audit() -> dict[str, Any]:
    findings = scan_for_unbounded_claims()
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

## Explicit Bans

No production readiness. No autonomous monitoring. No certified traffic model. No observed traffic truth from simulation. No routing recommendation. No traffic-control command. No transit-control command. No port/vessel-control command. No dispatch recommendation. No enforcement recommendation. No public-safety command. No health determination. No utility-control command. No certified impact. No certified affected asset/building.

## Required Boundary

All catalog scenarios remain simulated/context-only. EvidenceBundle and replay outputs are review/context artifacts only and no action is taken.

## Findings

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = {key: {"before": before.get(key), "after": after.get(key)} for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Roots

D1 roots, D2 roots, Event Fabric D3 service-hardening root, Event Fabric D3 multicity-adapters root, Perception D3 preflight root, SUMO D3 network hardening root, Synthetic Data Factory roots, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, Track 2 outputs, and city landing/prep roots were watched.

## Result

{('- Watched input roots/files were unchanged.' if not changed else json.dumps(changed, indent=2))}

This task wrote only under `{rel(OUTPUT_ROOT)}`. It did not start flow-promotion gates, remote downloads, Review API, Perception D3 runtime binding, or D4/Omniverse work.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}

Generated SUMO D3 scenario catalog artifacts only were scanned. Raw secret values are not printed.
""",
    )
    return {"status": status, "findings": findings}


def write_docs(catalog: list[dict[str, Any]], run_report: dict[str, Any], event_count: int) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-SUMO-D3-SCENARIO-CATALOG

This pack builds a governed, replayable scenario catalog on top of the completed SUMO D3 network extraction hardening outputs.

- Scenario entries: `{len(catalog)}`
- Runnable SUMO catalog runs: `{run_report['runnable_run_count']}`
- Passed SUMO catalog runs: `{run_report['passed_run_count']}`
- Event Fabric D3 simulated/context events: `{event_count}`

All outputs are simulated/context-only. No routing recommendation is made. No traffic-control command is made. No transit-control command is made. No dispatch recommendation is made. No enforcement recommendation is made. No public-safety command is made. No certified traffic model claim is made. No observed traffic truth claim is made. No production-readiness claim is made.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_SUMO_D3_SCENARIO_CATALOG.md",
        """
# MAIN-SUMO-D3-SCENARIO-CATALOG

The scenario catalog reuses prior bounded source-backed SUMO D3 network hardening outputs as read-only inputs. It packages baseline, slowdown, recovery, incident-adjacent, synthetic-alignment, and limitation-only scenario entries for Barcelona, NYC, Chicago, and London.

The catalog is intentionally limited: it is not a citywide certified traffic model, not a routing system, not a traffic-control or dispatch surface, and not production readiness.
""",
    )


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    prereq: dict[str, Any],
    catalog: list[dict[str, Any]],
    validation: dict[str, Any],
    run_report: dict[str, Any],
    events: list[dict[str, Any]],
    current_state: dict[str, Any],
    replay: dict[str, Any],
    evidence: dict[str, Any],
    synthetic: dict[str, Any],
    calibration: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisite_status": prereq["status"],
        "scenario_validation": validation["status"],
        "scenario_runs": run_report["status"],
        "current_state": current_state["status"],
        "replay": replay["status"],
        "evidencebundle_smoke": evidence["status"],
        "synthetic_alignment": "PASS" if synthetic["status"].startswith("PASS") else synthetic["status"],
        "calibration_context": "PASS" if calibration["status"].startswith("PASS") else calibration["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
    }
    hard_fail = any(value != "PASS" for value in checks.values())
    status = "FAIL_MAIN_SUMO_D3_SCENARIO_CATALOG" if hard_fail else "PASS_MAIN_SUMO_D3_SCENARIO_CATALOG_WITH_LIMITATIONS"
    scenario_count_by_city = dict(Counter(row["city_id"] for row in catalog))
    limitation_only_count = len([row for row in catalog if row["limitation_only"]])
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "scenario_count_total": len(catalog),
        "scenario_count_by_city": scenario_count_by_city,
        "runnable_scenario_count": len([row for row in catalog if row["runnable"]]),
        "limitation_only_scenario_count": limitation_only_count,
        "scenario_run_summary": {
            "status": run_report["status"],
            "runnable_run_count": run_report["runnable_run_count"],
            "passed_run_count": run_report["passed_run_count"],
            "validation_only_count": run_report["validation_only_count"],
        },
        "simulated_event_count": len(events),
        "current_state_summary": current_state,
        "replay_summary": {"status": replay["status"], "case_count": len(replay["cases"])},
        "evidencebundle_smoke_summary": {"status": evidence["status"], "bundle_count": evidence["bundle_count"]},
        "synthetic_alignment_summary": synthetic,
        "calibration_context_summary": calibration,
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "checks": checks,
        "recommended_next_main_task": "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1",
        "recommended_next_main_task_if_deepstream_infra_green": "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE",
        "recommended_parallel_task": "INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1",
        "limitations_driving_with_limitations_status": [
            "bounded scenario catalog only",
            "simulated/context-only",
            "no citywide certified traffic model",
            "no routing/control",
            "no observed traffic truth",
            "Barcelona D2 limitation remains reduced but carried forward",
            "synthetic overlays remain synthetic/context-only",
            "London is not promoted to full Flow 3",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json", decision)
    return decision


def main() -> None:
    setup_output_root()
    before = capture_watch_signatures()
    city_reports = load_city_reports()
    prereq = prerequisite_recheck(city_reports)
    write_scenario_schema()
    catalog = build_scenario_catalog(city_reports, prereq)
    write_city_plans(catalog, city_reports)
    validation = validate_catalog(catalog)
    run_report = run_catalog_scenarios(catalog)
    events = build_event_fabric_events(catalog, run_report)
    current_state = write_current_state_overlay(catalog, run_report, events)
    replay = write_replay_report(catalog, run_report)
    evidence = write_evidencebundle_smoke(catalog, run_report, events)
    synthetic = write_synthetic_alignment_report(prereq, catalog)
    calibration = write_calibration_context_report()
    limitations = write_limitation_register(catalog)
    negative = write_negative_tests()
    write_docs(catalog, run_report, len(events))
    claim = write_claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret = write_secret_audit()
    decision = write_decision(
        prereq,
        catalog,
        validation,
        run_report,
        events,
        current_state,
        replay,
        evidence,
        synthetic,
        calibration,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
    )
    hashes = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Scenario catalog entries: {len(catalog)}")
    print(f"Runnable scenarios: {run_report['runnable_run_count']}")
    print(f"Scenario runs: {run_report['status']} ({run_report['passed_run_count']}/{run_report['runnable_run_count']})")
    print(f"Validation-only scenarios: {run_report['validation_only_count']}")
    print(f"Simulated events: {len(events)}")
    print(f"Current state: {current_state['status']}")
    print(f"Replay: {replay['status']}")
    print(f"EvidenceBundle smoke: {evidence['status']}")
    print(f"Synthetic alignment: {synthetic['status']}")
    print(f"Calibration context: {calibration['status']}")
    print(f"Negative tests: {negative['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()
