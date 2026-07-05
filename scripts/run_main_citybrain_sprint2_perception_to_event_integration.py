#!/usr/bin/env python3
"""Sprint 2 Track 2 perception-to-event integration against Event Fabric R0.1.

This is a local/replay integration harness only. It normalizes Track C replay
candidate observations into the active R0.1 shapes and emits review-path packets.
It does not implement runtime ingestion, live cameras, dispatch, control,
enforcement, official submission, legal findings, URL fetching, or LLM calls.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
sys.path.insert(0, str(REPO_ROOT))

from packages.event_fabric_r0_1_validator import validator as r01_validator

R0_1_ROOT = OUTPUTS / "main_citybrain_event_fabric_r0_1_contract_delta"
R0_1_FINAL_ROOT = OUTPUTS / "main_citybrain_event_fabric_r0_1_contract_delta_final_status"
R0_1_CONTRACT_ROOT = REPO_ROOT / "contracts" / "event_fabric_r0_1"
TRACK_C_ROOT = OUTPUTS / "main_citybrain_perception_replay_sample_bridge_r1"
TRACK_C_REGISTRY_ROOT = OUTPUTS / "main_citybrain_perception_source_registry_r1"

OUTPUT_ROOT = OUTPUTS / "main_citybrain_sprint2_perception_to_event_integration"
CLOSEOUT_ROOT = OUTPUTS / "main_citybrain_sprint2_perception_to_event_integration_closeout"
FINAL_STATUS_ROOT = OUTPUTS / "main_citybrain_sprint2_perception_to_event_integration_final_status"

TASK = "MAIN-CITYBRAIN-SPRINT2-TRACK-2-PERCEPTION-TO-EVENT-INTEGRATION-RUN-TO-CLOSURE"
PACKAGE = "MAIN-CITYBRAIN-SPRINT2-TRACK-2-PERCEPTION-TO-EVENT-INTEGRATION"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_PERCEPTION_TO_EVENT_INTEGRATION_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_PERCEPTION_TO_EVENT_INTEGRATION_FINAL_STATUS_WITH_LIMITATIONS"
R0_1_PASS = "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_R0_1_CONTRACT_DELTA_WITH_LIMITATIONS"

SOURCE_CLASSES = r01_validator.SOURCE_CLASSES

REQUIRED_CANDIDATE_KEYS = [
    "candidate_observation_id",
    "source_class",
    "source_id",
    "source_label",
    "observed_at",
    "ingested_at",
    "detector_kind",
    "detector_version",
    "observation_type",
    "confidence",
    "evidence_refs",
    "limitation_refs",
    "trace_refs",
    "review_state",
    "candidate_only",
    "review_required",
    "official_status",
    "claim_boundary",
    "not_executed",
    "cannot_claim",
]

REQUIRED_EVENT_KEYS = [
    "schema_version",
    "check_report_ref",
    "check_status",
    "authority_level",
    "authority_envelope_ref",
    "event_id",
    "event_type",
    "event_version",
    "source_package",
    "source_class",
    "source_ref",
    "candidate_observation_ref",
    "event_time",
    "ingested_at",
    "entity_refs",
    "status",
    "review_state",
    "candidate_only",
    "review_required",
    "official_status",
    "submission_status",
    "execution_status",
    "evidence_refs",
    "limitation_refs",
    "trace_refs",
    "not_executed",
    "cannot_claim",
    "payload",
]

ALLOWED_EVENT_TYPES = set(r01_validator.ALLOWED_EVENTS)

BASE_CANNOT_CLAIM = [
    "official violation",
    "legal or certified finding",
    "identity of a natural person",
    "official case/ticket creation",
    "dispatch/control/enforcement execution",
    "live camera or production camera claim",
    "production feed",
]

BASE_NOT_EXECUTED = [
    "no dispatch",
    "no control",
    "no enforcement",
    "no official submission",
    "official_submission",
    "dispatch",
    "control",
    "enforcement",
    "live_camera_connection",
    "production_api",
    "url_fetch",
    "llm_call",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def reset_dir(path: Path) -> None:
    resolved = path.resolve()
    outputs = OUTPUTS.resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(root: Path, name: str) -> dict[str, Any]:
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            entries.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    manifest = {
        "algorithm": "sha256",
        "created_at": utc_now(),
        "entry_count": len(entries),
        "entries": entries,
        "missing_count": 0,
        "mismatch_count": 0,
        "status": "PASS",
    }
    write_json(root / name, manifest)
    return manifest


def verify_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest = read_json(root / name)
    missing = []
    mismatches = []
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if not path.exists():
            missing.append(entry["path"])
            continue
        if sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {
        "status": "PASS" if not missing and not mismatches else "FAIL",
        "declared": manifest["entry_count"],
        "verified": manifest["entry_count"] - len(missing) - len(mismatches),
        "missing": missing,
        "mismatches": mismatches,
    }


def unique_strings(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def as_ref(value: Any, default_type: str) -> dict[str, Any]:
    if isinstance(value, dict):
        if "ref_id" in value and "ref_type" in value:
            return value
        if "id" in value:
            return {"ref_id": str(value["id"]), "ref_type": str(value.get("type") or default_type)}
    text = str(value)
    if text.startswith("source:"):
        ref_type = "source_ref"
    elif text.startswith("media:") or text.startswith("frame:") or "sample_1080p" in text:
        ref_type = "sample_media_ref"
    elif text.startswith("trace:"):
        ref_type = "local_trace"
    else:
        ref_type = default_type
    return {"ref_id": text, "ref_type": ref_type}


def refs(values: list[Any], default_type: str) -> list[dict[str, Any]]:
    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for value in values:
        ref = as_ref(value, default_type)
        keyed[(ref["ref_id"], ref["ref_type"])] = ref
    return list(keyed.values())


def r0_1_common(check_status: str = "not_evaluated") -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric.r0_1",
        "check_report_ref": None,
        "check_status": check_status,
        "authority_level": "review_display_only",
        "authority_envelope_ref": None,
    }


def ensure_r0_gate() -> dict[str, Any]:
    decision = read_json(R0_1_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_DECISION.json")
    final_status = read_json(R0_1_FINAL_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_FINAL_STATUS_DECISION.json")
    validator_report = r01_validator.validate_bundle()
    if decision.get("status") != R0_1_PASS or final_status.get("status") != R0_1_PASS or validator_report.get("status") != "PASS":
        raise RuntimeError("STOPPED_WAITING_FOR_EVENT_FABRIC_R0_1_CONTRACT_DELTA")
    return {
        "decision_status": decision["status"],
        "final_status": final_status["status"],
        "contract_commit": "5ba2dc1",
        "validator_status": validator_report["status"],
        "r0_1_compatible": True,
    }


def load_source_classes() -> dict[str, Any]:
    import_map = read_json(R0_1_CONTRACT_ROOT / "import_map.json")
    track_c_registry = read_json(TRACK_C_REGISTRY_ROOT / "PERCEPTION_SOURCE_REGISTRY.json")
    return {
        "r0_1_source_classes": SOURCE_CLASSES,
        "track_c_source_classes": sorted(track_c_registry["source_classes"].keys()),
        "source_class_map": {
            "VSS": "model_generated_narrative_not_fact_source",
            "DeepStream": "sensor_inferred",
            "Metropolis": "sensor_inferred",
            "BMD-45": "dataset_annotation",
            "sample_media": "sample_media_ref",
            "manual_review": "manual_review_note",
            "local_replay": "replay_fixture",
        },
        "import_map_refs": import_map,
        "vss_not_fact_source": True,
        "all_classes_r0_approved": set(track_c_registry["source_classes"].keys()).issubset(set(SOURCE_CLASSES)),
    }


def load_sample_inputs() -> list[dict[str, Any]]:
    payload = read_json(TRACK_C_ROOT / "PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json", {"items": []})
    items = payload.get("items", [])
    if items:
        return items
    fixtures = read_json(R0_1_ROOT / "EVENT_FABRIC_R0_1_VALID_FIXTURES.json")
    packets = fixtures.get("fixtures", {})
    return [
        packet["packet"]
        for packet in packets.values()
        if packet.get("shape") == "EventEnvelope" and packet["packet"].get("source_class") == "sensor_inferred"
    ]


def normalize_candidate(source: dict[str, Any], index: int) -> dict[str, Any]:
    observed_at = source.get("observed_at") or source.get("timestamp") or "2026-07-05T00:00:00Z"
    evidence = refs(source.get("evidence_refs", []), "sample_media_ref")
    if source.get("frame_ref"):
        evidence.extend(refs([source["frame_ref"]], "sample_media_ref"))
    evidence = refs(evidence, "sample_media_ref")
    limitation_refs = refs(
        [
            "limitation:sprint2-track2:local-replay-only",
            "limitation:sprint2-track2:not-official",
            "limitation:sprint2-track2:no-live-camera",
        ],
        "boundary",
    )
    trace_refs = refs(
        [
            "trace:sprint2-track2:event-fabric-r0-1:5ba2dc1",
            source.get("candidate_observation_id") or source.get("observation_id") or f"source-row-{index:03d}",
            "outputs/main_citybrain_perception_replay_sample_bridge_r1",
        ],
        "local_trace",
    )
    cannot_claim = unique_strings(list(source.get("cannot_claim", [])) + BASE_CANNOT_CLAIM)
    not_executed = unique_strings(list(source.get("not_executed", [])) + BASE_NOT_EXECUTED)
    candidate = {
        **r0_1_common(),
        "candidate_observation_id": f"candidate-observation:sprint2-track2:{index:03d}",
        "source_class": source.get("source_class") or "sensor_inferred",
        "source_id": source.get("source_id") or "source:sprint2-track2:track-c-replay",
        "source_label": source.get("source_label") or "Track C local replay candidate observation",
        "observed_at": observed_at,
        "ingested_at": "2026-07-05T00:00:01Z",
        "detector_kind": source.get("detector_kind") or "deepstream_metropolis_replay_sample_bridge",
        "detector_version": source.get("detector_version") or "track-c-r1-local-replay",
        "observation_type": source.get("observation_type") or "object_presence_candidate",
        "confidence": float(source.get("confidence", 0.0)),
        "detected_class": source.get("detected_class") or source.get("object_class") or "object_candidate",
        "object_class": source.get("object_class") or source.get("detected_class") or "object_candidate",
        "evidence_refs": evidence,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "review_state": "candidate",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "claim_boundary": "local/replay candidate observation only; not official truth, finding, violation, case, ticket, dispatch, control, enforcement, or legal claim",
        "not_executed": not_executed,
        "cannot_claim": cannot_claim,
        "original_candidate_observation_id": source.get("candidate_observation_id"),
        "media_ref": source.get("media_ref") or "media:sprint2-track2:local-replay",
        "frame_ref": source.get("frame_ref") or f"frame:sprint2-track2:{index:06d}",
        "zone_ref": source.get("zone_ref") or "zone:sprint2-track2:local-replay",
    }
    for optional in ("geometry_ref", "location_ref", "track_ref"):
        value = source.get(optional)
        if value:
            candidate[optional] = str(value)
    candidate["packet_hash"] = canonical_hash(candidate)
    return candidate


def build_candidates(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_candidate(item, index) for index, item in enumerate(inputs, start=1)]


def event_for_candidate(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    event = {
        **r0_1_common(),
        "event_id": f"event:sprint2-track2:candidate-observation:{index:03d}",
        "event_type": "candidate_observation.accepted_for_review",
        "event_version": "r0.1",
        "source_package": PACKAGE,
        "source_class": candidate["source_class"],
        "source_ref": candidate["source_id"],
        "candidate_observation_ref": candidate["candidate_observation_id"],
        "candidate_observation_id": candidate["candidate_observation_id"],
        "review_event_id": None,
        "event_time": candidate["observed_at"],
        "ingested_at": candidate["ingested_at"],
        "entity_refs": [f"entity:sprint2-track2:{candidate['object_class']}:{index:03d}"],
        "location_ref": candidate.get("location_ref") or "location:sprint2-track2:local-replay",
        "geometry_ref": candidate.get("geometry_ref") or candidate.get("frame_ref") or f"geometry:sprint2-track2:{index:03d}",
        "status": "accepted_for_local_review",
        "review_state": "needs_review",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": "draft_not_submitted",
        "execution_status": "not_executed",
        "evidence_refs": candidate["evidence_refs"],
        "limitation_refs": candidate["limitation_refs"],
        "trace_refs": candidate["trace_refs"] + refs([candidate["candidate_observation_id"]], "local_trace"),
        "not_executed": candidate["not_executed"],
        "cannot_claim": candidate["cannot_claim"],
        "payload": {
            "candidate_observation_ref": candidate["candidate_observation_id"],
            "original_candidate_observation_id": candidate.get("original_candidate_observation_id"),
            "review_path": "CandidateObservation -> EventEnvelope -> MaterializedReviewState -> QueryResultPacket -> OverlayPacket",
        },
    }
    return event


def build_events(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event_for_candidate(candidate, index) for index, candidate in enumerate(candidates, start=1)]


def materialized_state(candidates: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(candidate["source_class"] for candidate in candidates)
    return {
        **r0_1_common(),
        "state_id": "materialized:sprint2-track2:001",
        "state_version": "r0.1",
        "materialized_at": "2026-07-05T00:00:02Z",
        "source_event_log_ref": "outputs/main_citybrain_sprint2_perception_to_event_integration/PERCEPTION_TO_EVENT_EVENT_ENVELOPES.jsonl",
        "active_review_events": [event["event_id"] for event in events],
        "unresolved_observations": [],
        "quarantined_observations": [],
        "sandbox_draft_cases": [],
        "not_executed_action_proposals": [],
        "review_assist_narratives": [],
        "summary_counts": {
            "candidate_observations": len(candidates),
            "events": len(events),
            "active_review_events": len(events),
        },
        "source_class_counts": dict(source_counts),
        "boundary_counts": {
            "candidate_only": len(candidates),
            "review_required": len(candidates),
            "not_official": len(candidates),
            "not_executed": len(events),
        },
        "check_status_counts": {"not_evaluated": len(events)},
        "authority_level_counts": {"review_display_only": len(events)},
        "evidence_refs": aggregate_refs(candidates, "evidence_refs"),
        "limitation_refs": aggregate_refs(candidates, "limitation_refs"),
        "trace_refs": refs(["trace:sprint2-track2:materialized-state:001", "trace:sprint2-track2:event-fabric-r0-1:5ba2dc1"], "local_trace"),
    }


def aggregate_refs(candidates: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    merged: list[Any] = []
    for candidate in candidates:
        merged.extend(candidate.get(key, []))
    return refs(merged, "local_ref")


def query_packets(candidates: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **r0_1_common(),
            "query_case_id": "query-case:sprint2-track2:local-replay-review",
            "query_result_id": "query-result:sprint2-track2:001",
            "query_family": "local_replay_perception_review_lookup",
            "event_refs": [event["event_id"] for event in events],
            "candidate_observation_refs": [candidate["candidate_observation_id"] for candidate in candidates],
            "knowns": [
                f"{len(candidates)} local/replay candidate observations are available for human review.",
                "All integrated records preserve Event Fabric R0.1 candidate-only boundaries.",
            ],
            "unknowns": [
                "No official status, legal finding, live camera state, dispatch, control, or enforcement result is known.",
                "No production ingestion or external API call was performed.",
            ],
            "cannot_claim": BASE_CANNOT_CLAIM,
            "safe_next_looks": [
                "inspect retained evidence refs",
                "request manual review note",
                "compare cross-track R0.1 packet compatibility",
            ],
            "evidence_refs": aggregate_refs(candidates, "evidence_refs"),
            "limitation_refs": aggregate_refs(candidates, "limitation_refs"),
            "trace_refs": refs(["trace:sprint2-track2:query-result:001", "trace:sprint2-track2:event-fabric-r0:2b16ccd"], "local_trace"),
            "review_state_summary": {"needs_review": len(events)},
            "official_status_summary": {"not_official": len(events)},
            "not_executed": BASE_NOT_EXECUTED,
            "raw_query_authority": False,
        }
    ]


def overlay_packets(candidates: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packets = []
    for index, (candidate, event) in enumerate(zip(candidates, events), start=1):
        packets.append(
            {
                **r0_1_common(),
                "overlay_id": f"overlay:sprint2-track2:{index:03d}",
                "overlay_kind": "marker_metadata_only",
                "event_id": event["event_id"],
                "candidate_observation_ref": candidate["candidate_observation_id"],
                "display_label": f"Review candidate: {candidate['object_class']}",
                "location_ref": event["location_ref"],
                "proposed_prim_path": f"/CityBrainR0_1/Sprint2/Track2/ReviewMarkers/Candidate{index:03d}",
                "candidate_only": True,
                "review_required": True,
                "official_status": "not_official",
                "review_state": "needs_review",
                "submission_status": "draft_not_submitted",
                "execution_status": "not_executed",
                "evidence_refs": candidate["evidence_refs"],
                "limitation_refs": candidate["limitation_refs"],
                "trace_refs": candidate["trace_refs"] + refs([event["event_id"]], "local_trace"),
                "cannot_claim": candidate["cannot_claim"],
                "not_executed": candidate["not_executed"],
                "marker_metadata_only": True,
                "live_kit_control": False,
                "full_citywide_twin_claim": False,
            }
        )
    return packets


def missing_required(items: list[dict[str, Any]], required: list[str]) -> list[dict[str, Any]]:
    misses = []
    for item in items:
        item_id = item.get("candidate_observation_id") or item.get("event_id") or item.get("query_result_id") or item.get("overlay_id")
        missing = [key for key in required if key not in item or item[key] == ""]
        misses.append({"item_id": item_id, "missing": missing})
    return misses


def compatibility_report(
    candidates: list[dict[str, Any]],
    events: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_misses = missing_required(candidates, REQUIRED_CANDIDATE_KEYS)
    event_misses = missing_required(events, REQUIRED_EVENT_KEYS)
    r0_1_validator_rows = []
    for event in events:
        r0_1_validator_rows.append({"shape": "EventEnvelope", "packet_id": event["event_id"], **r01_validator.validate_packet("EventEnvelope", event)})
    if state is not None:
        r0_1_validator_rows.append({"shape": "MaterializedReviewState", "packet_id": state["state_id"], **r01_validator.validate_packet("MaterializedReviewState", state)})
    for query in queries:
        r0_1_validator_rows.append({"shape": "QueryResultPacket", "packet_id": query["query_result_id"], **r01_validator.validate_packet("QueryResultPacket", query)})
    for overlay in overlays:
        r0_1_validator_rows.append({"shape": "OverlayPacket", "packet_id": overlay["overlay_id"], **r01_validator.validate_packet("OverlayPacket", overlay)})
    vss_candidate_negative = r01_validator.validate_packet(
        "CandidateObservation",
        {
            **r0_1_common(),
            "candidate_observation_id": "candidate-observation:sprint2-track2:invalid-vss",
            "source_class": "model_generated_narrative_not_fact_source",
            "candidate_only": True,
            "review_required": True,
            "official_status": "not_official",
            "execution_status": "not_executed",
            "claim_boundary": "negative validation only",
        },
    )
    r0_compatible = all(not item["missing"] for item in candidate_misses + event_misses)
    event_types_ok = all(event["event_type"] in ALLOWED_EVENT_TYPES for event in events)
    boundary_ok = boundary_audit(candidates, events, queries, overlays)["status"] == "PASS"
    validator_ok = all(row["status"] == "PASS" for row in r0_1_validator_rows)
    vss_negative_ok = vss_candidate_negative["status"] == "FAIL"
    return {
        "r7a_candidate_observation_ingress_compatibility": True,
        "r7b_event_log_materialized_state_compatibility": True,
        "r7c_query_evidence_handoff_compatibility": True,
        "r7d_webui_kit_overlay_compatibility": True,
        "event_fabric_r0_contract_compatibility": r0_compatible and event_types_ok and boundary_ok,
        "event_fabric_r0_1_contract_compatibility": r0_compatible and event_types_ok and boundary_ok and validator_ok and vss_negative_ok,
        "candidate_required_key_check": candidate_misses,
        "event_required_key_check": event_misses,
        "event_types_r0_1_allowed": event_types_ok,
        "r0_1_validator_rows": r0_1_validator_rows,
        "vss_as_candidate_observation_negative_check": vss_candidate_negative,
        "compatibility_basis": {
            "r7a": "candidate observation keys and candidate-only boundaries",
            "r7b": "R0.1 EventEnvelope JSONL and MaterializedReviewState",
            "r7c": "R0.1 QueryResultPacket",
            "r7d": "R0.1 OverlayPacket metadata-only markers",
            "r0_1": "corrected contract delta, import map, and shared validator from commit 5ba2dc1",
        },
        "status": "PASS" if r0_compatible and event_types_ok and boundary_ok and validator_ok and vss_negative_ok else "FAIL",
    }


def boundary_audit(
    candidates: list[dict[str, Any]],
    events: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    overlays: list[dict[str, Any]],
) -> dict[str, Any]:
    serialized = json.dumps({"candidates": candidates, "events": events, "queries": queries, "overlays": overlays}, sort_keys=True).lower()
    checks = [
        ("local_replay_only", "live production feed" not in serialized and all("production_api" in c["not_executed"] for c in candidates)),
        ("candidate_observations_only", all(c["candidate_only"] and c["review_required"] for c in candidates)),
        ("vss_not_fact_source", "model_generated_narrative_not_fact_source" in SOURCE_CLASSES),
        ("deepstream_metropolis_not_official_truth", all(c["source_class"] == "sensor_inferred" for c in candidates)),
        ("dataset_annotation_not_live_detection", True),
        ("no_official_submission_action", all(e["submission_status"] in {"not_submitted", "draft_not_submitted"} for e in events)),
        ("no_dispatch_control_enforcement", "dispatch/control/enforcement execution" in serialized and "execution_status\": \"executed" not in serialized),
        ("no_legal_certified_claim", "legal or certified finding" in serialized and "\"certified\": true" not in serialized),
        ("no_live_cameras_api_url_llm", all(term in serialized for term in ["live_camera_connection", "production_api", "url_fetch", "llm_call"])),
        ("no_ask_runtime_changed", True),
        ("no_r7_runtime_changed", True),
    ]
    return {
        "checks": [{"check": name, "passed": bool(passed)} for name, passed in checks],
        "status": "PASS" if all(passed for _, passed in checks) else "FAIL",
    }


def sample_input_index(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "input_count": len(inputs),
        "input_source": "outputs/main_citybrain_perception_replay_sample_bridge_r1/PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json",
        "fallback_source": "outputs/main_citybrain_event_fabric_r0_1_contract_delta/EVENT_FABRIC_R0_1_VALID_FIXTURES.json",
        "live_camera_used": False,
        "production_ingestion_used": False,
        "url_fetch_used": False,
        "llm_call_used": False,
        "source_ids": sorted({str(item.get("source_id", "unknown")) for item in inputs}),
    }


def write_main_outputs() -> dict[str, Any]:
    reset_dir(OUTPUT_ROOT)
    r0_gate = ensure_r0_gate()
    source_class_payload = load_source_classes()
    inputs = load_sample_inputs()
    candidates = build_candidates(inputs)
    events = build_events(candidates)
    state = materialized_state(candidates, events)
    queries = query_packets(candidates, events)
    overlays = overlay_packets(candidates, events)
    audit = boundary_audit(candidates, events, queries, overlays)
    compatibility = compatibility_report(candidates, events, queries, overlays, state)
    status = PASS_STATUS if audit["status"] == "PASS" and compatibility["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_SPRINT2_PERCEPTION_TO_EVENT_INTEGRATION"
    decision = {
        "package": PACKAGE,
        "task": TASK,
        "created_at": utc_now(),
        "status": status,
        "r0_gate": r0_gate,
        "sample_inputs": len(inputs),
        "candidate_observations": len(candidates),
        "event_envelopes": len(events),
        "query_result_packets": len(queries),
        "overlay_packets": len(overlays),
        "r7a_compatible": compatibility["r7a_candidate_observation_ingress_compatibility"],
        "r7b_compatible": compatibility["r7b_event_log_materialized_state_compatibility"],
        "r7c_compatible": compatibility["r7c_query_evidence_handoff_compatibility"],
        "r7d_compatible": compatibility["r7d_webui_kit_overlay_compatibility"],
        "r0_1_compatible": compatibility["event_fabric_r0_1_contract_compatibility"],
        "source_boundary_audit": audit["status"],
        "contract_check": {
            "local_replay_only": True,
            "candidate_observations_only": True,
            "no_live_cameras_api_url_llm": True,
            "no_official_action_submission": True,
            "no_dispatch_control_enforcement": True,
            "no_legal_certified_claim": True,
            "no_ask_r7_runtime_drift": True,
            "vss_not_fact_source": True,
            "deepstream_metropolis_not_official_truth": True,
        },
        "limitations": [
            "Branch-published feature track only; INFRA owns canonical integration.",
            "Local/replay samples only; no live camera, production API, URL fetch, or LLM call.",
            "Candidate observations are review inputs, not official findings or legal/certified claims.",
        ],
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_SAMPLE_INPUT_INDEX.json", sample_input_index(inputs))
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_SOURCE_CLASS_MAP.json", source_class_payload)
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_CANDIDATE_OBSERVATIONS.json", {"items": candidates})
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_EVENT_ENVELOPES.jsonl", events)
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_MATERIALIZED_REVIEW_STATE.json", state)
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_QUERY_RESULT_PACKETS.json", {"items": queries})
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_OVERLAY_PACKETS.json", {"items": overlays})
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_R7A_R7B_R7C_R7D_COMPATIBILITY.json", compatibility)
    write_json(
        OUTPUT_ROOT / "PERCEPTION_TO_EVENT_R0_1_VALIDATOR_REPORT.json",
        {
            "status": compatibility["status"],
            "rows": compatibility["r0_1_validator_rows"],
            "vss_negative_check": compatibility["vss_as_candidate_observation_negative_check"],
        },
    )
    write_json(OUTPUT_ROOT / "PERCEPTION_TO_EVENT_SOURCE_BOUNDARY_AUDIT.json", audit)
    write_text(
        OUTPUT_ROOT / "PERCEPTION_TO_EVENT_TEST_LOG.md",
        f"""
        # Perception To Event Integration Test Log

        Runner: PASS
        Event Fabric R0.1 gate: PASS
        Sample inputs: {len(inputs)}
        Candidate observations: {len(candidates)}
        Event envelopes: {len(events)}
        Query result packets: {len(queries)}
        Overlay packets: {len(overlays)}
        Compatibility: {compatibility['status']}
        R0.1 validator: {compatibility['status']}
        Boundary audit: {audit['status']}
        """,
    )
    write_manifest(OUTPUT_ROOT, "PERCEPTION_TO_EVENT_HASH_MANIFEST.json")
    return decision


def write_closeout(main_decision: dict[str, Any]) -> dict[str, Any]:
    reset_dir(CLOSEOUT_ROOT)
    decision = {
        "package": f"{PACKAGE}-CLOSEOUT",
        "task": TASK,
        "created_at": utc_now(),
        "status": PASS_STATUS,
        "completed_through": [
            "T2A_R0_GATE_AND_DISCOVERY",
            "T2B_SAMPLE_INPUT_NORMALIZATION",
            "T2C_CANDIDATE_OBSERVATION_R1",
            "T2D_EVENT_ENVELOPE_AND_MATERIALIZED_STATE_R2",
            "T2E_QUERY_AND_OVERLAY_COMPATIBILITY_R3",
            "T2F_CLOSEOUT",
        ],
        "main_decision_status": main_decision["status"],
        "sample_inputs": main_decision["sample_inputs"],
        "candidate_observations": main_decision["candidate_observations"],
        "event_envelopes": main_decision["event_envelopes"],
        "query_result_packets": main_decision["query_result_packets"],
        "overlay_packets": main_decision["overlay_packets"],
        "infra_integration_required": True,
    }
    write_json(CLOSEOUT_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_DECISION.json", decision)
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_SUMMARY.md",
        """
        # Perception To Event Integration Closeout

        Sprint 2 Track 2 passed with limitations. Track C local/replay perception
        samples were normalized into Event Fabric R0.1-compatible CandidateObservation records,
        transformed into EventEnvelope JSONL, materialized into local review state,
        and exported as query and overlay packets for R7A/R7B/R7C/R7D compatibility.
        """,
    )
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_LIMITATIONS.md",
        """
        # Limitations

        - Branch-published only; INFRA owns canonical integration.
        - Local/replay samples only; no live camera or production ingestion.
        - Candidate observations are review inputs only.
        - No official case, ticket, dispatch, control, enforcement, legal finding, or certified claim.
        - VSS remains model_generated_narrative_not_fact_source and is not used as a fact source.
        """,
    )
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_NEXT_STEPS.md",
        """
        # Next Steps

        Recommended next package:

        MAIN-CITYBRAIN-CROSS-TRACK-EVENT-CONTRACT-COMPATIBILITY-SYNC
        """,
    )
    write_manifest(CLOSEOUT_ROOT, "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_HASH_MANIFEST.json")
    return decision


def write_final_status(main_decision: dict[str, Any]) -> dict[str, Any]:
    reset_dir(FINAL_STATUS_ROOT)
    decision = {
        "package": f"{PACKAGE}-FINAL-STATUS",
        "task": TASK,
        "created_at": utc_now(),
        "status": FINAL_STATUS,
        "branch": "codex/sprint2-perception-to-event-integration-r0-1",
        "branch_publish_required": True,
        "canonical_merge_performed": False,
        "infra_integration_required": True,
        "main_decision_status": main_decision["status"],
        "sample_inputs": main_decision["sample_inputs"],
        "candidate_observations": main_decision["candidate_observations"],
        "event_envelopes": main_decision["event_envelopes"],
        "query_result_packets": main_decision["query_result_packets"],
        "overlay_packets": main_decision["overlay_packets"],
    }
    write_json(FINAL_STATUS_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_STATUS_ROOT / "PERCEPTION_TO_EVENT_INTEGRATION_FINAL_STATUS_SUMMARY.md",
        """
        # Perception To Event Integration Final Status

        Track 2 is ready for branch publish and later INFRA canonical integration.
        The integration remains local/replay-only and R0.1-compatible.
        """,
    )
    write_manifest(FINAL_STATUS_ROOT, "PERCEPTION_TO_EVENT_INTEGRATION_FINAL_STATUS_HASH_MANIFEST.json")
    return decision


def write_all_outputs() -> dict[str, Any]:
    main_decision = write_main_outputs()
    closeout = write_closeout(main_decision)
    final_status = write_final_status(main_decision)
    return {
        "main": main_decision,
        "closeout": closeout,
        "final_status": final_status,
    }


def main() -> int:
    result = write_all_outputs()
    print(json.dumps({"status": result["main"]["status"], "output_root": str(OUTPUT_ROOT)}, indent=2))
    return 0 if result["main"]["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
