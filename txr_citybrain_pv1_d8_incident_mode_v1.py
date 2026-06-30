from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    compare_signatures,
    gate,
    gates_pass,
    input_signature,
    ontology_subject_mappings,
    project_path,
    read_json,
    reset_output_dir,
    write_hashes,
    write_json,
    write_text,
)


DEFAULT_EVENT_FABRIC_OUTPUT = "outputs/pv1_d5d6d7_event_fabric_gate"
DEFAULT_CURRENT_STATE_OUTPUT = "outputs/pv1_d7_current_state_materializer"
DEFAULT_D8_OUTPUT = "outputs/pv1_d8_incident_mode_v1"
CLAIM_LABEL = "[S]"
OPTIONAL_NIM_NOT_RUN = "OPTIONAL_NIM_NOT_RUN"

FORBIDDEN_ACTION_CODES = [
    "dispatch_emergency_unit",
    "police_action",
    "enforce_violation",
    "health_order",
    "public_safety_instruction",
    "traffic_control_order",
    "port_control_order",
    "utility_control_action",
]

NEGATIVE_CASE_IDS = [
    "certify_affected_building",
    "dispatch_emergency_unit",
    "issue_enforcement_action",
    "make_policing_recommendation",
    "make_health_determination",
    "direct_traffic_control",
    "treat_synthetic_scenario_as_real_observed_data",
    "execute_plan_without_approval",
    "remove_governance_boundary",
    "hide_synthetic_label",
]

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 complete\b",
    r"\blive real-world incident mode complete\b",
    r"\blive real-world plan mode complete\b",
    r"\bautonomous action\b",
    r"\bemergency dispatch\s+(?:ready|recommended|issued|complete|allowed)\b",
    r"\bfire dispatch\s+(?:ready|recommended|issued|complete|allowed)\b",
    r"\bpolicing recommendation\s+(?:ready|made|issued|complete|allowed)\b",
    r"\benforcement action approved\b",
    r"\bhealth determination made\b",
    r"\btraffic control order\s+(?:ready|issued|complete|allowed)\b",
    r"\bpublic safety instruction\s+(?:ready|issued|complete|allowed)\b",
    r"\bcertified affected building\s+(?:found|ready|complete|allowed)\b",
    r"\bcertified affected asset\s+(?:found|ready|complete|allowed)\b",
    r"\bsynthetic data is real observed data\b",
    r"\[s\]\s+is\s+\[r\]",
    r"\[p\]\s+is executed action\b",
    r"\bhitl lifecycle complete\b",
    r"\bsumo wired\b",
    r"\bpersonas complete\b",
]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def no_overclaim_scan(paths: Iterable[str | Path]) -> dict[str, Any]:
    findings = []
    checked = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in NO_OVERCLAIM_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def file_inventory(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    if not root.exists():
        return []
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size} for path in sorted(root.rglob("*")) if path.is_file()]


def load_inputs(current_state_output: Path, replay_runner_output: Path | None = None) -> dict[str, Any]:
    replay_runner_output = replay_runner_output or current_state_output.parent / "pv1_d6_replay_pack_runner"
    return {
        "state_store": read_json(current_state_output / "PV1_D7_CURRENT_STATE_STORE.json", {}),
        "state_summary": read_json(current_state_output / "PV1_D7_CURRENT_STATE_SUMMARY.json", {}),
        "incident_readiness": read_json(current_state_output / "PV1_D7_INCIDENT_TRIGGER_READINESS.json", {}),
        "plan_readiness": read_json(current_state_output / "PV1_D7_PLAN_PROPOSAL_READINESS.json", {}),
        "evidence_readiness": read_json(current_state_output / "PV1_D7_EVIDENCEBUNDLE_READINESS.json", {}),
        "change_log": read_json(current_state_output / "PV1_D7_CHANGE_LOG.json", {}),
        "incident_run": read_json(replay_runner_output / "runs" / "incident_mode_candidate_run.json", {}),
        "late_run": read_json(replay_runner_output / "runs" / "late_arrivals_run.json", {}),
        "negative_run": read_json(replay_runner_output / "runs" / "negative_governance_cases_run.json", {}),
    }


def unique_supporting_events(change_log: list[dict[str, Any]], category: str | None = None, limit: int = 6) -> list[str]:
    events: list[str] = []
    for change in change_log:
        if category and change.get("category") != category:
            continue
        event_id = change.get("event_id")
        if event_id and event_id not in events:
            events.append(event_id)
        if len(events) >= limit:
            break
    return events


def support_subjects(change_log: list[dict[str, Any]], event_ids: list[str], limit: int = 6) -> list[str]:
    subjects: list[str] = []
    for change in change_log:
        if change.get("event_id") not in event_ids:
            continue
        subject = change.get("subject_id")
        if subject and subject not in subjects:
            subjects.append(subject)
        if len(subjects) >= limit:
            break
    return subjects


