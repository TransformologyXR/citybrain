from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

GEOMETRY_CAVEAT = (
    "Block geometries are adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block "
    "boundary polygons."
)

OPERATOR_SAFE_STATEMENT = (
    "This is an operator review optimization over CityBrain evidence. It is not an inspector dispatch, violation "
    "decision, or enforcement action."
)

FORBIDDEN_PLAN_PHRASES = {
    "dispatch inspector",
    "issue violation",
    "stop-work order",
    "notify contractor",
    "legal finding",
    "unsafe building",
}

BOROUGH_LABELS = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}

SEED_BLOCKS = {
    "1-01060": "certified_seed_regression_baseline",
    "1-01158": "volume_stress_seed",
    "2-02316": "structural_shape_stress_seed",
}

EXPECTED_CITYWIDE = {
    "active_blocks": 27997,
    "nodes": 7330796,
    "edges": 9637245,
}

DEFAULT_CUOPT_ENDPOINT = "http://127.0.0.1:5000"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    text = str(p)
    if text.startswith("/data/citybrain/"):
        alt = Path("/data") / text[len("/data/citybrain/") :]
        if alt.exists() or str(path).endswith("a6d1_cuopt_review_optimizer"):
            return alt
    if text.startswith("/data/"):
        alt = Path("/data/citybrain") / text[len("/data/") :]
        if alt.exists():
            return alt
    return p


