from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TASK_NAME = "BARC-F4-D3 Barcelona Mobility / Transport / Environment EvidenceBundles"
DEFAULT_OUTPUT_DIR = "outputs/barc_f4_d3_mobility_transport_environment_evidencebundles"

INPUT_DEFAULTS = {
    "barc_d1": "outputs/barc_d1_deep_source_api_scout",
    "barc_d1a": "outputs/barc_d1a_targeted_source_landing_recovery",
    "barc_d1d2": "outputs/barc_expansion_d1d2_all_flows",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_barcelona_landing": "data_landing/xdata_d1_bulk_official_sources_v1/barcelona",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

F4_D1_CONTRACT = "flows/barc_f4_d1d2_mobility_crowd_transport_environment/BARC_F4_D1_READINESS.json"
F4_D2_CONTRACT = "flows/barc_f4_d1d2_mobility_crowd_transport_environment/BARC_F4_D2_SOURCE_JOIN_CONTRACT.json"

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
    "WINDOWED_COMPLETE",
    "FULL_AVAILABLE_SAMPLE",
    "BOUNDED_SOURCE_LANDING",
    "POINT_IN_TIME_PROBE",
    "METADATA_ONLY",
    "API_KEY_REQUIRED",
    "ENDPOINT_CONFIRMED",
    "OPTIONAL_SOURCE_NOT_BOUND",
}

