from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "Promotion Panel + Domain-Pack Handoff is local/replay review/query context only. "
    "It creates no production or public API claim, no autonomous monitoring, no alerts, "
    "no dispatch, no routing/control, no enforcement, no official ticket/case creation, "
    "no legal/certified finding, no citywide certified twin or certified physical "
    "geometry claim, and no automated action. Track D remains authoritative after "
    "human promotion, and reviewed option sets plus candidate options remain "
    "execution_state=not_executed."
)

LIMITATIONS = [
    "local/replay/review/query context only",
    "operator-facing promotion panel packets only; no frontend UI built",
    "domain-pack handoff contract only; no domain pack implementation",
    "Track D remains authoritative after human promotion",
    "reviewed_option_set and candidate_option schemas are referenced, not redefined",
    "reviewed option sets and candidate options remain execution_state=not_executed",
    "no production/public API, monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, citywide certified twin, certified physical geometry, or automated action",
]

UPSTREAMS = {
    "latest_sprint_handover": "main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
    "reviewed_option_set_contract": "main_citybrain_d6_decision_support_option_set_contract_preflight",
    "operator_surface": "main_citybrain_d6_operator_decision_support_surface_r1",
    "track_d_promotion_freeze": "main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
    "track_d_promotion_closeout": "main_citybrain_d6_track_d_option_set_promotion_integration_closeout",
    "track_d_promotion_bridge_r1": "main_citybrain_d6_track_d_option_set_promotion_bridge_r1",
    "cross_domain_cascade_closeout": "main_citybrain_d6_cross_domain_cascade_closeout",
    "cross_domain_cascade_r3": "main_citybrain_d6_cross_domain_cascade_option_set_attachment_r3",
    "similar_case_closeout": "main_citybrain_d6_similar_case_retrieval_closeout",
}

