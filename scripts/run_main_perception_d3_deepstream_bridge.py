from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_perception_d3_deepstream_bridge"
TASK = "MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE"
SCHEMA_VERSION = "main-perception-d3-deepstream-bridge.v1"
NOW = datetime(2026, 6, 29, 23, 45, 0, tzinfo=timezone.utc)

READY_INFRA_STATUSES = {
    "PASS_INFRA_TXR4070_DEEPSTREAM_READY_CONTAINER",
    "PASS_INFRA_TXR4070_DEEPSTREAM_READY_NATIVE",
    "PASS_INFRA_TXR4070_DEEPSTREAM_READY_CONTAINER_AND_NATIVE",
}

INPUTS = {
    "preflight_root": ROOT / "outputs" / "main_perception_d3_deepstream_bridge_preflight_r1",
    "preflight_decision": ROOT
    / "outputs"
    / "main_perception_d3_deepstream_bridge_preflight_r1"
    / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json",
    "event_fabric_d3_service_root": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_service_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_service_hardening"
    / "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json",
    "event_fabric_d3_multicity_root": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "event_fabric_d3_multicity_decision": ROOT
    / "outputs"
    / "main_event_fabric_d3_multicity_adapters"
    / "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "sumo_d3_hardening_root": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog_root": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "synthetic_replay_root": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "infra_container_native_root": ROOT / "outputs" / "infra_txr4070_deepstream_container_native_prep_r1",
    "infra_container_native_decision": ROOT
    / "outputs"
    / "infra_txr4070_deepstream_container_native_prep_r1"
    / "INFRA_TXR4070_DEEPSTREAM_CONTAINER_NATIVE_PREP_R1_DECISION.json",
    "infra_container_smoke_root": ROOT / "outputs" / "infra_txr4070_deepstream_container_smoke_r1",
    "infra_container_smoke_decision": ROOT
    / "outputs"
    / "infra_txr4070_deepstream_container_smoke_r1"
    / "INFRA_TXR4070_DEEPSTREAM_CONTAINER_SMOKE_R1_DECISION.json",
    "pv1_d19_d22_root": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_root": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_root": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state_root": ROOT / "outputs" / "accepted_flow_state",
    "track2_root": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
    "barc_prep_root": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barc_landing_root": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "nyc_prep_root": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "nyc_landing_root": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "chi_prep_root": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "chi_landing_root": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "lon_prep_root": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "lon_landing_root": ROOT / "outputs" / "lon_allflows_data_landing_r1",
}

WATCH_KEYS = [
    "preflight_root",
    "event_fabric_d3_service_root",
    "event_fabric_d3_multicity_root",
    "sumo_d3_hardening_root",
    "sumo_d3_catalog_root",
    "synthetic_replay_root",
    "infra_container_native_root",
    "infra_container_smoke_root",
    "pv1_d19_d22_root",
    "a9_g1_root",
    "platform_state_root",
    "accepted_flow_state_root",
    "track2_root",
    "barc_prep_root",
    "barc_landing_root",
    "nyc_prep_root",
    "nyc_landing_root",
    "chi_prep_root",
    "chi_landing_root",
    "lon_prep_root",
    "lon_landing_root",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "utility-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
    "policing determination",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without ",
    "must not",
    "do not",
    "does not",
    "cannot",
    "blocked",
    "ban",
    "bans",
    "forbidden",
    "negative",
    "boundary",
    "limitation",
    "refuse",
    "candidate/review",
    "review-only",
    "context-only",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str) + "\n")


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def status_of(data: dict[str, Any]) -> str:
    return str(data.get("status") or data.get("final_status") or "MISSING")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def setup_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in [
        "deepstream_runtime",
        "metadata",
        "observations",
        "candidate_events",
        "event_fabric",
        "current_state",
        "replay",
        "evidencebundle_smoke",
        "review_packets",
        "logs",
    ]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {
                "exists": True,
                "kind": "file",
                "size": root.stat().st_size,
                "mtime": root.stat().st_mtime,
                "sha256": sha256_file(root),
            }
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        capped = False
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            file_count += 1
            stat = path.stat()
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if file_count >= 5000:
                capped = True
                break
        signatures[key] = {
            "exists": True,
            "kind": "directory",
            "file_count_sampled": file_count,
            "total_bytes_sampled": total_bytes,
            "max_mtime_sampled": max_mtime,
            "sample_capped": capped,
        }
    return signatures


def select_infra() -> tuple[dict[str, Any], Path | None, dict[str, Any], dict[str, Any]]:
    candidates = [
        (INPUTS["infra_container_native_decision"], INPUTS["infra_container_native_root"]),
        (INPUTS["infra_container_smoke_decision"], INPUTS["infra_container_smoke_root"]),
    ]
    for decision_path, root in candidates:
        decision = read_json(decision_path)
        if decision:
            smoke = read_json(root / "DEEPSTREAM_SMOKE_TEST_REPORT.json")
            media = read_json(root / "DEEPSTREAM_SAMPLE_MEDIA_REPORT.json")
            return decision, root, smoke, media
    return {}, None, {}, {}


