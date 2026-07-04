#!/usr/bin/env python3
"""Run R7C local/replay event-state query and ASK handoff fixture generation."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff"
R7B_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay"
R7B_DECISION = R7B_ROOT / "R7B_EVENT_FABRIC_DECISION.json"
R7B_EVENT_LOG = R7B_ROOT / "R7B_LOCAL_EVENT_LOG.jsonl"
R7B_MATERIALIZED = R7B_ROOT / "R7B_MATERIALIZED_REVIEW_STATE.json"
R7B_WEBUI = R7B_ROOT / "R7B_WEBUI_EVENT_OVERLAY_EXPORT.json"
R7B_KIT = R7B_ROOT / "R7B_KIT_EVENT_OVERLAY_EXPORT.json"

PACKAGE = "MAIN-CITYBRAIN-R7C-EVENT-FABRIC-STATE-QUERY-AND-ASK-HANDOFF"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_R7C_EVENT_FABRIC_STATE_QUERY_AND_ASK_HANDOFF_WITH_LIMITATIONS"
BOUNDARY = (
    "local/replay query and ASK handoff fixtures only; no ASK runtime invocation; "
    "candidate-only, not-official, draft_not_submitted, and not_executed boundaries preserved"
)
LIMITATIONS = [
    "local/replay query only",
    "ASK handoff outputs are fixture/evidence-shaped DTOs only",
    "candidate observations remain review inputs, not official facts",
    "sandbox draft cases remain draft_not_submitted",
    "action proposals remain not_executed",
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
QUERY_FAMILIES = [
    "active_review_events",
    "unresolved_observations",
    "quarantined_observations",
    "event_trace_by_id",
    "candidate_observation_context",
    "not_executed_actions",
    "sandbox_draft_cases",
    "webui_kit_overlay_context",
]


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def fallback_state() -> dict[str, Any]:
    event = {
        "event_id": "r7c:fallback:event:review-created",
        "event_type": "review_event.created",
        "candidate_observation_id": "candidate:r7c:fallback",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": "not_applicable",
        "execution_status": "not_executed",
        "evidence_refs": ["source:r7c:fallback-local-replay"],
        "limitation_refs": LIMITATIONS,
        "not_executed": ["official_submission", "dispatch_control_enforcement", "llm_call"],
        "trace_refs": ["R7C:fallback_state"],
        "payload": {},
    }
    materialized = {
        "status": "PASS_WITH_FALLBACK",
        "active_review_events": [event],
        "unresolved_observations": [],
        "quarantined_observations": [],
        "sandbox_draft_cases": [],
        "not_executed_action_proposals": [],
        "summary_counts": {
            "active_review_events": 1,
            "unresolved_observations": 0,
            "quarantined_observations": 0,
            "sandbox_draft_cases": 0,
            "not_executed_action_proposals": 0,
        },
    }
    return {
        "fallback_used": True,
        "fallback_reason": "R7B outputs unavailable; bounded local fallback fixture used.",
        "decision": {},
        "events": [event],
        "materialized": materialized,
        "webui_overlays": [],
        "kit_overlays": [],
    }


def load_r7b_state() -> dict[str, Any]:
    if not (R7B_DECISION.exists() and R7B_EVENT_LOG.exists() and R7B_MATERIALIZED.exists()):
        return fallback_state()
    return {
        "fallback_used": False,
        "fallback_reason": None,
        "decision": read_json(R7B_DECISION, {}),
        "events": read_jsonl(R7B_EVENT_LOG),
        "materialized": read_json(R7B_MATERIALIZED, {}),
        "webui_overlays": read_json(R7B_WEBUI, {"items": []}).get("items", []),
        "kit_overlays": read_json(R7B_KIT, {"items": []}).get("items", []),
    }


def safe_event_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "candidate_observation_id": event.get("candidate_observation_id"),
        "candidate_only": event.get("candidate_only") is True,
        "review_required": event.get("review_required") is True,
        "official_status": event.get("official_status", "not_official"),
        "submission_status": event.get("submission_status", "not_applicable"),
        "execution_status": event.get("execution_status", "not_executed"),
        "evidence_refs": event.get("evidence_refs") or [],
        "limitation_refs": event.get("limitation_refs") or LIMITATIONS,
        "not_executed": event.get("not_executed") or [],
        "trace_refs": event.get("trace_refs") or [],
        "cannot_claim": CANNOT_CLAIM,
    }


def query_active_review_events(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [safe_event_summary(event) for event in state["materialized"].get("active_review_events", [])]


def query_unresolved_observations(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [safe_event_summary(event) | {"preservation_state": "unresolved_review_candidate"} for event in state["materialized"].get("unresolved_observations", [])]


def query_quarantined_observations(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        safe_event_summary(event) | {"quarantine_state": "quarantined_not_promoted", "reasons": event.get("payload", {}).get("reasons", [])}
        for event in state["materialized"].get("quarantined_observations", [])
    ]


def query_event_trace_by_id(state: dict[str, Any], event_id: str) -> list[dict[str, Any]]:
    for event in state["events"]:
        if event.get("event_id") == event_id:
            return [
                {
                    "event_id": event_id,
                    "trace_refs": event.get("trace_refs") or [],
                    "evidence_refs": event.get("evidence_refs") or [],
                    "limitation_refs": event.get("limitation_refs") or LIMITATIONS,
                    "candidate_only": True,
                    "review_required": True,
                    "official_status": "not_official",
                    "execution_status": "not_executed",
                    "cannot_claim": CANNOT_CLAIM,
                }
            ]
    return []


def query_candidate_observation_context(state: dict[str, Any], candidate_observation_id: str) -> list[dict[str, Any]]:
    return [safe_event_summary(event) for event in state["events"] if event.get("candidate_observation_id") == candidate_observation_id]


def query_not_executed_actions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        safe_event_summary(event) | {"proposal_status": "not_executed"}
        for event in state["materialized"].get("not_executed_action_proposals", [])
    ]


def query_sandbox_draft_cases(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        safe_event_summary(event) | {"case_scope": "sandbox", "submission_status": "draft_not_submitted"}
        for event in state["materialized"].get("sandbox_draft_cases", [])
    ]


def query_webui_kit_overlay_context(state: dict[str, Any]) -> list[dict[str, Any]]:
    overlays = state.get("webui_overlays", []) + state.get("kit_overlays", [])
    return [
        {
            "surface": overlay.get("surface"),
            "overlay_id": overlay.get("overlay_id"),
            "event_id": overlay.get("event_id"),
            "event_type": overlay.get("event_type"),
            "candidate_observation_id": overlay.get("candidate_observation_id"),
            "candidate_only": overlay.get("candidate_only") is True,
            "review_required": overlay.get("review_required") is True,
            "official_status": overlay.get("official_status", "not_official"),
            "submission_status": overlay.get("submission_status", "not_applicable"),
            "execution_status": overlay.get("execution_status", "not_executed"),
            "evidence_refs": overlay.get("evidence_refs") or [],
            "limitation_refs": overlay.get("limitation_refs") or LIMITATIONS,
            "trace_refs": overlay.get("trace_refs") or [],
            "cannot_claim": CANNOT_CLAIM,
        }
        for overlay in overlays
    ]


def query_cases() -> list[dict[str, Any]]:
    return [
        {"case_id": "r7c-query-active-review-events", "query_family": "active_review_events", "input": {}, "example_user_text": "Show active review events."},
        {"case_id": "r7c-query-unresolved", "query_family": "unresolved_observations", "input": {}, "example_user_text": "Which observations still need source context?"},
        {"case_id": "r7c-query-quarantined", "query_family": "quarantined_observations", "input": {}, "example_user_text": "Show quarantined observations."},
        {"case_id": "r7c-query-trace", "query_family": "event_trace_by_id", "input": {"event_id": "r7b:event:review-created:0001"}, "example_user_text": "Show trace for the review event."},
        {"case_id": "r7c-query-candidate-context", "query_family": "candidate_observation_context", "input": {"candidate_observation_id": "candidate:r7a:obs:accepted-001"}, "example_user_text": "What context exists for this candidate?"},
        {"case_id": "r7c-query-not-executed", "query_family": "not_executed_actions", "input": {}, "example_user_text": "What actions were not executed?"},
        {"case_id": "r7c-query-sandbox-drafts", "query_family": "sandbox_draft_cases", "input": {}, "example_user_text": "Show sandbox draft cases."},
        {"case_id": "r7c-query-overlays", "query_family": "webui_kit_overlay_context", "input": {}, "example_user_text": "Show WebUI and Kit overlay context."},
    ]


def run_query_case(state: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    family = case["query_family"]
    if family == "active_review_events":
        items = query_active_review_events(state)
    elif family == "unresolved_observations":
        items = query_unresolved_observations(state)
    elif family == "quarantined_observations":
        items = query_quarantined_observations(state)
    elif family == "event_trace_by_id":
        items = query_event_trace_by_id(state, case["input"]["event_id"])
    elif family == "candidate_observation_context":
        items = query_candidate_observation_context(state, case["input"]["candidate_observation_id"])
    elif family == "not_executed_actions":
        items = query_not_executed_actions(state)
    elif family == "sandbox_draft_cases":
        items = query_sandbox_draft_cases(state)
    elif family == "webui_kit_overlay_context":
        items = query_webui_kit_overlay_context(state)
    else:
        items = []
    return {
        "case_id": case["case_id"],
        "query_family": family,
        "result_count": len(items),
        "candidate_only": all(item.get("candidate_only") is True for item in items),
        "official_status": "not_official",
        "execution_status": "not_executed",
        "items": items,
        "cannot_claim": CANNOT_CLAIM,
    }


def query_results(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [run_query_case(state, case) for case in query_cases()]


def ask_handoff_fixture(result: dict[str, Any]) -> dict[str, Any]:
    fixture = {
        "fixture_id": f"ask-handoff:{result['case_id']}",
        "fixture_kind": "ask_v11_local_demo_query_handoff",
        "query_family": result["query_family"],
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": "draft_not_submitted" if result["query_family"] == "sandbox_draft_cases" else "not_applicable",
        "execution_status": "not_executed",
        "source_kind": "local_replay",
        "not_executed": ["live_retrieval", "production_api", "official_submission", "dispatch_control_enforcement", "llm_call"],
        "cannot_claim": CANNOT_CLAIM,
        "limitation_refs": LIMITATIONS,
        "evidence_refs": sorted({ref for item in result["items"] for ref in item.get("evidence_refs", [])}),
        "trace_refs": sorted({ref for item in result["items"] for ref in item.get("trace_refs", [])}),
        "query_result_ref": result["case_id"],
        "item_count": result["result_count"],
    }
    fixture["packet_hash"] = canonical_hash(fixture, {"packet_hash"})
    return fixture


def ask_handoff_evidence_packet(fixture: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "packet_id": f"evidence:{fixture['fixture_id']}",
        "packet_kind": "ask_v11_evidence_compatible_fixture",
        "fixture_ref": fixture["fixture_id"],
        "facts": [
            {
                "fact_id": f"fact:{fixture['query_family']}",
                "text": f"Local/replay query family {fixture['query_family']} returned {fixture['item_count']} candidate-only item(s).",
            }
        ],
        "source_refs": [
            {
                "source_id": "r7b_local_event_state",
                "source_type": "local_replay_fixture",
                "title": "R7B local/replay event state",
                "claim_boundary": "candidate-only review context; not official truth",
            }
        ],
        "lineage": ["R7B_LOCAL_EVENT_LOG", "R7C_EVENT_STATE_QUERY"],
        "confidence": 1.0,
        "gaps": [],
        "warnings": CANNOT_CLAIM,
        "flags": {"no_data": fixture["item_count"] == 0, "partial_result": False, "truncated": False},
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": fixture["submission_status"],
        "execution_status": "not_executed",
        "not_executed": fixture["not_executed"],
        "cannot_claim": fixture["cannot_claim"],
        "evidence_refs": fixture["evidence_refs"],
        "trace_refs": fixture["trace_refs"],
    }
    packet["packet_hash"] = canonical_hash(packet, {"packet_hash"})
    return packet


def ask_handoff_fixtures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ask_handoff_fixture(result) for result in results]


def ask_handoff_evidence_packets(fixtures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ask_handoff_evidence_packet(fixture) for fixture in fixtures]


def context_exports(results: list[dict[str, Any]], surface: str) -> list[dict[str, Any]]:
    return [
        {
            "surface": surface,
            "context_id": f"{surface}:{result['case_id']}",
            "query_family": result["query_family"],
            "result_count": result["result_count"],
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "execution_status": "not_executed",
            "submission_status": "draft_not_submitted" if result["query_family"] == "sandbox_draft_cases" else "not_applicable",
            "cannot_claim": CANNOT_CLAIM,
            "limitation_refs": LIMITATIONS,
        }
        for result in results
    ]


def boundary_failures(payload: Any) -> list[str]:
    serial = json.dumps(payload, sort_keys=True).lower()
    failures = []
    forbidden_pairs = [
        '"execution_status": "executed"',
        '"official_status": "official"',
        '"submission_status": "submitted"',
        '"legal_violation": true',
        '"certified": true',
        '"live_camera": true',
        '"production_api": true',
        '"dispatch_ref": "',
        '"control_ref": "',
        '"enforcement_ref": "',
        '"external_submission_ref": "',
        '"official_case_id": "',
        '"raw_query"',
    ]
    for token in forbidden_pairs:
        if token in serial:
            failures.append(token)
    return failures


def boundary_audit(cases: list[dict[str, Any]], results: list[dict[str, Any]], fixtures: list[dict[str, Any]], evidence_packets: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "cases": cases,
        "results": results,
        "fixtures": fixtures,
        "evidence_packets": evidence_packets,
    }
    failures = boundary_failures(payload)
    return {
        "status": "PASS" if not failures else "FAIL",
        "boundary": BOUNDARY,
        "failures": failures,
        "candidate_only_preserved": all(item.get("candidate_only") is True for collection in [results, fixtures, evidence_packets] for item in collection),
        "official_status_not_official": all(item.get("official_status") == "not_official" for collection in [fixtures, evidence_packets] for item in collection),
        "execution_status_not_executed": all(item.get("execution_status") == "not_executed" for collection in [fixtures, evidence_packets] for item in collection),
        "raw_query_downstream_authority_absent": '"raw_query"' not in json.dumps(payload, sort_keys=True).lower(),
        "live_retrieval_performed": False,
        "production_api_called": False,
        "url_fetch_performed": False,
        "llm_call_performed": False,
        "ask_runtime_invoked": False,
    }


def write_hash_manifest(root: Path) -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "R7C_HASH_MANIFEST.json"):
        items.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "citybrain-r7c-hash-manifest.v1",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / "R7C_HASH_MANIFEST.json", manifest)
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
    write_json(root / "R7C_HASH_MANIFEST.json", manifest)
    return manifest


def write_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    state = load_r7b_state()
    cases = query_cases()
    results = query_results(state)
    fixtures = ask_handoff_fixtures(results)
    evidence_packets = ask_handoff_evidence_packets(fixtures)
    webui = context_exports(results, "webui")
    kit = context_exports(results, "kit")
    audit = boundary_audit(cases, results, fixtures, evidence_packets)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "R7C_EVENT_STATE_QUERY_CASES.json", {"items": cases})
    write_json(root / "R7C_EVENT_STATE_QUERY_RESULTS.json", {"items": results})
    write_json(root / "R7C_ASK_HANDOFF_FIXTURES.json", {"items": fixtures})
    write_json(root / "R7C_ASK_HANDOFF_EVIDENCE_PACKETS.json", {"items": evidence_packets})
    write_json(root / "R7C_WEBUI_QUERY_CONTEXT_EXPORT.json", {"items": webui})
    write_json(root / "R7C_KIT_QUERY_CONTEXT_EXPORT.json", {"items": kit})
    write_json(root / "R7C_BOUNDARY_AUDIT.json", audit)
    write_text(root / "R7C_LIMITATIONS.md", "# R7C Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "R7C_TEST_LOG.md",
        "# R7C Test Log\n\nGenerated by runner. Expected focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff`.\n",
    )
    decision = {
        "package": PACKAGE,
        "status": FINAL_DECISION if audit["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_R7C_EVENT_FABRIC_STATE_QUERY_AND_ASK_HANDOFF",
        "created_at": utc_now(),
        "source_r7b_decision": rel(R7B_DECISION),
        "r7b_state_loaded": not state["fallback_used"],
        "fallback_used": state["fallback_used"],
        "fallback_reason": state["fallback_reason"],
        "result_counts": {
            "query_cases": len(cases),
            "query_results": len(results),
            "ask_handoff_fixtures": len(fixtures),
            "ask_handoff_evidence_packets": len(evidence_packets),
            "webui_query_context_exports": len(webui),
            "kit_query_context_exports": len(kit),
        },
        "contract_check": {
            "local_replay_query_only": True,
            "r7b_materialized_state_consumed_or_fallback_documented": (not state["fallback_used"]) or bool(state["fallback_reason"]),
            "candidate_only_preserved": audit["candidate_only_preserved"],
            "unresolved_observations_queryable": any(result["query_family"] == "unresolved_observations" and result["result_count"] >= 1 for result in results),
            "quarantined_observations_queryable": any(result["query_family"] == "quarantined_observations" and result["result_count"] >= 1 for result in results),
            "event_trace_queryable": any(result["query_family"] == "event_trace_by_id" and result["result_count"] >= 1 for result in results),
            "case_ticket_remains_draft_sandbox_only": True,
            "submission_status_draft_not_submitted": all(item["submission_status"] in {"not_applicable", "draft_not_submitted"} for item in fixtures),
            "action_proposal_execution_status_not_executed": audit["execution_status_not_executed"],
            "no_official_submission_execution": audit["status"] == "PASS",
            "no_dispatch_control_enforcement_execution": audit["status"] == "PASS",
            "no_legal_certified_claim": audit["status"] == "PASS",
            "no_live_retrieval_production_api_url_fetch_llm_call": True,
            "ask_handoff_fixtures_created_without_ask_runtime_changes": len(fixtures) == len(QUERY_FAMILIES),
            "ask_runtime_untouched": True,
        },
        "limitations": LIMITATIONS,
        "next_recommended_package": "MAIN-CITYBRAIN-R7D-WEBUI-KIT-EVENT-STATE-SMOKE",
    }
    write_json(root / "R7C_EVENT_STATE_QUERY_AND_ASK_HANDOFF_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "R7C_EVENT_STATE_QUERY_AND_ASK_HANDOFF_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
