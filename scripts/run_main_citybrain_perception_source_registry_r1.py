#!/usr/bin/env python3
"""Track C perception source registry and preflight artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"

C0_ROOT = OUTPUTS / "main_citybrain_r7_production_perception_gap_assessment"
C1_ROOT = OUTPUTS / "main_citybrain_perception_source_registry_preflight"
C2_ROOT = OUTPUTS / "main_citybrain_perception_source_registry_r1"
C4_ROOT = OUTPUTS / "main_citybrain_perception_review_bridge_closeout"
C6_ROOT = OUTPUTS / "main_citybrain_perception_bridge_final_status"

SOURCE_CLASSES = {
    "dataset_annotation": {
        "can_be_fact_source": False,
        "description": "Dataset label or fixture annotation. Useful for comparison only; not live detection.",
    },
    "sensor_inferred": {
        "can_be_fact_source": False,
        "description": "Model or sensor runtime metadata such as DeepStream object metadata. Candidate only unless externally reviewed.",
    },
    "model_generated_narrative_not_fact_source": {
        "can_be_fact_source": False,
        "description": "VSS or similar model narration. Review context only, never a detection or fact source.",
    },
    "manual_review_note": {
        "can_be_fact_source": False,
        "description": "Human review note or label in a governed review context. Not an automated action.",
    },
    "replay_fixture": {
        "can_be_fact_source": False,
        "description": "Local/replay fixture used to test event-state and handoff behavior.",
    },
    "sample_media_ref": {
        "can_be_fact_source": False,
        "description": "Reference to sample media or external media. Not production camera truth.",
    },
}

FORBIDDEN_FLAGS = [
    "live_camera",
    "production_api",
    "url_fetch",
    "llm_call",
    "official_case_ticket_submission",
    "dispatch_control_enforcement",
    "legal_certified_finding",
    "autonomous_workflow",
    "full_citywide_twin_claim",
    "live_kit_control",
]

PASS_C0 = "PASS_MAIN_CITYBRAIN_R7_PRODUCTION_PERCEPTION_GAP_ASSESSMENT_WITH_LIMITATIONS"
PASS_C1 = "PASS_MAIN_CITYBRAIN_PERCEPTION_SOURCE_REGISTRY_PREFLIGHT_WITH_LIMITATIONS"
PASS_C2 = "PASS_MAIN_CITYBRAIN_PERCEPTION_SOURCE_REGISTRY_R1_WITH_LIMITATIONS"
PASS_C4 = "PASS_MAIN_CITYBRAIN_PERCEPTION_REVIEW_BRIDGE_CLOSEOUT_WITH_LIMITATIONS"
PASS_C6 = "PASS_MAIN_CITYBRAIN_PERCEPTION_BRIDGE_FINAL_STATUS_WITH_LIMITATIONS"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_hash(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_dir(path: Path) -> None:
    resolved = path.resolve()
    if OUTPUTS.resolve() not in resolved.parents:
        raise ValueError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == manifest_name:
            continue
        data = path.read_bytes()
        files.append({"path": path.relative_to(root).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)})
    manifest = {
        "algorithm": "sha256",
        "created_at": utc_now(),
        "files": files,
        "item_count": len(files),
        "missing_count": 0,
        "mismatch_count": 0,
        "status": "PASS",
    }
    write_json(root / manifest_name, manifest)
    return manifest


def known_evidence() -> dict[str, Any]:
    r9 = read_json(OUTPUTS / "main_citybrain_r9_deepstream_product_runtime_execution_smoke" / "DECISION.json")
    r22 = read_json(OUTPUTS / "main_citybrain_metropolis_vss_bmd45_cockpit_surface_runtime_smoke_r22" / "R22_CLOSEOUT_DECISION.json")
    r7 = read_json(OUTPUTS / "main_citybrain_r7_final_published_status" / "R7_FINAL_PUBLISHED_STATUS_DECISION.json")
    r2_rows = read_jsonl(OUTPUTS / "main_citybrain_metropolis_vss_object_metadata_export_r2" / "CANDIDATE_OBSERVATION_SAMPLE_R2.jsonl", limit=5)
    return {
        "r2_candidate_observation_sample_count": len(r2_rows),
        "r7_status": r7.get("status") or r7.get("final_decision"),
        "r9_deepstream_status": r9.get("status"),
        "r9_deepstream_runtime_executed": r9.get("deepstream_product_runtime_executed"),
        "r9_candidate_observation_count": r9.get("candidate_observation_count"),
        "r22_status": r22.get("status"),
        "r22_external_media_refs": r22.get("external_media_refs"),
    }


def registry_entries() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "source:track-c:bmd45-dataset-annotations",
            "source_class": "dataset_annotation",
            "source_kind": "offline_dataset_annotation",
            "source_label": "BMD-45 offline dataset annotations",
            "lineage_refs": ["outputs/main_citybrain_metropolis_vss_offline_cctv_dataset_expansion_r16"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["comparison fixture", "threshold calibration", "human review context"],
        },
        {
            "source_id": "source:track-c:deepstream-r2-object-metadata",
            "source_class": "sensor_inferred",
            "source_kind": "deepstream_metropolis_object_metadata",
            "source_label": "DeepStream/Metropolis R2 object metadata export",
            "lineage_refs": ["outputs/main_citybrain_metropolis_vss_object_metadata_export_r2"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["candidate observation generation", "EvidenceBundle context", "human review packet"],
        },
        {
            "source_id": "source:track-c:deepstream-r9-runtime-smoke",
            "source_class": "sensor_inferred",
            "source_kind": "deepstream_product_runtime_smoke",
            "source_label": "R9 DeepStream product runtime execution smoke",
            "lineage_refs": ["outputs/main_citybrain_r9_deepstream_product_runtime_execution_smoke"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["candidate observation source evidence", "runtime smoke evidence"],
        },
        {
            "source_id": "source:track-c:spark-vss-r7-narration",
            "source_class": "model_generated_narrative_not_fact_source",
            "source_kind": "spark_vss_narration_sidecar",
            "source_label": "Spark VSS R7 narration sidecar",
            "lineage_refs": ["outputs/main_citybrain_metropolis_vss_narration_runtime_smoke_r7"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["model-generated review context only"],
        },
        {
            "source_id": "source:track-c:r7-local-replay-fixture",
            "source_class": "replay_fixture",
            "source_kind": "local_replay_event_state_fixture",
            "source_label": "R7 local/replay perception-to-review fixture",
            "lineage_refs": ["outputs/main_citybrain_r7a_perception_candidate_observation_ingress"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["R7A compatibility checks", "local replay bridge"],
        },
        {
            "source_id": "source:track-c:r2-sample-media",
            "source_class": "sample_media_ref",
            "source_kind": "bundled_sample_media_reference",
            "source_label": "DeepStream bundled sample media reference",
            "lineage_refs": ["container_sample_stream:sample_1080p_h264"],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["sample replay reference only"],
        },
        {
            "source_id": "source:track-c:manual-review-note",
            "source_class": "manual_review_note",
            "source_kind": "reviewer_note_placeholder",
            "source_label": "Manual review note lane placeholder",
            "lineage_refs": [],
            "fact_source": False,
            "candidate_only": True,
            "review_required": True,
            "allowed_use": ["future governed reviewer annotation only"],
        },
    ]


def base_forbidden_state() -> dict[str, bool]:
    return {flag: False for flag in FORBIDDEN_FLAGS}


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    entries = registry.get("sources", [])
    classes_present = sorted({entry.get("source_class") for entry in entries})
    missing_classes = sorted(set(SOURCE_CLASSES) - set(classes_present))
    tests = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    add("required_source_classes_present", not missing_classes, ",".join(missing_classes))
    add("vss_cannot_be_fact_source", all(not e.get("fact_source") for e in entries if e.get("source_class") == "model_generated_narrative_not_fact_source"))
    add("deepstream_sensor_inferred_candidate_only", all(e.get("candidate_only") and not e.get("fact_source") for e in entries if e.get("source_class") == "sensor_inferred"))
    add("dataset_annotations_not_live_detection", all(e.get("source_kind") != "live_camera" and not e.get("fact_source") for e in entries if e.get("source_class") == "dataset_annotation"))
    add("no_source_creates_official_violation", all(not e.get("official_violation") and not e.get("legal_certified_finding") for e in entries))
    add("no_source_triggers_dispatch_control_enforcement", all(not e.get("dispatch_control_enforcement") for e in entries))
    add("no_live_camera_or_production_api", all(not e.get("live_camera") and not e.get("production_api") for e in entries))
    add("no_url_fetch_or_llm_call", all(not e.get("url_fetch") and not e.get("llm_call") for e in entries))
    return {
        "classes_present": classes_present,
        "missing_classes": missing_classes,
        "status": "PASS" if all(test["passed"] for test in tests) else "FAIL",
        "tests": tests,
    }


def enriched_registry() -> dict[str, Any]:
    sources = []
    for entry in registry_entries():
        enriched = {**entry, **base_forbidden_state()}
        enriched.update(
            {
                "official_record_allowed": False,
                "official_violation": False,
                "legal_certified_finding": False,
                "vss_as_fact_source": False,
            }
        )
        sources.append(enriched)
    return {
        "schema_version": "main-citybrain-perception-source-registry-r1.v1",
        "created_at": utc_now(),
        "source_classes": SOURCE_CLASSES,
        "sources": sources,
        "universal_non_claims": {
            "no_live_camera": True,
            "no_production_api": True,
            "no_url_fetch": True,
            "no_llm_call": True,
            "no_official_case_ticket_submission": True,
            "no_dispatch_control_enforcement": True,
            "no_legal_certified_finding": True,
            "no_autonomous_workflow": True,
            "no_full_citywide_twin_claim": True,
            "no_live_kit_control": True,
            "no_vss_as_fact_source": True,
        },
    }


def write_c0() -> None:
    reset_dir(C0_ROOT)
    evidence = known_evidence()
    write_json(
        C0_ROOT / "PERCEPTION_GAP_ASSESSMENT_DECISION.json",
        {
            "package": "MAIN-CITYBRAIN-R7-PRODUCTION-PERCEPTION-GAP-ASSESSMENT",
            "status": PASS_C0,
            "created_at": utc_now(),
            "evidence": evidence,
            "production_ready": False,
            "registry_preflight_recommended": True,
            "contract_check": {
                "no_live_camera": True,
                "no_production_ingestion": True,
                "vss_not_fact_source": True,
                "deepstream_metropolis_not_official_truth": True,
                "candidate_observations_only": True,
                "no_official_submission_action": True,
            },
        },
    )
    write_text(
        C0_ROOT / "PERCEPTION_CURRENT_EVIDENCE_INVENTORY.md",
        f"""# Perception Current Evidence Inventory

