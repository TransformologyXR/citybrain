#!/usr/bin/env python3
"""Run R7D local/replay WebUI and Kit event-state smoke packaging."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7d_webui_kit_event_state_smoke"
R7C_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff"
R7C_WEBUI = R7C_ROOT / "R7C_WEBUI_QUERY_CONTEXT_EXPORT.json"
R7C_KIT = R7C_ROOT / "R7C_KIT_QUERY_CONTEXT_EXPORT.json"
R7C_RESULTS = R7C_ROOT / "R7C_EVENT_STATE_QUERY_RESULTS.json"
R7C_FIXTURES = R7C_ROOT / "R7C_ASK_HANDOFF_FIXTURES.json"
R7C_EVIDENCE = R7C_ROOT / "R7C_ASK_HANDOFF_EVIDENCE_PACKETS.json"
R7C_AUDIT = R7C_ROOT / "R7C_BOUNDARY_AUDIT.json"

PACKAGE = "MAIN-CITYBRAIN-R7D-WEBUI-KIT-EVENT-STATE-SMOKE"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_R7D_WEBUI_KIT_EVENT_STATE_SMOKE_WITH_LIMITATIONS"
BOUNDARY = (
    "local/replay WebUI and Kit smoke only; marker/context handoff, no live Kit "
    "control, no official submission, and no ASK runtime invocation"
)
LIMITATIONS = [
    "local/replay smoke only",
    "WebUI and Kit outputs are review-safe fixture exports only",
    "candidate observations remain review inputs, not official facts",
    "sandbox draft cases remain draft_not_submitted",
    "action proposals remain not_executed",
    "Kit USDA layer is marker metadata only, not a full citywide twin or live scene control",
    "no live retrieval, production API, URL fetch, official submission, dispatch, control, enforcement, legal/certified claim, or LLM call",
]
CANNOT_CLAIM = [
    "Cannot claim official violation.",
    "Cannot claim live camera or production monitoring.",
    "Cannot claim official case/ticket submission.",
    "Cannot claim dispatch/control/enforcement action.",
    "Cannot claim legal/certified finding.",
    "Candidate observation requires human review.",
]
NOT_EXECUTED = [
    "live_retrieval",
    "production_api",
    "official_submission",
    "dispatch_control_enforcement",
    "llm_call",
]
REQUIRED_R7C_FILES = [R7C_WEBUI, R7C_KIT, R7C_RESULTS, R7C_FIXTURES, R7C_EVIDENCE, R7C_AUDIT]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: dict[str, Any], omit: set[str] | None = None) -> str:
    omit = omit or set()
    clean = {key: value for key, value in payload.items() if key not in omit}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sorted_unique(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "", [])})


def fallback_state(missing: list[Path]) -> dict[str, Any]:
    event_id = "r7d:fallback:event:review-context"
    candidate_ref = "candidate:r7d:fallback:review-context"
    result = {
        "case_id": "r7d-fallback-query-context",
        "query_family": "fallback_local_replay_context",
        "result_count": 1,
        "candidate_only": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "items": [
            {
                "event_id": event_id,
                "candidate_observation_id": candidate_ref,
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "submission_status": "not_applicable",
                "execution_status": "not_executed",
                "evidence_refs": ["source:r7d:fallback-local-replay"],
                "limitation_refs": LIMITATIONS,
                "trace_refs": ["R7D:fallback_state"],
                "cannot_claim": CANNOT_CLAIM,
            }
        ],
        "cannot_claim": CANNOT_CLAIM,
    }
    return {
        "fallback_used": True,
        "fallback_reason": "R7C outputs unavailable; bounded local/replay fallback fixture used.",
        "missing_r7c_files": [rel(path) for path in missing],
        "webui_context": [{"surface": "webui", "context_id": "webui:r7d-fallback-query-context"}],
        "kit_context": [{"surface": "kit", "context_id": "kit:r7d-fallback-query-context"}],
        "query_results": [result],
        "ask_fixtures": [],
        "evidence_packets": [],
        "r7c_boundary_audit": {"status": "PASS_WITH_FALLBACK"},
    }


def load_r7c_outputs() -> dict[str, Any]:
    missing = [path for path in REQUIRED_R7C_FILES if not path.exists()]
    if missing:
        return fallback_state(missing)
    return {
        "fallback_used": False,
        "fallback_reason": None,
        "missing_r7c_files": [],
        "webui_context": read_json(R7C_WEBUI, {"items": []}).get("items", []),
        "kit_context": read_json(R7C_KIT, {"items": []}).get("items", []),
        "query_results": read_json(R7C_RESULTS, {"items": []}).get("items", []),
        "ask_fixtures": read_json(R7C_FIXTURES, {"items": []}).get("items", []),
        "evidence_packets": read_json(R7C_EVIDENCE, {"items": []}).get("items", []),
        "r7c_boundary_audit": read_json(R7C_AUDIT, {}),
    }


def event_candidate_index(results: list[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for result in results:
        for item in result.get("items", []):
            event_id = item.get("event_id")
            candidate_ref = item.get("candidate_observation_id")
            if event_id and candidate_ref and event_id not in index:
                index[event_id] = candidate_ref
    return index


def review_state_for_family(query_family: str) -> str:
    return {
        "active_review_events": "active_review",
        "unresolved_observations": "unresolved_review_candidate",
        "quarantined_observations": "quarantined_not_promoted",
        "event_trace_by_id": "trace_only_review_context",
        "candidate_observation_context": "candidate_context",
        "not_executed_actions": "action_proposal_not_executed",
        "sandbox_draft_cases": "sandbox_draft_not_submitted",
        "webui_kit_overlay_context": "overlay_context",
    }.get(query_family, "local_replay_review_context")


def aggregate_result_refs(result: dict[str, Any], candidate_index: dict[str, str]) -> dict[str, Any]:
    items = result.get("items", [])
    event_refs = sorted_unique([item.get("event_id") for item in items])
    candidate_refs = sorted_unique(
        [
            item.get("candidate_observation_id") or candidate_index.get(item.get("event_id", ""))
            for item in items
        ]
    )
    evidence_refs = sorted_unique([ref for item in items for ref in item.get("evidence_refs", [])])
    limitation_refs = sorted_unique([ref for item in items for ref in item.get("limitation_refs", [])]) or LIMITATIONS
    trace_refs = sorted_unique([ref for item in items for ref in item.get("trace_refs", [])])
    primary_event = event_refs[0] if event_refs else f"aggregate:{result['case_id']}"
    primary_candidate = candidate_refs[0] if candidate_refs else f"candidate-context:{result['case_id']}"
    return {
        "event_id": primary_event,
        "event_refs": event_refs or [primary_event],
        "candidate_observation_ref": primary_candidate,
        "candidate_observation_refs": candidate_refs or [primary_candidate],
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "review_state": review_state_for_family(result["query_family"]),
        "submission_status": "draft_not_submitted" if result["query_family"] == "sandbox_draft_cases" else "not_applicable",
    }


def display_sections_for_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"section_id": "review_summary", "title": "Review summary", "item_count": result.get("result_count", 0)},
        {"section_id": "evidence", "title": "Evidence refs", "item_count": len(result.get("items", []))},
        {"section_id": "limitations", "title": "Limits", "item_count": len(CANNOT_CLAIM)},
        {"section_id": "trace", "title": "Trace refs", "item_count": len(result.get("items", []))},
    ]


def build_webui_smoke_export(state: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_index = event_candidate_index(state["query_results"])
    items = []
    for result in state["query_results"]:
        refs = aggregate_result_refs(result, candidate_index)
        payload = {
            "smoke_item_id": f"webui-smoke:{result['case_id']}",
            "surface": "webui",
            "query_case_id": result["case_id"],
            "query_result_id": result["case_id"],
            "query_family": result["query_family"],
            "event_id": refs["event_id"],
            "event_refs": refs["event_refs"],
            "candidate_observation_refs": refs["candidate_observation_refs"],
            "candidate_observation_ref": refs["candidate_observation_ref"],
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "submission_status": refs["submission_status"],
            "execution_status": "not_executed",
            "cannot_claim": CANNOT_CLAIM,
            "not_executed": NOT_EXECUTED,
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": refs["trace_refs"],
            "review_state": refs["review_state"],
            "display_sections": display_sections_for_result(result),
            "source_context_ref": f"r7c:{result['case_id']}",
            "source_context_kind": "local_replay_event_state_query",
        }
        payload["packet_hash"] = canonical_hash(payload, {"packet_hash"})
        items.append(payload)
    return items


def prim_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not name or name[0].isdigit():
        name = f"_{name}"
    return name[:128]


def build_kit_smoke_export(state: dict[str, Any]) -> list[dict[str, Any]]:
    candidate_index = event_candidate_index(state["query_results"])
    items = []
    for result in state["query_results"]:
        refs = aggregate_result_refs(result, candidate_index)
        prim = f"/World/CityBrain/R7D/EventStateSmoke/{prim_name(result['case_id'])}"
        payload = {
            "overlay_id": f"kit-smoke:{result['case_id']}",
            "surface": "kit",
            "query_case_id": result["case_id"],
            "query_result_id": result["case_id"],
            "query_family": result["query_family"],
            "event_id": refs["event_id"],
            "event_refs": refs["event_refs"],
            "candidate_observation_ref": refs["candidate_observation_ref"],
            "candidate_observation_refs": refs["candidate_observation_refs"],
            "prim_path": prim,
            "proposed_prim_path": prim,
            "display_label": f"R7D {result['query_family']} review marker",
            "overlay_kind": "local_replay_review_marker",
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "submission_status": refs["submission_status"],
            "execution_status": "not_executed",
            "evidence_refs": refs["evidence_refs"],
            "limitation_refs": refs["limitation_refs"],
            "trace_refs": refs["trace_refs"],
            "review_state": refs["review_state"],
            "cannot_claim": CANNOT_CLAIM,
            "not_executed": NOT_EXECUTED,
            "marker_only": True,
            "full_citywide_twin_claim": False,
            "live_kit_control": False,
            "production_omniverse_integration": False,
        }
        payload["packet_hash"] = canonical_hash(payload, {"packet_hash"})
        items.append(payload)
    return items


def build_parity_report(webui_items: list[dict[str, Any]], kit_items: list[dict[str, Any]]) -> dict[str, Any]:
    kit_by_case = {item["query_case_id"]: item for item in kit_items}
    pairs = []
    failures = []
    parity_fields = [
        "event_id",
        "candidate_observation_ref",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "candidate_only",
        "official_status",
        "review_state",
    ]
    for webui in webui_items:
        kit = kit_by_case.get(webui["query_case_id"])
        if kit is None:
            failures.append({"query_case_id": webui["query_case_id"], "reason": "missing_kit_pair"})
            continue
        mismatches = [field for field in parity_fields if webui.get(field) != kit.get(field)]
        pair = {
            "query_case_id": webui["query_case_id"],
            "webui_smoke_item_id": webui["smoke_item_id"],
            "kit_overlay_id": kit["overlay_id"],
            "event_id": webui["event_id"],
            "candidate_observation_ref": webui["candidate_observation_ref"],
            "parity_fields_checked": parity_fields,
            "mismatches": mismatches,
            "status": "PASS" if not mismatches else "FAIL",
        }
        if mismatches:
            failures.append({"query_case_id": webui["query_case_id"], "mismatches": mismatches})
        pairs.append(pair)
    return {
        "status": "PASS" if not failures and len(pairs) == len(webui_items) == len(kit_items) else "FAIL",
        "pairs_checked": len(pairs),
        "failure_count": len(failures),
        "failures": failures,
        "pairs": pairs,
    }


def walk_dicts(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        found.append(payload)
        for value in payload.values():
            found.extend(walk_dicts(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(walk_dicts(item))
    return found


def boundary_audit(
    webui_items: list[dict[str, Any]],
    kit_items: list[dict[str, Any]],
    parity: dict[str, Any],
    usda_text: str,
) -> dict[str, Any]:
    payload = {"webui_items": webui_items, "kit_items": kit_items, "parity": parity}
    failures = []
    forbidden_non_null_refs = [
        "official_case_id",
        "external_submission_ref",
        "dispatch_ref",
        "control_ref",
        "enforcement_ref",
    ]
    for item in walk_dicts(payload):
        for key in forbidden_non_null_refs:
            if item.get(key) not in (None, "", []):
                failures.append(f"{key}_present")
        if item.get("legal_violation") is True:
            failures.append("legal_violation_true")
        if item.get("certified") is True:
            failures.append("certified_true")
        if item.get("live_camera") is True:
            failures.append("live_camera_true")
        if item.get("production_api") is True:
            failures.append("production_api_true")
        if item.get("url_fetch") is True:
            failures.append("url_fetch_true")
        if item.get("llm_call") is True:
            failures.append("llm_call_true")
        if item.get("execution_status") not in (None, "not_executed"):
            failures.append("execution_status_not_not_executed")
        if item.get("query_family") == "sandbox_draft_cases" and item.get("submission_status") != "draft_not_submitted":
            failures.append("sandbox_draft_not_draft_not_submitted")
        if item.get("full_citywide_twin_claim") is True:
            failures.append("full_citywide_twin_claim_true")
        if item.get("live_kit_control") is True:
            failures.append("live_kit_control_true")
    lowered_usda = usda_text.lower()
    for token in ["official_case_id = \"", "external_submission_ref = \"", "dispatch_ref = \"", "control_ref = \"", "enforcement_ref = \""]:
        if token in lowered_usda:
            failures.append(f"usda_forbidden_token:{token}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "boundary": BOUNDARY,
        "failures": sorted_unique(failures),
        "local_replay_smoke_only": True,
        "webui_export_created": bool(webui_items),
        "kit_export_created": bool(kit_items),
        "webui_kit_one_truth_parity_checked": parity["status"] == "PASS",
        "candidate_only_preserved": all(item.get("candidate_only") is True for item in webui_items + kit_items),
        "review_required_preserved": all(item.get("review_required") is True for item in webui_items + kit_items),
        "case_ticket_remains_draft_sandbox_only": all(
            item.get("submission_status") == "draft_not_submitted"
            for item in webui_items + kit_items
            if item.get("query_family") == "sandbox_draft_cases"
        ),
        "submission_status_draft_not_submitted": all(
            item.get("submission_status") in {"not_applicable", "draft_not_submitted"} for item in webui_items + kit_items
        ),
        "action_proposal_execution_status_not_executed": all(item.get("execution_status") == "not_executed" for item in webui_items + kit_items),
        "no_official_submission_execution": not any(failure.endswith("_present") for failure in failures),
        "no_dispatch_control_enforcement_execution": not any(
            failure.startswith(("dispatch_ref", "control_ref", "enforcement_ref")) for failure in failures
        ),
        "no_legal_certified_claim": "legal_violation_true" not in failures and "certified_true" not in failures,
        "no_live_retrieval_production_api_url_fetch_llm_call": not any(
            failure in failures for failure in ["live_camera_true", "production_api_true", "url_fetch_true", "llm_call_true"]
        ),
        "no_full_citywide_twin_live_kit_control_claim": "full_citywide_twin_claim_true" not in failures and "live_kit_control_true" not in failures,
        "ask_runtime_invoked": False,
    }


def write_usda(kit_items: list[dict[str, Any]]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "CityBrain"',
        "    {",
        '        def Xform "R7D_EventStateSmoke"',
        "        {",
        f'            custom string citybrain_package = "{PACKAGE}"',
        '            custom string handoff_scope = "local_replay_marker_metadata_only"',
        "            custom bool candidate_only = true",
        "            custom bool review_required = true",
        "            custom bool full_citywide_twin_claim = false",
        "            custom bool live_kit_control = false",
    ]
    for item in kit_items:
        name = prim_name(item["query_case_id"])
        lines.extend(
            [
                f'            def Xform "{name}"',
                "            {",
                f'                custom string overlay_id = "{item["overlay_id"]}"',
                f'                custom string event_id = "{item["event_id"]}"',
                f'                custom string candidate_observation_ref = "{item["candidate_observation_ref"]}"',
                f'                custom string review_state = "{item["review_state"]}"',
                '                custom string official_status = "not_official"',
                '                custom string execution_status = "not_executed"',
                f'                custom string proposed_prim_path = "{item["proposed_prim_path"]}"',
                "                custom bool marker_only = true",
                "            }",
            ]
        )
    lines.extend(["        }", "    }", "}"])
    return "\n".join(lines) + "\n"


def write_hash_manifest(root: Path) -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "R7D_HASH_MANIFEST.json"):
        items.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "citybrain-r7d-hash-manifest.v1",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / "R7D_HASH_MANIFEST.json", manifest)
    missing = 0
    mismatch = 0
    for item in items:
        target = root / item["path"]
        if not target.exists():
            missing += 1
        elif sha256_file(target) != item["sha256"]:
            mismatch += 1
    manifest["missing_count"] = missing
    manifest["mismatch_count"] = mismatch
    manifest["status"] = "PASS" if missing == 0 and mismatch == 0 else "FAIL"
    write_json(root / "R7D_HASH_MANIFEST.json", manifest)
    return manifest


def verify_hash_manifest(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    manifest = read_json(root / "R7D_HASH_MANIFEST.json", {})
    missing = 0
    mismatch = 0
    for item in manifest.get("items", []):
        target = root / item["path"]
        if not target.exists():
            missing += 1
        elif sha256_file(target) != item["sha256"]:
            mismatch += 1
    return {
        "status": "PASS" if missing == 0 and mismatch == 0 and manifest.get("status") == "PASS" else "FAIL",
        "item_count": manifest.get("item_count", 0),
        "missing_count": missing,
        "mismatch_count": mismatch,
    }


def write_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    state = load_r7c_outputs()
    webui_items = build_webui_smoke_export(state)
    kit_items = build_kit_smoke_export(state)
    parity = build_parity_report(webui_items, kit_items)
    usda_text = write_usda(kit_items)
    audit = boundary_audit(webui_items, kit_items, parity, usda_text)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "R7D_WEBUI_EVENT_STATE_SMOKE_EXPORT.json", {"items": webui_items})
    write_json(root / "R7D_KIT_EVENT_STATE_SMOKE_EXPORT.json", {"items": kit_items})
    write_json(root / "R7D_WEBUI_EVENT_STATE_SMOKE_FIXTURE.json", {"items": webui_items, "source": rel(R7C_WEBUI)})
    write_json(root / "R7D_KIT_EVENT_STATE_SMOKE_MANIFEST.json", {"items": kit_items, "source": rel(R7C_KIT)})
    write_json(root / "R7D_WEBUI_KIT_PARITY_REPORT.json", parity)
    write_json(root / "R7D_BOUNDARY_AUDIT.json", audit)
    write_text(root / "R7D_KIT_EVENT_STATE_SMOKE.usda", usda_text)
    write_text(root / "R7D_LIMITATIONS.md", "# R7D Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "R7D_TEST_LOG.md",
        "# R7D Test Log\n\nGenerated by runner. Expected focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7d_webui_kit_event_state_smoke`.\n",
    )
    final_status = FINAL_DECISION if audit["status"] == "PASS" and parity["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_R7D_WEBUI_KIT_EVENT_STATE_SMOKE"
    decision = {
        "package": PACKAGE,
        "status": final_status,
        "created_at": utc_now(),
        "source_r7c_root": rel(R7C_ROOT),
        "r7c_outputs_loaded": not state["fallback_used"],
        "fallback_used": state["fallback_used"],
        "fallback_reason": state["fallback_reason"],
        "missing_r7c_files": state["missing_r7c_files"],
        "result_counts": {
            "webui_smoke_items": len(webui_items),
            "kit_smoke_items": len(kit_items),
            "parity_pairs_checked": parity["pairs_checked"],
            "parity_failures": parity["failure_count"],
            "optional_usda_created": True,
        },
        "contract_check": {
            "local_replay_smoke_only": audit["local_replay_smoke_only"],
            "webui_export_created": audit["webui_export_created"],
            "kit_export_created": audit["kit_export_created"],
            "webui_kit_one_truth_parity_checked": audit["webui_kit_one_truth_parity_checked"],
            "candidate_only_preserved": audit["candidate_only_preserved"],
            "review_required_preserved": audit["review_required_preserved"],
            "case_ticket_remains_draft_sandbox_only": audit["case_ticket_remains_draft_sandbox_only"],
            "submission_status_draft_not_submitted": audit["submission_status_draft_not_submitted"],
            "action_proposal_execution_status_not_executed": audit["action_proposal_execution_status_not_executed"],
            "no_official_submission_execution": audit["no_official_submission_execution"],
            "no_dispatch_control_enforcement_execution": audit["no_dispatch_control_enforcement_execution"],
            "no_legal_certified_claim": audit["no_legal_certified_claim"],
            "no_live_retrieval_production_api_url_fetch_llm_call": audit["no_live_retrieval_production_api_url_fetch_llm_call"],
            "no_full_citywide_twin_live_kit_control_claim": audit["no_full_citywide_twin_live_kit_control_claim"],
            "ask_runtime_untouched": not audit["ask_runtime_invoked"],
        },
        "limitations": LIMITATIONS,
        "next_recommended_package": "MAIN-CITYBRAIN-R7E-PERCEPTION-REVIEW-WORKFLOW-CLOSEOUT",
    }
    write_json(root / "R7D_WEBUI_KIT_EVENT_STATE_SMOKE_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "R7D_WEBUI_KIT_EVENT_STATE_SMOKE_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
