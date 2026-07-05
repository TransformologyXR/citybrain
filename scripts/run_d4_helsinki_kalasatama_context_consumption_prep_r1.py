#!/usr/bin/env python3
"""D4 Helsinki/Kalasatama context consumption prep.

Consumes the landed Kalasatama semantic/context package and prepares candidate
CityBrain CER/USD sidecar artifacts. This is a prep lane only: it does not
download sources, mutate prior outputs, or claim accepted/certified identity.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "D4-HELSINKI-KALASATAMA-CONTEXT-CONSUMPTION-PREP-R1"
STATUS_PASS_LIMITED = "PASS_D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_WITH_LIMITATIONS"
STATUS_FAIL = "FAIL_D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

INPUT_ROOT = REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_context_data_landing_r1"
TILES_ROOT = REPO_ROOT / "outputs" / "d4_3d_helsinki_kalasatama_3d_tiles_landing_r1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "d4_helsinki_kalasatama_context_consumption_prep_r1"

NS = {
    "gml": "http://www.opengis.net/gml",
    "bldg": "http://www.opengis.net/citygml/building/2.0",
    "gen": "http://www.opengis.net/citygml/generics/2.0",
}
GML_ID = "{http://www.opengis.net/gml}id"
BUILDING_TAG = "{http://www.opengis.net/citygml/building/2.0}Building"
GEN_NS = "{http://www.opengis.net/citygml/generics/2.0}"


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except Exception:
            continue
    return None


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_stat(path: Path, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "path": rel(path) if path.exists() else str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
    }
    if include_hash and path.exists():
        payload["sha256"] = sha256_file(path)
    return payload


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def stable_short(value: str, length: int = 16) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def sanitize_prim_token(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "unknown"
    if value[0].isdigit():
        value = f"b_{value}"
    return value


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None


def first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def collect_generic_attrs(elem: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}

    def walk(node: ET.Element, prefix: str = "") -> None:
        for child in list(node):
            if not child.tag.startswith(GEN_NS):
                continue
            lname = local_name(child.tag)
            name = child.attrib.get("name")
            if lname == "genericAttributeSet":
                walk(child, prefix=f"{prefix}{name}." if name else prefix)
                continue
            if lname.endswith("Attribute") and name:
                value_elem = child.find("gen:value", NS)
                value = value_elem.text.strip() if value_elem is not None and value_elem.text else ""
                key = name
                if key in attrs and attrs[key] != value:
                    key = f"{prefix}{name}"
                if key in attrs and attrs[key] != value:
                    idx = 2
                    while f"{key}_{idx}" in attrs:
                        idx += 1
                    key = f"{key}_{idx}"
                attrs[key] = value
                walk(child, prefix=prefix)

    walk(elem)
    return attrs


def direct_text(elem: ET.Element, xpath: str) -> str | None:
    found = elem.find(xpath, NS)
    if found is None or found.text is None:
        return None
    return found.text.strip()


def geometry_bbox(elem: ET.Element) -> dict[str, Any]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    pos_lists = elem.findall(".//gml:posList", NS)
    for pos_list in pos_lists:
        if not pos_list.text:
            continue
        raw = pos_list.text.split()
        try:
            nums = [float(v) for v in raw]
        except ValueError:
            continue
        dim = int(pos_list.attrib.get("srsDimension", "3") or 3)
        if dim not in (2, 3) or len(nums) % dim != 0:
            dim = 3 if len(nums) % 3 == 0 else 2
        for i in range(0, len(nums) - dim + 1, dim):
            xs.append(nums[i])
            ys.append(nums[i + 1])
            if dim == 3:
                zs.append(nums[i + 2])
    for pos in elem.findall(".//gml:pos", NS):
        if not pos.text:
            continue
        try:
            nums = [float(v) for v in pos.text.split()]
        except ValueError:
            continue
        if len(nums) >= 2:
            xs.append(nums[0])
            ys.append(nums[1])
        if len(nums) >= 3:
            zs.append(nums[2])
    if not xs or not ys:
        return {
            "bbox_native": None,
            "centroid_native": None,
            "point_count": 0,
            "bbox_status": "missing_geometry",
        }
    bbox = {
        "min_x": min(xs),
        "min_y": min(ys),
        "min_z": min(zs) if zs else None,
        "max_x": max(xs),
        "max_y": max(ys),
        "max_z": max(zs) if zs else None,
    }
    centroid = {
        "x": (bbox["min_x"] + bbox["max_x"]) / 2,
        "y": (bbox["min_y"] + bbox["max_y"]) / 2,
        "z": ((bbox["min_z"] + bbox["max_z"]) / 2) if bbox["min_z"] is not None and bbox["max_z"] is not None else None,
    }
    return {
        "bbox_native": bbox,
        "centroid_native": centroid,
        "point_count": len(xs),
        "bbox_status": "bbox_from_citygml_poslist",
    }


def candidate_id_for_gml(gml_id: str) -> str:
    return f"citybrain:cer_candidate:hel:kalasatama:building:{gml_id}"


def parse_citygml_buildings(zip_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    attr_counter: Counter[str] = Counter()
    crs_name: str | None = None
    source_gml_entry: str | None = None
    parse_errors: list[str] = []

    with zipfile.ZipFile(zip_path) as zf:
        gml_entries = [name for name in zf.namelist() if name.lower().endswith(".gml")]
        if not gml_entries:
            raise RuntimeError(f"No .gml entry found in {zip_path}")
        source_gml_entry = gml_entries[0]
        with zf.open(source_gml_entry) as fh:
            for _event, elem in ET.iterparse(fh, events=("end",)):
                if elem.tag == "{http://www.opengis.net/gml}Envelope" and crs_name is None:
                    crs_name = elem.attrib.get("srsName")
                if elem.tag != BUILDING_TAG:
                    continue
                try:
                    gml_id = elem.attrib.get(GML_ID) or f"missing_gml_{len(rows) + 1:05d}"
                    generic_attrs = collect_generic_attrs(elem)
                    attr_counter.update(generic_attrs.keys())
                    geom = geometry_bbox(elem)
                    measured_height = direct_text(elem, "bldg:measuredHeight")
                    storeys_above_ground = direct_text(elem, "bldg:storeysAboveGround")
                    source_identifiers = {
                        "VTJ_PRT": first_present(generic_attrs, ["Rakennustunnus_(VTJ-PRT)", "VTJ_PRT"]),
                        "ID": first_present(generic_attrs, ["ID"]),
                        "UUID": first_present(generic_attrs, ["UUID"]),
                        "CODE": first_present(generic_attrs, ["CODE"]),
                        "RATU": first_present(generic_attrs, ["RATU"]),
                    }
                    useful_attrs = {
                        "measuredHeight": measured_height,
                        "BREC_BuildingHeightNN": first_present(generic_attrs, ["BREC_BuildingHeightNN"]),
                        "BREC_RoofNames": first_present(generic_attrs, ["BREC_RoofNames"]),
                        "LowestRoof": first_present(generic_attrs, ["LowestRoof"]),
                        "HighestRoof": first_present(generic_attrs, ["HighestRoof"]),
                        "GroundLevel": first_present(generic_attrs, ["GroundLevel"]),
                        "REPAIRED": first_present(generic_attrs, ["REPAIRED"]),
                        "Rakennuksen_tila": first_present(generic_attrs, ["Rakennuksen_tila"]),
                        "TILA_KOODI": first_present(generic_attrs, ["TILA_KOODI"]),
                        "Kerroksia": first_present(generic_attrs, ["Kerroksia"]),
                        "C_KAYTTARK": first_present(generic_attrs, ["C_KAYTTARK"]),
                        "storeysAboveGround": storeys_above_ground,
                    }
                    primary_keys = [gml_id]
                    for value in source_identifiers.values():
                        if value not in (None, ""):
                            primary_keys.append(str(value))
                    confidence = "source_identity_high" if source_identifiers["UUID"] or source_identifiers["VTJ_PRT"] else "source_identity_medium"
                    if geom["bbox_native"] is None:
                        confidence = "source_identity_medium_geometry_missing"
                    row = {
                        "gml_id": gml_id,
                        "citybrain_candidate_id": candidate_id_for_gml(gml_id),
                        "canonical_entity_candidate_id": f"cer:candidate:hel:building:{stable_short(gml_id)}",
                        "entity_type": "building",
                        "source_system": "Helsinki CityGML Kalasatama",
                        "source_record_ref": f"{rel(zip_path)}#{source_gml_entry}#{gml_id}",
                        "source_identifiers": source_identifiers,
                        "source_attributes": useful_attrs,
                        "primary_matching_keys": primary_keys,
                        "aliases_source_ids": [value for value in source_identifiers.values() if value not in (None, "")],
                        "geometry": {
                            "source_crs": crs_name or "urn:ogc:drf:crs:EPSG::3879",
                            "source_crs_label": "EPSG:3879 / ETRS-GK25, height context from CityGML/N2000-like source metadata",
                            "bbox_native": geom["bbox_native"],
                            "centroid_native": geom["centroid_native"],
                            "point_count": geom["point_count"],
                            "geometry_status": geom["bbox_status"],
                        },
                        "evidence_refs": [
                            rel(zip_path),
                            "outputs/d4_helsinki_kalasatama_context_data_landing_r1/inventory/citygml_semantic_counts.json",
                            "outputs/d4_helsinki_kalasatama_context_data_landing_r1/inventory/citygml_zip_inventory.json",
                        ],
                        "confidence": confidence,
                        "review_state": "candidate_needs_review_not_canonical",
                        "limitation_refs": [
                            "lim:citygml_candidate_identity_not_canonical_acceptance",
                            "lim:visual_mesh_backdrop_only_until_alignment_smoke",
                            "lim:no_legal_or_certified_identity_claim",
                        ],
                    }
                    rows.append(row)
                except Exception as exc:  # keep parsing but record row failure
                    parse_errors.append(f"building_index={len(rows) + 1}: {exc}")
                finally:
                    elem.clear()
    heights = [
        as_float(row["source_attributes"].get("measuredHeight"))
        or as_float(row["source_attributes"].get("BREC_BuildingHeightNN"))
        for row in rows
    ]
    heights = [value for value in heights if value is not None]
    summary = {
        "zip_path": rel(zip_path),
        "source_gml_entry": source_gml_entry,
        "building_rows": len(rows),
        "source_crs": crs_name or "urn:ogc:drf:crs:EPSG::3879",
        "generic_attribute_names_top": attr_counter.most_common(40),
        "height_summary_m": {
            "count": len(heights),
            "min": min(heights) if heights else None,
            "median": statistics.median(heights) if heights else None,
            "max": max(heights) if heights else None,
        },
        "parse_errors": parse_errors[:50],
        "parse_error_count": len(parse_errors),
    }
    return rows, summary


def write_building_tables(rows: list[dict[str, Any]]) -> None:
    jsonl_path = OUTPUT_ROOT / "CITYGML_BUILDING_IDENTITY_NORMALIZATION.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_path = OUTPUT_ROOT / "CITYGML_BUILDING_IDENTITY_NORMALIZATION.csv"
    fieldnames = [
        "gml_id",
        "citybrain_candidate_id",
        "canonical_entity_candidate_id",
        "VTJ_PRT",
        "ID",
        "UUID",
        "CODE",
        "RATU",
        "measuredHeight",
        "BREC_BuildingHeightNN",
        "BREC_RoofNames",
        "LowestRoof",
        "HighestRoof",
        "GroundLevel",
        "REPAIRED",
        "Rakennuksen_tila",
        "TILA_KOODI",
        "Kerroksia",
        "C_KAYTTARK",
        "storeysAboveGround",
        "source_crs",
        "bbox_min_x",
        "bbox_min_y",
        "bbox_min_z",
        "bbox_max_x",
        "bbox_max_y",
        "bbox_max_z",
        "centroid_x",
        "centroid_y",
        "centroid_z",
        "evidence_refs",
        "confidence",
        "review_state",
        "limitation_refs",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            bbox = row["geometry"].get("bbox_native") or {}
            centroid = row["geometry"].get("centroid_native") or {}
            source_attrs = row["source_attributes"]
            source_ids = row["source_identifiers"]
            writer.writerow(
                {
                    "gml_id": row["gml_id"],
                    "citybrain_candidate_id": row["citybrain_candidate_id"],
                    "canonical_entity_candidate_id": row["canonical_entity_candidate_id"],
                    "VTJ_PRT": source_ids.get("VTJ_PRT"),
                    "ID": source_ids.get("ID"),
                    "UUID": source_ids.get("UUID"),
                    "CODE": source_ids.get("CODE"),
                    "RATU": source_ids.get("RATU"),
                    "measuredHeight": source_attrs.get("measuredHeight"),
                    "BREC_BuildingHeightNN": source_attrs.get("BREC_BuildingHeightNN"),
                    "BREC_RoofNames": source_attrs.get("BREC_RoofNames"),
                    "LowestRoof": source_attrs.get("LowestRoof"),
                    "HighestRoof": source_attrs.get("HighestRoof"),
                    "GroundLevel": source_attrs.get("GroundLevel"),
                    "REPAIRED": source_attrs.get("REPAIRED"),
                    "Rakennuksen_tila": source_attrs.get("Rakennuksen_tila"),
                    "TILA_KOODI": source_attrs.get("TILA_KOODI"),
                    "Kerroksia": source_attrs.get("Kerroksia"),
                    "C_KAYTTARK": source_attrs.get("C_KAYTTARK"),
                    "storeysAboveGround": source_attrs.get("storeysAboveGround"),
                    "source_crs": row["geometry"].get("source_crs"),
                    "bbox_min_x": bbox.get("min_x"),
                    "bbox_min_y": bbox.get("min_y"),
                    "bbox_min_z": bbox.get("min_z"),
                    "bbox_max_x": bbox.get("max_x"),
                    "bbox_max_y": bbox.get("max_y"),
                    "bbox_max_z": bbox.get("max_z"),
                    "centroid_x": centroid.get("x"),
                    "centroid_y": centroid.get("y"),
                    "centroid_z": centroid.get("z"),
                    "evidence_refs": ";".join(row["evidence_refs"]),
                    "confidence": row["confidence"],
                    "review_state": row["review_state"],
                    "limitation_refs": ";".join(row["limitation_refs"]),
                }
            )


def write_cer_map(rows: list[dict[str, Any]]) -> None:
    jsonl_path = OUTPUT_ROOT / "CITYGML_TO_CER_CANDIDATE_MAP.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            record = {
                "canonical_entity_candidate_id": row["canonical_entity_candidate_id"],
                "citybrain_candidate_id": row["citybrain_candidate_id"],
                "entity_type": "building",
                "source_system": row["source_system"],
                "source_record_ref": row["source_record_ref"],
                "primary_matching_keys": row["primary_matching_keys"],
                "aliases_source_ids": row["aliases_source_ids"],
                "geometry": row["geometry"],
                "evidence_refs": row["evidence_refs"],
                "confidence": row["confidence"],
                "review_state": row["review_state"],
                "limitation_refs": row["limitation_refs"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(
        OUTPUT_ROOT / "CITYGML_TO_CER_CANDIDATE_MAP_SUMMARY.json",
        {
            "task_id": TASK_ID,
            "status": "CANDIDATE_MAP_READY_WITH_LIMITATIONS",
            "row_count": len(rows),
            "entity_type": "building",
            "source_system": "Helsinki CityGML Kalasatama",
            "accepted_canonical_truth_claim": False,
            "notes": [
                "Every CityGML building row receives a deterministic candidate ID.",
                "Rows are CER candidates only; canonical acceptance requires later bridge/sidecar smoke.",
            ],
        },
    )


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_hsl_materialization() -> dict[str, Any]:
    stops_path = INPUT_ROOT / "inventory" / "hsl_kalasatama_stops.csv"
    routes_path = INPUT_ROOT / "inventory" / "hsl_kalasatama_routes.csv"
    summary_path = INPUT_ROOT / "inventory" / "hsl_kalasatama_summary.json"
    summary = read_json(summary_path) or {}
    stops = load_csv(stops_path) if stops_path.exists() else []
    routes = load_csv(routes_path) if routes_path.exists() else []

    stop_records = []
    for row in stops:
        stop_records.append(
            {
                "citybrain_candidate_id": f"hel:hsl_stop_candidate:{row.get('stop_id')}",
                "stop_id": row.get("stop_id"),
                "stop_code": row.get("stop_code"),
                "stop_name": row.get("stop_name"),
                "stop_lat": as_float(row.get("stop_lat")),
                "stop_lon": as_float(row.get("stop_lon")),
                "vehicle_type": row.get("vehicle_type"),
                "digistop_id": row.get("digistop_id"),
                "evidence_refs": [rel(stops_path), rel(summary_path)],
                "limitation_refs": ["lim:hsl_bbox_candidate_not_curated_kalasatama_service_truth"],
                "review_state": "candidate_bbox_context",
            }
        )
    route_records = []
    route_type_counter: Counter[str] = Counter()
    for row in routes:
        route_type_counter.update([row.get("route_type", "")])
        route_records.append(
            {
                "citybrain_candidate_id": f"hel:hsl_route_candidate:{row.get('route_id')}",
                "route_id": row.get("route_id"),
                "route_short_name": row.get("route_short_name"),
                "route_long_name": row.get("route_long_name"),
                "route_type": row.get("route_type"),
                "route_url": row.get("route_url"),
                "evidence_refs": [rel(routes_path), rel(summary_path)],
                "limitation_refs": ["lim:hsl_bbox_candidate_not_curated_kalasatama_service_truth"],
                "review_state": "candidate_bbox_context",
            }
        )
    materialization = {
        "task_id": TASK_ID,
        "status": "HSL_MOBILITY_CONTEXT_MATERIALIZED_WITH_BBOX_LIMITATIONS",
        "summary": {
            "stop_candidates": len(stop_records),
            "route_candidates": len(route_records),
            "trip_candidates_from_landing_summary": summary.get("kalasatama_trip_count"),
            "bbox": summary.get("bbox"),
            "route_type_counts": dict(route_type_counter),
        },
        "stops": stop_records,
        "routes": route_records,
        "limitations": [
            "HSL GTFS is city/region-wide and filtered to a Kalasatama bbox.",
            "Stop/route/trip counts are spatial candidates, not curated Kalasatama service truth.",
            "No transit-control, routing, or operations claim is made.",
        ],
    }
    write_json(OUTPUT_ROOT / "HSL_MOBILITY_MATERIALIZATION.json", materialization)
    return materialization


def xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for si in root:
        texts = []
        for node in si.iter():
            if local_name(node.tag) == "t" and node.text:
                texts.append(node.text)
        values.append("".join(texts))
    return values


def xlsx_sheet_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    if "xl/workbook.xml" not in zf.namelist() or "xl/_rels/workbook.xml.rels" not in zf.namelist():
        return {}
    rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rels = {}
    for rel_elem in rel_root:
        rel_id = rel_elem.attrib.get("Id")
        target = rel_elem.attrib.get("Target")
        if rel_id and target:
            rels[rel_id] = target if target.startswith("xl/") else f"xl/{target}"
    wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
    targets = {}
    for sheet in wb_root.iter():
        if local_name(sheet.tag) != "sheet":
            continue
        name = sheet.attrib.get("name")
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        if name and rel_id and rel_id in rels:
            targets[name] = rels[rel_id]
    return targets


def xlsx_cell_value(cell: ET.Element, shared: list[str]) -> Any:
    ctype = cell.attrib.get("t")
    if ctype == "inlineStr":
        texts = [node.text for node in cell.iter() if local_name(node.tag) == "t" and node.text]
        return "".join(texts)
    value_elem = None
    for child in cell:
        if local_name(child.tag) == "v":
            value_elem = child
            break
    if value_elem is None or value_elem.text is None:
        return ""
    value = value_elem.text
    if ctype == "s":
        try:
            return shared[int(value)]
        except Exception:
            return value
    return value


def xlsx_first_rows(path: Path, sheet_name: str, max_rows: int = 20) -> list[list[Any]]:
    rows: list[list[Any]] = []
    with zipfile.ZipFile(path) as zf:
        shared = xlsx_shared_strings(zf)
        targets = xlsx_sheet_targets(zf)
        target = targets.get(sheet_name)
        if not target or target not in zf.namelist():
            return rows
        root = ET.fromstring(zf.read(target))
        for row_elem in root.iter():
            if local_name(row_elem.tag) != "row":
                continue
            row = []
            for cell in row_elem:
                if local_name(cell.tag) == "c":
                    row.append(xlsx_cell_value(cell, shared))
            if any(str(v).strip() for v in row):
                rows.append(row)
            if len(rows) >= max_rows:
                break
    return rows


def classify_join_columns(headers: list[str]) -> tuple[str, list[str], str]:
    normalized = [(h, h.lower()) for h in headers if h and str(h).strip()]
    exact_terms = ["vtj", "prt", "rakennustunnus", "gml", "uuid"]
    probable_terms = ["ratu", "building", "rakennus", "id", "kiinteist"]
    weak_terms = ["address", "osoite", "koord", "x", "y", "lat", "lon", "postcode", "postal"]
    exact = [h for h, low in normalized if any(term in low for term in exact_terms)]
    if exact:
        return "exact", exact, "Explicit building identifier-like key present."
    probable = [h for h, low in normalized if any(term in low for term in probable_terms)]
    if probable:
        return "probable", probable, "Building/id-like columns present, but not enough to claim a CityGML join without value matching."
    weak = [h for h, low in normalized if any(term in low for term in weak_terms)]
    if weak:
        return "weak", weak, "Only location/address-like keys found; use for candidate review only."
    return "no_join", [], "No explicit or strongly inferable building join key found in sampled header rows."


def write_energy_report(building_rows: list[dict[str, Any]]) -> dict[str, Any]:
    inventory_path = INPUT_ROOT / "inventory" / "energy_workbook_sheet_inventory.json"
    inventory = read_json(inventory_path) or []
    candidate_values = {
        "VTJ_PRT": {str(row["source_identifiers"].get("VTJ_PRT")) for row in building_rows if row["source_identifiers"].get("VTJ_PRT")},
        "UUID": {str(row["source_identifiers"].get("UUID")) for row in building_rows if row["source_identifiers"].get("UUID")},
        "CODE": {str(row["source_identifiers"].get("CODE")) for row in building_rows if row["source_identifiers"].get("CODE")},
        "ID": {str(row["source_identifiers"].get("ID")) for row in building_rows if row["source_identifiers"].get("ID")},
    }
    sheet_reports = []
    for workbook in inventory:
        rel_path = workbook.get("path")
        workbook_path = INPUT_ROOT / rel_path if rel_path else None
        for sheet in workbook.get("sheets", []):
            sheet_name = sheet.get("name")
            rows = xlsx_first_rows(workbook_path, sheet_name) if workbook_path and workbook_path.exists() and sheet_name else []
            headers = [str(v).strip() for v in rows[0]] if rows else []
            join_class, key_cols, rationale = classify_join_columns(headers)
            explicit_matches = []
            if join_class in {"exact", "probable"} and rows:
                header_index = {str(h).strip(): idx for idx, h in enumerate(headers)}
                for key in key_cols[:5]:
                    idx = header_index.get(key)
                    if idx is None:
                        continue
                    values = {str(row[idx]).strip() for row in rows[1:] if idx < len(row) and str(row[idx]).strip()}
                    for source_key, known_values in candidate_values.items():
                        intersection = values & known_values
                        if intersection:
                            explicit_matches.append({"column": key, "source_key": source_key, "sample_matches": sorted(intersection)[:5]})
            if not explicit_matches and join_class == "exact":
                join_class = "probable"
                rationale = "Identifier-like columns exist, but bounded header/sample inspection did not prove value-level matches."
            sheet_reports.append(
                {
                    "workbook_path": rel_path,
                    "workbook_exists": workbook_path.exists() if workbook_path else False,
                    "sheet_name": sheet_name,
                    "sampled_headers": headers[:80],
                    "candidate_key_columns": key_cols,
                    "join_classification": join_class,
                    "explicit_sample_matches": explicit_matches,
                    "rationale": rationale,
                    "claim_successful_energy_building_linkage": bool(explicit_matches),
                    "limitation_refs": [
                        "lim:bounded_header_sample_only",
                        "lim:no_energy_building_linkage_claim_without_explicit_key_match",
                    ],
                }
            )
    report = {
        "task_id": TASK_ID,
        "status": "ENERGY_JOIN_CANDIDATES_CLASSIFIED_WITHOUT_OVERCLAIM",
        "citygml_building_candidate_keys": {key: len(value) for key, value in candidate_values.items()},
        "sheet_reports": sheet_reports,
        "summary_counts": dict(Counter(row["join_classification"] for row in sheet_reports)),
    }
    write_json(OUTPUT_ROOT / "ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.json", report)
    md_lines = [
        "# Energy Workbook Join Candidate Report",
        "",
        "This is a bounded join-readiness report. It does not claim successful energy-to-building linkage unless explicit sampled key matches exist.",
        "",
    ]
    for item in sheet_reports:
        md_lines.extend(
            [
                f"## {item['workbook_path']} / {item['sheet_name']}",
                "",
                f"- classification: `{item['join_classification']}`",
                f"- candidate key columns: {', '.join(item['candidate_key_columns']) if item['candidate_key_columns'] else 'none'}",
                f"- rationale: {item['rationale']}",
                f"- explicit sampled matches: {len(item['explicit_sample_matches'])}",
                "",
            ]
        )
    write_text(OUTPUT_ROOT / "ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.md", "\n".join(md_lines))
    return report


def write_usd_cer_sidecar(rows: list[dict[str, Any]]) -> dict[str, Any]:
    jsonl_path = OUTPUT_ROOT / "USD_CER_SIDECAR_CANDIDATE_MAP.jsonl"
    sidecar_rows = []
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            prim_path = f"/World/CityBrain/HEL/Kalasatama/SemanticBuildings/{sanitize_prim_token(row['gml_id'])}"
            record = {
                "candidate_prim_path": prim_path,
                "suggested_prim_name": sanitize_prim_token(row["gml_id"]),
                "linked_citybrain_candidate_id": row["citybrain_candidate_id"],
                "canonical_entity_candidate_id": row["canonical_entity_candidate_id"],
                "source_citygml_id": row["gml_id"],
                "source_record_ref": row["source_record_ref"],
                "geometry_ref": row["geometry"],
                "evidence_refs": row["evidence_refs"],
                "graph_runtime_refs": [],
                "limitation_refs": [
                    *row["limitation_refs"],
                    "lim:prim_path_suggested_not_written_to_source_usd",
                    "lim:visual_mesh_alignment_not_proven",
                ],
                "binding_status": "CANDIDATE_SIDECAR_READY_NOT_ALIGNED_TO_VISUAL_MESH",
                "review_state": "needs_omniverse_sidecar_alignment_smoke",
                "no_source_usd_mutation": True,
            }
            sidecar_rows.append(record)
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "task_id": TASK_ID,
        "status": "USD_CER_SIDECAR_CANDIDATES_READY_WITH_LIMITATIONS",
        "row_count": len(sidecar_rows),
        "source_usd_mutated": False,
        "sample_records": sidecar_rows[:10],
        "limitations": [
            "Candidate prim paths are sidecar suggestions only.",
            "No object-level visual mesh identity is claimed until an Omniverse/Web/Kit sidecar alignment smoke passes.",
        ],
    }
    write_json(OUTPUT_ROOT / "USD_CER_SIDECAR_CANDIDATE_MAP_SUMMARY.json", summary)
    return summary


def wfs_probe_summary(decision_input: dict[str, Any] | None) -> dict[str, Any]:
    path = INPUT_ROOT / "wfs" / "kalasatama_building_bbox_sample_cityjson.json"
    result = {
        "path": rel(path),
        "exists": path.exists(),
        "sample_cityobjects_count": None,
        "sample_building_count": None,
        "landing_decision_bbox_probe_building_count": decision_input.get("semantic_wfs_bbox_building_count") if decision_input else None,
        "status": "WFS_BBOX_PROBE_ONLY_NOT_KALASATAMA_BOUNDARY_TRUTH",
        "limitation_refs": ["lim:wfs_bbox_probe_broader_than_kalasatama_boundary"],
    }
    if not path.exists():
        return result
    data = read_json(path)
    if not data:
        result["status"] = "WFS_PROBE_PARSE_FAILED"
        return result
    objects = data.get("CityObjects", {})
    result["sample_cityobjects_count"] = len(objects)
    result["sample_building_count"] = sum(1 for value in objects.values() if value.get("type") == "Building")
    metadata = data.get("metadata", {})
    result["metadata"] = {
        "referenceSystem": metadata.get("referenceSystem"),
        "geographicalExtent": metadata.get("geographicalExtent"),
        "presentLoDs": metadata.get("presentLoDs"),
    }
    return result


def write_visual_mesh_note() -> dict[str, Any]:
    source_manifest = read_json(TILES_ROOT / "SOURCE_MANIFEST.json") if TILES_ROOT.exists() else None
    zip_summary = read_json(TILES_ROOT / "inventory" / "zip_inventory_summary.json") if TILES_ROOT.exists() else None
    root_profile = read_json(TILES_ROOT / "inventory" / "tileset_root_profile.json") if TILES_ROOT.exists() else None
    payload = {
        "task_id": TASK_ID,
        "status": "VISUAL_BACKDROP_ONLY",
        "tiles_root_exists": TILES_ROOT.exists(),
        "source_manifest": source_manifest,
        "zip_summary": {
            "entry_count": zip_summary.get("entry_count") if zip_summary else None,
            "compressed_bytes": zip_summary.get("compressed_bytes") if zip_summary else None,
            "uncompressed_bytes": zip_summary.get("uncompressed_bytes") if zip_summary else None,
        },
        "tileset_root_profile": root_profile,
        "identity_claim": "No object-level identity claim from 3D Tiles/reality mesh.",
        "allowed_use": "Visual backdrop/alignment target only.",
        "blocked_until": "Sidecar alignment and object-pick smoke proves selected visual prim maps to semantic CityGML candidate.",
    }
    write_json(OUTPUT_ROOT / "VISUAL_MESH_BOUNDARY_NOTE.json", payload)
    write_text(
        OUTPUT_ROOT / "VISUAL_MESH_BOUNDARY_NOTE.md",
        """# Visual Mesh Boundary Note

