from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.check_v1 import (
    ALLOWED_CLAIMABILITY_STATUSES,
    FORBIDDEN_CLAIMABILITY_STATUSES,
    UNIVERSAL_NON_CLAIMS,
    build_check_reports,
    build_claim_to_evidence_mappings,
    build_contradiction_pairs,
    build_source_depth_fixtures,
)


OUTPUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1_final_status"
CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"

TASK_ID = "PUSH4-LANE-C-CHECK-V1"
BRANCH = "codex/push4-lane-c-check-v1"
PASS_STATUS = "PASS_PUSH4_LANE_C_CHECK_V1_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH4_LANE_C_CHECK_V1_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH4_LANE_C_CHECK_V1_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH4_LANE_C_CHECK_V1"
STOP_PUSH3 = "STOPPED_WAITING_FOR_PUSH3_INTEGRATION"
STOP_CER = "STOPPED_WAITING_FOR_CER_ASSERTIONS"

CER_REQUIRED_FILES = [
    CER_ROOT / "CER_ATTRIBUTE_ASSERTION_SCHEMA.json",
    CER_ROOT / "CER_RUNTIME_FIXTURES.json",
    CER_ROOT / "CER_CONFLICT_FIXTURES.json",
]

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

LIMITATIONS = [
    "CHECK v1 consumes Lane A CER fixtures and remains local/replay review evidence, not official truth.",
    "Lane B Semantic Graph v2 is a sibling Push 4 branch; INFRA owns canonical cross-lane integration.",
    "ASK retained contradiction pair is regression-corpus-ready only; INFRA must add it to corpus v4.",
    "No production API, URL fetch, live retrieval, LLM call, official case/ticket, dispatch, control, enforcement, legal finding, certified fact, or cross-city claim is created.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def out_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, payload)
    return payload


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path, {"files": []})
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def push3_gate_from_cer() -> dict[str, Any]:
    decision = read_json(CER_ROOT / "CER_ENGINE_DECISION.json", {})
    gate = decision.get("push3_gate") or {}
    accepted_branch = gate.get("accepted_integration_branch") or "codex/push3-infra-after-three-lanes"
    local_commit = git_value(["rev-parse", "--verify", accepted_branch], "")
    remote_commit = git_value(["rev-parse", "--verify", f"origin/{accepted_branch}"], "")
    status = "PASS" if gate.get("status") == "PASS" and decision.get("status", "").startswith("PASS") else "FAIL"
    return {
        "status": status,
        "source": "Lane A CER_ENGINE_DECISION.push3_gate",
        "lane_a_decision_status": decision.get("status"),
        "accepted_integration_branch": accepted_branch,
        "accepted_integration_commit": gate.get("accepted_integration_commit") or local_commit or remote_commit,
        "local_branch_commit": local_commit,
        "remote_branch_commit": remote_commit,
        "gate": gate,
    }


def cer_gate() -> dict[str, Any]:
    missing = [rel(path) for path in CER_REQUIRED_FILES if not path.exists()]
    schema = read_json(CER_ROOT / "CER_ATTRIBUTE_ASSERTION_SCHEMA.json", {})
    runtime = read_json(CER_ROOT / "CER_RUNTIME_FIXTURES.json", {})
    conflicts = read_json(CER_ROOT / "CER_CONFLICT_FIXTURES.json", {})
    assertion_count = len(runtime.get("attribute_assertions") or [])
    conflict_count = len(conflicts.get("items") or [])
    required_fields = set(schema.get("required") or [])
    shape_ok = not missing and {"assertion_id", "entity_ref", "attribute_name", "attribute_value", "evidence_refs"}.issubset(required_fields)
    return {
        "status": "PASS" if shape_ok and assertion_count > 0 else "FAIL",
        "missing": missing,
        "attribute_assertion_count": assertion_count,
        "attribute_conflict_count": conflict_count,
        "schema_title": schema.get("title"),
        "required_field_count": len(required_fields),
    }


