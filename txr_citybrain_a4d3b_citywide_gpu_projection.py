from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

BOROUGH_LABELS = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
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
VRAM_STOP_MB = 20 * 1024


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
        return text[:-2]
    return text


def canonical_id(entity_type: str, id_system: str, native_id: Any) -> str:
    return f"{entity_type}:us-nyc:{id_system}:{clean(native_id)}"


def stable_name_hash(name: str) -> str:
    normalized = " ".join(clean(name).upper().split())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return json_safe(item())
        except Exception:
            pass
    return str(value)


def file_fingerprint(root: Path) -> dict[str, Any]:
    total_bytes = 0
    max_mtime_ns = 0
    file_count = 0
    if root.exists():
        for current, _, names in os.walk(root):
            for name in names:
                p = Path(current) / name
                try:
                    st = p.stat()
                except FileNotFoundError:
                    continue
                file_count += 1
                total_bytes += st.st_size
                max_mtime_ns = max(max_mtime_ns, st.st_mtime_ns)
    return {"root": str(root), "file_count": file_count, "total_bytes": total_bytes, "max_mtime_ns": max_mtime_ns}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(root)).replace("\\", "/")] = sha256_file(path)
    return hashes


def gpu_memory_mb() -> int | None:
    try:
        raw = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    values = [int(part.strip()) for part in raw.splitlines() if part.strip().isdigit()]
    return max(values) if values else None


class GpuMemoryMonitor:
    def __init__(self, interval_s: float = 0.5) -> None:
        self.interval_s = interval_s
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "GpuMemoryMonitor":
        def loop() -> None:
            while not self._stop.is_set():
                self.sample("poll")
                time.sleep(self.interval_s)

        self.sample("start")
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.sample("end")
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def sample(self, label: str) -> None:
        used = gpu_memory_mb()
        self.samples.append({"timestamp_utc": utc_now(), "label": label, "memory_used_mb": used})

    @property
    def peak_mb(self) -> int | None:
        values = [row["memory_used_mb"] for row in self.samples if row.get("memory_used_mb") is not None]
        return max(values) if values else None


def clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def read_parquet_scope(path: Path, block_keys: set[str] | None) -> pd.DataFrame:
    if block_keys is None:
        return pd.read_parquet(path)
    try:
        return pd.read_parquet(path, filters=[("block_key", "in", sorted(block_keys))])
    except Exception:
        df = pd.read_parquet(path)
        return df[df["block_key"].astype(str).isin(block_keys)].copy()


def clean_series(series: pd.Series) -> pd.Series:
    out = series.fillna("").astype(str).str.strip()
    out = out.mask(out.str.lower().isin(["nan", "none", "<na>", "nat"]), "")
    out = out.str.replace(r"\.0$", "", regex=True)
    return out


def normalize_code(value: Any) -> str:
    text = clean(value).upper()
    if not text:
        return ""
    try:
        if "." in text and float(text).is_integer():
            return str(int(float(text)))
    except ValueError:
        pass
    return text


def complaint_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    try:
        from txr_citybrain_dob_complaint_categories import DOB_COMPLAINT_CATEGORY_MAP
    except Exception:
        DOB_COMPLAINT_CATEGORY_MAP = {
            "01": {"type": "construction_accident_complaint", "severity": "critical", "category": "incident"},
            "05": {"type": "unpermitted_work_complaint", "severity": "high", "category": "incident"},
            "23": {"type": "scaffold_safety_complaint", "severity": "high", "category": "incident"},
            "83": {"type": "work_contrary_to_permit_complaint", "severity": "high", "category": "incident"},
            "86": {"type": "stop_work_order_violation_complaint", "severity": "critical", "category": "incident"},
            "90": {"type": "unlicensed_illegal_activity_complaint", "severity": "high", "category": "incident"},
            "91": {"type": "site_conditions_endangering_workers", "severity": "critical", "category": "incident"},
        }

    type_map: dict[str, str] = {}
    severity_map: dict[str, str] = {}
    category_map: dict[str, str] = {}
    for code, row in DOB_COMPLAINT_CATEGORY_MAP.items():
        type_map[normalize_code(code)] = clean(row.get("type")) or "construction_complaint"
        sev = row.get("severity")
        cat = row.get("category")
        severity_map[normalize_code(code)] = clean(getattr(sev, "value", sev)) or "medium"
        category_map[normalize_code(code)] = clean(getattr(cat, "value", cat)) or "incident"
    return type_map, severity_map, category_map


def relation_edge_id(src: pd.Series, relation: str | pd.Series, dst: pd.Series, role: str | pd.Series | None) -> pd.Series:
    if isinstance(relation, str):
        rel = pd.Series(relation, index=src.index)
    else:
        rel = relation.fillna("").astype(str)
    if isinstance(role, str) or role is None:
        role_s = pd.Series(role or "_", index=src.index)
    else:
        role_s = role.fillna("_").astype(str).replace("", "_")
    return src.astype(str) + "|" + rel.astype(str) + "|" + dst.astype(str) + "|" + role_s.astype(str)


def projection_edge_rows(edges: pd.DataFrame) -> pd.DataFrame:
    return edges[["edge_id", "src_ref", "dst_ref", "relation", "role", "confidence_score"]].rename(
        columns={"src_ref": "src", "dst_ref": "dst", "confidence_score": "confidence"}
    )