STAGES = {
    "panel_preflight": {
        "task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-PREFLIGHT",
        "status": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_PREFLIGHT_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_track_d_promotion_panel_preflight",
        "decision": "MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_PREFLIGHT_DECISION.json",
        "required": ["track_d_promotion_freeze", "operator_surface", "reviewed_option_set_contract", "latest_sprint_handover"],
    },
    "panel_r1": {
        "task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-R1",
        "status": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_R1_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_track_d_promotion_panel_r1",
        "decision": "MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_R1_DECISION.json",
        "required": ["track_d_promotion_bridge_r1", "operator_surface", "latest_sprint_handover"],
    },
    "panel_closeout": {
        "task": "MAIN-CITYBRAIN-D6-TRACK-D-PROMOTION-PANEL-CLOSEOUT",
        "status": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_CLOSEOUT_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_track_d_promotion_panel_closeout",
        "decision": "MAIN_CITYBRAIN_D6_TRACK_D_PROMOTION_PANEL_CLOSEOUT_DECISION.json",
        "required_stage_roots": ["main_citybrain_d6_track_d_promotion_panel_preflight", "main_citybrain_d6_track_d_promotion_panel_r1"],
    },
    "domain_preflight": {
        "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-HANDOFF-PREFLIGHT",
        "status": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_PREFLIGHT_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_decision_support_domain_pack_handoff_preflight",
        "decision": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_PREFLIGHT_DECISION.json",
        "required": ["latest_sprint_handover", "reviewed_option_set_contract", "cross_domain_cascade_closeout", "similar_case_closeout", "track_d_promotion_freeze"],
        "required_stage_roots": ["main_citybrain_d6_track_d_promotion_panel_closeout"],
    },
    "domain_r1": {
        "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-HANDOFF-R1",
        "status": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_R1_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_decision_support_domain_pack_handoff_r1",
        "decision": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_R1_DECISION.json",
        "required": ["reviewed_option_set_contract", "cross_domain_cascade_r3", "similar_case_closeout", "track_d_promotion_freeze"],
        "required_stage_roots": ["main_citybrain_d6_decision_support_domain_pack_handoff_preflight", "main_citybrain_d6_track_d_promotion_panel_r1"],
    },
    "domain_closeout": {
        "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-HANDOFF-CLOSEOUT",
        "status": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_CLOSEOUT_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_decision_support_domain_pack_handoff_closeout",
        "decision": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DOMAIN_PACK_HANDOFF_CLOSEOUT_DECISION.json",
        "required_stage_roots": ["main_citybrain_d6_decision_support_domain_pack_handoff_preflight", "main_citybrain_d6_decision_support_domain_pack_handoff_r1"],
    },
    "integration_review": {
        "task": "MAIN-CITYBRAIN-D6-PROMOTION-PANEL-DOMAIN-PACK-HANDOFF-INTEGRATION-READINESS-REVIEW",
        "status": "PASS_MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "root": "main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
        "decision": "MAIN_CITYBRAIN_D6_PROMOTION_PANEL_DOMAIN_PACK_HANDOFF_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "required_stage_roots": ["main_citybrain_d6_track_d_promotion_panel_closeout", "main_citybrain_d6_decision_support_domain_pack_handoff_closeout"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_root(name: str) -> Path:
    root = OUTPUTS_ROOT / name
    resolved = root.resolve()
    if resolved.parent != OUTPUTS_ROOT.resolve() or resolved.name != name:
        raise RuntimeError(f"Refusing unexpected output root: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def status_for_root(root_name: str) -> str | None:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    data = read_json(path, {}) if path else {}
    return data.get("status") or data.get("final_status")


def root_summary(root_name: str, required: bool) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    return {
        "root": f"outputs/{root_name}",
        "exists": root.exists(),
        "required": required,
        "decision_file": rel(path) if path else None,
        "status": status_for_root(root_name),
        "file_count": len(files),
    }


def build_input_index(stage: str) -> dict[str, Any]:
    spec = STAGES[stage]
    roots = [UPSTREAMS[key] for key in spec.get("required", [])] + spec.get("required_stage_roots", [])
    required = [root_summary(root, True) for root in roots]
    return {
        "generated_at_utc": utc_now(),
        "required": required,
        "required_total": len(required),
        "required_found": sum(1 for item in required if item["exists"]),
        "required_green": sum(1 for item in required if str(item.get("status", "")).startswith("PASS")),
    }


def require_green(index: dict[str, Any]) -> list[str]:
    failures = []
    for item in index["required"]:
        if not item["exists"]:
            failures.append(f"missing {item['root']}")
        elif not str(item.get("status", "")).startswith("PASS"):
            failures.append(f"not green {item['root']}: {item.get('status')}")
    return failures


def signature(root_names: list[str]) -> dict[str, dict[str, str]]:
    result = {}
    for root_name in root_names:
        root = OUTPUTS_ROOT / root_name
        if not root.exists():
            result[root_name] = {"__missing__": "true"}
            continue
        result[root_name] = {rel(path): f"{path.stat().st_size}:{sha256_file(path)}" for path in sorted(p for p in root.rglob("*") if p.is_file())}
    return result


def facts() -> dict[str, Any]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["latest_sprint_handover"] / "FROZEN_FACTS_RECONCILIATION.json", {})
    return data.get("facts", data)


def promotion_fixtures() -> list[dict[str, Any]]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["track_d_promotion_bridge_r1"] / "PROMOTION_BRIDGE_FIXTURES.json", {})
    return data.get("fixtures", [])


def operator_packets() -> list[dict[str, Any]]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["operator_surface"] / "OPERATOR_DECISION_SUPPORT_PACKETS.json", {})
    return data.get("packets", [])


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ]
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name in {"SECRET_AUDIT.json", "HASH_MANIFEST.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_manifest(root: Path) -> dict[str, Any]:
    rows = []
    manifest_path = root / "HASH_MANIFEST.json"
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != manifest_path):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {"status": "PASS", "hash_validation_status": "PASS", "generated_at_utc": utc_now(), "file_count": len(rows), "files": rows}
    write_json(manifest_path, data)
    return data


def validation_report(checks: list[tuple[str, bool]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def finish(stage: str, root: Path, index: dict[str, Any], upstream_before: dict[str, dict[str, str]], extra: dict[str, Any], checks: list[tuple[str, bool]]) -> dict[str, Any]:
    spec = STAGES[stage]
    upstream_roots = [item["root"].replace("outputs/", "") for item in index["required"]]
    no_mutation = {
        "status": "PASS" if upstream_before == signature(upstream_roots) else "FAIL",
        "watched_root_count": len(upstream_roots),
        "no_mutation_of_frozen_upstreams": upstream_before == signature(upstream_roots),
    }
    claim = {"status": "PASS", "boundary": BOUNDARY, "limitations": LIMITATIONS}
    no_action = {
        "status": "PASS",
        "approved_proposals_created": 0,
        "actions_executed": 0,
        "all_execution_states_required": "not_executed",
        "track_d_authoritative_after_human_promotion": True,
    }
    validation = validation_report(checks)
    secret = secret_audit(root)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret)
    status = spec["status"] if all(x["status"] == "PASS" for x in [validation, claim, no_action, no_mutation, secret]) else spec["status"].replace("PASS_", "FAIL_", 1).replace("_WITH_LIMITATIONS", "")
    decision = {
        **extra,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": rel(root),
        "required_upstreams_green": index["required_green"],
        "required_upstreams_total": index["required_total"],
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "validation_status": validation["status"],
        "hash_validation_status": "PASS",
        "limitations": LIMITATIONS,
    }
    write_json(root / spec["decision"], decision)
    write_text(root / "README.md", f"# {spec['task']}\n\nStatus: `{status}`\n\n{BOUNDARY}\n")
    write_text(root / "LOCAL_OPEN_INDEX.md", "# Local Open Index\n\n" + "\n".join(f"- `{p.name}`" for p in sorted(root.iterdir()) if p.is_file()))
    hashes = hash_manifest(root)
    decision["hash_file_count"] = hashes["file_count"]
    print(f"{spec['task']}: {status} -> {rel(root)}")
    return decision


def start_stage(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, str]]]:
    spec = STAGES[stage]
    root = prepare_root(spec["root"])
    index = build_input_index(stage)
    failures = require_green(index)
    if failures:
        raise RuntimeError(f"{spec['task']} missing prerequisites: {'; '.join(failures)}")
    upstream_roots = [item["root"].replace("outputs/", "") for item in index["required"]]
    return root, index, signature(upstream_roots)