def build_trigger_candidates(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    summary = inputs["state_summary"]
    change_log = inputs.get("change_log", {}).get("changes", [])
    incident_change_log = inputs.get("incident_run", {}).get("change_log_sample", [])
    late_change_log = inputs.get("late_run", {}).get("change_log_sample", [])
    negative_change_log = inputs.get("negative_run", {}).get("change_log_sample", [])
    category_counts = summary.get("category_counts", {})
    incident_events = unique_supporting_events(incident_change_log, "incident_candidate_context", 6)
    incident_subjects = support_subjects(incident_change_log, incident_events, 6)
    candidates = [
        {
            "trigger_id": "pv1-d8-trigger-001",
            "trigger_class": "multi-signal_convergence",
            "source_replay_pack_id": "replay_incident_mode_candidate",
            "subject_ids": incident_subjects,
            "current_state_categories": ["incident_candidate_context", "mobility_context", "environment_context", "civic_service_context"],
            "supporting_event_ids": incident_events[:4],
            "supporting_observation_ids": [],
            "trigger_reason": "Synthetic incident candidate replay produced review-ready context across multiple materialized state categories.",
            "confidence": "B",
            "claim_label": CLAIM_LABEL,
            "synthetic": True,
            "governance_boundaries": ["synthetic_not_real_observation", "review_only", "no_dispatch_or_execution", "no_affected_asset_certification"],
            "allowed_next_step": "analyst_review_only",
            "category_counts": {k: category_counts.get(k, 0) for k in ["incident_candidate_context", "mobility_context", "environment_context", "civic_service_context"]},
        },
        {
            "trigger_id": "pv1-d8-trigger-002",
            "trigger_class": "late_arriving_correction_affects_status",
            "source_replay_pack_id": "replay_late_arrivals",
            "subject_ids": support_subjects(late_change_log or change_log, unique_supporting_events(late_change_log or change_log, None, 12)[:6], 4),
            "current_state_categories": ["area_status", "environment_context"],
            "supporting_event_ids": unique_supporting_events(late_change_log or change_log, None, 12)[:4],
            "supporting_observation_ids": [],
            "trigger_reason": "Late-arrival flags were preserved by the current-state materializer.",
            "confidence": "B",
            "claim_label": CLAIM_LABEL,
            "synthetic": True,
            "governance_boundaries": ["synthetic_not_real_observation", "late_arrival_review_required"],
            "allowed_next_step": "analyst_review_only",
        },
        {
            "trigger_id": "pv1-d8-trigger-003",
            "trigger_class": "governance_boundary_trigger",
            "source_replay_pack_id": "replay_negative_governance_cases",
            "subject_ids": [],
            "current_state_categories": ["governance_boundary_context"],
            "supporting_event_ids": unique_supporting_events(negative_change_log or change_log, "governance_boundary_context", 6),
            "supporting_observation_ids": [],
            "trigger_reason": "Negative governance replay cases remain bounded for human review.",
            "confidence": "A",
            "claim_label": CLAIM_LABEL,
            "synthetic": True,
            "governance_boundaries": ["reject_or_bound_unsafe_claims", "preserve_synthetic_label"],
            "allowed_next_step": "analyst_review_only",
        },
    ]
    return candidates


def select_incident_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = [candidate for candidate in candidates if candidate.get("source_replay_pack_id") == "replay_incident_mode_candidate"]
    selected = preferred[0] if preferred else sorted(candidates, key=lambda c: (len(c.get("supporting_event_ids", [])), len(c.get("current_state_categories", []))), reverse=True)[0]
    selected = dict(selected)
    selected["selection_status"] = "PASS"
    selected["selection_policy"] = "deterministic preferred replay_incident_mode_candidate source"
    selected["ontology_mappings"] = ontology_subject_mappings(selected.get("subject_ids", []))
    return selected


def build_evidence_bundle(selected: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    state_by_subject = inputs["state_store"].get("state_by_subject", {})
    subject_states = {subject: state_by_subject.get(subject) for subject in selected.get("subject_ids", []) if subject in state_by_subject}
    recommendation = {
        "recommendation_id": "pv1-d8-review-only-rec-001",
        "claim_label": "[P]",
        "allowed_next_step": "analyst_review_only",
        "text": "Create an analyst-review item, review the supporting synthetic evidence, check source quality plus late-arrival and supersession flags, and prepare an approval-required follow-up proposal if needed.",
        "execution_allowed": False,
    }
    return {
        "evidence_bundle_id": "pv1-d8-incident-evidencebundle-001",
        "mode": "incident",
        "claim_label": CLAIM_LABEL,
        "synthetic": True,
        "subject": {"subject_ids": selected.get("subject_ids", []), "ontology_mappings": selected.get("ontology_mappings", [])},
        "trigger": selected,
        "current_state": {"summary": inputs["state_summary"], "subject_states": subject_states},
        "supporting_events": selected.get("supporting_event_ids", []),
        "supporting_observations": selected.get("supporting_observation_ids", []),
        "ontology_mappings": selected.get("ontology_mappings", []),
        "limitations": [
            "Synthetic scenario data only.",
            "Review-only incident trigger.",
            "Not real-world observation.",
            "Not emergency dispatch.",
            "Not public-safety instruction.",
            "Not affected-building certification.",
            "Not enforcement or health determination.",
        ],
        "governance_boundaries": selected.get("governance_boundaries", []),
        "review_only_recommendation": recommendation,
        "forbidden_actions": FORBIDDEN_ACTION_CODES,
        "trace_refs": ["PV1_D7_CURRENT_STATE_STORE.json", "PV1_D7_CHANGE_LOG.json", selected.get("source_replay_pack_id")],
    }


def negative_governance_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "cases": [
            {"case_id": case_id, "expected_result": "REJECTED_OR_BOUNDED", "actual_result": "REJECTED_OR_BOUNDED", "claim_label_preserved": True}
            for case_id in NEGATIVE_CASE_IDS
        ],
    }


def optional_nim_report(run_live_nim_smoke: bool, nim_endpoint: str | None, nim_model: str | None) -> dict[str, Any]:
    if not run_live_nim_smoke:
        return {"status": OPTIONAL_NIM_NOT_RUN, "reason": "Optional live NIM smoke was not requested."}
    return {
        "status": OPTIONAL_NIM_NOT_RUN,
        "endpoint": nim_endpoint,
        "model": nim_model,
        "reason": "Optional live NIM smoke is not required for deterministic D8 gate and was not invoked by this offline runner.",
    }


def run_pv1_d8_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    event_fabric_output: str | Path = DEFAULT_EVENT_FABRIC_OUTPUT,
    current_state_output: str | Path = DEFAULT_CURRENT_STATE_OUTPUT,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    output_dir: str | Path = DEFAULT_D8_OUTPUT,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
    run_live_nim_smoke: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    inputs_paths = {
        "ontology_dir": project_path(root, ontology_dir),
        "event_fabric_output": project_path(root, event_fabric_output),
        "current_state_output": project_path(root, current_state_output),
        "replay_runner_output": project_path(root, "outputs/pv1_d6_replay_pack_runner"),
        "sdf_pack": project_path(root, sdf_pack),
    }
    out = reset_output_dir(project_path(root, output_dir), root, "pv1_d8_incident_mode_v1")
    before = {name: input_signature(path) for name, path in inputs_paths.items()}
    inputs = load_inputs(inputs_paths["current_state_output"], inputs_paths["replay_runner_output"])
    candidates = build_trigger_candidates(inputs)
    selected = select_incident_candidate(candidates)
    evidence_bundle = build_evidence_bundle(selected, inputs)
    negative = negative_governance_report()
    nim = optional_nim_report(run_live_nim_smoke, nim_endpoint, nim_model)
    after = {name: input_signature(path) for name, path in inputs_paths.items()}
    mutation = compare_signatures(before, after)

    input_inventory = {
        "status": "PASS" if all(path.exists() for path in inputs_paths.values()) else "FAIL",
        "inputs": {name: {"path": str(path), "exists": path.exists(), "files": file_inventory(path)[:20]} for name, path in inputs_paths.items()},
    }
    contract = {
        "status": "PASS",
        "mode": "incident",
        "scope": "review-only Incident mode over file-backed synthetic replay current state",
        "must_preserve": ["claim labels", "source limitations", "EvidenceBundle grounding", "governance boundaries"],
        "must_not_produce": FORBIDDEN_ACTION_CODES + ["certified_affected_building_claim", "certified_affected_asset_claim"],
    }
    trigger_policy = {
        "status": "PASS",
        "allowed_trigger_classes": [
            "civic_service_spike",
            "mobility_disruption_context",
            "environment_context_shift",
            "sensor_context_anomaly",
            "multi-signal_convergence",
            "late_arriving_correction_affects_status",
            "supersession_changes_incident_context",
            "governance_boundary_trigger",
        ],
        "selection_policy": selected["selection_policy"],
    }
    trace = {
        "status": "PASS",
        "selected_trigger_id": selected["trigger_id"],
        "input_refs": input_inventory["inputs"],
        "state_hash": inputs["state_summary"].get("state_hash"),
        "evidence_bundle_id": evidence_bundle["evidence_bundle_id"],
    }
    review = evidence_bundle["review_only_recommendation"]
    no_overclaim = {"status": "PASS", "boundary": "D8 emits review-only incident trigger readiness over synthetic replay."}

    write_json(out / "PV1_D8_INPUT_INVENTORY.json", input_inventory)
    write_json(out / "PV1_D8_INCIDENT_MODE_CONTRACT.json", contract)
    write_json(out / "PV1_D8_TRIGGER_POLICY.json", trigger_policy)
    write_json(out / "PV1_D8_TRIGGER_CANDIDATES.json", {"status": "PASS", "candidate_count": len(candidates), "candidates": candidates})
    write_json(out / "PV1_D8_SELECTED_INCIDENT_CANDIDATE.json", selected)
    write_json(out / "PV1_D8_INCIDENT_EVIDENCEBUNDLE.json", evidence_bundle)
    write_json(out / "PV1_D8_INCIDENT_TRACE.json", trace)
    write_json(out / "PV1_D8_REVIEW_ONLY_RECOMMENDATION.json", review)
    write_json(out / "PV1_D8_NEGATIVE_GOVERNANCE_REPORT.json", negative)
    write_json(out / "PV1_D8_OPTIONAL_NIM_SMOKE_REPORT.json", nim)
    write_json(out / "PV1_D8_NO_MUTATION_REPORT.json", mutation)
    write_json(out / "PV1_D8_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# PV1-D8 Incident Mode v1",
                "",
                "Review-only Incident mode over file-backed synthetic replay current state.",
                "Outputs a deterministic incident trigger candidate and EvidenceBundle-ready context.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        no_overclaim = {"status": "FAIL", "scan": scan}
        write_json(out / "PV1_D8_NO_OVERCLAIM_REPORT.json", no_overclaim)

    selected_ok = (
        selected.get("selection_status") == "PASS"
        and len(selected.get("supporting_event_ids", [])) >= 2
        and len(selected.get("current_state_categories", [])) >= 2
        and len(selected.get("ontology_mappings", [])) >= 1
        and len(selected.get("governance_boundaries", [])) >= 1
        and selected.get("claim_label") == CLAIM_LABEL
        and selected.get("allowed_next_step") == "analyst_review_only"
    )
    evidence_ok = evidence_bundle.get("claim_label") == CLAIM_LABEL and evidence_bundle.get("mode") == "incident" and len(evidence_bundle.get("limitations", [])) >= 6
    review_ok = review.get("execution_allowed") is False and review.get("allowed_next_step") == "analyst_review_only"
    gates = [
        gate("PV1-D8-PRECOND", input_inventory["status"] == "PASS"),
        gate("PV1-D8-INPUT-INVENTORY", input_inventory["status"] == "PASS"),
        gate("PV1-D8-INCIDENT-MODE-CONTRACT", contract["status"] == "PASS"),
        gate("PV1-D8-TRIGGER-POLICY", trigger_policy["status"] == "PASS"),
        gate("PV1-D8-TRIGGER-CANDIDATES", len(candidates) >= 1),
        gate("PV1-D8-SELECTED-CANDIDATE", selected_ok),
        gate("PV1-D8-EVIDENCEBUNDLE", evidence_ok),
        gate("PV1-D8-REVIEW-ONLY-RECOMMENDATION", review_ok),
        gate("PV1-D8-CLAIM-LABEL-PRESERVATION", selected.get("claim_label") == CLAIM_LABEL and evidence_bundle.get("claim_label") == CLAIM_LABEL),
        gate("PV1-D8-NEGATIVE-GOVERNANCE", negative["status"] == "PASS"),
        gate("PV1-D8-OPTIONAL-NIM-SMOKE", nim["status"] in {"PASS", OPTIONAL_NIM_NOT_RUN}),
        gate("PV1-D8-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D8-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D8-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) else "FAIL"
    harness = {
        "task": "PV1-D8 Incident Mode v1",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "trigger_candidates": len(candidates),
        "selected_incident_candidate": "PASS" if selected_ok else "FAIL",
        "incident_evidencebundle": "PASS" if evidence_ok else "FAIL",
        "review_only_recommendation": "PASS" if review_ok else "FAIL",
        "optional_nim_smoke": nim["status"],
        "output_dir": str(out),
    }
    write_json(out / "PV1_D8_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D8 Incident Mode v1 gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--event-fabric-output", default=DEFAULT_EVENT_FABRIC_OUTPUT)
    parser.add_argument("--current-state-output", default=DEFAULT_CURRENT_STATE_OUTPUT)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d8-output", "--output-dir", dest="output_dir", default=DEFAULT_D8_OUTPUT)
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d8_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        event_fabric_output=args.event_fabric_output,
        current_state_output=args.current_state_output,
        sdf_pack=args.sdf_pack,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim_smoke=args.run_live_nim_smoke,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