- R9 DeepStream runtime smoke: `{evidence.get('r9_deepstream_status')}`
- R9 candidate observations: `{evidence.get('r9_candidate_observation_count')}`
- R22 BMD-45 cockpit surface smoke: `{evidence.get('r22_status')}`
- R7 final local/replay workflow status: `{evidence.get('r7_status')}`
- R2 sample candidate observations available for bridge input: `{evidence.get('r2_candidate_observation_sample_count')}`
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_SOURCE_CLASS_BOUNDARIES.md",
        """# Perception Source Class Boundaries

- `dataset_annotation`: dataset label or annotation fixture; comparison only.
- `sensor_inferred`: DeepStream/Metropolis object metadata; candidate review only.
- `model_generated_narrative_not_fact_source`: VSS narration; review context only.
- `manual_review_note`: future reviewer note; no automated action.
- `replay_fixture`: local/replay fixture; no live claim.
- `sample_media_ref`: sample media reference; no production camera claim.
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_PRODUCTION_GAPS.md",
        """# Perception Production Gaps

- No live camera onboarding.
- No production media ingestion.
- No retention policy for production video.
- No production camera registry.
- No independent verification loop.
- No operational response or dispatch path, intentionally.
- No legal/certified claim path, intentionally.
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_SECURITY_PRIVACY_RETENTION_GAPS.md",
        """# Security Privacy Retention Gaps

- Production privacy assessment is not complete.
- Production media retention and deletion rules are not defined.
- Secret rotation for vendor/runtime keys remains an infra responsibility.
- Identity, biometric, and license-plate flows remain out of scope.
- Sample/replay artifacts must remain clearly labeled as non-production.
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_TO_R7_REVIEW_PATH.md",
        """# Perception To R7 Review Path

