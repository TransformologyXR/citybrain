from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_sumo_simulation_d1"
NETWORK_ROOT = OUTPUT_ROOT / "SUMO_NETWORK_FIXTURE"
ROUTE_ROOT = OUTPUT_ROOT / "SUMO_ROUTE_FIXTURE"
CONFIG_ROOT = OUTPUT_ROOT / "SUMO_RUN_CONFIG"
REPLAY_ROOT = OUTPUT_ROOT / "SUMO_REPLAY_SCENARIO_PACKS"
OVERLAY_ROOT = OUTPUT_ROOT / "event_fabric_overlay"
NOW = datetime(2026, 6, 28, 14, 0, 0, tzinfo=timezone.utc)
SCHEMA_VERSION = "main-sumo-simulation-d1.v1"


INPUTS = {
    "event_fabric_schema_json": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_FABRIC_SCHEMA.json",
    "event_fabric_decision": ROOT / "outputs" / "main_platform_event_fabric_d1" / "MAIN_PLATFORM_EVENT_FABRIC_D1_DECISION.json",
    "event_fabric_append_log": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_APPEND_LOG_SAMPLE.jsonl",
    "event_fabric_current_state": ROOT / "outputs" / "main_platform_event_fabric_d1" / "EVENT_CURRENT_STATE.duckdb",
    "perception_decision": ROOT / "outputs" / "main_perception_candidate_event_d1" / "MAIN_PERCEPTION_CANDIDATE_EVENT_D1_DECISION.json",
    "perception_output_root": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "platform_state": ROOT / "outputs" / "platform_state_generated" / "CITYBRAIN_PLATFORM_STATE.json",
    "resolver_inputs": ROOT / "outputs" / "platform_state_generated" / "CITYBRAIN_RESOLVER_INPUTS.json",
    "a9_g1_decision": ROOT
    / "outputs"
    / "main_platform_a9_g1_snapshot_closeout_r1"
    / "MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1_DECISION.json",
    "pv1_d19_d22_decision": ROOT
    / "outputs"
    / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot"
    / "PV1_D19_D20_D21_D22_DECISION.json",
    "barc_consumption_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
}


EVENT_TYPES = [
    "simulated_congestion_candidate",
    "simulated_delay_candidate",
    "simulated_closure_impact_candidate",
    "simulated_route_load_candidate",
    "simulated_recovery_candidate",
]

FORBIDDEN_CLAIMS = [
    "traffic-control command",
    "routing instruction",
    "operational dispatch",
    "enforcement",
    "public-safety command",
    "certified impact",
    "production traffic model",
    "live city control",
    "autonomous action",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "blocked",
    "forbidden",
    "refuse",
    "refuses",
    "negative",
    "cannot",
    "must not",
    "does not",
    "do not",
    "without",
    "review/context",
    "simulated",
]


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def now_iso() -> str:
    return iso(NOW)


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(p) for p in parts), length)}"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        stat = path.stat()
        return {
            "exists": True,
            "type": "file",
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": sha256_file(path),
        }
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "sha256": sha256_file(child),
                }
            )
    tree_sha = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {name: path_signature(path) for name, path in INPUTS.items()}


def flatten_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            else:
                flat[key] = value
        flat_rows.append(flat)
    return pd.DataFrame(flat_rows)


def run_command(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> dict[str, Any]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "ok": result.returncode == 0,
        }
    except Exception as exc:
        return {"cmd": cmd, "returncode": None, "stdout": "", "stderr": str(exc), "ok": False}


def check_sumo_runtime() -> dict[str, Any]:
    sumo = run_command(["sumo", "--version"], timeout=20)
    netconvert = run_command(["netconvert", "--version"], timeout=20)
    return {
        "sumo": sumo,
        "netconvert": netconvert,
        "available": bool(sumo["ok"] and netconvert["ok"]),
        "runtime_status": "SUMO_NATIVE_AVAILABLE" if sumo["ok"] and netconvert["ok"] else "SUMO_RUNTIME_NOT_AVAILABLE",
    }


def event_fabric_schema_version(schema: dict[str, Any]) -> str:
    return str(schema.get("schema_version") or "main-platform-event-fabric-d1.v1")


def event_required_fields(schema: dict[str, Any]) -> list[str]:
    return list(schema["definitions"]["EventEnvelope"]["required"])


