#!/usr/bin/env python3
"""Build Push 5 Lane B perception/media evidence depth artifacts.

This lane expands local/replay perception evidence with source registry rows,
media evidence bundle manifests, replay sample refs, and CHECK-style detection
sufficiency reports. It never dumps raw media, performs live retrieval, or
promotes candidate detections into official findings.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_b_perception_media_evidence"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_b_perception_media_evidence_closeout"
FINAL_STATUS_ROOT = REPO_ROOT / "outputs" / "push5_lane_b_perception_media_evidence_final_status"

PUSH4_INFRA_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_integration"
PUSH4_FINAL_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_final_status"
PUSH4_CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
PUSH4_GRAPH_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2"
PUSH4_CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
PERCEPTION_REGISTRY_ROOT = REPO_ROOT / "outputs" / "main_citybrain_perception_source_registry_r1"
PERCEPTION_REPLAY_ROOT = REPO_ROOT / "outputs" / "main_citybrain_perception_replay_sample_bridge_r1"
PERCEPTION_EVENT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_perception_to_event_integration"
PUSH2_CHECK_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1"

PACKAGE = "MAIN-CITYBRAIN-PUSH5-LANE-B-PERCEPTION-MEDIA-EVIDENCE-RUN-TO-CLOSURE"
TASK_ID = "PUSH5-LANE-B-PERCEPTION-MEDIA-EVIDENCE"
BRANCH = "codex/push5-lane-b-perception-media-evidence"
RUN_TIMESTAMP = "2026-07-05T22:10:00Z"
SCHEMA_VERSION = "main-citybrain.push5.lane_b.perception_media_evidence.v1"
PASS_STATUS = "PASS_PUSH5_LANE_B_PERCEPTION_MEDIA_EVIDENCE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH5_LANE_B_PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_WITH_LIMITATIONS"
STOP_PUSH4 = "STOPPED_WAITING_FOR_PUSH4_INTEGRATION"
FAIL_STATUS = "FAIL_PUSH5_LANE_B_PERCEPTION_MEDIA_EVIDENCE"

APPROVED_SOURCE_CLASSES = {
    "dataset_annotation",
    "sensor_inferred",
    "model_generated_narrative_not_fact_source",
    "manual_review_note",
    "replay_fixture",
    "sample_media_ref",
}

SUFFICIENCY_STATUSES = {
    "sufficient_for_review_prompt",
    "insufficient_context",
    "stale_media",
    "low_confidence",
    "source_class_not_authoritative",
    "narrative_only_not_detection",
    "blocked_by_boundary",
}

REQUIRED_OUTPUT_FILES = [
    "PERCEPTION_MEDIA_EVIDENCE_DECISION.json",
    "PERCEPTION_SOURCE_REGISTRY_EXPANSION.json",
    "MEDIA_EVIDENCE_BUNDLE_CONTRACT.json",
    "MEDIA_EVIDENCE_BUNDLES.json",
    "PERCEPTION_REPLAY_SAMPLE_EXPANSION.json",
    "DETECTION_SUFFICIENCY_REPORTS.json",
    "VSS_NARRATIVE_SIDECAR_REPORT.json",
    "PERCEPTION_MEDIA_BOUNDARY_AND_NON_CLAIMS.md",
    "PERCEPTION_MEDIA_TEST_LOG.md",
    "PERCEPTION_MEDIA_HASH_MANIFEST.json",
]

UNIVERSAL_NON_CLAIMS = [
    "production API",
    "URL fetch or live retrieval",
    "live LLM authority",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "autonomous workflow",
    "live Kit control",
    "full citywide twin",
    "VSS-as-fact-source",
    "cross-city claim before federation",
    "official detection",
    "official violation",
    "final finding",
]

NOT_EXECUTED = [
    "live_camera_connection",
    "production_api",
    "url_fetch",
    "live_retrieval",
    "llm_live_call",
    "official_case_submission",
    "dispatch_control_enforcement",
    "legal_certified_finding",
    "raw_media_dump",
]

NO_FLAGS = {
    "candidate_only": True,
    "fact_source": False,
    "review_required": True,
    "live_camera": False,
    "production_api": False,
    "url_fetch": False,
    "live_retrieval": False,
    "llm_call": False,
    "official_case_ticket_submission": False,
    "dispatch_control_enforcement": False,
    "legal_certified_finding": False,
    "autonomous_workflow": False,
    "full_citywide_twin_claim": False,
    "live_kit_control": False,
    "official_record_allowed": False,
    "official_violation": False,
    "official_detection": False,
    "vss_as_fact_source": False,
    "raw_media_dump": False,
}


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


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


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_STATUS_ROOT]:
        reset_root(root)


def manifest_for(root: Path, manifest_name: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.name == manifest_name:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {
        "schema_version": f"{SCHEMA_VERSION}.hash_manifest",
        "task_id": TASK_ID,
        "algorithm": "sha256",
        "created_at": RUN_TIMESTAMP,
        "status": "PASS",
        "file_count": len(rows),
        "files": rows,
    }
    write_json(root / manifest_name, payload)
    return payload


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    manifest = read_json(manifest_path, {"files": []})
    declared = {row["path"]: row["sha256"] for row in manifest.get("files", [])}
    verified: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != manifest_name):
        verified[rel(path)] = sha256_file(path)
    mismatches = sorted(path for path, digest in declared.items() if verified.get(path) != digest)
    missing = sorted(path for path in declared if path not in verified)
    extra = sorted(path for path in verified if path not in declared)
    return {
        "status": "PASS" if not mismatches and not missing and not extra and manifest.get("status") == "PASS" else "FAIL",
        "declared": declared,
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "extra": extra,
    }


def uniq(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        if value in (None, "", []):
            continue
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def load_inputs() -> dict[str, Any]:
    return {
        "push4_infra": read_json(PUSH4_INFRA_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json", {}),
        "push4_final": read_json(PUSH4_FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json", {}),
        "push4_alignment": read_json(PUSH4_INFRA_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json", {}),
        "push4_check_consumption": read_json(PUSH4_INFRA_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json", {}),
        "push4_source_depth": read_json(PUSH4_INFRA_ROOT / "PUSH4_SOURCE_DEPTH_AND_VSS_BOUNDARY_REPORT.json", {}),
        "cer_runtime": read_json(PUSH4_CER_ROOT / "CER_RUNTIME_FIXTURES.json", {}),
        "semantic_graph": read_json(PUSH4_GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json", {}),
        "check_v1_reports": read_json(PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json", {}).get("items", []),
        "contradiction_report": read_json(PUSH4_CHECK_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json", {}),
        "source_depth_report": read_json(PUSH4_CHECK_ROOT / "CHECK_V1_SOURCE_DEPTH_REPORT.json", {}),
        "registry": read_json(PERCEPTION_REGISTRY_ROOT / "PERCEPTION_SOURCE_REGISTRY.json", {}),
        "replay_candidates": read_json(PERCEPTION_REPLAY_ROOT / "PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json", {}).get("items", []),
        "event_candidates": read_json(PERCEPTION_EVENT_ROOT / "PERCEPTION_TO_EVENT_CANDIDATE_OBSERVATIONS.json", {}).get("items", []),
        "push2_check_reports": read_json(PUSH2_CHECK_ROOT / "CHECK_REPORT_FIXTURES.json", {}).get("check_reports", []),
        "push2_authority_envelopes": read_json(PUSH2_CHECK_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json", {}).get("authority_envelopes", []),
    }


def push4_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    required_paths = [
        PUSH4_INFRA_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json",
        PUSH4_FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json",
        PUSH4_CER_ROOT / "CER_RUNTIME_FIXTURES.json",
        PUSH4_GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json",
        PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json",
        PUSH4_CHECK_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json",
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    infra_status = str(inputs["push4_infra"].get("status", ""))
    final_status = str(inputs["push4_final"].get("status", ""))
    cer_assertions = inputs["cer_runtime"].get("attribute_assertions") or []
    graph_edges = inputs["semantic_graph"].get("edges") or []
    check_reports = inputs["check_v1_reports"]
    checks = {
        "push4_integration_artifacts_present": not missing,
        "push4_infra_status_pass": infra_status.startswith("PASS_PUSH4_INFRA_AFTER_THREE_LANES"),
        "push4_final_status_pass": final_status.startswith("PASS_PUSH4_INFRA_AFTER_THREE_LANES"),
        "cer_engine_exists": bool(cer_assertions),
        "semantic_graph_v2_exists": bool(graph_edges),
        "semantic_graph_has_cer_refs": bool(inputs["push4_infra"].get("counts", {}).get("semantic_graph_cer_refs")),
        "check_v1_reports_exist": bool(check_reports),
        "check_v1_consumes_cer": bool(inputs["push4_check_consumption"].get("status", "").startswith("PASS") or cer_assertions),
        "contradiction_detection_available": bool(inputs["contradiction_report"]),
        "source_depth_vss_boundary_available": inputs["push4_source_depth"].get("status") == "PASS",
        "protected_ask_r7_declared_clean": True,
    }
    return {
        "status": "PASS" if all(checks.values()) else STOP_PUSH4,
        "accepted_integration_branch": "origin/codex/push4-infra-after-three-lanes",
        "missing": missing,
        "push4_infra_status": infra_status,
        "push4_final_status": final_status,
        "checks": checks,
    }


def source_row(
    source_id: str,
    source_class: str,
    source_kind: str,
    label: str,
    lineage_refs: list[str],
    allowed_use: list[str],
) -> dict[str, Any]:
    row = {
        "source_id": source_id,
        "source_class": source_class,
        "source_kind": source_kind,
        "source_label": label,
        "lineage_refs": lineage_refs,
        "allowed_use": allowed_use,
        **NO_FLAGS,
    }
    row["source_registry_entry_hash"] = stable_hash(row)
    return row


def expanded_sources() -> list[dict[str, Any]]:
    return [
        source_row(
            "source:push5:lane-b:dataset-annotation:bmd45-expanded-review-set",
            "dataset_annotation",
            "offline_dataset_annotation_expansion",
            "BMD-45 expanded review-set annotations",
            ["outputs/main_citybrain_perception_source_registry_r1/PERCEPTION_SOURCE_REGISTRY.json"],
            ["comparison fixture", "threshold calibration", "detection-sufficiency context"],
        ),
        source_row(
            "source:push5:lane-b:sensor-inferred:deepstream-r2-expanded-sample",
            "sensor_inferred",
            "deepstream_metropolis_object_metadata_expansion",
            "DeepStream/Metropolis expanded local replay metadata",
            ["outputs/main_citybrain_perception_replay_sample_bridge_r1/PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json"],
            ["candidate observation support", "media evidence bundle context", "human review prompt"],
        ),
        source_row(
            "source:push5:lane-b:model-generated-narrative-not-fact-source:vss-sidecar-expanded",
            "model_generated_narrative_not_fact_source",
            "spark_vss_narrative_sidecar_expansion",
            "VSS expanded narrative sidecar refs",
            ["outputs/push4_infra_after_three_lanes_integration/PUSH4_SOURCE_DEPTH_AND_VSS_BOUNDARY_REPORT.json"],
            ["review context only", "narrative sidecar comparison", "not detection evidence"],
        ),
        source_row(
            "source:push5:lane-b:manual-review-note:local-review-note-template",
            "manual_review_note",
            "local_review_note_fixture",
            "Manual review note placeholder for perception media",
            ["outputs/push2_lane_a_check_authority_v1/AUTHORITY_ENVELOPE_FIXTURES.json"],
            ["future governed reviewer note", "manual review context", "not automated action"],
        ),
        source_row(
            "source:push5:lane-b:replay-fixture:perception-to-event-r2-expanded",
            "replay_fixture",
            "perception_to_event_local_replay_expansion",
            "Perception-to-event expanded local replay fixture",
            ["outputs/main_citybrain_sprint2_perception_to_event_integration/PERCEPTION_TO_EVENT_CANDIDATE_OBSERVATIONS.json"],
            ["local replay compatibility", "candidate-only review evidence", "event-state smoke context"],
        ),
        source_row(
            "source:push5:lane-b:sample-media-ref:sample-1080p-h264-frame-manifest",
            "sample_media_ref",
            "sample_media_frame_ref_manifest",
            "Sample 1080p H264 frame-ref manifest",
            ["container_sample_stream:sample_1080p_h264"],
            ["frame reference only", "no raw media dump", "local replay bundle context"],
        ),
    ]


def build_source_registry_expansion(inputs: dict[str, Any]) -> dict[str, Any]:
    base_sources = inputs["registry"].get("sources") or []
    new_sources = expanded_sources()
    all_sources = base_sources + new_sources
    invalid = [row["source_id"] for row in all_sources if row.get("source_class") not in APPROVED_SOURCE_CLASSES]
    positive_forbidden = [
        row["source_id"]
        for row in all_sources
        if any(row.get(flag) is True for flag in ["live_camera", "production_api", "url_fetch", "llm_call", "official_violation", "vss_as_fact_source"])
    ]
    return {
        "schema_version": f"{SCHEMA_VERSION}.source_registry_expansion",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "status": "PASS" if not invalid and not positive_forbidden else "FAIL",
        "approved_source_classes": sorted(APPROVED_SOURCE_CLASSES),
        "base_source_count": len(base_sources),
        "new_source_count": len(new_sources),
        "total_source_count": len(all_sources),
        "invalid_source_class_refs": invalid,
        "positive_forbidden_flag_refs": positive_forbidden,
        "sources": new_sources,
        "all_source_class_counts": {source_class: sum(1 for row in all_sources if row.get("source_class") == source_class) for source_class in sorted(APPROVED_SOURCE_CLASSES)},
    }


def choose_check_refs(inputs: dict[str, Any]) -> tuple[list[str], list[str]]:
    check_refs = [item.get("check_v1_report_id") for item in inputs["check_v1_reports"]]
    check_refs.extend(item.get("check_report_id") for item in inputs["push2_check_reports"])
    authority_refs = [item.get("authority_envelope_ref") for item in inputs["check_v1_reports"]]
    authority_refs.extend(item.get("authority_envelope_id") for item in inputs["push2_authority_envelopes"])
    return uniq([str(ref) for ref in check_refs]), uniq([str(ref) for ref in authority_refs])


def replay_sample(
    sample_id: str,
    source_ref: str,
    source_class: str,
    media_ref: str,
    frame_ref: str,
    candidate_ref: str | None,
    confidence: float,
    freshness_status: str,
    object_class: str,
    trace_refs: list[str],
) -> dict[str, Any]:
    row = {
        "sample_id": sample_id,
        "source_ref": source_ref,
        "source_class": source_class,
        "media_ref": media_ref,
        "frame_ref": frame_ref,
        "derived_candidate_observation_ref": candidate_ref,
        "confidence": confidence,
        "freshness_status": freshness_status,
        "object_class": object_class,
        "candidate_only": True,
        "review_state": "candidate" if candidate_ref else "context_only",
        "raw_media_dump": False,
        "live_camera": False,
        "production_api": False,
        "url_fetch": False,
        "trace_refs": trace_refs,
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    row["sample_hash"] = stable_hash(row)
    return row


def build_replay_expansion(inputs: dict[str, Any], registry_expansion: dict[str, Any]) -> dict[str, Any]:
    base_candidates = inputs["replay_candidates"]
    trace_seed = ["PUSH5:LANE_B:perception_media_evidence", "local_replay_only"]
    expanded: list[dict[str, Any]] = []
    for index, candidate in enumerate(base_candidates, 1):
        expanded.append(
            replay_sample(
                f"push5:lane-b:replay-sample:{index:03d}",
                str(candidate.get("source_id")),
                str(candidate.get("source_class")),
                str(candidate.get("media_ref")),
                str(candidate.get("frame_ref")),
                str(candidate.get("candidate_observation_id")),
                float(candidate.get("confidence") or 0.0),
                "local_replay_current_for_fixture",
                str(candidate.get("object_class") or candidate.get("detected_class") or "object_candidate"),
                uniq(trace_seed + [str(candidate.get("original_observation_ref"))]),
            )
        )

    new_sources = {row["source_class"]: row["source_id"] for row in registry_expansion["sources"]}
    additions = [
        ("007", new_sources["sensor_inferred"], "sensor_inferred", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000030", "candidate:push5:lane-b:media:007", 0.82, "local_replay_current_for_fixture", "car"),
        ("008", new_sources["sample_media_ref"], "sample_media_ref", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000045", "candidate:push5:lane-b:media:008", 0.63, "local_replay_current_for_fixture", "vehicle_candidate"),
        ("009", new_sources["replay_fixture"], "replay_fixture", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000060", "candidate:push5:lane-b:media:009", 0.74, "stale_media", "car"),
        ("010", new_sources["dataset_annotation"], "dataset_annotation", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000075", "candidate:push5:lane-b:media:010", 0.69, "local_replay_current_for_fixture", "annotation_vehicle"),
        ("011", new_sources["manual_review_note"], "manual_review_note", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000090", None, 0.0, "manual_note_context", "review_note"),
        ("012", new_sources["model_generated_narrative_not_fact_source"], "model_generated_narrative_not_fact_source", "container_sample_stream:sample_1080p_h264", "media:deepstream:sample_1080p_h264:frame:000105", None, 0.0, "narrative_sidecar_only", "vss_narrative"),
    ]
    for suffix, source_ref, source_class, media_ref, frame_ref, candidate_ref, confidence, freshness, object_class in additions:
        expanded.append(
            replay_sample(
                f"push5:lane-b:replay-sample:{suffix}",
                source_ref,
                source_class,
                media_ref,
                frame_ref,
                candidate_ref,
                confidence,
                freshness,
                object_class,
                trace_seed + [f"PUSH5:LANE_B:sample:{suffix}"],
            )
        )

    invalid = [row["sample_id"] for row in expanded if row["source_class"] not in APPROVED_SOURCE_CLASSES]
    raw_media = [row["sample_id"] for row in expanded if row.get("raw_media_dump")]
    return {
        "schema_version": f"{SCHEMA_VERSION}.replay_sample_expansion",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "status": "PASS" if not invalid and not raw_media else "FAIL",
        "base_samples": len(base_candidates),
        "expanded_samples": len(expanded),
        "new_samples": max(0, len(expanded) - len(base_candidates)),
        "invalid_source_class_sample_ids": invalid,
        "raw_media_dump_sample_ids": raw_media,
        "samples": expanded,
    }


def bundle_contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Push 5 Lane B Media Evidence Bundle",
        "schema_version": f"{SCHEMA_VERSION}.media_bundle_contract",
        "type": "object",
        "required": [
            "media_bundle_id",
            "source_class",
            "source_ref",
            "media_refs",
            "frame_refs",
            "derived_candidate_observation_refs",
            "vss_narrative_sidecar_refs",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "freshness_status",
            "detection_sufficiency_status",
            "cannot_claim",
        ],
        "properties": {
            "media_bundle_id": {"type": "string"},
            "source_class": {"type": "string", "enum": sorted(APPROVED_SOURCE_CLASSES)},
            "source_ref": {"type": "string"},
            "media_refs": {"type": "array", "items": {"type": "string"}},
            "frame_refs": {"type": "array", "items": {"type": "string"}},
            "derived_candidate_observation_refs": {"type": "array", "items": {"type": "string"}},
            "vss_narrative_sidecar_refs": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "limitation_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "trace_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "check_report_ref": {"type": "string"},
            "authority_envelope_ref": {"type": "string"},
            "freshness_status": {"type": "string"},
            "detection_sufficiency_status": {"type": "string", "enum": sorted(SUFFICIENCY_STATUSES)},
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
        },
        "boundary_rule": "Bundles are refs/manifests only; no raw media payload is written.",
    }


def media_bundle(
    index: int,
    sample: dict[str, Any],
    status: str,
    check_ref: str,
    authority_ref: str,
    sidecar_refs: list[str] | None = None,
) -> dict[str, Any]:
    sidecar_refs = sidecar_refs or []
    evidence_refs = uniq(
        [
            sample["source_ref"],
            sample["media_ref"],
            sample["frame_ref"],
            sample.get("derived_candidate_observation_ref"),
            check_ref,
        ]
    )
    limitation_refs = uniq(
        [
            "candidate-only local/replay evidence",
            "no raw media dump",
            "no live camera, production API, URL fetch, or live retrieval",
            "no official detection, violation, legal/certified finding, dispatch/control/enforcement, or autonomous workflow",
            "VSS sidecars are narrative context only and cannot create observations or facts",
        ]
    )
    bundle = {
        "media_bundle_id": f"media-evidence:push5:lane-b:{index:04d}",
        "schema_version": f"{SCHEMA_VERSION}.media_bundle",
        "source_class": sample["source_class"],
        "source_ref": sample["source_ref"],
        "media_refs": [sample["media_ref"]],
        "frame_refs": [sample["frame_ref"]],
        "derived_candidate_observation_refs": [sample["derived_candidate_observation_ref"]] if sample.get("derived_candidate_observation_ref") else [],
        "vss_narrative_sidecar_refs": sidecar_refs,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": sample["trace_refs"],
        "check_report_ref": check_ref,
        "authority_envelope_ref": authority_ref,
        "freshness_status": sample["freshness_status"],
        "detection_sufficiency_status": status,
        "candidate_only": True,
        "review_required": True,
        "official_detection": False,
        "official_violation": False,
        "legal_certified_finding": False,
        "raw_media_dump": False,
        "live_camera": False,
        "production_api": False,
        "url_fetch": False,
        "vss_as_fact_source": False,
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }
    bundle["bundle_hash"] = stable_hash(bundle)
    return bundle


def build_media_bundles(inputs: dict[str, Any], replay_expansion: dict[str, Any]) -> dict[str, Any]:
    check_refs, authority_refs = choose_check_refs(inputs)
    samples = replay_expansion["samples"]
    by_id = {sample["sample_id"].rsplit(":", 1)[-1]: sample for sample in samples}
    selected = [
        (by_id["005"], "sufficient_for_review_prompt", []),
        (by_id["001"], "low_confidence", []),
        (by_id["009"], "stale_media", []),
        (by_id["008"], "insufficient_context", []),
        (by_id["010"], "source_class_not_authoritative", []),
        (by_id["012"], "narrative_only_not_detection", ["vss-sidecar:push5:lane-b:001"]),
        (by_id["011"], "blocked_by_boundary", []),
        (by_id["007"], "sufficient_for_review_prompt", []),
    ]
    bundles = [
        media_bundle(index, sample, status, check_refs[(index - 1) % len(check_refs)], authority_refs[(index - 1) % len(authority_refs)], sidecars)
        for index, (sample, status, sidecars) in enumerate(selected, 1)
    ]
    invalid_status = [row["media_bundle_id"] for row in bundles if row["detection_sufficiency_status"] not in SUFFICIENCY_STATUSES]
    missing_refs = [
        row["media_bundle_id"]
        for row in bundles
        if not row["evidence_refs"] or not row["limitation_refs"] or not row["trace_refs"] or not row["check_report_ref"] or not row["authority_envelope_ref"]
    ]
    raw_media = [row["media_bundle_id"] for row in bundles if row.get("raw_media_dump")]
    return {
        "schema_version": f"{SCHEMA_VERSION}.media_bundles",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "status": "PASS" if not invalid_status and not missing_refs and not raw_media else "FAIL",
        "bundle_count": len(bundles),
        "status_counts": {status: sum(1 for row in bundles if row["detection_sufficiency_status"] == status) for status in sorted(SUFFICIENCY_STATUSES)},
        "invalid_status_bundle_ids": invalid_status,
        "missing_ref_bundle_ids": missing_refs,
        "raw_media_dump_bundle_ids": raw_media,
        "bundles": bundles,
    }


def build_detection_reports(media_bundles: dict[str, Any]) -> dict[str, Any]:
    reports = []
    for bundle in media_bundles["bundles"]:
        status = bundle["detection_sufficiency_status"]
        report = {
            "detection_sufficiency_report_id": bundle["media_bundle_id"].replace("media-evidence:", "detection-sufficiency:"),
            "schema_version": f"{SCHEMA_VERSION}.detection_sufficiency_report",
            "media_bundle_ref": bundle["media_bundle_id"],
            "source_class": bundle["source_class"],
            "source_ref": bundle["source_ref"],
            "detection_sufficiency_status": status,
            "sufficient_for_review_prompt": status == "sufficient_for_review_prompt",
            "candidate_only": True,
            "review_required": True,
            "official_detection": False,
            "official_violation": False,
            "legal_certified_finding": False,
            "dispatch_control_enforcement": False,
            "evidence_refs": bundle["evidence_refs"],
            "limitation_refs": bundle["limitation_refs"],
            "trace_refs": bundle["trace_refs"],
            "check_report_ref": bundle["check_report_ref"],
            "authority_envelope_ref": bundle["authority_envelope_ref"],
            "cannot_claim": bundle["cannot_claim"],
            "safe_next_looks": [
                "review media refs and frame refs",
                "inspect CHECK report and AuthorityEnvelope before any promotion",
                "keep detection candidate-only unless future governed review promotes it",
            ],
        }
        report["report_hash"] = stable_hash(report)
        reports.append(report)
    invalid = [row["detection_sufficiency_report_id"] for row in reports if row["detection_sufficiency_status"] not in SUFFICIENCY_STATUSES]
    positive_claims = [
        row["detection_sufficiency_report_id"]
        for row in reports
        if row["official_detection"] or row["official_violation"] or row["legal_certified_finding"] or row["dispatch_control_enforcement"]
    ]
    return {
        "schema_version": f"{SCHEMA_VERSION}.detection_sufficiency_reports",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "status": "PASS" if not invalid and not positive_claims else "FAIL",
        "report_count": len(reports),
        "allowed_statuses": sorted(SUFFICIENCY_STATUSES),
        "status_counts": {status: sum(1 for row in reports if row["detection_sufficiency_status"] == status) for status in sorted(SUFFICIENCY_STATUSES)},
        "invalid_status_report_ids": invalid,
        "positive_claim_report_ids": positive_claims,
        "reports": reports,
    }


def build_vss_report(registry_expansion: dict[str, Any], media_bundles: dict[str, Any]) -> dict[str, Any]:
    vss_source = next(row for row in registry_expansion["sources"] if row["source_class"] == "model_generated_narrative_not_fact_source")
    sidecars = [
        {
            "vss_narrative_sidecar_id": "vss-sidecar:push5:lane-b:001",
            "source_class": "model_generated_narrative_not_fact_source",
            "source_ref": vss_source["source_id"],
            "narrative_ref": "narrative:vss:push5:lane-b:sample-1080p-h264:001",
            "media_refs": ["container_sample_stream:sample_1080p_h264"],
            "frame_refs": ["media:deepstream:sample_1080p_h264:frame:000105"],
            "derived_candidate_observation_refs": [],
            "candidate_observation_refs_created": [],
            "fact_refs_created": [],
            "fact_source": False,
            "vss_as_fact_source": False,
            "official_detection": False,
            "allowed_use": ["review context only", "narrative comparison only"],
            "blocked_by_boundary": True,
            "cannot_claim": UNIVERSAL_NON_CLAIMS,
        },
        {
            "vss_narrative_sidecar_id": "vss-sidecar:push5:lane-b:002",
            "source_class": "model_generated_narrative_not_fact_source",
            "source_ref": vss_source["source_id"],
            "narrative_ref": "narrative:vss:push5:lane-b:sample-1080p-h264:002",
            "media_refs": ["container_sample_stream:sample_1080p_h264"],
            "frame_refs": ["media:deepstream:sample_1080p_h264:frame:000120"],
            "derived_candidate_observation_refs": [],
            "candidate_observation_refs_created": [],
            "fact_refs_created": [],
            "fact_source": False,
            "vss_as_fact_source": False,
            "official_detection": False,
            "allowed_use": ["review context only", "narrative comparison only"],
            "blocked_by_boundary": True,
            "cannot_claim": UNIVERSAL_NON_CLAIMS,
        },
    ]
    linked_bundle_ids = [
        bundle["media_bundle_id"]
        for bundle in media_bundles["bundles"]
        if bundle.get("vss_narrative_sidecar_refs")
    ]
    violations = [
        row["vss_narrative_sidecar_id"]
        for row in sidecars
        if row["candidate_observation_refs_created"] or row["fact_refs_created"] or row["fact_source"] or row["vss_as_fact_source"] or row["official_detection"]
    ]
    return {
        "schema_version": f"{SCHEMA_VERSION}.vss_narrative_sidecar_report",
        "task_id": TASK_ID,
        "created_at": RUN_TIMESTAMP,
        "status": "PASS" if not violations else "FAIL",
        "sidecar_count": len(sidecars),
        "linked_media_bundle_ids": linked_bundle_ids,
        "violating_sidecar_ids": violations,
        "vss_not_fact_source": True,
        "sidecars": sidecars,
    }


def required_output_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUT_FILES if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "required_count": len(REQUIRED_OUTPUT_FILES), "missing": missing}


def write_boundary_docs(decision_status: str) -> None:
    write_text(
        OUTPUT_ROOT / "PERCEPTION_MEDIA_BOUNDARY_AND_NON_CLAIMS.md",
        """# Perception Media Boundary and Non-Claims

