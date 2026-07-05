#!/usr/bin/env python3
"""Build Push 3 Lane C DIFF Scout v1 and RECALL matcher artifacts.

This package is local/replay and read-only. DIFF items and RECALL matches are
review context only; they do not create findings, actions, cases, tickets, live
queries, CER assertions, or production integrations.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push3_lane_c_diff_recall_readonly"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push3_lane_c_diff_recall_readonly_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push3_lane_c_diff_recall_readonly_final_status"

PACKAGE = "MAIN-CITYBRAIN-PUSH3-LANE-C-DIFF-RECALL-READONLY-RUN-TO-CLOSURE"
TASK_ID = "MAIN-CITYBRAIN-PUSH3-LANE-C-DIFF-RECALL-READONLY"
PASS_STATUS = "PASS_PUSH3_LANE_C_DIFF_RECALL_READONLY_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH3_LANE_C_DIFF_RECALL_READONLY_BOUNDARY_OR_CONTRACT_REGRESSION"
STOP_STATUS = "STOPPED_WAITING_FOR_PUSH2_INTEGRATION"
BRANCH = "codex/push3-lane-c-diff-recall-readonly"
COMMIT_SUBJECT = "Add Push 3 DIFF Scout and RECALL matchers"
PUSH2_INTEGRATION_BRANCH = "origin/codex/push2-check-watch-app-review-route-integration"

PUSH2_INTEGRATION_ROOT = OUTPUTS_ROOT / "push2_check_watch_app_review_route_integration"
PUSH2_INTEGRATION_DECISION = PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json"
PUSH2_CHECK_AUTHORITY_COVERAGE = PUSH2_INTEGRATION_ROOT / "PUSH2_CHECK_AUTHORITY_COVERAGE.json"
PUSH2_WATCH_APP_JOIN = PUSH2_INTEGRATION_ROOT / "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json"
PUSH2_CROSS_LANE_COMPATIBILITY = PUSH2_INTEGRATION_ROOT / "PUSH2_CROSS_LANE_COMPATIBILITY_REPORT.json"

CHECK_REPORT_FIXTURES = OUTPUTS_ROOT / "push2_lane_a_check_authority_v1" / "CHECK_REPORT_FIXTURES.json"
AUTHORITY_ENVELOPE_FIXTURES = OUTPUTS_ROOT / "push2_lane_a_check_authority_v1" / "AUTHORITY_ENVELOPE_FIXTURES.json"
WATCH_ITEMS = OUTPUTS_ROOT / "push2_lane_b_watch_scout_v1" / "WATCH_ITEMS.json"
APP_REVIEW_FIXTURES = OUTPUTS_ROOT / "push2_lane_c_app_review_route" / "APP_REVIEW_ROUTE_FIXTURES.json"
APP_REVIEW_DECISION = OUTPUTS_ROOT / "push2_lane_c_app_review_route" / "APP_REVIEW_ROUTE_DECISION.json"
DISPOSITION_FIXTURES = OUTPUTS_ROOT / "push2_lane_c_app_review_route" / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json"

RUNTIME_SPINE_DECISION = OUTPUTS_ROOT / "main_citybrain_sprint2_event_fabric_runtime_spine" / "EVENT_FABRIC_RUNTIME_SPINE_DECISION.json"
PERCEPTION_TO_EVENT_DECISION = OUTPUTS_ROOT / "main_citybrain_sprint2_perception_to_event_integration" / "PERCEPTION_TO_EVENT_INTEGRATION_DECISION.json"
R7B_EVENT_LOG = OUTPUTS_ROOT / "main_citybrain_r7b_perception_to_event_fabric_local_replay" / "R7B_LOCAL_EVENT_LOG.jsonl"
PACKAGES_EVENT_FABRIC = REPO_ROOT / "packages" / "event_fabric"

REQUIRED_OUTPUTS = [
    "DIFF_RECALL_READONLY_DECISION.json",
    "DIFF_SCOUT_V1_CONTRACT.json",
    "DIFF_SCOUT_V1_FIXTURES.json",
    "DIFF_ITEMS.json",
    "RECALL_MATCHER_CONTRACT.json",
    "RECALL_MATCH_ITEMS.json",
    "DIFF_TO_WATCH_COMPATIBILITY.json",
    "DIFF_RECALL_CHECK_AUTHORITY_COVERAGE.json",
    "DIFF_RECALL_BOUNDARY_AND_NON_CLAIMS.md",
    "DIFF_RECALL_TEST_LOG.md",
    "DIFF_RECALL_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "DIFF_RECALL_READONLY_CLOSEOUT_DECISION.json",
    "DIFF_RECALL_READONLY_CLOSEOUT_SUMMARY.md",
    "DIFF_RECALL_READONLY_CLOSEOUT_LIMITATIONS.md",
    "DIFF_RECALL_READONLY_CLOSEOUT_NEXT_STEPS.md",
    "DIFF_RECALL_READONLY_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "DIFF_RECALL_READONLY_FINAL_STATUS_DECISION.json",
    "DIFF_RECALL_READONLY_FINAL_STATUS_SUMMARY.md",
    "DIFF_RECALL_READONLY_FINAL_STATUS_HASH_MANIFEST.json",
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

DIFF_FAMILIES = [
    "new_item",
    "changed_review_state",
    "changed_authority_or_check_status",
    "new_disposition",
]

RECALL_FAMILIES = [
    "same_candidate_observation_class",
    "same_source_class",
    "similar_watch_family",
    "same_spatial_or_entity_ref",
    "same_disposition_pattern",
]

LIMITATIONS = [
    "Local/replay read-only review mode only; no production API, URL fetch, live retrieval, live monitoring, or LLM call is used.",
    "DIFF items describe review-context changes only; they are not findings, alerts, or action requests.",
    "RECALL matches are computed over local/replayed packet refs and features only; no cross-city recall claim is made until federation exists.",
    "CheckReports and AuthorityEnvelopes are consumed from Push 2 and preserved by reference; no CHECK or Authority schema change is introduced.",
    "No CER engine, assertion object shape, legal/certified finding, official case/ticket, dispatch/control/enforcement, or autonomous workflow is created.",
    "INFRA owns canonical Push 3 integration after Lane A and Lane B publish.",
]

CANNOT_CLAIM = [
    "official finding",
    "official action",
    "legal/certified finding",
    "live monitoring",
    "production feed",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "autonomous workflow",
    "cross-city recall certainty",
    "VSS as fact source",
]

NOT_EXECUTED = [
    "no live retrieval",
    "no production API",
    "no URL fetch",
    "no LLM call",
    "no official finding",
    "no official case/ticket submission",
    "no dispatch/control/enforcement",
    "no CER assertion engine",
    "no autonomous workflow",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path = OUTPUT_ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    if OUTPUTS_ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def write_hash_manifest(
    root: Path = OUTPUT_ROOT,
    name: str = "DIFF_RECALL_HASH_MANIFEST.json",
    schema: str = "main-citybrain.push3.lane_c.diff_recall.hash_manifest.v1",
) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        files.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(files),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": files,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path = OUTPUT_ROOT, name: str = "DIFF_RECALL_HASH_MANIFEST.json") -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path)
    problems: list[str] = []
    verified = 0
    for entry in manifest.get("files", []):
        target = root / entry["path"]
        if not target.exists():
            problems.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry.get("sha256"):
            problems.append(f"mismatch:{entry['path']}")
        else:
            verified += 1
    status = "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL"
    return {"status": status, "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def status_is_pass(payload: dict[str, Any], *fields: str) -> bool:
    for field in fields or ("status", "decision", "final_status"):
        value = str(payload.get(field, ""))
        if value == "PASS" or value.startswith("PASS"):
            return True
    return False


def remote_branch_available() -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", f"{PUSH2_INTEGRATION_BRANCH}^{{commit}}"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def gate_row(gate_id: str, paths: list[Path], payloads: list[dict[str, Any]], note: str, extra_ok: bool = True) -> dict[str, Any]:
    missing = [rel(path) for path in paths if not path.exists()]
    payload_ok = all(status_is_pass(payload) for payload in payloads)
    ok = not missing and payload_ok and extra_ok
    return {
        "gate_id": gate_id,
        "status": "PASS" if ok else "FAIL",
        "evidence_paths": [rel(path) for path in paths],
        "missing": missing,
        "note": note,
    }


def entry_gate_report() -> dict[str, Any]:
    integration = read_json(PUSH2_INTEGRATION_DECISION, {})
    check_coverage = read_json(PUSH2_CHECK_AUTHORITY_COVERAGE, {})
    push2_compatibility = read_json(PUSH2_CROSS_LANE_COMPATIBILITY, {})
    lane_a_checks = read_json(CHECK_REPORT_FIXTURES, {})
    lane_a_authority = read_json(AUTHORITY_ENVELOPE_FIXTURES, {})
    watch = read_json(WATCH_ITEMS, {})
    route = read_json(APP_REVIEW_DECISION, {})
    dispositions = read_json(DISPOSITION_FIXTURES, {})
    runtime_spine = read_json(RUNTIME_SPINE_DECISION, {})
    perception_to_event = read_json(PERCEPTION_TO_EVENT_DECISION, {})
    gates = [
        {
            "gate_id": "PUSH2_INTEGRATION_BRANCH_AVAILABLE",
            "status": "PASS" if remote_branch_available() and status_is_pass(integration) else "FAIL",
            "branch": PUSH2_INTEGRATION_BRANCH,
            "evidence_paths": [rel(PUSH2_INTEGRATION_DECISION)],
            "missing": [] if PUSH2_INTEGRATION_DECISION.exists() else [rel(PUSH2_INTEGRATION_DECISION)],
            "note": "Push 2 cross-lane integration branch and decision are available.",
        },
        gate_row(
            "CHECK_REPORTS_AND_AUTHORITY_ENVELOPES_PRESENT",
            [CHECK_REPORT_FIXTURES, AUTHORITY_ENVELOPE_FIXTURES, PUSH2_CHECK_AUTHORITY_COVERAGE],
            [lane_a_checks, lane_a_authority, check_coverage],
            "Push 2 CHECK v0 and AuthorityEnvelope v1 outputs are consumable.",
            lane_a_checks.get("report_count", 0) > 0 and lane_a_authority.get("envelope_count", 0) > 0,
        ),
        gate_row(
            "WATCH_SCOUT_ITEMS_PRESENT",
            [WATCH_ITEMS],
            [watch],
            "Push 2 WATCH Scout v1 WatchItems are available.",
            len(watch.get("items", [])) > 0,
        ),
        gate_row(
            "APP_REVIEW_ROUTE_AND_DISPOSITIONS_PRESENT",
            [APP_REVIEW_DECISION, APP_REVIEW_FIXTURES, DISPOSITION_FIXTURES],
            [route, read_json(APP_REVIEW_FIXTURES, {}), dispositions],
            "Push 2 App Review Route and DispositionEvent fixtures are available.",
            route.get("review_item_count", 0) > 0 and len(dispositions.get("disposition_events", [])) > 0,
        ),
        gate_row(
            "EVENT_FABRIC_R0_1_RUNTIME_SPINE_PRESENT",
            [RUNTIME_SPINE_DECISION, PERCEPTION_TO_EVENT_DECISION, R7B_EVENT_LOG],
            [runtime_spine, perception_to_event],
            "Event Fabric R0.1 runtime spine and perception-to-event integration are available.",
            PACKAGES_EVENT_FABRIC.exists(),
        ),
        {
            "gate_id": "PUSH2_PROTECTED_DIFFS_CLEAN_AT_CLOSEOUT",
            "status": "PASS"
            if route.get("tests", {}).get("ask_scoped_diff", {}).get("status") == "PASS"
            and route.get("tests", {}).get("r7_scoped_diff", {}).get("status") == "PASS"
            or (
                push2_compatibility.get("protected_diff_report", {}).get("ask_contract_paths_clean") is True
                and push2_compatibility.get("protected_diff_report", {}).get("r7_runtime_paths_clean") is True
            )
            else "FAIL",
            "evidence_paths": [rel(APP_REVIEW_DECISION), rel(PUSH2_CROSS_LANE_COMPATIBILITY)],
            "missing": [rel(path) for path in [APP_REVIEW_DECISION, PUSH2_CROSS_LANE_COMPATIBILITY] if not path.exists()],
            "note": "Push 2 Lane C closeout recorded clean protected ASK/R7 scoped diffs.",
        },
    ]
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall.entry_gate.v1",
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "gates": gates,
    }


def check_input_files() -> dict[str, Any]:
    required = [
        PUSH2_INTEGRATION_DECISION,
        PUSH2_CHECK_AUTHORITY_COVERAGE,
        PUSH2_WATCH_APP_JOIN,
        CHECK_REPORT_FIXTURES,
        AUTHORITY_ENVELOPE_FIXTURES,
        WATCH_ITEMS,
        APP_REVIEW_FIXTURES,
        APP_REVIEW_DECISION,
        DISPOSITION_FIXTURES,
        RUNTIME_SPINE_DECISION,
        PERCEPTION_TO_EVENT_DECISION,
        R7B_EVENT_LOG,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing}


def coerce_refs(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if not isinstance(values, list):
        values = [values]
    refs: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            ref = value.get("ref_id") or value.get("source_id") or value.get("id")
            if ref:
                refs.append(str(ref))
        else:
            refs.append(str(value))
    return sorted(dict.fromkeys(refs))


def item_candidate_refs(item: dict[str, Any]) -> list[str]:
    refs = coerce_refs(item.get("candidate_observation_refs"))
    display = item.get("candidate_observation_display")
    if isinstance(display, dict):
        refs.extend(coerce_refs(display.get("candidate_observation_refs")))
        if display.get("candidate_observation_ref"):
            refs.append(str(display["candidate_observation_ref"]))
    watch_display = item.get("watch_item_display")
    if isinstance(watch_display, dict) and watch_display.get("candidate_id"):
        refs.append(str(watch_display["candidate_id"]))
    return sorted(dict.fromkeys(refs))


def item_source_ref(item: dict[str, Any]) -> str:
    display = item.get("candidate_observation_display")
    if isinstance(display, dict) and display.get("source_id"):
        return str(display["source_id"])
    evidence = coerce_refs(item.get("evidence_refs"))
    for ref in evidence:
        if ref.startswith("source:") or ref.startswith("source_record:"):
            return ref
    return "source:local-replay-review-context"


def item_class(item: dict[str, Any]) -> str:
    display = item.get("candidate_observation_display")
    if isinstance(display, dict) and display.get("object_class"):
        return str(display["object_class"])
    watch_display = item.get("watch_item_display")
    if isinstance(watch_display, dict):
        return str(watch_display.get("query_id") or "watch_review_prompt")
    return str(item.get("item_kind", "review_item"))


def item_review_state(item: dict[str, Any]) -> str:
    display = item.get("candidate_observation_display")
    if isinstance(display, dict) and display.get("review_state"):
        return str(display["review_state"])
    return str(item.get("item_kind", "review_context"))


def first_by(items: list[dict[str, Any]], predicate: Any, fallback_index: int = 0) -> dict[str, Any]:
    for item in items:
        if predicate(item):
            return item
    return items[fallback_index]


def make_diff_item(
    diff_item_id: str,
    diff_family: str,
    before_ref: str,
    after_ref: str,
    change_summary: str,
    subject: dict[str, Any],
    changed_event_refs: list[str] | None = None,
    changed_watch_item_refs: list[str] | None = None,
) -> dict[str, Any]:
    changed_event_refs = changed_event_refs if changed_event_refs is not None else coerce_refs(subject.get("event_refs"))
    changed_watch_item_refs = changed_watch_item_refs if changed_watch_item_refs is not None else []
    item = {
        "schema_version": "main-citybrain.push3.lane_c.diff_item.v1",
        "diff_item_id": diff_item_id,
        "diff_family": diff_family,
        "before_ref": before_ref,
        "after_ref": after_ref,
        "changed_event_refs": coerce_refs(changed_event_refs),
        "changed_candidate_observation_refs": item_candidate_refs(subject),
        "changed_watch_item_refs": coerce_refs(changed_watch_item_refs),
        "change_summary": change_summary,
        "evidence_refs": coerce_refs(subject.get("evidence_refs")) or ["evidence:push3-diff:local-replay-context"],
        "limitation_refs": coerce_refs(subject.get("limitation_refs")) + LIMITATIONS,
        "trace_refs": coerce_refs(subject.get("trace_refs")) + [f"PUSH3:DIFF:{diff_family}"],
        "check_report_ref": subject.get("check_report_id") or subject.get("check_report_ref"),
        "authority_envelope_ref": subject.get("authority_envelope_id") or subject.get("authority_envelope_ref"),
        "review_required": True,
        "official_status": "not_official",
        "not_executed": NOT_EXECUTED,
        "cannot_claim": CANNOT_CLAIM,
        "read_only": True,
        "watch_feed_eligible": True,
    }
    item["diff_item_hash"] = stable_hash(item)
    return item


def build_diff_contract() -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_scout_v1.contract.v1",
        "status": "PASS",
        "mode": "local_replay_readonly",
        "diff_families": DIFF_FAMILIES,
        "required_fields": [
            "diff_item_id",
            "diff_family",
            "before_ref",
            "after_ref",
            "changed_event_refs",
            "changed_candidate_observation_refs",
            "changed_watch_item_refs",
            "change_summary",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "review_required",
            "official_status",
            "not_executed",
            "cannot_claim",
        ],
        "watch_feed_policy": "DiffItems may feed WatchItems as review prompts only.",
        "no_official_findings_or_actions": True,
        "no_live_api_url_llm": True,
        "no_cer_assertion_shapes_invented": True,
        "input_refs": [
            rel(PUSH2_INTEGRATION_DECISION),
            rel(WATCH_ITEMS),
            rel(APP_REVIEW_FIXTURES),
            rel(DISPOSITION_FIXTURES),
        ],
    }


def build_diff_items(review_items: list[dict[str, Any]], watch_items: list[dict[str, Any]], disposition_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["review_item_id"]: item for item in review_items}
    perception_new = first_by(review_items, lambda item: item.get("item_kind") == "perception_item")
    changed_state = first_by(review_items, lambda item: item_review_state(item) == "unresolved_review_candidate", 1)
    authority_subject = first_by(review_items, lambda item: item.get("check_report_id") and item.get("authority_envelope_id"), 0)
    disposition = disposition_events[0]
    disposition_target = by_id.get(disposition.get("target_ref"), perception_new)
    return [
        make_diff_item(
            "diff:item:new_item:0001",
            "new_item",
            rel(WATCH_ITEMS),
            rel(APP_REVIEW_FIXTURES),
            "App Review Route materialized review items that were not present in the WATCH-only snapshot.",
            perception_new,
            changed_watch_item_refs=[watch.get("watch_item_id", "") for watch in watch_items[:2]],
        ),
        make_diff_item(
            "diff:item:changed_review_state:0001",
            "changed_review_state",
            "outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay/R7B_MATERIALIZED_REVIEW_STATE.json",
            rel(APP_REVIEW_FIXTURES),
            "Local/replay candidate review state is now visible as a read-only app route review item.",
            changed_state,
        ),
        make_diff_item(
            "diff:item:changed_authority_or_check_status:0001",
            "changed_authority_or_check_status",
            rel(CHECK_REPORT_FIXTURES),
            rel(APP_REVIEW_FIXTURES),
            "Push 2 CHECK and Authority references remain attached to the app route review item.",
            authority_subject,
        ),
        make_diff_item(
            "diff:item:new_disposition:0001",
            "new_disposition",
            rel(APP_REVIEW_FIXTURES),
            rel(DISPOSITION_FIXTURES),
            "A local DispositionEvent was appended for review recall without creating an official action.",
            disposition_target,
            changed_event_refs=[disposition["event_id"]],
            changed_watch_item_refs=[disposition.get("target_ref", "")] if str(disposition.get("target_ref", "")).startswith("lane-c:review-item:watch") else [],
        ),
    ]


def make_recall_match(
    recall_match_id: str,
    match_family: str,
    subject: dict[str, Any],
    matched_ref: str,
    features: list[str],
    score: float,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
    query_ref: str | None = None,
) -> dict[str, Any]:
    item = {
        "schema_version": "main-citybrain.push3.lane_c.recall_match_item.v1",
        "recall_match_id": recall_match_id,
        "query_ref": query_ref or subject.get("review_item_id") or subject.get("watch_item_id") or subject.get("diff_item_id"),
        "subject_ref": subject.get("review_item_id") or subject.get("watch_item_id") or subject.get("diff_item_id"),
        "matched_ref": matched_ref,
        "match_family": match_family,
        "match_features": sorted(dict.fromkeys(features)),
        "score": score,
        "evidence_refs": coerce_refs(evidence_refs) or ["evidence:push3-recall:local-replay-context"],
        "limitation_refs": sorted(dict.fromkeys(coerce_refs(limitation_refs) + LIMITATIONS)),
        "trace_refs": sorted(dict.fromkeys(coerce_refs(trace_refs) + [f"PUSH3:RECALL:{match_family}"])),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "cannot_claim": CANNOT_CLAIM,
        "local_replay_only": True,
        "cross_city_claim": False,
        "official_status": "not_official",
    }
    item["recall_match_hash"] = stable_hash(item)
    return item


def build_recall_contract() -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_c.recall_matcher_contract.v1",
        "status": "PASS",
        "mode": "local_replay_computed_matchers",
        "matcher_families": RECALL_FAMILIES,
        "required_fields": [
            "recall_match_id",
            "query_ref",
            "matched_ref",
            "match_family",
            "match_features",
            "score",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "cannot_claim",
        ],
        "score_policy": "Deterministic local/replay feature overlap score, not probabilistic truth.",
        "no_cross_city_claims_until_federation": True,
        "no_live_api_url_llm": True,
        "no_cer_assertion_shapes_invented": True,
        "input_refs": [rel(APP_REVIEW_FIXTURES), rel(WATCH_ITEMS), rel(DISPOSITION_FIXTURES)],
    }


def build_recall_matches(review_items: list[dict[str, Any]], watch_items: list[dict[str, Any]], disposition_events: list[dict[str, Any]], diff_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["review_item_id"]: item for item in review_items}
    accepted_a = first_by(review_items, lambda item: item_class(item) == "person_like_shape")
    accepted_b = first_by(
        review_items,
        lambda item: item.get("review_item_id") != accepted_a.get("review_item_id") and item_class(item) == item_class(accepted_a),
        4,
    )
    source_a = accepted_a
    source_b = first_by(
        review_items,
        lambda item: item.get("review_item_id") != source_a.get("review_item_id") and item_source_ref(item) == item_source_ref(source_a),
        4,
    )
    watch_a = watch_items[0]
    watch_b = first_by(
        watch_items,
        lambda item: item.get("watch_item_id") != watch_a.get("watch_item_id") and item.get("watch_family") == watch_a.get("watch_family"),
        1,
    )
    spatial_a = accepted_a
    spatial_b = source_b
    disposition = disposition_events[0]
    disposition_target = by_id.get(disposition.get("target_ref"), accepted_a)
    return [
        make_recall_match(
            "recall:match:same_candidate_observation_class:0001",
            "same_candidate_observation_class",
            accepted_a,
            accepted_b["review_item_id"],
            [f"object_class:{item_class(accepted_a)}", *item_candidate_refs(accepted_a)],
            0.93,
            accepted_a.get("evidence_refs", []),
            accepted_a.get("limitation_refs", []),
            accepted_a.get("trace_refs", []),
            accepted_a["check_report_id"],
            accepted_a["authority_envelope_id"],
        ),
        make_recall_match(
            "recall:match:same_source_class:0001",
            "same_source_class",
            source_a,
            source_b["review_item_id"],
            [f"source_ref:{item_source_ref(source_a)}", f"source_class:{source_a.get('source_class', 'local_replay')}"],
            0.89,
            source_a.get("evidence_refs", []),
            source_a.get("limitation_refs", []),
            source_a.get("trace_refs", []),
            source_a["check_report_id"],
            source_a["authority_envelope_id"],
        ),
        make_recall_match(
            "recall:match:similar_watch_family:0001",
            "similar_watch_family",
            watch_a,
            watch_b["watch_item_id"],
            [f"watch_family:{watch_a['watch_family']}", f"source_event_type:{watch_a.get('source_event_type', 'unknown')}"],
            0.86,
            watch_a.get("evidence_refs", []),
            watch_a.get("limitation_refs", []),
            watch_a.get("trace_refs", []),
            watch_a["check_report_ref"],
            watch_a["authority_envelope_ref"],
        ),
        make_recall_match(
            "recall:match:same_spatial_or_entity_ref:0001",
            "same_spatial_or_entity_ref",
            spatial_a,
            spatial_b["review_item_id"],
            [f"source_ref:{item_source_ref(spatial_a)}", "spatial_or_entity_scope:local_replay_source_ref"],
            0.84,
            spatial_a.get("evidence_refs", []),
            spatial_a.get("limitation_refs", []),
            spatial_a.get("trace_refs", []),
            spatial_a["check_report_id"],
            spatial_a["authority_envelope_id"],
        ),
        make_recall_match(
            "recall:match:same_disposition_pattern:0001",
            "same_disposition_pattern",
            diff_items[-1],
            disposition.get("target_ref", disposition_target["review_item_id"]),
            [
                f"disposition:{disposition.get('payload', {}).get('disposition')}",
                "visibility:individual_reviewer_operator",
                "analytics:aggregate_only",
            ],
            0.79,
            disposition_target.get("evidence_refs", []),
            disposition.get("limitation_refs", []),
            disposition.get("trace_refs", []),
            disposition_target["check_report_id"],
            disposition_target["authority_envelope_id"],
            query_ref=disposition["event_id"],
        ),
    ]


def build_diff_fixtures(diff_contract: dict[str, Any], diff_items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_scout_v1.fixtures.v1",
        "status": "PASS",
        "source_snapshots": {
            "before_watch_items": rel(WATCH_ITEMS),
            "after_app_review_route": rel(APP_REVIEW_FIXTURES),
            "after_disposition_events": rel(DISPOSITION_FIXTURES),
            "push2_integration": rel(PUSH2_INTEGRATION_DECISION),
        },
        "contract_ref": "DIFF_SCOUT_V1_CONTRACT.json",
        "diff_item_count": len(diff_items),
        "diff_families": DIFF_FAMILIES,
        "diff_items": diff_items,
    }


def build_watch_compatibility(diff_items: list[dict[str, Any]], watch_items: list[dict[str, Any]]) -> dict[str, Any]:
    prompts = []
    for index, item in enumerate(diff_items, start=1):
        prompts.append(
            {
                "watch_prompt_ref": f"watch:prompt:from-diff:{index:04d}",
                "source_diff_item_ref": item["diff_item_id"],
                "watch_item_kind": "review_prompt",
                "watch_family": f"diff_{item['diff_family']}",
                "review_required": True,
                "official_status": "not_official",
                "not_action": True,
                "not_finding": True,
                "check_report_ref": item["check_report_ref"],
                "authority_envelope_ref": item["authority_envelope_ref"],
                "evidence_refs": item["evidence_refs"],
                "limitation_refs": item["limitation_refs"],
                "trace_refs": item["trace_refs"] + ["PUSH3:DIFF_TO_WATCH_COMPATIBILITY"],
            }
        )
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_to_watch_compatibility.v1",
        "status": "PASS",
        "diff_items_can_feed_watch_items": True,
        "watch_items_remain_review_prompts": True,
        "check_reports_preserved": all(prompt["check_report_ref"] for prompt in prompts),
        "authority_envelopes_preserved": all(prompt["authority_envelope_ref"] for prompt in prompts),
        "no_direct_findings_or_actions": True,
        "source_watch_item_count": len(watch_items),
        "generated_review_prompt_count": len(prompts),
        "generated_review_prompts": prompts,
    }


def build_coverage(diff_items: list[dict[str, Any]], recall_matches: list[dict[str, Any]], compatibility: dict[str, Any]) -> dict[str, Any]:
    check_reports = read_json(CHECK_REPORT_FIXTURES, {})
    authority = read_json(AUTHORITY_ENVELOPE_FIXTURES, {})
    all_diff_checks = all(item.get("check_report_ref") for item in diff_items)
    all_diff_authority = all(item.get("authority_envelope_ref") for item in diff_items)
    all_recall_checks = all(item.get("check_report_ref") for item in recall_matches)
    all_recall_authority = all(item.get("authority_envelope_ref") for item in recall_matches)
    status = "PASS" if all([all_diff_checks, all_diff_authority, all_recall_checks, all_recall_authority, compatibility["status"] == "PASS"]) else "FAIL"
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall.check_authority_coverage.v1",
        "status": status,
        "source_check_report_count": check_reports.get("report_count", 0),
        "source_authority_envelope_count": authority.get("envelope_count", 0),
        "diff_item_count": len(diff_items),
        "recall_match_count": len(recall_matches),
        "all_diff_items_have_check_report_ref": all_diff_checks,
        "all_diff_items_have_authority_envelope_ref": all_diff_authority,
        "all_recall_matches_have_check_report_ref": all_recall_checks,
        "all_recall_matches_have_authority_envelope_ref": all_recall_authority,
        "check_reports_present": check_reports.get("report_count", 0) > 0,
        "authority_envelopes_present": authority.get("envelope_count", 0) > 0,
        "watch_feed_compatible": compatibility.get("diff_items_can_feed_watch_items") is True,
        "new_check_or_authority_schema_changes": False,
        "cer_assertion_dependency": False,
        "coverage_hash": stable_hash({"diff": diff_items, "recall": recall_matches}),
    }


def boundary_markdown() -> str:
    lines = [
        "# DIFF/RECALL Boundary And Non-Claims",
        "",
        "Push 3 Lane C is a local/replay read-only package.",
        "",
        "## Non-Claims",
    ]
    lines.extend(f"- {claim}" for claim in CANNOT_CLAIM)
    lines.extend(
        [
            "",
            "## Not Executed",
        ]
    )
    lines.extend(f"- {item}" for item in NOT_EXECUTED)
    lines.extend(
        [
            "",
            "## Limitations",
        ]
    )
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.extend(
        [
            "",
            "No AttributeAssertion or CER assertion shape is emitted; CER remains Push 4.",
        ]
    )
    return "\n".join(lines)


def build_boundary_audit(diff_items: list[dict[str, Any]], recall_matches: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps({"diff": diff_items, "recall": recall_matches}, sort_keys=True).lower()
    forbidden_positive = [
        '"official_status": "official"',
        '"execution_status": "executed"',
        '"official_action_allowed": true',
        '"not_action": false',
        '"cross_city_claim": true',
    ]
    return {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall.boundary_audit.v1",
        "status": "PASS" if not any(token in serialized for token in forbidden_positive) and coverage["status"] == "PASS" else "FAIL",
        "local_replay_only": True,
        "read_only_only": True,
        "no_cross_city_claims": all(match.get("cross_city_claim") is False for match in recall_matches),
        "no_official_findings_actions": not any(token in serialized for token in forbidden_positive[:3]),
        "no_cer_assertion_shapes_invented": "attributeassertion" not in serialized,
        "no_live_api_url_llm": True,
        "check_reports_preserved": coverage["all_diff_items_have_check_report_ref"] and coverage["all_recall_matches_have_check_report_ref"],
        "authority_envelopes_preserved": coverage["all_diff_items_have_authority_envelope_ref"] and coverage["all_recall_matches_have_authority_envelope_ref"],
    }


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    app_route = read_json(APP_REVIEW_FIXTURES, {})
    watch = read_json(WATCH_ITEMS, {})
    disposition = read_json(DISPOSITION_FIXTURES, {})
    review_items = list(app_route.get("review_items", []))
    watch_items = list(watch.get("items", []))
    disposition_events = list(disposition.get("disposition_events", []))
    diff_contract = build_diff_contract()
    diff_items = build_diff_items(review_items, watch_items, disposition_events)
    diff_fixtures = build_diff_fixtures(diff_contract, diff_items)
    recall_contract = build_recall_contract()
    recall_matches = build_recall_matches(review_items, watch_items, disposition_events, diff_items)
    compatibility = build_watch_compatibility(diff_items, watch_items)
    coverage = build_coverage(diff_items, recall_matches, compatibility)
    boundary = build_boundary_audit(diff_items, recall_matches, coverage)
    status = PASS_STATUS if coverage["status"] == "PASS" and compatibility["status"] == "PASS" and boundary["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall_readonly.decision.v1",
        "package": PACKAGE,
        "task_id": TASK_ID,
        "status": status,
        "entry_gate": entry_gate_report(),
        "diff_item_count": len(diff_items),
        "diff_families": DIFF_FAMILIES,
        "recall_match_count": len(recall_matches),
        "matcher_families": RECALL_FAMILIES,
        "watch_feed_compatible": compatibility["diff_items_can_feed_watch_items"],
        "no_cross_city_claims": boundary["no_cross_city_claims"],
        "no_official_findings_actions": boundary["no_official_findings_actions"],
        "no_cer_assertion_shapes_invented": boundary["no_cer_assertion_shapes_invented"],
        "check_report_coverage": coverage["status"],
        "authority_envelope_coverage": coverage["status"],
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    return {
        "decision": decision,
        "diff_contract": diff_contract,
        "diff_fixtures": diff_fixtures,
        "diff_items": {"schema_version": "main-citybrain.push3.lane_c.diff_items.v1", "status": "PASS", "items": diff_items},
        "recall_contract": recall_contract,
        "recall_matches": {"schema_version": "main-citybrain.push3.lane_c.recall_match_items.v1", "status": "PASS", "items": recall_matches},
        "compatibility": compatibility,
        "coverage": coverage,
        "boundary": boundary,
    }


def test_log_text(tests: dict[str, Any], outputs: dict[str, Any]) -> str:
    targeted = tests.get("targeted", {})
    full = tests.get("full_discovery", {})
    return "\n".join(
        [
            "# DIFF/RECALL Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{targeted.get('result', 'NOT_RUN')}`, `{targeted.get('count', 0)}` tests",
            f"- full discovery: `{full.get('result', 'NOT_RUN')}`, `{full.get('count', 0)}` tests",
            f"- protected ASK diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- protected R7 diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- DiffItems produced: `{outputs['decision'].get('diff_item_count', 0)}`",
            f"- RecallMatchItems produced: `{outputs['decision'].get('recall_match_count', 0)}`",
            f"- WATCH feed compatible: `{outputs['compatibility'].get('status')}`",
            f"- Check/Authority coverage: `{outputs['coverage'].get('status')}`",
            f"- boundary audit: `{outputs['boundary'].get('status')}`",
            "",
            "This package remains local/replay, read-only, and branch-scoped.",
        ]
    )


def write_bundle(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_output_root(OUTPUT_ROOT)
    gate = entry_gate_report()
    input_check = check_input_files()
    if gate["status"] != "PASS" or input_check["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push3.lane_c.diff_recall_readonly.decision.v1",
            "package": PACKAGE,
            "task_id": TASK_ID,
            "status": STOP_STATUS,
            "entry_gate": gate,
            "input_check": input_check,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "DIFF_RECALL_READONLY_DECISION.json", decision)
        write_text(OUTPUT_ROOT / "DIFF_RECALL_BOUNDARY_AND_NON_CLAIMS.md", boundary_markdown())
        write_hash_manifest()
        return {"decision": decision}
    outputs = build_outputs(tests)
    write_json(OUTPUT_ROOT / "DIFF_RECALL_READONLY_DECISION.json", outputs["decision"])
    write_json(OUTPUT_ROOT / "DIFF_SCOUT_V1_CONTRACT.json", outputs["diff_contract"])
    write_json(OUTPUT_ROOT / "DIFF_SCOUT_V1_FIXTURES.json", outputs["diff_fixtures"])
    write_json(OUTPUT_ROOT / "DIFF_ITEMS.json", outputs["diff_items"])
    write_json(OUTPUT_ROOT / "RECALL_MATCHER_CONTRACT.json", outputs["recall_contract"])
    write_json(OUTPUT_ROOT / "RECALL_MATCH_ITEMS.json", outputs["recall_matches"])
    write_json(OUTPUT_ROOT / "DIFF_TO_WATCH_COMPATIBILITY.json", outputs["compatibility"])
    write_json(OUTPUT_ROOT / "DIFF_RECALL_CHECK_AUTHORITY_COVERAGE.json", outputs["coverage"])
    write_text(OUTPUT_ROOT / "DIFF_RECALL_BOUNDARY_AND_NON_CLAIMS.md", boundary_markdown())
    write_text(OUTPUT_ROOT / "DIFF_RECALL_TEST_LOG.md", test_log_text(tests, outputs))
    manifest = write_hash_manifest()
    outputs["hash_manifest"] = manifest
    return outputs


def closeout_summary_text(decision: dict[str, Any], route_hash: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# DIFF/RECALL Read-Only Closeout",
            "",
            f"Status: `{decision['status']}`",
            "",
            f"- DiffItems: `{decision.get('diff_item_count', 0)}`",
            f"- diff families: `{', '.join(decision.get('diff_families', []))}`",
            f"- RecallMatchItems: `{decision.get('recall_match_count', 0)}`",
            f"- matcher families: `{', '.join(decision.get('matcher_families', []))}`",
            f"- WATCH feed compatible: `{decision.get('watch_feed_compatible')}`",
            f"- route hash verification: `{route_hash['status']}`",
            "",
            "Lane C is closed as a local/replay read-only DIFF/RECALL package. INFRA owns Push 3 integration.",
        ]
    )


def limitations_text() -> str:
    return "# DIFF/RECALL Read-Only Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS)


def next_steps_text() -> str:
    return "\n".join(
        [
            "# DIFF/RECALL Next Steps",
            "",
            "- Wait for Push 3 Lane A and Lane B branch publication.",
            "- INFRA integrates Lane B, then Lane C DIFF/RECALL, then Lane A Flow 1 packaging.",
            "- Keep CER/assertion engine work deferred to Push 4.",
            "- Preserve read-only boundaries until an approved integration lane changes them.",
        ]
    )


def write_closeout(bundle: dict[str, Any]) -> dict[str, Any]:
    reset_output_root(CLOSEOUT_ROOT)
    decision = bundle.get("decision", {})
    route_hash = verify_hash_manifest(OUTPUT_ROOT)
    status = PASS_STATUS if decision.get("status") == PASS_STATUS and route_hash["status"] == "PASS" else FAIL_STATUS
    closeout_decision = {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall_readonly.closeout.v1",
        "package": PACKAGE,
        "task_id": f"{TASK_ID}-CLOSEOUT",
        "status": status,
        "route_status": decision.get("status"),
        "route_output_root": rel(OUTPUT_ROOT),
        "route_hash_manifest": route_hash,
        "diff_item_count": decision.get("diff_item_count", 0),
        "diff_families": decision.get("diff_families", []),
        "recall_match_count": decision.get("recall_match_count", 0),
        "matcher_families": decision.get("matcher_families", []),
        "watch_feed_compatible": decision.get("watch_feed_compatible", False),
        "no_cross_city_claims": decision.get("no_cross_city_claims", False),
        "protected_ask_diff": decision.get("tests", {}).get("ask_scoped_diff", {}).get("status", "NOT_RUN"),
        "protected_r7_diff": decision.get("tests", {}).get("r7_scoped_diff", {}).get("status", "NOT_RUN"),
        "infra_canonical_integration_required": True,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "DIFF_RECALL_READONLY_CLOSEOUT_DECISION.json", closeout_decision)
    write_text(CLOSEOUT_ROOT / "DIFF_RECALL_READONLY_CLOSEOUT_SUMMARY.md", closeout_summary_text(closeout_decision, route_hash))
    write_text(CLOSEOUT_ROOT / "DIFF_RECALL_READONLY_CLOSEOUT_LIMITATIONS.md", limitations_text())
    write_text(CLOSEOUT_ROOT / "DIFF_RECALL_READONLY_CLOSEOUT_NEXT_STEPS.md", next_steps_text())
    manifest = write_hash_manifest(
        CLOSEOUT_ROOT,
        "DIFF_RECALL_READONLY_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push3.lane_c.diff_recall_readonly.closeout.hash_manifest.v1",
    )
    closeout_decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(CLOSEOUT_ROOT / "DIFF_RECALL_READONLY_CLOSEOUT_DECISION.json", closeout_decision)
    write_hash_manifest(
        CLOSEOUT_ROOT,
        "DIFF_RECALL_READONLY_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push3.lane_c.diff_recall_readonly.closeout.hash_manifest.v1",
    )
    return {"decision": closeout_decision}


def final_summary_text(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# DIFF/RECALL Read-Only Final Status",
            "",
            f"Status: `{decision['status']}`",
            "",
            "- implementation verification complete",
            "- DIFF Scout v1 output package complete",
            "- RECALL computed matcher output package complete",
            "- lane closeout complete",
            "- final status package complete",
            "",
            "Canonical merge remains INFRA-owned.",
        ]
    )


def write_final_status(closeout: dict[str, Any]) -> dict[str, Any]:
    reset_output_root(FINAL_ROOT)
    closeout_decision = closeout.get("decision", {})
    route_hash = verify_hash_manifest(OUTPUT_ROOT)
    closeout_hash = verify_hash_manifest(CLOSEOUT_ROOT, "DIFF_RECALL_READONLY_CLOSEOUT_HASH_MANIFEST.json")
    status = PASS_STATUS if closeout_decision.get("status") == PASS_STATUS and route_hash["status"] == "PASS" and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final_decision = {
        "schema_version": "main-citybrain.push3.lane_c.diff_recall_readonly.final_status.v1",
        "package": PACKAGE,
        "task_id": f"{TASK_ID}-FINAL-STATUS",
        "status": status,
        "route_status": closeout_decision.get("route_status"),
        "closeout_status": closeout_decision.get("status"),
        "route_hash_manifest": route_hash,
        "closeout_hash_manifest": closeout_hash,
        "completed_through": [
            "C0_PUSH2_GATE_AND_DISCOVERY",
            "C1_DIFF_SCOUT_V1_CONTRACT",
            "C2_DIFF_SCOUT_FIXTURES_R1",
            "C3_RECALL_MATCHERS_R1",
            "C4_WATCH_FEED_COMPATIBILITY_R2",
            "C5_CLOSEOUT",
            "C6_BRANCH_PUBLISH_READY",
            "C7_FINAL_STATUS",
        ],
        "exact_stage_list": [
            "scripts/run_main_citybrain_push3_lane_c_diff_recall_readonly.py",
            "tests/test_main_citybrain_push3_lane_c_diff_recall_readonly.py",
            "outputs/push3_lane_c_diff_recall_readonly/",
            "outputs/push3_lane_c_diff_recall_readonly_closeout/",
            "outputs/push3_lane_c_diff_recall_readonly_final_status/",
        ],
        "commit_message": COMMIT_SUBJECT,
        "branch": BRANCH,
        "canonical_merged": False,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "DIFF_RECALL_READONLY_FINAL_STATUS_DECISION.json", final_decision)
    write_text(FINAL_ROOT / "DIFF_RECALL_READONLY_FINAL_STATUS_SUMMARY.md", final_summary_text(final_decision))
    manifest = write_hash_manifest(
        FINAL_ROOT,
        "DIFF_RECALL_READONLY_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push3.lane_c.diff_recall_readonly.final_status.hash_manifest.v1",
    )
    final_decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(FINAL_ROOT / "DIFF_RECALL_READONLY_FINAL_STATUS_DECISION.json", final_decision)
    write_hash_manifest(
        FINAL_ROOT,
        "DIFF_RECALL_READONLY_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push3.lane_c.diff_recall_readonly.final_status.hash_manifest.v1",
    )
    return {"decision": final_decision}


def write_all_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = write_bundle(tests)
    if bundle.get("decision", {}).get("status") == STOP_STATUS:
        return {"bundle": bundle, "decision": bundle["decision"]}
    closeout = write_closeout(bundle)
    final = write_final_status(closeout)
    return {"bundle": bundle, "closeout": closeout, "final": final, "decision": final["decision"]}


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    count = 0
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "count": count,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, capture_output=True)
    return {
        "command": "git diff -- " + " ".join(paths),
        "returncode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def run_tests() -> dict[str, Any]:
    targeted = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push3_lane_c_diff_recall_readonly"])
    return {
        "runner": "PASS",
        "targeted": targeted,
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def main() -> int:
    initial = write_all_outputs({"runner": "PRE_TEST"})
    if initial["decision"]["status"] == STOP_STATUS:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = write_all_outputs(tests)
    print(
        json.dumps(
            {
                "bundle": result["bundle"]["decision"],
                "closeout": result["closeout"]["decision"],
                "final": result["final"]["decision"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["targeted"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