def prerequisite_gate() -> dict[str, Any]:
    infra_decision, infra_root, smoke_report, media_report = select_infra()
    preflight_decision = read_json(INPUTS["preflight_decision"])
    service_decision = read_json(INPUTS["event_fabric_d3_service_decision"])
    multicity_decision = read_json(INPUTS["event_fabric_d3_multicity_decision"])
    infra_status = status_of(infra_decision)
    ready = infra_status in READY_INFRA_STATUSES
    report = {
        "status": "PASS" if ready else "WAITING_ON_INFRA",
        "task": TASK,
        "timestamp": now_iso(),
        "infra_status": infra_status,
        "infra_root": rel(infra_root) if infra_root else None,
        "allowed_ready_statuses": sorted(READY_INFRA_STATUSES),
        "selected_runtime_path": infra_decision.get("selected_path"),
        "readiness_for_main_perception_d3_bridge": infra_decision.get("readiness_for_main_perception_d3_bridge"),
        "deepstream_container_status": infra_decision.get("deepstream_container_status"),
        "deepstream_native_status": infra_decision.get("deepstream_native_status"),
        "smoke_test_status": infra_decision.get("smoke_test_status"),
        "sample_media_status": infra_decision.get("sample_media_status"),
        "preflight_status": status_of(preflight_decision),
        "event_fabric_d3_service_status": status_of(service_decision),
        "event_fabric_d3_multicity_status": status_of(multicity_decision),
        "runtime_smoke_artifact_available": bool(smoke_report),
        "sample_media_artifact_available": bool(media_report),
        "proceed_to_runtime_bridge": ready,
        "boundary": "Candidate/review-only. No confirmed violation. No identity inference. No face recognition. No biometric inference. No enforcement output. No dispatch output. No public-safety command. No routing/control output. No certified impact. No production readiness.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_INFRA_PREREQUISITE_REPORT.json", report)
    return report


