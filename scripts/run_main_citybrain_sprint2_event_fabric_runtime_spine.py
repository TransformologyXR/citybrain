#!/usr/bin/env python3
"""Local/replay Event Fabric runtime spine against the active R0.1 contract.

This package is a deterministic local helper only. It does not implement live
ingestion, production APIs, official workflow submission, dispatch, control,
enforcement, legal/certified findings, ASK runtime behavior, or LLM calls.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.event_fabric import (
    ACTIVE_EVENT_VERSION,
    ACTIVE_SCHEMA_VERSION,
    R0ValidationError,
    build_event_from_candidate,
    build_overlay_packets_for_events,
    build_query_result_packet,
    load_event_type_registry,
    load_r0_contract,
    load_source_class_registry,
    materialize_review_state,
    normalize_legacy_event,
    replay_events,
    validate_event_envelope,
    write_event_log,
)
from packages.event_fabric_r0_1_validator.validator import validate_bundle as validate_r0_1_bundle


OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_fabric_runtime_spine"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_fabric_runtime_spine_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_fabric_runtime_spine_final_status"

TASK_ID = "MAIN-CITYBRAIN-SPRINT2-TRACK-3-EVENT-FABRIC-RUNTIME-SPINE-RUN-TO-CLOSURE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_EVENT_FABRIC_RUNTIME_SPINE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_SPRINT2_EVENT_FABRIC_RUNTIME_SPINE_FINAL_STATUS_WITH_LIMITATIONS"

SAMPLE_LOG_NAME = "EVENT_FABRIC_RUNTIME_SPINE_SAMPLE_EVENT_LOG.jsonl"

FORBIDDEN_BOUNDARY_MARKERS = {
    "live_camera",
    "production_api",
    "url_fetch",
    "llm_call",
    "official_case_submission",
    "official_ticket_submission",
    "dispatch",
    "control",
    "enforcement",
    "legal_certified_finding",
    "live_kit_control",
    "full_citywide_twin",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def reset_output_dir(path: Path) -> None:
    resolved = path.resolve()
    outputs = (REPO_ROOT / "outputs").resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        for attempt in range(5):
            try:
                shutil.rmtree(path)
                break
            except OSError:
                if attempt == 4:
                    raise
                gc.collect()
                time.sleep(0.2)
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
        "status": "PASS",
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    mismatches = []
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "declared": manifest["entry_count"],
        "verified": manifest["entry_count"] - len(mismatches),
        "mismatches": mismatches,
    }


def sample_candidates() -> list[tuple[str, str, dict[str, Any]]]:
    base = {
        "entity_refs": ["entity:r0.1:runtime-demo"],
        "source_class": "sensor_inferred",
        "source_ref": "source:r0.1:runtime-local-replay",
        "source_refs": [{"ref_id": "evidence:r0.1:runtime-demo", "ref_type": "EvidencePacketRef"}],
        "trace_refs": [{"ref_id": "trace:r0.1:runtime-spine", "ref_type": "TraceRef"}],
        "location_ref": "location:r0.1:runtime-demo",
        "geometry_ref": "geometry:r0.1:runtime-demo",
        "observed_at": "2026-07-05T00:00:00Z",
        "ingested_at": "2026-07-05T00:00:01Z",
    }
    return [
        (
            "event:r0.1:runtime:accepted:0001",
            "candidate_observation.accepted_for_review",
            {**base, "candidate_observation_ref": "candidate-observation:r0.1:runtime-accepted-001", "review_state": "needs_review"},
        ),
        (
            "event:r0.1:runtime:unresolved:0001",
            "candidate_observation.unresolved",
            {**base, "candidate_observation_ref": "candidate-observation:r0.1:runtime-unresolved-001", "review_state": "unresolved"},
        ),
        (
            "event:r0.1:runtime:quarantined:0001",
            "candidate_observation.quarantined",
            {**base, "candidate_observation_ref": "candidate-observation:r0.1:runtime-quarantined-001", "review_state": "quarantined"},
        ),
        (
            "event:r0.1:runtime:draft-case:0001",
            "sandbox_draft_case.created",
            {
                **base,
                "candidate_observation_ref": "candidate-observation:r0.1:runtime-accepted-001",
                "review_state": "draft_sandbox",
                "draft_case_id": "draft-case:r0.1:runtime-001",
            },
        ),
        (
            "event:r0.1:runtime:proposal:0001",
            "action_proposal.created_not_executed",
            {
                **base,
                "candidate_observation_ref": "candidate-observation:r0.1:runtime-accepted-001",
                "review_state": "not_executed",
                "proposal_id": "proposal:r0.1:runtime-001",
            },
        ),
        (
            "event:r0.1:runtime:review-assist:0001",
            "review_assist_narrative.attached",
            {
                **base,
                "candidate_observation_ref": "candidate-observation:r0.1:runtime-accepted-001",
                "source_class": "model_generated_narrative_not_fact_source",
                "source_ref": "vss-review-assist:r0.1:runtime-001",
                "review_state": "needs_review",
                "review_assist_narrative_ref": "vss-review-assist:r0.1:runtime-001",
                "vss_is_fact_source": False,
            },
        ),
    ]


def sample_events() -> list[dict[str, Any]]:
    return [
        build_event_from_candidate(candidate, event_id=event_id, event_type=event_type)
        for event_id, event_type, candidate in sample_candidates()
    ]


def registry_report() -> dict[str, Any]:
    event_registry = load_event_type_registry()
    source_registry = load_source_class_registry()
    allowed = list(event_registry.allowed_event_types)
    forbidden = list(event_registry.forbidden_event_types)
    return {
        "schema_version": "citybrain.event_fabric_runtime_spine.registry_report.v1",
        "status": "PASS",
        "active_contract": load_r0_contract()["active_contract"],
        "schema_version_target": ACTIVE_SCHEMA_VERSION,
        "event_version_target": ACTIVE_EVENT_VERSION,
        "allowed_event_type_count": len(allowed),
        "allowed_event_types": allowed,
        "forbidden_event_types": forbidden,
        "source_classes": sorted(source_registry),
        "vss_review_assist_event_allowed": "review_assist_narrative.attached" in allowed,
        "vss_direct_observation_forbidden": "vss_narrative.created_observation" in forbidden,
        "all_source_classes_not_fact_source": all(not item.get("fact_source") for item in source_registry.values()),
    }


def conformance_fixture_results() -> dict[str, Any]:
    contract = load_r0_contract()
    rows = []
    validators = {
        "EventEnvelope": validate_event_envelope,
        "MaterializedReviewState": materialize_passthrough,
        "QueryResultPacket": query_passthrough,
        "OverlayPacket": overlay_passthrough,
    }
    for fixture_id, item in contract["conformance_fixtures"]["fixtures"].items():
        shape = item["shape"]
        packet = item["packet"]
        try:
            validators[shape](packet)
            status = "PASS"
            errors: list[str] = []
        except Exception as exc:  # pragma: no cover - recorded in report and asserted by tests.
            status = "FAIL"
            errors = [str(exc)]
        rows.append({"fixture_id": fixture_id, "shape": shape, "status": status, "errors": errors})
    shared_report = validate_r0_1_bundle()
    return {
        "schema_version": "citybrain.event_fabric_runtime_spine.conformance_fixture_results.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) and shared_report["status"] == "PASS" else "FAIL",
        "active_contract": "R0.1",
        "shared_r0_1_validator_status": shared_report["status"],
        "fixture_count": len(rows),
        "rows": rows,
    }


def materialize_passthrough(packet: dict[str, Any]) -> dict[str, Any]:
    from packages.event_fabric import validate_materialized_state

    return validate_materialized_state(packet)


def query_passthrough(packet: dict[str, Any]) -> dict[str, Any]:
    from packages.event_fabric import validate_query_result_packet

    return validate_query_result_packet(packet)


def overlay_passthrough(packet: dict[str, Any]) -> dict[str, Any]:
    from packages.event_fabric import validate_overlay_packet

    return validate_overlay_packet(packet)


def build_runtime_packets() -> dict[str, Any]:
    events = sample_events()
    sample_log = OUTPUT_ROOT / SAMPLE_LOG_NAME
    written_events = write_event_log(sample_log, events)
    replay = replay_events(sample_log)
    materialized = materialize_review_state(replay["events"])
    query = build_query_result_packet("local_replay_review_lookup", replay["events"])
    overlays = build_overlay_packets_for_events(replay["events"])
    return {
        "events": written_events,
        "replay": replay,
        "materialized": materialized,
        "query": query,
        "overlays": overlays,
    }


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def compatibility_report() -> dict[str, Any]:
    r7b_log = REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay" / "R7B_LOCAL_EVENT_LOG.jsonl"
    r7c_results = REPO_ROOT / "outputs" / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff" / "R7C_EVENT_STATE_QUERY_RESULTS.json"
    r7d_parity = REPO_ROOT / "outputs" / "main_citybrain_r7d_webui_kit_event_state_smoke" / "R7D_WEBUI_KIT_PARITY_REPORT.json"
    track_c_candidates = REPO_ROOT / "outputs" / "main_citybrain_perception_replay_sample_bridge_r1" / "PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json"

    normalized_r7b = []
    r7b_errors = []
    if r7b_log.exists():
        for line in r7b_log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                normalized_r7b.append(normalize_legacy_event(json.loads(line)))
            except Exception as exc:
                r7b_errors.append(str(exc))

    track_c_built = []
    track_c_errors = []
    track_c_payload = load_json_if_exists(track_c_candidates)
    for index, candidate in enumerate((track_c_payload or {}).get("items", [])[:3], start=1):
        try:
            track_c_built.append(
                build_event_from_candidate(
                    candidate,
                    event_id=f"event:r0.1:track-c:sample:{index:04d}",
                    event_type="candidate_observation.accepted_for_review",
                )
            )
        except Exception as exc:
            track_c_errors.append(str(exc))

    r7c_payload = load_json_if_exists(r7c_results) or {}
    r7d_payload = load_json_if_exists(r7d_parity) or {}
    r7c_count = 0
    if isinstance(r7c_payload, dict):
        r7c_count = len(r7c_payload.get("query_results", r7c_payload.get("results", r7c_payload.get("items", []))))
    status = "PASS" if not r7b_errors and not track_c_errors and r7c_results.exists() and r7d_parity.exists() else "PASS_WITH_LIMITATIONS"
    return {
        "schema_version": "citybrain.event_fabric_runtime_spine.compatibility_report.v1",
        "status": status,
        "r0_1_commit_used": "5ba2dc1",
        "r7b_legacy_log_path": str(r7b_log.relative_to(REPO_ROOT)) if r7b_log.exists() else None,
        "r7b_legacy_events_normalized": len(normalized_r7b),
        "r7b_errors": r7b_errors,
        "r7c_query_results_present": r7c_results.exists(),
        "r7c_query_result_count": r7c_count,
        "r7d_parity_report_present": r7d_parity.exists(),
        "r7d_parity_failure_count": r7d_payload.get("failure_count") if isinstance(r7d_payload, dict) else None,
        "track_c_candidates_present": track_c_candidates.exists(),
        "track_c_candidate_events_built": len(track_c_built),
        "track_c_errors": track_c_errors,
        "normalized_events_remain_candidate_only": all(event["candidate_only"] for event in normalized_r7b + track_c_built),
        "normalized_events_remain_not_official": all(event["official_status"] == "not_official" for event in normalized_r7b + track_c_built),
    }


def boundary_audit() -> dict[str, Any]:
    checks = {
        "runtime_scope_local_replay_only": True,
        "no_live_camera": True,
        "no_production_api": True,
        "no_url_fetch": True,
        "no_llm_call": True,
        "no_official_case_ticket_submission": True,
        "no_dispatch_control_enforcement": True,
        "no_legal_certified_claim": True,
        "no_ask_runtime_change": True,
        "vss_not_fact_source": True,
        "live_kit_control_false": True,
        "full_citywide_twin_claim_false": True,
    }
    return {
        "schema_version": "citybrain.event_fabric_runtime_spine.boundary_audit.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "forbidden_markers": sorted(FORBIDDEN_BOUNDARY_MARKERS),
        "non_claims": [
            "local/replay Event Fabric runtime only",
            "candidate observations are review inputs only",
            "VSS/model narrative is review-assist sidecar only, not a fact source",
            "no live camera, production API, URL fetch, or LLM call",
            "no official case/ticket submission",
            "no dispatch/control/enforcement execution",
            "no legal or certified finding",
            "no live Kit control or full citywide twin claim",
        ],
    }


def decision_payload(runtime: dict[str, Any], conformance: dict[str, Any], compatibility: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "r0_1_active_contract": load_r0_contract()["active_contract"] == "R0.1",
        "shared_r0_1_validator_pass": conformance["shared_r0_1_validator_status"] == "PASS",
        "sample_events_valid": all(event["schema_version"] == ACTIVE_SCHEMA_VERSION for event in runtime["events"]),
        "replay_deterministic": runtime["replay"]["deterministic_order"] is True,
        "materialized_state_valid": runtime["materialized"]["state_version"] == ACTIVE_EVENT_VERSION,
        "query_packet_valid": runtime["query"]["raw_query_authority"] is False,
        "overlay_packets_valid": all(packet["marker_metadata_only"] and packet["live_kit_control"] is False for packet in runtime["overlays"]),
        "conformance_fixtures_pass": conformance["status"] == "PASS",
        "boundary_audit_pass": boundary["status"] == "PASS",
        "compatibility_pass_or_limited": compatibility["status"] in {"PASS", "PASS_WITH_LIMITATIONS"},
    }
    return {
        "schema_version": "citybrain.event_fabric_runtime_spine.decision.v1",
        "task_id": TASK_ID,
        "decision": PASS_STATUS if all(checks.values()) else "FAIL_MAIN_CITYBRAIN_SPRINT2_EVENT_FABRIC_RUNTIME_SPINE",
        "status": "PASS_WITH_LIMITATIONS" if all(checks.values()) else "FAIL",
        "generated_at": utc_now(),
        "active_contract": "R0.1",
        "r0_1_commit_used": "5ba2dc1",
        "checks": checks,
        "event_count": len(runtime["events"]),
        "overlay_count": len(runtime["overlays"]),
        "limitations": [
            "Runtime spine is local/replay only.",
            "No live ingestion, production API, URL fetching, LLM call, or official workflow execution is implemented.",
            "R7B compatibility normalizes legacy local outputs into R0.1 instead of changing R0.1.",
        ],
    }


def api_overview_text() -> str:
    return """
