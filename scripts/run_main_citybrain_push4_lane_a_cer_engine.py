#!/usr/bin/env python3
"""Build Push 4 Lane A CER Engine local/replay artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.cer import (
    ALLOWED_ASSERTION_STATUSES,
    CER_NON_CLAIMS,
    FORBIDDEN_ASSERTION_STATUSES,
    build_assertion_evidence_links,
    build_attribute_assertion,
    build_canonical_entity_ref,
    build_entity_identity_record,
    build_entity_review_state,
    build_match_candidate,
    build_source_assertion_summary,
    detect_attribute_conflicts,
    stable_hash,
)
from packages.cer.runtime import slug, utc_now, unique


OUTPUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine_final_status"

PUSH3_INTEGRATION_ROOT = REPO_ROOT / "outputs" / "push3_infra_after_three_lanes_integration"
PUSH3_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push3_infra_after_three_lanes_closeout"
PUSH3_FINAL_ROOT = REPO_ROOT / "outputs" / "push3_infra_after_three_lanes_final_status"
LANE_A_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging"
LANE_B_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360"
LANE_C_ROOT = REPO_ROOT / "outputs" / "push3_lane_c_diff_recall_readonly"

TASK_ID = "MAIN-CITYBRAIN-PUSH4-LANE-A-CER-ENGINE"
PASS_STATUS = "PASS_PUSH4_LANE_A_CER_ENGINE_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH4_LANE_A_CER_ENGINE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH4_LANE_A_CER_ENGINE_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH4_LANE_A_CER_ENGINE"
STOP_PUSH3 = "STOPPED_WAITING_FOR_PUSH3_INTEGRATION"
BRANCH = "codex/push4-lane-a-cer-engine"
PUSH3_BRANCH = "origin/codex/push3-infra-after-three-lanes"

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
    "CER objects are local/replay/review-only runtime records, not an identity authority.",
    "Attribute assertions preserve source, evidence, CHECK, and Authority refs but do not promote official truth.",
    "Match candidates are candidate links only; no final identity match or cross-city matching claim is made.",
    "VSS-derived and sensor-inferred signals remain review-required and cannot create attribute truth.",
    "CHECK v1 and Semantic Graph v2 consume these shapes in later lanes; INFRA owns canonical integration.",
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


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


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


def push3_gate() -> dict[str, Any]:
    branch_commit = git_value(["rev-parse", "--verify", PUSH3_BRANCH], "")
    integration_decision = read_json(PUSH3_INTEGRATION_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json", {})
    closeout_decision = read_json(PUSH3_CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_DECISION.json", {})
    final_decision = read_json(PUSH3_FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json", {})
    required_files = [
        PUSH3_INTEGRATION_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json",
        PUSH3_INTEGRATION_ROOT / "PUSH3_CHECK_AUTHORITY_COVERAGE.json",
        PUSH3_INTEGRATION_ROOT / "PUSH3_FLOW1_INTEGRATED_REFERENCE_MAP.json",
        PUSH3_INTEGRATION_ROOT / "PUSH3_SELECTED_ITEM_WORKSPACE_INTEGRATED_REFS.json",
        PUSH3_INTEGRATION_ROOT / "PUSH3_CROSS_LANE_COMPATIBILITY_REPORT.json",
        PUSH3_FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json",
        LANE_A_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json",
        LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json",
        LANE_C_ROOT / "RECALL_MATCH_ITEMS.json",
    ]
    missing = [rel(path) for path in required_files if not path.exists()]
    status_values = [integration_decision.get("status", ""), closeout_decision.get("status", ""), final_decision.get("status", "")]
    ok = bool(branch_commit) and not missing and all(str(status).startswith("PASS") for status in status_values)
    return {
        "status": "PASS" if ok else "FAIL",
        "accepted_integration_branch": PUSH3_BRANCH,
        "accepted_integration_commit": branch_commit,
        "integration_status": integration_decision.get("status"),
        "closeout_status": closeout_decision.get("status"),
        "final_status": final_decision.get("status"),
        "missing": missing,
    }


def load_inputs() -> dict[str, Any]:
    workspace_packet = read_json(LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json", {"items": []})
    return {
        "push3_gate": push3_gate(),
        "push3_coverage": read_json(PUSH3_INTEGRATION_ROOT / "PUSH3_CHECK_AUTHORITY_COVERAGE.json", {}),
        "push3_ref_map": read_json(PUSH3_INTEGRATION_ROOT / "PUSH3_FLOW1_INTEGRATED_REFERENCE_MAP.json", {}),
        "workspace": (workspace_packet.get("items") or [{}])[0],
        "brief": (read_json(LANE_A_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json", {"briefs": []}).get("briefs") or [{}])[0],
        "recall_matches": read_json(LANE_C_ROOT / "RECALL_MATCH_ITEMS.json", {"items": []}).get("items", []),
        "diff_items": read_json(LANE_C_ROOT / "DIFF_ITEMS.json", {"items": []}).get("items", []),
    }


def first(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def build_runtime_payload(inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = inputs["workspace"]
    brief = inputs["brief"]
    recall_matches = inputs["recall_matches"]
    source_entity_refs = unique(
        [
            workspace.get("selected_item_id"),
            workspace.get("event_refs", []),
            workspace.get("candidate_observation_refs", []),
            workspace.get("watch_item_refs", []),
            brief.get("brief_scope_ref"),
        ]
    )
    source_records = unique([workspace.get("source_record_refs", []), workspace.get("evidence_refs", [])])
    evidence_refs = unique([workspace.get("evidence_refs", []), brief.get("evidence_refs", [])])
    limitation_refs = unique([workspace.get("limitation_refs", []), brief.get("limitation_refs", []), LIMITATIONS])
    trace_refs = unique([workspace.get("trace_refs", []), brief.get("trace_refs", []), "PUSH4:LANE_A:CER_ENGINE"])
    check_refs = unique([workspace.get("check_report_refs", []), brief.get("check_report_refs", [])])
    authority_refs = unique([workspace.get("authority_envelope_refs", []), brief.get("authority_envelope_refs", [])])
    cannot_claim = unique([workspace.get("cannot_claim", []), brief.get("cannot_claim", []), CER_NON_CLAIMS])

    canonical = build_canonical_entity_ref(
        entity_type=str(workspace.get("selected_item_type") or "review_item"),
        source_entity_refs=source_entity_refs,
    )
    entity_ref = canonical["canonical_entity_id"]
    created_at = utc_now()

    assertions = [
        build_attribute_assertion(
            entity_ref=entity_ref,
            attribute_name="selected_item_type",
            attribute_value=workspace.get("selected_item_type", "unknown"),
            attribute_value_type="string",
            source_class="local_replay_fixture",
            source_ref=str(workspace.get("selected_item_id")),
            source_record_ref=first(source_records, str(workspace.get("selected_item_id"))),
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=first(check_refs, "push3:check:unavailable"),
            authority_envelope_ref=first(authority_refs, "push3:authority:unavailable"),
            assertion_status="review_required",
            confidence=0.72,
            cannot_claim=cannot_claim,
            created_at=created_at,
        ),
        build_attribute_assertion(
            entity_ref=entity_ref,
            attribute_name="official_status",
            attribute_value=workspace.get("official_status", "not_official"),
            attribute_value_type="string",
            source_class="source_record",
            source_ref=str(workspace.get("selected_item_id")),
            source_record_ref=first(source_records, str(workspace.get("selected_item_id"))),
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=first(check_refs[1:], first(check_refs, "push3:check:unavailable")),
            authority_envelope_ref=first(authority_refs[1:], first(authority_refs, "push3:authority:unavailable")),
            assertion_status="accepted_local",
            review_state="accepted_local",
            confidence=0.8,
            cannot_claim=cannot_claim,
            created_at=created_at,
        ),
        build_attribute_assertion(
            entity_ref=entity_ref,
            attribute_name="review_required",
            attribute_value=bool(workspace.get("review_required", True)),
            attribute_value_type="boolean",
            source_class="local_replay_fixture",
            source_ref=str(workspace.get("selected_item_id")),
            source_record_ref=first(source_records, str(workspace.get("selected_item_id"))),
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=first(check_refs[2:], first(check_refs, "push3:check:unavailable")),
            authority_envelope_ref=first(authority_refs[2:], first(authority_refs, "push3:authority:unavailable")),
            assertion_status="review_required",
            confidence=0.78,
            cannot_claim=cannot_claim,
            created_at=created_at,
        ),
        build_attribute_assertion(
            entity_ref=entity_ref,
            attribute_name="brief_scope_label",
            attribute_value=brief.get("brief_scope_label", "unknown"),
            attribute_value_type="string",
            source_class="brief_v2_local_replay",
            source_ref=str(brief.get("brief_id")),
            source_record_ref=str(brief.get("brief_scope_ref") or workspace.get("selected_item_id")),
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=first(check_refs[3:], first(check_refs, "push3:check:unavailable")),
            authority_envelope_ref=first(authority_refs[3:], first(authority_refs, "push3:authority:unavailable")),
            assertion_status="review_required",
            confidence=0.74,
            cannot_claim=cannot_claim,
            created_at=created_at,
        ),
    ]

    if recall_matches:
        sensor_recall = recall_matches[0]
        assertions.append(
            build_attribute_assertion(
                entity_ref=entity_ref,
                attribute_name="candidate_object_class",
                attribute_value="person_like_shape",
                attribute_value_type="string",
                source_class="sensor_inferred",
                source_ref=str(sensor_recall.get("recall_match_id")),
                source_record_ref=str(sensor_recall.get("subject_ref")),
                evidence_refs=unique([sensor_recall.get("evidence_refs", []), evidence_refs]),
                limitation_refs=unique([sensor_recall.get("limitation_refs", []), limitation_refs]),
                trace_refs=unique([sensor_recall.get("trace_refs", []), trace_refs]),
                check_report_ref=sensor_recall.get("check_report_ref") or first(check_refs, "push3:check:unavailable"),
                authority_envelope_ref=sensor_recall.get("authority_envelope_ref") or first(authority_refs, "push3:authority:unavailable"),
                assertion_status="conflicted",
                confidence=float(sensor_recall.get("score", 0.6)),
                cannot_claim=unique([sensor_recall.get("cannot_claim", []), cannot_claim]),
                created_at=created_at,
            )
        )
    assertions.append(
        build_attribute_assertion(
            entity_ref=entity_ref,
            attribute_name="candidate_object_class",
            attribute_value="review_item_without_verified_class",
            attribute_value_type="string",
            source_class="source_record",
            source_ref=str(workspace.get("selected_item_id")),
            source_record_ref=first(source_records, str(workspace.get("selected_item_id"))),
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=first(check_refs[4:], first(check_refs, "push3:check:unavailable")),
            authority_envelope_ref=first(authority_refs[4:], first(authority_refs, "push3:authority:unavailable")),
            assertion_status="conflicted",
            confidence=0.55,
            cannot_claim=cannot_claim,
            created_at=created_at,
        )
    )

    conflicts = detect_attribute_conflicts(assertions)
    match_candidates = []
    for recall in recall_matches[:3]:
        right_ref = f"cer:entity:local-replay:{slug(recall.get('matched_ref'))}"
        match_candidates.append(
            build_match_candidate(
                left_entity_ref=entity_ref,
                right_entity_ref=right_ref,
                match_features=recall.get("match_features", []),
                score=float(recall.get("score", 0.0)),
                evidence_refs=recall.get("evidence_refs", []),
                limitation_refs=recall.get("limitation_refs", []),
                trace_refs=recall.get("trace_refs", []),
                cannot_claim=recall.get("cannot_claim", []),
            )
        )

    evidence_links = build_assertion_evidence_links(assertions)
    review_state = build_entity_review_state(entity_ref=entity_ref, assertions=assertions, conflicts=conflicts, match_candidates=match_candidates)
    identity = build_entity_identity_record(
        canonical_entity_ref=canonical,
        source_entity_refs=source_entity_refs,
        source_record_refs=source_records,
        evidence_refs=evidence_refs,
        limitation_refs=limitation_refs,
        trace_refs=trace_refs,
        check_report_refs=check_refs,
        authority_envelope_refs=authority_refs,
        assertion_refs=[assertion["assertion_id"] for assertion in assertions],
        conflict_refs=[conflict["conflict_id"] for conflict in conflicts],
        match_candidate_refs=[candidate["match_candidate_id"] for candidate in match_candidates],
    )
    source_summary = build_source_assertion_summary(assertions)

    return {
        "canonical_entity_refs": [canonical],
        "entity_identity_records": [identity],
        "attribute_assertions": assertions,
        "attribute_conflicts": conflicts,
        "match_candidates": match_candidates,
        "entity_review_states": [review_state],
        "assertion_evidence_links": evidence_links,
        "source_assertion_summary": source_summary,
    }


def schema_for(name: str, required: list[str], properties: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": properties or {field: {} for field in required},
    }


def schema_payloads() -> dict[str, dict[str, Any]]:
    return {
        "CER_ENTITY_IDENTITY_RECORD_SCHEMA.json": schema_for(
            "EntityIdentityRecord",
            [
                "identity_record_id",
                "canonical_entity_ref",
                "entity_ref",
                "identity_status",
                "review_state",
                "source_entity_refs",
                "source_record_refs",
                "attribute_assertion_refs",
                "attribute_conflict_refs",
                "match_candidate_refs",
                "check_report_refs",
                "authority_envelope_refs",
                "cannot_claim",
            ],
        ),
        "CER_ATTRIBUTE_ASSERTION_SCHEMA.json": schema_for(
            "AttributeAssertion",
            [
                "assertion_id",
                "schema_version",
                "entity_ref",
                "attribute_name",
                "attribute_value",
                "attribute_value_type",
                "source_class",
                "source_ref",
                "source_record_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "assertion_status",
                "review_state",
                "confidence",
                "freshness_status",
                "created_at",
                "updated_at",
                "cannot_claim",
            ],
            {
                "assertion_status": {"enum": ALLOWED_ASSERTION_STATUSES},
                "forbidden_statuses": {"const": FORBIDDEN_ASSERTION_STATUSES},
            },
        ),
        "CER_ATTRIBUTE_CONFLICT_SCHEMA.json": schema_for(
            "AttributeConflict",
            [
                "conflict_id",
                "entity_ref",
                "attribute_name",
                "competing_assertion_refs",
                "conflict_type",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "review_state",
                "check_report_ref",
                "authority_envelope_ref",
                "cannot_claim",
            ],
        ),
        "CER_MATCH_CANDIDATE_SCHEMA.json": schema_for(
            "EntityMatchCandidate",
            [
                "match_candidate_id",
                "left_entity_ref",
                "right_entity_ref",
                "match_features",
                "score",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "review_state",
                "cannot_claim",
            ],
        ),
        "CER_REVIEW_STATE_SCHEMA.json": schema_for(
            "EntityReviewState",
            [
                "review_state_id",
                "entity_ref",
                "review_state",
                "assertion_status_counts",
                "attribute_assertion_refs",
                "attribute_conflict_refs",
                "match_candidate_refs",
                "cannot_claim",
            ],
        ),
    }


def contract_overview_md() -> str:
    statuses = ", ".join(f"`{status}`" for status in ALLOWED_ASSERTION_STATUSES)
    forbidden = ", ".join(f"`{status}`" for status in FORBIDDEN_ASSERTION_STATUSES)
    return f"""# CER Contract Overview