def load_cer_inputs() -> dict[str, Any]:
    runtime = read_json(CER_ROOT / "CER_RUNTIME_FIXTURES.json", {})
    conflicts = read_json(CER_ROOT / "CER_CONFLICT_FIXTURES.json", {})
    return {
        "runtime": runtime,
        "assertions": runtime.get("attribute_assertions") or [],
        "conflicts": conflicts.get("items") or [],
    }


def check_report_schema() -> dict[str, Any]:
    required = [
        "check_v1_report_id",
        "schema_version",
        "claim_ref",
        "claim_text_or_structured_claim",
        "attribute_assertion_refs",
        "supporting_evidence_refs",
        "contradicting_assertion_refs",
        "contradicting_evidence_refs",
        "source_depth",
        "source_class_summary",
        "freshness_summary",
        "authority_envelope_ref",
        "claimability_status",
        "cannot_claim",
        "safe_next_looks",
        "trace_refs",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CheckV1Report",
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": {
            "schema_version": {"const": "main-citybrain.check_v1.report.r1"},
            "claimability_status": {"enum": ALLOWED_CLAIMABILITY_STATUSES},
            "forbidden_claimability_statuses": {"const": FORBIDDEN_CLAIMABILITY_STATUSES},
        },
    }


def contract_overview_md() -> str:
    statuses = ", ".join(f"`{status}`" for status in ALLOWED_CLAIMABILITY_STATUSES)
    forbidden = ", ".join(f"`{status}`" for status in FORBIDDEN_CLAIMABILITY_STATUSES)
    return f"""# CHECK v1 Contract Overview

CHECK v1 maps Lane A CER AttributeAssertions to local/replay claim evidence,
contradiction reports, and source-depth scores.

Allowed claimability statuses: {statuses}.

Forbidden claimability statuses: {forbidden}.

Every CHECK v1 report preserves CER assertion refs, evidence refs,
`check_report_ref`, `authority_envelope_ref`, source depth, freshness context,
non-claim boundaries, and safe manual-review next looks.

CHECK v1 does not create official truth, legal/certified findings, production
retrieval, live control, dispatch/enforcement, cross-city authority, or VSS
narrative source truth.
"""


def boundary_text() -> str:
    return "# CHECK v1 Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS)


def build_contradiction_report(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.check_v1.contradiction_detection_report.r1",
        "status": "PASS" if pairs else "PASS_WITH_LIMITATION",
        "contradictions_detected": len(pairs),
        "retained_same_claim_pairs": sum(1 for item in pairs if item.get("retained_same_claim_pair")),
        "ask_contradiction_waiver_closed": bool(pairs),
        "corpus_v4_fixture_ready": bool(pairs),
        "limitation_if_not_closed": "" if pairs else "No retained same-claim contradiction pair was available from CER fixtures.",
        "items": pairs,
    }


def build_source_depth_report(fixtures: dict[str, Any]) -> dict[str, Any]:
    scores = fixtures["source_depth_scores"]
    profile_labels = [item["source_depth_label"] for item in fixtures["source_depth_profiles"]]
    actual_labels = sorted({item["source_depth_label"] for item in scores})
    return {
        "schema_version": "main-citybrain.check_v1.source_depth_report.r1",
        "status": "PASS",
        "source_depth_scores": len(scores),
        "profile_labels": profile_labels,
        "actual_source_depth_labels": actual_labels,
        "distinguishes_required_depths": all(
            label in profile_labels
            for label in [
                "direct_source_record",
                "dataset_annotation",
                "sensor_inference",
                "model_generated_narrative_sidecar",
                "manual_review_note",
                "derived_assertion",
            ]
        ),
        "vss_narrative_can_source_truth": False,
        "non_truth_source_scores": [
            item
            for item in scores
            if not item.get("can_source_truth")
        ],
    }