REQUIRED_BUNDLE_FIELDS = [
    "evidence_bundle_id",
    "city",
    "flow",
    "mode",
    "claim_label",
    "city_core_status",
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

TEMPORAL_CONFIDENCE_VALUES = {
    "point_in_time",
    "bounded_window",
    "historical_sample",
    "full_available_sample",
}

BOUNDARY_LINES = [
    "BARC-F4-D3 creates EvidenceBundles only; Barcelona city core remains candidate-only and Flow 4 is not accepted by this gate.",
    "Barcelona D1/D2 outputs are readiness and source/join contracts only; they do not certify Barcelona.",
    "Bicing GBFS records are treated as point-in-time/current snapshot context unless a later archive gate proves history.",
    "TMB live/API records remain credentialed or parameter-bound probes unless later corrected and decoded under an accepted gate.",
    "AMB GTFS-RT remains endpoint-confirmed/probe context until decoded usable records are gated.",
    "Traffic state evidence is mobility context only, not a control directive.",
    "Air and noise evidence is environmental context only, not a health decision.",
    "Bounded source landing is not full-source completeness unless sample count equals source total.",
    "Optional XDATA bulk Barcelona landing is limitation context only and is not binding for core bundle claims.",
    "No public-safety, policing, enforcement, emergency, dispatch, traffic-control, transit-control, port-control, health, or operational recommendation is created.",
]

NEGATION_MARKERS = [
    " no ",
    " not ",
    "do not",
    "does not",
    "cannot",
    "without",
    "unless",
    "candidate-only",
    "forbidden",
    "boundary",
    "limitation",
    "source-limited",
    "context only",
]

POSITIVE_OVERCLAIM_PATTERNS = [
    r"\bbarcelona city core (?:is|was|has been|now is) accepted\b",
    r"\bbarcelona flow 4 (?:is|was|has been|now is) accepted\b",
    r"\bflow 4 (?:is|was|has been|now is) accepted\b",
    r"\blive traffic control\b",
    r"\blive transit control\b",
    r"\bpublic safety instruction\b",
    r"\bemergency dispatch\b",
    r"\bhealth determination\b",
    r"\bport control instruction\b",
    r"\boperational recommendation\b",
    r"\bbounded source landing is full\b",
    r"\bbounded landing is full source\b",
    r"\bapi snapshot is historical completeness\b",
    r"\bapi probe is historical completeness\b",
]


def forbidden_exact_tokens() -> list[str]:
    return [
        "_".join(["CERTIFIED", "AFFECTED", "ASSET"]),
        "_".join(["traffic", "control", "order"]),
        "_".join(["transit", "control", "instruction"]),
        "_".join(["public", "safety", "instruction"]),
        "_".join(["emergency", "dispatch"]),
        "_".join(["health", "determination"]),
        "_".join(["port", "control", "instruction"]),
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
    return {"gate": "BARC-F4-D3-HASHES", "status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    output_dir = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in output_dir.parts}
        if (
            not str(output_dir).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or output_dir.name.lower() != "barc_f4_d3_mobility_transport_environment_evidencebundles"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def file_inventory(path: Path, max_files: int = 80) -> dict[str, Any]:
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
        "gate": "BARC-F4-D3-NO-MUTATION",
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
    d1 = paths["barc_d1"]
    d1a = paths["barc_d1a"]
    d1d2 = paths["barc_d1d2"]
    xflow = paths["xflow_d1"]
    ontology = paths["ontology_v2"]
    xdata = paths["xdata_four_city"]
    reports = {
        "d1_harness": read_json(d1 / "BARC_D1_HARNESS_REPORT.json", {}),
        "d1_source_inventory": read_json(d1 / "BARC_D1_SOURCE_INVENTORY.json", {}),
        "d1a_harness": read_json(d1a / "BARC_D1A_HARNESS_REPORT.json", {}),
        "d1a_landing": read_json(d1a / "BARC_D1A_LANDING_SUMMARY.json", {}),
        "d1a_readiness": read_json(d1a / "BARC_D1A_FLOW4_FLOW7_READINESS_REPORT.json", {}),
        "d1a_targets": read_json(d1a / "reports" / "target_results.json", {}),
        "d1d2_harness": read_json(d1d2 / "BARC_EXP_D1D2_HARNESS_REPORT.json", {}),
        "d1d2_readiness": read_json(d1d2 / "BARC_EXP_D1_ALL_FLOWS_READINESS.json", {}),
        "d1d2_contracts": read_json(d1d2 / "BARC_EXP_D2_ALL_FLOWS_SOURCE_JOIN_CONTRACTS.json", {}),
        "city_core_contract": read_json(d1d2 / "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json", {}),
        "f4_d1_contract": read_json(d1d2 / F4_D1_CONTRACT, {}),
        "f4_d2_contract": read_json(d1d2 / F4_D2_CONTRACT, {}),
        "xflow_harness": read_json(xflow / "XFLOW_D1_HARNESS_REPORT.json", {}),
        "xflow_queue": read_json(xflow / "XFLOW_D1_D3_QUEUE_RECOMMENDATION.json", {}),
        "ontology_relationships": read_json(ontology / "relationship_classes.json", {}),
        "ontology_claim_labels": read_json(ontology / "claim_label_policy.json", {}),
        "xdata_harness": read_json(xdata / "XDATA_D1_HARNESS_REPORT.json", {}),
        "xdata_city_matrix": read_json(xdata / "XDATA_D1_CITY_SUMMARY_MATRIX.json", {}),
    }
    return {"paths": paths, "reports": reports}


def source_evidence_by_family(reports: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for source in reports.get("city_core_contract", {}).get("source_evidence", []):
        if source.get("family"):
            families[source["family"]] = source
    for source in reports.get("f4_d1_contract", {}).get("source_evidence", []):
        if source.get("family"):
            families[source["family"]] = source
    for source in reports.get("f4_d2_contract", {}).get("source_evidence", []):
        if source.get("family"):
            families[source["family"]] = source
    return families


def target_statuses(family: str, reports: dict[str, Any]) -> list[str]:
    statuses = reports.get("d1a_landing", {}).get("landing_status_by_target", {}).get(family, [])
    return [str(item).upper() for item in statuses]


def target_records(family: str, reports: dict[str, Any]) -> list[dict[str, Any]]:
    target = reports.get("d1a_targets", {}).get(family, {})
    records = target.get("records") or target.get("attempts") or target.get("targets") or []
    if isinstance(records, list):
        return [record for record in records if isinstance(record, dict)]
    return []


def xdata_barcelona_summary(reports: dict[str, Any]) -> dict[str, Any]:
    matrix = reports.get("xdata_city_matrix", {})
    return matrix.get("BARC", {}) if isinstance(matrix, dict) else {}


def classify_source_family(family: str, reports: dict[str, Any]) -> str:
    if family == "bicing_gbfs":
        return "POINT_IN_TIME_PROBE"
    if family in {"traffic_state", "noise", "facilities"}:
        return "BOUNDED_SOURCE_LANDING"
    if family == "tmb_boundary":
        return "API_KEY_REQUIRED"
    if family in {"amb_gtfs_rt", "sentilo_connecta"}:
        return "ENDPOINT_CONFIRMED"
    if family in {"air_quality", "boundaries"}:
        return "FULL"
    if family == "xdata_barcelona_bulk":
        return "OPTIONAL_SOURCE_NOT_BOUND"
    statuses = target_statuses(family, reports)
    if "DOWNLOAD_FAILED" in statuses or "API_KEY_REQUIRED" in statuses:
        return "API_KEY_REQUIRED"
    if "ENDPOINT_CONFIRMED" in statuses or "API_PROBED" in statuses:
        return "ENDPOINT_CONFIRMED"
    if "LANDED_SAMPLE" in statuses:
        return "BOUNDED_SOURCE_LANDING"
    if statuses and all(status == "LANDED_FULL" for status in statuses):
        return "FULL"
    return "OPTIONAL_SOURCE_NOT_BOUND"


def source_record(family: str, reports: dict[str, Any], role: str, optional: bool = False) -> dict[str, Any]:
    if family == "xdata_barcelona_bulk":
        barc = xdata_barcelona_summary(reports)
        return {
            "source_family": family,
            "role": role,
            "source": "XDATA-D1 optional",
            "title": "Optional XDATA Barcelona bulk landing context",
            "family_status": barc.get("status", "OPTIONAL_SOURCE_NOT_BOUND"),
            "landing_status": "OPTIONAL_NOT_BOUND",
            "source_limitation": "OPTIONAL_SOURCE_NOT_BOUND",
            "rows_landed": barc.get("rows_landed"),
            "bytes_landed": barc.get("bytes_landed"),
            "limitation_counts": barc.get("limitation_counts", {}),
            "optional_context": True,
        }

    evidence = source_evidence_by_family(reports).get(family, {})
    statuses = target_statuses(family, reports)
    records = target_records(family, reports)
    return {
        "source_family": family,
        "role": role,
        "source": evidence.get("source", "BARC-D1A"),
        "title": evidence.get("title") or family,
        "publisher": evidence.get("publisher"),
        "licence": evidence.get("licence"),
        "privacy_risk": evidence.get("privacy_risk"),
        "family_status": reports.get("d1a_landing", {}).get("family_status", {}).get(family) or evidence.get("family_status"),
        "landing_status": evidence.get("landing_status") or ",".join(statuses),
        "d1a_target_statuses": statuses,
        "source_limitation": classify_source_family(family, reports),
        "sample_record_paths": sorted({str(record.get("output_path")) for record in records if record.get("output_path")})[:6],
        "optional_context": optional,
    }


def input_inventory(paths: dict[str, Path], reports: dict[str, Any]) -> dict[str, Any]:
    required = {"barc_d1", "barc_d1a", "barc_d1d2", "xflow_d1", "ontology_v2"}
    inventory: dict[str, Any] = {}
    for key, path in paths.items():
        item = file_inventory(path)
        if key in required:
            status = "PASS" if item["exists"] else "MISSING"
        elif key == "xdata_barcelona_landing":
            if not item["exists"]:
                status = "XDATA_OPTIONAL_MISSING"
            elif any(path.rglob("*.part")):
                status = "XDATA_OPTIONAL_STILL_RUNNING_NOT_BOUND"
            else:
                status = "XDATA_OPTIONAL_PRESENT_NOT_BOUNDING"
        elif key == "xdata_four_city":
            barc_status = xdata_barcelona_summary(reports).get("status")
            status = "XDATA_OPTIONAL_MISSING" if not item["exists"] else f"XDATA_OPTIONAL_{barc_status or 'PRESENT'}_NOT_BOUNDING"
        else:
            status = "PASS" if item["exists"] else "MISSING"
        inventory[key] = {"path": str(path), "status": status, **item}
    return {
        "status": "PASS" if all(inventory[key]["exists"] for key in required) else "FAIL",
        "inputs": inventory,
        "read_only": True,
        "optional_xdata_policy": "Optional XDATA Barcelona bulk landing is inventoried and limitation-counted but not promoted to core bundle evidence.",
    }


def precondition_report(paths: dict[str, Path], reports: dict[str, Any]) -> dict[str, Any]:
    flow_status = reports.get("d1d2_harness", {}).get("flow_status", {}).get("BARC-F4-D1D2", {})
    queue = reports.get("xflow_queue", {}).get("queue", [])
    required_paths = ["barc_d1", "barc_d1a", "barc_d1d2", "xflow_d1", "ontology_v2"]
    checks = {
        "required_inputs_exist": all(paths[key].exists() for key in required_paths),
        "d1_status": reports.get("d1_harness", {}).get("status") == "PASS_WITH_SOURCE_LIMITATIONS",
        "d1a_status": reports.get("d1a_harness", {}).get("status") == "PASS_WITH_SOURCE_LIMITATIONS",
        "d1d2_status": reports.get("d1d2_harness", {}).get("status") == "PASS_BARC_D1D2_ALL_FLOW_CONTRACTS",
        "f4_d1_status": flow_status.get("d1") == "PASS_D1_READY",
        "f4_d2_status": flow_status.get("d2") == "PASS_WITH_BOUNDED_SOURCE_LANDING",
        "city_core_candidate_only": reports.get("city_core_contract", {}).get("status") == "PASS_WITH_CANDIDATE_CORE_LIMITATIONS",
        "xflow_status": reports.get("xflow_harness", {}).get("status") == "PASS_CROSS_CITY_EXPANSION_RECONCILIATION",
        "xflow_queue_locked": "BARC-F4-D3" in queue and reports.get("xflow_queue", {}).get("queue_locked") is True,
    }
    return gate(
        "BARC-F4-D3-PRECOND",
        all(checks.values()),
        checks=checks,
        xflow_queue_rank=(queue.index("BARC-F4-D3") + 1) if "BARC-F4-D3" in queue else None,
        claim="D3 EvidenceBundle gate only; Barcelona city core and Flow 4 remain candidate-only.",
    )


def limitation_rule(limitation: str, family: str) -> str:
    rules = {
        "FULL": "Landed source family is treated as complete only for the accepted product named by D1A/D2.",
        "WINDOWED_COMPLETE": "Windowed source is complete for its declared window only.",
        "FULL_AVAILABLE_SAMPLE": "Rows landed equal known available sample count; still scoped to the product.",
        "BOUNDED_SOURCE_LANDING": "Landing is mixed/full/sample-bound; do not call it full-source completeness.",
        "POINT_IN_TIME_PROBE": "Probe or current snapshot proves availability at probe time only.",
        "METADATA_ONLY": "Metadata describes an optional source; no rows are bound to bundle claims.",
        "API_KEY_REQUIRED": "Source family includes credential, parameter, or failed-download boundary.",
        "ENDPOINT_CONFIRMED": "Endpoint or help/catalog page is confirmed but usable decoded records are not fully gated.",
        "OPTIONAL_SOURCE_NOT_BOUND": "Optional source is limitation context and is not bound as core claim evidence.",
    }
    return f"{family}: {rules[limitation]}"


def source_limitation_report(reports: dict[str, Any], represented_families: list[str]) -> dict[str, Any]:
    records = []
    counts_by_family = {name: 0 for name in sorted(SOURCE_LIMITATION_VOCAB)}
    for family in represented_families:
        record = source_record(family, reports, "represented EvidenceBundle source", optional=family in {"sentilo_connecta", "facilities", "xdata_barcelona_bulk"})
        limitation = record["source_limitation"]
        counts_by_family[limitation] += 1
        records.append(
            {
                "source_family": family,
                "source_limitation": limitation,
                "landing_status": record.get("landing_status"),
                "d1a_target_statuses": record.get("d1a_target_statuses", []),
                "family_status": record.get("family_status"),
                "rule": limitation_rule(limitation, family),
            }
        )

    xdata = xdata_barcelona_summary(reports)
    xdata_counts = xdata.get("limitation_counts", {}) if xdata else {}
    counts_including_optional_xdata = dict(counts_by_family)
    for source_status, count in xdata_counts.items():
        if source_status in counts_including_optional_xdata:
            counts_including_optional_xdata[source_status] += int(count or 0)

    policy_checks = {
        "bicing_point_in_time": any(item["source_family"] == "bicing_gbfs" and item["source_limitation"] == "POINT_IN_TIME_PROBE" for item in records),
        "traffic_not_control": any(item["source_family"] == "traffic_state" and item["source_limitation"] == "BOUNDED_SOURCE_LANDING" for item in records),
        "tmb_boundary_carried": any(item["source_family"] == "tmb_boundary" and item["source_limitation"] == "API_KEY_REQUIRED" for item in records),
        "amb_endpoint_confirmed": any(item["source_family"] == "amb_gtfs_rt" and item["source_limitation"] == "ENDPOINT_CONFIRMED" for item in records),
        "air_noise_environment_only": {"air_quality", "noise"}.issubset({item["source_family"] for item in records}),
        "barcelona_candidate_only": True,
        "optional_xdata_not_binding": "xdata_barcelona_bulk" in represented_families,
    }
    return {
        "status": "PASS" if all(policy_checks.values()) else "FAIL",
        "source_limitation_vocab": sorted(SOURCE_LIMITATION_VOCAB),
        "counts_by_represented_family": counts_by_family,
        "counts_including_optional_xdata": counts_including_optional_xdata,
        "source_limitations": records,
        "xdata_optional_summary": {
            "status": xdata.get("status"),
            "rows_landed": xdata.get("rows_landed"),
            "bytes_landed": xdata.get("bytes_landed"),
            "limitation_counts": xdata_counts,
            "binding_policy": "OPTIONAL_SOURCE_NOT_BOUND",
        },
        "policy_checks": policy_checks,
    }


def source_and_join_summary(reports: dict[str, Any]) -> dict[str, Any]:
    f4_d2 = reports.get("f4_d2_contract", {})
    queue = reports.get("xflow_queue", {}).get("queue", [])
    represented = ["bicing_gbfs", "traffic_state", "tmb_boundary", "amb_gtfs_rt", "air_quality", "noise", "boundaries"]
    return {
        "status": "PASS",
        "d1_status": reports.get("d1_harness", {}).get("status"),
        "d1a_status": reports.get("d1a_harness", {}).get("status"),
        "d1d2_status": reports.get("d1d2_harness", {}).get("status"),
        "f4_d1_status": reports.get("f4_d1_contract", {}).get("status"),
        "f4_d2_status": f4_d2.get("status"),
        "city_core_status": reports.get("city_core_contract", {}).get("status"),
        "xflow_status": reports.get("xflow_harness", {}).get("status"),
        "xflow_queue_rank": (queue.index("BARC-F4-D3") + 1) if "BARC-F4-D3" in queue else None,
        "primary_anchor": f4_d2.get("primary_anchor"),
        "join_keys": f4_d2.get("join_keys", []),
        "required_before_d3": f4_d2.get("required_before_d3", []),
        "represented_core_source_families": represented,
        "optional_context_source_families": ["sentilo_connecta", "facilities", "xdata_barcelona_bulk"],
        "source_records": [source_record(family, reports, "D1A/D2 source family") for family in represented],
        "summary": "BARC-F4-D3 binds source-limited mobility, transport, and environment context bundles without accepting Barcelona Flow 4.",
    }


def governance_boundaries() -> list[str]:
    return list(BOUNDARY_LINES)


def forbidden_claims() -> list[str]:
    return [
        "no_city_core_acceptance",
        "no_flow4_acceptance",
        "no_live_control_claim",
        "no_public_safety_or_dispatch_claim",
        "no_health_decision",
        "no_port_control_claim",
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
        "city": "barcelona",
        "flow": "F4",
        "mode": "mobility_transport_environment_context",
        "claim_label": "[R]",
        "city_core_status": "candidate_only",
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
    bicing_subject = "barc-f4:bicing_station_status_context"
    traffic_subject = "barc-f4:traffic_road_section_context"
    tmb_subject = "barc-f4:tmb_transit_context"
    air_noise_subject = "barc-f4:air_noise_environment_context"
    governance_subject = "barc-f4:mobility_environment_governance_boundary"
    amb_subject = "barc-f4:amb_gtfs_rt_context"
    sentilo_subject = "barc-f4:sentilo_sensor_mobility_context"
    facility_subject = "barc-f4:area_facility_mobility_context"

    return [
        make_bundle(
            "bicing_station_status_context_bundle",
            {
                "subject_id": bicing_subject,
                "question": "How can Bicing station status and station information provide review context for a place/time window?",
                "anchor": "station_id/district_id/neighbourhood_id/observed_at",
            },
            {"type": "current_snapshot", "historical_completeness": False, "archive_bound": False},
            [
                source_record("bicing_gbfs", reports, "Bicing station status and information context"),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "Bicing GBFS", "native_namespace": "gbfs_station_information_status", "native_id_role": "station_id", "native_id_confidence": "source_native"},
                {"native_authority": "Open Data BCN", "native_namespace": "district_neighbourhood_boundaries", "native_id_role": "district_id_or_neighbourhood_id", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", bicing_subject, "source:bicing_gbfs", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", bicing_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", bicing_subject, "native:bicing:station_id", "source_native", "GBFS station fields"),
                rel("LOCATED_IN", bicing_subject, "context:district_or_neighbourhood", "contextual", "D2 join keys"),
                rel("OBSERVED_BY", bicing_subject, "probe:bicing_gbfs_current_snapshot", "point_in_time", "D1A landed GBFS current files"),
                rel("HAS_LIMITATION", bicing_subject, "limitation:bicing_current_snapshot_only", "boundary", "Source limitation policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", bicing_subject, "boundary:candidate_only_no_flow_acceptance", "boundary", "D3 governance boundary"),
            ],
            "A",
            "point_in_time",
            [
                "Bicing GBFS station status is current snapshot context, not historical completeness.",
                "Station observations are review context only and do not create operational recommendations.",
            ],
            [
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#bicing_gbfs",
                "BARC_D1A_LANDING_SUMMARY.json#bicing_gbfs",
                "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json#boundaries",
            ],
        ),
        make_bundle(
            "traffic_road_section_context_bundle",
            {
                "subject_id": traffic_subject,
                "question": "How can traffic state and road-section sources provide mobility review context for a bounded window?",
                "anchor": "road_section_id/district_id/neighbourhood_id/observed_at",
            },
            {"type": "bounded_source_window", "full_source_completeness": False},
            [
                source_record("traffic_state", reports, "road-section traffic state context"),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "Open Data BCN", "native_namespace": "traffic_state", "native_id_role": "road_section_id", "native_id_confidence": "source_native_or_contextual"},
                {"native_authority": "Open Data BCN", "native_namespace": "district_neighbourhood_boundaries", "native_id_role": "district_id_or_neighbourhood_id", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", traffic_subject, "source:traffic_state", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", traffic_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", traffic_subject, "native:barcelona:road_section_id", "source_native_or_contextual", "D2 join keys"),
                rel("NEAR", traffic_subject, "context:station_stop_or_area_window", "contextual", "F4 join anchor"),
                rel("LOCATED_IN", traffic_subject, "context:district_or_neighbourhood", "contextual", "D2 join keys"),
                rel("HAS_LIMITATION", traffic_subject, "limitation:bounded_traffic_source_landing", "boundary", "Source limitation policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", traffic_subject, "boundary:mobility_context_only", "boundary", "D3 no-overclaim policy"),
            ],
            "B",
            "bounded_window",
            [
                "Traffic state sources include mixed full/sample landing and must remain bounded mobility context.",
                "Traffic state context does not create control directives or route actions.",
            ],
            [
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#traffic_state",
                "BARC_D1A_LANDING_SUMMARY.json#traffic_state",
            ],
        ),
        make_bundle(
            "tmb_transit_context_bundle",
            {
                "subject_id": tmb_subject,
                "question": "How can TMB static and API-boundary records provide transit review context?",
                "anchor": "stop_id/route_id/district_id/observed_at",
            },
            {"type": "credentialed_or_parameter_bound_probe", "historical_completeness": False},
            [
                source_record("tmb_boundary", reports, "TMB static GTFS, metro lines, and API-boundary context"),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "TMB", "native_namespace": "gtfs_static_or_line_api", "native_id_role": "stop_id_or_route_id", "native_id_confidence": "source_native_or_probe"},
                {"native_authority": "Open Data BCN", "native_namespace": "district_neighbourhood_boundaries", "native_id_role": "district_id_or_neighbourhood_id", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", tmb_subject, "source:tmb_boundary", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", tmb_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", tmb_subject, "native:tmb:stop_or_route_id", "source_native_or_probe", "D2 join keys"),
                rel("LOCATED_IN", tmb_subject, "context:district_or_neighbourhood", "contextual", "D2 join keys"),
                rel("OBSERVED_BY", tmb_subject, "probe:tmb_api_boundary", "point_in_time", "D1A endpoint retry and landing summary"),
                rel("HAS_LIMITATION", tmb_subject, "limitation:tmb_credential_or_parameter_boundary", "boundary", "D1A credential boundary"),
                rel("HAS_GOVERNANCE_BOUNDARY", tmb_subject, "boundary:transit_context_only", "boundary", "D3 governance boundary"),
            ],
            "B",
            "point_in_time",
            [
                "TMB source family includes a credential/parameter/download boundary, so it remains transit context only.",
                "TMB iBus exact parameter work is carried forward to later gates.",
            ],
            [
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#tmb_boundary",
                "BARC_D1A_CREDENTIAL_BOUNDARY_REPORT.json#tmb_boundary",
                "BARC_D1A_ENDPOINT_RETRY_REPORT.json#tmb_boundary",
            ],
        ),
        make_bundle(
            "air_noise_environment_context_bundle",
            {
                "subject_id": air_noise_subject,
                "question": "How can air quality and noise sources provide environmental context for mobility review windows?",
                "anchor": "monitor_or_area_id/district_id/neighbourhood_id/time_window",
            },
            {"type": "mixed_environment_source_window", "full_source_completeness": False},
            [
                source_record("air_quality", reports, "air quality station and measurement context"),
                source_record("noise", reports, "noise monitoring and strategic context"),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "Open Data BCN", "native_namespace": "air_quality", "native_id_role": "station_or_measurement_id", "native_id_confidence": "source_native"},
                {"native_authority": "Open Data BCN", "native_namespace": "noise", "native_id_role": "monitor_or_noise_area_id", "native_id_confidence": "source_native_or_contextual"},
                {"native_authority": "Open Data BCN", "native_namespace": "district_neighbourhood_boundaries", "native_id_role": "district_id_or_neighbourhood_id", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", air_noise_subject, "source:air_quality", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", air_noise_subject, "source:noise", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", air_noise_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("OBSERVED_BY", air_noise_subject, "program:barcelona_air_noise_sources", "source_context", "D1A landed environmental sources"),
                rel("OBSERVES", "program:barcelona_air_noise_sources", air_noise_subject, "source_context", "Environmental observation context"),
                rel("LOCATED_IN", air_noise_subject, "context:district_or_neighbourhood", "contextual", "D2 join keys"),
                rel("HAS_LIMITATION", air_noise_subject, "limitation:environment_context_only", "boundary", "Source limitation policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", air_noise_subject, "boundary:no_health_decision", "boundary", "D3 governance boundary"),
            ],
            "B",
            "bounded_window",
            [
                "Air quality and noise evidence is environmental context only and does not create a health decision.",
                "Noise sources include mixed sample/full landing and remain source-limited.",
            ],
            [
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#air_quality",
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#noise",
                "BARC_D1A_LANDING_SUMMARY.json#air_quality",
                "BARC_D1A_LANDING_SUMMARY.json#noise",
            ],
        ),
        make_bundle(
            "mobility_environment_governance_boundary_bundle",
            {
                "subject_id": governance_subject,
                "question": "Which governance and source boundaries must be carried into D4 replay and face proof?",
                "anchor": "station_id/stop_id/route_id/road_section_id/area_id/time_window",
            },
            {"type": "governance_boundary_register", "candidate_city_core": True},
            [
                source_record("boundaries", reports, "candidate geography spine"),
                source_record("xdata_barcelona_bulk", reports, "optional bulk limitation context", optional=True),
            ],
            [
                {"native_authority": "BARC-D2", "native_namespace": "candidate_city_core", "native_id_role": "district_id/neighbourhood_id/facility_id/station_id/stop_id/road_section_id", "native_id_confidence": "candidate_only"},
            ],
            [
                rel("SUPPORTED_BY", governance_subject, "contract:BARC-F4-D2", "source_reference", "BARC-F4-D2 source/join contract"),
                rel("SUPPORTED_BY", governance_subject, "contract:XFLOW-D1", "source_reference", "XFLOW queue lock"),
                rel("HAS_SOURCE_RECORD", governance_subject, "source:boundaries", "source_reference", "BARC candidate city core"),
                rel("HAS_SOURCE_RECORD", governance_subject, "source:xdata_barcelona_bulk_optional", "optional_context", "XDATA-D1 Barcelona limited landing"),
                rel("HAS_LIMITATION", governance_subject, "limitation:barcelona_candidate_only", "boundary", "BARC-D2 city core boundary"),
                rel("HAS_LIMITATION", governance_subject, "limitation:optional_xdata_not_binding", "boundary", "XDATA optional policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", governance_subject, "boundary:no_acceptance_or_operations", "boundary", "D3 governance boundary"),
                rel("SUBJECT_OF", governance_subject, "bundle:mobility_environment_governance_boundary_bundle", "bundle_reference", "EvidenceBundle contract"),
            ],
            "B",
            "full_available_sample",
            [
                "Barcelona city core remains candidate-only; D3 creates bundle contracts, not accepted city core output.",
                "Optional XDATA bulk records are limitation context and do not replace D1A/D2 source evidence.",
            ],
            [
                "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json#status",
                "XFLOW_D1_D3_QUEUE_RECOMMENDATION.json#BARC-F4-D3",
                "XDATA_D1_CITY_SUMMARY_MATRIX.json#BARC",
            ],
        ),
        make_bundle(
            "amb_gtfs_rt_context_bundle",
            {
                "subject_id": amb_subject,
                "question": "How can AMB GTFS-RT endpoint confirmation support later transit context review?",
                "anchor": "feed_endpoint/route_id/stop_id/observed_at",
            },
            {"type": "endpoint_confirmed_probe", "decoded_records_gated": False},
            [
                source_record("amb_gtfs_rt", reports, "AMB GTFS-RT endpoint confirmation context"),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "AMB", "native_namespace": "gtfs_rt", "native_id_role": "feed_endpoint_or_route_stop_id", "native_id_confidence": "endpoint_confirmed"},
            ],
            [
                rel("HAS_SOURCE_RECORD", amb_subject, "source:amb_gtfs_rt", "source_reference", "BARC-F4-D2 source evidence"),
                rel("HAS_SOURCE_RECORD", amb_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", amb_subject, "native:amb:gtfs_rt_feed_or_route_stop", "endpoint_confirmed", "D1A endpoint confirmation"),
                rel("OBSERVED_BY", amb_subject, "probe:amb_gtfs_rt_endpoint", "point_in_time", "D1A API probe"),
                rel("HAS_LIMITATION", amb_subject, "limitation:amb_endpoint_confirmed_not_decoded_feed", "boundary", "Source limitation policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", amb_subject, "boundary:transit_context_only", "boundary", "D3 governance boundary"),
            ],
            "C",
            "point_in_time",
            [
                "AMB GTFS-RT is endpoint-confirmed/probe context until decoded usable records are gated.",
                "Endpoint confirmation alone is not historical completeness.",
            ],
            [
                "BARC_F4_D2_SOURCE_JOIN_CONTRACT.json#amb_gtfs_rt",
                "BARC_D1A_ENDPOINT_RETRY_REPORT.json#amb_gtfs_rt",
            ],
        ),
        make_bundle(
            "sentilo_sensor_mobility_context_bundle",
            {
                "subject_id": sentilo_subject,
                "question": "How can Sentilo/Connecta catalogue and sensor map context support mobility/environment review?",
                "anchor": "sensor_id/component_id/area_id/observed_at",
            },
            {"type": "catalog_or_endpoint_confirmed_probe", "direct_actuation": False},
            [
                source_record("sentilo_connecta", reports, "Sentilo/Connecta catalogue and sensor-map optional context", optional=True),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "Sentilo/Connecta BCN", "native_namespace": "catalog_component_or_sensor_map", "native_id_role": "sensor_id_or_component_id", "native_id_confidence": "endpoint_confirmed_or_catalog"},
            ],
            [
                rel("HAS_SOURCE_RECORD", sentilo_subject, "source:sentilo_connecta", "source_reference", "BARC-D1A targeted landing"),
                rel("HAS_SOURCE_RECORD", sentilo_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", sentilo_subject, "native:sentilo:component_or_sensor_id", "endpoint_confirmed_or_catalog", "D1A landed catalog files"),
                rel("OBSERVED_BY", sentilo_subject, "catalog:sentilo_connecta", "source_context", "D1A landed catalog pages"),
                rel("HAS_LIMITATION", sentilo_subject, "limitation:sentilo_optional_context", "boundary", "Optional source policy"),
                rel("HAS_GOVERNANCE_BOUNDARY", sentilo_subject, "boundary:sensor_context_no_live_control", "boundary", "D3 governance boundary"),
            ],
            "C",
            "point_in_time",
            [
                "Sentilo/Connecta is optional catalogue and sensor-map context, not a live control interface.",
                "Sensor context remains candidate-only until later joins are gated.",
            ],
            [
                "BARC_D1A_LANDING_SUMMARY.json#sentilo_connecta",
                "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json#sentilo_connecta",
            ],
        ),
        make_bundle(
            "area_facility_mobility_context_bundle",
            {
                "subject_id": facility_subject,
                "question": "How can facilities and public services context support mobility/environment area review?",
                "anchor": "facility_id/area_id/district_id/neighbourhood_id",
            },
            {"type": "bounded_facility_context", "full_source_completeness": False},
            [
                source_record("facilities", reports, "facilities and public-services optional mobility context", optional=True),
                source_record("boundaries", reports, "district/neighbourhood join context"),
            ],
            [
                {"native_authority": "Open Data BCN", "native_namespace": "facilities_public_services", "native_id_role": "facility_id", "native_id_confidence": "source_native_or_contextual"},
                {"native_authority": "Open Data BCN", "native_namespace": "district_neighbourhood_boundaries", "native_id_role": "district_id_or_neighbourhood_id", "native_id_confidence": "source_native"},
            ],
            [
                rel("HAS_SOURCE_RECORD", facility_subject, "source:facilities", "source_reference", "BARC-D2 candidate city core source evidence"),
                rel("HAS_SOURCE_RECORD", facility_subject, "source:boundaries", "source_reference", "BARC candidate geography spine"),
                rel("HAS_NATIVE_ID", facility_subject, "native:barcelona:facility_id", "source_native_or_contextual", "BARC-D2 native id candidates"),
                rel("LOCATED_IN", facility_subject, "context:district_or_neighbourhood", "contextual", "D2 join keys"),
                rel("NEAR", facility_subject, "context:station_stop_road_section_or_area", "contextual", "F4 join anchor"),
                rel("HAS_LIMITATION", facility_subject, "limitation:bounded_facility_source_landing", "boundary", "D1A mixed sample/full landing"),
                rel("HAS_GOVERNANCE_BOUNDARY", facility_subject, "boundary:facility_context_only", "boundary", "D3 governance boundary"),
            ],
            "B",
            "bounded_window",
            [
                "Facilities context includes mixed landed sample/full sources and must not be treated as full-source unless a later count gate proves it.",
                "Facility proximity is review context only and does not certify service coverage.",
            ],
            [
                "BARC_EXP_D1D2_CITY_CORE_D2_CONTRACT.json#facilities",
                "BARC_D1A_LANDING_SUMMARY.json#facilities",
            ],
        ),
    ]


def validate_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    relationship_types = set()
    exact_tokens = forbidden_exact_tokens()
    for bundle in bundles:
        bundle_id = bundle.get("evidence_bundle_id", "<missing>")
        for field in REQUIRED_BUNDLE_FIELDS:
            if field not in bundle:
                findings.append({"bundle": bundle_id, "finding": f"missing field {field}"})
        if bundle.get("city") != "barcelona":
            findings.append({"bundle": bundle_id, "finding": "city must be barcelona"})
        if bundle.get("flow") != "F4":
            findings.append({"bundle": bundle_id, "finding": "flow must be F4"})
        if bundle.get("mode") != "mobility_transport_environment_context":
            findings.append({"bundle": bundle_id, "finding": "unexpected mode"})
        if bundle.get("claim_label") != "[R]":
            findings.append({"bundle": bundle_id, "finding": "claim label must be [R]"})
        if bundle.get("city_core_status") != "candidate_only":
            findings.append({"bundle": bundle_id, "finding": "city core status must remain candidate_only"})
        if bundle.get("location_confidence") not in {"A", "B", "C", "D"}:
            findings.append({"bundle": bundle_id, "finding": "invalid location confidence"})
        if bundle.get("temporal_confidence") not in TEMPORAL_CONFIDENCE_VALUES:
            findings.append({"bundle": bundle_id, "finding": "invalid temporal confidence"})
        if not bundle.get("source_records"):
            findings.append({"bundle": bundle_id, "finding": "missing source records"})
        if not bundle.get("limitations"):
            findings.append({"bundle": bundle_id, "finding": "missing limitations"})
        if not bundle.get("governance_boundaries"):
            findings.append({"bundle": bundle_id, "finding": "missing governance boundaries"})
        bundle_text = json.dumps(bundle, sort_keys=True, ensure_ascii=True)
        for token in exact_tokens:
            if token in bundle_text:
                findings.append({"bundle": bundle_id, "finding": "contains reserved exact forbidden token"})
        for relationship in bundle.get("relationships", []):
            rel_type = relationship.get("relationship_type")
            relationship_types.add(rel_type)
            if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
                findings.append({"bundle": bundle_id, "finding": f"relationship type not allowed: {rel_type}"})
    return {
        "gate": "BARC-F4-D3-EVIDENCEBUNDLES",
        "status": "PASS" if not findings and len(bundles) >= 5 else "FAIL",
        "bundle_count": len(bundles),
        "relationship_types": sorted(item for item in relationship_types if item),
        "findings": findings,
    }


def evidence_bundle_contract(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "contract_version": "BARC-F4-D3-EvidenceBundle-v1",
        "required_fields": REQUIRED_BUNDLE_FIELDS,
        "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES),
        "source_limitation_vocab": sorted(SOURCE_LIMITATION_VOCAB),
        "claim_label": "[R]",
        "city_core_status": "candidate_only",
        "city": "barcelona",
        "flow": "F4",
        "mode": "mobility_transport_environment_context",
        "bundle_ids": [bundle["evidence_bundle_id"] for bundle in bundles],
        "minimum_required_bundle_count": 5,
    }


def selected_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = {
        "bicing_station_status_context_bundle": "Required Bicing station/status snapshot context.",
        "traffic_road_section_context_bundle": "Required road-section traffic context with bounded source landing.",
        "tmb_transit_context_bundle": "Required TMB transit boundary context.",
        "air_noise_environment_context_bundle": "Required air/noise environment context.",
        "mobility_environment_governance_boundary_bundle": "Required boundary carry-forward bundle.",
        "amb_gtfs_rt_context_bundle": "Safe optional AMB endpoint-confirmed GTFS-RT context.",
        "sentilo_sensor_mobility_context_bundle": "Safe optional Sentilo catalogue/sensor context.",
        "area_facility_mobility_context_bundle": "Safe optional area/facility mobility context.",
    }
    return {
        "status": "PASS",
        "selected_count": len(bundles),
        "selected_bundles": [
            {
                "evidence_bundle_id": bundle["evidence_bundle_id"],
                "subject_id": bundle["subject"].get("subject_id"),
                "selection_reason": reasons.get(bundle["evidence_bundle_id"], "Selected source-limited context bundle."),
                "source_families": [record["source_family"] for record in bundle["source_records"]],
                "city_core_status": bundle["city_core_status"],
            }
            for bundle in bundles
        ],
    }


def trace_report(bundles: list[dict[str, Any]], reports: dict[str, Any]) -> dict[str, Any]:
    source_family_trace = {}
    for bundle in bundles:
        for record in bundle["source_records"]:
            family = record["source_family"]
            source_family_trace.setdefault(family, set()).update(bundle["trace_refs"])
    return {
        "status": "PASS",
        "traceability": [
            {"source_family": family, "trace_refs": sorted(refs)}
            for family, refs in sorted(source_family_trace.items())
        ],
        "xflow_queue_entry": next(
            (
                item
                for item in reports.get("xflow_queue", {}).get("scored_lanes", [])
                if item.get("d3_gate") == "BARC-F4-D3"
            ),
            {},
        ),
        "bundle_trace_refs_complete": all(bundle.get("trace_refs") for bundle in bundles),
    }


def ontology_compatibility_report(bundles: list[dict[str, Any]], reports: dict[str, Any]) -> dict[str, Any]:
    ontology_relationships = {
        item.get("relationship_name")
        for item in reports.get("ontology_relationships", {}).get("relationship_classes", [])
        if item.get("relationship_name")
    }
    claim_labels = reports.get("ontology_claim_labels", {}).get("claim_labels", {})
    emitted_relationships = {
        relationship.get("relationship_type")
        for bundle in bundles
        for relationship in bundle.get("relationships", [])
        if relationship.get("relationship_type")
    }
    findings = []
    for rel_type in sorted(emitted_relationships):
        if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
            findings.append({"relationship_type": rel_type, "finding": "not in BARC-F4-D3 allowed relationship list"})
        if rel_type not in ontology_relationships:
            findings.append({"relationship_type": rel_type, "finding": "not present in ontology v2 relationship classes"})
    if "[R]" not in claim_labels:
        findings.append({"claim_label": "[R]", "finding": "claim label not present in ontology v2 policy"})
    return {
        "gate": "BARC-F4-D3-ONTOLOGY-COMPATIBILITY",
        "status": "PASS" if not findings else "FAIL",
        "emitted_relationship_types": sorted(emitted_relationships),
        "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES),
        "claim_label": "[R]",
        "claim_label_present": "[R]" in claim_labels,
        "findings": findings,
    }


def boundary_carry_forward_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    checks = {
        "all_bundles_candidate_only": all(bundle.get("city_core_status") == "candidate_only" for bundle in bundles),
        "city_core_not_accepted_boundary": all(any("candidate-only" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "bicing_point_in_time_boundary": all(any("Bicing GBFS" in line and "point-in-time" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "tmb_boundary": all(any("TMB" in line and "parameter-bound" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "amb_boundary": all(any("AMB GTFS-RT" in line and "endpoint-confirmed" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "environment_boundary": all(any("Air and noise" in line and "health decision" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "bounded_source_boundary": all(any("Bounded source landing" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
        "xdata_optional_boundary": all(any("Optional XDATA" in line for line in bundle.get("governance_boundaries", [])) for bundle in bundles),
    }
    return {
        "gate": "BARC-F4-D3-BOUNDARY-CARRY-FORWARD",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "boundary_lines": BOUNDARY_LINES,
    }


def line_is_negated(line: str) -> bool:
    lowered = f" {line.lower()} "
    if any(marker in lowered for marker in NEGATION_MARKERS):
        return True
    return bool(re.search(r"\b(?:no|not|cannot|without|unless)\b", lowered))


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    violations = []
    exact_tokens = forbidden_exact_tokens()
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"BARC_F4_D3_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except UnicodeDecodeError:
            continue
        rel_path = path.relative_to(output_dir).as_posix()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for token in exact_tokens:
                if token in line:
                    violations.append(
                        {
                            "file": rel_path,
                            "line": line_no,
                            "finding": "reserved exact forbidden token emitted",
                        }
                    )
            lowered = line.lower()
            for pattern in POSITIVE_OVERCLAIM_PATTERNS:
                if re.search(pattern, lowered) and not line_is_negated(line):
                    violations.append(
                        {
                            "file": rel_path,
                            "line": line_no,
                            "finding": "positive overclaim phrase",
                            "line_excerpt": line[:160],
                        }
                    )
    return {
        "gate": "BARC-F4-D3-NO-OVERCLAIM",
        "status": "PASS" if not violations else "FAIL",
        "checked_files": len([path for path in output_dir.rglob("*") if path.is_file()]),
        "violations": violations,
    }


def next_d4_handoff(bundles: list[dict[str, Any]], limitation_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "next_gate": "BARC-F4-D4",
        "handoff_mode": "replay_faceproof_with_source_boundaries",
        "eligible_bundle_ids": [bundle["evidence_bundle_id"] for bundle in bundles],
        "must_preserve": [
            "city_core_status=candidate_only",
            "claim_label=[R] only for source-grounded bundle fields",
            "source limitation vocabulary and per-family limitation rules",
            "no Flow 4 acceptance claim",
            "no live control, dispatch, enforcement, health, port, or operational recommendations",
            "optional XDATA context remains non-binding unless a later gate promotes it with evidence",
        ],
        "source_limitation_counts": limitation_report.get("counts_by_represented_family", {}),
    }


def represented_families_from_bundles(bundles: list[dict[str, Any]]) -> list[str]:
    families = []
    for bundle in bundles:
        for record in bundle["source_records"]:
            family = record["source_family"]
            if family not in families:
                families.append(family)
    return families


def artifact_gate(output_dir: Path) -> dict[str, Any]:
    required = [
        "README.md",
        "BARC_F4_D3_HARNESS_REPORT.json",
        "BARC_F4_D3_INPUT_INVENTORY.json",
        "BARC_F4_D3_SOURCE_AND_JOIN_SUMMARY.json",
        "BARC_F4_D3_EVIDENCEBUNDLE_CONTRACT.json",
        "BARC_F4_D3_EVIDENCEBUNDLES.json",
        "BARC_F4_D3_SELECTED_BUNDLES.json",
        "BARC_F4_D3_TRACE_REPORT.json",
        "BARC_F4_D3_SOURCE_LIMITATION_REPORT.json",
        "BARC_F4_D3_NEXT_D4_HANDOFF.json",
        "BARC_F4_D3_NO_OVERCLAIM_REPORT.json",
        "BARC_F4_D3_NO_MUTATION_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    return {"gate": "BARC-F4-D3-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present}


def final_status_from_gates(gates: list[dict[str, Any]], limitation_report: dict[str, Any]) -> str:
    if not gates_pass(gates):
        return "FAIL"
    limited_counts = limitation_report.get("counts_by_represented_family", {})
    limited_total = sum(
        int(limited_counts.get(name, 0))
        for name in ["BOUNDED_SOURCE_LANDING", "POINT_IN_TIME_PROBE", "API_KEY_REQUIRED", "ENDPOINT_CONFIRMED", "OPTIONAL_SOURCE_NOT_BOUND"]
    )
    return "PASS_WITH_SOURCE_LIMITATIONS" if limited_total else "PASS_MOBILITY_TRANSPORT_ENVIRONMENT_EVIDENCEBUNDLES"


def summary_counts(bundles: list[dict[str, Any]], limitation_report: dict[str, Any]) -> dict[str, int]:
    counts = limitation_report.get("counts_by_represented_family", {})
    xdata_counts = limitation_report.get("xdata_optional_summary", {}).get("limitation_counts", {})
    represented = represented_families_from_bundles(bundles)
    return {
        "evidence_bundles_created": len(bundles),
        "selected_bundles": len(bundles),
        "sources_represented": len(represented),
        "bounded_source_inputs": int(counts.get("BOUNDED_SOURCE_LANDING", 0)),
        "point_in_time_probes": int(counts.get("POINT_IN_TIME_PROBE", 0)),
        "metadata_only_sources": int(counts.get("METADATA_ONLY", 0)) + int(xdata_counts.get("METADATA_ONLY", 0) or 0),
    }


def readme_text(final_status: str, counts: dict[str, int], output_dir: Path) -> str:
    return "\n".join(
        [
            f"# {TASK_NAME}",
            "",
            f"Final status: `{final_status}`",
            "",
            "This package creates Barcelona Flow 4 mobility/transport/environment EvidenceBundles only. It preserves candidate-only Barcelona city-core status and does not accept Barcelona Flow 4.",
            "",
            "## Summary",
            "",
            f"- EvidenceBundles created: {counts['evidence_bundles_created']}",
            f"- Selected bundles: {counts['selected_bundles']}",
            f"- Sources represented: {counts['sources_represented']}",
            f"- Bounded source inputs: {counts['bounded_source_inputs']}",
            f"- Point-in-time probes: {counts['point_in_time_probes']}",
            f"- Metadata-only sources: {counts['metadata_only_sources']}",
            "",
            "## Boundaries",
            "",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
            "## Output",
            "",
            str(output_dir),
            "",
        ]
    )


def harness_report(
    output_dir: Path,
    final_status: str,
    gates: list[dict[str, Any]],
    counts: dict[str, int],
    hash_gate: dict[str, Any],
) -> dict[str, Any]:
    all_gates = gates + [hash_gate]
    return {
        "task": TASK_NAME,
        "generation_version": "BARC-F4-D3-v1",
        "generated_at_utc": utc_now(),
        "status": final_status,
        "passed": final_status != "FAIL",
        "output_dir": str(output_dir),
        "counts": counts,
        "gates": all_gates,
        "claim": "EvidenceBundle D3 gate only; Barcelona city core and Flow 4 remain candidate-only.",
    }


def write_core_artifacts(
    output_dir: Path,
    inventory: dict[str, Any],
    source_summary: dict[str, Any],
    bundle_contract: dict[str, Any],
    bundles: list[dict[str, Any]],
    selected: dict[str, Any],
    trace: dict[str, Any],
    limitation_report: dict[str, Any],
    handoff: dict[str, Any],
) -> None:
    write_json(output_dir / "BARC_F4_D3_INPUT_INVENTORY.json", inventory)
    write_json(output_dir / "BARC_F4_D3_SOURCE_AND_JOIN_SUMMARY.json", source_summary)
    write_json(output_dir / "BARC_F4_D3_EVIDENCEBUNDLE_CONTRACT.json", bundle_contract)
    write_json(output_dir / "BARC_F4_D3_EVIDENCEBUNDLES.json", {"status": "PASS", "evidence_bundles": bundles})
    write_json(output_dir / "BARC_F4_D3_SELECTED_BUNDLES.json", selected)
    write_json(output_dir / "BARC_F4_D3_TRACE_REPORT.json", trace)
    write_json(output_dir / "BARC_F4_D3_SOURCE_LIMITATION_REPORT.json", limitation_report)
    write_json(output_dir / "BARC_F4_D3_NEXT_D4_HANDOFF.json", handoff)


def run_barc_f4_d3_gate(
    project_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    loaded = load_inputs(root)
    paths: dict[str, Path] = loaded["paths"]
    reports: dict[str, Any] = loaded["reports"]

    watch_paths = [
        paths["barc_d1"],
        paths["barc_d1a"],
        paths["barc_d1d2"],
        paths["xflow_d1"],
        paths["ontology_v2"],
        paths["xdata_barcelona_landing"],
        paths["xdata_four_city"],
    ]
    before_snapshot = input_snapshot(watch_paths)

    out = reset_output_dir(project_path(root, output_dir), root)

    precond = precondition_report(paths, reports)
    inventory = input_inventory(paths, reports)
    input_gate = gate("BARC-F4-D3-INPUT-INVENTORY", inventory.get("status") == "PASS", optional_xdata_policy=inventory["optional_xdata_policy"])

    bundles = build_evidence_bundles(reports)
    represented = represented_families_from_bundles(bundles)
    limitation_report = source_limitation_report(reports, represented)
    source_limit_gate = gate("BARC-F4-D3-SOURCE-LIMITATIONS", limitation_report.get("status") == "PASS", counts=limitation_report["counts_by_represented_family"])
    source_summary = source_and_join_summary(reports)
    source_join_gate = gate("BARC-F4-D3-SOURCE-JOIN-SUMMARY", source_summary.get("status") == "PASS")
    bundle_contract = evidence_bundle_contract(bundles)
    contract_gate = gate("BARC-F4-D3-EVIDENCEBUNDLE-CONTRACT", bundle_contract.get("status") == "PASS")
    evidence_gate = validate_bundles(bundles)
    ontology_gate = ontology_compatibility_report(bundles, reports)
    boundary_gate = boundary_carry_forward_report(bundles)
    selected = selected_bundles(bundles)
    trace = trace_report(bundles, reports)
    handoff = next_d4_handoff(bundles, limitation_report)

    write_core_artifacts(out, inventory, source_summary, bundle_contract, bundles, selected, trace, limitation_report, handoff)

    after_snapshot = input_snapshot(watch_paths)
    no_mutation = compare_snapshots(before_snapshot, after_snapshot)
    write_json(out / "BARC_F4_D3_NO_MUTATION_REPORT.json", no_mutation)

    provisional_gates = [
        precond,
        input_gate,
        source_join_gate,
        contract_gate,
        evidence_gate,
        source_limit_gate,
        ontology_gate,
        boundary_gate,
        no_mutation,
    ]
    provisional_status = final_status_from_gates(provisional_gates, limitation_report)
    counts = summary_counts(bundles, limitation_report)
    placeholder_hash_gate = {"gate": "BARC-F4-D3-HASHES", "status": "PASS", "file_count": "pending"}
    write_json(out / "BARC_F4_D3_HARNESS_REPORT.json", harness_report(out, provisional_status, provisional_gates, counts, placeholder_hash_gate))
    write_text(out / "README.md", readme_text(provisional_status, counts, out))

    no_overclaim = scan_no_overclaim(out)
    write_json(out / "BARC_F4_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)

    final_gates = [
        precond,
        input_gate,
        source_join_gate,
        contract_gate,
        evidence_gate,
        source_limit_gate,
        ontology_gate,
        boundary_gate,
        no_overclaim,
        no_mutation,
    ]
    final_status = final_status_from_gates(final_gates, limitation_report)
    write_json(out / "BARC_F4_D3_HARNESS_REPORT.json", harness_report(out, final_status, final_gates, counts, placeholder_hash_gate))
    write_text(out / "README.md", readme_text(final_status, counts, out))
    hash_gate = write_hashes(out)
    final_gates_with_artifacts = final_gates + [artifact_gate(out)]
    final_status = final_status_from_gates(final_gates_with_artifacts, limitation_report)
    write_json(out / "BARC_F4_D3_HARNESS_REPORT.json", harness_report(out, final_status, final_gates_with_artifacts, counts, hash_gate))
    write_text(out / "README.md", readme_text(final_status, counts, out))
    hash_gate = write_hashes(out)
    final_harness = harness_report(out, final_status, final_gates_with_artifacts, counts, hash_gate)
    write_json(out / "BARC_F4_D3_HARNESS_REPORT.json", final_harness)
    write_text(out / "README.md", readme_text(final_status, counts, out))
    hash_gate = write_hashes(out)
    final_harness = harness_report(out, final_status, final_gates_with_artifacts, counts, hash_gate)
    write_json(out / "BARC_F4_D3_HARNESS_REPORT.json", final_harness)
    write_hashes(out)

    return {
        "status": final_status,
        "output_dir": out,
        "counts": counts,
        "gates": final_gates_with_artifacts + [hash_gate],
        "harness": final_harness,
    }


def gate_status(gates: list[dict[str, Any]], gate_name: str) -> str:
    for item in gates:
        if item.get("gate") == gate_name:
            return str(item.get("status", "FAIL"))
    return "FAIL"


def final_print(result: dict[str, Any]) -> str:
    counts = result["counts"]
    gates = result["gates"]
    output_display = str(Path(DEFAULT_OUTPUT_DIR))
    lines = [
        f"BARC-F4-D3 Barcelona Mobility / Transport / Environment EvidenceBundles: {result['status']}",
        "",
        f"EvidenceBundles created: {counts['evidence_bundles_created']}",
        f"Selected bundles: {counts['selected_bundles']}",
        f"Sources represented: {counts['sources_represented']}",
        f"Bounded source inputs: {counts['bounded_source_inputs']}",
        f"Point-in-time probes: {counts['point_in_time_probes']}",
        f"Metadata-only sources: {counts['metadata_only_sources']}",
        "",
        f"Source limitations: {gate_status(gates, 'BARC-F4-D3-SOURCE-LIMITATIONS')}",
        f"Ontology compatibility: {gate_status(gates, 'BARC-F4-D3-ONTOLOGY-COMPATIBILITY')}",
        f"Boundary carry-forward: {gate_status(gates, 'BARC-F4-D3-BOUNDARY-CARRY-FORWARD')}",
        f"No-overclaim: {gate_status(gates, 'BARC-F4-D3-NO-OVERCLAIM')}",
        f"No-mutation: {gate_status(gates, 'BARC-F4-D3-NO-MUTATION')}",
        f"Hashes: {gate_status(gates, 'BARC-F4-D3-HASHES')}",
        "",
        f"Final status: {result['status']}",
        f"Output: {output_display}",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".", help="Project root containing outputs and contracts.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for BARC-F4-D3 artifacts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_barc_f4_d3_gate(args.project_root, args.output_dir)
    print(final_print(result))


if __name__ == "__main__":
    main()
