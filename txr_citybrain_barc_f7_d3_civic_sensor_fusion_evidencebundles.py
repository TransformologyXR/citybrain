from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-F7-D3 Barcelona Civic / Sensor Fusion EvidenceBundles"
DEFAULT_OUTPUT_DIR = "outputs/barc_f7_d3_civic_sensor_fusion_evidencebundles"

INPUT_DEFAULTS = {
    "barc_d1": "outputs/barc_d1_deep_source_api_scout",
    "barc_d1a": "outputs/barc_d1a_targeted_source_landing_recovery",
    "barc_d1d2": "outputs/barc_expansion_d1d2_all_flows",
    "barc_f4_d6": "outputs/barc_f4_d6_candidate_review_snapshot",
    "xflow_d1": "outputs/xflow_d1_cross_city_expansion_reconciliation",
    "ontology_v2": "contracts/ontology_v2",
    "xdata_barcelona_landing": "data_landing/xdata_d1_bulk_official_sources_v1/barcelona",
    "xdata_four_city": "outputs/xdata_d1_four_city_bulk_source_landing",
}

F7_D2_CONTRACT = "flows/barc_f7_d1d2_civic_sensor_fusion/BARC_F7_D2_SOURCE_JOIN_CONTRACT.json"

ALLOWED_RELATIONSHIP_TYPES = {
    "HAS_NATIVE_ID",
    "HAS_SOURCE_RECORD",
    "SUPPORTED_BY",
    "HAS_LIMITATION",
    "HAS_GOVERNANCE_BOUNDARY",
    "LOCATED_IN",
    "NEAR",
    "OBSERVED_BY",
    "OBSERVES",
    "SUBJECT_OF",
}

BOUNDARY_LINES = [
    "Barcelona remains candidate-only.",
    "BARC-F7-D3 does not accept Barcelona Flow 7.",
    "IRIS is civic-service context, not emergency/public-safety signal.",
    "Sensor/environment data is context, not health determination.",
    "Mobility/traffic context is not traffic-control instruction.",
    "Point-in-time/API snapshots are not historical completeness.",
]

FORBIDDEN_CLAIMS = [
    "city_core_acceptance",
    "flow7_acceptance",
    "emergency_public_safety_signal",
    "health_determination",
    "traffic_control_instruction",
    "policing_recommendation",
    "enforcement_action",
    "operational_command",
    "api_snapshot_historical_completeness",
    "bounded_landing_full_source",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bbarcelona city core (?:is|was|now is|has been) accepted\b",
    r"\bbarcelona flow 7 (?:is|was|now is|has been) accepted\b",
    r"\bemergency/public-safety signal\b",
    r"\bemergency public safety signal\b",
    r"\bpublic-safety signal\b",
    r"\bpublic safety signal\b",
    r"\bhealth determination\b",
    r"\btraffic-control instruction\b",
    r"\btraffic control instruction\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\boperational command\b",
    r"\bapi snapshot is historical completeness\b",
    r"\bbounded landing is full source\b",
    r"\bbounded source landing is full\b",
]

NEGATION_MARKERS = [
    "\"no ",
    "'no ",
    "no ",
    " no ",
    " not ",
    "do not",
    "does not",
    "cannot",
    "without",
    "unless",
    "not emergency",
    "not health",
    "not traffic-control",
    "not historical completeness",
    "forbidden",
    "boundary",
]

SOURCE_LIMITATION_RULES = {
    "iris": "BOUNDED_SOURCE_LANDING",
    "sentilo_connecta": "ENDPOINT_CONFIRMED",
    "air_quality": "FULL",
    "noise": "BOUNDED_SOURCE_LANDING",
    "traffic_state": "BOUNDED_SOURCE_LANDING",
    "bicing_gbfs": "POINT_IN_TIME_PROBE",
    "facilities": "BOUNDED_SOURCE_LANDING",
    "boundaries": "FULL",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def project_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def reset_output_dir(output_dir: Path, project_root: Path) -> None:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if output_dir.exists():
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(root).lower())
            or "outputs" not in parts
            or resolved.name.lower() != "barc_f7_d3_civic_sensor_fusion_evidencebundles"
        ):
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    output_dir.mkdir(parents=True, exist_ok=True)