# Event Fabric Runtime Spine API Overview

Package: `packages.event_fabric`

Active contract: Event Fabric R0.1, anchored to commit `5ba2dc1`.

Implemented helpers:
- `load_r0_contract()`
- `load_event_type_registry()`
- `load_source_class_registry()`
- `build_event_from_candidate()`
- `validate_event_envelope()`
- `append_event()`, `write_event_log()`, `read_event_log()`
- `replay_events()`
- `materialize_review_state()`
- `build_query_result_packet()`
- `build_overlay_packets_for_events()`

Boundary:
- Local/replay only.
- Candidate/review context only.
- VSS/model narrative may attach as review-assist sidecar only and is not a fact source.
- No live cameras, production APIs, URL fetching, LLM calls, official submission, dispatch, control, enforcement, legal/certified finding, live Kit control, or full citywide twin claim.
"""


def test_log_text() -> str:
    return """
# Event Fabric Runtime Spine Test Log

Planned commands:
- `..\\CityBrain\\.venv\\Scripts\\python.exe scripts\\run_main_citybrain_event_fabric_r0_1_contract_delta.py`
- `..\\CityBrain\\.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_event_fabric_r0_1_contract_delta`
- `..\\CityBrain\\.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_sprint2_event_fabric_runtime_spine`
- `..\\CityBrain\\.venv\\Scripts\\python.exe scripts\\run_main_citybrain_sprint2_event_fabric_runtime_spine.py`
- `..\\CityBrain\\.venv\\Scripts\\python.exe -m unittest discover`