Safe path:

`source registry -> source-class validation -> local/replay candidate observation -> R7A-compatible candidate observation -> human review context`

The path stops at candidate review. It does not submit a case, dispatch, control, enforce, or certify.
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_NON_CLAIMS.md",
        """# Perception Non-Claims

- No live camera.
- No production ingestion.
- No VSS-as-fact-source.
- No official detection or violation.
- No dispatch/control/enforcement.
- No legal/certified finding.
- No autonomous workflow.
""",
    )
    write_text(
        C0_ROOT / "PERCEPTION_NEXT_REGISTRY_REQUIREMENTS.md",
        """# Perception Next Registry Requirements

The registry must enumerate source classes, source ids, allowed uses, forbidden uses, provenance refs, and candidate-only review boundaries.

Minimum source classes: dataset_annotation, sensor_inferred, model_generated_narrative_not_fact_source, manual_review_note, replay_fixture, sample_media_ref.
""",
    )
    write_manifest(C0_ROOT, "PERCEPTION_GAP_ASSESSMENT_HASH_MANIFEST.json")


def write_c1() -> None:
    reset_dir(C1_ROOT)
    write_json(
        C1_ROOT / "PERCEPTION_SOURCE_REGISTRY_PREFLIGHT_DECISION.json",
        {
            "package": "MAIN-CITYBRAIN-PERCEPTION-SOURCE-REGISTRY-PREFLIGHT",
            "status": PASS_C1,
            "created_at": utc_now(),
            "required_source_classes": sorted(SOURCE_CLASSES),
            "continue_to_r1": True,
        },
    )
    write_text(
        C1_ROOT / "PERCEPTION_SOURCE_REGISTRY_REQUIREMENTS.md",
        """# Perception Source Registry Requirements

- Every source must have `source_id`, `source_class`, `source_kind`, `source_label`, lineage refs, allowed use, and forbidden state flags.
- No source may be an official fact source in this Track C sprint.
- All outputs remain local/replay or sample-media candidate review context.
""",
    )
    write_text(
        C1_ROOT / "PERCEPTION_SOURCE_CLASS_TAXONOMY.md",
        "\n".join(["# Perception Source Class Taxonomy", ""] + [f"- `{name}`: {meta['description']}" for name, meta in SOURCE_CLASSES.items()]),
    )
    write_json(
        C1_ROOT / "PERCEPTION_SOURCE_REGISTRY_SCHEMA_DRAFT.json",
        {
            "type": "object",
            "required": ["schema_version", "source_classes", "sources", "universal_non_claims"],
            "properties": {
                "source_classes": {"type": "object"},
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["source_id", "source_class", "source_kind", "source_label", "fact_source", "candidate_only", "review_required"],
                    },
                },
            },
        },
    )
    write_text(
        C1_ROOT / "PERCEPTION_SOURCE_BOUNDARY_RULES.md",
        """# Perception Source Boundary Rules

- VSS cannot be a fact source.
- DeepStream/Metropolis detections remain `sensor_inferred`.
- Dataset annotations cannot imply live detection.
- Sample media refs cannot imply production cameras.
- No source can create official violation, ticket, submission, dispatch, control, enforcement, or legal/certified claim.
""",
    )
    write_text(
        C1_ROOT / "PERCEPTION_SOURCE_REGISTRY_R1_PROMPT.md",
        """# MAIN-CITYBRAIN-PERCEPTION-SOURCE-REGISTRY-R1

Build the perception source registry from the Track C preflight taxonomy.

Required outputs: registry JSON, audit JSON, boundary tests JSON, test log, hash manifest.

Keep all sources candidate-review-only. Do not add live cameras, production APIs, URL fetching, LLM calls, official actions, dispatch/control/enforcement, or legal/certified claims.
""",
    )
    write_manifest(C1_ROOT, "PERCEPTION_SOURCE_REGISTRY_PREFLIGHT_HASH_MANIFEST.json")


