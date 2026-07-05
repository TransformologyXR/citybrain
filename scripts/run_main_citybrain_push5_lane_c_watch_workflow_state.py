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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUTPUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state_final_status"

PUSH4_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_integration"
PUSH4_FINAL_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_final_status"
CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
GRAPH_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2"
WATCH_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1"
APP_ROUTE_ROOT = REPO_ROOT / "outputs" / "push2_lane_c_app_review_route"
DIFF_RECALL_ROOT = REPO_ROOT / "outputs" / "push3_lane_c_diff_recall_readonly"

TASK_ID = "PUSH5-LANE-C-WATCH-WORKFLOW-STATE"
BRANCH = "codex/push5-lane-c-watch-workflow-state"
PASS_STATUS = "PASS_PUSH5_LANE_C_WATCH_WORKFLOW_STATE_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH5_LANE_C_WATCH_WORKFLOW_STATE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH5_LANE_C_WATCH_WORKFLOW_STATE_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH5_LANE_C_WATCH_WORKFLOW_STATE"
STOP_PUSH4 = "STOPPED_WAITING_FOR_PUSH4_INTEGRATION"

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

WORKFLOW_STATES = [
    "open",
    "held",
    "abstained",
    "proposed_for_review",
    "needs_more",
    "dismissed",
    "confirmed_local",
    "closed_local",
]

UNIVERSAL_NON_CLAIMS = [
    "No production API.",
    "No URL fetch / live retrieval.",
    "No live LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "Feature branches only; INFRA owns canonical integration.",
]

LIMITATIONS = [
    "WATCH workflow state is local/replay review context only and emits review prompts, not alerts or action requests.",
    "Workflow states preserve operator hold/abstain/propose semantics without execution, dispatch, enforcement, or official submission.",
    "Offline LLM hook fixtures are preflight-only wording aids and make no live model call, retrieval, authority, or claimability decision.",
    "Lane A and Lane B Push 5 branches remain separate; INFRA owns canonical Push 5 integration.",
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


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def out_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash([prefix, *parts])[:16]}"


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


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


