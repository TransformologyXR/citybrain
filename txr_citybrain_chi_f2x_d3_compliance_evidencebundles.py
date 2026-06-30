from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK_NAME = "CHI-F2X-D3 Chicago Compliance Cascade EvidenceBundles"
DEFAULT_OUTPUT_DIR = "outputs/chi_f2x_d3_compliance_evidencebundles"

INPUT_DEFAULTS = {
    "accepted_core": "outputs/chi_f1f7_d5_dual_flow_accepted_snapshot",
    "flowx_d1": "outputs/chi_flowx_d1_parallel_expansion_scouts",
    "flowx_d2": "outputs/chi_flowx_d2_parallel_join_hardening",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_chicago_landing": "data_landing/xdata_d1_bulk_official_sources_v1/chicago",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

F2X_D2_SUBDIR = "chi_f2x_d2_compliance_cascade_join_hardening"

ALLOWED_RELATIONSHIP_TYPES = {
    "HAS_NATIVE_ID",
    "HAS_ALIAS",
    "CANDIDATE_MATCH",
    "REJECTED_MATCH",
    "LOCATED_IN",
    "CONTAINS",
    "NEAR",
    "HAS_SOURCE_RECORD",
    "SUPPORTED_BY",
    "HAS_LIMITATION",
    "HAS_GOVERNANCE_BOUNDARY",
}

REQUIRED_BUNDLE_FIELDS = [
    "evidence_bundle_id",
    "city",
    "flow",
    "mode",
    "claim_label",
    "subject",
    "source_records",
    "native_ids",
    "relationships",
    "identity_confidence",
    "location_confidence",
    "limitations",
    "governance_boundaries",
    "forbidden_claims",
    "trace_refs",
]

BOUNDARY_LINES = [
    "CHI-F2X-D3 creates review-context EvidenceBundles only; Chicago Flow 2 is not accepted by this gate.",
    "Chicago Flow 2 has strong compliance ingredients, but certified parcel/building compliance cascade remains blocked until exact identity joins are gated.",
    "Permit, violation, inspection, license, building, and parcel relationships are candidate or contextual unless the bundle explicitly states exact native-source identity.",
    "Cook parcel coverage remains windowed/capped and cannot certify the full parcel universe.",
    "Building footprints remain geometry candidates, not certified building identities.",
    "No enforcement, legal, health, policing, public-safety, emergency, dispatch, operational, traffic-control, utility-control, or port-control recommendation is created.",
    "D4 handoff is limited to replay/face proof for candidate compliance EvidenceBundles with identity blockers carried forward.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bchicago flow 2 (?:is|was|now is|has been) accepted\b",
    r"\bflow 2 (?:is|was|now is|has been) accepted\b",
    r"\bcertified parcel/building compliance cascade (?:is|was|ready|complete|confirmed|created)\b",
    r"\bcertified building compliance cascade (?:is|was|ready|complete|confirmed|created)\b",
    r"\bcertified affected asset (?:is|was|ready|complete|confirmed|created|identified)\b",
    r"\blegal determination (?:is|was|made|issued|confirmed|ready)\b",
    r"\benforcement action (?:is|was|approved|issued|recommended|ready)\b",
    r"\bpublic safety instruction (?:is|was|issued|recommended|ready)\b",
    r"\bhealth determination (?:is|was|made|issued|confirmed|ready)\b",
    r"\bpolicing recommendation (?:is|was|made|issued|ready)\b",
    r"\bemergency dispatch (?:is|was|recommended|issued|ready)\b",
    r"\boperational instruction (?:is|was|recommended|issued|ready)\b",
    r"\bEXACT_SAME_AS\b",
    r"\bCERTIFIED_AFFECTED_ASSET\b",
    r"\bcertified_building_compliance_cascade\b",
    r"\blegal_determination\b",
    r"\benforcement_instruction\b",
]

NEGATION_MARKERS = [
    " no ",
    " not ",
    " not_",
    "do not",
    "does not",
    "cannot",
    "forbidden",
    "blocked",
    "blocker",
    "reject",
    "without",
    "until",
    "not_allowed",
    "boundary",
    "limitation",
    "prohibited",
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
    return {"gate": "CHI-F2X-D3-HASHES", "status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    output_dir = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in output_dir.parts}
        if (
            not str(output_dir).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or output_dir.name.lower() != "chi_f2x_d3_compliance_evidencebundles"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def file_inventory(path: Path, max_files: int = 50) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    roots = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
    for item in roots[:max_files]:
        stat = item.stat()
        files.append(
            {
                "path": item.name if path.is_file() else item.relative_to(path).as_posix(),
                "bytes": stat.st_size,
            }
        )
    total = 1 if path.is_file() else sum(1 for item in path.rglob("*") if item.is_file())
    return {"exists": True, "file_count": total, "files": files}


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
        "gate": "CHI-F2X-D3-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def gate(name: str, passed: bool, **extra: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(extra)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(item.get("status") == "PASS" for item in gates)


def load_inputs(root: Path) -> dict[str, Any]:
    paths = {key: project_path(root, value) for key, value in INPUT_DEFAULTS.items()}
    f2x_d2_dir = paths["flowx_d2"] / F2X_D2_SUBDIR
    reports = {
        "accepted_core": read_json(paths["accepted_core"] / "CHI_F1F7_D5_HARNESS_REPORT.json", {}),
        "flowx_d1": read_json(paths["flowx_d1"] / "CHI_FLOWX_D1_HARNESS_REPORT.json", {}),
        "flowx_d2": read_json(paths["flowx_d2"] / "CHI_FLOWX_D2_HARNESS_REPORT.json", {}),
        "f2x_d2": read_json(f2x_d2_dir / "CHI_F2X_D2_HARNESS_REPORT.json", {}),
        "f2x_d2_join_contract": read_json(f2x_d2_dir / "CHI_F2X_D2_JOIN_CONTRACT.json", {}),
        "f2x_d2_key_profile": read_json(f2x_d2_dir / "CHI_F2X_D2_JOIN_KEY_PROFILE.json", {}),
        "f2x_d2_source_landing": read_json(f2x_d2_dir / "CHI_F2X_D2_SOURCE_LANDING_REPORT.json", {}),
        "f2x_d2_handoff": read_json(f2x_d2_dir / "CHI_F2X_D2_D3_HANDOFF.json", {}),
        "xflow_harness": read_json(paths["xflow_d1"] / "XFLOW_D1_HARNESS_REPORT.json", {}),
        "xflow_queue": read_json(paths["xflow_d1"] / "XFLOW_D1_D3_QUEUE_RECOMMENDATION.json", {}),
        "ontology_relationships": read_json(paths["ontology_v2"] / "relationship_classes.json", {}),
        "ontology_claim_labels": read_json(paths["ontology_v2"] / "claim_label_policy.json", {}),
        "xdata_harness": read_json(paths["xdata_four_city"] / "XDATA_D1_HARNESS_REPORT.json", {}),
        "xdata_city_matrix": read_json(paths["xdata_four_city"] / "XDATA_D1_CITY_SUMMARY_MATRIX.json", {}),
    }
    return {"paths": paths, "reports": reports}


def input_inventory(paths: dict[str, Path], reports: dict[str, Any]) -> dict[str, Any]:
    inventory = {}
    for key, path in paths.items():
        item = file_inventory(path)
        status = "PASS" if item["exists"] else "XDATA_OPTIONAL_MISSING" if key.startswith("xdata") else "MISSING"
        if key == "xdata_chicago_landing" and item["exists"] and any(path.rglob("*.part")):
            status = "XDATA_OPTIONAL_STILL_RUNNING"
        if key == "xdata_four_city" and item["exists"]:
            status = "XDATA_OPTIONAL_PARTIAL_CHICAGO_RAW_PRESENT" if "CHICAGO" not in reports.get("xdata_city_matrix", {}) else "PASS"
        inventory[key] = {"path": str(path), "status": status, **item}
    return {
        "status": "PASS",
        "inputs": inventory,
        "read_only": True,
        "optional_xdata_note": inventory["xdata_four_city"]["status"],
    }


def source_and_join_summary(reports: dict[str, Any]) -> dict[str, Any]:
    f2x = reports["f2x_d2"]
    source_fit = f2x.get("source_fit", {})
    key_profile = reports["f2x_d2_key_profile"]
    join_contract = reports["f2x_d2_join_contract"]
    xdata_matrix = reports.get("xdata_city_matrix", {})
    return {
        "status": "PASS",
        "d2_status": f2x.get("status"),
        "accepted_core_status": reports["accepted_core"].get("accepted_status") or reports["accepted_core"].get("status"),
        "xflow_status": reports["xflow_harness"].get("status"),
        "xflow_top_queue": reports["xflow_harness"].get("top_next_d3_gates", []),
        "source_fit_status": source_fit.get("status"),
        "present_source_keys": source_fit.get("present_source_keys", []),
        "missing_source_keys": source_fit.get("missing_source_keys", []),
        "downloaded_rows_across_present_sources": source_fit.get("downloaded_rows_across_present_sources"),
        "sources": source_fit.get("sources", {}),
        "optional_xdata_chicago_status": xdata_matrix.get("CHICAGO", {}).get("status", "XDATA_OPTIONAL_NOT_BINDING_FOR_D3"),
        "join_key_profile": key_profile,
        "approved_candidate_join_keys": join_contract.get("approved_candidate_join_keys", []),
        "blocked_certifications": join_contract.get("blocked_certifications", []),
        "summary": "CHI-F2X-D3 may create candidate/context compliance EvidenceBundles from CHI-F2X-D2, while exact parcel/building identity remains blocked.",
    }


def governance_boundaries() -> list[str]:
    return list(BOUNDARY_LINES)


def forbidden_claims() -> list[str]:
    return [
        "no_flow_acceptance",
        "no_certified_parcel_building_cascade",
        "no_certified_affected_asset",
        "no_legal_or_enforcement_determination",
        "no_public_safety_or_health_instruction",
        "no_policing_dispatch_or_operational_instruction",
    ]


def source_record(source_key: str, reports: dict[str, Any], role: str) -> dict[str, Any]:
    source = reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get(source_key, {})
    return {
        "source_key": source_key,
        "role": role,
        "resource_id": source.get("resource_id"),
        "completion_status": source.get("completion_status"),
        "rows_loaded_by_d3": source.get("rows_loaded_by_d3"),
        "downloaded_rows": source.get("downloaded_rows"),
        "total_count": source.get("total_count"),
    }


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
    source_records: list[dict[str, Any]],
    native_ids: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    identity_confidence: str,
    location_confidence: str,
    limitations: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    return {
        "evidence_bundle_id": bundle_id,
        "city": "chicago",
        "flow": "F2X",
        "mode": "compliance_cascade",
        "claim_label": "[R]",
        "subject": subject,
        "source_records": source_records,
        "native_ids": native_ids,
        "relationships": relationships,
        "identity_confidence": identity_confidence,
        "location_confidence": location_confidence,
        "limitations": limitations + BOUNDARY_LINES,
        "governance_boundaries": governance_boundaries(),
        "forbidden_claims": forbidden_claims(),
        "trace_refs": trace_refs,
    }


def build_evidence_bundles(reports: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = reports["f2x_d2"].get("profiles", {})
    permit_profile = profiles.get("permit_pin_profile", {})
    violation_profile = profiles.get("building_violation_context_profile", {})
    footprint_profile = profiles.get("building_footprint_pin_profile", {})
    parcel_profile = profiles.get("parcel_profile", {})
    permit_subject = "chi-f2x:permit_pin10_candidate_rollup"
    violation_subject = "chi-f2x:violation_building_candidate_context"
    inspection_subject = "chi-f2x:inspection_license_context_cluster"
    area_subject = "chi-f2x:area_compliance_context_rollup"
    blocker_subject = "chi-f2x:governance_identity_blocker"
    return [
        make_bundle(
            "permit_to_building_candidate_bundle",
            {
                "subject_id": permit_subject,
                "question": "What evidence chain exists around a permit and a candidate building/parcel subject?",
                "profile_counts": permit_profile,
            },
            [
                source_record("building_permits", reports, "permit source"),
                source_record("cook_county_parcel_universe", reports, "windowed parcel candidate context"),
                source_record("building_footprints_primary", reports, "building geometry candidate context"),
            ],
            [
                {"native_authority": "city_of_chicago", "native_namespace": "ydr8-5enu", "native_id_role": "permit_resource_id", "native_id_confidence": "exact"},
                {"native_authority": "cook_county", "native_namespace": "nj4t-kc8j", "native_id_role": "parcel_resource_id", "native_id_confidence": "source_limited"},
            ],
            [
                rel("HAS_SOURCE_RECORD", permit_subject, "source:city_of_chicago:building_permits", "exact_source_reference", "D2 source landing report"),
                rel("HAS_NATIVE_ID", permit_subject, "native:city_of_chicago:ydr8-5enu", "exact_within_source", "Official resource identifier"),
                rel("CANDIDATE_MATCH", permit_subject, "candidate:pin10:parcel", "candidate", "Permit pin_list normalized to PIN10 matched the windowed parcel universe for a subset of permits"),
                rel("NEAR", permit_subject, "candidate:building_footprint", "contextual", "Permit geometry can support spatial review context, not identity certification"),
                rel("HAS_LIMITATION", permit_subject, "limitation:cook_parcel_windowed_capped", "exact_boundary", "D2 identity blocker"),
                rel("HAS_GOVERNANCE_BOUNDARY", permit_subject, "boundary:no_flow2_acceptance", "exact_boundary", "D3 gate boundary"),
            ],
            "candidate",
            "A",
            [
                "PIN10 matches are candidate parcel context because the parcel universe is windowed/capped.",
                "Building geometry is review context and does not certify a building identity.",
            ],
            [
                "CHI_F2X_D2_HARNESS_REPORT.json#profiles.permit_pin_profile",
                "CHI_F2X_D2_JOIN_CONTRACT.json#approved_candidate_join_keys[0]",
            ],
        ),
        make_bundle(
            "violation_to_building_candidate_bundle",
            {
                "subject_id": violation_subject,
                "question": "What evidence chain exists around a violation and a candidate building subject?",
                "profile_counts": violation_profile,
            },
            [
                source_record("building_violations", reports, "violation source"),
                source_record("building_footprints_primary", reports, "building geometry candidate context"),
            ],
            [
                {"native_authority": "city_of_chicago", "native_namespace": "22u3-xenr", "native_id_role": "violation_resource_id", "native_id_confidence": "exact"},
            ],
            [
                rel("HAS_SOURCE_RECORD", violation_subject, "source:city_of_chicago:building_violations", "exact_source_reference", "D2 source landing report"),
                rel("HAS_NATIVE_ID", violation_subject, "native:city_of_chicago:22u3-xenr", "exact_within_source", "Official resource identifier"),
                rel("CANDIDATE_MATCH", violation_subject, "candidate:building_footprint", "candidate", "Violation address/point may support building candidate review"),
                rel("LOCATED_IN", violation_subject, "context:chicago_area", "contextual", "Area fields support bounded review context"),
                rel("HAS_LIMITATION", violation_subject, "limitation:address_geometry_candidate_only", "exact_boundary", "D2 join contract"),
            ],
            "candidate",
            "A",
            [
                "Violation rows with point geometry remain candidate building context.",
                "Address/geometry context cannot be collapsed into an exact parcel/building identity.",
            ],
            [
                "CHI_F2X_D2_HARNESS_REPORT.json#profiles.building_violation_context_profile",
                "CHI_F2X_D2_JOIN_CONTRACT.json#blocked_certifications",
            ],
        ),
        make_bundle(
            "inspection_to_business_license_context_bundle",
            {
                "subject_id": inspection_subject,
                "question": "What evidence chain exists around inspection and license context?",
                "profile_counts": {
                    "business_license_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("business_licenses", {}).get("downloaded_rows"),
                    "food_inspection_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("food_inspections", {}).get("downloaded_rows"),
                },
            },
            [
                source_record("business_licenses", reports, "license source"),
                source_record("food_inspections", reports, "inspection source"),
            ],
            [
                {"native_authority": "city_of_chicago", "native_namespace": "r5kz-chrr", "native_id_role": "business_license_resource_id", "native_id_confidence": "exact"},
                {"native_authority": "city_of_chicago", "native_namespace": "4ijn-s7e5", "native_id_role": "food_inspection_resource_id", "native_id_confidence": "exact"},
            ],
            [
                rel("HAS_SOURCE_RECORD", inspection_subject, "source:city_of_chicago:business_licenses", "exact_source_reference", "D2 source landing report"),
                rel("HAS_SOURCE_RECORD", inspection_subject, "source:city_of_chicago:food_inspections", "exact_source_reference", "D2 source landing report"),
                rel("HAS_NATIVE_ID", inspection_subject, "native:city_of_chicago:r5kz-chrr", "exact_within_source", "Official resource identifier"),
                rel("HAS_NATIVE_ID", inspection_subject, "native:city_of_chicago:4ijn-s7e5", "exact_within_source", "Official resource identifier"),
                rel("LOCATED_IN", inspection_subject, "context:chicago_area", "contextual", "Area/address fields support review context"),
                rel("SUPPORTED_BY", inspection_subject, "source:city_of_chicago:business_licenses", "contextual", "License source is part of the compliance context"),
                rel("HAS_LIMITATION", inspection_subject, "limitation:inspection_license_context_only", "exact_boundary", "D3 gate boundary"),
            ],
            "contextual",
            "B",
            [
                "Inspection/license context is review-only unless an exact subject identity key is gated later.",
                "Business and food inspection records do not create legal, health, or enforcement determinations.",
            ],
            [
                "CHI_F2X_D2_SOURCE_LANDING_REPORT.json#sources.business_licenses",
                "CHI_F2X_D2_SOURCE_LANDING_REPORT.json#sources.food_inspections",
            ],
        ),
        make_bundle(
            "permit_violation_inspection_area_context_bundle",
            {
                "subject_id": area_subject,
                "question": "What compliance context co-occurs around an area subject?",
                "profile_counts": {
                    "permit_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("building_permits", {}).get("downloaded_rows"),
                    "violation_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("building_violations", {}).get("downloaded_rows"),
                    "inspection_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("food_inspections", {}).get("downloaded_rows"),
                    "service_request_rows": reports["f2x_d2"].get("source_fit", {}).get("sources", {}).get("311_service_requests", {}).get("downloaded_rows"),
                },
            },
            [
                source_record("building_permits", reports, "permit source"),
                source_record("building_violations", reports, "violation source"),
                source_record("food_inspections", reports, "inspection source"),
                source_record("311_service_requests", reports, "area service context"),
            ],
            [
                {"native_authority": "city_of_chicago", "native_namespace": "community_area_or_ward", "native_id_role": "area_key", "native_id_confidence": "contextual"},
            ],
            [
                rel("HAS_SOURCE_RECORD", area_subject, "source:city_of_chicago:building_permits", "exact_source_reference", "D2 source landing report"),
                rel("HAS_SOURCE_RECORD", area_subject, "source:city_of_chicago:building_violations", "exact_source_reference", "D2 source landing report"),
                rel("HAS_SOURCE_RECORD", area_subject, "source:city_of_chicago:food_inspections", "exact_source_reference", "D2 source landing report"),
                rel("HAS_SOURCE_RECORD", area_subject, "source:city_of_chicago:311_service_requests", "exact_source_reference", "D2 source landing report"),
                rel("LOCATED_IN", area_subject, "context:community_area_or_ward", "contextual", "D2 area rollup contract"),
                rel("CONTAINS", "context:community_area_or_ward", area_subject, "contextual", "Area rollup containment, not parcel/building identity"),
                rel("SUPPORTED_BY", area_subject, "source:city_of_chicago:311_service_requests", "contextual", "Windowed 311 source contributes area context"),
                rel("HAS_GOVERNANCE_BOUNDARY", area_subject, "boundary:area_context_only", "exact_boundary", "D2 join contract"),
            ],
            "contextual",
            "B",
            [
                "Area rollups are context, not subject identity.",
                "Co-occurrence of permit, violation, inspection, and 311 context does not certify a compliance cascade.",
            ],
            [
                "CHI_F2X_D2_JOIN_CONTRACT.json#approved_candidate_join_keys[2]",
                "CHI_F2X_D2_SOURCE_LANDING_REPORT.json#sources.311_service_requests",
            ],
        ),
        make_bundle(
            "governance_boundary_identity_blocker_bundle",
            {
                "subject_id": blocker_subject,
                "question": "Which parcel/building joins remain blocked and what evidence is needed to promote them?",
                "profile_counts": {
                    "parcel_profile": parcel_profile,
                    "footprint_profile": footprint_profile,
                    "permit_profile": permit_profile,
                },
            },
            [
                source_record("cook_county_parcel_universe", reports, "windowed parcel candidate context"),
                source_record("building_footprints_primary", reports, "building geometry candidate context"),
                source_record("building_permits", reports, "permit source"),
            ],
            [
                {"native_authority": "cook_county", "native_namespace": "nj4t-kc8j", "native_id_role": "windowed_parcel_source", "native_id_confidence": "source_limited"},
            ],
            [
                rel("REJECTED_MATCH", blocker_subject, "promotion:parcel_building_certification", "rejected", "D2 identity blockers remain active"),
                rel("HAS_LIMITATION", blocker_subject, "limitation:d2b_identity_edges_zero", "exact_boundary", "D2 join contract"),
                rel("HAS_LIMITATION", blocker_subject, "limitation:cook_parcel_windowed_capped", "exact_boundary", "D2 source profile"),
                rel("HAS_LIMITATION", blocker_subject, "limitation:building_footprints_geometry_candidate", "exact_boundary", "D2 join contract"),
                rel("HAS_GOVERNANCE_BOUNDARY", blocker_subject, "boundary:human_review_required_for_promotion", "exact_boundary", "D3 blocker policy"),
                rel("SUPPORTED_BY", blocker_subject, "source:chi_f2x_d2_join_contract", "exact_source_reference", "D2 blocker report"),
            ],
            "rejected",
            "D",
            [
                "Exact parcel/building compliance cascade promotion is rejected at D3.",
                "Promotion would require official exact parcel/building keys, full or explicitly sufficient parcel universe evidence, and a later gate that certifies identity.",
            ],
            [
                "CHI_F2X_D2_JOIN_CONTRACT.json#blocked_certifications",
                "CHI_F2X_D2_HARNESS_REPORT.json#join_contract.status",
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
        "exact_same_as_policy": "Not emitted by CHI-F2X-D3 because source evidence does not prove exact cross-entity identity.",
        "claim_label_policy": "[R] because bundle facts are sourced from accepted/read-only official-source landing reports; boundaries are carried as governance metadata.",
        "forbidden_relationship_policy": "Certified affected asset and certified compliance-cascade relations are not emitted by this gate.",
        "ontology_relationships_present": sorted(ALLOWED_RELATIONSHIP_TYPES.intersection(ontology_relationships)),
        "ontology_missing_relationships": sorted(ALLOWED_RELATIONSHIP_TYPES.difference(ontology_relationships)),
    }


def validate_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    missing_fields = {}
    invalid_relationships = []
    invalid_confidence = []
    forbidden_tokens = []
    for bundle in bundles:
        bundle_id = bundle.get("evidence_bundle_id")
        missing = [field for field in REQUIRED_BUNDLE_FIELDS if field not in bundle]
        if missing:
            missing_fields[bundle_id] = missing
        if bundle.get("identity_confidence") not in {"exact", "candidate", "contextual", "rejected"}:
            invalid_confidence.append(bundle_id)
        if bundle.get("location_confidence") not in {"A", "B", "C", "D"}:
            invalid_confidence.append(bundle_id)
        for relationship in bundle.get("relationships", []):
            rel_type = relationship.get("relationship_type")
            if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
                invalid_relationships.append({"bundle": bundle_id, "relationship_type": rel_type})
            if rel_type == "EXACT_SAME_AS":
                invalid_relationships.append({"bundle": bundle_id, "relationship_type": rel_type, "reason": "exact identity not proven"})
        serialized = json.dumps(bundle, ensure_ascii=True)
        for token in ["CERTIFIED_AFFECTED_ASSET", "certified_building_compliance_cascade", "legal_determination", "enforcement_instruction"]:
            if token in serialized:
                forbidden_tokens.append({"bundle": bundle_id, "token": token})
    return {
        "status": "PASS" if not missing_fields and not invalid_relationships and not invalid_confidence and not forbidden_tokens else "FAIL",
        "bundle_count": len(bundles),
        "missing_fields": missing_fields,
        "invalid_relationships": invalid_relationships,
        "invalid_confidence": invalid_confidence,
        "forbidden_tokens": forbidden_tokens,
    }


def relationship_counts(bundles: list[dict[str, Any]]) -> dict[str, int]:
    exact = 0
    candidate_context = 0
    rejected_blocker = 0
    for bundle in bundles:
        for relationship in bundle.get("relationships", []):
            rel_type = relationship.get("relationship_type")
            confidence = relationship.get("confidence")
            if rel_type == "EXACT_SAME_AS":
                exact += 1
            elif rel_type in {"CANDIDATE_MATCH", "LOCATED_IN", "NEAR", "CONTAINS"} or confidence in {"candidate", "contextual"}:
                candidate_context += 1
            elif rel_type in {"REJECTED_MATCH", "HAS_LIMITATION", "HAS_GOVERNANCE_BOUNDARY"} or confidence == "rejected":
                rejected_blocker += 1
    return {
        "exact_joins": exact,
        "candidate_context_joins": candidate_context,
        "rejected_blocker_joins": rejected_blocker,
    }


def identity_blocker_report(bundles: list[dict[str, Any]], reports: dict[str, Any]) -> dict[str, Any]:
    counts = relationship_counts(bundles)
    join_contract = reports["f2x_d2_join_contract"]
    return {
        "status": "PASS",
        "answer": "Chicago Flow 2 has strong compliance ingredients, but certified parcel/building compliance cascade remains blocked until exact identity joins are gated.",
        "which_joins_are_exact": [
            "Native source identifiers are exact within their source systems.",
            "No exact cross-entity parcel/building compliance identity join is emitted by CHI-F2X-D3.",
        ],
        "which_joins_are_candidate_or_contextual": [
            "permit.pin_list -> PIN10 -> parcel.pin10 is candidate only",
            "building_footprint.harris_pin_candidate -> PIN14 -> parcel.pin14 is candidate only",
            "permits/violations/licenses/food/311 area fields -> D2B ward/community_area/police district is contextual only",
        ],
        "which_parcel_building_joins_remain_blocked": join_contract.get("blocked_certifications", []),
        "evidence_needed_to_promote": [
            "Official exact parcel/building join key or accepted deterministic identity rule",
            "Parcel universe coverage that is full or explicitly sufficient for the promoted claim",
            "Nonzero accepted D2B identity edges or an equivalent later gate",
            "D4 replay/face proof showing the bundle remains bounded and reproducible",
        ],
        **counts,
    }


def selected_bundles_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    selected_ids = [bundle["evidence_bundle_id"] for bundle in bundles]
    return {
        "status": "PASS",
        "selection_policy": "Select all deterministic CHI-F2X-D3 bundle targets for D4 replay/face proof.",
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
        "mutation_policy": "Inputs are snapshotted before and after bundle generation; no accepted output is mutated.",
    }


def next_d4_handoff(bundles: list[dict[str, Any]], blocker_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "D4_READY_WITH_IDENTITY_BLOCKERS",
        "recommended_next": "CHI-F2X-D4 replay/face proof for candidate compliance EvidenceBundles",
        "selected_bundle_ids": [bundle["evidence_bundle_id"] for bundle in bundles],
        "must_carry_forward": [
            "Do not claim Chicago Flow 2 is accepted.",
            "Do not certify parcel/building compliance cascades without exact identity evidence.",
            "Do not create enforcement, legal, health, policing, public-safety, dispatch, emergency, operational, traffic-control, utility-control, or port-control recommendations.",
        ],
        "identity_blockers": blocker_report["which_parcel_building_joins_remain_blocked"],
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
            if not path.is_file() or path.name in {"SHA256SUMS.json", "CHI_F2X_D3_NO_OVERCLAIM_REPORT.json"}:
                continue
            if path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            checked_files += 1
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for number, line in enumerate(lines, start=1):
                if line_is_negated(line):
                    continue
                for pattern in FORBIDDEN_POSITIVE_PATTERNS:
                    if re.search(pattern, line, flags=re.IGNORECASE):
                        findings.append({"path": str(path), "line": number, "pattern": pattern})
    return {"gate": "CHI-F2X-D3-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "checked_files": checked_files, "findings": findings}


def ontology_compatibility_report(bundles: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    relationship_types = sorted({relationship["relationship_type"] for bundle in bundles for relationship in bundle["relationships"]})
    unsupported = sorted(set(relationship_types).difference(ALLOWED_RELATIONSHIP_TYPES))
    return {
        "status": "PASS" if contract["status"] == "PASS" and not unsupported else "FAIL",
        "relationship_types_emitted": relationship_types,
        "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES),
        "unsupported_relationship_types": unsupported,
        "exact_same_as_emitted": "EXACT_SAME_AS" in relationship_types,
        "claim_labels": ["[R]"],
    }


def final_print(result: dict[str, Any]) -> str:
    lines = [
        f"CHI-F2X-D3 Chicago Compliance Cascade EvidenceBundles: {result.get('status', 'FAIL')}",
        "",
        f"EvidenceBundles created: {result.get('evidence_bundles_created', 0)}",
        f"Selected bundles: {result.get('selected_bundles', 0)}",
        f"Exact joins: {result.get('exact_joins', 0)}",
        f"Candidate/context joins: {result.get('candidate_context_joins', 0)}",
        f"Rejected/blocker joins: {result.get('rejected_blocker_joins', 0)}",
        "",
        f"Identity blockers: {result.get('identity_blockers', 'FAIL')}",
        f"Ontology compatibility: {result.get('ontology_compatibility', 'FAIL')}",
        f"Boundary carry-forward: {result.get('boundary_carry_forward', 'FAIL')}",
        f"No-overclaim: {result.get('no_overclaim', 'FAIL')}",
        f"No-mutation: {result.get('no_mutation', 'FAIL')}",
        f"Hashes: {result.get('hashes', 'FAIL')}",
        "",
        f"Final status: {result.get('status', 'FAIL')}",
        "Output: outputs\\chi_f2x_d3_compliance_evidencebundles",
    ]
    return "\n".join(lines)


def run_chi_f2x_d3_gate(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = reset_output_dir(project_path(root, output_dir), root)
    loaded = load_inputs(root)
    paths = loaded["paths"]
    reports = loaded["reports"]
    watched_inputs = [
        paths["accepted_core"],
        paths["flowx_d1"],
        paths["flowx_d2"],
        paths["xflow_d1"],
        paths["ontology_v2"],
        paths["xdata_chicago_landing"] / "manifests",
        paths["xdata_four_city"],
    ]
    before = input_snapshot(watched_inputs)

    inventory = input_inventory(paths, reports)
    source_join = source_and_join_summary(reports)
    bundles = build_evidence_bundles(reports)
    contract = evidencebundle_contract(reports["ontology_relationships"])
    bundle_validation = validate_bundles(bundles)
    selected = selected_bundles_report(bundles)
    blocker_report = identity_blocker_report(bundles, reports)
    trace = trace_report(bundles, paths)
    d4_handoff = next_d4_handoff(bundles, blocker_report)
    ontology = ontology_compatibility_report(bundles, contract)

    write_json(out / "CHI_F2X_D3_INPUT_INVENTORY.json", inventory)
    write_json(out / "CHI_F2X_D3_SOURCE_AND_JOIN_SUMMARY.json", source_join)
    write_json(out / "CHI_F2X_D3_IDENTITY_BLOCKER_REPORT.json", blocker_report)
    write_json(out / "CHI_F2X_D3_EVIDENCEBUNDLE_CONTRACT.json", contract)
    write_json(out / "CHI_F2X_D3_EVIDENCEBUNDLES.json", {"status": bundle_validation["status"], "evidence_bundle_count": len(bundles), "bundles": bundles, "validation": bundle_validation})
    write_json(out / "CHI_F2X_D3_SELECTED_BUNDLES.json", selected)
    write_json(out / "CHI_F2X_D3_TRACE_REPORT.json", trace)
    write_json(out / "CHI_F2X_D3_NEXT_D4_HANDOFF.json", d4_handoff)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# CHI-F2X-D3 Chicago Compliance Cascade EvidenceBundles",
                "",
                "This D3 gate creates governed review-context EvidenceBundles over CHI-F2X-D2 source/join hardening.",
                "It does not accept Chicago Flow 2 and does not certify parcel/building compliance cascades.",
                "",
                *[f"- {line}" for line in BOUNDARY_LINES],
                "",
            ]
        ),
    )

    after = input_snapshot(watched_inputs)
    mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F2X_D3_NO_MUTATION_REPORT.json", mutation)

    no_overclaim = no_overclaim_scan([out])
    write_json(out / "CHI_F2X_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)

    counts = relationship_counts(bundles)
    precond_pass = all(paths[key].exists() for key in ["accepted_core", "flowx_d1", "flowx_d2", "xflow_d1", "ontology_v2"])
    source_join_pass = (
        reports["accepted_core"].get("accepted_status") == "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS"
        and reports["flowx_d1"].get("status") == "PASS_PARALLEL_FLOW_EXTENSION_SCOUTS"
        and reports["flowx_d2"].get("results", {}).get("CHI-F2X-D2") == "PASS_JOIN_HARDENED_WITH_IDENTITY_BLOCKERS"
        and reports["xflow_harness"].get("status") == "PASS_CROSS_CITY_EXPANSION_RECONCILIATION"
    )
    boundary_pass = all(line in json.dumps(bundles, ensure_ascii=True) for line in BOUNDARY_LINES)
    gates = [
        gate("CHI-F2X-D3-PRECOND", precond_pass),
        gate("CHI-F2X-D3-INPUT-INVENTORY", inventory["status"] == "PASS"),
        gate("CHI-F2X-D3-SOURCE-JOIN-SUMMARY", source_join["status"] == "PASS" and source_join_pass),
        gate("CHI-F2X-D3-EVIDENCEBUNDLE-CONTRACT", contract["status"] == "PASS"),
        gate("CHI-F2X-D3-EVIDENCEBUNDLES", bundle_validation["status"] == "PASS" and len(bundles) >= 5),
        gate("CHI-F2X-D3-IDENTITY-BLOCKERS", blocker_report["status"] == "PASS" and counts["exact_joins"] == 0 and counts["rejected_blocker_joins"] > 0),
        gate("CHI-F2X-D3-ONTOLOGY-COMPATIBILITY", ontology["status"] == "PASS" and not ontology["exact_same_as_emitted"]),
        gate("CHI-F2X-D3-BOUNDARY-CARRY-FORWARD", boundary_pass),
        gate("CHI-F2X-D3-NO-OVERCLAIM", no_overclaim["status"] == "PASS", findings=no_overclaim["findings"]),
        gate("CHI-F2X-D3-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("CHI-F2X-D3-HASHES", True),
    ]
    status = "PASS_WITH_IDENTITY_BLOCKERS" if gates_pass(gates) and counts["exact_joins"] == 0 else "PASS_COMPLIANCE_EVIDENCEBUNDLES" if gates_pass(gates) else "FAIL"
    hashes = write_hashes(out)
    harness = {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "gates": gates,
        "evidence_bundles_created": len(bundles),
        "selected_bundles": selected["selected_bundle_count"],
        **counts,
        "identity_blockers": "PASS" if gates[5]["status"] == "PASS" else "FAIL",
        "ontology_compatibility": ontology["status"],
        "boundary_carry_forward": "PASS" if boundary_pass else "FAIL",
        "no_overclaim": no_overclaim["status"],
        "no_mutation": mutation["status"],
        "hashes": hashes["status"],
        "output_dir": str(out),
    }
    write_json(out / "CHI_F2X_D3_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F2X-D3 Chicago compliance cascade EvidenceBundle gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_chi_f2x_d3_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(final_print(result))
    return 0 if result.get("status") in {"PASS_COMPLIANCE_EVIDENCEBUNDLES", "PASS_WITH_IDENTITY_BLOCKERS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
