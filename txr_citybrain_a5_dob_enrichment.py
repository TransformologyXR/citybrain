"""
A5 DOB district enrichment for MN block 1060.

Canonical-first DOB-only enrichment over the current harvested subset. Raw DOB
rows are adapted into canonical Parcel/Building/Permit/Event/Party entities and
canonical edges, then projected through the A4 canonical projector.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_a4_graph_gate import DistrictManifest, project_canonical, run_a4_gate
from txr_citybrain_harness import GateResult, HarnessReport, run_harness
from txr_citybrain_dob_complaint_categories import map_dob_complaint
from txr_citybrain_schema_v1 import (
    Building,
    Confidence,
    Domain,
    Edge,
    EntityType,
    Event,
    EventCategory,
    Geometry,
    GeometryType,
    Parcel,
    Party,
    PartyType,
    Permit,
    Provenance,
    Relation,
    ResolutionMethod,
    build_canonical_id,
)


ROOT = Path(__file__).resolve().parent
A4_DIR = ROOT / "outputs" / "a4_mn_block_1060"
A5_DIR = ROOT / "outputs" / "a5_dob_district_enrichment"
A5_SNAPSHOT_DIR = A5_DIR / "snapshot"
RAW_DOB_ROOT = (
    ROOT
    / "citybrain_data_harvest_pack"
    / "citybrain_data_harvest"
    / "data"
    / "raw"
    / "nyc"
    / "permits_inspections"
)

BOUNDARY_STATEMENT = (
    "DOB enrichment is built from the current harvested DOB subset, capped and "
    "deduped across sample/chunk files, not full NYC DOB history. Counts are subset counts."
)

DISTRICT_ID = "mn_block_1060_a5_dob_enrichment"
DISTRICT_NAME = "MN Block 1060 DOB District Enrichment"
HERO_BBL = "1010607502"
HERO_BIN = "1026676"
HERO_COMPLAINT_ID = "event:us-nyc:dob_complaint:1366080"
HERO_BUILDING_ID = "building:us-nyc:bin:1026676"
HERO_PERMIT_ID = "permit:us-nyc:dob_job:121912591"
HERO_CONTRACTOR_ID = "party:us-nyc:dob_license:GC-0037441"
OLD_COMPLAINT_SLUG = "construction_site_safety_complaint"

ALLOWED_A5_ENTITY_TYPES = {"parcel", "building", "permit", "event", "party"}
ALLOWED_A5_RELATIONS = {
    "has_building",
    "subject_of_permit",
    "resolves_to",
    "performed_by",
    "designed_by",
    "involves_party",
    "near",
    "affects",
}
COMPLAINT_EDGE_METHODS = {"exact_bin", "address_fallback", "spatial_fallback"}
BOROUGH_CODES = {
    "MANHATTAN": "1",
    "NEW YORK": "1",
    "MN": "1",
    "1": "1",
    "BRONX": "2",
    "BX": "2",
    "2": "2",
    "BROOKLYN": "3",
    "BK": "3",
    "3": "3",
    "QUEENS": "4",
    "QN": "4",
    "4": "4",
    "STATEN ISLAND": "5",
    "SI": "5",
    "5": "5",
}


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text.strip()


def norm_upper(value: object) -> str:
    return " ".join(clean(value).upper().split())


def normalize_address(*parts: object) -> str:
    return " ".join(" ".join(clean(p).upper().replace(".", "").split()) for p in parts if clean(p)).strip()


def norm_bbl(value: object) -> str:
    text = clean(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits or int(digits) == 0:
        return ""
    return digits.zfill(10)[-10:]


def bbl_from_parts(borough: object, block: object, lot: object) -> str:
    borough_code = BOROUGH_CODES.get(clean(borough).upper(), "")
    block_digits = "".join(ch for ch in clean(block) if ch.isdigit())
    lot_digits = "".join(ch for ch in clean(lot) if ch.isdigit())
    if not borough_code or not block_digits or not lot_digits:
        return ""
    return f"{borough_code}{block_digits.zfill(5)[-5:]}{lot_digits.zfill(4)[-4:]}"


def parse_datetime(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime().replace(tzinfo=None)


def parse_float(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    try:
        val = float(text)
    except ValueError:
        return None
    if math.isnan(val):
        return None
    return val


def geometry_point(lon: float, lat: float) -> Geometry:
    return Geometry(type=GeometryType.point, coordinates=[lon, lat], point=[lon, lat], crs="EPSG:4326")


def point_from_entity(entity: dict[str, Any]) -> list[float] | None:
    geom = entity.get("geometry") or {}
    point = geom.get("point")
    if isinstance(point, list) and len(point) == 2:
        return [float(point[0]), float(point[1])]
    return None


def confidence(score: float, method: ResolutionMethod, basis: str) -> Confidence:
    return Confidence(score=score, method=method, basis=basis)


def provenance(dataset: str, row_key: str, fields: list[str], derivation: str | None = None) -> Provenance:
    return Provenance(
        source_dataset=dataset,
        source_id=row_key,
        domain=Domain.dm,
        source_fields=fields,
        derivation=derivation,
    )


def source_ref(dataset: str, row_key: str, fields: list[str], method: str, basis: str) -> dict[str, Any]:
    return {
        "source_dataset": dataset,
        "source_row_key": row_key,
        "source_fields": fields,
        "resolution_method": method,
        "basis": basis,
    }


def stable_name_hash(name: str) -> str:
    return hashlib.sha1(norm_upper(name).encode("utf-8")).hexdigest()[:12]


def license_native(license_type: object, license_id: object) -> str:
    ltype = norm_upper(license_type)
    lid = clean(license_id)
    if not ltype or not lid:
        return ""
    digits = "".join(ch for ch in lid if ch.isdigit())
    normalized_id = digits.zfill(len(lid)) if digits else lid.upper()
    return f"{ltype}-{normalized_id}"


def files_for(folder: str) -> list[Path]:
    return sorted((RAW_DOB_ROOT / folder).rglob("*.csv"))


def load_a4_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], bytes]:
    entities = [
        json.loads(value)
        for value in pd.read_parquet(A4_DIR / "canonical_entities.parquet")["record_json"].tolist()
    ]
    edges = [
        json.loads(value)
        for value in pd.read_parquet(A4_DIR / "canonical_edges.parquet")["record_json"].tolist()
    ]
    trace_bytes = (A4_DIR / "scenario_trace_hero_flow.json").read_bytes()
    return entities, edges, trace_bytes


def edge_key(edge: dict[str, Any]) -> tuple[str, str, str, str]:
    return (edge["src_ref"], edge["dst_ref"], edge["relation"], edge.get("role") or "")


def projection_edge_id(edge: dict[str, Any]) -> str:
    role = edge.get("role") or "_"
    return f"{edge['src']}|{edge['relation']}|{edge['dst']}|{role}"


def confidence_score(record: dict[str, Any]) -> float | None:
    conf = record.get("confidence") or {}
    return conf.get("score")


def model_dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def merge_source_refs(target: dict[str, Any], refs: list[dict[str, Any]]) -> None:
    ext = target.setdefault("ext", {})
    existing = {(r.get("source_dataset"), r.get("source_row_key")) for r in ext.get("source_refs", [])}
    merged = list(ext.get("source_refs", []))
    for ref in refs:
        key = (ref.get("source_dataset"), ref.get("source_row_key"))
        if key not in existing:
            merged.append(ref)
            existing.add(key)
    ext["source_refs"] = merged


def merge_provenance(target: dict[str, Any], provs: list[Provenance]) -> None:
    existing_by_key = {
        (p.get("source_dataset"), p.get("source_id")): p for p in target.get("provenance", [])
    }
    for prov in provs:
        dumped = prov.model_dump(mode="json")
        key = (dumped.get("source_dataset"), dumped.get("source_id"))
        if key not in existing_by_key:
            target.setdefault("provenance", []).append(dumped)
            existing_by_key[key] = dumped
        else:
            existing = existing_by_key[key]
            if not existing.get("source_fields") and dumped.get("source_fields"):
                existing["source_fields"] = dumped["source_fields"]
            if not existing.get("derivation") and dumped.get("derivation"):
                existing["derivation"] = dumped["derivation"]


def latest_status(records: list[dict[str, Any]]) -> str | None:
    candidates: list[tuple[datetime, str]] = []
    for rec in records:
        status = clean(rec.get("status"))
        if not status:
            continue
        for key in ("current_status_date", "first_permit_date", "issuance_date", "filing_date"):
            dt = parse_datetime(rec.get(key))
            if dt:
                candidates.append((dt, status))
                break
    if not candidates:
        for rec in records:
            status = clean(rec.get("status"))
            if status:
                return status
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def earliest_datetime(records: list[dict[str, Any]], keys: list[str]) -> datetime | None:
    values = []
    for rec in records:
        for key in keys:
            dt = parse_datetime(rec.get(key))
            if dt:
                values.append(dt)
    return min(values) if values else None


def latest_datetime(records: list[dict[str, Any]], keys: list[str]) -> datetime | None:
    values = []
    for rec in records:
        for key in keys:
            dt = parse_datetime(rec.get(key))
            if dt:
                values.append(dt)
    return max(values) if values else None


def read_dob_subset(
    district_bbls: set[str],
    address_to_bbl: dict[str, str],
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    permit_jobs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    building_sources_by_bin: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bin_to_bbl: dict[str, str] = {}
    bin_to_address: dict[str, str] = {}
    excluded = Counter()
    raw_rows = Counter()
    source_rows = Counter()
    seen_source_rows: set[tuple[str, str]] = set()

    permit_cols = [
        "borough",
        "bin__",
        "house__",
        "street_name",
        "job__",
        "job_doc___",
        "job_type",
        "block",
        "lot",
        "work_type",
        "permit_status",
        "permit_type",
        "permit_sequence__",
        "filing_date",
        "issuance_date",
        "expiration_date",
        "permittee_s_first_name",
        "permittee_s_last_name",
        "permittee_s_business_name",
        "permittee_s_phone__",
        "permittee_s_license_type",
        "permittee_s_license__",
        "owner_s_business_name",
        "owner_s_first_name",
        "owner_s_last_name",
        "permit_si_no",
        "gis_latitude",
        "gis_longitude",
        "bbl",
    ]
    for path in files_for("dob_permit_issuance__ipu4-2q9a"):
        for df in pd.read_csv(path, dtype=str, usecols=lambda col: col in permit_cols, chunksize=50000):
            raw_rows["dob_permit_issuance"] += len(df)
            for row in df.to_dict("records"):
                bbl = norm_bbl(row.get("bbl")) or bbl_from_parts(row.get("borough"), row.get("block"), row.get("lot"))
                if bbl not in district_bbls:
                    excluded["dob_permit_issuance_out_of_district"] += 1
                    continue
                job = clean(row.get("job__"))
                if not job:
                    excluded["dob_permit_issuance_missing_job"] += 1
                    continue
                row_key = clean(row.get("permit_si_no")) or "|".join(
                    [
                        job,
                        clean(row.get("job_doc___")),
                        clean(row.get("permit_sequence__")),
                        clean(row.get("permit_type")),
                        clean(row.get("work_type")),
                        clean(row.get("issuance_date")),
                    ]
                )
                dedupe_key = ("dob_permit_issuance", row_key)
                if dedupe_key in seen_source_rows:
                    continue
                seen_source_rows.add(dedupe_key)
                source_rows["dob_permit_issuance_attached"] += 1
                address = normalize_address(row.get("house__"), row.get("street_name"))
                bin_value = clean(row.get("bin__"))
                rec = {
                    "dataset": "dob_permit_issuance",
                    "row_key": row_key,
                    "job_number": job,
                    "bbl": bbl,
                    "bin": bin_value,
                    "address": address,
                    "job_type": clean(row.get("job_type")),
                    "permit_type": clean(row.get("permit_type")),
                    "work_type": clean(row.get("work_type")),
                    "status": clean(row.get("permit_status")),
                    "filing_date": clean(row.get("filing_date")),
                    "issuance_date": clean(row.get("issuance_date")),
                    "expiration_date": clean(row.get("expiration_date")),
                    "lat": clean(row.get("gis_latitude")),
                    "lon": clean(row.get("gis_longitude")),
                    "permittee_first_name": clean(row.get("permittee_s_first_name")),
                    "permittee_last_name": clean(row.get("permittee_s_last_name")),
                    "permittee_business_name": clean(row.get("permittee_s_business_name")),
                    "permittee_phone": clean(row.get("permittee_s_phone__")),
                    "permittee_license_type": clean(row.get("permittee_s_license_type")),
                    "permittee_license": clean(row.get("permittee_s_license__")),
                    "owner_business_name": clean(row.get("owner_s_business_name")),
                    "owner_first_name": clean(row.get("owner_s_first_name")),
                    "owner_last_name": clean(row.get("owner_s_last_name")),
                    "source_fields": [
                        "job__",
                        "bin__",
                        "bbl",
                        "borough",
                        "block",
                        "lot",
                        "permit_si_no",
                        "permittee_s_license__",
                    ],
                }
                permit_jobs[job].append(rec)
                if bin_value and bin_value != "0":
                    bin_to_bbl[bin_value] = bbl
                    bin_to_address.setdefault(bin_value, address)
                    building_sources_by_bin[bin_value].append(rec)

    now_cols = [
        "job_filing_number",
        "filing_status",
        "house_no",
        "street_name",
        "borough",
        "block",
        "lot",
        "bin",
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
        "filing_date",
        "current_status_date",
        "first_permit_date",
        "general_construction_work_type_",
        "plumbing_work_type",
        "sidewalk_shed_work_type_",
        "suspended_scaffold_work_type_",
        "job_type",
        "latitude",
        "longitude",
        "bbl",
        "initial_cost",
        "total_construction_floor_area",
    ]
    for path in files_for("dob_now_build_job_application_filings__w9ak-ipjd"):
        for df in pd.read_csv(path, dtype=str, usecols=lambda col: col in now_cols, chunksize=50000):
            raw_rows["dob_now_filings"] += len(df)
            for row in df.to_dict("records"):
                bbl = norm_bbl(row.get("bbl")) or bbl_from_parts(row.get("borough"), row.get("block"), row.get("lot"))
                if bbl not in district_bbls:
                    excluded["dob_now_out_of_district"] += 1
                    continue
                job = clean(row.get("job_filing_number"))
                if not job:
                    excluded["dob_now_missing_job"] += 1
                    continue
                row_key = job
                dedupe_key = ("dob_now_build_job_application_filings", row_key)
                if dedupe_key in seen_source_rows:
                    continue
                seen_source_rows.add(dedupe_key)
                source_rows["dob_now_filings_attached"] += 1
                address = normalize_address(row.get("house_no"), row.get("street_name"))
                bin_value = clean(row.get("bin"))
                work_types = []
                for key in (
                    "general_construction_work_type_",
                    "plumbing_work_type",
                    "sidewalk_shed_work_type_",
                    "suspended_scaffold_work_type_",
                ):
                    if norm_upper(row.get(key)) in {"YES", "Y"}:
                        work_types.append(key.replace("_work_type_", "").replace("_work_type", ""))
                rec = {
                    "dataset": "dob_now_build_job_application_filings",
                    "row_key": row_key,
                    "job_number": job,
                    "bbl": bbl,
                    "bin": bin_value,
                    "address": address,
                    "job_type": clean(row.get("job_type")),
                    "permit_type": "DOB_NOW",
                    "work_type": ",".join(work_types),
                    "status": clean(row.get("filing_status")),
                    "filing_date": clean(row.get("filing_date")),
                    "current_status_date": clean(row.get("current_status_date")),
                    "first_permit_date": clean(row.get("first_permit_date")),
                    "lat": clean(row.get("latitude")),
                    "lon": clean(row.get("longitude")),
                    "initial_cost": clean(row.get("initial_cost")),
                    "floor_area_sqft": clean(row.get("total_construction_floor_area")),
                    "applicant_professional_title": clean(row.get("applicant_professional_title")),
                    "applicant_license": clean(row.get("applicant_license")),
                    "applicant_first_name": clean(row.get("applicant_first_name")),
                    "applicant_last_name": clean(row.get("applicant_last_name")),
                    "filing_representative_first_name": clean(row.get("filing_representative_first_name")),
                    "filing_representative_last_name": clean(row.get("filing_representative_last_name")),
                    "filing_representative_business_name": clean(row.get("filing_representative_business_name")),
                    "owner_business_name": clean(row.get("owner_s_business_name")),
                    "owner_first_name": clean(row.get("owner_first_name")),
                    "owner_last_name": clean(row.get("owner_last_name")),
                    "source_fields": [
                        "job_filing_number",
                        "bin",
                        "bbl",
                        "borough",
                        "block",
                        "lot",
                        "applicant_license",
                    ],
                }
                permit_jobs[job].append(rec)
                if bin_value and bin_value != "0":
                    bin_to_bbl[bin_value] = bbl
                    bin_to_address.setdefault(bin_value, address)
                    building_sources_by_bin[bin_value].append(rec)

    complaint_records: dict[str, dict[str, Any]] = {}
    complaint_resolution_counts = Counter()
    complaint_cols = [
        "complaint_number",
        "status",
        "date_entered",
        "house_number",
        "house_street",
        "bin",
        "complaint_category",
        "disposition_code",
        "inspection_date",
    ]
    seen_complaints: set[str] = set()
    for path in files_for("dob_complaints_received__eabe-havv"):
        for df in pd.read_csv(path, dtype=str, usecols=lambda col: col in complaint_cols, chunksize=50000):
            raw_rows["dob_complaints"] += len(df)
            for row in df.to_dict("records"):
                complaint_number = clean(row.get("complaint_number"))
                if not complaint_number or complaint_number in seen_complaints:
                    continue
                seen_complaints.add(complaint_number)
                bin_value = clean(row.get("bin"))
                address = normalize_address(row.get("house_number"), row.get("house_street"))
                bbl = ""
                method = ""
                confidence_value = 0.0
                basis = ""
                if bin_value in bin_to_bbl:
                    bbl = bin_to_bbl[bin_value]
                    method = "exact_bin"
                    confidence_value = 0.95
                    basis = f"complaint BIN {bin_value} equals building BIN {bin_value}"
                elif address and address in address_to_bbl and address_to_bbl[address] in district_bbls:
                    bbl = address_to_bbl[address]
                    method = "address_fallback"
                    confidence_value = 0.65
                    basis = f"complaint address {address} matched district parcel address"
                else:
                    excluded["dob_complaint_unresolved_or_out_of_scope"] += 1
                    continue
                if bbl not in district_bbls:
                    excluded["dob_complaint_out_of_district"] += 1
                    continue
                if method != "exact_bin":
                    excluded["dob_complaint_address_fallback_without_known_building"] += 1
                    continue
                source_rows["dob_complaints_attached"] += 1
                complaint_resolution_counts[method] += 1
                complaint_records[complaint_number] = {
                    "dataset": "dob_complaints_received",
                    "row_key": complaint_number,
                    "complaint_number": complaint_number,
                    "bbl": bbl,
                    "bin": bin_value,
                    "address": address,
                    "status": clean(row.get("status")),
                    "date_entered": clean(row.get("date_entered")),
                    "complaint_category": clean(row.get("complaint_category")),
                    "disposition_code": clean(row.get("disposition_code")),
                    "inspection_date": clean(row.get("inspection_date")),
                    "resolution_method": method,
                    "resolution_confidence": confidence_value,
                    "resolution_basis": basis,
                    "source_fields": [
                        "complaint_number",
                        "bin",
                        "complaint_category",
                        "date_entered",
                        "status",
                    ],
                }

    complaint_resolution_counts.setdefault("exact_bin", 0)
    complaint_resolution_counts.setdefault("address_fallback", 0)
    complaint_resolution_counts.setdefault("spatial_fallback", 0)
    complaint_resolution_counts["excluded_unresolved"] = excluded["dob_complaint_unresolved_or_out_of_scope"]

    return (
        {
            "permit_jobs": dict(permit_jobs),
            "building_sources_by_bin": dict(building_sources_by_bin),
            "complaint_records": complaint_records,
            "excluded": dict(excluded),
            "raw_rows": dict(raw_rows),
            "source_rows": dict(source_rows),
            "complaint_resolution_counts": dict(complaint_resolution_counts),
        },
        bin_to_bbl,
        bin_to_address,
    )


def choose_building_geometry(records: list[dict[str, Any]], parcel_entity: dict[str, Any]) -> Geometry:
    for rec in records:
        lat = parse_float(rec.get("lat"))
        lon = parse_float(rec.get("lon"))
        if lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            return geometry_point(lon, lat)
    point = point_from_entity(parcel_entity)
    if point:
        return geometry_point(point[0], point[1])
    return geometry_point(-73.990134, 40.7643741)


def add_or_merge_edge(edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]], edge: Edge) -> None:
    dumped = model_dump(edge)
    key = edge_key(dumped)
    if key not in edge_by_key:
        edge_by_key[key] = dumped
        return
    target = edge_by_key[key]
    merge_provenance(target, edge.provenance)
    if dumped.get("confidence") is not None:
        target["confidence"] = dumped["confidence"]


def add_party(
    entity_by_id: dict[str, dict[str, Any]],
    edge_by_key: dict[tuple[str, str, str, str], dict[str, Any]],
    permit_id: str,
    rec: dict[str, Any],
    relation: Relation,
    role: str,
    name: str,
    license_type: str = "",
    license_id: str = "",
    contact: str = "",
) -> str | None:
    name = " ".join(clean(name).split())
    native_license = license_native(license_type, license_id)
    if native_license:
        party_id = build_canonical_id(EntityType.party, "us", "nyc", "dob_license", native_license)
        conf = confidence(0.95, ResolutionMethod.license_number, f"license_number policy: DOB license {native_license}")
        source_basis = f"DOB license {native_license} present for role {role}"
        party = Party(
            canonical_id=party_id,
            name=name or native_license,
            party_type=PartyType.organization,
            license_id=clean(license_id),
            license_type=norm_upper(license_type),
            contact=contact or None,
            confidence=conf,
            provenance=[provenance(rec["dataset"], rec["row_key"], rec["source_fields"])],
            ext={
                "source_refs": [
                    source_ref(rec["dataset"], rec["row_key"], rec["source_fields"], "license_number", source_basis)
                ],
                "party_policy": "license_number",
            },
        )
        edge_conf = confidence(0.95, ResolutionMethod.license_number, source_basis)
    elif name:
        party_hash = stable_name_hash(name)
        party_id = build_canonical_id(EntityType.party, "us", "nyc", "name_hash", party_hash)
        conf = confidence(0.55, ResolutionMethod.name_hash, f"fuzzy_match: name_hash policy for '{name}'")
        source_basis = f"name_hash policy for business/name-only role {role}"
        party = Party(
            canonical_id=party_id,
            name=name,
            party_type=PartyType.organization,
            confidence=conf,
            provenance=[provenance(rec["dataset"], rec["row_key"], rec["source_fields"])],
            ext={
                "source_refs": [
                    source_ref(rec["dataset"], rec["row_key"], rec["source_fields"], "name_hash", source_basis)
                ],
                "party_policy": "name_hash",
                "match_label": "fuzzy_match",
            },
        )
        edge_conf = confidence(0.55, ResolutionMethod.name_hash, source_basis)
    else:
        return None

    dumped = model_dump(party)
    if party_id in entity_by_id:
        entity_by_id[party_id]["confidence"] = dumped["confidence"]
        if native_license:
            entity_by_id[party_id]["license_id"] = clean(license_id)
            entity_by_id[party_id]["license_type"] = norm_upper(license_type)
        if contact:
            entity_by_id[party_id]["contact"] = contact
        entity_by_id[party_id].setdefault("ext", {}).update(dumped.get("ext", {}))
        merge_source_refs(entity_by_id[party_id], dumped.get("ext", {}).get("source_refs", []))
        merge_provenance(entity_by_id[party_id], party.provenance)
    else:
        entity_by_id[party_id] = dumped

    add_or_merge_edge(
        edge_by_key,
        Edge(
            src_ref=permit_id,
            dst_ref=party_id,
            relation=relation,
            role=role,
            provenance=[provenance(rec["dataset"], rec["row_key"], rec["source_fields"])],
            confidence=edge_conf,
        ),
    )
    return party_id


def build_enrichment() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    bytes,
]:
    base_entities, base_edges, a4_trace_bytes = load_a4_records()
    entity_by_id = {entity["canonical_id"]: entity for entity in base_entities}
    edge_by_key = {edge_key(edge): edge for edge in base_edges}

    parcel_entities = [entity for entity in base_entities if entity["entity_type"] == "parcel"]
    district_bbls = {entity["canonical_id"].rsplit(":", 1)[-1] for entity in parcel_entities}
    parcel_by_bbl = {entity["canonical_id"].rsplit(":", 1)[-1]: entity for entity in parcel_entities}
    address_to_bbl = {
        normalize_address(entity.get("address")): entity["canonical_id"].rsplit(":", 1)[-1]
        for entity in parcel_entities
        if entity.get("address")
    }

    harvested, bin_to_bbl, _bin_to_address = read_dob_subset(district_bbls, address_to_bbl)
    building_sources_by_bin = harvested["building_sources_by_bin"]

    building_by_bin: dict[str, str] = {}
    for bin_value, records in sorted(building_sources_by_bin.items()):
        bbl = records[0]["bbl"]
        parcel_entity = parcel_by_bbl[bbl]
        parcel_id = parcel_entity["canonical_id"]
        building_id = build_canonical_id(EntityType.building, "us", "nyc", "bin", bin_value)
        building_by_bin[bin_value] = building_id
        refs = [
            source_ref(
                rec["dataset"],
                rec["row_key"],
                rec["source_fields"],
                "exact_bin",
                f"DOB row carries BIN {bin_value} and district BBL {bbl}",
            )
            for rec in records
        ]
        provs = [
            provenance(rec["dataset"], rec["row_key"], rec["source_fields"], f"BIN {bin_value} associated with BBL {bbl}")
            for rec in records
        ]
        if building_id in entity_by_id:
            entity_by_id[building_id]["parcel_ref"] = entity_by_id[building_id].get("parcel_ref") or parcel_id
            merge_source_refs(entity_by_id[building_id], refs)
            merge_provenance(entity_by_id[building_id], provs)
        else:
            building = Building(
                canonical_id=building_id,
                parcel_ref=parcel_id,
                geometry=choose_building_geometry(records, parcel_entity),
                confidence=confidence(0.95, ResolutionMethod.exact_bin, f"DOB BIN {bin_value} resolved to district building"),
                provenance=provs,
                ext={
                    "source_refs": refs,
                    "nyc.bbl": bbl,
                    "nyc.address": records[0].get("address") or parcel_entity.get("address"),
                },
            )
            entity_by_id[building_id] = model_dump(building)
        add_or_merge_edge(
            edge_by_key,
            Edge(
                src_ref=parcel_id,
                dst_ref=building_id,
                relation=Relation.has_building,
                provenance=[provs[0]],
                confidence=confidence(1.0, ResolutionMethod.exact_bin, f"DOB BIN {bin_value} is attached to district BBL {bbl}"),
            ),
        )

    permits_with_multi_source_refs = 0
    permit_jobs = harvested["permit_jobs"]
    for job_number, records in sorted(permit_jobs.items()):
        permit_id = build_canonical_id(EntityType.permit, "us", "nyc", "dob_job", job_number)
        source_refs = [
            source_ref(
                rec["dataset"],
                rec["row_key"],
                rec["source_fields"],
                "job_number",
                f"source row contributes to DOB job {job_number}",
            )
            for rec in records
        ]
        if len(source_refs) > 1:
            permits_with_multi_source_refs += 1
        provs = [provenance(rec["dataset"], rec["row_key"], rec["source_fields"]) for rec in records]
        bbls = sorted({rec["bbl"] for rec in records if rec.get("bbl")})
        bins = sorted({rec["bin"] for rec in records if rec.get("bin") and rec.get("bin") != "0"})
        primary_bbl = bbls[0] if bbls else ""
        primary_bin = bins[0] if bins else ""
        parcel_id = build_canonical_id(EntityType.parcel, "us", "nyc", "bbl", primary_bbl) if primary_bbl else None
        building_id = building_by_bin.get(primary_bin) if primary_bin else None
        work_types = sorted({w for rec in records for w in clean(rec.get("work_type")).split(",") if w})
        permit = Permit(
            canonical_id=permit_id,
            building_ref=building_id,
            parcel_ref=parcel_id,
            permit_type=next((clean(rec.get("permit_type")) for rec in records if clean(rec.get("permit_type"))), None),
            job_type=next((clean(rec.get("job_type")) for rec in records if clean(rec.get("job_type"))), None),
            permit_status=latest_status(records),
            work_types=work_types,
            filing_date=earliest_datetime(records, ["filing_date"]),
            issuance_date=latest_datetime(records, ["issuance_date", "first_permit_date"]),
            expiration_date=latest_datetime(records, ["expiration_date"]),
            initial_cost=next((parse_float(rec.get("initial_cost")) for rec in records if parse_float(rec.get("initial_cost")) is not None), None),
            floor_area_sqft=next((parse_float(rec.get("floor_area_sqft")) for rec in records if parse_float(rec.get("floor_area_sqft")) is not None), None),
            confidence=confidence(0.97, ResolutionMethod.job_number, f"DOB job number {job_number} is the stable permit key"),
            provenance=provs,
            ext={
                "job_number": job_number,
                "source_refs": source_refs,
                "source_datasets": sorted({rec["dataset"] for rec in records}),
                "all_bbls": bbls,
                "all_bins": bins,
                "latest_known_status": latest_status(records),
            },
        )
        entity_by_id[permit_id] = model_dump(permit)
        for bin_value in bins:
            building_id_for_edge = building_by_bin.get(bin_value)
            if not building_id_for_edge:
                continue
            add_or_merge_edge(
                edge_by_key,
                Edge(
                    src_ref=building_id_for_edge,
                    dst_ref=permit_id,
                    relation=Relation.subject_of_permit,
                    provenance=[provs[0]],
                    confidence=confidence(0.97, ResolutionMethod.job_number, f"permit job {job_number} carries BIN {bin_value}"),
                ),
            )

        for rec in records:
            if rec["dataset"] == "dob_permit_issuance":
                permittee_name = clean(rec.get("permittee_business_name")) or " ".join(
                    [clean(rec.get("permittee_first_name")), clean(rec.get("permittee_last_name"))]
                ).strip()
                add_party(
                    entity_by_id,
                    edge_by_key,
                    permit_id,
                    rec,
                    Relation.performed_by,
                    "contractor",
                    permittee_name,
                    rec.get("permittee_license_type", ""),
                    rec.get("permittee_license", ""),
                    rec.get("permittee_phone", ""),
                )
            else:
                applicant_name = " ".join([clean(rec.get("applicant_first_name")), clean(rec.get("applicant_last_name"))]).strip()
                add_party(
                    entity_by_id,
                    edge_by_key,
                    permit_id,
                    rec,
                    Relation.designed_by,
                    "applicant",
                    applicant_name,
                    rec.get("applicant_professional_title", ""),
                    rec.get("applicant_license", ""),
                )
                representative_name = clean(rec.get("filing_representative_business_name")) or " ".join(
                    [clean(rec.get("filing_representative_first_name")), clean(rec.get("filing_representative_last_name"))]
                ).strip()
                add_party(
                    entity_by_id,
                    edge_by_key,
                    permit_id,
                    rec,
                    Relation.involves_party,
                    "filing_representative",
                    representative_name,
                )
            owner_name = clean(rec.get("owner_business_name")) or " ".join(
                [clean(rec.get("owner_first_name")), clean(rec.get("owner_last_name"))]
            ).strip()
            add_party(
                entity_by_id,
                edge_by_key,
                permit_id,
                rec,
                Relation.involves_party,
                "owner",
                owner_name,
            )

    complaint_records = harvested["complaint_records"]
    for complaint_number, rec in sorted(complaint_records.items()):
        bin_value = rec["bin"]
        building_id = building_by_bin.get(bin_value)
        if not building_id:
            continue
        building_entity = entity_by_id[building_id]
        point = point_from_entity(building_entity) or point_from_entity(parcel_by_bbl[rec["bbl"]]) or [-73.990134, 40.7643741]
        mapping = map_dob_complaint(rec.get("complaint_category"))
        complaint_id = build_canonical_id(EntityType.event, "us", "nyc", "dob_complaint", complaint_number)
        prov = provenance(rec["dataset"], rec["row_key"], rec["source_fields"])
        ref = source_ref(
            rec["dataset"],
            rec["row_key"],
            rec["source_fields"],
            "complaint_number",
            f"DOB complaint number {complaint_number} is unique",
        )
        event = Event(
            canonical_id=complaint_id,
            category=mapping["category"],
            type=mapping["type"],
            timestamp=parse_datetime(rec.get("date_entered")) or datetime(1970, 1, 1),
            severity=mapping["severity"],
            status=rec.get("status") or None,
            geometry=geometry_point(point[0], point[1]),
            confidence=confidence(0.92, ResolutionMethod.complaint_number, f"DOB complaint number {complaint_number} is unique"),
            payload={
                "complaint_category_description": mapping["description"],
                "disposition_code": rec.get("disposition_code"),
                "inspection_date": rec.get("inspection_date"),
            },
            provenance=[prov],
            ext={
                "nyc.dob_complaint_category": rec.get("complaint_category"),
                "nyc.house_address": rec.get("address"),
                "resolution_method": rec["resolution_method"],
                "source_refs": [ref],
            },
        )
        entity_by_id[complaint_id] = model_dump(event)
        add_or_merge_edge(
            edge_by_key,
            Edge(
                src_ref=complaint_id,
                dst_ref=building_id,
                relation=Relation.resolves_to,
                provenance=[prov],
                confidence=confidence(
                    rec["resolution_confidence"],
                    ResolutionMethod(rec["resolution_method"]),
                    rec["resolution_basis"],
                ),
            ),
        )

    entities = list(entity_by_id.values())
    edges = list(edge_by_key.values())
    dob_activity_bbls = set()
    for permit in permit_jobs.values():
        for rec in permit:
            if rec.get("bbl"):
                dob_activity_bbls.add(rec["bbl"])
    for rec in complaint_records.values():
        if rec.get("bbl"):
            dob_activity_bbls.add(rec["bbl"])

    party_counts = Counter()
    for entity in entities:
        if entity["entity_type"] != "party":
            continue
        method = (entity.get("confidence") or {}).get("method")
        if method == "license_number":
            party_counts["high_license_number"] += 1
        elif method == "name_hash":
            party_counts["low_name_hash"] += 1
        else:
            party_counts[method or "unknown"] += 1

    permit_entities = [entity for entity in entities if entity["entity_type"] == "permit"]
    event_entities = [entity for entity in entities if entity["entity_type"] == "event"]
    summary = {
        "subset_boundary_statement": BOUNDARY_STATEMENT,
        "district_id": DISTRICT_ID,
        "parcel_count": len(district_bbls),
        "parcels_with_dob_activity": len(dob_activity_bbls),
        "raw_rows_read_including_sample_overlap": harvested["raw_rows"],
        "attached_source_rows_after_dedupe": harvested["source_rows"],
        "permit_lifecycle_merge": {
            "raw_dob_now_filing_rows": harvested["source_rows"].get("dob_now_filings_attached", 0),
            "raw_dob_permit_issuance_rows": harvested["source_rows"].get("dob_permit_issuance_attached", 0),
            "unique_job_numbers": len(permit_jobs),
            "unique_permit_entities_after_merge": len(permit_entities),
            "permits_with_multiple_source_refs": permits_with_multi_source_refs,
        },
        "complaint_resolution_counts": harvested["complaint_resolution_counts"],
        "parties_by_confidence_tier": dict(party_counts),
        "entity_counts_by_type": dict(sorted(Counter(entity["entity_type"] for entity in entities).items())),
        "edge_counts_by_relation": dict(sorted(Counter(edge["relation"] for edge in edges).items())),
        "excluded_records_with_reasons": harvested["excluded"],
        "hero_parcel_enriched_profile": {
            "bbl": HERO_BBL,
            "dob_permit_issuance_records": sum(
                1
                for records in permit_jobs.values()
                for rec in records
                if rec.get("dataset") == "dob_permit_issuance" and rec.get("bbl") == HERO_BBL
            ),
            "dob_now_job_filings": sum(
                1
                for records in permit_jobs.values()
                for rec in records
                if rec.get("dataset") == "dob_now_build_job_application_filings" and rec.get("bbl") == HERO_BBL
            ),
            "dob_complaints": sum(1 for rec in complaint_records.values() if rec.get("bbl") == HERO_BBL),
        },
        "category_91_cascade_status": {
            "code_91_events": sum(
                1
                for entity in event_entities
                if (entity.get("ext") or {}).get("nyc.dob_complaint_category") == "91"
            ),
            "canonical_type": "site_conditions_endangering_workers",
            "old_slug_absent": OLD_COMPLAINT_SLUG not in json.dumps(entities),
        },
    }

    manifest = {
        "district_id": DISTRICT_ID,
        "district_name": DISTRICT_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "subset_boundary_statement": BOUNDARY_STATEMENT,
        "boundary_definition": {
            "kind": "nyc_tax_block",
            "borough": "MN",
            "borough_code": "1",
            "block": "1060",
            "bbls": sorted(district_bbls),
            "source": "A4 MN block 1060 canonical Parcel cut plus DOB-only harvested subset enrichment",
        },
        "source_records_included": {
            "dob_permit_issuance_records": harvested["source_rows"].get("dob_permit_issuance_attached", 0),
            "dob_now_job_filings": harvested["source_rows"].get("dob_now_filings_attached", 0),
            "dob_complaints": harvested["source_rows"].get("dob_complaints_attached", 0),
        },
        "canonical_entity_ids_included": sorted(entity["canonical_id"] for entity in entities),
        "canonical_edge_ids_included": sorted(
            f"{edge['src_ref']}|{edge['relation']}|{edge['dst_ref']}|{edge.get('role') or '_'}" for edge in edges
        ),
        "excluded_records_with_reason": [
            {"reason": reason, "count": count} for reason, count in sorted(harvested["excluded"].items())
        ],
    }
    return entities, edges, summary, manifest, a4_trace_bytes


def entity_rows(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "canonical_id": entity["canonical_id"],
            "entity_type": entity["entity_type"],
            "status": entity.get("status"),
            "confidence_score": confidence_score(entity),
            "record_json": json.dumps(entity, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        }
        for entity in entities
    ]


def edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": f"{edge['src_ref']}|{edge['relation']}|{edge['dst_ref']}|{edge.get('role') or '_'}",
            "src_ref": edge["src_ref"],
            "dst_ref": edge["dst_ref"],
            "relation": edge["relation"],
            "role": edge.get("role"),
            "confidence_score": confidence_score(edge),
            "record_json": json.dumps(edge, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
        }
        for edge in edges
    ]


def gate_json(report: HarnessReport) -> dict[str, Any]:
    return {
        "all_green": report.all_green,
        "exit_code": report.exit_code,
        "invariants_green": report.invariants_green,
        "flow2_green": report.flow2_green,
        "failed_gates": [result.gate_id for result in report.results if not result.passed],
        "results": [asdict(result) for result in report.results],
    }


def dob_provenance(record: dict[str, Any]) -> bool:
    return any((prov.get("source_dataset") or "").startswith("dob_") for prov in record.get("provenance", []))


def source_refs_ok(record: dict[str, Any]) -> bool:
    refs = (record.get("ext") or {}).get("source_refs", [])
    if not refs:
        return False
    return all(ref.get("source_dataset") and ref.get("source_row_key") and ref.get("source_fields") for ref in refs)


def run_a5_gate(
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    proj_nodes: list[dict[str, Any]],
    proj_edges: list[dict[str, Any]],
    manifest: dict[str, Any],
    summary: dict[str, Any],
    readme_text: str,
    a4_trace_bytes: bytes,
    a5_trace_bytes: bytes,
) -> tuple[HarnessReport, HarnessReport, HarnessReport]:
    full_a2_entities = json.loads((ROOT / "artifacts" / "nyc_flow2" / "entities.json").read_text(encoding="utf-8"))
    full_a2_edges = json.loads((ROOT / "artifacts" / "nyc_flow2" / "edges.json").read_text(encoding="utf-8"))
    a2_report = run_harness(full_a2_entities, full_a2_edges)
    district_manifest = DistrictManifest(
        name=DISTRICT_ID,
        boundary_desc="MN block 1060 DOB enriched district cut",
        member_ids={entity["canonical_id"] for entity in entities},
    )
    a4_report = run_a4_gate(
        entities,
        edges,
        proj_nodes,
        proj_edges,
        district_manifest,
        a2_entity_dicts=full_a2_entities,
        a2_edge_dicts=full_a2_edges,
    )

    results: list[GateResult] = []

    boundary_sources = [
        readme_text,
        json.dumps(manifest),
        json.dumps(summary),
        BOUNDARY_STATEMENT,
    ]
    boundary_ok = all(BOUNDARY_STATEMENT in item for item in boundary_sources)
    results.append(GateResult("A5-SUBSET-BOUNDARY", "Capped/deduped subset boundary stated", "a5", boundary_ok, 4, 0 if boundary_ok else 1, [] if boundary_ok else ["boundary statement missing from one or more artifacts"]))

    parcels_with_activity = summary["parcels_with_dob_activity"]
    results.append(GateResult("A5-COUNT-SANITY", "District has real DOB activity", "a5", parcels_with_activity >= 15, 1, 0 if parcels_with_activity >= 15 else 1, [f"{parcels_with_activity}/52 parcels with DOB activity"]))

    permit_entities = [entity for entity in entities if entity["entity_type"] == "permit"]
    jobs = [((entity.get("ext") or {}).get("job_number")) for entity in permit_entities]
    duplicate_jobs = [job for job, count in Counter(jobs).items() if job and count > 1]
    multi_source_bad = [
        entity["canonical_id"]
        for entity in permit_entities
        if len((entity.get("ext") or {}).get("source_refs", [])) > 1
        and len({ref["source_dataset"] for ref in (entity.get("ext") or {}).get("source_refs", [])}) < 2
    ]
    merge_ok = not duplicate_jobs and not multi_source_bad
    results.append(GateResult("A5-PERMIT-MERGE", "Permit lifecycle merge by job", "a5", merge_ok, len(permit_entities), len(duplicate_jobs) + len(multi_source_bad), [f"duplicate jobs: {duplicate_jobs[:4]}"] if duplicate_jobs else []))

    district_parcels = {entity["canonical_id"] for entity in entities if entity["entity_type"] == "parcel"}
    building_to_parcel = {
        entity["canonical_id"]: entity.get("parcel_ref")
        for entity in entities
        if entity["entity_type"] == "building"
    }
    permit_to_scope = {
        entity["canonical_id"]: (entity.get("parcel_ref") in district_parcels)
        or (building_to_parcel.get(entity.get("building_ref")) in district_parcels)
        for entity in permit_entities
    }
    event_targets = {edge["src_ref"]: edge["dst_ref"] for edge in edges if edge["relation"] == "resolves_to"}
    party_sources = {edge["dst_ref"]: edge["src_ref"] for edge in edges if edge["relation"] in {"performed_by", "designed_by", "involves_party"}}
    scope_bad = []
    for entity in entities:
        etype = entity["entity_type"]
        if etype == "parcel":
            continue
        ok = False
        if etype == "building":
            ok = entity.get("parcel_ref") in district_parcels
        elif etype == "permit":
            ok = permit_to_scope.get(entity["canonical_id"], False)
        elif etype == "event":
            ok = building_to_parcel.get(event_targets.get(entity["canonical_id"])) in district_parcels
        elif etype == "party":
            ok = permit_to_scope.get(party_sources.get(entity["canonical_id"]), False)
        if not ok:
            scope_bad.append(entity["canonical_id"])
    results.append(GateResult("A5-DISTRICT-SCOPE", "DOB entities attach to district", "a5", not scope_bad, len(entities), len(scope_bad), [f"unscoped: {cid}" for cid in scope_bad[:4]]))

    complaint_edges = [
        edge
        for edge in edges
        if edge["relation"] == "resolves_to" and edge["src_ref"].startswith("event:us-nyc:dob_complaint:")
    ]
    method_bad = []
    for edge in complaint_edges:
        method = ((edge.get("confidence") or {}).get("method") or "")
        if method not in COMPLAINT_EDGE_METHODS or method == "exact_bbl":
            method_bad.append(f"{edge['src_ref']}->{method}")
    results.append(GateResult("A5-COMPLAINT-METHOD", "Complaint resolution methods labelled", "a5", not method_bad, len(complaint_edges), len(method_bad), method_bad[:4]))

    complaint_events = [entity for entity in entities if entity["canonical_id"].startswith("event:us-nyc:dob_complaint:")]
    category_bad = []
    for event in complaint_events:
        code = (event.get("ext") or {}).get("nyc.dob_complaint_category")
        expected = map_dob_complaint(code)["type"]
        if event.get("type") != expected:
            category_bad.append(f"{event['canonical_id']} {event.get('type')} != {expected}")
    old_slug_present = OLD_COMPLAINT_SLUG in json.dumps({"entities": entities, "summary": summary, "manifest": manifest})
    if old_slug_present:
        category_bad.append("old construction_site_safety_complaint slug present")
    results.append(GateResult("A5-COMPLAINT-CATEGORY", "DOB complaint category map canonical", "a5", not category_bad, len(complaint_events), len(category_bad), category_bad[:4]))

    raw_node_bad = [
        node["id"]
        for node in proj_nodes
        if node.get("type") not in ALLOWED_A5_ENTITY_TYPES
        or ":raw:" in node.get("id", "")
        or node.get("id", "").startswith(("101", "102"))
    ]
    raw_relation_bad = [edge["relation"] for edge in proj_edges if edge.get("relation") not in ALLOWED_A5_RELATIONS]
    no_raw_ok = not raw_node_bad and not raw_relation_bad
    results.append(GateResult("A5-NO-RAW-GRAPH", "Projection has canonical graph nodes only", "a5", no_raw_ok, len(proj_nodes) + len(proj_edges), len(raw_node_bad) + len(raw_relation_bad), raw_node_bad[:3] + raw_relation_bad[:3]))

    prov_bad = []
    for record in [*entities, *edges]:
        if not dob_provenance(record):
            continue
        conf = record.get("confidence")
        provs = record.get("provenance", [])
        has_complete_dob_provenance = any(
            (p.get("source_dataset") or "").startswith("dob_")
            and p.get("source_id")
            and p.get("source_fields")
            for p in provs
        )
        if not conf or not has_complete_dob_provenance:
            prov_bad.append(record.get("canonical_id") or f"{record.get('src_ref')}->{record.get('dst_ref')}")
        if record.get("entity_type") == "permit" and not source_refs_ok(record):
            prov_bad.append(record["canonical_id"])
    results.append(GateResult("A5-PROVENANCE", "DOB provenance and confidence carried", "a5", not prov_bad, len(entities) + len(edges), len(prov_bad), prov_bad[:4]))

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
    results.append(GateResult("A5-PARTY-POLICY", "Uniform party license/name_hash policy", "a5", not party_bad, len([e for e in entities if e["entity_type"] == "party"]), len(party_bad), party_bad[:4]))

    trace_ok = a5_trace_bytes == a4_trace_bytes
    hero_edge_scores = {
        (edge["src_ref"], edge["dst_ref"], edge["relation"], edge.get("role")): (edge.get("confidence") or {}).get("score")
        for edge in edges
    }
    required_scores = {
        (HERO_COMPLAINT_ID, HERO_BUILDING_ID, "resolves_to", None): 0.95,
        (f"parcel:us-nyc:bbl:{HERO_BBL}", HERO_BUILDING_ID, "has_building", None): 1.0,
        (HERO_BUILDING_ID, HERO_PERMIT_ID, "subject_of_permit", None): 0.97,
        (HERO_PERMIT_ID, HERO_CONTRACTOR_ID, "performed_by", "contractor"): 0.95,
    }
    score_bad = [str(key) for key, score in required_scores.items() if hero_edge_scores.get(key) != score]
    hero_ok = trace_ok and not score_bad
    details = [] if hero_ok else (["A5 trace differs from A4 trace"] if not trace_ok else []) + score_bad
    results.append(GateResult("A5-HERO-STABILITY", "A4 hero traversal byte-for-byte stable", "a5", hero_ok, 1, 0 if hero_ok else 1, details))

    projection_ok = a4_report.all_green
    results.append(GateResult("A5-PROJECTION-FIDELITY", "A4 projection fidelity still passes", "a5", projection_ok, 1, 0 if projection_ok else 1, [f"A4 failed gates: {[r.gate_id for r in a4_report.results if not r.passed]}"] if not projection_ok else []))

    a5_report = HarnessReport(results)
    return a2_report, a4_report, a5_report


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_readme(summary: dict[str, Any], a5_report: HarnessReport, a4_report: HarnessReport) -> str:
    lines = [
        "# A5 DOB District Enrichment",
        "",
        BOUNDARY_STATEMENT,
        "",
        "## A5 status",
        "PASS" if a5_report.all_green else "FAIL",
        "",
        "## A4 regression status",
        "PASS" if a4_report.all_green else "FAIL",
        "",
        "## Counts",
        f"- parcels: {summary['parcel_count']}",
        f"- parcels with DOB activity: {summary['parcels_with_dob_activity']}",
        f"- raw DOB Permit Issuance rows attached after dedupe: {summary['permit_lifecycle_merge']['raw_dob_permit_issuance_rows']}",
        f"- raw DOB NOW filing rows attached after dedupe: {summary['permit_lifecycle_merge']['raw_dob_now_filing_rows']}",
        f"- unique Permit entities after merge: {summary['permit_lifecycle_merge']['unique_permit_entities_after_merge']}",
        f"- Permit entities with multiple source refs: {summary['permit_lifecycle_merge']['permits_with_multiple_source_refs']}",
        "",
        "## Complaint Resolution",
    ]
    for key, value in sorted(summary["complaint_resolution_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Parties"])
    for key, value in sorted(summary["parties_by_confidence_tier"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Edges"])
    for key, value in sorted(summary["edge_counts_by_relation"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Hero Parcel Enriched Profile",
        f"- BBL: {summary['hero_parcel_enriched_profile']['bbl']}",
        f"- DOB Permit Issuance records: {summary['hero_parcel_enriched_profile']['dob_permit_issuance_records']}",
        f"- DOB NOW job filings: {summary['hero_parcel_enriched_profile']['dob_now_job_filings']}",
        f"- DOB complaints: {summary['hero_parcel_enriched_profile']['dob_complaints']}",
        "",
        "## Category 91",
        f"- code 91 events: {summary['category_91_cascade_status']['code_91_events']}",
        f"- canonical type: {summary['category_91_cascade_status']['canonical_type']}",
        f"- old slug absent: {summary['category_91_cascade_status']['old_slug_absent']}",
        "",
        "## Known Limitations",
        "- DOB-only enrichment from the bounded harvested subset.",
        "- No footprints, 3D, LL84, public safety, resources, traffic, citywide graph, or GPU work included.",
        "",
        "## Recommended A6",
        "Operator query over the enriched district graph, with filters for DOB event category, permit lifecycle, party confidence, and parcel reachability.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    A5_DIR.mkdir(parents=True, exist_ok=True)
    A5_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    entities, edges, summary, manifest, a4_trace_bytes = build_enrichment()
    nodes, projection_edges = project_canonical(entities, edges)
    for edge in projection_edges:
        edge["edge_id"] = projection_edge_id(edge)

    a5_trace_path = A5_DIR / "scenario_trace_hero_flow.json"
    a5_trace_path.write_bytes(a4_trace_bytes)
    a5_trace_bytes = a5_trace_path.read_bytes()

    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False)
    summary_text = json.dumps(summary, indent=2, ensure_ascii=False)
    preliminary_readme = "\n".join(["# A5 DOB District Enrichment", "", BOUNDARY_STATEMENT])
    a2_report, a4_report, a5_report = run_a5_gate(
        entities,
        edges,
        nodes,
        projection_edges,
        manifest,
        summary,
        preliminary_readme + manifest_text + summary_text,
        a4_trace_bytes,
        a5_trace_bytes,
    )
    readme = write_readme(summary, a5_report, a4_report)
    a2_report, a4_report, a5_report = run_a5_gate(
        entities,
        edges,
        nodes,
        projection_edges,
        manifest,
        summary,
        readme,
        a4_trace_bytes,
        a5_trace_bytes,
    )

    pd.DataFrame(entity_rows(entities)).to_parquet(A5_DIR / "canonical_entities.parquet", index=False)
    pd.DataFrame(edge_rows(edges)).to_parquet(A5_DIR / "canonical_edges.parquet", index=False)
    pd.DataFrame([{"id": node["id"], "type": node["type"]} for node in nodes]).to_parquet(
        A5_DIR / "graph_projection_nodes.parquet",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "edge_id": edge["edge_id"],
                "src": edge["src"],
                "dst": edge["dst"],
                "relation": edge["relation"],
                "role": edge.get("role"),
                "confidence": edge.get("confidence"),
            }
            for edge in projection_edges
        ]
    ).to_parquet(A5_DIR / "graph_projection_edges.parquet", index=False)

    write_json(A5_DIR / "district_cut_manifest.json", manifest)
    write_json(A5_DIR / "a5_enrichment_summary.json", summary)
    (A5_DIR / "README.md").write_text(readme, encoding="utf-8")

    harness_report = {
        "subset_boundary_statement": BOUNDARY_STATEMENT,
        "a5_status": "PASS" if a5_report.all_green else "FAIL",
        "a4_regression_status": "PASS" if a4_report.all_green else "FAIL",
        "a2_preflight_status": "PASS" if a2_report.all_green else "FAIL",
        "exit_code": 0 if a5_report.all_green and a4_report.all_green and a2_report.all_green else 1,
        "summary": summary,
        "a2_report": gate_json(a2_report),
        "a4_report": gate_json(a4_report),
        "a5_report": gate_json(a5_report),
    }
    write_json(A5_DIR / "harness_report_a5.json", harness_report)

    snapshot = {
        "snapshot_id": "a5_district_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "subset_boundary_statement": BOUNDARY_STATEMENT,
        "status": {
            "a5": harness_report["a5_status"],
            "a4_regression": harness_report["a4_regression_status"],
            "a2_preflight": harness_report["a2_preflight_status"],
            "exit_code": harness_report["exit_code"],
        },
        "summary": summary,
        "artifact_paths": {
            "district_cut_manifest": "outputs/a5_dob_district_enrichment/district_cut_manifest.json",
            "canonical_entities": "outputs/a5_dob_district_enrichment/canonical_entities.parquet",
            "canonical_edges": "outputs/a5_dob_district_enrichment/canonical_edges.parquet",
            "graph_projection_nodes": "outputs/a5_dob_district_enrichment/graph_projection_nodes.parquet",
            "graph_projection_edges": "outputs/a5_dob_district_enrichment/graph_projection_edges.parquet",
            "harness_report": "outputs/a5_dob_district_enrichment/harness_report_a5.json",
            "scenario_trace": "outputs/a5_dob_district_enrichment/scenario_trace_hero_flow.json",
        },
    }
    write_json(A5_SNAPSHOT_DIR / "a5_district_v1.json", snapshot)

    print(f"A5 status: {harness_report['a5_status']}")
    print(f"A4 regression: {harness_report['a4_regression_status']}")
    print(f"A2 preflight: {harness_report['a2_preflight_status']}")
    print(f"Parcels with DOB activity: {summary['parcels_with_dob_activity']}/{summary['parcel_count']}")
    print(f"Permit entities after merge: {summary['permit_lifecycle_merge']['unique_permit_entities_after_merge']}")
    print(f"Complaint resolution: {summary['complaint_resolution_counts']}")
    print(f"Output: {A5_DIR}")
    return harness_report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