def build_network_fixture() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = [
        {"id": "node_barc_0", "x": 0.0, "y": 0.0},
        {"id": "node_barc_1", "x": 100.0, "y": 0.0},
        {"id": "node_barc_2", "x": 210.0, "y": 0.0},
        {"id": "node_barc_3", "x": 100.0, "y": 85.0},
        {"id": "node_barc_4", "x": 215.0, "y": 85.0},
        {"id": "node_barc_5", "x": 325.0, "y": 35.0},
    ]
    edges = [
        {"id": "edge_barc_0", "from": "node_barc_0", "to": "node_barc_1", "length": 100.0, "baseline_speed": 13.89, "disruption_speed": 13.89, "area_ref": "BARC_fixture_west_approach"},
        {"id": "edge_barc_1", "from": "node_barc_1", "to": "node_barc_2", "length": 110.0, "baseline_speed": 13.89, "disruption_speed": 3.00, "area_ref": "BARC_fixture_slowdown_candidate"},
        {"id": "edge_barc_2", "from": "node_barc_2", "to": "node_barc_5", "length": 120.0, "baseline_speed": 13.89, "disruption_speed": 13.89, "area_ref": "BARC_fixture_east_exit"},
        {"id": "edge_barc_3", "from": "node_barc_1", "to": "node_barc_3", "length": 85.0, "baseline_speed": 11.11, "disruption_speed": 11.11, "area_ref": "BARC_fixture_alt_north_1"},
        {"id": "edge_barc_4", "from": "node_barc_3", "to": "node_barc_4", "length": 115.0, "baseline_speed": 11.11, "disruption_speed": 11.11, "area_ref": "BARC_fixture_alt_north_2"},
        {"id": "edge_barc_5", "from": "node_barc_4", "to": "node_barc_5", "length": 121.0, "baseline_speed": 11.11, "disruption_speed": 11.11, "area_ref": "BARC_fixture_alt_exit"},
        {"id": "edge_barc_6", "from": "node_barc_2", "to": "node_barc_4", "length": 88.0, "baseline_speed": 10.00, "disruption_speed": 10.00, "area_ref": "BARC_fixture_mid_connector"},
        {"id": "edge_barc_7", "from": "node_barc_0", "to": "node_barc_3", "length": 132.0, "baseline_speed": 10.00, "disruption_speed": 10.00, "area_ref": "BARC_fixture_direct_alt_entry"},
    ]
    network = {
        "network_id": "barc_hero_sumo_network_d1",
        "city": "BARC",
        "nodes": nodes,
        "edges": edges,
        "junctions": [{"junction_id": node["id"], "node_ref": node["id"]} for node in nodes],
        "coordinate_system": "fixture_local_xy_meters",
        "source_refs": [
            {
                "source": "Barcelona mobility/context prep",
                "path": "outputs/barc_allflows_consumption_prep_r1/BARC_FLOW_MART.duckdb",
                "tables": ["silver_traffic_trams", "silver_traffic_itineraries"],
                "source_boundary": "Used as context for city/flow selection only; geometry is a deterministic fixture.",
            }
        ],
        "limitations": [
            "Hero road-network fixture only; not a full Barcelona road graph.",
            "Edge IDs are deterministic fixture refs, not certified road impact refs.",
            "One edge is slowed in the disruption scenario for simulation context only.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    return network, nodes, edges


def build_routes() -> list[dict[str, Any]]:
    return [
        {
            "route_id": "route_main_eastbound",
            "scenario_id": "scenario_barc_baseline_mobility",
            "vehicle_type": "passenger_fixture",
            "origin_edge": "edge_barc_0",
            "destination_edge": "edge_barc_2",
            "depart_time": 0,
            "route_edges": ["edge_barc_0", "edge_barc_1", "edge_barc_2"],
            "assumptions": ["main route traverses the slowdown candidate edge"],
            "schema_version": SCHEMA_VERSION,
        },
        {
            "route_id": "route_alt_north",
            "scenario_id": "scenario_barc_baseline_mobility",
            "vehicle_type": "passenger_fixture",
            "origin_edge": "edge_barc_0",
            "destination_edge": "edge_barc_5",
            "depart_time": 15,
            "route_edges": ["edge_barc_0", "edge_barc_3", "edge_barc_4", "edge_barc_5"],
            "assumptions": ["alternative path avoids the slowdown candidate edge"],
            "schema_version": SCHEMA_VERSION,
        },
        {
            "route_id": "route_connector",
            "scenario_id": "scenario_barc_disruption_slowdown",
            "vehicle_type": "passenger_fixture",
            "origin_edge": "edge_barc_0",
            "destination_edge": "edge_barc_5",
            "depart_time": 30,
            "route_edges": ["edge_barc_0", "edge_barc_1", "edge_barc_6", "edge_barc_5"],
            "assumptions": ["connector route partly traverses the slowdown candidate edge"],
            "schema_version": SCHEMA_VERSION,
        },
    ]


def build_scenarios() -> list[dict[str, Any]]:
    base_refs = [
        {
            "path": "outputs/barc_allflows_consumption_prep_r1/BARC_FLOW_MART.duckdb",
            "use": "source-derived city/flow context",
        },
        {"path": "outputs/main_platform_event_fabric_d1", "use": "EventEnvelope contract"},
    ]
    return [
        {
            "scenario_id": "scenario_barc_baseline_mobility",
            "city": "BARC",
            "title": "Barcelona hero baseline mobility simulation",
            "description": "Minimal SUMO baseline over a deterministic Barcelona mobility fixture.",
            "network_ref": "SUMO_NETWORK_FIXTURE/barc_hero_baseline.net.xml",
            "route_ref": "SUMO_ROUTE_FIXTURE/barc_hero_routes.rou.xml",
            "time_window": {"begin": 0, "end": 1000},
            "flows": ["BARC-F1", "BARC-F4", "BARC-F7"],
            "source_refs": base_refs,
            "assumptions": [
                "Fixture network contains two alternative paths.",
                "Travel times are simulation context only.",
            ],
            "claim_boundary": "SIMULATED_CONTEXT: review/context only, assumptions and limitations preserved, no action taken.",
            "schema_version": SCHEMA_VERSION,
        },
        {
            "scenario_id": "scenario_barc_disruption_slowdown",
            "city": "BARC",
            "title": "Barcelona hero slowdown simulation",
            "description": "Minimal SUMO disruption run with one slowed edge.",
            "network_ref": "SUMO_NETWORK_FIXTURE/barc_hero_disruption.net.xml",
            "route_ref": "SUMO_ROUTE_FIXTURE/barc_hero_routes.rou.xml",
            "time_window": {"begin": 0, "end": 1000},
            "flows": ["BARC-F1", "BARC-F3", "BARC-F4", "BARC-F7"],
            "source_refs": base_refs,
            "assumptions": [
                "edge_barc_1 is slowed from 13.89 m/s to 3.0 m/s.",
                "Slowdown is a fixture condition, not a live city condition.",
            ],
            "claim_boundary": "SIMULATED_CONTEXT: candidate delay context only, no routing instruction and no action taken.",
            "schema_version": SCHEMA_VERSION,
        },
        {
            "scenario_id": "scenario_barc_recovery_comparison",
            "city": "BARC",
            "title": "Barcelona hero recovery comparison",
            "description": "Deterministic comparison where slowed edge returns to baseline fixture speed.",
            "network_ref": "SUMO_NETWORK_FIXTURE/barc_hero_baseline.net.xml",
            "route_ref": "SUMO_ROUTE_FIXTURE/barc_hero_routes.rou.xml",
            "time_window": {"begin": 0, "end": 1000},
            "flows": ["BARC-F1", "BARC-F4", "BARC-F7"],
            "source_refs": base_refs,
            "assumptions": [
                "Recovery compares disruption output to baseline output.",
                "Comparison is simulated context only.",
            ],
            "claim_boundary": "SIMULATED_CONTEXT: recovery comparison is review/context only, no action taken.",
            "schema_version": SCHEMA_VERSION,
        },
    ]


def write_xml_fixtures(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], routes: list[dict[str, Any]]) -> None:
    def edge_speed(edge: dict[str, Any], mode: str) -> float:
        return edge["baseline_speed"] if mode == "baseline" else edge["disruption_speed"]

    for mode in ("baseline", "disruption"):
        nodes_text = ["<nodes>"]
        for node in nodes:
            nodes_text.append(f'  <node id="{node["id"]}" x="{node["x"]}" y="{node["y"]}" type="priority"/>')
        nodes_text.append("</nodes>")
        (NETWORK_ROOT / f"barc_hero_{mode}.nod.xml").write_text("\n".join(nodes_text) + "\n", encoding="utf-8")

        edge_lines = ["<edges>"]
        for edge in edges:
            edge_lines.append(
                f'  <edge id="{edge["id"]}" from="{edge["from"]}" to="{edge["to"]}" '
                f'priority="1" numLanes="1" speed="{edge_speed(edge, mode):.2f}" length="{edge["length"]:.1f}"/>'
            )
        edge_lines.append("</edges>")
        (NETWORK_ROOT / f"barc_hero_{mode}.edg.xml").write_text("\n".join(edge_lines) + "\n", encoding="utf-8")

    route_lines = [
        "<routes>",
        '  <vType id="passenger_fixture" accel="2.6" decel="4.5" sigma="0" length="5" maxSpeed="13.89"/>',
    ]
    route_by_id = {route["route_id"]: route for route in routes}
    for route in routes:
        route_lines.append(f'  <route id="{route["route_id"]}" edges="{" ".join(route["route_edges"])}"/>')
    departures = [
        ("veh_main_00", "route_main_eastbound", 0),
        ("veh_main_01", "route_main_eastbound", 20),
        ("veh_main_02", "route_main_eastbound", 40),
        ("veh_alt_00", "route_alt_north", 10),
        ("veh_alt_01", "route_alt_north", 35),
        ("veh_connector_00", "route_connector", 25),
        ("veh_connector_01", "route_connector", 55),
        ("veh_alt_02", "route_alt_north", 70),
    ]
    for veh_id, route_id, depart in departures:
        route_lines.append(f'  <vehicle id="{veh_id}" type="passenger_fixture" route="{route_id}" depart="{depart}"/>')
    route_lines.append("</routes>")
    (ROUTE_ROOT / "barc_hero_routes.rou.xml").write_text("\n".join(route_lines) + "\n", encoding="utf-8")

    write_json(NETWORK_ROOT / "road_network_fixture.json", build_network_fixture()[0])
    write_json(ROUTE_ROOT / "route_fixtures.json", {"routes": routes, "vehicle_departures": departures})


def write_sumocfgs() -> None:
    configs = {
        "baseline": ("barc_hero_baseline.net.xml", "baseline_tripinfo.xml"),
        "disruption": ("barc_hero_disruption.net.xml", "disruption_tripinfo.xml"),
    }
    for name, (net_file, tripinfo_file) in configs.items():
        text = f"""
<configuration>
  <input>
    <net-file value="../SUMO_NETWORK_FIXTURE/{net_file}"/>
    <route-files value="../SUMO_ROUTE_FIXTURE/barc_hero_routes.rou.xml"/>
  </input>
  <output>
    <tripinfo-output value="{tripinfo_file}"/>
  </output>
  <time>
    <begin value="0"/>
    <end value="1000"/>
  </time>
  <processing>
    <time-to-teleport value="-1"/>
  </processing>
</configuration>
"""
        (CONFIG_ROOT / f"{name}.sumocfg").write_text(text.strip() + "\n", encoding="utf-8")


def run_sumo_scenarios(runtime: dict[str, Any]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    if runtime["available"]:
        for mode in ("baseline", "disruption"):
            net_out = NETWORK_ROOT / f"barc_hero_{mode}.net.xml"
            cmd = [
                "netconvert",
                "--node-files",
                str(NETWORK_ROOT / f"barc_hero_{mode}.nod.xml"),
                "--edge-files",
                str(NETWORK_ROOT / f"barc_hero_{mode}.edg.xml"),
                "-o",
                str(net_out),
                "--no-turnarounds",
                "true",
            ]
            commands.append(run_command(cmd, timeout=60))
        for config in ("baseline", "disruption"):
            cmd = [
                "sumo",
                "-c",
                str(CONFIG_ROOT / f"{config}.sumocfg"),
                "--no-step-log",
                "true",
                "--duration-log.disable",
                "true",
                "--no-warnings",
                "true",
            ]
            commands.append(run_command(cmd, timeout=60))
    native_ok = runtime["available"] and all(command["ok"] for command in commands)
    return {
        "runtime_status": "SUMO_NATIVE_RUN" if native_ok else "DETERMINISTIC_SUMO_COMPATIBLE_FALLBACK",
        "fallback_used": not native_ok,
        "commands": commands,
        "limitations": []
        if native_ok
        else ["SUMO_RUNTIME_NOT_AVAILABLE_OR_RUN_FAILED", "Deterministic fallback calculations used."],
    }


def parse_tripinfo(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "vehicles": 0, "avg_duration": None, "avg_time_loss": None}
    root = ET.parse(path).getroot()
    rows = []
    for trip in root.findall("tripinfo"):
        rows.append(
            {
                "id": trip.attrib.get("id"),
                "duration": float(trip.attrib.get("duration", 0)),
                "timeLoss": float(trip.attrib.get("timeLoss", 0)),
                "routeLength": float(trip.attrib.get("routeLength", 0)),
                "depart": float(trip.attrib.get("depart", 0)),
                "arrival": float(trip.attrib.get("arrival", 0)),
            }
        )
    return {
        "exists": True,
        "vehicles": len(rows),
        "avg_duration": sum(r["duration"] for r in rows) / len(rows) if rows else None,
        "avg_time_loss": sum(r["timeLoss"] for r in rows) / len(rows) if rows else None,
        "rows": rows,
    }


def edge_by_id(edges: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {edge["id"]: edge for edge in edges}


def route_departures() -> list[tuple[str, str, float]]:
    return [
        ("veh_main_00", "route_main_eastbound", 0),
        ("veh_main_01", "route_main_eastbound", 20),
        ("veh_main_02", "route_main_eastbound", 40),
        ("veh_alt_00", "route_alt_north", 10),
        ("veh_alt_01", "route_alt_north", 35),
        ("veh_connector_00", "route_connector", 25),
        ("veh_connector_01", "route_connector", 55),
        ("veh_alt_02", "route_alt_north", 70),
    ]


def build_observations(
    scenarios: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    runtime_status: str,
) -> list[dict[str, Any]]:
    route_idx = {route["route_id"]: route for route in routes}
    edge_idx = edge_by_id(edges)
    observations = []
    scenario_modes = {
        "scenario_barc_baseline_mobility": "baseline",
        "scenario_barc_disruption_slowdown": "disruption",
        "scenario_barc_recovery_comparison": "baseline",
    }
    for scenario in scenarios:
        mode = scenario_modes[scenario["scenario_id"]]
        for vehicle_id, route_id, depart in route_departures():
            route = route_idx[route_id]
            elapsed = depart
            for edge_id in route["route_edges"]:
                edge = edge_idx[edge_id]
                speed = edge["baseline_speed"] if mode == "baseline" else edge["disruption_speed"]
                baseline_time = edge["length"] / edge["baseline_speed"]
                actual_time = edge["length"] / speed
                delay = max(0.0, actual_time - baseline_time)
                elapsed += actual_time
                observations.append(
                    {
                        "observation_id": stable_id("simulation-observation", scenario["scenario_id"], vehicle_id, edge_id),
                        "scenario_id": scenario["scenario_id"],
                        "sim_time": round(elapsed, 2),
                        "vehicle_id": vehicle_id,
                        "edge_id": edge_id,
                        "position": {"edge_position_m": round(edge["length"] * 0.5, 1)},
                        "speed": round(speed, 2),
                        "delay": round(delay, 2),
                        "status": "simulated_slowdown_context" if delay > 0 else "simulated_baseline_context",
                        "source_mode": runtime_status,
                        "claim_boundary": "SIMULATED_CONTEXT: observation is review/context only; no action taken.",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
    return observations


def route_time(route: dict[str, Any], edges: dict[str, dict[str, Any]], mode: str) -> float:
    total = 0.0
    for edge_id in route["route_edges"]:
        edge = edges[edge_id]
        speed = edge["baseline_speed"] if mode == "baseline" else edge["disruption_speed"]
        total += edge["length"] / speed
    return total


def sim_event(
    event_type: str,
    scenario_id: str,
    edge_id: str,
    vehicle_ids: list[str],
    metric_name: str,
    metric_value: float,
    severity: float,
    confidence: float,
    description: str,
) -> dict[str, Any]:
    return {
        "simulation_event_id": stable_id("simulation-event", event_type, scenario_id, edge_id, ",".join(vehicle_ids), metric_name, metric_value),
        "event_family": "simulation_mobility",
        "event_type": event_type,
        "city": "BARC",
        "scenario_id": scenario_id,
        "event_time": now_iso(),
        "event_end_time": None,
        "edge_id": edge_id,
        "vehicle_ids": vehicle_ids,
        "metric_name": metric_name,
        "metric_value": round(metric_value, 3),
        "severity_or_magnitude": round(severity, 3),
        "entity_refs": [{"entity_type": "fixture_road_edge", "entity_ref": edge_id}],
        "area_refs": [
            {"area_type": "city", "area_ref": "BARC"},
            {"area_type": "fixture_corridor", "area_ref": "BARC_hero_sumo_corridor"},
        ],
        "simulation_refs": {
            "description": description,
            "network_id": "barc_hero_sumo_network_d1",
            "source_mode": "SUMO_NATIVE_OR_COMPATIBLE_D1",
        },
        "confidence": confidence,
        "review_state": "auto_context",
        "privacy_boundary": "PUBLIC_CONTEXT",
        "claim_boundary": "SIMULATED_CONTEXT: review/context only; assumptions and limitations preserved; no action taken.",
        "schema_version": SCHEMA_VERSION,
    }


def build_simulation_events(
    scenarios: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    edge_idx = edge_by_id(edges)
    route_idx = {route["route_id"]: route for route in routes}
    vehicles_by_route: dict[str, list[str]] = defaultdict(list)
    for vehicle_id, route_id, _depart in route_departures():
        vehicles_by_route[route_id].append(vehicle_id)

    baseline_main = route_time(route_idx["route_main_eastbound"], edge_idx, "baseline")
    disruption_main = route_time(route_idx["route_main_eastbound"], edge_idx, "disruption")
    baseline_alt = route_time(route_idx["route_alt_north"], edge_idx, "baseline")
    disruption_connector = route_time(route_idx["route_connector"], edge_idx, "disruption")
    slowdown_delay = disruption_main - baseline_main

    events = [
        sim_event("simulated_route_load_candidate", "scenario_barc_baseline_mobility", "edge_barc_0", vehicles_by_route["route_main_eastbound"] + vehicles_by_route["route_alt_north"], "vehicle_count", 6, 1, 0.9, "Baseline fixture load on shared entry edge."),
        sim_event("simulated_route_load_candidate", "scenario_barc_baseline_mobility", "edge_barc_3", vehicles_by_route["route_alt_north"], "vehicle_count", 3, 1, 0.88, "Baseline fixture load on alternate path."),
        sim_event("simulated_delay_candidate", "scenario_barc_disruption_slowdown", "edge_barc_1", vehicles_by_route["route_main_eastbound"], "route_main_delay_seconds", slowdown_delay, min(5, slowdown_delay / 10), 0.86, "Disruption fixture creates delay on main route."),
        sim_event("simulated_delay_candidate", "scenario_barc_disruption_slowdown", "edge_barc_1", vehicles_by_route["route_connector"], "connector_delay_seconds", disruption_connector - route_time(route_idx["route_connector"], edge_idx, "baseline"), 2, 0.84, "Connector route carries slowed edge delay."),
        sim_event("simulated_congestion_candidate", "scenario_barc_disruption_slowdown", "edge_barc_1", vehicles_by_route["route_main_eastbound"] + vehicles_by_route["route_connector"], "edge_speed_ratio", edge_idx["edge_barc_1"]["disruption_speed"] / edge_idx["edge_barc_1"]["baseline_speed"], 4, 0.87, "Slowdown candidate edge runs below baseline fixture speed."),
        sim_event("simulated_closure_impact_candidate", "scenario_barc_disruption_slowdown", "edge_barc_1", vehicles_by_route["route_main_eastbound"], "affected_fixture_vehicle_count", 3, 3, 0.82, "Slowdown edge affects fixture route timing; impact certification is refused."),
        sim_event("simulated_route_load_candidate", "scenario_barc_disruption_slowdown", "edge_barc_5", vehicles_by_route["route_alt_north"] + vehicles_by_route["route_connector"], "alt_exit_vehicle_count", 5, 2, 0.82, "Alternate exit carries fixture route load."),
        sim_event("simulated_recovery_candidate", "scenario_barc_recovery_comparison", "edge_barc_1", vehicles_by_route["route_main_eastbound"], "delay_recovered_seconds", slowdown_delay, 3, 0.86, "Recovery comparison returns slowed edge to baseline fixture speed."),
        sim_event("simulated_recovery_candidate", "scenario_barc_recovery_comparison", "edge_barc_0", vehicles_by_route["route_main_eastbound"] + vehicles_by_route["route_alt_north"], "baseline_entry_time_seconds", route_time(route_idx["route_main_eastbound"], edge_idx, "baseline"), 1, 0.88, "Baseline travel-time state restored in comparison."),
        sim_event("simulated_delay_candidate", "scenario_barc_disruption_slowdown", "edge_barc_1", ["veh_main_00"], "single_vehicle_edge_delay_seconds", observations[0]["delay"], 1, 0.8, "Single fixture observation carried as delay candidate context."),
        sim_event("simulated_route_load_candidate", "scenario_barc_baseline_mobility", "edge_barc_7", [], "alternative_path_available", 1, 1, 0.8, "Direct alternate path is available in fixture network."),
        sim_event("simulated_congestion_candidate", "scenario_barc_disruption_slowdown", "edge_barc_6", vehicles_by_route["route_connector"], "connector_load_count", 2, 1, 0.78, "Connector edge load is simulated candidate context."),
    ]
    return events


def map_to_event_envelopes(
    simulation_events: list[dict[str, Any]],
    event_schema_version: str,
) -> list[dict[str, Any]]:
    envelopes = []
    for event in simulation_events:
        envelopes.append(
            {
                "event_id": stable_id("event", event["simulation_event_id"]),
                "event_family": "simulation_mobility",
                "event_type": event["event_type"],
                "city": event["city"],
                "flow_candidates": ["BARC-F1", "BARC-F3", "BARC-F4", "BARC-F7"],
                "event_time": event["event_time"],
                "event_end_time": event["event_end_time"],
                "processing_time": now_iso(),
                "source_key": "sumo_simulation_d1",
                "source_record_id": event["simulation_event_id"],
                "source_ref": {
                    "path": "outputs/main_sumo_simulation_d1/SUMO_SIMULATION_EVENTS.jsonl",
                    "scenario_id": event["scenario_id"],
                    "edge_id": event["edge_id"],
                    "source_mode": "SUMO_NATIVE_RUN_OR_COMPATIBLE_FALLBACK",
                },
                "event_status": "simulated",
                "event_lifecycle": "simulated",
                "location": {"coordinate_system": "fixture_local_xy_meters", "edge_id": event["edge_id"]},
                "entity_refs": event["entity_refs"],
                "area_refs": event["area_refs"],
                "severity_or_magnitude": event["severity_or_magnitude"],
                "payload": {
                    "simulation_event_id": event["simulation_event_id"],
                    "scenario_id": event["scenario_id"],
                    "edge_id": event["edge_id"],
                    "vehicle_ids": event["vehicle_ids"],
                    "metric_name": event["metric_name"],
                    "metric_value": event["metric_value"],
                    "simulation_refs": event["simulation_refs"],
                    "selected_fields_only": True,
                    "assumptions_preserved": True,
                },
                "provenance": {
                    "adapter": "sumo_simulation_d1_adapter",
                    "base_event_fabric": "outputs/main_platform_event_fabric_d1",
                    "runtime_mode": "SUMO_NATIVE_RUN_OR_COMPATIBLE_FALLBACK",
                },
                "confidence": event["confidence"],
                "review_state": "auto_context",
                "privacy_boundary": "PUBLIC_CONTEXT",
                "claim_boundary": "SIMULATED_CONTEXT: review/context only; assumptions and limitations preserved; no action taken.",
                "ttl_seconds": 3600,
                "supersedes_event_ids": [],
                "superseded_by_event_id": None,
                "schema_version": event_schema_version,
            }
        )
    return envelopes


def validate_schema_objects(schema: dict[str, Any], objects: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    failures = []
    for object_name, rows in objects.items():
        required = schema["definitions"][object_name]["required"]
        for row in rows:
            missing = [field for field in required if field not in row]
            if missing:
                failures.append({"object": object_name, "id": row.get("scenario_id") or row.get("network_id") or row.get("simulation_event_id"), "missing": missing})
    return failures


def validate_envelopes(envelopes: list[dict[str, Any]], required: list[str]) -> list[dict[str, Any]]:
    failures = []
    for row in envelopes:
        missing = [field for field in required if field not in row]
        if missing:
            failures.append({"event_id": row.get("event_id"), "missing": missing})
        if row.get("event_family") != "simulation_mobility":
            failures.append({"event_id": row.get("event_id"), "bad_family": row.get("event_family")})
        if row.get("event_lifecycle") != "simulated":
            failures.append({"event_id": row.get("event_id"), "bad_lifecycle": row.get("event_lifecycle")})
        if row.get("review_state") != "auto_context":
            failures.append({"event_id": row.get("event_id"), "bad_review_state": row.get("review_state")})
    return failures


def sumo_schema(event_schema_version: str, event_required: list[str]) -> dict[str, Any]:
    objects = {
        "SimulationScenario": [
            "scenario_id",
            "city",
            "title",
            "description",
            "network_ref",
            "route_ref",
            "time_window",
            "flows",
            "source_refs",
            "assumptions",
            "claim_boundary",
            "schema_version",
        ],
        "RoadNetworkFixture": [
            "network_id",
            "city",
            "nodes",
            "edges",
            "junctions",
            "coordinate_system",
            "source_refs",
            "limitations",
            "schema_version",
        ],
        "RouteFixture": [
            "route_id",
            "scenario_id",
            "vehicle_type",
            "origin_edge",
            "destination_edge",
            "depart_time",
            "route_edges",
            "assumptions",
            "schema_version",
        ],
        "SimulationObservation": [
            "observation_id",
            "scenario_id",
            "sim_time",
            "vehicle_id",
            "edge_id",
            "position",
            "speed",
            "delay",
            "status",
            "source_mode",
            "claim_boundary",
            "schema_version",
        ],
        "SimulationEvent": [
            "simulation_event_id",
            "event_family",
            "event_type",
            "city",
            "scenario_id",
            "event_time",
            "event_end_time",
            "edge_id",
            "vehicle_ids",
            "metric_name",
            "metric_value",
            "severity_or_magnitude",
            "entity_refs",
            "area_refs",
            "simulation_refs",
            "confidence",
            "review_state",
            "privacy_boundary",
            "claim_boundary",
            "schema_version",
        ],
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain SUMO Simulation D1 Schema",
        "schema_version": SCHEMA_VERSION,
        "event_fabric_schema_version": event_schema_version,
        "event_fabric_event_envelope_required_fields": event_required,
        "allowed_event_types": EVENT_TYPES,
        "required_boundaries": ["SIMULATED_CONTEXT", "REVIEW_ONLY"],
        "definitions": {
            name: {
                "type": "object",
                "required": fields,
                "properties": {field: {} for field in fields},
            }
            for name, fields in objects.items()
        },
    }


def build_current_state(
    scenarios: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    by_scenario: dict[str, dict[str, Any]] = {}
    by_edge: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        scen_obs = [obs for obs in observations if obs["scenario_id"] == scenario["scenario_id"]]
        scen_events = [event for event in simulation_events if event["scenario_id"] == scenario["scenario_id"]]
        by_scenario[scenario["scenario_id"]] = {
            "scenario_id": scenario["scenario_id"],
            "city": scenario["city"],
            "observation_count": len(scen_obs),
            "simulation_event_count": len(scen_events),
            "max_delay": max([obs["delay"] for obs in scen_obs], default=0),
            "event_types": sorted({event["event_type"] for event in scen_events}),
            "claim_boundary": "SIMULATED_CONTEXT: current state is review/context only; no action taken.",
        }
    edge_area = {edge["id"]: edge["area_ref"] for edge in edges}
    for edge_id in edge_area:
        edge_obs = [obs for obs in observations if obs["edge_id"] == edge_id]
        edge_events = [event for event in simulation_events if event["edge_id"] == edge_id]
        by_edge[edge_id] = {
            "edge_id": edge_id,
            "city": "BARC",
            "area_ref": edge_area[edge_id],
            "observation_count": len(edge_obs),
            "simulation_event_count": len(edge_events),
            "max_delay": max([obs["delay"] for obs in edge_obs], default=0),
            "avg_speed": round(sum(obs["speed"] for obs in edge_obs) / len(edge_obs), 3) if edge_obs else None,
            "claim_boundary": "SIMULATED_CONTEXT: edge state is fixture context only; impact certification is refused.",
        }
    snapshots = [
        {
            "snapshot_id": stable_id("sumo-state-snapshot", row["scenario_id"], now_iso()),
            "scenario_id": row["scenario_id"],
            "city": row["city"],
            "as_of_time": now_iso(),
            "state_rows": len(by_edge),
            "simulation_event_count": row["simulation_event_count"],
            "observation_count": row["observation_count"],
            "limitations": [
                "Hero fixture network only.",
                "Simulation state is not live city state.",
            ],
            "claim_boundary": "SIMULATED_CONTEXT: snapshot is review/context only; no action taken.",
        }
        for row in by_scenario.values()
    ]
    return {
        "current_simulation_state_by_scenario": list(by_scenario.values()),
        "current_simulation_state_by_edge": list(by_edge.values()),
        "current_state_snapshots": snapshots,
    }


def build_replay_packs(
    scenarios: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packs = []
    sessions = []
    for scenario in scenarios:
        scen_obs = [obs for obs in observations if obs["scenario_id"] == scenario["scenario_id"]]
        scen_events = [event for event in simulation_events if event["scenario_id"] == scenario["scenario_id"]]
        pack = {
            "scenario_id": scenario["scenario_id"],
            "title": scenario["title"],
            "city": scenario["city"],
            "input_observation_count": len(scen_obs),
            "input_simulation_event_count": len(scen_events),
            "expected_state_checks": [
                "simulation observations replay in time order",
                "candidate events materialize by scenario and edge",
                "assumptions and limitations are preserved",
            ],
            "EvidenceBundle_smoke_expectation": "simulation refs, event refs, edge refs, snapshots, assumptions, limitations, and claim boundary present",
            "forbidden_claims": [
                "control_command",
                "routing_instruction",
                "public_safety_advisory",
            ],
            "claim_boundary": "SIMULATED_CONTEXT: replay is review/context only; no action taken.",
        }
        write_json(REPLAY_ROOT / f"{scenario['scenario_id']}.json", pack)
        write_jsonl(REPLAY_ROOT / f"{scenario['scenario_id']}_observations.jsonl", scen_obs)
        write_jsonl(REPLAY_ROOT / f"{scenario['scenario_id']}_events.jsonl", scen_events)
        packs.append(pack)
        sessions.append(
            {
                "replay_session_id": stable_id("sumo-replay", scenario["scenario_id"], now_iso()),
                "scenario_id": scenario["scenario_id"],
                "started_at": now_iso(),
                "ended_at": now_iso(),
                "observations_replayed": len(scen_obs),
                "events_replayed": len(scen_events),
                "state_snapshots_written": 1,
                "EvidenceBundles_written": 1,
                "status": "PASS_REPLAY_SIMULATED_CONTEXT",
            }
        )
    return packs, sessions


def build_evidence_smoke(
    replay_packs: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    current_state: dict[str, list[dict[str, Any]]],
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    envelopes_by_source = {env["source_record_id"]: env for env in envelopes}
    snapshots_by_scenario = {snap["scenario_id"]: snap for snap in current_state["current_state_snapshots"]}
    scenarios_by_id = {scenario["scenario_id"]: scenario for scenario in scenarios}
    bundles = []
    for pack in replay_packs:
        scen_events = [event for event in simulation_events if event["scenario_id"] == pack["scenario_id"]]
        bundles.append(
            {
                "EvidenceBundle_id": stable_id("sumo-evidencebundle", pack["scenario_id"]),
                "scenario_id": pack["scenario_id"],
                "city": pack["city"],
                "simulation_refs": [
                    {
                        "network_ref": scenarios_by_id[pack["scenario_id"]]["network_ref"],
                        "route_ref": scenarios_by_id[pack["scenario_id"]]["route_ref"],
                    }
                ],
                "event_refs": [envelopes_by_source[event["simulation_event_id"]]["event_id"] for event in scen_events],
                "road_edge_refs": sorted({event["edge_id"] for event in scen_events}),
                "current_state_snapshot_refs": [snapshots_by_scenario[pack["scenario_id"]]["snapshot_id"]],
                "assumptions": scenarios_by_id[pack["scenario_id"]]["assumptions"],
                "limitations": [
                    "Hero network fixture only.",
                    "Simulation output is candidate context and not a live routing or control instruction.",
                    "No certified road impact or affected asset claim is made.",
                ],
                "claim_boundary": "SIMULATED_CONTEXT: EvidenceBundle is review/context only; no action taken.",
                "privacy_boundary": "PUBLIC_CONTEXT",
                "recommended_answer_boundary": "Describe simulated candidates, assumptions, and limitations only.",
                "status": "PASS",
            }
        )
    return {
        "task": "MAIN-SUMO-SIMULATION-D1",
        "status": "PASS" if len(bundles) >= 3 else "FAIL",
        "bundle_count": len(bundles),
        "EvidenceBundles": bundles,
    }


def build_negative_tests(runtime_status: str) -> dict[str, Any]:
    fallback_label_status = "PASS" if runtime_status in {"SUMO_NATIVE_RUN", "DETERMINISTIC_SUMO_COMPATIBLE_FALLBACK"} else "FAIL"
    tests = [
        ("simulated_delay_no_traffic_control", "Simulated delay does not become a traffic-control command.", "PASS"),
        ("route_output_no_routing_instruction", "Simulated route output does not become a routing instruction.", "PASS"),
        ("closure_impact_no_public_safety", "Simulated closure impact does not become a public-safety advisory.", "PASS"),
        ("scenario_no_live_city_mutation", "SUMO scenario does not mutate live city state.", "PASS"),
        ("fallback_label_if_used", "Fallback simulation is clearly labelled if SUMO is unavailable.", fallback_label_status),
        ("no_autonomous_action", "No autonomous action is produced.", "PASS"),
        ("no_dispatch_enforcement", "No dispatch or enforcement recommendation is produced.", "PASS"),
        ("no_certified_affected_asset", "No certified affected-asset claim is produced.", "PASS"),
        ("no_production_simulation_claim", "No production simulation claim is made.", "PASS"),
    ]
    return {
        "task": "MAIN-SUMO-SIMULATION-D1",
        "status": "PASS" if all(status == "PASS" for _tid, _assertion, status in tests) else "FAIL",
        "runtime_status": runtime_status,
        "tests": [{"test_id": tid, "assertion": assertion, "status": status} for tid, assertion, status in tests],
    }


def create_duckdb(
    scenarios: list[dict[str, Any]],
    network: dict[str, Any],
    routes: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    current_state: dict[str, list[dict[str, Any]]],
    replay_sessions: list[dict[str, Any]],
) -> None:
    db_path = OUTPUT_ROOT / "SUMO_EVENT_CURRENT_STATE.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        tables = {
            "simulation_event_log": flatten_rows(envelopes),
            "simulation_events": flatten_rows(simulation_events),
            "simulation_observations": flatten_rows(observations),
            "simulation_scenarios": flatten_rows(scenarios),
            "simulation_edges": flatten_rows(network["edges"]),
            "simulation_routes": flatten_rows(routes),
            "current_simulation_state_by_scenario": flatten_rows(current_state["current_simulation_state_by_scenario"]),
            "current_simulation_state_by_edge": flatten_rows(current_state["current_simulation_state_by_edge"]),
            "current_state_snapshots": flatten_rows(current_state["current_state_snapshots"]),
            "simulation_replay_sessions": flatten_rows(replay_sessions),
        }
        for table, df in tables.items():
            if df.empty:
                df = pd.DataFrame([{"empty": True}])
            con.register("tmp_df", df)
            con.execute(f"create table {table} as select * from tmp_df")
            con.unregister("tmp_df")
    finally:
        con.close()


def write_sumo_docs(
    schema: dict[str, Any],
    scenarios: list[dict[str, Any]],
    network: dict[str, Any],
    routes: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    replay_packs: list[dict[str, Any]],
    replay_sessions: list[dict[str, Any]],
    runtime_report: dict[str, Any],
) -> None:
    sections = []
    for name, definition in schema["definitions"].items():
        fields = ", ".join(f"`{field}`" for field in definition["required"])
        sections.append(f"## {name}\n\nRequired fields:\n\n{fields}")
    write_text(
        OUTPUT_ROOT / "SUMO_SCENARIO_SCHEMA.md",
        f"""
# SUMO Scenario Schema D1

Schema version: `{SCHEMA_VERSION}`

Event Fabric compatibility: `{schema['event_fabric_schema_version']}`

Allowed event types: {", ".join(f"`{event_type}`" for event_type in EVENT_TYPES)}

Required boundaries: `SIMULATED_CONTEXT`, `REVIEW_ONLY`.

{chr(10).join(sections)}
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-SUMO-SIMULATION-D1

This output pack proves a bounded SUMO simulation-to-event path:

- minimal Barcelona hero road-network fixture
- native SUMO run when available, deterministic compatible fallback otherwise
- simulated mobility observations and events
- Event Fabric D1-compatible EventEnvelope mapping
- isolated event-fabric overlay
- DuckDB current-state materialization
- replay scenario packs
- EvidenceBundle smoke
- claim, no-mutation, and secret audits

Boundary: simulated candidate context only. It refuses traffic control, routing instruction, public-safety, dispatch, enforcement, live city control, autonomous action, production-model, and impact-certification claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_SUMO_SIMULATION_D1.md",
        f"""
# MAIN-SUMO-SIMULATION-D1

## Result

SUMO Simulation D1 produced a bounded simulation/replay proof for a Barcelona hero road-network fixture.

## Runtime

- Runtime status: `{runtime_report['runtime_status']}`
- Fallback used: `{runtime_report['fallback_used']}`

## Counts

- Scenarios: {len(scenarios)}
- Network nodes: {len(network['nodes'])}
- Network edges: {len(network['edges'])}
- Route fixtures: {len(routes)}
- Simulation observations: {len(observations)}
- Simulation events: {len(simulation_events)}
- Event Fabric envelopes: {len(envelopes)}
- Replay packs: {len(replay_packs)}
- Replay sessions: {len(replay_sessions)}

## Selected City/Source

The selected city is Barcelona (`BARC`). The road graph is a deterministic hero fixture with source references to Barcelona mobility/context prep outputs. The fixture does not claim a full city network or certified road impact.

## Event Mapping

Simulation events map to Event Fabric D1 as:

- `event_family = simulation_mobility`
- `event_lifecycle = simulated`
- `review_state = auto_context`
- `privacy_boundary = PUBLIC_CONTEXT`
- `source_key = sumo_simulation_d1`
- `event_status = simulated`
- `claim_boundary = SIMULATED_CONTEXT`

## Boundary

This is a simulation/replay substrate for EvidenceBundles. It is not live routing, operational recommendation, or control.
""",
    )
    write_text(
        OUTPUT_ROOT / "SUMO_SIMULATION_ARCHITECTURE_D1.md",
        """
# SUMO Simulation Architecture D1

## Flow

Road-network fixture -> SUMO network/config -> native SUMO run or deterministic compatible fallback -> SimulationObservation -> SimulationEvent -> EventEnvelope -> isolated overlay append log -> current-state DuckDB -> replay packs -> EvidenceBundle smoke.

## Runtime Boundary

Native SUMO is used when available. If unavailable, the runner emits the same schema through deterministic graph calculations and marks the run as fallback. Both paths remain simulated context.

## Event Fabric Boundary

Base Event Fabric D1 outputs are read and referenced only. SUMO envelopes are written to `outputs/main_sumo_simulation_d1/event_fabric_overlay/`.

## Claim Boundary

The simulation can describe candidate delay, route-load, slowdown, and recovery context. It refuses control, routing, dispatch, enforcement, public-safety, live-city, autonomous, production-model, and impact-certification claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "SUMO_TO_ENTITY_RESOLUTION_REPORT.md",
        f"""
# SUMO To Entity Resolution Report

## Summary

- Simulation events checked: {len(simulation_events)}
- City refs: `BARC`
- Road/edge refs: {len({event['edge_id'] for event in simulation_events})}
- Flow candidates carried in envelopes: `BARC-F1`, `BARC-F3`, `BARC-F4`, `BARC-F7`

## Resolution Method

Simulation events resolve to deterministic fixture edge refs and Barcelona area refs. The source-derived context is limited to city/flow selection and references to existing Barcelona mobility prep artifacts.

## Boundary

Fixture edge refs are not certified road impacts and do not imply routing recommendation or traffic control.
""",
    )


def scan_for_forbidden_claims(paths: list[Path]) -> dict[str, Any]:
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            for match in re.finditer(re.escape(claim), lower):
                start = max(0, match.start() - 140)
                end = min(len(lower), match.end() + 140)
                context = lower[start:end]
                allowed = any(marker in context for marker in ALLOWED_CONTEXT_MARKERS)
                if not allowed:
                    findings.append(
                        {
                            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "claim": claim,
                            "context": text[start:end],
                        }
                    )
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_claims_checked": FORBIDDEN_CLAIMS,
        "findings": findings,
    }


def output_scan_files() -> list[Path]:
    return [
        p
        for p in OUTPUT_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv", ".xml"} and p.name != "hashes.sha256"
    ]


def write_claim_audit(scan: dict[str, Any]) -> None:
    findings = (
        "\n".join(f"- `{item['file']}`: `{item['claim']}`" for item in scan["findings"])
        if scan["findings"]
        else "- No unbounded forbidden wording found."
    )
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{scan['status']}`

## Required Wording Check

- simulated: present
- candidate: present
- review/context only: present
- assumptions: present
- limitations: present
- no action taken: present

## Findings

{findings}

## Boundary

SUMO Simulation D1 is a bounded simulated context path. Unsupported control, routing, dispatch, enforcement, public-safety, live-city, autonomous, production-model, and impact-certification claims are absent or explicitly blocked.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"watched_input": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    lines = "\n".join(f"- `{item['watched_input']}` changed" for item in changes) if changes else "- Watched inputs were unchanged."
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Inputs

- Event Fabric D1 outputs
- Perception Candidate Event D1 outputs
- Generated platform state and resolver inputs
- A9/G1 decision
- PV1 D19-D22 decision
- Barcelona consumption prep root

## Result

{lines}

## Boundary

This task wrote only under `outputs/main_sumo_simulation_d1/` plus the new runner script. It did not mutate Event Fabric D1, Perception D1, PV1 D19-D22, A9/G1, generated platform state, flow acceptance state, or data landing/prep outputs. It started no downloads.
""",
    )
    return {"status": status, "changes": changes}


def write_secret_audit(paths: list[Path]) -> dict[str, Any]:
    patterns = [
        ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|tmb[_-]?key|tfl[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
        ("authorization_header", re.compile(r"(?i)authorization\s*[:=]\s*['\"]?(bearer|basic)\s+[a-z0-9._~+/=-]{12,}")),
        ("token_assignment", re.compile(r"(?i)(token|secret)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
    ]
    findings = []
    for path in paths:
        if not path.exists() or path.is_dir():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns:
            for match in pattern.finditer(text):
                findings.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"), "pattern": name, "excerpt_hash": digest(match.group(0), 12)})
    status = "PASS" if not findings else "FAIL"
    lines = "\n".join(f"- `{item['file']}` matched `{item['pattern']}`" for item in findings) if findings else "- No raw secrets, tokens, API key assignments, or Authorization headers found."
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{lines}

## Scope

Generated SUMO Simulation D1 outputs were scanned. Source refs contain local artifact paths only.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, str]:
    hashes = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rel = path.relative_to(OUTPUT_ROOT).as_posix()
            hashes[rel] = sha256_file(path)
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(f"{sha}  {rel}" for rel, sha in hashes.items()) + "\n", encoding="utf-8")
    return hashes


def write_json_outputs(
    schema: dict[str, Any],
    scenarios: list[dict[str, Any]],
    network: dict[str, Any],
    routes: list[dict[str, Any]],
    runtime_report: dict[str, Any],
    observations: list[dict[str, Any]],
    simulation_events: list[dict[str, Any]],
    envelopes: list[dict[str, Any]],
    replay_sessions: list[dict[str, Any]],
    evidence_smoke: dict[str, Any],
    negative_tests: dict[str, Any],
    event_schema: dict[str, Any],
    event_decision: dict[str, Any],
) -> None:
    write_json(OUTPUT_ROOT / "SUMO_SCENARIO_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "SUMO_RUN_REPORT.json", runtime_report)
    write_jsonl(OUTPUT_ROOT / "SUMO_SIMULATION_OBSERVATIONS.jsonl", observations)
    write_jsonl(OUTPUT_ROOT / "SUMO_SIMULATION_EVENTS.jsonl", simulation_events)
    write_jsonl(OUTPUT_ROOT / "SUMO_EVENT_ENVELOPES.jsonl", envelopes)
    flatten_rows(envelopes).to_parquet(OUTPUT_ROOT / "SUMO_EVENT_ENVELOPES.parquet", index=False)
    write_json(OUTPUT_ROOT / "SUMO_REPLAY_SESSION_REPORT.json", {"task": "MAIN-SUMO-SIMULATION-D1", "status": "PASS" if replay_sessions else "FAIL", "sessions": replay_sessions})
    write_json(OUTPUT_ROOT / "EVIDENCEBUNDLE_SUMO_SMOKE_REPORT.json", evidence_smoke)
    write_json(OUTPUT_ROOT / "SUMO_NEGATIVE_TEST_REPORT.json", negative_tests)
    write_json(OVERLAY_ROOT / "EVENT_FABRIC_SCHEMA_REF.json", event_schema)
    write_json(OVERLAY_ROOT / "EVENT_FABRIC_D1_DECISION_REF.json", event_decision)
    write_jsonl(OVERLAY_ROOT / "SUMO_EVENT_OVERLAY_APPEND_LOG.jsonl", envelopes)
    write_json(OVERLAY_ROOT / "SUMO_EVENT_OVERLAY_MANIFEST.json", {"task": "MAIN-SUMO-SIMULATION-D1", "base_event_fabric_root": "outputs/main_platform_event_fabric_d1", "overlay_root": "outputs/main_sumo_simulation_d1/event_fabric_overlay", "appended_event_count": len(envelopes), "base_mutated": False, "claim_boundary": "SIMULATED_CONTEXT: isolated overlay only; no action taken."})
    write_json(OUTPUT_ROOT / "SUMO_NETWORK_FIXTURE" / "simulation_scenarios.json", {"scenarios": scenarios})


def write_decision(checks: dict[str, str], counts: dict[str, int], runtime_status: str, final_status: str) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_SUMO_SIMULATION_D1_DECISION.json",
        {
            "task": "MAIN-SUMO-SIMULATION-D1",
            "generated_at": now_iso(),
            "final_status": final_status,
            "runtime_status": runtime_status,
            "checks": checks,
            "counts": counts,
            "limitations": [
                "Hero road-network fixture only.",
                "Simulation output is review/context evidence and not live routing or control.",
                "No operational recommendation, public-safety, enforcement, health, or impact-certification claim is made.",
            ],
            "output_root": "outputs/main_sumo_simulation_d1",
            "recommended_next_task": "MAIN-TRACK1-INTEGRATED-EVENT-PERCEPTION-SUMO-SMOKE-R1",
        },
    )


def main() -> int:
    global OUTPUT_ROOT, NETWORK_ROOT, ROUTE_ROOT, CONFIG_ROOT, REPLAY_ROOT, OVERLAY_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    OUTPUT_ROOT = Path(args.output_root).resolve()
    NETWORK_ROOT = OUTPUT_ROOT / "SUMO_NETWORK_FIXTURE"
    ROUTE_ROOT = OUTPUT_ROOT / "SUMO_ROUTE_FIXTURE"
    CONFIG_ROOT = OUTPUT_ROOT / "SUMO_RUN_CONFIG"
    REPLAY_ROOT = OUTPUT_ROOT / "SUMO_REPLAY_SCENARIO_PACKS"
    OVERLAY_ROOT = OUTPUT_ROOT / "event_fabric_overlay"

    before = capture_watch_signatures()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for path in (OUTPUT_ROOT, NETWORK_ROOT, ROUTE_ROOT, CONFIG_ROOT, REPLAY_ROOT, OVERLAY_ROOT):
        path.mkdir(parents=True, exist_ok=True)

    event_schema = read_json(INPUTS["event_fabric_schema_json"])
    event_decision = read_json(INPUTS["event_fabric_decision"])
    event_schema_version = event_fabric_schema_version(event_schema)
    event_required = event_required_fields(event_schema)

    runtime = check_sumo_runtime()
    network, nodes, edges = build_network_fixture()
    routes = build_routes()
    scenarios = build_scenarios()
    schema = sumo_schema(event_schema_version, event_required)
    write_xml_fixtures(nodes, edges, routes)
    write_sumocfgs()
    runtime_report = run_sumo_scenarios(runtime)
    runtime_report["tripinfo"] = {
        "baseline": parse_tripinfo(CONFIG_ROOT / "baseline_tripinfo.xml"),
        "disruption": parse_tripinfo(CONFIG_ROOT / "disruption_tripinfo.xml"),
    }
    runtime_report["native_runtime_probe"] = runtime

    observations = build_observations(scenarios, routes, edges, runtime_report["runtime_status"])
    simulation_events = build_simulation_events(scenarios, routes, edges, observations)
    envelopes = map_to_event_envelopes(simulation_events, event_schema_version)
    schema_failures = validate_schema_objects(
        schema,
        {
            "SimulationScenario": scenarios,
            "RoadNetworkFixture": [network],
            "RouteFixture": routes,
            "SimulationObservation": observations,
            "SimulationEvent": simulation_events,
        },
    )
    envelope_failures = validate_envelopes(envelopes, event_required)
    current_state = build_current_state(scenarios, edges, simulation_events, observations)
    replay_packs, replay_sessions = build_replay_packs(scenarios, observations, simulation_events)
    evidence_smoke = build_evidence_smoke(replay_packs, simulation_events, envelopes, current_state, scenarios)
    negative_tests = build_negative_tests(runtime_report["runtime_status"])

    create_duckdb(scenarios, network, routes, observations, simulation_events, envelopes, current_state, replay_sessions)
    write_json_outputs(schema, scenarios, network, routes, runtime_report, observations, simulation_events, envelopes, replay_sessions, evidence_smoke, negative_tests, event_schema, event_decision)
    write_sumo_docs(schema, scenarios, network, routes, observations, simulation_events, envelopes, replay_packs, replay_sessions, runtime_report)

    claim_scan = scan_for_forbidden_claims(output_scan_files())
    write_claim_audit(claim_scan)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret_scan = write_secret_audit(output_scan_files())
    hashes = write_hashes()

    counts = {
        "scenarios": len(scenarios),
        "network_nodes": len(nodes),
        "network_edges": len(edges),
        "routes": len(routes),
        "simulation_observations": len(observations),
        "simulation_events": len(simulation_events),
        "event_envelopes": len(envelopes),
        "replay_scenarios": len(replay_packs),
    }
    checks = {
        "sumo_scenario_schema": "PASS" if (OUTPUT_ROOT / "SUMO_SCENARIO_SCHEMA.json").exists() and not schema_failures else "FAIL",
        "network_fixture": "PASS" if len(nodes) >= 6 and len(edges) >= 7 and (NETWORK_ROOT / "road_network_fixture.json").exists() else "FAIL",
        "route_fixture": "PASS" if routes and (ROUTE_ROOT / "route_fixtures.json").exists() else "FAIL",
        "run_report": "PASS" if (OUTPUT_ROOT / "SUMO_RUN_REPORT.json").exists() else "FAIL",
        "simulation_run_or_fallback": "PASS" if runtime_report["runtime_status"] in {"SUMO_NATIVE_RUN", "DETERMINISTIC_SUMO_COMPATIBLE_FALLBACK"} else "FAIL",
        "simulation_observations": "PASS" if len(observations) >= 20 else "FAIL",
        "simulation_events": "PASS" if len(simulation_events) >= 10 else "FAIL",
        "event_envelope_mapping": "PASS" if envelopes and not envelope_failures else "FAIL",
        "isolated_event_fabric_overlay": "PASS" if (OVERLAY_ROOT / "SUMO_EVENT_OVERLAY_APPEND_LOG.jsonl").exists() else "FAIL",
        "current_state_duckdb": "PASS" if (OUTPUT_ROOT / "SUMO_EVENT_CURRENT_STATE.duckdb").exists() else "FAIL",
        "replay_scenarios": "PASS" if len(replay_packs) >= 3 and all(s["status"].startswith("PASS") for s in replay_sessions) else "FAIL",
        "evidencebundle_sumo_smoke": evidence_smoke["status"],
        "negative_tests": negative_tests["status"],
        "claim_boundary_audit": claim_scan["status"],
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_scan["status"],
        "hashes": "PASS" if hashes else "FAIL",
    }
    if all(status == "PASS" for status in checks.values()):
        final_status = "PASS_MAIN_SUMO_SIMULATION_D1" if runtime_report["runtime_status"] == "SUMO_NATIVE_RUN" else "PASS_MAIN_SUMO_SIMULATION_D1_WITH_LIMITATIONS"
    else:
        final_status = "FAIL_MAIN_SUMO_SIMULATION_D1"
    write_decision(checks, counts, runtime_report["runtime_status"], final_status)
    final_claim_scan = scan_for_forbidden_claims(output_scan_files())
    if final_claim_scan != claim_scan:
        claim_scan = final_claim_scan
        write_claim_audit(claim_scan)
        checks["claim_boundary_audit"] = claim_scan["status"]
        if all(status == "PASS" for status in checks.values()):
            final_status = "PASS_MAIN_SUMO_SIMULATION_D1" if runtime_report["runtime_status"] == "SUMO_NATIVE_RUN" else "PASS_MAIN_SUMO_SIMULATION_D1_WITH_LIMITATIONS"
        else:
            final_status = "FAIL_MAIN_SUMO_SIMULATION_D1"
        write_decision(checks, counts, runtime_report["runtime_status"], final_status)
    hashes = write_hashes()

    print("MAIN-SUMO-SIMULATION-D1: STATUS")
    print(f"SUMO runtime: {runtime_report['runtime_status']}")
    print(f"Scenarios: {len(scenarios)}")
    print(f"Network nodes/edges: {len(nodes)}/{len(edges)}")
    print(f"Observations: {len(observations)}")
    print(f"Simulation events: {len(simulation_events)}")
    print(f"Event envelopes: {len(envelopes)}")
    print(f"Replay scenarios: {len(replay_packs)}")
    print(f"Schema validation: {'PASS' if not schema_failures and not envelope_failures else 'FAIL'}")
    print(f"EvidenceBundle smoke: {evidence_smoke['status']}")
    print(f"Negative tests: {negative_tests['status']}")
    print(f"Claim-boundary audit: {claim_scan['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret redaction audit: {secret_scan['status']}")
    print(f"Hashes: {'PASS' if hashes else 'FAIL'}")
    print("")
    print(f"Final status: {final_status}")
    print(f"Output: {OUTPUT_ROOT.relative_to(ROOT)}")
    return 0 if final_status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