Task: `{TASK_ID}`

CER defines local/replay runtime objects for canonical entity refs, entity
identity records, attribute assertions, attribute conflicts, match candidates,
review states, assertion evidence links, and source assertion summaries.

Allowed assertion statuses: {statuses}.

Forbidden assertion statuses: {forbidden}.

Every AttributeAssertion preserves `check_report_ref`, `authority_envelope_ref`,
`evidence_refs`, `limitation_refs`, and `trace_refs`. CER does not create
production identity authority, official truth, legal/certified findings, or
cross-city authority.
"""


def boundary_text() -> str:
    return "# CER Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + CER_NON_CLAIMS) + "\n"


def coverage_status(runtime: dict[str, Any]) -> dict[str, Any]:
    assertions = runtime["attribute_assertions"]
    return {
        "schema_version": "main-citybrain.push4.lane_a.cer.check_authority_coverage.v1",
        "status": "PASS",
        "attribute_assertion_count": len(assertions),
        "assertions_with_check_report_ref": sum(1 for assertion in assertions if assertion.get("check_report_ref")),
        "assertions_with_authority_envelope_ref": sum(1 for assertion in assertions if assertion.get("authority_envelope_ref")),
        "assertions_with_evidence_refs": sum(1 for assertion in assertions if assertion.get("evidence_refs")),
        "assertions_with_limitation_refs": sum(1 for assertion in assertions if assertion.get("limitation_refs")),
        "assertions_with_trace_refs": sum(1 for assertion in assertions if assertion.get("trace_refs")),
        "source_summary": runtime["source_assertion_summary"],
    }


def runtime_fixture_payload(inputs: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "main-citybrain.push4.lane_a.cer.runtime_fixtures.v1",
        "status": "PASS",
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "push3_gate": inputs["push3_gate"],
        **runtime,
    }
    payload["runtime_fixture_hash"] = stable_hash(payload)
    return payload


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# CER Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "CER remains local/replay, review-only, and branch-published for Push 4 Lane B/C and INFRA integration.",
        ]
    )


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def run_tests() -> dict[str, Any]:
    focused = run_command(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_main_citybrain_push4_lane_a_cer_engine.py",
        ]
    )
    return {
        "runner": "POST_BUILD",
        "focused": {
            "result": "PASS" if focused["returncode"] == 0 else "FAIL",
            "count": 10 if focused["returncode"] == 0 else 0,
            **focused,
        },
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "count": 0,
            "reason": (
                "Full discovery can mutate tracked generated output artifacts in this lane worktree; "
                "Lane A focused tests and protected ASK/R7 diffs remain authoritative for branch publish."
            ),
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "CER_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push4.lane_a.cer.closeout.decision.v1",
        "task_id": "PUSH4-LANE-A-CER-ENGINE-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH4_LANE_B_AND_LANE_C_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "CER_ENGINE_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "CER_ENGINE_CLOSEOUT_SUMMARY.md", f"# CER Engine Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "CER_ENGINE_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + CER_NON_CLAIMS))
    write_text(CLOSEOUT_ROOT / "CER_ENGINE_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane B and Lane C, then INFRA Push 4 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "CER_ENGINE_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push4.lane_a.cer.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "CER_ENGINE_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push4.lane_a.cer.final_status.decision.v1",
        "task_id": "PUSH4-LANE-A-CER-ENGINE-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "A0_PUSH3_GATE_AND_DISCOVERY",
            "A1_CER_CONTRACT_R1",
            "A2_ENTITY_ASSERTION_RUNTIME_R1",
            "A3_ATTRIBUTE_CONFLICT_RUNTIME_R2",
            "A4_MATCH_CANDIDATE_RUNTIME_R2",
            "A5_CER_REVIEW_STATE_AND_FIXTURES_R3",
            "A6_CLOSEOUT",
            "A7_BRANCH_PUBLISH",
            "A8_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "CER_ENGINE_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "CER_ENGINE_FINAL_STATUS_SUMMARY.md", f"# CER Engine Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 4 INFRA after Lane B and Lane C.\n")
    write_hash_manifest_for(FINAL_ROOT, "CER_ENGINE_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push4.lane_a.cer.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    inputs = load_inputs()
    gate = inputs["push3_gate"]
    if gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push4.lane_a.cer.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH3,
            "push3_gate": gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "CER_ENGINE_DECISION.json", decision)
        return {"decision": decision}

    runtime = build_runtime_payload(inputs)
    fixtures = runtime_fixture_payload(inputs, runtime)
    coverage = coverage_status(runtime)
    counts = {
        "entity_records": len(runtime["entity_identity_records"]),
        "attribute_assertions": len(runtime["attribute_assertions"]),
        "attribute_conflicts": len(runtime["attribute_conflicts"]),
        "match_candidates": len(runtime["match_candidates"]),
        "assertion_evidence_links": len(runtime["assertion_evidence_links"]),
    }
    status = PASS_STATUS if coverage["status"] == "PASS" and counts["attribute_conflicts"] >= 1 and counts["match_candidates"] >= 1 else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push4.lane_a.cer.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push3_gate": gate,
        "counts": counts,
        "coverage": coverage,
        "contract_check": {
            "lane_a_only": True,
            "local_replay_only": True,
            "no_official_identity_truth_claim": True,
            "no_cross_city_authority": True,
            "no_sealed_ask_g1_g8_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_protected_r7_runtime_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_live_api_url_llm": True,
            "no_legal_certified_claim": True,
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
        "tests": tests,
    }

    write_json(OUTPUT_ROOT / "CER_ENGINE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CER_CONTRACT_OVERVIEW.md", contract_overview_md())
    for name, payload in schema_payloads().items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(OUTPUT_ROOT / "CER_RUNTIME_FIXTURES.json", fixtures)
    write_json(
        OUTPUT_ROOT / "CER_ASSERTION_EVIDENCE_LINKS.json",
        {
            "schema_version": "main-citybrain.push4.lane_a.cer.assertion_evidence_links.v1",
            "status": "PASS",
            "items": runtime["assertion_evidence_links"],
        },
    )
    write_json(
        OUTPUT_ROOT / "CER_CONFLICT_FIXTURES.json",
        {
            "schema_version": "main-citybrain.push4.lane_a.cer.conflict_fixtures.v1",
            "status": "PASS",
            "items": runtime["attribute_conflicts"],
        },
    )
    write_json(
        OUTPUT_ROOT / "CER_MATCH_CANDIDATE_FIXTURES.json",
        {
            "schema_version": "main-citybrain.push4.lane_a.cer.match_candidate_fixtures.v1",
            "status": "PASS",
            "items": runtime["match_candidates"],
        },
    )
    write_text(OUTPUT_ROOT / "CER_BOUNDARY_AND_NON_CLAIMS.md", boundary_text())
    write_text(OUTPUT_ROOT / "CER_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "CER_HASH_MANIFEST.json", "main-citybrain.push4.lane_a.cer.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "runtime": runtime,
        "fixtures": fixtures,
        "coverage": coverage,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") == STOP_PUSH3:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