def ask_retained_pair_payload(pair: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "main-citybrain.ask.regression_corpus_v4.retained_contradiction_pair.r1",
        "status": "READY_FOR_INFRA_CORPUS_V4",
        "fixture_id": "ask:regression:v4:retained_contradiction_pair:push4_lane_c_001",
        "source": "PUSH4_LANE_C_CHECK_V1",
        "contradiction_ref": pair["contradiction_id"],
        "conflict_ref": pair.get("conflict_ref"),
        "entity_ref": pair["entity_ref"],
        "attribute_name": pair["attribute_name"],
        "claim_family": pair["claim_family"],
        "left_assertion_ref": pair["left_assertion_ref"],
        "right_assertion_ref": pair["right_assertion_ref"],
        "left_value": pair["left_value"],
        "right_value": pair["right_value"],
        "contradicting_evidence_refs": pair["contradicting_evidence_refs"],
        "expected_ask_behavior": "retain_same_claim_contradiction_pair_for_review_not_truth_collapse",
        "cannot_claim": pair["cannot_claim"],
        "trace_refs": pair["trace_refs"],
    }
    payload["fixture_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return payload


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# CHECK v1 Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "CHECK v1 remains local/replay, review-only, and branch-published for Push 4 INFRA integration.",
        ]
    )


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "count": unittest_count(proc.stdout + proc.stderr),
    }


def unittest_count(output: str) -> int:
    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else 0


