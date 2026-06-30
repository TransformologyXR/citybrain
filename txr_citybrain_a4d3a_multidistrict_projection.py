from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_a4_graph_gate import DistrictManifest, project_canonical, run_a4_gate
from txr_citybrain_dob_complaint_categories import map_dob_complaint
from txr_citybrain_harness import GateResult, HarnessReport
from txr_citybrain_schema_v1 import Relation


ROOT = Path(__file__).resolve().parent
DEFAULT_STAGING_DIR = ROOT / "data" / "processed" / "nyc" / "harvest_v0_2" / "discovery_staging"
DEFAULT_DEDUPED_DIR = ROOT / "data" / "processed" / "nyc" / "harvest_v0_2" / "deduped_tables"
DEFAULT_DISCOVERY_DIR = ROOT / "outputs" / "a4d2b_district_discovery"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a4d3a_multidistrict_projection"
BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped "
    "depending on local harvest status. Discovery and projection counts are not claims about "
    "complete NYC history unless the dataset is marked full in the inventory."
)

DISTRICTS = {
    "1-01060": {
        "district_id": "1-01060",
        "district_name": "MN Block 1060 certified seed / regression baseline",
        "district_role": "certified_seed_regression_baseline",
        "boundary": "Borough 1 tax block 01060 from NYC Harvest Prep v0.2 staging.",
    },
    "1-01158": {
        "district_id": "1-01158",
        "district_name": "MN Block 1158 volume stress test",
        "district_role": "volume_stress_test",
        "boundary": "Borough 1 tax block 01158 from NYC Harvest Prep v0.2 staging.",
    },
    "2-02316": {
        "district_id": "2-02316",
        "district_name": "BX Block 2316 structural shape stress test",
        "district_role": "structural_shape_stress_test",
        "boundary": "Borough 2 tax block 02316 from NYC Harvest Prep v0.2 staging.",
    },
}

HERO_IDS = {
    "parcel": "parcel:us-nyc:bbl:1010607502",
    "building": "building:us-nyc:bin:1026676",
    "permit": "permit:us-nyc:dob_job:121912591",
    "complaint": "event:us-nyc:dob_complaint:1366080",
    "contractor": "party:us-nyc:dob_license:GC-0037441",
}

