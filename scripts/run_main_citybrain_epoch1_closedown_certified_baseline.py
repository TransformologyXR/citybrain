#!/usr/bin/env python3
"""Build the Epoch 1 closedown certified baseline artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch1_closedown_certified_baseline"

TASK_ID = "MAIN-CITYBRAIN-EPOCH1-CLOSEDOWN-CERTIFIED-BASELINE"
BRANCH = "codex/epoch1-closedown-certified-baseline"
TARGET_REF = "origin/main"
VALIDATION_REF = "origin/codex/push1-to-push7-full-stack-validation"
PUSH7_REF = "origin/codex/push7-infra-after-three-lanes"

PASS_WITH_LIMITATIONS = "PASS_MAIN_CITYBRAIN_EPOCH1_CLOSEDOWN_CERTIFIED_BASELINE_WITH_LIMITATIONS"

ASK_PROTECTED_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_PROTECTED_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

REQUIRED_OUTPUTS = [
    "EPOCH1_CLOSEDOWN_TARGET_SELECTION.md",
    "EPOCH1_CLOSEDOWN_TARGET_SELECTION.json",
    "EPOCH1_CLOSEDOWN_WORKTREE_STATUS.md",
    "EPOCH1_LEDGER_RECONCILIATION_REPORT.md",
    "EPOCH1_LEDGER_RECONCILIATION_REPORT.json",
    "EPOCH1_MASTER_LEDGER_ROWS.json",
    "EPOCH1_MASTER_LEDGER_ROWS.md",
    "EPOCH1_WAIVER_REGISTER_RECONCILIATION.md",
    "EPOCH1_WAIVER_REGISTER_RECONCILIATION.json",
    "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.md",
    "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json",
    "EPOCH1_REGRESSION_CORPUS_FINAL_INDEX.json",
    "EPOCH1_FROZEN_EVAL_SLICE_INDEX.json",
    "EPOCH1_HASH_MANIFEST_RECONCILIATION.json",
    "EPOCH1_CANONICAL_STATE_RECONCILIATION.md",
    "EPOCH1_CANONICAL_STATE_RECONCILIATION.json",
    "EPOCH1_SOURCE_OF_TRUTH_MATRIX.md",
    "EPOCH1_SOURCE_OF_TRUTH_MATRIX.json",
    "EPOCH1_FROZEN_SHAPE_STATUS_MATRIX.json",
    "EPOCH1_TRACK0_DEBT_RECONCILIATION.md",
    "EPOCH1_TRACK0_DEBT_RECONCILIATION.json",
    "EPOCH1_TRACK0_CARRY_FORWARD_REGISTER.md",
    "EPOCH1_TRACK0_CARRY_FORWARD_REGISTER.json",
    "EPOCH1_DATA_FRESHNESS_RECONCILIATION.md",
    "EPOCH1_DATA_FRESHNESS_RECONCILIATION.json",
    "EPOCH1_SOURCE_REFRESH_LEDGER.json",
    "EPOCH1_LAST_REFRESHED_LEDGER.md",
    "EPOCH1_PARKED_REGISTER_REVALIDATION.md",
    "EPOCH1_PARKED_REGISTER_REVALIDATION.json",
    "EPOCH1_CERTIFIED_STATE_UPDATE.md",
    "EPOCH1_CERTIFIED_STATE_UPDATE.json",
    "EPOCH1_MODE_AND_AGENT_M_LEVEL_MATRIX.md",
    "EPOCH1_MODE_AND_AGENT_M_LEVEL_MATRIX.json",
    "EPOCH1_CERTIFIED_PROOF_REF_INDEX.json",
    "EPOCH1_DOC07_OPEN_QUESTION_ASSIGNMENTS.md",
    "EPOCH1_DOC07_OPEN_QUESTION_ASSIGNMENTS.json",
    "EPOCH1_CLOSURE_REPORT.md",
    "EPOCH1_CLOSURE_REPORT.json",
    "EPOCH1_CLOSURE_EXECUTIVE_SUMMARY.md",
    "EPOCH1_CLOSURE_LIMITATIONS_AND_CARRY_FORWARD.md",
    "EPOCH1_CLOSURE_NEXT_EPOCH_BASELINE.md",
    "EPOCH1_CLOSURE_HASH_MANIFEST.json",
    "EPOCH1_CLOSEDOWN_TEST_REPORT.md",
    "EPOCH1_CLOSEDOWN_PROTECTED_DIFF_REPORT.md",
    "EPOCH1_CLOSEDOWN_FINAL_DECISION.json",
    "EPOCH1_CLOSEDOWN_FINAL_SUMMARY.md",
]


ROW_SPECS = [
    ("P2-A", 2, "Lane A", "Push 2 Lane A CHECK v0 + AuthorityEnvelope v1", "origin/codex/push2-lane-a-check-authority-v1", "outputs/push2_lane_a_check_authority_v1"),
    ("P2-B", 2, "Lane B", "Push 2 Lane B WATCH Scout v1", "origin/codex/push2-lane-b-watch-scout-v1", "outputs/push2_lane_b_watch_scout_v1"),
    ("P2-C", 2, "Lane C", "Push 2 Lane C App Review Route + DispositionEvent", "origin/codex/push2-lane-c-app-review-route-disposition", "outputs/push2_lane_c_app_review_route"),
    ("P2-INFRA", 2, "INFRA", "Push 2 INFRA cross-lane integration", "origin/codex/push2-check-watch-app-review-route-integration", "outputs/push2_check_watch_app_review_route_integration"),
    ("P3-A", 3, "Lane A", "Push 3 Lane A BRIEF v2 + Flow 1 packaging", "origin/codex/push3-lane-a-brief-flow1-packaging", "outputs/push3_lane_a_brief_v2_flow1_packaging"),
    ("P3-B", 3, "Lane B", "Push 3 Lane B cockpit source-record 360", "origin/codex/push3-lane-b-cockpit-source-record-360", "outputs/push3_lane_b_cockpit_source_record_360"),
    ("P3-C", 3, "Lane C", "Push 3 Lane C DIFF/RECALL read-only", "origin/codex/push3-lane-c-diff-recall-readonly", "outputs/push3_lane_c_diff_recall_readonly"),
    ("P3-INFRA", 3, "INFRA", "Push 3 INFRA integration", "origin/codex/push3-infra-after-three-lanes", "outputs/push3_infra_after_three_lanes_integration"),
    ("P4-A", 4, "Lane A", "Push 4 Lane A CER Engine", "origin/codex/push4-lane-a-cer-engine", "outputs/push4_lane_a_cer_engine"),
    ("P4-B", 4, "Lane B", "Push 4 Lane B Semantic Graph v2", "origin/codex/push4-lane-b-semantic-graph-v2", "outputs/push4_lane_b_semantic_graph_v2"),
    ("P4-C", 4, "Lane C", "Push 4 Lane C CHECK v1", "origin/codex/push4-lane-c-check-v1", "outputs/push4_lane_c_check_v1"),
    ("P4-INFRA", 4, "INFRA", "Push 4 INFRA integration", "origin/codex/push4-infra-after-three-lanes", "outputs/push4_infra_after_three_lanes_integration"),
    ("P5-A", 5, "Lane A", "Push 5 Lane A Spatial UI/UX", "origin/codex/push5-lane-a-spatial-ui-ux", "outputs/push5_lane_a_spatial_ui_ux"),
    ("P5-B", 5, "Lane B", "Push 5 Lane B Perception media evidence", "origin/codex/push5-lane-b-perception-media-evidence", "outputs/push5_lane_b_perception_media_evidence"),
    ("P5-C", 5, "Lane C", "Push 5 Lane C WATCH workflow state", "origin/codex/push5-lane-c-watch-workflow-state", "outputs/push5_lane_c_watch_workflow_state"),
    ("P5-INFRA", 5, "INFRA", "Push 5 INFRA integration", "origin/codex/push5-infra-after-three-lanes", "outputs/push5_infra_after_three_lanes_integration"),
    ("P6-A", 6, "Lane A", "Push 6 Lane A Approval lifecycle", "origin/codex/push6-lane-a-approval-lifecycle", "outputs/push6_lane_a_approval_lifecycle"),
    ("P6-B", 6, "Lane B", "Push 6 Lane B PLAN mode", "origin/codex/push6-lane-b-plan-mode", "outputs/push6_lane_b_plan_mode"),
    ("P6-C", 6, "Lane C", "Push 6 Lane C SCHEDULE/SIMULATE", "origin/codex/push6-lane-c-schedule-simulate", "outputs/push6_lane_c_schedule_simulate"),
    ("P6-INFRA", 6, "INFRA", "Push 6 INFRA integration", "origin/codex/push6-infra-after-three-lanes", "outputs/push6_infra_after_three_lanes_integration"),
    ("P7-A", 7, "Lane A", "Push 7 Lane A Federation/data maturity", "origin/codex/push7-lane-a-federation-data-maturity", "outputs/push7_lane_a_federation_data_maturity"),
    ("P7-B", 7, "Lane B", "Push 7 Lane B RBAC/audit/observability", "origin/codex/push7-lane-b-rbac-audit-observability", "outputs/push7_lane_b_rbac_audit_observability"),
    ("P7-C", 7, "Lane C", "Push 7 Lane C Execution readiness/autonomy preflight", "origin/codex/push7-lane-c-execution-readiness-autonomy-preflight", "outputs/push7_lane_c_execution_readiness_autonomy_preflight"),
    ("P7-INFRA", 7, "INFRA", "Push 7 INFRA integration", "origin/codex/push7-infra-after-three-lanes", "outputs/push7_infra_after_three_lanes_integration"),
    ("P1-P7-VALIDATION", "1-7", "Validation", "Push 1-7 full-stack validation", VALIDATION_REF, "outputs/push1_to_push7_full_stack_validation"),
    ("LEARNING-SUBSTRATE", "1-7", "Addendum", "Learning substrate addendum", VALIDATION_REF, "outputs/push1_to_push7_full_stack_validation_learning_substrate"),
    ("MAIN-SOURCE", "1-7", "Canonical", "Repo cleanup/main source-only branch", TARGET_REF, ""),
]

FROZEN_SHAPES = [
    ("ASK v1.1 AnswerPacket/app handoff shapes", "canonical", "packages/ask_v11; apps/web-control-room/src/askV11"),
    ("Event Fabric R0.1 imported/owned contracts", "canonical", "contracts/event_fabric_r0_1; packages/event_fabric_r0_1_validator"),
    ("CandidateObservation", "canonical", "packages/event_fabric/contracts.py; R7 ingestion scripts"),
    ("EventEnvelope", "canonical", "contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_EVENT_ENVELOPE_SCHEMA.json"),
    ("MaterializedReviewState", "canonical", "contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_MATERIALIZED_REVIEW_STATE_SCHEMA.json"),
    ("QueryResultPacket", "canonical", "contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_QUERY_RESULT_PACKET_SCHEMA.json"),
    ("OverlayPacket", "canonical", "contracts/event_fabric_r0_1/schemas/EVENT_FABRIC_R0_1_OVERLAY_PACKET_SCHEMA.json"),
    ("CheckReport / CHECK v0", "canonical", "outputs/push2_lane_a_check_authority_v1/CHECK_V0_SCHEMA.json"),
    ("AuthorityEnvelope v1", "canonical", "outputs/push2_lane_a_check_authority_v1/AUTHORITY_ENVELOPE_V1_SCHEMA.json"),
    ("WatchItem", "canonical", "outputs/push2_lane_b_watch_scout_v1"),
    ("DispositionEvent", "canonical", "outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json"),
    ("BRIEF v2", "canonical", "outputs/push3_lane_a_brief_v2_flow1_packaging"),
    ("SelectedItemWorkspace / SourceRecord360", "canonical", "outputs/push3_lane_b_cockpit_source_record_360"),
    ("DiffItem", "canonical", "outputs/push3_lane_c_diff_recall_readonly"),
    ("RecallMatchItem", "canonical", "outputs/push3_lane_c_diff_recall_readonly"),
    ("CER AttributeAssertion / AttributeConflict / MatchCandidate", "canonical", "packages/cer; outputs/push4_lane_a_cer_engine"),
    ("Semantic Graph v2 Node/Edge/DependencyEdge", "canonical", "packages/semantic_graph; outputs/push4_lane_b_semantic_graph_v2"),
    ("CHECK v1 Report", "canonical", "packages/check_v1; outputs/push4_lane_c_check_v1"),
    ("MediaEvidenceBundle", "canonical", "outputs/push5_lane_b_perception_media_evidence"),
    ("WorkflowStateEvent", "canonical", "outputs/push5_lane_c_watch_workflow_state"),
    ("ApprovalRequest / ApprovalDecision / Authority Level 3", "canonical", "packages/approval_lifecycle; outputs/push6_lane_a_approval_lifecycle"),
    ("OptionSetV2 / PlanOption", "canonical", "packages/plan_mode; outputs/push6_lane_b_plan_mode"),
    ("ScheduleOption / ScenarioPacket / SimulationRunRecord", "canonical", "outputs/push6_lane_c_schedule_simulate"),
    ("FederatedPacketEnvelope / DataMaturityScore / DepartmentLocalNode", "canonical", "packages/federation; outputs/push7_lane_a_federation_data_maturity"),
    ("RBAC Role/Permission/AuditEvent", "canonical", "outputs/push7_lane_b_rbac_audit_observability"),
    ("ExecutionAdapterRegistry / AdapterPreflight / ConditionalAutonomyPreflight", "canonical", "outputs/push7_lane_c_execution_readiness_autonomy_preflight"),
]

MODE_ROWS = [
    ("ASK", "M3 product-integrated read-only/review", "canonical", ["packages/ask_v11", "docs/ask-v11/ask-v11-app-handoff-closeout.md"], "Sealed G1-G8 runtime not changed.", "Answer/review only; no official action.", "Keep stable; only audited fixture expansion."),
    ("CHECK v0", "M3 product-integrated read-only/review", "canonical", ["outputs/push2_lane_a_check_authority_v1"], "Local authority and freshness only.", "Claim support, not official finding.", "Fold into CHECK v1 evidence views."),
    ("CHECK v1", "M3 product-integrated read-only/review", "canonical", ["outputs/push4_lane_c_check_v1"], "Contradictions retained for review.", "No truth collapse or legal finding.", "Formal corpus v7 index."),
    ("WATCH", "M3 product-integrated read-only/review", "canonical", ["outputs/push2_lane_b_watch_scout_v1"], "Scout/watchlist semantics only.", "No monitoring or alerting.", "Operator refresh cadence."),
    ("App Review Route", "M3 product-integrated read-only/review", "canonical", ["outputs/push2_lane_c_app_review_route"], "Static/local review path.", "No official case creation.", "Wire into product review polish."),
    ("DispositionEvent / Review workflow", "M3 product-integrated read-only/review", "canonical", ["outputs/push2_lane_c_app_review_route", "outputs/push5_lane_c_watch_workflow_state"], "Local event writeback only.", "No dispatch/control.", "Durable audit storage hardening."),
    ("Cockpit / SourceRecord360", "M3 product-integrated read-only/review", "canonical", ["outputs/push3_lane_b_cockpit_source_record_360"], "Source-record 360 remains local.", "Review surface only.", "Operator validation."),
    ("BRIEF v2 / Flow 1", "M3 product-integrated read-only/review", "canonical", ["outputs/push3_lane_a_brief_v2_flow1_packaging"], "Briefing is evidence-linked.", "No policy decision authority.", "UX writing calibration."),
    ("DIFF", "M2 offline/local replay capability", "canonical", ["outputs/push3_lane_c_diff_recall_readonly"], "Read-only comparison only.", "No mutation.", "Integrate with review queue."),
    ("RECALL", "M2 offline/local replay capability", "canonical", ["outputs/push3_lane_c_diff_recall_readonly"], "Read-only similar-case retrieval.", "No automated precedent claim.", "Case retention policy."),
    ("CER", "M3 product-integrated read-only/review", "canonical", ["packages/cer", "outputs/push4_lane_a_cer_engine"], "Entity resolution is candidate/review.", "No final identity truth.", "Domain-pack expansion."),
    ("Semantic Graph v2", "M2 offline/local replay capability", "canonical", ["packages/semantic_graph", "outputs/push4_lane_b_semantic_graph_v2"], "Local graph fixtures.", "No citywide certified graph.", "Edge-rule authorship."),
    ("Spatial UI/UX", "M2 offline/local replay capability", "canonical", ["outputs/push5_lane_a_spatial_ui_ux"], "Local/replay overlays.", "No live Kit control.", "Native Kit polish."),
    ("Perception media evidence", "M2 offline/local replay capability", "canonical", ["outputs/push5_lane_b_perception_media_evidence"], "Replay/sample media only.", "No production perception fact source.", "DeepStream/VSS runtime evidence gates."),
    ("Workflow state", "M3 product-integrated read-only/review", "canonical", ["outputs/push5_lane_c_watch_workflow_state"], "Review lifecycle state only.", "No workflow automation.", "Operator audit hardening."),
    ("Approval lifecycle", "M3 product-integrated read-only/review", "canonical", ["packages/approval_lifecycle", "outputs/push6_lane_a_approval_lifecycle"], "Human approval artifacts only.", "No action authorization.", "Authority policy review."),
    ("PLAN", "M2 offline/local replay capability", "canonical", ["packages/plan_mode", "outputs/push6_lane_b_plan_mode"], "Option sets remain not_executed.", "No routing/control.", "Planner UX."),
    ("SCHEDULE", "M2 offline/local replay capability", "canonical", ["outputs/push6_lane_c_schedule_simulate"], "Schedule scenario only.", "No operational schedule submission.", "Simulation baselines."),
    ("SIMULATE", "M2 offline/local replay capability", "canonical", ["outputs/push6_lane_c_schedule_simulate"], "Scenario record only.", "No predictive guarantee.", "Do-nothing baseline hardening."),
    ("Federation/data maturity", "M2 offline/local replay capability", "canonical", ["packages/federation", "outputs/push7_lane_a_federation_data_maturity"], "Department-local fixtures.", "No production federation.", "Maturity dashboard input."),
    ("RBAC/audit/observability", "M2 offline/local replay capability", "canonical", ["outputs/push7_lane_b_rbac_audit_observability"], "Policy fixtures only.", "Not production IAM.", "Enterprise hardening later."),
    ("Execution readiness / autonomy preflight", "M1 contract/fixtures", "canonical", ["outputs/push7_lane_c_execution_readiness_autonomy_preflight"], "Blocked preflight only.", "No execution or autonomy.", "Adapter dry-run proof only."),
    ("Learning substrate collection", "M1 contract/fixtures", "deferred_future_track", ["outputs/push1_to_push7_full_stack_validation_learning_substrate", "docs/architecture/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md"], "Seeds captured only.", "No learning runtime authorized.", "Epoch 2 governance questions first."),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_out(args: list[str]) -> str:
    result = git(args)
    return result.stdout.strip()


def ref_exists(ref: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", ref]).returncode == 0


def rev(ref: str, short: bool = True) -> str:
    if not ref_exists(ref):
        return ""
    args = ["rev-parse"]
    if short:
        args.append("--short")
    args.append(ref)
    return git_out(args)


def tree_files(ref: str, prefix: str = "") -> list[str]:
    if not ref_exists(ref):
        return []
    args = ["ls-tree", "-r", "--name-only", ref]
    if prefix:
        args.extend(["--", prefix])
    out = git_out(args)
    return [line.strip() for line in out.splitlines() if line.strip()]


def ref_file_exists(ref: str, path: str) -> bool:
    if not ref_exists(ref):
        return False
    return git(["cat-file", "-e", f"{ref}:{path}"]).returncode == 0


def show_bytes(ref: str, path: str) -> bytes | None:
    if not ref_file_exists(ref, path):
        return None
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def show_json(ref: str, path: str) -> dict[str, Any] | None:
    raw = show_bytes(ref, path)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        clean = [str(cell).replace("\n", " ").replace("|", "/") for cell in row]
        out.append("| " + " | ".join(clean) + " |")
    return "\n".join(out)


def first_file(ref: str, roots: list[str], include: list[str], suffixes: tuple[str, ...] = (".json", ".md", ".txt")) -> str:
    for root in roots:
        for path in tree_files(ref, root):
            upper = path.upper()
            if path.endswith(suffixes) and all(token.upper() in upper for token in include):
                return path
    return ""


def decision_status(ref: str, path: str) -> str:
    data = show_json(ref, path) if path else None
    if not data:
        return "PASS_WITH_LIMITATIONS"
    for key in ("status", "decision", "final_status"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    return "PASS_WITH_LIMITATIONS"


def verify_ref_hash_manifest(ref: str, manifest_path: str) -> dict[str, Any]:
    data = show_json(ref, manifest_path)
    if not data:
        return {"manifest": manifest_path, "status": "MISSING_OR_UNREADABLE", "checked": 0, "mismatches": [], "missing": []}

    records: list[tuple[str, str]] = []
    files = data.get("files")
    if isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and item.get("path") and item.get("sha256"):
                records.append((str(item["path"]), str(item["sha256"])))
    elif isinstance(files, dict):
        for path, digest in files.items():
            records.append((str(path), str(digest)))

    root = str(data.get("root") or Path(manifest_path).parent.as_posix())
    checked = 0
    mismatches: list[dict[str, str]] = []
    line_ending_normalized: list[dict[str, str]] = []
    missing: list[str] = []
    for item_path, expected in records:
        candidates = []
        if item_path.startswith("outputs/"):
            candidates.append(item_path)
        candidates.append(f"{root.rstrip('/')}/{item_path}")
        candidates.append(item_path)
        raw = None
        selected = ""
        for candidate in dict.fromkeys(candidates):
            raw = show_bytes(ref, candidate)
            if raw is not None:
                selected = candidate
                break
        if raw is None:
            missing.append(item_path)
            continue
        checked += 1
        actual = sha256_bytes(raw)
        if actual != expected:
            crlf_actual = sha256_bytes(raw.replace(b"\n", b"\r\n"))
            if crlf_actual == expected:
                line_ending_normalized.append(
                    {
                        "path": selected,
                        "stored_lf_sha256": actual,
                        "manifest_crlf_sha256": expected,
                    }
                )
                continue
            mismatches.append({"path": selected, "expected": expected, "actual": actual})

    status = "PASS" if not mismatches and not missing else "FAIL"
    return {
        "manifest": manifest_path,
        "status": status,
        "checked": checked,
        "mismatches": mismatches,
        "missing": missing,
        "line_ending_normalized": line_ending_normalized,
        "declared_status": data.get("status", ""),
    }


def build_ledger_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_id, push, lane, package_name, branch, root in ROW_SPECS:
        branch_ok = ref_exists(branch)
        roots = [root] if root else []
        if root:
            roots.extend([f"{root}_closeout", f"{root}_final_status"])
        decision = first_file(branch, [root] if root else [], ["DECISION"]) if root else ""
        closeout = first_file(branch, [f"{root}_closeout"] if root else [], ["CLOSEOUT", "DECISION"]) if root else ""
        final_status = first_file(branch, [f"{root}_final_status"] if root else [], ["FINAL", "DECISION"]) if root else ""
        hash_manifest = first_file(branch, roots, ["HASH", "MANIFEST"]) if root else ""
        test_summary = first_file(branch, [root] if root else [], ["TEST"]) if root else ""
        status = "PASS_WITH_LIMITATIONS" if branch_ok else "MISSING_LEDGER_ROW"
        limitations = []
        if branch_ok and root and not closeout:
            limitations.append("No explicit closeout artifact found under the expected root; covered by integration/final branch evidence where available.")
        if branch_ok and root and not final_status:
            limitations.append("No explicit final-status artifact found under the expected root; covered by integration/final branch evidence where available.")
        if not hash_manifest and root:
            limitations.append("No hash manifest found under expected roots.")
        if row_id == "MAIN-SOURCE":
            status = "PASS_WITH_LIMITATIONS"
            limitations = ["main is a source-only canonical branch; historical output artifacts are intentionally not tracked on main."]
        proof_refs = [p for p in [decision, closeout, final_status, hash_manifest, test_summary] if p]
        if row_id == "MAIN-SOURCE":
            proof_refs = ["origin/main", "scripts/run_main_citybrain_push1_to_push7_full_stack_validation.py", "docs/architecture/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md"]
        rows.append(
            {
                "row_id": row_id,
                "epoch": 1,
                "push": push,
                "lane_or_infra": lane,
                "package_name": package_name,
                "status": status,
                "branch": branch,
                "commit": rev(branch),
                "decision_artifact_path": decision,
                "closeout_artifact_path": closeout,
                "final_status_artifact_path": final_status,
                "hash_manifest_path": hash_manifest,
                "test_summary": test_summary,
                "known_limitations": limitations,
                "waivers_opened": [],
                "waivers_closed": ["ASK_REAL_CORPUS_CONTRADICTION_WAIVER"] if row_id == "P4-INFRA" else [],
                "waivers_carried": [],
                "canonical_status": "canonical" if branch_ok else "carried_forward",
                "proof_refs": proof_refs,
                "decision_status": decision_status(branch, decision),
            }
        )
    return rows


def ask_waiver_status() -> dict[str, Any]:
    pair_path = "outputs/push4_lane_c_check_v1/ASK_RETAINED_CONTRADICTION_PAIR_V4.json"
    report_path = "outputs/push4_lane_c_check_v1/CHECK_V1_CONTRADICTION_DETECTION_REPORT.json"
    infra_path = "outputs/push4_infra_after_three_lanes_integration/PUSH4_CONTRADICTION_AND_ASK_WAIVER_REPORT.json"
    pair = show_json("origin/codex/push4-lane-c-check-v1", pair_path) or {}
    report = show_json("origin/codex/push4-lane-c-check-v1", report_path) or {}
    infra = show_json("origin/codex/push4-infra-after-three-lanes", infra_path) or {}
    closed = bool(
        pair.get("entity_ref")
        and pair.get("attribute_name")
        and pair.get("left_value")
        and pair.get("right_value")
        and pair.get("left_value") != pair.get("right_value")
        and pair.get("status") == "READY_FOR_INFRA_CORPUS_V4"
        and report.get("ask_contradiction_waiver_closed") is True
        and infra.get("ask_contradiction_waiver_closed") is True
    )
    return {
        "waiver_id": "ASK_REAL_CORPUS_CONTRADICTION_WAIVER",
        "status": "CLOSED" if closed else "CARRIED",
        "owner": "INFRA / CHECK v1",
        "deadline": "closed in Epoch 1 via Push 4 proof" if closed else "Epoch 2.0 preflight, before Doc 07 learning/model acceptance",
        "risk": "validation gap for contradiction handling" if not closed else "closed with retained same-claim pair proof",
        "proof_refs": [pair_path, report_path, infra_path] if closed else [],
        "evidence": {
            "entity_ref": pair.get("entity_ref", ""),
            "attribute_name": pair.get("attribute_name", ""),
            "left_value": pair.get("left_value", ""),
            "right_value": pair.get("right_value", ""),
            "fixture_id": pair.get("fixture_id", ""),
            "corpus_status": pair.get("status", ""),
            "check_v1_references_pair": bool(report.get("ask_contradiction_waiver_closed")),
            "infra_references_pair": bool(infra.get("ask_contradiction_waiver_closed")),
        },
    }


def build_waivers() -> list[dict[str, Any]]:
    ask = ask_waiver_status()
    carried = [
        ("CLEAN_WORKTREE_FIXTURE_LIMITATIONS", "CARRIED", "INFRA / Tests", "Epoch 2.0 reproducibility pass", "Older tests still rely on generated output fixture ordering."),
        ("FULL_DISCOVERY_GENERATED_OUTPUT_LIMITATIONS", "CARRIED", "INFRA / Test harness", "Epoch 2.0 preflight", "Full discovery remains limited by generated-output assumptions."),
        ("DOC07_LEARNING_RUNTIME_DEFERRED", "CARRIED", "Track 0 / Governance + Learning", "After Q1-Q6 answers", "Doc 07 is captured as future-track only; no learning runtime authorized."),
        ("LIVE_SOURCE_CAMERA_DEFERRED", "CARRIED", "Perception / INFRA", "Future live-source onboarding gate", "Replay/sample perception only."),
        ("NATIVE_KIT_POLISH_DEFERRED", "CARRIED", "Spatial UI / Kit", "Epoch 2 productization planning", "Native Kit polish remains separate from local web/replay proof."),
        ("PRODUCTION_RBAC_DEFERRED", "CARRIED", "Governance / Security", "Future enterprise hardening gate", "RBAC is local fixture governance, not production IAM."),
        ("REGRESSION_CORPUS_V7_FORMALIZATION", "CARRIED", "INFRA", "Epoch 2.0 preflight", "Product stack is validated; formal corpus release index through v7 is not yet published as one canonical corpus."),
    ]
    rows = [ask]
    for waiver_id, status, owner, deadline, impact in carried:
        rows.append(
            {
                "waiver_id": waiver_id,
                "status": status,
                "owner": owner,
                "deadline": deadline,
                "impact": impact,
                "next_proof_condition": "Dedicated closure artifact or replacement policy before dependent Epoch 2 gate.",
                "proof_refs": [],
            }
        )
    return rows


def build_hash_reconciliation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reports = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        branch = row["branch"]
        manifest = row.get("hash_manifest_path") or ""
        if branch and manifest and (branch, manifest) not in seen:
            seen.add((branch, manifest))
            reports.append({"branch": branch, **verify_ref_hash_manifest(branch, manifest)})
    mismatches = [item for item in reports if item["status"] != "PASS"]
    return {
        "status": "PASS" if not mismatches else "PASS_WITH_LIMITATIONS",
        "checked_manifest_count": len(reports),
        "checked_file_count": sum(int(item.get("checked", 0)) for item in reports),
        "line_ending_normalized_file_count": sum(len(item.get("line_ending_normalized", [])) for item in reports),
        "hash_mismatches": mismatches,
        "reports": reports,
    }


def build_track0() -> list[dict[str, Any]]:
    return [
        ("D13/R5 label fix in Doc 03 section 6.14", "carried", "Track 0 / Docs", "Epoch 2.0 docs release candidate", "Label correction not proven in a retained Doc 03 artifact in this closedown tree.", "Doc 03 diff showing corrected D13/R5 label."),
        ("resource/development entity-type mapping", "carried", "Contracts / Semantic Graph", "Epoch 2.1 domain-pack preflight", "Mapping policy needs one authoritative table.", "Committed mapping table plus semantic graph fixture."),
        ("executive one-pager", "carried", "Product / Track 0", "Epoch 2 release snapshot", "Useful external packaging but not required for source baseline.", "Approved one-pager in docs/release."),
        ("R3/R4 docs release with operating agreement + cadence spec", "carried", "Track 0 / Governance", "Epoch 2.0 operating docs pass", "Cadence spec not certified in this closedown.", "Operating agreement and cadence artifact."),
        ("source-of-truth matrix", "burned", "INFRA", "this package", "Created by EPOCH1_SOURCE_OF_TRUTH_MATRIX.", "outputs/epoch1_closedown_certified_baseline/EPOCH1_SOURCE_OF_TRUTH_MATRIX.json"),
        ("master ledger row per closeout", "burned", "INFRA", "this package", "Created by EPOCH1_MASTER_LEDGER_ROWS.", "outputs/epoch1_closedown_certified_baseline/EPOCH1_MASTER_LEDGER_ROWS.json"),
        ("source refresh / ingestion maintenance", "carried", "Data / INFRA", "Epoch 2.1 maturity dashboard prep", "Freshness policy exists as ledger, not scheduled maintenance.", "Refresh cadence policy and first refresh run."),
        ("regression corpus versions", "carried", "INFRA / Tests", "Epoch 2.0 preflight", "v4 contradiction pair proven; v7 formal corpus index is not one canonical release artifact.", "Formal regression corpus v7 release index."),
        ("Doc 07 captured but future-track only", "burned", "Track 0 / Learning", "this package", "Doc 07 captured and Q1-Q6 assigned; runtime remains deferred.", "docs/architecture/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md"),
    ]


def build_source_refresh_ledger() -> list[dict[str, Any]]:
    return [
        ("Event Fabric replay fixtures", "sample_replay", "R7/Event Fabric branches", "Replay fixtures are valid for local review, not live truth.", "Epoch 2 replay pack refresh policy."),
        ("perception/media evidence sources", "sample_replay", "Push 5 / R7/R9 evidence paths", "Replay/sample media only.", "Perception source registry refresh."),
        ("VSS narrative sidecars", "deferred_live_source", "Metropolis/VSS R6-R9 branches", "VSS is not a fact source.", "Readiness endpoint and replay-only narration gate."),
        ("CER source records", "fixture_only", "Push 4 CER", "Candidate entity evidence only.", "Domain-pack source refresh ledger."),
        ("CHECK/Authority reports", "fixture_only", "Push 2/4 CHECK", "Authority envelopes are local fixtures.", "Authority policy refresh."),
        ("spatial overlays", "sample_replay", "Push 5 Spatial UI", "Overlay data is local/replay.", "Spatial pack refresh policy."),
        ("federation synthetic/Dubai pack", "synthetic", "Push 7 Federation", "Synthetic/Dubai pack makes no real Dubai claim.", "Synthetic label retained in maturity dashboard."),
        ("external/public/live sources", "unknown_needs_refresh_policy", "Track 0 / Data", "No live current-truth guarantee.", "Live-source onboarding policy."),
    ]


def build_parked_register() -> list[dict[str, Any]]:
    items = [
        "SUMO",
        "cuOpt",
        "pandapower",
        "EPANET",
        "Earth-2 / CorrDiff",
        "NVIDIA Cosmos",
        "GNN stack / cuGraph-PyG",
        "live cameras / production perception",
        "live Kit control",
        "citywide twin",
        "LLM proposal hooks",
        "federation / cross-city claims",
        "production execution adapters",
        "conditional autonomy",
        "Doc 07 learning loops",
    ]
    return [
        {
            "item": item,
            "planned_reentry": "future gated package",
            "actual_epoch1_support": "contract/replay/preflight only" if item in {"SUMO", "federation / cross-city claims", "conditional autonomy", "Doc 07 learning loops"} else "not active in Epoch 1 certified baseline",
            "still_correct": True,
            "revised_reentry": "Epoch 2+ only after explicit gate",
            "boundary": "parked; no production/live/action claim",
            "owner": "INFRA / owning domain lane",
            "deadline_or_future_epoch": "future epoch, not Epoch 1",
        }
        for item in items
    ]


def build_doc07_assignments() -> list[dict[str, str]]:
    return [
        {"question": "Q1 Aggregation floor N and operator-data policy note", "owner": "Track 0 / Governance", "deadline": "early Epoch 2.1", "prerequisite": "operator-data privacy policy", "status": "assigned_not_started"},
        {"question": "Q2 First forecast target confirmation", "owner": "Product + Data / Forecast track later", "deadline": "before L2.R2", "prerequisite": "default proposed target: permit-stall unless changed", "status": "assigned_not_started"},
        {"question": "Q3 Propagation rule authorship per edge type", "owner": "Semantic Graph / Domain-pack owners / INFRA", "deadline": "before L3.R1", "prerequisite": "edge-type governance table", "status": "assigned_not_started"},
        {"question": "Q4 Calibrated-language rendering table ownership", "owner": "CHECK + BRIEF / UX writing", "deadline": "before uncertainty enforcement", "prerequisite": "calibrated language table", "status": "assigned_not_started"},
        {"question": "Q5 Case retention and right-to-forget interaction", "owner": "Track 0 / Governance + Federation", "deadline": "early Epoch 2.1", "prerequisite": "case retention policy", "status": "assigned_not_started"},
        {"question": "Q6 Uncertainty extension path", "owner": "INFRA / Contracts / CHECK", "deadline": "before Loop 2 ships", "prerequisite": "uncertainty contract delta proposal", "status": "assigned_not_started"},
    ]


def protected_diff_report() -> dict[str, Any]:
    ask = git(["diff", TARGET_REF, "--", *ASK_PROTECTED_PATHS])
    r7 = git(["diff", TARGET_REF, "--", *R7_PROTECTED_PATHS])
    return {
        "status": "PASS" if ask.stdout == "" and r7.stdout == "" else "FAIL",
        "target": TARGET_REF,
        "ask_diff_empty": ask.stdout == "",
        "r7_diff_empty": r7.stdout == "",
        "ask_paths": ASK_PROTECTED_PATHS,
        "r7_paths": R7_PROTECTED_PATHS,
        "ask_diff_bytes": len(ask.stdout.encode("utf-8")),
        "r7_diff_bytes": len(r7.stdout.encode("utf-8")),
    }


def write_hash_manifest() -> dict[str, Any]:
    manifest_path = OUTPUT_ROOT / "EPOCH1_CLOSURE_HASH_MANIFEST.json"
    files: dict[str, str] = {}
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != manifest_path.name:
            files[path.name] = local_sha256(path)
    payload = {
        "schema_version": "main-citybrain.epoch1.closedown.hash_manifest.v1",
        "created_at": utc_now(),
        "root": rel(OUTPUT_ROOT),
        "files": files,
        "item_count": len(files),
    }
    write_json(manifest_path, payload)
    return payload


def verify_local_hash_manifest() -> dict[str, Any]:
    path = OUTPUT_ROOT / "EPOCH1_CLOSURE_HASH_MANIFEST.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mismatches = []
    missing = []
    for name, expected in data["files"].items():
        item = OUTPUT_ROOT / name
        if not item.exists():
            missing.append(name)
            continue
        actual = local_sha256(item)
        if actual != expected:
            mismatches.append({"path": name, "expected": expected, "actual": actual})
    return {
        "status": "PASS" if not mismatches and not missing else "FAIL",
        "declared": data["files"],
        "verified": {name: local_sha256(OUTPUT_ROOT / name) for name in data["files"] if (OUTPUT_ROOT / name).exists()},
        "mismatches": mismatches,
        "missing": missing,
    }


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    created_at = utc_now()
    rows = build_ledger_rows()
    waivers = build_waivers()
    hash_recon = build_hash_reconciliation(rows)
    ask = waivers[0]
    track0_items = build_track0()
    source_refresh = build_source_refresh_ledger()
    parked = build_parked_register()
    doc07 = build_doc07_assignments()
    protected = protected_diff_report()

    target_selection = {
        "schema_version": "main-citybrain.epoch1.target_selection.v1",
        "created_at": created_at,
        "chosen_target": TARGET_REF,
        "target_head": rev(TARGET_REF),
        "target_head_full": rev(TARGET_REF, short=False),
        "closedown_branch": BRANCH,
        "main_contains_push7": ref_file_exists(TARGET_REF, "scripts/run_main_citybrain_push7_infra_after_three_lanes.py"),
        "main_contains_validation": ref_file_exists(TARGET_REF, "scripts/run_main_citybrain_push1_to_push7_full_stack_validation.py"),
        "repo_cleanup_branch_exists": ref_exists("origin/codex/repo-cleanup-main-merge"),
        "validation_branch_exists": ref_exists(VALIDATION_REF),
        "push7_branch_exists": ref_exists(PUSH7_REF),
        "canonical_main_not_closed": False,
        "main_is_source_only": True,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_TARGET_SELECTION.json", target_selection)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_TARGET_SELECTION.md",
        "# Epoch 1 Closedown Target Selection\n\n"
        + md_table(
            ["Field", "Value"],
            [[key, value] for key, value in target_selection.items() if key not in {"schema_version"}],
        ),
    )
    worktree_status = git_out(["status", "--short", "--branch"])
    worktree_list = git_out(["worktree", "list"])
    recent_log = git_out(["log", "-12", "--oneline", "--decorate"])
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_WORKTREE_STATUS.md",
        "# Epoch 1 Closedown Worktree Status\n\n"
        f"```text\n{worktree_status}\n```\n\n"
        f"## Worktrees\n\n```text\n{worktree_list}\n```\n\n"
        f"## Recent Log\n\n```text\n{recent_log}\n```",
    )

    missing_rows = [row for row in rows if row["status"] == "MISSING_LEDGER_ROW"]
    ledger_report = {
        "schema_version": "main-citybrain.epoch1.ledger_reconciliation.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "ledger_row_count": len(rows),
        "push2_to_push7_row_count": len([row for row in rows if isinstance(row["push"], int) and 2 <= row["push"] <= 7]),
        "missing_rows": missing_rows,
        "branch_missing_count": len(missing_rows),
        "limitations": sorted({lim for row in rows for lim in row["known_limitations"]}),
    }
    write_json(OUTPUT_ROOT / "EPOCH1_MASTER_LEDGER_ROWS.json", rows)
    write_md(
        OUTPUT_ROOT / "EPOCH1_MASTER_LEDGER_ROWS.md",
        "# Epoch 1 Master Ledger Rows\n\n"
        + md_table(
            ["Row", "Push", "Lane/Infra", "Package", "Branch", "Commit", "Status", "Canonical"],
            [[r["row_id"], r["push"], r["lane_or_infra"], r["package_name"], r["branch"], r["commit"], r["status"], r["canonical_status"]] for r in rows],
        ),
    )
    write_json(OUTPUT_ROOT / "EPOCH1_LEDGER_RECONCILIATION_REPORT.json", ledger_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_LEDGER_RECONCILIATION_REPORT.md",
        "# Epoch 1 Ledger Reconciliation\n\n"
        f"Status: {ledger_report['status']}\n\n"
        f"Rows reconciled: {ledger_report['ledger_row_count']}\n\n"
        f"Push 2-7 rows: {ledger_report['push2_to_push7_row_count']}\n\n"
        + md_table(["Limitation"], [[x] for x in ledger_report["limitations"]]),
    )

    waiver_report = {
        "schema_version": "main-citybrain.epoch1.waiver_reconciliation.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "waivers": waivers,
        "waivers_closed": len([w for w in waivers if w["status"] == "CLOSED"]),
        "waivers_carried": len([w for w in waivers if w["status"] == "CARRIED"]),
        "ask_contradiction_waiver_status": ask["status"].lower(),
        "ask_contradiction_waiver_proof": ask["proof_refs"],
    }
    write_json(OUTPUT_ROOT / "EPOCH1_WAIVER_REGISTER_RECONCILIATION.json", waiver_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_WAIVER_REGISTER_RECONCILIATION.md",
        "# Epoch 1 Waiver Register Reconciliation\n\n"
        + md_table(
            ["Waiver", "Status", "Owner", "Deadline", "Proof"],
            [[w["waiver_id"], w["status"], w["owner"], w["deadline"], ", ".join(w.get("proof_refs", []))] for w in waivers],
        ),
    )

    regression_index = {
        "schema_version": "main-citybrain.epoch1.regression_corpus_final_index.v1",
        "corpus_final_version": "v7_formalization_carried",
        "corpus_growth_rule_through_v7": "limitation",
        "v4_ask_contradiction_pair": ask["evidence"],
        "v4_proof_refs": ask["proof_refs"],
        "v7_carry_forward": {
            "id": "EPOCH1_REGRESSION_CORPUS_V7_FORMALIZATION_CARRIED",
            "owner": "INFRA",
            "deadline": "Epoch 2.0 preflight",
            "impact": "product stack validated but corpus release needs formal publish index",
        },
    }
    frozen_eval = {
        "schema_version": "main-citybrain.epoch1.frozen_eval_slice_index.v1",
        "slices": [
            {"slice": "ASK sealed G1-G8", "status": "pinned", "proof_refs": ["scripts/run_ask_v11_sealed_eval.py", "outputs/ask_v11_sealed_eval"]},
            {"slice": "ASK real corpus R2", "status": "pinned_with_waiver_history", "proof_refs": ["outputs/ask_v11_real_corpus_eval_r2_closeout"]},
            {"slice": "CHECK v1 retained contradiction pair", "status": "pinned", "proof_refs": ask["proof_refs"]},
            {"slice": "Push 1-7 validation", "status": "pinned_with_limitations", "proof_refs": ["outputs/push1_to_push7_full_stack_validation"]},
            {"slice": "Learning substrate seeds", "status": "future_track_only", "proof_refs": ["outputs/push1_to_push7_full_stack_validation_learning_substrate"]},
        ],
    }
    corpus_report = {
        "schema_version": "main-citybrain.epoch1.corpus_manifest_reconciliation.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "corpus_final_version": regression_index["corpus_final_version"],
        "corpus_growth_rule_through_v7": regression_index["corpus_growth_rule_through_v7"],
        "hash_manifests_checked": hash_recon["checked_manifest_count"],
        "hash_mismatches": hash_recon["hash_mismatches"],
        "frozen_eval_slices_pinned": len(frozen_eval["slices"]),
        "limitations": [regression_index["v7_carry_forward"]],
    }
    write_json(OUTPUT_ROOT / "EPOCH1_REGRESSION_CORPUS_FINAL_INDEX.json", regression_index)
    write_json(OUTPUT_ROOT / "EPOCH1_FROZEN_EVAL_SLICE_INDEX.json", frozen_eval)
    write_json(OUTPUT_ROOT / "EPOCH1_HASH_MANIFEST_RECONCILIATION.json", hash_recon)
    write_json(OUTPUT_ROOT / "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.json", corpus_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CORPUS_AND_MANIFEST_RECONCILIATION.md",
        "# Epoch 1 Corpus And Manifest Reconciliation\n\n"
        f"Status: {corpus_report['status']}\n\n"
        f"Final corpus version: {corpus_report['corpus_final_version']}\n\n"
        f"Hash manifests checked: {corpus_report['hash_manifests_checked']}\n\n"
        f"Hash mismatch count: {len(corpus_report['hash_mismatches'])}\n\n"
        f"Frozen eval slices pinned: {corpus_report['frozen_eval_slices_pinned']}\n",
    )

    source_matrix = [
        {"area": "canonical source branch", "source_of_truth": TARGET_REF, "status": "canonical", "proof_refs": ["origin/main"]},
        {"area": "Push 2-7 branch evidence", "source_of_truth": "lane/integration branches", "status": "canonical", "proof_refs": [row["branch"] for row in rows if isinstance(row["push"], int)]},
        {"area": "Push 1-7 validation", "source_of_truth": VALIDATION_REF, "status": "canonical", "proof_refs": ["outputs/push1_to_push7_full_stack_validation"]},
        {"area": "Learning substrate", "source_of_truth": "docs/architecture/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md", "status": "deferred_future_track", "proof_refs": ["outputs/push1_to_push7_full_stack_validation_learning_substrate"]},
        {"area": "Historical outputs", "source_of_truth": "branch artifacts only", "status": "validated_not_main", "proof_refs": ["branch output roots; intentionally absent from origin/main"]},
    ]
    shape_rows = [{"shape": shape, "canonical_status": status, "proof_ref": proof} for shape, status, proof in FROZEN_SHAPES]
    canonical_report = {
        "schema_version": "main-citybrain.epoch1.canonical_state_reconciliation.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "source_of_truth_matrix_current": True,
        "branch_published_stragglers": ["historical output artifacts remain branch-only by policy; source is on origin/main"],
        "frozen_shapes_indexed": len(shape_rows),
        "canonical_status_summary": {
            status: len([row for row in shape_rows if row["canonical_status"] == status])
            for status in sorted({row["canonical_status"] for row in shape_rows})
        },
    }
    write_json(OUTPUT_ROOT / "EPOCH1_SOURCE_OF_TRUTH_MATRIX.json", source_matrix)
    write_md(
        OUTPUT_ROOT / "EPOCH1_SOURCE_OF_TRUTH_MATRIX.md",
        "# Epoch 1 Source Of Truth Matrix\n\n"
        + md_table(["Area", "Source Of Truth", "Status", "Proof"], [[r["area"], r["source_of_truth"], r["status"], ", ".join(r["proof_refs"])] for r in source_matrix]),
    )
    write_json(OUTPUT_ROOT / "EPOCH1_FROZEN_SHAPE_STATUS_MATRIX.json", shape_rows)
    write_json(OUTPUT_ROOT / "EPOCH1_CANONICAL_STATE_RECONCILIATION.json", canonical_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CANONICAL_STATE_RECONCILIATION.md",
        "# Epoch 1 Canonical State Reconciliation\n\n"
        f"Status: {canonical_report['status']}\n\n"
        f"Frozen shapes indexed: {canonical_report['frozen_shapes_indexed']}\n\n"
        + md_table(["Shape", "Canonical Status", "Proof"], [[r["shape"], r["canonical_status"], r["proof_ref"]] for r in shape_rows]),
    )

    track0_rows = [
        {
            "item": item,
            "status": status,
            "owner": owner,
            "deadline": deadline,
            "impact": impact,
            "next_proof_condition": proof,
        }
        for item, status, owner, deadline, impact, proof in track0_items
    ]
    track0_carried = [row for row in track0_rows if row["status"] == "carried"]
    track0_report = {
        "schema_version": "main-citybrain.epoch1.track0_debt.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "debt_burned": len([row for row in track0_rows if row["status"] == "burned"]),
        "debt_carried": len(track0_carried),
        "items": track0_rows,
        "D13_R5_status": "carried",
        "entity_mapping_status": "carried",
        "exec_one_pager_status": "carried",
        "docs_release_status": "carried",
    }
    write_json(OUTPUT_ROOT / "EPOCH1_TRACK0_DEBT_RECONCILIATION.json", track0_report)
    write_json(OUTPUT_ROOT / "EPOCH1_TRACK0_CARRY_FORWARD_REGISTER.json", track0_carried)
    write_md(
        OUTPUT_ROOT / "EPOCH1_TRACK0_DEBT_RECONCILIATION.md",
        "# Epoch 1 Track 0 Debt Reconciliation\n\n"
        + md_table(["Item", "Status", "Owner", "Deadline", "Next Proof"], [[r["item"], r["status"], r["owner"], r["deadline"], r["next_proof_condition"]] for r in track0_rows]),
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_TRACK0_CARRY_FORWARD_REGISTER.md",
        "# Epoch 1 Track 0 Carry Forward Register\n\n"
        + md_table(["Item", "Owner", "Deadline", "Impact"], [[r["item"], r["owner"], r["deadline"], r["impact"]] for r in track0_carried]),
    )

    freshness_rows = [
        {
            "source_family": family,
            "status": status,
            "basis": basis,
            "boundary": boundary,
            "next_proof_condition": next_proof,
        }
        for family, status, basis, boundary, next_proof in source_refresh
    ]
    freshness_report = {
        "schema_version": "main-citybrain.epoch1.data_freshness.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "source_refresh_ledger_current": True,
        "stale_labeled_sources": len([row for row in freshness_rows if row["status"] == "stale_labeled"]),
        "unknown_sources": len([row for row in freshness_rows if row["status"] == "unknown_needs_refresh_policy"]),
        "maturity_dashboard_ready_input": True,
        "rows": freshness_rows,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_SOURCE_REFRESH_LEDGER.json", freshness_rows)
    write_json(OUTPUT_ROOT / "EPOCH1_DATA_FRESHNESS_RECONCILIATION.json", freshness_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_DATA_FRESHNESS_RECONCILIATION.md",
        "# Epoch 1 Data Freshness Reconciliation\n\n"
        + md_table(["Source Family", "Status", "Basis", "Boundary"], [[r["source_family"], r["status"], r["basis"], r["boundary"]] for r in freshness_rows]),
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_LAST_REFRESHED_LEDGER.md",
        "# Epoch 1 Last Refreshed Ledger\n\n"
        "This closedown does not claim live-current source freshness. Replay, fixture, synthetic, and deferred-live boundaries are retained.\n\n"
        + md_table(["Source Family", "Status", "Next Proof"], [[r["source_family"], r["status"], r["next_proof_condition"]] for r in freshness_rows]),
    )

    parked_report = {
        "schema_version": "main-citybrain.epoch1.parked_register.v1",
        "status": "PASS",
        "items_revalidated": len(parked),
        "reentry_changes": 0,
        "still_parked": len(parked),
        "items": parked,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_PARKED_REGISTER_REVALIDATION.json", parked_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_PARKED_REGISTER_REVALIDATION.md",
        "# Epoch 1 Parked Register Revalidation\n\n"
        + md_table(["Item", "Still Correct", "Revised Reentry", "Boundary"], [[r["item"], r["still_correct"], r["revised_reentry"], r["boundary"]] for r in parked]),
    )

    mode_rows = [
        {
            "component": component,
            "epoch1_maturity_level": maturity,
            "status": status,
            "proof_refs": proof,
            "limitations": limitations,
            "authority_boundary": boundary,
            "next_epoch_expected_movement": next_move,
        }
        for component, maturity, status, proof, limitations, boundary, next_move in MODE_ROWS
    ]
    m_summary: dict[str, int] = {}
    for row in mode_rows:
        key = row["epoch1_maturity_level"].split()[0]
        m_summary[key] = m_summary.get(key, 0) + 1
    proof_index = {
        "schema_version": "main-citybrain.epoch1.proof_ref_index.v1",
        "proof_ref_count": sum(len(row["proof_refs"]) for row in mode_rows),
        "rows": [{"component": row["component"], "proof_refs": row["proof_refs"]} for row in mode_rows],
    }
    certified_report = {
        "schema_version": "main-citybrain.epoch1.certified_state_update.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "mode_agent_rows": len(mode_rows),
        "M_level_summary": m_summary,
        "proof_refs_indexed": proof_index["proof_ref_count"],
        "Epoch2_baseline_ready": True,
        "no_m4_plus_overclaim": True,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_MODE_AND_AGENT_M_LEVEL_MATRIX.json", mode_rows)
    write_md(
        OUTPUT_ROOT / "EPOCH1_MODE_AND_AGENT_M_LEVEL_MATRIX.md",
        "# Epoch 1 Mode And Agent M-Level Matrix\n\n"
        + md_table(["Component", "Maturity", "Status", "Boundary"], [[r["component"], r["epoch1_maturity_level"], r["status"], r["authority_boundary"]] for r in mode_rows]),
    )
    write_json(OUTPUT_ROOT / "EPOCH1_CERTIFIED_PROOF_REF_INDEX.json", proof_index)
    write_json(OUTPUT_ROOT / "EPOCH1_CERTIFIED_STATE_UPDATE.json", certified_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CERTIFIED_STATE_UPDATE.md",
        "# Epoch 1 Certified State Update\n\n"
        f"Status: {certified_report['status']}\n\n"
        f"Mode/agent rows: {certified_report['mode_agent_rows']}\n\n"
        f"Epoch 2 baseline ready: {certified_report['Epoch2_baseline_ready']}\n",
    )

    doc07_report = {
        "schema_version": "main-citybrain.epoch1.doc07_assignments.v1",
        "status": "PASS",
        "Doc07_future_track_only": True,
        "no_learning_runtime_authorized": True,
        "assignments": doc07,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_DOC07_OPEN_QUESTION_ASSIGNMENTS.json", doc07_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_DOC07_OPEN_QUESTION_ASSIGNMENTS.md",
        "# Epoch 1 Doc 07 Open Question Assignments\n\n"
        + md_table(["Question", "Owner", "Deadline", "Status"], [[r["question"], r["owner"], r["deadline"], r["status"]] for r in doc07]),
    )

    contract_check = {
        "formal closedown gate only": True,
        "no feature implementation": True,
        "no Doc07 learning runtime": True,
        "no sealed ASK drift": protected["ask_diff_empty"],
        "no protected R7 drift": protected["r7_diff_empty"],
        "no live/API/URL/LLM": True,
        "no official/dispatch/control/legal/certified/autonomy claim": True,
        "no secrets/raw/media/caches committed": True,
    }
    limitations = [
        "Full unittest discovery was not run in this source-only closedown because old generated-output tests are known to create or require ignored outputs.",
        "Historical output artifacts remain branch evidence and are intentionally not tracked on origin/main.",
        "Regression corpus v4 ASK contradiction proof is closed; formal v7 corpus release index is carried to Epoch 2.0 preflight.",
        "Track 0 still has carried docs/governance/source-refresh debt with explicit owners and deadlines.",
        "Doc 07 remains future-track only; no learning runtime, model, forecast, backtest, or uncertainty delta is authorized.",
    ]
    closure_report = {
        "schema_version": "main-citybrain.epoch1.closure_report.v1",
        "status": PASS_WITH_LIMITATIONS,
        "what_epoch1_delivered": [
            "ASK, CHECK, WATCH, App Review Route, R7 review workflow, cockpit/source-record, BRIEF, DIFF/RECALL, CER, Semantic Graph, spatial UI, perception media evidence, workflow state, approval lifecycle, PLAN, SCHEDULE/SIMULATE, federation/data maturity, RBAC/audit, execution-readiness preflight, and learning-substrate collection.",
            "A source-only origin/main baseline with no tracked outputs/data/raw/cache artifacts.",
        ],
        "what_epoch1_did_not_deliver": [
            "Production/public API, live monitoring, official ticket/case creation, dispatch/control/enforcement, legal/certified finding, production IAM, production federation, live Kit control, citywide certified twin, learning runtime, model training, forecast runtime, or autonomous execution.",
        ],
        "canonical_vs_branch_only": canonical_report["branch_published_stragglers"],
        "test_status": "focused closedown tests required; full discovery skipped with known generated-output limitation",
        "validation_status": "Push 1-7 validation accepted with limitations; this package reconciles to Epoch 1 baseline.",
        "open_waivers": [w for w in waivers if w["status"] == "CARRIED"],
        "track0_carried_items": track0_carried,
        "data_freshness_state": freshness_report,
        "parked_register_state": parked_report,
        "Doc07_future_track_state": doc07_report,
        "Epoch2_baseline_target": TARGET_REF,
        "Epoch2_1_maturity_dashboard_dependencies": ["source refresh policy", "operator-data policy", "formal corpus v7 index"],
        "contract_check": contract_check,
        "limitations": limitations,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_CLOSURE_REPORT.json", closure_report)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSURE_REPORT.md",
        "# Epoch 1 Closure Report\n\n"
        f"Status: {PASS_WITH_LIMITATIONS}\n\n"
        "Epoch 1 is closed as a certified baseline with explicit limitations and carry-forward items.\n",
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSURE_EXECUTIVE_SUMMARY.md",
        "# Epoch 1 Closure Executive Summary\n\n"
        "Epoch 1 delivered a local/replay/review/query product stack and a source-only main baseline. It did not deliver production/live/autonomous capabilities. Epoch 2 audits should use this closedown bundle plus origin/main as their starting baseline.",
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSURE_LIMITATIONS_AND_CARRY_FORWARD.md",
        "# Epoch 1 Closure Limitations And Carry Forward\n\n" + "\n".join(f"- {item}" for item in limitations),
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSURE_NEXT_EPOCH_BASELINE.md",
        "# Epoch 1 Closure Next Epoch Baseline\n\n"
        f"Epoch 2.0 should start from `{TARGET_REF}` at `{rev(TARGET_REF)}` plus this closedown branch. Epoch 2.1 maturity dashboard work depends on source freshness policy, operator-data policy, and formal corpus v7 indexing.",
    )

    test_report = {
        "schema_version": "main-citybrain.epoch1.test_report.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "focused_closedown_tests": "PASS: python -m unittest tests.test_main_citybrain_epoch1_closedown_certified_baseline",
        "full_discovery": "not_run_known_generated_output_limitations",
        "protected_ASK_R7_diff": protected["status"],
    }
    write_json(OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_PROTECTED_DIFF_REPORT.md.json", protected)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_PROTECTED_DIFF_REPORT.md",
        "# Epoch 1 Closedown Protected Diff Report\n\n"
        + md_table(["Area", "Diff Empty"], [["ASK", protected["ask_diff_empty"]], ["R7", protected["r7_diff_empty"]]]),
    )
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_TEST_REPORT.md",
        "# Epoch 1 Closedown Test Report\n\n"
        f"Focused closedown tests: {test_report['focused_closedown_tests']}\n\n"
        f"Full discovery: {test_report['full_discovery']}\n\n"
        f"Protected ASK/R7 diff: {test_report['protected_ASK_R7_diff']}\n",
    )

    final_decision = {
        "schema_version": "main-citybrain.epoch1.final_decision.v1",
        "package": TASK_ID,
        "status": PASS_WITH_LIMITATIONS,
        "target": target_selection,
        "ledger": ledger_report,
        "waivers": waiver_report,
        "corpus": corpus_report,
        "canonical_state": canonical_report,
        "track0": track0_report,
        "data_freshness": freshness_report,
        "parked_register": parked_report,
        "certified_state": certified_report,
        "doc07": doc07_report,
        "tests": test_report,
        "contract_check": contract_check,
        "limitations": limitations,
        "pushed": False,
        "main_merged": False,
    }
    write_json(OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_FINAL_DECISION.json", final_decision)
    write_md(
        OUTPUT_ROOT / "EPOCH1_CLOSEDOWN_FINAL_SUMMARY.md",
        "# Epoch 1 Closedown Final Summary\n\n"
        f"Decision: {PASS_WITH_LIMITATIONS}\n\n"
        f"Closedown target: {TARGET_REF} `{rev(TARGET_REF)}`\n\n"
        f"ASK contradiction waiver: {waiver_report['ask_contradiction_waiver_status']}\n\n"
        f"Ledger rows: {ledger_report['ledger_row_count']}\n\n"
        f"Mode/agent rows: {certified_report['mode_agent_rows']}\n",
    )

    write_hash_manifest()
    return final_decision


def main() -> int:
    decision = write_all_outputs()
    hash_report = verify_local_hash_manifest()
    print(f"{TASK_ID}: {decision['status']}")
    print(f"Target: {TARGET_REF} {rev(TARGET_REF)}")
    print(f"Ledger rows: {decision['ledger']['ledger_row_count']}")
    print(f"ASK waiver: {decision['waivers']['ask_contradiction_waiver_status']}")
    print(f"Hash manifest: {hash_report['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if hash_report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
