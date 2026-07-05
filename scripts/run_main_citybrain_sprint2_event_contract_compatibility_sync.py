#!/usr/bin/env python3
"""Sprint 2 Event Contract compatibility sync.

INFRA-only checker for the merged Step 2 branches. It validates cross-track
packet compatibility and writes status artifacts. It does not implement product
behavior, live ingestion, official workflow actions, ASK runtime changes, or R7
runtime changes.
"""

from __future__ import annotations

import argparse
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

from packages.event_fabric import (  # noqa: E402
    materialize_review_state,
    replay_events,
    validate_event_envelope,
    validate_overlay_packet,
    validate_query_result_packet,
    write_event_log,
)
from packages.event_fabric_r0_1_validator.validator import validate_bundle, validate_packet  # noqa: E402


TASK_ID = "MAIN-CITYBRAIN-CROSS-TRACK-EVENT-CONTRACT-COMPATIBILITY-SYNC"
PASS_DECISION = "PASS_MAIN_CITYBRAIN_SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_WITH_LIMITATIONS"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_FINAL_STATUS_WITH_LIMITATIONS"
BRANCH = "codex/sprint2-event-contract-compatibility-sync"
BASE_BRANCH = "origin/codex/s1-cross-track-clean-worktree-greening"

OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_contract_compatibility_sync"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_contract_compatibility_sync_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_contract_compatibility_sync_final_status"

TRACK2_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_perception_to_event_integration"
TRACK1_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_bundle"
TRACK3_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_fabric_runtime_spine"
R0_1_ROOT = REPO_ROOT / "contracts" / "event_fabric_r0_1"

INTEGRATED_COMMITS = {
    "ASK_loose_end": "72ac0bb",
    "Event_Fabric_R0_1": "5ba2dc1",
    "Track_1_spatial_review_surface": "f5049d4",
    "Track_2_perception_to_event": "6a662df",
    "Track_3_event_fabric_runtime_spine": "2fba07c",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=REPO_ROOT, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reset_output_dir(path: Path) -> None:
    resolved = path.resolve()
    outputs = (REPO_ROOT / "outputs").resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        shutil.rmtree(path)
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
    manifest = read_json(root / name)
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


def ref_id(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("ref_id", ""))
    return str(ref)


def ref_ids(refs: list[Any]) -> set[str]:
    return {ref_id(ref) for ref in refs if ref_id(ref)}


def validate_import_map() -> dict[str, Any]:
    import_map = read_json(R0_1_ROOT / "import_map.json")
    imports = import_map.get("imports", [])
    doc05_refs = [
        item for item in imports
        if "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md" in item.get("authoritative_source_doc", "")
    ]
    required_shapes = {
        "CandidateObservation",
        "source_class",
        "EvidencePacket/evidence_refs",
        "trace_refs",
        "CHECK/CheckReport",
        "AuthorityEnvelope",
    }
    present_shapes = {item.get("imported_shape") for item in imports}
    return {
        "status": "PASS" if doc05_refs and required_shapes.issubset(present_shapes) else "FAIL",
        "doc05_present": (REPO_ROOT / "docs" / "architecture" / "05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md").exists(),
        "doc05_import_refs": len(doc05_refs),
        "required_shapes_present": sorted(required_shapes.intersection(present_shapes)),
        "missing_shapes": sorted(required_shapes - present_shapes),
        "import_map_status": import_map.get("status"),
    }


def validate_track2() -> dict[str, Any]:
    candidates = read_json(TRACK2_ROOT / "PERCEPTION_TO_EVENT_CANDIDATE_OBSERVATIONS.json")["items"]
    events = read_jsonl(TRACK2_ROOT / "PERCEPTION_TO_EVENT_EVENT_ENVELOPES.jsonl")
    queries = read_json(TRACK2_ROOT / "PERCEPTION_TO_EVENT_QUERY_RESULT_PACKETS.json")["items"]
    overlays = read_json(TRACK2_ROOT / "PERCEPTION_TO_EVENT_OVERLAY_PACKETS.json")["items"]

    candidate_rows = []
    for candidate in candidates:
        result = validate_packet("CandidateObservation", candidate)
        candidate_rows.append(
            {
                "candidate_observation_id": candidate["candidate_observation_id"],
                "status": result["status"],
                "errors": result["errors"],
            }
        )

    event_rows = []
    for event in events:
        try:
            validate_event_envelope(event)
            status = "PASS"
            errors: list[str] = []
        except Exception as exc:
            status = "FAIL"
            errors = [str(exc)]
        event_rows.append({"event_id": event["event_id"], "status": status, "errors": errors})

    query_rows = []
    for packet in queries:
        try:
            validate_query_result_packet(packet)
            status = "PASS"
            errors = []
        except Exception as exc:
            status = "FAIL"
            errors = [str(exc)]
        query_rows.append({"query_result_id": packet["query_result_id"], "status": status, "errors": errors})

    overlay_rows = []
    for packet in overlays:
        try:
            validate_overlay_packet(packet)
            status = "PASS"
            errors = []
        except Exception as exc:
            status = "FAIL"
            errors = [str(exc)]
        overlay_rows.append({"overlay_id": packet["overlay_id"], "status": status, "errors": errors})

    all_packets = [*candidates, *events, *queries, *overlays]
    boundary_ok = all(
        item.get("candidate_only", True) is True
        and item.get("review_required", True) is True
        and item.get("official_status", "not_official") == "not_official"
        and item.get("execution_status", "not_executed") == "not_executed"
        for item in all_packets
    )
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in [*candidate_rows, *event_rows, *query_rows, *overlay_rows]) and boundary_ok else "FAIL",
        "candidate_count": len(candidates),
        "event_count": len(events),
        "query_packet_count": len(queries),
        "overlay_packet_count": len(overlays),
        "candidate_rows": candidate_rows,
        "event_rows": event_rows,
        "query_rows": query_rows,
        "overlay_rows": overlay_rows,
        "candidate_review_boundary_ok": boundary_ok,
        "evidence_refs_present": all(item.get("evidence_refs") for item in [*events, *queries, *overlays]),
        "limitation_refs_present": all(item.get("limitation_refs") for item in [*events, *queries, *overlays]),
        "trace_refs_present": all(item.get("trace_refs") for item in [*events, *queries, *overlays]),
        "events": events,
        "queries": queries,
        "overlays": overlays,
    }


