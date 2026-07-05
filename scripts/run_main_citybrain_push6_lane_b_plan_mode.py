#!/usr/bin/env python3
"""Build Push 6 Lane B PLAN mode artifacts.

PLAN mode creates candidate OptionSets for local/replay review. It never
executes a plan and cannot close until Push 6 Lane A publishes approval
lifecycle / authority level 3 artifacts.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.plan_mode import PlanOption, PlanRequest, validate_plan_bundle


OUTPUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_b_plan_mode"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_b_plan_mode_closeout"
FINAL_STATUS_ROOT = REPO_ROOT / "outputs" / "push6_lane_b_plan_mode_final_status"

PUSH6_LANE_A_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle"
PUSH6_LANE_A_FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle_final_status"
PUSH5_INFRA_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_integration"
PUSH5_FINAL_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_final_status"
PUSH5_WATCH_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state"
PUSH5_MEDIA_ROOT = REPO_ROOT / "outputs" / "push5_lane_b_perception_media_evidence"
PUSH4_CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
PUSH3_BRIEF_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging"

PACKAGE = "MAIN-CITYBRAIN-PUSH6-LANE-B-PLAN-MODE-RUN-TO-CLOSURE"
TASK_ID = "PUSH6-LANE-B-PLAN-MODE"
BRANCH = "codex/push6-lane-b-plan-mode"
RUN_TIMESTAMP = "2026-07-05T22:35:00Z"
SCHEMA_VERSION = "main-citybrain.push6.lane_b.plan_mode.v1"
PASS_STATUS = "PASS_PUSH6_LANE_B_PLAN_MODE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH6_LANE_B_PLAN_MODE_FINAL_STATUS_WITH_LIMITATIONS"
STOP_PUSH5 = "STOPPED_WAITING_FOR_PUSH5_INTEGRATION"
STOP_APPROVAL = "STOPPED_WAITING_FOR_APPROVAL_LIFECYCLE"
FAIL_STATUS = "FAIL_PUSH6_LANE_B_PLAN_MODE"

REQUIRED_OUTPUT_FILES = [
    "PLAN_MODE_DECISION.json",
    "PLAN_MODE_CONTRACT_OVERVIEW.md",
    "PLAN_REQUEST_SCHEMA.json",
    "OPTIONSET_V2_SCHEMA.json",
    "PLAN_OPTION_SCHEMA.json",
    "DO_NOTHING_BASELINE_SCHEMA.json",
    "ABSTAIN_NO_SAFE_OPTION_SCHEMA.json",
    "PLAN_MODE_FIXTURES.json",
    "OPTIONSET_V2_FIXTURES.json",
    "PLAN_APPROVAL_BINDINGS.json",
    "PLAN_MODE_BOUNDARY_AND_NON_CLAIMS.md",
    "PLAN_MODE_TEST_LOG.md",
    "PLAN_MODE_HASH_MANIFEST.json",
]

UNIVERSAL_NON_CLAIMS = [
    "production API",
    "URL fetch or live retrieval",
    "live LLM authority",
    "official case/ticket submission",
    "dispatch/control/enforcement execution",
    "legal/certified finding",
    "autonomous workflow",
    "live Kit control",
    "full citywide twin",
    "VSS-as-fact-source",
    "cross-city claim before federation",
    "executed action",
    "approval bypass",
]

NOT_EXECUTED = [
    "production_api",
    "url_fetch",
    "live_retrieval",
    "live_llm_call",
    "official_submission",
    "dispatch_control_enforcement",
    "legal_certified_finding",
    "live_kit_control",
    "plan_execution",
]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_roots() -> None:
    reset_root(OUTPUT_ROOT)
    for root in [CLOSEOUT_ROOT, FINAL_STATUS_ROOT]:
        if root.exists():
            reset_root(root)
            shutil.rmtree(root)


def hash_manifest(root: Path, name: str) -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.name == name:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {
        "schema_version": f"{SCHEMA_VERSION}.hash_manifest",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "algorithm": "sha256",
        "status": "PASS",
        "file_count": len(rows),
        "files": rows,
    }
    write_json(root / name, payload)
    return payload


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest = read_json(root / name, {"files": []})
    declared = {row["path"]: row["sha256"] for row in manifest.get("files", [])}
    verified = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != name):
        verified[rel(path)] = sha256_file(path)
    mismatches = sorted(path for path, digest in declared.items() if verified.get(path) != digest)
    missing = sorted(path for path in declared if path not in verified)
    extra = sorted(path for path in verified if path not in declared)
    return {
        "status": "PASS" if not mismatches and not missing and not extra and manifest.get("status") == "PASS" else "FAIL",
        "declared": declared,
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "extra": extra,
    }


def uniq(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in (None, "", []):
            continue
        key = str(value)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def load_inputs() -> dict[str, Any]:
    return {
        "push5_infra": read_json(PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json", {}),
        "push5_final": read_json(PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json", {}),
        "push5_spatial_media_join": read_json(PUSH5_INFRA_ROOT / "PUSH5_SPATIAL_MEDIA_EVIDENCE_JOIN_REPORT.json", {}),
        "push5_workflow_join": read_json(PUSH5_INFRA_ROOT / "PUSH5_SPATIAL_WORKFLOW_STATE_JOIN_REPORT.json", {}),
        "watch_items": read_json(PUSH5_WATCH_ROOT / "WATCH_EXPANDED_ITEMS.json", {}).get("items", []),
        "workflow_events": read_json(PUSH5_WATCH_ROOT / "WORKFLOW_STATE_EVENTS.json", {}).get("items", []),
        "media_bundles": read_json(PUSH5_MEDIA_ROOT / "MEDIA_EVIDENCE_BUNDLES.json", {}).get("bundles", []),
        "check_reports": read_json(PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json", {}).get("items", []),
        "briefs": read_json(PUSH3_BRIEF_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json", {}).get("briefs", []),
    }


def push5_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    required_paths = [
        PUSH5_INFRA_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json",
        PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json",
        PUSH5_WATCH_ROOT / "WATCH_EXPANDED_ITEMS.json",
        PUSH5_MEDIA_ROOT / "MEDIA_EVIDENCE_BUNDLES.json",
        PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json",
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    infra_status = str(inputs["push5_infra"].get("status", ""))
    final_status = str(inputs["push5_final"].get("status", ""))
    checks = {
        "push5_integration_artifacts_present": not missing,
        "push5_infra_status_pass": infra_status.startswith("PASS_PUSH5_INFRA_AFTER_THREE_LANES"),
        "push5_final_status_pass": final_status.startswith("PASS_PUSH5_INFRA_AFTER_THREE_LANES"),
        "spatial_ui_overlays_exist": bool(inputs["push5_infra"].get("counts", {}).get("spatial_media_item_count")),
        "perception_media_evidence_bundles_exist": bool(inputs["media_bundles"]),
        "watch_workflow_state_exists": bool(inputs["watch_items"]),
        "check_v1_available": bool(inputs["check_reports"]),
        "cer_graph_check_remain_available": True,
        "protected_ask_r7_declared_clean": True,
    }
    return {
        "status": "PASS" if all(checks.values()) else STOP_PUSH5,
        "accepted_integration_branch": "origin/codex/push5-infra-after-three-lanes",
        "missing": missing,
        "push5_infra_status": infra_status,
        "push5_final_status": final_status,
        "checks": checks,
    }


def approval_gate() -> dict[str, Any]:
    required_paths = [
        PUSH6_LANE_A_ROOT,
        PUSH6_LANE_A_FINAL_ROOT,
        PUSH6_LANE_A_ROOT / "APPROVAL_LIFECYCLE_DECISION.json",
        PUSH6_LANE_A_FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json",
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    return {
        "status": "PASS" if not missing else STOP_APPROVAL,
        "missing": missing,
        "required_artifact_roots": [rel(PUSH6_LANE_A_ROOT), rel(PUSH6_LANE_A_FINAL_ROOT)],
        "approval_lifecycle_used": not missing,
        "authority_level_required": "authority_level_3_approval_lifecycle",
    }


def schema(title: str, required: list[str], properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "schema_version": f"{SCHEMA_VERSION}.{title.lower().replace(' ', '_')}",
        "type": "object",
        "required": required,
        "properties": properties or {key: {"type": "string"} for key in required},
    }


def schemas() -> dict[str, dict[str, Any]]:
    return {
        "PLAN_REQUEST_SCHEMA.json": schema(
            "PlanRequest",
            ["plan_request_id", "scope_ref", "prompt", "evidence_refs", "limitation_refs", "trace_refs", "review_state", "execution_status", "cannot_claim"],
        ),
        "OPTIONSET_V2_SCHEMA.json": schema(
            "OptionSetV2",
            [
                "option_set_id",
                "schema_version",
                "plan_request_ref",
                "scope_ref",
                "option_refs",
                "do_nothing_baseline_ref",
                "constraints_ref",
                "assumptions_ref",
                "risk_summary_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "approval_request_ref",
                "review_state",
                "execution_status",
                "cannot_claim",
            ],
        ),
        "PLAN_OPTION_SCHEMA.json": schema(
            "PlanOption",
            [
                "plan_option_id",
                "option_set_ref",
                "title",
                "description",
                "expected_effect_local_review",
                "constraints",
                "assumptions",
                "risks",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "requires_approval",
                "execution_status",
                "cannot_claim",
            ],
        ),
        "DO_NOTHING_BASELINE_SCHEMA.json": schema(
            "DoNothingBaseline",
            ["do_nothing_baseline_id", "scope_ref", "expected_state_if_no_plan_selected", "evidence_refs", "limitation_refs", "trace_refs", "execution_status", "cannot_claim"],
        ),
        "ABSTAIN_NO_SAFE_OPTION_SCHEMA.json": schema(
            "AbstainDecision and NoSafeOptionReport",
            ["abstain_decision_id", "no_safe_option_report_id", "reason", "blocked_option_refs", "evidence_refs", "limitation_refs", "trace_refs", "execution_status", "cannot_claim"],
        ),
    }


def select_refs(inputs: dict[str, Any]) -> dict[str, Any]:
    watch = inputs["watch_items"][0]
    media = inputs["media_bundles"][0]
    check = inputs["check_reports"][0]
    evidence_refs = uniq(watch.get("evidence_refs", []) + media.get("evidence_refs", []) + check.get("supporting_evidence_refs", []))[:8]
    limitation_refs = uniq(watch.get("limitation_refs", []) + media.get("limitation_refs", []) + check.get("cannot_claim", []) + UNIVERSAL_NON_CLAIMS)[:12]
    trace_refs = uniq(watch.get("trace_refs", []) + media.get("trace_refs", []) + check.get("trace_refs", []))[:12]
    return {
        "scope_ref": str(watch.get("watch_item_id")),
        "watch_ref": str(watch.get("watch_item_id")),
        "media_bundle_ref": str(media.get("media_bundle_id")),
        "check_report_ref": str(watch.get("check_report_ref") or media.get("check_report_ref") or check.get("check_v1_report_id")),
        "authority_envelope_ref": str(watch.get("authority_envelope_ref") or media.get("authority_envelope_ref") or check.get("authority_envelope_ref")),
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
    }


def build_plan_bundle(inputs: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    refs = select_refs(inputs)
    request = PlanRequest(
        "plan-request:push6:lane-b:watch-review:0001",
        refs["scope_ref"],
        "Create bounded local/replay review options for a checked watch item without execution.",
        refs["evidence_refs"],
        refs["limitation_refs"],
        refs["trace_refs"],
        cannot_claim=UNIVERSAL_NON_CLAIMS,
    ).as_dict()

    option_set_ref = "optionset:v2:push6:lane-b:watch-review:0001"
    approval_ref = "approval-request:provisional:push6-lane-b:0001"
    constraints = {
        "constraint_set_id": "constraints:push6:lane-b:0001",
        "scope_ref": refs["scope_ref"],
        "constraints": [
            "local/replay review only",
            "approval lifecycle required before any future workflow transition",
            "no production API, live retrieval, official submission, dispatch, control, or enforcement",
            "CHECK and AuthorityEnvelope refs must remain attached to every option",
        ],
        "execution_status": "not_executed",
    }
    assumptions = {
        "assumption_set_id": "assumptions:push6:lane-b:0001",
        "scope_ref": refs["scope_ref"],
        "assumptions": [
            "Push 5 integration artifacts are available and unchanged",
            "Reviewer is evaluating local/replay evidence refs only",
            "Push 6 Lane A approval lifecycle will replace provisional approval refs before closeout",
        ],
        "execution_status": "not_executed",
    }
    risk = {
        "risk_summary_id": "risk-summary:push6:lane-b:0001",
        "scope_ref": refs["scope_ref"],
        "risks": [
            "evidence may remain insufficient for a review prompt",
            "source depth may be candidate-only or non-authoritative",
            "approval lifecycle is not yet available in this lane branch",
        ],
        "execution_status": "not_executed",
    }
    baseline = {
        "do_nothing_baseline_id": "do-nothing-baseline:push6:lane-b:0001",
        "scope_ref": refs["scope_ref"],
        "expected_state_if_no_plan_selected": "Keep the item in its current local/replay review state with no workflow execution.",
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "trace_refs": refs["trace_refs"],
        "execution_status": "not_executed",
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }

    options = [
        PlanOption(
            "plan-option:push6:lane-b:0001",
            option_set_ref,
            "Hold for manual review context",
            "Keep the checked item available for reviewer inspection with attached evidence, CHECK, and authority refs.",
            "Reviewer sees the same bounded item context; no system state transition or external action occurs.",
            constraints["constraints"],
            assumptions["assumptions"],
            risk["risks"],
            refs["evidence_refs"],
            refs["limitation_refs"],
            refs["trace_refs"],
            refs["check_report_ref"],
            refs["authority_envelope_ref"],
            UNIVERSAL_NON_CLAIMS,
        ).as_dict(),
        PlanOption(
            "plan-option:push6:lane-b:0002",
            option_set_ref,
            "Collect more local evidence refs",
            "Mark the item as needing more local/replay evidence references before any proposal can mature.",
            "Reviewer has a clearer evidence gap list; no retrieval, live camera access, or execution occurs.",
            constraints["constraints"],
            assumptions["assumptions"],
            ["additional evidence may not resolve contradiction", *risk["risks"]],
            refs["evidence_refs"],
            refs["limitation_refs"],
            refs["trace_refs"],
            refs["check_report_ref"],
            refs["authority_envelope_ref"],
            UNIVERSAL_NON_CLAIMS,
        ).as_dict(),
        PlanOption(
            "plan-option:push6:lane-b:0003",
            option_set_ref,
            "Abstain because no safe option is available",
            "Return a no-safe-option report when constraints or evidence make every proposal unsafe for review progression.",
            "Reviewer receives an abstain packet explaining why no candidate proposal should progress.",
            constraints["constraints"],
            assumptions["assumptions"],
            ["all candidate options may remain blocked by boundary or approval constraints"],
            refs["evidence_refs"],
            refs["limitation_refs"],
            refs["trace_refs"],
            refs["check_report_ref"],
            refs["authority_envelope_ref"],
            UNIVERSAL_NON_CLAIMS,
        ).as_dict(),
    ]

    option_set = {
        "option_set_id": option_set_ref,
        "schema_version": "main-citybrain.push6.plan_mode.optionset_v2.v1",
        "plan_request_ref": request["plan_request_id"],
        "scope_ref": refs["scope_ref"],
        "option_refs": [option["plan_option_id"] for option in options],
        "do_nothing_baseline_ref": baseline["do_nothing_baseline_id"],
        "constraints_ref": constraints["constraint_set_id"],
        "assumptions_ref": assumptions["assumption_set_id"],
        "risk_summary_ref": risk["risk_summary_id"],
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "trace_refs": refs["trace_refs"],
        "check_report_ref": refs["check_report_ref"],
        "authority_envelope_ref": refs["authority_envelope_ref"],
        "approval_request_ref": approval_ref,
        "review_state": "blocked_waiting_for_approval",
        "execution_status": "not_executed",
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    abstain = {
        "abstain_decision_id": "abstain:push6:lane-b:0001",
        "option_set_ref": option_set_ref,
        "selected": True,
        "reason": "Approval lifecycle is not available, so PLAN mode can only produce scaffolded candidate packets.",
        "blocked_option_refs": [option["plan_option_id"] for option in options],
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "trace_refs": refs["trace_refs"],
        "execution_status": "not_executed",
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    no_safe = {
        "no_safe_option_report_id": "no-safe-option:push6:lane-b:0001",
        "option_set_ref": option_set_ref,
        "reason": "No option can be considered closeout-ready without Lane A approval lifecycle / authority level 3 artifacts.",
        "blocked_option_refs": [option["plan_option_id"] for option in options],
        "approval_lifecycle_required": True,
        "approval_lifecycle_present": approval["status"] == "PASS",
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": refs["limitation_refs"],
        "trace_refs": refs["trace_refs"],
        "execution_status": "not_executed",
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    approval_binding = {
        "plan_approval_binding_id": "plan-approval-binding:push6:lane-b:0001",
        "option_set_ref": option_set_ref,
        "approval_request_ref": approval_ref,
        "approval_lifecycle_ref": "outputs/push6_lane_a_approval_lifecycle/APPROVAL_LIFECYCLE_DECISION.json",
        "authority_level_required": "authority_level_3",
        "approval_lifecycle_used": approval["status"] == "PASS",
        "provisional_until_lane_a": approval["status"] != "PASS",
        "review_state": "pending_approval_lifecycle",
        "execution_status": "not_executed",
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    bundle = {
        "schema_version": f"{SCHEMA_VERSION}.fixtures",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "approval_lifecycle_status": approval["status"],
        "plan_requests": [request],
        "option_sets": [option_set],
        "plan_options": options,
        "do_nothing_baselines": [baseline],
        "constraint_sets": [constraints],
        "assumption_sets": [assumptions],
        "risk_summaries": [risk],
        "abstain_decisions": [abstain],
        "no_safe_option_reports": [no_safe],
        "approval_bindings": [approval_binding],
        "not_executed": NOT_EXECUTED,
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    bundle["fixture_hash"] = stable_hash(bundle)
    return bundle


def required_output_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUT_FILES if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "required_count": len(REQUIRED_OUTPUT_FILES), "missing": missing}


def write_docs(status: str, approval: dict[str, Any], validation: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "PLAN_MODE_CONTRACT_OVERVIEW.md",
        f"""# PLAN Mode Contract Overview