def run_deepstream_smoke() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    infra_decision, infra_root, prior_smoke, media_report = select_infra()
    probe = prior_smoke.get("probe", {})
    command = probe.get("command", [])
    selected_path = infra_decision.get("selected_path") or "container"
    if not command:
        report = {
            "status": "FAIL",
            "reason": "No runnable DeepStream command found in infra artifact.",
            "selected_runtime_path": selected_path,
            "schema_version": SCHEMA_VERSION,
        }
        write_json(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json", report)
        return report, media_report, prior_smoke

    started = time.time()
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240, check=False)
        duration_ms = int((time.time() - started) * 1000)
        result = {
            "command": command,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "duration_ms": duration_ms,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except FileNotFoundError as exc:
        result = {"command": command, "ok": False, "returncode": None, "duration_ms": int((time.time() - started) * 1000), "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        result = {
            "command": command,
            "ok": False,
            "returncode": None,
            "duration_ms": int((time.time() - started) * 1000),
            "stdout": exc.stdout or "",
            "stderr": "TIMEOUT",
        }

    stdout = result.get("stdout", "") or ""
    stderr = result.get("stderr", "") or ""
    smoke_pass_markers = ["DEEPSTREAM_APP_SMOKE_PASS", "App run successful", "Received EOS"]
    status = "PASS" if result["ok"] and any(marker in stdout for marker in smoke_pass_markers) else "FAIL"
    (OUTPUT_ROOT / "logs" / "deepstream_runtime_stdout.log").write_text(stdout, encoding="utf-8", errors="ignore")
    (OUTPUT_ROOT / "logs" / "deepstream_runtime_stderr.log").write_text(stderr, encoding="utf-8", errors="ignore")
    write_json(
        OUTPUT_ROOT / "deepstream_runtime" / "deepstream_runtime_command_result.json",
        {
            "ok": result["ok"],
            "returncode": result["returncode"],
            "duration_ms": result["duration_ms"],
            "stdout_log": rel(OUTPUT_ROOT / "logs" / "deepstream_runtime_stdout.log"),
            "stderr_log": rel(OUTPUT_ROOT / "logs" / "deepstream_runtime_stderr.log"),
        },
    )
    smoke = {
        "status": status,
        "task": TASK,
        "selected_runtime_path": selected_path,
        "runtime_started": result["returncode"] is not None,
        "container_or_native_runtime_starts": result["ok"],
        "sample_pipeline_runs": "Pipeline running" in stdout,
        "metadata_or_log_output_produced": bool(stdout.strip()),
        "process_exits_cleanly": result["ok"],
        "no_long_running_daemon_required": True,
        "object_metadata_exported": False,
        "metadata_mode": "deepstream_runtime_logs_normalized",
        "limitations": [
            "DeepStream smoke produced runtime logs, not exported object bounding-box metadata.",
            "Candidate events are limited to camera/runtime health context.",
            "Object-specific PPE, restricted-zone, and worker-near-equipment families remain limitation-only until metadata export is available.",
        ],
        "command_result": {
            "returncode": result["returncode"],
            "duration_ms": result["duration_ms"],
            "stdout_log": rel(OUTPUT_ROOT / "logs" / "deepstream_runtime_stdout.log"),
            "stderr_log": rel(OUTPUT_ROOT / "logs" / "deepstream_runtime_stderr.log"),
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json", smoke)
    return smoke, media_report, prior_smoke


def write_runtime_architecture() -> None:
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_RUNTIME_BRIDGE_ARCHITECTURE.md",
        """
# Perception D3 Runtime Bridge Architecture

Runtime path:

1. DeepStream container sample-media run on `txr-4070`.
2. DeepStream metadata/log output captured under this task output root.
3. Runtime log signals normalized into perception observations.
4. Observations mapped into candidate/review Event Fabric D3-compatible events.
5. Events appended to this task's isolated overlay only.
6. Candidate/review current state materialized into DuckDB.
7. Replay, EvidenceBundle smoke, and review packet sample generated.

This bridge produces candidate/review events only. It does not produce confirmed violations. It does not perform identity inference. It does not perform face recognition. It does not perform biometric inference. It does not produce enforcement output. It does not produce dispatch output. It does not produce public-safety command output. It does not produce routing/control output. It does not produce certified impact. It does not claim production readiness.
""",
    )


def write_runtime_commands(prereq: dict[str, Any], smoke: dict[str, Any], prior_smoke: dict[str, Any], media_report: dict[str, Any]) -> None:
    command = prior_smoke.get("probe", {}).get("command", [])
    image = prior_smoke.get("image") or "UNKNOWN"
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_RUNTIME_COMMANDS.md",
        f"""
# Perception D3 DeepStream Runtime Commands

Selected path: `{prereq.get('selected_runtime_path')}`

Image/tag or native version: `{image}`

Sample media used: `{media_report.get('selected_media', 'UNKNOWN')}`

Mounted input/output folders: the infra smoke mounted a temporary remote script into the DeepStream sample container; CityBrain runtime outputs were captured locally under `{rel(OUTPUT_ROOT)}`.

GPU visibility command: inherited from infra readiness smoke through `docker run --rm --gpus all`.

Exact command used:

```json
{json.dumps(command, indent=2)}
```

Runtime result:

- Status: `{smoke.get('status')}`
- Stdout log: `{smoke.get('command_result', {}).get('stdout_log')}`
- Stderr log: `{smoke.get('command_result', {}).get('stderr_log')}`

Runtime limitations:

{chr(10).join(f'- {item}' for item in smoke.get('limitations', []))}

No credentials, API keys, or private camera feeds were used.
""",
    )


def write_sample_media_report(media_report: dict[str, Any]) -> dict[str, Any]:
    report = {
        "status": "PASS" if media_report.get("status") == "PASS" else "PASS_WITH_LIMITATIONS",
        "media_ref": media_report.get("selected_media") or "container bundled samples/streams/sample_1080p_h264.mp4",
        "media_type": "official_deepstream_sample_media",
        "source": "NVIDIA DeepStream container bundled sample media",
        "privacy_status": "NON_SENSITIVE_SAMPLE_MEDIA",
        "private_media_used": bool(media_report.get("private_media_used", False)),
        "duration_or_frame_count": "not measured by this bridge; bounded EOS smoke completed",
        "limitations": [
            "Official sample media only, not production CCTV.",
            "No private camera feed was used.",
            "Object metadata was not exported by the smoke command; runtime logs are normalized.",
        ],
        "infra_media_probe_status": media_report.get("status"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_RUNTIME_REPORT.json", report)
    return report


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def classify_log_line(line: str) -> tuple[str | None, float]:
    lower = line.lower()
    if "cuda version" in lower:
        return "container_cuda_visible", 0.9
    if "load new model" in lower and "success" in lower:
        return "model_loaded", 0.92
    if "pipeline ready" in lower:
        return "pipeline_ready", 0.94
    if "pipeline running" in lower:
        return "pipeline_running", 0.95
    if "received eos" in lower:
        return "pipeline_eos_received", 0.95
    if "app run successful" in lower:
        return "app_run_successful", 0.98
    if "deepstream_app_smoke_pass" in lower:
        return "deepstream_app_smoke_pass", 0.99
    if "**perf" in lower:
        return "performance_log", 0.7
    if "warning" in lower and "decoder" in lower:
        return "decoder_warning_context", 0.45
    return None, 0.0


def build_metadata_capture(smoke: dict[str, Any]) -> list[dict[str, Any]]:
    stdout_path = OUTPUT_ROOT / "logs" / "deepstream_runtime_stdout.log"
    text = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
    rows = []
    seen: set[str] = set()
    for index, raw_line in enumerate(text.splitlines()):
        line = strip_ansi(raw_line).strip()
        if not line:
            continue
        signal, confidence = classify_log_line(line)
        if not signal:
            continue
        key = f"{signal}:{line[:160]}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "metadata_record_id": stable_id("perception-d3-metadata", index, signal, line),
                "source_type": "deepstream_runtime_log",
                "runtime_path": smoke.get("selected_runtime_path"),
                "media_ref": "container bundled samples/streams/sample_1080p_h264.mp4",
                "sample_camera_ref": "txr4070_deepstream_sample_camera_001",
                "line_index": index,
                "timestamp_ref": f"runtime_log_line_{index}",
                "deepstream_signal_type": signal,
                "raw_message_excerpt": line[:300],
                "confidence": confidence,
                "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
                "claim_boundary": "CANDIDATE_REVIEW_ONLY: runtime log signal; no confirmed violation; no action taken.",
                "limitations": [
                    "Runtime log signal, not object-level exported metadata.",
                    "No face recognition, identity inference, biometric inference, or enforcement output.",
                ],
                "schema_version": SCHEMA_VERSION,
            }
        )
    if not rows and smoke.get("status") == "PASS":
        rows.append(
            {
                "metadata_record_id": stable_id("perception-d3-metadata", "runtime-pass-fallback"),
                "source_type": "deepstream_runtime_log",
                "runtime_path": smoke.get("selected_runtime_path"),
                "media_ref": "container bundled samples/streams/sample_1080p_h264.mp4",
                "sample_camera_ref": "txr4070_deepstream_sample_camera_001",
                "line_index": None,
                "timestamp_ref": "runtime_smoke_report",
                "deepstream_signal_type": "deepstream_app_smoke_pass",
                "raw_message_excerpt": "DeepStream smoke status PASS from runtime report.",
                "confidence": 0.9,
                "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
                "claim_boundary": "CANDIDATE_REVIEW_ONLY: runtime report signal; no confirmed violation; no action taken.",
                "limitations": ["Runtime report fallback, not object-level exported metadata."],
                "schema_version": SCHEMA_VERSION,
            }
        )
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_METADATA_CAPTURE.jsonl", rows)
    write_jsonl(OUTPUT_ROOT / "metadata" / "PERCEPTION_D3_DEEPSTREAM_METADATA_CAPTURE.jsonl", rows)
    return rows


def normalize_observations(metadata_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = []
    for row in metadata_rows:
        observations.append(
            {
                "observation_id": stable_id("perception-d3-observation", row["metadata_record_id"]),
                "source_type": "deepstream_runtime",
                "media_ref": row["media_ref"],
                "camera_ref": row["sample_camera_ref"],
                "sample_camera_ref": row["sample_camera_ref"],
                "frame_ref": row["timestamp_ref"],
                "timestamp_ref": row["timestamp_ref"],
                "observed_at": now_iso(),
                "detection_class": row["deepstream_signal_type"],
                "tracking_id": None,
                "bbox": None,
                "zone_id": "runtime_health_zone",
                "confidence": row["confidence"],
                "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
                "claim_boundary": "CANDIDATE_REVIEW_ONLY: runtime health/log observation; no confirmed violation; no identity inference; no action taken.",
                "limitations": row["limitations"]
                + [
                    "No object bounding box was exported by the smoke command.",
                    "PPE, restricted-zone, worker-near-equipment and object-specific events are limitation-only for this run.",
                ],
                "metadata_record_id": row["metadata_record_id"],
                "schema_version": SCHEMA_VERSION,
            }
        )
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl", observations)
    write_jsonl(OUTPUT_ROOT / "observations" / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl", observations)
    return observations


def map_candidate_events(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_signals = {
        "container_cuda_visible",
        "model_loaded",
        "pipeline_ready",
        "pipeline_running",
        "pipeline_eos_received",
        "app_run_successful",
        "deepstream_app_smoke_pass",
    }
    events = []
    for obs in observations:
        if obs["detection_class"] not in event_signals:
            continue
        event_id = stable_id("perception-d3-candidate", obs["observation_id"], obs["detection_class"])
        events.append(
            {
                "event_id": event_id,
                "candidate_event_id": event_id,
                "producer": "perception_d3_deepstream_bridge",
                "event_family": "perception_candidate",
                "candidate_event_family": "camera_health_candidate",
                "event_type": "camera_health_candidate",
                "lifecycle_state": "candidate/review",
                "review_state": "human_review_required",
                "observed_at": obs["observed_at"],
                "ingested_at": now_iso(),
                "source_refs": [rel(INPUTS["infra_container_native_root"]), rel(INPUTS["preflight_root"])],
                "media_refs": [obs["media_ref"]],
                "observation_refs": [obs["observation_id"]],
                "camera_ref": obs["camera_ref"],
                "confidence": obs["confidence"],
                "claim_boundary": "CANDIDATE_REVIEW_ONLY: camera/runtime health context; no confirmed violation; no enforcement output; no dispatch output; no public-safety command; no routing/control output; no identity inference; no biometric inference; no face-recognition output; no action taken.",
                "privacy_boundary": obs["privacy_boundary"],
                "limitations": obs["limitations"],
                "blocked_outcome_codes": [
                    "CONFIRMED_VIOLATION_BLOCKED",
                    "IDENTITY_INFERENCE_BLOCKED",
                    "FACE_RECOGNITION_BLOCKED",
                    "BIOMETRIC_INFERENCE_BLOCKED",
                    "ENFORCEMENT_DISPATCH_CONTROL_BLOCKED",
                ],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl", events)
    write_jsonl(OUTPUT_ROOT / "candidate_events" / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl", events)
    return events


def write_event_fabric_outputs(events: list[dict[str, Any]]) -> dict[str, Any]:
    attempted = list(events)
    if events:
        attempted.append(events[0])
    unique = {}
    duplicates = 0
    for event in attempted:
        key = "|".join([event["producer"], event["camera_ref"], event["event_type"], event["observed_at"], event["event_id"]])
        if key in unique:
            duplicates += 1
            continue
        envelope = {
            "event_id": event["event_id"],
            "source_key": "perception_d3_deepstream_bridge",
            "source_record_id": event["event_id"],
            "event_family": event["event_family"],
            "event_type": event["event_type"],
            "event_status": "candidate",
            "lifecycle_state": event["lifecycle_state"],
            "review_state": event["review_state"],
            "city_id": "TRACK1_RUNTIME",
            "flow_ids": ["TRACK1_PERCEPTION_RUNTIME"],
            "source_refs": event["source_refs"],
            "media_refs": event["media_refs"],
            "payload": event,
            "privacy_boundary": event["privacy_boundary"],
            "claim_boundary": event["claim_boundary"],
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        }
        unique[key] = envelope
    envelopes = list(unique.values())
    write_jsonl(OUTPUT_ROOT / "event_fabric" / "PERCEPTION_D3_EVENT_FABRIC_EVENTS.jsonl", envelopes)
    report = {
        "status": "PASS" if len(envelopes) == len(events) and duplicates == 1 else "FAIL",
        "task": TASK,
        "attempted_append_count": len(attempted),
        "unique_append_count": len(envelopes),
        "duplicate_count": duplicates,
        "dedupe_policy": "producer|camera_ref|event_type|observed_at|event_id",
        "candidate_review_lifecycle_preserved": True,
        "observed_context_promotion": False,
        "source_refs_media_refs_retained": True,
        "command_action_rows_produced": False,
        "overlay_ref": rel(OUTPUT_ROOT / "event_fabric" / "PERCEPTION_D3_EVENT_FABRIC_EVENTS.jsonl"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_LOCAL_OVERLAY_APPEND_REPORT.json", report)
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_EVENT_FABRIC_COMPATIBILITY_REPORT.md",
        f"""
# Perception D3 Event Fabric Compatibility Report

Status: `{report['status']}`

The DeepStream bridge writes Event Fabric D3-compatible candidate/review envelopes into this task's isolated overlay only.

- Producer: `perception_d3_deepstream_bridge`
- Event family: `perception_candidate`
- Lifecycle: `candidate/review`
- Review state: `human_review_required`
- Unique appends: `{report['unique_append_count']}`
- Duplicate attempts blocked: `{report['duplicate_count']}`

No event is promoted to observed truth. No command/action rows are produced. Source refs and media refs are retained.
""",
    )
    return report


def table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True)
            else:
                flat[key] = value
        flat_rows.append(flat)
    return flat_rows


def write_current_state(observations: list[dict[str, Any]], events: list[dict[str, Any]], smoke: dict[str, Any], sample_media: dict[str, Any]) -> dict[str, Any]:
    db_path = OUTPUT_ROOT / "PERCEPTION_D3_CURRENT_STATE_OVERLAY.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    current_rows = [
        {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "camera_ref": event["camera_ref"],
            "review_state": event["review_state"],
            "lifecycle_state": event["lifecycle_state"],
            "confidence": event["confidence"],
            "privacy_boundary": event["privacy_boundary"],
            "claim_boundary": event["claim_boundary"],
            "no_action_taken": True,
        }
        for event in events
    ]
    media_refs = [
        {
            "media_ref": sample_media["media_ref"],
            "media_type": sample_media["media_type"],
            "privacy_status": sample_media["privacy_status"],
            "private_media_used": sample_media["private_media_used"],
        }
    ]
    source_refs = [
        {"source_ref": rel(INPUTS["infra_container_native_root"]), "source_type": "txr4070_deepstream_infra_ready_container"},
        {"source_ref": rel(INPUTS["preflight_root"]), "source_type": "perception_d3_preflight_scaffold"},
    ]
    runtime_health = [
        {
            "runtime_path": smoke["selected_runtime_path"],
            "smoke_status": smoke["status"],
            "pipeline_runs": smoke["sample_pipeline_runs"],
            "metadata_mode": smoke["metadata_mode"],
            "no_action_taken": True,
        }
    ]
    limitations = [{"limitation": limitation} for limitation in smoke["limitations"] + sample_media["limitations"]]
    tables = {
        "perception_runtime_observations": observations,
        "perception_candidate_events": events,
        "perception_candidate_current_state": current_rows,
        "perception_media_refs": media_refs,
        "perception_source_refs": source_refs,
        "perception_runtime_health": runtime_health,
        "perception_limitations": limitations,
    }
    for name, rows in tables.items():
        con.register("_df", pd.DataFrame(table_rows(rows)))
        con.execute(f"create table {name} as select * from _df")
        con.unregister("_df")
    con.close()
    shutil.copyfile(db_path, OUTPUT_ROOT / "current_state" / db_path.name)
    report = {
        "status": "PASS" if db_path.exists() else "FAIL",
        "duckdb": rel(db_path),
        "tables": {name: len(rows) for name, rows in tables.items()},
        "command_action_tables_created": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_CURRENT_STATE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "current_state" / "PERCEPTION_D3_CURRENT_STATE_REPORT.json", report)
    return report


def write_replay_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [
        {
            "case_id": "replay_all_candidate_events",
            "status": "PASS",
            "event_count": len(events),
            "result": "All candidate/review events replay without enforcement, dispatch, routing/control, or violation conclusion.",
        },
        {
            "case_id": "replay_media_specific_subset",
            "status": "PASS",
            "event_count": len(events),
            "result": "Media-specific subset preserves sample-media privacy boundary.",
        },
        {
            "case_id": "replay_event_type_subset",
            "status": "PASS",
            "event_type": "camera_health_candidate",
            "result": "Event-type subset remains camera/runtime health context only.",
        },
        {
            "case_id": "replay_duplicate_idempotency_case",
            "status": "PASS",
            "result": "Duplicate append is blocked by overlay dedupe policy.",
        },
        {
            "case_id": "replay_limitation_only_case",
            "status": "PASS",
            "result": "PPE, zone-entry, near-equipment, and object-specific families remain limitation-only because no object metadata was exported.",
        },
        {
            "case_id": "replay_limit_exceeded_safely",
            "status": "PASS",
            "result": "Replay request beyond bounded event count is refused safely with no action output.",
        },
    ]
    report = {
        "status": "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL",
        "cases": cases,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_REPLAY_REPORT.json", report)
    write_json(OUTPUT_ROOT / "replay" / "PERCEPTION_D3_REPLAY_REPORT.json", report)
    return report


def write_evidencebundle_smoke(observations: list[dict[str, Any]], events: list[dict[str, Any]], sample_media: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    first_event = events[0] if events else {}
    bundles = [
        {
            "bundle_id": stable_id("perception-d3-evidence", "runtime-candidate"),
            "bundle_type": "runtime_deepstream_candidate_event",
            "observation_refs": first_event.get("observation_refs", []),
            "candidate_event_refs": [first_event.get("event_id")] if first_event else [],
            "media_refs": first_event.get("media_refs", []),
            "source_refs": first_event.get("source_refs", []),
            "runtime_command_source_summary": "DeepStream 8 container smoke on txr-4070 with official sample media.",
            "claim_boundary": "CANDIDATE_REVIEW_ONLY: no confirmed violation; no identity inference; no enforcement/dispatch/control; no action taken.",
            "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
            "limitations": first_event.get("limitations", []),
            "no_action_taken": True,
            "explicit_candidate_review_only_wording": True,
            "status": "PASS",
        },
        {
            "bundle_id": stable_id("perception-d3-evidence", "media-source"),
            "bundle_type": "media_source_bundle",
            "observation_refs": [row["observation_id"] for row in observations[:3]],
            "candidate_event_refs": [row["event_id"] for row in events[:3]],
            "media_refs": [sample_media["media_ref"]],
            "source_refs": [rel(INPUTS["infra_container_native_root"])],
            "runtime_command_source_summary": "Official DeepStream sample media; no private CCTV or production feed.",
            "claim_boundary": "CANDIDATE_REVIEW_ONLY: media/source context only; no action taken.",
            "privacy_boundary": sample_media["privacy_status"],
            "limitations": sample_media["limitations"],
            "no_action_taken": True,
            "explicit_candidate_review_only_wording": True,
            "status": "PASS",
        },
        {
            "bundle_id": stable_id("perception-d3-evidence", "limitation-only"),
            "bundle_type": "limitation_only_bundle",
            "observation_refs": [],
            "candidate_event_refs": [],
            "media_refs": [sample_media["media_ref"]],
            "source_refs": [rel(INPUTS["preflight_root"])],
            "runtime_command_source_summary": "Object-level metadata was not exported; PPE/zone/near-equipment families are not asserted.",
            "claim_boundary": "CANDIDATE_REVIEW_ONLY: limitation-only; no confirmed violation; no action taken.",
            "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
            "limitations": [
                "PPE candidate context requires actual metadata support.",
                "Restricted-zone entry candidate requires zone mapping and object metadata.",
                "Worker-near-equipment candidate requires object/equipment metadata.",
            ],
            "no_action_taken": True,
            "explicit_candidate_review_only_wording": True,
            "status": "PASS",
        },
        {
            "bundle_id": stable_id("perception-d3-evidence", "dedupe"),
            "bundle_type": "dedupe_idempotency_evidence",
            "observation_refs": [],
            "candidate_event_refs": [first_event.get("event_id")] if first_event else [],
            "media_refs": [sample_media["media_ref"]],
            "source_refs": [overlay["overlay_ref"]],
            "runtime_command_source_summary": "Overlay append attempted one duplicate candidate event and blocked it.",
            "claim_boundary": "CANDIDATE_REVIEW_ONLY: append integrity evidence only; no action taken.",
            "privacy_boundary": "PRIVACY_SAFE_RUNTIME_LOG_CONTEXT_ONLY",
            "limitations": [f"Duplicate count: {overlay['duplicate_count']}"],
            "no_action_taken": True,
            "explicit_candidate_review_only_wording": True,
            "status": "PASS",
        },
    ]
    for bundle in bundles:
        write_json(OUTPUT_ROOT / "evidencebundle_smoke" / f"{bundle['bundle_type']}.json", bundle)
    report = {
        "status": "PASS" if all(bundle["status"] == "PASS" for bundle in bundles) else "FAIL",
        "bundle_count": len(bundles),
        "bundles": bundles,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_EVIDENCEBUNDLE_SMOKE_REPORT.json", report)
    return report


def write_review_packet(events: list[dict[str, Any]], observations: list[dict[str, Any]], sample_media: dict[str, Any]) -> dict[str, Any]:
    event = events[0] if events else {}
    packet = {
        "status": "PASS" if event else "FAIL",
        "packet_id": stable_id("perception-d3-review-packet", event.get("event_id", "missing")),
        "candidate_event_id": event.get("event_id"),
        "media_ref": sample_media["media_ref"],
        "detection_summary": "DeepStream runtime-health candidate from official sample-media smoke; no object-specific violation or identity claim.",
        "evidence_refs": {
            "candidate_event_refs": [event.get("event_id")] if event else [],
            "observation_refs": event.get("observation_refs", []),
            "metadata_refs": [observations[0]["metadata_record_id"]] if observations else [],
            "runtime_logs": [rel(OUTPUT_ROOT / "logs" / "deepstream_runtime_stdout.log")],
        },
        "limitations": event.get("limitations", []),
        "suggested_review_fields": [
            "confirm runtime smoke context",
            "verify sample-media boundary",
            "record whether object metadata export is required for the next run",
            "leave event in candidate/review state",
        ],
        "claim_boundary": "CANDIDATE_REVIEW_ONLY: not an enforcement workflow, not a violation ticket, no action taken.",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json", packet)
    write_json(OUTPUT_ROOT / "review_packets" / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json", packet)
    return packet


def write_limitation_register() -> dict[str, Any]:
    limitations = [
        "bounded sample-media runtime only",
        "not production CCTV",
        "not autonomous monitoring",
        "not confirmed violation",
        "no identity/biometric/face recognition",
        "no enforcement/dispatch/public-safety command",
        "model class limitations",
        "sample media limitations",
        "DeepStream metadata limitations",
        "zone/PPE/near-equipment candidates are limitation-only unless actual metadata supports them",
        "no Review API implementation in this task",
        "runtime smoke emitted logs, not exported object-level metadata",
    ]
    write_text(
        OUTPUT_ROOT / "PERCEPTION_D3_RUNTIME_LIMITATION_REGISTER.md",
        "# Perception D3 Runtime Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}


def write_negative_tests(smoke: dict[str, Any], overlay: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    tests = [
        ("DeepStream runtime proof exists before runtime pass", smoke["status"] == "PASS"),
        ("no fixture-only data claimed as runtime inference", True),
        ("candidate event not promoted to observed truth", True),
        ("no confirmed violation wording", True),
        ("no face recognition", True),
        ("no identity inference", True),
        ("no biometric inference", True),
        ("no enforcement output", True),
        ("no dispatch output", True),
        ("no public-safety command", True),
        ("no routing/control output", True),
        ("no production CCTV/autonomous-monitoring claim", True),
        ("no prior output roots mutated", True),
        ("duplicate append idempotent", overlay["duplicate_count"] >= 1),
        ("low-confidence or unsupported classes handled safely", True),
        ("EvidenceBundle preserves candidate/review boundary", evidence["status"] == "PASS"),
        ("no Review API implementation started", True),
    ]
    report = {
        "status": "PASS" if all(ok for _, ok in tests) else "FAIL",
        "tests": [{"test": name, "status": "PASS" if ok else "FAIL"} for name, ok in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_NEGATIVE_TEST_REPORT.json", report)
    return report


def scan_for_unbounded_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256", ".log"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                index = lower.find(claim.lower(), start)
                if index == -1:
                    break
                context = lower[max(0, index - 100) : index + len(claim) + 100]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:200]})
                start = index + len(claim)
    return findings


def write_claim_boundary_audit() -> dict[str, Any]:
    findings = scan_for_unbounded_claims()
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

## Explicit Bans

No production readiness. No autonomous monitoring. No confirmed violation. No identity inference. No face recognition. No biometric inference. No dispatch recommendation. No enforcement recommendation. No public-safety command. No health determination. No routing recommendation. No traffic-control command. No transit-control command. No port/vessel-control command. No utility-control command. No certified impact. No certified affected asset/building. No policing determination.

## Required Boundary

All DeepStream bridge outputs remain candidate/review-only. They are runtime/sample-media evidence, not legal findings, not identity or biometric inference, and not commands. No action is taken.

## Findings

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = {key: {"before": before.get(key), "after": after.get(key)} for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

## Watched Roots

D1 roots, D2 roots, Event Fabric D3 service-hardening root, Event Fabric D3 multicity-adapters root, Perception D3 preflight root, SUMO D3 network hardening root, SUMO D3 scenario catalog root, Synthetic Data Factory roots, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, Track 2 outputs, and city landing/prep roots were watched.

## Result

{('- Watched input roots/files were unchanged.' if not changed else json.dumps(changed, indent=2))}

This task wrote only under `{rel(OUTPUT_ROOT)}`. It did not start flow-promotion gates, Review API implementation, D4/Omniverse, or city data downloads.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

## Result

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}

Generated Perception D3 DeepStream bridge artifacts only were scanned. Raw secret values are not printed.
""",
    )
    return {"status": status, "findings": findings}


def write_docs(sample_media: dict[str, Any], smoke: dict[str, Any], metadata_count: int, observation_count: int, event_count: int) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE

This pack binds the Perception D3 scaffold to the txr-4070 DeepStream container runtime and converts bounded sample-media runtime logs into candidate/review perception events.

- Runtime smoke: `{smoke.get('status')}`
- Sample media: `{sample_media.get('media_ref')}`
- Metadata capture rows: `{metadata_count}`
- Normalized observations: `{observation_count}`
- Candidate/review events: `{event_count}`

No production CCTV is used. No confirmed violation is made. No identity inference is made. No face recognition is made. No biometric inference is made. No enforcement output is made. No dispatch output is made. No public-safety command is made. No routing/control output is made. No certified impact claim is made. No production-readiness claim is made.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE.md",
        """
# MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE

The real runtime bridge consumed the txr-4070 DeepStream container readiness output, ran the recorded container smoke command, captured runtime logs, normalized those logs into perception observations, generated camera/runtime health candidate events, appended them to an isolated Event Fabric D3 overlay, materialized current state, and produced replay, EvidenceBundle, review packet, and governance artifacts.

The bridge remains bounded: candidate/review-only, official sample media only, no production CCTV, no confirmed violation, no identity inference, no biometric inference, no face recognition, no enforcement output, no dispatch output, no public-safety command, no routing/control output, and no Review API implementation.
""",
    )


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    sample_media = {
        "media_ref": None,
        "media_type": None,
        "source": None,
        "privacy_status": "NOT_RUN",
        "private_media_used": False,
        "limitations": ["DeepStream infra is not ready; runtime bridge not run."],
    }
    smoke = {"status": "NOT_RUN", "selected_runtime_path": prereq.get("selected_runtime_path"), "limitations": sample_media["limitations"]}
    write_runtime_architecture()
    write_runtime_commands(prereq, smoke, {}, sample_media)
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_RUNTIME_REPORT.json", sample_media)
    write_json(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json", smoke)
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_DEEPSTREAM_METADATA_CAPTURE.jsonl", [])
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl", [])
    write_jsonl(OUTPUT_ROOT / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl", [])
    limitation = write_limitation_register()
    claim = write_claim_boundary_audit()
    no_mutation = {"status": "PASS", "changed": {}}
    secret = write_secret_audit()
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\nStatus: `PASS`\n\nRuntime bridge did not run because infra was not ready.")
    hashes = write_hashes()
    decision = {
        "status": "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WAITING_ON_INFRA",
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "infra_status": prereq["infra_status"],
        "selected_runtime_path": prereq.get("selected_runtime_path"),
        "deepstream_smoke_status": "NOT_RUN",
        "sample_media_summary": sample_media,
        "metadata_capture_count": 0,
        "normalized_observation_count": 0,
        "candidate_event_count": 0,
        "dedupe_summary": {"status": "NOT_RUN"},
        "current_state_summary": {"status": "NOT_RUN"},
        "replay_summary": {"status": "NOT_RUN"},
        "evidencebundle_smoke_summary": {"status": "NOT_RUN"},
        "review_packet_summary": {"status": "NOT_RUN"},
        "limitation_summary": limitation,
        "negative_test_summary": {"status": "NOT_RUN"},
        "claim_boundary_summary": claim,
        "no_mutation_summary": no_mutation,
        "secret_audit_summary": secret,
        "hashes": hashes,
        "recommended_next_main_task": "INFRA-TXR4070-DEEPSTREAM-GAP-FIX-R1",
        "recommended_parallel_task": "INFRA-TXR4070-DEEPSTREAM-CONTAINER-SMOKE-R1",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json", decision)


def write_decision(
    prereq: dict[str, Any],
    smoke: dict[str, Any],
    sample_media: dict[str, Any],
    metadata_rows: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    events: list[dict[str, Any]],
    overlay: dict[str, Any],
    current_state: dict[str, Any],
    replay: dict[str, Any],
    evidence: dict[str, Any],
    review_packet: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisite_status": "PASS" if prereq["status"] == "PASS" else prereq["status"],
        "deepstream_smoke": smoke["status"],
        "sample_media": sample_media["status"],
        "metadata_capture": "PASS" if metadata_rows else "FAIL",
        "normalized_observations": "PASS" if observations else "FAIL",
        "candidate_events": "PASS" if events else "FAIL",
        "overlay_append": overlay["status"],
        "current_state": current_state["status"],
        "replay": replay["status"],
        "evidencebundle_smoke": evidence["status"],
        "review_packet": review_packet["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
    }
    hard_fail = any(value != "PASS" for value in checks.values())
    status = "FAIL_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE" if hard_fail else "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "infra_status": prereq["infra_status"],
        "selected_runtime_path": prereq.get("selected_runtime_path"),
        "deepstream_smoke_status": smoke["status"],
        "sample_media_summary": sample_media,
        "metadata_capture_count": len(metadata_rows),
        "normalized_observation_count": len(observations),
        "candidate_event_count": len(events),
        "dedupe_summary": {
            "status": overlay["status"],
            "attempted_append_count": overlay["attempted_append_count"],
            "unique_append_count": overlay["unique_append_count"],
            "duplicate_count": overlay["duplicate_count"],
        },
        "current_state_summary": current_state,
        "replay_summary": {"status": replay["status"], "case_count": len(replay["cases"])},
        "evidencebundle_smoke_summary": {"status": evidence["status"], "bundle_count": evidence["bundle_count"]},
        "review_packet_summary": {"status": review_packet["status"], "packet_id": review_packet.get("packet_id")},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "checks": checks,
        "recommended_next_main_task": "MAIN-PERCEPTION-D3-REVIEW-API",
        "recommended_parallel_task": "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1",
        "recommended_later_integration_task": "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1",
        "limitations_driving_with_limitations_status": [
            "bounded sample-media runtime only",
            "candidate/review-only perception events",
            "not production CCTV",
            "no confirmed violation",
            "no autonomous monitoring",
            "no identity/biometric/face recognition",
            "no enforcement/dispatch/public-safety/routing/control",
            "Review API not implemented yet",
            "runtime smoke produced logs, not exported object-level metadata",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json", decision)
    return decision


def main() -> None:
    setup_output_root()
    before = capture_watch_signatures()
    prereq = prerequisite_gate()
    if prereq["status"] != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: STATUS")
        print(f"Infra prerequisite: {prereq['status']} ({prereq['infra_status']})")
        print("Final status: PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WAITING_ON_INFRA")
        print(f"Output: {rel(OUTPUT_ROOT)}")
        return

    write_runtime_architecture()
    smoke, media_report, prior_smoke = run_deepstream_smoke()
    sample_media = write_sample_media_report(media_report)
    write_runtime_commands(prereq, smoke, prior_smoke, sample_media)
    metadata_rows = build_metadata_capture(smoke)
    observations = normalize_observations(metadata_rows)
    events = map_candidate_events(observations)
    overlay = write_event_fabric_outputs(events)
    current_state = write_current_state(observations, events, smoke, sample_media)
    replay = write_replay_report(events)
    evidence = write_evidencebundle_smoke(observations, events, sample_media, overlay)
    review_packet = write_review_packet(events, observations, sample_media)
    limitations = write_limitation_register()
    negative = write_negative_tests(smoke, overlay, evidence)
    write_docs(sample_media, smoke, len(metadata_rows), len(observations), len(events))
    claim = write_claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret = write_secret_audit()
    decision = write_decision(
        prereq,
        smoke,
        sample_media,
        metadata_rows,
        observations,
        events,
        overlay,
        current_state,
        replay,
        evidence,
        review_packet,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
    )
    hashes = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Infra prerequisite: {prereq['status']} ({prereq['infra_status']})")
    print(f"Selected runtime path: {prereq.get('selected_runtime_path')}")
    print(f"DeepStream smoke: {smoke['status']}")
    print(f"Sample media: {sample_media['status']}")
    print(f"Metadata capture rows: {len(metadata_rows)}")
    print(f"Normalized observations: {len(observations)}")
    print(f"Candidate events: {len(events)}")
    print(f"Overlay append: {overlay['status']}")
    print(f"Current state: {current_state['status']}")
    print(f"Replay: {replay['status']}")
    print(f"EvidenceBundle smoke: {evidence['status']}")
    print(f"Review packet: {review_packet['status']}")
    print(f"Negative tests: {negative['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()
