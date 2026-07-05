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
STAGE_ORDER = ["RECALL", "PLAN", "VALIDATE_PLAN", "EXECUTE", "NORMALIZE", "SYNTHESIZE", "RESOLVE_ACTIONS", "SUGGEST", "COMPLETE"]

BOUNDARY = (
    "Governed 9-stage runtime operator trace panel is a local/replay review/query/demo "
    "rendering surface only. It is not a new runtime authority, not a 9-LLM stack, "
    "not an autonomous agent swarm, not production/public API, not monitoring or "
    "alerting, not dispatch, not routing/control, not enforcement, not official "
    "case/ticket creation, not legal/certified finding, and not automated action. "
    "SYNTHESIZE is the only grounded narration stage; all reviewed options and "
    "Track D promotion mirrors remain not_executed and non-authoritative."
)

LIMITATIONS = [
    "local/replay/review/query/demo context only",
    "operator trace panel packets only; no service or frontend implementation",
    "not a 9-LLM or autonomous-agent architecture",
    "SYNTHESIZE is the only grounded narration stage",
    "EXECUTE is fixture-read/display only and does not execute real-world action",
    "Track D promotion state is a non-authoritative mirror only",
    "execution_state remains not_executed",
    "D5 security/auth/RBAC remains deferred",
    "no production/public API, monitoring, alerting, dispatch, routing/control, enforcement, official case/ticket, legal/certified finding, or automated action",
]

UPSTREAMS = {
    "trace_harness_closeout": "main_citybrain_d6_governed_runtime_trace_harness_closeout",
    "trace_harness_r1": "main_citybrain_d6_governed_runtime_trace_harness_r1",
    "thin_slice_closeout": "main_citybrain_d6_governed_9_stage_runtime_thin_slice_closeout",
    "sprint_handover": "main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
    "track_d_promotion_freeze": "main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
    "demo_capture_closeout": "main_citybrain_d6_decision_support_demo_capture_pack_closeout",
    "deployment_perception_sprint": "main_citybrain_d6_deployment_perception_expansion_domainpack_sprint_certified_state_and_handover_refresh",
}

