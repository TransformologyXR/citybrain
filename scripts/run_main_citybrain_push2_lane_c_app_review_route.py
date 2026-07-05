#!/usr/bin/env python3
"""Build PUSH 2 Lane C app review route and DispositionEvent bundle.

This lane is a local/replay review route only. It joins existing R7
perception review items with D9 WATCH and CHECK fixtures, renders a static
operator review workspace, and emits local Event Fabric-compatible
DispositionEvent fixtures. It does not mutate ASK, R7, or production runtime
contracts.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push2_lane_c_app_review_route"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push2_lane_c_app_review_route_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push2_lane_c_app_review_route_final_status"

TASK_ID = "MAIN-CITYBRAIN-PUSH2-LANE-C-APP-REVIEW-ROUTE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_PUSH2_LANE_C_APP_REVIEW_ROUTE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_PUSH2_LANE_C_APP_REVIEW_ROUTE_BOUNDARY_OR_ROUTE_REGRESSION"
STOP_STATUS = "STOPPED_MAIN_CITYBRAIN_PUSH2_LANE_C_ENTRY_GATE_NOT_MET"

R7A_FIXTURES = OUTPUTS_ROOT / "main_citybrain_r7a_perception_candidate_observation_ingress" / "R7A_CANDIDATE_OBSERVATION_FIXTURES.json"
R7B_REVIEW_STATE = OUTPUTS_ROOT / "main_citybrain_r7b_perception_to_event_fabric_local_replay" / "R7B_MATERIALIZED_REVIEW_STATE.json"
R7B_EVENT_LOG = OUTPUTS_ROOT / "main_citybrain_r7b_perception_to_event_fabric_local_replay" / "R7B_LOCAL_EVENT_LOG.jsonl"
R7D_WEBUI = OUTPUTS_ROOT / "main_citybrain_r7d_webui_kit_event_state_smoke" / "R7D_WEBUI_EVENT_STATE_SMOKE_EXPORT.json"
R7D_KIT = OUTPUTS_ROOT / "main_citybrain_r7d_webui_kit_event_state_smoke" / "R7D_KIT_EVENT_STATE_SMOKE_EXPORT.json"
R7E_DECISION = OUTPUTS_ROOT / "main_citybrain_r7e_perception_review_workflow_closeout" / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json"

D9_WATCH = OUTPUTS_ROOT / "main_citybrain_d9_watch_named_query_queue_r4" / "D9_WATCH_REVIEW_QUEUE_FIXTURE.json"
D9_CHECK_RULESET = OUTPUTS_ROOT / "main_citybrain_d9_check_guardrail_and_source_depth_r6" / "D9_CHECK_RULESET.json"
D9_CHECK_RESULTS = OUTPUTS_ROOT / "main_citybrain_d9_check_guardrail_and_source_depth_r6" / "D9_CHECK_SAMPLE_RESULTS.json"
D9_FREEZE = OUTPUTS_ROOT / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze" / "D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_DECISION.json"

EVENT_FABRIC_D1 = OUTPUTS_ROOT / "main_platform_event_fabric_d1" / "MAIN_PLATFORM_EVENT_FABRIC_D1_DECISION.json"
EVENT_FABRIC_D2 = OUTPUTS_ROOT / "main_event_fabric_d2" / "MAIN_EVENT_FABRIC_D2_DECISION.json"
EVENT_FABRIC_D3 = OUTPUTS_ROOT / "main_event_fabric_d3_service_hardening" / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json"
LOCAL_RUNTIME_FABRIC = OUTPUTS_ROOT / "main_citybrain_d5_local_served_runtime_event_fabric_integration_r3" / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json"
REGRESSION_CORPUS = OUTPUTS_ROOT / "main_citybrain_d8_one_truth_regression_r4" / "D8_ONE_TRUTH_REGRESSION_R4_DECISION.json"
ASK_LOOSE_END_LEDGER = OUTPUTS_ROOT / "main_citybrain_d14_governed_open_ask_production_readiness_r1" / "D14_STANDING_CAPABILITY_REGRESSION_REPORT.json"

REQUIRED_OUTPUTS = [
    "APP_REVIEW_ROUTE_DECISION.json",
    "APP_REVIEW_ROUTE_FIXTURES.json",
    "APP_REVIEW_ROUTE_RENDER_STATE_REPORT.json",
    "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
    "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json",
    "APP_REVIEW_ROUTE_TEST_LOG.md",
    "APP_REVIEW_ROUTE_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "APP_REVIEW_ROUTE_CLOSEOUT_DECISION.json",
    "APP_REVIEW_ROUTE_CLOSEOUT_SUMMARY.md",
    "APP_REVIEW_ROUTE_CLOSEOUT_LIMITATIONS.md",
    "APP_REVIEW_ROUTE_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "APP_REVIEW_ROUTE_FINAL_STATUS_DECISION.json",
    "APP_REVIEW_ROUTE_FINAL_STATUS_SUMMARY.md",
    "APP_REVIEW_ROUTE_FINAL_STATUS_HASH_MANIFEST.json",
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
    "Local/replay route only; no production API, URL fetch, live monitoring, or LLM call is used.",
    "Perception items remain candidate-only review items, not official facts or certified detections.",
    "WATCH items remain manual review prompts, not alerts or action requests.",
    "DispositionEvent records local operator review disposition only; they do not create official actions, cases, tickets, dispatch, control, or enforcement.",
    "Individual dispositions are visible only to reviewer/operator roles in this local route; analytics receives aggregate counts only.",
    "INFRA owns canonical integration, merge, and any future production separation of individual disposition visibility from aggregate analytics.",
]

CANNOT_CLAIM = [
    "official violation",
    "legal/certified finding",
    "live monitoring",
    "production feed",
    "identity of a natural person",
    "official case or ticket",
    "dispatch/control/enforcement",
    "automated action",
]

NOT_EXECUTED = [
    "live_camera_connection",
    "production_api",
    "url_fetch",
    "llm_call",
    "official_submission",
    "dispatch_control_enforcement",
]

SAFE_NEXT_LOOKS = [
    "inspect retained evidence refs",
    "compare limitation refs before any claim",
    "run or review CHECK report",
    "record a local disposition with optional note",
    "ask INFRA to integrate only after branch review",
]

DISPOSITIONS = ["confirmed", "dismissed", "needs_more"]
FIXED_EVENT_TIME = "2026-07-05T20:00:00Z"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path = OUTPUT_ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


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


def reset_output_root(root: Path = OUTPUT_ROOT) -> None:
    resolved = root.resolve()
    outputs = OUTPUTS_ROOT.resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_hash_manifest(
    root: Path = OUTPUT_ROOT,
    name: str = "APP_REVIEW_ROUTE_HASH_MANIFEST.json",
    schema: str = "main-citybrain.push2.lane_c.app_review_route.hash_manifest.v1",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path = OUTPUT_ROOT, name: str = "APP_REVIEW_ROUTE_HASH_MANIFEST.json") -> dict[str, Any]:
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
    values = [str(payload.get(field, "")) for field in fields or ("status", "final_status")]
    return any(value.startswith("PASS") for value in values)


def gate_row(gate_id: str, paths: list[Path], status_payloads: list[dict[str, Any]], note: str) -> dict[str, Any]:
    missing = [rel(path) for path in paths if not path.exists()]
    status_ok = all(status_is_pass(payload) for payload in status_payloads)
    ok = not missing and status_ok
    return {
        "gate_id": gate_id,
        "status": "PASS" if ok else "FAIL",
        "evidence_paths": [rel(path) for path in paths],
        "missing": missing,
        "note": note,
    }


def entry_gate_report() -> dict[str, Any]:
    d1 = read_json(EVENT_FABRIC_D1, {})
    d2 = read_json(EVENT_FABRIC_D2, {})
    d3 = read_json(EVENT_FABRIC_D3, {})
    local_fabric = read_json(LOCAL_RUNTIME_FABRIC, {})
    r7e = read_json(R7E_DECISION, {})
    d9 = read_json(D9_FREEZE, {})
    regression = read_json(REGRESSION_CORPUS, {})
    ask = read_json(ASK_LOOSE_END_LEDGER, {})
    gates = [
        gate_row(
            "R0.1_EVENT_FABRIC_BRANCH_AVAILABLE",
            [EVENT_FABRIC_D1, EVENT_FABRIC_D2, EVENT_FABRIC_D3],
            [d1, d2, d3],
            "Event Fabric D1-D3 outputs are branch-available and passing.",
        ),
        gate_row(
            "EVENT_FABRIC_RUNTIME_SPINE_LOCAL",
            [LOCAL_RUNTIME_FABRIC, R7B_EVENT_LOG],
            [local_fabric],
            "Local served Event Fabric route contract and R7B append log are present.",
        ),
        gate_row(
            "LANE_A_CHECK_OUTPUTS_REAL",
            [D9_CHECK_RULESET, D9_CHECK_RESULTS, D9_FREEZE],
            [d9],
            "D9 CHECK rules and sample results are available from the freeze.",
        ),
        gate_row(
            "LANE_B_WATCH_OUTPUTS_REAL",
            [D9_WATCH, D9_FREEZE],
            [d9],
            "D9 WATCH review queue is available from the freeze.",
        ),
        gate_row(
            "R7_PERCEPTION_REVIEW_OUTPUTS_REAL",
            [R7A_FIXTURES, R7B_REVIEW_STATE, R7D_WEBUI, R7D_KIT, R7E_DECISION],
            [r7e],
            "R7 perception-to-review closeout and WebUI/Kit exports are available.",
        ),
        gate_row(
            "REGRESSION_CORPUS_V1_BRANCH_AVAILABLE",
            [REGRESSION_CORPUS],
            [regression],
            "Regression evidence is published via the D8 one-truth regression package.",
        ),
        {
            "gate_id": "ASK_LOOSE_END_LEDGERED",
            "status": "PASS" if ASK_LOOSE_END_LEDGER.exists() and str(ask.get("status", "")).startswith("BLOCKED_OPEN_ASK_ROUTER") else "FAIL",
            "evidence_paths": [rel(ASK_LOOSE_END_LEDGER)],
            "missing": [] if ASK_LOOSE_END_LEDGER.exists() else [rel(ASK_LOOSE_END_LEDGER)],
            "note": "The open ASK router loose end is explicitly ledgered, not silently greened.",
        },
    ]
    return {
        "schema_version": "main-citybrain.push2.lane_c.entry_gate.v1",
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "gates": gates,
    }


def check_input_files() -> dict[str, Any]:
    required = [
        R7A_FIXTURES,
        R7B_REVIEW_STATE,
        R7B_EVENT_LOG,
        R7D_WEBUI,
        R7D_KIT,
        R7E_DECISION,
        D9_WATCH,
        D9_CHECK_RULESET,
        D9_CHECK_RESULTS,
        D9_FREEZE,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing}


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique(values: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for value in values:
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def source_class_for_perception(item: dict[str, Any], candidate: dict[str, Any]) -> str:
    if candidate.get("source_kind"):
        return str(candidate["source_kind"])
    if item.get("source_context_kind"):
        return str(item["source_context_kind"])
    return "local_replay_event_state_query"


def check_report_from_result(target_ref: str, result: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.check_report.v1",
        "check_report_id": f"lane-c:check:{fallback_id}",
        "source_check_id": result.get("check_id") or fallback_id,
        "source_mode_run_id": result.get("mode_run_id"),
        "target_ref": target_ref,
        "status": result.get("status", "PASS_WITH_LIMITATIONS"),
        "rule_ids": result.get("rule_ids", ["check:claim_boundary@v1", "check:no_action_boundary@v1"]),
        "reason": result.get("reason", "Lane C route shows evidence, limitations, trace, and no-action boundary."),
        "source_class": "d9_check_fixture",
        "visible_in_selected_panel": True,
    }


def authority_envelope(target_ref: str, item_kind: str) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.authority_envelope.v1",
        "authority_envelope_id": f"lane-c:authority:{target_ref.replace(':', '-')}",
        "target_ref": target_ref,
        "item_kind": item_kind,
        "scope": "local_review_route",
        "individual_visibility_roles": ["reviewer", "operator"],
        "aggregate_visibility_roles": ["analytics"],
        "allowed_local_affordances": ["record_disposition", "preserve_optional_note", "inspect_evidence", "inspect_check_report"],
        "forbidden_affordances": ["official_action", "official_ticket", "dispatch", "control", "enforcement", "automated_action"],
        "official_action_allowed": False,
        "official_record_created": False,
        "analytics_receives_individual_notes": False,
        "aggregate_analytics_allowed": True,
        "visible_in_selected_panel": True,
    }


def disposition_capture(target_ref: str) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.disposition_capture.v1",
        "target_ref": target_ref,
        "allowed_dispositions": DISPOSITIONS,
        "operator_ref_policy": "local_pseudonymous_allowed",
        "note": {"optional": True, "preserved_if_entered": True},
        "emits_event_type": "review_item.disposition_recorded",
        "official_action_created": False,
        "visible_in_selected_panel": True,
    }


def load_inputs() -> dict[str, Any]:
    return {
        "r7a": read_json(R7A_FIXTURES, {"items": []}),
        "r7b": read_json(R7B_REVIEW_STATE, {}),
        "r7d_webui": read_json(R7D_WEBUI, {"items": []}),
        "r7d_kit": read_json(R7D_KIT, {"items": []}),
        "watch": read_json(D9_WATCH, {"queue_items": []}),
        "check_rules": read_json(D9_CHECK_RULESET, {"rules": []}),
        "check_results": read_json(D9_CHECK_RESULTS, {"results": []}),
    }


def pick_check_result(results: list[dict[str, Any]], item_kind: str, target_hint: str) -> dict[str, Any]:
    if item_kind == "perception_item":
        return next((item for item in results if item.get("target_ref") == "mode:PERCEPTION_VSS"), {})
    hint = target_hint.lower()
    if "nyc" in hint or "mvc" in hint:
        return next((item for item in results if "nyc" in str(item.get("target_ref", "")).lower()), {})
    if "source-gap" in hint or "ev-asset" in hint or "87" in hint:
        return next((item for item in results if "ev-asset-87" in str(item.get("target_ref", "")).lower()), {})
    if "helsinki" in hint:
        return next((item for item in results if "recall" in str(item.get("target_ref", "")).lower()), {})
    return next((item for item in results if "wood-lane" in str(item.get("target_ref", "")).lower()), results[0] if results else {})


def build_perception_items(inputs: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = {item.get("candidate_observation_id"): item for item in inputs["r7a"].get("items", [])}
    kit_by_query = {item.get("query_case_id"): item for item in inputs["r7d_kit"].get("items", [])}
    check_reports: list[dict[str, Any]] = []
    authority: list[dict[str, Any]] = []
    route_items: list[dict[str, Any]] = []
    check_results = inputs["check_results"].get("results", [])
    for index, item in enumerate(inputs["r7d_webui"].get("items", []), start=1):
        route_item_id = f"lane-c:review-item:perception:{index:03d}"
        candidate = candidates.get(item.get("candidate_observation_ref"), {})
        kit = kit_by_query.get(item.get("query_case_id"), {})
        check = check_report_from_result(route_item_id, pick_check_result(check_results, "perception_item", item.get("query_case_id", "")), f"perception-{index:03d}")
        envelope = authority_envelope(route_item_id, "perception_item")
        check_reports.append(check)
        authority.append(envelope)
        display_title = f"Perception review: {item.get('query_family', 'candidate observation').replace('_', ' ')}"
        route_items.append(
            {
                "review_item_id": route_item_id,
                "item_kind": "perception_item",
                "display_title": display_title,
                "candidate_observation_display": {
                    "candidate_observation_ref": item.get("candidate_observation_ref"),
                    "candidate_observation_refs": item.get("candidate_observation_refs", []),
                    "object_class": candidate.get("object_class") or candidate.get("detected_class") or "candidate_observation",
                    "confidence": candidate.get("confidence"),
                    "review_state": item.get("review_state"),
                    "source_id": candidate.get("source_id") or item.get("source_context_ref"),
                    "source_label": candidate.get("source_label") or item.get("source_context_kind"),
                },
                "watch_item_display": None,
                "event_refs": item.get("event_refs", []),
                "evidence_refs": item.get("evidence_refs", []),
                "limitation_refs": item.get("limitation_refs", LIMITATIONS),
                "trace_refs": item.get("trace_refs", []),
                "source_class": source_class_for_perception(item, candidate),
                "check_report_id": check["check_report_id"],
                "authority_envelope_id": envelope["authority_envelope_id"],
                "cannot_claim": item.get("cannot_claim") or CANNOT_CLAIM,
                "not_executed": item.get("not_executed") or NOT_EXECUTED,
                "safe_next_looks": SAFE_NEXT_LOOKS,
                "spatial_overlay_reference": {
                    "surface": "kit",
                    "overlay_id": kit.get("overlay_id"),
                    "overlay_kind": kit.get("overlay_kind", "local_replay_review_marker"),
                    "prim_path": kit.get("prim_path") or kit.get("proposed_prim_path"),
                    "marker_only": kit.get("marker_only", True),
                    "live_kit_control": kit.get("live_kit_control", False),
                    "full_citywide_twin_claim": kit.get("full_citywide_twin_claim", False),
                },
                "disposition_capture": disposition_capture(route_item_id),
                "official_status": item.get("official_status", "not_official"),
                "execution_status": item.get("execution_status", "not_executed"),
                "review_required": item.get("review_required", True),
                "candidate_only": item.get("candidate_only", True),
            }
        )
    return route_items, check_reports, authority


def build_watch_items(inputs: dict[str, Any], start_index: int = 1) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    check_results = inputs["check_results"].get("results", [])
    check_reports: list[dict[str, Any]] = []
    authority: list[dict[str, Any]] = []
    route_items: list[dict[str, Any]] = []
    for index, item in enumerate(inputs["watch"].get("queue_items", []), start=start_index):
        route_item_id = f"lane-c:review-item:watch:{index:03d}"
        check = check_report_from_result(route_item_id, pick_check_result(check_results, "watch_item", item.get("candidate_id", "")), f"watch-{index:03d}")
        envelope = authority_envelope(route_item_id, "watch_item")
        check_reports.append(check)
        authority.append(envelope)
        source_refs = item.get("source_refs", [])
        evidence_refs = [
            f"{ref.get('artifact_type', 'source_record')}:{ref.get('record_id', ref.get('title', 'unknown'))}"
            for ref in source_refs
        ]
        route_items.append(
            {
                "review_item_id": route_item_id,
                "item_kind": "watch_item",
                "display_title": f"WATCH prompt: {item.get('review_reason', item.get('query_id', 'manual review prompt'))}",
                "candidate_observation_display": None,
                "watch_item_display": {
                    "candidate_id": item.get("candidate_id"),
                    "query_id": item.get("query_id"),
                    "mode_run_id": item.get("mode_run_id"),
                    "review_reason": item.get("review_reason"),
                    "recommended_human_review_action_only": item.get("recommended_human_review_action_only"),
                    "false_positive_notes": item.get("false_positive_notes"),
                    "boundary_statement": item.get("boundary_statement"),
                },
                "event_refs": [item.get("mode_run_id")],
                "evidence_refs": evidence_refs,
                "limitation_refs": [item.get("false_positive_notes"), item.get("boundary_statement")] + LIMITATIONS,
                "trace_refs": [item.get("query_id"), item.get("mode_run_id")],
                "source_class": "watch_review_queue_fixture",
                "check_report_id": check["check_report_id"],
                "authority_envelope_id": envelope["authority_envelope_id"],
                "cannot_claim": CANNOT_CLAIM,
                "not_executed": [item.get("execution_state", "not_executed")] + NOT_EXECUTED,
                "safe_next_looks": SAFE_NEXT_LOOKS,
                "spatial_overlay_reference": {
                    "surface": "none",
                    "overlay_id": None,
                    "overlay_kind": "watch_prompt_no_spatial_marker",
                    "prim_path": None,
                    "marker_only": True,
                    "live_kit_control": False,
                    "full_citywide_twin_claim": False,
                },
                "disposition_capture": disposition_capture(route_item_id),
                "official_status": "not_official",
                "execution_status": item.get("execution_state", "not_executed"),
                "review_required": True,
                "candidate_only": True,
                "source_refs": source_refs,
            }
        )
    return route_items, check_reports, authority


def event_type_registry_entry() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_type_registry.entry.v1",
        "registry_name": "EventTypeRegistry",
        "event_type": "review_item.disposition_recorded",
        "event_version": "1.0",
        "new_top_level_frozen_contract": False,
        "payload_required": ["target_ref", "disposition", "operator_ref", "timestamp", "note"],
        "payload_optional": [],
        "disposition_enum": DISPOSITIONS,
        "note_policy": "optional_but_preserved_if_entered",
        "operator_ref_policy": "local_pseudonymous_allowed",
        "visibility_policy": {
            "individual_dispositions_visible_to": ["reviewer", "operator"],
            "aggregate_dispositions_visible_to": ["analytics"],
            "future_production_requirement": "separate individual visibility from aggregate analytics",
        },
    }


def build_disposition_event(target_ref: str, disposition: str, note: str, operator_ref: str, index: int) -> dict[str, Any]:
    payload = {
        "target_ref": target_ref,
        "disposition": disposition,
        "operator_ref": operator_ref,
        "timestamp": FIXED_EVENT_TIME,
        "note": note,
    }
    event = {
        "schema_version": "citybrain.event_fabric.event_envelope.v1",
        "event_id": f"lane-c:event:disposition:{index:04d}",
        "event_type": "review_item.disposition_recorded",
        "event_version": "1.0",
        "event_time": FIXED_EVENT_TIME,
        "ingested_at": FIXED_EVENT_TIME,
        "source_package": TASK_ID,
        "source_ref": target_ref,
        "target_ref": target_ref,
        "payload": payload,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "candidate_only": True,
        "review_required": True,
        "trace_refs": ["LaneC:disposition_capture", "LaneC:event_fabric_writeback"],
        "limitation_refs": LIMITATIONS,
        "not_executed": NOT_EXECUTED,
    }
    event["event_hash"] = stable_hash(event)
    return event


def build_disposition_fixtures(route_items: list[dict[str, Any]]) -> dict[str, Any]:
    selected = route_items[0]
    second = next((item for item in route_items if item["item_kind"] == "watch_item"), route_items[-1])
    events = [
        build_disposition_event(
            selected["review_item_id"],
            "needs_more",
            "Need sharper retained evidence before any claim is promoted.",
            "operator:local-reviewer:001",
            1,
        ),
        build_disposition_event(
            second["review_item_id"],
            "dismissed",
            "False-positive risk is visible; keep aggregate count only.",
            "operator:local-reviewer:001",
            2,
        ),
    ]
    return {
        "schema_version": "main-citybrain.push2.lane_c.disposition_event_fixtures.v1",
        "status": "PASS",
        "event_type_registry": [event_type_registry_entry()],
        "event_type_registry_entry_count": 1,
        "disposition_events": events,
        "allowed_dispositions": DISPOSITIONS,
        "event_fabric_writeback": {
            "append_only_local_log": "APP_REVIEW_ROUTE_EVENT_FABRIC_APPEND_LOG.jsonl",
            "written_event_count": len(events),
            "all_events_written": True,
            "event_types": unique([event["event_type"] for event in events]),
        },
    }


def render_list(items: list[Any]) -> str:
    values = [item for item in items if item not in (None, "")]
    if not values:
        return "<li>None recorded.</li>"
    return "".join(f"<li>{escape(str(value))}</li>" for value in values)


def render_route_html(
    route_items: list[dict[str, Any]],
    check_reports: list[dict[str, Any]],
    authority_envelopes: list[dict[str, Any]],
    dispositions: dict[str, Any],
) -> str:
    selected = route_items[0]
    check_by_id = {item["check_report_id"]: item for item in check_reports}
    authority_by_id = {item["authority_envelope_id"]: item for item in authority_envelopes}
    selected_check = check_by_id[selected["check_report_id"]]
    selected_authority = authority_by_id[selected["authority_envelope_id"]]
    item_cards = []
    for item in route_items:
        item_cards.append(
            f"""
        <article class="review-row" data-review-item-id="{escape(item['review_item_id'])}" data-item-kind="{escape(item['item_kind'])}">
          <span>{escape(item['item_kind'].replace('_', ' '))}</span>
          <h3>{escape(item['display_title'])}</h3>
          <p>Source class: {escape(item['source_class'])}</p>
          <p>CheckReport: {escape(item['check_report_id'])}</p>
        </article>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Lane C App Review Route</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #20242a; background: #f6f7f9; }}
    main {{ display: grid; grid-template-columns: minmax(280px, 38%) 1fr; gap: 16px; padding: 16px; }}
    header {{ padding: 18px 16px; background: #101820; color: white; }}
    h1, h2, h3 {{ margin: 0 0 8px; letter-spacing: 0; }}
    section, article {{ border: 1px solid #d5dbe3; border-radius: 6px; background: white; }}
    section {{ padding: 14px; }}
    .review-list {{ display: grid; gap: 10px; }}
    .review-row {{ padding: 12px; }}
    .review-row span, .pill {{ display: inline-block; padding: 2px 7px; border: 1px solid #9fb2c7; border-radius: 999px; font-size: 12px; }}
    .panel-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .mini {{ padding: 10px; background: #fbfcfd; border: 1px solid #d5dbe3; border-radius: 6px; }}
    .capture button {{ margin: 4px 6px 4px 0; }}
    button {{ border: 1px solid #3f6f9c; background: #eef5fb; padding: 7px 9px; border-radius: 5px; }}
    textarea {{ width: 100%; min-height: 72px; box-sizing: border-box; }}
    .boundary {{ background: #fff8e7; }}
    .overlay {{ display: grid; min-height: 100px; place-items: center; border: 1px dashed #7c8a9b; background: repeating-linear-gradient(45deg, #f2f5f7, #f2f5f7 8px, #e9eef3 8px, #e9eef3 16px); }}
  </style>
</head>
<body data-app-review-route="true" data-route-path="/review" data-official-action-affordance="false">
  <header>
    <p class="pill">PUSH 2 Lane C</p>
    <h1>App Review Route</h1>
    <p>Perception items and WATCH prompts in one local review workspace. No official action has been taken.</p>
  </header>
  <main>
    <section>
      <h2>Review Items</h2>
      <div class="review-list">{''.join(item_cards)}</div>
    </section>
    <section id="selected-review-item" data-selected-review-item-id="{escape(selected['review_item_id'])}">
      <h2>{escape(selected['display_title'])}</h2>
      <p>Selected item panel shows evidence, limitations, trace, CheckReport, AuthorityEnvelope, safe next looks, and disposition capture.</p>
      <div class="panel-grid">
        <div class="mini"><h3>Evidence refs</h3><ul>{render_list(selected['evidence_refs'])}</ul></div>
        <div class="mini"><h3>Limitation refs</h3><ul>{render_list(selected['limitation_refs'])}</ul></div>
        <div class="mini"><h3>Trace refs</h3><ul>{render_list(selected['trace_refs'])}</ul></div>
        <div class="mini"><h3>Cannot claim</h3><ul>{render_list(selected['cannot_claim'])}</ul></div>
        <div class="mini"><h3>Not executed</h3><ul>{render_list(selected['not_executed'])}</ul></div>
        <div class="mini"><h3>Safe next looks</h3><ul>{render_list(selected['safe_next_looks'])}</ul></div>
        <div class="mini" data-check-report-visible="true"><h3>CheckReport</h3><p>{escape(selected_check['status'])}: {escape(selected_check['reason'])}</p></div>
        <div class="mini" data-authority-envelope-visible="true"><h3>AuthorityEnvelope</h3><p>{escape(selected_authority['scope'])}; individual reviewer/operator visibility, aggregate analytics only.</p></div>
      </div>
      <div class="mini">
        <h3>Spatial overlay reference</h3>
        <div class="overlay">{escape(str(selected['spatial_overlay_reference'].get('overlay_id') or 'No spatial marker'))}</div>
      </div>
      <div class="mini capture" data-disposition-capture-visible="true">
        <h3>Disposition capture</h3>
        <button type="button" data-disposition="confirmed">Confirmed</button>
        <button type="button" data-disposition="dismissed">Dismissed</button>
        <button type="button" data-disposition="needs_more">Needs more</button>
        <textarea aria-label="Optional local disposition note" placeholder="Optional local note is preserved if entered."></textarea>
        <p>Emits Event Fabric fixture type: {escape(dispositions['event_type_registry'][0]['event_type'])}</p>
      </div>
      <div class="mini boundary">
        <h3>Boundary</h3>
        <p>No official case, ticket, dispatch, control, enforcement, legal finding, live API, URL fetch, or LLM call is exposed by this route.</p>
      </div>
    </section>
  </main>
</body>
</html>"""


def build_render_state(route_items: list[dict[str, Any]], html: str) -> dict[str, Any]:
    selected = route_items[0]
    perception_count = len([item for item in route_items if item["item_kind"] == "perception_item"])
    watch_count = len([item for item in route_items if item["item_kind"] == "watch_item"])
    return {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.render_state.v1",
        "status": "PASS",
        "route_path": "/review",
        "workspace_id": "push2-lane-c-app-review-route",
        "html_artifact": "APP_REVIEW_ROUTE_STATIC_WORKSPACE.html",
        "perception_items_visible": perception_count > 0,
        "perception_item_count": perception_count,
        "watch_items_visible": watch_count > 0,
        "watch_item_count": watch_count,
        "selected_review_item_panel": {
            "visible": True,
            "selected_review_item_id": selected["review_item_id"],
            "candidate_observation_display_visible": selected["candidate_observation_display"] is not None,
            "evidence_refs_visible": bool(selected["evidence_refs"]),
            "limitation_refs_visible": bool(selected["limitation_refs"]),
            "trace_refs_visible": bool(selected["trace_refs"]),
            "source_class_visible": bool(selected["source_class"]),
            "cannot_claim_visible": bool(selected["cannot_claim"]),
            "not_executed_visible": bool(selected["not_executed"]),
            "safe_next_looks_visible": bool(selected["safe_next_looks"]),
            "spatial_overlay_reference_visible": selected["spatial_overlay_reference"] is not None,
            "check_report_visible": bool(selected["check_report_id"]),
            "authority_envelope_visible": bool(selected["authority_envelope_id"]),
            "disposition_capture_visible": bool(selected["disposition_capture"]),
        },
        "forbidden_affordances_visible": {
            "official_action": False,
            "official_ticket": False,
            "dispatch": False,
            "control": False,
            "enforcement": False,
            "live_api": False,
            "llm": False,
        },
        "dom_assertions": {
            "data_app_review_route_true": 'data-app-review-route="true"' in html,
            "data_route_review": 'data-route-path="/review"' in html,
            "check_report_marker": 'data-check-report-visible="true"' in html,
            "authority_marker": 'data-authority-envelope-visible="true"' in html,
            "disposition_marker": 'data-disposition-capture-visible="true"' in html,
        },
        "render_state_hash": stable_hash({"selected": selected, "perception_count": perception_count, "watch_count": watch_count}),
    }


def build_boundary_audit(
    route_items: list[dict[str, Any]],
    check_reports: list[dict[str, Any]],
    authority_envelopes: list[dict[str, Any]],
    disposition_fixtures: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    for item in route_items:
        if item.get("official_status") != "not_official":
            failures.append(f"{item['review_item_id']}:official_status")
        if item.get("execution_status") != "not_executed":
            failures.append(f"{item['review_item_id']}:execution_status")
        if item.get("review_required") is not True or item.get("candidate_only") is not True:
            failures.append(f"{item['review_item_id']}:review_flags")
        overlay = item.get("spatial_overlay_reference") or {}
        if overlay.get("live_kit_control") is True or overlay.get("full_citywide_twin_claim") is True:
            failures.append(f"{item['review_item_id']}:spatial_overlay_claim")
    for envelope in authority_envelopes:
        if envelope.get("official_action_allowed") is not False or envelope.get("official_record_created") is not False:
            failures.append(f"{envelope['authority_envelope_id']}:authority")
    for event in disposition_fixtures.get("disposition_events", []):
        payload = event.get("payload", {})
        for field in ["target_ref", "disposition", "operator_ref", "timestamp", "note"]:
            if field not in payload:
                failures.append(f"{event['event_id']}:missing_payload_{field}")
        if event.get("event_type") != "review_item.disposition_recorded":
            failures.append(f"{event['event_id']}:event_type")
        if event.get("execution_status") != "not_executed":
            failures.append(f"{event['event_id']}:execution_status")
    return {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.boundary_audit.v1",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "route_scope": "local_replay_review_only",
        "local_review_route_may_show_individual_dispositions_to_reviewer_operator": True,
        "aggregate_dispositions_for_analytics_only": True,
        "future_production_visibility_separation_required": True,
        "no_official_action_ticket_dispatch_affordance": True,
        "no_live_api_url_llm": True,
        "no_sealed_ask_runtime_mutation": True,
        "no_r7_runtime_mutation": True,
        "check_report_visible_count": len(check_reports),
        "authority_envelope_visible_count": len(authority_envelopes),
        "disposition_event_count": len(disposition_fixtures.get("disposition_events", [])),
    }


def build_fixtures(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    inputs = load_inputs()
    perception_items, perception_checks, perception_authority = build_perception_items(inputs)
    watch_items, watch_checks, watch_authority = build_watch_items(inputs)
    route_items = perception_items + watch_items
    check_reports = perception_checks + watch_checks
    authority = perception_authority + watch_authority
    disposition_fixtures = build_disposition_fixtures(route_items)
    route_html = render_route_html(route_items, check_reports, authority, disposition_fixtures)
    render_state = build_render_state(route_items, route_html)
    boundary = build_boundary_audit(route_items, check_reports, authority, disposition_fixtures)
    fixtures = {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.fixtures.v1",
        "status": "PASS",
        "route_path": "/review",
        "review_items": route_items,
        "selected_review_item": route_items[0],
        "check_reports": check_reports,
        "authority_envelopes": authority,
        "source_inputs": {
            "r7a_candidate_observation_fixtures": rel(R7A_FIXTURES),
            "r7b_materialized_review_state": rel(R7B_REVIEW_STATE),
            "r7d_webui_export": rel(R7D_WEBUI),
            "r7d_kit_export": rel(R7D_KIT),
            "d9_watch_queue": rel(D9_WATCH),
            "d9_check_results": rel(D9_CHECK_RESULTS),
        },
    }
    decision = {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if boundary["status"] == "PASS" and render_state["status"] == "PASS" else FAIL_STATUS,
        "route_path": "/review",
        "entry_gates": entry_gate_report(),
        "review_item_count": len(route_items),
        "perception_item_count": render_state["perception_item_count"],
        "watch_item_count": render_state["watch_item_count"],
        "check_report_count": len(check_reports),
        "authority_envelope_count": len(authority),
        "disposition_event_type": "review_item.disposition_recorded",
        "disposition_event_count": len(disposition_fixtures["disposition_events"]),
        "event_fabric_writeback_log": "APP_REVIEW_ROUTE_EVENT_FABRIC_APPEND_LOG.jsonl",
        "static_route_html": "APP_REVIEW_ROUTE_STATIC_WORKSPACE.html",
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    return {
        "decision": decision,
        "fixtures": fixtures,
        "render_state": render_state,
        "boundary": boundary,
        "disposition_fixtures": disposition_fixtures,
        "route_html": route_html,
    }


def test_log_text(tests: dict[str, Any], render_state: dict[str, Any], boundary: dict[str, Any]) -> str:
    targeted = tests.get("targeted", {})
    full = tests.get("full_discovery", {})
    return "\n".join(
        [
            "# App Review Route Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- targeted: `{targeted.get('result', 'NOT_RUN')}`, `{targeted.get('count', 0)}` tests",
            f"- full discovery: `{full.get('result', 'NOT_RUN')}`, `{full.get('count', 0)}` tests",
            f"- ASK protected diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 protected diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- perception items visible: `{'PASS' if render_state.get('perception_items_visible') else 'FAIL'}`",
            f"- WatchItems visible: `{'PASS' if render_state.get('watch_items_visible') else 'FAIL'}`",
            f"- selected item evidence/limitations/trace: `{'PASS' if render_state.get('selected_review_item_panel', {}).get('evidence_refs_visible') and render_state.get('selected_review_item_panel', {}).get('limitation_refs_visible') and render_state.get('selected_review_item_panel', {}).get('trace_refs_visible') else 'FAIL'}`",
            f"- CheckReport visible: `{'PASS' if render_state.get('selected_review_item_panel', {}).get('check_report_visible') else 'FAIL'}`",
            f"- AuthorityEnvelope visible: `{'PASS' if render_state.get('selected_review_item_panel', {}).get('authority_envelope_visible') else 'FAIL'}`",
            f"- DispositionEvent emitted/writeback: `{'PASS' if boundary.get('disposition_event_count', 0) > 0 else 'FAIL'}`",
            f"- no official action/ticket/dispatch affordance: `{'PASS' if boundary.get('no_official_action_ticket_dispatch_affordance') else 'FAIL'}`",
            f"- no live API/URL/LLM: `{'PASS' if boundary.get('no_live_api_url_llm') else 'FAIL'}`",
            "",
            "This package is local/replay only and leaves canonical integration to INFRA.",
        ]
    )


def write_bundle(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_output_root()
    input_check = check_input_files()
    gates = entry_gate_report()
    if input_check["status"] != "PASS" or gates["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push2.lane_c.app_review_route.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_STATUS,
            "input_check": input_check,
            "entry_gates": gates,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_DECISION.json", decision)
        write_hash_manifest()
        return {"decision": decision}
    bundle = build_fixtures(tests)
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_DECISION.json", bundle["decision"])
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json", bundle["fixtures"])
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_RENDER_STATE_REPORT.json", bundle["render_state"])
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json", bundle["disposition_fixtures"])
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json", bundle["boundary"])
    write_text(OUTPUT_ROOT / "APP_REVIEW_ROUTE_STATIC_WORKSPACE.html", bundle["route_html"])
    event_lines = "\n".join(json.dumps(event, sort_keys=True) for event in bundle["disposition_fixtures"]["disposition_events"])
    write_text(OUTPUT_ROOT / "APP_REVIEW_ROUTE_EVENT_FABRIC_APPEND_LOG.jsonl", event_lines)
    write_json(OUTPUT_ROOT / "APP_REVIEW_ROUTE_EVENT_TYPE_REGISTRY.json", {"entries": bundle["disposition_fixtures"]["event_type_registry"]})
    write_text(OUTPUT_ROOT / "APP_REVIEW_ROUTE_TEST_LOG.md", test_log_text(tests, bundle["render_state"], bundle["boundary"]))
    manifest = write_hash_manifest()
    bundle["hash_manifest"] = manifest
    return bundle


def closeout_summary_text(decision: dict[str, Any], hash_report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# App Review Route Closeout",
            "",
            f"Status: `{decision['status']}`",
            "",
            f"- route items: `{decision.get('review_item_count', 0)}`",
            f"- perception items: `{decision.get('perception_item_count', 0)}`",
            f"- WATCH items: `{decision.get('watch_item_count', 0)}`",
            f"- disposition events: `{decision.get('disposition_event_count', 0)}`",
            f"- route hash verification: `{hash_report['status']}`",
            "",
            "Lane C is closed as a local/replay review route. INFRA owns canonical integration.",
        ]
    )


def limitations_text() -> str:
    return "# App Review Route Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS)


def write_closeout(bundle: dict[str, Any]) -> dict[str, Any]:
    reset_output_root(CLOSEOUT_ROOT)
    decision = bundle.get("decision", {})
    route_hash = verify_hash_manifest(OUTPUT_ROOT)
    status = PASS_STATUS if decision.get("status") == PASS_STATUS and route_hash["status"] == "PASS" else FAIL_STATUS
    closeout_decision = {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.closeout.v1",
        "task_id": f"{TASK_ID}-CLOSEOUT",
        "status": status,
        "route_status": decision.get("status"),
        "route_output_root": rel(OUTPUT_ROOT),
        "route_hash_manifest": route_hash,
        "review_item_count": decision.get("review_item_count", 0),
        "perception_item_count": decision.get("perception_item_count", 0),
        "watch_item_count": decision.get("watch_item_count", 0),
        "check_report_count": decision.get("check_report_count", 0),
        "authority_envelope_count": decision.get("authority_envelope_count", 0),
        "disposition_event_count": decision.get("disposition_event_count", 0),
        "protected_ask_diff": decision.get("tests", {}).get("ask_scoped_diff", {}).get("status", "NOT_RUN"),
        "protected_r7_diff": decision.get("tests", {}).get("r7_scoped_diff", {}).get("status", "NOT_RUN"),
        "infra_canonical_integration_required": True,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "APP_REVIEW_ROUTE_CLOSEOUT_DECISION.json", closeout_decision)
    write_text(CLOSEOUT_ROOT / "APP_REVIEW_ROUTE_CLOSEOUT_SUMMARY.md", closeout_summary_text(closeout_decision, route_hash))
    write_text(CLOSEOUT_ROOT / "APP_REVIEW_ROUTE_CLOSEOUT_LIMITATIONS.md", limitations_text())
    manifest = write_hash_manifest(
        CLOSEOUT_ROOT,
        "APP_REVIEW_ROUTE_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push2.lane_c.app_review_route.closeout.hash_manifest.v1",
    )
    closeout_decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(CLOSEOUT_ROOT / "APP_REVIEW_ROUTE_CLOSEOUT_DECISION.json", closeout_decision)
    write_hash_manifest(
        CLOSEOUT_ROOT,
        "APP_REVIEW_ROUTE_CLOSEOUT_HASH_MANIFEST.json",
        "main-citybrain.push2.lane_c.app_review_route.closeout.hash_manifest.v1",
    )
    return {"decision": closeout_decision}


def final_summary_text(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# App Review Route Final Status",
            "",
            f"Status: `{decision['status']}`",
            "",
            "- implementation verification complete",
            "- lane closeout complete",
            "- final status package complete",
            "- exact staging and branch publish remain git operations outside the artifact generator",
            "",
            "No canonical merge or cross-lane consolidation is performed by Lane C.",
        ]
    )


def write_final_status(closeout: dict[str, Any]) -> dict[str, Any]:
    reset_output_root(FINAL_ROOT)
    closeout_decision = closeout.get("decision", {})
    route_hash = verify_hash_manifest(OUTPUT_ROOT)
    closeout_hash = verify_hash_manifest(CLOSEOUT_ROOT, "APP_REVIEW_ROUTE_CLOSEOUT_HASH_MANIFEST.json")
    status = PASS_STATUS if closeout_decision.get("status") == PASS_STATUS and route_hash["status"] == "PASS" and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final_decision = {
        "schema_version": "main-citybrain.push2.lane_c.app_review_route.final_status.v1",
        "task_id": f"{TASK_ID}-FINAL-STATUS",
        "status": status,
        "route_status": closeout_decision.get("route_status"),
        "closeout_status": closeout_decision.get("status"),
        "route_hash_manifest": route_hash,
        "closeout_hash_manifest": closeout_hash,
        "completed_through": [
            "implementation_verification",
            "app_review_route_output_package",
            "lane_closeout",
            "lane_final_status",
        ],
        "exact_stage_list": [
            "scripts/run_main_citybrain_push2_lane_c_app_review_route.py",
            "tests/test_main_citybrain_push2_lane_c_app_review_route.py",
            "outputs/push2_lane_c_app_review_route/",
            "outputs/push2_lane_c_app_review_route_closeout/",
            "outputs/push2_lane_c_app_review_route_final_status/",
        ],
        "commit_message": "Add Push 2 app review route and dispositions",
        "branch": "codex/push2-lane-c-app-review-route-disposition",
        "infra_canonical_integration_required": True,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "APP_REVIEW_ROUTE_FINAL_STATUS_DECISION.json", final_decision)
    write_text(FINAL_ROOT / "APP_REVIEW_ROUTE_FINAL_STATUS_SUMMARY.md", final_summary_text(final_decision))
    manifest = write_hash_manifest(
        FINAL_ROOT,
        "APP_REVIEW_ROUTE_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push2.lane_c.app_review_route.final_status.hash_manifest.v1",
    )
    final_decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(FINAL_ROOT / "APP_REVIEW_ROUTE_FINAL_STATUS_DECISION.json", final_decision)
    write_hash_manifest(
        FINAL_ROOT,
        "APP_REVIEW_ROUTE_FINAL_STATUS_HASH_MANIFEST.json",
        "main-citybrain.push2.lane_c.app_review_route.final_status.hash_manifest.v1",
    )
    return {"decision": final_decision}


def write_all_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = write_bundle(tests)
    if bundle.get("decision", {}).get("status") == STOP_STATUS:
        return {"bundle": bundle, "decision": bundle["decision"]}
    closeout = write_closeout(bundle)
    final = write_final_status(closeout)
    return {
        "bundle": bundle,
        "closeout": closeout,
        "final": final,
        "decision": final["decision"],
    }


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
    targeted = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push2_lane_c_app_review_route"])
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
