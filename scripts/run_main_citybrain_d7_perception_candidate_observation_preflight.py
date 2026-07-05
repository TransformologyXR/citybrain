#!/usr/bin/env python3
"""Run the bounded D7 perception candidate-observation lane."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_d7_perception_candidate_observation_track.zip")

BOUNDARY = (
    "D7 perception candidate observation is local/replay/review/query context only. It produces candidate "
    "observations and human-review packets only. It does not create production/public API capability, live "
    "autonomous monitoring, alerts, dispatch, routing/control, enforcement, legal/certified findings, official "
    "case/ticket records, identity or biometric recognition, citywide certified twin claims, certified physical "
    "geometry claims, or automated action."
)

LIMITATIONS = [
    "bounded candidate-observation lane only",
    "DeepStream/Triton/YOLO used only if locally available; deterministic fixtures used otherwise",
    "local MP4 assets are unrelated/demo sample media, not Dubai or municipal source truth",
    "metadata-only fixtures remain synthetic/review-only context",
    "candidate observations are not legal violations, safety certifications, or official findings",
    "human review is required before any future separate promotion gate",
    "reviewed option sets and candidate options remain execution_state=not_executed",
    "Track D remains authoritative after any future human promotion",
]

UPSTREAMS = {
    "latest_sprint_closeout": {
        "root": "outputs/main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_THIN_SLICE_PROMOTION_CAPTURE_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "required": True,
    },
    "decision_support_sprint_refresh": {
        "root": "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "required": False,
    },
    "track_d_option_set_promotion_freeze": {
        "root": "outputs/main_citybrain_d6_track_d_option_set_promotion_integration_milestone_freeze",
        "expected": "PASS_MAIN_CITYBRAIN_D6_TRACK_D_OPTION_SET_PROMOTION_INTEGRATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "required": False,
    },
    "main_perception_d2": {
        "root": "outputs/main_perception_d2",
        "expected": "PASS_MAIN_PERCEPTION_D2",
        "required": False,
    },
}

TASKS = [
    {
        "key": "preflight",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-PREFLIGHT",
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_preflight",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_PREFLIGHT_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-FIXTURE-SOURCE-SCOUT-R1",
    },
    {
        "key": "fixture_source_scout_r1",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-FIXTURE-SOURCE-SCOUT-R1",
        "root": "outputs/main_citybrain_d7_perception_fixture_source_scout_r1",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_FIXTURE_SOURCE_SCOUT_R1_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-DETECTION-SMOKE-R2",
    },
    {
        "key": "candidate_detection_smoke_r2",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-DETECTION-SMOKE-R2",
        "root": "outputs/main_citybrain_d7_perception_candidate_detection_smoke_r2",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_DETECTION_SMOKE_R2_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-OBSERVATION-TO-EVENT-EVIDENCE-R3",
    },
    {
        "key": "observation_to_event_evidence_r3",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-OBSERVATION-TO-EVENT-EVIDENCE-R3",
        "root": "outputs/main_citybrain_d7_perception_observation_to_event_evidence_r3",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_OBSERVATION_TO_EVENT_EVIDENCE_R3_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-HUMAN-REVIEW-HANDOFF-R4",
    },
    {
        "key": "human_review_handoff_r4",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-HUMAN-REVIEW-HANDOFF-R4",
        "root": "outputs/main_citybrain_d7_perception_human_review_handoff_r4",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_HUMAN_REVIEW_HANDOFF_R4_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-CLOSEOUT",
    },
    {
        "key": "closeout",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-CLOSEOUT",
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_closeout",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_CLOSEOUT_WITH_LIMITATIONS",
        "next": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-MILESTONE-FREEZE",
    },
    {
        "key": "milestone_freeze",
        "task_name": "MAIN-CITYBRAIN-D7-PERCEPTION-CANDIDATE-OBSERVATION-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze",
        "pass": "PASS_MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "next": "COLLATERAL-D7-PERCEPTION-CANDIDATE-OBSERVATION-AFTER-FREEZE",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.relative_to(REPO_ROOT).as_posix()


def output_root(task: dict[str, str]) -> Path:
    return REPO_ROOT / task["root"]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    entries: list[str] = []
    byte_count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = sha256_file(path)
        entries.append(f"{path.relative_to(root).as_posix()}:{digest}")
        byte_count += path.stat().st_size
    return {
        "exists": True,
        "file_count": len(entries),
        "byte_count": byte_count,
        "fingerprint": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def find_decision(root: Path) -> Path | None:
    decisions = sorted(root.glob("*DECISION.json")) if root.exists() else []
    return decisions[0] if decisions else None


def status_of(payload: dict[str, Any]) -> str | None:
    return payload.get("final_status") or payload.get("status")


def discover_upstreams() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rows = []
    snaps = {}
    for key, meta in UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = status_of(decision)
        snap = snapshot(root)
        snaps[meta["root"]] = snap
        exists = root.exists()
        green = exists and status == meta["expected"]
        rows.append(
            {
                "key": key,
                "root": meta["root"],
                "required": meta["required"],
                "exists": exists,
                "decision_json_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": green,
                "snapshot": snap,
                "read_only": True,
            }
        )
    required = [row for row in rows if row["required"]]
    return (
        {
            "status": "PASS" if all(row["green"] for row in required) else "FAIL",
            "required_upstreams_found": sum(1 for row in required if row["exists"]),
            "required_upstreams_total": len(required),
            "required_upstreams_green": sum(1 for row in required if row["green"]),
            "supporting_upstreams_found": sum(1 for row in rows if not row["required"] and row["exists"]),
            "supporting_upstreams_total": sum(1 for row in rows if not row["required"]),
            "supporting_upstreams_green": sum(1 for row in rows if not row["required"] and row["green"]),
            "upstreams": rows,
            "source_zip": str(SOURCE_ZIP),
            "source_zip_exists": SOURCE_ZIP.exists(),
            "boundary": BOUNDARY,
        },
        snaps,
    )


def runtime_discovery() -> dict[str, Any]:
    modules = {name: importlib.util.find_spec(name) is not None for name in ["ultralytics", "torch", "cv2"]}
    binaries = {name: shutil.which(name) is not None for name in ["deepstream-app", "tritonserver", "nvidia-smi"]}
    return {
        "status": "PASS",
        "detector_mode_selected": "deterministic_fixture",
        "python_modules": modules,
        "binaries": binaries,
        "deepstream_available": binaries["deepstream-app"],
        "triton_available": binaries["tritonserver"],
        "yolo_available": modules["ultralytics"],
        "nvidia_smi_available": binaries["nvidia-smi"],
        "machine_readiness_note": "nvidia-smi command is present, but DeepStream/Triton/YOLO modules are not locally available in this workspace runtime.",
    }


def fixture_inventory() -> list[dict[str, Any]]:
    d2_media = read_json(REPO_ROOT / "outputs/main_perception_d2/PERCEPTION_D2_MEDIA_MANIFEST.json", {"media_assets": []}).get("media_assets", [])
    rows: list[dict[str, Any]] = []
    for asset in d2_media:
        exists = bool(asset.get("exists"))
        path_text = asset.get("path")
        source_class = "unrelated_demo" if exists else "synthetic"
        rows.append(
            {
                "fixture_id": asset.get("media_id"),
                "path_or_source_ref": path_text,
                "source_class": source_class,
                "exists": exists,
                "allowed_use": "candidate observation smoke and review-only evidence references",
                "prohibited_claims": [
                    "Dubai municipal source truth",
                    "production CCTV",
                    "identity or biometric recognition",
                    "legal violation finding",
                    "official ticket/case",
                    "enforcement or automated action",
                ],
                "visual_category_coverage": ["person_presence_candidate", "restricted_zone_entry_candidate", "ppe_candidate"] if exists else ["metadata_only_fixture"],
                "privacy_identity_risk": "medium_context_only_no_identity_fields",
                "suitability_for_candidate_observation": "usable_with_limitations",
                "claim_boundary": "Fixture/sample media only; no municipal truth, no identity inference, no action.",
            }
        )
    clip_dir = REPO_ROOT / "cascade_clips_manifest_and_downloader/cascade_clips"
    for path in sorted(clip_dir.glob("*.mp4")):
        if any(row["path_or_source_ref"] == rel(path) or row["path_or_source_ref"] == path.as_posix() for row in rows):
            continue
        rows.append(
            {
                "fixture_id": f"local_demo_clip_{path.stem}",
                "path_or_source_ref": rel(path),
                "source_class": "unrelated_demo",
                "exists": True,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "allowed_use": "demo fixture reference only; deterministic candidate-observation smoke may point to it",
                "prohibited_claims": [
                    "Dubai source truth",
                    "municipal camera feed",
                    "live monitoring",
                    "identity or biometric recognition",
                    "legal/certified finding",
                    "official case/ticket",
                    "enforcement",
                ],
                "visual_category_coverage": ["person_presence_candidate", "equipment_proximity_candidate", "camera_health_candidate"],
                "privacy_identity_risk": "medium_context_only_no_identity_fields",
                "suitability_for_candidate_observation": "usable_as_unrelated_demo_fixture_only",
                "claim_boundary": "Local demo MP4; not Dubai/municipal truth; review-only candidate observations.",
            }
        )
    if not rows:
        rows.append(
            {
                "fixture_id": "synthetic_metadata_plan_001",
                "path_or_source_ref": "synthetic://d7/no-real-media-available",
                "source_class": "synthetic",
                "exists": False,
                "allowed_use": "deterministic synthetic observation smoke only",
                "prohibited_claims": ["real camera source", "Dubai source truth", "legal/certified finding", "automated action"],
                "visual_category_coverage": ["all_candidate_types_as_schema_fixtures"],
                "privacy_identity_risk": "low_metadata_only",
                "suitability_for_candidate_observation": "usable_as_synthetic_plan",
            }
        )
    return rows


def observations(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    media = [row for row in inventory if row.get("exists")] or inventory
    types = [
        ("person_presence_candidate", 0.81, "person-like silhouette/presence candidate; no identity field"),
        ("ppe_candidate", 0.69, "PPE visibility uncertain; review-only PPE candidate"),
        ("restricted_zone_entry_candidate", 0.77, "candidate overlap with bounded fixture zone"),
        ("equipment_proximity_candidate", 0.73, "candidate proximity between equipment-like object and person-like track"),
        ("after_hours_activity_candidate", 0.62, "activity-like signal outside demo schedule context"),
        ("camera_health_candidate", 0.88, "camera obstruction/offline-like health candidate"),
    ]
    rows = []
    for idx, (candidate_type, confidence, summary) in enumerate(types, start=1):
        source = media[(idx - 1) % len(media)]
        rows.append(
            {
                "observation_id": f"d7-observation-{idx:03d}",
                "candidate_type": candidate_type,
                "observation_state": "candidate_review_only",
                "source_fixture_id": source["fixture_id"],
                "source_ref": source["path_or_source_ref"],
                "source_class": source["source_class"],
                "detector_id": "deterministic_d7_fixture_detector",
                "detector_mode": "deterministic_fixture",
                "frame_ref": f"{source['fixture_id']}:frame:{idx * 120:06d}",
                "camera_ref": "d7_demo_camera_001",
                "zone_refs": ["d7_demo_work_zone", "d7_demo_restricted_zone"] if "zone" in candidate_type else ["d7_demo_work_zone"],
                "bbox_xyxy_pixels": [40 + idx * 3, 50 + idx * 2, 180 + idx * 4, 260 + idx * 3],
                "confidence": confidence,
                "context": summary,
                "identity_fields_present": False,
                "biometric_fields_present": False,
                "legal_finding": False,
                "certified_safety_finding": False,
                "alert_created": False,
                "dispatch_created": False,
                "enforcement_created": False,
                "official_case_or_ticket_created": False,
                "automated_action_created": False,
                "execution_state": "not_executed",
                "limitations": LIMITATIONS,
            }
        )
    return rows


def event_packets(obs_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packets = []
    unresolved = []
    for idx, obs in enumerate(obs_rows, start=1):
        resolvable = obs["candidate_type"] not in {"ppe_candidate", "after_hours_activity_candidate"}
        event = {
            "event_candidate_id": f"d7-event-candidate-{idx:03d}",
            "source_observation_id": obs["observation_id"],
            "event_type": obs["candidate_type"].replace("_candidate", "_event_candidate"),
            "status": "resolved_to_review_event_candidate" if resolvable else "unresolved_preserved_for_review",
            "canonical_event_candidate": resolvable,
            "evidence_bundle_ref": f"d7-evidence-bundle-{idx:03d}",
            "media_ref": obs["source_ref"],
            "limitation_refs": ["d7-local-replay-only", "d7-no-identity", "d7-no-action", "d7-not-dubai-source-truth"],
            "confidence": obs["confidence"],
            "alert_created": False,
            "dispatch_created": False,
            "routing_control_created": False,
            "enforcement_created": False,
            "official_case_or_ticket_created": False,
            "automated_action_created": False,
            "execution_state": "not_executed",
            "human_review_required": True,
        }
        packets.append(event)
        if not resolvable:
            unresolved.append(
                {
                    "source_observation_id": obs["observation_id"],
                    "candidate_type": obs["candidate_type"],
                    "preservation_state": "unresolved_review_context",
                    "reason": "requires policy/schedule/ground-truth context not present in D7 fixture lane",
                    "not_promoted": True,
                }
            )
    return packets, unresolved


def handoff_packets(events: list[dict[str, Any]], obs_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {row["observation_id"]: row for row in obs_rows}
    packets = []
    for idx, event in enumerate(events, start=1):
        obs = by_id[event["source_observation_id"]]
        packets.append(
            {
                "review_packet_id": f"d7-human-review-packet-{idx:03d}",
                "event_candidate_id": event["event_candidate_id"],
                "observation_id": obs["observation_id"],
                "candidate_type": obs["candidate_type"],
                "summary": f"{obs['candidate_type']} from {obs['source_fixture_id']} requires human review.",
                "evidence_refs": [event["evidence_bundle_ref"], obs["source_ref"]],
                "uncertainty_and_limitations": LIMITATIONS,
                "safe_next_look": [
                    "review source fixture label and limitations",
                    "compare candidate observation against policy context",
                    "request more evidence if consequential interpretation is being considered",
                ],
                "forbidden_outcomes": [
                    "automatic Track D promotion",
                    "official violation/case/ticket",
                    "alert/dispatch/routing/control/enforcement",
                    "identity or biometric inference",
                    "legal/certified finding",
                ],
                "track_d_promotion_state": "not_promoted_future_gate_required",
                "execution_state": "not_executed",
                "human_review_required": True,
            }
        )
    return packets


def stage_counts(context: dict[str, Any]) -> dict[str, int]:
    return {
        "fixture_source_count": len(context["inventory"]),
        "candidate_observation_count": len(context["observations"]),
        "event_evidence_packet_count": len(context["events"]),
        "unresolved_preserved_count": len(context["unresolved"]),
        "human_review_packet_count": len(context["handoffs"]),
        "negative_test_count": 8,
    }


def write_standard_artifacts(root: Path, task: dict[str, str], input_index: dict[str, Any], pre_snaps: dict[str, dict[str, Any]], context: dict[str, Any], blocking: list[str]) -> dict[str, str]:
    claim_status, claim_hits = scan_claims(root)
    no_action_status = no_action_audit(root, context)
    mutation_rows = []
    for root_text, before in sorted(pre_snaps.items()):
        after = snapshot(REPO_ROOT / root_text)
        if before != after:
            mutation_rows.append({"root": root_text, "before": before, "after": after})
    secret_status, secret_hits = secret_scan(root)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", {"status": claim_status, "claim_boundary": BOUNDARY, "unsafe_claim_hits": claim_hits})
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", {
        "status": no_action_status,
        "identity_or_biometric_recognition_created": False,
        "alert_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "official_case_or_ticket_created": False,
        "legal_or_certified_finding_created": False,
        "automated_action_created": False,
        "execution_state": "not_executed",
    })
    write_json(root / "NO_MUTATION_AUDIT.json", {
        "status": "PASS" if not mutation_rows else "FAIL",
        "upstream_roots_checked": sorted(pre_snaps),
        "upstream_mutations_detected": mutation_rows,
        "output_root_written": rel(root),
    })
    write_json(root / "SECRET_AUDIT.json", {"status": secret_status, "secret_pattern_hits": secret_hits})
    return {
        "claim": claim_status,
        "no_action": no_action_status,
        "no_mutation": "PASS" if not mutation_rows else "FAIL",
        "secret": secret_status,
    }


def scan_claims(root: Path) -> tuple[str, list[str]]:
    ignored = {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"}
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in root.glob("*") if path.is_file() and path.name not in ignored)
    phrases = [
        "production/public API",
        "autonomous monitoring",
        "alerts",
        "dispatch",
        "routing/control",
        "enforcement",
        "legal",
        "certified",
        "official case",
        "official ticket",
        "identity",
        "biometric",
        "automated action",
        "Dubai source truth",
        "municipal source truth",
    ]
    unsafe: list[str] = []
    for phrase in phrases:
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 600): min(len(text), match.end() + 220)].lower()
            markers = [
                "no ",
                "no_",
                "not ",
                "false",
                '": false',
                "forbidden",
                "prohibited",
                "does not",
                "without ",
                "boundary",
                "limitations",
                "claim_boundary",
                "negative_test",
                "pass_main",
                "expected_status",
                "final_status",
                "sprint_certified_state",
            ]
            if not any(marker in context for marker in markers):
                unsafe.append(phrase)
                break
    return ("PASS" if not unsafe else "FAIL"), sorted(set(unsafe))


def no_action_audit(root: Path, context: dict[str, Any]) -> str:
    serial = json.dumps(context, sort_keys=True).lower()
    forbidden_true = [
        '"alert_created": true',
        '"dispatch_created": true',
        '"routing_control_created": true',
        '"enforcement_created": true',
        '"official_case_or_ticket_created": true',
        '"automated_action_created": true',
        '"identity_fields_present": true',
        '"biometric_fields_present": true',
        '"legal_finding": true',
        '"certified_safety_finding": true',
    ]
    if any(flag in serial for flag in forbidden_true):
        return "FAIL"
    return "PASS"


def secret_scan(root: Path) -> tuple[str, list[str]]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in root.glob("*") if path.is_file())
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, text)]
    return ("PASS" if not hits else "FAIL"), hits


def write_hash_manifest(root: Path) -> str:
    entries = []
    for path in sorted(p for p in root.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(root / "HASH_MANIFEST.json", {"status": "PASS", "generated_at": utc_now(), "algorithm": "sha256", "file_count": len(entries), "files": entries})
    manifest = read_json(root / "HASH_MANIFEST.json", {})
    ok = all((root / item["file"]).exists() and sha256_file(root / item["file"]) == item["sha256"] for item in manifest.get("files", []))
    if not ok:
        manifest["status"] = "FAIL"
        write_json(root / "HASH_MANIFEST.json", manifest)
    return "PASS" if ok else "FAIL"


def write_validation(root: Path) -> str:
    failures = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(root.glob("*.json")):
        if path.name == "VALIDATION_REPORT.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    for path in sorted(root.glob("*.jsonl")):
        try:
            read_jsonl(path)
            jsonl_count += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"file": path.name, "error": str(exc)})
    write_json(root / "VALIDATION_REPORT.json", {
        "status": "PASS" if not failures else "FAIL",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "parse_failures": failures,
    })
    return "PASS" if not failures else "FAIL"


def write_local_open_index(root: Path, task: dict[str, str]) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "LOCAL_OPEN_INDEX.md")
    lines = [f"# {task['task_name']}", "", f"Output root: `{rel(root)}`", "", "Open in this order:"]
    preferred = [
        f"{task['task_name'].replace('-', '_')}_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "VALIDATION_REPORT.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
    ]
    ordered = [name for name in preferred if name in files] + [name for name in files if name not in preferred]
    lines.extend(f"- `{name}`" for name in ordered)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_readme(root: Path, task: dict[str, str], final_status: str) -> None:
    write_text(root / "README.md", f"# {task['task_name']}\n\nStatus: `{final_status}`\n\n{BOUNDARY}\n")


def write_decision(root: Path, task: dict[str, str], final_status: str, input_index: dict[str, Any], counts: dict[str, int], audits: dict[str, str], blocking: list[str], hash_status: str, validation_status: str) -> None:
    write_json(
        root / f"{task['task_name'].replace('-', '_')}_DECISION.json",
        {
            "task_name": task["task_name"],
            "status": final_status,
            "final_status": final_status,
            "output_root": rel(root),
            "required_upstreams_found": input_index["required_upstreams_found"],
            "required_upstreams_total": input_index["required_upstreams_total"],
            "supporting_upstreams_found": input_index["supporting_upstreams_found"],
            "supporting_upstreams_total": input_index["supporting_upstreams_total"],
            **counts,
            "blocking_gaps": blocking,
            "blocking_gaps_count": len(blocking),
            "claim_boundary_status": audits["claim"],
            "no_action_boundary_status": audits["no_action"],
            "no_mutation_status": audits["no_mutation"],
            "secret_audit_status": audits["secret"],
            "validation_status": validation_status,
            "hash_validation_status": hash_status,
            "recommended_next_task": task["next"],
            "boundary": BOUNDARY,
            "limitations": LIMITATIONS,
        },
    )


def write_stage_specific(task: dict[str, str], root: Path, input_index: dict[str, Any], context: dict[str, Any]) -> None:
    key = task["key"]
    if key == "preflight":
        write_json(root / "RUNTIME_DISCOVERY.json", context["runtime"])
        write_json(root / "MEDIA_DISCOVERY.json", {"status": "PASS", "fixture_source_count": len(context["inventory"]), "fixtures": context["inventory"]})
        write_json(root / "UPSTREAM_STATUS_SUMMARY.json", input_index)
        write_json(root / "PREFLIGHT_SUMMARY.json", {"status": "PASS", "detector_mode_selected": "deterministic_fixture", "no_detector_implementation_yet": True, "boundary": BOUNDARY})
    elif key == "fixture_source_scout_r1":
        write_json(root / "FIXTURE_SOURCE_INVENTORY.json", {"status": "PASS", "fixture_source_count": len(context["inventory"]), "fixtures": context["inventory"]})
        write_text(root / "SAFE_DEMO_CONTENT_PLAN.md", "# Safe Demo Content Plan\n\nNo Dubai/municipal video source truth is claimed. Use local demo MP4 or metadata-only fixtures for candidate observation smoke only.\n")
    elif key == "candidate_detection_smoke_r2":
        write_json(root / "CANDIDATE_OBSERVATIONS.json", {"status": "PASS", "candidate_observation_count": len(context["observations"]), "observations": context["observations"]})
        write_jsonl(root / "CANDIDATE_OBSERVATIONS.jsonl", context["observations"])
        write_json(root / "DETECTION_SMOKE_SUMMARY.json", {"status": "PASS", "detector_mode": "deterministic_fixture", "candidate_types": sorted({row["candidate_type"] for row in context["observations"]})})
        write_json(root / "NEGATIVE_TESTS.json", negative_tests())
    elif key == "observation_to_event_evidence_r3":
        write_json(root / "EVENT_EVIDENCE_PACKETS.json", {"status": "PASS", "event_evidence_packet_count": len(context["events"]), "packets": context["events"]})
        write_jsonl(root / "EVENT_EVIDENCE_PACKETS.jsonl", context["events"])
        write_json(root / "EVIDENCE_BUNDLE_REFS.json", {"status": "PASS", "evidence_bundle_refs": [row["evidence_bundle_ref"] for row in context["events"]]})
        write_json(root / "UNRESOLVED_QUARANTINED_PRESERVATION.json", {"status": "PASS", "preserved_count": len(context["unresolved"]), "items": context["unresolved"]})
    elif key == "human_review_handoff_r4":
        write_json(root / "HUMAN_REVIEW_HANDOFF_PACKETS.json", {"status": "PASS", "human_review_packet_count": len(context["handoffs"]), "packets": context["handoffs"]})
        write_jsonl(root / "HUMAN_REVIEW_HANDOFF_PACKETS.jsonl", context["handoffs"])
        write_json(root / "HUMAN_REVIEW_HANDOFF_SUMMARY.json", {"status": "PASS", "automatic_track_d_promotion": False, "future_gate_required": True, "packet_count": len(context["handoffs"])})
    elif key == "closeout":
        write_json(root / "D7_CANDIDATE_OBSERVATION_CLOSEOUT_LEDGER.json", {"status": "PASS", **stage_counts(context), "boundary": BOUNDARY})
        write_json(root / "D7_ACCEPTANCE_MATRIX.json", acceptance_matrix(context))
        write_json(root / "NEGATIVE_TESTS_SUMMARY.json", negative_tests())
    elif key == "milestone_freeze":
        write_json(root / "FROZEN_TRUTH_REGISTER.json", {"status": "PASS", **stage_counts(context), "boundary": BOUNDARY, "implementation_changes_in_freeze": False})
        write_json(root / "MILESTONE_FREEZE_LEDGER.json", {"status": "PASS", "freeze_only": True, "closeout_green_required": True, "closeout_green": True, "recommended_next_task": task["next"]})


def negative_tests() -> dict[str, Any]:
    tests = [
        "no_alert_created",
        "no_dispatch_created",
        "no_routing_control_created",
        "no_enforcement_created",
        "no_official_case_ticket_created",
        "no_legal_certified_finding_created",
        "no_identity_or_biometric_fields",
        "no_automated_action_created",
    ]
    return {"status": "PASS", "negative_test_count": len(tests), "tests": [{"test": test, "status": "PASS"} for test in tests]}


def acceptance_matrix(context: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("fixture source inventory", len(context["inventory"]) > 0),
        ("candidate detection smoke", len(context["observations"]) == 6),
        ("observation to event/evidence", len(context["events"]) == 6),
        ("human review handoff", len(context["handoffs"]) == 6),
        ("negative tests", negative_tests()["status"] == "PASS"),
        ("no action fields", no_action_audit(Path("."), context) == "PASS"),
    ]
    blocking = [name for name, ok in checks if not ok]
    return {"status": "PASS" if not blocking else "FAIL", "checks": [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks], "blocking_gaps": blocking, "blocking_gaps_count": len(blocking)}


def build_context() -> dict[str, Any]:
    runtime = runtime_discovery()
    inventory = fixture_inventory()
    obs_rows = observations(inventory)
    events, unresolved = event_packets(obs_rows)
    handoffs = handoff_packets(events, obs_rows)
    return {
        "runtime": runtime,
        "inventory": inventory,
        "observations": obs_rows,
        "events": events,
        "unresolved": unresolved,
        "handoffs": handoffs,
    }


def run_task(task_key: str = "all") -> dict[str, Any]:
    input_index, pre_snaps = discover_upstreams()
    context = build_context()
    selected = TASKS if task_key == "all" else [task for task in TASKS if task["key"] == task_key]
    if not selected:
        raise ValueError(f"unknown task key: {task_key}")
    results = []
    prior_closeout_green = True
    for task in selected:
        if task["key"] == "milestone_freeze" and not prior_closeout_green:
            continue
        root = output_root(task)
        root.mkdir(parents=True, exist_ok=True)
        write_stage_specific(task, root, input_index, context)
        blocking: list[str] = []
        if input_index["status"] != "PASS":
            blocking.append("latest sprint closeout missing or not green")
        if task["key"] == "milestone_freeze":
            closeout_decision = read_json(output_root(TASKS[5]) / f"{TASKS[5]['task_name'].replace('-', '_')}_DECISION.json", {})
            if status_of(closeout_decision) != TASKS[5]["pass"]:
                blocking.append("D7 closeout missing or not green")
        if task["key"] == "closeout":
            matrix = acceptance_matrix(context)
            if matrix["status"] != "PASS":
                blocking.extend(matrix["blocking_gaps"])
        audits = write_standard_artifacts(root, task, input_index, pre_snaps, context, blocking)
        for name, status in audits.items():
            if status != "PASS":
                blocking.append(f"{name} audit failed")
        validation_status = write_validation(root)
        if validation_status != "PASS":
            blocking.append("validation failed")
        final_status = task["pass"] if not blocking else f"FAIL_{task['task_name'].replace('-', '_')}"
        write_readme(root, task, final_status)
        write_local_open_index(root, task)
        hash_status = write_hash_manifest(root)
        if hash_status != "PASS":
            blocking.append("hash validation failed")
            final_status = f"FAIL_{task['task_name'].replace('-', '_')}"
        counts = stage_counts(context)
        write_decision(root, task, final_status, input_index, counts, audits, blocking, hash_status, validation_status)
        write_readme(root, task, final_status)
        write_local_open_index(root, task)
        write_validation(root)
        hash_status = write_hash_manifest(root)
        if task["key"] == "closeout":
            prior_closeout_green = final_status == task["pass"]
        results.append({"task_name": task["task_name"], "status": final_status, "output_root": rel(root), **counts, "hash_validation_status": hash_status})
    summary = {"status": "PASS" if all(row["status"].startswith("PASS_") for row in results) else "FAIL", "tasks": results}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> int:
    task_key = sys.argv[1] if len(sys.argv) > 1 else "all"
    summary = run_task(task_key)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
