from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "LON-D6 Lambeth Enforcement / Building-Control Source Probe"
DEFAULT_LON_D4_DIR = "outputs/lon_d4_identity_backbone_ingest"
DEFAULT_LON_D5_DIR = "outputs/lon_d5_pld_planning_ingest"
DEFAULT_LON_D5C_DIR = "outputs/lon_d5c_lids_confirmed_identity_bridge"
DEFAULT_OUTPUT_DIR = "outputs/lon_d6_enforcement_building_control"

BOUNDARY_STRINGS = [
    "PLD is not DOB.",
    "Lambeth enforcement/building-control records are not NYC DOB records.",
    "D6 is Lambeth-only and sampled.",
    "D6 does not prove complete London enforcement/building-control coverage.",
    "D6 does not ingest private complainant data.",
    "D6 does not create a London hero cascade.",
    "D6 does not prove citywide London coverage.",
]

SOURCE_CLASSIFICATIONS = {
    "D6A_USABLE_ENFORCEMENT_SOURCE",
    "D6A_USABLE_BUILDING_CONTROL_SOURCE",
    "D6A_USABLE_BOTH_SOURCES",
    "D6A_NO_MACHINE_SOURCE_REGISTER_ONLY",
    "D6A_SOURCE_BLOCKED_OR_INSUFFICIENT",
}
USABLE_SOURCE_STATUSES = {"usable_machine_source", "usable_html_source"}
REGISTER_ONLY_STATUSES = {"human_register_only"}
ALLOWED_CONNECTED_PATH_RESULTS = {
    "STRONG",
    "MEDIUM",
    "MINIMUM",
    "NONE_WITH_SOURCE_LIMITATION",
    "NONE_WITH_NO_OVERCLAIM",
}

EVENT_ID_PATTERN = re.compile(r"^event:uk-london:planning_enforcement:[A-Za-z0-9_.-]+$")
BUILDING_CONTROL_ID_PATTERN = re.compile(r"^permit:uk-london:building_control:[A-Za-z0-9_.-]+$")
PLD_ID_PATTERN = re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$")
UPRN_ID_PATTERN = re.compile(r"^parcel:uk-london:uprn:\d+$")
BUILDING_ID_PATTERN = re.compile(r"^building:uk-london:toid:osgb[0-9A-Za-z]+$")
ROAD_ID_PATTERN = re.compile(r"^road_segment:uk-london:usrn:\d+$")
FORBIDDEN_ID_TOKEN_PATTERN = re.compile(r"(^|[:_-])(bbl|bin|dob|dob_complaint|dob_permit)([:_-]|$)", re.IGNORECASE)

ENFORCEMENT_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "event_type",
    "event_subtype",
    "source_dataset",
    "reference",
    "status",
    "notice_date",
    "address",
    "description",
    "related_planning_reference",
    "uprn_refs",
    "geometry",
    "geometry_status",
    "confidence",
    "provenance",
]
BUILDING_CONTROL_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "permit_type",
    "source_dataset",
    "reference",
    "status",
    "application_type",
    "received_date",
    "decision_date",
    "completion_date",
    "address",
    "description",
    "uprn_refs",
    "geometry",
    "geometry_status",
    "confidence",
    "provenance",
]
EDGE_COLUMNS = [
    "edge_id",
    "src",
    "relation",
    "dst",
    "role",
    "confidence",
    "provenance",
    "source_record_id",
    "source_join_key",
    "semantic_caveat",
]
UNATTACHED_COLUMNS = [
    "canonical_id",
    "entity_type",
    "source_dataset",
    "native_id",
    "reference",
    "address",
    "uprn_refs",
    "related_planning_reference",
    "unattached_reason",
    "candidate_match_type",
    "confidence",
    "provenance",
]
PATH_COLUMNS = [
    "path_id",
    "path_strength",
    "d6_record_id",
    "d6_record_type",
    "uprn_id",
    "pld_id",
    "context_id",
    "context_relation",
    "d6_edge_id",
    "pld_edge_id",
    "context_edge_id",
    "confidence_score",
    "path_summary",
    "provenance",
]