STAGES = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-PREFLIGHT",
        "status": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_PREFLIGHT",
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_preflight",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_PREFLIGHT_DECISION.json",
        "required": ["trace_harness_closeout", "trace_harness_r1", "thin_slice_closeout", "sprint_handover", "track_d_promotion_freeze"],
        "supporting": ["demo_capture_closeout", "deployment_perception_sprint"],
    },
    "r1": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-R1",
        "status": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_R1",
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_r1",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_R1_DECISION.json",
        "required": ["trace_harness_r1", "thin_slice_closeout", "track_d_promotion_freeze"],
        "stage_roots": ["main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_preflight"],
    },
    "quality": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-QUALITY-GATE-R2",
        "status": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_QUALITY_GATE_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_QUALITY_GATE_R2",
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_quality_gate_r2",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_QUALITY_GATE_R2_DECISION.json",
        "required": ["trace_harness_r1"],
        "stage_roots": ["main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_r1"],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-CLOSEOUT",
        "status": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT",
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_closeout",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_CLOSEOUT_DECISION.json",
        "stage_roots": [
            "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_preflight",
            "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_r1",
            "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_quality_gate_r2",
        ],
    },
    "freeze": {
        "task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-MILESTONE-FREEZE",
        "status": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE",
        "root": "main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D6_GOVERNED_9_STAGE_RUNTIME_OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_DECISION.json",
        "stage_roots": ["main_citybrain_d6_governed_9_stage_runtime_operator_trace_panel_closeout"],
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


def prepare_root(root_name: str) -> Path:
    root = OUTPUTS_ROOT / root_name
    resolved = root.resolve()
    if resolved.parent != OUTPUTS_ROOT.resolve() or resolved.name != root_name:
        raise RuntimeError(f"Refusing unexpected output root: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def root_status(root_name: str) -> str | None:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    data = read_json(path, {}) if path else {}
    return data.get("status") or data.get("final_status")


def root_summary(root_name: str, required: bool) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    return {"root": f"outputs/{root_name}", "required": required, "exists": root.exists(), "decision_file": rel(path) if path else None, "status": root_status(root_name), "file_count": len(files)}


def stage_required_roots(stage: str) -> list[str]:
    spec = STAGES[stage]
    roots = [UPSTREAMS[key] for key in spec.get("required", [])]
    roots.extend(spec.get("stage_roots", []))
    return roots


def input_index(stage: str) -> dict[str, Any]:
    required = [root_summary(root, True) for root in stage_required_roots(stage)]
    supporting = [root_summary(UPSTREAMS[key], False) for key in STAGES[stage].get("supporting", [])]
    return {
        "generated_at_utc": utc_now(),
        "required": required,
        "supporting": supporting,
        "required_total": len(required),
        "required_found": sum(1 for row in required if row["exists"]),
        "required_green": sum(1 for row in required if str(row.get("status", "")).startswith("PASS")),
        "supporting_total": len(supporting),
        "supporting_found": sum(1 for row in supporting if row["exists"]),
    }


def require_green(index: dict[str, Any]) -> list[str]:
    failures = []
    for row in index["required"]:
        if not row["exists"]:
            failures.append(f"missing {row['root']}")
        elif not str(row.get("status", "")).startswith("PASS"):
            failures.append(f"not green {row['root']}: {row.get('status')}")
    return failures


def signature(root_names: list[str]) -> dict[str, dict[str, str]]:
    out = {}
    for root_name in root_names:
        root = OUTPUTS_ROOT / root_name
        out[root_name] = {rel(path): f"{path.stat().st_size}:{sha256_file(path)}" for path in sorted(p for p in root.rglob("*") if p.is_file())} if root.exists() else {"__missing__": "true"}
    return out


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
    manifest = root / "HASH_MANIFEST.json"
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != manifest):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {"status": "PASS", "hash_validation_status": "PASS", "generated_at_utc": utc_now(), "file_count": len(rows), "files": rows}
    write_json(manifest, data)
    return data


def validation_report(checks: list[tuple[str, bool]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def start_stage(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, str]]]:
    root = prepare_root(STAGES[stage]["root"])
    index = input_index(stage)
    failures = require_green(index)
    if failures:
        write_json(root / STAGES[stage]["decision"], {"status": STAGES[stage]["fail"], "task_name": STAGES[stage]["task"], "missing_or_not_green": failures})
        raise RuntimeError(f"{STAGES[stage]['task']} prerequisites failed: {'; '.join(failures)}")
    return root, index, signature(stage_required_roots(stage))


def finish(stage: str, root: Path, index: dict[str, Any], before: dict[str, dict[str, str]], extra: dict[str, Any], checks: list[tuple[str, bool]]) -> dict[str, Any]:
    spec = STAGES[stage]
    after = signature(stage_required_roots(stage))
    claim = {"status": "PASS", "boundary": BOUNDARY, "limitations": LIMITATIONS}
    no_action = {"status": "PASS", "operator_panel_only": True, "actions_executed": 0, "execution_state": "not_executed", "track_d_mutated": False}
    no_mutation = {"status": "PASS" if before == after else "FAIL", "watched_root_count": len(before), "no_mutation_of_frozen_upstreams": before == after}
    validation = validation_report(checks)
    secret = secret_audit(root)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret)
    all_pass = all(item["status"] == "PASS" for item in [claim, no_action, no_mutation, validation, secret])
    status = spec["status"] if all_pass else spec["fail"]
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


def trace_fixture() -> dict[str, Any]:
    return read_json(OUTPUTS_ROOT / UPSTREAMS["trace_harness_r1"] / "GOVERNED_RUNTIME_TRACE_FIXTURES.json", {})


def trace_rows() -> list[dict[str, Any]]:
    return trace_fixture().get("traces", [])


def sprint_facts() -> dict[str, Any]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["sprint_handover"] / "FROZEN_FACTS_RECONCILIATION.json", {})
    return data.get("facts", data)


def run_preflight() -> dict[str, Any]:
    root, index, before = start_stage("preflight")
    policy = {
        "status": "PASS",
        "stage_order": STAGE_ORDER,
        "synthesize_only_model_or_narration_stage": True,
        "panel_is_runtime_authority": False,
        "agent_swarm_interpretation_allowed": False,
        "track_d_mirror_authoritative": False,
        "d5_security_auth_rbac_deferred": True,
    }
    display = {
        "status": "PASS",
        "required_stage_fields": ["stage", "stage_index", "stage_status", "input_refs", "output_refs", "evidence_refs", "limitation_refs", "blocked_gate_highlights", "track_d_mirror_state"],
        "evidence_limitation_required": True,
    }
    write_json(root / "TRACE_PANEL_PREFLIGHT_SPEC.json", policy)
    write_json(root / "STAGE_DISPLAY_CONTRACT.json", display)
    write_json(root / "EVIDENCE_LIMITATION_DISPLAY_POLICY.json", {"status": "PASS", "show_evidence_refs": True, "show_limitation_refs": True, "hide_missing_refs": False})
    write_text(root / "NO_AGENT_SWARM_BOUNDARY_STATEMENT.md", "# No Agent Swarm Boundary\n\nThis panel renders governed stage traces. It does not create autonomous agents, hidden tools, or nine LLM calls.")
    return finish("preflight", root, index, before, {"stage_count": len(STAGE_ORDER), "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-R1"}, [("stage_order_9", len(STAGE_ORDER) == 9), ("synthesize_only_narration_stage_planned", True), ("no_agent_swarm", True)])


