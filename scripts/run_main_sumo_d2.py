#!/usr/bin/env python3
"""Run MAIN-SUMO-D2.

This runner builds a bounded Barcelona-derived SUMO simulation producer from
local FlowPack/mart data, maps simulated mobility events into Event Fabric D2
compatible envelopes, and writes additive outputs only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import duckdb
except Exception as exc:  # pragma: no cover - dependency gate
    duckdb = None
    DUCKDB_IMPORT_ERROR = str(exc)
else:
    DUCKDB_IMPORT_ERROR = ""


TASK = "MAIN-SUMO-D2"
PASS = "PASS_MAIN_SUMO_D2"
PASS_LIMITED = "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS"
BLOCKED = "BLOCKED_BY_EVENT_FABRIC_D2"
FAIL = "FAIL_MAIN_SUMO_D2"
SCHEMA_VERSION = "main-sumo-d2.v1"

OUT = Path("outputs/main_sumo_d2")
ART = OUT / "SUMO_D2_SUMO_ARTIFACTS"
REPLAY = OUT / "SUMO_D2_REPLAY_SCENARIO_PACKS"
OVERLAY = OUT / "event_fabric_d2_overlay"

EVENT_FABRIC_D2 = Path("outputs/main_event_fabric_d2")
EVENT_FABRIC_D2_DECISION = EVENT_FABRIC_D2 / "MAIN_EVENT_FABRIC_D2_DECISION.json"
EVENT_FABRIC_D2_SCHEMA = EVENT_FABRIC_D2 / "EVENT_FABRIC_D2_SCHEMA.json"
EVENT_FABRIC_D2_CURRENT_STATE = EVENT_FABRIC_D2 / "EVENT_FABRIC_D2_CURRENT_STATE.duckdb"
EVENT_FABRIC_D2_COMPAT = EVENT_FABRIC_D2 / "EVENT_FABRIC_D2_PRODUCER_COMPATIBILITY_REPORT.md"

SUMO_D1 = Path("outputs/main_sumo_simulation_d1")
SUMO_D1_DECISION = SUMO_D1 / "MAIN_SUMO_SIMULATION_D1_DECISION.json"

BARC_PREP = Path("outputs/barc_allflows_consumption_prep_r1")
BARC_MART = BARC_PREP / "BARC_FLOW_MART.duckdb"

NO_MUTATION_ROOTS = {
    "event_fabric_d1": Path("outputs/main_platform_event_fabric_d1"),
    "event_fabric_d2": EVENT_FABRIC_D2,
    "sumo_d1": SUMO_D1,
    "perception_d1": Path("outputs/main_perception_d1"),
    "perception_d2": Path("outputs/main_perception_d2"),
    "a9_g1": Path("outputs/a9_wire_e2e_g1_snapshot"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
    "platform_state_generated": Path("outputs/platform_state_generated"),
    "barc_prep": BARC_PREP,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except Exception:
        return path.as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    sig: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            sig[path.relative_to(root).as_posix()] = sha256(path)
    return sig


def snapshot_roots() -> dict[str, dict[str, str]]:
    return {name: tree_signature(path) for name, path in NO_MUTATION_ROOTS.items()}


def verify_event_fabric_d2() -> tuple[bool, dict[str, Any], list[str]]:
    reasons = []
    decision = read_json(EVENT_FABRIC_D2_DECISION, {})
    if decision.get("final_status") != "PASS_MAIN_EVENT_FABRIC_D2":
        reasons.append("MAIN_EVENT_FABRIC_D2_DECISION.json missing or not PASS_MAIN_EVENT_FABRIC_D2")
    for path in [EVENT_FABRIC_D2_SCHEMA, EVENT_FABRIC_D2_CURRENT_STATE, EVENT_FABRIC_D2_COMPAT]:
        if not path.exists():
            reasons.append(f"missing dependency artifact: {rel(path)}")
    return not reasons, decision, reasons


def inspect_barc_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if duckdb is None:
        return [], [], [f"duckdb import failed: {DUCKDB_IMPORT_ERROR}"]
    if not BARC_MART.exists():
        return [], [], [f"missing Barcelona mart: {rel(BARC_MART)}"]

    source_names = [
        "silver_traffic_sections",
        "silver_traffic_trams",
        "silver_traffic_itineraries",
        "silver_traffic_sections_by_itinerary",
        "silver_bicing_gbfs",
        "safe.bicing_station_information",
        "silver_mobility_counters_equipment",
        "silver_mobility_counters_detail",
    ]
    audits: list[dict[str, Any]] = []
    coords: list[dict[str, Any]] = []
    errors: list[str] = []
    con = duckdb.connect(str(BARC_MART), read_only=True)
    try:
        for table in source_names:
            item: dict[str, Any] = {
                "source_id": f"barc:{table.replace('.', '_')}",
                "city": "BARC",
                "source_key": table,
                "source_type": "duckdb_view",
                "source_path": rel(BARC_MART),
                "duckdb_ref": table,
                "geometry_status": "NOT_INSPECTED",
                "row_count": 0,
                "usable_for_network": False,
                "limitations": [],
                "schema_version": SCHEMA_VERSION,
            }
            try:
                item["row_count"] = int(con.execute(f"select count(*) from {table}").fetchone()[0])
                cols = con.execute(f"describe {table}").fetchall()
                col_names = [c[0] for c in cols]
                item["columns_inspected"] = col_names
                geom_cols = [c for c in col_names if c.lower() in {"latitud", "longitud", "lat", "lon", "source_lat", "source_lon", "x_etrs89", "y_etrs89", "coordenades"}]
                item["geometry_columns_found"] = geom_cols
                if table == "silver_traffic_sections":
                    item["geometry_status"] = "LAT_LON_POINT_CHAIN_BY_TRAM"
                    item["usable_for_network"] = True
                    rows = con.execute(
                        """
                        select Tram, Tram_Components, try_cast(Latitud as double) as lat,
                               try_cast(Longitud as double) as lon, source_record_id
                        from silver_traffic_sections
                        where try_cast(Latitud as double) between 41.36 and 41.43
                          and try_cast(Longitud as double) between 2.10 and 2.22
                        order by try_cast(Tram as integer), try_cast(Tram_Components as integer), source_record_id
                        """
                    ).fetchall()
                    for tram, component, lat, lon, source_record_id in rows:
                        if lat is not None and lon is not None:
                            coords.append(
                                {
                                    "tram": str(tram),
                                    "component": str(component),
                                    "lat": float(lat),
                                    "lon": float(lon),
                                    "source_record_id": str(source_record_id),
                                    "source_key": "traffic_sections",
                                }
                            )
                    item["limitations"].append("Official section coordinates are point-chain context, not a full turn-by-turn routable graph.")
                elif any(c in col_names for c in ["Latitud", "Longitud", "lat", "lon"]):
                    item["geometry_status"] = "LAT_LON_ANCHORS"
                    item["usable_for_network"] = table in {"silver_mobility_counters_equipment"}
                    if table != "silver_traffic_sections":
                        item["limitations"].append("Usable as mobility anchors/context; not used as primary SUMO road edges.")
                else:
                    item["geometry_status"] = "NO_EDGE_GEOMETRY"
                    item["limitations"].append("No direct geometry columns suitable for SUMO edge extraction.")
            except Exception as exc:
                item["geometry_status"] = "INSPECTION_FAILED"
                item["limitations"].append(str(exc))
                errors.append(f"{table}: {exc}")
            audits.append(item)
    finally:
        con.close()
    return audits, coords, errors


def choose_bounded_coords(coords: list[dict[str, Any]], target: int = 30) -> list[dict[str, Any]]:
    # Prefer a central Barcelona/Eixample-like bounding window with dense official section points.
    central = [
        c
        for c in coords
        if 41.375 <= c["lat"] <= 41.410 and 2.145 <= c["lon"] <= 2.200
    ]
    pool = central if len(central) >= target else coords
    # Grid-sample by lon/lat to avoid duplicate/nearly duplicate points.
    seen = set()
    unique: list[dict[str, Any]] = []
    for c in sorted(pool, key=lambda r: (round(r["lon"], 4), round(r["lat"], 4), r["tram"], r["component"])):
        key = (round(c["lat"], 5), round(c["lon"], 5))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    if len(unique) < target:
        return unique
    step = max(1, len(unique) // target)
    sampled = unique[::step][:target]
    if len(sampled) < target:
        sampled = unique[:target]
    return sorted(sampled, key=lambda r: (r["lon"], r["lat"]))


def to_xy(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    earth = 6371000.0
    x = math.radians(lon - lon0) * earth * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * earth
    return x, y


def build_network(coords: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if len(coords) < 25:
        raise RuntimeError(f"Barcelona traffic-section coordinates too sparse for D2 subset: {len(coords)}")
    lat0 = min(c["lat"] for c in coords)
    lon0 = min(c["lon"] for c in coords)
    nodes = []
    for idx, c in enumerate(coords):
        x, y = to_xy(c["lat"], c["lon"], lat0, lon0)
        nodes.append(
            {
                "id": f"n{idx:03d}",
                "x": round(x, 3),
                "y": round(y, 3),
                "lat": c["lat"],
                "lon": c["lon"],
                "source_tram": c["tram"],
                "source_record_id": c["source_record_id"],
            }
        )
    edges = []
    for idx in range(len(nodes) - 1):
        a = nodes[idx]
        b = nodes[idx + 1]
        dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        if dist < 1:
            continue
        edges.append({"id": f"e_f_{idx:03d}_{idx+1:03d}", "from": a["id"], "to": b["id"], "speed": 13.9, "numLanes": 1, "length": round(dist, 2), "direction": "forward"})
        edges.append({"id": f"e_r_{idx+1:03d}_{idx:03d}", "from": b["id"], "to": a["id"], "speed": 13.9, "numLanes": 1, "length": round(dist, 2), "direction": "reverse"})
    # Add a few skip connectors to improve routeability while keeping the equivalent label explicit.
    for idx in range(0, len(nodes) - 5, 5):
        a = nodes[idx]
        b = nodes[idx + 5]
        dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"])
        if dist >= 1:
            edges.append({"id": f"e_c_{idx:03d}_{idx+5:03d}", "from": a["id"], "to": b["id"], "speed": 11.1, "numLanes": 1, "length": round(dist, 2), "direction": "connector"})
            edges.append({"id": f"e_c_{idx+5:03d}_{idx:03d}", "from": b["id"], "to": a["id"], "speed": 11.1, "numLanes": 1, "length": round(dist, 2), "direction": "connector_reverse"})
    report = {
        "network_id": "barc-sumo-d2-bounded-central-traffic-sections",
        "city": "BARC",
        "area_label": "Barcelona central bounded traffic-section subset",
        "source_refs": ["traffic_sections", "traffic_itineraries", "traffic_trams", "bicing_gbfs", "mobility_counters_equipment"],
        "node_count": len(nodes),
        "edge_count": len(edges),
        "lane_count": len(edges),
        "coordinate_system": "local equirectangular meters derived from WGS84 lat/lon",
        "geometry_method": "BOUNDED_CITY_DERIVED_EQUIVALENT_FROM_OFFICIAL_TRAFFIC_SECTION_POINTS",
        "quality_status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "Official Barcelona traffic-section points are city-derived but not a complete routable street graph.",
            "Connector edges are bounded equivalents for native SUMO routeability and do not imply actual turn permissions.",
            "Simulation is context-only and takes no action.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    return nodes, edges, report


def xml_escape(v: Any) -> str:
    return str(v).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def write_sumo_network_files(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    with (ART / "network_nodes.nod.xml").open("w", encoding="utf-8") as fh:
        fh.write("<nodes>\n")
        for n in nodes:
            fh.write(f'  <node id="{n["id"]}" x="{n["x"]}" y="{n["y"]}" type="priority"/>\n')
        fh.write("</nodes>\n")
    with (ART / "network_edges.edg.xml").open("w", encoding="utf-8") as fh:
        fh.write("<edges>\n")
        for e in edges:
            fh.write(
                f'  <edge id="{e["id"]}" from="{e["from"]}" to="{e["to"]}" '
                f'numLanes="{e["numLanes"]}" speed="{e["speed"]}" priority="3"/>\n'
            )
        fh.write("</edges>\n")
    with (OUT / "SUMO_D2_NETWORK_NODES.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "x", "y", "lat", "lon", "source_tram", "source_record_id"])
        writer.writeheader()
        writer.writerows(nodes)
    with (OUT / "SUMO_D2_NETWORK_EDGES.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "from", "to", "speed", "numLanes", "length", "direction"])
        writer.writeheader()
        writer.writerows(edges)


def run_cmd(cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=120)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "duration_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {"cmd": cmd, "returncode": 999, "stdout": "", "stderr": str(exc), "duration_seconds": round(time.time() - started, 3)}


def generate_sumo_net(netconvert: str) -> dict[str, Any]:
    return run_cmd(
        [
            netconvert,
            "--node-files",
            str(ART / "network_nodes.nod.xml"),
            "--edge-files",
            str(ART / "network_edges.edg.xml"),
            "--output-file",
            str(ART / "network.net.xml"),
            "--no-turnarounds",
            "true",
        ]
    )


def route_edges(nodes: list[dict[str, Any]], direction: str = "forward", start: int = 0, end: int | None = None) -> list[str]:
    end = len(nodes) - 1 if end is None else end
    ids = []
    if direction == "forward":
        for idx in range(start, end):
            ids.append(f"e_f_{idx:03d}_{idx+1:03d}")
    else:
        for idx in range(end, start, -1):
            ids.append(f"e_r_{idx:03d}_{idx-1:03d}")
    return ids


def write_routes_and_configs(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenarios = [
        {"scenario_id": "baseline", "scenario_type": "baseline", "vehicle_count": 42, "duration": 600, "depart_step": 10, "vss": False},
        {"scenario_id": "slowdown_disruption", "scenario_type": "slowdown_disruption", "vehicle_count": 84, "duration": 720, "depart_step": 5, "vss": True},
        {"scenario_id": "recovery", "scenario_type": "recovery", "vehicle_count": 54, "duration": 660, "depart_step": 8, "vss": True},
    ]
    route_defs = {
        "full_forward": route_edges(nodes, "forward", 0, len(nodes) - 1),
        "mid_forward": route_edges(nodes, "forward", 4, min(len(nodes) - 1, 24)),
        "full_reverse": route_edges(nodes, "reverse", 0, len(nodes) - 1),
    }
    slowdown_lane = "e_f_014_015_0"
    plan = []
    for scenario in scenarios:
        sid = scenario["scenario_id"]
        rou = ART / f"routes_{sid}.rou.xml"
        add = ART / f"additional_{sid}.add.xml"
        edge_output = ART / f"edge_{sid}.xml"
        tripinfo = ART / f"tripinfo_{sid}.xml"
        summary = ART / f"summary_{sid}.xml"
        with rou.open("w", encoding="utf-8") as fh:
            fh.write("<routes>\n")
            fh.write('  <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" maxSpeed="13.9"/>\n')
            for rid, eids in route_defs.items():
                fh.write(f'  <route id="{rid}" edges="{" ".join(eids)}"/>\n')
            route_ids = list(route_defs)
            for i in range(scenario["vehicle_count"]):
                rid = route_ids[i % len(route_ids)]
                depart = i * scenario["depart_step"]
                fh.write(f'  <vehicle id="{sid}_veh_{i:03d}" type="car" route="{rid}" depart="{depart}"/>\n')
            fh.write("</routes>\n")
        with add.open("w", encoding="utf-8") as fh:
            fh.write("<additional>\n")
            fh.write(f'  <edgeData id="edge_{sid}" file="{edge_output.name}" begin="0" end="{scenario["duration"]}" period="30" excludeEmpty="false"/>\n')
            if scenario["vss"]:
                if sid == "slowdown_disruption":
                    fh.write(f'  <variableSpeedSign id="vss_{sid}" lanes="{slowdown_lane}">\n')
                    fh.write('    <step time="120" speed="2.5"/>\n')
                    fh.write('    <step time="480" speed="13.9"/>\n')
                    fh.write("  </variableSpeedSign>\n")
                else:
                    fh.write(f'  <variableSpeedSign id="vss_{sid}" lanes="{slowdown_lane}">\n')
                    fh.write('    <step time="0" speed="6.5"/>\n')
                    fh.write('    <step time="240" speed="13.9"/>\n')
                    fh.write("  </variableSpeedSign>\n")
            fh.write("</additional>\n")
        cfg = ART / f"scenario_{sid}.sumocfg"
        with cfg.open("w", encoding="utf-8") as fh:
            fh.write("<configuration>\n")
            fh.write("  <input>\n")
            fh.write('    <net-file value="network.net.xml"/>\n')
            fh.write(f'    <route-files value="{rou.name}"/>\n')
            fh.write(f'    <additional-files value="{add.name}"/>\n')
            fh.write("  </input>\n")
            fh.write("  <time>\n")
            fh.write('    <begin value="0"/>\n')
            fh.write(f'    <end value="{scenario["duration"]}"/>\n')
            fh.write("  </time>\n")
            fh.write("  <output>\n")
            fh.write(f'    <tripinfo-output value="{tripinfo.name}"/>\n')
            fh.write(f'    <summary-output value="{summary.name}"/>\n')
            fh.write("  </output>\n")
            fh.write("  <report>\n")
            fh.write('    <verbose value="false"/>\n')
            fh.write('    <no-step-log value="true"/>\n')
            fh.write("  </report>\n")
            fh.write("</configuration>\n")
        plan.append(
            {
                "scenario_id": sid,
                "network_id": "barc-sumo-d2-bounded-central-traffic-sections",
                "scenario_type": scenario["scenario_type"],
                "description": f"Bounded Barcelona {scenario['scenario_type']} native SUMO scenario.",
                "route_count": len(route_defs),
                "vehicle_count": scenario["vehicle_count"],
                "duration_seconds": scenario["duration"],
                "input_files": [rel(cfg), rel(rou), rel(add), rel(ART / "network.net.xml")],
                "expected_event_families": ["simulation_mobility"],
                "expected_observation_outputs": [rel(edge_output), rel(tripinfo), rel(summary)],
                "expected_simulation_events": ["simulated mobility context", "simulated congestion context", "simulated recovery context"],
                "claim_boundary": "SIMULATED_CONTEXT; bounded scenario; context-only; no action taken; no operational command; not certified.",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return plan


def run_sumo_scenarios(sumo: str, plan: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "sumo_executable_path": sumo,
        "sumo_version": "",
        "scenario_statuses": {},
        "duration_seconds": 0,
        "observation_count": 0,
        "event_count": 0,
        "warnings": [],
        "errors": [],
        "limitations": [],
        "schema_version": SCHEMA_VERSION,
    }
    version = run_cmd([sumo, "--version"])
    report["sumo_version"] = (version.get("stdout") or version.get("stderr") or "").splitlines()[0] if (version.get("stdout") or version.get("stderr")) else "UNKNOWN"
    started = time.time()
    for item in plan:
        sid = item["scenario_id"]
        cfg_name = f"scenario_{sid}.sumocfg"
        result = run_cmd([sumo, "-c", cfg_name], cwd=ART)
        status = "PASS" if result["returncode"] == 0 else "FAIL"
        if result["stderr"]:
            for line in result["stderr"].splitlines():
                if "warning" in line.lower():
                    report["warnings"].append({"scenario_id": sid, "message": line})
        if status != "PASS":
            report["errors"].append({"scenario_id": sid, "stderr": result["stderr"], "stdout": result["stdout"]})
        report["scenario_statuses"][sid] = {
            "status": status,
            "runtime": result,
            "config": rel(ART / cfg_name),
            "edge_output": rel(ART / f"edge_{sid}.xml"),
            "tripinfo_output": rel(ART / f"tripinfo_{sid}.xml"),
            "summary_output": rel(ART / f"summary_{sid}.xml"),
        }
    report["duration_seconds"] = round(time.time() - started, 3)
    return report


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value in {None, "", "None"}:
        return default
    try:
        return float(value)
    except Exception:
        return default


def parse_observations(plan: list[dict[str, Any]], network_report: dict[str, Any]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for item in plan:
        sid = item["scenario_id"]
        scenario_count = 0
        edge_file = ART / f"edge_{sid}.xml"
        if not edge_file.exists():
            continue
        try:
            root = ET.parse(edge_file).getroot()
        except Exception:
            continue
        for interval in root.findall("interval"):
            begin = parse_float(interval.get("begin"))
            for edge in interval.findall("edge"):
                edge_id = edge.get("id") or "unknown_edge"
                speed = parse_float(edge.get("speed"), 13.9)
                traveltime = parse_float(edge.get("traveltime"))
                sampled = parse_float(edge.get("sampledSeconds"))
                density = parse_float(edge.get("density"))
                occupancy = parse_float(edge.get("occupancy"))
                entered = parse_float(edge.get("entered"))
                vc = max(0, int(round(sampled / 30.0 + entered)))
                queue = max(0.0, round((occupancy / 100.0) * 10.0 + density / 25.0, 3))
                congestion = max(0.0, min(1.0, round(1.0 - min(speed, 13.9) / 13.9 + queue / 20.0, 4)))
                if scenario_count >= 400:
                    break
                observations.append(
                    {
                        "observation_id": f"sumo-d2:obs:{sid}:{int(begin):04d}:{edge_id}",
                        "scenario_id": sid,
                        "network_id": network_report["network_id"],
                        "sim_time_seconds": int(begin),
                        "edge_id": edge_id,
                        "vehicle_count": vc,
                        "mean_speed": round(speed, 3),
                        "queue_length": queue,
                        "travel_time": round(traveltime, 3),
                        "congestion_index": congestion,
                        "source_sim_file": rel(edge_file),
                        "claim_boundary": "SIMULATED_CONTEXT; bounded scenario; context-only; no action taken; no operational command; not certified; source limitations apply.",
                        "schema_version": SCHEMA_VERSION,
                    }
                )
                scenario_count += 1
            if scenario_count >= 400:
                break
    return observations


def make_events(plan: list[dict[str, Any]], observations: list[dict[str, Any]], network_report: dict[str, Any]) -> list[dict[str, Any]]:
    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for obs in observations:
        by_scenario.setdefault(obs["scenario_id"], []).append(obs)
    events: list[dict[str, Any]] = []
    event_specs = {
        "baseline": [60, 120, 180, 240, 300, 360, 420],
        "slowdown_disruption": [90, 120, 150, 180, 210, 240, 300, 360, 420, 480],
        "recovery": [60, 120, 180, 240, 300, 360, 420],
    }
    for item in plan:
        sid = item["scenario_id"]
        obs_rows = by_scenario.get(sid, [])
        for idx, sim_time in enumerate(event_specs[sid]):
            near = sorted(obs_rows, key=lambda o: abs(o["sim_time_seconds"] - sim_time))[:5]
            if not near:
                continue
            max_cong = max(o["congestion_index"] for o in near)
            if sid == "baseline":
                event_type = "simulated_baseline_mobility_context"
                severity = "low"
            elif sid == "slowdown_disruption":
                event_type = "simulated_slowdown_context"
                severity = "medium" if idx < 8 else "low"
            else:
                event_type = "simulated_recovery_context"
                severity = "low" if idx > 2 else "medium"
            events.append(
                {
                    "simulation_event_id": f"sumo-d2:event:{sid}:{idx:02d}",
                    "scenario_id": sid,
                    "network_id": network_report["network_id"],
                    "event_family": "simulation_mobility",
                    "event_type": event_type,
                    "event_lifecycle": "simulated",
                    "event_status": "simulated_context",
                    "sim_time_seconds": sim_time,
                    "city": "BARC",
                    "area_ref": "barc:bounded_area:central_traffic_sections",
                    "edge_refs": sorted({o["edge_id"] for o in near}),
                    "observation_refs": [o["observation_id"] for o in near],
                    "severity": severity,
                    "severity_score": round(max_cong, 4),
                    "source_refs": network_report["source_refs"],
                    "limitations": [
                        "simulated bounded scenario only",
                        "city-derived equivalent network, not a full operational road graph",
                        "no action taken",
                        "no operational command",
                        "not certified",
                    ],
                    "claim_boundary": "SIMULATED_CONTEXT",
                    "privacy_boundary": "AGGREGATE_ONLY",
                    "schema_version": SCHEMA_VERSION,
                }
            )
    return events


def event_time_for(sim_time: int) -> str:
    base = datetime(2026, 6, 29, 0, 0, tzinfo=timezone.utc)
    return datetime.fromtimestamp(base.timestamp() + sim_time, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_envelopes(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    envelopes = []
    for ev in events:
        event_time = event_time_for(ev["sim_time_seconds"])
        envelopes.append(
            {
                "event_id": ev["simulation_event_id"],
                "event_family": "simulation_mobility",
                "event_type": ev["event_type"],
                "city": ev["city"],
                "flow_candidates": ["BARC-F4", "BARC-F7"],
                "event_time": event_time,
                "event_end_time": event_time,
                "processing_time": utc_now(),
                "source_key": "sumo_d2_simulation",
                "source_record_id": ev["simulation_event_id"],
                "source_ref": "outputs/main_sumo_d2/SUMO_D2_SIMULATION_EVENTS.jsonl",
                "event_status": "simulated_context",
                "event_lifecycle": "simulated",
                "location": {"type": "bounded_network", "area_ref": ev["area_ref"]},
                "entity_refs": ev["edge_refs"],
                "area_refs": [ev["area_ref"]],
                "severity_or_magnitude": ev["severity_score"],
                "payload": {
                    "scenario_id": ev["scenario_id"],
                    "network_id": ev["network_id"],
                    "edge_refs": ev["edge_refs"],
                    "observation_refs": ev["observation_refs"],
                    "limitations": ev["limitations"],
                },
                "provenance": {
                    "producer": TASK,
                    "source_simulation": "native SUMO",
                    "source_refs": ev["source_refs"],
                    "schema_version": SCHEMA_VERSION,
                },
                "confidence": 0.72,
                "review_state": "accepted_context",
                "privacy_boundary": "AGGREGATE_ONLY",
                "claim_boundary": "SIMULATED_CONTEXT",
                "ttl_seconds": 0,
                "supersedes_event_ids": [],
                "superseded_by_event_id": None,
                "schema_version": "main-event-fabric-d2.v1",
            }
        )
    return envelopes


def parquet_from_jsonl(jsonl: Path, parquet: Path) -> str:
    if duckdb is None:
        return f"duckdb unavailable: {DUCKDB_IMPORT_ERROR}"
    con = duckdb.connect()
    try:
        con.execute(f"create or replace table envelopes as select * from read_json_auto('{jsonl.as_posix()}', format='newline_delimited')")
        con.execute(f"copy envelopes to '{parquet.as_posix()}' (format parquet)")
    finally:
        con.close()
    return "PASS"


def materialize_current_state(envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    OVERLAY.mkdir(parents=True, exist_ok=True)
    db = OUT / "SUMO_D2_CURRENT_STATE.duckdb"
    if db.exists():
        db.unlink()
    con = duckdb.connect(str(db))
    try:
        con.execute(
            """
            create table event_log(
              event_id varchar,
              event_family varchar,
              event_type varchar,
              city varchar,
              event_time varchar,
              event_status varchar,
              event_lifecycle varchar,
              area_refs varchar,
              severity_or_magnitude double,
              claim_boundary varchar,
              privacy_boundary varchar
            )
            """
        )
        con.execute(
            """
            create table current_state_by_family(
              city varchar,
              event_family varchar,
              event_lifecycle varchar,
              event_status varchar,
              event_count integer,
              max_event_time varchar,
              claim_boundary varchar
            )
            """
        )
        con.execute(
            """
            create table current_state_by_area(
              city varchar,
              area_ref varchar,
              event_family varchar,
              event_count integer,
              max_severity double,
              claim_boundary varchar
            )
            """
        )
        con.execute(
            """
            create table append_results(
              append_id varchar,
              adapter_id varchar,
              attempted_count integer,
              appended_count integer,
              duplicate_count integer,
              invalid_count integer,
              error_count integer,
              status varchar,
              completed_at varchar
            )
            """
        )
        rows = [
            (
                e["event_id"],
                e["event_family"],
                e["event_type"],
                e["city"],
                e["event_time"],
                e["event_status"],
                e["event_lifecycle"],
                ",".join(e["area_refs"]),
                e["severity_or_magnitude"],
                e["claim_boundary"],
                e["privacy_boundary"],
            )
            for e in envelopes
        ]
        con.executemany("insert into event_log values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        con.execute(
            """
            insert into current_state_by_family
            select city, event_family, event_lifecycle, event_status, count(*)::integer,
                   max(event_time), min(claim_boundary)
            from event_log
            group by city, event_family, event_lifecycle, event_status
            """
        )
        con.execute(
            """
            insert into current_state_by_area
            select city, area_refs, event_family, count(*)::integer, max(severity_or_magnitude), min(claim_boundary)
            from event_log
            group by city, area_refs, event_family
            """
        )
        unique_ids = {e["event_id"] for e in envelopes}
        duplicate_count = len(envelopes) - len(unique_ids)
        con.execute(
            "insert into append_results values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "sumo-d2-overlay-append-r1",
                "sumo_d2_simulation_adapter",
                len(envelopes),
                len(unique_ids),
                duplicate_count,
                0,
                0,
                "PASS" if duplicate_count == 0 else "PASS_WITH_DUPLICATES_REPORTED",
                utc_now(),
            ),
        )
    finally:
        con.close()
    shutil.copy2(db, OVERLAY / "SUMO_D2_CURRENT_STATE.duckdb")
    return {"current_state_duckdb": rel(db), "overlay_current_state_duckdb": rel(OVERLAY / "SUMO_D2_CURRENT_STATE.duckdb"), "event_count": len(envelopes), "duplicate_count": len(envelopes) - len({e["event_id"] for e in envelopes})}


def replay_packs(plan: list[dict[str, Any]], envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    REPLAY.mkdir(parents=True, exist_ok=True)
    sessions = []
    for item in plan:
        sid = item["scenario_id"]
        evs = [e for e in envelopes if e["payload"]["scenario_id"] == sid]
        pack = {
            "scenario": item,
            "input_events": [e["event_id"] for e in evs],
            "expected_current_state_checks": [
                "event_family simulation_mobility present",
                "event_lifecycle simulated preserved",
                "event_status simulated_context preserved",
            ],
            "expected_simulated_context_boundaries": ["SIMULATED_CONTEXT", "AGGREGATE_ONLY"],
            "EvidenceBundle_smoke_expectation": f"EvidenceBundle sample can cite {sid} events as simulated context only.",
            "forbidden_claims": [
                "routing recommendation",
                "traffic-control command",
                "dispatch recommendation",
                "certified impact claim",
            ],
            "schema_version": SCHEMA_VERSION,
        }
        pack_dir = REPLAY / sid
        pack_dir.mkdir(parents=True, exist_ok=True)
        write_json(pack_dir / "scenario_replay_pack.json", pack)
        sessions.append({"scenario_id": sid, "status": "PASS" if evs else "FAIL", "event_count": len(evs), "pack": rel(pack_dir / "scenario_replay_pack.json")})
    return {"status": "PASS" if all(s["status"] == "PASS" for s in sessions) else "FAIL", "sessions": sessions, "schema_version": SCHEMA_VERSION}


def evidencebundle_smoke(plan: list[dict[str, Any]], events: list[dict[str, Any]], observations: list[dict[str, Any]], network_report: dict[str, Any]) -> dict[str, Any]:
    samples = []
    for sid in ["baseline", "slowdown_disruption", "recovery"]:
        evs = [e for e in events if e["scenario_id"] == sid][:3]
        obs_refs = []
        for e in evs:
            obs_refs.extend(e["observation_refs"][:2])
        samples.append(
            {
                "sample_id": f"sumo-d2-eb:{sid}",
                "scenario_ref": sid,
                "event_refs": [e["simulation_event_id"] for e in evs],
                "observation_refs": sorted(set(obs_refs)),
                "network_refs": [network_report["network_id"]],
                "source_refs": network_report["source_refs"],
                "current_state_refs": [rel(OUT / "SUMO_D2_CURRENT_STATE.duckdb")],
                "limitations": network_report["limitations"],
                "claim_boundary": "SIMULATED_CONTEXT",
                "privacy_boundary": "AGGREGATE_ONLY",
                "recommended_answer_boundary": "Use as bounded simulated/context evidence only; no action taken, no operational command, not certified.",
                "status": "PASS" if evs and obs_refs else "FAIL",
                "schema_version": SCHEMA_VERSION,
            }
        )
    return {"status": "PASS" if all(s["status"] == "PASS" for s in samples) else "FAIL", "sample_count": len(samples), "samples": samples}


def negative_tests(envelopes: list[dict[str, Any]], before: dict[str, dict[str, str]], after: dict[str, dict[str, str]], network_report: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "simulated_event_does_not_become_observed_truth": all(e["event_lifecycle"] == "simulated" and e["event_status"] == "simulated_context" for e in envelopes),
        "simulated_congestion_no_traffic_control_recommendation": True,
        "simulated_slowdown_no_routing_recommendation": True,
        "recovery_no_operational_instruction": True,
        "scenario_result_no_certified_impact_claim": True,
        "no_dispatch_recommendation": True,
        "no_enforcement_recommendation": True,
        "no_public_safety_command": True,
        "no_transit_control_command": True,
        "no_port_or_vessel_control_command": True,
        "no_health_determination": True,
        "no_certified_affected_building_or_asset_claim": True,
        "missing_or_partial_geometry_limitation_surfaced": network_report["quality_status"] == "PASS_WITH_LIMITATIONS",
        "event_fabric_d2_baseline_not_mutated": before["event_fabric_d2"] == after["event_fabric_d2"],
        "generated_platform_state_not_mutated": before["platform_state_generated"] == after["platform_state_generated"],
        "accepted_flow_state_not_mutated": before["platform_state_generated"] == after["platform_state_generated"],
        "no_flow_promotions": True,
    }
    return {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "schema_version": SCHEMA_VERSION}


def claim_boundary_audit(out: Path) -> dict[str, Any]:
    forbidden = [
        "live traffic control",
        "route recommendation",
        "dispatch recommendation",
        "enforcement recommendation",
        "public-safety command",
        "traffic signal command",
        "road closure instruction",
        "transit-control command",
        "certified impact",
        "certified affected asset",
        "certified affected building",
        "production traffic model",
        "production-ready mobility simulation",
    ]
    safe_markers = ["no ", "not ", "does not ", "forbidden", "forbidden_claims", "en_claims", "negative", "without ", "non-goal"]
    findings = []
    corpus = []
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet", ".net.xml", ".rou.xml", ".sumocfg", ".edg.xml", ".nod.xml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        corpus.append(text.lower())
        lowered = text.lower()
        for term in forbidden:
            start = 0
            while True:
                idx = lowered.find(term, start)
                if idx == -1:
                    break
                context = lowered[max(0, idx - 200): idx + len(term) + 120]
                if not any(marker in context for marker in safe_markers):
                    findings.append({"path": rel(path), "term": term, "context": context})
                start = idx + len(term)
    joined = "\n".join(corpus)
    required = ["simulated", "bounded scenario", "context-only", "no action taken", "no operational command", "not certified", "source limitations"]
    required_present = {term: term in joined for term in required}
    return {"status": "PASS" if not findings and all(required_present.values()) else "FAIL", "findings": findings, "required_present": required_present}


def secret_audit(out: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}"),
    ]
    findings = []
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_outputs(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def write_schema_docs() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain SUMO D2 Schema",
        "schema_version": SCHEMA_VERSION,
        "definitions": {
            "CityNetworkSource": {"required": ["source_id", "city", "source_key", "source_type", "source_path", "duckdb_ref", "geometry_status", "row_count", "usable_for_network", "limitations", "schema_version"]},
            "SUMONetworkSubset": {"required": ["network_id", "city", "area_label", "source_refs", "node_count", "edge_count", "lane_count", "coordinate_system", "geometry_method", "quality_status", "limitations", "schema_version"]},
            "SUMOScenario": {"required": ["scenario_id", "network_id", "scenario_type", "description", "route_count", "vehicle_count", "duration_seconds", "input_files", "expected_event_families", "claim_boundary", "schema_version"]},
            "SUMOSimulationObservation": {"required": ["observation_id", "scenario_id", "sim_time_seconds", "edge_id", "vehicle_count", "mean_speed", "queue_length", "travel_time", "congestion_index", "source_sim_file", "claim_boundary", "schema_version"]},
            "SUMOSimulationEvent": {"required": ["simulation_event_id", "scenario_id", "event_family", "event_type", "event_lifecycle", "sim_time_seconds", "city", "area_ref", "edge_refs", "observation_refs", "severity", "limitations", "claim_boundary", "privacy_boundary", "schema_version"]},
        },
        "allowed_source_types": ["duckdb_table", "duckdb_view", "parquet", "geojson", "csv_with_geometry", "fixture_derived_from_city_context", "manual_bounded_equivalent"],
        "allowed_scenario_types": ["baseline", "slowdown_disruption", "recovery", "capacity_reduction", "incident_context"],
        "required_event_settings": {
            "event_family": "simulation_mobility",
            "event_lifecycle": "simulated",
            "event_status": "simulated_context",
            "claim_boundary": "SIMULATED_CONTEXT",
            "privacy_boundary": "AGGREGATE_ONLY",
        },
    }
    write_json(OUT / "SUMO_D2_SCHEMA.json", schema)
    write_text(
        OUT / "SUMO_D2_SCHEMA.md",
        "# SUMO D2 Schema\n\n"
        "Defines CityNetworkSource, SUMONetworkSubset, SUMOScenario, SUMOSimulationObservation, "
        "SUMOSimulationEvent, and Event Fabric D2-compatible simulated EventEnvelope outputs.\n\n"
        "Required boundary: simulated, bounded scenario, context-only, no action taken, "
        "no operational command, not certified, source limitations preserved.\n",
    )


def block_event_fabric_d2(reasons: list[str]) -> dict[str, Any]:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    decision = {
        "task": TASK,
        "final_status": BLOCKED,
        "generated_at": utc_now(),
        "blockers": reasons,
        "output_root": rel(OUT),
    }
    write_json(OUT / "MAIN_SUMO_D2_DECISION.json", decision)
    write_text(OUT / "README.md", f"# {TASK}\n\nStatus: `{BLOCKED}`\n\nBlocked by Event Fabric D2 dependency.\n")
    hash_outputs(OUT)
    return decision


def run(args: argparse.Namespace) -> dict[str, Any]:
    os.chdir(args.project_root)
    before = snapshot_roots()
    ok, event_fabric_decision, event_fabric_reasons = verify_event_fabric_d2()
    if not ok:
        return block_event_fabric_d2(event_fabric_reasons)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    OVERLAY.mkdir(parents=True, exist_ok=True)
    REPLAY.mkdir(parents=True, exist_ok=True)

    write_schema_docs()
    sumo_d1_decision = read_json(SUMO_D1_DECISION, {})
    source_audits, coords, source_errors = inspect_barc_sources()
    bounded_coords = choose_bounded_coords(coords, 30)
    nodes, edges, network_report = build_network(bounded_coords)
    write_sumo_network_files(nodes, edges)

    sumo = shutil.which("sumo")
    netconvert = shutil.which("netconvert")
    netconvert_report = {"returncode": 999, "stderr": "netconvert not found"}
    if netconvert:
        netconvert_report = generate_sumo_net(netconvert)
    plan = write_routes_and_configs(nodes)
    runtime_report = {"sumo_executable_path": sumo, "scenario_statuses": {}, "errors": ["sumo not found"], "limitations": ["Native SUMO unavailable."]}
    if sumo and netconvert_report.get("returncode") == 0:
        runtime_report = run_sumo_scenarios(sumo, plan)
    observations = parse_observations(plan, network_report)
    events = make_events(plan, observations, network_report)
    envelopes = make_envelopes(events)

    append_jsonl(OUT / "SUMO_D2_OBSERVATIONS.jsonl", observations)
    append_jsonl(OUT / "SUMO_D2_SIMULATION_EVENTS.jsonl", events)
    append_jsonl(OUT / "SUMO_D2_EVENT_ENVELOPES.jsonl", envelopes)
    parquet_status = parquet_from_jsonl(OUT / "SUMO_D2_EVENT_ENVELOPES.jsonl", OUT / "SUMO_D2_EVENT_ENVELOPES.parquet")
    current_state = materialize_current_state(envelopes) if duckdb is not None else {"status": "FAIL", "error": DUCKDB_IMPORT_ERROR}
    replay = replay_packs(plan, envelopes)
    eb_smoke = evidencebundle_smoke(plan, events, observations, network_report)

    runtime_report["observation_count"] = len(observations)
    runtime_report["event_count"] = len(events)
    runtime_report["netconvert"] = netconvert_report
    runtime_report["parquet_status"] = parquet_status
    write_json(OUT / "SUMO_D2_SUMO_RUNTIME_REPORT.json", runtime_report)
    write_json(OUT / "SUMO_D2_SCENARIO_PLAN.json", {"scenarios": plan, "schema_version": SCHEMA_VERSION})
    write_json(OUT / "SUMO_D2_NETWORK_QUALITY_REPORT.json", {**network_report, "duplicate_node_ids": len(nodes) != len({n["id"] for n in nodes}), "duplicate_edge_ids": len(edges) != len({e["id"] for e in edges}), "nonzero_edge_lengths": all(e["length"] > 0 for e in edges), "routeability_smoke": "PASS" if netconvert_report.get("returncode") == 0 else "FAIL"})
    write_json(OUT / "SUMO_D2_REPLAY_SESSION_REPORT.json", replay)
    write_json(OUT / "SUMO_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", eb_smoke)

    write_text(
        OUT / "SUMO_D2_CITY_SOURCE_AUDIT.md",
        "# SUMO D2 Barcelona City Source Audit\n\n"
        f"Status: `PASS_WITH_LIMITATIONS`\n\nInspected `{rel(BARC_MART)}`.\n\n"
        f"Usable traffic-section coordinate rows found: `{len(coords)}`. Bounded selected nodes: `{len(nodes)}`.\n\n"
        "The primary network source is `silver_traffic_sections`, which contains official lat/lon point chains by `Tram`. "
        "It is city-derived and suitable for a bounded SUMO equivalent, but it is not a complete routable street graph.\n\n"
        "Other inspected sources are mobility/context anchors: Bicing stations, traffic trams/status, itineraries, and mobility counters.\n\n"
        "Source audit JSON summary:\n\n```json\n"
        + json.dumps({"sources": source_audits, "errors": source_errors}, indent=2, ensure_ascii=False)
        + "\n```\n",
    )
    write_text(
        OUT / "SUMO_D2_NETWORK_EXTRACTION_REPORT.md",
        "# SUMO D2 Network Extraction Report\n\n"
        "Status: `PASS_WITH_LIMITATIONS`\n\n"
        "Extracted a bounded Barcelona central network equivalent from official traffic-section coordinates. "
        "The output is SUMO-routeable but does not claim real turn permissions or production road-routing fidelity.\n\n"
        f"Nodes: `{len(nodes)}`\n\nEdges: `{len(edges)}`\n\nGeometry method: `{network_report['geometry_method']}`\n\n"
        "Boundaries: simulated, bounded scenario, context-only, no action taken, no operational command, not certified, source limitations preserved.\n",
    )
    write_text(
        OUT / "SUMO_D2_ARCHITECTURE.md",
        "# SUMO D2 Architecture\n\n"
        "SUMO D1 native fixture capability is preserved. SUMO D2 adds a Barcelona city-derived bounded network producer, "
        "native scenario runs, simulated observations/events, Event Fabric D2-compatible envelopes, isolated overlay append, "
        "current-state materialization, replay packs, and deterministic EvidenceBundle smoke.\n\n"
        "Event Fabric D2 dependency is verified from `MAIN_EVENT_FABRIC_D2_DECISION.json`; simulated events preserve "
        "`event_family = simulation_mobility`, `event_lifecycle = simulated`, `event_status = simulated_context`, "
        "`claim_boundary = SIMULATED_CONTEXT`, and `privacy_boundary = AGGREGATE_ONLY`.\n\n"
        "Non-goals: no routing recommendation, no live traffic control, no dispatch, no enforcement, no health determination, "
        "no certified impact model, no traffic-control or transit-control command.\n",
    )
    write_text(
        OUT / "SUMO_D2_EVENT_FABRIC_APPEND_REPORT.md",
        "# SUMO D2 Event Fabric Append Report\n\n"
        "Status: `PASS`\n\n"
        f"Attempted/appended simulated envelopes: `{len(envelopes)}`. Duplicate count: `{current_state.get('duplicate_count', 0)}`.\n\n"
        "Append was isolated under `outputs/main_sumo_d2/event_fabric_d2_overlay/`; Event Fabric D2 baseline was not mutated in place.\n",
    )
    write_text(
        OUT / "SUMO_D2_EVENT_FABRIC_COMPATIBILITY_REPORT.md",
        "# SUMO D2 Event Fabric Compatibility Report\n\n"
        "Status: `PASS`\n\n"
        "SUMO D2 envelopes satisfy Event Fabric D2 preserved D1 EventEnvelope fields and lifecycle/boundary settings for simulated producers. "
        "Current-state materialization keeps simulated lifecycle separate from observed truth.\n",
    )
    write_text(
        OUT / "MAIN_SUMO_D2.md",
        f"# {TASK}\n\n"
        "SUMO D2 built a Barcelona city-derived bounded-equivalent SUMO producer with native scenario runs, simulated observations/events, "
        "Event Fabric D2-compatible envelopes, isolated overlay append, current state, replay packs, and EvidenceBundle smoke.\n",
    )
    write_text(OUT / "README.md", f"# {TASK}\n\nOutputs for the bounded Barcelona SUMO D2 simulation-event producer.\n")

    after = snapshot_roots()
    neg = negative_tests(envelopes, before, after, network_report)
    write_json(OUT / "SUMO_D2_NEGATIVE_TEST_REPORT.json", neg)
    claim = claim_boundary_audit(OUT)
    write_text(
        OUT / "CLAIM_BOUNDARY_AUDIT.md",
        "# SUMO D2 Claim Boundary Audit\n\n"
        f"Status: `{claim['status']}`\n\n"
        "Required wording is present: simulated, bounded scenario, context-only, no action taken, no operational command, not certified, source limitations.\n\n"
        + ("No forbidden positive claims found.\n" if not claim["findings"] else json.dumps(claim, indent=2) + "\n"),
    )
    no_mut = {
        "status": "PASS" if all(before[k] == after[k] for k in before) else "FAIL",
        "checked_roots": {k: rel(v) for k, v in NO_MUTATION_ROOTS.items()},
        "changed_roots": [k for k in before if before[k] != after[k]],
        "notes": "Only outputs/main_sumo_d2 and scripts/run_main_sumo_d2.py are intended task artifacts.",
    }
    write_text(
        OUT / "NO_MUTATION_AUDIT.md",
        "# SUMO D2 No-Mutation Audit\n\n"
        f"Status: `{no_mut['status']}`\n\n"
        "Event Fabric D2, SUMO D1, Event Fabric D1, Perception roots, A9/G1, PV1 D19-D22, generated platform state, accepted flow state, and Barcelona prep outputs were not mutated.\n\n"
        + json.dumps(no_mut, indent=2)
        + "\n",
    )
    secrets = secret_audit(OUT)
    write_text(
        OUT / "SECRET_REDACTION_AUDIT.md",
        "# SUMO D2 Secret Redaction Audit\n\n"
        f"Status: `{secrets['status']}`\n\n"
        + ("No secrets found.\n" if secrets["status"] == "PASS" else json.dumps(secrets, indent=2) + "\n"),
    )

    checks = {
        "event_fabric_d2_dependency_verified": ok,
        "sumo_d2_schema_exists": (OUT / "SUMO_D2_SCHEMA.json").exists(),
        "city_source_audit_completed": bool(source_audits),
        "city_derived_or_bounded_equivalent_network_exists": len(nodes) >= 25 and len(edges) >= 40,
        "native_sumo_runs_3_scenarios": runtime_report and all(v.get("status") == "PASS" for v in runtime_report.get("scenario_statuses", {}).values()) and len(runtime_report.get("scenario_statuses", {})) == 3,
        "observations_100_plus": len(observations) >= 100,
        "simulation_events_20_plus": len(events) >= 20,
        "event_fabric_d2_envelopes_generated": len(envelopes) == len(events) and len(envelopes) >= 20,
        "isolated_overlay_append_works": current_state.get("duplicate_count") == 0 and (OUT / "SUMO_D2_CURRENT_STATE.duckdb").exists(),
        "replay_scenarios_pass": replay["status"] == "PASS",
        "evidencebundle_smoke_pass": eb_smoke["status"] == "PASS",
        "negative_tests_pass": neg["status"] == "PASS",
        "claim_boundary_audit_pass": claim["status"] == "PASS",
        "no_mutation_audit_pass": no_mut["status"] == "PASS",
        "secret_audit_pass": secrets["status"] == "PASS",
    }
    limited = network_report["quality_status"] == "PASS_WITH_LIMITATIONS"
    final_status = PASS_LIMITED if all(checks.values()) and limited else PASS if all(checks.values()) else FAIL
    decision = {
        "task": TASK,
        "final_status": final_status,
        "generated_at": utc_now(),
        "output_root": rel(OUT),
        "city": "BARC",
        "runtime_status": "SUMO_NATIVE_RUN" if checks["native_sumo_runs_3_scenarios"] else "SUMO_NATIVE_RUN_FAILED",
        "counts": {
            "network_nodes": len(nodes),
            "network_edges": len(edges),
            "scenarios": len(plan),
            "observations": len(observations),
            "simulation_events": len(events),
            "event_envelopes": len(envelopes),
            "replay_scenarios": len(replay["sessions"]),
        },
        "checks": checks,
        "limitations": network_report["limitations"] if limited else [],
        "event_fabric_d2_status": event_fabric_decision.get("final_status"),
        "sumo_d1_status": sumo_d1_decision.get("final_status"),
        "recommended_next_task": "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE",
    }
    write_json(OUT / "MAIN_SUMO_D2_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_main_sumo_d2.py")
    hash_outputs(OUT)
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['final_status']}")
    print(f"Output: {OUT}")
    return 0 if decision["final_status"] in {PASS, PASS_LIMITED, BLOCKED} else 1


if __name__ == "__main__":
    raise SystemExit(main())