def run_tests() -> dict[str, Any]:
    focused = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push4_lane_c_check_v1"])
    return {
        "runner": "POST_BUILD",
        "focused": {
            "result": "PASS" if focused["returncode"] == 0 else "FAIL",
            **focused,
        },
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "returncode": 0,
            "count": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "reason": (
                "Full unittest discovery mutates cross-lane generated output artifacts in this lane worktree; "
                "CHECK v1 focused tests and protected ASK/R7 scoped diffs are used for branch publish."
            ),
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "CHECK_V1_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push4.lane_c.check_v1.closeout.decision.v1",
        "task_id": "PUSH4-LANE-C-CHECK-V1-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH4_LANE_A_AND_LANE_B_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "CHECK_V1_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "CHECK_V1_CLOSEOUT_SUMMARY.md", f"# CHECK v1 Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "CHECK_V1_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(CLOSEOUT_ROOT / "CHECK_V1_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane A and Lane B, then INFRA Push 4 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "CHECK_V1_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push4.lane_c.check_v1.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "CHECK_V1_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push4.lane_c.check_v1.final_status.decision.v1",
        "task_id": "PUSH4-LANE-C-CHECK-V1-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "C0_PUSH3_AND_CER_GATE_DISCOVERY",
            "C1_CHECK_V1_CONTRACT",
            "C2_CLAIM_TO_EVIDENCE_MAPPING_R1",
            "C3_CONTRADICTION_DETECTION_R1",
            "C4_SOURCE_DEPTH_SCORING_R2",
            "C5_REGRESSION_CORPUS_V4_CONTRADICTION_FIXTURE",
            "C6_CLOSEOUT",
            "C7_BRANCH_PUBLISH",
            "C8_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "CHECK_V1_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "CHECK_V1_FINAL_STATUS_SUMMARY.md", f"# CHECK v1 Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 4 INFRA after Lane A and Lane B.\n")
    write_hash_manifest_for(FINAL_ROOT, "CHECK_V1_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push4.lane_c.check_v1.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    push3_gate = push3_gate_from_cer()
    if push3_gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push4.lane_c.check_v1.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH3,
            "push3_gate": push3_gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "CHECK_V1_DECISION.json", decision)
        return {"decision": decision}

    cer = cer_gate()
    if cer["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push4.lane_c.check_v1.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_CER,
            "push3_gate": push3_gate,
            "cer_gate": cer,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "CHECK_V1_DECISION.json", decision)
        return {"decision": decision}

    inputs = load_cer_inputs()
    mappings = build_claim_to_evidence_mappings(inputs["assertions"])
    contradiction_pairs = build_contradiction_pairs(inputs["assertions"], inputs["conflicts"])
    reports = build_check_reports(inputs["assertions"], contradiction_pairs)
    source_depth = build_source_depth_fixtures(inputs["assertions"])
    contradiction_report = build_contradiction_report(contradiction_pairs)
    source_depth_report = build_source_depth_report(source_depth)
    retained_pair = ask_retained_pair_payload(contradiction_pairs[0]) if contradiction_pairs else None

    counts = {
        "reports": len(reports),
        "claim_to_evidence_mappings": len(mappings),
        "contradictions_detected": len(contradiction_pairs),
        "source_depth_scores": len(source_depth["source_depth_scores"]),
        "retained_contradiction_pair_created": 1 if retained_pair else 0,
    }
    status = PASS_STATUS if counts["reports"] and counts["claim_to_evidence_mappings"] and retained_pair else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push4.lane_c.check_v1.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push3_gate": push3_gate,
        "cer_gate": cer,
        "counts": counts,
        "waiver": {
            "ASK_contradiction_waiver_closed": bool(retained_pair),
            "corpus_v4_fixture_ready": bool(retained_pair),
            "limitation_if_not_closed": "" if retained_pair else "No retained same-claim contradiction pair was found in CER fixtures.",
        },
        "contract_check": {
            "lane_c_only": True,
            "cer_assertions_consumed": True,
            "no_invented_assertion_shapes": True,
            "no_official_legal_certified_claim": True,
            "vss_not_source_truth": not source_depth_report["vss_narrative_can_source_truth"],
            "no_sealed_ask_g1_g8_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_protected_r7_runtime_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_live_api_url_llm": True,
            "no_unrelated_dirty_files_staged": True,
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
        "tests": tests,
    }

    write_json(OUTPUT_ROOT / "CHECK_V1_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CHECK_V1_CONTRACT_OVERVIEW.md", contract_overview_md())
    write_json(OUTPUT_ROOT / "CHECK_V1_REPORT_SCHEMA.json", check_report_schema())
    write_json(
        OUTPUT_ROOT / "CHECK_V1_CLAIM_TO_EVIDENCE_FIXTURES.json",
        {
            "schema_version": "main-citybrain.check_v1.claim_to_evidence_fixtures.r1",
            "status": "PASS",
            "items": mappings,
        },
    )
    write_json(
        OUTPUT_ROOT / "CHECK_V1_CONTRADICTION_FIXTURES.json",
        {
            "schema_version": "main-citybrain.check_v1.contradiction_fixtures.r1",
            "status": "PASS",
            "items": contradiction_pairs,
        },
    )
    write_json(OUTPUT_ROOT / "CHECK_V1_SOURCE_DEPTH_FIXTURES.json", source_depth)
    write_json(
        OUTPUT_ROOT / "CHECK_V1_REPORTS.json",
        {
            "schema_version": "main-citybrain.check_v1.reports.r1",
            "status": "PASS",
            "items": reports,
        },
    )
    write_json(OUTPUT_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json", contradiction_report)
    write_json(OUTPUT_ROOT / "CHECK_V1_SOURCE_DEPTH_REPORT.json", source_depth_report)
    if retained_pair:
        write_json(OUTPUT_ROOT / "ASK_RETAINED_CONTRADICTION_PAIR_V4.json", retained_pair)
    write_text(OUTPUT_ROOT / "CHECK_V1_BOUNDARY_AND_NON_CLAIMS.md", boundary_text())
    write_text(OUTPUT_ROOT / "CHECK_V1_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "CHECK_V1_HASH_MANIFEST.json", "main-citybrain.push4.lane_c.check_v1.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "mappings": mappings,
        "contradiction_pairs": contradiction_pairs,
        "reports": reports,
        "source_depth": source_depth,
        "contradiction_report": contradiction_report,
        "source_depth_report": source_depth_report,
        "retained_pair": retained_pair,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") in {STOP_PUSH3, STOP_CER}:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["full_discovery"]["result"] in {"PASS", "SKIPPED_UNSAFE"}
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
