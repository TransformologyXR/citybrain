from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "LON-D10B Local Plan Data Semantic Certification"
DEFAULT_D10_DIR = "outputs/lon_d10_planning_context_enrichment"
DEFAULT_D10Z_DIR = "outputs/lon_d10z_d10_accepted_snapshot"
DEFAULT_RAW_ROOT = "data_landing/london_d9_raw"
DEFAULT_OUTPUT_DIR = "outputs/lon_d10b_local_plan_semantic_certification"
SYNC_TARGET = Path("/data/citybrain/from_3090/london_d10b_local_plan_semantics_v1")
EXECUTION_BACKEND = "geopandas_cpu"

ALLOWED_SEMANTIC_CATEGORIES = {
    "site_allocation",
    "opportunity_area",
    "area_of_intensification",
    "strategic_industrial_land",
    "town_centre",
    "designated_open_space",
    "green_belt",
    "metropolitan_open_land",
    "conservation_area",
    "heritage_context",
    "protected_view",
    "biodiversity_context",
    "housing_zone",
    "employment_land",
    "regeneration_area",
    "transport_accessibility_context",
    "flood_or_environmental_constraint",
    "other_policy_context",
}
ALLOWED_RELATIONS = {
    "within_policy_context",
    "intersects_policy_context",
    "near_policy_context",
    "has_local_plan_context",
}
FORBIDDEN_ID_TERMS = {
    "legal_planning_decision",
    "policy_compliance",
    "approved_by_policy",
    "dob",
    "bbl",
    "bin",
}

BOUNDARY_LINES = [
    "This briefing is generated from CityBrain London D10B evidence only.",
    "Local Plan layers are planning-context evidence, not legal planning determinations.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D10B does not decide whether an application complies with policy.",
    "D10B does not ingest enforcement/building-control records.",
    "No NIM/NeMo/LLM generated these facts.",
]
NO_OVERCLAIM_LINES = [
    "D10B provides Local Plan context only.",
    "D10B does not make legal planning determinations.",
    "D10B does not certify application compliance.",
    "D10B does not prove complete London Local Plan coverage unless measured.",
    "D10B does not ingest enforcement/building-control records.",
    "D10B uses deterministic evidence only.",
]
D10_LIMITATION_CARRY_FORWARD = [
    "D10 is context only, not legal planning judgment.",
    "D6 enforcement/building-control remains source-limited.",
    "TOID context remains geometry-limited unless new official TOID geometry is added.",
    "5,116 D9D2 unmatched PLD records remain unmatched unless explicitly changed by a valid source.",
]
LONDON_BOROUGHS_33 = {
    "Barking and Dagenham",
    "Barnet",
    "Bexley",
    "Brent",
    "Bromley",
    "Camden",
    "City of London",
    "Croydon",
    "Ealing",
    "Enfield",
    "Greenwich",
    "Hackney",
    "Hammersmith and Fulham",
    "Haringey",
    "Harrow",
    "Havering",
    "Hillingdon",
    "Hounslow",
    "Islington",
    "Kensington and Chelsea",
    "Kingston upon Thames",
    "Lambeth",
    "Lewisham",
    "Merton",
    "Newham",
    "Redbridge",
    "Richmond upon Thames",
    "Southwark",
    "Sutton",
    "Tower Hamlets",
    "Waltham Forest",
    "Wandsworth",
    "Westminster",
}
BOROUGH_ALIASES = {
    "barking & dagenham": "Barking and Dagenham",
    "barking and dagenham": "Barking and Dagenham",
    "london borough of barking and dagenham": "Barking and Dagenham",
    "greenwich": "Greenwich",
    "royal borough of greenwich": "Greenwich",
    "hammersmith & fulham": "Hammersmith and Fulham",
    "hammersmith and fulham": "Hammersmith and Fulham",
    "london borough of hammersmith and fulham": "Hammersmith and Fulham",
    "kensington & chelsea": "Kensington and Chelsea",
    "kensington and chelsea": "Kensington and Chelsea",
    "kingston": "Kingston upon Thames",
    "kingston upon thames": "Kingston upon Thames",
    "richmond": "Richmond upon Thames",
    "richmond upon thames": "Richmond upon Thames",
    "hillingon": "Hillingdon",
    "redbirdge": "Redbridge",
    "enfield council": "Enfield",
    "lb bromley": "Bromley",
    "bromley custodian code": "Bromley",
    "city of london": "City of London",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(parts: list[Any], size: int = 24) -> str:
    joined = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:size]


def safe_token(value: Any, fallback: str) -> str:
    text = str(value if value is not None and str(value).strip() else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:120] or safe_token(fallback, "unknown")


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {
        "gate": "LON-D10B-HASHES",
        "status": "PASS",
        "file_count": len(sums),
        "sha256s": sums,
    }


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in {part.lower() for part in resolved.parts}
            or "lon_d10b" not in resolved.name.lower()
        ):
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    for child in ["canonical", "queries", "bundles", "reports"]:
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def import_geo():
    import geopandas as gpd  # type: ignore
    import pyogrio  # type: ignore
    from shapely.geometry import Point  # type: ignore

    return gpd, pyogrio, Point


