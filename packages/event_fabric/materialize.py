from __future__ import annotations

from collections import Counter

from .contracts import (
    ACTIVE_SCHEMA_VERSION,
    ACTIVE_STATE_VERSION,
    common_fields,
    utc_now,
    validate_materialized_state,
)


def _candidate_ref(event: dict) -> str | None:
    return event.get("candidate_observation_ref") or event.get("candidate_observation_id")


def materialize_review_state(events: list[dict]) -> dict:
    active = []
    unresolved = []
    quarantined = []
    drafts = []
    proposals = []
    narratives = []
    source_counts: Counter[str] = Counter()
    boundary_counts: Counter[str] = Counter()
    check_status_counts: Counter[str] = Counter()
    authority_level_counts: Counter[str] = Counter()
    evidence_refs = []
    limitation_refs = []
    trace_refs = []
    for event in events:
        source_counts[event["source_class"]] += 1
        boundary_counts[event["official_status"]] += 1
        boundary_counts[event["execution_status"]] += 1
        check_status_counts[event["check_status"]] += 1
        authority_level_counts[str(event["authority_level"])] += 1
        evidence_refs.extend(event["evidence_refs"])
        limitation_refs.extend(event["limitation_refs"])
        trace_refs.extend(event["trace_refs"])
        if event["candidate_only"]:
            boundary_counts["candidate_only"] += 1
        if event["event_type"] in {"candidate_observation.accepted_for_review", "review_event.created"}:
            active.append(event["event_id"])
        if event["event_type"] == "candidate_observation.unresolved":
            unresolved.append(_candidate_ref(event))
        if event["event_type"] == "candidate_observation.quarantined":
            quarantined.append(_candidate_ref(event))
        if event["event_type"] == "sandbox_draft_case.created":
            drafts.append({
                "event_id": event["event_id"],
                "draft_case_id": event["payload"].get("draft_case_id", event["event_id"]),
                "submission_status": event["submission_status"],
            })
        if event["event_type"] == "action_proposal.created_not_executed":
            proposals.append({
                "event_id": event["event_id"],
                "proposal_id": event["payload"].get("proposal_id", event["event_id"]),
                "execution_status": event["execution_status"],
            })
        if event["event_type"] == "review_assist_narrative.attached":
            narratives.append({
                "event_id": event["event_id"],
                "narrative_ref": event["payload"].get("review_assist_narrative_ref", event["source_ref"]),
                "source_class": event["source_class"],
            })
    state = {
        **common_fields(),
        "state_id": "materialized:r0.1:event-fabric-runtime-spine",
        "state_version": ACTIVE_STATE_VERSION,
        "materialized_at": utc_now(),
        "source_event_log_ref": "event-log:r0.1:event-fabric-runtime-spine",
        "active_review_events": active,
        "unresolved_observations": [ref for ref in unresolved if ref],
        "quarantined_observations": [ref for ref in quarantined if ref],
        "sandbox_draft_cases": drafts,
        "not_executed_action_proposals": proposals,
        "review_assist_narratives": narratives,
        "summary_counts": {
            "events": len(events),
            "candidate_observations": len({ref for ref in (_candidate_ref(event) for event in events) if ref}),
            "active_review_events": len(active),
            "unresolved_observations": len(unresolved),
            "quarantined_observations": len(quarantined),
            "sandbox_draft_cases": len(drafts),
            "not_executed_action_proposals": len(proposals),
            "review_assist_narratives": len(narratives),
        },
        "source_class_counts": dict(source_counts),
        "boundary_counts": dict(boundary_counts),
        "check_status_counts": dict(check_status_counts),
        "authority_level_counts": dict(authority_level_counts),
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
    }
    state["schema_version"] = ACTIVE_SCHEMA_VERSION
    return validate_materialized_state(state)