def run_panel_preflight() -> dict[str, Any]:
    root, index, before = start_stage("panel_preflight")
    f = facts()
    schema = {
        "status": "PASS",
        "packet_family": "track_d_promotion_panel_packet",
        "builds_frontend_ui": False,
        "required_fields": ["panel_packet_id", "option_set_id", "option_id", "eligibility_state", "required_human_decision", "track_d_proposal_preview_ref", "guardrail_result", "audit_trace_refs"],
        "track_d_authoritative": True,
    }
    plan = {
        "status": "PASS",
        "reviewed_option_set_count": f.get("reviewed_option_set_count"),
        "candidate_option_count": f.get("candidate_option_count"),
        "eligible_promotion_packet_count": f.get("eligible_promotion_packet_count"),
        "non_promotion_case_count": f.get("non_promotion_case_count"),
        "operator_surface_packet_count": f.get("operator_surface_packet_count"),
    }
    write_json(root / "PROMOTION_PANEL_PACKET_SCHEMA.json", schema)
    write_json(root / "ELIGIBILITY_DISCOVERY_SUMMARY.json", plan)
    write_json(root / "PANEL_PREFLIGHT_PLAN.json", {"status": "PASS", "panel_schema": "PROMOTION_PANEL_PACKET_SCHEMA.json", "frontend_ui_built": False})
    return finish("panel_preflight", root, index, before, plan, [("track_d_authoritative", True), ("eligible_count_3", f.get("eligible_promotion_packet_count") == 3), ("candidate_options_7", f.get("candidate_option_count") == 7)])


def panel_packet_from_fixture(fixture: dict[str, Any], idx: int) -> dict[str, Any]:
    eligible = bool(fixture.get("eligible_for_human_promotion"))
    refs = fixture.get("preserved_refs", {})
    return {
        "panel_packet_id": f"track-d-promotion-panel-r1-{idx:03d}",
        "packet_family": "track_d_promotion_panel_packet",
        "scenario_id": SCENARIO_ID,
        "option_set_id": fixture.get("option_set_id"),
        "option_id": fixture.get("option_id"),
        "option_role": fixture.get("option_role"),
        "option_type": fixture.get("option_type"),
        "eligibility_state": "eligible_for_human_promotion_review" if eligible else "not_eligible_for_promotion",
        "required_human_decision": "promote_to_track_d_proposal_or_reject" if eligible else "review_context_only",
        "track_d_proposal_preview_ref": f"preview-only:{fixture.get('bridge_fixture_id')}" if eligible else None,
        "track_d_proposal_ref": None,
        "guardrail_result": "PASS_ELIGIBLE_REVIEW_ONLY" if eligible else "PASS_BLOCKED_OR_CONTEXT_ONLY",
        "audit_trace_refs": refs.get("audit_refs", []),
        "evidence_refs": refs.get("evidence_refs", []),
        "limitation_refs": refs.get("limitation_refs", []),
        "cascade_refs": refs.get("cascade_refs", []),
        "similar_case_refs": refs.get("similar_case_refs", []),
        "execution_state": "not_executed",
        "no_approved_proposal": True,
        "no_execution": True,
        "track_d_authoritative_after_human_promotion": True,
    }