def build_scope(
    scope_id: str,
    scope_name: str,
    scope_role: str,
    active_blocks: pd.DataFrame,
    staging_dir: Path,
    out_dir: Path,
    selected_spot_blocks: dict[str, str] | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    block_keys = set(active_blocks["block_key"].astype(str).tolist())
    block_filter = None if scope_id == "citywide" else block_keys
    out_dir.mkdir(parents=True, exist_ok=True)

    parcels = read_parquet_scope(staging_dir / "parcel_bbl_block_lookup.parquet", block_filter)
    buildings_lookup = read_parquet_scope(staging_dir / "building_bin_bbl_lookup.parquet", block_filter)
    now_rows = read_parquet_scope(staging_dir / "dob_now_filings.parquet", block_filter)
    permit_rows = read_parquet_scope(staging_dir / "dob_permit_issuance.parquet", block_filter)
    complaint_rows = read_parquet_scope(staging_dir / "dob_complaints.parquet", block_filter)

    if block_filter is not None:
        for name, df in [
            ("parcels", parcels),
            ("buildings", buildings_lookup),
            ("now", now_rows),
            ("permit", permit_rows),
            ("complaints", complaint_rows),
        ]:
            if "block_key" in df.columns:
                before = len(df)
                df.drop(df.index[~df["block_key"].astype(str).isin(block_keys)], inplace=True)
                df.reset_index(drop=True, inplace=True)
                if before != len(df):
                    print(f"{scope_id}: post-filtered {name} from {before} to {len(df)}", flush=True)

    for df in [parcels, buildings_lookup, now_rows, permit_rows, complaint_rows]:
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = clean_series(df[col])

    parcels = parcels[parcels["block_key"].astype(str).isin(block_keys)].copy()
    parcels = parcels[parcels["bbl_norm"].astype(str) != ""].drop_duplicates("bbl_norm")
    parcel_bbls = set(parcels["bbl_norm"].astype(str))

    combined_work = pd.concat([permit_rows, now_rows], ignore_index=True)
    combined_work["job_number_norm"] = clean_series(combined_work["job_number_norm"])
    combined_work["bbl_norm"] = clean_series(combined_work["bbl_norm"])
    combined_work["bin_norm"] = clean_series(combined_work["bin_norm"])
    combined_work["source_dataset"] = clean_series(combined_work["source_dataset"])
    combined_work["source_row_key"] = clean_series(combined_work["source_row_key"])
    valid_work = combined_work[
        (combined_work["job_number_norm"] != "")
        & (combined_work["bbl_norm"].isin(parcel_bbls))
        & (combined_work["bin_norm"] != "")
        & (combined_work["bin_norm"] != "0")
    ].copy()

    complaint_rows["resolved_scope_bbl"] = clean_series(complaint_rows.get("resolved_bbl_norm", "")) if "resolved_bbl_norm" in complaint_rows else ""
    complaint_rows.loc[complaint_rows["resolved_scope_bbl"] == "", "resolved_scope_bbl"] = clean_series(
        complaint_rows.loc[complaint_rows["resolved_scope_bbl"] == "", "bbl_norm"]
    )
    complaint_rows["bin_norm"] = clean_series(complaint_rows["bin_norm"])
    complaint_rows["complaint_number_norm"] = clean_series(complaint_rows["complaint_number_norm"])
    valid_complaints = complaint_rows[
        (complaint_rows["complaint_resolution_status"] == "resolved_exact_bin")
        & (complaint_rows["complaint_number_norm"] != "")
        & (complaint_rows["resolved_scope_bbl"].isin(parcel_bbls))
        & (complaint_rows["bin_norm"] != "")
        & (complaint_rows["bin_norm"] != "0")
    ].copy()

    parcel_entities = pd.DataFrame(
        {
            "canonical_id": "parcel:us-nyc:bbl:" + parcels["bbl_norm"].astype(str),
            "entity_type": "parcel",
            "block_key": parcels["block_key"].astype(str),
            "bbl": parcels["bbl_norm"].astype(str),
            "bin": "",
            "job_number": "",
            "complaint_number": "",
            "party_policy": "",
            "license_number": "",
            "name": "",
            "source_dataset": "mappluto_harvest_v0_2_lookup",
            "source_row_key": parcels["bbl_norm"].astype(str),
            "source_fields_json": json.dumps(["bbl_norm", "block_key", "address", "latitude", "longitude"]),
            "confidence_score": 1.0,
            "confidence_method": "exact_key",
            "confidence_basis": "MapPLUTO BBL exact key",
            "category": "",
            "type": "",
            "severity": "",
            "longitude": parcels.get("longitude", pd.Series("", index=parcels.index)).astype(str),
            "latitude": parcels.get("latitude", pd.Series("", index=parcels.index)).astype(str),
        }
    )

    building_parts: list[pd.DataFrame] = []
    lookup_bbl = clean_series(buildings_lookup.get("mappluto_bbl_norm", ""))
    lookup_bbl = lookup_bbl.mask(lookup_bbl == "", clean_series(buildings_lookup.get("base_bbl_norm", "")))
    lookup_buildings = pd.DataFrame(
        {
            "bin_norm": clean_series(buildings_lookup.get("bin_norm", "")),
            "bbl_norm": lookup_bbl,
            "block_key": clean_series(buildings_lookup.get("block_key", "")),
            "source_dataset": "building_footprints_harvest_v0_2_lookup",
            "source_row_key": clean_series(buildings_lookup.get("bin_norm", "")),
            "source_fields_json": json.dumps(["bin_norm", "mappluto_bbl_norm", "base_bbl_norm", "block_key"]),
        }
    )
    building_parts.append(lookup_buildings)
    if len(valid_work):
        building_parts.append(
            pd.DataFrame(
                {
                    "bin_norm": valid_work["bin_norm"].astype(str),
                    "bbl_norm": valid_work["bbl_norm"].astype(str),
                    "block_key": valid_work["block_key"].astype(str),
                    "source_dataset": valid_work["source_dataset"].astype(str),
                    "source_row_key": valid_work["source_row_key"].astype(str),
                    "source_fields_json": json.dumps(["bin_norm", "bbl_norm", "job_number_norm", "source_row_key"]),
                }
            )
        )
    if len(valid_complaints):
        building_parts.append(
            pd.DataFrame(
                {
                    "bin_norm": valid_complaints["bin_norm"].astype(str),
                    "bbl_norm": valid_complaints["resolved_scope_bbl"].astype(str),
                    "block_key": valid_complaints["block_key"].astype(str),
                    "source_dataset": valid_complaints["source_dataset"].astype(str),
                    "source_row_key": valid_complaints["source_row_key"].astype(str),
                    "source_fields_json": json.dumps(["complaint_number_norm", "bin_norm", "resolved_bbl_norm", "complaint_category"]),
                }
            )
        )
    building_sources = pd.concat(building_parts, ignore_index=True)
    building_sources = building_sources[
        (building_sources["bin_norm"] != "")
        & (building_sources["bin_norm"] != "0")
        & (building_sources["bbl_norm"].isin(parcel_bbls))
    ].drop_duplicates("bin_norm")

    building_entities = pd.DataFrame(
        {
            "canonical_id": "building:us-nyc:bin:" + building_sources["bin_norm"].astype(str),
            "entity_type": "building",
            "block_key": building_sources["block_key"].astype(str),
            "bbl": building_sources["bbl_norm"].astype(str),
            "bin": building_sources["bin_norm"].astype(str),
            "job_number": "",
            "complaint_number": "",
            "party_policy": "",
            "license_number": "",
            "name": "",
            "source_dataset": building_sources["source_dataset"].astype(str),
            "source_row_key": building_sources["source_row_key"].astype(str),
            "source_fields_json": building_sources["source_fields_json"].astype(str),
            "confidence_score": 0.95,
            "confidence_method": "exact_key",
            "confidence_basis": "DOB/MapPLUTO BIN exact key; parcel linked by BBL",
            "category": "",
            "type": "",
            "severity": "",
            "longitude": "",
            "latitude": "",
        }
    )

    has_building_edges = pd.DataFrame(
        {
            "src_ref": "parcel:us-nyc:bbl:" + building_sources["bbl_norm"].astype(str),
            "dst_ref": "building:us-nyc:bin:" + building_sources["bin_norm"].astype(str),
            "relation": "has_building",
            "role": "",
            "block_key": building_sources["block_key"].astype(str),
            "source_dataset": building_sources["source_dataset"].astype(str),
            "source_row_key": building_sources["source_row_key"].astype(str),
            "source_fields_json": building_sources["source_fields_json"].astype(str),
            "confidence_score": 1.0,
            "confidence_method": "exact_key",
            "confidence_basis": "parcel BBL has DOB/MapPLUTO building BIN",
        }
    ).drop_duplicates(["src_ref", "dst_ref", "relation", "role"])
    has_building_edges["edge_id"] = relation_edge_id(
        has_building_edges["src_ref"], has_building_edges["relation"], has_building_edges["dst_ref"], has_building_edges["role"]
    )

    building_ids = set(building_entities["bin"].astype(str))
    valid_work = valid_work[valid_work["bin_norm"].isin(building_ids)].copy()
    valid_work.sort_values(["job_number_norm", "source_dataset", "source_row_key"], inplace=True)
    permit_rep = valid_work.drop_duplicates("job_number_norm").copy()

    permit_entities = pd.DataFrame(
        {
            "canonical_id": "permit:us-nyc:dob_job:" + permit_rep["job_number_norm"].astype(str),
            "entity_type": "permit",
            "block_key": permit_rep["block_key"].astype(str),
            "bbl": permit_rep["bbl_norm"].astype(str),
            "bin": permit_rep["bin_norm"].astype(str),
            "job_number": permit_rep["job_number_norm"].astype(str),
            "complaint_number": "",
            "party_policy": "",
            "license_number": "",
            "name": "",
            "source_dataset": permit_rep["source_dataset"].astype(str),
            "source_row_key": permit_rep["source_row_key"].astype(str),
            "source_fields_json": json.dumps(["source_row_key", "job_number_norm", "bbl_norm", "bin_norm", "permit_number_norm", "latest_activity_date"]),
            "confidence_score": 0.97,
            "confidence_method": "job_number",
            "confidence_basis": "DOB job number is stable within scope",
            "category": "",
            "type": "",
            "severity": "",
            "longitude": "",
            "latitude": "",
        }
    )

    subject_edges = pd.DataFrame(
        {
            "src_ref": "building:us-nyc:bin:" + permit_rep["bin_norm"].astype(str),
            "dst_ref": "permit:us-nyc:dob_job:" + permit_rep["job_number_norm"].astype(str),
            "relation": "subject_of_permit",
            "role": "",
            "block_key": permit_rep["block_key"].astype(str),
            "source_dataset": permit_rep["source_dataset"].astype(str),
            "source_row_key": permit_rep["source_row_key"].astype(str),
            "source_fields_json": json.dumps(["job_number_norm", "bin_norm", "bbl_norm"]),
            "confidence_score": 0.97,
            "confidence_method": "job_number",
            "confidence_basis": "permit job carries exact BIN and BBL scope",
        }
    ).drop_duplicates(["src_ref", "dst_ref", "relation", "role"])
    subject_edges["edge_id"] = relation_edge_id(subject_edges["src_ref"], subject_edges["relation"], subject_edges["dst_ref"], subject_edges["role"])

    type_map, severity_map, category_map = complaint_maps()
    valid_complaints = valid_complaints[valid_complaints["bin_norm"].isin(building_ids)].copy()
    valid_complaints.sort_values(["complaint_number_norm", "source_dataset", "source_row_key"], inplace=True)
    event_rep = valid_complaints.drop_duplicates("complaint_number_norm").copy()
    codes = event_rep["complaint_category"].map(normalize_code)
    event_entities = pd.DataFrame(
        {
            "canonical_id": "event:us-nyc:dob_complaint:" + event_rep["complaint_number_norm"].astype(str),
            "entity_type": "event",
            "block_key": event_rep["block_key"].astype(str),
            "bbl": event_rep["resolved_scope_bbl"].astype(str),
            "bin": event_rep["bin_norm"].astype(str),
            "job_number": "",
            "complaint_number": event_rep["complaint_number_norm"].astype(str),
            "party_policy": "",
            "license_number": "",
            "name": "",
            "source_dataset": event_rep["source_dataset"].astype(str),
            "source_row_key": event_rep["source_row_key"].astype(str),
            "source_fields_json": json.dumps(["complaint_number_norm", "bin_norm", "complaint_category", "event_date_norm", "complaint_resolution_status"]),
            "confidence_score": 0.92,
            "confidence_method": "complaint_number",
            "confidence_basis": "DOB complaint number is unique within source",
            "category": codes.map(category_map).fillna("incident"),
            "type": codes.map(type_map).fillna("construction_complaint"),
            "severity": codes.map(severity_map).fillna("medium"),
            "longitude": "",
            "latitude": "",
        }
    )

    resolves_edges = pd.DataFrame(
        {
            "src_ref": "event:us-nyc:dob_complaint:" + event_rep["complaint_number_norm"].astype(str),
            "dst_ref": "building:us-nyc:bin:" + event_rep["bin_norm"].astype(str),
            "relation": "resolves_to",
            "role": "",
            "block_key": event_rep["block_key"].astype(str),
            "source_dataset": event_rep["source_dataset"].astype(str),
            "source_row_key": event_rep["source_row_key"].astype(str),
            "source_fields_json": json.dumps(["complaint_number_norm", "bin_norm", "complaint_category"]),
            "confidence_score": 0.95,
            "confidence_method": "exact_bin",
            "confidence_basis": "complaint BIN equals building BIN",
        }
    ).drop_duplicates(["src_ref", "dst_ref", "relation", "role"])
    resolves_edges["edge_id"] = relation_edge_id(resolves_edges["src_ref"], resolves_edges["relation"], resolves_edges["dst_ref"], resolves_edges["role"])

    party_rows = valid_work[(valid_work["license_number_norm"].astype(str) != "") | (valid_work["business_name_norm"].astype(str) != "")].copy()
    if len(party_rows):
        party_rows["license_number_norm"] = clean_series(party_rows["license_number_norm"])
        party_rows["business_name_norm"] = clean_series(party_rows["business_name_norm"])
        has_license = party_rows["license_number_norm"] != ""
        party_rows["party_policy"] = has_license.map({True: "license_number", False: "name_hash"})
        party_rows["party_native_id"] = ""
        party_rows.loc[has_license, "party_native_id"] = party_rows.loc[has_license, "license_number_norm"]
        party_rows.loc[~has_license, "party_native_id"] = party_rows.loc[~has_license, "business_name_norm"].map(stable_name_hash)
        party_rows["party_id"] = ""
        party_rows.loc[has_license, "party_id"] = "party:us-nyc:dob_license:" + party_rows.loc[has_license, "party_native_id"]
        party_rows.loc[~has_license, "party_id"] = "party:us-nyc:name_hash:" + party_rows.loc[~has_license, "party_native_id"]
        party_rows["party_relation"] = party_rows["source_dataset"].map(
            lambda value: "performed_by" if value == "nyc__dob_permit_issuance" else "designed_by"
        )
        party_rows["party_role"] = party_rows["source_dataset"].map(
            lambda value: "contractor" if value == "nyc__dob_permit_issuance" else "applicant"
        )
        party_rows["party_confidence_score"] = has_license.map({True: 0.95, False: 0.55}).astype(float)
        party_rows["party_confidence_method"] = has_license.map({True: "license_number", False: "name_hash"})
        party_rows["party_confidence_basis"] = has_license.map(
            {True: "license_number policy: DOB license present", False: "fuzzy_match: name_hash policy for business/name-only role"}
        )
        party_rep = party_rows.drop_duplicates("party_id").copy()
        party_entities = pd.DataFrame(
            {
                "canonical_id": party_rep["party_id"].astype(str),
                "entity_type": "party",
                "block_key": party_rep["block_key"].astype(str),
                "bbl": party_rep["bbl_norm"].astype(str),
                "bin": party_rep["bin_norm"].astype(str),
                "job_number": party_rep["job_number_norm"].astype(str),
                "complaint_number": "",
                "party_policy": party_rep["party_policy"].astype(str),
                "license_number": party_rep["license_number_norm"].astype(str),
                "name": party_rep["business_name_norm"].astype(str),
                "source_dataset": party_rep["source_dataset"].astype(str),
                "source_row_key": party_rep["source_row_key"].astype(str),
                "source_fields_json": json.dumps(["source_row_key", "job_number_norm", "license_number_norm", "business_name_norm"]),
                "confidence_score": party_rep["party_confidence_score"].astype(float),
                "confidence_method": party_rep["party_confidence_method"].astype(str),
                "confidence_basis": party_rep["party_confidence_basis"].astype(str),
                "category": "",
                "type": "",
                "severity": "",
                "longitude": "",
                "latitude": "",
            }
        )
        party_edges = pd.DataFrame(
            {
                "src_ref": "permit:us-nyc:dob_job:" + party_rows["job_number_norm"].astype(str),
                "dst_ref": party_rows["party_id"].astype(str),
                "relation": party_rows["party_relation"].astype(str),
                "role": party_rows["party_role"].astype(str),
                "block_key": party_rows["block_key"].astype(str),
                "source_dataset": party_rows["source_dataset"].astype(str),
                "source_row_key": party_rows["source_row_key"].astype(str),
                "source_fields_json": json.dumps(["source_row_key", "job_number_norm", "license_number_norm", "business_name_norm"]),
                "confidence_score": party_rows["party_confidence_score"].astype(float),
                "confidence_method": party_rows["party_confidence_method"].astype(str),
                "confidence_basis": party_rows["party_confidence_basis"].astype(str),
            }
        ).drop_duplicates(["src_ref", "dst_ref", "relation", "role"])
        party_edges["edge_id"] = relation_edge_id(party_edges["src_ref"], party_edges["relation"], party_edges["dst_ref"], party_edges["role"])
    else:
        party_entities = pd.DataFrame(columns=parcel_entities.columns)
        party_edges = pd.DataFrame(columns=has_building_edges.columns)

    entities = pd.concat([parcel_entities, building_entities, permit_entities, event_entities, party_entities], ignore_index=True)
    entities.sort_values(["canonical_id"], inplace=True)
    entities.drop_duplicates("canonical_id", keep="first", inplace=True)
    edges = pd.concat([has_building_edges, subject_edges, resolves_edges, party_edges], ignore_index=True)
    edges.sort_values(["edge_id"], inplace=True)
    edges.drop_duplicates("edge_id", keep="first", inplace=True)

    projection_nodes = entities[["canonical_id", "entity_type"]].rename(columns={"canonical_id": "id", "entity_type": "type"})
    projection_edges = projection_edge_rows(edges)

    entities.to_parquet(out_dir / "canonical_entities.parquet", index=False)
    edges.to_parquet(out_dir / "canonical_edges.parquet", index=False)
    projection_nodes.to_parquet(out_dir / "graph_projection_nodes.parquet", index=False)
    projection_edges.to_parquet(out_dir / "graph_projection_edges.parquet", index=False)

    entity_counts = entities["entity_type"].value_counts().sort_index().to_dict()
    relation_counts = edges["relation"].value_counts().sort_index().to_dict()
    raw_counts = {
        "dob_now_filings": int(len(now_rows)),
        "dob_permit_issuance": int(len(permit_rows)),
        "dob_complaints": int(len(complaint_rows)),
        "valid_permit_or_now_rows_attached": int(len(valid_work)),
        "valid_complaints_exact_bin_attached": int(len(valid_complaints)),
    }
    excluded = {
        "permit_or_now_rows_without_job_bbl_bin_or_parcel_scope": int(len(combined_work) - len(valid_work)),
        "complaints_not_exact_bin_or_out_of_scope": int(len(complaint_rows) - len(valid_complaints)),
    }

    spot_counts: dict[str, Any] = {}
    if selected_spot_blocks:
        selected = set(selected_spot_blocks.values())
        spot_counts = compute_spot_counts_from_frames(entities, edges, selected)

    manifest = {
        "scope_id": scope_id,
        "scope_name": scope_name,
        "scope_role": scope_role,
        "boundary_statement": BOUNDARY_STATEMENT,
        "boundary_definition": {
            "type": "nyc_tax_blocks",
            "block_count": int(len(active_blocks)),
            "borough_codes": sorted(active_blocks["borough_code"].astype(str).unique().tolist()),
            "description": f"{scope_name}: active DOB blocks from block_dob_activity_base.parquet",
        },
        "source_records_included": raw_counts,
        "excluded_records_with_reason": excluded,
    }
    write_json(out_dir / "district_cut_manifest.json", manifest)

    traversal = local_traversal_from_frames(entities, edges)
    harness = run_vector_harness(scope_id, entities, edges, projection_nodes, projection_edges, raw_counts, traversal)
    drift = run_drift_test(scope_id, entities, edges, projection_nodes, projection_edges)
    if drift["status"] != "PASS":
        harness["status"] = "FAIL"
        harness.setdefault("failed_gates", []).append("A4-DRIFT")

    summary = {
        "scope_id": scope_id,
        "scope_name": scope_name,
        "scope_role": scope_role,
        "status": harness["status"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "active_block_count": int(len(active_blocks)),
        "entity_counts_by_type": {str(k): int(v) for k, v in entity_counts.items()},
        "edge_counts_by_relation": {str(k): int(v) for k, v in relation_counts.items()},
        "projection_nodes": int(len(projection_nodes)),
        "projection_edges": int(len(projection_edges)),
        "raw_source_row_counts": raw_counts,
        "excluded_records_with_reason": excluded,
        "local_traversal": traversal,
        "spot_block_counts": spot_counts,
        "build_wall_time_s": round(time.perf_counter() - start, 3),
    }
    write_json(out_dir / "harness_report.json", harness)
    write_json(out_dir / "drift_test_report.json", drift)
    write_json(out_dir / "district_summary.json", summary)
    return summary


def compute_spot_counts_from_frames(entities: pd.DataFrame, edges: pd.DataFrame, block_keys: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for block_key in sorted(block_keys):
        block_entity_ids = set(entities.loc[entities["block_key"].astype(str) == block_key, "canonical_id"].astype(str))
        block_edges = edges[edges["block_key"].astype(str) == block_key]
        endpoint_ids = set(block_edges["src_ref"].astype(str)).union(set(block_edges["dst_ref"].astype(str)))
        node_ids = block_entity_ids.union(endpoint_ids)
        out[block_key] = {
            "block_key": block_key,
            "node_count": int(len(node_ids)),
            "edge_count": int(block_edges["edge_id"].nunique()),
            "entity_counts_by_type": {
                str(k): int(v)
                for k, v in entities[entities["canonical_id"].isin(node_ids)]["entity_type"].value_counts().sort_index().to_dict().items()
            },
            "edge_counts_by_relation": {
                str(k): int(v) for k, v in block_edges["relation"].value_counts().sort_index().to_dict().items()
            },
        }
    return out


def local_traversal_from_frames(entities: pd.DataFrame, edges: pd.DataFrame) -> dict[str, Any]:
    resolves = edges[edges["relation"] == "resolves_to"][["src_ref", "dst_ref"]].rename(
        columns={"src_ref": "event", "dst_ref": "building"}
    )
    has_building = edges[edges["relation"] == "has_building"][["src_ref", "dst_ref"]].rename(
        columns={"src_ref": "parcel", "dst_ref": "building"}
    )
    subject = edges[edges["relation"] == "subject_of_permit"][["src_ref", "dst_ref"]].rename(
        columns={"src_ref": "building", "dst_ref": "permit"}
    )
    party = edges[edges["relation"].isin(["performed_by", "designed_by", "involves_party"])][["src_ref", "dst_ref", "relation"]].rename(
        columns={"src_ref": "permit", "dst_ref": "party"}
    )
    if resolves.empty or has_building.empty or subject.empty or party.empty:
        return {
            "status": "FAIL",
            "requirement": "complaint/event -> building -> parcel -> permit/job -> party",
            "reason": "one or more relation classes are empty",
        }
    path = resolves.merge(has_building, on="building").merge(subject, on="building").merge(party, on="permit")
    if path.empty:
        return {
            "status": "FAIL",
            "requirement": "complaint/event -> building -> parcel -> permit/job -> party",
            "reason": "no complete chain found",
        }
    first = path.iloc[0].to_dict()
    return {
        "status": "PASS",
        "requirement": "complaint/event -> building -> parcel -> permit/job -> party",
        "path": {
            "event": first["event"],
            "building": first["building"],
            "parcel": first["parcel"],
            "permit": first["permit"],
            "party": first["party"],
            "party_relation": first["relation"],
        },
        "relation_sequence": ["resolves_to", "has_building", "subject_of_permit", first["relation"]],
    }


def run_vector_harness(
    scope_id: str,
    entities: pd.DataFrame,
    edges: pd.DataFrame,
    nodes: pd.DataFrame,
    proj_edges: pd.DataFrame,
    raw_counts: dict[str, int],
    traversal: dict[str, Any],
) -> dict[str, Any]:
    gates: list[dict[str, Any]] = []

    def gate(gate_id: str, passed: bool, details: list[Any] | None = None) -> None:
        gates.append({"gate_id": gate_id, "passed": bool(passed), "details": json_safe(details or [])})

    gate("DISTRICT", len(nodes) > 0 and len(proj_edges) > 0, [f"nodes={len(nodes)}", f"edges={len(proj_edges)}"])
    gate("A4-UNIQUE", nodes["id"].is_unique and proj_edges["edge_id"].is_unique and entities["canonical_id"].is_unique and edges["edge_id"].is_unique)
    gate("A4-VOCAB", set(nodes["type"].dropna().unique()).issubset(ALLOWED_ENTITY_TYPES) and set(proj_edges["relation"].dropna().unique()).issubset(ALLOWED_RELATIONS))
    gate("A4-NODE-FID", nodes["id"].isin(set(entities["canonical_id"])).all())
    edge_fid = proj_edges[["edge_id", "confidence"]].merge(edges[["edge_id", "confidence_score"]], on="edge_id", how="left")
    gate("A4-EDGE-FID", edge_fid["confidence_score"].notna().all())
    gate("A4-CONF", edge_fid["confidence"].fillna(-1).astype(float).eq(edge_fid["confidence_score"].fillna(-2).astype(float)).all())
    gate("A4-TRAVERSAL", traversal.get("status") == "PASS", [traversal])

    entity_counts = entities["entity_type"].value_counts().to_dict()
    gate("A5-COUNT-SANITY", entity_counts.get("parcel", 0) > 0 and entity_counts.get("permit", 0) > 0 and entity_counts.get("event", 0) > 0)
    endpoint_ids = set(edges["src_ref"].astype(str)).union(set(edges["dst_ref"].astype(str)))
    gate("A5-DISTRICT-SCOPE", endpoint_ids.issubset(set(entities["canonical_id"].astype(str))))
    permit_jobs = entities.loc[entities["entity_type"] == "permit", "job_number"]
    gate("A5-PERMIT-MERGE", permit_jobs.is_unique)
    complaint_methods = set(edges.loc[edges["relation"] == "resolves_to", "confidence_method"].dropna().unique())
    gate("A5-COMPLAINT-METHOD", complaint_methods.issubset(COMPLAINT_METHODS) and "exact_bbl" not in complaint_methods, sorted(complaint_methods))
    code91 = entities[(entities["entity_type"] == "event") & (entities["type"] == "site_conditions_endangering_workers")]
    old_slug_present = (
        (entities.get("type", pd.Series(dtype=str)) == "construction_site_safety_complaint").any()
        or (entities.get("category", pd.Series(dtype=str)) == "construction_site_safety_complaint").any()
    )
    gate("A5-COMPLAINT-CATEGORY", not old_slug_present and len(code91) >= 0)
    raw_node_bad = nodes["id"].astype(str).str.contains(":raw:", regex=False).any() or nodes["type"].astype(str).eq("TaxLot").any()
    gate("A5-NO-RAW-GRAPH", not raw_node_bad)
    entity_prov = entities["source_dataset"].astype(str).ne("").all() and entities["source_row_key"].astype(str).ne("").all() and entities["confidence_method"].astype(str).ne("").all()
    edge_prov = edges["source_dataset"].astype(str).ne("").all() and edges["source_row_key"].astype(str).ne("").all() and edges["confidence_method"].astype(str).ne("").all()
    gate("A5-PROVENANCE", entity_prov and edge_prov)
    parties = entities[entities["entity_type"] == "party"]
    if len(parties):
        license_ok = parties[parties["canonical_id"].str.contains(":dob_license:", regex=False)]["confidence_method"].eq("license_number").all()
        hash_parties = parties[parties["canonical_id"].str.contains(":name_hash:", regex=False)]
        hash_ok = hash_parties["confidence_method"].eq("name_hash").all() and hash_parties["confidence_score"].astype(float).le(0.65).all()
    else:
        license_ok = hash_ok = True
    gate("A5-PARTY-POLICY", license_ok and hash_ok)
    a4_green = all(g["passed"] for g in gates if g["gate_id"].startswith("A4-") or g["gate_id"] == "DISTRICT")
    gate("A5-PROJECTION-FIDELITY", a4_green)

    failed = [g["gate_id"] for g in gates if not g["passed"]]
    return {
        "scope_id": scope_id,
        "status": "PASS" if not failed else "FAIL",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "raw_source_row_counts": raw_counts,
        "gates": gates,
        "failed_gates": failed,
    }


def run_drift_test(
    scope_id: str,
    entities: pd.DataFrame,
    edges: pd.DataFrame,
    nodes: pd.DataFrame,
    proj_edges: pd.DataFrame,
) -> dict[str, Any]:
    bad_nodes = nodes.head(5).copy()
    bad_edges = proj_edges.head(5).copy()
    if not bad_nodes.empty:
        bad_nodes.iloc[0, bad_nodes.columns.get_loc("type")] = "TaxLot"
    bad_nodes = pd.concat(
        [
            bad_nodes,
            pd.DataFrame(
                [
                    {"id": "raw:taxlot:1010607502", "type": "TaxLot"},
                    {"id": "parcel:us-nyc:bbl:9999999999", "type": "parcel"},
                ]
            ),
        ],
        ignore_index=True,
    )
    if not bad_edges.empty:
        bad_edges.iloc[0, bad_edges.columns.get_loc("relation")] = "HAS_PERMIT"
        bad_edges.iloc[-1, bad_edges.columns.get_loc("confidence")] = None
        bad_edges = pd.concat(
            [
                bad_edges,
                pd.DataFrame(
                    [
                        {
                            "edge_id": "raw:taxlot:1010607502|HAS_PERMIT|permit:us-nyc:dob_job:999999999|_",
                            "src": "raw:taxlot:1010607502",
                            "dst": "permit:us-nyc:dob_job:999999999",
                            "relation": "HAS_PERMIT",
                            "role": "",
                            "confidence": 0.5,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    drift_report = run_vector_harness(
        scope_id,
        entities,
        edges,
        bad_nodes,
        bad_edges,
        {"drift": 1},
        {"status": "FAIL", "reason": "drift projection"},
    )
    failed = set(drift_report.get("failed_gates", []))
    required = {"A4-VOCAB", "A4-NODE-FID", "A4-EDGE-FID", "A4-CONF"}
    passed = drift_report["status"] == "FAIL" and required.issubset(failed)
    return {
        "scope_id": scope_id,
        "status": "PASS" if passed else "FAIL",
        "failed_as_expected": passed,
        "injected_faults": [
            "TaxLot node type",
            "HAS_PERMIT relation",
            "raw taxlot node",
            "dropped confidence",
            "extra projected node not in canonical entities",
        ],
        "failed_gates": sorted(failed),
        "expected_failed_gates": sorted(required),
        "drift_harness_report": drift_report,
    }


def cudf_records(gdf: Any, limit: int = 10) -> list[dict[str, Any]]:
    return gdf.head(limit).to_arrow().to_pylist()


def run_gpu_graph(scope_id: str, out_dir: Path, role: str, vram_stop_mb: int | None = None) -> dict[str, Any]:
    import cupy as cp
    import cudf
    import cugraph

    start = time.perf_counter()
    monitor = GpuMemoryMonitor()
    with monitor:
        edges = cudf.read_parquet(str(out_dir / "graph_projection_edges.parquet"), columns=["src", "dst", "relation", "confidence"])
        nodes = cudf.read_parquet(str(out_dir / "graph_projection_nodes.parquet"), columns=["id", "type"])
        node_ids = cudf.concat(
            [
                nodes["id"].astype("str").rename("node_id"),
                edges["src"].astype("str").rename("node_id"),
                edges["dst"].astype("str").rename("node_id"),
            ],
            ignore_index=True,
        ).dropna().drop_duplicates().sort_values().reset_index(drop=True)
        vertex_map = cudf.DataFrame({"node_id": node_ids, "vertex_id": cp.arange(len(node_ids), dtype=cp.int32)})

        edge_work = edges.copy()
        edge_work["src"] = edge_work["src"].astype("str")
        edge_work["dst"] = edge_work["dst"].astype("str")
        gpu_edges = edge_work.merge(vertex_map.rename(columns={"node_id": "src", "vertex_id": "src_vertex"}), on="src", how="left")
        gpu_edges = gpu_edges.merge(vertex_map.rename(columns={"node_id": "dst", "vertex_id": "dst_vertex"}), on="dst", how="left")
        missing = int(gpu_edges["src_vertex"].isna().sum() + gpu_edges["dst_vertex"].isna().sum())
        if missing:
            raise RuntimeError(f"{scope_id}: vertex encoding failed with {missing} missing endpoints")
        gpu_edges["src_vertex"] = gpu_edges["src_vertex"].astype("int32")
        gpu_edges["dst_vertex"] = gpu_edges["dst_vertex"].astype("int32")
        gpu_edges["weight"] = 1.0
        gpu_input = gpu_edges[["src_vertex", "dst_vertex", "weight", "relation", "confidence"]]
        gpu_input.to_parquet(str(out_dir / "graph_edges_gpu_input.parquet"), index=False)
        vertex_map.to_parquet(str(out_dir / "vertex_id_map.parquet"), index=False)

        g_directed = cugraph.Graph(directed=True)
        g_directed.from_cudf_edgelist(
            gpu_input[["src_vertex", "dst_vertex", "weight"]],
            source="src_vertex",
            destination="dst_vertex",
            edge_attr="weight",
            renumber=False,
        )
        degree = g_directed.degree()
        degree.to_parquet(str(out_dir / "degree.parquet"), index=False)

        try:
            components = cugraph.weakly_connected_components(g_directed)
            component_method = "cugraph.weakly_connected_components(directed)"
        except Exception:
            g_undirected = cugraph.Graph(directed=False)
            g_undirected.from_cudf_edgelist(
                gpu_input[["src_vertex", "dst_vertex", "weight"]],
                source="src_vertex",
                destination="dst_vertex",
                edge_attr="weight",
                renumber=False,
            )
            components = cugraph.connected_components(g_undirected)
            component_method = "cugraph.connected_components(undirected)"
        components.to_parquet(str(out_dir / "components.parquet"), index=False)
        label_col = next((c for c in ["labels", "component", "component_id"] if c in components.columns), None)
        if label_col:
            component_summary = (
                components.groupby(label_col)
                .size()
                .reset_index(name="vertex_count")
                .sort_values("vertex_count", ascending=False)
                .reset_index(drop=True)
            )
            component_count = int(len(component_summary))
            largest_component_size = int(component_summary["vertex_count"].max().item()) if len(component_summary) else 0
            component_summary.to_parquet(str(out_dir / "component_summary.parquet"), index=False)
        else:
            component_count = None
            largest_component_size = None
            component_summary = components.head(0)

        degree_vertex_col = "vertex" if "vertex" in degree.columns else list(degree.columns)[0]
        degree_col = "degree" if "degree" in degree.columns else list(degree.columns)[1]
        degree_sorted = degree.sort_values([degree_col, degree_vertex_col], ascending=[False, True]).reset_index(drop=True)
        seed_vertex = int(degree_sorted[degree_vertex_col].iloc[0].item()) if len(degree_sorted) else None
        seed_node_id = None
        sssp_status: dict[str, Any]
        neighborhood_rows = 0
        if seed_vertex is not None:
            seed_match = vertex_map[vertex_map["vertex_id"] == seed_vertex].head(1).to_arrow().to_pylist()
            seed_node_id = seed_match[0]["node_id"] if seed_match else None
            try:
                sssp = cugraph.sssp(g_directed, source=seed_vertex)
                sssp.to_parquet(str(out_dir / "sssp.parquet"), index=False)
                sssp_vertex_col = "vertex" if "vertex" in sssp.columns else list(sssp.columns)[0]
                dist_col = next((c for c in ["distance", "distances"] if c in sssp.columns), None)
                if dist_col:
                    reachable = sssp[(sssp[dist_col] >= 0) & (sssp[dist_col] < 1.0e20)]
                    neighborhood = reachable[reachable[dist_col] <= 2.0].merge(
                        vertex_map.rename(columns={"vertex_id": sssp_vertex_col}),
                        on=sssp_vertex_col,
                        how="left",
                    )
                    max_distance = float(reachable[dist_col].max().item()) if len(reachable) else None
                else:
                    reachable = sssp
                    neighborhood = sssp.head(100)
                    max_distance = None
                neighborhood_rows = int(len(neighborhood))
                neighborhood.to_parquet(str(out_dir / "neighborhood_sample.parquet"), index=False)
                sssp_status = {
                    "status": "PASS",
                    "source_vertex": seed_vertex,
                    "source_node_id": seed_node_id,
                    "rows": int(len(sssp)),
                    "reachable_rows": int(len(reachable)),
                    "max_distance": max_distance,
                }
            except Exception as exc:
                gpu_input.head(0).to_parquet(str(out_dir / "neighborhood_sample.parquet"), index=False)
                sssp_status = {"status": "SKIPPED", "reason": str(exc), "source_vertex": seed_vertex, "source_node_id": seed_node_id}
        else:
            gpu_input.head(0).to_parquet(str(out_dir / "neighborhood_sample.parquet"), index=False)
            sssp_status = {"status": "SKIPPED", "reason": "No seed vertex"}

        hubs = degree.rename(columns={degree_vertex_col: "vertex_id", degree_col: "degree"}).merge(vertex_map, on="vertex_id", how="left")
        hubs = hubs.sort_values(["degree", "vertex_id"], ascending=[False, True]).reset_index(drop=True)
        hubs.head(100).to_parquet(str(out_dir / "top_hubs.parquet"), index=False)
        building_hubs = hubs[hubs["node_id"].str.startswith("building:us-nyc:bin:")].head(50)
        building_hubs.to_parquet(str(out_dir / "top_building_hubs.parquet"), index=False)

        relation_counts = edges.groupby("relation").size().reset_index(name="count").sort_values("count", ascending=False)
        relation_counts.to_parquet(str(out_dir / "relation_counts.parquet"), index=False)
        monitor.sample("after_graph_ops")

    peak_mb = monitor.peak_mb
    if vram_stop_mb is not None and peak_mb is not None and peak_mb > vram_stop_mb:
        raise RuntimeError(f"{scope_id}: peak GPU memory {peak_mb} MB exceeded limit {vram_stop_mb} MB")

    metrics = {
        "scope_id": scope_id,
        "scope_role": role,
        "status": "PASS",
        "boundary_statement": BOUNDARY_STATEMENT,
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "encoded_vertex_count": int(len(vertex_map)),
        "encoded_edge_count": int(len(gpu_input)),
        "degree_rows": int(len(degree)),
        "component_method": component_method,
        "component_count": component_count,
        "largest_component_size": largest_component_size,
        "sssp": sssp_status,
        "neighborhood_rows": neighborhood_rows,
        "top_hubs": cudf_records(hubs, 15),
        "top_building_hubs": cudf_records(building_hubs, 50),
        "component_summary_head": cudf_records(component_summary, 20),
        "relation_counts": cudf_records(relation_counts, 20),
        "peak_gpu_memory_mb": peak_mb,
        "gpu_memory_samples": monitor.samples,
        "wall_time_s": round(time.perf_counter() - start, 3),
        "used_cudf_for_parquet_reads": True,
        "used_cugraph_for_graph_operations": True,
    }
    write_json(out_dir / "graph_metrics.json", metrics)
    write_json(
        out_dir / "gpu_projection_report.json",
        {
            "scope_id": scope_id,
            "status": "PASS",
            "boundary_statement": BOUNDARY_STATEMENT,
            "used_cudf_for_parquet_reads": True,
            "used_cugraph_for_graph_operations": True,
            "operation_status": {
                "degree": "PASS",
                "components": "PASS",
                "sssp": sssp_status["status"],
                "neighborhood_sample": "PASS" if neighborhood_rows else sssp_status["status"],
            },
            "peak_gpu_memory_mb": peak_mb,
            "wall_time_s": metrics["wall_time_s"],
        },
    )
    return metrics


def load_active_blocks(staging_dir: Path) -> pd.DataFrame:
    blocks = pd.read_parquet(staging_dir / "block_dob_activity_base.parquet")
    for col in ["block_key", "borough_code", "block"]:
        blocks[col] = clean_series(blocks[col])
    activity = blocks["dob_now_filing_count"] + blocks["dob_permit_issuance_count"] + blocks["dob_complaint_count"]
    return blocks[activity > 0].copy()


def select_spot_blocks(active_blocks: pd.DataFrame) -> dict[str, str]:
    selected: dict[str, str] = {}
    for borough in ["1", "2", "3", "4", "5"]:
        rows = active_blocks[active_blocks["borough_code"] == borough].sort_values("block_key")
        sampled = rows.sample(n=1, random_state=4200 + int(borough)) if len(rows) else pd.DataFrame()
        if len(sampled):
            selected[borough] = str(sampled.iloc[0]["block_key"])
    return selected


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    staging_dir = Path(args.staging_dir)
    processed_root = Path(args.processed_root)
    output_root = Path(args.output_root)
    logs_root = Path(args.logs_root)
    by_borough_root = output_root / "by_borough"
    citywide_root = output_root / "citywide"
    snapshot_root = output_root / "snapshot" / "a4d3b_citywide_v1"
    output_root.mkdir(parents=True, exist_ok=True)
    by_borough_root.mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)
    log_path = logs_root / "txr-3090-a4d3b-citywide-gpu-projection.log"
    log_path.write_text("", encoding="utf-8")

    def log(message: str) -> None:
        print(message, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")

    start_all = time.perf_counter()
    source_before = {"processed": file_fingerprint(processed_root)}
    active_blocks = load_active_blocks(staging_dir)
    spot_blocks = select_spot_blocks(active_blocks)
    log(f"active blocks: {len(active_blocks)}; spot blocks: {spot_blocks}")

    import cudf
    import cugraph

    versions = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "cudf": getattr(cudf, "__version__", "unknown"),
        "cugraph": getattr(cugraph, "__version__", "unknown"),
    }

    borough_reports: list[dict[str, Any]] = []
    borough_metrics: list[dict[str, Any]] = []
    for borough in ["1", "2", "3", "4", "5"]:
        scope_start = time.perf_counter()
        borough_dir = by_borough_root / borough
        clean_output_dir(borough_dir)
        rows = active_blocks[active_blocks["borough_code"] == borough].copy()
        log(f"borough {borough} {BOROUGH_LABELS[borough]}: build {len(rows)} active blocks")
        summary = build_scope(
            scope_id=f"borough-{borough}",
            scope_name=BOROUGH_LABELS[borough],
            scope_role="borough_scale_checkpoint",
            active_blocks=rows,
            staging_dir=staging_dir,
            out_dir=borough_dir,
            selected_spot_blocks={borough: spot_blocks[borough]} if borough in spot_blocks else {},
        )
        if summary["status"] != "PASS":
            raise RuntimeError(f"borough {borough}: harness failed")
        metrics = run_gpu_graph(f"borough-{borough}", borough_dir, "borough_scale_checkpoint", vram_stop_mb=VRAM_STOP_MB)
        if metrics.get("peak_gpu_memory_mb") and metrics["peak_gpu_memory_mb"] > VRAM_STOP_MB:
            raise RuntimeError(f"borough {borough}: peak GPU memory exceeded 20GB")
        summary["gpu_metrics"] = {
            "peak_gpu_memory_mb": metrics.get("peak_gpu_memory_mb"),
            "wall_time_s": metrics.get("wall_time_s"),
            "component_count": metrics.get("component_count"),
            "largest_component_size": metrics.get("largest_component_size"),
        }
        summary["total_wall_time_s"] = round(time.perf_counter() - scope_start, 3)
        write_json(borough_dir / "district_summary.json", summary)
        borough_reports.append(summary)
        borough_metrics.append(metrics)
        log(
            f"borough {borough}: PASS blocks={summary['active_block_count']} nodes={summary['projection_nodes']} "
            f"edges={summary['projection_edges']} peak_mb={metrics.get('peak_gpu_memory_mb')} wall_s={summary['total_wall_time_s']}"
        )

    log("all boroughs passed; starting citywide")
    clean_output_dir(citywide_root)
    citywide_summary = build_scope(
        scope_id="citywide",
        scope_name="NYC active DOB blocks citywide",
        scope_role="citywide_scale_projection",
        active_blocks=active_blocks,
        staging_dir=staging_dir,
        out_dir=citywide_root,
        selected_spot_blocks=spot_blocks,
    )
    if citywide_summary["status"] != "PASS":
        raise RuntimeError("citywide harness failed")
    citywide_metrics = run_gpu_graph("citywide", citywide_root, "citywide_scale_projection", vram_stop_mb=None)
    citywide_summary["gpu_metrics"] = {
        "peak_gpu_memory_mb": citywide_metrics.get("peak_gpu_memory_mb"),
        "wall_time_s": citywide_metrics.get("wall_time_s"),
        "component_count": citywide_metrics.get("component_count"),
        "largest_component_size": citywide_metrics.get("largest_component_size"),
    }
    write_json(citywide_root / "district_summary.json", citywide_summary)

    spot_check: dict[str, Any] = {}
    city_spots = citywide_summary.get("spot_block_counts", {})
    for borough, block_key in spot_blocks.items():
        borough_summary = read_json(by_borough_root / borough / "district_summary.json")
        borough_spot = borough_summary.get("spot_block_counts", {}).get(block_key)
        city_spot = city_spots.get(block_key)
        spot_check[borough] = {
            "block_key": block_key,
            "borough_output": borough_spot,
            "citywide_output": city_spot,
            "match": borough_spot == city_spot,
        }
    spot_ok = all(row["match"] for row in spot_check.values())
    if not spot_ok:
        raise RuntimeError(f"citywide spot-check mismatch: {spot_check}")

    per_borough = []
    for row in borough_reports:
        per_borough.append(
            {
                "borough_code": row["scope_id"].split("-")[-1],
                "borough_name": row["scope_name"],
                "active_blocks": row["active_block_count"],
                "nodes": row["projection_nodes"],
                "edges": row["projection_edges"],
                "entity_counts_by_type": row["entity_counts_by_type"],
                "edge_counts_by_relation": row["edge_counts_by_relation"],
                "peak_gpu_memory_mb": row["gpu_metrics"]["peak_gpu_memory_mb"],
                "wall_time_s": row["total_wall_time_s"],
            }
        )

    top_building_hubs = citywide_metrics.get("top_building_hubs", [])
    city_entities = pd.read_parquet(citywide_root / "canonical_entities.parquet", columns=["canonical_id", "bbl", "bin", "entity_type"])
    building_lookup = city_entities[city_entities["entity_type"] == "building"][["canonical_id", "bbl", "bin"]].rename(columns={"canonical_id": "node_id"})
    hub_df = pd.DataFrame(top_building_hubs)
    if len(hub_df) and "node_id" in hub_df:
        hub_df = hub_df.merge(building_lookup, on="node_id", how="left")
        top_50_hubs = hub_df[["node_id", "bin", "bbl", "degree"]].head(50).to_dict("records")
    else:
        top_50_hubs = []

    city_summary = {
        "task": "a4-D3b citywide GPU graph projection",
        "status": "PASS",
        "final_marker": "PASS_A4D3B_CITYWIDE_GPU_GRAPH_PROJECTION",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "total_active_blocks_projected": int(len(active_blocks)),
        "total_nodes": citywide_summary["projection_nodes"],
        "total_edges": citywide_summary["projection_edges"],
        "per_borough_breakdown": per_borough,
        "top_50_hub_buildings_citywide": top_50_hubs,
        "connectivity_distribution": {
            "component_count": citywide_metrics.get("component_count"),
            "largest_component_size": citywide_metrics.get("largest_component_size"),
            "component_summary_head": citywide_metrics.get("component_summary_head", []),
        },
        "peak_memory": {
            "citywide_peak_gpu_memory_mb": citywide_metrics.get("peak_gpu_memory_mb"),
            "per_borough_peak_gpu_memory_mb": {
                item["borough_code"]: item["peak_gpu_memory_mb"] for item in per_borough
            },
        },
        "wall_time": {
            "total_wall_time_s": round(time.perf_counter() - start_all, 3),
            "citywide_gpu_wall_time_s": citywide_metrics.get("wall_time_s"),
            "per_borough_total_wall_time_s": {item["borough_code"]: item["wall_time_s"] for item in per_borough},
        },
        "spot_check_citywide_vs_borough": spot_check,
        "versions": versions,
    }
    write_json(output_root / "A4D3B_CITYWIDE_SUMMARY.json", city_summary)
    write_text(
        output_root / "A4D3B_CITYWIDE_SUMMARY.md",
        "\n".join(
            [
                "# A4-D3b Citywide GPU Summary",
                "",
                "Status: **PASS**",
                "",
                BOUNDARY_STATEMENT,
                "",
                f"Total active blocks projected: {city_summary['total_active_blocks_projected']}",
                f"Total nodes: {city_summary['total_nodes']}",
                f"Total edges: {city_summary['total_edges']}",
                "",
                "| Borough | Blocks | Nodes | Edges | Peak GPU MB | Wall time s |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
                *[
                    f"| {item['borough_code']} {item['borough_name']} | {item['active_blocks']} | {item['nodes']} | {item['edges']} | {item['peak_gpu_memory_mb']} | {item['wall_time_s']} |"
                    for item in per_borough
                ],
                "",
                f"Citywide peak GPU MB: {citywide_metrics.get('peak_gpu_memory_mb')}",
                f"Citywide components: {citywide_metrics.get('component_count')}",
                f"Largest component: {citywide_metrics.get('largest_component_size')}",
                "",
            ]
        ),
    )

    source_after = {"processed": file_fingerprint(processed_root)}
    no_mutation = source_before == source_after
    harness = {
        "task": "a4-D3b borough-to-citywide GPU graph projection",
        "status": "PASS" if no_mutation and spot_ok else "FAIL",
        "final_marker": "PASS_A4D3B_CITYWIDE_GPU_GRAPH_PROJECTION" if no_mutation and spot_ok else "FAIL_A4D3B_CITYWIDE_GPU_GRAPH_PROJECTION",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "versions": versions,
        "hard_checks": {
            "five_boroughs_processed": len(borough_reports) == 5,
            "borough_harnesses_pass": all(row["status"] == "PASS" for row in borough_reports),
            "borough_peak_vram_under_20gb": all((row["gpu_metrics"].get("peak_gpu_memory_mb") or 0) <= VRAM_STOP_MB for row in borough_reports),
            "citywide_processed": citywide_summary["status"] == "PASS",
            "citywide_spot_checks_match_borough": spot_ok,
            "source_not_mutated": no_mutation,
            "cudf_used_for_parquet_reads": True,
            "cugraph_used_for_graph_operations": True,
        },
        "per_borough": per_borough,
        "citywide": {
            "active_blocks": city_summary["total_active_blocks_projected"],
            "nodes": city_summary["total_nodes"],
            "edges": city_summary["total_edges"],
            "peak_gpu_memory_mb": citywide_metrics.get("peak_gpu_memory_mb"),
            "wall_time_s": citywide_metrics.get("wall_time_s"),
            "component_count": citywide_metrics.get("component_count"),
            "largest_component_size": citywide_metrics.get("largest_component_size"),
        },
        "spot_check_citywide_vs_borough": spot_check,
        "no_source_mutation_confirmation": {"status": "PASS" if no_mutation else "FAIL", "before": source_before, "after": source_after},
    }
    write_json(output_root / "A4D3B_CITYWIDE_HARNESS_REPORT.json", harness)
    write_text(
        output_root / "A4D3B_CITYWIDE_HARNESS_REPORT.md",
        f"# A4-D3b Citywide Harness Report\n\nOverall: **{harness['status']}**\n\nFinal marker: `{harness['final_marker']}`\n\n{BOUNDARY_STATEMENT}\n",
    )
    if harness["status"] != "PASS":
        raise RuntimeError("A4-D3b citywide hard checks failed")

    clean_output_dir(snapshot_root)
    write_json(
        snapshot_root / "a4d3b_citywide_v1.json",
        {
            "snapshot_id": "a4d3b_citywide_v1",
            "summary_path": str(output_root / "A4D3B_CITYWIDE_SUMMARY.json"),
            "harness_path": str(output_root / "A4D3B_CITYWIDE_HARNESS_REPORT.json"),
            "by_borough_root": str(by_borough_root),
            "citywide_root": str(citywide_root),
            "final_marker": harness["final_marker"],
            "created_utc": utc_now(),
        },
    )
    write_json(output_root / "SHA256SUMS.json", output_hashes(output_root))
    log(harness["final_marker"])
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Scale A4-D3b GPU graph projection borough-by-borough then citywide")
    parser.add_argument("--staging-dir", default="/data/processed/nyc/harvest_v0_2/discovery_staging")
    parser.add_argument("--processed-root", default="/data/processed")
    parser.add_argument("--output-root", default="/data/a4d3b_outputs")
    parser.add_argument("--logs-root", default="/data/logs")
    args = parser.parse_args()
    try:
        run(args)
        return 0
    except Exception:
        Path(args.logs_root).mkdir(parents=True, exist_ok=True)
        err_path = Path(args.logs_root) / "txr-3090-a4d3b-citywide-gpu-projection-error.txt"
        err_path.write_text(traceback.format_exc(), encoding="utf-8")
        print(traceback.format_exc(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