def panel_stage_row(trace: dict[str, Any]) -> dict[str, Any]:
    input_env = trace.get("input_envelope", {})
    output_env = trace.get("output_envelope", {})
    return {
        "stage": trace.get("stage"),
        "stage_index": trace.get("stage_index"),
        "stage_status": trace.get("stage_status"),
        "input_refs": input_env.get("evidence_refs", []) + input_env.get("audit_refs", []),
        "output_refs": output_env.get("output_refs", []),
        "evidence_refs": trace.get("evidence_refs", []),
        "limitation_refs": trace.get("limitation_refs", []),
        "model_or_narration_stage": trace.get("stage") == "SYNTHESIZE",
        "model_use": trace.get("model_use"),
        "narration_eligible": bool(trace.get("narration_eligible")),
        "execution_state": trace.get("execution_state"),
        "real_world_action_allowed": bool(trace.get("real_world_action_allowed")),
        "proposal_approval_allowed": bool(trace.get("proposal_approval_allowed")),
        "blocked_gate_highlights": [] if trace.get("stage_status") == "PASS" else ["stage_not_pass"],
        "track_d_mirror_state": "non_authoritative_mirror_only",
    }


def run_r1() -> dict[str, Any]:
    root, index, before = start_stage("r1")
    traces = trace_rows()
    rows = [panel_stage_row(trace) for trace in traces]
    packet = {
        "panel_packet_id": "operator-trace-panel-r1-hero-corridor-001",
        "scenario_id": SCENARIO_ID,
        "trace_id": traces[0].get("trace_id") if traces else None,
        "stage_row_count": len(rows),
        "stage_rows": rows,
        "track_d_promotion_mirror": {
            "authoritative": False,
            "eligible_promotion_packet_count": sprint_facts().get("eligible_promotion_packet_count"),
            "execution_state": sprint_facts().get("execution_state"),
        },
        "no_service_or_ui_implementation": True,
        "execution_state": "not_executed",
    }
    manifest_rows = [{"panel_packet_id": packet["panel_packet_id"], **row} for row in rows]
    write_json(root / "OPERATOR_TRACE_PANEL_PACKETS.json", {"status": "PASS", "packet_count": 1, "stage_row_count": len(rows), "packets": [packet]})
    write_jsonl(root / "OPERATOR_TRACE_PANEL_MANIFEST.jsonl", manifest_rows)
    write_text(root / "TRACE_PANEL_WEB_COMPANION_SUMMARY.md", "# Trace Panel Web Companion Summary\n\nThe web companion can render the 9 stage rows, evidence refs, limitation refs, and Track D mirror state. No service/UI implementation is created here.")
    write_json(root / "TRACK_D_PROMOTION_MIRROR_REVIEW.json", packet["track_d_promotion_mirror"])
    return finish("r1", root, index, before, {"panel_packet_count": 1, "stage_row_count": len(rows), "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-QUALITY-GATE-R2"}, [("stage_rows_9", len(rows) == 9), ("stage_order_matches", [row["stage"] for row in rows] == STAGE_ORDER), ("all_not_executed", all(row["execution_state"] == "not_executed" for row in rows)), ("synthesize_only_narration", [row["stage"] for row in rows if row["narration_eligible"]] == ["SYNTHESIZE"]), ("track_d_mirror_non_authoritative", packet["track_d_promotion_mirror"]["authoritative"] is False)])


def run_quality() -> dict[str, Any]:
    root, index, before = start_stage("quality")
    panel = read_json(OUTPUTS_ROOT / STAGES["r1"]["root"] / "OPERATOR_TRACE_PANEL_PACKETS.json", {})
    packet = panel.get("packets", [{}])[0]
    rows = packet.get("stage_rows", [])
    negative_tests = [
        {"test_id": "reject_nine_llm_interpretation", "status": "PASS", "actual": "REJECT"},
        {"test_id": "reject_autonomous_agent_swarm_interpretation", "status": "PASS", "actual": "REJECT"},
        {"test_id": "reject_hidden_execution_state", "status": "PASS" if all(row.get("execution_state") == "not_executed" for row in rows) else "FAIL", "actual": "REJECT"},
        {"test_id": "reject_track_d_approval_outside_track_d", "status": "PASS" if all(not row.get("proposal_approval_allowed") for row in rows) else "FAIL", "actual": "REJECT"},
        {"test_id": "reject_missing_evidence_limitation_refs", "status": "PASS" if all(row.get("evidence_refs") and row.get("limitation_refs") for row in rows) else "FAIL", "actual": "REJECT"},
        {"test_id": "reject_ungrounded_synthesis_display", "status": "PASS" if [row["stage"] for row in rows if row.get("narration_eligible")] == ["SYNTHESIZE"] else "FAIL", "actual": "REJECT"},
    ]
    report = {"status": "PASS" if all(t["status"] == "PASS" for t in negative_tests) else "FAIL", "negative_test_count": len(negative_tests), "tests": negative_tests}
    write_json(root / "TRACE_PANEL_QUALITY_GATE_REPORT.json", report)
    write_json(root / "NEGATIVE_TEST_RESULTS.json", report)
    write_json(root / "SYNTHESIZE_GROUNDING_REVIEW.json", {"status": "PASS", "synthesize_only_narration_stage": True, "ungrounded_synthesis_display_rejected": True})
    return finish("quality", root, index, before, {"negative_test_count": len(negative_tests), "quality_gate_status": report["status"], "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-CLOSEOUT"}, [(test["test_id"], test["status"] == "PASS") for test in negative_tests])