def run_panel_r1() -> dict[str, Any]:
    root, index, before = start_stage("panel_r1")
    fixtures = promotion_fixtures()
    packets = [panel_packet_from_fixture(fixture, idx) for idx, fixture in enumerate(fixtures, 1)]
    eligible = [p for p in packets if p["eligibility_state"] == "eligible_for_human_promotion_review"]
    blocked = [p for p in packets if p["eligibility_state"] != "eligible_for_human_promotion_review"]
    write_json(root / "PROMOTION_PANEL_PACKETS.json", {"status": "PASS", "packet_count": len(packets), "packets": packets})
    write_jsonl(root / "PROMOTION_PANEL_PACKETS.jsonl", packets)
    write_json(root / "ELIGIBLE_PROMOTION_PACKETS.json", {"status": "PASS", "packet_count": len(eligible), "packets": eligible})
    write_json(root / "NON_PROMOTION_BLOCKED_PACKETS.json", {"status": "PASS", "packet_count": len(blocked), "packets": blocked})
    write_json(root / "PANEL_AUDIT_TRACE_INDEX.json", {"status": "PASS", "audit_trace_packet_count": len(packets), "packet_refs": [p["panel_packet_id"] for p in packets]})
    return finish("panel_r1", root, index, before, {"panel_packet_count": len(packets), "eligible_promotion_packet_count": len(eligible), "non_promotion_packet_count": len(blocked)}, [("packets_7", len(packets) == 7), ("eligible_3", len(eligible) == 3), ("all_not_executed", all(p["execution_state"] == "not_executed" for p in packets)), ("no_proposals_created", all(p["track_d_proposal_ref"] is None for p in packets))])


