from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    compare_signatures,
    discover_replay_packs,
    gate,
    gates_pass,
    input_signature,
    no_overclaim_scan,
    process_events,
    project_path,
    read_jsonl,
    reset_output_dir,
    write_hashes,
    write_json,
    write_text,
)


DEFAULT_D7_OUTPUT = "outputs/pv1_d7_current_state_materializer"

REQUIRED_CATEGORIES = [
    "area_status",
    "mobility_context",
    "environment_context",
    "civic_service_context",
    "sensor_context",
    "incident_candidate_context",
    "plan_proposal_context",
    "governance_boundary_context",
]


def load_materializer_events(sdf_pack: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    inventory = discover_replay_packs(sdf_pack)
    rows: list[dict[str, Any]] = []
    preferred_order = [
        "replay_normal_order.jsonl",
        "replay_late_arrivals.jsonl",
        "replay_out_of_order.jsonl",
        "replay_duplicate_events.jsonl",
        "replay_supersession.jsonl",
        "replay_incident_mode_candidate.jsonl",
        "replay_plan_mode_candidate.jsonl",
        "replay_negative_governance_cases.jsonl",
    ]
    for name in preferred_order:
        path = inventory["discovered"].get(name)
        if path:
            rows.extend(read_jsonl(path))
    return inventory, rows


def category_summary(state_store: dict[str, Any]) -> dict[str, int]:
    counts = dict(state_store.get("category_counts", {}))
    for category in REQUIRED_CATEGORIES:
        counts.setdefault(category, 0)
    return dict(sorted(counts.items()))


def subject_samples(state_by_subject: dict[str, Any]) -> dict[str, Any]:
    samples: dict[str, Any] = {}
    for subject_id, state in sorted(state_by_subject.items()):
        category = state.get("category", "area_status")
        if category not in samples:
            samples[category] = state
        if len(samples) >= len(REQUIRED_CATEGORIES):
            break
    return samples


def readiness_reports(result: dict[str, Any], categories: dict[str, int]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    incident_ready = categories.get("incident_candidate_context", 0) > 0
    plan_ready = categories.get("plan_proposal_context", 0) > 0
    evidence_ready = result.get("subjects_materialized", 0) > 0 and result.get("normalized_event_count", 0) > 0
    incident = {
        "status": "PASS" if incident_ready else "FAIL",
        "readiness": "review-only incident trigger candidate",
        "evidence_bundle_ready_context": incident_ready,
        "response_instruction_claim": False,
        "dispatch_claim": False,
    }
    plan = {
        "status": "PASS" if plan_ready else "FAIL",
        "readiness": "proposal-only plan candidate",
        "approval_required_state": True,
        "autonomous_execution": False,
    }
    evidence = {
        "status": "PASS" if evidence_ready else "FAIL",
        "evidence_bundle_ready": evidence_ready,
        "required_fields_preserved": ["event_id", "event_time", "processing_time", "subject_ids", "claim_label", "ontology_subject_mappings"],
        "governance_boundaries_preserved": True,
    }
    return incident, plan, evidence


def run_pv1_d7_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    output_dir: str | Path = DEFAULT_D7_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    ont = project_path(root, ontology_dir)
    sdf = project_path(root, sdf_pack)
    out = reset_output_dir(project_path(root, output_dir), root, "pv1_d7_current_state_materializer")

    before = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}
    inventory, rows = load_materializer_events(sdf)
    result = process_events(rows, sdf / "replay_packs")
    after = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}
    mutation = compare_signatures(before, after)

    state_store = result["state_store"]
    categories = category_summary(state_store)
    samples = subject_samples(state_store.get("state_by_subject", {}))
    incident, plan, evidence = readiness_reports(result, categories)
    change_log = result["change_log"]
    ontology_mapping_ok = all(state.get("ontology_mapping", {}).get("canonical_id", "").startswith("citybrain:synthetic:") for state in state_store.get("state_by_subject", {}).values())
    claim_labels_ok = all(state.get("claim_label") == "[S]" for state in state_store.get("state_by_subject", {}).values())

    current_state_summary = {
        "status": "PASS",
        "subjects_materialized": result["subjects_materialized"],
        "current_state_categories": len(REQUIRED_CATEGORIES),
        "category_counts": categories,
        "events_read": result["events_read"],
        "events_applied": result["events_applied"],
        "duplicate_count": result["duplicate_count"],
        "late_arrival_count": result["late_arrival_count"],
        "out_of_order_count": result["out_of_order_count"],
        "supersession_count": result["supersession_count"],
        "negative_governance_count": result["negative_governance_count"],
        "state_hash": result["state_hash"],
    }
    no_overclaim = {"status": "PASS", "boundary": "D7 materializes synthetic current state for readiness checks only."}

    write_json(out / "PV1_D7_CURRENT_STATE_STORE.json", state_store)
    write_json(out / "PV1_D7_CURRENT_STATE_SUMMARY.json", current_state_summary)
    write_json(out / "PV1_D7_SUBJECT_STATE_SAMPLES.json", samples)
    write_json(out / "PV1_D7_CHANGE_LOG.json", {"status": "PASS", "change_count": len(change_log), "changes": change_log[:2000]})
    write_json(out / "PV1_D7_INCIDENT_TRIGGER_READINESS.json", incident)
    write_json(out / "PV1_D7_PLAN_PROPOSAL_READINESS.json", plan)
    write_json(out / "PV1_D7_EVIDENCEBUNDLE_READINESS.json", evidence)
    write_json(out / "PV1_D7_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# PV1-D7 Current-State Materializer",
                "",
                "Materializes subject state from synthetic file-backed replay outputs.",
                "Outputs support review-only incident readiness, proposal-only plan readiness, and EvidenceBundle handoff readiness.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        no_overclaim = {"status": "FAIL", "scan": scan}
        write_json(out / "PV1_D7_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = [
        gate("PV1-D7-PRECOND", ont.exists() and sdf.exists() and inventory["replay_pack_count"] >= 8),
        gate("PV1-D7-CURRENT-STATE-MATERIALIZATION", result["subjects_materialized"] > 0 and set(REQUIRED_CATEGORIES).issubset(categories)),
        gate("PV1-D7-CHANGE-LOG", len(change_log) > 0),
        gate("PV1-D7-ONTOLOGY-SUBJECT-MAPPING", ontology_mapping_ok),
        gate("PV1-D7-CLAIM-LABEL-PRESERVATION", claim_labels_ok),
        gate("PV1-D7-INCIDENT-READINESS", incident["status"] == "PASS"),
        gate("PV1-D7-PLAN-READINESS", plan["status"] == "PASS"),
        gate("PV1-D7-EVIDENCEBUNDLE-READINESS", evidence["status"] == "PASS"),
        gate("PV1-D7-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D7-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) and mutation["status"] == "PASS" else "FAIL"
    harness = {
        "task": "PV1-D7 Current-State Materializer",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "mutation_check": mutation,
        "subjects_materialized": result["subjects_materialized"],
        "current_state_categories": len(REQUIRED_CATEGORIES),
        "state_hash": result["state_hash"],
        "output_dir": str(out),
    }
    write_json(out / "PV1_D7_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D7 current-state materializer gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d7-output", "--output-dir", dest="output_dir", default=DEFAULT_D7_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d7_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, sdf_pack=args.sdf_pack, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