ALLOWED_ENTITY_TYPES = {"parcel", "building", "permit", "event", "party"}
ALLOWED_RELATIONS = {
    "has_building",
    "subject_of_permit",
    "resolves_to",
    "performed_by",
    "designed_by",
    "involves_party",
    "near",
    "affects",
}
COMPLAINT_METHODS = {"exact_bin", "address_fallback", "spatial_fallback"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def norm_upper(value: Any) -> str:
    return " ".join(clean(value).upper().split())


def stable_name_hash(name: str) -> str:
    return hashlib.sha1(norm_upper(name).encode("utf-8")).hexdigest()[:12]


def license_native(license_type: Any, license_id: Any) -> str:
    ltype = norm_upper(license_type).replace(".", "").replace(" ", "")
    lid = clean(license_id)
    if not lid:
        return ""
    digits = "".join(ch for ch in lid if ch.isdigit())
    normalized_id = digits.zfill(len(lid)) if digits else lid.upper()
    if ltype:
        return f"{ltype}-{normalized_id}"
    return normalized_id


def canonical_id(entity_type: str, id_system: str, native_id: str) -> str:
    return f"{entity_type}:us-nyc:{id_system}:{native_id}"


def confidence(score: float, method: str, basis: str) -> dict[str, Any]:
    return {"score": float(score), "method": method, "basis": basis}


def provenance(dataset: str, row_key: str, fields: list[str], derivation: str | None = None) -> dict[str, Any]:
    return {
        "source_dataset": dataset,
        "source_id": row_key,
        "domain": "dm" if "dob" in dataset else "land",
        "source_fields": fields,
        "observed_at": None,
        "derivation": derivation,
        "ingest_run_id": None,
    }


def source_ref(dataset: str, row_key: str, fields: list[str], method: str, basis: str) -> dict[str, Any]:
    return {
        "source_dataset": dataset,
        "source_row_key": row_key,
        "source_fields": fields,
        "resolution_method": method,
        "confidence_method": method,
        "basis": basis,
    }


def point_from_row(row: dict[str, Any]) -> list[float]:
    lon = clean(row.get("longitude"))
    lat = clean(row.get("latitude"))
    try:
        lon_f = float(lon)
        lat_f = float(lat)
        if -180 <= lon_f <= 180 and -90 <= lat_f <= 90:
            return [lon_f, lat_f]
    except ValueError:
        pass
    return [-73.990134, 40.7643741]


def point_geometry(point: list[float]) -> dict[str, Any]:
    return {"type": "Point", "coordinates": point, "point": point, "crs": "EPSG:4326"}


def parse_timestamp(value: Any) -> str:
    parsed = pd.to_datetime(clean(value), errors="coerce")
    if pd.isna(parsed):
        return "1970-01-01T00:00:00"
    return parsed.to_pydatetime().replace(tzinfo=None).isoformat()


def json_blob(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def read_block_table(staging_dir: Path, filename: str, block_key: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(staging_dir / filename, columns=columns, filters=[("block_key", "==", block_key)])


def read_raw_lookup(deduped_dir: Path, dataset: str, key_col: str, keys: set[str], columns: list[str]) -> dict[str, dict[str, Any]]:
    if not keys:
        return {}
    source = deduped_dir / dataset
    if not source.exists():
        return {}
    try:
        df = pd.read_parquet(source, columns=columns, filters=[(key_col, "in", sorted(keys))])
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in df.fillna("").to_dict("records"):
        key = clean(row.get(key_col))
        if key and key not in out:
            out[key] = row
    return out


def load_raw_party_lookups(deduped_dir: Path, permit_rows: pd.DataFrame, now_rows: pd.DataFrame) -> dict[str, dict[str, dict[str, Any]]]:
    permit_keys = {clean(v) for v in permit_rows.get("source_row_key", pd.Series(dtype=str)).tolist() if clean(v)}
    now_keys = {clean(v) for v in now_rows.get("source_row_key", pd.Series(dtype=str)).tolist() if clean(v)}
    permit_lookup = read_raw_lookup(
        deduped_dir,
        "nyc__dob_permit_issuance",
        "permit_si_no",
        permit_keys,
        [
            "permit_si_no",
            "permittee_s_first_name",
            "permittee_s_last_name",
            "permittee_s_business_name",
            "permittee_s_license_type",
            "permittee_s_license__",
            "owner_s_business_name",
            "owner_s_first_name",
            "owner_s_last_name",
        ],
    )
    now_lookup = read_raw_lookup(
        deduped_dir,
        "nyc__dob_now_build_job_application_filings",
        "job_filing_number",
        now_keys,
        [
            "job_filing_number",
            "applicant_professional_title",
            "applicant_license",
            "applicant_first_name",
            "applicant_last_name",
            "filing_representative_first_name",
            "filing_representative_last_name",
            "filing_representative_business_name",
            "owner_s_business_name",
            "owner_first_name",
            "owner_last_name",
        ],
    )
    return {"dob_permit_issuance": permit_lookup, "dob_now_build_job_application_filings": now_lookup}


def add_entity(entity_by_id: dict[str, dict[str, Any]], entity: dict[str, Any]) -> None:
    cid = entity["canonical_id"]
    if cid not in entity_by_id:
        entity_by_id[cid] = entity
        return
    target = entity_by_id[cid]
    existing_prov = {(p.get("source_dataset"), p.get("source_id")) for p in target.get("provenance", [])}
    for prov in entity.get("provenance", []):
        key = (prov.get("source_dataset"), prov.get("source_id"))
        if key not in existing_prov:
            target.setdefault("provenance", []).append(prov)
            existing_prov.add(key)
    existing_refs = {
        (r.get("source_dataset"), r.get("source_row_key"))
        for r in (target.get("ext") or {}).get("source_refs", [])
    }
    for ref in (entity.get("ext") or {}).get("source_refs", []):
        key = (ref.get("source_dataset"), ref.get("source_row_key"))
        if key not in existing_refs:
            target.setdefault("ext", {}).setdefault("source_refs", []).append(ref)
            existing_refs.add(key)


def edge_key(edge: dict[str, Any]) -> tuple[str, str, str, str]:
    return (edge["src_ref"], edge["dst_ref"], edge["relation"], edge.get("role") or "")


def add_edge(edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]], edge: dict[str, Any]) -> None:
    key = edge_key(edge)
    if key not in edge_by_key:
        edge_by_key[key] = edge
        return
    target = edge_by_key[key]
    existing_prov = {(p.get("source_dataset"), p.get("source_id")) for p in target.get("provenance", [])}
    for prov in edge.get("provenance", []):
        key2 = (prov.get("source_dataset"), prov.get("source_id"))
        if key2 not in existing_prov:
            target.setdefault("provenance", []).append(prov)
            existing_prov.add(key2)
    if edge.get("confidence") and not target.get("confidence"):
        target["confidence"] = edge["confidence"]


def build_parcel(row: dict[str, Any]) -> dict[str, Any]:
    bbl = clean(row.get("bbl_norm"))
    point = point_from_row(row)
    fields = ["bbl_norm", "block_key", "address", "land_use", "zoning", "latitude", "longitude"]
    return {
        "canonical_id": canonical_id("parcel", "bbl", bbl),
        "entity_type": "parcel",
        "status": "active",
        "provenance": [provenance("mappluto_harvest_v0_2_parcel_lookup", bbl, fields)],
        "confidence": confidence(1.0, "exact_key", f"parcel BBL {bbl} from MapPLUTO lookup"),
        "geometry": point_geometry(point),
        "ext": {
            "block_key": row.get("block_key"),
            "source_refs": [source_ref("mappluto_harvest_v0_2_parcel_lookup", bbl, fields, "exact_key", f"parcel BBL {bbl}")],
        },
        "land_use": clean(row.get("land_use")) or None,
        "zoning": [z for z in clean(row.get("zoning")).split("|") if z],
        "lot_area_sqft": None,
        "address": clean(row.get("address")) or None,
        "development_ref": None,
    }


def building_entity(bin_value: str, bbl: str, point: list[float], dataset: str, row_key: str, fields: list[str]) -> dict[str, Any]:
    return {
        "canonical_id": canonical_id("building", "bin", bin_value),
        "entity_type": "building",
        "status": "active",
        "provenance": [provenance(dataset, row_key, fields, f"BIN {bin_value} associated with BBL {bbl}")],
        "confidence": confidence(0.95, "exact_key", f"DOB BIN exact; parcel linked by BBL {bbl}"),
        "geometry": point_geometry(point),
        "ext": {
            "source_refs": [source_ref(dataset, row_key, fields, "exact_key", f"building BIN {bin_value}")],
            "bbl": bbl,
        },
        "parcel_ref": canonical_id("parcel", "bbl", bbl),
        "building_class": None,
        "num_floors": None,
        "year_built": None,
        "units_residential": None,
        "units_total": None,
        "height_ft": None,
        "development_ref": None,
    }


def ensure_building(
    bin_value: str,
    bbl: str,
    parcel_by_bbl: dict[str, dict[str, Any]],
    entity_by_id: dict[str, dict[str, Any]],
    edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]],
    dataset: str,
    row_key: str,
    fields: list[str],
) -> str | None:
    if not bin_value or bin_value == "0" or not bbl or bbl not in parcel_by_bbl:
        return None
    parcel_id = canonical_id("parcel", "bbl", bbl)
    point = (parcel_by_bbl[bbl].get("geometry") or {}).get("point") or [-73.990134, 40.7643741]
    bid = canonical_id("building", "bin", bin_value)
    add_entity(entity_by_id, building_entity(bin_value, bbl, point, dataset, row_key, fields))
    add_edge(
        edge_by_key,
        {
            "src_ref": parcel_id,
            "dst_ref": bid,
            "relation": "has_building",
            "role": None,
            "provenance": [provenance(dataset, row_key, fields, f"BIN {bin_value} attached to parcel BBL {bbl}")],
            "confidence": confidence(1.0, "exact_key", f"parcel BBL {bbl} has DOB/MapPLUTO building BIN {bin_value}"),
        },
    )
    return bid