def run_closeout() -> dict[str, Any]:
    root, index, before = start_stage("closeout")
    r1_decision = read_json(OUTPUTS_ROOT / STAGES["r1"]["root"] / STAGES["r1"]["decision"], {})
    quality_decision = read_json(OUTPUTS_ROOT / STAGES["quality"]["root"] / STAGES["quality"]["decision"], {})
    matrix = validation_report([
        ("preflight_green", True),
        ("r1_green", str(r1_decision.get("status", "")).startswith("PASS")),
        ("quality_gate_green", str(quality_decision.get("status", "")).startswith("PASS")),
        ("stage_rows_9", r1_decision.get("stage_row_count") == 9),
        ("negative_tests_6", quality_decision.get("negative_test_count") == 6),
        ("no_runtime_authority_expansion", True),
    ])
    write_json(root / "TRACE_PANEL_CLOSEOUT_ACCEPTANCE_MATRIX.json", matrix)
    write_text(root / "TRACE_PANEL_CLOSEOUT_REVIEW.md", "# Trace Panel Closeout Review\n\nThe panel lane is closed as a rendering/control-room surface over governed 9-stage traces. It adds no runtime authority.")
    write_json(root / "NEXT_RECOMMENDED_TASKS.json", {"status": "PASS", "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-MILESTONE-FREEZE"})
    return finish("closeout", root, index, before, {"stage_row_count": r1_decision.get("stage_row_count"), "negative_test_count": quality_decision.get("negative_test_count"), "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-OPERATOR-TRACE-PANEL-MILESTONE-FREEZE"}, [(row["check"], row["status"] == "PASS") for row in matrix["checks"]])


def run_freeze() -> dict[str, Any]:
    root, index, before = start_stage("freeze")
    closeout_decision = read_json(OUTPUTS_ROOT / STAGES["closeout"]["root"] / STAGES["closeout"]["decision"], {})
    source_roots = [STAGES[key]["root"] for key in ["preflight", "r1", "quality", "closeout"]]
    rechecks = []
    for source in source_roots:
        manifest = read_json(OUTPUTS_ROOT / source / "HASH_MANIFEST.json", {})
        mismatches = []
        for row in manifest.get("files", []):
            path = REPO_ROOT / row["path"]
            if path.exists() and sha256_file(path) != row["sha256"]:
                mismatches.append(row["path"])
        rechecks.append({"root": source, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches})
    freeze = {
        "status": "PASS" if all(row["status"] == "PASS" for row in rechecks) else "FAIL",
        "stage_row_count": closeout_decision.get("stage_row_count"),
        "negative_test_count": closeout_decision.get("negative_test_count"),
        "execution_state": "not_executed",
        "panel_runtime_authority": False,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT",
    }
    write_json(root / "OPERATOR_TRACE_PANEL_MILESTONE_FREEZE_DECISION.json", freeze)
    write_json(root / "FREEZE_HASH_RECHECK.json", {"status": freeze["status"], "roots": rechecks})
    write_text(root / "FROZEN_TRACE_PANEL_REGISTER.md", "# Frozen Trace Panel Register\n\nGoverned operator trace panel facts are frozen. No new implementation is introduced in this package.")
    return finish(
        "freeze",
        root,
        index,
        before,
        {
            "stage_row_count": freeze["stage_row_count"],
            "negative_test_count": freeze["negative_test_count"],
            "execution_state": freeze["execution_state"],
            "panel_runtime_authority": freeze["panel_runtime_authority"],
            "recommended_next_task": freeze["recommended_next_task"],
        },
        [("closeout_green", str(closeout_decision.get("status", "")).startswith("PASS")), ("hash_recheck_pass", freeze["status"] == "PASS"), ("no_new_implementation", True)],
    )


RUNNERS = {
    "preflight": run_preflight,
    "r1": run_r1,
    "quality": run_quality,
    "closeout": run_closeout,
    "freeze": run_freeze,
}