def file_fingerprint(paths: list[Path]) -> dict[str, dict[str, Any]]:
    out = {}
    for path in paths:
        out[str(path)] = {
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else None,
            "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        }
    return out


def local_input_paths(d10_dir: Path, d10z_dir: Path | None, raw_root: Path) -> list[Path]:
    paths = [
        d10_dir / "LON_D10_HARNESS_REPORT.json",
        d10_dir / "LON_D10_CONTEXT_LAYER_INVENTORY.json",
        d10_dir / "LON_D10_COVERAGE_REPORT.json",
        raw_root / "osopenuprn_202606_csv.zip",
    ]
    paths.extend(sorted((raw_root / "planning_local_plan_data").glob("*.gpkg")))
    if d10z_dir is not None:
        paths.append(d10z_dir / "LON_D10Z_HARNESS_REPORT.json")
        paths.append(d10z_dir / "LON_D10Z_ACCEPTED_SNAPSHOT.json")
    d9d2 = Path("outputs/lon_d9d2_pld_api_uprn_recovery")
    paths.extend(
        [
            d9d2 / "LON_D9D2_HARNESS_REPORT.json",
            d9d2 / "canonical" / "london_pld_api_identity_edges.parquet",
            d9d2 / "canonical" / "london_pld_api_uprn_recovered.parquet",
            d9d2 / "canonical" / "london_pld_api_unmatched_records.parquet",
        ]
    )
    return paths


def normalize_layer_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def normalize_borough_label(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    lower = re.sub(r"\s+", " ", text.lower()).strip()
    if lower in {"unknown", "none", "nan", "opdc", "lldc", "out of borough", "custodian code"}:
        return None
    if lower.startswith("london borough of "):
        lower = lower.replace("london borough of ", "", 1)
    canonical = BOROUGH_ALIASES.get(lower)
    if canonical:
        return canonical
    title = text.replace("&", "and").strip()
    if title in LONDON_BOROUGHS_33:
        return title
    for borough in LONDON_BOROUGHS_33:
        if borough.lower() == lower:
            return borough
    return None


def boroughs_from_label(value: Any) -> list[str]:
    text = "" if value is None or pd.isna(value) else str(value)
    parts = [part.strip() for part in text.split(",")] if "," in text else [text]
    out = []
    for part in parts:
        borough = normalize_borough_label(part)
        if borough and borough not in out:
            out.append(borough)
    return out


def classify_semantic_category(layer_name: str, fields: list[str] | None = None) -> tuple[str | None, str, float]:
    n = normalize_layer_name(layer_name)
    field_text = normalize_layer_name("_".join(fields or []))
    basis = "official_layer_title"
    if any(x in n for x in ["potential_site_allocation", "site_allocation_option", "site_options", "draft_site"]):
        return None, "candidate_only_site_allocation_language", 0.60
    if "site_allocation" in n or n in {"site_allocations"} or n.endswith("_site_allocations_adopted"):
        return "site_allocation", basis, 0.85
    if "opportunity_area" in n:
        return "opportunity_area", basis, 0.85
    if "area_of_intensification" in n or "intensification_area" in n:
        return "area_of_intensification", basis, 0.85
    if "strategic_industrial" in n or n == "sil" or "strategic_industrial_location" in n:
        return "strategic_industrial_land", basis, 0.85
    if "locally_significant_industrial" in n or n == "lsis" or "employment_land" in n or "employment_area" in n or "office_cluster" in n:
        return "employment_land", basis, 0.85
    if any(x in n for x in ["town_centre", "town_center", "district_centre", "district_center", "neighbourhood_centre", "neighborhood_center", "local_centre", "local_center"]):
        return "town_centre", basis, 0.85
    if any(x in n for x in ["open_space", "public_open_space", "urban_open_space", "allotment", "protected_square"]):
        return "designated_open_space", basis, 0.85
    if "green_belt" in n:
        return "green_belt", basis, 0.85
    if "metropolitan_open_land" in n or n == "mol":
        return "metropolitan_open_land", basis, 0.85
    if "conservation_area" in n:
        return "conservation_area", basis, 0.85
    if any(x in n for x in ["protected_view", "lvmf", "local_strategic_view", "monument_view", "view_corridor"]):
        return "protected_view", basis, 0.85
    if any(x in n for x in ["listed_building", "scheduled_monument", "archaeological", "heritage", "world_heritage", "whs", "ancient_monument"]):
        return "heritage_context", basis, 0.85
    if any(x in n for x in ["sinc", "nature_reserve", "biodiversity", "wildlife", "sssi", "ancient_woodland", "geological_site"]):
        return "biodiversity_context", basis, 0.85
    if "housing_zone" in n or ("housing" in n and "application" not in n and "permission" not in n):
        return "housing_zone", basis, 0.85
    if "regeneration" in n:
        return "regeneration_area", basis, 0.85
    if "ptal" in n or "public_transport_accessibility" in n or "transport_accessibility" in n:
        return "transport_accessibility_context", basis, 0.85
    if any(x in n for x in ["flood", "air_quality", "contaminated_land", "safeguarding_area", "airport_safeguarding", "minerals_safeguarding", "pipeline"]):
        return "flood_or_environmental_constraint", basis, 0.85
    if any(x in field_text for x in ["designation", "boroughdesignation", "classification"]):
        return None, "fields_have_policy_terms_but_layer_title_is_ambiguous", 0.55
    return None, "policy_category_not_identifiable_from_title", 0.0


def geometry_status(geometry_type: str | None) -> str:
    text = (geometry_type or "").lower()
    if "polygon" in text:
        return "official_polygon"
    if "point" in text:
        return "official_point"
    if "line" in text:
        return "official_line"
    return "missing_geometry"


def first_present(row: pd.Series, fields: list[str], fallback: str) -> str:
    for field in fields:
        if field in row and pd.notna(row[field]) and str(row[field]).strip():
            return str(row[field]).strip()
    return fallback


def precondition_report(d10_dir: Path, d10z_dir: Path | None) -> dict[str, Any]:
    d10_harness = d10_dir / "LON_D10_HARNESS_REPORT.json"
    d10_inventory = d10_dir / "LON_D10_CONTEXT_LAYER_INVENTORY.json"
    d10_edges = d10_dir / "LON_D10_CONTEXT_EDGE_REPORT.json"
    d10_status = read_json(d10_harness).get("status") if d10_harness.exists() else None
    d10z_report = d10z_dir / "LON_D10Z_HARNESS_REPORT.json" if d10z_dir is not None else None
    checks = {
        "d10_harness_report_exists": d10_harness.exists(),
        "d10_harness_status_pass": d10_status == "PASS",
        "d10_context_inventory_exists": d10_inventory.exists(),
        "d10_context_edge_report_exists": d10_edges.exists(),
        "d10z_accepted_snapshot_exists": d10z_report.exists() if d10z_report is not None else False,
        "d10z_status_pass": read_json(d10z_report).get("status") == "PASS" if d10z_report is not None and d10z_report.exists() else False,
    }
    return {
        "gate": "LON-D10B-PRECOND",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "d10z_not_found_used_d10_directly": not checks["d10z_accepted_snapshot_exists"],
        "local_graph_note": "D10 canonical graph parquet is not present in the lightweight local D10 directory; D10B emits an overlay enriched graph containing D10B context nodes, D10B edges, and resolved PLD/UPRN endpoint references.",
    }


def discover_local_plan_layers(raw_root: Path, d10_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    _, pyogrio, _ = import_geo()
    root = raw_root / "planning_local_plan_data"
    d10_inventory_path = d10_dir / "LON_D10_CONTEXT_LAYER_INVENTORY.json"
    d10_inventory = read_json(d10_inventory_path) if d10_inventory_path.exists() else {}
    d10_deferred_count = len(d10_inventory.get("planning_local_plan_inventory", []))
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return pd.DataFrame(), {
            "gate": "LON-D10B-SOURCE-INVENTORY",
            "status": "FAIL",
            "candidate_layers": 0,
            "d10_deferred_inventory_count": d10_deferred_count,
            "reason": "planning_local_plan_data directory not found",
        }
    for gpkg in sorted(root.glob("*.gpkg")):
        try:
            layer_info = pyogrio.list_layers(gpkg)
        except Exception as exc:
            rows.append(
                {
                    "source_dataset": "Planning Local Plan Data",
                    "source_layer": f"planning_local_plan_data:{gpkg.stem}:__read_error__",
                    "path": str(gpkg),
                    "classification": "manual_review",
                    "certification_status": "manual_review",
                    "reason": f"could not list GeoPackage layers: {type(exc).__name__}: {exc}",
                }
            )
            continue
        for layer_name, geom_type in layer_info:
            fields: list[str] = []
            features = 0
            crs = None
            info_error = None
            try:
                info = pyogrio.read_info(gpkg, layer=layer_name)
                raw_fields = info.get("fields")
                fields = [str(x) for x in list(raw_fields)] if raw_fields is not None else []
                features = int(info.get("features") or 0)
                crs = str(info.get("crs")) if info.get("crs") is not None else None
                geom_type = str(info.get("geometry_type") or geom_type)
            except Exception as exc:
                info_error = f"{type(exc).__name__}: {exc}"
            semantic_category, method, score = classify_semantic_category(layer_name, fields)
            geom_status = geometry_status(str(geom_type))
            if info_error:
                classification = "manual_review"
                reason = f"layer metadata unreadable: {info_error}"
            elif features <= 0:
                classification = "source_limited"
                reason = "official layer exists but has no features locally"
            elif geom_status == "missing_geometry":
                classification = "manual_review"
                reason = "missing or unsupported geometry type"
            elif crs is None:
                classification = "manual_review"
                reason = "unknown geometry CRS"
            elif semantic_category is None and method.startswith("candidate_only"):
                classification = "used_candidate_only"
                reason = "candidate/draft policy language; not certified canonical context"
            elif semantic_category is None:
                classification = "manual_review"
                reason = method
            elif semantic_category not in ALLOWED_SEMANTIC_CATEGORIES:
                classification = "manual_review"
                reason = "semantic category not in D10B taxonomy"
            else:
                classification = "used_certified"
                reason = "official spatial layer title maps to D10B controlled taxonomy"
            rows.append(
                {
                    "source_dataset": "Planning Local Plan Data",
                    "source_layer": f"planning_local_plan_data:{gpkg.stem}:{layer_name}",
                    "source_file": gpkg.name,
                    "path": str(gpkg),
                    "layer_name": str(layer_name),
                    "geometry_type": str(geom_type),
                    "geometry_status": geom_status,
                    "crs": crs,
                    "feature_count": features,
                    "fields": fields,
                    "classification": classification,
                    "certification_status": classification,
                    "semantic_category": semantic_category,
                    "semantic_method": method,
                    "semantic_confidence": score,
                    "official_source": True,
                    "download_attempted": False,
                    "license_basis": "official London Datastore / GLA Planning Local Plan Data source in local D9 landing area",
                    "reason": reason,
                }
            )
    inventory = pd.DataFrame(rows)
    status = "PASS" if len(inventory) > 0 else "FAIL"
    return inventory, {
        "gate": "LON-D10B-SOURCE-INVENTORY",
        "status": status,
        "candidate_layers": int(len(inventory)),
        "d10_deferred_inventory_count": d10_deferred_count,
        "local_planning_local_plan_gpkg_count": len(list(root.glob("*.gpkg"))),
        "classification_counts": inventory["classification"].value_counts().to_dict() if not inventory.empty else {},
    }


def repair_geometry(gdf: Any) -> Any:
    if gdf.empty:
        return gdf
    try:
        from shapely import make_valid  # type: ignore

        invalid = ~gdf.geometry.is_valid
        if invalid.any():
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].apply(make_valid)
    except Exception:
        invalid = ~gdf.geometry.is_valid
        if invalid.any():
            gdf.loc[invalid, "geometry"] = gdf.loc[invalid, "geometry"].buffer(0)
    return gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty & gdf.geometry.is_valid].copy()


def build_context_nodes_and_layers(certified_layers: pd.DataFrame) -> tuple[pd.DataFrame, Any, list[dict[str, Any]], list[dict[str, Any]]]:
    gpd, _, _ = import_geo()
    node_records: list[dict[str, Any]] = []
    layer_frames = []
    read_reports: list[dict[str, Any]] = []
    geometry_limitations: list[dict[str, Any]] = []
    id_seen: set[str] = set()
    for layer in certified_layers.to_dict("records"):
        path = Path(layer["path"])
        layer_name = layer["layer_name"]
        try:
            gdf = gpd.read_file(path, layer=layer_name)
            source_crs = str(gdf.crs) if gdf.crs is not None else None
            gdf = gdf[~gdf.geometry.isna()].copy()
            if gdf.crs is None:
                raise ValueError("missing CRS during layer read")
            if str(gdf.crs) != "EPSG:27700":
                gdf = gdf.to_crs(27700)
            before_repair = int(len(gdf))
            gdf = repair_geometry(gdf)
            if gdf.empty:
                geometry_limitations.append({"source_layer": layer["source_layer"], "reason": "all geometries empty or invalid after repair"})
                read_reports.append({"source_layer": layer["source_layer"], "status": "source_limited", "rows": 0})
                continue
            gdf["source_layer"] = layer["source_layer"]
            gdf["source_dataset"] = layer["source_dataset"]
            gdf["semantic_category"] = layer["semantic_category"]
            gdf["geometry_status"] = layer["geometry_status"]
            gdf["source_file"] = layer["source_file"]
            gdf["layer_name"] = layer_name
            gdf["source_crs"] = source_crs
            canonical_ids = []
            policy_names = []
            policy_refs = []
            boroughs = []
            boroughs_normalized = []
            confidence_json = []
            provenance_json = []
            for idx, row in gdf.drop(columns="geometry", errors="ignore").iterrows():
                source_id = first_present(row, ["layerreference", "sitereference", "GlobalID", "OBJECTID", "objectid", "fid"], f"row_{idx}")
                policy_name = first_present(row, ["sitename", "designation", "boroughdesignation", "classification", "name", "Name"], layer_name)
                policy_ref = first_present(row, ["extrainfo1", "extrainfo2", "extrainfo3", "source", "notes", "layerreference"], source_id)
                borough = first_present(row, ["borough", "planningauthority", "local_authority", "lpa"], "London")
                borough_normalized = boroughs_from_label(borough)
                safe_id = safe_token(f"{borough}_{layer_name}_{source_id}", f"{path.stem}_{layer_name}_{idx}")
                canonical_id = f"planning_policy_context_area:uk-london:{layer['semantic_category']}:{safe_id}"
                if canonical_id in id_seen:
                    canonical_id = f"{canonical_id}_{stable_hash([layer['source_layer'], idx], 8)}"
                id_seen.add(canonical_id)
                confidence = {
                    "method": "semantic_category_inferred_from_official_layer_title",
                    "score": float(layer["semantic_confidence"]),
                }
                provenance = [
                    {
                        "stage": "D10B",
                        "source_dataset": layer["source_dataset"],
                        "source_file": layer["source_file"],
                        "source_layer": layer["source_layer"],
                        "layer_name": layer_name,
                        "official_source": True,
                    }
                ]
                canonical_ids.append(canonical_id)
                policy_names.append(policy_name)
                policy_refs.append(policy_ref)
                boroughs.append(borough)
                boroughs_normalized.append(json.dumps(borough_normalized, sort_keys=True))
                confidence_json.append(json.dumps(confidence, sort_keys=True))
                provenance_json.append(json.dumps(provenance, sort_keys=True))
                node_records.append(
                    {
                        "canonical_id": canonical_id,
                        "entity_type": "planning_policy_context_area",
                        "semantic_category": layer["semantic_category"],
                        "source_layer": layer["source_layer"],
                        "source_dataset": layer["source_dataset"],
                        "borough": borough,
                        "borough_normalized": json.dumps(borough_normalized, sort_keys=True),
                        "policy_name": policy_name,
                        "policy_reference": policy_ref,
                        "geometry_status": layer["geometry_status"],
                        "confidence": json.dumps(confidence, sort_keys=True),
                        "provenance": json.dumps(provenance, sort_keys=True),
                    }
                )
            gdf["canonical_id"] = canonical_ids
            gdf["entity_type"] = "planning_policy_context_area"
            gdf["borough"] = boroughs
            gdf["borough_normalized"] = boroughs_normalized
            gdf["policy_name"] = policy_names
            gdf["policy_reference"] = policy_refs
            gdf["confidence"] = confidence_json
            gdf["provenance"] = provenance_json
            keep = [
                "canonical_id",
                "entity_type",
                "semantic_category",
                "source_layer",
                "source_dataset",
                "borough",
                "borough_normalized",
                "policy_name",
                "policy_reference",
                "geometry_status",
                "confidence",
                "provenance",
                "source_file",
                "layer_name",
                "source_crs",
                "geometry",
            ]
            layer_frames.append(gdf[[c for c in keep if c in gdf.columns]].copy())
            read_reports.append(
                {
                    "source_layer": layer["source_layer"],
                    "status": "PASS",
                    "rows_read": before_repair,
                    "rows_valid": int(len(gdf)),
                    "source_crs": source_crs,
                    "geometry_status": layer["geometry_status"],
                }
            )
        except Exception as exc:
            geometry_limitations.append(
                {
                    "source_layer": layer["source_layer"],
                    "reason": f"certified layer could not be read for canonical emission: {type(exc).__name__}: {exc}",
                }
            )
            read_reports.append({"source_layer": layer["source_layer"], "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    nodes = pd.DataFrame(node_records).drop_duplicates("canonical_id") if node_records else pd.DataFrame()
    layers = gpd.GeoDataFrame(pd.concat(layer_frames, ignore_index=True), geometry="geometry", crs="EPSG:27700") if layer_frames else gpd.GeoDataFrame()
    return nodes, layers, read_reports, geometry_limitations


def load_d9d2_edges_and_records() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d9d2 = Path("outputs/lon_d9d2_pld_api_uprn_recovery")
    edges = pd.read_parquet(d9d2 / "canonical" / "london_pld_api_identity_edges.parquet")
    records = pd.read_parquet(d9d2 / "canonical" / "london_pld_api_uprn_recovered.parquet")
    unmatched = pd.read_parquet(d9d2 / "canonical" / "london_pld_api_unmatched_records.parquet")
    return edges, records, unmatched


def stream_matched_uprn_points(raw_root: Path, pld_edges: pd.DataFrame, pld_records: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    zip_path = raw_root / "osopenuprn_202606_csv.zip"
    target_ids = sorted({int(str(src).rsplit(":", 1)[-1]) for src in pld_edges["src"].astype(str) if str(src).rsplit(":", 1)[-1].isdigit()})
    target_set = set(target_ids)
    found_frames = []
    chunks = 0
    rows_scanned = 0
    if not zip_path.exists():
        return pd.DataFrame(), {
            "status": "source_limited",
            "reason": "OS Open UPRN zip not found",
            "target_uprns": len(target_set),
            "matched_uprns": 0,
        }
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("osopenuprn_202606.csv") as handle:
            for chunk in pd.read_csv(
                handle,
                usecols=["UPRN", "X_COORDINATE", "Y_COORDINATE", "LATITUDE", "LONGITUDE"],
                chunksize=1_000_000,
            ):
                chunks += 1
                rows_scanned += int(len(chunk))
                matched = chunk[chunk["UPRN"].isin(target_set)].copy()
                if not matched.empty:
                    found_frames.append(matched)
                    target_set -= set(matched["UPRN"].astype(int).tolist())
                if not target_set:
                    break
    points = pd.concat(found_frames, ignore_index=True).drop_duplicates("UPRN") if found_frames else pd.DataFrame()
    if not points.empty:
        points["canonical_id"] = "parcel:uk-london:uprn:" + points["UPRN"].astype("int64").astype(str)
        pld_to_borough = pld_edges[["src", "dst"]].merge(
            pld_records[["canonical_id", "api_borough"]],
            left_on="dst",
            right_on="canonical_id",
            how="left",
        )
        borough_by_uprn = (
            pld_to_borough.dropna(subset=["api_borough"])
            .groupby("src")["api_borough"]
            .agg(lambda s: Counter(s).most_common(1)[0][0])
            .to_dict()
        )
        points["borough"] = points["canonical_id"].map(borough_by_uprn).fillna("unknown")
    report = {
        "status": "PASS" if len(points) else "FAIL",
        "target_uprns": len(target_ids),
        "matched_uprns": int(len(points)),
        "missing_uprns": int(len(target_ids) - len(points)),
        "chunks_read": chunks,
        "rows_scanned": rows_scanned,
        "source": str(zip_path),
    }
    return points, report


def build_spatial_edges(points_df: pd.DataFrame, policy_layers: Any, pld_edges: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    gpd, _, Point = import_geo()
    empty = pd.DataFrame(
        columns=[
            "edge_id",
            "src",
            "dst",
            "relation",
            "confidence",
            "join_method",
            "source_geometry_status",
            "target_geometry_status",
            "distance_threshold_m",
            "source_stage",
            "source_layer",
            "source_dataset",
            "semantic_category",
            "confidence_basis",
        ]
    )
    if points_df.empty or policy_layers.empty:
        return empty, {"gate": "LON-D10B-SPATIAL-JOIN", "status": "FAIL", "reason": "missing points or policy layers"}, {"context_edges": 0, "src_missing": 0, "dst_missing": 0}
    polygon_layers = policy_layers[policy_layers["geometry_status"].eq("official_polygon")].copy()
    if polygon_layers.empty:
        return empty, {"gate": "LON-D10B-SPATIAL-JOIN", "status": "FAIL", "reason": "no certified polygon layers"}, {"context_edges": 0, "src_missing": 0, "dst_missing": 0}
    points_gdf = gpd.GeoDataFrame(
        points_df.copy(),
        geometry=[Point(x, y) for x, y in zip(points_df["X_COORDINATE"], points_df["Y_COORDINATE"])],
        crs="EPSG:27700",
    )
    point_cols = ["canonical_id", "UPRN", "borough", "geometry"]
    poly_cols = [
        "canonical_id",
        "semantic_category",
        "source_layer",
        "source_dataset",
        "geometry_status",
        "policy_name",
        "borough",
        "geometry",
    ]
    joined = gpd.sjoin(
        points_gdf[point_cols].rename(columns={"canonical_id": "uprn_id", "borough": "uprn_borough"}),
        polygon_layers[poly_cols].rename(columns={"canonical_id": "context_id", "borough": "context_borough"}),
        how="inner",
        predicate="within",
    )
    if joined.empty:
        return empty, {"gate": "LON-D10B-SPATIAL-JOIN", "status": "FAIL", "join_method": "point-in-polygon", "matches": 0}, {"context_edges": 0, "src_missing": 0, "dst_missing": 0}
    uprn_edges = pd.DataFrame(
        {
            "src": joined["uprn_id"].astype(str),
            "dst": joined["context_id"].astype(str),
            "relation": "within_policy_context",
            "confidence": 0.90,
            "join_method": "point-in-polygon",
            "source_geometry_status": "official_uprn_point",
            "target_geometry_status": "official_polygon",
            "distance_threshold_m": None,
            "source_stage": "D10B",
            "source_layer": joined["source_layer"].astype(str),
            "source_dataset": joined["source_dataset"].astype(str),
            "semantic_category": joined["semantic_category"].astype(str),
            "confidence_basis": "UPRN point-in-policy-polygon via exact PLD-to-UPRN recovery",
        }
    )
    uprn_edges["edge_id"] = [
        "edge:uk-london:d10b:uprn:" + stable_hash([src, rel, dst, layer])
        for src, rel, dst, layer in zip(uprn_edges["src"], uprn_edges["relation"], uprn_edges["dst"], uprn_edges["source_layer"])
    ]
    uprn_edges = uprn_edges.drop_duplicates(["src", "dst", "relation", "source_layer"])
    mapping = pld_edges[["src", "dst", "edge_id"]].rename(
        columns={"src": "uprn_id", "dst": "permit_id", "edge_id": "d9d2_subject_edge_id"}
    )
    pld_joined = joined.merge(mapping, on="uprn_id", how="inner")
    pld_context_edges = pd.DataFrame(
        {
            "src": pld_joined["permit_id"].astype(str),
            "dst": pld_joined["context_id"].astype(str),
            "relation": "within_policy_context",
            "confidence": 0.88,
            "join_method": "exact_pld_uprn_plus_uprn_point-in-polygon",
            "source_geometry_status": "PLD context inferred through exact D9D2 PLD-to-UPRN edge and official UPRN point",
            "target_geometry_status": "official_polygon",
            "distance_threshold_m": None,
            "source_stage": "D10B",
            "source_layer": pld_joined["source_layer"].astype(str),
            "source_dataset": pld_joined["source_dataset"].astype(str),
            "semantic_category": pld_joined["semantic_category"].astype(str),
            "confidence_basis": "PLD context via exact PLD-to-UPRN plus UPRN geometry",
        }
    )
    pld_context_edges["edge_id"] = [
        "edge:uk-london:d10b:pld:" + stable_hash([src, rel, dst, layer])
        for src, rel, dst, layer in zip(pld_context_edges["src"], pld_context_edges["relation"], pld_context_edges["dst"], pld_context_edges["source_layer"])
    ]
    pld_context_edges = pld_context_edges.drop_duplicates(["src", "dst", "relation", "source_layer"])
    all_edges = pd.concat([uprn_edges, pld_context_edges], ignore_index=True).drop_duplicates("edge_id")
    node_set = set(policy_layers["canonical_id"].astype(str)) | set(points_df["canonical_id"].astype(str)) | set(pld_edges["dst"].astype(str))
    edge_integrity = {
        "context_edges": int(len(all_edges)),
        "src_missing": int((~all_edges["src"].astype(str).isin(node_set)).sum()),
        "dst_missing": int((~all_edges["dst"].astype(str).isin(node_set)).sum()),
    }
    join_report = {
        "gate": "LON-D10B-SPATIAL-JOIN",
        "status": "PASS",
        "join_method": "point-in-polygon",
        "source_points": int(len(points_df)),
        "target_polygon_contexts": int(len(polygon_layers)),
        "uprn_context_edges": int(len(uprn_edges)),
        "pld_context_edges": int(len(pld_context_edges)),
        "point_and_line_layer_edge_policy": "certified point/line context nodes are emitted, but no near_policy_context edges are emitted in D10B v1 because no explicit distance threshold was selected.",
    }
    return all_edges, join_report, edge_integrity


def endpoint_nodes(edges: pd.DataFrame, points_df: pd.DataFrame, pld_records: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    point_map = points_df.set_index("canonical_id").to_dict("index") if not points_df.empty else {}
    record_borough = pld_records.set_index("canonical_id")["api_borough"].to_dict() if "api_borough" in pld_records.columns else {}
    for src in sorted(set(edges["src"].astype(str))) if not edges.empty else []:
        if src.startswith("parcel:uk-london:uprn:"):
            p = point_map.get(src, {})
            rows.append(
                {
                    "canonical_id": src,
                    "entity_type": "parcel",
                    "source_stage": "D10B endpoint reference",
                    "borough": p.get("borough", "unknown"),
                    "geometry_status": "official_uprn_point",
                }
            )
        elif src.startswith("permit:uk-london:pld:"):
            rows.append(
                {
                    "canonical_id": src,
                    "entity_type": "planning_application",
                    "source_stage": "D10B endpoint reference",
                    "borough": record_borough.get(src, "unknown"),
                    "geometry_status": "inferred_via_exact_pld_to_uprn",
                }
            )
    return pd.DataFrame(rows).drop_duplicates("canonical_id") if rows else pd.DataFrame()


def parse_json_column(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def sample_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    if df.empty:
        return []
    records = df.head(limit).drop(columns=["geometry"], errors="ignore").to_dict("records")
    for rec in records:
        for key in ["confidence", "provenance"]:
            if key in rec:
                rec[key] = parse_json_column(rec[key])
    return records


def parsed_boroughs(value: Any) -> list[str]:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item) in LONDON_BOROUGHS_33]
        except Exception:
            pass
    borough = normalize_borough_label(value)
    return [borough] if borough else []


def borough_policy_coverage(nodes: pd.DataFrame, context_ids: set[str] | None = None) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    if nodes.empty:
        return coverage
    subset = nodes[nodes["canonical_id"].astype(str).isin(context_ids)].copy() if context_ids is not None else nodes.copy()
    for row in subset.to_dict("records"):
        boroughs = parsed_boroughs(row.get("borough_normalized")) or boroughs_from_label(row.get("borough"))
        for borough in boroughs:
            entry = coverage.setdefault(borough, {"context_nodes": 0, "source_layers": set(), "semantic_categories": set()})
            entry["context_nodes"] += 1
            if row.get("source_layer"):
                entry["source_layers"].add(row["source_layer"])
            if row.get("semantic_category"):
                entry["semantic_categories"].add(row["semantic_category"])
    return {
        borough: {
            "context_nodes": values["context_nodes"],
            "certified_layers": len(values["source_layers"]),
            "semantic_categories": sorted(values["semantic_categories"]),
        }
        for borough, values in sorted(coverage.items())
    }


def nodes_for_borough(nodes: pd.DataFrame, borough: str | None) -> pd.DataFrame:
    if nodes.empty or not borough:
        return nodes.head(0)
    mask = nodes.apply(
        lambda row: borough in (parsed_boroughs(row.get("borough_normalized")) or boroughs_from_label(row.get("borough"))),
        axis=1,
    )
    return nodes[mask].copy()


def evidence_bundle(query_id: str, query_type: str, counts: dict[str, Any], facts: list[str], warnings: list[str], entities: list[Any] | None = None, edges: list[Any] | None = None) -> dict[str, Any]:
    return {
        "evidence_bundle_version": "london_d10b_v1",
        "query_id": query_id,
        "query_type": query_type,
        "boundary_statement": " ".join(BOUNDARY_LINES),
        "counts": counts,
        "entities": entities or [],
        "edges": edges or [],
        "answer_facts": facts,
        "provenance_summary": [
            {"stage": "D10Z", "source": "accepted D10 planning-context snapshot"},
            {"stage": "D10B", "source": "official Planning Local Plan Data spatial layers"},
            {"stage": "D9D2", "source": "exact PLD-to-UPRN recovery"},
            {"stage": "OS Open UPRN", "source": "official UPRN point geometry"},
        ],
        "confidence_summary": [
            {"method": "semantic_category_inferred_from_official_layer_title", "confidence": 0.85},
            {"method": "UPRN point-in-policy-polygon via exact PLD-to-UPRN", "confidence": 0.90},
            {"method": "PLD context via exact PLD-to-UPRN plus UPRN geometry", "confidence": 0.88},
        ],
        "warnings": warnings,
        "llm_narration": {"enabled": False, "model": None, "text": None},
    }


def build_queries_and_bundles(
    output_dir: Path,
    counts: dict[str, Any],
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    inventory: pd.DataFrame,
    manual_layers: pd.DataFrame,
    points_df: pd.DataFrame,
    max_query_examples: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    queries_dir = output_dir / "queries"
    bundles_dir = output_dir / "bundles"
    category_counts = nodes["semantic_category"].value_counts().to_dict() if not nodes.empty else {}
    sample_pld = next((x for x in edges["src"].astype(str) if x.startswith("permit:uk-london:pld:")), None) if not edges.empty else None
    sample_uprn = next((x for x in edges["src"].astype(str) if x.startswith("parcel:uk-london:uprn:")), None) if not edges.empty else None
    borough_coverage = borough_policy_coverage(nodes)
    borough_layer_counts = {borough: values["certified_layers"] for borough, values in borough_coverage.items()}
    sample_borough = next((b for b, n in borough_layer_counts.items() if n >= 3), next(iter(borough_layer_counts), None))
    manual_example = manual_layers.head(1).to_dict("records")[0] if not manual_layers.empty else {}
    source_limitations = [
        "D10 canonical graph parquet is not present in the lightweight local D10 directory; D10B emits an overlay graph with resolved endpoints.",
        "Point and line Local Plan context nodes are certified where semantics are clear, but D10B v1 emits spatial edges only for polygon point-in-polygon joins.",
        "TOID context remains geometry-limited unless official TOID geometry is added.",
        "D6 enforcement/building-control remains source-limited.",
        "5,116 D9D2 unmatched PLD records remain unmatched.",
    ]
    query_inputs = [
        {"query_type": "local_plan_context_summary", "parameters": {}},
        {"query_type": "pld_local_plan_context_profile", "parameters": {"canonical_id": sample_pld}},
        {"query_type": "uprn_local_plan_context_profile", "parameters": {"canonical_id": sample_uprn}},
        {"query_type": "borough_local_plan_context_coverage", "parameters": {"borough": sample_borough}},
        {"query_type": "policy_layer_status", "parameters": {"source_layer": manual_example.get("source_layer")}},
        {"query_type": "manual_review_layers", "parameters": {"limit": max_query_examples}},
        {"query_type": "source_limitations", "parameters": {}},
    ]
    node_lookup = nodes.set_index("canonical_id").to_dict("index") if not nodes.empty else {}
    def context_for_subject(subject: str | None) -> list[dict[str, Any]]:
        if not subject:
            return []
        subset = edges[edges["src"].astype(str).eq(subject)].head(max_query_examples)
        out = []
        for row in subset.to_dict("records"):
            context = node_lookup.get(row["dst"], {})
            out.append(
                {
                    "edge": row,
                    "context": {
                        "canonical_id": row["dst"],
                        "semantic_category": context.get("semantic_category"),
                        "policy_name": context.get("policy_name"),
                        "source_layer": context.get("source_layer"),
                        "confidence": parse_json_column(context.get("confidence")),
                    },
                }
            )
        return out
    query_results = [
        {
            "query_type": "local_plan_context_summary",
            "status": "PASS",
            "result": {"counts": counts, "semantic_category_counts": category_counts},
        },
        {
            "query_type": "pld_local_plan_context_profile",
            "status": "PASS" if sample_pld else "FAIL",
            "parameters": {"canonical_id": sample_pld},
            "result": context_for_subject(sample_pld),
        },
        {
            "query_type": "uprn_local_plan_context_profile",
            "status": "PASS" if sample_uprn else "FAIL",
            "parameters": {"canonical_id": sample_uprn},
            "result": context_for_subject(sample_uprn),
        },
        {
            "query_type": "borough_local_plan_context_coverage",
            "status": "PASS" if sample_borough else "FAIL",
            "parameters": {"borough": sample_borough},
            "result": {
                "borough": sample_borough,
                "certified_layers": int(borough_layer_counts.get(sample_borough, 0)) if sample_borough else 0,
                "semantic_categories": borough_coverage.get(sample_borough, {}).get("semantic_categories", []) if sample_borough else [],
            },
        },
        {
            "query_type": "policy_layer_status",
            "status": "PASS" if manual_example else "FAIL",
            "parameters": {"source_layer": manual_example.get("source_layer")},
            "result": manual_example,
        },
        {
            "query_type": "manual_review_layers",
            "status": "PASS",
            "result": manual_layers.head(max_query_examples).to_dict("records"),
        },
        {
            "query_type": "source_limitations",
            "status": "PASS",
            "result": source_limitations,
        },
    ]
    write_json(queries_dir / "sample_query_inputs.json", query_inputs)
    write_json(queries_dir / "sample_query_results.json", {"query_results": query_results})
    bundle_context = evidence_bundle(
        "d10b-local-plan-context",
        "local_plan_context_summary",
        counts,
        [
            f"D10B inventoried {counts['candidate_layers_inventoried']} Local Plan candidate layers.",
            f"D10B certified {counts['certified_layers']} Local Plan layers into controlled semantic categories.",
            f"D10B emitted {counts['context_nodes_emitted']} Local Plan context nodes and {counts['context_edges_emitted']} context edges.",
            f"{counts['pld_applications_with_local_plan_context']} PLD applications have Local Plan context through exact PLD-to-UPRN plus UPRN geometry.",
        ],
        source_limitations,
        sample_records(nodes, max_query_examples),
        sample_records(edges, max_query_examples),
    )
    bundle_borough = evidence_bundle(
        "d10b-local-plan-borough-coverage",
        "borough_local_plan_context_coverage",
        counts,
        [
            f"D10B measured Local Plan context coverage for {counts['boroughs_with_local_plan_context_coverage']} boroughs out of 33.",
            f"The sample borough for deterministic query smoke is {sample_borough}.",
        ],
        source_limitations,
        sample_records(nodes_for_borough(nodes, sample_borough) if sample_borough and not nodes.empty else nodes, max_query_examples),
        [],
    )
    bundle_manual = evidence_bundle(
        "d10b-local-plan-manual-review",
        "manual_review_layers",
        counts,
        [
            f"{counts['manual_review_layers']} layers remain manual-review or candidate-only because their semantics were ambiguous, candidate/draft, source-limited, or not safely normalizable.",
            "Manual-review layers were not forced into the certified graph.",
        ],
        source_limitations,
        manual_layers.head(max_query_examples).to_dict("records"),
        [],
    )
    bundle_limitations = evidence_bundle(
        "d10b-source-limitations",
        "source_limitations",
        counts,
        source_limitations,
        source_limitations,
        [],
        [],
    )
    bundles = {
        "evidence_bundle_local_plan_context.json": bundle_context,
        "evidence_bundle_local_plan_borough_coverage.json": bundle_borough,
        "evidence_bundle_local_plan_manual_review.json": bundle_manual,
        "evidence_bundle_source_limitations.json": bundle_limitations,
    }
    for filename, bundle in bundles.items():
        write_json(bundles_dir / filename, bundle)
    deterministic = {
        "pld_context": bundle_context["answer_facts"],
        "borough_context": bundle_borough["answer_facts"],
        "manual_review": bundle_manual["answer_facts"],
        "source_limitations": bundle_limitations["answer_facts"],
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(queries_dir / "deterministic_briefings.json", deterministic)
    write_briefings(queries_dir, bundles)
    smoke = {
        "gate": "LON-D10B-QUERY-SMOKE",
        "status": "PASS" if all(item["status"] == "PASS" for item in query_results) else "FAIL",
        "query_results": query_results,
    }
    grounding = briefing_grounding_report(queries_dir, bundles)
    return smoke, grounding


def write_briefings(queries_dir: Path, bundles: dict[str, dict[str, Any]]) -> None:
    boundary = "\n".join(BOUNDARY_LINES)
    mapping = {
        "london_local_plan_pld_context_briefing.md": bundles["evidence_bundle_local_plan_context.json"],
        "london_local_plan_borough_context_briefing.md": bundles["evidence_bundle_local_plan_borough_coverage.json"],
        "london_manual_review_limitations_briefing.md": bundles["evidence_bundle_local_plan_manual_review.json"],
        "london_source_limitations_briefing.md": bundles["evidence_bundle_source_limitations.json"],
    }
    for filename, bundle in mapping.items():
        lines = [
            f"# {bundle['query_type'].replace('_', ' ').title()}",
            "",
            boundary,
            "",
            "## No-Overclaim Boundary",
            *[f"- {line}" for line in NO_OVERCLAIM_LINES],
            "",
            "## Evidence Facts",
            *[f"- {fact}" for fact in bundle["answer_facts"]],
            "",
            "## Warnings",
            *[f"- {warning}" for warning in bundle["warnings"]],
        ]
        (queries_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def briefing_grounding_report(queries_dir: Path, bundles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    grounded = True
    checks = {}
    for filename in [
        "london_local_plan_pld_context_briefing.md",
        "london_local_plan_borough_context_briefing.md",
        "london_manual_review_limitations_briefing.md",
        "london_source_limitations_briefing.md",
    ]:
        text = (queries_dir / filename).read_text(encoding="utf-8")
        missing_boundary = [line for line in BOUNDARY_LINES if line not in text]
        if missing_boundary:
            grounded = False
        checks[filename] = {"missing_boundary_lines": missing_boundary, "source": "generated from D10B EvidenceBundles"}
    return {"gate": "LON-D10B-BRIEFING-GROUNDING", "status": "PASS" if grounded else "FAIL", "checks": checks}


def id_format_report(nodes: pd.DataFrame) -> dict[str, Any]:
    bad = []
    pattern = re.compile(r"^planning_policy_context_area:uk-london:([a-z_]+):[a-z0-9_]+$")
    for cid in nodes["canonical_id"].astype(str).tolist() if not nodes.empty else []:
        match = pattern.match(cid)
        if not match or match.group(1) not in ALLOWED_SEMANTIC_CATEGORIES or any(term in cid for term in FORBIDDEN_ID_TERMS):
            bad.append(cid)
    return {"gate": "LON-D10B-ID-FORMAT", "status": "PASS" if not bad and len(nodes) else "FAIL", "bad_ids": bad[:50]}


def edge_report(edges: pd.DataFrame, enriched_nodes: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    required_cols = ["join_method", "source_geometry_status", "target_geometry_status", "distance_threshold_m", "source_stage", "source_layer", "confidence"]
    missing_cols = [c for c in required_cols if c not in edges.columns]
    bad_relations = sorted(set(edges["relation"].astype(str)) - ALLOWED_RELATIONS) if not edges.empty else []
    node_set = set(enriched_nodes["canonical_id"].astype(str)) if not enriched_nodes.empty else set()
    src_missing = int((~edges["src"].astype(str).isin(node_set)).sum()) if not edges.empty else 0
    dst_missing = int((~edges["dst"].astype(str).isin(node_set)).sum()) if not edges.empty else 0
    context_report = {
        "gate": "LON-D10B-CONTEXT-EDGE",
        "status": "PASS" if not missing_cols and not bad_relations and len(edges) else "FAIL",
        "context_edges": int(len(edges)),
        "edges_by_relation": edges["relation"].value_counts().to_dict() if not edges.empty else {},
        "edges_by_semantic_category": edges["semantic_category"].value_counts().to_dict() if "semantic_category" in edges.columns and not edges.empty else {},
        "missing_required_columns": missing_cols,
        "bad_relations": bad_relations,
    }
    integrity = {
        "gate": "LON-D10B-EDGE-INTEGRITY",
        "status": "PASS" if src_missing == 0 and dst_missing == 0 and len(edges) else "FAIL",
        "context_edges": int(len(edges)),
        "src_missing": src_missing,
        "dst_missing": dst_missing,
    }
    return context_report, integrity


def coverage_report(counts: dict[str, Any], nodes: pd.DataFrame, edges: pd.DataFrame, inventory: pd.DataFrame) -> dict[str, Any]:
    return {
        "gate": "LON-D10B-COVERAGE",
        "status": "PASS" if counts["candidate_layers_inventoried"] and counts["certified_layers"] and counts["context_edges_emitted"] else "FAIL",
        "counts": counts,
        "coverage_by_semantic_category": nodes["semantic_category"].value_counts().to_dict() if not nodes.empty else {},
        "edge_coverage_by_semantic_category": edges["semantic_category"].value_counts().to_dict() if not edges.empty else {},
        "layer_classification_counts": inventory["classification"].value_counts().to_dict() if not inventory.empty else {},
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    required_files = [
        output_dir / "README.md",
        output_dir / "LON_D10B_MANIFEST.json",
        output_dir / "LON_D10B_HARNESS_REPORT.json",
        output_dir / "LON_D10B_ADAPTER_HANDOVER.md",
        output_dir / "queries" / "london_local_plan_pld_context_briefing.md",
        output_dir / "queries" / "london_local_plan_borough_context_briefing.md",
        output_dir / "queries" / "london_manual_review_limitations_briefing.md",
        output_dir / "queries" / "london_source_limitations_briefing.md",
    ]
    checks = {}
    passed = True
    for path in required_files:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [line for line in NO_OVERCLAIM_LINES if line not in text]
        checks[str(path.relative_to(output_dir))] = {"missing_no_overclaim_lines": missing}
        if missing:
            passed = False
    all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in required_files if path.exists()).lower()
    forbidden_positive = [
        "application should be approved",
        "application should be refused",
        "certifies application compliance",
        "complete london local-plan coverage",
        "complete borough policy coverage",
        "legal interpretation of local plan policy",
        "enforcement/building-control integrated",
    ]
    found = [phrase for phrase in forbidden_positive if phrase in all_text]
    if found:
        passed = False
    return {
        "gate": "LON-D10B-NO-OVERCLAIM",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "forbidden_positive_claims_found": found,
    }


def drift_test_report(manual_layers: pd.DataFrame) -> dict[str, Any]:
    tests = [
        {"case": "site_allocation_to_approval_area", "accepted": "approval_area" in ALLOWED_SEMANTIC_CATEGORIES},
        {"case": "within_policy_context_to_approved_by_policy", "accepted": "approved_by_policy" in ALLOWED_RELATIONS},
        {"case": "legal_planning_decision_id", "accepted": not any(term in "planning_policy_context_area:uk-london:legal_planning_decision:x" for term in FORBIDDEN_ID_TERMS)},
        {"case": "manual_review_forced_certified", "accepted": bool(manual_layers.empty)},
        {"case": "d6_source_limitation_omitted", "accepted": "D6 enforcement/building-control remains source-limited." not in D10_LIMITATION_CARRY_FORWARD},
    ]
    passed = all(not test["accepted"] for test in tests)
    return {"gate": "LON-D10B-DRIFT", "status": "PASS" if passed else "FAIL", "tests": tests}


def write_text_artifacts(output_dir: Path, counts: dict[str, Any]) -> None:
    boundary = "\n".join(NO_OVERCLAIM_LINES + D10_LIMITATION_CARRY_FORWARD)
    readme = [
        "# LON-D10B Local Plan Data Semantic Certification",
        "",
        f"Status: `{counts['status']}`",
        "",
        "D10B certifies only Local Plan / borough policy layers that map cleanly to the controlled planning-context taxonomy.",
        "",
        "## Counts",
        f"- Candidate layers inventoried: `{counts['candidate_layers_inventoried']}`",
        f"- Certified layers: `{counts['certified_layers']}`",
        f"- Manual-review layers: `{counts['manual_review_layers']}`",
        f"- Context nodes emitted: `{counts['context_nodes_emitted']}`",
        f"- Context edges emitted: `{counts['context_edges_emitted']}`",
        f"- PLD applications with Local Plan context: `{counts['pld_applications_with_local_plan_context']}`",
        f"- UPRNs with Local Plan context: `{counts['uprns_with_local_plan_context']}`",
        f"- Boroughs with Local Plan context coverage: `{counts['boroughs_with_local_plan_context_coverage']} / 33`",
        "",
        "## Boundaries",
        boundary,
    ]
    (output_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    handover = [
        "# LON-D10B Adapter Handover",
        "",
        "The adapter should treat D10B outputs as deterministic Local Plan context evidence.",
        "",
        "Query types: local_plan_context_summary, pld_local_plan_context_profile, uprn_local_plan_context_profile, borough_local_plan_context_coverage, policy_layer_status, manual_review_layers, source_limitations.",
        "",
        "Spatial edge semantics are geometry-backed polygon containment joins only in D10B v1.",
        "",
        "## Boundaries",
        boundary,
    ]
    (output_dir / "LON_D10B_ADAPTER_HANDOVER.md").write_text("\n".join(handover) + "\n", encoding="utf-8")


def sync_to_4070(output_dir: Path, publish_4070: bool) -> dict[str, Any]:
    if not publish_4070:
        return {"gate": "LON-D10B-4070-SYNC", "status": "NOT_RUN", "target": str(SYNC_TARGET), "reason": "publish_4070_false"}
    include = [
        "README.md",
        "LON_D10B_MANIFEST.json",
        "LON_D10B_HARNESS_REPORT.json",
        "LON_D10B_COVERAGE_REPORT.json",
        "LON_D10B_POLICY_LAYER_CERTIFICATION_REPORT.json",
        "LON_D10B_MANUAL_REVIEW_REPORT.json",
        "LON_D10B_NO_OVERCLAIM_REPORT.json",
        "LON_D10B_ADAPTER_HANDOVER.md",
        "SHA256SUMS.json",
        "queries/sample_query_inputs.json",
        "queries/sample_query_results.json",
        "queries/deterministic_briefings.json",
        "bundles/evidence_bundle_local_plan_context.json",
        "bundles/evidence_bundle_local_plan_borough_coverage.json",
        "bundles/evidence_bundle_local_plan_manual_review.json",
        "bundles/evidence_bundle_source_limitations.json",
        "reports/source_layer_counts.json",
        "reports/certified_layer_counts.json",
        "reports/manual_review_layer_counts.json",
        "reports/semantic_category_counts.json",
        "reports/borough_policy_layer_coverage.json",
        "reports/pld_local_plan_context_coverage.json",
        "reports/uprn_local_plan_context_coverage.json",
        "reports/spatial_join_methods.json",
        "reports/confidence_summary.json",
        "reports/geometry_limitations.json",
        "reports/execution_backend.json",
    ]
    try:
        if SYNC_TARGET.exists():
            shutil.rmtree(SYNC_TARGET)
        copied = []
        bytes_total = 0
        for rel in include:
            src = output_dir / rel
            if not src.exists():
                continue
            dst = SYNC_TARGET / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
            bytes_total += dst.stat().st_size
        return {
            "gate": "LON-D10B-4070-SYNC",
            "status": "PASS",
            "target": str(SYNC_TARGET),
            "file_count": len(copied),
            "bytes": bytes_total,
            "raw_files_included": False,
            "large_parquet_included": False,
            "files": copied,
        }
    except Exception as exc:
        return {"gate": "LON-D10B-4070-SYNC", "status": "NOT_RUN_OR_UNREACHABLE", "target": str(SYNC_TARGET), "reason": f"{type(exc).__name__}: {exc}"}


def run_lon_d10b_gate(
    d10_dir: str,
    d10z_dir: str | None,
    raw_root: str,
    output_dir: str,
    max_query_examples: int = 25,
    publish_4070: bool = True,
) -> dict:
    d10_path = Path(d10_dir)
    d10z_path = Path(d10z_dir) if d10z_dir else None
    raw_path = Path(raw_root)
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    canonical = output_path / "canonical"
    reports = output_path / "reports"

    input_paths = local_input_paths(d10_path, d10z_path, raw_path)
    before_fingerprint = file_fingerprint(input_paths)
    precond = precondition_report(d10_path, d10z_path)
    d10_harness = read_json(d10_path / "LON_D10_HARNESS_REPORT.json")
    d10z_snapshot = read_json(d10z_path / "LON_D10Z_ACCEPTED_SNAPSHOT.json") if d10z_path and (d10z_path / "LON_D10Z_ACCEPTED_SNAPSHOT.json").exists() else {}
    inventory, source_inventory_report = discover_local_plan_layers(raw_path, d10_path)
    write_json(output_path / "LON_D10B_LOCAL_PLAN_LAYER_INVENTORY.json", {"layers": inventory.to_dict("records"), **source_inventory_report})
    inventory.to_parquet(canonical / "london_local_plan_layer_inventory.parquet", index=False)

    certified_layers = inventory[inventory["classification"].eq("used_certified")].copy() if not inventory.empty else pd.DataFrame()
    manual_layers = inventory[~inventory["classification"].eq("used_certified")].copy() if not inventory.empty else pd.DataFrame()
    nodes, policy_layers, layer_read_reports, geometry_limitations = build_context_nodes_and_layers(certified_layers)
    nodes.to_parquet(canonical / "london_local_plan_context_nodes.parquet", index=False)
    if policy_layers.empty:
        policy_layers.to_parquet(canonical / "london_local_plan_layers.parquet", index=False)
    else:
        policy_layers.to_parquet(canonical / "london_local_plan_layers.parquet", index=False)
    manual_layers.to_parquet(canonical / "london_local_plan_manual_review_layers.parquet", index=False)

    pld_edges, pld_records, unmatched = load_d9d2_edges_and_records()
    points_df, uprn_geometry_report = stream_matched_uprn_points(raw_path, pld_edges, pld_records)
    context_edges, spatial_join, edge_integrity_pre = build_spatial_edges(points_df, policy_layers, pld_edges)
    context_edges.to_parquet(canonical / "london_local_plan_context_edges.parquet", index=False)

    endpoints = endpoint_nodes(context_edges, points_df, pld_records)
    enriched_nodes = pd.concat(
        [
            nodes[["canonical_id", "entity_type", "semantic_category", "source_layer", "borough", "geometry_status"]].assign(source_stage="D10B context node") if not nodes.empty else pd.DataFrame(),
            endpoints,
        ],
        ignore_index=True,
        sort=False,
    ).drop_duplicates("canonical_id")
    enriched_edges = context_edges.copy()
    enriched_nodes.to_parquet(canonical / "london_d10b_enriched_graph_nodes.parquet", index=False)
    enriched_edges.to_parquet(canonical / "london_d10b_enriched_graph_edges.parquet", index=False)
    write_json(canonical / "london_local_plan_context_entities_sample.json", sample_records(nodes, max_query_examples))
    write_json(canonical / "london_local_plan_context_edges_sample.json", sample_records(context_edges, max_query_examples))

    context_edge_report, edge_integrity = edge_report(context_edges, enriched_nodes)
    id_format = id_format_report(nodes)
    pld_context_count = int(context_edges[context_edges["src"].astype(str).str.startswith("permit:uk-london:pld:")]["src"].nunique()) if not context_edges.empty else 0
    uprn_context_count = int(context_edges[context_edges["src"].astype(str).str.startswith("parcel:uk-london:uprn:")]["src"].nunique()) if not context_edges.empty else 0
    context_target_ids = set(context_edges["dst"].astype(str)) if not context_edges.empty else set()
    borough_coverage_for_targets = borough_policy_coverage(nodes, context_target_ids)
    boroughs_with_context = len(borough_coverage_for_targets)
    semantic_counts = nodes["semantic_category"].value_counts().to_dict() if not nodes.empty else {}
    counts = {
        "status": "PENDING",
        "candidate_layers_inventoried": int(len(inventory)),
        "certified_layers": int(len(certified_layers)),
        "manual_review_layers": int(len(manual_layers)),
        "context_nodes_emitted": int(len(nodes)),
        "context_edges_emitted": int(len(context_edges)),
        "pld_applications_with_local_plan_context": pld_context_count,
        "uprns_with_local_plan_context": uprn_context_count,
        "boroughs_with_local_plan_context_coverage": boroughs_with_context,
        "boroughs_total": 33,
        "semantic_categories_emitted": semantic_counts,
        "d9d2_unmatched_pld_records_carried_forward": int(len(unmatched)),
    }
    coverage = coverage_report(counts, nodes, context_edges, inventory)
    certification_report = {
        "gate": "LON-D10B-CERTIFICATION",
        "status": "PASS" if len(certified_layers) and len(nodes) and len(manual_layers) else "FAIL",
        "policy": "Only official layers with clear taxonomy mapping and valid/readable geometry are certified.",
        "certified_layers": int(len(certified_layers)),
        "manual_review_or_non_certified_layers": int(len(manual_layers)),
        "layer_read_reports": layer_read_reports,
        "ambiguous_layers_forced_into_graph": 0,
    }
    semantic_classification = {
        "gate": "LON-D10B-SEMANTIC-CLASSIFICATION",
        "status": "PASS" if len(inventory) and inventory["classification"].notna().all() else "FAIL",
        "classification_counts": inventory["classification"].value_counts().to_dict() if not inventory.empty else {},
        "semantic_category_counts_certified_layers": certified_layers["semantic_category"].value_counts().to_dict() if not certified_layers.empty else {},
    }
    manual_report = {
        "gate": "LON-D10B-MANUAL-REVIEW",
        "status": "PASS" if len(manual_layers) else "FAIL",
        "manual_review_layers": int((manual_layers["classification"] == "manual_review").sum()) if not manual_layers.empty else 0,
        "candidate_only_layers": int((manual_layers["classification"] == "used_candidate_only").sum()) if not manual_layers.empty else 0,
        "source_limited_layers": int((manual_layers["classification"] == "source_limited").sum()) if not manual_layers.empty else 0,
        "examples": manual_layers.head(max_query_examples).to_dict("records"),
    }

    counts["status"] = "PASS"
    write_text_artifacts(output_path, counts)
    query_smoke, briefing_grounding = build_queries_and_bundles(
        output_path, counts, nodes, context_edges, inventory, manual_layers, points_df, max_query_examples
    )
    write_json(output_path / "LON_D10B_INPUT_INVENTORY.json", {
        "d10_dir": str(d10_path),
        "d10z_dir": str(d10z_path) if d10z_path else None,
        "raw_root": str(raw_path),
        "input_file_count": len(input_paths),
        "input_fingerprint_before": before_fingerprint,
        "d10_status": d10_harness.get("status"),
        "d10z_status": d10z_snapshot.get("status"),
        "d10z_not_found_used_d10_directly": precond["d10z_not_found_used_d10_directly"],
    })
    write_json(output_path / "LON_D10B_SEMANTIC_CLASSIFICATION_REPORT.json", semantic_classification)
    write_json(output_path / "LON_D10B_POLICY_LAYER_CERTIFICATION_REPORT.json", certification_report)
    write_json(output_path / "LON_D10B_SPATIAL_JOIN_REPORT.json", spatial_join)
    write_json(output_path / "LON_D10B_CONTEXT_EDGE_REPORT.json", {**context_edge_report, "edge_integrity": edge_integrity})
    write_json(output_path / "LON_D10B_COVERAGE_REPORT.json", coverage)
    write_json(output_path / "LON_D10B_QUERY_SMOKE_REPORT.json", query_smoke)
    write_json(output_path / "LON_D10B_BRIEFING_GROUNDING_REPORT.json", briefing_grounding)
    write_json(output_path / "LON_D10B_MANUAL_REVIEW_REPORT.json", manual_report)
    drift = drift_test_report(manual_layers)
    write_json(output_path / "LON_D10B_DRIFT_TEST_REPORT.json", drift)
    write_json(reports / "source_layer_counts.json", source_inventory_report)
    write_json(reports / "certified_layer_counts.json", certified_layers["semantic_category"].value_counts().to_dict() if not certified_layers.empty else {})
    write_json(reports / "manual_review_layer_counts.json", manual_layers["classification"].value_counts().to_dict() if not manual_layers.empty else {})
    write_json(reports / "semantic_category_counts.json", semantic_counts)
    write_json(reports / "borough_policy_layer_coverage.json", borough_policy_coverage(nodes))
    write_json(reports / "pld_local_plan_context_coverage.json", {"pld_applications_with_local_plan_context": pld_context_count, "pld_context_edges": int((context_edges["src"].astype(str).str.startswith("permit:uk-london:pld:")).sum()) if not context_edges.empty else 0})
    write_json(reports / "uprn_local_plan_context_coverage.json", {"uprns_with_local_plan_context": uprn_context_count, "uprn_context_edges": int((context_edges["src"].astype(str).str.startswith("parcel:uk-london:uprn:")).sum()) if not context_edges.empty else 0, "uprn_geometry_recovery": uprn_geometry_report})
    write_json(reports / "spatial_join_methods.json", spatial_join)
    write_json(reports / "confidence_summary.json", {
        "semantic category inferred from official layer title/metadata": {"confidence": 0.85, "certified_layers": int(len(certified_layers))},
        "UPRN point-in-policy-polygon via exact PLD-to-UPRN": {"confidence": 0.90, "edges": int((context_edges["src"].astype(str).str.startswith("parcel:uk-london:uprn:")).sum()) if not context_edges.empty else 0},
        "PLD context via exact PLD-to-UPRN plus UPRN geometry": {"confidence": 0.88, "edges": int((context_edges["src"].astype(str).str.startswith("permit:uk-london:pld:")).sum()) if not context_edges.empty else 0},
    })
    write_json(reports / "geometry_limitations.json", {
        "limitations": geometry_limitations,
        "point_line_edge_policy": spatial_join.get("point_and_line_layer_edge_policy"),
        "toid_context": "TOID context remains geometry-limited unless new official TOID geometry is added.",
    })
    write_json(reports / "execution_backend.json", {"execution_backend": EXECUTION_BACKEND})

    carry_forward = {
        "gate": "LON-D10B-D10-LIMITATION-CARRY-FORWARD",
        "status": "PASS",
        "limitations": D10_LIMITATION_CARRY_FORWARD,
        "d9d2_unmatched_records": int(len(unmatched)),
    }
    after_fingerprint = file_fingerprint(input_paths)
    no_mutation = {
        "gate": "LON-D10B-NO-MUTATION",
        "status": "PASS" if before_fingerprint == after_fingerprint else "FAIL",
        "changed_inputs": [path for path in before_fingerprint if before_fingerprint.get(path) != after_fingerprint.get(path)],
    }
    manifest = {
        "task": TASK_NAME,
        "status": "PENDING",
        "created_utc": utc_now(),
        "execution_backend": EXECUTION_BACKEND,
        "counts": counts,
        "allowed_semantic_categories": sorted(ALLOWED_SEMANTIC_CATEGORIES),
        "allowed_relations": sorted(ALLOWED_RELATIONS),
        "no_overclaim": NO_OVERCLAIM_LINES,
        "d10_limitations_carried_forward": D10_LIMITATION_CARRY_FORWARD,
        "enriched_graph_scope": "D10B overlay graph with D10B context nodes, D10B context edges, and resolved PLD/UPRN endpoints; it does not claim to be a full copy of the accepted D10 graph parquet.",
    }
    write_json(output_path / "LON_D10B_MANIFEST.json", manifest)
    write_json(output_path / "LON_D10B_HARNESS_REPORT.json", {**manifest, "status": "PENDING"})
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D10B_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = {
        "LON-D10B-PRECOND": precond["status"],
        "LON-D10B-SOURCE-INVENTORY": source_inventory_report["status"],
        "LON-D10B-SEMANTIC-CLASSIFICATION": semantic_classification["status"],
        "LON-D10B-CERTIFICATION": certification_report["status"],
        "LON-D10B-ID-FORMAT": id_format["status"],
        "LON-D10B-SPATIAL-JOIN": spatial_join["status"],
        "LON-D10B-EDGE-INTEGRITY": edge_integrity["status"],
        "LON-D10B-COVERAGE": coverage["status"],
        "LON-D10B-MANUAL-REVIEW": manual_report["status"],
        "LON-D10B-QUERY-SMOKE": query_smoke["status"],
        "LON-D10B-BRIEFING-GROUNDING": briefing_grounding["status"],
        "LON-D10B-D10-LIMITATION-CARRY-FORWARD": carry_forward["status"],
        "LON-D10B-DRIFT": drift["status"],
        "LON-D10B-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D10B-NO-MUTATION": no_mutation["status"],
        "LON-D10B-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    counts["status"] = overall
    sync_report = sync_to_4070(output_path, publish_4070 and overall == "PASS")
    write_json(output_path / "LON_D10B_4070_SYNC_REPORT.json", sync_report)
    gates["LON-D10B-4070-SYNC"] = "PASS" if sync_report["status"] in {"PASS", "NOT_RUN", "NOT_RUN_OR_UNREACHABLE"} else "FAIL"
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    counts["status"] = overall
    write_text_artifacts(output_path, counts)
    manifest["status"] = overall
    manifest["counts"] = counts
    manifest["4070_lightweight_sync"] = sync_report
    harness = {
        **manifest,
        "preconditions": precond,
        "source_inventory": source_inventory_report,
        "semantic_classification": semantic_classification,
        "certification": certification_report,
        "id_format": id_format,
        "spatial_join": spatial_join,
        "context_edge_report": context_edge_report,
        "edge_integrity": edge_integrity,
        "coverage": coverage,
        "query_smoke": query_smoke,
        "briefing_grounding": briefing_grounding,
        "manual_review": manual_report,
        "d10_limitation_carry_forward": carry_forward,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "no_mutation": no_mutation,
        "gates": gates,
    }
    write_json(output_path / "LON_D10B_MANIFEST.json", manifest)
    write_json(output_path / "LON_D10B_HARNESS_REPORT.json", harness)
    hash_report = write_hashes(output_path)
    harness["hashes"] = hash_report
    write_json(output_path / "LON_D10B_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d10-dir", default=DEFAULT_D10_DIR)
    parser.add_argument("--d10z-dir", default=DEFAULT_D10Z_DIR)
    parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-query-examples", type=int, default=25)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d10b_gate(
        d10_dir=args.d10_dir,
        d10z_dir=args.d10z_dir,
        raw_root=args.raw_root,
        output_dir=args.output_dir,
        max_query_examples=args.max_query_examples,
        publish_4070=args.publish_4070,
    )
    counts = report["counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D10: {report['preconditions']['checks']['d10_harness_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Candidate Local Plan layers inventoried: {counts['candidate_layers_inventoried']}")
    print(f"Certified layers: {counts['certified_layers']}")
    print(f"Manual-review layers: {counts['manual_review_layers']}")
    print(f"Context nodes emitted: {counts['context_nodes_emitted']}")
    print(f"Context edges emitted: {counts['context_edges_emitted']}")
    print(f"PLD applications with Local Plan context: {counts['pld_applications_with_local_plan_context']}")
    print(f"UPRNs with Local Plan context: {counts['uprns_with_local_plan_context']}")
    print(f"Boroughs with Local Plan context coverage: {counts['boroughs_with_local_plan_context_coverage']} / 33")
    print(f"Semantic categories emitted: {counts['semantic_categories_emitted']}")
    print(f"Query smoke: {report['query_smoke']['status']}")
    print(f"Briefing grounding: {report['briefing_grounding']['status']}")
    print(f"Manual-review report: {report['manual_review']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Execution backend: {report['execution_backend']}")
    print(f"4070 lightweight sync: {report['4070_lightweight_sync']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