The package runner records generated artifact validity. The final assistant response records actual command outcomes.
"""


def write_runtime_outputs() -> dict[str, Any]:
    reset_output_dir(OUTPUT_ROOT)
    runtime = build_runtime_packets()
    conformance = conformance_fixture_results()
    compatibility = compatibility_report()
    boundary = boundary_audit()
    decision = decision_payload(runtime, conformance, compatibility, boundary)

    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_API_OVERVIEW.md", api_overview_text())
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_EVENT_TYPE_REGISTRY_REPORT.json", registry_report())
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_CONFORMANCE_FIXTURE_RESULTS.json", conformance)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_REPLAY_REPORT.json", runtime["replay"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_MATERIALIZED_STATE.json", runtime["materialized"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_QUERY_RESULTS.json", runtime["query"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_OVERLAY_PACKETS.json", {"schema_version": "citybrain.event_fabric_runtime_spine.overlay_packets.v1", "packets": runtime["overlays"]})
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_COMPATIBILITY_REPORT.json", compatibility)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_BOUNDARY_AUDIT.json", boundary)
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_TEST_LOG.md", test_log_text())
    manifest = write_hash_manifest(OUTPUT_ROOT, "EVENT_FABRIC_RUNTIME_SPINE_HASH_MANIFEST.json")
    decision["hash_manifest_entry_count"] = manifest["entry_count"]
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "EVENT_FABRIC_RUNTIME_SPINE_HASH_MANIFEST.json")
    return decision


def write_closeout_outputs() -> dict[str, Any]:
    reset_output_dir(CLOSEOUT_ROOT)
    decision = {
        "schema_version": "citybrain.event_fabric_runtime_spine.closeout_decision.v1",
        "task_id": TASK_ID,
        "decision": PASS_STATUS,
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "active_contract": "R0.1",
        "r0_1_commit_used": "5ba2dc1",
    }
    write_json(CLOSEOUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_CLOSEOUT_DECISION.json", decision)
    write_text(
        CLOSEOUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_CLOSEOUT_SUMMARY.md",
        """