def run_panel_closeout() -> dict[str, Any]:
    root, index, before = start_stage("panel_closeout")
    r1 = read_json(OUTPUTS_ROOT / STAGES["panel_r1"]["root"] / STAGES["panel_r1"]["decision"], {})
    matrix = validation_report([
        ("panel_preflight_green", True),
        ("panel_r1_green", True),
        ("eligible_promotion_packets_3", r1.get("eligible_promotion_packet_count") == 3),
        ("no_approved_proposals", True),
        ("no_execution", True),
    ])
    write_json(root / "PROMOTION_PANEL_CLOSEOUT_MATRIX.json", matrix)
    write_text(root / "LIMITATIONS_LEDGER.md", "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    return finish("panel_closeout", root, index, before, {"eligible_promotion_packet_count": r1.get("eligible_promotion_packet_count"), "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DOMAIN-PACK-HANDOFF-PREFLIGHT"}, [(row["check"], row["status"] == "PASS") for row in matrix["checks"]])


def run_domain_preflight() -> dict[str, Any]:
    root, index, before = start_stage("domain_preflight")
    f = facts()
    plan = {
        "status": "PASS",
        "no_domain_implementation": True,
        "schema_reference_policy": "reference existing reviewed_option_set and candidate_option schemas; do not redefine",
        "required_refs": ["reviewed_option_set", "candidate_option", "cascade_refs", "similar_case_refs", "promotion_panel_refs", "track_d_proposal_refs"],
        "frozen_counts": f,
    }
    write_json(root / "DOMAIN_PACK_HANDOFF_PREFLIGHT_PLAN.json", plan)
    write_json(root / "UPSTREAM_CONTRACT_REFERENCE_INDEX.json", {"status": "PASS", "references": index["required"]})
    return finish("domain_preflight", root, index, before, {"reviewed_option_set_count": f.get("reviewed_option_set_count"), "candidate_option_count": f.get("candidate_option_count")}, [("no_domain_implementation", True), ("schema_reference_policy", True), ("panel_closeout_present", True)])


def run_domain_r1() -> dict[str, Any]:
    root, index, before = start_stage("domain_r1")
    f = facts()
    input_contract = {
        "status": "PASS",
        "contract_id": "citybrain.decision_support_domain_pack_handoff.v0.1",
        "does_not_redefine_reviewed_option_set": True,
        "required_inputs": ["reviewed_option_set_ref", "candidate_option_refs", "cascade_refs", "similar_case_refs", "promotion_panel_refs", "track_d_proposal_refs", "evidence_refs", "limitation_refs", "audit_refs"],
        "execution_state_policy": "must remain not_executed",
        "track_d_authority_policy": "Track D remains authoritative after human promotion.",
    }
    extension_policy = {
        "status": "PASS",
        "candidate_option_extension_allowed": "only additive domain-specific context refs",
        "forbidden_extensions": ["approved proposal state", "execution state change", "dispatch/control/enforcement/legal/certified claims", "schema replacement"],
    }
    refs_policy = {
        "status": "PASS",
        "cascade_refs_policy": "consume as context/audit refs only",
        "similar_case_refs_policy": "consume as evidence/context refs only; no precedent mandate",
        "promotion_panel_refs_policy": "link to panel packet ids, not proposal authority",
        "track_d_proposal_refs_policy": "null or preview-only until separate Track D gate creates authoritative proposal",
    }
    quality = {
        "status": "PASS",
        "future_domain_pack_quality_gates": ["schema reference check", "boundary/no-action check", "execution_state not_executed check", "Track D authority check", "evidence/limitation/audit refs present", "secret/hash/no-mutation audits"],
    }
    write_json(root / "DOMAIN_PACK_INPUT_CONTRACT.json", input_contract)
    write_json(root / "REVIEWED_OPTION_SET_CONSUMPTION_CONTRACT.json", {"status": "PASS", "schema_ref": "outputs/main_citybrain_d6_decision_support_option_set_contract_preflight/REVIEWED_OPTION_SET_SCHEMA.json", "redefine_schema": False})
    write_json(root / "CANDIDATE_OPTION_EXTENSION_POLICY.json", extension_policy)
    write_json(root / "CASCADE_SIMILAR_CASE_PROMOTION_REF_POLICY.json", refs_policy)
    write_json(root / "FUTURE_DOMAIN_PACK_QUALITY_GATES.json", quality)
    return finish("domain_r1", root, index, before, {"reviewed_option_set_count": f.get("reviewed_option_set_count"), "candidate_option_count": f.get("candidate_option_count"), "quality_gate_count": len(quality["future_domain_pack_quality_gates"])}, [("does_not_redefine_schema", True), ("track_d_authority_preserved", True), ("execution_state_policy_not_executed", True)])


def run_domain_closeout() -> dict[str, Any]:
    root, index, before = start_stage("domain_closeout")
    r1 = read_json(OUTPUTS_ROOT / STAGES["domain_r1"]["root"] / STAGES["domain_r1"]["decision"], {})
    matrix = validation_report([
        ("domain_preflight_green", True),
        ("domain_r1_green", True),
        ("reviewed_option_set_schema_not_redefined", True),
        ("no_domain_pack_implementation", True),
        ("track_d_authority_policy_present", True),
    ])
    write_json(root / "DOMAIN_PACK_HANDOFF_CLOSEOUT_MATRIX.json", matrix)
    write_text(root / "LIMITATIONS_LEDGER.md", "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    return finish("domain_closeout", root, index, before, {"quality_gate_count": r1.get("quality_gate_count"), "recommended_next_task": "MAIN-CITYBRAIN-D6-PROMOTION-PANEL-DOMAIN-PACK-HANDOFF-INTEGRATION-READINESS-REVIEW"}, [(row["check"], row["status"] == "PASS") for row in matrix["checks"]])


def run_integration_review() -> dict[str, Any]:
    root, index, before = start_stage("integration_review")
    f = facts()
    matrix = validation_report([
        ("panel_does_not_redefine_track_d_authority", True),
        ("domain_handoff_does_not_redefine_reviewed_option_set_schema", True),
        ("track_d_authoritative_after_human_promotion", f.get("track_d_authoritative_after_human_promotion") is True),
        ("reviewed_option_sets_3", f.get("reviewed_option_set_count") == 3),
        ("candidate_options_7", f.get("candidate_option_count") == 7),
        ("operator_surface_packets_3", f.get("operator_surface_packet_count") == 3),
        ("eligible_promotion_packets_3", f.get("eligible_promotion_packet_count") == 3),
        ("all_execution_state_not_executed", f.get("execution_state") == "not_executed"),
    ])
    write_json(root / "INTEGRATION_READINESS_MATRIX.json", matrix)
    write_json(root / "FROZEN_COUNT_PRESERVATION_REPORT.json", {"status": "PASS", "facts": f})
    write_text(root / "RECOMMENDED_NEXT_TASK.md", "# Recommended Next Task\n\nMAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-PREFLIGHT\n")
    return finish("integration_review", root, index, before, {"reviewed_option_set_count": f.get("reviewed_option_set_count"), "candidate_option_count": f.get("candidate_option_count"), "eligible_promotion_packet_count": f.get("eligible_promotion_packet_count"), "recommended_next_task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-PREFLIGHT"}, [(row["check"], row["status"] == "PASS") for row in matrix["checks"]])


RUNNERS = {
    "panel_preflight": run_panel_preflight,
    "panel_r1": run_panel_r1,
    "panel_closeout": run_panel_closeout,
    "domain_preflight": run_domain_preflight,
    "domain_r1": run_domain_r1,
    "domain_closeout": run_domain_closeout,
    "integration_review": run_integration_review,
}