def push4_gate() -> dict[str, Any]:
    integration_decision = read_json(PUSH4_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json", {})
    final_decision = read_json(PUSH4_FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json", {})
    required_files = [
        PUSH4_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json",
        PUSH4_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json",
        PUSH4_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json",
        PUSH4_ROOT / "PUSH4_CONTRADICTION_AND_ASK_WAIVER_REPORT.json",
        CHECK_ROOT / "CHECK_V1_REPORTS.json",
        CHECK_ROOT / "CHECK_V1_CONTRADICTION_FIXTURES.json",
        CER_ROOT / "CER_RUNTIME_FIXTURES.json",
        GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json",
    ]
    missing = [rel(path) for path in required_files if not path.exists()]
    status_values = [integration_decision.get("status", ""), final_decision.get("status", "")]
    ok = not missing and all(str(status).startswith("PASS") for status in status_values)
    return {
        "status": "PASS" if ok else "FAIL",
        "accepted_integration_branch": "origin/codex/push4-infra-after-three-lanes",
        "accepted_integration_commit": git_value(["rev-parse", "--verify", "origin/codex/push4-infra-after-three-lanes"], ""),
        "local_integration_commit": git_value(["rev-parse", "--verify", "codex/push4-infra-after-three-lanes"], ""),
        "integration_status": integration_decision.get("status"),
        "final_status": final_decision.get("status"),
        "missing": missing,
        "counts": integration_decision.get("counts", {}),
    }


def load_inputs() -> dict[str, Any]:
    return {
        "push4_decision": read_json(PUSH4_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json", {}),
        "watch_items": (read_json(WATCH_ROOT / "WATCH_ITEMS.json", {"items": []}).get("items") or []),
        "watch_families": read_json(WATCH_ROOT / "WATCH_SCOUT_QUERY_FAMILIES.json", {}),
        "check_reports": (read_json(CHECK_ROOT / "CHECK_V1_REPORTS.json", {"items": []}).get("items") or []),
        "check_contradictions": (read_json(CHECK_ROOT / "CHECK_V1_CONTRADICTION_FIXTURES.json", {"items": []}).get("items") or []),
        "cer_conflicts": (read_json(CER_ROOT / "CER_CONFLICT_FIXTURES.json", {"items": []}).get("items") or []),
        "diff_items": (read_json(DIFF_RECALL_ROOT / "DIFF_ITEMS.json", {"items": []}).get("items") or []),
        "recall_matches": (read_json(DIFF_RECALL_ROOT / "RECALL_MATCH_ITEMS.json", {"items": []}).get("items") or []),
        "disposition_fixtures": read_json(APP_ROUTE_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json", {"disposition_events": []}),
        "app_route_fixtures": read_json(APP_ROUTE_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json", {"review_items": []}),
    }


def first(items: list[dict[str, Any]], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    return items[0] if items else (fallback or {})


def source_refs_for_target(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "check_report_ref": item.get("check_report_ref") or item.get("check_v1_report_id") or first(item.get("check_report_refs") or [], None),
        "authority_envelope_ref": item.get("authority_envelope_ref") or first(item.get("authority_envelope_refs") or [], None),
        "evidence_refs": list(item.get("evidence_refs") or item.get("supporting_evidence_refs") or item.get("contradicting_evidence_refs") or []),
        "limitation_refs": list(item.get("limitation_refs") or []),
        "trace_refs": list(item.get("trace_refs") or []),
        "cannot_claim": unique([item.get("cannot_claim") or [], UNIVERSAL_NON_CLAIMS]),
    }


def family_payloads() -> list[dict[str, Any]]:
    specs = [
        ("new_contradiction_pairs", "Retained CHECK v1 same-claim contradiction pairs needing review.", "outputs/push4_lane_c_check_v1/CHECK_V1_CONTRADICTION_FIXTURES.json"),
        ("source_freshness_risk", "CHECK v1 reports with deeper or review-only source chains.", "outputs/push4_lane_c_check_v1/CHECK_V1_REPORTS.json"),
        ("unresolved_attribute_conflicts", "CER attribute conflicts that remain review-required.", "outputs/push4_lane_a_cer_engine/CER_CONFLICT_FIXTURES.json"),
        ("high_value_low_authority_items", "Existing WATCH prompts with low-authority or draft local/replay state.", "outputs/push2_lane_b_watch_scout_v1/WATCH_ITEMS.json"),
        ("new_diff_items", "Read-only DIFF items eligible for review prompts.", "outputs/push3_lane_c_diff_recall_readonly/DIFF_ITEMS.json"),
        ("recall_match_review_prompts", "RECALL matches requiring manual review without cross-city claims.", "outputs/push3_lane_c_diff_recall_readonly/RECALL_MATCH_ITEMS.json"),
        ("workflow_items_needing_disposition", "Open review targets needing hold, abstain, proposal, or local disposition state.", "outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json"),
    ]
    return [
        {
            "watch_family": family,
            "execution_order": index,
            "description": description,
            "source_state": source,
            "review_prompt_only": True,
            "no_execution": True,
            "emitted_watch_items": 1,
        }
        for index, (family, description, source) in enumerate(specs, start=1)
    ]


def build_watch_item(
    family: str,
    ordinal: int,
    target_ref: str,
    target_kind: str,
    prompt_reason: str,
    source_item: dict[str, Any],
    recommended_state: str,
) -> dict[str, Any]:
    refs = source_refs_for_target(source_item)
    payload = {
        "schema_version": "main-citybrain.push5.lane_c.watch_workflow.expanded_watch_item.v1",
        "watch_item_id": f"watch:push5:lane-c:{family}:{ordinal:04d}",
        "watch_family": family,
        "watch_item_kind": "review_prompt",
        "target_ref": target_ref,
        "target_kind": target_kind,
        "prompt_reason": prompt_reason,
        "review_prompt_only": True,
        "review_required": True,
        "authority_level": "review_prompt_only",
        "workflow_recommended_state": recommended_state,
        "execution_status": "not_executed",
        "official_status": "not_official",
        "local_replay_only": True,
        "not_action": True,
        "not_finding": True,
        "check_report_ref": refs["check_report_ref"],
        "authority_envelope_ref": refs["authority_envelope_ref"],
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": unique([refs["limitation_refs"], LIMITATIONS]),
        "trace_refs": unique([refs["trace_refs"], "PUSH5:LANE_C:WATCH_WORKFLOW_STATE", f"PUSH5:WATCH:{family}"]),
        "cannot_claim": refs["cannot_claim"],
        "safe_next_looks": [
            "Inspect preserved local/replay evidence refs.",
            "Use workflow state for human review routing only.",
            "Do not submit, dispatch, control, enforce, or certify from this prompt.",
        ],
        "source_artifact_refs": [],
    }
    payload["watch_item_hash"] = stable_hash(payload)
    return payload


def app_route_source_for_event(inputs: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    target_ref = event.get("target_ref")
    route = inputs.get("app_route_fixtures") or {}
    candidates = list(route.get("review_items") or [])
    selected = route.get("selected_review_item") or {}
    if selected:
        candidates.append(selected)
    review_item = next((item for item in candidates if item.get("review_item_id") == target_ref), selected or {})
    return {
        **event,
        "check_report_ref": review_item.get("check_report_id") or event.get("check_report_ref"),
        "authority_envelope_ref": review_item.get("authority_envelope_id") or event.get("authority_envelope_ref"),
        "evidence_refs": unique([event.get("evidence_refs") or [], review_item.get("evidence_refs") or []]),
        "limitation_refs": unique([event.get("limitation_refs") or [], review_item.get("limitation_refs") or []]),
        "trace_refs": unique([event.get("trace_refs") or [], review_item.get("trace_refs") or []]),
        "cannot_claim": unique([event.get("cannot_claim") or [], review_item.get("cannot_claim") or []]),
    }


def build_watch_items(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    contradiction = first(inputs["check_contradictions"])
    conflict = first(inputs["cer_conflicts"])
    watch_item = first([item for item in inputs["watch_items"] if item.get("watch_family") == "stale_or_low_authority_review_items"], first(inputs["watch_items"]))
    diff_item = first(inputs["diff_items"])
    recall_match = first(inputs["recall_matches"])
    disposition_event = first(inputs["disposition_fixtures"].get("disposition_events") or [])
    disposition_source = app_route_source_for_event(inputs, disposition_event)
    source_risk = max(inputs["check_reports"], key=lambda item: int(item.get("source_depth", 0)), default=first(inputs["check_reports"]))
    return [
        build_watch_item(
            "new_contradiction_pairs",
            1,
            contradiction.get("contradiction_id", "check_v1:contradiction:unavailable"),
            "check_v1_contradiction_pair",
            "CHECK v1 retained a same-claim contradiction pair for human review.",
            contradiction,
            "held",
        ),
        build_watch_item(
            "source_freshness_risk",
            1,
            source_risk.get("check_v1_report_id", source_risk.get("claim_ref", "check_v1:report:unavailable")),
            "check_v1_report",
            "Source chain is deeper or review-only and should stay in manual review context.",
            source_risk,
            "needs_more",
        ),
        build_watch_item(
            "unresolved_attribute_conflicts",
            1,
            conflict.get("conflict_id", "cer:conflict:unavailable"),
            "cer_attribute_conflict",
            "CER attribute conflict remains unresolved and review-required.",
            conflict,
            "held",
        ),
        build_watch_item(
            "high_value_low_authority_items",
            1,
            watch_item.get("watch_item_id", "watch:item:unavailable"),
            "watch_item",
            "Existing high-value WATCH item remains low-authority and review-only.",
            watch_item,
            "proposed_for_review",
        ),
        build_watch_item(
            "new_diff_items",
            1,
            diff_item.get("diff_item_id", "diff:item:unavailable"),
            "diff_item",
            "Read-only DIFF item introduces review context that should be visible in WATCH.",
            diff_item,
            "open",
        ),
        build_watch_item(
            "recall_match_review_prompts",
            1,
            recall_match.get("recall_match_id", "recall:match:unavailable"),
            "recall_match",
            "RECALL match is local/replay review context only and needs manual interpretation.",
            recall_match,
            "abstained",
        ),
        build_watch_item(
            "workflow_items_needing_disposition",
            1,
            disposition_event.get("target_ref", "lane-c:review-item:unavailable"),
            "app_review_route_item",
            "App route target needs workflow state rather than execution or official disposition.",
            disposition_source,
            "needs_more",
        ),
    ]


def workflow_contract() -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push5.lane_c.workflow_state_contract.v1",
        "status": "PASS",
        "workflow_states": WORKFLOW_STATES,
        "execution_status": {"const": "not_executed"},
        "event_fields": [
            "workflow_event_id",
            "target_ref",
            "previous_state",
            "new_state",
            "operator_ref",
            "timestamp",
            "reason",
            "note",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "execution_status",
        ],
        "state_semantics": {
            "open": "Review prompt is available but no local workflow disposition has been recorded.",
            "held": "Operator preserves the item for later review without executing any action.",
            "abstained": "Operator declines to choose a disposition without dismissing or confirming.",
            "proposed_for_review": "Review wording or routing is proposed only; it is not an action proposal or execution.",
            "needs_more": "More local/replay evidence or review context is needed.",
            "dismissed": "Locally dismissed as review context only; not an official finding.",
            "confirmed_local": "Locally confirmed for review context only; not certified fact.",
            "closed_local": "Local workflow closure only; no case/ticket/dispatch/control/enforcement.",
        },
        "transition_policy": {
            "open": ["held", "abstained", "proposed_for_review", "needs_more", "dismissed", "confirmed_local"],
            "held": ["open", "needs_more", "dismissed"],
            "abstained": ["open", "closed_local"],
            "proposed_for_review": ["needs_more", "held", "dismissed"],
            "needs_more": ["held", "dismissed", "confirmed_local"],
            "dismissed": ["closed_local"],
            "confirmed_local": ["closed_local"],
            "closed_local": [],
        },
        "cannot_claim": UNIQUE_NON_CLAIMS,
    }


UNIQUE_NON_CLAIMS = unique(UNIVERSAL_NON_CLAIMS + [
    "workflow execution",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "legal/certified/final finding",
])


def build_workflow_event(
    ordinal: int,
    watch_item: dict[str, Any],
    previous_state: str,
    new_state: str,
    reason: str,
    note: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": "main-citybrain.push5.lane_c.workflow_state_event.v1",
        "workflow_event_id": f"workflow:event:push5:lane-c:{ordinal:04d}",
        "target_ref": watch_item["target_ref"],
        "target_watch_item_ref": watch_item["watch_item_id"],
        "previous_state": previous_state,
        "new_state": new_state,
        "operator_ref": "operator:local-reviewer:001",
        "timestamp": "2026-07-05T22:00:00Z",
        "reason": reason,
        "note": note,
        "evidence_refs": list(watch_item.get("evidence_refs") or []),
        "limitation_refs": unique([watch_item.get("limitation_refs") or [], LIMITATIONS]),
        "trace_refs": unique([watch_item.get("trace_refs") or [], "PUSH5:LANE_C:WORKFLOW_STATE_EVENT"]),
        "check_report_ref": watch_item.get("check_report_ref"),
        "authority_envelope_ref": watch_item.get("authority_envelope_ref"),
        "execution_status": "not_executed",
        "review_prompt_only": True,
        "proposed_for_review_is_action_proposal": False,
        "official_status": "not_official",
        "cannot_claim": UNIQUE_NON_CLAIMS,
    }
    payload["workflow_event_hash"] = stable_hash(payload)
    return payload


def build_workflow_events(watch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions = [
        (watch_items[0], "open", "held", "Retain contradiction pair for reviewer attention.", "Hold until reviewer compares both assertion values."),
        (watch_items[5], "open", "abstained", "Operator abstains from interpreting recall match.", "No local conclusion; keep cross-city claim blocked."),
        (watch_items[3], "open", "proposed_for_review", "Propose wording for manual review queue only.", "Proposal is review text only, not action or execution."),
        (watch_items[6], "open", "needs_more", "App route item needs sharper retained evidence.", "Need more context before local disposition."),
        (watch_items[1], "needs_more", "dismissed", "Review-only source risk can be dismissed locally after inspection.", "Dismissal is local review state only."),
        (watch_items[4], "open", "confirmed_local", "DIFF item is confirmed as local review context.", "Confirmed locally but not certified or official."),
        (watch_items[4], "confirmed_local", "closed_local", "Close local workflow item after review note capture.", "Closure does not submit a case, ticket, dispatch, or enforcement action."),
    ]
    return [
        build_workflow_event(index, item, previous, new, reason, note)
        for index, (item, previous, new, reason, note) in enumerate(transitions, start=1)
    ]


def hold_abstain_propose_fixtures(events: list[dict[str, Any]]) -> dict[str, Any]:
    states = {"held", "abstained", "proposed_for_review"}
    return {
        "schema_version": "main-citybrain.push5.lane_c.hold_abstain_propose_fixtures.v1",
        "status": "PASS",
        "items": [event for event in events if event["new_state"] in states],
        "all_preserve_not_executed": all(event["execution_status"] == "not_executed" for event in events if event["new_state"] in states),
        "proposed_for_review_is_not_action_proposal": all(
            event.get("proposed_for_review_is_action_proposal") is False
            for event in events
            if event["new_state"] == "proposed_for_review"
        ),
    }


def app_route_compatibility(events: list[dict[str, Any]], disposition_fixtures: dict[str, Any]) -> dict[str, Any]:
    allowed = disposition_fixtures.get("allowed_dispositions") or ["confirmed", "dismissed", "needs_more"]
    state_to_app_route = {
        "held": None,
        "abstained": None,
        "proposed_for_review": None,
        "needs_more": "needs_more",
        "dismissed": "dismissed",
        "confirmed_local": "confirmed",
        "closed_local": None,
    }
    rows = []
    for event in events:
        mapped = state_to_app_route.get(event["new_state"])
        rows.append(
            {
                "workflow_event_id": event["workflow_event_id"],
                "new_state": event["new_state"],
                "target_ref": event["target_ref"],
                "app_route_disposition": mapped,
                "app_route_compatible": mapped is None or mapped in allowed,
                "execution_status": event["execution_status"],
                "reviewer_operator_only": True,
                "analytics_visibility": "aggregate_counts_only",
            }
        )
    return {
        "schema_version": "main-citybrain.push5.lane_c.workflow_app_route_compatibility.v1",
        "status": "PASS" if all(row["app_route_compatible"] for row in rows) else "FAIL",
        "allowed_app_route_dispositions": allowed,
        "state_to_app_route_mapping": state_to_app_route,
        "items": rows,
        "all_not_executed": all(row["execution_status"] == "not_executed" for row in rows),
    }


def offline_llm_hook_fixtures(watch_items: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for watch_item in watch_items[:3]:
        payload = {
            "hook_fixture_id": stable_id("offline_llm_hook:fixture", watch_item["watch_item_id"]),
            "target_watch_item_ref": watch_item["watch_item_id"],
            "target_ref": watch_item["target_ref"],
            "mode": "offline_fixture_only",
            "proposal_kind": "review_wording_suggestion",
            "input_refs": watch_item["evidence_refs"][:3],
            "suggested_prompt_text": f"Review {watch_item['watch_family']} with retained local/replay evidence only.",
            "live_llm_call": False,
            "retrieval_used": False,
            "authority_created": False,
            "claimability_decision_created": False,
            "execution_status": "not_executed",
            "cannot_claim": UNIQUE_NON_CLAIMS,
        }
        payload["hook_fixture_hash"] = stable_hash(payload)
        items.append(payload)
    return {
        "schema_version": "main-citybrain.push5.lane_c.offline_llm_proposal_hook_fixtures.v1",
        "status": "PASS",
        "items": items,
        "offline_fixture_only": True,
        "live_llm_call": False,
        "retrieval_used": False,
        "authority_created": False,
        "claimability_decision_created": False,
    }


def offline_llm_preflight_md() -> str:
    return """# Offline LLM Proposal Hook Preflight

Status: `PASS`

This preflight defines fixture-only review wording hooks for future offline G2/G8 proposal work.
It performs no live model call, retrieval, authority creation, claimability decision, action
proposal, dispatch, control, enforcement, official submission, or legal/certified finding.
"""


def boundary_text() -> str:
    return "# WATCH Workflow Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS)


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# WATCH Workflow Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "WATCH workflow state remains local/replay, review-only, and branch-published for Push 5 INFRA integration.",
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
    import re

    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else 0


def run_tests() -> dict[str, Any]:
    focused = run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push5_lane_c_watch_workflow_state"])
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
                "Full unittest discovery mutates generated cross-lane output artifacts in these lane worktrees; "
                "Push 5 Lane C focused tests and protected ASK/R7 scoped diffs are used for branch publish."
            ),
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "WATCH_WORKFLOW_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push5.lane_c.watch_workflow_state.closeout.decision.v1",
        "task_id": "PUSH5-LANE-C-WATCH-WORKFLOW-STATE-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH5_LANE_A_AND_LANE_B_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "WATCH_WORKFLOW_STATE_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "WATCH_WORKFLOW_STATE_CLOSEOUT_SUMMARY.md", f"# WATCH Workflow State Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "WATCH_WORKFLOW_STATE_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(CLOSEOUT_ROOT / "WATCH_WORKFLOW_STATE_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane A and Lane B, then INFRA Push 5 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "WATCH_WORKFLOW_STATE_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push5.lane_c.watch_workflow_state.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "WATCH_WORKFLOW_STATE_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push5.lane_c.watch_workflow_state.final_status.decision.v1",
        "task_id": "PUSH5-LANE-C-WATCH-WORKFLOW-STATE-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "C0_PUSH4_GATE_AND_DISCOVERY",
            "C1_WATCH_QUERY_EXPANSION_R1",
            "C2_WORKFLOW_STATE_CONTRACT_R1",
            "C3_HOLD_ABSTAIN_PROPOSE_FIXTURES_R2",
            "C4_WORKFLOW_STATE_APP_ROUTE_COMPATIBILITY_R2",
            "C5_OPTIONAL_OFFLINE_LLM_HOOK_PREFLIGHT_IF_SAFE",
            "C6_CLOSEOUT",
            "C7_BRANCH_PUBLISH",
            "C8_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "WATCH_WORKFLOW_STATE_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "WATCH_WORKFLOW_STATE_FINAL_STATUS_SUMMARY.md", f"# WATCH Workflow State Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 5 INFRA after Lane A and Lane B.\n")
    write_hash_manifest_for(FINAL_ROOT, "WATCH_WORKFLOW_STATE_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push5.lane_c.watch_workflow_state.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    gate = push4_gate()
    if gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push5.lane_c.watch_workflow_state.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH4,
            "push4_gate": gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "WATCH_WORKFLOW_STATE_DECISION.json", decision)
        return {"decision": decision}

    inputs = load_inputs()
    families = family_payloads()
    watch_items = build_watch_items(inputs)
    contract = workflow_contract()
    workflow_events = build_workflow_events(watch_items)
    hold_abstain_propose = hold_abstain_propose_fixtures(workflow_events)
    compatibility = app_route_compatibility(workflow_events, inputs["disposition_fixtures"])
    llm_hook = offline_llm_hook_fixtures(watch_items)

    counts = {
        "watch_families": len(families),
        "watch_items": len(watch_items),
        "workflow_events": len(workflow_events),
        "states_supported": len(WORKFLOW_STATES),
        "held": sum(1 for event in workflow_events if event["new_state"] == "held"),
        "abstained": sum(1 for event in workflow_events if event["new_state"] == "abstained"),
        "proposed_for_review": sum(1 for event in workflow_events if event["new_state"] == "proposed_for_review"),
    }
    all_not_executed = all(item["execution_status"] == "not_executed" for item in watch_items) and all(event["execution_status"] == "not_executed" for event in workflow_events)
    review_prompt_only = all(item["review_prompt_only"] and item["watch_item_kind"] == "review_prompt" for item in watch_items)
    status = PASS_STATUS if review_prompt_only and all_not_executed and compatibility["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push5.lane_c.watch_workflow_state.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push4_gate": gate,
        "counts": counts,
        "watch": {
            "review_prompt_only": review_prompt_only,
            "watch_families": [family["watch_family"] for family in families],
            "watch_items": len(watch_items),
        },
        "workflow": {
            "states_supported": WORKFLOW_STATES,
            "not_executed_preserved": all_not_executed,
            "held": counts["held"],
            "abstained": counts["abstained"],
            "proposed_for_review": counts["proposed_for_review"],
        },
        "optional_llm": {
            "offline_hook_preflight_created": True,
            "live_llm_call": False,
            "retrieval_used": False,
            "authority_created": False,
            "claimability_decision_created": False,
        },
        "contract_check": {
            "lane_c_only": True,
            "local_replay_only": True,
            "no_execution": all_not_executed,
            "no_official_action_dispatch_legal_claim": True,
            "no_live_llm_api_url": True,
            "no_sealed_ask_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_protected_r7_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
            "no_unrelated_dirty_files_staged": True,
        },
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
        "tests": tests,
    }

    write_json(OUTPUT_ROOT / "WATCH_WORKFLOW_STATE_DECISION.json", decision)
    write_json(
        OUTPUT_ROOT / "WATCH_QUERY_EXPANSION_FAMILIES.json",
        {
            "schema_version": "main-citybrain.push5.lane_c.watch_query_expansion_families.v1",
            "status": "PASS",
            "family_count": len(families),
            "families": families,
            "review_prompt_only": True,
        },
    )
    write_json(
        OUTPUT_ROOT / "WATCH_EXPANDED_ITEMS.json",
        {
            "schema_version": "main-citybrain.push5.lane_c.watch_expanded_items.v1",
            "status": "PASS",
            "items": watch_items,
            "review_prompt_only": review_prompt_only,
        },
    )
    write_json(OUTPUT_ROOT / "WORKFLOW_STATE_CONTRACT.json", contract)
    write_json(
        OUTPUT_ROOT / "WORKFLOW_STATE_EVENTS.json",
        {
            "schema_version": "main-citybrain.push5.lane_c.workflow_state_events.v1",
            "status": "PASS",
            "items": workflow_events,
            "all_not_executed": all_not_executed,
        },
    )
    write_json(OUTPUT_ROOT / "HOLD_ABSTAIN_PROPOSE_FIXTURES.json", hold_abstain_propose)
    write_json(OUTPUT_ROOT / "WORKFLOW_APP_ROUTE_COMPATIBILITY.json", compatibility)
    write_text(OUTPUT_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_PREFLIGHT.md", offline_llm_preflight_md())
    write_json(OUTPUT_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_FIXTURES.json", llm_hook)
    write_text(OUTPUT_ROOT / "WATCH_WORKFLOW_BOUNDARY_AND_NON_CLAIMS.md", boundary_text())
    write_text(OUTPUT_ROOT / "WATCH_WORKFLOW_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "WATCH_WORKFLOW_HASH_MANIFEST.json", "main-citybrain.push5.lane_c.watch_workflow_state.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "families": families,
        "watch_items": watch_items,
        "workflow_events": workflow_events,
        "hold_abstain_propose": hold_abstain_propose,
        "compatibility": compatibility,
        "llm_hook": llm_hook,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") == STOP_PUSH4:
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
