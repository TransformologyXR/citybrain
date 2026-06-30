from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd


TASK_NAME = "F3-NYC-D3 Affected Asset and Response Context Linking"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"
DEFAULT_D2_DIR = "outputs/f3_nyc_d2_fdny_incident_response_slice_ingest"
DEFAULT_ASSET_DISTANCE_M = 30.0
DEFAULT_NEAREST_FIREHOUSES = 3

NO_OVERCLAIM_LINES = [
    "F3-NYC-D3 emits candidate affected-asset and response-resource context only.",
    "D3 does not certify affected buildings or affected assets.",
    "D3 does not geocode address-only events.",
    "D3 does not perform dispatch optimization or routing.",
    "D3 does not make emergency response recommendations.",
    "MapPLUTO parcel matches are tax-lot candidates, not BIN/building certification.",
    "Firehouse proximity is response-resource context, not dispatched-unit truth.",
    "FDNY address/borough events remain context-only until official coordinates or deterministic geometry are added.",
    "MVC Vehicles remain event context only, not primary crash events.",
    "No NIM/NeMo/LLM generated these facts.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"affected buildings? (?:are )?certified",
    r"affected assets? (?:are )?certified",
    r"certified affected (?:building|asset)",
    r"address-only events? (?:are )?geocoded",
    r"dispatch optimization (?:is )?(?:performed|complete|available)",
    r"routing (?:is )?(?:performed|optimized|available)",
    r"emergency response recommendations? (?:are )?(?:made|available)",
    r"mappluto parcel matches are bin",
    r"firehouse proximity is dispatched-unit truth",
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
    return {"gate": "F3-NYC-D3-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d3" not in resolved.name.lower():
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


def numeric(value: Any) -> float | None:
    text = cell(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def bbl_text(value: Any) -> str | None:
    number = numeric(value)
    if number is None:
        return None
    return str(int(round(number)))


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def sample_records(frame: pd.DataFrame, n: int) -> list[dict[str, Any]]:
    if frame.empty or "_empty" in frame.columns:
        return []
    sample = frame.head(n).where(pd.notna(frame.head(n)), None)
    return sample.to_dict("records")


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        if root.is_file():
            files = [root]
        else:
            files = [path for path in sorted(root.rglob("*")) if path.is_file()]
        for path in files:
            watched[str(path)] = {
                "exists": True,
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "sha256": sha256_file(path) if path.stat().st_size < 250_000_000 else None,
            }
    return watched


def find_mappluto(project_root: Path, asset_roots: list[str]) -> Path | None:
    candidates = [
        project_root / "nyc_mappluto_25v4_arc_shp" / "MapPLUTO.shp",
        project_root / "nyc_mappluto_25v4_arc_shp" / "MapPLUTO_UNCLIPPED.shp",
        project_root / "data_landing" / "nyc_flow3" / "MapPLUTO.shp",
        Path("C:/data/citybrain/nyc_mappluto_25v4_arc_shp/MapPLUTO.shp"),
        Path("/data/citybrain/nyc_mappluto_25v4_arc_shp/MapPLUTO.shp"),
    ]
    for root_text in asset_roots:
        root = Path(root_text)
        root = (project_root / root).resolve() if not root.is_absolute() else root.resolve()
        candidates.extend([root / "MapPLUTO.shp", root / "nyc_mappluto_25v4_arc_shp" / "MapPLUTO.shp"])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def d2_paths(d2_dir: Path) -> dict[str, Path]:
    canonical = d2_dir / "canonical"
    return {
        "harness": d2_dir / "F3_NYC_D2_HARNESS_REPORT.json",
        "mvc_crashes": canonical / "f3_nyc_d2_mvc_crash_events.parquet",
        "fdny_incidents": canonical / "f3_nyc_d2_incident_events.parquet",
        "firehouses": canonical / "f3_nyc_d2_firehouses.parquet",
        "mvc_vehicle_context": canonical / "f3_nyc_d2_mvc_vehicle_context.parquet",
    }


def classify_location_tiers(mvc: pd.DataFrame, fdny: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for family, frame in [("mvc_crash", mvc), ("fdny_incident", fdny)]:
        for record in frame.to_dict("records"):
            status = cell(record.get("location_status")) or "unavailable"
            if status == "latlon_exact":
                tier = "A"
                policy = "spatial_candidate_allowed"
                confidence = 0.85
                note = "Official source latitude/longitude may support geometry-backed candidate asset and response-resource context."
            elif status in {"borough_street_zip_candidate", "address_candidate"}:
                tier = "B"
                policy = "context_only_no_asset_edge_without_geocoding"
                confidence = 0.55
                note = "Address/street/ZIP was not geocoded in D3; no affected-asset edge is emitted."
            elif status == "borough_only":
                tier = "C"
                policy = "borough_context_only"
                confidence = 0.35
                note = "Borough-only evidence cannot support asset candidates."
            else:
                tier = "D"
                policy = "location_unavailable"
                confidence = 0.0
                note = "No location-backed context emitted."
            records.append(
                {
                    "event_id": record.get("canonical_id"),
                    "event_family": family,
                    "source_record_id": record.get("source_record_id") or record.get("collision_id"),
                    "event_type": record.get("event_type"),
                    "event_time": record.get("event_time"),
                    "borough": record.get("borough"),
                    "location_status": status,
                    "location_confidence_tier": tier,
                    "asset_link_policy": policy,
                    "confidence": confidence,
                    "note": note,
                }
            )
    return pd.DataFrame(records)


def load_mappluto_assets(path: Path) -> gpd.GeoDataFrame:
    cols = ["Borough", "BoroCode", "BBL", "Address", "LandUse", "BldgClass", "ZipCode", "Latitude", "Longitude", "Shape_Area", "geometry"]
    gdf = gpd.read_file(path, columns=cols)
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf["bbl_norm"] = gdf["BBL"].map(bbl_text)
    gdf = gdf[gdf["bbl_norm"].notna()].copy()
    gdf["asset_id"] = "asset:us-nyc:mappluto_tax_lot:" + gdf["bbl_norm"].astype(str)
    return gdf


def mvc_asset_candidate_links(mvc: pd.DataFrame, parcels: gpd.GeoDataFrame, max_events: int, distance_threshold_m: float) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    mvc_latlon = mvc[(mvc["latitude"].notna()) & (mvc["longitude"].notna())].copy().head(max_events)
    if mvc_latlon.empty:
        return pd.DataFrame(), pd.DataFrame(), {"status": "FAIL", "reason": "No MVC lat/lon events available."}
    mvc_points = gpd.GeoDataFrame(
        mvc_latlon,
        geometry=gpd.points_from_xy(mvc_latlon["longitude"].astype(float), mvc_latlon["latitude"].astype(float)),
        crs="EPSG:4326",
    ).to_crs(parcels.crs)
    distance_threshold_units = distance_threshold_m / 0.3048 if str(parcels.crs).upper().endswith("2263") else distance_threshold_m
    joined = gpd.sjoin_nearest(
        mvc_points,
        parcels[["asset_id", "bbl_norm", "Borough", "BoroCode", "Address", "LandUse", "BldgClass", "ZipCode", "Shape_Area", "geometry"]],
        how="left",
        max_distance=distance_threshold_units,
        distance_col="distance_units",
    )
    joined = joined[joined["asset_id"].notna()].copy()
    if joined.empty:
        return pd.DataFrame(), pd.DataFrame(), {"status": "FAIL", "reason": "No MapPLUTO tax-lot candidates within threshold."}
    joined["distance_m"] = joined["distance_units"].astype(float) * (0.3048 if str(parcels.crs).upper().endswith("2263") else 1.0)
    joined["spatial_relation"] = np.where(joined["distance_m"] <= 0.01, "point_within_tax_lot_polygon", "nearest_tax_lot_within_threshold")
    joined["confidence"] = np.where(joined["distance_m"] <= 0.01, 0.86, 0.72)
    edge_records = []
    for record in joined.to_dict("records"):
        edge_records.append(
            {
                "canonical_id": f"edge:us-nyc:flow3:d3:{safe_id(record.get('canonical_id'))}:candidate_asset:{record.get('bbl_norm')}",
                "entity_type": "context_edge",
                "source_id": record.get("canonical_id"),
                "target_id": record.get("asset_id"),
                "relation": "candidate_affected_asset",
                "evidence_class": "A",
                "source_dataset": record.get("source_dataset"),
                "source_record_id": record.get("source_record_id") or record.get("collision_id"),
                "source_location_status": record.get("location_status"),
                "target_asset_type": "mappluto_tax_lot",
                "target_bbl": record.get("bbl_norm"),
                "spatial_relation": record.get("spatial_relation"),
                "join_method": f"official_latlon_nearest_mappluto_tax_lot_within_{int(distance_threshold_m)}m",
                "distance_m": round(float(record.get("distance_m")), 3),
                "distance_threshold_m": distance_threshold_m,
                "confidence": float(record.get("confidence")),
                "status": "candidate_only",
                "overclaim_guard": "not_certified_affected_building_or_asset",
            }
        )
    edges = pd.DataFrame(edge_records).drop_duplicates(subset=["source_id", "target_id"])
    assets = (
        joined[["asset_id", "bbl_norm", "Borough", "BoroCode", "Address", "LandUse", "BldgClass", "ZipCode", "Shape_Area"]]
        .drop_duplicates(subset=["asset_id"])
        .rename(
            columns={
                "asset_id": "canonical_id",
                "bbl_norm": "bbl",
                "Borough": "borough",
                "BoroCode": "boro_code",
                "Address": "address_text",
                "LandUse": "land_use",
                "BldgClass": "building_class",
                "ZipCode": "zipcode",
                "Shape_Area": "shape_area",
            }
        )
    )
    assets.insert(1, "entity_type", "city_asset_candidate")
    assets.insert(2, "asset_type", "mappluto_tax_lot")
    assets["geometry_status"] = "official_mappluto_polygon_used_for_join_geometry_not_exported"
    assets["status"] = "candidate_asset_context_only"
    report = {
        "status": "PASS",
        "mvc_latlon_events_considered": int(len(mvc_latlon)),
        "candidate_edges_emitted": int(len(edges)),
        "unique_asset_candidates": int(len(assets)),
        "distance_threshold_m": distance_threshold_m,
        "median_distance_m": float(edges["distance_m"].median()) if not edges.empty else None,
        "within_polygon_edges": int((edges["spatial_relation"] == "point_within_tax_lot_polygon").sum()) if not edges.empty else 0,
        "nearest_within_threshold_edges": int((edges["spatial_relation"] == "nearest_tax_lot_within_threshold").sum()) if not edges.empty else 0,
    }
    return edges, assets, report


def response_resource_context_edges(events: pd.DataFrame, firehouses: pd.DataFrame, max_events: int, nearest_count: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    mvc_latlon = events[(events["latitude"].notna()) & (events["longitude"].notna())].copy().head(max_events)
    fh = firehouses[(firehouses["latitude"].notna()) & (firehouses["longitude"].notna())].copy()
    if mvc_latlon.empty or fh.empty:
        return pd.DataFrame(), {"status": "FAIL", "reason": "MVC lat/lon events or firehouse coordinates missing."}
    event_gdf = gpd.GeoDataFrame(
        mvc_latlon,
        geometry=gpd.points_from_xy(mvc_latlon["longitude"].astype(float), mvc_latlon["latitude"].astype(float)),
        crs="EPSG:4326",
    ).to_crs("EPSG:2263")
    fh_gdf = gpd.GeoDataFrame(
        fh,
        geometry=gpd.points_from_xy(fh["longitude"].astype(float), fh["latitude"].astype(float)),
        crs="EPSG:4326",
    ).to_crs("EPSG:2263")
    event_xy = np.column_stack([event_gdf.geometry.x.to_numpy(), event_gdf.geometry.y.to_numpy()])
    fh_xy = np.column_stack([fh_gdf.geometry.x.to_numpy(), fh_gdf.geometry.y.to_numpy()])
    edges: list[dict[str, Any]] = []
    for start in range(0, len(event_xy), 2000):
        stop = min(start + 2000, len(event_xy))
        diff = event_xy[start:stop, None, :] - fh_xy[None, :, :]
        distances_ft = np.sqrt((diff * diff).sum(axis=2))
        nearest_idx = np.argsort(distances_ft, axis=1)[:, :nearest_count]
        for local_idx, indices in enumerate(nearest_idx):
            event_record = event_gdf.iloc[start + local_idx]
            for rank, fh_idx in enumerate(indices, start=1):
                firehouse_record = fh_gdf.iloc[int(fh_idx)]
                distance_m = float(distances_ft[local_idx, int(fh_idx)] * 0.3048)
                edges.append(
                    {
                        "canonical_id": f"edge:us-nyc:flow3:d3:{safe_id(event_record.get('canonical_id'))}:response_resource:{rank}:{safe_id(firehouse_record.get('canonical_id'))}",
                        "entity_type": "context_edge",
                        "source_id": event_record.get("canonical_id"),
                        "target_id": firehouse_record.get("canonical_id"),
                        "relation": "nearest_response_resource_context",
                        "evidence_class": "A",
                        "source_record_id": event_record.get("source_record_id") or event_record.get("collision_id"),
                        "source_location_status": event_record.get("location_status"),
                        "target_resource_type": firehouse_record.get("resource_type"),
                        "target_status": firehouse_record.get("status"),
                        "rank": rank,
                        "join_method": "official_latlon_to_firehouse_distance",
                        "distance_m": round(distance_m, 3),
                        "confidence": 0.80 if rank == 1 else 0.76,
                        "status": "context_only",
                        "overclaim_guard": "not_route_not_dispatch_recommendation",
                    }
                )
    frame = pd.DataFrame(edges)
    report = {
        "status": "PASS" if not frame.empty else "FAIL",
        "events_with_response_context": int(frame["source_id"].nunique()) if not frame.empty else 0,
        "response_context_edges": int(len(frame)),
        "nearest_firehouses_per_event": nearest_count,
        "median_nearest_distance_m": float(frame[frame["rank"] == 1]["distance_m"].median()) if not frame.empty else None,
        "semantic_guard": "Firehouse proximity is context only. It is not a route, dispatch optimization, or emergency recommendation.",
    }
    return frame, report


def make_evidence_bundle(query_type: str, answer_status: str, facts: list[dict[str, Any]], counts: dict[str, Any], entities: list[dict[str, Any]], edges: list[dict[str, Any]], limitations: list[str], source_lineage: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tool": "citybrain_flow3_nyc_d3_query",
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
    lines.append("This briefing is generated from F3-NYC-D3 deterministic evidence only.")
    lines.append("")
    lines.append("## Facts")
    lines.extend(f"- {fact}" for fact in facts)
    lines.append("")
    lines.append("## Limitations")
    lines.extend(f"- {limitation}" for limitation in limitations)
    lines.append("")
    return "\n".join(lines)


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    texts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json"} and path.name not in {"SHA256SUMS.json", "F3_NYC_D3_NO_OVERCLAIM_REPORT.json"}:
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


def private_data_scan(samples: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(samples, default=str)
    phone = re.search(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)", text) is not None
    return {
        "status": "FAIL" if phone else "PASS",
        "policy": "D3 emits public event IDs, public street/borough context, MapPLUTO BBL/tax-lot identifiers, and public firehouse identifiers. No names, phone numbers, narratives, license fields, or patient-level details are emitted.",
        "unredacted_phone_pattern_found_in_samples": phone,
    }


def build_query_smoke(asset_edges: pd.DataFrame, assets: pd.DataFrame, response_edges: pd.DataFrame, tiers: pd.DataFrame) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if not asset_edges.empty:
        event_id = asset_edges.iloc[0]["source_id"]
        results["mvc_latlon_asset_context"] = {
            "status": "answered",
            "event_id": event_id,
            "asset_edges": sample_records(asset_edges[asset_edges["source_id"] == event_id], 5),
            "response_edges": sample_records(response_edges[response_edges["source_id"] == event_id], 5) if not response_edges.empty else [],
        }
    else:
        results["mvc_latlon_asset_context"] = {"status": "source_limited"}
    class_b = tiers[(tiers["event_family"] == "fdny_incident") & (tiers["location_confidence_tier"] == "B")].head(1)
    results["fdny_address_context_limitations"] = {
        "status": "answered" if not class_b.empty else "source_limited",
        "event": sample_records(class_b, 1),
        "asset_edge_policy": "no affected-asset edge without geocoding or official coordinates",
    }
    results["source_limitations"] = {
        "status": "answered",
        "limitations": NO_OVERCLAIM_LINES,
    }
    return {
        "status": "PASS" if all(value["status"] in {"answered", "source_limited"} for value in results.values()) else "FAIL",
        "queries": results,
    }


def gate_report(
    d2_ok: bool,
    mappluto_ok: bool,
    tiers: pd.DataFrame,
    asset_edges: pd.DataFrame,
    response_edges: pd.DataFrame,
    evidence_count: int,
    query_smoke: dict[str, Any],
    privacy: dict[str, Any],
    overclaim: dict[str, Any],
    no_mutation: dict[str, Any],
) -> dict[str, str]:
    tier_counts = Counter(tiers["location_confidence_tier"].tolist()) if not tiers.empty else Counter()
    return {
        "F3-NYC-D3-PRECOND": "PASS" if d2_ok else "FAIL",
        "F3-NYC-D3-ASSET-SOURCE": "PASS" if mappluto_ok else "FAIL",
        "F3-NYC-D3-LOCATION-CONFIDENCE-TIERS": "PASS" if tier_counts.get("A", 0) > 0 and tier_counts.get("B", 0) > 0 else "FAIL",
        "F3-NYC-D3-MVC-ASSET-CANDIDATE-LINKS": "PASS" if not asset_edges.empty and set(asset_edges["status"]) == {"candidate_only"} else "FAIL",
        "F3-NYC-D3-FDNY-CONTEXT-ONLY": "PASS" if tier_counts.get("B", 0) > 0 else "FAIL",
        "F3-NYC-D3-RESPONSE-RESOURCE-CONTEXT": "PASS" if not response_edges.empty and set(response_edges["status"]) == {"context_only"} else "FAIL",
        "F3-NYC-D3-EVIDENCE-BUNDLES": "PASS" if evidence_count >= 3 else "FAIL",
        "F3-NYC-D3-QUERY-SMOKE": query_smoke.get("status", "FAIL"),
        "F3-NYC-D3-PRIVATE-DATA": privacy.get("status", "FAIL"),
        "F3-NYC-D3-NO-OVERCLAIM": overclaim.get("status", "FAIL"),
        "F3-NYC-D3-NO-MUTATION": no_mutation.get("status", "FAIL"),
    }


def run_f3_nyc_d3_gate(
    project_root: str,
    d2_dir: str,
    asset_roots: list[str],
    output_dir: str,
    max_events: int = 50_000,
    asset_distance_threshold_m: float = DEFAULT_ASSET_DISTANCE_M,
    nearest_firehouses: int = DEFAULT_NEAREST_FIREHOUSES,
) -> dict:
    project = Path(project_root).resolve()
    d2_path = Path(d2_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    paths = d2_paths(d2_path)
    mappluto_path = find_mappluto(project, asset_roots)
    watched_inputs = [d2_path]
    if mappluto_path:
        watched_inputs.append(mappluto_path)
        for sibling_suffix in [".dbf", ".shx", ".prj", ".cpg"]:
            sibling = mappluto_path.with_suffix(sibling_suffix)
            if sibling.exists():
                watched_inputs.append(sibling)
    before = input_snapshot(watched_inputs)

    d2_harness = read_json(paths["harness"], {})
    d2_ok = d2_harness.get("status") in {"PASS", "PASS_WITH_BOUNDED_SAMPLE", "PASS_WITH_SOURCE_LIMITATION"}

    mvc = pd.read_parquet(paths["mvc_crashes"])
    fdny = pd.read_parquet(paths["fdny_incidents"])
    firehouses = pd.read_parquet(paths["firehouses"])
    tiers = classify_location_tiers(mvc.head(max_events), fdny.head(max_events))

    if not mappluto_path:
        parcels = gpd.GeoDataFrame()
        asset_edges = pd.DataFrame()
        asset_nodes = pd.DataFrame()
        asset_report = {"status": "FAIL", "reason": "MapPLUTO shapefile not found."}
    else:
        parcels = load_mappluto_assets(mappluto_path)
        asset_edges, asset_nodes, asset_report = mvc_asset_candidate_links(mvc, parcels, max_events, asset_distance_threshold_m)

    response_edges, response_report = response_resource_context_edges(mvc, firehouses, max_events, nearest_firehouses)
    query_smoke = build_query_smoke(asset_edges, asset_nodes, response_edges, tiers)

    write_parquet(output_path / "canonical" / "f3_nyc_d3_incident_asset_candidate_edges.parquet", asset_edges)
    write_parquet(output_path / "canonical" / "f3_nyc_d3_response_resource_context_edges.parquet", response_edges)
    write_parquet(output_path / "canonical" / "f3_nyc_d3_asset_candidates.parquet", asset_nodes)
    write_parquet(output_path / "canonical" / "f3_nyc_d3_location_tiers.parquet", tiers)
    write_json(output_path / "canonical" / "f3_nyc_d3_incident_asset_candidate_edges_sample.json", sample_records(asset_edges, 25))
    write_json(output_path / "canonical" / "f3_nyc_d3_response_resource_context_edges_sample.json", sample_records(response_edges, 25))
    write_json(output_path / "canonical" / "f3_nyc_d3_asset_candidates_sample.json", sample_records(asset_nodes, 25))
    write_json(output_path / "queries" / "sample_query_results.json", query_smoke)

    source_lineage = [
        {"source": "F3-NYC-D2 MVC crash canonical events", "path": str(paths["mvc_crashes"])},
        {"source": "F3-NYC-D2 FDNY incident canonical events", "path": str(paths["fdny_incidents"])},
        {"source": "F3-NYC-D2 firehouse resources", "path": str(paths["firehouses"])},
        {"source": "MapPLUTO tax-lot polygons", "path": str(mappluto_path) if mappluto_path else None},
    ]
    limitations = NO_OVERCLAIM_LINES + [
        f"Class A parcel candidates use nearest MapPLUTO tax-lot polygons within {asset_distance_threshold_m:g} meters.",
        "Crash points often fall in the roadbed; nearest parcel candidates are not proof that a building was affected.",
        "FDNY address/street/ZIP records were not geocoded in D3.",
    ]
    mvc_bundle = make_evidence_bundle(
        "mvc_latlon_asset_context",
        "answered" if not asset_edges.empty else "source_limited",
        [
            {"fact": "MVC Class A events were linked to candidate MapPLUTO tax lots with an explicit distance threshold.", "value": int(asset_edges["source_id"].nunique()) if not asset_edges.empty else 0},
            {"fact": "Candidate affected-asset edges are not certified affected-building links.", "value": True},
        ],
        asset_report,
        sample_records(asset_nodes, 5),
        sample_records(asset_edges, 5),
        limitations,
        source_lineage,
    )
    fdny_bundle = make_evidence_bundle(
        "fdny_address_context_limitations",
        "answered",
        [
            {"fact": "FDNY events in D2 are address/borough candidates in this bounded sample.", "value": int((tiers["event_family"] == "fdny_incident").sum())},
            {"fact": "D3 emits no affected-asset edges for FDNY address-only rows.", "value": True},
        ],
        dict(Counter(tiers[tiers["event_family"] == "fdny_incident"]["location_confidence_tier"].tolist())),
        sample_records(tiers[tiers["event_family"] == "fdny_incident"], 5),
        [],
        limitations,
        source_lineage,
    )
    response_bundle = make_evidence_bundle(
        "response_resource_context",
        "answered" if not response_edges.empty else "source_limited",
        [
            {"fact": "Firehouse proximity edges are context only, not routing or dispatch recommendation.", "value": True},
            {"fact": "Nearest firehouses are computed from official event and firehouse coordinates where available.", "value": int(response_edges["source_id"].nunique()) if not response_edges.empty else 0},
        ],
        response_report,
        [],
        sample_records(response_edges, 5),
        limitations,
        source_lineage,
    )
    write_json(output_path / "evidence" / "evidence_bundle_mvc_latlon_asset_context.json", mvc_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_fdny_address_context_limitations.json", fdny_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_response_resource_context.json", response_bundle)
    write_text(
        output_path / "evidence" / "deterministic_briefing_mvc_asset_context.md",
        make_briefing(
            "F3-NYC-D3 MVC Asset Context",
            [
                f"MVC asset candidate edges emitted: {len(asset_edges)}.",
                f"Unique MapPLUTO tax-lot candidates: {len(asset_nodes)}.",
                f"Distance threshold: {asset_distance_threshold_m:g} meters.",
            ],
            limitations,
        ),
    )
    write_text(
        output_path / "evidence" / "deterministic_briefing_fdny_context_limitations.md",
        make_briefing(
            "F3-NYC-D3 FDNY Context Limitations",
            [
                "FDNY D2 incident rows remain address/borough candidates.",
                "D3 did not geocode FDNY addresses.",
                "D3 emitted no affected-asset edges for FDNY address-only events.",
            ],
            limitations,
        ),
    )

    tier_counts = dict(Counter(tiers["location_confidence_tier"].tolist()))
    fdny_tier_counts = dict(Counter(tiers[tiers["event_family"] == "fdny_incident"]["location_confidence_tier"].tolist()))
    mvc_tier_counts = dict(Counter(tiers[tiers["event_family"] == "mvc_crash"]["location_confidence_tier"].tolist()))
    input_inventory = {
        "project_root": str(project),
        "d2_dir": str(d2_path),
        "asset_roots": asset_roots,
        "d2_status": d2_harness.get("status"),
        "mappluto_path": str(mappluto_path) if mappluto_path else None,
        "input_files": {key: str(path) for key, path in paths.items()},
    }
    write_json(output_path / "F3_NYC_D3_INPUT_INVENTORY.json", input_inventory)
    write_json(output_path / "F3_NYC_D3_ASSET_SOURCE_REPORT.json", {"status": "PASS" if mappluto_path and not parcels.empty else "FAIL", "mappluto_path": str(mappluto_path) if mappluto_path else None, "mappluto_rows": int(len(parcels)) if not parcels.empty else 0, "crs": str(parcels.crs) if not parcels.empty else None, "source_limitation": "MapPLUTO provides tax-lot polygons and BBLs; local clipped shapefile does not provide BIN/building footprint certification."})
    write_json(output_path / "F3_NYC_D3_LOCATION_CONFIDENCE_REPORT.json", {"status": "PASS", "tier_counts": tier_counts, "mvc_tier_counts": mvc_tier_counts, "fdny_tier_counts": fdny_tier_counts, "policy": {"A": "official lat/lon spatial candidates allowed", "B": "address/street/ZIP context only", "C": "borough context only", "D": "unavailable"}})
    write_json(output_path / "F3_NYC_D3_MVC_ASSET_LINK_REPORT.json", asset_report)
    write_json(output_path / "F3_NYC_D3_FDNY_CONTEXT_REPORT.json", {"status": "PASS", "fdny_tier_counts": fdny_tier_counts, "asset_edges_for_fdny": 0, "policy": "FDNY address/borough events remain context-only until official coordinates or deterministic geometry are added."})
    write_json(output_path / "F3_NYC_D3_RESPONSE_CONTEXT_REPORT.json", response_report)
    write_json(output_path / "F3_NYC_D3_EVIDENCE_BUNDLE_REPORT.json", {"status": "PASS", "bundles": 3, "deterministic_only": True})
    write_json(output_path / "F3_NYC_D3_QUERY_SMOKE_REPORT.json", query_smoke)
    write_json(output_path / "reports" / "source_lineage.json", source_lineage)
    write_json(output_path / "reports" / "location_tier_counts.json", {"all": tier_counts, "mvc": mvc_tier_counts, "fdny": fdny_tier_counts})
    write_json(output_path / "reports" / "mvc_asset_link_counts.json", asset_report)
    write_json(output_path / "reports" / "response_context_counts.json", response_report)
    write_json(output_path / "reports" / "source_limitations.json", {"limitations": limitations})
    write_json(output_path / "reports" / "recommended_d4_plan.json", {"recommended_next": "Flow 3 D4 should add route/optimization only after D3 candidate context is accepted and routing sources are explicit.", "do_not_promote": ["candidate_affected_asset", "nearest_response_resource_context"]})

    samples = {
        "asset_edges": sample_records(asset_edges, 10),
        "response_edges": sample_records(response_edges, 10),
        "asset_nodes": sample_records(asset_nodes, 10),
        "tiers": sample_records(tiers, 10),
    }
    privacy = private_data_scan(samples)
    write_json(output_path / "F3_NYC_D3_PRIVATE_DATA_SCAN_REPORT.json", privacy)

    readme = "# F3-NYC-D3 Affected Asset and Response Context Linking\n\nStatus: pending final harness write.\n\n" + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES) + "\n"
    write_text(output_path / "README.md", readme)
    write_text(
        output_path / "F3_NYC_D3_ADAPTER_HANDOVER.md",
        "# F3-NYC-D3 Adapter Handover\n\n"
        + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES)
        + "\n\nD4 may consider routing only as a separate task. D3 candidate edges must not be promoted to certified affected-building links without official coordinates or deterministic building geometry.\n",
    )

    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D3_NO_OVERCLAIM_REPORT.json", overclaim)
    after = input_snapshot(watched_inputs)
    no_mutation = {"gate": "F3-NYC-D3-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "watched_input_count": len(watched_inputs)}
    gates = gate_report(d2_ok, bool(mappluto_path and not parcels.empty), tiers, asset_edges, response_edges, 3, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_LOCATION_CONFIDENCE_TIERS" if hard_pass else "FAIL"

    final_readme = f"""# F3-NYC-D3 Affected Asset and Response Context Linking

Status: {status}

{chr(10).join(f"- {line}" for line in NO_OVERCLAIM_LINES)}

Class A MVC lat/lon events considered: {asset_report.get('mvc_latlon_events_considered', 0)}
Candidate affected-asset edges emitted: {len(asset_edges)}
Unique MapPLUTO tax-lot candidates: {len(asset_nodes)}
Response-resource context edges emitted: {len(response_edges)}
FDNY affected-asset edges emitted: 0
Location tiers: {tier_counts}
"""
    write_text(output_path / "README.md", final_readme)
    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D3_NO_OVERCLAIM_REPORT.json", overclaim)
    gates = gate_report(d2_ok, bool(mappluto_path and not parcels.empty), tiers, asset_edges, response_edges, 3, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_LOCATION_CONFIDENCE_TIERS" if hard_pass else "FAIL"

    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "location_tier_counts": tier_counts,
        "mvc_tier_counts": mvc_tier_counts,
        "fdny_tier_counts": fdny_tier_counts,
        "asset_candidate_edges": int(len(asset_edges)),
        "asset_candidates": int(len(asset_nodes)),
        "response_context_edges": int(len(response_edges)),
        "fdny_asset_edges": 0,
        "asset_distance_threshold_m": asset_distance_threshold_m,
        "nearest_firehouses_per_event": nearest_firehouses,
        "asset_report": asset_report,
        "response_report": response_report,
        "private_data_scan": privacy,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
    }
    write_json(output_path / "F3_NYC_D3_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D3-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D3_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D3_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D3 affected asset and response context linking")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d2-dir", default=DEFAULT_D2_DIR)
    parser.add_argument("--asset-root", action="append", dest="asset_roots", default=[])
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-events", type=int, default=50_000)
    parser.add_argument("--asset-distance-threshold-m", type=float, default=DEFAULT_ASSET_DISTANCE_M)
    parser.add_argument("--nearest-firehouses", type=int, default=DEFAULT_NEAREST_FIREHOUSES)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d3_gate(
        project_root=args.project_root,
        d2_dir=args.d2_dir,
        asset_roots=args.asset_roots,
        output_dir=args.output_dir,
        max_events=args.max_events,
        asset_distance_threshold_m=args.asset_distance_threshold_m,
        nearest_firehouses=args.nearest_firehouses,
    )
    print(f"F3-NYC-D3 Affected Asset and Response Context Linking: {report['status']}")
    print(f"Location tiers: {report['location_tier_counts']}")
    print(f"MVC Class A asset candidate edges: {report['asset_candidate_edges']}")
    print(f"Unique asset candidates: {report['asset_candidates']}")
    print(f"Response-resource context edges: {report['response_context_edges']}")
    print(f"FDNY affected-asset edges: {report['fdny_asset_edges']}")
    print(f"Private-data scan: {report['private_data_scan']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_LOCATION_CONFIDENCE_TIERS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