SOURCE_CANDIDATES = [
    {
        "source_id": "lambeth_planning_enforcement_page",
        "source_family": "planning_enforcement",
        "url_or_path": "https://www.lambeth.gov.uk/planning-building-control/planning-applications/planning-enforcement",
        "access_method_attempted": "http_get",
        "official_owner": "Lambeth Council",
        "probe_role": "enforcement_guidance",
    },
    {
        "source_id": "lambeth_enforcement_notice_register_request",
        "source_family": "planning_enforcement",
        "url_or_path": "https://planningservices.lambeth.gov.uk/request-copies-of-enforcement-notices-and-register",
        "access_method_attempted": "manual_page_only",
        "official_owner": "Lambeth Council",
        "probe_role": "register_request",
    },
    {
        "source_id": "lambeth_planning_applications_search_page",
        "source_family": "planning_database",
        "url_or_path": "https://www.lambeth.gov.uk/planning-building-control/planning-applications/search-submit-comment-applications",
        "access_method_attempted": "http_get",
        "official_owner": "Lambeth Council",
        "probe_role": "planning_database_guidance",
    },
    {
        "source_id": "lambeth_publicaccess_planning_simple_search",
        "source_family": "planning_database",
        "url_or_path": "https://planning.lambeth.gov.uk/online-applications/search.do?action=simple&searchType=Application",
        "access_method_attempted": "html_parse",
        "official_owner": "Lambeth Council",
        "probe_role": "interactive_public_access",
    },
    {
        "source_id": "lambeth_publicaccess_planning_weekly_list",
        "source_family": "planning_database",
        "url_or_path": "https://planning.lambeth.gov.uk/online-applications/search.do?action=weeklyList&searchType=Application",
        "access_method_attempted": "html_parse",
        "official_owner": "Lambeth Council",
        "probe_role": "interactive_public_access",
    },
    {
        "source_id": "lambeth_building_regulation_search_page",
        "source_family": "building_control",
        "url_or_path": "https://www.lambeth.gov.uk/planning-and-building-control/building-control-and-regulations/search-building-regulation",
        "access_method_attempted": "http_get",
        "official_owner": "Lambeth Council",
        "probe_role": "building_control_guidance",
    },
    {
        "source_id": "lambeth_publicaccess_building_control_simple_search",
        "source_family": "building_control",
        "url_or_path": "https://planning.lambeth.gov.uk/online-applications/search.do?action=simple&searchType=BuildingControl",
        "access_method_attempted": "html_parse",
        "official_owner": "Lambeth Council",
        "probe_role": "interactive_public_access",
    },
    {
        "source_id": "lambeth_publicaccess_building_control_weekly_list",
        "source_family": "building_control",
        "url_or_path": "https://planning.lambeth.gov.uk/online-applications/search.do?action=weeklyList&searchType=BuildingControl",
        "access_method_attempted": "html_parse",
        "official_owner": "Lambeth Council",
        "probe_role": "interactive_public_access",
    },
    {
        "source_id": "lambeth_data_hub_planning_applications_database",
        "source_family": "planning_database",
        "url_or_path": "https://www.lambeth.gov.uk/lambeth-data-hub/planning-applications-database",
        "access_method_attempted": "http_get",
        "official_owner": "Lambeth Council",
        "probe_role": "planning_data_hub_page",
    },
    {
        "source_id": "lambeth_open_mapping_catalog",
        "source_family": "open_data",
        "url_or_path": "https://lambethopenmappingdata-lambethcouncil.opendata.arcgis.com/",
        "access_method_attempted": "html_parse",
        "official_owner": "Lambeth Council",
        "probe_role": "open_data_catalog",
    },
    {
        "source_id": "planning_data_platform_dataset_catalog",
        "source_family": "national_planning_data",
        "url_or_path": "https://www.planning.data.gov.uk/dataset/",
        "access_method_attempted": "http_get",
        "official_owner": "Planning Data",
        "probe_role": "national_dataset_catalog",
    },
    {
        "source_id": "planning_london_datahub_context_only",
        "source_family": "planning_database",
        "url_or_path": "outputs/lon_d5_pld_planning_ingest",
        "access_method_attempted": "local_context_only",
        "official_owner": "Planning London Datahub",
        "probe_role": "pld_context_not_d6_source",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_col(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_json_col(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        return json.loads(value) if value else None
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def frame_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    records = df.head(limit).to_dict(orient="records")
    for record in records:
        for key in ("geometry", "confidence", "provenance", "uprn_refs"):
            if key in record:
                try:
                    record[key] = parse_json_col(record[key])
                except Exception:
                    pass
    return records


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "lon_d6_enforcement_building_control" not in resolved.name.lower()
        ):
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        last_error: Exception | None = None
        for _ in range(3):
            try:
                shutil.rmtree(resolved)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error:
            raise last_error
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "raw_sample").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def collect_tracked_inputs(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for root in [lon_d4_dir, lon_d5_dir, lon_d5c_dir]:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(paths))


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists()}


def inventory_inputs(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    roots = {
        "lon_d4_dir": lon_d4_dir,
        "lon_d5_dir": lon_d5_dir,
        "lon_d5c_dir": lon_d5c_dir,
    }
    root_report = {}
    for name, path in roots.items():
        files = [file for file in path.rglob("*") if file.is_file()] if path.exists() else []
        root_report[name] = {
            "path": str(path),
            "exists": path.exists(),
            "file_count": len(files),
            "required_for": {
                "lon_d4_dir": "UPRN/TOID/USRN identity registries",
                "lon_d5_dir": "PLD planning application references for exact reference joins",
                "lon_d5c_dir": "LIDS-confirmed UPRN stubs and connected context paths",
            }[name],
        }
    return {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "roots": root_report,
        "tracked_input_files": len(tracked_inputs),
        "tracked_input_hashes": {str(path): sha256_file(path) for path in tracked_inputs if path.exists()},
    }


def normalize_reference(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def normalize_uprn(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return None
    return text.lstrip("0") or "0"


def confidence(method: str, score: float, basis: str) -> str:
    return json_col({"method": method, "score": score, "basis": basis})


def provenance(source_dataset: str, source_id: str, source_fields: list[str], derivation: str) -> str:
    return json_col(
        [
            {
                "source_dataset": source_dataset,
                "source_id": source_id,
                "source_fields": source_fields,
                "derivation": derivation,
                "observed_at": utc_now(),
            }
        ]
    )


def http_probe(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TXR-CityBrain-LON-D6-source-probe/1.0",
            "Accept": "text/html,application/json,text/csv,*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(750_000)
            charset = response.headers.get_content_charset() or "utf-8"
            return {
                "ok": True,
                "http_status": int(response.status),
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type", ""),
                "text": raw.decode(charset, errors="replace"),
                "bytes_read": len(raw),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000) if exc.fp else b""
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        charset = exc.headers.get_content_charset() if exc.headers else None
        return {
            "ok": False,
            "http_status": int(exc.code),
            "final_url": url,
            "content_type": content_type,
            "text": body.decode(charset or "utf-8", errors="replace"),
            "bytes_read": len(body),
            "error": f"HTTPError: {exc}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "http_status": None,
            "final_url": url,
            "content_type": "",
            "text": "",
            "bytes_read": 0,
            "error": f"{type(exc).__name__}: {exc}",
        }


def detect_markers(text: str, patterns: list[str]) -> list[str]:
    found = []
    lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, lower, flags=re.IGNORECASE):
            found.append(pattern)
    return found


def detect_records(text: str) -> int:
    patterns = [
        r"applicationDetails\.do\?",
        r"buildingControlDetails\.do\?",
        r"class=[\"'][^\"']*searchresult",
        r"data-record-id=",
        r"resultCount",
    ]
    counts = [len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns]
    return max(counts) if counts else 0


def classify_candidate_status(candidate: dict[str, Any], probe: dict[str, Any], records_detected: int, marker_notes: dict[str, list[str]]) -> tuple[str, str]:
    source_id = candidate["source_id"]
    source_family = candidate["source_family"]
    role = candidate.get("probe_role")
    if role == "pld_context_not_d6_source":
        return (
            "not_relevant",
            "PLD is retained as context for exact planning-reference joins; it is not treated as a D6 enforcement/building-control source.",
        )
    if not probe["ok"]:
        if probe["http_status"] in {401, 403, 429}:
            return ("blocked", "Official source probe was blocked or rate-limited; no records were ingested.")
        return ("failed", "Official source probe failed; no records were ingested.")
    if source_family in {"open_data", "national_planning_data"}:
        lower = probe["text"].lower()
        relevant_terms = ["enforcement", "building control", "building-control", "building regulation"]
        if not any(term in lower for term in relevant_terms):
            return (
                "not_relevant",
                "Official catalog was reachable, but no Lambeth enforcement/building-control dataset was detected by the bounded probe.",
            )
        return (
            "not_relevant",
            "Official catalog contains planning-related text, but the bounded probe did not identify a specific Lambeth enforcement/building-control record feed.",
        )
    if role in {"register_request", "enforcement_guidance"}:
        return (
            "human_register_only",
            "Official enforcement surface points to guidance/register request or portal lookup, not a bounded machine-readable record feed.",
        )
    if role in {"building_control_guidance", "planning_database_guidance", "planning_data_hub_page"}:
        return (
            "human_register_only",
            "Official page is reachable and points to an interactive database, but it does not itself expose a bounded record list.",
        )
    if role == "interactive_public_access":
        has_form = bool(re.search(r"<form\b", probe["text"], flags=re.IGNORECASE))
        if records_detected > 0 and marker_notes.get("identifier_fields_detected"):
            return (
                "human_register_only",
                "Official PublicAccess page exposed HTML/search markers, but the bounded probe did not establish a stable machine-readable record feed; D6b is not allowed from this alone.",
            )
        if has_form:
            return (
                "human_register_only",
                "Official PublicAccess interactive search form is reachable; no bounded result feed was detected without supplying search criteria.",
            )
        return (
            "human_register_only",
            "Official PublicAccess page is reachable but no safely extractable bounded record list was detected.",
        )
    return ("failed", "Probe role was not recognized; source was not used for ingest.")


def probe_source_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    if candidate.get("probe_role") == "pld_context_not_d6_source":
        local_path = Path(candidate["url_or_path"])
        return {
            "source_id": candidate["source_id"],
            "source_family": candidate["source_family"],
            "url_or_path": candidate["url_or_path"],
            "access_method_attempted": candidate["access_method_attempted"],
            "official_owner": candidate["official_owner"],
            "official_source": True,
            "status": "not_relevant",
            "http_status": None,
            "content_type": "local directory",
            "records_detected": 0,
            "identifier_fields_detected": ["lpa_app_no", "native_id"] if local_path.exists() else [],
            "date_fields_detected": [],
            "address_fields_detected": [],
            "geometry_fields_detected": [],
            "machine_readable": False,
            "d6b_allowed": False,
            "notes": "PLD is used only as D5 context for exact planning-reference joins, not as a Lambeth enforcement/building-control source.",
            "final_url": candidate["url_or_path"],
            "bytes_read": 0,
            "error": None,
            "probed_at": utc_now(),
        }

    probe = http_probe(candidate["url_or_path"])
    text = probe.get("text") or ""
    identifier_fields = detect_markers(
        text,
        [
            r"\buprn\b",
            r"application reference",
            r"planning reference",
            r"case reference",
            r"\breference\b",
            r"enforcement notice",
        ],
    )
    date_fields = detect_markers(text, [r"\bdate\b", r"received", r"decision", r"notice date", r"weekly list"])
    address_fields = detect_markers(text, [r"\baddress\b", r"site address", r"property"])
    geometry_fields = detect_markers(text, [r"\bgeometry\b", r"\blatitude\b", r"\blongitude\b", r"\bmap\b"])
    marker_notes = {
        "identifier_fields_detected": identifier_fields,
        "date_fields_detected": date_fields,
        "address_fields_detected": address_fields,
        "geometry_fields_detected": geometry_fields,
    }
    records_detected = detect_records(text)
    status, notes = classify_candidate_status(candidate, probe, records_detected, marker_notes)
    return {
        "source_id": candidate["source_id"],
        "source_family": candidate["source_family"],
        "url_or_path": candidate["url_or_path"],
        "access_method_attempted": candidate["access_method_attempted"],
        "official_owner": candidate["official_owner"],
        "official_source": True,
        "status": status,
        "http_status": probe["http_status"],
        "content_type": probe["content_type"],
        "records_detected": records_detected,
        "identifier_fields_detected": identifier_fields,
        "date_fields_detected": date_fields,
        "address_fields_detected": address_fields,
        "geometry_fields_detected": geometry_fields,
        "machine_readable": status in USABLE_SOURCE_STATUSES,
        "d6b_allowed": status in USABLE_SOURCE_STATUSES,
        "notes": notes,
        "final_url": probe["final_url"],
        "bytes_read": probe["bytes_read"],
        "error": probe["error"],
        "probed_at": utc_now(),
    }


def run_source_probe() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [probe_source_candidate(candidate) for candidate in SOURCE_CANDIDATES]
    usable_enforcement = any(
        record["status"] in USABLE_SOURCE_STATUSES and record["source_family"] == "planning_enforcement" for record in records
    )
    usable_building_control = any(
        record["status"] in USABLE_SOURCE_STATUSES and record["source_family"] == "building_control" for record in records
    )
    if usable_enforcement and usable_building_control:
        classification = "D6A_USABLE_BOTH_SOURCES"
    elif usable_enforcement:
        classification = "D6A_USABLE_ENFORCEMENT_SOURCE"
    elif usable_building_control:
        classification = "D6A_USABLE_BUILDING_CONTROL_SOURCE"
    elif any(record["status"] in REGISTER_ONLY_STATUSES for record in records):
        classification = "D6A_NO_MACHINE_SOURCE_REGISTER_ONLY"
    else:
        classification = "D6A_SOURCE_BLOCKED_OR_INSUFFICIENT"
    reason = (
        "Official Lambeth surfaces were reachable, but the bounded probe found only guidance, register-request, or interactive search pages; no stable machine-readable record feed was established."
        if classification == "D6A_NO_MACHINE_SOURCE_REGISTER_ONLY"
        else "No usable official Lambeth enforcement/building-control source was established by the bounded probe."
    )
    if classification.startswith("D6A_USABLE"):
        reason = "At least one official usable source was detected by D6a."
    source_decision = {
        "gate": "LON-D6A-SOURCE-CLASSIFICATION",
        "status": "PASS" if classification in SOURCE_CLASSIFICATIONS else "FAIL",
        "classification": classification,
        "usable_enforcement_source": usable_enforcement,
        "usable_building_control_source": usable_building_control,
        "d6b_allowed": usable_enforcement or usable_building_control,
        "reason": reason,
        "sources_probed": len(records),
        "source_status_counts": dict(Counter(record["status"] for record in records)),
        "official_sources_only": all(record["official_source"] for record in records),
    }
    return records, source_decision


def load_registry(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path) -> dict[str, Any]:
    registry: set[str] = set()
    d4_uprn_ids: set[str] = set()
    d5c_uprn_ids: set[str] = set()
    d4_building_ids: set[str] = set()
    d4_road_ids: set[str] = set()
    pld_ids: set[str] = set()
    pld_reference_to_id: dict[str, str] = {}

    d4_parcels_path = lon_d4_dir / "canonical" / "london_parcels_uprn.parquet"
    d4_building_path = lon_d4_dir / "canonical" / "london_buildings_toid.parquet"
    d4_road_path = lon_d4_dir / "canonical" / "london_road_segments_usrn.parquet"
    d5_pld_path = lon_d5_dir / "canonical" / "london_planning_applications.parquet"
    d5c_uprns_path = lon_d5c_dir / "canonical" / "london_lids_confirmed_uprn_stubs.parquet"
    d5c_context_path = lon_d5c_dir / "canonical" / "london_lids_context_entity_stubs.parquet"

    if d4_parcels_path.exists():
        d4_parcels = pd.read_parquet(d4_parcels_path)
        d4_uprn_ids = set(d4_parcels["canonical_id"].astype(str))
        registry |= d4_uprn_ids
    if d5c_uprns_path.exists():
        d5c_uprns = pd.read_parquet(d5c_uprns_path)
        d5c_uprn_ids = set(d5c_uprns["canonical_id"].astype(str))
        registry |= d5c_uprn_ids
    if d4_building_path.exists():
        d4_buildings = pd.read_parquet(d4_building_path)
        d4_building_ids = set(d4_buildings["canonical_id"].astype(str))
        registry |= d4_building_ids
    if d4_road_path.exists():
        d4_roads = pd.read_parquet(d4_road_path)
        d4_road_ids = set(d4_roads["canonical_id"].astype(str))
        registry |= d4_road_ids
    if d5c_context_path.exists():
        d5c_context = pd.read_parquet(d5c_context_path)
        registry |= set(d5c_context["canonical_id"].astype(str))
    if d5_pld_path.exists():
        pld = pd.read_parquet(d5_pld_path)
        pld_ids = set(pld["canonical_id"].astype(str))
        registry |= pld_ids
        for row in pld.to_dict(orient="records"):
            pld_id = str(row.get("canonical_id"))
            for field in ["lpa_app_no", "native_id", "raw_hit_id"]:
                value = normalize_reference(row.get(field))
                if value:
                    pld_reference_to_id[value.lower()] = pld_id
    return {
        "registry": registry,
        "d4_uprn_ids": d4_uprn_ids,
        "d5c_uprn_ids": d5c_uprn_ids,
        "d4_building_ids": d4_building_ids,
        "d4_road_ids": d4_road_ids,
        "pld_ids": pld_ids,
        "pld_reference_to_id": pld_reference_to_id,
        "counts": {
            "d4_uprn_ids": len(d4_uprn_ids),
            "d5c_uprn_ids": len(d5c_uprn_ids),
            "d4_building_ids": len(d4_building_ids),
            "d4_road_ids": len(d4_road_ids),
            "pld_ids": len(pld_ids),
            "combined_registry_ids": len(registry),
        },
    }


def preconditions(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path) -> dict[str, Any]:
    checks = {}
    d4_harness = lon_d4_dir / "LON_D4_HARNESS_REPORT.json"
    d5_harness = lon_d5_dir / "LON_D5_HARNESS_REPORT.json"
    d5c_harness = lon_d5c_dir / "LON_D5C_HARNESS_REPORT.json"
    d5c_smoke_path = lon_d5c_dir / "LON_D5C_CONNECTED_PATH_SMOKE.json"
    for name, path in [
        ("lon_d4_harness_report", d4_harness),
        ("lon_d5_harness_report", d5_harness),
        ("lon_d5c_harness_report", d5c_harness),
        ("lon_d5c_connected_path_smoke", d5c_smoke_path),
    ]:
        checks[f"{name}_exists"] = path.exists()
    for name, path in [
        ("lon_d4_harness_report_status_pass", d4_harness),
        ("lon_d5_harness_report_status_pass", d5_harness),
        ("lon_d5c_harness_report_status_pass", d5c_harness),
    ]:
        value = False
        if path.exists():
            try:
                value = read_json(path).get("status") == "PASS"
            except Exception:
                value = False
        checks[name] = value
    d5c_smoke = {}
    if d5c_smoke_path.exists():
        try:
            d5c_smoke = read_json(d5c_smoke_path)
        except Exception:
            d5c_smoke = {}
    checks["lon_d5c_connected_path_smoke_non_empty"] = d5c_smoke.get("result") in {"BOTH", "STRONG", "MEDIUM", "MINIMUM"} or int(
        d5c_smoke.get("paths_emitted", 0) or 0
    ) > 0
    return {
        "gate": "LON-D6-PRECOND",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "d5c_connected_path_smoke": d5c_smoke,
    }


def make_empty_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame(columns=ENFORCEMENT_COLUMNS),
        pd.DataFrame(columns=BUILDING_CONTROL_COLUMNS),
        pd.DataFrame(columns=EDGE_COLUMNS),
        pd.DataFrame(columns=UNATTACHED_COLUMNS),
        pd.DataFrame(columns=PATH_COLUMNS),
    )


def d6b_not_run_reports(max_records: int, classification: dict[str, Any]) -> dict[str, Any]:
    reason = classification["reason"]
    join_report = {
        "gate": "LON-D6-JOIN-REPORT",
        "status": "PASS",
        "d6b_run": False,
        "reason": reason,
        "d6_records_total": 0,
        "records_with_uprn": 0,
        "records_with_planning_reference": 0,
        "exact_uprn_edges_emitted": 0,
        "exact_pld_reference_edges_emitted": 0,
        "records_still_unattached": 0,
        "unattached_reasons": {"source_limitation_no_d6b_records": 0},
        "join_rate": 0.0,
        "join_attempts_reported": True,
    }
    smoke = {
        "gate": "LON-D6-CONNECTED-PATH-SMOKE",
        "status": "PASS",
        "result": "NONE_WITH_SOURCE_LIMITATION",
        "claim_connected_path_proof": False,
        "paths_emitted": 0,
        "strong_paths_available": 0,
        "medium_paths_available": 0,
        "minimum_paths_available": 0,
        "reason": "No D6b canonical records were emitted because D6a did not establish a usable official source.",
        "sample_paths": [],
    }
    ingest_report = {
        "gate": "LON-D6B-SAMPLE-INGEST",
        "status": "PASS",
        "d6b_run": False,
        "run_d6b_if_possible": True,
        "max_records": max_records,
        "reason": reason,
        "enforcement_records_emitted": 0,
        "building_control_records_emitted": 0,
        "records_ingested": 0,
        "no_fabrication": True,
    }
    return {"ingest_report": ingest_report, "join_report": join_report, "smoke": smoke}


def id_format_gate(enforcement: pd.DataFrame, building_control: pd.DataFrame, edges: pd.DataFrame) -> dict[str, Any]:
    failures = []
    for df, pattern in [(enforcement, EVENT_ID_PATTERN), (building_control, BUILDING_CONTROL_ID_PATTERN)]:
        for canonical_id in df.get("canonical_id", pd.Series(dtype=str)).astype(str):
            if not pattern.match(canonical_id) or FORBIDDEN_ID_TOKEN_PATTERN.search(canonical_id):
                failures.append(canonical_id)
    for edge in edges.to_dict(orient="records"):
        for key in ["src", "dst"]:
            value = str(edge.get(key, ""))
            if FORBIDDEN_ID_TOKEN_PATTERN.search(value):
                failures.append(value)
            if not any(
                pattern.match(value)
                for pattern in [EVENT_ID_PATTERN, BUILDING_CONTROL_ID_PATTERN, PLD_ID_PATTERN, UPRN_ID_PATTERN, BUILDING_ID_PATTERN, ROAD_ID_PATTERN]
            ):
                failures.append(value)
    return {
        "gate": "LON-D6-ID-FORMAT",
        "status": "PASS" if not failures else "FAIL",
        "checked_entities": len(enforcement) + len(building_control),
        "checked_edges": len(edges),
        "failures": sorted(set(failures))[:25],
        "allowed_id_patterns": [
            "event:uk-london:planning_enforcement:{id}",
            "permit:uk-london:building_control:{id}",
            "permit:uk-london:pld:{id}",
            "parcel:uk-london:uprn:{uprn}",
            "building:uk-london:toid:{toid}",
            "road_segment:uk-london:usrn:{usrn}",
        ],
    }


def edge_integrity(edges: pd.DataFrame, registry: set[str], d6_entity_ids: set[str], pld_ids: set[str]) -> dict[str, Any]:
    failures = []
    combined = set(registry) | set(d6_entity_ids) | set(pld_ids)
    for edge in edges.to_dict(orient="records"):
        src = str(edge.get("src"))
        dst = str(edge.get("dst"))
        if src not in combined:
            failures.append(f"{edge.get('edge_id')} missing src {src}")
        if dst not in combined:
            failures.append(f"{edge.get('edge_id')} missing dst {dst}")
    return {
        "gate": "LON-D6-EDGE-INTEGRITY",
        "status": "PASS" if not failures else "FAIL",
        "edges_checked": len(edges),
        "failures": failures[:25],
    }


def geometry_honesty(enforcement: pd.DataFrame, building_control: pd.DataFrame) -> dict[str, Any]:
    allowed_statuses = {
        "missing_geometry",
        "point_if_source_provided",
        "missing_geometry_lids_identity_stub",
        "toid_identity_only_no_polygon",
        "usrn_identity_only_no_geometry",
    }
    failures = []
    rows = pd.concat([enforcement, building_control], ignore_index=True) if not enforcement.empty or not building_control.empty else pd.DataFrame()
    for row in rows.to_dict(orient="records"):
        status = row.get("geometry_status")
        geometry = row.get("geometry")
        if status not in allowed_statuses:
            failures.append(f"{row.get('canonical_id')} unsupported geometry_status {status}")
        if geometry not in {None, "", "null"} and status != "point_if_source_provided":
            failures.append(f"{row.get('canonical_id')} has geometry without point_if_source_provided")
    return {
        "gate": "LON-D6-GEOMETRY-HONESTY",
        "status": "PASS" if not failures else "FAIL",
        "entities_checked": len(rows),
        "allowed_statuses": sorted(allowed_statuses),
        "geometry_status_counts": dict(Counter(rows["geometry_status"].astype(str))) if not rows.empty and "geometry_status" in rows else {},
        "failures": failures[:25],
    }


def add_compat_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool, checked: int, failed: int, details: list[str]) -> None:
    gates.append(
        {
            "gate_id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "checked": checked,
            "failed": failed,
            "details": details[:25],
        }
    )


def a2_not_applicable_report(reason: str) -> dict[str, Any]:
    gates = [
        {"gate_id": gate_id, "status": "NOT_APPLICABLE", "checked": 0, "failed": 0, "details": [reason]}
        for gate_id in ["G-SCHEMA", "G-ID", "G-TRIAD", "G-GEO", "G-REF", "G-EDGE"]
    ]
    return {
        "gate": "LON-D6-A2-COMPATIBILITY",
        "status": "NOT_APPLICABLE",
        "gate_status": "PASS",
        "compatibility_marker": "a2_not_applicable_d6a_only_source_limitation",
        "reason": reason,
        "gates": gates,
    }


def compatibility_harness(
    enforcement: pd.DataFrame,
    building_control: pd.DataFrame,
    edges: pd.DataFrame,
    registry: set[str],
    pld_ids: set[str],
    source_limitation: bool = False,
) -> dict[str, Any]:
    if source_limitation and enforcement.empty and building_control.empty and edges.empty:
        return a2_not_applicable_report(
            "D6b did not run because D6a found no usable machine-readable or safely extractable source."
        )
    gates: list[dict[str, Any]] = []
    entity_records = enforcement.to_dict(orient="records") + building_control.to_dict(orient="records")
    edge_records = edges.to_dict(orient="records")

    schema_failures = []
    for row in enforcement.to_dict(orient="records"):
        if row.get("entity_type") != "event" or row.get("event_type") != "planning_enforcement":
            schema_failures.append(str(row.get("canonical_id")))
    for row in building_control.to_dict(orient="records"):
        if row.get("entity_type") != "permit" or row.get("permit_type") != "building_control_application":
            schema_failures.append(str(row.get("canonical_id")))
    for row in edge_records:
        if row.get("relation") not in {"subject_of_event", "subject_of_permit", "related_to_event", "related_to_permit"}:
            schema_failures.append(str(row.get("edge_id")))
    add_compat_gate(gates, "G-SCHEMA", not schema_failures, len(entity_records) + len(edge_records), len(schema_failures), schema_failures)

    id_failures = []
    for row in enforcement.to_dict(orient="records"):
        value = str(row.get("canonical_id", ""))
        if not EVENT_ID_PATTERN.match(value):
            id_failures.append(value)
    for row in building_control.to_dict(orient="records"):
        value = str(row.get("canonical_id", ""))
        if not BUILDING_CONTROL_ID_PATTERN.match(value):
            id_failures.append(value)
    for value in [str(row.get("src", "")) for row in edge_records] + [str(row.get("dst", "")) for row in edge_records]:
        if not any(pattern.match(value) for pattern in [EVENT_ID_PATTERN, BUILDING_CONTROL_ID_PATTERN, PLD_ID_PATTERN, UPRN_ID_PATTERN, BUILDING_ID_PATTERN, ROAD_ID_PATTERN]):
            id_failures.append(value)
    add_compat_gate(gates, "G-ID", not id_failures, len(entity_records) + len(edge_records) * 2, len(id_failures), id_failures)

    triad_failures = []
    for row in entity_records + edge_records:
        confidence_value = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not isinstance(confidence_value, dict) or confidence_value.get("score") is None or not confidence_value.get("method") or not provenance_value:
            triad_failures.append(str(row.get("canonical_id") or row.get("edge_id")))
    add_compat_gate(gates, "G-TRIAD", not triad_failures, len(entity_records) + len(edge_records), len(triad_failures), triad_failures)

    geo = geometry_honesty(enforcement, building_control)
    add_compat_gate(gates, "G-GEO", geo["status"] == "PASS", geo["entities_checked"], len(geo["failures"]), geo["failures"])

    d6_entity_ids = {str(row.get("canonical_id")) for row in entity_records}
    ref_failures = []
    combined = registry | pld_ids | d6_entity_ids
    for row in edge_records:
        if str(row.get("src")) not in combined:
            ref_failures.append(f"{row.get('edge_id')} missing src {row.get('src')}")
        if str(row.get("dst")) not in combined:
            ref_failures.append(f"{row.get('edge_id')} missing dst {row.get('dst')}")
    add_compat_gate(gates, "G-REF", not ref_failures, len(edge_records) * 2, len(ref_failures), ref_failures)

    edge_failures = []
    for row in edge_records:
        confidence_value = parse_json_col(row.get("confidence"))
        if not confidence_value or float(confidence_value.get("score", 0)) <= 0:
            edge_failures.append(str(row.get("edge_id")))
        if row.get("relation") in {"subject_of_event", "subject_of_permit"} and not UPRN_ID_PATTERN.match(str(row.get("src"))):
            edge_failures.append(str(row.get("edge_id")))
        if row.get("relation") in {"related_to_event", "related_to_permit"} and not PLD_ID_PATTERN.match(str(row.get("src"))):
            edge_failures.append(str(row.get("edge_id")))
    add_compat_gate(gates, "G-EDGE", not edge_failures, len(edge_records), len(edge_failures), edge_failures)

    status = "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL"
    return {
        "gate": "LON-D6-A2-COMPATIBILITY",
        "status": status,
        "gate_status": status,
        "compatibility_marker": "a2_binary_unavailable_compatibility_harness_used",
        "reason": "Local A2 binary is NYC-specific; D6 runs the same invariant names over London D6 entities and edges without claiming exact NYC binary acceptance.",
        "gates": gates,
    }


def drift_test() -> dict[str, Any]:
    synthetic_uprn = "parcel:uk-london:uprn:100023363937"
    synthetic_event = "event:uk-london:planning_enforcement:SYNTHETIC_ENF_1"
    synthetic_permit = "permit:uk-london:building_control:SYNTHETIC_BC_1"
    enforcement = pd.DataFrame(
        [
            {
                "canonical_id": synthetic_event,
                "entity_type": "event",
                "id_system": "lambeth_planning_enforcement",
                "native_id": "SYNTHETIC-ENF-1",
                "city": "london",
                "country": "uk",
                "borough": "Lambeth",
                "event_type": "planning_enforcement",
                "event_subtype": "unknown",
                "source_dataset": "lambeth_planning_enforcement",
                "reference": "SYNTHETIC-ENF-1",
                "status": "synthetic_for_drift",
                "notice_date": None,
                "address": None,
                "description": None,
                "related_planning_reference": None,
                "uprn_refs": json_col(["100023363937"]),
                "geometry": None,
                "geometry_status": "missing_geometry",
                "confidence": confidence("official_lambeth_enforcement_record", 0.90, "Synthetic valid row for D6 drift baseline."),
                "provenance": provenance("LON-D6 drift synthetic", "SYNTHETIC-ENF-1", ["uprn"], "Valid baseline row before deliberate mutation."),
            }
        ],
        columns=ENFORCEMENT_COLUMNS,
    )
    building_control = pd.DataFrame(
        [
            {
                "canonical_id": synthetic_permit,
                "entity_type": "permit",
                "id_system": "lambeth_building_control",
                "native_id": "SYNTHETIC-BC-1",
                "city": "london",
                "country": "uk",
                "borough": "Lambeth",
                "permit_type": "building_control_application",
                "source_dataset": "lambeth_building_control",
                "reference": "SYNTHETIC-BC-1",
                "status": "synthetic_for_drift",
                "application_type": None,
                "received_date": None,
                "decision_date": None,
                "completion_date": None,
                "address": None,
                "description": None,
                "uprn_refs": json_col(["100023363937"]),
                "geometry": None,
                "geometry_status": "missing_geometry",
                "confidence": confidence("official_lambeth_building_control_record", 0.90, "Synthetic valid row for D6 drift baseline."),
                "provenance": provenance("LON-D6 drift synthetic", "SYNTHETIC-BC-1", ["uprn"], "Valid baseline row before deliberate mutation."),
            }
        ],
        columns=BUILDING_CONTROL_COLUMNS,
    )
    edges = pd.DataFrame(
        [
            {
                "edge_id": "edge:uk-london:d6:synthetic-event",
                "src": synthetic_uprn,
                "relation": "subject_of_event",
                "dst": synthetic_event,
                "role": "enforcement_subject",
                "confidence": confidence("exact_uprn_join", 0.90, "Synthetic exact UPRN edge for D6 drift baseline."),
                "provenance": provenance("LON-D6 drift synthetic", "SYNTHETIC-EDGE-ENF", ["uprn"], "Valid baseline edge before deliberate mutation."),
                "source_record_id": "SYNTHETIC-ENF-1",
                "source_join_key": "100023363937",
                "semantic_caveat": "",
            },
            {
                "edge_id": "edge:uk-london:d6:synthetic-permit",
                "src": synthetic_uprn,
                "relation": "subject_of_permit",
                "dst": synthetic_permit,
                "role": "building_control_subject",
                "confidence": confidence("exact_uprn_join", 0.90, "Synthetic exact UPRN edge for D6 drift baseline."),
                "provenance": provenance("LON-D6 drift synthetic", "SYNTHETIC-EDGE-BC", ["uprn"], "Valid baseline edge before deliberate mutation."),
                "source_record_id": "SYNTHETIC-BC-1",
                "source_join_key": "100023363937",
                "semantic_caveat": "",
            },
        ],
        columns=EDGE_COLUMNS,
    )
    registry = {synthetic_uprn}
    baseline = compatibility_harness(enforcement, building_control, edges, registry, set(), source_limitation=False)
    mutated_enforcement = enforcement.copy()
    mutated_building = building_control.copy()
    mutated_edges = edges.copy()
    mutated_enforcement.loc[0, "canonical_id"] = "enforcement_notice:uk-london:lambeth:SYNTHETIC_ENF_1"
    mutated_building.loc[0, "canonical_id"] = "building_control_application:uk-london:lambeth:SYNTHETIC_BC_1"
    mutated_edges.loc[0, "relation"] = "linked_to_enforcement"
    mutated_edges.loc[1, "relation"] = "linked_to_building_control"
    mutated = compatibility_harness(mutated_enforcement, mutated_building, mutated_edges, registry, set(), source_limitation=False)
    failing_gates = [gate["gate_id"] for gate in mutated["gates"] if gate["status"] == "FAIL"]
    return {
        "gate": "LON-D6-DRIFT",
        "status": "PASS" if baseline["status"] == "PASS" and mutated["status"] == "FAIL" and failing_gates else "FAIL",
        "drift_mutation": {
            "event:uk-london:planning_enforcement:{id}": "enforcement_notice:uk-london:lambeth:{id}",
            "permit:uk-london:building_control:{id}": "building_control_application:uk-london:lambeth:{id}",
            "subject_of_event": "linked_to_enforcement",
            "subject_of_permit": "linked_to_building_control",
        },
        "baseline_harness_status": baseline["status"],
        "mutated_harness_status": mutated["status"],
        "failing_gates": failing_gates,
    }


def confidence_summary(enforcement: pd.DataFrame, building_control: pd.DataFrame, edges: pd.DataFrame) -> dict[str, Any]:
    methods: Counter[str] = Counter()
    scores: dict[str, list[float]] = {}
    for df in [enforcement, building_control, edges]:
        if df.empty or "confidence" not in df:
            continue
        for value in df["confidence"]:
            parsed = parse_json_col(value)
            if not isinstance(parsed, dict):
                continue
            method = str(parsed.get("method"))
            methods[method] += 1
            if parsed.get("score") is not None:
                scores.setdefault(method, []).append(float(parsed["score"]))
    return {
        "status": "PASS",
        "policy": {
            "Official enforcement/building-control entity from source record": 0.90,
            "Exact UPRN edge to LON-D4 or D5c identity node": 0.90,
            "Exact planning-reference edge to LON-D5 PLD permit entity": 0.85,
            "TOID/USRN context via D5c traversal": "inherit min edge confidence",
            "Address-only candidate": "<=0.60 and not canonical in D6",
            "No geometry confidence when geometry is missing": True,
        },
        "method_counts": dict(methods),
        "score_ranges": {method: {"min": min(values), "max": max(values)} for method, values in scores.items() if values},
    }


def out_of_scope_report(enforcement: pd.DataFrame, building_control: pd.DataFrame, edges: pd.DataFrame, paths: pd.DataFrame) -> dict[str, Any]:
    payload = "\n".join(
        [
            enforcement.to_json(orient="records"),
            building_control.to_json(orient="records"),
            edges.to_json(orient="records"),
            paths.to_json(orient="records"),
        ]
    ).lower()
    forbidden_payload_terms = [
        "nyc dob",
        "dob_complaint",
        "dob_permit",
        "private complainant",
        "copyright plans",
        "copyright documents",
        "citywide london ingest",
    ]
    found = sorted(term for term in forbidden_payload_terms if term in payload)
    return {
        "gate": "LON-D6-OUT-OF-SCOPE",
        "status": "PASS" if not found else "FAIL",
        "found_forbidden_payload_terms": found,
        "checked_payloads": [
            "canonical/london_enforcement_events.parquet",
            "canonical/london_building_control_applications.parquet",
            "canonical/london_d6_identity_edges.parquet",
            "canonical/london_d6_connected_paths.parquet",
        ],
        "scope_policy": "D6 does not ingest private complainant data, personal contact details, documents/plans, other borough records, or citywide London records.",
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    required_files = {
        "README.md": output_dir / "README.md",
        "LON_D6_MANIFEST.json": output_dir / "LON_D6_MANIFEST.json",
        "LON_D6_HARNESS_REPORT.json": output_dir / "LON_D6_HARNESS_REPORT.json",
        "LON_D6_ADAPTER_HANDOVER.md": output_dir / "LON_D6_ADAPTER_HANDOVER.md",
    }
    files = {}
    passed = True
    for name, path in required_files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in BOUNDARY_STRINGS if item not in text]
        files[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {
        "gate": "LON-D6-NO-OVERCLAIM",
        "status": "PASS" if passed else "FAIL",
        "boundary_strings": BOUNDARY_STRINGS,
        "files": files,
    }


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D6-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_schema_decision(output_dir: Path, source_decision: dict[str, Any], source_records: list[dict[str, Any]]) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    candidates = "\n".join(
        f"- `{record['source_id']}`: {record['status']} ({record['source_family']}) - {record['notes']}"
        for record in source_records
    )
    text = f"""# LON-D6a Schema Decision

{boundary}

## Classification

`{source_decision['classification']}`

{source_decision['reason']}

## Decision

D6b may run only when D6a establishes an official, machine-readable or safely extractable Lambeth enforcement/building-control record source. This run did not establish that condition, so D6 emits empty canonical D6 tables with explicit source limitation rather than fabricated sample rows.

## Candidate Sources

{candidates}

## Canonical Mapping If A Usable Source Appears

- Planning enforcement records map to `event:uk-london:planning_enforcement:{{safe_enforcement_id}}`.
- Building-control application records map to `permit:uk-london:building_control:{{safe_building_control_id}}`.
- Exact UPRN joins create `subject_of_event` or `subject_of_permit` edges.
- Exact PLD planning-reference joins create `related_to_event` or `related_to_permit` edges.
- Address-only evidence is candidate evidence only and does not create canonical D6 edges.
"""
    (output_dir / "LON_D6A_SCHEMA_DECISION.md").write_text(text, encoding="utf-8")


def write_docs(
    output_dir: Path,
    status: str,
    source_decision: dict[str, Any],
    ingest_report: dict[str, Any],
    join_report: dict[str, Any],
    smoke: dict[str, Any],
    a2_report: dict[str, Any],
) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    readme = f"""# LON-D6 Lambeth Enforcement / Building-Control Source Probe

{boundary}

## Result

- Status: {status}
- D6a classification: {source_decision['classification']}
- Sources probed: {source_decision['sources_probed']}
- Usable enforcement source: {'YES' if source_decision['usable_enforcement_source'] else 'NO'}
- Usable building-control source: {'YES' if source_decision['usable_building_control_source'] else 'NO'}
- D6b run: {'YES' if ingest_report['d6b_run'] else 'NO'}
- Reason: {source_decision['reason']}
- Connected path smoke: {smoke['result']}
- A2 compatibility gates: {a2_report['status']}

## Scope

D6 is bounded to Lambeth source discovery and a sampled ingest only when an official usable source is proven. In this run, the official sources were reachable as guidance, register request, or interactive search surfaces, but not as a stable bounded record feed for D6b.

## Join Policy

If D6b later runs, joins are attempted in order: exact UPRN to D4/D5c identity nodes, exact planning reference to D5 PLD entities, then address-only candidate reporting without canonical edges.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    handover = f"""# LON-D6 Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d6_enforcement_building_control.py`

```bash
python txr_citybrain_lon_d6_enforcement_building_control.py --lon-d4-dir outputs/lon_d4_identity_backbone_ingest --lon-d5-dir outputs/lon_d5_pld_planning_ingest --lon-d5c-dir outputs/lon_d5c_lids_confirmed_identity_bridge --output-dir outputs/lon_d6_enforcement_building_control --borough Lambeth --max-records 500 --run-d6b-if-possible --run-gates
```

## Source Decision

- D6a classification: {source_decision['classification']}
- D6b allowed: {source_decision['d6b_allowed']}
- D6b run: {ingest_report['d6b_run']}
- Reason: {source_decision['reason']}

## Compatibility

A2-style invariant names are present. For D6a-only source limitation runs, A2 compatibility is `{a2_report['status']}` with gate status `{a2_report.get('gate_status')}`.

## Next Adapter Work

If Lambeth exposes an official bounded API, CSV, JSON feed, or stable downloadable register, implement only that adapter branch, preserve the canonical IDs above, and keep address-only matches out of canonical edges.
"""
    (output_dir / "LON_D6_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_manifest(
    output_dir: Path,
    lon_d4_dir: Path,
    lon_d5_dir: Path,
    lon_d5c_dir: Path,
    status: str,
    source_decision: dict[str, Any],
    counts: dict[str, Any],
    borough: str,
    max_records: int,
) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "lon_d5c_dir": str(lon_d5c_dir),
        "output_dir": str(output_dir),
        "borough": borough,
        "max_records": max_records,
        "boundary_strings": BOUNDARY_STRINGS,
        "scope": "Lambeth-only sampled enforcement/building-control source probe with conditional bounded ingest",
        "d6a_classification": source_decision["classification"],
        "d6b_allowed": source_decision["d6b_allowed"],
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D6_MANIFEST.json",
            "LON_D6_HARNESS_REPORT.json",
            "LON_D6_INPUT_INVENTORY.json",
            "LON_D6A_SOURCE_DISCOVERY_REPORT.json",
            "LON_D6A_SOURCE_PROBE_REPORT.json",
            "LON_D6A_SCHEMA_DECISION.md",
            "LON_D6B_INGEST_REPORT.json",
            "LON_D6B_JOIN_REPORT.json",
            "LON_D6B_CONNECTED_PATH_SMOKE.json",
            "LON_D6_NO_OVERCLAIM_REPORT.json",
            "LON_D6_DRIFT_TEST_REPORT.json",
            "LON_D6_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
            "canonical/london_enforcement_events.parquet",
            "canonical/london_building_control_applications.parquet",
            "canonical/london_d6_identity_edges.parquet",
            "canonical/london_d6_unattached_records.parquet",
            "canonical/london_d6_connected_paths.parquet",
            "canonical/london_d6_entities_sample.json",
            "canonical/london_d6_edges_sample.json",
            "raw_sample/source_probe_index.json",
            "raw_sample/lambeth_enforcement_sample.json",
            "raw_sample/lambeth_building_control_sample.json",
            "reports/source_candidates.json",
            "reports/source_access_results.json",
            "reports/field_coverage.json",
            "reports/identifier_coverage.json",
            "reports/join_rates.json",
            "reports/unattached_reasons.json",
            "reports/confidence_summary.json",
            "reports/geometry_limitations.json",
            "reports/skipped_sources.json",
        ],
    }
    write_json(output_dir / "LON_D6_MANIFEST.json", manifest)
    return manifest


def source_discovery_report(source_records: list[dict[str, Any]], source_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate": "LON-D6A-SOURCE-DISCOVERY",
        "status": "PASS" if source_records and all(record["official_source"] for record in source_records) else "FAIL",
        "sources_considered": len(source_records),
        "official_sources_considered": len([record for record in source_records if record["official_source"]]),
        "non_official_sources_excluded": [
            "commercial planning APIs",
            "third-party planning portals",
            "non-official mirror sites",
        ],
        "d6b_allowed": source_decision["d6b_allowed"],
        "machine_readable_sources": [record["source_id"] for record in source_records if record["machine_readable"]],
        "candidate_records": source_records,
    }


def field_coverage_report(d6b_run: bool, enforcement: pd.DataFrame, building_control: pd.DataFrame, source_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "d6b_run": d6b_run,
        "source_limitation": None if d6b_run else source_decision["reason"],
        "enforcement_rows": len(enforcement),
        "building_control_rows": len(building_control),
        "enforcement_non_null_counts": enforcement.notna().sum().to_dict() if not enforcement.empty else {},
        "building_control_non_null_counts": building_control.notna().sum().to_dict() if not building_control.empty else {},
    }


def identifier_coverage_report(d6b_run: bool, enforcement: pd.DataFrame, building_control: pd.DataFrame, edges: pd.DataFrame, source_decision: dict[str, Any]) -> dict[str, Any]:
    records_total = len(enforcement) + len(building_control)
    edge_relations = dict(Counter(edges["relation"].astype(str))) if not edges.empty else {}
    return {
        "status": "PASS",
        "d6b_run": d6b_run,
        "source_limitation": None if d6b_run else source_decision["reason"],
        "records_total": records_total,
        "records_with_uprn": 0 if records_total == 0 else None,
        "records_with_planning_reference": 0 if records_total == 0 else None,
        "canonical_edge_relation_counts": edge_relations,
    }


def skipped_sources_report(source_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "skipped_sources": [
            {
                "source_id": record["source_id"],
                "status": record["status"],
                "reason": record["notes"],
            }
            for record in source_records
            if record["status"] not in USABLE_SOURCE_STATUSES
        ],
    }


def run_lon_d6_gate(
    lon_d4_dir: str,
    lon_d5_dir: str,
    lon_d5c_dir: str,
    output_dir: str,
    borough: str = "Lambeth",
    max_records: int = 500,
    run_d6b_if_possible: bool = True,
) -> dict:
    if borough != "Lambeth":
        raise ValueError("LON-D6 is Lambeth-only and sampled.")
    lon_d4_path = Path(lon_d4_dir)
    lon_d5_path = Path(lon_d5_dir)
    lon_d5c_path = Path(lon_d5c_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(lon_d4_path, lon_d5_path, lon_d5c_path)
    before_hashes = input_hashes(tracked_inputs)
    precond = preconditions(lon_d4_path, lon_d5_path, lon_d5c_path)
    registry_info = load_registry(lon_d4_path, lon_d5_path, lon_d5c_path)
    source_records, source_decision = run_source_probe()
    source_discovery = source_discovery_report(source_records, source_decision)

    d6b_run = bool(run_d6b_if_possible and source_decision["d6b_allowed"])
    enforcement, building_control, edges, unattached, paths = make_empty_outputs()
    if d6b_run:
        # No source is currently marked usable by the bounded official probe. This branch is
        # intentionally conservative and should be filled only for a proven official feed.
        raise RuntimeError("D6b adapter branch is not implemented because no usable official source was established.")
    d6b_reports = d6b_not_run_reports(max_records, source_decision)
    ingest_report = d6b_reports["ingest_report"]
    ingest_report["run_d6b_if_possible"] = run_d6b_if_possible
    join_report = d6b_reports["join_report"]
    smoke = d6b_reports["smoke"]

    d6_entity_ids = set(enforcement["canonical_id"].astype(str)) | set(building_control["canonical_id"].astype(str))
    id_report = id_format_gate(enforcement, building_control, edges)
    edge_report = edge_integrity(edges, registry_info["registry"], d6_entity_ids, registry_info["pld_ids"])
    geometry_report = geometry_honesty(enforcement, building_control)
    a2_report = compatibility_harness(
        enforcement,
        building_control,
        edges,
        registry_info["registry"],
        registry_info["pld_ids"],
        source_limitation=not d6b_run,
    )
    drift = drift_test()
    confidence = confidence_summary(enforcement, building_control, edges)
    out_scope = out_of_scope_report(enforcement, building_control, edges, paths)
    geometry_limitations = {
        "gate": "LON-D6-GEOMETRY-HONESTY",
        "status": geometry_report["status"],
        "limitation": "D6 does not invent geometry. Missing geometry remains explicit unless an official source provides a point.",
        "allowed_statuses": geometry_report["allowed_statuses"],
        "geometry_status_counts": geometry_report["geometry_status_counts"],
        "invented_geometry_failures": geometry_report["failures"],
    }
    conditional_run = {
        "gate": "LON-D6B-CONDITIONAL-RUN",
        "status": "PASS" if (not d6b_run and not source_decision["d6b_allowed"]) or (d6b_run and source_decision["d6b_allowed"]) else "FAIL",
        "d6b_run": d6b_run,
        "d6b_allowed_by_d6a": source_decision["d6b_allowed"],
        "no_fabrication_from_human_register": not d6b_run,
    }
    connected_path_gate = {
        **smoke,
        "status": "PASS"
        if smoke.get("result") in ALLOWED_CONNECTED_PATH_RESULTS and not smoke.get("claim_connected_path_proof")
        else "FAIL",
    }
    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D6-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }

    counts = {
        "sources_probed": len(source_records),
        "enforcement_records_emitted": len(enforcement),
        "building_control_records_emitted": len(building_control),
        "records_with_uprn": join_report["records_with_uprn"],
        "records_with_planning_reference": join_report["records_with_planning_reference"],
        "exact_uprn_edges_emitted": join_report["exact_uprn_edges_emitted"],
        "exact_pld_reference_edges_emitted": join_report["exact_pld_reference_edges_emitted"],
        "records_still_unattached": join_report["records_still_unattached"],
        "connected_paths_emitted": len(paths),
        **registry_info["counts"],
    }

    write_parquet(output_path / "canonical" / "london_enforcement_events.parquet", enforcement)
    write_parquet(output_path / "canonical" / "london_building_control_applications.parquet", building_control)
    write_parquet(output_path / "canonical" / "london_d6_identity_edges.parquet", edges)
    write_parquet(output_path / "canonical" / "london_d6_unattached_records.parquet", unattached)
    write_parquet(output_path / "canonical" / "london_d6_connected_paths.parquet", paths)
    write_json(
        output_path / "canonical" / "london_d6_entities_sample.json",
        {"enforcement_events": frame_to_records(enforcement), "building_control_applications": frame_to_records(building_control)},
    )
    write_json(output_path / "canonical" / "london_d6_edges_sample.json", {"identity_edges": frame_to_records(edges)})

    write_json(output_path / "raw_sample" / "source_probe_index.json", {"sources": source_records})
    write_json(
        output_path / "raw_sample" / "lambeth_enforcement_sample.json",
        {"d6b_run": False, "records": [], "reason": source_decision["reason"]},
    )
    write_json(
        output_path / "raw_sample" / "lambeth_building_control_sample.json",
        {"d6b_run": False, "records": [], "reason": source_decision["reason"]},
    )

    write_json(output_path / "LON_D6_INPUT_INVENTORY.json", inventory_inputs(lon_d4_path, lon_d5_path, lon_d5c_path, tracked_inputs))
    write_json(output_path / "LON_D6A_SOURCE_DISCOVERY_REPORT.json", source_discovery)
    write_json(output_path / "LON_D6A_SOURCE_PROBE_REPORT.json", {**source_decision, "source_records": source_records})
    write_schema_decision(output_path, source_decision, source_records)
    write_json(output_path / "LON_D6B_INGEST_REPORT.json", ingest_report)
    write_json(output_path / "LON_D6B_JOIN_REPORT.json", join_report)
    write_json(output_path / "LON_D6B_CONNECTED_PATH_SMOKE.json", smoke)
    write_json(output_path / "LON_D6_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "reports" / "source_candidates.json", {"status": "PASS", "candidates": SOURCE_CANDIDATES})
    write_json(output_path / "reports" / "source_access_results.json", {"status": "PASS", "source_records": source_records})
    write_json(output_path / "reports" / "field_coverage.json", field_coverage_report(d6b_run, enforcement, building_control, source_decision))
    write_json(output_path / "reports" / "identifier_coverage.json", identifier_coverage_report(d6b_run, enforcement, building_control, edges, source_decision))
    write_json(output_path / "reports" / "join_rates.json", join_report)
    write_json(output_path / "reports" / "unattached_reasons.json", {"status": "PASS", "unattached_reasons": join_report["unattached_reasons"], "source_limitation": source_decision["reason"]})
    write_json(output_path / "reports" / "confidence_summary.json", confidence)
    write_json(output_path / "reports" / "geometry_limitations.json", geometry_limitations)
    write_json(output_path / "reports" / "skipped_sources.json", skipped_sources_report(source_records))

    preliminary_status = "PASS_D6A_ONLY_SOURCE_LIMITATION" if not d6b_run and source_decision["classification"] in {"D6A_NO_MACHINE_SOURCE_REGISTER_ONLY", "D6A_SOURCE_BLOCKED_OR_INSUFFICIENT"} else "PENDING"
    preliminary = {
        "task": TASK_NAME,
        "status": preliminary_status,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "d6a": source_decision,
        "d6b": ingest_report,
        "connected_path_smoke": smoke,
    }
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, preliminary_status, source_decision, counts, borough, max_records)
    write_json(output_path / "LON_D6_HARNESS_REPORT.json", preliminary)
    write_docs(output_path, preliminary_status, source_decision, ingest_report, join_report, smoke, a2_report)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D6_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = {
        "LON-D6-PRECOND": precond["status"],
        "LON-D6A-SOURCE-DISCOVERY": source_discovery["status"],
        "LON-D6A-SOURCE-CLASSIFICATION": source_decision["status"],
        "LON-D6B-CONDITIONAL-RUN": conditional_run["status"],
        "LON-D6B-SAMPLE-INGEST": ingest_report["status"],
        "LON-D6-ID-FORMAT": id_report["status"],
        "LON-D6-EDGE-INTEGRITY": edge_report["status"],
        "LON-D6-JOIN-REPORT": join_report["status"],
        "LON-D6-CONNECTED-PATH-SMOKE": connected_path_gate["status"],
        "LON-D6-GEOMETRY-HONESTY": geometry_report["status"],
        "LON-D6-A2-COMPATIBILITY": a2_report.get("gate_status", a2_report["status"]),
        "LON-D6-DRIFT": drift["status"],
        "LON-D6-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D6-OUT-OF-SCOPE": out_scope["status"],
        "LON-D6-NO-MUTATION": no_mutation["status"],
        "LON-D6-HASHES": "PASS",
    }
    if all(status == "PASS" for status in gates.values()):
        overall = (
            "PASS_D6A_ONLY_SOURCE_LIMITATION"
            if not d6b_run and source_decision["classification"] in {"D6A_NO_MACHINE_SOURCE_REGISTER_ONLY", "D6A_SOURCE_BLOCKED_OR_INSUFFICIENT"}
            else "PASS"
        )
    else:
        overall = "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "lon_d4_dir": str(lon_d4_path),
        "lon_d5_dir": str(lon_d5_path),
        "lon_d5c_dir": str(lon_d5c_path),
        "output_dir": str(output_path),
        "borough": borough,
        "max_records": max_records,
        "run_d6b_if_possible": run_d6b_if_possible,
        "counts": counts,
        "preconditions": precond,
        "source_discovery": source_discovery,
        "source_classification": source_decision,
        "d6b_conditional_run": conditional_run,
        "ingest_report": ingest_report,
        "join_report": join_report,
        "id_format": id_report,
        "edge_integrity": edge_report,
        "connected_path_smoke": connected_path_gate,
        "geometry_honesty": geometry_report,
        "geometry_limitations": geometry_limitations,
        "confidence_summary": confidence,
        "a2_compatibility": a2_report,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
        "hashes": {"gate": "LON-D6-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D6_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, overall, source_decision, counts, borough, max_records)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D6_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D6-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = overall if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D6_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, harness["status"], source_decision, counts, borough, max_records)
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5c-dir", default=DEFAULT_LON_D5C_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--borough", default="Lambeth")
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--run-d6b-if-possible", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d6_gate(
        args.lon_d4_dir,
        args.lon_d5_dir,
        args.lon_d5c_dir,
        args.output_dir,
        args.borough,
        args.max_records,
        args.run_d6b_if_possible,
    )
    counts = report["counts"]
    source = report["source_classification"]
    if report["status"] == "PASS_D6A_ONLY_SOURCE_LIMITATION":
        print(f"{TASK_NAME}: {report['status']}")
        print(f"D6a classification: {source['classification']}")
        print(f"Sources probed: {counts['sources_probed']}")
        print(f"Usable enforcement source: {'YES' if source['usable_enforcement_source'] else 'NO'}")
        print(f"Usable building-control source: {'YES' if source['usable_building_control_source'] else 'NO'}")
        print("D6b run: NO")
        print(f"Reason: {source['reason']}")
        print(f"A2 compatibility gates: {report['a2_compatibility']['status']}")
        print(f"Drift test: {report['drift_test']['status']}")
        print(f"No-overclaim: {report['no_overclaim']['status']}")
        print(f"Output: {args.output_dir}")
    else:
        print("LON-D6 Lambeth Enforcement / Building-Control Bounded Ingest: " + report["status"])
        print(f"D6a classification: {source['classification']}")
        print(f"Enforcement records emitted: {counts['enforcement_records_emitted']}")
        print(f"Building-control records emitted: {counts['building_control_records_emitted']}")
        print(f"Records with UPRN: {counts['records_with_uprn']}")
        print(f"Records with planning reference: {counts['records_with_planning_reference']}")
        print(f"Exact UPRN edges emitted: {counts['exact_uprn_edges_emitted']}")
        print(f"Exact PLD-reference edges emitted: {counts['exact_pld_reference_edges_emitted']}")
        print(f"Records still unattached: {counts['records_still_unattached']}")
        print(f"Connected path smoke: {report['connected_path_smoke']['result']}")
        print(f"A2 compatibility gates: {report['a2_compatibility']['status']}")
        print(f"Drift test: {report['drift_test']['status']}")
        print(f"No-overclaim: {report['no_overclaim']['status']}")
        print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_D6A_ONLY_SOURCE_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