def party_candidates(row: dict[str, Any], raw: dict[str, Any] | None) -> list[dict[str, Any]]:
    dataset = clean(row.get("source_dataset"))
    candidates: list[dict[str, Any]] = []
    raw = raw or {}
    if dataset == "nyc__dob_permit_issuance":
        name = clean(raw.get("permittee_s_business_name")) or " ".join(
            part for part in [clean(raw.get("permittee_s_first_name")), clean(raw.get("permittee_s_last_name"))] if part
        ) or clean(row.get("business_name_norm"))
        candidates.append(
            {
                "relation": "performed_by",
                "role": "contractor",
                "name": name,
                "license_type": clean(raw.get("permittee_s_license_type")),
                "license_id": clean(raw.get("permittee_s_license__")) or clean(row.get("license_number_norm")),
            }
        )
        owner = clean(raw.get("owner_s_business_name")) or " ".join(
            part for part in [clean(raw.get("owner_s_first_name")), clean(raw.get("owner_s_last_name"))] if part
        )
        if owner:
            candidates.append({"relation": "involves_party", "role": "owner", "name": owner, "license_type": "", "license_id": ""})
    else:
        applicant = " ".join(part for part in [clean(raw.get("applicant_first_name")), clean(raw.get("applicant_last_name"))] if part)
        candidates.append(
            {
                "relation": "designed_by",
                "role": "applicant",
                "name": applicant or clean(row.get("business_name_norm")),
                "license_type": clean(raw.get("applicant_professional_title")),
                "license_id": clean(raw.get("applicant_license")) or clean(row.get("license_number_norm")),
            }
        )
        filing_rep = clean(raw.get("filing_representative_business_name")) or " ".join(
            part
            for part in [clean(raw.get("filing_representative_first_name")), clean(raw.get("filing_representative_last_name"))]
            if part
        )
        if filing_rep:
            candidates.append(
                {"relation": "involves_party", "role": "filing_representative", "name": filing_rep, "license_type": "", "license_id": ""}
            )
        owner = clean(raw.get("owner_s_business_name")) or " ".join(
            part for part in [clean(raw.get("owner_first_name")), clean(raw.get("owner_last_name"))] if part
        )
        if owner:
            candidates.append({"relation": "involves_party", "role": "owner", "name": owner, "license_type": "", "license_id": ""})
    return candidates


def add_party_and_edge(
    entity_by_id: dict[str, dict[str, Any]],
    edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]],
    permit_id: str,
    row: dict[str, Any],
    raw: dict[str, Any] | None,
) -> None:
    dataset = clean(row.get("source_dataset"))
    row_key = clean(row.get("source_row_key"))
    fields = ["source_row_key", "job_number_norm", "license_number_norm", "business_name_norm"]
    for candidate in party_candidates(row, raw):
        name = " ".join(clean(candidate.get("name")).split())
        native_license = license_native(candidate.get("license_type"), candidate.get("license_id"))
        if native_license:
            party_id = canonical_id("party", "dob_license", native_license)
            conf = confidence(0.95, "license_number", f"license_number policy: DOB license {native_license}")
            basis = f"DOB license {native_license} present for role {candidate['role']}"
            party = {
                "canonical_id": party_id,
                "entity_type": "party",
                "status": "active",
                "provenance": [provenance(dataset, row_key, fields)],
                "confidence": conf,
                "geometry": None,
                "ext": {
                    "source_refs": [source_ref(dataset, row_key, fields, "license_number", basis)],
                    "party_policy": "license_number",
                },
                "name": name or native_license,
                "party_type": "organization",
                "license_id": clean(candidate.get("license_id")),
                "license_type": norm_upper(candidate.get("license_type")).replace(".", "").replace(" ", "") or None,
                "contact": None,
            }
            edge_conf = confidence(0.95, "license_number", basis)
        elif name:
            party_hash = stable_name_hash(name)
            party_id = canonical_id("party", "name_hash", party_hash)
            basis = f"name_hash policy for business/name-only role {candidate['role']}"
            party = {
                "canonical_id": party_id,
                "entity_type": "party",
                "status": "active",
                "provenance": [provenance(dataset, row_key, fields)],
                "confidence": confidence(0.55, "name_hash", f"fuzzy_match: name_hash policy for '{name}'"),
                "geometry": None,
                "ext": {
                    "source_refs": [source_ref(dataset, row_key, fields, "name_hash", basis)],
                    "party_policy": "name_hash",
                    "match_label": "fuzzy_match",
                },
                "name": name,
                "party_type": "organization",
                "license_id": None,
                "license_type": None,
                "contact": None,
            }
            edge_conf = confidence(0.55, "name_hash", basis)
        else:
            continue
        add_entity(entity_by_id, party)
        add_edge(
            edge_by_key,
            {
                "src_ref": permit_id,
                "dst_ref": party_id,
                "relation": candidate["relation"],
                "role": candidate["role"],
                "provenance": [provenance(dataset, row_key, fields)],
                "confidence": edge_conf,
            },
        )


def build_permit(job: str, rows: list[dict[str, Any]], building_ref: str | None, parcel_ref: str | None) -> dict[str, Any]:
    first = rows[0]
    fields = ["source_row_key", "job_number_norm", "bbl_norm", "bin_norm", "permit_number_norm", "latest_activity_date"]
    refs = [
        source_ref(
            clean(row.get("source_dataset")),
            clean(row.get("source_row_key")),
            fields,
            "job_number",
            f"DOB job number {job} contributes to merged Permit",
        )
        for row in rows
    ]
    datasets = sorted({clean(row.get("source_dataset")) for row in rows if clean(row.get("source_dataset"))})
    return {
        "canonical_id": canonical_id("permit", "dob_job", job),
        "entity_type": "permit",
        "status": "active",
        "provenance": [
            provenance(clean(row.get("source_dataset")), clean(row.get("source_row_key")), fields)
            for row in rows
        ],
        "confidence": confidence(0.97, "job_number", f"DOB job number {job} is stable within district cut"),
        "geometry": None,
        "ext": {
            "job_number": job,
            "source_refs": refs,
            "source_datasets": datasets,
            "latest_known_status": None,
        },
        "building_ref": building_ref,
        "parcel_ref": parcel_ref,
        "permit_type": clean(first.get("permit_number_norm")) or None,
        "job_type": None,
        "permit_status": None,
        "work_types": [],
        "filing_date": None,
        "issuance_date": parse_timestamp(first.get("event_date_norm")) if clean(first.get("event_date_norm")) else None,
        "expiration_date": None,
        "initial_cost": None,
        "floor_area_sqft": None,
    }


def build_event(row: dict[str, Any], building_id: str, point: list[float]) -> dict[str, Any]:
    complaint_number = clean(row.get("complaint_number_norm"))
    code = clean(row.get("complaint_category"))
    mapped = map_dob_complaint(code)
    category = getattr(mapped["category"], "value", mapped["category"])
    severity = getattr(mapped["severity"], "value", mapped["severity"])
    fields = ["complaint_number_norm", "bin_norm", "complaint_category", "event_date_norm", "complaint_resolution_status"]
    return {
        "canonical_id": canonical_id("event", "dob_complaint", complaint_number),
        "entity_type": "event",
        "status": "active",
        "provenance": [provenance(clean(row.get("source_dataset")), clean(row.get("source_row_key")), fields)],
        "confidence": confidence(0.92, "complaint_number", f"DOB complaint number {complaint_number} is unique"),
        "geometry": point_geometry(point),
        "ext": {
            "nyc.dob_complaint_category": code,
            "source_refs": [
                source_ref(
                    clean(row.get("source_dataset")),
                    clean(row.get("source_row_key")),
                    fields,
                    "complaint_number",
                    f"DOB complaint number {complaint_number} is unique",
                )
            ],
            "resolved_building_ref": building_id,
        },
        "category": category,
        "type": mapped["type"],
        "timestamp": parse_timestamp(row.get("event_date_norm") or row.get("latest_activity_date")),
        "severity": severity,
        "value": None,
        "payload": {"complaint_category_description": mapped.get("description")},
    }