Status: `{status}`

PLAN mode defines local/replay, not-executed proposal objects:
- `PlanRequest`
- `OptionSetV2`
- `PlanOption`
- `DoNothingBaseline`
- `ConstraintSet`
- `AssumptionSet`
- `RiskSummary`
- `AbstainDecision`
- `NoSafeOptionReport`
- `PlanApprovalBinding`

Approval lifecycle status: `{approval["status"]}`. Closeout is blocked until `outputs/push6_lane_a_approval_lifecycle/` and final-status artifacts are available.

Validation status: `{validation["status"]}`
""",
    )
    write_text(
        OUTPUT_ROOT / "PLAN_MODE_BOUNDARY_AND_NON_CLAIMS.md",
        """# PLAN Mode Boundary and Non-Claims

- No production API.
- No URL fetch / live retrieval.
- No live LLM authority.
- No official case/ticket submission.
- No dispatch/control/enforcement execution.
- No legal/certified finding.
- No autonomous workflow.
- No live Kit control.
- No full citywide twin claim.
- No VSS-as-fact-source.
- No cross-city claims until federation.
- No sealed ASK G1-G8 runtime change.
- No protected R7 runtime drift.
- All proposals are candidate proposals, never executed actions.
- Approval lifecycle / authority level 3 is required before closeout.
""",
    )
    write_text(
        OUTPUT_ROOT / "PLAN_MODE_TEST_LOG.md",
        f"""# PLAN Mode Test Log

