from __future__ import annotations

from collections import Counter

from .contracts import common_fields, validate_overlay_packet, validate_query_result_packet


def _candidate_ref(event: dict) -> str | None:
    return event.get("candidate_observation_ref") or event.get("candidate_observation_id")


def list_active_review_events(events: list[dict]) -> list[dict]:
    return [event for event in events if event["event_type"] in {"candidate_observation.accepted_for_review", "review_event.created"}]


def list_unresolved_observations(events: list[dict]) -> list[dict]:
    return [event for event in events if event["event_type"] == "candidate_observation.unresolved"]


def list_quarantined_observations(events: list[dict]) -> list[dict]:
    return [event for event in events if event["event_type"] == "candidate_observation.quarantined"]


def get_events_for_candidate_observation(events: list[dict], candidate_observation_id: str) -> list[dict]:
    return [event for event in events if _candidate_ref(event) == candidate_observation_id]


def get_events_for_source_class(events: list[dict], source_class: str) -> list[dict]:
    return [event for event in events if event.get("source_class") == source_class]


def get_event_trace(events: list[dict], event_id: str) -> dict:
    for event in events:
        if event["event_id"] == event_id:
            return {
                "event_id": event_id,
                "trace_refs": event["trace_refs"],
                "evidence_refs": event["evidence_refs"],
                "limitation_refs": event["limitation_refs"],
            }
    return {"event_id": event_id, "trace_refs": [], "evidence_refs": [], "limitation_refs": []}


def build_query_result_packet(query_family: str, events: list[dict], filters: dict | None = None) -> dict:
    filters = filters or {}
    event_refs = [event["event_id"] for event in events]
    candidate_refs = sorted({ref for ref in (_candidate_ref(event) for event in events) if ref})
    review_summary = Counter(event["review_state"] for event in events)
    official_summary = Counter(event["official_status"] for event in events)
    evidence_refs = [ref for event in events for ref in event["evidence_refs"]]
    limitation_refs = [ref for event in events for ref in event["limitation_refs"]]
    trace_refs = [ref for event in events for ref in event["trace_refs"]]
    cannot_claim = sorted({claim for event in events for claim in event["cannot_claim"]})
    not_executed = sorted({item for event in events for item in event["not_executed"]})
    packet = {
        **common_fields(),
        "query_case_id": filters.get("query_case_id", f"query-case:{query_family}"),
        "query_result_id": filters.get("query_result_id", f"query-result:{query_family}"),
        "query_family": query_family,
        "event_refs": event_refs,
        "candidate_observation_refs": candidate_refs,
        "knowns": [f"{len(events)} local/replay Event Fabric event(s) matched."],
        "unknowns": ["No official status, live state, legal finding, or certified finding is known."],
        "cannot_claim": cannot_claim,
        "safe_next_looks": ["inspect retained evidence refs", "request human review note"],
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "review_state_summary": dict(review_summary),
        "official_status_summary": dict(official_summary),
        "not_executed": not_executed,
        "raw_query_authority": False,
    }
    return validate_query_result_packet(packet)


def build_overlay_packets_for_events(events: list[dict]) -> list[dict]:
    overlays = []
    for index, event in enumerate(events, start=1):
        candidate_observation_ref = _candidate_ref(event)
        packet = {
            **common_fields(),
            "overlay_id": f"overlay:event-fabric-runtime:{index:04d}",
            "overlay_kind": "marker_metadata_only",
            "event_id": event["event_id"],
            "candidate_observation_ref": candidate_observation_ref,
            "display_label": f"Review candidate: {candidate_observation_ref or event['event_id']}",
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "review_state": event["review_state"],
            "submission_status": event["submission_status"],
            "execution_status": "not_executed",
            "location_ref": event.get("location_ref"),
            "proposed_prim_path": f"/CityBrain/EventFabricRuntime/{index:04d}",
            "marker_metadata_only": True,
            "evidence_refs": event["evidence_refs"],
            "limitation_refs": event["limitation_refs"],
            "trace_refs": event["trace_refs"],
            "cannot_claim": event["cannot_claim"],
            "not_executed": event["not_executed"],
            "live_kit_control": False,
            "full_citywide_twin_claim": False,
        }
        overlays.append(validate_overlay_packet(packet))
    return overlays