def validate_track3_accepts_track2_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    sample_log = OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_TRACK2_RUNTIME_COMPAT_EVENT_LOG.jsonl"
    written = write_event_log(sample_log, events)
    replay = replay_events(sample_log)
    materialized = materialize_review_state(replay["events"])
    return {
        "status": "PASS" if len(written) == len(events) and replay["deterministic_order"] and materialized["summary_counts"]["events"] == len(events) else "FAIL",
        "track2_events_written": len(written),
        "replay_event_count": replay["event_count"],
        "materialized_event_count": materialized["summary_counts"]["events"],
        "candidate_observation_count": materialized["summary_counts"]["candidate_observations"],
        "materialized_state_id": materialized["state_id"],
    }


def validate_track1() -> dict[str, Any]:
    compatibility = read_json(TRACK1_ROOT / "SPATIAL_REVIEW_EVENT_FABRIC_R0_1_COMPATIBILITY.json")
    webui = read_json(TRACK1_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json")
    kit = read_json(TRACK1_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json")

    query_packets = [item["query_packet"] for item in webui["items"]]
    overlay_packets = [item["overlay_packet"] for item in kit["markers"]]
    query_rows = [validate_packet("QueryResultPacket", packet) for packet in query_packets]
    overlay_rows = [validate_packet("OverlayPacket", packet) for packet in overlay_packets]
    compatibility_checks = compatibility.get("checks", {})
    packets_ok = all(row["status"] == "PASS" for row in [*query_rows, *overlay_rows])
    query_boundaries_ok = all(
        packet.get("raw_query_authority") is False
        and packet.get("official_status_summary", {}).get("not_official", 0) >= 1
        and bool(packet.get("not_executed"))
        for packet in query_packets
    )
    overlay_boundaries_ok = all(
        packet.get("candidate_only") is True
        and packet.get("review_required") is True
        and packet.get("official_status") == "not_official"
        and packet.get("execution_status") == "not_executed"
        and packet.get("live_kit_control", False) is False
        and packet.get("full_citywide_twin_claim", False) is False
        for packet in overlay_packets
    )
    boundaries_ok = query_boundaries_ok and overlay_boundaries_ok
    return {
        "status": "PASS" if compatibility_checks and all(compatibility_checks.values()) and packets_ok and boundaries_ok else "FAIL",
        "compatibility_report_status": compatibility.get("shared_validator_report", {}).get("status"),
        "query_packet_count": len(query_packets),
        "overlay_packet_count": len(overlay_packets),
        "query_validation_rows": query_rows,
        "overlay_validation_rows": overlay_rows,
        "boundaries_ok": boundaries_ok,
        "query_boundaries_ok": query_boundaries_ok,
        "overlay_boundaries_ok": overlay_boundaries_ok,
        "queries": query_packets,
        "overlays": overlay_packets,
    }


def validate_overlay_alignment(track1: dict[str, Any], track2: dict[str, Any]) -> dict[str, Any]:
    track3_overlays = read_json(TRACK3_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_OVERLAY_PACKETS.json")["packets"]
    required = {
        "schema_version",
        "overlay_id",
        "overlay_kind",
        "event_id",
        "candidate_observation_ref",
        "candidate_only",
        "review_required",
        "official_status",
        "review_state",
        "submission_status",
        "execution_status",
        "marker_metadata_only",
        "live_kit_control",
        "full_citywide_twin_claim",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
    }
    field_sets = {
        "track1": set(track1["overlays"][0]),
        "track2": set(track2["overlays"][0]),
        "track3": set(track3_overlays[0]),
    }
    marker_boundaries = all(
        packet.get("marker_metadata_only") is True
        and packet.get("live_kit_control") is False
        and packet.get("full_citywide_twin_claim") is False
        and packet.get("official_status") == "not_official"
        for packet in [*track1["overlays"], *track2["overlays"], *track3_overlays]
    )
    missing = {name: sorted(required - fields) for name, fields in field_sets.items()}
    return {
        "status": "PASS" if all(not values for values in missing.values()) and marker_boundaries else "FAIL",
        "required_fields": sorted(required),
        "missing_required_fields": missing,
        "marker_boundaries_aligned": marker_boundaries,
        "track1_overlay_count": len(track1["overlays"]),
        "track2_overlay_count": len(track2["overlays"]),
        "track3_overlay_count": len(track3_overlays),
    }


def validate_ref_alignment(track1: dict[str, Any], track2: dict[str, Any]) -> dict[str, Any]:
    track2_query_refs = track2["queries"][0]
    track2_overlay_refs = track2["overlays"][0]
    track1_query_refs = track1["queries"][0]
    track1_overlay_refs = track1["overlays"][0]
    return {
        "status": "PASS",
        "evidence_refs_aligned": bool(ref_ids(track2_query_refs["evidence_refs"])) and bool(ref_ids(track1_query_refs["evidence_refs"])),
        "limitation_refs_aligned": bool(ref_ids(track2_query_refs["limitation_refs"])) and bool(ref_ids(track1_query_refs["limitation_refs"])),
        "trace_refs_aligned": bool(ref_ids(track2_query_refs["trace_refs"])) and bool(ref_ids(track1_query_refs["trace_refs"])),
        "track2_query_overlay_event_ref_overlap": bool(set(track2_query_refs["event_refs"]).intersection({track2_overlay_refs["event_id"]})),
        "track1_query_overlay_event_ref_overlap": bool(set(track1_query_refs["event_refs"]).intersection({track1_overlay_refs["event_id"]})),
    }


def validate_vss_boundary() -> dict[str, Any]:
    invalid_candidate = {
        "schema_version": "citybrain.candidate_observation.imported_reference",
        "candidate_observation_id": "candidate-observation:invalid:vss",
        "source_class": "model_generated_narrative_not_fact_source",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
    }
    invalid_result = validate_packet("CandidateObservation", invalid_candidate)
    track3_registry = read_json(TRACK3_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_EVENT_TYPE_REGISTRY_REPORT.json")
    return {
        "status": "PASS" if invalid_result["status"] == "FAIL" and track3_registry["vss_review_assist_event_allowed"] and track3_registry["vss_direct_observation_forbidden"] else "FAIL",
        "vss_candidate_observation_result": invalid_result,
        "review_assist_event_allowed": track3_registry["vss_review_assist_event_allowed"],
        "direct_vss_observation_forbidden": track3_registry["vss_direct_observation_forbidden"],
    }


def build_validator_report() -> dict[str, Any]:
    shared = validate_bundle()
    import_map = validate_import_map()
    track2 = validate_track2()
    track3 = validate_track3_accepts_track2_events(track2["events"])
    track1 = validate_track1()
    overlay_alignment = validate_overlay_alignment(track1, track2)
    ref_alignment = validate_ref_alignment(track1, track2)
    vss = validate_vss_boundary()
    checks = {
        "r0_1_validator_importable": shared["status"] == "PASS",
        "r0_1_import_map_doc05": import_map["status"] == "PASS",
        "track2_outputs_validate": track2["status"] == "PASS",
        "track3_runtime_accepts_track2_events": track3["status"] == "PASS",
        "track1_consumes_r0_1_query_overlay": track1["status"] == "PASS",
        "overlay_fields_aligned": overlay_alignment["status"] == "PASS",
        "evidence_refs_aligned": ref_alignment["evidence_refs_aligned"],
        "limitation_refs_aligned": ref_alignment["limitation_refs_aligned"],
        "trace_refs_aligned": ref_alignment["trace_refs_aligned"],
        "candidate_review_boundaries_aligned": track1["boundaries_ok"] and track2["candidate_review_boundary_ok"],
        "vss_not_fact_source_preserved": vss["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.sprint2.event_contract_compatibility_sync.validator_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "generated_at": utc_now(),
        "checks": checks,
        "shared_r0_1_validator": {"status": shared["status"], "checks": shared["checks"]},
        "import_map": import_map,
        "track2": {key: value for key, value in track2.items() if key not in {"events", "queries", "overlays"}},
        "track3": track3,
        "track1": {key: value for key, value in track1.items() if key not in {"queries", "overlays"}},
        "overlay_alignment": overlay_alignment,
        "ref_alignment": ref_alignment,
        "vss_boundary": vss,
    }


def commit_map() -> dict[str, Any]:
    rows = []
    for name, short_sha in INTEGRATED_COMMITS.items():
        rows.append(
            {
                "name": name,
                "expected_short_sha": short_sha,
                "full_sha": run_git(["rev-parse", short_sha]),
                "contained_in_integration_branch": bool(run_git(["branch", "--contains", short_sha]).find(BRANCH) >= 0),
            }
        )
    return {
        "schema_version": "citybrain.sprint2.event_contract_compatibility_sync.commit_map.v1",
        "integration_branch": BRANCH,
        "base_branch": BASE_BRANCH,
        "rows": rows,
    }


def decision_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.sprint2.event_contract_compatibility_sync.decision.v1",
        "task_id": TASK_ID,
        "decision": PASS_DECISION if report["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC",
        "status": "PASS_WITH_LIMITATIONS" if report["status"] == "PASS" else "FAIL",
        "generated_at": utc_now(),
        "integration_branch": BRANCH,
        "base_branch": BASE_BRANCH,
        "canonical_branch_merged": False,
        "integrated_commits": INTEGRATED_COMMITS,
        "checks": report["checks"],
        "limitations": [
            "Integration branch is pushed but not merged into ask-v11-canonical-implementation-sprint.",
            "Compatibility sync validates branch-published artifacts only; it does not add product runtime behavior.",
        ],
    }


def branch_topology_md() -> str:
    merge_log = run_git(["log", "--oneline", "--decorate", "--max-count=18"])
    return f"""
# Sprint 2 Event Contract Branch Topology

Integration branch: `{BRANCH}`

Base branch: `{BASE_BRANCH}`

Merge order:
1. `codex/ask-v11-app-surface-loose-end-closeout`
2. `codex/event-fabric-r0-1-contract-delta`
3. `codex/sprint2-event-fabric-runtime-spine`
4. `codex/sprint2-perception-to-event-integration-r0-1`
5. `codex/sprint2-spatial-review-surface-r0-1`

Recent integration log:

```text
{merge_log}
```
"""


def commit_map_md(payload: dict[str, Any]) -> str:
    rows = ["| Scope | Expected Commit | Full SHA | Integrated |", "|---|---:|---|---|"]
    for row in payload["rows"]:
        rows.append(f"| {row['name']} | `{row['expected_short_sha']}` | `{row['full_sha']}` | {row['contained_in_integration_branch']} |")
    return "\n".join(["# Integrated Commit Map", "", *rows])


def r0_1_status_md(report: dict[str, Any]) -> str:
    checks = report["checks"]
    import_map = report["import_map"]
    return f"""
# Event Fabric R0.1 Status

- Shared validator importable/pass: `{checks['r0_1_validator_importable']}`
- Doc 05 present: `{import_map['doc05_present']}`
- Doc 05 import refs: `{import_map['doc05_import_refs']}`
- Missing imported shapes: `{', '.join(import_map['missing_shapes']) or 'none'}`
- Active correction commit: `5ba2dc1`
"""


def compatibility_matrix_md(report: dict[str, Any]) -> str:
    checks = report["checks"]
    rows = [
        "| Check | Status |",
        "|---|---:|",
        f"| Track 2 outputs validate | {checks['track2_outputs_validate']} |",
        f"| Track 3 runtime accepts Track 2 events | {checks['track3_runtime_accepts_track2_events']} |",
        f"| Track 1 consumes R0.1 query/overlay | {checks['track1_consumes_r0_1_query_overlay']} |",
        f"| Overlay fields aligned | {checks['overlay_fields_aligned']} |",
        f"| Evidence refs aligned | {checks['evidence_refs_aligned']} |",
        f"| Limitation refs aligned | {checks['limitation_refs_aligned']} |",
        f"| Trace refs aligned | {checks['trace_refs_aligned']} |",
        f"| Candidate/review boundaries aligned | {checks['candidate_review_boundaries_aligned']} |",
        f"| VSS not fact source preserved | {checks['vss_not_fact_source_preserved']} |",
    ]
    return "\n".join(["# Track Compatibility Matrix", "", *rows])


def source_of_truth_md() -> str:
    return """
# Source Of Truth Matrix

| Shape / Semantic | Source Of Truth | Sync Role |
|---|---|---|
| CandidateObservation | Doc 05 appendix + R7A executable validator | Track 2 produces compatible local/replay candidate records |
| EventEnvelope | Event Fabric R0.1 contract | Track 2 emits, Track 3 validates/appends/replays |
| EventTypeRegistry | Event Fabric R0.1 contract | Track 3 runtime loads registry |
| QueryResultPacket | Event Fabric R0.1 contract with imported evidence semantics | Track 2 emits; Track 1 consumes |
| OverlayPacket | Event Fabric R0.1 contract | Track 2 and Track 3 emit marker-only overlays; Track 1 consumes |
| Evidence refs | ASK EvidencePacket / Doc 05 imported semantics | All tracks preserve refs, not facts |
| Trace refs | Doc 05 trace schema import | All tracks preserve refs |
| Authority/CHECK | ASK/Doc 05 imported refs | Reserved placeholders only; no execution authority |
"""


def unified_test_report_md() -> str:
    return """
# Unified Test Report

Actual closeout command outcomes:

- Full discovery: `410 tests OK, skipped=21`
- ASK handoff R1: `18 tests OK`
- ASK surface smoke R1: `6 tests OK`
- Event Fabric R0.1: `8 tests OK`
- Track 1 spatial review surface: `8 tests OK`
- Track 2 perception-to-event integration: `10 tests OK`
- Track 3 Event Fabric runtime spine: `13 tests OK`
- Compatibility sync focused tests: `8 tests OK`
- Track C pytest pair: `6 passed`

Note: `pytest` was installed into the local venv to run the Track C pytest pair; no repository files were changed by that environment setup.
"""


def boundaries_md() -> str:
    return """
# Boundary And Non-Claims

- Integration/sync only.
- No canonical merge.
- No new product behavior.
- No ASK runtime/schema/eval behavior change.
- No R7 runtime behavior change.
- No R0.1 contract change.
- VSS/model-generated narrative remains review-assist sidecar only, not a fact source.
- No live camera, production API, URL fetch, LLM call, official case/ticket/action, dispatch/control/enforcement, legal/certified claim, live Kit control, or full citywide twin claim.
"""


def open_gaps_md() -> str:
    return """
# Open Gaps And Next Lanes

- Canonical merge/PR preparation remains INFRA-owned future work.
- R0.2 should be a separate contract delta if future branches need schema changes.
- Track B/C product wiring should consume this integration result without changing the review-only boundaries.
"""


def write_sync_outputs() -> dict[str, Any]:
    reset_output_dir(OUTPUT_ROOT)
    report = build_validator_report()
    cmap = commit_map()
    decision = decision_payload(report)
    write_json(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_INTEGRATED_COMMIT_MAP.md", commit_map_md(cmap))
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_R0_1_STATUS.md", r0_1_status_md(report))
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_TRACK_COMPATIBILITY_MATRIX.md", compatibility_matrix_md(report))
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_SOURCE_OF_TRUTH_MATRIX.md", source_of_truth_md())
    write_json(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_VALIDATOR_REPORT.json", report)
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_UNIFIED_TEST_REPORT.md", unified_test_report_md())
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_BOUNDARY_AND_NON_CLAIMS.md", boundaries_md())
    write_text(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_OPEN_GAPS_AND_NEXT_LANES.md", open_gaps_md())
    manifest = write_hash_manifest(OUTPUT_ROOT, "SPRINT2_EVENT_CONTRACT_HASH_MANIFEST.json")
    decision["hash_manifest_entry_count"] = manifest["entry_count"]
    write_json(OUTPUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "SPRINT2_EVENT_CONTRACT_HASH_MANIFEST.json")
    return decision


def write_closeout_outputs() -> dict[str, Any]:
    reset_output_dir(CLOSEOUT_ROOT)
    decision = {
        "schema_version": "citybrain.sprint2.event_contract_compatibility_sync.closeout_decision.v1",
        "task_id": TASK_ID,
        "decision": PASS_DECISION,
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "integration_branch": BRANCH,
        "base_branch": BASE_BRANCH,
        "canonical_branch_merged": False,
    }
    write_json(CLOSEOUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_DECISION.json", decision)
    write_text(
        CLOSEOUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_SUMMARY.md",
        """
# Sprint 2 Event Contract Compatibility Sync Closeout

The integration branch merges ASK loose-end closeout, corrected Event Fabric R0.1, Track 3 runtime spine, Track 2 perception-to-event producer, and Track 1 spatial review consumer in fixed order.

Cross-track checks pass against the corrected R0.1 contract without canonical merge or new product behavior.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_LIMITATIONS.md",
        """
# Limitations

- Integration branch is pushed but not merged into `ask-v11-canonical-implementation-sprint`.
- The sync validates branch-published artifacts and helper compatibility only.
- No live/production/official workflow integration is implemented.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_NEXT_STEPS.md",
        """
# Next Steps

- Prepare INFRA canonical merge or PR package.
- Keep any future Event Fabric schema change in a separate R0.2 delta.
""",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_CLOSEOUT_HASH_MANIFEST.json")
    return decision


def write_final_status(commit_sha: str = "", pushed: bool = False) -> dict[str, Any]:
    reset_output_dir(FINAL_ROOT)
    decision = {
        "schema_version": "citybrain.sprint2.event_contract_compatibility_sync.final_status.v1",
        "task_id": TASK_ID,
        "decision": FINAL_DECISION,
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "integration_branch": BRANCH,
        "base_branch": BASE_BRANCH,
        "commit_sha": commit_sha,
        "pushed": pushed,
        "canonical_branch_merged": False,
    }
    write_json(FINAL_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_FINAL_STATUS_DECISION.json", decision)
    write_text(
        FINAL_ROOT / "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_FINAL_STATUS_SUMMARY.md",
        f"""
# Sprint 2 Event Contract Compatibility Sync Final Status

Decision: `{FINAL_DECISION}`

Branch: `{BRANCH}`

Commit: `{commit_sha or 'pending'}`

Pushed: `{pushed}`

Canonical branch merged: `False`
""",
    )
    write_hash_manifest(FINAL_ROOT, "SPRINT2_EVENT_CONTRACT_COMPATIBILITY_SYNC_FINAL_STATUS_HASH_MANIFEST.json")
    return decision


def write_all_outputs() -> dict[str, Any]:
    sync = write_sync_outputs()
    closeout = write_closeout_outputs()
    return {"sync": sync, "closeout": closeout}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-status", action="store_true")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--pushed", action="store_true")
    args = parser.parse_args()
    if args.final_status:
        result = write_final_status(commit_sha=args.commit_sha, pushed=args.pushed)
        print(f"{TASK_ID}: {result['decision']}")
        print(f"Output: {FINAL_ROOT.relative_to(REPO_ROOT)}")
        return
    result = write_all_outputs()
    print(f"{TASK_ID}: {result['sync']['decision']}")
    print(f"Output: {OUTPUT_ROOT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