def build_district(
    block_key: str,
    staging_dir: Path,
    deduped_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    parcels_df = read_block_table(staging_dir, "parcel_bbl_block_lookup.parquet", block_key)
    buildings_df = read_block_table(staging_dir, "building_bin_bbl_lookup.parquet", block_key)
    now_df = read_block_table(staging_dir, "dob_now_filings.parquet", block_key)
    permit_df = read_block_table(staging_dir, "dob_permit_issuance.parquet", block_key)
    complaints_df = read_block_table(staging_dir, "dob_complaints.parquet", block_key)
    raw_lookups = load_raw_party_lookups(deduped_dir, permit_df, now_df)

    entity_by_id: dict[str, dict[str, Any]] = {}
    edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}

    parcel_by_bbl: dict[str, dict[str, Any]] = {}
    for row in parcels_df.fillna("").to_dict("records"):
        parcel = build_parcel(row)
        parcel_by_bbl[clean(row.get("bbl_norm"))] = parcel
        add_entity(entity_by_id, parcel)

    for row in buildings_df.fillna("").to_dict("records"):
        bbl = clean(row.get("mappluto_bbl_norm")) or clean(row.get("base_bbl_norm"))
        ensure_building(
            clean(row.get("bin_norm")),
            bbl,
            parcel_by_bbl,
            entity_by_id,
            edge_by_key,
            "building_footprints_harvest_v0_2_lookup",
            clean(row.get("bin_norm")),
            ["bin_norm", "mappluto_bbl_norm", "base_bbl_norm", "block_key"],
        )

    combined = pd.concat([permit_df, now_df], ignore_index=True).fillna("")
    permit_jobs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in combined.to_dict("records"):
        job = clean(row.get("job_number_norm"))
        if job:
            permit_jobs[job].append(row)

    for job, rows in sorted(permit_jobs.items()):
        bbl = next((clean(row.get("bbl_norm")) for row in rows if clean(row.get("bbl_norm")) in parcel_by_bbl), "")
        bin_value = next((clean(row.get("bin_norm")) for row in rows if clean(row.get("bin_norm")) and clean(row.get("bin_norm")) != "0"), "")
        dataset = clean(rows[0].get("source_dataset"))
        row_key = clean(rows[0].get("source_row_key"))
        building_ref = ensure_building(
            bin_value,
            bbl,
            parcel_by_bbl,
            entity_by_id,
            edge_by_key,
            dataset,
            row_key,
            ["bin_norm", "bbl_norm", "job_number_norm", "source_row_key"],
        )
        parcel_ref = canonical_id("parcel", "bbl", bbl) if bbl in parcel_by_bbl else None
        permit = build_permit(job, rows, building_ref, parcel_ref)
        permit_id = permit["canonical_id"]
        add_entity(entity_by_id, permit)
        if building_ref:
            add_edge(
                edge_by_key,
                {
                    "src_ref": building_ref,
                    "dst_ref": permit_id,
                    "relation": "subject_of_permit",
                    "role": None,
                    "provenance": [provenance(dataset, row_key, ["job_number_norm", "bin_norm", "bbl_norm"])],
                    "confidence": confidence(0.97, "job_number", f"permit job {job} carries BIN {bin_value}"),
                },
            )
        for row in rows:
            dataset_short = (
                "dob_permit_issuance"
                if clean(row.get("source_dataset")) == "nyc__dob_permit_issuance"
                else "dob_now_build_job_application_filings"
            )
            raw = raw_lookups.get(dataset_short, {}).get(clean(row.get("source_row_key")))
            add_party_and_edge(entity_by_id, edge_by_key, permit_id, row, raw)

    for row in complaints_df.fillna("").to_dict("records"):
        if clean(row.get("complaint_resolution_status")) != "resolved_exact_bin":
            continue
        bbl = clean(row.get("resolved_bbl_norm")) or clean(row.get("bbl_norm"))
        bin_value = clean(row.get("bin_norm"))
        building_ref = ensure_building(
            bin_value,
            bbl,
            parcel_by_bbl,
            entity_by_id,
            edge_by_key,
            clean(row.get("source_dataset")),
            clean(row.get("source_row_key")),
            ["complaint_number_norm", "bin_norm", "resolved_bbl_norm", "complaint_category"],
        )
        if not building_ref:
            continue
        point = (entity_by_id[building_ref].get("geometry") or {}).get("point") or [-73.990134, 40.7643741]
        event = build_event(row, building_ref, point)
        event_id = event["canonical_id"]
        add_entity(entity_by_id, event)
        method = clean(row.get("complaint_to_building_method")) or "exact_bin"
        add_edge(
            edge_by_key,
            {
                "src_ref": event_id,
                "dst_ref": building_ref,
                "relation": "resolves_to",
                "role": None,
                "provenance": [
                    provenance(
                        clean(row.get("source_dataset")),
                        clean(row.get("source_row_key")),
                        ["complaint_number_norm", "bin_norm", "complaint_category"],
                    )
                ],
                "confidence": confidence(0.95, method, f"complaint BIN {bin_value} equals building BIN {bin_value}"),
            },
        )

    entities = sorted(entity_by_id.values(), key=lambda item: item["canonical_id"])
    edges = sorted(edge_by_key.values(), key=lambda item: edge_id(item))
    summary_inputs = {
        "raw_source_row_counts": {
            "dob_now_filings": int(len(now_df)),
            "dob_permit_issuance": int(len(permit_df)),
            "dob_complaints": int(len(complaints_df)),
        },
        "staging_rows": {
            "parcels": int(len(parcels_df)),
            "buildings": int(len(buildings_df)),
        },
    }
    return entities, edges, summary_inputs


def edge_id(edge: dict[str, Any]) -> str:
    return f"{edge['src_ref']}|{edge['relation']}|{edge['dst_ref']}|{edge.get('role') or '_'}"


