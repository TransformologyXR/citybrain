from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TASK_NAME = "F3-NYC-D4 Candidate Prioritization + Operator Review Routing Plan"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d4_candidate_prioritization_review_routing"
DEFAULT_D3_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"

NO_OVERCLAIM_LINES = [
    "F3-NYC-D4 creates operator review prioritization and situational assessment routing plans only.",
    "D4 does not perform emergency dispatch optimization.",
    "D4 does not make emergency response recommendations.",
    "D4 does not certify affected buildings or affected assets.",
    "D4 does not geocode address-only events.",
    "D4 does not claim live or real-time incident management.",
    "D4 route plans are review itineraries using straight-line context proxies, not navigable routes.",
    "Candidate affected tax-lot links remain candidate-only.",
    "Firehouse/resource context is not dispatched-unit truth.",
    "MVC Vehicles remain event context only, not primary crash events.",
    "No NIM/NeMo/LLM generated these facts.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"emergency dispatch optimization (?:is )?(?:performed|complete|available|ready)",
    r"dispatch(?:ed)? unit truth",
    r"emergency response recommendations? (?:are )?(?:made|available|ready)",
    r"affected buildings? (?:are )?certified",
    r"affected assets? (?:are )?certified",
    r"certified affected (?:building|asset)",
    r"address-only events? (?:are )?geocoded",
    r"live incident management (?:is|enabled|available|ready)",
    r"real-time incident management (?:is|enabled|available|ready)",
    r"navigable routes? (?:are )?(?:generated|ready|available)",
    r"mvc vehicles (?:are|is) (?:the )?primary crash events?",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D4-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d4" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["canonical", "evidence", "queries", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value is not None else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:120] or fallback


def cell(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "nat", "none", "<na>"} else None


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def sample_records(frame: pd.DataFrame, n: int) -> list[dict[str, Any]]:
    if frame.empty or "_empty" in frame.columns:
        return []
    return frame.head(n).where(pd.notna(frame.head(n)), None).to_dict("records")


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [path for path in sorted(root.rglob("*")) if path.is_file()]
        for path in files:
            watched[str(path)] = {
                "exists": True,
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "sha256": sha256_file(path) if path.stat().st_size < 250_000_000 else None,
            }
    return watched


def d3_paths(d3_dir: Path) -> dict[str, Path]:
    canonical = d3_dir / "canonical"
    return {
        "harness": d3_dir / "F3_NYC_D3_HARNESS_REPORT.json",
        "input_inventory": d3_dir / "F3_NYC_D3_INPUT_INVENTORY.json",
        "asset_edges": canonical / "f3_nyc_d3_incident_asset_candidate_edges.parquet",
        "response_edges": canonical / "f3_nyc_d3_response_resource_context_edges.parquet",
        "asset_candidates": canonical / "f3_nyc_d3_asset_candidates.parquet",
        "location_tiers": canonical / "f3_nyc_d3_location_tiers.parquet",
    }


def d2_paths_from_d3(d3_dir: Path, explicit_d2_dir: str | None) -> dict[str, Path]:
    d2_dir = Path(explicit_d2_dir) if explicit_d2_dir else None
    if d2_dir is None:
        inventory = read_json(d3_dir / "F3_NYC_D3_INPUT_INVENTORY.json", {})
        if inventory.get("d2_dir"):
            d2_dir = Path(inventory["d2_dir"])
    if d2_dir is None:
        d2_dir = Path("outputs/f3_nyc_d2_fdny_incident_response_slice_ingest")
    canonical = d2_dir / "canonical"
    return {
        "d2_dir": d2_dir,
        "mvc_crashes": canonical / "f3_nyc_d2_mvc_crash_events.parquet",
        "firehouses": canonical / "f3_nyc_d2_firehouses.parquet",
        "mvc_vehicle_context": canonical / "f3_nyc_d2_mvc_vehicle_context.parquet",
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * radius * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def build_prioritized_candidates(asset_edges: pd.DataFrame, response_edges: pd.DataFrame, tiers: pd.DataFrame, mvc_events: pd.DataFrame, asset_nodes: pd.DataFrame) -> pd.DataFrame:
    edge = asset_edges.copy()
    response = response_edges.copy()
    tier = tiers.copy()
    mvc = mvc_events.copy()
    assets = asset_nodes.copy()

    asset_summary = edge.groupby("source_id").agg(
        asset_candidate_count=("target_id", "nunique"),
        nearest_asset_distance_m=("distance_m", "min"),
        mean_asset_confidence=("confidence", "mean"),
        within_polygon_count=("spatial_relation", lambda values: int((values == "point_within_tax_lot_polygon").sum())),
    ).reset_index()
    first_assets = edge.sort_values(["source_id", "distance_m"]).drop_duplicates("source_id")[
        ["source_id", "target_id", "target_bbl", "spatial_relation", "join_method", "status", "overclaim_guard"]
    ].rename(
        columns={
            "target_id": "primary_candidate_asset_id",
            "target_bbl": "primary_candidate_bbl",
            "spatial_relation": "primary_asset_spatial_relation",
            "join_method": "asset_join_method",
            "status": "asset_edge_status",
            "overclaim_guard": "asset_overclaim_guard",
        }
    )
    asset_summary = asset_summary.merge(first_assets, on="source_id", how="left")

    nearest_response = response[response["rank"] == 1].copy()
    nearest_response = nearest_response.sort_values(["source_id", "distance_m"]).drop_duplicates("source_id")[
        ["source_id", "target_id", "distance_m", "confidence", "status", "overclaim_guard"]
    ].rename(
        columns={
            "target_id": "nearest_resource_id",
            "distance_m": "nearest_resource_distance_m",
            "confidence": "resource_context_confidence",
            "status": "resource_context_status",
            "overclaim_guard": "resource_overclaim_guard",
        }
    )

    tier_cols = [
        "event_id",
        "event_family",
        "source_record_id",
        "event_type",
        "event_time",
        "borough",
        "location_status",
        "location_confidence_tier",
        "asset_link_policy",
        "confidence",
    ]
    tier = tier[tier_cols].rename(columns={"event_id": "source_id", "confidence": "location_confidence"})
    mvc_cols = ["canonical_id", "collision_id", "latitude", "longitude", "zipcode", "address_text"]
    mvc = mvc[mvc_cols].rename(columns={"canonical_id": "source_id"})
    assets_small = assets[["canonical_id", "address_text", "land_use", "building_class", "zipcode"]].rename(
        columns={
            "canonical_id": "primary_candidate_asset_id",
            "address_text": "asset_address_text",
            "zipcode": "asset_zipcode",
        }
    )

    candidates = asset_summary.merge(tier, on="source_id", how="left")
    candidates = candidates.merge(mvc, on="source_id", how="left")
    candidates = candidates.merge(nearest_response, on="source_id", how="left")
    candidates = candidates.merge(assets_small, on="primary_candidate_asset_id", how="left")
    candidates = candidates[candidates["location_confidence_tier"] == "A"].copy()

    asset_threshold = candidates["nearest_asset_distance_m"].fillna(30.0).clip(lower=0, upper=30.0)
    resource_threshold = candidates["nearest_resource_distance_m"].fillna(3000.0).clip(lower=0, upper=3000.0)
    candidates["location_component"] = candidates["location_confidence"].fillna(0.0) * 100.0
    candidates["asset_proximity_component"] = (1.0 - asset_threshold / 30.0) * 100.0
    candidates["asset_context_component"] = candidates["mean_asset_confidence"].fillna(0.0) * 100.0
    candidates["resource_proximity_component"] = (1.0 - resource_threshold / 3000.0) * 100.0
    candidates["evidence_completeness_component"] = np.where(
        candidates["nearest_resource_id"].notna() & candidates["primary_candidate_asset_id"].notna(),
        100.0,
        70.0,
    )
    candidates["operator_review_priority_score"] = (
        0.35 * candidates["location_component"]
        + 0.25 * candidates["asset_proximity_component"]
        + 0.20 * candidates["resource_proximity_component"]
        + 0.10 * candidates["asset_context_component"]
        + 0.10 * candidates["evidence_completeness_component"]
    ).round(3)
    candidates["priority_model"] = "deterministic_review_score_v1"
    candidates["priority_status"] = "operator_review_candidate"
    candidates["route_plan_eligibility"] = np.where(candidates["nearest_resource_id"].notna(), "eligible_for_review_itinerary", "not_eligible_missing_resource_context")
    candidates["semantic_guard"] = "score_orders_operator_review_only_not_emergency_response_recommendation"
    order_cols = [
        "source_id",
        "source_record_id",
        "event_type",
        "event_time",
        "borough",
        "latitude",
        "longitude",
        "zipcode",
        "location_status",
        "location_confidence_tier",
        "asset_link_policy",
        "operator_review_priority_score",
        "priority_model",
        "priority_status",
        "route_plan_eligibility",
        "primary_candidate_asset_id",
        "primary_candidate_bbl",
        "asset_address_text",
        "land_use",
        "building_class",
        "asset_candidate_count",
        "nearest_asset_distance_m",
        "primary_asset_spatial_relation",
        "asset_edge_status",
        "nearest_resource_id",
        "nearest_resource_distance_m",
        "resource_context_status",
        "location_component",
        "asset_proximity_component",
        "resource_proximity_component",
        "asset_context_component",
        "evidence_completeness_component",
        "semantic_guard",
    ]
    return candidates[order_cols].sort_values(
        ["operator_review_priority_score", "nearest_asset_distance_m", "nearest_resource_distance_m"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def build_review_routes(candidates: pd.DataFrame, firehouses: pd.DataFrame, max_candidates: int, max_routes: int, stops_per_route: int) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    eligible = candidates[candidates["route_plan_eligibility"] == "eligible_for_review_itinerary"].head(max_candidates).copy()
    if eligible.empty:
        return pd.DataFrame(), pd.DataFrame(), {"status": "FAIL", "reason": "No candidates eligible for review itineraries."}
    firehouses = firehouses[["canonical_id", "source_record_id", "borough", "address_text", "latitude", "longitude"]].rename(
        columns={
            "canonical_id": "nearest_resource_id",
            "source_record_id": "resource_label",
            "borough": "resource_borough",
            "address_text": "resource_address_text",
            "latitude": "resource_latitude",
            "longitude": "resource_longitude",
        }
    )
    eligible = eligible.merge(firehouses, on="nearest_resource_id", how="left")
    eligible["route_group_borough"] = eligible["borough"].fillna(eligible["resource_borough"]).fillna("UNKNOWN")
    group_summary = eligible.groupby(["route_group_borough", "nearest_resource_id"]).agg(
        candidate_count=("source_id", "nunique"),
        max_score=("operator_review_priority_score", "max"),
        median_resource_distance_m=("nearest_resource_distance_m", "median"),
    ).reset_index()
    group_summary = group_summary.sort_values(["max_score", "candidate_count"], ascending=[False, False]).head(max_routes)

    route_rows: list[dict[str, Any]] = []
    stop_rows: list[dict[str, Any]] = []
    for route_idx, group in enumerate(group_summary.to_dict("records"), start=1):
        route_candidates = eligible[
            (eligible["route_group_borough"] == group["route_group_borough"])
            & (eligible["nearest_resource_id"] == group["nearest_resource_id"])
        ].sort_values(["operator_review_priority_score", "nearest_asset_distance_m"], ascending=[False, True]).head(stops_per_route)
        if route_candidates.empty:
            continue
        first = route_candidates.iloc[0]
        route_id = f"review_route:us-nyc:flow3:d4:{route_idx:03d}:{safe_id(group['route_group_borough'])}:{safe_id(group['nearest_resource_id'])}"
        prev_lat = float(first["resource_latitude"]) if pd.notna(first.get("resource_latitude")) else None
        prev_lon = float(first["resource_longitude"]) if pd.notna(first.get("resource_longitude")) else None
        total_proxy_m = 0.0
        for sequence, candidate in enumerate(route_candidates.to_dict("records"), start=1):
            lat = float(candidate["latitude"])
            lon = float(candidate["longitude"])
            if prev_lat is None or prev_lon is None:
                segment_m = float(candidate.get("nearest_resource_distance_m") or 0.0)
            else:
                segment_m = haversine_m(prev_lat, prev_lon, lat, lon)
            total_proxy_m += segment_m
            prev_lat, prev_lon = lat, lon
            stop_rows.append(
                {
                    "route_id": route_id,
                    "sequence": sequence,
                    "source_id": candidate["source_id"],
                    "source_record_id": candidate["source_record_id"],
                    "operator_review_priority_score": candidate["operator_review_priority_score"],
                    "primary_candidate_asset_id": candidate["primary_candidate_asset_id"],
                    "primary_candidate_bbl": candidate["primary_candidate_bbl"],
                    "nearest_resource_id": candidate["nearest_resource_id"],
                    "segment_straight_line_proxy_m": round(segment_m, 3),
                    "event_latitude": lat,
                    "event_longitude": lon,
                    "status": "review_stop_only",
                    "semantic_guard": "not_emergency_dispatch_stop",
                }
            )
        route_rows.append(
            {
                "route_id": route_id,
                "entity_type": "operator_review_route_plan",
                "route_group_borough": group["route_group_borough"],
                "anchor_resource_id": group["nearest_resource_id"],
                "anchor_resource_label": first.get("resource_label"),
                "anchor_resource_address": first.get("resource_address_text"),
                "candidate_stop_count": int(len(route_candidates)),
                "max_priority_score": float(route_candidates["operator_review_priority_score"].max()),
                "mean_priority_score": round(float(route_candidates["operator_review_priority_score"].mean()), 3),
                "straight_line_review_proxy_m": round(total_proxy_m, 3),
                "planning_method": "deterministic_score_ordered_review_itinerary",
                "route_plan_status": "operator_review_plan_only",
                "optimization_backend": "not_called",
                "semantic_guard": "not_dispatch_not_navigable_route_not_emergency_recommendation",
            }
        )
    routes = pd.DataFrame(route_rows)
    stops = pd.DataFrame(stop_rows)
    report = {
        "status": "PASS" if not routes.empty and not stops.empty else "FAIL",
        "routes_emitted": int(len(routes)),
        "route_stops_emitted": int(len(stops)),
        "candidate_pool_considered": int(len(eligible)),
        "max_routes": max_routes,
        "stops_per_route": stops_per_route,
        "planning_method": "deterministic score-ordered review itinerary anchored on nearest firehouse context",
        "optimization_backend": "not_called",
        "semantic_guard": "operator review routing only; no emergency dispatch optimization or navigable routes",
    }
    return routes, stops, report


def build_review_edges(route_stops: pd.DataFrame) -> pd.DataFrame:
    if route_stops.empty:
        return pd.DataFrame()
    rows = []
    for record in route_stops.to_dict("records"):
        rows.append(
            {
                "canonical_id": f"edge:us-nyc:flow3:d4:{safe_id(record['route_id'])}:stop:{record['sequence']}:{safe_id(record['source_id'])}",
                "entity_type": "review_plan_edge",
                "source_id": record["route_id"],
                "target_id": record["source_id"],
                "relation": "includes_operator_review_candidate",
                "sequence": record["sequence"],
                "status": "review_plan_only",
                "semantic_guard": "not_dispatch_not_emergency_recommendation",
            }
        )
    return pd.DataFrame(rows)


def make_evidence_bundle(query_type: str, answer_status: str, facts: list[dict[str, Any]], counts: dict[str, Any], entities: list[dict[str, Any]], edges: list[dict[str, Any]], limitations: list[str], source_lineage: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tool": "citybrain_flow3_nyc_d4_query",
        "query_type": query_type,
        "answer_status": answer_status,
        "facts": facts,
        "counts": counts,
        "entities": entities,
        "edges": edges,
        "paths": [],
        "limitations": limitations,
        "source_lineage": source_lineage,
        "grounding_policy": {
            "model_may_narrate": True,
            "model_may_compute_counts": False,
            "model_may_add_facts": False,
        },
    }


def make_briefing(title: str, facts: list[str], limitations: list[str]) -> str:
    lines = [f"# {title}", ""]
    lines.extend(NO_OVERCLAIM_LINES)
    lines.append("")
    lines.append("This briefing is generated from F3-NYC-D4 deterministic evidence only.")
    lines.append("")
    lines.append("## Facts")
    lines.extend(f"- {fact}" for fact in facts)
    lines.append("")
    lines.append("## Limitations")
    lines.extend(f"- {limitation}" for limitation in limitations)
    lines.append("")
    return "\n".join(lines)


def build_query_smoke(candidates: pd.DataFrame, routes: pd.DataFrame, stops: pd.DataFrame) -> dict[str, Any]:
    results = {
        "top_candidate_priority_profile": {
            "status": "answered" if not candidates.empty else "source_limited",
            "candidate": sample_records(candidates, 1),
        },
        "operator_review_route_plan": {
            "status": "answered" if not routes.empty else "source_limited",
            "route": sample_records(routes, 1),
            "stops": sample_records(stops[stops["route_id"] == routes.iloc[0]["route_id"]], 10) if not routes.empty else [],
        },
        "source_limitations": {
            "status": "answered",
            "limitations": NO_OVERCLAIM_LINES,
        },
    }
    return {"status": "PASS" if all(item["status"] in {"answered", "source_limited"} for item in results.values()) else "FAIL", "queries": results}


def private_data_scan(samples: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(samples, default=str)
    phone = re.search(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)", text) is not None
    return {
        "status": "FAIL" if phone else "PASS",
        "policy": "D4 emits event IDs, scores, candidate BBL/tax-lot IDs, public firehouse identifiers, and straight-line review proxy distances. No names, phone numbers, narratives, license fields, or patient-level details are emitted.",
        "unredacted_phone_pattern_found_in_samples": phone,
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    texts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json"} and path.name not in {"SHA256SUMS.json", "F3_NYC_D4_NO_OVERCLAIM_REPORT.json"}:
            texts.append((path.relative_to(output_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace").lower()))
    combined = "\n".join(text for _, text in texts)
    missing = [line for line in NO_OVERCLAIM_LINES if line.lower() not in combined]
    forbidden = []
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        for path, text in texts:
            if re.search(pattern, text):
                forbidden.append({"path": path, "pattern": pattern})
    return {
        "status": "PASS" if not missing and not forbidden else "FAIL",
        "required_boundary_lines": NO_OVERCLAIM_LINES,
        "missing_boundary_lines": missing,
        "forbidden_positive_claims_found": forbidden,
    }


def gate_report(
    d3_ok: bool,
    candidates: pd.DataFrame,
    routes: pd.DataFrame,
    stops: pd.DataFrame,
    evidence_count: int,
    query_smoke: dict[str, Any],
    privacy: dict[str, Any],
    overclaim: dict[str, Any],
    no_mutation: dict[str, Any],
) -> dict[str, str]:
    return {
        "F3-NYC-D4-PRECOND": "PASS" if d3_ok else "FAIL",
        "F3-NYC-D4-CANDIDATE-INPUTS": "PASS" if not candidates.empty else "FAIL",
        "F3-NYC-D4-PRIORITIZATION": "PASS" if not candidates.empty and candidates["operator_review_priority_score"].notna().all() else "FAIL",
        "F3-NYC-D4-OPERATOR-REVIEW-ROUTE-PLAN": "PASS" if not routes.empty and not stops.empty and set(routes["route_plan_status"]) == {"operator_review_plan_only"} else "FAIL",
        "F3-NYC-D4-NO-EMERGENCY-OPTIMIZATION": "PASS" if not routes.empty and set(routes["optimization_backend"]) == {"not_called"} else "FAIL",
        "F3-NYC-D4-EVIDENCE-BUNDLES": "PASS" if evidence_count >= 3 else "FAIL",
        "F3-NYC-D4-QUERY-SMOKE": query_smoke.get("status", "FAIL"),
        "F3-NYC-D4-PRIVATE-DATA": privacy.get("status", "FAIL"),
        "F3-NYC-D4-NO-OVERCLAIM": overclaim.get("status", "FAIL"),
        "F3-NYC-D4-NO-MUTATION": no_mutation.get("status", "FAIL"),
    }


def run_f3_nyc_d4_gate(
    project_root: str,
    d3_dir: str,
    output_dir: str,
    d2_dir: str | None = None,
    max_candidates: int = 250,
    max_routes: int = 25,
    stops_per_route: int = 10,
) -> dict:
    project = Path(project_root).resolve()
    d3_path = Path(d3_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    d3p = d3_paths(d3_path)
    d2p = d2_paths_from_d3(d3_path, d2_dir)
    watched_inputs = [d3_path, d2p["mvc_crashes"], d2p["firehouses"]]
    before = input_snapshot(watched_inputs)

    d3_harness = read_json(d3p["harness"], {})
    d3_ok = d3_harness.get("status") in {"PASS", "PASS_WITH_LOCATION_CONFIDENCE_TIERS"}

    asset_edges = pd.read_parquet(d3p["asset_edges"])
    response_edges = pd.read_parquet(d3p["response_edges"])
    asset_nodes = pd.read_parquet(d3p["asset_candidates"])
    tiers = pd.read_parquet(d3p["location_tiers"])
    mvc_events = pd.read_parquet(d2p["mvc_crashes"])
    firehouses = pd.read_parquet(d2p["firehouses"])

    candidates_all = build_prioritized_candidates(asset_edges, response_edges, tiers, mvc_events, asset_nodes)
    candidates = candidates_all.head(max_candidates).copy()
    routes, route_stops, route_report = build_review_routes(candidates_all, firehouses, max_candidates, max_routes, stops_per_route)
    review_edges = build_review_edges(route_stops)
    query_smoke = build_query_smoke(candidates, routes, route_stops)

    write_parquet(output_path / "canonical" / "f3_nyc_d4_prioritized_incident_candidates.parquet", candidates)
    write_parquet(output_path / "canonical" / "f3_nyc_d4_operator_review_routes.parquet", routes)
    write_parquet(output_path / "canonical" / "f3_nyc_d4_route_stops.parquet", route_stops)
    write_parquet(output_path / "canonical" / "f3_nyc_d4_review_plan_edges.parquet", review_edges)
    write_json(output_path / "canonical" / "f3_nyc_d4_prioritized_incident_candidates_sample.json", sample_records(candidates, 25))
    write_json(output_path / "canonical" / "f3_nyc_d4_operator_review_routes_sample.json", sample_records(routes, 25))
    write_json(output_path / "canonical" / "f3_nyc_d4_route_stops_sample.json", sample_records(route_stops, 25))

    source_lineage = [
        {"source": "F3-NYC-D3 candidate affected-asset edges", "path": str(d3p["asset_edges"])},
        {"source": "F3-NYC-D3 response-resource context edges", "path": str(d3p["response_edges"])},
        {"source": "F3-NYC-D3 location tiers", "path": str(d3p["location_tiers"])},
        {"source": "F3-NYC-D2 MVC crash canonical events", "path": str(d2p["mvc_crashes"])},
        {"source": "F3-NYC-D2 firehouse resources", "path": str(d2p["firehouses"])},
    ]
    limitations = NO_OVERCLAIM_LINES + [
        "Priority score ranks records for operator review, not incident severity or emergency urgency.",
        "Route plan order is deterministic score order with straight-line proxy distances; it is not a street network route.",
        "D4 uses the bounded D2/D3 working set, not full-source citywide Flow 3 materialization.",
    ]
    priority_summary = {
        "status": "PASS" if not candidates.empty else "FAIL",
        "candidate_pool_rows": int(len(candidates_all)),
        "prioritized_rows_emitted": int(len(candidates)),
        "score_min": float(candidates["operator_review_priority_score"].min()) if not candidates.empty else None,
        "score_median": float(candidates["operator_review_priority_score"].median()) if not candidates.empty else None,
        "score_max": float(candidates["operator_review_priority_score"].max()) if not candidates.empty else None,
        "score_model": {
            "location_component": 0.35,
            "asset_proximity_component": 0.25,
            "resource_proximity_component": 0.20,
            "asset_context_component": 0.10,
            "evidence_completeness_component": 0.10,
        },
        "semantic_guard": "operator review score only, not emergency response recommendation",
    }
    cuopt_pattern = {
        "status": "PASS",
        "cuopt_backend_called": False,
        "pattern_reused": "A6-style operator-safe review routing artifact structure",
        "reason": "D4 is a situational assessment review plan. It must not claim emergency dispatch optimization.",
        "optimization_backend": "not_called",
    }

    priority_bundle = make_evidence_bundle(
        "candidate_prioritization",
        "answered" if not candidates.empty else "source_limited",
        [
            {"fact": "D4 emitted operator review candidate scores.", "value": int(len(candidates))},
            {"fact": "The score is not an emergency response recommendation.", "value": True},
        ],
        priority_summary,
        sample_records(candidates, 5),
        [],
        limitations,
        source_lineage,
    )
    route_bundle = make_evidence_bundle(
        "operator_review_route_plan",
        "answered" if not routes.empty else "source_limited",
        [
            {"fact": "D4 emitted operator review itinerary plans.", "value": int(len(routes))},
            {"fact": "Route distances are straight-line context proxies, not navigable routes.", "value": True},
        ],
        route_report,
        sample_records(routes, 5),
        sample_records(review_edges, 5),
        limitations,
        source_lineage,
    )
    limitation_bundle = make_evidence_bundle(
        "d4_source_limitations",
        "answered",
        [{"fact": "D4 remains bounded to D2/D3 working sets and candidate-only links.", "value": True}],
        {"limitations_count": len(limitations)},
        [],
        [],
        limitations,
        source_lineage,
    )
    write_json(output_path / "evidence" / "evidence_bundle_candidate_prioritization.json", priority_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_operator_review_route_plan.json", route_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_source_limitations.json", limitation_bundle)
    write_text(
        output_path / "evidence" / "deterministic_briefing_candidate_prioritization.md",
        make_briefing(
            "F3-NYC-D4 Candidate Prioritization",
            [
                f"Candidate pool rows: {len(candidates_all)}.",
                f"Prioritized rows emitted: {len(candidates)}.",
                f"Top review score: {priority_summary['score_max']}.",
            ],
            limitations,
        ),
    )
    write_text(
        output_path / "evidence" / "deterministic_briefing_operator_review_route_plan.md",
        make_briefing(
            "F3-NYC-D4 Operator Review Route Plan",
            [
                f"Review routes emitted: {len(routes)}.",
                f"Review stops emitted: {len(route_stops)}.",
                "Routes are review itineraries with straight-line context proxies.",
            ],
            limitations,
        ),
    )

    write_json(output_path / "F3_NYC_D4_INPUT_INVENTORY.json", {"project_root": str(project), "d3_dir": str(d3_path), "d2_dir": str(d2p["d2_dir"]), "inputs": {**{k: str(v) for k, v in d3p.items()}, **{k: str(v) for k, v in d2p.items()}}})
    write_json(output_path / "F3_NYC_D4_PRIORITY_MODEL_REPORT.json", priority_summary)
    write_json(output_path / "F3_NYC_D4_CANDIDATE_PRIORITIZATION_REPORT.json", {"status": priority_summary["status"], "candidate_pool_rows": len(candidates_all), "prioritized_rows_emitted": len(candidates), "top_candidates": sample_records(candidates, 10)})
    write_json(output_path / "F3_NYC_D4_OPERATOR_REVIEW_ROUTE_PLAN_REPORT.json", route_report)
    write_json(output_path / "F3_NYC_D4_RESPONSE_RESOURCE_CONTEXT_REPORT.json", {"status": "PASS", "source_response_edges": int(len(response_edges)), "route_response_anchors": int(routes["anchor_resource_id"].nunique()) if not routes.empty else 0, "semantic_guard": "response resource context only, not dispatched-unit truth"})
    write_json(output_path / "F3_NYC_D4_CUOPT_PATTERN_REPORT.json", cuopt_pattern)
    write_json(output_path / "F3_NYC_D4_EVIDENCE_BUNDLE_REPORT.json", {"status": "PASS", "bundles": 3, "deterministic_only": True})
    write_json(output_path / "F3_NYC_D4_QUERY_SMOKE_REPORT.json", query_smoke)
    write_json(output_path / "queries" / "sample_query_results.json", query_smoke)
    write_json(output_path / "reports" / "source_lineage.json", source_lineage)
    write_json(output_path / "reports" / "priority_score_summary.json", priority_summary)
    write_json(output_path / "reports" / "operator_review_route_summary.json", route_report)
    write_json(output_path / "reports" / "confidence_summary.json", {"location_tiers_in_candidate_pool": dict(Counter(candidates_all["location_confidence_tier"].tolist())), "candidate_score_quantiles": candidates["operator_review_priority_score"].quantile([0, 0.25, 0.5, 0.75, 1]).to_dict() if not candidates.empty else {}})
    write_json(output_path / "reports" / "source_limitations.json", {"limitations": limitations})
    write_json(output_path / "reports" / "recommended_d5_plan.json", {"recommended_next": "D5 can expose deterministic operator briefing/query surfaces over D4 evidence bundles. Do not add live NIM/Face claims until explicitly scoped.", "status_to_carry": "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION"})

    samples = {
        "candidates": sample_records(candidates, 10),
        "routes": sample_records(routes, 10),
        "stops": sample_records(route_stops, 10),
    }
    privacy = private_data_scan(samples)
    write_json(output_path / "F3_NYC_D4_PRIVATE_DATA_SCAN_REPORT.json", privacy)

    readme = "# F3-NYC-D4 Candidate Prioritization + Operator Review Routing Plan\n\nStatus: pending final harness write.\n\n" + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES) + "\n"
    write_text(output_path / "README.md", readme)
    write_text(
        output_path / "F3_NYC_D4_ADAPTER_HANDOVER.md",
        "# F3-NYC-D4 Adapter Handover\n\n"
        + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES)
        + "\n\nD5 should expose deterministic operator queries and grounded briefings over D4 review-plan evidence. Do not promote review routes to emergency dispatch or navigable routing.\n",
    )

    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D4_NO_OVERCLAIM_REPORT.json", overclaim)
    after = input_snapshot(watched_inputs)
    no_mutation = {"gate": "F3-NYC-D4-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "watched_input_count": len(watched_inputs)}
    gates = gate_report(d3_ok, candidates, routes, route_stops, 3, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION" if hard_pass else "FAIL"

    final_readme = f"""# F3-NYC-D4 Candidate Prioritization + Operator Review Routing Plan

Status: {status}

{chr(10).join(f"- {line}" for line in NO_OVERCLAIM_LINES)}

Candidate pool rows: {len(candidates_all)}
Prioritized candidate rows emitted: {len(candidates)}
Operator review routes emitted: {len(routes)}
Operator review stops emitted: {len(route_stops)}
cuOpt/backend optimization called: no
"""
    write_text(output_path / "README.md", final_readme)
    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D4_NO_OVERCLAIM_REPORT.json", overclaim)
    gates = gate_report(d3_ok, candidates, routes, route_stops, 3, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION" if hard_pass else "FAIL"

    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "candidate_pool_rows": int(len(candidates_all)),
        "prioritized_candidate_rows": int(len(candidates)),
        "operator_review_routes": int(len(routes)),
        "operator_review_stops": int(len(route_stops)),
        "review_plan_edges": int(len(review_edges)),
        "optimization_backend": "not_called",
        "cuopt_backend_called": False,
        "priority_summary": priority_summary,
        "route_report": route_report,
        "private_data_scan": privacy,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
    }
    write_json(output_path / "F3_NYC_D4_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D4-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D4_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D4_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D4 candidate prioritization + operator review routing")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d2-dir", default=None)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-candidates", type=int, default=250)
    parser.add_argument("--max-routes", type=int, default=25)
    parser.add_argument("--stops-per-route", type=int, default=10)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d4_gate(
        project_root=args.project_root,
        d3_dir=args.d3_dir,
        d2_dir=args.d2_dir,
        output_dir=args.output_dir,
        max_candidates=args.max_candidates,
        max_routes=args.max_routes,
        stops_per_route=args.stops_per_route,
    )
    print(f"F3-NYC-D4 Candidate Prioritization + Operator Review Routing Plan: {report['status']}")
    print(f"Candidate pool rows: {report['candidate_pool_rows']}")
    print(f"Prioritized candidate rows emitted: {report['prioritized_candidate_rows']}")
    print(f"Operator review routes emitted: {report['operator_review_routes']}")
    print(f"Operator review stops emitted: {report['operator_review_stops']}")
    print(f"cuOpt/backend optimization called: {'YES' if report['cuopt_backend_called'] else 'NO'}")
    print(f"Private-data scan: {report['private_data_scan']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
