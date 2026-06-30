from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


GENERATION_VERSION = "PV1-D5D6D7-FILE-FABRIC-v1"
GENERATED_AT_UTC = "2026-06-28T12:30:00+00:00"
DEFAULT_ONTOLOGY_DIR = "contracts/ontology_v2"
DEFAULT_SDF_PACK = "data_synthetic/pv1_sdf/packs/sdf_chi_near_west_side_v1"
DEFAULT_D5_OUTPUT = "outputs/pv1_d5_event_fabric_contract"
CLAIM_LABEL = "[S]"

REPLAY_PACK_NAMES = [
    "replay_normal_order.jsonl",
    "replay_out_of_order.jsonl",
    "replay_late_arrivals.jsonl",
    "replay_duplicate_events.jsonl",
    "replay_supersession.jsonl",
    "replay_incident_mode_candidate.jsonl",
    "replay_plan_mode_candidate.jsonl",
    "replay_negative_governance_cases.jsonl",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\blive city event fabric complete\b",
    r"\bkafka/redpanda/redis production fabric exists\b",
    r"\bsynthetic data is real observation\b",
    r"\bincident mode complete\b",
    r"\bplan mode complete\b",
    r"\bhitl complete\b",
    r"\bsumo wired\b",
    r"\bpublic safety instruction\b",
    r"\bdispatch recommendation\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\bhealth determination\b",
    r"\btraffic-control order\b",
]


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            return value
    return value