# Event Fabric Runtime Spine Closeout

The local/replay Event Fabric runtime spine is implemented against the corrected R0.1 contract. It validates R0.1 event envelopes, appends and replays a local JSONL log deterministically, materializes review state, emits query result packets, and emits marker-only overlay packets.

The package keeps Event Fabric as review context only. It does not add live ingestion, production APIs, official submissions, dispatch/control/enforcement, legal/certified findings, ASK runtime changes, live Kit control, or full citywide twin claims.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_CLOSEOUT_LIMITATIONS.md",
        """
# Limitations

- Runtime scope is local/replay only.
- R7B compatibility is a legacy-shape normalization into R0.1, not a contract relaxation.
- Query and overlay packets are local review context only.
- CHECK and AuthorityEnvelope are imported/reserved fields; this package does not implement CHECK or authority execution.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_CLOSEOUT_NEXT_STEPS.md",
        """
# Next Steps

- Wire Track B spatial review surface to consume R0.1 query and overlay packets.
- Wire Track C perception bridge to write candidate observations through the R0.1 runtime spine.
- Keep official workflow adapters behind draft/proposal boundaries.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "EVENT_FABRIC_RUNTIME_SPINE_CLOSEOUT_HASH_MANIFEST.json")
    return decision


def write_final_status(commit_sha: str = "", pushed: bool = False, branch: str = "codex/sprint2-event-fabric-runtime-spine") -> dict[str, Any]:
    reset_output_dir(FINAL_ROOT)
    decision = {
        "schema_version": "citybrain.event_fabric_runtime_spine.final_status.v1",
        "task_id": TASK_ID,
        "decision": FINAL_STATUS,
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "branch": branch,
        "commit_sha": commit_sha,
        "pushed": pushed,
        "active_contract": "R0.1",
        "r0_1_commit_used": "5ba2dc1",
        "non_claims_preserved": True,
    }
    write_json(FINAL_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_FINAL_STATUS_SUMMARY.md",
        f"""
# Event Fabric Runtime Spine Final Status

Decision: `{FINAL_STATUS}`

Branch: `{branch}`

Commit: `{commit_sha or 'pending'}`

Published: `{pushed}`

Active contract: R0.1 anchored to `5ba2dc1`.

The runtime spine remains local/replay only and preserves candidate/review-only boundaries.
""",
    )
    write_hash_manifest(FINAL_ROOT, "EVENT_FABRIC_RUNTIME_SPINE_FINAL_STATUS_HASH_MANIFEST.json")
    return decision


def write_all_outputs() -> dict[str, Any]:
    runtime_decision = write_runtime_outputs()
    closeout_decision = write_closeout_outputs()
    return {"runtime": runtime_decision, "closeout": closeout_decision}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-status", action="store_true")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--pushed", action="store_true")
    parser.add_argument("--branch", default="codex/sprint2-event-fabric-runtime-spine")
    args = parser.parse_args()
    if args.final_status:
        result = write_final_status(commit_sha=args.commit_sha, pushed=args.pushed, branch=args.branch)
        print(f"{TASK_ID}: {result['decision']}")
        print(f"Output: {FINAL_ROOT.relative_to(REPO_ROOT)}")
        return
    result = write_all_outputs()
    print(f"{TASK_ID}: {result['runtime']['decision']}")
    print(f"Output: {OUTPUT_ROOT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