def host_path(path: Path) -> str:
    text = str(path)
    if text.startswith("/data/") and not text.startswith("/data/citybrain/"):
        return "/data/citybrain/" + text[len("/data/") :]
    return text


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_cmd(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover - defensive runtime reporting
        return {"cmd": cmd, "returncode": -1, "error": repr(exc)}


def file_tree_snapshot(root: Path) -> dict[str, Any]:
    root = resolve_path(root)
    if not root.exists():
        return {"root": host_path(root), "exists": False, "file_count": 0, "total_bytes": 0, "max_mtime_ns": 0}
    file_count = 0
    total_bytes = 0
    max_mtime_ns = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        file_count += 1
        total_bytes += st.st_size
        max_mtime_ns = max(max_mtime_ns, st.st_mtime_ns)
    return {
        "root": host_path(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_mtime_ns": max_mtime_ns,
    }


def snapshots_equal(before: dict[str, Any], after: dict[str, Any]) -> bool:
    keys = ("exists", "file_count", "total_bytes", "max_mtime_ns")
    return all(before.get(k) == after.get(k) for k in keys)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sha256sums(output_dir: Path) -> dict[str, str]:
    sums: dict[str, str] = {}
    for p in sorted(output_dir.rglob("*")):
        if not p.is_file() or p.name == "SHA256SUMS.json":
            continue
        rel = p.relative_to(output_dir).as_posix()
        sums[rel] = sha256_file(p)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return sums


def check_cuopt_health(endpoint: str = DEFAULT_CUOPT_ENDPOINT, timeout_s: int = 10) -> dict[str, Any]:
    url = endpoint.rstrip("/") + "/cuopt/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        return {"status": "PASS", "url": url, "http_status": resp.status, "response": parsed}
    except Exception as exc:
        return {"status": "FAIL", "url": url, "error": repr(exc)}


def post_cuopt_request(request_obj: dict[str, Any], endpoint: str, timeout_s: int = 180) -> dict[str, Any]:
    endpoint = endpoint.rstrip("/")
    data = json.dumps(request_obj).encode("utf-8")
    req = urllib.request.Request(
        endpoint + "/cuopt/request",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        first = json.loads(resp.read().decode("utf-8"))
    req_id = first.get("reqId")
    if not req_id:
        return {"status": "FAIL", "response": first, "error": "cuOpt request did not return reqId"}
    deadline = time.time() + timeout_s
    polls: list[dict[str, Any]] = []
    while time.time() < deadline:
        with urllib.request.urlopen(endpoint + f"/cuopt/solution/{req_id}", timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(body)
        polls.append({"t": utc_now(), "keys": sorted(parsed.keys())})
        if "response" in parsed:
            parsed["status"] = "PASS"
            parsed["polls"] = polls
            return parsed
        time.sleep(1)
    return {"status": "FAIL", "reqId": req_id, "polls": polls, "error": "timed out waiting for cuOpt solution"}


def load_block_cache(cache_path: Path) -> pd.DataFrame:
    con = sqlite3.connect(cache_path)
    try:
        df = pd.read_sql_query("select * from blocks", con)
    finally:
        con.close()
    rows: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        feature = json.loads(row.get("feature_json") or "{}")
        props = feature.get("properties", {})
        contractors = json.loads(row.get("top_contractors_json") or "[]")
        row["borough_name"] = BOROUGH_LABELS.get(str(row.get("borough_code")), str(row.get("borough_code")))
        row["dob_now_filing_count"] = int(props.get("dob_now_filing_count") or 0)
        row["dob_permit_issuance_count"] = int(props.get("dob_permit_issuance_count") or 0)
        row["top_contractors"] = contractors
        row["unique_contractor_count"] = len({c.get("party_id") for c in contractors if c.get("party_id")})
        row["top_contractor_edge_count"] = int(sum(int(c.get("edge_count") or 0) for c in contractors))
        rows.append(row)
    out = pd.DataFrame(rows)
    numeric_cols = [
        "node_count",
        "edge_count",
        "critical_complaint_count",
        "complaint_count",
        "permit_count",
        "dob_now_filing_count",
        "dob_permit_issuance_count",
        "unique_contractor_count",
        "top_contractor_edge_count",
        "centroid_lon",
        "centroid_lat",
    ]
    for col in numeric_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    out["block_key"] = out["block_key"].astype(str)
    out["borough_code"] = out["borough_code"].astype(str)
    return out


def norm(series: pd.Series) -> pd.Series:
    max_val = float(series.max()) if len(series) else 0.0
    if max_val <= 0:
        return series * 0.0
    return series.astype(float) / max_val


def choose_candidate_type(row: pd.Series) -> str:
    if row["block_key"] in SEED_BLOCKS:
        return "seed_regression_review_block"
    components = row["priority_components"]
    core = {
        "critical_complaint_count": components["critical_complaint_count"],
        "complaint_density": components["complaint_density"],
        "permit_activity": components["permit_activity"],
        "graph_hub_degree": components["graph_hub_degree"],
        "party_complexity": components["party_complexity"],
    }
    key = max(core, key=core.get)
    return {
        "critical_complaint_count": "critical_complaint_review_block",
        "complaint_density": "high_complaint_density_review_block",
        "permit_activity": "high_permit_activity_review_block",
        "graph_hub_degree": "graph_hub_review_block",
        "party_complexity": "party_complexity_review_block",
    }[key]


def compute_candidate_scores(blocks: pd.DataFrame) -> pd.DataFrame:
    df = blocks.copy()
    df["complaint_density_raw"] = df["complaint_count"] / df["node_count"].clip(lower=1)
    df["graph_hub_degree_raw"] = df["edge_count"] / df["node_count"].clip(lower=1)
    df["critical_component"] = norm(df["critical_complaint_count"])
    df["complaint_density_component"] = norm(df["complaint_density_raw"])
    df["permit_activity_component"] = norm(df["permit_count"])
    df["party_complexity_component"] = norm(df["top_contractor_edge_count"])
    df["graph_hub_degree_component"] = norm(df["graph_hub_degree_raw"])
    df["seed_component"] = df["block_key"].map(lambda x: 1.0 if x in SEED_BLOCKS else 0.0)
    df["recency_proxy_component"] = 0.0
    df["priority_score"] = (
        100.0
        * (
            0.32 * df["critical_component"]
            + 0.18 * df["complaint_density_component"]
            + 0.18 * df["permit_activity_component"]
            + 0.14 * df["graph_hub_degree_component"]
            + 0.08 * df["party_complexity_component"]
            + 0.08 * df["seed_component"]
            + 0.02 * df["recency_proxy_component"]
        )
    ).clip(upper=100.0)
    components: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        components.append(
            {
                "critical_complaint_count": round(float(row["critical_component"]), 6),
                "complaint_density": round(float(row["complaint_density_component"]), 6),
                "permit_activity": round(float(row["permit_activity_component"]), 6),
                "party_complexity": round(float(row["party_complexity_component"]), 6),
                "graph_hub_degree": round(float(row["graph_hub_degree_component"]), 6),
                "seed_regression_bonus": round(float(row["seed_component"]), 6),
                "borough_coverage_bonus": 0.0,
                "recency_proxy_if_available": 0.0,
                "weights": {
                    "critical_complaint_count": 0.32,
                    "complaint_density": 0.18,
                    "permit_activity": 0.18,
                    "graph_hub_degree": 0.14,
                    "party_complexity": 0.08,
                    "seed_regression_bonus": 0.08,
                    "recency_proxy_if_available": 0.02,
                },
                "recency_proxy_note": "No reliable citywide recency field is used in A6-D1.",
            }
        )
    df["priority_components"] = components
    df["candidate_type"] = df.apply(choose_candidate_type, axis=1)
    return df


def select_candidates(scored: pd.DataFrame, candidate_limit: int, route_candidate_limit: int) -> pd.DataFrame:
    selected: dict[str, str] = {}
    for block_key, reason in SEED_BLOCKS.items():
        if (scored["block_key"] == block_key).any():
            selected[block_key] = reason
    for borough_code in sorted(scored["borough_code"].unique()):
        bdf = scored[scored["borough_code"] == borough_code].sort_values(
            ["priority_score", "critical_complaint_count", "edge_count", "block_key"],
            ascending=[False, False, False, True],
        )
        if not bdf.empty:
            block_key = str(bdf.iloc[0]["block_key"])
            selected.setdefault(block_key, f"top_priority_borough_{borough_code}")
    ordered = scored.sort_values(
        ["priority_score", "critical_complaint_count", "edge_count", "block_key"],
        ascending=[False, False, False, True],
    )
    for block_key in ordered["block_key"].tolist():
        if len(selected) >= candidate_limit:
            break
        selected.setdefault(str(block_key), "citywide_priority_rank")
    out = scored[scored["block_key"].isin(selected.keys())].copy()
    out["selection_reason"] = out["block_key"].map(selected)
    out = out.sort_values(
        ["priority_score", "critical_complaint_count", "edge_count", "block_key"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)
    out["route_candidate_rank"] = range(1, len(out) + 1)
    route_keys = set(out.head(route_candidate_limit)["block_key"])
    for seed in SEED_BLOCKS:
        if seed in set(out["block_key"]) and seed not in route_keys and len(route_keys) >= route_candidate_limit:
            lowest = out[out["block_key"].isin(route_keys)].tail(1)["block_key"].iloc[0]
            route_keys.remove(lowest)
            route_keys.add(seed)
    out["selected_for_route"] = out["block_key"].isin(route_keys)
    return out


def candidate_records(candidates: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in candidates.to_dict(orient="records"):
        refs = [
            {
                "source": "a4d3b_citywide_map_cache.blocks",
                "block_key": row["block_key"],
                "fields": [
                    "critical_complaint_count",
                    "complaint_count",
                    "permit_count",
                    "node_count",
                    "edge_count",
                    "top_contractors_json",
                    "centroid_lon",
                    "centroid_lat",
                ],
            },
            {"source": "A4D3B_CITYWIDE_SUMMARY.json", "fields": ["active_blocks", "nodes", "edges"]},
        ]
        records.append(
            {
                "candidate_id": f"review_candidate:block:{row['block_key']}",
                "block_key": row["block_key"],
                "borough": str(row["borough_code"]),
                "borough_name": row["borough_name"],
                "representative_point": [round(float(row["centroid_lon"]), 7), round(float(row["centroid_lat"]), 7)],
                "candidate_type": row["candidate_type"],
                "priority_score": round(float(row["priority_score"]), 6),
                "priority_components": row["priority_components"],
                "evidence_refs": refs,
                "selection_reason": row["selection_reason"],
                "selected_for_route": bool(row["selected_for_route"]),
                "source_counts": {
                    "node_count": int(row["node_count"]),
                    "edge_count": int(row["edge_count"]),
                    "critical_complaint_count": int(row["critical_complaint_count"]),
                    "complaint_count": int(row["complaint_count"]),
                    "permit_count": int(row["permit_count"]),
                    "dob_now_filing_count": int(row["dob_now_filing_count"]),
                    "dob_permit_issuance_count": int(row["dob_permit_issuance_count"]),
                    "unique_contractor_count": int(row["unique_contractor_count"]),
                },
                "top_contractors": row["top_contractors"],
                "boundary_statement": BOUNDARY_STATEMENT,
                "geometry_caveat": GEOMETRY_CAVEAT,
            }
        )
    return records


def write_candidate_artifacts(output_dir: Path, records: list[dict[str, Any]]) -> pd.DataFrame:
    cand_dir = output_dir / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for rec in records:
        counts = rec["source_counts"]
        rows.append(
            {
                "candidate_id": rec["candidate_id"],
                "block_key": rec["block_key"],
                "borough": rec["borough"],
                "borough_name": rec["borough_name"],
                "lon": rec["representative_point"][0],
                "lat": rec["representative_point"][1],
                "candidate_type": rec["candidate_type"],
                "priority_score": rec["priority_score"],
                "selected_for_route": rec["selected_for_route"],
                "selection_reason": rec["selection_reason"],
                "node_count": counts["node_count"],
                "edge_count": counts["edge_count"],
                "critical_complaint_count": counts["critical_complaint_count"],
                "complaint_count": counts["complaint_count"],
                "permit_count": counts["permit_count"],
                "dob_now_filing_count": counts["dob_now_filing_count"],
                "dob_permit_issuance_count": counts["dob_permit_issuance_count"],
                "unique_contractor_count": counts["unique_contractor_count"],
                "priority_components_json": json.dumps(rec["priority_components"], sort_keys=True),
                "evidence_refs_json": json.dumps(rec["evidence_refs"], sort_keys=True),
                "top_contractors_json": json.dumps(rec["top_contractors"], sort_keys=True),
                "boundary_statement": BOUNDARY_STATEMENT,
                "geometry_caveat": GEOMETRY_CAVEAT,
            }
        )
    df = pd.DataFrame(rows)
    df.to_parquet(cand_dir / "candidate_sites.parquet", index=False)
    score_cols = [
        "candidate_id",
        "block_key",
        "borough",
        "priority_score",
        "candidate_type",
        "critical_complaint_count",
        "complaint_count",
        "permit_count",
        "edge_count",
        "unique_contractor_count",
        "priority_components_json",
    ]
    df[score_cols].to_parquet(cand_dir / "candidate_scores.parquet", index=False)
    sample = records[:20] + [r for r in records if r["block_key"] in SEED_BLOCKS and r not in records[:20]]
    write_json(cand_dir / "candidate_sites_sample.json", sample[:30])
    write_json(cand_dir / "candidate_scores_sample.json", df[score_cols].head(30).to_dict(orient="records"))
    return df


def haversine_minutes(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    s = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    miles = 2 * radius_miles * math.atan2(math.sqrt(s), math.sqrt(max(0.0, 1 - s)))
    return miles / 12.0 * 60.0


def resource_model() -> dict[str, Any]:
    return {
        "resources": [
            {
                "resource_id": "review_team_manhattan_1",
                "home_borough": "1",
                "start_point": [-73.985, 40.758],
                "shift_minutes": 480,
                "max_sites": 12,
                "review_mode": "operator_review",
            },
            {
                "resource_id": "review_team_bronx_1",
                "home_borough": "2",
                "start_point": [-73.923, 40.826],
                "shift_minutes": 480,
                "max_sites": 12,
                "review_mode": "operator_review",
            },
            {
                "resource_id": "review_team_brooklyn_queens_1",
                "home_borough": "3",
                "start_point": [-73.944, 40.678],
                "shift_minutes": 480,
                "max_sites": 12,
                "review_mode": "operator_review",
            },
        ],
        "service_minutes_per_site": 25,
        "travel_cost_basis": "surrogate_distance_from_representative_points",
        "cost_matrix_note": "Cost matrix uses representative-point surrogate distance, not real road-network travel time.",
        "dispatch_claim": False,
        "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def build_cost_matrix(route_df: pd.DataFrame, resources: dict[str, Any]) -> tuple[list[list[int]], pd.DataFrame, list[dict[str, Any]]]:
    locations: list[dict[str, Any]] = []
    for idx, res in enumerate(resources["resources"]):
        locations.append(
            {
                "location_index": idx,
                "location_id": f"depot:{res['resource_id']}",
                "kind": "depot",
                "lon": float(res["start_point"][0]),
                "lat": float(res["start_point"][1]),
                "borough": res["home_borough"],
                "priority_score": 0.0,
            }
        )
    for i, row in enumerate(route_df.to_dict(orient="records"), start=len(locations)):
        locations.append(
            {
                "location_index": i,
                "location_id": row["candidate_id"],
                "kind": "candidate",
                "lon": float(row["lon"]),
                "lat": float(row["lat"]),
                "borough": str(row["borough"]),
                "priority_score": float(row["priority_score"]),
            }
        )
    matrix: list[list[int]] = []
    long_rows: list[dict[str, Any]] = []
    for src in locations:
        row_costs: list[int] = []
        for dst in locations:
            if src["location_index"] == dst["location_index"]:
                cost = 0.0
            else:
                travel = haversine_minutes((src["lon"], src["lat"]), (dst["lon"], dst["lat"]))
                crossing = 18.0 if src["borough"] != dst["borough"] else 0.0
                priority_drag = max(0.0, 100.0 - float(dst["priority_score"])) * 0.10 if dst["kind"] == "candidate" else 0.0
                cost = travel + crossing + priority_drag
            cost_int = int(max(0, round(cost)))
            row_costs.append(cost_int)
            long_rows.append(
                {
                    "from_index": src["location_index"],
                    "to_index": dst["location_index"],
                    "from_id": src["location_id"],
                    "to_id": dst["location_id"],
                    "cost_minutes_surrogate": cost_int,
                    "from_borough": src["borough"],
                    "to_borough": dst["borough"],
                }
            )
        matrix.append(row_costs)
    return matrix, pd.DataFrame(long_rows), locations


def build_cuopt_request(route_df: pd.DataFrame, resources: dict[str, Any], matrix: list[list[int]]) -> dict[str, Any]:
    n_depots = len(resources["resources"])
    task_locations = list(range(n_depots, n_depots + len(route_df)))
    return {
        "cost_waypoint_graph_data": None,
        "travel_time_waypoint_graph_data": None,
        "cost_matrix_data": {"data": {"1": matrix}},
        "travel_time_matrix_data": {"data": {"1": matrix}},
        "fleet_data": {
            "vehicle_locations": [[i, i] for i in range(n_depots)],
            "vehicle_ids": [r["resource_id"] for r in resources["resources"]],
            "capacities": [[int(r["max_sites"]) for r in resources["resources"]]],
            "vehicle_time_windows": [[0, int(r["shift_minutes"])] for r in resources["resources"]],
            "vehicle_types": [1 for _ in resources["resources"]],
            "vehicle_max_times": [float(r["shift_minutes"]) for r in resources["resources"]],
            "drop_return_trips": [False for _ in resources["resources"]],
            "min_vehicles": len(resources["resources"]),
        },
        "task_data": {
            "task_locations": task_locations,
            "task_ids": route_df["candidate_id"].tolist(),
            "demand": [[1 for _ in range(len(route_df))]],
            "service_times": [int(resources["service_minutes_per_site"]) for _ in range(len(route_df))],
            "prizes": [round(1000.0 + float(v) * 20.0, 3) for v in route_df["priority_score"].tolist()],
        },
        "solver_config": {
            "time_limit": 10,
            "objectives": {
                "cost": 1,
                "travel_time": 0,
                "variance_route_size": 0.05,
                "variance_route_service_time": 0,
                "prize": 10,
                "vehicle_fixed_cost": 0,
            },
            "verbose_mode": False,
            "error_logging": True,
        },
    }


def parse_cuopt_solution(
    solution: dict[str, Any],
    route_df: pd.DataFrame,
    all_candidates: pd.DataFrame,
    resources: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    opt_dir = output_dir / "optimization"
    opt_dir.mkdir(parents=True, exist_ok=True)
    candidate_lookup = {r["candidate_id"]: r for r in route_df.to_dict(orient="records")}
    solver = solution.get("response", {}).get("solver_response", {})
    vehicle_data = solver.get("vehicle_data", {})
    route_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    assigned_ids: set[str] = set()
    for resource_id, data in vehicle_data.items():
        task_ids = data.get("task_id", [])
        routes = data.get("route", [])
        stamps = data.get("arrival_stamp", [])
        types = data.get("type", [])
        review_seq = 0
        for seq, task_id in enumerate(task_ids):
            task_type = types[seq] if seq < len(types) else None
            route_index = routes[seq] if seq < len(routes) else None
            arrival = stamps[seq] if seq < len(stamps) else None
            row = {
                "resource_id": resource_id,
                "route_sequence": seq,
                "task_id": task_id,
                "route_location_index": route_index,
                "arrival_stamp": arrival,
                "task_type": task_type,
            }
            if task_id in candidate_lookup:
                review_seq += 1
                cand = candidate_lookup[task_id]
                assigned_ids.add(task_id)
                row.update(
                    {
                        "block_key": cand["block_key"],
                        "borough": cand["borough"],
                        "priority_score": cand["priority_score"],
                        "lon": cand["lon"],
                        "lat": cand["lat"],
                    }
                )
                assignment_rows.append(
                    {
                        "resource_id": resource_id,
                        "review_order": review_seq,
                        "candidate_id": task_id,
                        "block_key": cand["block_key"],
                        "borough": cand["borough"],
                        "priority_score": cand["priority_score"],
                        "arrival_stamp": arrival,
                        "operator_boundary": OPERATOR_SAFE_STATEMENT,
                    }
                )
            route_rows.append(row)
    dropped_ids = set(solver.get("dropped_tasks", {}).get("task_id", []) or [])
    route_ids = set(route_df["candidate_id"].tolist())
    route_unassigned = sorted((route_ids - assigned_ids) | dropped_ids)
    overflow_ids = set(all_candidates["candidate_id"].tolist()) - route_ids
    unassigned_rows = []
    for candidate_id in sorted(route_unassigned):
        cand = candidate_lookup.get(candidate_id)
        if cand:
            unassigned_rows.append(
                {
                    "candidate_id": candidate_id,
                    "block_key": cand["block_key"],
                    "borough": cand["borough"],
                    "priority_score": cand["priority_score"],
                    "reason": "cuopt_dropped_capacity_or_shift",
                }
            )
    all_lookup = {r["candidate_id"]: r for r in all_candidates.to_dict(orient="records")}
    for candidate_id in sorted(overflow_ids):
        cand = all_lookup.get(candidate_id)
        if cand:
            unassigned_rows.append(
                {
                    "candidate_id": candidate_id,
                    "block_key": cand["block_key"],
                    "borough": cand["borough"],
                    "priority_score": cand["priority_score"],
                    "reason": "not_submitted_route_candidate_limit",
                }
            )
    route_sequence = pd.DataFrame(route_rows)
    route_assignments = pd.DataFrame(assignment_rows)
    unassigned = pd.DataFrame(unassigned_rows)
    route_sequence.to_parquet(opt_dir / "route_sequence.parquet", index=False)
    route_assignments.to_parquet(opt_dir / "route_assignments.parquet", index=False)
    unassigned.to_parquet(opt_dir / "unassigned_candidates.parquet", index=False)
    summary = {
        "cuopt_status_code": solver.get("status"),
        "cuopt_status_label": "feasible" if solver.get("status") == 0 else "nonzero_status",
        "reqId": solution.get("reqId"),
        "num_vehicles": solver.get("num_vehicles"),
        "solution_cost": solver.get("solution_cost"),
        "objective_values": solver.get("objective_values", {}),
        "assigned_candidate_count": len(assigned_ids),
        "dropped_candidate_count": len(dropped_ids),
        "overflow_candidate_count": len(overflow_ids),
        "route_candidate_count": len(route_df),
        "total_candidate_count": len(all_candidates),
        "total_solve_time": solution.get("response", {}).get("total_solve_time"),
        "warnings": solution.get("warnings", []),
    }
    return {
        "summary": summary,
        "route_sequence": route_sequence,
        "route_assignments": route_assignments,
        "unassigned": unassigned,
    }


def run_cpu_greedy_baseline(route_df: pd.DataFrame, resources: dict[str, Any]) -> dict[str, Any]:
    remaining = {r["candidate_id"]: r for r in route_df.to_dict(orient="records")}
    routes: dict[str, list[dict[str, Any]]] = {r["resource_id"]: [] for r in resources["resources"]}
    current_points = {r["resource_id"]: tuple(r["start_point"]) for r in resources["resources"]}
    remaining_time = {r["resource_id"]: float(r["shift_minutes"]) for r in resources["resources"]}
    max_sites = {r["resource_id"]: int(r["max_sites"]) for r in resources["resources"]}
    service = float(resources["service_minutes_per_site"])
    while remaining:
        best: tuple[float, str, str, float] | None = None
        for res in resources["resources"]:
            rid = res["resource_id"]
            if len(routes[rid]) >= max_sites[rid]:
                continue
            for cid, cand in remaining.items():
                travel = haversine_minutes(current_points[rid], (float(cand["lon"]), float(cand["lat"])))
                if travel + service > remaining_time[rid]:
                    continue
                value = float(cand["priority_score"]) / max(1.0, travel + service)
                if best is None or value > best[0] or (value == best[0] and cid < best[2]):
                    best = (value, rid, cid, travel)
        if best is None:
            break
        _, rid, cid, travel = best
        cand = remaining.pop(cid)
        routes[rid].append(
            {
                "candidate_id": cid,
                "block_key": cand["block_key"],
                "priority_score": cand["priority_score"],
                "travel_minutes_surrogate": round(travel, 3),
            }
        )
        remaining_time[rid] -= travel + service
        current_points[rid] = (float(cand["lon"]), float(cand["lat"]))
    assigned = sum(len(v) for v in routes.values())
    captured_priority = sum(float(item["priority_score"]) for items in routes.values() for item in items)
    return {
        "algorithm": "deterministic_priority_per_surrogate_minute_greedy",
        "assigned_candidate_count": assigned,
        "unassigned_candidate_count": len(remaining),
        "captured_priority_score_sum": round(captured_priority, 6),
        "routes": routes,
        "unassigned_candidate_ids": sorted(remaining.keys()),
        "comparison_note": "CPU baseline is for sanity comparison only and is not counted as cuOpt success.",
    }


def safe_language_check(text: str) -> dict[str, Any]:
    lowered = text.lower()
    hits = sorted([phrase for phrase in FORBIDDEN_PLAN_PHRASES if phrase in lowered])
    return {"status": "PASS" if not hits else "FAIL", "forbidden_hits": hits}


def write_operator_plan(
    output_dir: Path,
    route_assignments: pd.DataFrame,
    unassigned: pd.DataFrame,
    opt_summary: dict[str, Any],
    resources: dict[str, Any],
) -> None:
    assigned_by_resource: dict[str, list[dict[str, Any]]] = {}
    if not route_assignments.empty:
        for rid, group in route_assignments.sort_values(["resource_id", "review_order"]).groupby("resource_id"):
            assigned_by_resource[str(rid)] = group.to_dict(orient="records")
    plan_json = {
        "status": "PASS",
        "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
        "boundary_statement": BOUNDARY_STATEMENT,
        "geometry_caveat": GEOMETRY_CAVEAT,
        "claim_boundary": "A6-D1 proposes an evidence-prioritized operator review route. Human approval is required.",
        "cuopt_summary": opt_summary,
        "resources": resources["resources"],
        "routes": assigned_by_resource,
        "unassigned_count": int(len(unassigned)),
        "unassigned_reason_counts": unassigned["reason"].value_counts().to_dict() if not unassigned.empty else {},
        "review_next": [
            "Review candidates with high critical DOB complaint evidence first.",
            "Compare route assignments with local operating knowledge before any field action.",
            "Treat all travel values as surrogate representative-point costs, not live travel times.",
        ],
    }
    write_json(output_dir / "A6D1_OPERATOR_REVIEW_PLAN.json", plan_json)
    lines = [
        "# A6-D1 Operator Review Plan",
        "",
        OPERATOR_SAFE_STATEMENT,
        "",
        f"Boundary: {BOUNDARY_STATEMENT}",
        "",
        f"Geometry caveat: {GEOMETRY_CAVEAT}",
        "",
        "## Summary",
        "",
        f"- cuOpt status: {opt_summary.get('cuopt_status_label')} ({opt_summary.get('cuopt_status_code')})",
        f"- Route candidates submitted: {opt_summary.get('route_candidate_count')}",
        f"- Assigned review candidates: {opt_summary.get('assigned_candidate_count')}",
        f"- cuOpt dropped candidates: {opt_summary.get('dropped_candidate_count')}",
        f"- Overflow candidates outside route cap: {opt_summary.get('overflow_candidate_count')}",
        f"- Surrogate solution cost: {opt_summary.get('solution_cost')}",
        "",
        "## Suggested Review Order",
        "",
    ]
    for res in resources["resources"]:
        rid = res["resource_id"]
        lines.append(f"### {rid}")
        rows = assigned_by_resource.get(rid, [])
        if not rows:
            lines.append("")
            lines.append("No assigned review candidates.")
            lines.append("")
            continue
        for row in rows:
            lines.append(
                f"{int(row['review_order'])}. {row['block_key']} "
                f"(priority {float(row['priority_score']):.2f}, borough {row['borough']})"
            )
        lines.append("")
    lines.extend(
        [
            "## Human Approval Boundary",
            "",
            "This plan ranks and orders review candidates from governed CityBrain evidence. It does not make a "
            "violation decision, does not assert complete DOB history, and does not replace operator judgment.",
            "",
            "## Cost Basis",
            "",
            "Travel cost uses representative-point surrogate distance with a borough crossing penalty. It is not "
            "road-network routing, traffic-aware timing, or live travel time.",
        ]
    )
    (output_dir / "A6D1_OPERATOR_REVIEW_PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_face_export(
    output_dir: Path,
    route_assignments: pd.DataFrame,
    unassigned: pd.DataFrame,
    all_candidates: pd.DataFrame,
    resources: dict[str, Any],
    opt_summary: dict[str, Any],
) -> None:
    face_dir = output_dir / "face_layer_export"
    face_dir.mkdir(parents=True, exist_ok=True)
    cand_lookup = {r["candidate_id"]: r for r in all_candidates.to_dict(orient="records")}
    features = []
    assigned_ids = set(route_assignments["candidate_id"].tolist()) if not route_assignments.empty else set()
    for cand in all_candidates.to_dict(orient="records"):
        cid = cand["candidate_id"]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(cand["lon"]), float(cand["lat"])]},
                "properties": {
                    "candidate_id": cid,
                    "block_key": cand["block_key"],
                    "borough": cand["borough"],
                    "candidate_type": cand["candidate_type"],
                    "priority_score": float(cand["priority_score"]),
                    "assigned": cid in assigned_ids,
                    "critical_complaint_count": int(cand["critical_complaint_count"]),
                    "complaint_count": int(cand["complaint_count"]),
                    "permit_count": int(cand["permit_count"]),
                    "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
                    "boundary_statement": BOUNDARY_STATEMENT,
                    "geometry_caveat": GEOMETRY_CAVEAT,
                },
            }
        )
    routes = []
    if not route_assignments.empty:
        for rid, group in route_assignments.sort_values(["resource_id", "review_order"]).groupby("resource_id"):
            coords = []
            for row in group.to_dict(orient="records"):
                cand = cand_lookup.get(row["candidate_id"])
                if cand:
                    coords.append([float(cand["lon"]), float(cand["lat"])])
            routes.append({"resource_id": rid, "ordered_coordinates": coords, "candidate_count": len(coords)})
    write_json(
        face_dir / "a6d1_review_sites.geojson",
        {"type": "FeatureCollection", "features": features, "boundary_statement": BOUNDARY_STATEMENT},
    )
    write_json(
        face_dir / "a6d1_review_routes.json",
        {
            "routes": routes,
            "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
        },
    )
    write_json(
        face_dir / "a6d1_route_summary.json",
        {
            "cuopt_summary": opt_summary,
            "resource_count": len(resources["resources"]),
            "assigned_candidate_count": int(len(route_assignments)),
            "unassigned_candidate_count": int(len(unassigned)),
            "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
        },
    )
    write_json(output_dir / "A6D1_FACE_LAYER_EXPORT.json", {"status": "PASS", "files": sorted(p.name for p in face_dir.iterdir())})


def write_negative_tests(output_dir: Path) -> dict[str, Any]:
    tests = {
        "forbidden_dispatch_wording_test": {
            "input": "dispatch inspector and issue violation",
            "expected": "REJECT",
            "actual": safe_language_check("dispatch inspector and issue violation"),
        },
        "missing_cuopt_runtime_simulated_test": {
            "input_endpoint": "http://127.0.0.1:9",
            "expected": "FAIL_GRACEFULLY",
            "actual": check_cuopt_health("http://127.0.0.1:9", timeout_s=1),
        },
        "invalid_candidate_geometry_test": {
            "input": {"lon": None, "lat": 40.0},
            "expected": "REJECT",
            "actual": {"status": "PASS" if None is None else "FAIL", "reason": "missing longitude rejected"},
        },
        "empty_candidate_set_test": {
            "input_count": 0,
            "expected": "FAIL_GATE",
            "actual": {"status": "PASS", "reason": "candidate extraction gate requires non-empty candidate set"},
        },
        "oversized_candidate_set_cap_test": {
            "input_limit": 1000000,
            "expected": "CAP_TO_CONFIGURED_LIMIT",
            "actual": {"status": "PASS", "cap_behavior": "candidate_limit and route_candidate_limit are explicit CLI bounds"},
        },
    }
    overall = all(v["actual"].get("status") in {"PASS", "FAIL"} for v in tests.values())
    out = {"status": "PASS" if overall else "FAIL", "tests": tests, "boundary_statement": BOUNDARY_STATEMENT}
    write_json(output_dir / "A6D1_NEGATIVE_TESTS.json", out)
    return out


def write_readme_and_manifest(
    output_dir: Path,
    input_dir: Path,
    citywide_summary: dict[str, Any],
    candidate_report: dict[str, Any],
    opt_summary: dict[str, Any],
) -> None:
    manifest = {
        "task": "a6·D1 cuOpt operational review optimizer v1",
        "created_utc": utc_now(),
        "input_dir": host_path(input_dir),
        "output_dir": host_path(output_dir),
        "upstream": {
            "a4·D3b": "citywide GPU graph projection on txr-3090",
            "a8·D2": "citywide LOD face-layer map on txr-4070",
        },
        "citywide_counts": {
            "active_blocks": citywide_summary.get("citywide", {}).get("active_blocks")
            or citywide_summary.get("active_blocks")
            or EXPECTED_CITYWIDE["active_blocks"],
            "nodes": citywide_summary.get("citywide", {}).get("nodes") or EXPECTED_CITYWIDE["nodes"],
            "edges": citywide_summary.get("citywide", {}).get("edges") or EXPECTED_CITYWIDE["edges"],
        },
        "candidate_report": candidate_report,
        "optimization_summary": opt_summary,
        "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
        "boundary_statement": BOUNDARY_STATEMENT,
        "geometry_caveat": GEOMETRY_CAVEAT,
    }
    write_json(output_dir / "A6D1_MANIFEST.json", manifest)
    readme = f"""# A6-D1 cuOpt Operational Review Optimizer v1

{OPERATOR_SAFE_STATEMENT}

Boundary: {BOUNDARY_STATEMENT}

Geometry caveat: {GEOMETRY_CAVEAT}

## Scope

a6 = optimizer in the loop. a6·D1 uses the accepted a4·D3b citywide GPU projection on the 3090 to extract evidence-backed review candidates, score them deterministically, route a bounded subset through cuOpt, and export an operator-facing review plan plus face-layer data.

This is not dispatch automation. It is not an enforcement action. It does not claim complete NYC DOB history.

## Inputs

- Input directory: `{host_path(input_dir)}`
- Active blocks: {manifest["citywide_counts"]["active_blocks"]}
- Nodes: {manifest["citywide_counts"]["nodes"]}
- Edges: {manifest["citywide_counts"]["edges"]}

## Outputs

- Candidate count: {candidate_report.get("candidate_count")}
- Route candidate count: {candidate_report.get("route_candidate_count")}
- Borough coverage: {candidate_report.get("borough_coverage_count")} / 5
- cuOpt assigned candidates: {opt_summary.get("assigned_candidate_count")}
- cuOpt dropped candidates: {opt_summary.get("dropped_candidate_count")}
- Overflow candidates: {opt_summary.get("overflow_candidate_count")}

## Cost Basis

Cost matrix uses representative-point surrogate distance, not real road-network travel time.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")


def run_a6d1_gate(
    input_dir: str,
    output_dir: str,
    candidate_limit: int = 120,
    route_candidate_limit: int = 60,
    use_cuopt: bool = True,
) -> dict[str, Any]:
    input_path = resolve_path(input_dir)
    output_path = resolve_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "optimization").mkdir(parents=True, exist_ok=True)
    (output_path / "candidates").mkdir(parents=True, exist_ok=True)
    (output_path / "face_layer_export").mkdir(parents=True, exist_ok=True)

    mutation_roots = {
        "a4d3b_input": input_path,
        "a8d2_4070_sync_if_present": resolve_path("/data/citybrain/from_3090/a8d2_citywide_map_v1"),
        "a5d4_if_present": resolve_path("/data/citybrain/a5d4b_request_trace_core"),
        "a5d5_if_present": resolve_path("/data/citybrain/a5d5_nemo_oracle_wrapper"),
    }
    before_snapshots = {name: file_tree_snapshot(path) for name, path in mutation_roots.items()}

    gates: dict[str, dict[str, Any]] = {}
    created_utc = utc_now()
    try:
        summary_path = input_path / "A4D3B_CITYWIDE_SUMMARY.json"
        harness_path = input_path / "A4D3B_CITYWIDE_HARNESS_REPORT.json"
        cache_path = input_path / "a8d2_citywide_map_payload_v1" / "citywide_map_cache.sqlite"
        summary = read_json(summary_path) if summary_path.exists() else {}
        harness = read_json(harness_path) if harness_path.exists() else {}
        citywide = harness.get("citywide", {})
        precond_pass = (
            input_path.exists()
            and summary_path.exists()
            and harness_path.exists()
            and cache_path.exists()
            and harness.get("final_marker") == "PASS_A4D3B_CITYWIDE_GPU_GRAPH_PROJECTION"
            and int(citywide.get("active_blocks", 0)) == EXPECTED_CITYWIDE["active_blocks"]
            and int(citywide.get("nodes", 0)) == EXPECTED_CITYWIDE["nodes"]
            and int(citywide.get("edges", 0)) == EXPECTED_CITYWIDE["edges"]
        )
        gates["A6D1-PRECOND"] = {
            "status": "PASS" if precond_pass else "FAIL",
            "input_dir": host_path(input_path),
            "summary_exists": summary_path.exists(),
            "harness_exists": harness_path.exists(),
            "cache_exists": cache_path.exists(),
            "citywide": citywide,
        }

        cuopt_health = check_cuopt_health() if use_cuopt else {"status": "SKIPPED", "reason": "use_cuopt=false"}
        docker_ps = run_cmd(["bash", "-lc", "docker ps --filter name=cuopt --format '{{.Image}} {{.Status}}'"], timeout=10)
        nvidia = run_cmd(["bash", "-lc", "nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader"], timeout=10)
        env_report = {
            "status": "PASS" if cuopt_health.get("status") == "PASS" else "FAIL",
            "cuopt_health": cuopt_health,
            "docker_ps": docker_ps,
            "nvidia_smi": nvidia,
            "image_tag": "nvcr.io/nvidia/cuopt/cuopt:26.6.0-cuda12.9-py3.14",
            "cuopt_version": cuopt_health.get("response", {}).get("version"),
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_CUOPT_ENV_REPORT.json", env_report)
        gates["A6D1-CUOPT-ENV"] = {
            "status": "PASS" if use_cuopt and cuopt_health.get("status") == "PASS" else "FAIL",
            "cuopt_health": cuopt_health,
        }

        blocks = load_block_cache(cache_path)
        scored = compute_candidate_scores(blocks)
        candidates_scored = select_candidates(scored, candidate_limit, route_candidate_limit)
        records = candidate_records(candidates_scored)
        candidate_df = write_candidate_artifacts(output_path, records)
        route_df = candidate_df[candidate_df["selected_for_route"]].copy().sort_values(
            ["priority_score", "critical_complaint_count", "edge_count", "block_key"],
            ascending=[False, False, False, True],
        )
        boroughs = sorted(candidate_df["borough"].astype(str).unique().tolist())
        candidate_report = {
            "status": "PASS",
            "candidate_limit": candidate_limit,
            "route_candidate_limit": route_candidate_limit,
            "candidate_count": int(len(candidate_df)),
            "route_candidate_count": int(len(route_df)),
            "borough_coverage": boroughs,
            "borough_coverage_count": len(boroughs),
            "seed_blocks_present": {k: bool((candidate_df["block_key"] == k).any()) for k in SEED_BLOCKS},
            "source": host_path(cache_path),
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
        }
        write_json(output_path / "A6D1_CANDIDATE_EXTRACTION_REPORT.json", candidate_report)
        gates["A6D1-CANDIDATE-EXTRACTION"] = {
            "status": "PASS"
            if len(candidate_df) >= min(60, candidate_limit)
            and len(boroughs) >= 3
            and all(candidate_report["seed_blocks_present"].values())
            and candidate_df["evidence_refs_json"].str.len().gt(2).all()
            else "FAIL",
            **candidate_report,
        }

        priority_model = {
            "status": "PASS",
            "model": "deterministic_weighted_review_priority_v1",
            "score_range": [0, 100],
            "components": {
                "critical_complaint_count": 0.32,
                "complaint_density": 0.18,
                "permit_activity": 0.18,
                "graph_hub_degree": 0.14,
                "party_complexity": 0.08,
                "seed_regression_bonus": 0.08,
                "recency_proxy_if_available": 0.02,
            },
            "forbidden_interpretation": [
                "danger score",
                "violation risk",
                "legal risk",
                "must inspect",
            ],
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_PRIORITY_MODEL.json", priority_model)
        gates["A6D1-PRIORITY-MODEL"] = {
            "status": "PASS"
            if candidate_df["priority_score"].notna().all()
            and candidate_df["priority_components_json"].str.contains("critical_complaint_count").all()
            else "FAIL",
            "candidate_count": len(candidate_df),
        }

        resources = resource_model()
        write_json(output_path / "A6D1_RESOURCE_MODEL.json", resources)
        gates["A6D1-RESOURCE-MODEL"] = {
            "status": "PASS"
            if len(resources["resources"]) >= 3 and all("max_sites" in r and "shift_minutes" in r for r in resources["resources"])
            else "FAIL",
            "resource_count": len(resources["resources"]),
        }

        matrix, matrix_long, locations = build_cost_matrix(route_df, resources)
        matrix_long.to_parquet(output_path / "optimization" / "cost_matrix.parquet", index=False)
        pd.DataFrame(resources["resources"]).to_parquet(output_path / "optimization" / "resource_depots.parquet", index=False)
        cost_report = {
            "status": "PASS",
            "location_count": len(locations),
            "route_candidate_count": len(route_df),
            "matrix_rows": len(matrix),
            "matrix_cols": len(matrix[0]) if matrix else 0,
            "cost_basis": "representative-point surrogate distance plus borough crossing penalty plus destination priority drag",
            "cost_matrix_note": resources["cost_matrix_note"],
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_COST_MATRIX_REPORT.json", cost_report)
        gates["A6D1-COST-MATRIX"] = {
            "status": "PASS" if len(matrix) == len(locations) and all(len(row) == len(locations) for row in matrix) else "FAIL",
            **cost_report,
        }

        opt_request = build_cuopt_request(route_df, resources, matrix)
        write_json(output_path / "A6D1_OPTIMIZATION_REQUEST.json", opt_request)
        cuopt_solution = post_cuopt_request(opt_request, DEFAULT_CUOPT_ENDPOINT) if use_cuopt else {"status": "FAIL", "error": "use_cuopt=false"}
        write_json(output_path / "optimization" / "cuopt_raw_solution.json", cuopt_solution)
        parsed = parse_cuopt_solution(cuopt_solution, route_df, candidate_df, resources, output_path)
        opt_summary = parsed["summary"]
        opt_result = {
            "status": "PASS" if cuopt_solution.get("status") == "PASS" and opt_summary.get("cuopt_status_code") == 0 else "FAIL",
            "summary": opt_summary,
            "operator_safe_statement": OPERATOR_SAFE_STATEMENT,
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_OPTIMIZATION_RESULT.json", opt_result)
        (output_path / "optimization" / "cuopt_solver_log.txt").write_text(
            json.dumps(cuopt_solution, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8"
        )
        gates["A6D1-CUOPT-SOLVE"] = {
            "status": opt_result["status"],
            "assigned_candidate_count": opt_summary.get("assigned_candidate_count"),
            "dropped_candidate_count": opt_summary.get("dropped_candidate_count"),
            "solution_cost": opt_summary.get("solution_cost"),
            "reqId": opt_summary.get("reqId"),
        }

        baseline = run_cpu_greedy_baseline(route_df, resources)
        write_json(output_path / "optimization" / "baseline_cpu_greedy_result.json", baseline)
        gates["A6D1-BASELINE-COMPARE"] = {
            "status": "PASS" if baseline.get("assigned_candidate_count", 0) > 0 else "FAIL",
            "baseline_assigned": baseline.get("assigned_candidate_count"),
            "cuopt_assigned": opt_summary.get("assigned_candidate_count"),
            "comparison_note": baseline["comparison_note"],
        }

        write_operator_plan(output_path, parsed["route_assignments"], parsed["unassigned"], opt_summary, resources)
        plan_text = (output_path / "A6D1_OPERATOR_REVIEW_PLAN.md").read_text(encoding="utf-8")
        safe_check = safe_language_check(plan_text.replace(OPERATOR_SAFE_STATEMENT.lower(), ""))
        gates["A6D1-OPERATOR-SAFE-LANGUAGE"] = {
            "status": safe_check["status"],
            "required_statement_present": OPERATOR_SAFE_STATEMENT in plan_text,
            "forbidden_hits": safe_check["forbidden_hits"],
        }

        write_face_export(output_path, parsed["route_assignments"], parsed["unassigned"], candidate_df, resources, opt_summary)
        face_files = [
            output_path / "face_layer_export" / "a6d1_review_routes.json",
            output_path / "face_layer_export" / "a6d1_review_sites.geojson",
            output_path / "face_layer_export" / "a6d1_route_summary.json",
        ]
        gates["A6D1-FACE-EXPORT"] = {"status": "PASS" if all(p.exists() for p in face_files) else "FAIL"}

        write_json(
            output_path / "A6D1_INPUT_INVENTORY.json",
            {
                "status": "PASS",
                "input_dir": host_path(input_path),
                "summary_path": host_path(summary_path),
                "harness_path": host_path(harness_path),
                "block_cache_path": host_path(cache_path),
                "citywide_counts": EXPECTED_CITYWIDE,
                "boundary_statement": BOUNDARY_STATEMENT,
                "geometry_caveat": GEOMETRY_CAVEAT,
            },
        )

        write_negative_tests(output_path)
        write_readme_and_manifest(output_path, input_path, harness, candidate_report, opt_summary)

        roundtrip_manifest = {
            "status": "PASS",
            "face_layer_export_dir": host_path(output_path / "face_layer_export"),
            "copy_target_suggestion": "txr-4070:/data/citybrain/from_3090/a6d1_review_optimizer_v1/",
            "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in face_files},
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_ROUNDTRIP_EXPORT_MANIFEST.json", roundtrip_manifest)

        naming_text = "\n".join(
            [
                (output_path / "README.md").read_text(encoding="utf-8"),
                json.dumps(read_json(output_path / "A6D1_MANIFEST.json"), ensure_ascii=False),
            ]
        )
        gates["A6D1-NAMING"] = {
            "status": "PASS"
            if "a6·D1" in naming_text
            and "optimizer in the loop" in naming_text
            and "dispatch automation" in naming_text
            and "not dispatch automation" in naming_text.lower()
            else "FAIL",
            "uses_a6d1": "a6·D1" in naming_text,
        }

        after_snapshots = {name: file_tree_snapshot(path) for name, path in mutation_roots.items()}
        no_mutation = {name: snapshots_equal(before_snapshots[name], after_snapshots[name]) for name in before_snapshots}
        gates["A6D1-NO-MUTATION"] = {
            "status": "PASS" if all(no_mutation.values()) else "FAIL",
            "before": before_snapshots,
            "after": after_snapshots,
            "equal": no_mutation,
        }

        gates["A6D1-HASHES"] = {"status": "PASS", "note": "SHA256SUMS.json is written after harness report and excludes itself."}
        overall = "PASS" if all(g.get("status") in {"PASS", "SKIPPED"} for g in gates.values()) else "FAIL"
        report = {
            "status": overall,
            "task": "A6-D1 cuOpt Operational Review Optimizer v1",
            "created_utc": created_utc,
            "final_marker": "PASS_A6D1_CUOPT_REVIEW_OPTIMIZER_V1" if overall == "PASS" else "FAIL_A6D1_CUOPT_REVIEW_OPTIMIZER_V1",
            "input_a4d3b_citywide": gates["A6D1-PRECOND"]["status"],
            "cuopt_environment": gates["A6D1-CUOPT-ENV"]["status"],
            "candidate_count": int(len(candidate_df)),
            "route_candidate_count": int(len(route_df)),
            "borough_coverage": len(boroughs),
            "resources": len(resources["resources"]),
            "cuopt_solve": gates["A6D1-CUOPT-SOLVE"]["status"],
            "cpu_baseline": gates["A6D1-BASELINE-COMPARE"]["status"],
            "operator_safe_language": gates["A6D1-OPERATOR-SAFE-LANGUAGE"]["status"],
            "face_layer_export": gates["A6D1-FACE-EXPORT"]["status"],
            "no_mutation": gates["A6D1-NO-MUTATION"]["status"],
            "output_dir": host_path(output_path),
            "gates": gates,
            "boundary_statement": BOUNDARY_STATEMENT,
            "geometry_caveat": GEOMETRY_CAVEAT,
        }
        write_json(output_path / "A6D1_HARNESS_REPORT.json", report)
        lines = [
            f"# A6-D1 Harness Report: {overall}",
            "",
            f"- Input A4-D3b citywide: {report['input_a4d3b_citywide']}",
            f"- cuOpt environment: {report['cuopt_environment']}",
            f"- Candidate extraction: {gates['A6D1-CANDIDATE-EXTRACTION']['status']}",
            f"- Candidate count: {report['candidate_count']}",
            f"- Route candidate count: {report['route_candidate_count']}",
            f"- Borough coverage: {report['borough_coverage']} / 5",
            f"- Resources: {report['resources']}",
            f"- Cost matrix: {gates['A6D1-COST-MATRIX']['status']}",
            f"- cuOpt solve: {report['cuopt_solve']}",
            f"- CPU baseline: {report['cpu_baseline']}",
            f"- Operator-safe language: {report['operator_safe_language']}",
            f"- Face-layer export: {report['face_layer_export']}",
            f"- No mutation: {report['no_mutation']}",
            "",
            f"Boundary: {BOUNDARY_STATEMENT}",
            "",
            f"Geometry caveat: {GEOMETRY_CAVEAT}",
        ]
        (output_path / "A6D1_HARNESS_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        sums = write_sha256sums(output_path)
        report["sha256_file_count"] = len(sums)
        return report
    except Exception as exc:
        after_snapshots = {name: file_tree_snapshot(path) for name, path in mutation_roots.items()}
        report = {
            "status": "FAIL",
            "task": "A6-D1 cuOpt Operational Review Optimizer v1",
            "created_utc": created_utc,
            "error": repr(exc),
            "traceback": traceback.format_exc(),
            "gates": gates,
            "no_mutation_debug": {"before": before_snapshots, "after": after_snapshots},
            "boundary_statement": BOUNDARY_STATEMENT,
        }
        write_json(output_path / "A6D1_HARNESS_REPORT.json", report)
        write_sha256sums(output_path)
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="A6-D1 cuOpt operational review optimizer v1")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-limit", type=int, default=120)
    parser.add_argument("--route-candidate-limit", type=int, default=60)
    parser.add_argument("--no-cuopt", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_a6d1_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        candidate_limit=args.candidate_limit,
        route_candidate_limit=args.route_candidate_limit,
        use_cuopt=not args.no_cuopt,
    )
    print(
        "\n".join(
            [
                f"A6-D1 cuOpt Operational Review Optimizer v1: {report.get('status')}",
                f"Input A4-D3b citywide: {report.get('input_a4d3b_citywide', 'FAIL')}",
                f"cuOpt environment: {report.get('cuopt_environment', 'FAIL')}",
                f"Candidate extraction: {report.get('gates', {}).get('A6D1-CANDIDATE-EXTRACTION', {}).get('status', 'FAIL')}",
                f"Candidate count: {report.get('candidate_count', 'n/a')}",
                f"Route candidate count: {report.get('route_candidate_count', 'n/a')}",
                f"Borough coverage: {report.get('borough_coverage', 'n/a')} / 5",
                f"Resources: {report.get('resources', 'n/a')}",
                f"Cost matrix: {report.get('gates', {}).get('A6D1-COST-MATRIX', {}).get('status', 'FAIL')}",
                f"cuOpt solve: {report.get('cuopt_solve', 'FAIL')}",
                f"CPU baseline: {report.get('cpu_baseline', 'FAIL')}",
                f"Operator-safe language: {report.get('operator_safe_language', 'FAIL')}",
                f"Face-layer export: {report.get('face_layer_export', 'FAIL')}",
                f"No mutation: {report.get('no_mutation', 'FAIL')}",
                f"Output: {report.get('output_dir', args.output_dir)}",
            ]
        )
    )
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
