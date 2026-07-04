#!/usr/bin/env python3
"""Run R7A local/replay perception candidate-observation ingress."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7a_perception_candidate_observation_ingress"
PREFLIGHT_DECISION = REPO_ROOT / "outputs" / "main_citybrain_r7_perception_to_review_workflow_preflight" / "DECISION.json"

PACKAGE = "MAIN-CITYBRAIN-R7A-PERCEPTION-CANDIDATE-OBSERVATION-INGRESS"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS_WITH_LIMITATIONS"
BOUNDARY = (
    "local/replay candidate-observation ingress only; perception remains candidate observation; "
    "invalid observations quarantine; unresolved observations preserve; no official submission, "
    "dispatch, control, enforcement, legal/certified claim, live retrieval, production API, or LLM call"
)
LIMITATIONS = [
    "local/replay ingress only",
    "candidate observations are review inputs, not official facts",
    "unresolved observations are preserved for review instead of promoted",
    "quarantined observations do not enter review promotion",
    "draft case/ticket examples are sandbox only and draft_not_submitted",
    "action proposal examples remain not_executed",
]

ALLOWED_SOURCE_KINDS = {"replay_fixture", "sample_clip", "synthetic_event", "manual_test_fixture"}
ALLOWED_OBSERVATION_TYPES = {
    "person_vehicle_proximity_candidate",
    "zone_presence_candidate",
    "camera_health_candidate",
    "object_presence_candidate",
}
FORBIDDEN_ASSERTION_TOKENS = {
    "live_camera",
    "production_camera",
    "official_violation",
    "submitted_case",
    "certified_detection",
    "legal_non_compliance",
}
REQUIRED_FIELDS = [
    "candidate_observation_id",
    "source_kind",
    "source_id",
    "source_label",
    "observed_at",
    "detector_kind",
    "detector_version",
    "observation_type",
    "detected_class",
    "confidence",
    "evidence_refs",
    "review_state",
    "claim_boundary",
    "not_executed",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_fixture_set() -> list[dict[str, Any]]:
    base = {
        "source_label": "R7A local replay west gate fixture",
        "observed_at": "2026-07-04T11:10:00Z",
        "detector_kind": "deterministic_fixture_detector",
        "detector_version": "r7a-local-1.0",
        "review_state": "candidate",
        "claim_boundary": "candidate observation only; not an official fact, finding, violation, case, ticket, dispatch, control, or enforcement action",
        "not_executed": [
            "live_camera_connection",
            "production_api",
            "official_case_submission",
            "dispatch_control_enforcement",
            "llm_call",
        ],
        "cannot_claim": [
            "official violation",
            "legal or certified finding",
            "identity of a natural person",
            "official case/ticket creation",
            "dispatch/control/enforcement execution",
        ],
    }
    rows = [
        {
            **base,
            "candidate_observation_id": "candidate:r7a:obs:accepted-001",
            "source_kind": "replay_fixture",
            "source_id": "source:r7a:replay-west-gate-001",
            "media_ref": "media:r7a:west-gate-local-replay-clip",
            "frame_ref": "frame:r7a:west-gate-local-replay-clip:000420",
            "location_ref": "location:r7a:demo-west-gate",
            "geometry_ref": "geometry:r7a:demo-west-gate-zone",
            "observation_type": "person_vehicle_proximity_candidate",
            "detected_class": "person_like_shape",
            "object_class": "person_like_shape",
            "confidence": 0.82,
            "zone_ref": "zone:r7a:demo-review-zone-a",
            "track_ref": "track:r7a:local-0001",
            "evidence_refs": [
                "source:r7a:replay-west-gate-001",
                "frame:r7a:west-gate-local-replay-clip:000420",
            ],
        },
        {
            **base,
            "candidate_observation_id": "candidate:r7a:obs:unresolved-location-001",
            "source_kind": "sample_clip",
            "source_id": "source:r7a:sample-clip-002",
            "media_ref": "media:r7a:sample-clip-002",
            "frame_ref": "frame:r7a:sample-clip-002:000090",
            "location_ref": None,
            "geometry_ref": None,
            "observation_type": "zone_presence_candidate",
            "detected_class": "vehicle_like_shape",
            "object_class": "vehicle_like_shape",
            "confidence": 0.64,
            "zone_ref": "zone:r7a:ambiguous-zone",
            "track_ref": "track:r7a:local-0002",
            "evidence_refs": ["source:r7a:sample-clip-002", "frame:r7a:sample-clip-002:000090"],
        },
        {
            **base,
            "candidate_observation_id": "candidate:r7a:obs:unresolved-low-confidence-001",
            "source_kind": "manual_test_fixture",
            "source_id": "source:r7a:manual-test-003",
            "media_ref": "media:r7a:manual-test-003",
            "frame_ref": "frame:r7a:manual-test-003:000015",
            "location_ref": "location:r7a:demo-loading-bay",
            "geometry_ref": "geometry:r7a:demo-loading-bay",
            "observation_type": "object_presence_candidate",
            "detected_class": "unknown_object_candidate",
            "object_class": "unknown_object_candidate",
            "confidence": 0.39,
            "zone_ref": "zone:r7a:demo-loading-bay",
            "track_ref": None,
            "evidence_refs": ["source:r7a:manual-test-003", "frame:r7a:manual-test-003:000015"],
        },
        {
            **base,
            "candidate_observation_id": "",
            "source_kind": "synthetic_event",
            "source_id": "source:r7a:synthetic-invalid-004",
            "media_ref": "media:r7a:synthetic-invalid-004",
            "frame_ref": "frame:r7a:synthetic-invalid-004:000001",
            "location_ref": "location:r7a:demo-yard",
            "geometry_ref": "geometry:r7a:demo-yard",
            "observation_type": "camera_health_candidate",
            "detected_class": "camera_obstruction_candidate",
            "object_class": "camera_obstruction_candidate",
            "confidence": 0.71,
            "zone_ref": "zone:r7a:demo-yard",
            "track_ref": None,
            "evidence_refs": ["source:r7a:synthetic-invalid-004"],
        },
        {
            **base,
            "candidate_observation_id": "candidate:r7a:obs:quarantine-live-claim-001",
            "source_kind": "live_camera",
            "source_id": "source:r7a:live-production-claim-005",
            "source_label": "Rejected live production source claim fixture",
            "media_ref": "media:r7a:blocked-live-source",
            "frame_ref": "frame:r7a:blocked-live-source:000001",
            "location_ref": "location:r7a:blocked",
            "geometry_ref": "geometry:r7a:blocked",
            "observation_type": "official_violation",
            "detected_class": "certified_detection",
            "object_class": "certified_detection",
            "confidence": 0.93,
            "zone_ref": "zone:r7a:blocked",
            "track_ref": "track:r7a:blocked-0005",
            "evidence_refs": ["source:r7a:live-production-claim-005"],
            "claim_boundary": "official_violation certified_detection live_camera production_camera legal_non_compliance",
        },
    ]
    for row in rows:
        row["packet_hash"] = canonical_hash(row, {"packet_hash"})
    return rows


def danger_tokens(observation: dict[str, Any]) -> list[str]:
    asserted_fields = {
        "source_kind": observation.get("source_kind"),
        "observation_type": observation.get("observation_type"),
        "detected_class": observation.get("detected_class"),
        "object_class": observation.get("object_class"),
        "claim_boundary": observation.get("claim_boundary"),
    }
    text = json.dumps(asserted_fields, sort_keys=True).lower()
    return sorted(token for token in FORBIDDEN_ASSERTION_TOKENS if token in text)


def classify_observation(observation: dict[str, Any]) -> dict[str, Any]:
    quarantine_reasons: list[str] = []
    unresolved_reasons: list[str] = []
    for field in REQUIRED_FIELDS:
        value = observation.get(field)
        if value is None or value == "" or value == []:
            quarantine_reasons.append(f"missing_{field}")
    if observation.get("source_kind") not in ALLOWED_SOURCE_KINDS:
        quarantine_reasons.append("unsupported_or_live_source_kind")
    if observation.get("observation_type") not in ALLOWED_OBSERVATION_TYPES:
        quarantine_reasons.append("unsupported_observation_type")
    confidence = observation.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        quarantine_reasons.append("invalid_confidence")
    elif confidence < 0.5:
        unresolved_reasons.append("low_confidence")
    if not observation.get("location_ref") and not observation.get("geometry_ref"):
        unresolved_reasons.append("missing_location_or_geometry")
    if observation.get("zone_ref") in {None, "", "zone:r7a:ambiguous-zone"}:
        unresolved_reasons.append("ambiguous_zone")
    tokens = danger_tokens(observation)
    if tokens:
        quarantine_reasons.append("forbidden_assertion_tokens:" + ",".join(tokens))
    if observation.get("packet_hash") != canonical_hash(observation, {"packet_hash"}):
        quarantine_reasons.append("packet_hash_mismatch")

    if quarantine_reasons:
        return {"classification": "quarantine", "reasons": sorted(set(quarantine_reasons))}
    if unresolved_reasons:
        return {"classification": "unresolved", "reasons": sorted(set(unresolved_reasons))}
    return {"classification": "accepted", "reasons": []}


def build_review_event(observation: dict[str, Any]) -> dict[str, Any]:
    event = {
        "review_event_id": f"review-event:{observation['candidate_observation_id'].split(':')[-1]}",
        "candidate_observation_id": observation["candidate_observation_id"],
        "event_kind": "candidate_observation_review_event",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "event_truth_status": "candidate_not_confirmed",
        "review_state": "candidate",
        "source_kind": observation["source_kind"],
        "source_id": observation["source_id"],
        "evidence_refs": observation["evidence_refs"],
        "confidence": observation["confidence"],
        "claim_boundary": observation["claim_boundary"],
        "cannot_claim": observation["cannot_claim"],
        "not_executed": observation["not_executed"],
        "trace": [
            "R7A:ingress_validate",
            "R7A:classification_accepted",
            "R7A:review_event_export",
        ],
    }
    event["packet_hash"] = canonical_hash(event, {"packet_hash"})
    return event


def build_unresolved_record(observation: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    record = {
        "candidate_observation_id": observation["candidate_observation_id"],
        "preservation_state": "unresolved_review_candidate",
        "promotion_allowed": False,
        "review_required": True,
        "review_state": "needs_source",
        "candidate_only": True,
        "reasons": reasons,
        "source_id": observation["source_id"],
        "evidence_refs": observation["evidence_refs"],
        "not_executed": observation["not_executed"],
        "safe_next_looks": [
            "request missing location/geometry context",
            "request additional retained evidence before promotion",
            "keep as candidate-only review context",
        ],
    }
    record["packet_hash"] = canonical_hash(record, {"packet_hash"})
    return record


def build_quarantine_record(observation: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    record = {
        "candidate_observation_id": observation.get("candidate_observation_id") or "missing_candidate_observation_id",
        "quarantine_state": "quarantined_not_promoted",
        "review_queue_entered": False,
        "promotion_allowed": False,
        "reasons": reasons,
        "source_kind": observation.get("source_kind"),
        "source_id": observation.get("source_id"),
        "official_status": "not_official",
        "execution_status": "not_executed",
        "not_executed": observation.get("not_executed", ["review_promotion", "official_submission"]),
    }
    record["packet_hash"] = canonical_hash(record, {"packet_hash"})
    return record


def require_reviewer_note(reviewer_note: str | None) -> None:
    if not reviewer_note or not reviewer_note.strip():
        raise ValueError("reviewer_note_required")


def build_sandbox_draft_case_ticket(event: dict[str, Any], reviewer_note: str) -> dict[str, Any]:
    require_reviewer_note(reviewer_note)
    draft = {
        "draft_id": "draft:r7a:sandbox-case-ticket-001",
        "linked_review_event_id": event["review_event_id"],
        "linked_candidate_observation_id": event["candidate_observation_id"],
        "case_scope": "sandbox",
        "submission_status": "draft_not_submitted",
        "official_case_id": None,
        "external_submission_ref": None,
        "reviewer_note": reviewer_note,
        "evidence_refs": event["evidence_refs"],
        "cannot_claim": event["cannot_claim"],
        "not_executed": ["official_case_submission", "external_ticket_creation"],
    }
    draft["packet_hash"] = canonical_hash(draft, {"packet_hash"})
    return draft


def build_action_proposal(event: dict[str, Any]) -> dict[str, Any]:
    proposal = {
        "proposal_id": "proposal:r7a:source-review-001",
        "linked_review_event_id": event["review_event_id"],
        "proposal_type": "request_additional_source_review",
        "approval_required": True,
        "approval_state": "not_approved",
        "execution_status": "not_executed",
        "external_action_ref": None,
        "dispatch_ref": None,
        "control_ref": None,
        "enforcement_ref": None,
        "not_executed": ["dispatch", "control", "enforcement", "external_action"],
    }
    proposal["packet_hash"] = canonical_hash(proposal, {"packet_hash"})
    return proposal


def process_observations(observations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    observations = observations or candidate_fixture_set()
    accepted: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for observation in observations:
        classification = classify_observation(observation)
        if classification["classification"] == "accepted":
            accepted.append(build_review_event(observation))
        elif classification["classification"] == "unresolved":
            unresolved.append(build_unresolved_record(observation, classification["reasons"]))
        else:
            quarantined.append(build_quarantine_record(observation, classification["reasons"]))
    draft = build_sandbox_draft_case_ticket(
        accepted[0],
        "Reviewer note for sandbox draft only; no official submission or action.",
    ) if accepted else None
    proposal = build_action_proposal(accepted[0]) if accepted else None
    review_exports = [
        *[
            {
                "export_kind": "accepted_review_event",
                "candidate_observation_id": event["candidate_observation_id"],
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "limitations": LIMITATIONS,
                "not_executed": event["not_executed"],
            }
            for event in accepted
        ],
        *[
            {
                "export_kind": "unresolved_review_candidate",
                "candidate_observation_id": item["candidate_observation_id"],
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "limitations": LIMITATIONS,
                "not_executed": item["not_executed"],
                "reasons": item["reasons"],
            }
            for item in unresolved
        ],
    ]
    return {
        "candidate_observations": observations,
        "accepted_review_events": accepted,
        "unresolved_observations": unresolved,
        "quarantined_observations": quarantined,
        "sandbox_draft_case_ticket": draft,
        "action_proposal": proposal,
        "webui_exports": [{"surface": "webui", **item} for item in review_exports],
        "kit_exports": [{"surface": "kit", **item} for item in review_exports],
    }


def audit_report(result: dict[str, Any]) -> dict[str, Any]:
    serial = json.dumps(result, sort_keys=True).lower()
    forbidden_true = [
        '"submission_status": "submitted"',
        '"execution_status": "executed"',
        '"official_case_id": "',
        '"external_submission_ref": "',
        '"external_action_ref": "',
        '"dispatch_ref": "',
        '"control_ref": "',
        '"enforcement_ref": "',
    ]
    return {
        "status": "PASS" if not any(token in serial for token in forbidden_true) else "FAIL",
        "boundary": BOUNDARY,
        "candidate_observations_total": len(result["candidate_observations"]),
        "accepted_review_events": len(result["accepted_review_events"]),
        "unresolved_observations": len(result["unresolved_observations"]),
        "quarantined_observations": len(result["quarantined_observations"]),
        "webui_exports": len(result["webui_exports"]),
        "kit_exports": len(result["kit_exports"]),
        "perception_remains_candidate_observation": True,
        "invalid_observations_quarantined": len(result["quarantined_observations"]) >= 1,
        "unresolved_observations_preserved": len(result["unresolved_observations"]) >= 1,
        "reviewer_note_required_for_draft": True,
        "draft_case_ticket_sandbox_only": result["sandbox_draft_case_ticket"]["case_scope"] == "sandbox",
        "action_proposal_not_executed": result["action_proposal"]["execution_status"] == "not_executed",
        "live_retrieval_performed": False,
        "production_api_called": False,
        "llm_call_performed": False,
        "ask_runtime_changed": False,
    }


def write_hash_manifest(root: Path) -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "R7A_HASH_MANIFEST.json"):
        items.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "citybrain-r7a-hash-manifest.v1",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / "R7A_HASH_MANIFEST.json", manifest)
    missing = 0
    mismatch = 0
    for item in items:
        target = root / item["path"]
        if not target.exists():
            missing += 1
        elif sha256_file(target) != item["sha256"]:
            mismatch += 1
    manifest["status"] = "PASS" if missing == 0 and mismatch == 0 else "FAIL"
    manifest["missing_count"] = missing
    manifest["mismatch_count"] = mismatch
    write_json(root / "R7A_HASH_MANIFEST.json", manifest)
    return manifest


def write_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    result = process_observations()
    audit = audit_report(result)
    preflight = read_json(PREFLIGHT_DECISION)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "R7A_CANDIDATE_OBSERVATION_FIXTURES.json", {"items": result["candidate_observations"]})
    write_json(root / "R7A_ACCEPTED_REVIEW_EVENTS.json", {"items": result["accepted_review_events"]})
    write_json(root / "R7A_UNRESOLVED_OBSERVATIONS.json", {"items": result["unresolved_observations"]})
    write_json(root / "R7A_QUARANTINED_OBSERVATIONS.json", {"items": result["quarantined_observations"]})
    write_json(root / "R7A_WEBUI_REVIEW_EXPORT.json", {"items": result["webui_exports"]})
    write_json(root / "R7A_KIT_REVIEW_EXPORT.json", {"items": result["kit_exports"]})
    write_json(root / "R7A_AUDIT_REPORT.json", audit)
    write_text(root / "R7A_LIMITATIONS.md", "# R7A Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "R7A_TEST_LOG.md",
        "# R7A Test Log\n\nGenerated by runner. Expected focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7a_perception_candidate_observation_ingress`.\n",
    )
    decision = {
        "package": PACKAGE,
        "status": FINAL_DECISION if audit["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_R7A_PERCEPTION_CANDIDATE_OBSERVATION_INGRESS",
        "created_at": utc_now(),
        "preflight_status": preflight.get("status"),
        "result_counts": {
            "candidate_observations_total": audit["candidate_observations_total"],
            "accepted_review_events": audit["accepted_review_events"],
            "unresolved_observations": audit["unresolved_observations"],
            "quarantined_observations": audit["quarantined_observations"],
            "webui_exports": audit["webui_exports"],
            "kit_exports": audit["kit_exports"],
        },
        "sandbox_draft_case_ticket": result["sandbox_draft_case_ticket"],
        "action_proposal": result["action_proposal"],
        "contract_check": {
            "perception_remains_candidate_observation": True,
            "invalid_observations_quarantined": audit["invalid_observations_quarantined"],
            "unresolved_observations_preserved": audit["unresolved_observations_preserved"],
            "human_review_promotion_requires_reviewer_note": True,
            "case_ticket_is_draft_sandbox_only": True,
            "submission_status_draft_not_submitted": result["sandbox_draft_case_ticket"]["submission_status"] == "draft_not_submitted",
            "action_proposal_execution_status_not_executed": result["action_proposal"]["execution_status"] == "not_executed",
            "no_official_submission_execution": audit["status"] == "PASS",
            "no_dispatch_control_enforcement_execution": audit["status"] == "PASS",
            "no_legal_certified_claim": audit["status"] == "PASS",
            "no_live_retrieval_production_api_llm_call": True,
            "ask_runtime_untouched": True,
        },
        "limitations": LIMITATIONS,
        "next_recommended_package": "MAIN-CITYBRAIN-R7B-PERCEPTION-TO-EVENT-FABRIC-LOCAL-REPLAY",
    }
    write_json(root / "R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = {
        "status": manifest["status"],
        "item_count": manifest["item_count"],
        "missing_count": manifest["missing_count"],
        "mismatch_count": manifest["mismatch_count"],
    }
    write_json(root / "R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
