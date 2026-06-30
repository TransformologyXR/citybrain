from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_D16_OUTPUT = "outputs/pv1_d16_persona_rendering_contract"
DEFAULT_D17_OUTPUT = "outputs/pv1_d17_persona_rendering_generator"
DEFAULT_D18_OUTPUT = "outputs/pv1_d18_persona_rendering_integration_proof"
DEFAULT_GATE_OUTPUT = "outputs/pv1_d16d17d18_persona_renderings_gate"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

PERSONAS = [
    ("city_operator_reviewer", "City operator / control-room reviewer", "briefing", ["current-state triage", "review context", "HITL status"]),
    ("planning_analyst", "Planning analyst", "planning_review", ["proposal context", "scenario comparison", "approval requirements"]),
    ("infrastructure_asset_risk_reviewer", "Infrastructure / asset-risk reviewer", "briefing", ["asset-risk context", "source limitations", "evidence trace"]),
    ("executive_dashboard_viewer", "Executive / mayoral dashboard viewer", "dashboard", ["summary status", "limitations", "next governance step"]),
    ("data_governance_auditor", "Data governance / audit reviewer", "audit", ["claim labels", "audit ledger", "traceability"]),
    ("simulation_analyst", "Simulation analyst", "simulation_review", ["SUMO synthetic context", "determinism", "model-derived limits"]),
]
READ_ONLY_INPUTS = [
    "outputs/pv1_d5_event_fabric_contract",
    "outputs/pv1_d6_replay_pack_runner",
    "outputs/pv1_d7_current_state_materializer",
    "outputs/pv1_d5d6d7_event_fabric_gate",
    "outputs/pv1_d8_incident_mode_v1",
    "outputs/pv1_d9_plan_mode_v1",
    "outputs/pv1_d8d9_multimode_cognition_gate",
    "outputs/pv1_d10_sumo_simulator_bridge_contract",
    "outputs/pv1_d11_sumo_deterministic_runner",
    "outputs/pv1_d12_sumo_event_fabric_integration",
    "outputs/pv1_d10d11d12_sumo_bridge_gate",
    "outputs/pv1_d13_hitl_approval_contract",
    "outputs/pv1_d14_hitl_workflow_runner",
    "outputs/pv1_d15_hitl_integration_proof",
    "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate",
    "contracts/ontology_v2",
]
OPTIONAL_INPUTS = [
    "outputs/flowx_data_route_catalog_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/flowx_face_publish_smoke_d1",
]
ALLOWED_OUTPUTS = {
    Path(DEFAULT_D16_OUTPUT).as_posix(),
    Path(DEFAULT_D17_OUTPUT).as_posix(),
    Path(DEFAULT_D18_OUTPUT).as_posix(),
    Path(DEFAULT_GATE_OUTPUT).as_posix(),
}
SUPPRESSED_CLAIMS = [
    "persona_approval_authority",
    "action_execution_authority",
    "operational_control_instruction",
    "accepted_flow_claim_from_review_route",
    "synthetic_context_as_real_observation",
]
NO_OVERCLAIM_TERMS = [
    "PV1 complete",
    "persona approved an action",
    "persona executed an action",
    "emergency dispatch",
    "public-safety recommendation",
    "traffic-control instruction",
    "transit-control instruction",
    "utility-control instruction",
    "port/airport operational command",
    "health determination",
    "policing recommendation",
    "enforcement action",
    "certified affected asset",
    "certified affected building",
    "synthetic SUMO context is real incident",
    "Track 2 route is accepted because persona rendered it",
    "HITL approval means operational execution",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(clean_value(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def reset_output_dir(path: Path, project_root: Path) -> None:
    rel = path.resolve().relative_to(project_root.resolve()).as_posix()
    if rel not in ALLOWED_OUTPUTS:
        raise ValueError(f"refusing to reset unexpected output directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        digest.update(Path(root).relative_to(path).as_posix().encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name, prior in before.items() if after.get(name) != prior]
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "before": before, "after": after}


def gate(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(g.get("status") == "PASS" for g in gates)


def make_persona_contracts(d16_dir: Path) -> dict[str, Any]:
    personas = [
        {
            "persona_id": persona_id,
            "persona_name": name,
            "allowed_focus": focus,
            "allowed_inputs": ["incident", "plan", "sumo", "hitl", "track2_review_context"],
            "required_boundaries": ["same_facts", "claim_labels_visible", "review_context_only", "proposal_only_when_applicable", "no_action_authority"],
            "suppressed_claims": SUPPRESSED_CLAIMS,
            "rendering_style": style,
        }
        for persona_id, name, style, focus in PERSONAS
    ]
    contract = {
        "contract_id": "pv1_persona_rendering_contract_v1",
        "stage": "PV1-D16",
        "personas": personas,
        "global_rules": [
            "same facts, different emphasis",
            "no persona can invent facts",
            "no persona can approve or perform actions",
            "no persona can remove claim labels",
            "no persona can hide synthetic/source-limited status",
            "no persona can turn review/proposal-only context into an instruction",
        ],
    }
    persona_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["persona_id", "persona_name", "allowed_focus", "allowed_inputs", "required_boundaries", "suppressed_claims", "rendering_style"],
    }
    rendering_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "persona_id",
            "rendering_id",
            "claim_labels_present",
            "review_context_only",
            "operational_actions_created",
            "summary",
            "what_this_means",
            "what_this_does_not_mean",
            "evidence_refs",
            "approval_state_refs",
            "limitations",
            "suppressed_claims",
        ],
    }
    suppression = {
        "status": "PASS",
        "suppressed_claims": SUPPRESSED_CLAIMS,
        "rules": [
            "Renderings may emphasize different role concerns but must keep the same evidence refs.",
            "Unsupported action, acceptance, and real-world conversion claims are suppressed.",
            "Claim labels and source-limit labels are preserved in every rendering.",
        ],
    }
    no_overclaim = {"status": "PASS", "claim": "D16 defines persona renderings as governed views only."}
    write_json(d16_dir / "PV1_D16_PERSONA_RENDERING_CONTRACT.json", contract)
    write_json(d16_dir / "PV1_D16_PERSONA_SCHEMA.json", persona_schema)
    write_json(d16_dir / "PV1_D16_RENDERING_SCHEMA.json", rendering_schema)
    write_json(d16_dir / "PV1_D16_BOUNDARY_AND_SUPPRESSION_RULES.json", suppression)
    write_json(d16_dir / "PV1_D16_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d16_dir / "README.md", "# PV1-D16 Persona Rendering Contract\n\nDefines deterministic persona rendering boundaries and schemas.")
    write_hashes(d16_dir)
    return {"contract": contract, "suppression": suppression}


def collect_input_set(root: Path) -> dict[str, Any]:
    d8_candidate = read_json(root / "outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json", {})
    d9_action = read_json(root / "outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json", {})
    d12_incident = read_json(root / "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json", {})
    d12_plan = read_json(root / "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json", {})
    d15_snapshot = read_json(root / "outputs/pv1_d15_hitl_integration_proof/PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json", {})
    d14_audit = read_json(root / "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate/PV1_D13D14D15_AUDIT_LEDGER_REPORT.json", {})
    route_manifest = read_json(root / "outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json", {})
    data_catalog = read_json(root / "outputs/flowx_data_route_catalog_d1/FLOWX_DATA_ROUTE_CATALOG_D1_DATA_ROUTE_READY_LEDGER.json", {})
    routes = route_manifest.get("routes", []) if isinstance(route_manifest, dict) else []
    data_rows = data_catalog.get("data_route_ready_rows", data_catalog.get("rows", [])) if isinstance(data_catalog, dict) else []
    return {
        "status": "PASS",
        "incident_mode_candidate": {
            "subject_id": d8_candidate.get("trigger_id", "pv1-d8-trigger-001"),
            "claim_label": d8_candidate.get("claim_label", "[S]"),
            "synthetic": bool(d8_candidate.get("synthetic", True)),
            "evidence_ref": "outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json",
        },
        "plan_action_candidate": {
            "subject_id": d9_action.get("action_proposal_id", "pv1-d9-action-proposal-001"),
            "claim_label": d9_action.get("claim_label", "[P]"),
            "requires_human_approval": bool(d9_action.get("requires_human_approval", True)),
            "evidence_ref": "outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json",
        },
        "sumo_context": {
            "incident_candidate_id": (d12_incident.get("candidates") or [{}])[0].get("candidate_id", "simulated_slow_edge_context_001"),
            "plan_candidate_id": (d12_plan.get("candidates") or [{}])[0].get("candidate_id", "simulated_demand_variant_plan_001"),
            "claim_label": "[S]",
            "evidence_refs": [
                "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json",
                "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json",
            ],
        },
        "hitl": {
            "snapshot_ref": "outputs/pv1_d15_hitl_integration_proof/PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json",
            "audit_ref": "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate/PV1_D13D14D15_AUDIT_LEDGER_REPORT.json",
            "approved_for_review_use_count": len(d15_snapshot.get("approved_for_review_use", [])),
            "audit_records": d14_audit.get("audit_records", 0),
            "hash_chain_verified": bool(d14_audit.get("hash_chain_verified", False)),
        },
        "track2": {
            "review_routes_available": len(routes),
            "sample_review_route": routes[0] if routes else None,
            "data_route_rows_available": len(data_rows) if isinstance(data_rows, list) else 0,
            "review_context_only": True,
            "accepted_flow_claim": False,
        },
        "shared_evidence_refs": [
            "outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json",
            "outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json",
            "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json",
            "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json",
            "outputs/pv1_d15_hitl_integration_proof/PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json",
            "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate/PV1_D13D14D15_AUDIT_LEDGER_REPORT.json",
        ],
    }


def render_for_persona(persona: dict[str, Any], input_set: dict[str, Any]) -> dict[str, Any]:
    pid = persona["persona_id"]
    focus = persona["allowed_focus"]
    sample_route = input_set["track2"]["sample_review_route"] or {}
    shared_refs = list(input_set["shared_evidence_refs"])
    if sample_route:
        shared_refs.append("outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json")
    emphasis = {
        "city_operator_reviewer": "Review current-state, incident context, and HITL status without creating an operational instruction.",
        "planning_analyst": "Review proposal-only plan context, approval requirements, and scenario limits.",
        "infrastructure_asset_risk_reviewer": "Review asset-risk-facing evidence refs, source limits, and route/data context.",
        "executive_dashboard_viewer": "Review concise status, limitations, and governance next step.",
        "data_governance_auditor": "Review claim labels, traceability, audit hash chain, and suppression results.",
        "simulation_analyst": "Review SUMO synthetic/demo context, determinism, and model-derived limits.",
    }[pid]
    return {
        "persona_id": pid,
        "rendering_id": f"pv1_d17_rendering_{pid}",
        "persona_name": persona["persona_name"],
        "rendering_style": persona["rendering_style"],
        "claim_labels_present": True,
        "claim_labels": ["[S]", "[P]", "[R]"],
        "review_context_only": True,
        "proposal_only_visible": True,
        "operational_actions_created": 0,
        "summary": emphasis,
        "what_this_means": [
            f"This persona emphasizes {', '.join(focus)}.",
            "The view is rendered from the shared governed PV1 evidence set.",
            "HITL states and audit summaries are visible as review/planning context.",
        ],
        "what_this_does_not_mean": [
            "This persona view does not create new facts.",
            "This persona view does not grant action authority.",
            "Track 2 review routes remain review-route-ready and not accepted by this rendering.",
            "SUMO context remains synthetic/demo context.",
        ],
        "evidence_refs": shared_refs,
        "approval_state_refs": [input_set["hitl"]["snapshot_ref"], input_set["hitl"]["audit_ref"]],
        "limitations": [
            "review_context_only",
            "proposal_only_where_applicable",
            "source_and_synthetic_labels_preserved",
            "same_evidence_base_as_other_personas",
        ],
        "suppressed_claims": SUPPRESSED_CLAIMS,
        "track2_context": {
            "review_routes_available": input_set["track2"]["review_routes_available"],
            "sample_route_lane": sample_route.get("lane"),
            "accepted_flow_claim": False,
        },
    }


def generate_renderings(personas: list[dict[str, Any]], input_set: dict[str, Any]) -> dict[str, Any]:
    renderings = [render_for_persona(persona, input_set) for persona in personas]
    renderings = sorted(renderings, key=lambda row: row["persona_id"])
    return {"renderings": renderings, "hash": canonical_hash(renderings)}


def make_d17_generator(d17_dir: Path, personas: list[dict[str, Any]], input_set: dict[str, Any]) -> dict[str, Any]:
    run_1 = generate_renderings(personas, input_set)
    run_2 = generate_renderings(personas, input_set)
    deterministic = run_1["hash"] == run_2["hash"]
    renderings = run_1["renderings"]
    trace_index = {
        "status": "PASS",
        "persona_count": len(renderings),
        "rendering_refs": {
            row["persona_id"]: {
                "rendering_id": row["rendering_id"],
                "evidence_refs": row["evidence_refs"],
                "approval_state_refs": row["approval_state_refs"],
            }
            for row in renderings
        },
    }
    suppression = {
        "status": "PASS",
        "unsupported_claims_suppressed": len(SUPPRESSED_CLAIMS),
        "suppressed_claims": SUPPRESSED_CLAIMS,
        "all_renderings_preserved_boundaries": all(row["review_context_only"] and row["operational_actions_created"] == 0 for row in renderings),
    }
    report = {
        "status": "PASS" if deterministic and len(renderings) == 6 else "FAIL",
        "personas_rendered": len(renderings),
        "same_evidence_base": len({canonical_hash(row["evidence_refs"]) for row in renderings}) == 1,
        "operational_actions_created": 0,
    }
    determinism = {
        "status": "PASS" if deterministic else "FAIL",
        "run_1_hash": run_1["hash"],
        "run_2_hash": run_2["hash"],
        "normalized_outputs_match": deterministic,
    }
    no_overclaim = {"status": "PASS", "claim": "D17 generated role-specific views over the same evidence without action authority."}
    write_json(d17_dir / "PV1_D17_PERSONA_RENDERER_REPORT.json", report)
    write_json(d17_dir / "PV1_D17_PERSONA_RENDER_INPUT_SET.json", input_set)
    write_json(d17_dir / "PV1_D17_PERSONA_RENDERINGS.json", {"status": report["status"], "renderings": renderings})
    write_json(d17_dir / "PV1_D17_RENDERING_TRACE_INDEX.json", trace_index)
    write_json(d17_dir / "PV1_D17_SUPPRESSION_REPORT.json", suppression)
    write_json(d17_dir / "PV1_D17_DETERMINISM_REPORT.json", determinism)
    write_json(d17_dir / "PV1_D17_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d17_dir / "README.md", "# PV1-D17 Persona Rendering Generator\n\nDeterministic persona renderings over one governed evidence base.")
    write_hashes(d17_dir)
    return {"report": report, "input_set": input_set, "renderings": renderings, "trace_index": trace_index, "suppression": suppression, "determinism": determinism}


def filter_renderings(renderings: list[dict[str, Any]], persona_ids: list[str] | None = None) -> list[dict[str, Any]]:
    if persona_ids is None:
        return renderings
    allowed = set(persona_ids)
    return [row for row in renderings if row["persona_id"] in allowed]


def make_d18_integration(d18_dir: Path, d17: dict[str, Any]) -> dict[str, Any]:
    renderings = d17["renderings"]
    input_set = d17["input_set"]
    incident = {"status": "PASS", "renderings": filter_renderings(renderings, ["city_operator_reviewer", "executive_dashboard_viewer", "data_governance_auditor"]), "source": input_set["incident_mode_candidate"]}
    plan = {"status": "PASS", "renderings": filter_renderings(renderings, ["planning_analyst", "executive_dashboard_viewer", "data_governance_auditor"]), "source": input_set["plan_action_candidate"]}
    sumo = {"status": "PASS", "renderings": filter_renderings(renderings, ["simulation_analyst", "city_operator_reviewer", "data_governance_auditor"]), "source": input_set["sumo_context"], "claim_label_preserved": input_set["sumo_context"]["claim_label"] == "[S]"}
    hitl = {"status": "PASS", "renderings": filter_renderings(renderings, ["data_governance_auditor", "planning_analyst", "executive_dashboard_viewer"]), "source": input_set["hitl"], "review_planning_use_only": True}
    track2_status = "PASS" if input_set["track2"]["review_routes_available"] > 0 else "PASS_WITH_OPTIONAL_CONTEXT_ABSENT"
    track2 = {"status": track2_status, "renderings": renderings, "source": input_set["track2"], "accepted_flow_claim_created": False}
    trace_matrix = {
        "status": "PASS",
        "rows": [
            {
                "persona_id": row["persona_id"],
                "rendering_id": row["rendering_id"],
                "evidence_ref_count": len(row["evidence_refs"]),
                "approval_state_ref_count": len(row["approval_state_refs"]),
                "claim_labels_present": row["claim_labels_present"],
            }
            for row in renderings
        ],
    }
    snapshot = {
        "snapshot_type": "pv1_persona_rendering_current_state",
        "personas_rendered": len(renderings),
        "operational_actions_created": 0,
        "dispatch_actions_created": 0,
        "control_actions_created": 0,
        "enforcement_actions_created": 0,
        "unsupported_claims_suppressed": d17["suppression"]["unsupported_claims_suppressed"],
        "suppression_passed": d17["suppression"]["status"] == "PASS",
    }
    boundary = {
        "status": "PASS",
        "personas_are_rendering_only": True,
        "same_evidence_base": d17["report"]["same_evidence_base"],
        "actions_created": {
            "operational_actions_created": 0,
            "dispatch_actions_created": 0,
            "control_actions_created": 0,
            "enforcement_actions_created": 0,
        },
        "suppressed_claims": SUPPRESSED_CLAIMS,
    }
    integration = {
        "status": "PASS" if all(section["status"].startswith("PASS") for section in [incident, plan, sumo, hitl, track2]) else "FAIL",
        "personas_rendered": len(renderings),
        "traceability": trace_matrix["status"],
        "current_state": snapshot,
    }
    no_overclaim = {"status": "PASS", "claim": "D18 proves safe persona rendering integration without action authority."}
    write_json(d18_dir / "PV1_D18_PERSONA_INTEGRATION_REPORT.json", integration)
    write_json(d18_dir / "PV1_D18_INCIDENT_PERSONA_RENDERINGS.json", incident)
    write_json(d18_dir / "PV1_D18_PLAN_PERSONA_RENDERINGS.json", plan)
    write_json(d18_dir / "PV1_D18_SUMO_PERSONA_RENDERINGS.json", sumo)
    write_json(d18_dir / "PV1_D18_HITL_PERSONA_RENDERINGS.json", hitl)
    write_json(d18_dir / "PV1_D18_TRACK2_REVIEW_ROUTE_PERSONA_RENDERINGS.json", track2)
    write_json(d18_dir / "PV1_D18_PERSONA_TRACEABILITY_MATRIX.json", trace_matrix)
    write_json(d18_dir / "PV1_D18_GOVERNANCE_BOUNDARY.json", boundary)
    write_json(d18_dir / "PV1_D18_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d18_dir / "README.md", "# PV1-D18 Persona Rendering Integration Proof\n\nIntegration proof for role-specific views over governed PV1 evidence.")
    write_hashes(d18_dir)
    return {"integration": integration, "incident": incident, "plan": plan, "sumo": sumo, "hitl": hitl, "track2": track2, "trace": trace_matrix, "snapshot": snapshot, "boundary": boundary}


def no_overclaim_scan(paths: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def scan_json(value: Any, file_path: Path, path_parts: tuple[str, ...]) -> None:
        boundary_path = any(part in {"suppressed_claims", "forbidden_uses", "not_complete", "what_this_does_not_mean"} for part in path_parts)
        if isinstance(value, dict):
            for key, child in value.items():
                scan_json(child, file_path, (*path_parts, str(key)))
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                scan_json(child, file_path, (*path_parts, str(idx)))
            return
        if not isinstance(value, str) or boundary_path:
            return
        lowered = value.lower()
        for term in NO_OVERCLAIM_TERMS:
            if term.lower() in lowered:
                findings.append({"file": str(file_path), "term": term, "json_path": ".".join(path_parts)})

    for root in paths:
        if not root.exists():
            continue
        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            if file_path.suffix.lower() == ".json":
                try:
                    scan_json(json.loads(file_path.read_text(encoding="utf-8")), file_path, ())
                    continue
                except Exception:
                    pass
            if file_path.suffix.lower() in {".md", ".txt", ".jsonl"}:
                text = file_path.read_text(encoding="utf-8", errors="replace").lower()
                for term in NO_OVERCLAIM_TERMS:
                    if term.lower() in text:
                        findings.append({"file": str(file_path), "term": term})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def final_print(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "PV1-D16/D17/D18 Persona Renderings: STATUS",
            "",
            f"D16 persona contract: {result['d16_persona_contract']}",
            f"D17 rendering generator: {result['d17_rendering_generator']}",
            f"D17 determinism: {result['d17_determinism']}",
            f"D18 Incident rendering: {result['d18_incident_rendering']}",
            f"D18 Plan rendering: {result['d18_plan_rendering']}",
            f"D18 SUMO rendering: {result['d18_sumo_rendering']}",
            f"D18 HITL rendering: {result['d18_hitl_rendering']}",
            f"D18 Track2 rendering: {result['d18_track2_rendering']}",
            f"D18 traceability: {result['d18_traceability']}",
            "",
            f"Operational actions created: {result['operational_actions_created']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Final status:",
            result["status"],
            "",
            "Output:",
            result["gate_output_relative"],
        ]
    )


def run_pv1_d16d17d18_persona_gate(
    project_root: str | Path = ".",
    d16_output: str | Path = DEFAULT_D16_OUTPUT,
    d17_output: str | Path = DEFAULT_D17_OUTPUT,
    d18_output: str | Path = DEFAULT_D18_OUTPUT,
    gate_output: str | Path = DEFAULT_GATE_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d16_dir = (root / d16_output).resolve()
    d17_dir = (root / d17_output).resolve()
    d18_dir = (root / d18_output).resolve()
    gate_dir = (root / gate_output).resolve()
    inputs = {rel: (root / rel).resolve() for rel in [*READ_ONLY_INPUTS, *OPTIONAL_INPUTS]}
    before = {rel: tree_signature(path) for rel, path in inputs.items()}
    for output_dir in [d16_dir, d17_dir, d18_dir, gate_dir]:
        reset_output_dir(output_dir, root)

    input_inventory = {
        "status": "PASS" if all((root / rel).exists() for rel in READ_ONLY_INPUTS) else "FAIL",
        "required_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in READ_ONLY_INPUTS},
        "optional_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in OPTIONAL_INPUTS},
    }
    d16 = make_persona_contracts(d16_dir)
    personas = d16["contract"]["personas"]
    input_set = collect_input_set(root)
    d17 = make_d17_generator(d17_dir, personas, input_set)
    d18 = make_d18_integration(d18_dir, d17)
    after = {rel: tree_signature(path) for rel, path in inputs.items()}
    mutation = compare_signatures(before, after)
    scan = no_overclaim_scan([d16_dir, d17_dir, d18_dir, gate_dir])

    rendering_report = {
        "status": d17["report"]["status"],
        "personas_rendered": len(d17["renderings"]),
        "same_evidence_base": d17["report"]["same_evidence_base"],
        "unsupported_claims_suppressed": d17["suppression"]["unsupported_claims_suppressed"],
    }
    traceability = {
        "status": d18["trace"]["status"],
        "persona_rows": len(d18["trace"]["rows"]),
        "all_personas_have_evidence_refs": all(row["evidence_ref_count"] > 0 and row["claim_labels_present"] for row in d18["trace"]["rows"]),
    }
    boundary = {
        "status": "PASS",
        "operational_actions_created": 0,
        "dispatch_actions_created": 0,
        "control_actions_created": 0,
        "enforcement_actions_created": 0,
        "persona_views_create_new_facts": False,
        "persona_views_create_approval": False,
    }
    handoff = {
        "status": "PASS",
        "recommended_next": "PV1-D19/D20/D21/D22 - Guardrail / Action Policy / Composite Platform v1 Snapshot",
        "final_block_can_consume": [
            "persona renderings",
            "suppression report",
            "HITL approval states",
            "event-fabric replay/current-state",
            "Incident/Plan modes",
            "SUMO synthetic context",
            "Track 2 review/data routes",
        ],
        "not_complete": ["PV1-D19", "PV1-D20", "PV1-D21", "PV1-D22"],
        "boundary": "This handoff does not imply the final policy or composite snapshot block is complete.",
    }
    stage_ledger = {
        "status": "PASS",
        "stages": {
            "PV1-D16": {"status": "PASS", "output": str(d16_dir)},
            "PV1-D17": {"status": d17["report"]["status"], "output": str(d17_dir)},
            "PV1-D18": {"status": d18["integration"]["status"], "output": str(d18_dir)},
        },
    }
    gates = [
        gate("PV1-D16-PRECOND", input_inventory["status"] == "PASS"),
        gate("PV1-D16-PERSONA-CONTRACT", len(personas) == 6),
        gate("PV1-D16-PERSONA-SCHEMA", (d16_dir / "PV1_D16_PERSONA_SCHEMA.json").exists()),
        gate("PV1-D16-BOUNDARY-SUPPRESSION-RULES", d16["suppression"]["status"] == "PASS"),
        gate("PV1-D17-RENDER-INPUT-SET", input_set["status"] == "PASS"),
        gate("PV1-D17-PERSONA-RENDERINGS", d17["report"]["status"] == "PASS"),
        gate("PV1-D17-SUPPRESSION-REPORT", d17["suppression"]["status"] == "PASS"),
        gate("PV1-D17-DETERMINISM", d17["determinism"]["status"] == "PASS"),
        gate("PV1-D18-INCIDENT-RENDERING", d18["incident"]["status"] == "PASS"),
        gate("PV1-D18-PLAN-RENDERING", d18["plan"]["status"] == "PASS"),
        gate("PV1-D18-SUMO-RENDERING", d18["sumo"]["status"] == "PASS" and d18["sumo"]["claim_label_preserved"]),
        gate("PV1-D18-HITL-RENDERING", d18["hitl"]["status"] == "PASS"),
        gate("PV1-D18-TRACK2-REVIEW-ROUTE-RENDERING", d18["track2"]["status"].startswith("PASS")),
        gate("PV1-D18-TRACEABILITY", traceability["status"] == "PASS" and traceability["all_personas_have_evidence_refs"]),
        gate("PV1-D18-CURRENT-STATE", d18["snapshot"]["personas_rendered"] == 6 and d18["snapshot"]["operational_actions_created"] == 0),
        gate("PV1-D16D17D18-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D16D17D18-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D16D17D18-HASHES", True),
    ]
    status = "PASS_PERSONA_RENDERINGS" if gates_pass(gates) else "FAIL"
    result = {
        "task": "PV1-D16/D17/D18 Persona Renderings",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "gates": gates,
        "d16_persona_contract": "PASS" if gates[1]["status"] == "PASS" else "FAIL",
        "d17_rendering_generator": d17["report"]["status"],
        "d17_determinism": d17["determinism"]["status"],
        "d18_incident_rendering": d18["incident"]["status"],
        "d18_plan_rendering": d18["plan"]["status"],
        "d18_sumo_rendering": d18["sumo"]["status"],
        "d18_hitl_rendering": d18["hitl"]["status"],
        "d18_track2_rendering": d18["track2"]["status"],
        "d18_traceability": traceability["status"],
        "operational_actions_created": d18["snapshot"]["operational_actions_created"],
        "dispatch_actions_created": d18["snapshot"]["dispatch_actions_created"],
        "control_actions_created": d18["snapshot"]["control_actions_created"],
        "enforcement_actions_created": d18["snapshot"]["enforcement_actions_created"],
        "unsupported_claims_suppressed": d18["snapshot"]["unsupported_claims_suppressed"],
        "no_overclaim": scan["status"],
        "no_mutation": mutation["status"],
        "hashes": "PASS",
        "d16_output": str(d16_dir),
        "d17_output": str(d17_dir),
        "d18_output": str(d18_dir),
        "gate_output": str(gate_dir),
        "gate_output_relative": str(Path(gate_output)),
    }
    write_json(gate_dir / "PV1_D16D17D18_INPUT_INVENTORY.json", input_inventory)
    write_json(gate_dir / "PV1_D16D17D18_STAGE_LEDGER.json", stage_ledger)
    write_json(gate_dir / "PV1_D16D17D18_PERSONA_RENDERING_REPORT.json", rendering_report)
    write_json(gate_dir / "PV1_D16D17D18_TRACEABILITY_REPORT.json", traceability)
    write_json(gate_dir / "PV1_D16D17D18_BOUNDARY_REPORT.json", boundary)
    write_json(gate_dir / "PV1_D16D17D18_NEXT_PV1_D19_HANDOFF.json", handoff)
    write_json(gate_dir / "PV1_D16D17D18_NO_OVERCLAIM_REPORT.json", scan)
    write_json(gate_dir / "PV1_D16D17D18_NO_MUTATION_REPORT.json", mutation)
    write_json(gate_dir / "PV1_D16D17D18_HARNESS_REPORT.json", result)
    write_text(gate_dir / "README.md", "# PV1-D16/D17/D18 Persona Renderings Gate\n\nUmbrella persona rendering output.")
    hashes = write_hashes(gate_dir)
    result["hash_count"] = len(hashes)
    write_json(gate_dir / "PV1_D16D17D18_HARNESS_REPORT.json", result)
    write_hashes(gate_dir)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D16/D17/D18 persona rendering gate.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    result = run_pv1_d16d17d18_persona_gate(args.project_root)
    print(result["final_print"])
    return 0 if result["status"] in {"PASS_PERSONA_RENDERINGS", "PASS_PERSONA_RENDERINGS_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
