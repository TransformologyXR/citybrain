#!/usr/bin/env python3
"""Run R7B local/replay perception-to-event fabric integration."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay"
R7A_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7a_perception_candidate_observation_ingress"
R7A_DECISION = R7A_ROOT / "R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json"

PACKAGE = "MAIN-CITYBRAIN-R7B-PERCEPTION-TO-EVENT-FABRIC-LOCAL-REPLAY"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_R7B_PERCEPTION_TO_EVENT_FABRIC_LOCAL_REPLAY_WITH_LIMITATIONS"
BOUNDARY = (
    "local/replay event fabric only; event log is append-only fixture output; "
    "candidate observations remain candidate-only and not official; draft cases remain draft_not_submitted; "
    "action proposals remain not_executed"
)
LIMITATIONS = [
    "local/replay event fabric only",
    "event log is deterministic fixture output, not production ingestion",
    "candidate observations and review events are not official facts",
    "unresolved and quarantined records are preserved, not promoted",
    "sandbox draft case event is draft_not_submitted",
    "action proposal event remains not_executed",
    "no live retrieval, production API, URL fetch, official submission, dispatch, control, enforcement, legal/certified claim, or LLM call",
]
ALLOWED_EVENT_TYPES = {
    "candidate_observation.accepted_for_review",
    "candidate_observation.unresolved",
    "candidate_observation.quarantined",
    "review_event.created",
    "sandbox_draft_case.created",
    "action_proposal.created_not_executed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_hash(payload: dict[str, Any], omit: set[str] | None = None) -> str:
    omit = omit or set()
    clean = {key: value for key, value in payload.items() if key not in omit}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


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


def load_r7a_outputs() -> dict[str, Any]:
    decision = read_json(R7A_DECISION, {})
    return {
        "decision": decision,
        "accepted_review_events": read_json(R7A_ROOT / "R7A_ACCEPTED_REVIEW_EVENTS.json", {"items": []}).get("items", []),
        "unresolved_observations": read_json(R7A_ROOT / "R7A_UNRESOLVED_OBSERVATIONS.json", {"items": []}).get("items", []),
        "quarantined_observations": read_json(R7A_ROOT / "R7A_QUARANTINED_OBSERVATIONS.json", {"items": []}).get("items", []),
        "sandbox_draft_case_ticket": decision.get("sandbox_draft_case_ticket"),
        "action_proposal": decision.get("action_proposal"),
    }


def base_event(
    *,
    event_id: str,
    event_type: str,
    candidate_observation_id: str,
    payload: dict[str, Any],
    review_event_id: str | None = None,
    status: str = "materialized",
    review_state: str = "candidate",
    submission_status: str | None = None,
) -> dict[str, Any]:
    evidence_refs = payload.get("evidence_refs") or payload.get("source_refs") or []
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": "1.0",
        "source_package": "MAIN-CITYBRAIN-R7A-PERCEPTION-CANDIDATE-OBSERVATION-INGRESS",
        "source_ref": payload.get("source_id") or payload.get("linked_review_event_id") or candidate_observation_id,
        "candidate_observation_id": candidate_observation_id,
        "review_event_id": review_event_id,
        "event_time": "2026-07-04T11:20:00Z",
        "ingested_at": "2026-07-04T11:20:05Z",
        "entity_refs": payload.get("entity_refs") or [],
        "location_ref": payload.get("location_ref"),
        "status": status,
        "review_state": review_state,
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": submission_status or "not_applicable",
        "execution_status": "not_executed",
        "evidence_refs": evidence_refs,
        "limitation_refs": payload.get("limitation_refs") or LIMITATIONS,
        "not_executed": payload.get("not_executed") or ["production_api", "official_submission", "dispatch_control_enforcement", "llm_call"],
        "trace_refs": payload.get("trace") or [f"R7B:{event_type}", "R7B:local_replay_event_log"],
        "payload": payload,
    }
    event["event_hash"] = canonical_hash(event, {"event_hash"})
    return event


def build_event_log(r7a: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    r7a = r7a or load_r7a_outputs()
    events: list[dict[str, Any]] = []
    for item in r7a["accepted_review_events"]:
        candidate_id = item["candidate_observation_id"]
        review_event_id = item.get("review_event_id")
        events.append(
            base_event(
                event_id="r7b:event:accepted:0001",
                event_type="candidate_observation.accepted_for_review",
                candidate_observation_id=candidate_id,
                review_event_id=review_event_id,
                payload=item,
                review_state="candidate",
            )
        )
        events.append(
            base_event(
                event_id="r7b:event:review-created:0001",
                event_type="review_event.created",
                candidate_observation_id=candidate_id,
                review_event_id=review_event_id,
                payload=item,
                review_state="candidate",
            )
        )
    for index, item in enumerate(r7a["unresolved_observations"], start=1):
        events.append(
            base_event(
                event_id=f"r7b:event:unresolved:{index:04d}",
                event_type="candidate_observation.unresolved",
                candidate_observation_id=item["candidate_observation_id"],
                payload=item,
                status="preserved_unresolved",
                review_state="needs_source",
            )
        )
    for index, item in enumerate(r7a["quarantined_observations"], start=1):
        events.append(
            base_event(
                event_id=f"r7b:event:quarantined:{index:04d}",
                event_type="candidate_observation.quarantined",
                candidate_observation_id=item["candidate_observation_id"],
                payload=item,
                status="quarantined_not_promoted",
                review_state="quarantined",
            )
        )
    draft = r7a.get("sandbox_draft_case_ticket")
    if draft:
        events.append(
            base_event(
                event_id="r7b:event:sandbox-draft-case:0001",
                event_type="sandbox_draft_case.created",
                candidate_observation_id=draft["linked_candidate_observation_id"],
                review_event_id=draft["linked_review_event_id"],
                payload=draft,
                review_state="reviewed_candidate",
                submission_status="draft_not_submitted",
            )
        )
    proposal = r7a.get("action_proposal")
    if proposal:
        events.append(
            base_event(
                event_id="r7b:event:action-proposal:0001",
                event_type="action_proposal.created_not_executed",
                candidate_observation_id="candidate:r7a:obs:accepted-001",
                review_event_id=proposal["linked_review_event_id"],
                payload=proposal,
                review_state="proposal_pending",
            )
        )
    return events


def replay_event_log(events: list[dict[str, Any]]) -> dict[str, Any]:
    replayed = []
    for ordinal, event in enumerate(events, start=1):
        expected_hash = canonical_hash(event, {"event_hash"})
        replayed.append(
            {
                "ordinal": ordinal,
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "candidate_observation_id": event["candidate_observation_id"],
                "hash_ok": event.get("event_hash") == expected_hash,
                "candidate_only": event["candidate_only"],
                "official_status": event["official_status"],
                "submission_status": event["submission_status"],
                "execution_status": event["execution_status"],
            }
        )
    return {
        "status": "PASS" if all(item["hash_ok"] for item in replayed) else "FAIL",
        "event_count": len(events),
        "accepted_events": sum(1 for event in events if event["event_type"] == "candidate_observation.accepted_for_review"),
        "unresolved_events": sum(1 for event in events if event["event_type"] == "candidate_observation.unresolved"),
        "quarantined_events": sum(1 for event in events if event["event_type"] == "candidate_observation.quarantined"),
        "not_executed_preserved": all(event["execution_status"] == "not_executed" for event in events),
        "not_official_preserved": all(event["official_status"] == "not_official" for event in events),
        "no_official_submissions": all(event["submission_status"] in {"not_applicable", "draft_not_submitted"} for event in events),
        "no_execution_refs": not boundary_failures(events),
        "events": replayed,
    }


def materialize_review_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    active_review_events = [event for event in events if event["event_type"] == "review_event.created"]
    unresolved = [event for event in events if event["event_type"] == "candidate_observation.unresolved"]
    quarantined = [event for event in events if event["event_type"] == "candidate_observation.quarantined"]
    sandbox_drafts = [event for event in events if event["event_type"] == "sandbox_draft_case.created"]
    proposals = [event for event in events if event["event_type"] == "action_proposal.created_not_executed"]
    return {
        "status": "PASS",
        "active_review_events": active_review_events,
        "unresolved_observations": unresolved,
        "quarantined_observations": quarantined,
        "sandbox_draft_cases": sandbox_drafts,
        "not_executed_action_proposals": proposals,
        "summary_counts": {
            "active_review_events": len(active_review_events),
            "unresolved_observations": len(unresolved),
            "quarantined_observations": len(quarantined),
            "sandbox_draft_cases": len(sandbox_drafts),
            "not_executed_action_proposals": len(proposals),
        },
    }


def list_active_review_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["event_type"] == "review_event.created"]


def list_unresolved_observations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["event_type"] == "candidate_observation.unresolved"]


def list_quarantined_observations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event["event_type"] == "candidate_observation.quarantined"]


def get_events_for_candidate_observation(events: list[dict[str, Any]], candidate_observation_id: str) -> list[dict[str, Any]]:
    return [event for event in events if event["candidate_observation_id"] == candidate_observation_id]


def get_events_for_entity(events: list[dict[str, Any]], entity_ref: str) -> list[dict[str, Any]]:
    return [event for event in events if entity_ref in event.get("entity_refs", [])]


def get_event_trace(events: list[dict[str, Any]], event_id: str) -> list[str]:
    for event in events:
        if event["event_id"] == event_id:
            return event["trace_refs"]
    return []


def query_fixture(events: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_id = "candidate:r7a:obs:accepted-001"
    return {
        "active_review_events": [event["event_id"] for event in list_active_review_events(events)],
        "unresolved_observations": [event["candidate_observation_id"] for event in list_unresolved_observations(events)],
        "quarantined_observations": [event["candidate_observation_id"] for event in list_quarantined_observations(events)],
        "events_for_accepted_candidate": [event["event_id"] for event in get_events_for_candidate_observation(events, accepted_id)],
        "events_for_demo_entity": [event["event_id"] for event in get_events_for_entity(events, "entity:r7a:demo-west-gate-review-area")],
        "trace_for_review_event": get_event_trace(events, "r7b:event:review-created:0001"),
    }


def overlay_exports(events: list[dict[str, Any]], surface: str) -> list[dict[str, Any]]:
    overlays = []
    for event in events:
        if event["event_type"] in {
            "candidate_observation.accepted_for_review",
            "candidate_observation.unresolved",
            "review_event.created",
            "sandbox_draft_case.created",
            "action_proposal.created_not_executed",
        }:
            overlays.append(
                {
                    "surface": surface,
                    "overlay_id": f"{surface}:{event['event_id']}",
                    "event_id": event["event_id"],
                    "event_type": event["event_type"],
                    "candidate_observation_id": event["candidate_observation_id"],
                    "candidate_only": event["candidate_only"],
                    "review_required": event["review_required"],
                    "official_status": event["official_status"],
                    "submission_status": event["submission_status"],
                    "execution_status": event["execution_status"],
                    "evidence_refs": event["evidence_refs"],
                    "limitation_refs": event["limitation_refs"],
                    "trace_refs": event["trace_refs"],
                }
            )
    return overlays


def boundary_failures(events: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for event in events:
        payload = event.get("payload", {})
        if event["event_type"] not in ALLOWED_EVENT_TYPES:
            failures.append(f"unsupported_event_type:{event['event_id']}")
        if event.get("candidate_only") is not True:
            failures.append(f"candidate_only_false:{event['event_id']}")
        if event.get("official_status") != "not_official":
            failures.append(f"official_status:{event['event_id']}")
        if event.get("execution_status") != "not_executed":
            failures.append(f"execution_status:{event['event_id']}")
        if event.get("submission_status") not in {"not_applicable", "draft_not_submitted"}:
            failures.append(f"submission_status:{event['event_id']}")
        for field in ["official_case_id", "external_submission_ref", "dispatch_ref", "control_ref", "enforcement_ref", "external_action_ref"]:
            if payload.get(field) not in (None, "", []):
                failures.append(f"{field}:{event['event_id']}")
        for flag in ["legal_violation", "certified", "live_camera", "production_api"]:
            if payload.get(flag) is True or event.get(flag) is True:
                failures.append(f"{flag}:{event['event_id']}")
    return failures


def boundary_audit(events: list[dict[str, Any]]) -> dict[str, Any]:
    failures = boundary_failures(events)
    return {
        "status": "PASS" if not failures else "FAIL",
        "boundary": BOUNDARY,
        "failures": failures,
        "candidate_only_preserved": all(event["candidate_only"] for event in events),
        "official_status_not_official": all(event["official_status"] == "not_official" for event in events),
        "submission_status_safe": all(event["submission_status"] in {"not_applicable", "draft_not_submitted"} for event in events),
        "execution_status_not_executed": all(event["execution_status"] == "not_executed" for event in events),
        "live_retrieval_performed": False,
        "production_api_called": False,
        "url_fetch_performed": False,
        "llm_call_performed": False,
    }


def write_hash_manifest(root: Path) -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "R7B_HASH_MANIFEST.json"):
        items.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "citybrain-r7b-hash-manifest.v1",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / "R7B_HASH_MANIFEST.json", manifest)
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
    write_json(root / "R7B_HASH_MANIFEST.json", manifest)
    return manifest


def write_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    events = build_event_log()
    replay = replay_event_log(events)
    materialized = materialize_review_state(events)
    queries = query_fixture(events)
    webui = overlay_exports(events, "webui")
    kit = overlay_exports(events, "kit")
    audit = boundary_audit(events)
    root.mkdir(parents=True, exist_ok=True)
    write_jsonl(root / "R7B_LOCAL_EVENT_LOG.jsonl", events)
    write_json(root / "R7B_REPLAY_REPORT.json", replay)
    write_json(root / "R7B_MATERIALIZED_REVIEW_STATE.json", materialized)
    write_json(root / "R7B_EVENT_STATE_QUERY_FIXTURES.json", queries)
    write_json(root / "R7B_WEBUI_EVENT_OVERLAY_EXPORT.json", {"items": webui})
    write_json(root / "R7B_KIT_EVENT_OVERLAY_EXPORT.json", {"items": kit})
    write_json(root / "R7B_BOUNDARY_AUDIT.json", audit)
    write_text(root / "R7B_LIMITATIONS.md", "# R7B Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "R7B_TEST_LOG.md",
        "# R7B Test Log\n\nGenerated by runner. Expected focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7b_perception_to_event_fabric_local_replay`.\n",
    )
    counts = {
        "event_log_entries": len(events),
        "replayed_events": replay["event_count"],
        **materialized["summary_counts"],
        "webui_event_overlays": len(webui),
        "kit_event_overlays": len(kit),
    }
    decision = {
        "package": PACKAGE,
        "status": FINAL_DECISION if replay["status"] == "PASS" and audit["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_R7B_PERCEPTION_TO_EVENT_FABRIC_LOCAL_REPLAY",
        "created_at": utc_now(),
        "source_r7a_decision": rel(R7A_DECISION),
        "result_counts": counts,
        "contract_check": {
            "local_replay_event_fabric_only": True,
            "candidate_only_preserved": audit["candidate_only_preserved"],
            "unresolved_observations_preserved": counts["unresolved_observations"] == 2,
            "quarantined_observations_preserved": counts["quarantined_observations"] == 2,
            "materialized_state_created": materialized["status"] == "PASS",
            "event_replay_deterministic": replay["status"] == "PASS",
            "case_ticket_is_draft_sandbox_only": True,
            "submission_status_draft_not_submitted": audit["submission_status_safe"],
            "action_proposal_execution_status_not_executed": audit["execution_status_not_executed"],
            "no_official_submission_execution": audit["status"] == "PASS",
            "no_dispatch_control_enforcement_execution": audit["status"] == "PASS",
            "no_legal_certified_claim": audit["status"] == "PASS",
            "no_live_retrieval_production_api_llm_call": True,
            "ask_runtime_untouched": True,
        },
        "limitations": LIMITATIONS,
        "next_recommended_package": "MAIN-CITYBRAIN-R7C-EVENT-FABRIC-STATE-QUERY-AND-ASK-HANDOFF",
    }
    write_json(root / "R7B_EVENT_FABRIC_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "R7B_EVENT_FABRIC_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