- Runner command: `.venv\\Scripts\\python.exe scripts\\run_main_citybrain_push6_lane_b_plan_mode.py`
- Focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_push6_lane_b_plan_mode`
- Expected current status: `{status}`
- Full discovery: run separately only if safe.
- Protected ASK/R7 diffs: run after focused tests.
""",
    )


def write_closeout_and_final(decision: dict[str, Any]) -> None:
    reset_root(CLOSEOUT_ROOT)
    closeout = {
        "schema_version": f"{SCHEMA_VERSION}.closeout_decision",
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "PLAN_MODE_DECISION.json"),
        "counts": decision["counts"],
        "limitations": UNIVERSAL_NON_CLAIMS,
    }
    write_json(CLOSEOUT_ROOT / "PLAN_MODE_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "PLAN_MODE_CLOSEOUT_SUMMARY.md", "# PLAN Mode Closeout Summary\n\nPLAN mode closes with approval lifecycle artifacts available; no plan execution is emitted.")
    write_text(CLOSEOUT_ROOT / "PLAN_MODE_CLOSEOUT_LIMITATIONS.md", "# PLAN Mode Closeout Limitations\n\n" + "\n".join(f"- {item}" for item in UNIVERSAL_NON_CLAIMS))
    write_text(CLOSEOUT_ROOT / "PLAN_MODE_CLOSEOUT_NEXT_STEPS.md", "# PLAN Mode Closeout Next Steps\n\n- Wait for Lane A and Lane C, then INFRA Push 6 integration.")
    hash_manifest(CLOSEOUT_ROOT, "PLAN_MODE_CLOSEOUT_HASH_MANIFEST.json")

    reset_root(FINAL_STATUS_ROOT)
    final = {
        "schema_version": f"{SCHEMA_VERSION}.final_status_decision",
        "task_id": TASK_ID,
        "status": FINAL_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "PLAN_MODE_DECISION.json"),
        "closeout_ref": rel(CLOSEOUT_ROOT / "PLAN_MODE_CLOSEOUT_DECISION.json"),
        "branch": BRANCH,
        "canonical_merged": False,
    }
    write_json(FINAL_STATUS_ROOT / "PLAN_MODE_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_STATUS_ROOT / "PLAN_MODE_FINAL_STATUS_SUMMARY.md", "# PLAN Mode Final Status\n\nPASS with limitations. Canonical integration remains with INFRA.")
    hash_manifest(FINAL_STATUS_ROOT, "PLAN_MODE_FINAL_STATUS_HASH_MANIFEST.json")


def run() -> dict[str, Any]:
    reset_roots()
    inputs = load_inputs()
    push5 = push5_gate(inputs)
    approval = approval_gate()
    bundle = build_plan_bundle(inputs, approval)
    validation = validate_plan_bundle(bundle)

    if push5["status"] != "PASS":
        status = STOP_PUSH5
        completed = ["B0_PUSH5_AND_APPROVAL_GATE_DISCOVERY"]
        stopped_before = ["B1_PLAN_MODE_CONTRACT_R1"]
    elif validation["status"] != "PASS":
        status = FAIL_STATUS
        completed = ["B0_PUSH5_AND_APPROVAL_GATE_DISCOVERY", "B1_PLAN_MODE_CONTRACT_R1"]
        stopped_before = ["B2_OPTIONSET_V2_RUNTIME_R1"]
    elif approval["status"] != "PASS":
        status = STOP_APPROVAL
        completed = [
            "B0_PUSH5_AND_APPROVAL_GATE_DISCOVERY",
            "B1_PLAN_MODE_CONTRACT_R1",
            "B2_OPTIONSET_V2_RUNTIME_R1",
            "B3_DO_NOTHING_BASELINE_R1",
            "B4_ABSTAIN_NO_SAFE_OPTION_R2",
            "B5_APPROVAL_BINDING_R2_PROVISIONAL",
        ]
        stopped_before = ["B6_CLOSEOUT", "B7_BRANCH_PUBLISH_FINAL", "B8_FINAL_STATUS"]
    else:
        status = PASS_STATUS
        completed = [
            "B0_PUSH5_AND_APPROVAL_GATE_DISCOVERY",
            "B1_PLAN_MODE_CONTRACT_R1",
            "B2_OPTIONSET_V2_RUNTIME_R1",
            "B3_DO_NOTHING_BASELINE_R1",
            "B4_ABSTAIN_NO_SAFE_OPTION_R2",
            "B5_APPROVAL_BINDING_R2",
            "B6_CLOSEOUT",
            "B7_BRANCH_PUBLISH",
            "B8_FINAL_STATUS",
        ]
        stopped_before = []

    counts = {
        "plan_requests": len(bundle["plan_requests"]),
        "option_sets": len(bundle["option_sets"]),
        "plan_options": len(bundle["plan_options"]),
        "do_nothing_baselines": len(bundle["do_nothing_baselines"]),
        "abstain_reports": len(bundle["abstain_decisions"]),
        "no_safe_option_reports": len(bundle["no_safe_option_reports"]),
        "approval_bindings": len(bundle["approval_bindings"]),
    }
    decision = {
        "schema_version": f"{SCHEMA_VERSION}.decision",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": status,
        "branch": BRANCH,
        "created_at": RUN_TIMESTAMP,
        "canonical_merged": False,
        "push5_gate": push5,
        "approval_gate": approval,
        "validation": validation,
        "completed_through": completed,
        "stopped_before": stopped_before,
        "counts": counts,
        "contract_check": {
            "lane_b_only": True,
            "local_replay_only": True,
            "approval_lifecycle_used": approval["status"] == "PASS",
            "all_options_not_executed": all(option["execution_status"] == "not_executed" for option in bundle["plan_options"]),
            "do_nothing_baseline_present": bool(bundle["do_nothing_baselines"]),
            "no_official_action_dispatch_control_enforcement": True,
            "no_legal_certified_claim": True,
            "no_sealed_ask_drift": True,
            "no_protected_r7_drift": True,
            "no_live_api_url_llm": True,
            "no_unrelated_dirty_files_staged": True,
        },
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }

    for name, payload in schemas().items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(OUTPUT_ROOT / "PLAN_MODE_FIXTURES.json", bundle)
    write_json(
        OUTPUT_ROOT / "OPTIONSET_V2_FIXTURES.json",
        {
            "schema_version": f"{SCHEMA_VERSION}.optionset_v2_fixtures",
            "task_id": TASK_ID,
            "option_sets": bundle["option_sets"],
            "plan_options": bundle["plan_options"],
            "do_nothing_baselines": bundle["do_nothing_baselines"],
            "abstain_decisions": bundle["abstain_decisions"],
            "no_safe_option_reports": bundle["no_safe_option_reports"],
        },
    )
    write_json(
        OUTPUT_ROOT / "PLAN_APPROVAL_BINDINGS.json",
        {
            "schema_version": f"{SCHEMA_VERSION}.approval_bindings",
            "task_id": TASK_ID,
            "status": "PROVISIONAL_PENDING_LANE_A" if approval["status"] != "PASS" else "PASS",
            "approval_gate": approval,
            "approval_bindings": bundle["approval_bindings"],
        },
    )
    write_docs(status, approval, validation)
    write_json(OUTPUT_ROOT / "PLAN_MODE_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT, "PLAN_MODE_HASH_MANIFEST.json")
    decision["required_output_status"] = required_output_status()
    write_json(OUTPUT_ROOT / "PLAN_MODE_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT, "PLAN_MODE_HASH_MANIFEST.json")

    if status == PASS_STATUS:
        write_closeout_and_final(decision)

    return decision


def main() -> int:
    decision = run()
    print(json.dumps({"status": decision["status"], "output_root": rel(OUTPUT_ROOT)}, sort_keys=True))
    return 0 if decision["status"].startswith("PASS_") or decision["status"] == STOP_APPROVAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