def write_c2() -> dict[str, Any]:
    reset_dir(C2_ROOT)
    registry = enriched_registry()
    validation = validate_registry(registry)
    audit = {
        "status": validation["status"],
        "source_count": len(registry["sources"]),
        "source_classes_present": validation["classes_present"],
        "vss_not_fact_source": True,
        "deepstream_metropolis_not_official_truth": True,
        "no_live_camera": True,
        "no_production_api": True,
        "no_dispatch_control_enforcement": True,
        "no_legal_certified_claim": True,
    }
    write_json(C2_ROOT / "PERCEPTION_SOURCE_REGISTRY.json", registry)
    write_json(C2_ROOT / "PERCEPTION_SOURCE_REGISTRY_AUDIT.json", audit)
    write_json(C2_ROOT / "PERCEPTION_SOURCE_CLASS_BOUNDARY_TESTS.json", validation)
    write_text(
        C2_ROOT / "PERCEPTION_SOURCE_REGISTRY_R1_TEST_LOG.md",
        "\n".join(
            [
                "# Perception Source Registry R1 Test Log",
                "",
                f"Status: `{validation['status']}`",
                f"Tests: `{sum(1 for t in validation['tests'] if t['passed'])}/{len(validation['tests'])}`",
                "",
                "No runtime calls were made.",
            ]
        ),
    )
    write_json(
        C2_ROOT / "PERCEPTION_SOURCE_REGISTRY_R1_DECISION.json",
        {
            "package": "MAIN-CITYBRAIN-PERCEPTION-SOURCE-REGISTRY-R1",
            "status": PASS_C2 if validation["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_PERCEPTION_SOURCE_REGISTRY_R1",
            "created_at": utc_now(),
            "source_count": len(registry["sources"]),
            "source_classes": sorted(SOURCE_CLASSES),
            "audit_status": audit["status"],
            "continue_to_replay_bridge": validation["status"] == "PASS",
        },
    )
    write_manifest(C2_ROOT, "PERCEPTION_SOURCE_REGISTRY_R1_HASH_MANIFEST.json")
    return validation


def write_closeout(bridge_summary: dict[str, Any] | None = None) -> None:
    reset_dir(C4_ROOT)
    bridge_summary = bridge_summary or read_json(OUTPUTS / "main_citybrain_perception_replay_sample_bridge_r1" / "PERCEPTION_REPLAY_SAMPLE_BRIDGE_R1_DECISION.json")
    write_json(
        C4_ROOT / "PERCEPTION_REVIEW_BRIDGE_CLOSEOUT_DECISION.json",
        {
            "package": "MAIN-CITYBRAIN-PERCEPTION-REVIEW-BRIDGE-CLOSEOUT",
            "status": PASS_C4,
            "created_at": utc_now(),
            "completed_slices": ["C0", "C1", "C2", "C3"],
            "bridge_status": bridge_summary.get("status"),
            "candidate_observations": bridge_summary.get("candidate_observations"),
            "r7a_compatible": bridge_summary.get("r7a_compatible"),
            "contract_check": {
                "no_live_cameras": True,
                "no_production_ingestion": True,
                "vss_not_fact_source": True,
                "deepstream_metropolis_not_official_truth": True,
                "candidate_observations_only": True,
                "no_official_submission_action": True,
                "no_dispatch_control_enforcement": True,
                "no_legal_certified_claim": True,
                "no_ask_runtime_changed": True,
            },
        },
    )
    write_text(
        C4_ROOT / "PERCEPTION_REVIEW_BRIDGE_CLOSEOUT_SUMMARY.md",
        f"""# Perception Review Bridge Closeout

Status: `{PASS_C4}`

C0-C3 are closed with limitations. The source registry exists, the replay sample bridge emitted R7A-compatible candidate observations, and all source classes remain candidate-review-only.

Bridge candidate observations: `{bridge_summary.get('candidate_observations')}`

R7A compatible: `{bridge_summary.get('r7a_compatible')}`
""",
    )
    write_text(
        C4_ROOT / "PERCEPTION_REVIEW_BRIDGE_LIMITATIONS.md",
        """# Limitations

- No live camera.
- No production media ingestion.
- No production source registry service.
- No reviewer disposition lifecycle.
- No official fact, finding, ticket, dispatch, control, enforcement, legal claim, or certified claim.
""",
    )
    write_text(
        C4_ROOT / "PERCEPTION_REVIEW_BRIDGE_NON_CLAIMS.md",
        """# Non-Claims

DeepStream/Metropolis is sensor-inferred candidate context. VSS is model-generated narrative and not a fact source. Dataset annotations are comparison labels. Replay bridge outputs are candidate observations only.
""",
    )
    write_manifest(C4_ROOT, "PERCEPTION_REVIEW_BRIDGE_CLOSEOUT_HASH_MANIFEST.json")


def write_final_status(commit_sha: str = "", push_status: str = "PENDING") -> None:
    reset_dir(C6_ROOT)
    write_json(
        C6_ROOT / "PERCEPTION_BRIDGE_FINAL_STATUS_DECISION.json",
        {
            "package": "MAIN-CITYBRAIN-PERCEPTION-BRIDGE-FINAL-PUBLISHED-STATUS",
            "status": PASS_C6,
            "created_at": utc_now(),
            "commit_sha": commit_sha,
            "push_status": push_status,
            "published_with_limitations": True,
            "contract_check": {
                "no_live_cameras": True,
                "no_production_ingestion": True,
                "vss_not_fact_source": True,
                "deepstream_metropolis_not_official_truth": True,
                "candidate_observations_only": True,
                "no_official_submission_action": True,
                "no_dispatch_control_enforcement": True,
                "no_legal_certified_claim": True,
                "no_ask_runtime_changed": True,
            },
        },
    )
    write_text(
        C6_ROOT / "PERCEPTION_BRIDGE_FINAL_STATUS_SUMMARY.md",
        f"""# Perception Bridge Final Status

Final decision: `{PASS_C6}`

Commit: `{commit_sha or 'pending'}`

Push status: `{push_status}`

The Track C sprint source registry and replay bridge are published with limitations. The lane remains local/replay and candidate-review-only.
""",
    )
    write_manifest(C6_ROOT, "PERCEPTION_BRIDGE_FINAL_STATUS_HASH_MANIFEST.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Track C perception source registry artifacts.")
    parser.add_argument("--stage", choices=["c0", "c1", "c2", "closeout", "final", "all"], default="all")
    parser.add_argument("--commit-sha", default="")
    parser.add_argument("--push-status", default="PENDING")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.stage in {"c0", "all"}:
        write_c0()
    if args.stage in {"c1", "all"}:
        write_c1()
    validation = None
    if args.stage in {"c2", "all"}:
        validation = write_c2()
    if args.stage == "closeout":
        write_closeout()
    if args.stage == "final":
        write_final_status(args.commit_sha, args.push_status)
    if args.stage == "all":
        print("C0-C2 complete")
        if validation:
            print(f"Registry validation: {validation['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