def projection_edge_id(edge: dict[str, Any]) -> str:
    return f"{edge['src']}|{edge['relation']}|{edge['dst']}|{edge.get('role') or '_'}"


def source_datasets(record: dict[str, Any]) -> list[str]:
    return sorted({p.get("source_dataset", "") for p in record.get("provenance", []) if p.get("source_dataset")})


def confidence_score(record: dict[str, Any]) -> float | None:
    conf = record.get("confidence") or {}
    return conf.get("score")


def entity_rows(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "canonical_id": entity["canonical_id"],
            "entity_type": entity["entity_type"],
            "confidence_score": confidence_score(entity),
            "source_datasets_json": json_blob(source_datasets(entity)),
            "record_json": json_blob(entity),
        }
        for entity in entities
    ]


def edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": edge_id(edge),
            "src_ref": edge["src_ref"],
            "dst_ref": edge["dst_ref"],
            "relation": edge["relation"],
            "role": edge.get("role"),
            "confidence_score": confidence_score(edge),
            "source_datasets_json": json_blob(source_datasets(edge)),
            "record_json": json_blob(edge),
        }
        for edge in edges
    ]


def projection_node_rows(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": node["id"], "type": node["type"]} for node in nodes]


def projection_edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": projection_edge_id(edge),
            "src": edge["src"],
            "dst": edge["dst"],
            "relation": edge["relation"],
            "role": edge.get("role"),
            "confidence": edge.get("confidence"),
        }
        for edge in edges
    ]


def report_dict(report: HarnessReport) -> dict[str, Any]:
    return {
        "all_green": report.all_green,
        "exit_code": report.exit_code,
        "failed_gates": [result.gate_id for result in report.results if not result.passed],
        "results": [asdict(result) for result in report.results],
    }


def load_a2_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifact_dir = ROOT / "artifacts" / "nyc_flow2"
    return (
        read_json(artifact_dir / "entities.json"),
        read_json(artifact_dir / "edges.json"),
    )