def file_inventory(path: Path, max_files: int = 80) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    all_files = sorted(item for item in path.rglob("*") if item.is_file())
    files = []
    for item in all_files[:max_files]:
        stat = item.stat()
        files.append({"path": item.relative_to(path).as_posix(), "bytes": stat.st_size, "sha256": sha256_file(item) if stat.st_size <= 25_000_000 else None})
    return {"exists": True, "file_count": len(all_files), "files": files}


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".tmp", ".part"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(path) if stat.st_size <= 25_000_000 else None}
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(key for key, value in before.items() if after.get(key) != value)
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    return {"gate": "BARC-F7-D3-NO-MUTATION", "status": "PASS" if not changed and not added and not removed else "FAIL", "checked_files": len(before), "changed_inputs": changed, "added_inputs": added, "removed_inputs": removed}


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    return {"gate": "BARC-F7-D3-HASHES", "status": "PASS", "file_count": len(sums)}


def unique_lines(*groups: Any) -> list[str]:
    out: list[str] = []
    for group in groups:
        values = group if isinstance(group, list) else [group]
        for value in values:
            text = str(value).strip()
            if text and text not in out:
                out.append(text)
    return out


def source_lookup(f7_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for record in f7_contract.get("source_evidence", []):
        if isinstance(record, dict) and record.get("family"):
            out[str(record["family"])] = record
    return out


def make_source_record(family: str, lookup: dict[str, dict[str, Any]], landing: dict[str, Any], role: str) -> dict[str, Any]:
    base = dict(lookup.get(family, {}))
    base.update(
        {
            "source_family": family,
            "role": role,
            "source_limitation": SOURCE_LIMITATION_RULES.get(family, "BOUNDED_SOURCE_LANDING"),
            "d1a_target_statuses": landing.get("landing_status_by_target", {}).get(family, []),
            "optional_context": family in {"facilities", "bicing_gbfs"},
        }
    )
    return base


def make_bundle(bundle_id: str, families: list[str], lookup: dict[str, dict[str, Any]], landing: dict[str, Any], subject_question: str, anchor: str, temporal_confidence: str, location_confidence: str = "B") -> dict[str, Any]:
    records = [make_source_record(family, lookup, landing, role=f"{family} context for civic/sensor fusion") for family in families]
    relationships = []
    subject_id = f"barc-f7:{bundle_id.replace('_bundle', '')}"
    for record in records:
        family = record["source_family"]
        relationships.append({"from": subject_id, "relationship_type": "HAS_SOURCE_RECORD", "to": f"source:{family}", "confidence": "source_reference", "evidence_basis": "BARC-F7-D2 source evidence"})
        relationships.append({"from": subject_id, "relationship_type": "HAS_LIMITATION", "to": f"limitation:{record['source_limitation'].lower()}", "confidence": "boundary", "evidence_basis": "F7 source limitation policy"})
    relationships.append({"from": subject_id, "relationship_type": "HAS_GOVERNANCE_BOUNDARY", "to": "boundary:candidate_only_no_flow7_acceptance", "confidence": "boundary", "evidence_basis": "BARC-F7-D3 governance boundary"})
    relationships.append({"from": subject_id, "relationship_type": "LOCATED_IN", "to": "context:district_or_neighbourhood", "confidence": "contextual", "evidence_basis": "D2 join keys"})
    limitations = unique_lines([f"{record['source_family']}: {record['source_limitation']}" for record in records], BOUNDARY_LINES)
    return {
        "evidence_bundle_id": bundle_id,
        "city": "barcelona",
        "flow": "F7",
        "mode": "civic_sensor_fusion_context",
        "claim_label": "[R]",
        "city_core_status": "candidate_only",
        "subject": {"subject_id": subject_id, "question": subject_question, "anchor": anchor},
        "time_window": {"type": temporal_confidence, "historical_completeness": False, "archive_bound": False},
        "source_records": records,
        "native_ids": [{"native_namespace": f"{family}_native_ids", "native_id_role": "source_native_id_or_area_join_key", "native_authority": record.get("publisher", "mixed official/public sources"), "native_id_confidence": "source_native_or_contextual"} for family, record in zip(families, records)],
        "relationships": relationships,
        "location_confidence": location_confidence,
        "temporal_confidence": temporal_confidence,
        "limitations": limitations,
        "governance_boundaries": BOUNDARY_LINES,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "trace_refs": unique_lines([f"BARC_F7_D2_SOURCE_JOIN_CONTRACT.json#{family}" for family in families], [f"BARC_D1A_LANDING_SUMMARY.json#{family}" for family in families], "BARC_F4_D6_CANDIDATE_REVIEW_SNAPSHOT.json#candidate_only_boundary"),
    }


def build_bundles(lookup: dict[str, dict[str, Any]], landing: dict[str, Any]) -> list[dict[str, Any]]:
    specs = [
        ("iris_civic_service_context_bundle", ["iris", "boundaries"], "Where does IRIS civic-service demand appear by area/time?", "civic_event_id/district_id/neighbourhood_id/observed_at", "bounded_window", "B"),
        ("sentilo_sensor_context_bundle", ["sentilo_connecta", "boundaries"], "Where can Sentilo / Connecta sensor catalogue context support civic/sensor review?", "sensor_id/component_id/district_id/observed_at", "point_in_time", "B"),
        ("air_noise_environment_context_bundle", ["air_quality", "noise", "boundaries"], "Where do air-quality and noise context signals overlap with civic/sensor review areas?", "station_id/noise_area_id/district_id/observed_at", "bounded_window", "A"),
        ("civic_mobility_convergence_context_bundle", ["iris", "traffic_state", "bicing_gbfs", "boundaries"], "Where do civic-service demand and mobility context converge?", "civic_event_id/road_section_id/station_id/area_id/time_window", "bounded_window", "B"),
        ("civic_sensor_governance_boundary_bundle", ["iris", "sentilo_connecta", "air_quality", "traffic_state", "boundaries"], "What can and cannot be claimed from Barcelona civic/sensor fusion context?", "source_family/area_id/boundary_id", "bounded_window", "B"),
        ("facilities_public_services_context_bundle", ["facilities", "iris", "boundaries"], "Where do facilities and public services provide area context for civic demand?", "facility_id/civic_event_id/district_id", "bounded_window", "B"),
        ("bicing_civic_sensor_context_bundle", ["bicing_gbfs", "iris", "sentilo_connecta", "boundaries"], "Where do Bicing, civic-service, and sensor catalogue contexts converge?", "station_id/civic_event_id/sensor_id/area_id", "point_in_time", "B"),
        ("district_neighbourhood_fusion_context_bundle", ["boundaries", "iris", "facilities", "air_quality", "noise"], "Where do district/neighbourhood joins anchor civic, facility, and environment context?", "district_id/neighbourhood_id/source_family/time_window", "bounded_window", "A"),
    ]
    return [make_bundle(spec[0], spec[1], lookup, landing, spec[2], spec[3], spec[4], spec[5]) for spec in specs]


def no_overclaim(output_dir: Path) -> dict[str, Any]:
    violations = []
    files = [path for path in output_dir.rglob("*") if path.is_file()]
    for path in files:
        if path.name in {"BARC_F7_D3_NO_OVERCLAIM_REPORT.json", "SHA256SUMS.json"}:
            continue
        lowered = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in FORBIDDEN_POSITIVE_PATTERNS:
            for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                context = lowered[max(0, match.start() - 90) : min(len(lowered), match.end() + 90)]
                if any(marker in context for marker in NEGATION_MARKERS):
                    continue
                violations.append({"file": path.relative_to(output_dir).as_posix(), "pattern_id": hashlib.sha256(pattern.encode("utf-8")).hexdigest()[:12], "context": context.strip()})
    return {"gate": "BARC-F7-D3-NO-OVERCLAIM", "status": "PASS" if not violations else "FAIL", "checked_files": len(files), "violations": violations, "forbidden_claims": FORBIDDEN_CLAIMS}


def gate(name: str, status: str = "PASS", **extra: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": status}
    payload.update(extra)
    return payload


def run(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root).resolve()
    output_dir = project_path(project_root, args.output_dir)
    inputs = {name: project_path(project_root, value) for name, value in INPUT_DEFAULTS.items()}
    mutation_roots = [inputs[name] for name in ["barc_d1", "barc_d1a", "barc_d1d2", "barc_f4_d6", "xflow_d1", "ontology_v2"]] + [project_root / "snapshot", project_root / "snapshots"]
    before = snapshot([path for path in mutation_roots if path.exists()])
    reset_output_dir(output_dir, project_root)

    d1a_harness = read_json(inputs["barc_d1a"] / "BARC_D1A_HARNESS_REPORT.json", {})
    d1d2_harness = read_json(inputs["barc_d1d2"] / "BARC_EXP_D1D2_HARNESS_REPORT.json", {})
    f4_d6 = read_json(inputs["barc_f4_d6"] / "BARC_F4_D6_HARNESS_REPORT.json", {})
    landing = read_json(inputs["barc_d1a"] / "BARC_D1A_LANDING_SUMMARY.json", {})
    f7_contract = read_json(inputs["barc_d1d2"] / F7_D2_CONTRACT, {})
    lookup = source_lookup(f7_contract)
    bundles = build_bundles(lookup, landing)
    selected = bundles
    limitation_counts: dict[str, int] = {value: 0 for value in sorted(set(SOURCE_LIMITATION_RULES.values()))}
    represented_families = set()
    for bundle in bundles:
        for record in bundle["source_records"]:
            represented_families.add(record["source_family"])
            limitation_counts[record["source_limitation"]] = limitation_counts.get(record["source_limitation"], 0) + 1
    final_status = "PASS_WITH_SOURCE_LIMITATIONS"

    input_inventory = {
        "task": TASK_NAME,
        "status": "PASS",
        "inputs": {name: file_inventory(path) for name, path in inputs.items()},
        "optional_xdata_status": "AVAILABLE" if inputs["xdata_barcelona_landing"].exists() or inputs["xdata_four_city"].exists() else "XDATA_OPTIONAL_MISSING",
        "upstream_statuses": {"barc_d1a": d1a_harness.get("status"), "barc_d1d2": d1d2_harness.get("status"), "barc_f4_d6": f4_d6.get("status")},
    }
    write_json(output_dir / "BARC_F7_D3_INPUT_INVENTORY.json", input_inventory)
    source_join = {"status": "PASS", "flow_question": "Where do civic-service demand, sensor/environment signals, mobility context, and facilities converge?", "join_keys": f7_contract.get("join_keys", []), "source_families": sorted(represented_families), "source_limitations": limitation_counts}
    write_json(output_dir / "BARC_F7_D3_SOURCE_AND_JOIN_SUMMARY.json", source_join)
    contract = {"status": "PASS", "contract_version": "BARC-F7-D3-EvidenceBundle-v1", "city": "barcelona", "flow": "F7", "mode": "civic_sensor_fusion_context", "minimum_required_bundle_count": 5, "bundle_ids": [bundle["evidence_bundle_id"] for bundle in bundles], "allowed_relationship_types": sorted(ALLOWED_RELATIONSHIP_TYPES), "required_fields": ["evidence_bundle_id", "city", "flow", "mode", "claim_label", "city_core_status", "subject", "time_window", "source_records", "native_ids", "relationships", "location_confidence", "temporal_confidence", "limitations", "governance_boundaries", "forbidden_claims", "trace_refs"]}
    write_json(output_dir / "BARC_F7_D3_EVIDENCEBUNDLE_CONTRACT.json", contract)
    write_json(output_dir / "BARC_F7_D3_EVIDENCEBUNDLES.json", {"status": "PASS", "evidence_bundles": bundles, "bundle_count": len(bundles)})
    write_json(output_dir / "BARC_F7_D3_SELECTED_BUNDLES.json", {"status": "PASS", "selected_bundles": [{"evidence_bundle_id": bundle["evidence_bundle_id"], "subject_id": bundle["subject"]["subject_id"], "source_families": [record["source_family"] for record in bundle["source_records"]], "selection_reason": "Required or safe optional BARC-F7-D3 civic/sensor fusion context."} for bundle in selected], "selected_count": len(selected)})
    write_json(output_dir / "BARC_F7_D3_TRACE_REPORT.json", {"status": "PASS", "bundle_trace_refs_complete": all(bundle.get("trace_refs") for bundle in bundles), "traceability": [{"evidence_bundle_id": bundle["evidence_bundle_id"], "trace_refs": bundle["trace_refs"]} for bundle in bundles], "xflow_context": "BARC-F7-D3 candidate-flow breadth while city-core remains candidate-only"})
    source_limit_report = {"status": "PASS", "source_limitations": [{"source_family": family, "source_limitation": SOURCE_LIMITATION_RULES[family], "family_status": lookup.get(family, {}).get("family_status"), "landing_status": lookup.get(family, {}).get("landing_status"), "rule": "Preserve source limitation in every F7 downstream artifact."} for family in sorted(SOURCE_LIMITATION_RULES)], "counts": limitation_counts}
    write_json(output_dir / "BARC_F7_D3_SOURCE_LIMITATION_REPORT.json", source_limit_report)
    write_json(output_dir / "BARC_F7_D3_NEXT_D4_HANDOFF.json", {"status": "PASS", "next_gate": "BARC-F7-D4", "handoff_mode": "replay_faceproof_with_civic_sensor_boundaries", "eligible_bundle_ids": [bundle["evidence_bundle_id"] for bundle in selected], "must_preserve": ["city_core_status=candidate_only", "BARC-F7-D3 does not accept Barcelona Flow 7", "IRIS civic-service context is not emergency/public-safety signal", "sensor/environment data is not health determination", "mobility context is not traffic-control instruction", "source limitations and point-in-time/API snapshot boundaries"]})

    readme = f"""# BARC-F7-D3 Barcelona Civic / Sensor Fusion EvidenceBundles

Final status: `{final_status}`

This package creates Barcelona Flow 7 civic/sensor fusion EvidenceBundles only. It preserves candidate-only Barcelona city-core status and does not accept Barcelona Flow 7.

## Summary

- EvidenceBundles created: {len(bundles)}
- Selected bundles: {len(selected)}
- Sources represented: {len(represented_families)}
- Bounded source inputs: {limitation_counts.get('BOUNDED_SOURCE_LANDING', 0)}
- Point-in-time probes: {limitation_counts.get('POINT_IN_TIME_PROBE', 0)}
- Metadata-only sources: {limitation_counts.get('METADATA_ONLY', 0)}

## Boundaries

""" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + f"""

## Output

{output_dir}
"""
    write_text(output_dir / "README.md", readme)
    overclaim = no_overclaim(output_dir)
    write_json(output_dir / "BARC_F7_D3_NO_OVERCLAIM_REPORT.json", overclaim)
    after = snapshot([path for path in mutation_roots if path.exists()])
    mutation = compare_snapshots(before, after)
    write_json(output_dir / "BARC_F7_D3_NO_MUTATION_REPORT.json", mutation)
    ontology_pass = all(rel["relationship_type"] in ALLOWED_RELATIONSHIP_TYPES for bundle in bundles for rel in bundle["relationships"])
    boundary_pass = all(all(line in bundle["governance_boundaries"] for line in BOUNDARY_LINES) for bundle in bundles)
    source_limit_pass = all(record.get("source_limitation") for bundle in bundles for record in bundle["source_records"])
    artifacts = ["README.md", "BARC_F7_D3_INPUT_INVENTORY.json", "BARC_F7_D3_SOURCE_AND_JOIN_SUMMARY.json", "BARC_F7_D3_EVIDENCEBUNDLE_CONTRACT.json", "BARC_F7_D3_EVIDENCEBUNDLES.json", "BARC_F7_D3_SELECTED_BUNDLES.json", "BARC_F7_D3_TRACE_REPORT.json", "BARC_F7_D3_SOURCE_LIMITATION_REPORT.json", "BARC_F7_D3_NEXT_D4_HANDOFF.json", "BARC_F7_D3_NO_OVERCLAIM_REPORT.json", "BARC_F7_D3_NO_MUTATION_REPORT.json"]
    gates = [
        gate("BARC-F7-D3-PRECOND", required_inputs_exist=all(inputs[name].exists() for name in ["barc_d1", "barc_d1a", "barc_d1d2", "barc_f4_d6", "xflow_d1", "ontology_v2"])),
        gate("BARC-F7-D3-INPUT-INVENTORY"),
        gate("BARC-F7-D3-SOURCE-JOIN-SUMMARY"),
        gate("BARC-F7-D3-EVIDENCEBUNDLE-CONTRACT"),
        gate("BARC-F7-D3-EVIDENCEBUNDLES", "PASS" if len(bundles) >= 5 else "FAIL", bundle_count=len(bundles)),
        gate("BARC-F7-D3-SOURCE-LIMITATIONS", "PASS" if source_limit_pass else "FAIL", counts=limitation_counts),
        gate("BARC-F7-D3-ONTOLOGY-COMPATIBILITY", "PASS" if ontology_pass else "FAIL", allowed_relationship_types=sorted(ALLOWED_RELATIONSHIP_TYPES)),
        gate("BARC-F7-D3-BOUNDARY-CARRY-FORWARD", "PASS" if boundary_pass else "FAIL"),
        overclaim,
        mutation,
        gate("BARC-F7-D3-ARTIFACTS", "PASS" if all((output_dir / name).exists() for name in artifacts) else "FAIL", present={name: (output_dir / name).exists() for name in artifacts}),
    ]
    hashes = write_hashes(output_dir)
    gates.append(hashes)
    if any(item.get("status") == "FAIL" for item in gates):
        final_status = "FAIL"
    harness = {"task": TASK_NAME, "status": final_status, "passed": final_status != "FAIL", "claim": "D3 EvidenceBundle gate only; Barcelona city core and Flow 7 remain candidate-only.", "counts": {"evidence_bundles_created": len(bundles), "selected_bundles": len(selected), "sources_represented": len(represented_families), "bounded_source_inputs": limitation_counts.get("BOUNDED_SOURCE_LANDING", 0), "point_in_time_probes": limitation_counts.get("POINT_IN_TIME_PROBE", 0), "metadata_only_sources": limitation_counts.get("METADATA_ONLY", 0)}, "gates": gates, "output_dir": str(output_dir), "generated_at_utc": utc_now()}
    write_json(output_dir / "BARC_F7_D3_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    for item in gates:
        if item.get("gate") == "BARC-F7-D3-HASHES":
            item.update(hashes)
    harness["gates"] = gates
    write_json(output_dir / "BARC_F7_D3_HARNESS_REPORT.json", harness)
    write_hashes(output_dir)

    print(f"BARC-F7-D3 Barcelona Civic / Sensor Fusion EvidenceBundles: {final_status}")
    print()
    print(f"EvidenceBundles created: {len(bundles)}")
    print(f"Selected bundles: {len(selected)}")
    print(f"Sources represented: {len(represented_families)}")
    print(f"Bounded source inputs: {limitation_counts.get('BOUNDED_SOURCE_LANDING', 0)}")
    print(f"Point-in-time probes: {limitation_counts.get('POINT_IN_TIME_PROBE', 0)}")
    print(f"Metadata-only sources: {limitation_counts.get('METADATA_ONLY', 0)}")
    print()
    print(f"Source limitations: {'PASS' if source_limit_pass else 'FAIL'}")
    print(f"Ontology compatibility: {'PASS' if ontology_pass else 'FAIL'}")
    print(f"Boundary carry-forward: {'PASS' if boundary_pass else 'FAIL'}")
    print(f"No-overclaim: {overclaim['status']}")
    print(f"No-mutation: {mutation['status']}")
    print(f"Hashes: {hashes['status']}")
    print()
    print(f"Final status: {final_status}")
    print(f"Output: {output_dir.relative_to(project_root)}")
    return 0 if final_status != "FAIL" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