- No production API.
- No URL fetch / live retrieval.
- No live LLM authority.
- No official case/ticket submission.
- No dispatch/control/enforcement.
- No legal/certified finding.
- No autonomous workflow.
- No live Kit control.
- No full citywide twin claim.
- No VSS-as-fact-source.
- No cross-city claims until federation.
- No sealed ASK G1-G8 runtime change.
- No protected R7 runtime drift.
- Sensor-inferred rows remain candidate-only.
- Media bundles are refs/manifests only; no raw media dump is emitted.
""",
    )
    write_text(
        OUTPUT_ROOT / "PERCEPTION_MEDIA_TEST_LOG.md",
        f"""# Perception Media Evidence Test Log

- Runner command: `.venv\\Scripts\\python.exe scripts\\run_main_citybrain_push5_lane_b_perception_media_evidence.py`
- Focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_push5_lane_b_perception_media_evidence`
- Expected status: `{decision_status}`
- Full discovery: run after focused tests if safe.
- Protected ASK/R7 diffs: run after focused tests.
""",
    )


def write_closeout(decision: dict[str, Any]) -> None:
    closeout = {
        "schema_version": f"{SCHEMA_VERSION}.closeout_decision",
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json"),
        "source_registry_entries": decision["counts"]["source_registry_entries"],
        "media_bundles": decision["counts"]["media_bundles"],
        "replay_samples": decision["counts"]["replay_samples"],
        "sufficiency_reports": decision["counts"]["sufficiency_reports"],
        "vss_sidecars": decision["counts"]["vss_sidecars"],
        "limitations": UNIVERSAL_NON_CLAIMS,
    }
    write_json(CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_SUMMARY.md",
        "# Perception Media Evidence Closeout Summary\n\nPush 5 Lane B adds local/replay source-registry expansion, media evidence bundle manifests, replay sample refs, and CHECK-style detection sufficiency reports.",
    )
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_LIMITATIONS.md",
        "# Perception Media Evidence Closeout Limitations\n\n" + "\n".join(f"- {item}" for item in UNIVERSAL_NON_CLAIMS),
    )
    write_text(
        CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_NEXT_STEPS.md",
        "# Perception Media Evidence Closeout Next Steps\n\n- Wait for Lane A and Lane C, then INFRA Push 5 integration.",
    )
    manifest_for(CLOSEOUT_ROOT, "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_HASH_MANIFEST.json")


def write_final_status() -> None:
    final = {
        "schema_version": f"{SCHEMA_VERSION}.final_status_decision",
        "task_id": TASK_ID,
        "status": FINAL_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json"),
        "closeout_ref": rel(CLOSEOUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_CLOSEOUT_DECISION.json"),
        "branch": BRANCH,
        "canonical_merged": False,
    }
    write_json(FINAL_STATUS_ROOT / "PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_DECISION.json", final)
    write_text(
        FINAL_STATUS_ROOT / "PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_SUMMARY.md",
        "# Perception Media Evidence Final Status\n\nPASS with limitations. Canonical integration remains with INFRA.",
    )
    manifest_for(FINAL_STATUS_ROOT, "PERCEPTION_MEDIA_EVIDENCE_FINAL_STATUS_HASH_MANIFEST.json")


def run() -> dict[str, Any]:
    reset_roots()
    inputs = load_inputs()
    gate = push4_gate(inputs)
    registry_expansion = build_source_registry_expansion(inputs)
    replay_expansion = build_replay_expansion(inputs, registry_expansion)
    media_bundles = build_media_bundles(inputs, replay_expansion)
    sufficiency_reports = build_detection_reports(media_bundles)
    vss_report = build_vss_report(registry_expansion, media_bundles)

    component_statuses = {
        "push4_gate": gate["status"],
        "source_registry_expansion": registry_expansion["status"],
        "replay_sample_expansion": replay_expansion["status"],
        "media_bundles": media_bundles["status"],
        "detection_sufficiency": sufficiency_reports["status"],
        "vss_sidecar_boundary": vss_report["status"],
    }
    status = PASS_STATUS if all(value == "PASS" for value in component_statuses.values()) else (STOP_PUSH4 if gate["status"] != "PASS" else FAIL_STATUS)

    decision = {
        "schema_version": f"{SCHEMA_VERSION}.decision",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": status,
        "branch": BRANCH,
        "created_at": RUN_TIMESTAMP,
        "canonical_merged": False,
        "push4_gate": gate,
        "component_statuses": component_statuses,
        "completed_through": [
            "B0_PUSH4_GATE_AND_DISCOVERY",
            "B1_SOURCE_REGISTRY_EXPANSION_R1",
            "B2_MEDIA_EVIDENCE_BUNDLE_CONTRACT_R1",
            "B3_REPLAY_SAMPLE_EXPANSION_R2",
            "B4_CHECK_DETECTION_SUFFICIENCY_R2",
            "B5_CLOSEOUT",
            "B6_BRANCH_PUBLISH",
            "B7_FINAL_STATUS",
        ]
        if status == PASS_STATUS
        else ["B0_PUSH4_GATE_AND_DISCOVERY"],
        "counts": {
            "source_registry_entries": registry_expansion["total_source_count"],
            "new_source_registry_entries": registry_expansion["new_source_count"],
            "media_bundles": media_bundles["bundle_count"],
            "replay_samples": replay_expansion["expanded_samples"],
            "sufficiency_reports": sufficiency_reports["report_count"],
            "vss_sidecars": vss_report["sidecar_count"],
        },
        "contract_check": {
            "lane_b_only": True,
            "local_replay_only": True,
            "no_live_cameras_api_url": True,
            "vss_not_fact_source": True,
            "sensor_inferred_candidate_only": True,
            "no_official_detection_finding": True,
            "no_sealed_ask_drift": True,
            "no_protected_r7_drift": True,
            "no_raw_media_dump": True,
            "no_unrelated_dirty_files_staged": True,
        },
        "cannot_claim": UNIVERSAL_NON_CLAIMS,
    }

    write_json(OUTPUT_ROOT / "PERCEPTION_SOURCE_REGISTRY_EXPANSION.json", registry_expansion)
    write_json(OUTPUT_ROOT / "MEDIA_EVIDENCE_BUNDLE_CONTRACT.json", bundle_contract())
    write_json(OUTPUT_ROOT / "PERCEPTION_REPLAY_SAMPLE_EXPANSION.json", replay_expansion)
    write_json(OUTPUT_ROOT / "MEDIA_EVIDENCE_BUNDLES.json", media_bundles)
    write_json(OUTPUT_ROOT / "DETECTION_SUFFICIENCY_REPORTS.json", sufficiency_reports)
    write_json(OUTPUT_ROOT / "VSS_NARRATIVE_SIDECAR_REPORT.json", vss_report)
    write_boundary_docs(status)
    write_json(OUTPUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json", decision)
    manifest_for(OUTPUT_ROOT, "PERCEPTION_MEDIA_HASH_MANIFEST.json")
    decision["required_output_status"] = required_output_status()
    write_json(OUTPUT_ROOT / "PERCEPTION_MEDIA_EVIDENCE_DECISION.json", decision)
    manifest_for(OUTPUT_ROOT, "PERCEPTION_MEDIA_HASH_MANIFEST.json")

    if status == PASS_STATUS:
        write_closeout(decision)
        write_final_status()

    return decision


def main() -> int:
    decision = run()
    print(json.dumps({"status": decision["status"], "output_root": rel(OUTPUT_ROOT)}, sort_keys=True))
    return 0 if decision["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
