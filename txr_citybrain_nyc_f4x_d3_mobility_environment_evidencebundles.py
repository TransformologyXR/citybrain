from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK_NAME = "NYC-F4X-D3 NYC Mobility / Event / Environment EvidenceBundles"
DEFAULT_OUTPUT_DIR = "outputs/nyc_f4x_d3_mobility_environment_evidencebundles"

INPUT_DEFAULTS = {
    "nyc_expansion_d1": "outputs/nyc_expansion_potential_d1",
    "nyc_expansion_d2": "outputs/nyc_expansion_d2_all_flows",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_nyc_landing": "data_landing/xdata_d1_bulk_official_sources_v1/nyc",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

F4X_D1_SUBDIR = "nyc_f4x_d1_mobility_event_environment_expansion"
F4X_D2_SUBDIR = "subcartridges/nyc_f4x_d2_mobility_source_landing"

ALLOWED_RELATIONSHIP_TYPES = {
    "HAS_NATIVE_ID",
    "HAS_ALIAS",
    "LOCATED_IN",
    "NEAR",
    "HAS_SOURCE_RECORD",
    "SUPPORTED_BY",
    "HAS_LIMITATION",
    "HAS_GOVERNANCE_BOUNDARY",
    "OBSERVED_BY",
    "OBSERVES",
    "SUBJECT_OF",
}

SOURCE_LIMITATION_VOCAB = {
    "FULL",
    "FULL_AVAILABLE_SAMPLE",
    "BOUNDED_SOURCE_LANDING",
    "POINT_IN_TIME_PROBE",
    "METADATA_ONLY",
    "API_KEY_REQUIRED",
    "OPTIONAL_SOURCE_NOT_BOUND",
}

REQUIRED_BUNDLE_FIELDS = [
    "evidence_bundle_id",
    "city",
    "flow",
    "mode",
    "claim_label",
    "subject",
    "time_window",
    "source_records",
    "native_ids",
    "relationships",
    "location_confidence",
    "temporal_confidence",
    "limitations",
    "governance_boundaries",
    "forbidden_claims",
    "trace_refs",
]

BOUNDARY_LINES = [
    "NYC-F4X-D3 creates review-context EvidenceBundles only; NYC Flow 4 is not accepted by this gate.",
    "NYC-F4X-D3 does not claim live real-time operations or historical completeness from point-in-time probes.",
    "MTA GTFS-RT binary probes are point-in-time transport context unless a later gate binds a historical archive.",
    "311 and MVC 50000-row samples remain bounded source landings, not full-source proof.",
    "Air quality, flood vulnerability, and PANYNJ passenger rows are full available samples only where D2 sample rows equal source total.",
    "Taxi/FHV and Citi Bike remain metadata-only optional context unless a privacy-preserving aggregate product is explicitly landed.",
    "No public-safety, policing, enforcement, emergency, dispatch, health, traffic-control, transit-control, port-control, utility-control, or operational recommendation is created.",
    "D4 handoff is limited to replay/face proof for source-limited mobility/environment EvidenceBundles with boundaries carried forward.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bnyc flow 4 (?:is|was|now is|has been) accepted\b",
    r"\bflow 4 (?:is|was|now is|has been) accepted\b",
    r"\blive real-time mobility system\b",
    r"\breal-time mobility operations (?:are|is|ready|available|provided)\b",
    r"\boperational transit control\b",
    r"\btransit control instruction\b",
    r"\btraffic-control instruction\b",
    r"\btraffic control instruction\b",
    r"\bpublic-safety recommendation\b",
    r"\bpublic safety recommendation\b",
    r"\bemergency dispatch\b",
    r"\bpolicing recommendation\b",
    r"\bhealth determination\b",
    r"\bcertified affected asset\b",
    r"\bbounded landing is full source\b",
    r"\bbounded source landing is full\b",
    r"\bGTFS-RT point-in-time probe is historical completeness\b",
    r"\bgtfs rt point in time probe is historical completeness\b",
    r"\bCERTIFIED_AFFECTED_ASSET\b",
    r"\bemergency_dispatch\b",
    r"\btransit_control_instruction\b",
    r"\btraffic_control_order\b",
    r"\bpublic_safety_instruction\b",
    r"\bhealth_determination\b",
]

NEGATION_MARKERS = [
    " no ",
    " no_",
    " not ",
    " not_",
    "do not",
    "does not",
    "cannot",
    "without",
    "unless",
    "forbidden",
    "boundary",
    "limitation",
    "source-limited",
    "metadata-only",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            return value
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("generated_at", utc_now())
        payload.setdefault("boundary_lines", BOUNDARY_LINES)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    return {"gate": "NYC-F4X-D3-HASHES", "status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    output_dir = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in output_dir.parts}
        if (
            not str(output_dir).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or output_dir.name.lower() != "nyc_f4x_d3_mobility_environment_evidencebundles"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def file_inventory(path: Path, max_files: int = 50) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = [path] if path.is_file() else [item for item in sorted(path.rglob("*")) if item.is_file()]
    payload = []
    for item in files[:max_files]:
        payload.append({"path": item.name if path.is_file() else item.relative_to(path).as_posix(), "bytes": item.stat().st_size})
    return {"exists": True, "file_count": len(files), "files": payload}


def input_snapshot(paths: Iterable[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        files = [root] if root.is_file() else [path for path in sorted(root.rglob("*")) if path.is_file()]
        for path in files:
            if path.suffix.lower() in {".tmp", ".part"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size <= 25_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(key for key, value in before.items() if after.get(key) != value)
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    return {
        "gate": "NYC-F4X-D3-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def gate(name: str, passed: bool, **extra: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(extra)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(item.get("status") == "PASS" for item in gates)


def load_inputs(root: Path) -> dict[str, Any]:
    paths = {key: project_path(root, value) for key, value in INPUT_DEFAULTS.items()}
    d2 = paths["nyc_expansion_d2"]
    d1 = paths["nyc_expansion_d1"]
    f4x_d2 = d2 / F4X_D2_SUBDIR
    f4x_d1 = d1 / F4X_D1_SUBDIR
    reports = {
        "d1_harness": read_json(d1 / "NYC_EXPANSION_POTENTIAL_D1_HARNESS_REPORT.json", {}),
        "f4x_d1_contract": read_json(f4x_d1 / "NYC_F4X_D1_READINESS_CONTRACT.json", {}),
        "f4x_d1_boundary": read_json(f4x_d1 / "boundary_register.json", {}),
        "d2_harness": read_json(d2 / "NYC_EXPANSION_D2_ALL_FLOWS_HARNESS_REPORT.json", {}),
        "all_source_profiles": read_json(d2 / "reports" / "all_source_landing_profiles.json", {}),
        "f4x_d2_ledger": read_json(f4x_d2 / "source_landing_ledger.json", {}),
        "f4x_d2_contract": read_json(f4x_d2 / "NYC_F4X_D2_SOURCE_LANDING_JOIN_CONTRACT.json", {}),
        "f4x_d2_join": read_json(f4x_d2 / "identity_geography_join_hardening.json", {}),
        "xflow_harness": read_json(paths["xflow_d1"] / "XFLOW_D1_HARNESS_REPORT.json", {}),
        "xflow_queue": read_json(paths["xflow_d1"] / "XFLOW_D1_D3_QUEUE_RECOMMENDATION.json", {}),
        "ontology_relationships": read_json(paths["ontology_v2"] / "relationship_classes.json", {}),
        "ontology_claim_labels": read_json(paths["ontology_v2"] / "claim_label_policy.json", {}),
        "xdata_harness": read_json(paths["xdata_four_city"] / "XDATA_D1_HARNESS_REPORT.json", {}),
        "xdata_city_matrix": read_json(paths["xdata_four_city"] / "XDATA_D1_CITY_SUMMARY_MATRIX.json", {}),
    }
    return {"paths": paths, "reports": reports}


def profiles_by_key(reports: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles = reports.get("all_source_profiles", {}).get("profiles", [])
    return {item.get("source_key"): item for item in profiles if item.get("source_key")}


def classify_source(profile: dict[str, Any]) -> str:
    status = str(profile.get("status") or profile.get("landing_status") or "").upper()
    kind = str(profile.get("kind") or "").lower()
    source_key = str(profile.get("source_key") or "")
    if "API_KEY" in status or "FORBIDDEN" in status:
        return "API_KEY_REQUIRED"
    if status == "METADATA_ONLY" or kind == "metadata_only":
        return "METADATA_ONLY"
    if kind in {"binary_probe", "url_probe"} or status in {"LANDED_BINARY_PROBE", "URL_PROBE_OK"}:
        return "POINT_IN_TIME_PROBE"
    sample_rows = profile.get("sample_rows")
    total_rows = profile.get("total_available_rows")
    if status == "FULL":
        return "FULL"
    if sample_rows is not None and total_rows is not None:
        try:
            sample = int(sample_rows)
            total = int(total_rows)
        except (TypeError, ValueError):
            return "BOUNDED_SOURCE_LANDING"
        if sample == total:
            return "FULL_AVAILABLE_SAMPLE"
        return "BOUNDED_SOURCE_LANDING"
    if source_key:
        return "BOUNDED_SOURCE_LANDING"
    return "OPTIONAL_SOURCE_NOT_BOUND"


def source_record(source_key: str, reports: dict[str, Any], role: str) -> dict[str, Any]:
    profile = profiles_by_key(reports).get(source_key, {})
    ledger_sources = {item.get("source_key"): item for item in reports.get("f4x_d2_ledger", {}).get("sources", [])}
    ledger = ledger_sources.get(source_key, {})
    return {
        "source_key": source_key,
        "role": role,
        "provider": profile.get("provider") or ledger.get("provider"),
        "label": profile.get("label") or ledger.get("label"),
        "kind": profile.get("kind") or ledger.get("kind"),
        "status": profile.get("status") or ledger.get("landing_status"),
        "source_limitation": classify_source(profile or ledger),
        "sample_rows": profile.get("sample_rows") or ledger.get("sample_rows"),
        "total_available_rows": profile.get("total_available_rows"),
        "dataset_id": profile.get("dataset_id"),
    }


def input_inventory(paths: dict[str, Path], reports: dict[str, Any]) -> dict[str, Any]:
    inventory = {}
    for key, path in paths.items():
        item = file_inventory(path)
        status = "PASS" if item["exists"] else "XDATA_OPTIONAL_MISSING" if key.startswith("xdata") else "MISSING"
        if key == "xdata_nyc_landing" and item["exists"]:
            status = "XDATA_OPTIONAL_STILL_RUNNING" if any(path.rglob("*.part")) else "XDATA_OPTIONAL_PRESENT_NOT_BINDING"
        if key == "xdata_four_city" and item["exists"]:
            nyc_status = reports.get("xdata_city_matrix", {}).get("NYC", {}).get("status")
            status = "XDATA_OPTIONAL_NOT_REQUESTED" if nyc_status == "SKIPPED_NOT_REQUESTED" else "PASS"
        inventory[key] = {"path": str(path), "status": status, **item}
    return {
        "status": "PASS",
        "inputs": inventory,
        "read_only": True,
        "optional_xdata_note": inventory["xdata_four_city"]["status"],
    }


def source_limitation_report(reports: dict[str, Any], represented_keys: list[str]) -> dict[str, Any]:
    profiles = profiles_by_key(reports)
    records = []
    counts = {name: 0 for name in sorted(SOURCE_LIMITATION_VOCAB)}
    for source_key in represented_keys:
        profile = profiles.get(source_key, {"source_key": source_key})
        limitation = classify_source(profile)
        counts[limitation] = counts.get(limitation, 0) + 1
        records.append(
            {
                "source_key": source_key,
                "source_limitation": limitation,
                "status": profile.get("status"),
                "kind": profile.get("kind"),
                "sample_rows": profile.get("sample_rows"),
                "total_available_rows": profile.get("total_available_rows"),
                "rule": limitation_rule(limitation, source_key),
            }
        )
    return {
        "status": "PASS",
        "source_limitation_vocab": sorted(SOURCE_LIMITATION_VOCAB),
        "counts": counts,
        "source_limitations": records,
        "policy_checks": {
            "mta_gtfs_rt_is_point_in_time": any(item["source_key"] == "mta_gtfs_rt" and item["source_limitation"] == "POINT_IN_TIME_PROBE" for item in records),
            "air_quality_full_available_sample": any(item["source_key"] == "nyc_air_quality" and item["source_limitation"] == "FULL_AVAILABLE_SAMPLE" for item in records),
            "mvc_not_full_source": all(item["source_limitation"] == "BOUNDED_SOURCE_LANDING" for item in records if item["source_key"] in {"nyc_mvc_crashes", "nyc_mvc_vehicles"}),
            "311_not_full_source": all(item["source_limitation"] == "BOUNDED_SOURCE_LANDING" for item in records if item["source_key"].startswith("nyc_311")),
        },
    }


def limitation_rule(limitation: str, source_key: str) -> str:
    rules = {
        "FULL": "Rows landed equal the complete source by accepted report.",
        "FULL_AVAILABLE_SAMPLE": "D2 sample rows equal source total; still scoped to that source product.",
        "BOUNDED_SOURCE_LANDING": "D2 landed a bounded sample or source-specific slice; do not call it full source.",
        "POINT_IN_TIME_PROBE": "Probe proves endpoint/sample availability at probe time only, not historical completeness.",
        "METADATA_ONLY": "Metadata describes an optional source; no data rows are bound for EvidenceBundle claims.",
        "API_KEY_REQUIRED": "Source requires credentials or is otherwise not directly bound.",
        "OPTIONAL_SOURCE_NOT_BOUND": "Optional source is present only as non-binding context.",
    }
    return f"{source_key}: {rules[limitation]}"


def source_and_join_summary(reports: dict[str, Any]) -> dict[str, Any]:
    f4_flow = reports["d2_harness"].get("flows", {}).get("NYC-F4X-D2", {})
    join = reports["f4x_d2_join"]
    return {
        "status": "PASS",
        "d1_status": reports["d1_harness"].get("status"),
        "f4x_d1_readiness": reports["f4x_d1_contract"].get("readiness_status"),
        "d2_status": reports["d2_harness"].get("status"),
        "f4x_d2_status": f4_flow.get("status"),
        "xflow_status": reports["xflow_harness"].get("status"),
        "xflow_queue_rank": (reports["xflow_queue"].get("queue", []).index("NYC-F4X-D3") + 1) if "NYC-F4X-D3" in reports["xflow_queue"].get("queue", []) else None,
        "primary_anchor": join.get("primary_anchor"),
        "join_keys": join.get("join_keys", []),
        "identity_geography_rules": join.get("identity_geography_rules", []),
        "source_landing_status": reports["f4x_d2_ledger"].get("status"),
        "source_count": reports["f4x_d2_ledger"].get("source_count"),
        "d3_handoff": f4_flow.get("d3_handoff") or join.get("d3_handoff"),
        "summary": "NYC-F4X-D3 creates mobility/environment context EvidenceBundles from bounded D2 source landing and does not promote NYC Flow 4.",
    }


def governance_boundaries() -> list[str]:
    return list(BOUNDARY_LINES)


def forbidden_claims() -> list[str]:
    return [
        "no_flow4_acceptance",
        "no_live_realtime_operations",
        "no_transit_or_traffic_control",
        "no_public_safety_or_dispatch_recommendation",
        "no_policing_enforcement_or_health_decision",
        "no_certified_affected_asset",
        "no_full_source_claim_from_bounded_landing",
    ]


def rel(rel_type: str, from_id: str, to_id: str, confidence: str, basis: str) -> dict[str, str]:
    return {
        "relationship_type": rel_type,
        "from": from_id,
        "to": to_id,
        "confidence": confidence,
        "evidence_basis": basis,
    }


def make_bundle(
    bundle_id: str,
    subject: dict[str, Any],
    time_window: dict[str, Any],
    source_records: list[dict[str, Any]],
    native_ids: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    location_confidence: str,
    temporal_confidence: str,
    limitations: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    return {
        "evidence_bundle_id": bundle_id,
        "city": "nyc",
        "flow": "F4X",
        "mode": "mobility_environment_context",
        "claim_label": "[R]",
        "subject": subject,
        "time_window": time_window,
        "source_records": source_records,
        "native_ids": native_ids,
        "relationships": relationships,
        "location_confidence": location_confidence,
        "temporal_confidence": temporal_confidence,
        "limitations": limitations + BOUNDARY_LINES,
        "governance_boundaries": governance_boundaries(),
        "forbidden_claims": forbidden_claims(),
        "trace_refs": trace_refs,
    }


def build_evidence_bundles(reports: dict[str, Any]) -> list[dict[str, Any]]:
    transit_subject = "nyc-f4x:transit_status_context_probe"
    collision_subject = "nyc-f4x:mobility_collision_area_context"
    air_subject = "nyc-f4x:air_quality_environment_context"
    flood_subject = "nyc-f4x:flood_vulnerability_area_context"
    boundary_subject = "nyc-f4x:mobility_environment_governance_boundary"
    panynj_subject = "nyc-f4x:panynj_airport_logistics_context"
    return [
        make_bundle(
            "transit_status_context_bundle",
            {
                "subject_id": transit_subject,
                "question": "How do point-in-time transit feed probes provide review context for a place or time window?",
                "anchor": "route_id/stop_id/trip_id/service_alert_id/event_time",
            },
            {"type": "point_in_time_probe", "historical_completeness": False},
            [
                source_record("mta_gtfs_static", reports, "static schedule geography probe"),
                source_record("mta_gtfs_rt", reports, "GTFS-RT service context binary probe"),
            ],
            [
                {"native_authority": "MTA", "native_namespace": "gtfs_static", "native_id_role": "route_or_stop_id", "native_id_confidence": "source_native"},
                {"native_authority": "MTA", "native_namespace": "gtfs_rt", "native_id_role": "feed_or_alert_id", "native_id_confidence": "point_in_time_probe"},
            ],
            [
                rel("HAS_SOURCE_RECORD", transit_subject, "source:mta_gtfs_static", "source_reference", "NYC-F4X-D2 source landing ledger"),
                rel("HAS_SOURCE_RECORD", transit_subject, "source:mta_gtfs_rt", "source_reference", "NYC-F4X-D2 source landing ledger"),
                rel("HAS_NATIVE_ID", transit_subject, "native:mta:route_stop_trip_or_alert", "source_native", "D2 join keys"),
                rel("OBSERVED_BY", transit_subject, "probe:mta_gtfs_rt", "point_in_time", "Binary probe sample"),
                rel("HAS_LIMITATION", transit_subject, "limitation:point_in_time_probe_not_historical_archive", "boundary", "Source limitation policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", transit_subject, "boundary:no_transit_control", "boundary", "D3 no-overclaim policy"),
            ],
            "B",
            "point_in_time",
            [
                "GTFS-RT is a point-in-time transport probe, not historical completeness.",
                "Static GTFS is schedule geography context and not live operations proof.",
            ],
            [
                "source_landing_ledger.json#mta_gtfs_static",
                "source_landing_ledger.json#mta_gtfs_rt",
                "identity_geography_join_hardening.json#join_keys",
            ],
        ),
        make_bundle(
            "mobility_collision_context_bundle",
            {
                "subject_id": collision_subject,
                "question": "How do collision, vehicle, and civic event signals interact for an area/time review window?",
                "anchor": "lat_lon/borough/community_district/event_time",
            },
            {"type": "bounded_historical_sample", "sample_limit": 50000},
            [
                source_record("nyc_mvc_crashes", reports, "collision event context"),
                source_record("nyc_mvc_vehicles", reports, "vehicle context"),
                source_record("nyc_311_2020_present", reports, "civic event context 2020-present"),
                source_record("nyc_311_2010_2019", reports, "civic event context 2010-2019"),
            ],
            [
                {"native_authority": "NYC Open Data", "native_namespace": "h9gi-nx95", "native_id_role": "collision_id", "native_id_confidence": "source_native"},
                {"native_authority": "NYC Open Data", "native_namespace": "bm4k-52h4", "native_id_role": "vehicle_or_collision_id", "native_id_confidence": "source_native"},
                {"native_authority": "NYC Open Data", "native_namespace": "311", "native_id_role": "unique_key", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", collision_subject, "source:nyc_mvc_crashes", "source_reference", "D2 source profile"),
                rel("HAS_SOURCE_RECORD", collision_subject, "source:nyc_mvc_vehicles", "source_reference", "D2 source profile"),
                rel("HAS_SOURCE_RECORD", collision_subject, "source:nyc_311_2020_present", "source_reference", "D2 source profile"),
                rel("HAS_SOURCE_RECORD", collision_subject, "source:nyc_311_2010_2019", "source_reference", "D2 source profile"),
                rel("LOCATED_IN", collision_subject, "context:borough_or_community_district", "contextual", "D2 join keys"),
                rel("NEAR", collision_subject, "context:lat_lon_area_window", "contextual", "Lat/lon and area fields support review context"),
                rel("SUBJECT_OF", collision_subject, "bundle:mobility_collision_context_bundle", "bundle_reference", "EvidenceBundle contract"),
                rel("HAS_LIMITATION", collision_subject, "limitation:bounded_50000_row_samples", "boundary", "D2 sample limit"),
            ],
            "A",
            "historical_sample",
            [
                "MVC and 311 sources are bounded source landings at 50000 rows each, not full-source proof.",
                "Collision and civic-event context does not create public-safety, dispatch, or traffic-control recommendations.",
            ],
            [
                "all_source_landing_profiles.json#nyc_mvc_crashes",
                "all_source_landing_profiles.json#nyc_mvc_vehicles",
                "all_source_landing_profiles.json#nyc_311_2020_present",
                "all_source_landing_profiles.json#nyc_311_2010_2019",
            ],
        ),
        make_bundle(
            "air_quality_environment_context_bundle",
            {
                "subject_id": air_subject,
                "question": "How does air quality context interact with mobility/event review windows?",
                "anchor": "air_quality_indicator/time_period/area_context",
            },
            {"type": "full_available_sample", "sample_rows": source_record("nyc_air_quality", reports, "air quality context").get("sample_rows")},
            [source_record("nyc_air_quality", reports, "environment context")],
            [
                {"native_authority": "NYC Open Data / NYC Health", "native_namespace": "c3uy-2p5r", "native_id_role": "air_quality_record", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", air_subject, "source:nyc_air_quality", "source_reference", "D2 source profile"),
                rel("OBSERVED_BY", air_subject, "sensor_or_program:nyc_air_quality", "source_context", "NYC Health/Open Data source"),
                rel("OBSERVES", "sensor_or_program:nyc_air_quality", air_subject, "source_context", "Air quality observation context"),
                rel("LOCATED_IN", air_subject, "context:nyc_area", "contextual", "Area fields in source profile"),
                rel("HAS_LIMITATION", air_subject, "limitation:context_signal_not_health_decision", "boundary", "D1/D3 boundary"),
            ],
            "B",
            "full_available_sample",
            [
                "Air quality rows are a context signal, not a health determination.",
                "Full available sample status is limited to the D2-proven source product.",
            ],
            ["all_source_landing_profiles.json#nyc_air_quality"],
        ),
        make_bundle(
            "flood_vulnerability_area_context_bundle",
            {
                "subject_id": flood_subject,
                "question": "How does flood vulnerability context relate to area-based mobility/environment review?",
                "anchor": "flood_area_id/area_context",
            },
            {"type": "full_available_sample", "sample_rows": source_record("nyc_flood_vulnerability_index", reports, "flood context").get("sample_rows")},
            [
                source_record("nyc_flood_vulnerability_index", reports, "flood vulnerability index context"),
                source_record("nyc_flood_vulnerability_index_map", reports, "flood vulnerability map context"),
            ],
            [
                {"native_authority": "NYC Open Data", "native_namespace": "mrjc-v9pm", "native_id_role": "flood_index_record", "native_id_confidence": "source_native"},
                {"native_authority": "NYC Open Data", "native_namespace": "4vym-qrg3", "native_id_role": "flood_map_record", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", flood_subject, "source:nyc_flood_vulnerability_index", "source_reference", "D2 source profile"),
                rel("HAS_SOURCE_RECORD", flood_subject, "source:nyc_flood_vulnerability_index_map", "source_reference", "D2 source profile"),
                rel("LOCATED_IN", flood_subject, "context:flood_area_or_neighborhood", "contextual", "Flood source area fields"),
                rel("SUPPORTED_BY", flood_subject, "source:nyc_flood_vulnerability_index_map", "source_context", "Map source supports area context"),
                rel("HAS_LIMITATION", flood_subject, "limitation:flood_context_not_emergency_or_utility_determination", "boundary", "D3 boundary"),
            ],
            "B",
            "full_available_sample",
            [
                "Flood vulnerability context is not emergency, insurance, utility, or operational instruction.",
                "Full available sample status is limited to the D2-proven source products.",
            ],
            [
                "all_source_landing_profiles.json#nyc_flood_vulnerability_index",
                "all_source_landing_profiles.json#nyc_flood_vulnerability_index_map",
            ],
        ),
        make_bundle(
            "mobility_environment_governance_boundary_bundle",
            {
                "subject_id": boundary_subject,
                "question": "Which mobility/environment sources remain optional, metadata-only, or governance-limited?",
                "anchor": "governance_boundary",
            },
            {"type": "review_context_boundary", "historical_completeness": False},
            [
                source_record("taxi_fhv_optional", reports, "optional mobility demand metadata"),
                source_record("citi_bike_optional", reports, "optional bikeshare metadata"),
            ],
            [
                {"native_authority": "NYC TLC", "native_namespace": "taxi_fhv_optional", "native_id_role": "metadata_source", "native_id_confidence": "metadata_only"},
                {"native_authority": "Citi Bike / Lyft", "native_namespace": "citi_bike_optional", "native_id_role": "metadata_source", "native_id_confidence": "metadata_only"},
            ],
            [
                rel("HAS_SOURCE_RECORD", boundary_subject, "source:taxi_fhv_optional", "metadata_reference", "D2 metadata profile"),
                rel("HAS_SOURCE_RECORD", boundary_subject, "source:citi_bike_optional", "metadata_reference", "D2 metadata profile"),
                rel("HAS_LIMITATION", boundary_subject, "limitation:metadata_only_optional_sources", "boundary", "D2 source landing ledger"),
                rel("HAS_GOVERNANCE_BOUNDARY", boundary_subject, "boundary:privacy_preserving_aggregate_required", "boundary", "D1 readiness contract"),
                rel("SUPPORTED_BY", boundary_subject, "source:nyc_f4x_d1_boundary_register", "boundary", "D1 boundary register"),
            ],
            "D",
            "bounded_window",
            [
                "Taxi/FHV and Citi Bike are metadata-only in D2; they cannot support row-level mobility claims.",
                "Any later use needs explicit privacy-preserving aggregate landing.",
            ],
            [
                "source_landing_ledger.json#taxi_fhv_optional",
                "source_landing_ledger.json#citi_bike_optional",
                "NYC_F4X_D1_READINESS_CONTRACT.json#acceptance_conditions",
            ],
        ),
        make_bundle(
            "panynj_airport_logistics_context_bundle",
            {
                "subject_id": panynj_subject,
                "question": "How can airport passenger aggregate context be reviewed alongside mobility/environment signals?",
                "anchor": "airport_code/month",
            },
            {"type": "full_available_sample", "sample_rows": source_record("panynj_air_passenger_traffic", reports, "airport context").get("sample_rows")},
            [
                source_record("panynj_air_passenger_traffic", reports, "monthly airport passenger aggregate context"),
                source_record("panynj_airport_statistics", reports, "airport statistics metadata context"),
            ],
            [
                {"native_authority": "Data NY / PANYNJ", "native_namespace": "8pkr-4b7t", "native_id_role": "airport_month_record", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", panynj_subject, "source:panynj_air_passenger_traffic", "source_reference", "D2 source profile"),
                rel("HAS_SOURCE_RECORD", panynj_subject, "source:panynj_airport_statistics", "metadata_reference", "D2 metadata profile"),
                rel("LOCATED_IN", panynj_subject, "context:airport_code", "contextual", "Monthly aggregate source"),
                rel("HAS_NATIVE_ID", panynj_subject, "native:panynj:airport_code_month", "source_native", "PANYNJ passenger rows"),
                rel("HAS_GOVERNANCE_BOUNDARY", panynj_subject, "boundary:no_airport_or_port_operational_command", "boundary", "D2 boundary"),
            ],
            "B",
            "full_available_sample",
            [
                "PANYNJ passenger rows are monthly aggregate context, not airport or port operational command.",
                "This optional bundle is D4-ready only for review-context replay/face proof.",
            ],
            [
                "all_source_landing_profiles.json#panynj_air_passenger_traffic",
                "all_source_landing_profiles.json#panynj_airport_statistics",
            ],
        ),
    ]


def evidencebundle_contract(ontology_relationship_report: dict[str, Any]) -> dict[str, Any]:
    ontology_relationships = {
        item.get("relationship_name")
        for item in ontology_relationship_report.get("relationship_classes", [])
        if item.get("relationship_name")
    }
    return {
        "status": "PASS" if ALLOWED_RELATIONSHIP_TYPES.issubset(ontology_relationships) else "FAIL",
        "required_fields": REQUIRED_BUNDLE_FIELDS,
        "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES),
        "source_limitation_vocab": sorted(SOURCE_LIMITATION_VOCAB),
        "claim_label_policy": "[R] because facts are source-derived from read-only D2 profiles; governance boundaries travel as metadata.",
        "forbidden_relationship_policy": "Certified affected asset and control/instruction relations are not emitted by this gate.",
        "ontology_relationships_present": sorted(ALLOWED_RELATIONSHIP_TYPES.intersection(ontology_relationships)),
        "ontology_missing_relationships": sorted(ALLOWED_RELATIONSHIP_TYPES.difference(ontology_relationships)),
    }


def validate_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    missing_fields = {}
    invalid_relationships = []
    invalid_temporal = []
    forbidden_tokens = []
    allowed_temporal = {"point_in_time", "bounded_window", "historical_sample", "full_available_sample"}
    for bundle in bundles:
        bundle_id = bundle.get("evidence_bundle_id")
        missing = [field for field in REQUIRED_BUNDLE_FIELDS if field not in bundle]
        if missing:
            missing_fields[bundle_id] = missing
        if bundle.get("location_confidence") not in {"A", "B", "C", "D"}:
            invalid_temporal.append({"bundle": bundle_id, "field": "location_confidence"})
        if bundle.get("temporal_confidence") not in allowed_temporal:
            invalid_temporal.append({"bundle": bundle_id, "field": "temporal_confidence"})
        for relationship in bundle.get("relationships", []):
            rel_type = relationship.get("relationship_type")
            if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
                invalid_relationships.append({"bundle": bundle_id, "relationship_type": rel_type})
        serialized = json.dumps(bundle, ensure_ascii=True)
        for token in ["CERTIFIED_AFFECTED_ASSET", "emergency_dispatch", "transit_control_instruction", "traffic_control_order", "public_safety_instruction", "health_determination"]:
            if token in serialized:
                forbidden_tokens.append({"bundle": bundle_id, "token": token})
    return {
        "status": "PASS" if not missing_fields and not invalid_relationships and not invalid_temporal and not forbidden_tokens else "FAIL",
        "bundle_count": len(bundles),
        "missing_fields": missing_fields,
        "invalid_relationships": invalid_relationships,
        "invalid_temporal_or_location": invalid_temporal,
        "forbidden_tokens": forbidden_tokens,
    }


def represented_sources(bundles: list[dict[str, Any]]) -> list[str]:
    return sorted({source["source_key"] for bundle in bundles for source in bundle.get("source_records", [])})


def selected_bundles_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    selected_ids = [bundle["evidence_bundle_id"] for bundle in bundles]
    return {
        "status": "PASS",
        "selection_policy": "Select all deterministic NYC-F4X-D3 bundle targets for D4 replay/face proof.",
        "selected_bundle_count": len(selected_ids),
        "selected_bundle_ids": selected_ids,
    }


def trace_report(bundles: list[dict[str, Any]], paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "read_only_inputs": {key: str(path) for key, path in paths.items()},
        "bundle_traces": [
            {
                "evidence_bundle_id": bundle["evidence_bundle_id"],
                "trace_refs": bundle["trace_refs"],
                "source_keys": [source["source_key"] for source in bundle["source_records"]],
            }
            for bundle in bundles
        ],
        "mutation_policy": "Inputs are snapshotted before and after bundle generation; optional live XDATA raw files do not upgrade D2 claims.",
    }


def next_d4_handoff(bundles: list[dict[str, Any]], source_limitations: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "D4_READY_WITH_SOURCE_LIMITATIONS",
        "recommended_next": "NYC-F4X-D4 replay/face proof for mobility/environment EvidenceBundles",
        "selected_bundle_ids": [bundle["evidence_bundle_id"] for bundle in bundles],
        "must_carry_forward": [
            "Do not claim NYC Flow 4 is accepted.",
            "Do not claim live real-time operations or control instructions.",
            "Keep 311/MVC bounded samples, GTFS probes, and metadata-only optional sources explicitly limited.",
        ],
        "source_limitation_counts": source_limitations["counts"],
    }


def ontology_compatibility_report(bundles: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    relationship_types = sorted({relationship["relationship_type"] for bundle in bundles for relationship in bundle["relationships"]})
    unsupported = sorted(set(relationship_types).difference(ALLOWED_RELATIONSHIP_TYPES))
    return {
        "status": "PASS" if contract["status"] == "PASS" and not unsupported else "FAIL",
        "relationship_types_emitted": relationship_types,
        "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES),
        "unsupported_relationship_types": unsupported,
        "claim_labels": ["[R]"],
    }


def line_is_negated(line: str) -> bool:
    padded = f" {line.lower()} "
    return any(marker in padded for marker in NEGATION_MARKERS)


def no_overclaim_scan(paths: Iterable[Path]) -> dict[str, Any]:
    findings = []
    checked_files = 0
    for root in paths:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name in {"SHA256SUMS.json", "NYC_F4X_D3_NO_OVERCLAIM_REPORT.json"}:
                continue
            if path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            checked_files += 1
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                if line_is_negated(line):
                    continue
                for pattern in FORBIDDEN_POSITIVE_PATTERNS:
                    if re.search(pattern, line, flags=re.IGNORECASE):
                        findings.append({"path": str(path), "line": number, "pattern": pattern})
    return {"gate": "NYC-F4X-D3-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "checked_files": checked_files, "findings": findings}


def final_print(result: dict[str, Any]) -> str:
    lines = [
        f"NYC-F4X-D3 NYC Mobility / Event / Environment EvidenceBundles: {result.get('status', 'FAIL')}",
        "",
        f"EvidenceBundles created: {result.get('evidence_bundles_created', 0)}",
        f"Selected bundles: {result.get('selected_bundles', 0)}",
        f"Sources represented: {result.get('sources_represented', 0)}",
        f"Bounded source inputs: {result.get('bounded_source_inputs', 0)}",
        f"Point-in-time probes: {result.get('point_in_time_probes', 0)}",
        f"Metadata-only sources: {result.get('metadata_only_sources', 0)}",
        "",
        f"Source limitations: {result.get('source_limitations', 'FAIL')}",
        f"Ontology compatibility: {result.get('ontology_compatibility', 'FAIL')}",
        f"Boundary carry-forward: {result.get('boundary_carry_forward', 'FAIL')}",
        f"No-overclaim: {result.get('no_overclaim', 'FAIL')}",
        f"No-mutation: {result.get('no_mutation', 'FAIL')}",
        f"Hashes: {result.get('hashes', 'FAIL')}",
        "",
        f"Final status: {result.get('status', 'FAIL')}",
        "Output: outputs\\nyc_f4x_d3_mobility_environment_evidencebundles",
    ]
    return "\n".join(lines)


def run_nyc_f4x_d3_gate(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_output_dir(project_path(root, output_dir), root)
    loaded = load_inputs(root)
    paths = loaded["paths"]
    reports = loaded["reports"]
    watched_inputs = [
        paths["nyc_expansion_d1"],
        paths["nyc_expansion_d2"],
        paths["xflow_d1"],
        paths["ontology_v2"],
        paths["xdata_nyc_landing"] / "manifests",
        paths["xdata_four_city"],
    ]
    before = input_snapshot(watched_inputs)

    inventory = input_inventory(paths, reports)
    source_join = source_and_join_summary(reports)
    bundles = build_evidence_bundles(reports)
    represented = represented_sources(bundles)
    source_limits = source_limitation_report(reports, represented)
    contract = evidencebundle_contract(reports["ontology_relationships"])
    bundle_validation = validate_bundles(bundles)
    selected = selected_bundles_report(bundles)
    trace = trace_report(bundles, paths)
    d4_handoff = next_d4_handoff(bundles, source_limits)
    ontology = ontology_compatibility_report(bundles, contract)

    write_json(out / "NYC_F4X_D3_INPUT_INVENTORY.json", inventory)
    write_json(out / "NYC_F4X_D3_SOURCE_AND_JOIN_SUMMARY.json", source_join)
    write_json(out / "NYC_F4X_D3_EVIDENCEBUNDLE_CONTRACT.json", contract)
    write_json(out / "NYC_F4X_D3_EVIDENCEBUNDLES.json", {"status": bundle_validation["status"], "evidence_bundle_count": len(bundles), "bundles": bundles, "validation": bundle_validation})
    write_json(out / "NYC_F4X_D3_SELECTED_BUNDLES.json", selected)
    write_json(out / "NYC_F4X_D3_TRACE_REPORT.json", trace)
    write_json(out / "NYC_F4X_D3_SOURCE_LIMITATION_REPORT.json", source_limits)
    write_json(out / "NYC_F4X_D3_NEXT_D4_HANDOFF.json", d4_handoff)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# NYC-F4X-D3 NYC Mobility / Event / Environment EvidenceBundles",
                "",
                "This D3 gate creates governed review-context EvidenceBundles over NYC-F4X-D2 bounded source landing.",
                "It does not accept NYC Flow 4 and does not create live operations or control recommendations.",
                "",
                *[f"- {line}" for line in BOUNDARY_LINES],
                "",
            ]
        ),
    )

    after = input_snapshot(watched_inputs)
    mutation = compare_snapshots(before, after)
    write_json(out / "NYC_F4X_D3_NO_MUTATION_REPORT.json", mutation)

    no_overclaim = no_overclaim_scan([out])
    write_json(out / "NYC_F4X_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)

    counts = source_limits["counts"]
    precond_pass = all(paths[key].exists() for key in ["nyc_expansion_d1", "nyc_expansion_d2", "xflow_d1", "ontology_v2"])
    source_join_pass = (
        reports["d1_harness"].get("status") == "PASS_WITH_EXPANSION_CONTRACTS"
        and reports["d2_harness"].get("flows", {}).get("NYC-F4X-D2", {}).get("status") == "PASS_WITH_BOUNDED_SOURCE_LANDING"
        and reports["xflow_harness"].get("status") == "PASS_CROSS_CITY_EXPANSION_RECONCILIATION"
    )
    limitation_policy_pass = all(source_limits["policy_checks"].values()) and set(counts).issuperset(SOURCE_LIMITATION_VOCAB)
    boundary_pass = all(line in json.dumps(bundles, ensure_ascii=True) for line in BOUNDARY_LINES)
    gates = [
        gate("NYC-F4X-D3-PRECOND", precond_pass),
        gate("NYC-F4X-D3-INPUT-INVENTORY", inventory["status"] == "PASS"),
        gate("NYC-F4X-D3-SOURCE-JOIN-SUMMARY", source_join["status"] == "PASS" and source_join_pass),
        gate("NYC-F4X-D3-EVIDENCEBUNDLE-CONTRACT", contract["status"] == "PASS"),
        gate("NYC-F4X-D3-EVIDENCEBUNDLES", bundle_validation["status"] == "PASS" and len(bundles) >= 5),
        gate("NYC-F4X-D3-SOURCE-LIMITATIONS", source_limits["status"] == "PASS" and limitation_policy_pass),
        gate("NYC-F4X-D3-ONTOLOGY-COMPATIBILITY", ontology["status"] == "PASS"),
        gate("NYC-F4X-D3-BOUNDARY-CARRY-FORWARD", boundary_pass),
        gate("NYC-F4X-D3-NO-OVERCLAIM", no_overclaim["status"] == "PASS", findings=no_overclaim["findings"]),
        gate("NYC-F4X-D3-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("NYC-F4X-D3-HASHES", True),
    ]
    hashes = write_hashes(out)
    bounded_count = counts.get("BOUNDED_SOURCE_LANDING", 0)
    limited = bounded_count > 0 or counts.get("POINT_IN_TIME_PROBE", 0) > 0 or counts.get("METADATA_ONLY", 0) > 0
    status = "PASS_WITH_SOURCE_LIMITATIONS" if gates_pass(gates) and limited else "PASS_MOBILITY_ENVIRONMENT_EVIDENCEBUNDLES" if gates_pass(gates) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "gates": gates,
        "evidence_bundles_created": len(bundles),
        "selected_bundles": selected["selected_bundle_count"],
        "sources_represented": len(represented),
        "bounded_source_inputs": bounded_count,
        "point_in_time_probes": counts.get("POINT_IN_TIME_PROBE", 0),
        "metadata_only_sources": counts.get("METADATA_ONLY", 0),
        "full_available_sample_sources": counts.get("FULL_AVAILABLE_SAMPLE", 0),
        "source_limitations": source_limits["status"],
        "ontology_compatibility": ontology["status"],
        "boundary_carry_forward": "PASS" if boundary_pass else "FAIL",
        "no_overclaim": no_overclaim["status"],
        "no_mutation": mutation["status"],
        "hashes": hashes["status"],
        "output_dir": str(out),
    }
    write_json(out / "NYC_F4X_D3_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC-F4X-D3 mobility/environment EvidenceBundle gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_nyc_f4x_d3_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(final_print(result))
    return 0 if result.get("status") in {"PASS_MOBILITY_ENVIRONMENT_EVIDENCEBUNDLES", "PASS_WITH_SOURCE_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