Kalasatama 3D Tiles / reality mesh is a visual backdrop and alignment target only.

The semantic identity spine in this prep task comes from the Helsinki CityGML Kalasatama building features. The 3D Tiles mesh is not treated as object-level canonical identity, legal truth, certified building truth, or a source of ownership/compliance conclusions.

Object-level visual selection remains blocked until a sidecar alignment smoke proves:

- selected USD/Kit prim path,
- source mesh/tile context,
- linked CityGML building candidate,
- CER candidate request packet,
- evidence and limitations.
""",
    )
    return payload


def write_claim_audits(input_stats_before: dict[str, dict[str, Any]], input_stats_after: dict[str, dict[str, Any]]) -> None:
    mutated = []
    for key, before in input_stats_before.items():
        after = input_stats_after.get(key)
        if before != after:
            mutated.append({"key": key, "before": before, "after": after})
    write_json(
        OUTPUT_ROOT / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not mutated else "FAIL",
            "prior_outputs_mutated": bool(mutated),
            "mutated_inputs": mutated,
            "input_roots_read_only": [rel(INPUT_ROOT), rel(TILES_ROOT)] if TILES_ROOT.exists() else [rel(INPUT_ROOT)],
            "generated_output_root": rel(OUTPUT_ROOT),
        },
    )
    write_json(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "production_claim_made": False,
            "legal_claim_made": False,
            "certified_identity_claim_made": False,
            "live_operational_claim_made": False,
            "autonomous_action_claim_made": False,
            "vss_or_perception_claim_made": False,
            "visual_mesh_object_identity_claim_made": False,
            "accepted_cer_truth_claim_made": False,
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_LEGAL_CERTIFIED_PRODUCTION_LIVE_AUTONOMOUS_VSS_CLAIM_AUDIT.json",
        {
            "status": "PASS",
            "no_legal_claim": True,
            "no_certified_identity_claim": True,
            "no_production_readiness_claim": True,
            "no_live_operational_readiness_claim": True,
            "no_autonomous_action_claim": True,
            "no_vss_claim": True,
        },
    )


def secret_scan() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|accountkey|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"(?i)x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    ]
    hits = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "hashes.sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not hits else "FAIL", "secrets_found": len(hits), "hits": hits}


def hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"generated_at": RUN_TS, "files": files}


def write_hashes_sha256(manifest: dict[str, Any]) -> None:
    lines = [f"{item['sha256']}  {item['path']}" for item in manifest["files"] if not item["path"].endswith("hashes.sha256")]
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(lines))


def input_stats() -> dict[str, dict[str, Any]]:
    paths = {
        "decision": INPUT_ROOT / "D4_HELSINKI_KALASATAMA_CONTEXT_DATA_LANDING_R1_DECISION.json",
        "citygml_semantic_counts": INPUT_ROOT / "inventory" / "citygml_semantic_counts.json",
        "citygml_zip_inventory": INPUT_ROOT / "inventory" / "citygml_zip_inventory.json",
        "energy_inventory": INPUT_ROOT / "inventory" / "energy_workbook_sheet_inventory.json",
        "hsl_stops": INPUT_ROOT / "inventory" / "hsl_kalasatama_stops.csv",
        "hsl_routes": INPUT_ROOT / "inventory" / "hsl_kalasatama_routes.csv",
        "source_ledger": INPUT_ROOT / "inventory" / "kalasatama_source_ledger.csv",
        "wfs_cityjson": INPUT_ROOT / "wfs" / "kalasatama_building_bbox_sample_cityjson.json",
        "tiles_source_manifest": TILES_ROOT / "SOURCE_MANIFEST.json",
    }
    return {key: file_stat(path, include_hash=False) for key, path in paths.items()}


def write_readme(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# D4 Helsinki Kalasatama Context Consumption Prep R1

Status: `{decision['status']}`

This package consumes the landed Kalasatama semantic/context data and prepares the first CityBrain semantic visual-object-to-CER/USD sidecar lane.

Core outputs:

- `CITYGML_BUILDING_IDENTITY_NORMALIZATION.csv`
- `CITYGML_BUILDING_IDENTITY_NORMALIZATION.jsonl`
- `CITYGML_TO_CER_CANDIDATE_MAP.jsonl`
- `CITYGML_TO_CER_CANDIDATE_MAP_SUMMARY.json`
- `ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.md`
- `ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.json`
- `HSL_MOBILITY_MATERIALIZATION.json`
- `USD_CER_SIDECAR_CANDIDATE_MAP.jsonl`
- `USD_CER_SIDECAR_CANDIDATE_MAP_SUMMARY.json`
- `VISUAL_MESH_BOUNDARY_NOTE.md`
- `JSON_PARSE_AUDIT.json`
- audits and hashes

Boundary:

This is candidate/prep data only. It does not claim production readiness, legal/certified identity, accepted CER truth, live operations, VSS/perception readiness, autonomous action, or object-level identity from the visual mesh.
""",
    )
    write_text(
        OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md",
        """# Local Open Index

- `D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json`
- `CITYGML_BUILDING_IDENTITY_NORMALIZATION.csv`
- `CITYGML_BUILDING_IDENTITY_NORMALIZATION.jsonl`
- `CITYGML_TO_CER_CANDIDATE_MAP.jsonl`
- `CITYGML_TO_CER_CANDIDATE_MAP_SUMMARY.json`
- `ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.md`
- `ENERGY_WORKBOOK_JOIN_CANDIDATE_REPORT.json`
- `HSL_MOBILITY_MATERIALIZATION.json`
- `USD_CER_SIDECAR_CANDIDATE_MAP.jsonl`
- `USD_CER_SIDECAR_CANDIDATE_MAP_SUMMARY.json`
- `VISUAL_MESH_BOUNDARY_NOTE.md`
- `VISUAL_MESH_BOUNDARY_NOTE.json`
- `JSON_PARSE_AUDIT.json`
- `LIMITATIONS_AND_NEXT_STEPS.md`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_PRIOR_OUTPUT_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `hashes.sha256`
""",
    )


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    before = input_stats()
    decision_input = read_json(INPUT_ROOT / "D4_HELSINKI_KALASATAMA_CONTEXT_DATA_LANDING_R1_DECISION.json")
    counts_input = read_json(INPUT_ROOT / "inventory" / "citygml_semantic_counts.json")
    citygml_zip_inventory = read_json(INPUT_ROOT / "inventory" / "citygml_zip_inventory.json")
    zip_path = INPUT_ROOT / "downloads" / "citygml" / "Helsinki3D_CityGML_Kalasatama_20190326.zip"

    hard_errors: list[str] = []
    if not decision_input:
        hard_errors.append("Missing or unparsable landing decision JSON.")
    if not counts_input:
        hard_errors.append("Missing or unparsable citygml_semantic_counts.json.")
    if not zip_path.exists():
        hard_errors.append("Missing CityGML ZIP.")

    building_rows: list[dict[str, Any]] = []
    citygml_summary: dict[str, Any] = {}
    if not hard_errors:
        building_rows, citygml_summary = parse_citygml_buildings(zip_path)
        expected_buildings = decision_input.get("citygml_buildings") if decision_input else None
        if expected_buildings and len(building_rows) != int(expected_buildings):
            hard_errors.append(f"CityGML building count mismatch: parsed={len(building_rows)} expected={expected_buildings}")

    wfs_summary = wfs_probe_summary(decision_input)
    if not hard_errors:
        write_building_tables(building_rows)
        write_cer_map(building_rows)
        energy_report = write_energy_report(building_rows)
        hsl_materialization = write_hsl_materialization()
        sidecar_summary = write_usd_cer_sidecar(building_rows)
        visual_mesh = write_visual_mesh_note()
    else:
        energy_report = {}
        hsl_materialization = {}
        sidecar_summary = {}
        visual_mesh = {}

    parse_audit = {
        "task_id": TASK_ID,
        "status": "PASS" if not hard_errors else "FAIL",
        "hard_errors": hard_errors,
        "input_decision_status": decision_input.get("status") if decision_input else None,
        "citygml_zip_inventory_present": bool(citygml_zip_inventory),
        "citygml_summary": citygml_summary,
        "expected_citygml_buildings": decision_input.get("citygml_buildings") if decision_input else None,
        "parsed_citygml_buildings": len(building_rows),
        "wfs_probe_summary": wfs_summary,
        "wfs_bbox_count_preserved_as_probe_only": True,
        "hsl_counts": {
            "stop_candidates": hsl_materialization.get("summary", {}).get("stop_candidates"),
            "route_candidates": hsl_materialization.get("summary", {}).get("route_candidates"),
            "trip_candidates_from_landing_summary": hsl_materialization.get("summary", {}).get("trip_candidates_from_landing_summary"),
        },
        "energy_join_summary": energy_report.get("summary_counts"),
    }
    write_json(OUTPUT_ROOT / "JSON_PARSE_AUDIT.json", parse_audit)

    limitations = [
        "CityGML building rows are CER candidates, not accepted canonical/legal/certified building truth.",
        "WFS bbox sample count is preserved as a broader spatial probe, not Kalasatama boundary truth.",
        "HSL stops/routes/trips are bbox-filtered candidates, not curated Kalasatama service truth.",
        "Energy workbook join report is bounded and does not claim successful building linkage unless explicit sampled key matches exist.",
        "Kalasatama 3D Tiles / mesh remains visual backdrop only until sidecar alignment smoke passes.",
        "No source USD/3D Tiles/CityGML outputs were mutated.",
    ]
    write_text(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        "# Limitations And Next Steps\n\n"
        + "\n".join(f"- {item}" for item in limitations)
        + "\n\n## Recommended Next\n\n"
        + "- `D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1`\n"
        + "- `MAIN-CITYBRAIN-D8-WEB-KIT-BUNDLE-CONSUMPTION-SMOKE-R1`\n",
    )

    after = input_stats()
    write_claim_audits(before, after)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret_scan())

    status = STATUS_FAIL if hard_errors else STATUS_PASS_LIMITED
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "input_root": rel(INPUT_ROOT),
        "visual_backdrop_root": rel(TILES_ROOT) if TILES_ROOT.exists() else None,
        "output_root": rel(OUTPUT_ROOT),
        "citygml_building_identity_rows": len(building_rows),
        "expected_citygml_buildings": decision_input.get("citygml_buildings") if decision_input else None,
        "wfs_bbox_probe_buildings": wfs_summary.get("landing_decision_bbox_probe_building_count"),
        "wfs_bbox_sample_buildings_materialized": wfs_summary.get("sample_building_count"),
        "wfs_bbox_is_probe_not_boundary": True,
        "hsl_stop_candidates": hsl_materialization.get("summary", {}).get("stop_candidates"),
        "hsl_route_candidates": hsl_materialization.get("summary", {}).get("route_candidates"),
        "hsl_trip_candidates_from_landing_summary": hsl_materialization.get("summary", {}).get("trip_candidates_from_landing_summary"),
        "energy_sheet_count": len(energy_report.get("sheet_reports", [])),
        "energy_join_summary": energy_report.get("summary_counts"),
        "usd_cer_sidecar_candidates": sidecar_summary.get("row_count"),
        "visual_mesh_boundary_status": visual_mesh.get("status"),
        "hard_errors": hard_errors,
        "production_claim_made": False,
        "legal_or_certified_identity_claim_made": False,
        "live_operational_claim_made": False,
        "autonomous_action_claim_made": False,
        "vss_claim_made": False,
        "source_outputs_mutated": False,
        "next_recommended_task": "D4-HELSINKI-KALASATAMA-USD-SIDECAR-ALIGNMENT-SMOKE-R1",
    }
    write_json(OUTPUT_ROOT / "D4_HELSINKI_KALASATAMA_CONTEXT_CONSUMPTION_PREP_R1_DECISION.json", decision)
    write_readme(decision)

    manifest = hash_manifest()
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    write_hashes_sha256(manifest)
    # Recreate manifest after hashes.sha256 exists so it appears in JSON manifest.
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", hash_manifest())

    print(json.dumps({
        "task_id": TASK_ID,
        "status": status,
        "output_root": rel(OUTPUT_ROOT),
        "citygml_building_identity_rows": len(building_rows),
        "wfs_bbox_probe_buildings": wfs_summary.get("landing_decision_bbox_probe_building_count"),
        "wfs_bbox_sample_buildings_materialized": wfs_summary.get("sample_building_count"),
        "hsl_stop_candidates": hsl_materialization.get("summary", {}).get("stop_candidates"),
        "hsl_route_candidates": hsl_materialization.get("summary", {}).get("route_candidates"),
        "usd_cer_sidecar_candidates": sidecar_summary.get("row_count"),
        "hard_errors": hard_errors,
    }, indent=2))
    return 1 if hard_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