def local_traversal(entities: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    entity_by_id = {entity["canonical_id"]: entity for entity in entities}
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in edges:
        adj[edge["src_ref"]].append((edge["dst_ref"], edge["relation"]))
        adj[edge["dst_ref"]].append((edge["src_ref"], edge["relation"]))
    starts = [entity["canonical_id"] for entity in entities if entity["canonical_id"].startswith("event:us-nyc:dob_complaint:")]
    for start in starts:
        seen: set[str] = set()
        rels: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for nb, rel in adj.get(node, []):
                rels.add(rel)
                if nb not in seen:
                    stack.append(nb)
        types = {entity_by_id[n]["entity_type"] for n in seen if n in entity_by_id}
        if {"event", "building", "parcel", "permit", "party"}.issubset(types) and {
            "resolves_to",
            "has_building",
            "subject_of_permit",
        }.issubset(rels) and ("performed_by" in rels or "involves_party" in rels or "designed_by" in rels):
            return {
                "status": "PASS",
                "start_event": start,
                "types_reached": sorted(types),
                "relations_reached": sorted(rels),
                "requirement": "complaint/event -> building -> parcel -> permit/job -> party",
            }
    return {
        "status": "FAIL",
        "start_event": starts[0] if starts else None,
        "types_reached": [],
        "relations_reached": [],
        "requirement": "complaint/event -> building -> parcel -> permit/job -> party",
    }


def build_summary(block_key: str, role: str, entities: list[dict[str, Any]], edges: list[dict[str, Any]], nodes: list[dict[str, Any]], proj_edges: list[dict[str, Any]], ranking: dict[str, Any] | None, summary_inputs: dict[str, Any]) -> dict[str, Any]:
    entity_counts = Counter(entity["entity_type"] for entity in entities)
    relation_counts = Counter(edge["relation"] for edge in edges)
    complaint_events = [e for e in entities if e["canonical_id"].startswith("event:us-nyc:dob_complaint:")]
    d2b_critical = [
        e for e in complaint_events if (e.get("ext") or {}).get("nyc.dob_complaint_category") == "91"
    ]
    canonical_critical = [e for e in complaint_events if e.get("severity") == "critical"]
    permit_entities = [e for e in entities if e["entity_type"] == "permit"]
    party_entities = [e for e in entities if e["entity_type"] == "party"]
    role_mix = Counter(edge.get("role") or edge["relation"] for edge in edges if edge["relation"] in {"performed_by", "designed_by", "involves_party"})
    complaint_methods = Counter(
        (edge.get("confidence") or {}).get("method")
        for edge in edges
        if edge["relation"] == "resolves_to" and edge["src_ref"].startswith("event:us-nyc:dob_complaint:")
    )
    raw_counts = summary_inputs["raw_source_row_counts"]
    unique_jobs = len(permit_entities)
    unique_contractors = len(
        {
            edge["dst_ref"]
            for edge in edges
            if edge["relation"] in {"performed_by", "designed_by", "involves_party"}
        }
    )
    now_to_issuance = raw_counts["dob_now_filings"] / (raw_counts["dob_permit_issuance"] + 1)
    complaint_job = len(complaint_events) / (unique_jobs + 1)
    critical_share = len(d2b_critical) / len(complaint_events) if complaint_events else 0.0
    return {
        "district_id": block_key,
        "district_role": role,
        "boundary_statement": BOUNDARY_STATEMENT,
        "parcel_count": entity_counts.get("parcel", 0),
        "building_count": entity_counts.get("building", 0),
        "permit_count": entity_counts.get("permit", 0),
        "complaint_count": len(complaint_events),
        "critical_complaint_count": len(d2b_critical),
        "critical_complaint_definition": "DOB complaint category 91, aligned to a4-D2b discovery scoring",
        "canonical_critical_severity_count": len(canonical_critical),
        "unique_jobs": unique_jobs,
        "unique_contractors": unique_contractors,
        "now_issuance_ratio": round(now_to_issuance, 6),
        "complaint_job_ratio": round(complaint_job, 6),
        "critical_complaint_share": round(critical_share, 6),
        "party_role_mix": dict(sorted(role_mix.items())),
        "complaint_resolution_method_split": dict(sorted((k or "none", v) for k, v in complaint_methods.items())),
        "entity_counts_by_type": dict(sorted(entity_counts.items())),
        "edge_counts_by_relation": dict(sorted(relation_counts.items())),
        "projection_nodes": len(nodes),
        "projection_edges": len(proj_edges),
        "source_row_counts": raw_counts,
        "discovery_ranking_features": ranking or {},
        "known_limitations": [
            "CPU bounded to the selected block, not citywide.",
            "DOB/MapPLUTO projection only; no footprints geometry upgrade, 3D, LL84, emergency/public-safety, traffic, GPU, NeMo, or NIM.",
            "Counts inherit the local harvested dataset boundary statement.",
        ],
    }


def source_refs_ok(record: dict[str, Any]) -> bool:
    refs = (record.get("ext") or {}).get("source_refs", [])
    return bool(refs) and all(ref.get("source_dataset") and ref.get("source_row_key") and ref.get("source_fields") for ref in refs)


def run_local_a5_gates(
    block_key: str,
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    proj_nodes: list[dict[str, Any]],
    proj_edges: list[dict[str, Any]],
    a4_report: HarnessReport,
    summary: dict[str, Any],
    traversal: dict[str, Any],
) -> HarnessReport:
    results: list[GateResult] = []
    count_ok = summary["parcel_count"] > 0 and summary["permit_count"] > 0 and summary["complaint_count"] > 0 and traversal["status"] == "PASS"
    results.append(GateResult("A5-COUNT-SANITY", "District has bounded real DOB activity and a complete local chain", "a5", count_ok, 1, 0 if count_ok else 1, [] if count_ok else [json_blob(summary["source_row_counts"]), traversal["status"]]))

    district_parcels = {entity["canonical_id"] for entity in entities if entity["entity_type"] == "parcel"}
    building_to_parcel = {entity["canonical_id"]: entity.get("parcel_ref") for entity in entities if entity["entity_type"] == "building"}
    permit_to_scope = {
        entity["canonical_id"]: entity.get("parcel_ref") in district_parcels or building_to_parcel.get(entity.get("building_ref")) in district_parcels
        for entity in entities
        if entity["entity_type"] == "permit"
    }
    event_target = {edge["src_ref"]: edge["dst_ref"] for edge in edges if edge["relation"] == "resolves_to"}
    party_source = {edge["dst_ref"]: edge["src_ref"] for edge in edges if edge["relation"] in {"performed_by", "designed_by", "involves_party"}}
    scope_bad = []
    for entity in entities:
        etype = entity["entity_type"]
        ok = etype == "parcel"
        if etype == "building":
            ok = entity.get("parcel_ref") in district_parcels
        elif etype == "permit":
            ok = permit_to_scope.get(entity["canonical_id"], False)
        elif etype == "event":
            ok = building_to_parcel.get(event_target.get(entity["canonical_id"])) in district_parcels
        elif etype == "party":
            ok = permit_to_scope.get(party_source.get(entity["canonical_id"]), False)
        if not ok:
            scope_bad.append(entity["canonical_id"])
    results.append(GateResult("A5-DISTRICT-SCOPE", "DOB entities attach to district reachability", "a5", not scope_bad, len(entities), len(scope_bad), scope_bad[:4]))

    jobs = [(entity.get("ext") or {}).get("job_number") for entity in entities if entity["entity_type"] == "permit"]
    duplicate_jobs = [job for job, count in Counter(jobs).items() if job and count > 1]
    results.append(GateResult("A5-PERMIT-MERGE", "No two Permit entities share a job number", "a5", not duplicate_jobs, len(jobs), len(duplicate_jobs), duplicate_jobs[:4]))

    complaint_edges = [edge for edge in edges if edge["relation"] == "resolves_to" and edge["src_ref"].startswith("event:us-nyc:dob_complaint:")]
    method_bad = [
        f"{edge['src_ref']}->{(edge.get('confidence') or {}).get('method')}"
        for edge in complaint_edges
        if (edge.get("confidence") or {}).get("method") not in COMPLAINT_METHODS or (edge.get("confidence") or {}).get("method") == "exact_bbl"
    ]
    results.append(GateResult("A5-COMPLAINT-METHOD", "Complaint edges use exact_bin or labelled fallback", "a5", not method_bad, len(complaint_edges), len(method_bad), method_bad[:4]))

    category_bad = []
    for event in [entity for entity in entities if entity["canonical_id"].startswith("event:us-nyc:dob_complaint:")]:
        code = (event.get("ext") or {}).get("nyc.dob_complaint_category")
        expected = map_dob_complaint(code)["type"]
        if event.get("type") != expected:
            category_bad.append(f"{event['canonical_id']} {event.get('type')} != {expected}")
    if "construction_site_safety_complaint" in json_blob({"entities": entities, "summary": summary}):
        category_bad.append("old construction_site_safety_complaint slug present")
    results.append(GateResult("A5-COMPLAINT-CATEGORY", "DOB complaint category map canonical", "a5", not category_bad, len(entities), len(category_bad), category_bad[:4]))

    raw_bad = [
        node["id"]
        for node in proj_nodes
        if node.get("type") not in ALLOWED_ENTITY_TYPES
        or ":raw:" in node.get("id", "")
        or re.match(r"^\d{7,10}$", node.get("id", ""))
    ]
    rel_bad = [edge["relation"] for edge in proj_edges if edge.get("relation") not in ALLOWED_RELATIONS]
    results.append(GateResult("A5-NO-RAW-GRAPH", "Projected graph nodes are canonicalized", "a5", not raw_bad and not rel_bad, len(proj_nodes) + len(proj_edges), len(raw_bad) + len(rel_bad), raw_bad[:3] + rel_bad[:3]))

    prov_bad = []
    for record in [*entities, *edges]:
        provs = record.get("provenance", [])
        conf = record.get("confidence")
        if not provs or not all(p.get("source_dataset") and p.get("source_id") and p.get("source_fields") for p in provs) or not conf:
            prov_bad.append(record.get("canonical_id") or edge_id(record))
        if record.get("entity_type") in {"permit", "event", "party", "building", "parcel"} and not source_refs_ok(record):
            prov_bad.append(record["canonical_id"])
    results.append(GateResult("A5-PROVENANCE", "Entities and edges carry source, row, field basis and confidence", "a5", not prov_bad, len(entities) + len(edges), len(prov_bad), prov_bad[:4]))

    party_bad = []
    for party in [entity for entity in entities if entity["entity_type"] == "party"]:
        cid = party["canonical_id"]
        conf = party.get("confidence") or {}
        if ":dob_license:" in cid:
            if conf.get("method") != "license_number" or conf.get("score", 0) < 0.9 or not party.get("license_id"):
                party_bad.append(cid)
        elif ":name_hash:" in cid:
            if conf.get("method") != "name_hash" or conf.get("score", 1) > 0.65 or (party.get("ext") or {}).get("match_label") != "fuzzy_match":
                party_bad.append(cid)
        else:
            party_bad.append(cid)
    results.append(GateResult("A5-PARTY-POLICY", "Uniform license/name_hash party policy", "a5", not party_bad, len([e for e in entities if e["entity_type"] == "party"]), len(party_bad), party_bad[:4]))

    results.append(GateResult("A5-PROJECTION-FIDELITY", "A4 node/edge/vocab/confidence fidelity passes", "a5", a4_report.all_green, 1, 0 if a4_report.all_green else 1, [f"A4 failed gates: {[r.gate_id for r in a4_report.results if not r.passed]}"] if not a4_report.all_green else []))

    if block_key == "1-01060":
        hero_pairs = {
            (HERO_IDS["complaint"], HERO_IDS["building"], "resolves_to", None): 0.95,
            (HERO_IDS["parcel"], HERO_IDS["building"], "has_building", None): 1.0,
            (HERO_IDS["building"], HERO_IDS["permit"], "subject_of_permit", None): 0.97,
            (HERO_IDS["permit"], HERO_IDS["contractor"], "performed_by", "contractor"): 0.95,
        }
        edge_scores = {
            (edge["src_ref"], edge["dst_ref"], edge["relation"], edge.get("role")): (edge.get("confidence") or {}).get("score")
            for edge in edges
        }
        missing = [str(key) for key, score in hero_pairs.items() if edge_scores.get(key) != score]
        results.append(GateResult("A5D3A-HERO-STABILITY", "MN-1060 hero cascade IDs/confidence scores remain stable", "a5", not missing, len(hero_pairs), len(missing), missing[:4]))
    return HarnessReport(results)


def build_drift_projection(nodes: list[dict[str, Any]], proj_edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    bad_nodes = [dict(node) for node in nodes]
    bad_edges = [dict(edge) for edge in proj_edges]
    faults = ["TaxLot node type", "HAS_PERMIT relation", "raw taxlot node", "dropped confidence", "extra projected node not in canonical entities"]
    if bad_nodes:
        bad_nodes[0]["type"] = "TaxLot"
    if bad_edges:
        bad_edges[0]["relation"] = "HAS_PERMIT"
    bad_nodes.append({"id": "raw:taxlot:1010607502", "type": "TaxLot"})
    bad_nodes.append({"id": "parcel:us-nyc:bbl:9999999999", "type": "parcel"})
    for edge in bad_edges[1:]:
        if edge.get("confidence") is not None:
            edge["confidence"] = None
            break
    return bad_nodes, bad_edges, faults


def run_drift_test(
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    proj_edges: list[dict[str, Any]],
    manifest: DistrictManifest,
    a2_entities: list[dict[str, Any]],
    a2_edges: list[dict[str, Any]],
) -> tuple[dict[str, Any], HarnessReport]:
    bad_nodes, bad_edges, faults = build_drift_projection(nodes, proj_edges)
    report = run_a4_gate(
        entities,
        edges,
        bad_nodes,
        bad_edges,
        manifest,
        a2_entity_dicts=a2_entities,
        a2_edge_dicts=a2_edges,
    )
    failed_gates = [result.gate_id for result in report.results if not result.passed]
    required = {"A4-VOCAB", "A4-NODE-FID", "A4-EDGE-FID", "A4-CONF"}
    passed = not report.all_green and required.issubset(set(failed_gates))
    return (
        {
            "status": "PASS" if passed else "FAIL",
            "failed_as_expected": passed,
            "injected_faults": faults,
            "failed_gates": failed_gates,
            "expected_failed_gates": sorted(required),
            "a4_drift_report": report_dict(report),
        },
        report,
    )


def ranking_by_block(discovery_dir: Path) -> dict[str, dict[str, Any]]:
    path = discovery_dir / "block_rankings.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype={"block_key": str})
    wanted = df[df["block_key"].isin(DISTRICTS.keys())]
    return {row["block_key"]: row for row in wanted.to_dict("records")}


def write_district_manifest(path: Path, block_key: str, entities: list[dict[str, Any]], edges: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    info = DISTRICTS[block_key]
    manifest = {
        "district_id": info["district_id"],
        "district_name": info["district_name"],
        "district_role": info["district_role"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "boundary_definition": {
            "type": "nyc_tax_block",
            "block_key": block_key,
            "description": info["boundary"],
        },
        "source_records_included": summary["source_row_counts"],
        "canonical_entity_ids_included": [entity["canonical_id"] for entity in entities],
        "canonical_edge_ids_included": [edge_id(edge) for edge in edges],
        "excluded_records_with_reason": [
            {
                "reason": "Records outside this exact block_key are excluded from the district cut.",
                "scope_rule": f"block_key == {block_key}",
            }
        ],
    }
    write_json(path, manifest)
    return manifest


def write_readme(out: Path, report: dict[str, Any]) -> None:
    lines = [
        "# a4-D3a CPU Bounded Multi-District Projection",
        "",
        f"Status: **{report['status']}**",
        "",
        BOUNDARY_STATEMENT,
        "",
        "This is a CPU bounded, three-district projection test over exactly `1-01060`, `1-01158`, and `2-02316`. It is not citywide, not cuGraph/GPU, not 3D/OpenUSD, and not NeMo/NIM.",
        "",
        "## District Summary",
    ]
    for item in report["districts"]:
        lines.append(
            f"- `{item['district_id']}` ({item['district_role']}): "
            f"{item['parcel_count']} parcels, {item['permit_count']} permits, "
            f"{item['complaint_count']} complaints, {item['projection_nodes']} nodes, "
            f"{item['projection_edges']} edges, gates {item['gates_passed']}, drift {item['drift_test_result']}."
        )
    lines.extend(
        [
            "",
            "## Known Limitations",
            "- Built from the current local NYC harvested dataset and prepared lookup/staging layer.",
            "- Only canonical Parcel, Building, Permit, Event, and Party entities are projected.",
            "- Building footprints geometry, 3D/OpenUSD, public safety, LL84, traffic, GPU/cuGraph, and NeMo/NIM remain out of scope.",
            "",
        ]
    )
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


def output_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    return hashes


def run_a4d3a_gate(
    staging_dir: str | Path = DEFAULT_STAGING_DIR,
    deduped_dir: str | Path = DEFAULT_DEDUPED_DIR,
    discovery_dir: str | Path = DEFAULT_DISCOVERY_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    staging = Path(staging_dir)
    deduped = Path(deduped_dir)
    discovery = Path(discovery_dir)
    out = Path(output_dir)
    if not staging.is_absolute():
        staging = ROOT / staging
    if not deduped.is_absolute():
        deduped = ROOT / deduped
    if not discovery.is_absolute():
        discovery = ROOT / discovery
    if not out.is_absolute():
        out = ROOT / out

    clean_output_dir(out)
    a2_entities, a2_edges = load_a2_records()
    rankings = ranking_by_block(discovery)

    combined_districts: list[dict[str, Any]] = []
    per_reports: dict[str, Any] = {}
    all_green = True

    for block_key, info in DISTRICTS.items():
        district_out = out / "districts" / block_key
        district_out.mkdir(parents=True, exist_ok=True)
        entities, edges, summary_inputs = build_district(block_key, staging, deduped)
        nodes, proj_edges = project_canonical(entities, edges)
        for edge in proj_edges:
            edge["edge_id"] = projection_edge_id(edge)
        manifest = DistrictManifest(
            name=block_key,
            boundary_desc=info["boundary"],
            member_ids={entity["canonical_id"] for entity in entities},
        )
        a4_report = run_a4_gate(
            entities,
            edges,
            nodes,
            proj_edges,
            manifest,
            a2_entity_dicts=a2_entities,
            a2_edge_dicts=a2_edges,
        )
        traversal = local_traversal(entities, edges)
        summary = build_summary(block_key, info["district_role"], entities, edges, nodes, proj_edges, rankings.get(block_key), summary_inputs)
        a5_report = run_local_a5_gates(block_key, entities, edges, nodes, proj_edges, a4_report, summary, traversal)
        drift_report, _ = run_drift_test(entities, edges, nodes, proj_edges, manifest, a2_entities, a2_edges)

        district_manifest = write_district_manifest(district_out / "district_cut_manifest.json", block_key, entities, edges, summary)
        pd.DataFrame(entity_rows(entities)).to_parquet(district_out / "canonical_entities.parquet", index=False)
        pd.DataFrame(edge_rows(edges)).to_parquet(district_out / "canonical_edges.parquet", index=False)
        pd.DataFrame(projection_node_rows(nodes)).to_parquet(district_out / "graph_projection_nodes.parquet", index=False)
        pd.DataFrame(projection_edge_rows(proj_edges)).to_parquet(district_out / "graph_projection_edges.parquet", index=False)

        required_a4 = {r.gate_id: r for r in a4_report.results}
        district_gate_report = {
            "district_id": block_key,
            "status": "PASS" if a4_report.all_green and a5_report.all_green and drift_report["status"] == "PASS" else "FAIL",
            "boundary_statement": BOUNDARY_STATEMENT,
            "a4_report": report_dict(a4_report),
            "a5_report": report_dict(a5_report),
            "local_traversal": traversal,
            "required_gate_status": {
                **{key: required_a4.get(key).passed if required_a4.get(key) else False for key in ["DISTRICT", "A4-UNIQUE", "A4-VOCAB", "A4-NODE-FID", "A4-EDGE-FID", "A4-CONF", "A4-TRAVERSAL"]},
                **{result.gate_id: result.passed for result in a5_report.results},
            },
            "manifest": district_manifest,
            "summary": summary,
        }
        write_json(district_out / "harness_report.json", district_gate_report)
        write_json(district_out / "drift_test_report.json", drift_report)
        write_json(district_out / "district_summary.json", summary)

        gates_passed = district_gate_report["status"] == "PASS"
        all_green = all_green and gates_passed
        combined_item = {
            **summary,
            "gates_passed": gates_passed,
            "drift_test_result": drift_report["status"],
            "local_traversal_status": traversal["status"],
            "output_dir": str(district_out),
        }
        combined_districts.append(combined_item)
        per_reports[block_key] = district_gate_report

    combined = {
        "task": "a4-D3a CPU Bounded Multi-District Projection",
        "status": "PASS" if all_green else "FAIL",
        "exit_code": 0 if all_green else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "input_districts": list(DISTRICTS.keys()),
        "output_dir": str(out),
        "districts": combined_districts,
        "completion_checks": {
            "all_three_projection_built": len(combined_districts) == 3,
            "all_required_gates_pass": all(item["gates_passed"] for item in combined_districts),
            "per_district_drift_tests_failed_as_expected": all(item["drift_test_result"] == "PASS" for item in combined_districts),
            "mn_1060_hero_cascade_stable": per_reports.get("1-01060", {}).get("required_gate_status", {}).get("A5D3A-HERO-STABILITY") is True,
            "block_1158_volume_scaling": next((d for d in combined_districts if d["district_id"] == "1-01158"), {}).get("permit_count", 0) > next((d for d in combined_districts if d["district_id"] == "1-01060"), {}).get("permit_count", 0),
            "block_2316_shape_generalization": next((d for d in combined_districts if d["district_id"] == "2-02316"), {}).get("local_traversal_status") == "PASS",
        },
    }
    write_json(out / "combined_projection_summary.json", combined)
    write_json(out / "a4d3a_districts_v1.json", combined)
    write_json(
        out / "districts_manifest.json",
        {
            "task": combined["task"],
            "status": combined["status"],
            "boundary_statement": BOUNDARY_STATEMENT,
            "districts": [
                {
                    "district_id": item["district_id"],
                    "district_role": item["district_role"],
                    "output_dir": item["output_dir"],
                    "source_row_counts": item["source_row_counts"],
                }
                for item in combined_districts
            ],
        },
    )
    write_json(
        out / "combined_harness_report.json",
        {
            "status": combined["status"],
            "exit_code": combined["exit_code"],
            "boundary_statement": BOUNDARY_STATEMENT,
            "completion_checks": combined["completion_checks"],
            "district_reports": per_reports,
        },
    )
    write_readme(out, combined)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return combined


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a4-D3a CPU bounded multi-district projection.")
    parser.add_argument("--staging-dir", default=str(DEFAULT_STAGING_DIR))
    parser.add_argument("--deduped-dir", default=str(DEFAULT_DEDUPED_DIR))
    parser.add_argument("--discovery-dir", default=str(DEFAULT_DISCOVERY_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_a4d3a_gate(args.staging_dir, args.deduped_dir, args.discovery_dir, args.output_dir)
    print(f"a4-D3a CPU Bounded Multi-District Projection: {report['status']}")
    print(f"Output: {report['output_dir']}")
    for item in report["districts"]:
        print(
            f"- {item['district_id']} ({item['district_role']}): "
            f"parcels={item['parcel_count']} buildings={item['building_count']} "
            f"permits={item['permit_count']} complaints={item['complaint_count']} "
            f"nodes={item['projection_nodes']} edges={item['projection_edges']} "
            f"gates={item['gates_passed']} drift={item['drift_test_result']}"
        )
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