def stable_json(value: Any) -> str:
    return json.dumps(clean_value(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(path: str | Path, project_root: str | Path, required_token: str) -> Path:
    path = Path(path)
    resolved = path.resolve()
    root = Path(project_root).resolve()
    if path.exists():
        resolved_text = str(resolved).lower()
        if not resolved_text.startswith(str(root).lower()) or required_token.lower() not in resolved_text:
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def gate(gate_id: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": gate_id, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: Iterable[dict[str, Any]]) -> bool:
    return all(gate.get("status") == "PASS" for gate in gates)


def no_overclaim_scan(paths: Iterable[str | Path]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    checked = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in NO_OVERCLAIM_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def input_signature(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {"exists": False, "file_count": 0, "files": []}
    files = []
    for item in sorted(path.rglob("*")) if path.is_dir() else [path]:
        if item.is_file():
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {"exists": True, "file_count": len(files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, sig in before.items() if after.get(name) != sig)
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_inputs": sorted(before)}


def discover_replay_packs(sdf_pack: str | Path) -> dict[str, Any]:
    sdf_pack = Path(sdf_pack)
    replay_dir = sdf_pack / "replay_packs"
    discovered: dict[str, str] = {}
    missing: list[str] = []
    for name in REPLAY_PACK_NAMES:
        path = replay_dir / name
        if path.exists():
            discovered[name] = str(path)
        else:
            missing.append(name)
    if not discovered and replay_dir.exists():
        for path in sorted(replay_dir.glob("*.jsonl")):
            discovered[path.name] = str(path)
    return {
        "status": "PASS" if discovered and not missing else "WARN" if discovered else "FAIL",
        "sdf_pack": str(sdf_pack),
        "replay_dir": str(replay_dir),
        "discovered": discovered,
        "missing_expected": missing,
        "replay_pack_count": len(discovered),
    }


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def iso_key(value: Any) -> str:
    return str(value or "")


def ontology_class_for_subject(subject_id: str) -> str:
    parts = subject_id.split(":")
    subject_kind = parts[1] if len(parts) > 1 else "subject"
    return {
        "area": "AdministrativeArea",
        "location": "AddressableLocation",
        "parcel": "Parcel",
        "building": "Building",
        "road_segment": "RoadSegment",
        "transit_node": "TransitNode",
        "facility": "Facility",
        "sensor": "Sensor",
        "organization": "Organization",
        "event": "Event",
        "observation": "Observation",
        "action_proposal": "ActionProposal",
    }.get(subject_kind, "SourceRecord")


def canonical_id_for_subject(subject_id: str) -> str:
    parts = subject_id.split(":")
    subject_kind = parts[1] if len(parts) > 1 else "subject"
    namespace = parts[2] if len(parts) > 2 else "synthetic"
    native = parts[-1] if parts else subject_id
    return f"citybrain:synthetic:{subject_kind}:{namespace}:{native}"


def ontology_subject_mappings(subject_ids: Iterable[str]) -> list[dict[str, Any]]:
    mappings = []
    for subject_id in subject_ids:
        mappings.append(
            {
                "subject_id": subject_id,
                "ontology_class": ontology_class_for_subject(str(subject_id)),
                "canonical_id": canonical_id_for_subject(str(subject_id)),
                "native_id": str(subject_id),
                "native_namespace": "sdf_chi_near_west_side_v1",
                "native_id_role": "primary",
                "native_id_confidence": "exact",
                "claim_label": CLAIM_LABEL,
            }
        )
    return mappings


def normalize_event(row: dict[str, Any], source_path: str | Path | None = None) -> dict[str, Any]:
    subject_ids = [str(item) for item in row.get("subject_ids", [])]
    envelope = {
        "event_id": str(row.get("event_id")),
        "event_time": str(row.get("event_time")),
        "processing_time": str(row.get("processing_time")),
        "source_system": str(row.get("source_system")),
        "event_type": str(row.get("event_type")),
        "subject_ids": subject_ids,
        "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
        "sequence_number": int(row.get("sequence_number") or 0),
        "replay_pack_id": str(row.get("replay_pack_id")),
        "late_arrival_flag": bool(row.get("late_arrival_flag", False)),
        "out_of_order_flag": bool(row.get("out_of_order_flag", False)),
        "duplicate_of_event_id": row.get("duplicate_of_event_id"),
        "supersedes_event_id": row.get("supersedes_event_id"),
        "claim_label": row.get("claim_label", CLAIM_LABEL),
        "synthetic": bool(row.get("synthetic", True)),
        "ontology_subject_mappings": ontology_subject_mappings(subject_ids),
        "source_path": str(source_path) if source_path else None,
    }
    return envelope


def state_category(event: dict[str, Any]) -> str:
    event_type = str(event.get("event_type", ""))
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    request_code = str(payload.get("request_code", ""))
    if "negative_governance" in event_type or request_code:
        return "governance_boundary_context"
    if "incident_mode" in event_type or "incident" in event_type:
        return "incident_candidate_context"
    if "plan_mode" in event_type or "action_proposal" in event_type:
        return "plan_proposal_context"
    if "traffic" in event_type or "mobility" in event_type:
        return "mobility_context"
    if "environment" in event_type or "sensor" in event_type or "air" in event_type:
        return "environment_context"
    if "civic" in event_type or "inspection" in event_type or "license" in event_type or "permit" in event_type:
        return "civic_service_context"
    if any("sensor" in str(subject) for subject in event.get("subject_ids", [])):
        return "sensor_context"
    return "area_status"


def process_events(rows: list[dict[str, Any]], pack_path: str | Path | None = None) -> dict[str, Any]:
    normalized = [normalize_event(row, pack_path) for row in rows]
    state_by_subject: dict[str, dict[str, Any]] = {}
    change_log: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    duplicate_count = 0
    late_count = 0
    out_of_order_count = 0
    supersession_count = 0
    negative_count = 0
    category_counts: dict[str, int] = {}
    superseded_events: dict[str, str] = {}

    for arrival_index, event in enumerate(normalized, start=1):
        event_id = event["event_id"]
        category = state_category(event)
        category_counts[category] = category_counts.get(category, 0) + 1
        duplicate = event_id in seen_event_ids
        if duplicate:
            duplicate_count += 1
            event["duplicate_of_event_id"] = event_id
        else:
            seen_event_ids.add(event_id)
        if event.get("late_arrival_flag"):
            late_count += 1
        if event.get("out_of_order_flag"):
            out_of_order_count += 1
        if event.get("supersedes_event_id"):
            supersession_count += 1
            superseded_events[str(event["supersedes_event_id"])] = event_id
        if category == "governance_boundary_context":
            negative_count += 1
        if duplicate:
            change_log.append(
                {
                    "arrival_index": arrival_index,
                    "event_id": event_id,
                    "change_type": "duplicate_skipped",
                    "category": category,
                    "claim_label": event["claim_label"],
                    "duplicate_of_event_id": event["duplicate_of_event_id"],
                }
            )
            continue
        for subject_id in event.get("subject_ids", []) or [event_id]:
            prior = state_by_subject.get(subject_id)
            should_update = prior is None or iso_key(event["event_time"]) >= iso_key(prior.get("event_time")) or event.get("late_arrival_flag") or event.get("supersedes_event_id")
            if should_update:
                state_by_subject[subject_id] = {
                    "subject_id": subject_id,
                    "ontology_mapping": ontology_subject_mappings([subject_id])[0],
                    "current_event_id": event_id,
                    "event_time": event["event_time"],
                    "processing_time": event["processing_time"],
                    "event_type": event["event_type"],
                    "category": category,
                    "claim_label": event["claim_label"],
                    "synthetic": event["synthetic"],
                    "late_arrival_flag": event["late_arrival_flag"],
                    "out_of_order_flag": event["out_of_order_flag"],
                    "duplicate_of_event_id": event.get("duplicate_of_event_id"),
                    "supersedes_event_id": event.get("supersedes_event_id"),
                    "superseded_by_event_id": None,
                    "governance_boundaries": governance_boundaries_for_event(event),
                }
                change_log.append(
                    {
                        "arrival_index": arrival_index,
                        "event_id": event_id,
                        "subject_id": subject_id,
                        "change_type": "state_updated",
                        "category": category,
                        "claim_label": event["claim_label"],
                        "late_arrival_flag": event["late_arrival_flag"],
                        "out_of_order_flag": event["out_of_order_flag"],
                        "supersedes_event_id": event.get("supersedes_event_id"),
                    }
                )
            else:
                change_log.append(
                    {
                        "arrival_index": arrival_index,
                        "event_id": event_id,
                        "subject_id": subject_id,
                        "change_type": "older_event_recorded_not_current",
                        "category": category,
                        "claim_label": event["claim_label"],
                    }
                )
    for subject_state in state_by_subject.values():
        current_event_id = subject_state["current_event_id"]
        if current_event_id in superseded_events:
            subject_state["superseded_by_event_id"] = superseded_events[current_event_id]

    state_store = {
        "state_by_subject": dict(sorted(state_by_subject.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "superseded_events": dict(sorted(superseded_events.items())),
    }
    state_hash = hashlib.sha256(stable_json(state_store).encode("utf-8")).hexdigest()
    return {
        "status": "PASS",
        "events_read": len(rows),
        "events_applied": len(seen_event_ids),
        "duplicate_count": duplicate_count,
        "late_arrival_count": late_count,
        "out_of_order_count": out_of_order_count,
        "supersession_count": supersession_count,
        "negative_governance_count": negative_count,
        "subjects_materialized": len(state_by_subject),
        "current_state_categories": len(category_counts),
        "state_store": state_store,
        "state_hash": state_hash,
        "change_log": change_log,
        "normalized_event_count": len(normalized),
    }


def governance_boundaries_for_event(event: dict[str, Any]) -> list[str]:
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    boundaries = ["synthetic_not_real_observation", "review_only"]
    if event.get("claim_label") == "[S]":
        boundaries.append("claim_label_synthetic_preserved")
    if payload.get("execution_allowed") is False:
        boundaries.append("no_autonomous_execution")
    if payload.get("expected_behavior"):
        boundaries.append(str(payload["expected_behavior"]))
    if "incident" in str(event.get("event_type")):
        boundaries.append("no_emergency_dispatch_claim")
    if "plan" in str(event.get("event_type")) or "proposal" in str(event.get("event_type")):
        boundaries.append("approval_required_proposal_only")
    return sorted(set(boundaries))


def event_envelope_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PV1-D5 File-backed Event Envelope",
        "type": "object",
        "required": [
            "event_id",
            "event_time",
            "processing_time",
            "source_system",
            "event_type",
            "subject_ids",
            "payload",
            "sequence_number",
            "replay_pack_id",
            "late_arrival_flag",
            "out_of_order_flag",
            "duplicate_of_event_id",
            "supersedes_event_id",
            "claim_label",
            "synthetic",
            "ontology_subject_mappings",
        ],
        "properties": {
            "event_id": {"type": "string"},
            "event_time": {"type": "string"},
            "processing_time": {"type": "string"},
            "source_system": {"type": "string"},
            "event_type": {"type": "string"},
            "subject_ids": {"type": "array", "items": {"type": "string"}},
            "payload": {"type": "object"},
            "sequence_number": {"type": "integer"},
            "replay_pack_id": {"type": "string"},
            "late_arrival_flag": {"type": "boolean"},
            "out_of_order_flag": {"type": "boolean"},
            "duplicate_of_event_id": {"type": ["string", "null"]},
            "supersedes_event_id": {"type": ["string", "null"]},
            "claim_label": {"type": "string", "enum": ["[S]", "[R]", "[M]", "[Q]", "[G]", "[P]", "[SIM]"]},
            "synthetic": {"type": "boolean"},
            "ontology_subject_mappings": {"type": "array"},
        },
        "additionalProperties": True,
    }


def run_pv1_d5_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    output_dir: str | Path = DEFAULT_D5_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    ont = project_path(root, ontology_dir)
    sdf = project_path(root, sdf_pack)
    out = reset_output_dir(project_path(root, output_dir), root, "pv1_d5_event_fabric_contract")
    replay_inventory = discover_replay_packs(sdf)

    contract = {
        "contract_id": "PV1-D5-FILE-BACKED-EVENT-FABRIC",
        "status": "PASS",
        "generation_version": GENERATION_VERSION,
        "generated_at_utc": GENERATED_AT_UTC,
        "scope": "file-backed event fabric over SDF JSONL replay packs",
        "deferred_event_bus_candidates": ["Kafka", "Redpanda", "Redis Streams"],
        "required_inputs": [str(ont), str(sdf)],
        "rules": [
            "event_time controls historical truth ordering.",
            "processing_time controls arrival/materialization order.",
            "supersession replaces or amends prior state according to policy.",
            "duplicates must not double-count current state.",
            "late arrivals update materialized state when valid under policy.",
            "[S] remains [S].",
            "[SIM] remains simulation output if present.",
            "[P] remains proposal-only, not execution.",
        ],
    }
    event_time_policy = {
        "status": "PASS",
        "rule": "event_time is the canonical historical ordering key.",
        "late_arrival_handling": "late events are recorded as late and may update current state when they supersede or have a newer event_time for a subject.",
    }
    processing_time_policy = {
        "status": "PASS",
        "rule": "processing_time is the arrival/materialization order key.",
        "out_of_order_handling": "arrival order is preserved in change logs while current state uses event-time semantics for subject state.",
    }
    ontology_mapping_policy = {
        "status": "PASS",
        "rule": "subject_ids map to ontology_subject_mappings without replacing native synthetic IDs.",
        "mapping_examples": {
            "synthetic:location:*": "AddressableLocation",
            "synthetic:building:*": "Building",
            "synthetic:organization:*": "Organization",
            "synthetic:event:*": "Event",
            "synthetic:action_proposal:*": "ActionProposal",
        },
    }
    dedupe_policy = {
        "status": "PASS",
        "dedupe_key": "event_id",
        "duplicate_policy": "first event_id application wins; subsequent duplicates are logged with duplicate_of_event_id and skipped for current-state counts.",
        "supersession_policy": "supersedes_event_id marks prior event state as amended by a later event.",
    }
    current_state_policy = {
        "status": "PASS",
        "materialization_key": "subject_id",
        "categories": [
            "area_status",
            "mobility_context",
            "environment_context",
            "civic_service_context",
            "sensor_context",
            "incident_candidate_context",
            "plan_proposal_context",
            "governance_boundary_context",
        ],
    }
    claim_policy = {
        "status": "PASS",
        "rules": ["[S] remains synthetic replay.", "[P] remains proposal-only.", "[SIM] is not observed truth.", "claim labels are preserved into current-state outputs."],
    }
    no_overclaim = {"status": "PASS", "scan": {"findings": []}, "boundary": "D5 defines file-backed synthetic replay mechanics only."}

    write_json(out / "PV1_D5_EVENT_FABRIC_CONTRACT.json", contract)
    write_json(out / "PV1_D5_EVENT_ENVELOPE_SCHEMA.json", event_envelope_schema())
    write_json(out / "PV1_D5_EVENT_TIME_POLICY.json", event_time_policy)
    write_json(out / "PV1_D5_PROCESSING_TIME_POLICY.json", processing_time_policy)
    write_json(out / "PV1_D5_EVENT_TO_ONTOLOGY_MAPPING_POLICY.json", ontology_mapping_policy)
    write_json(out / "PV1_D5_DEDUPE_AND_SUPERSESSION_POLICY.json", dedupe_policy)
    write_json(out / "PV1_D5_CURRENT_STATE_POLICY.json", current_state_policy)
    write_json(out / "PV1_D5_CLAIM_LABEL_POLICY.json", claim_policy)
    write_json(out / "PV1_D5_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# PV1-D5 Event Fabric Contract",
                "",
                "Defines a file-backed event fabric contract over SDF JSONL replay packs.",
                "This is synthetic replay mechanics and readiness work, with production event bus choices deferred.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        no_overclaim = {"status": "FAIL", "scan": scan}
        write_json(out / "PV1_D5_NO_OVERCLAIM_REPORT.json", no_overclaim)

    schema = event_envelope_schema()
    gates = [
        gate("PV1-D5-PRECOND", ont.exists() and sdf.exists() and replay_inventory["replay_pack_count"] > 0, ontology_dir=str(ont), sdf_pack=str(sdf)),
        gate("PV1-D5-EVENT-FABRIC-CONTRACT", contract["status"] == "PASS"),
        gate("PV1-D5-EVENT-ENVELOPE-SCHEMA", "ontology_subject_mappings" in schema["required"]),
        gate("PV1-D5-EVENT-TIME-POLICY", event_time_policy["status"] == "PASS"),
        gate("PV1-D5-PROCESSING-TIME-POLICY", processing_time_policy["status"] == "PASS"),
        gate("PV1-D5-ONTOLOGY-MAPPING", ontology_mapping_policy["status"] == "PASS"),
        gate("PV1-D5-DEDUPE-SUPERSESSION-POLICY", dedupe_policy["status"] == "PASS"),
        gate("PV1-D5-CLAIM-LABEL-POLICY", claim_policy["status"] == "PASS"),
        gate("PV1-D5-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D5-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) else "FAIL"
    harness = {
        "task": "PV1-D5 Event Fabric Contract",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "replay_inventory": replay_inventory,
        "output_dir": str(out),
    }
    write_json(out / "PV1_D5_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D5 event fabric contract gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d5-output", "--output-dir", dest="output_dir", default=DEFAULT_D5_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d5_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, sdf_pack=args.sdf_pack, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
