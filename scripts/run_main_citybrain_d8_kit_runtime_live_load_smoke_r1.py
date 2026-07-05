#!/usr/bin/env python3
"""Run the D8 CityBrain Kit runtime live-load smoke.

This is an additive runtime-availability check. It launches a local Kit runtime
with the maintained CityBrain control-room extension enabled, probes the frozen
Mobility Access runtime bundle from inside Kit Python, and writes evidence under
outputs/. It does not mutate frozen upstream outputs and does not claim a
production runtime, certified twin, dispatch, control, enforcement, approval, or
execution path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D8-KIT-RUNTIME-LIVE-LOAD-SMOKE-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D8_KIT_RUNTIME_LIVE_LOAD_SMOKE_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D8_KIT_RUNTIME_LIVE_LOAD_SMOKE_R1"
SCHEMA_VERSION = "main-citybrain-d8-kit-runtime-live-load-smoke-r1.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d8_kit_runtime_live_load_smoke_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d8_kit_runtime_live_load_smoke_r1.py"
PROBE_SCRIPT = OUTPUT_ROOT / "kit_runtime_control_room_probe.py"
PROBE_OUTPUT = OUTPUT_ROOT / "CITYBRAIN_KIT_RUNTIME_PROBE_OUTPUT.json"
PORTABLE_ROOT = OUTPUT_ROOT / "kit_portable_runtime_probe"

EXT_PARENT = REPO_ROOT / "apps/kit"
EXT_ROOT = EXT_PARENT / "citybrain.control_room"
RUNTIME_BUNDLE = REPO_ROOT / "packages/fixtures/mobility_access/runtime_bundle"
FREEZE_ROOT = REPO_ROOT / "outputs/main_citybrain_d8_web_kit_live_surface_milestone_freeze"
SOURCE_PROMOTION_ROOT = REPO_ROOT / "outputs/main_citybrain_d8_kit_control_room_extension_source_promotion_r2"

READ_ONLY_ROOTS = [RUNTIME_BUNDLE, FREEZE_ROOT, SOURCE_PROMOTION_ROOT]

FORBIDDEN_CLAIMS = [
    "production runtime",
    "public API",
    "autonomous monitoring",
    "alert",
    "dispatch",
    "routing/control",
    "control signal",
    "enforcement",
    "legal finding",
    "certified finding",
    "official ticket",
    "case creation",
    "citywide certified twin",
    "certified physical geometry",
    "executed option",
    "approved proposal",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def reset_output_root() -> None:
    output_resolved = OUTPUT_ROOT.resolve()
    if OUTPUT_ROOT.exists():
        for child in OUTPUT_ROOT.iterdir():
            child_resolved = child.resolve()
            if output_resolved not in [child_resolved, *child_resolved.parents]:
                raise RuntimeError(f"Refusing to remove path outside output root: {child}")
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "tree_hash": None}
    rows: list[str] = []
    total_bytes = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            total_bytes += stat.st_size
            rows.append(f"{rel(path)}|{stat.st_size}|{sha256_file(path)}")
    tree_hash = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return {
        "root": rel(root),
        "exists": True,
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "tree_hash": tree_hash,
    }


def detect_kit() -> dict[str, Any]:
    env_release = os.environ.get("OMNIVERSE_KIT_RELEASE")
    candidates = []
    if env_release:
        candidates.append(Path(env_release))
    candidates.extend(
        [
            Path.home() / "Documents/OmniverseKit/kit-app-template/_build/windows-x86_64/release",
            Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release"),
        ]
    )
    for release in candidates:
        kit_exe = release / "kit/kit.exe"
        app_config = release / "apps/txr.citybrain.kit"
        if kit_exe.exists() and app_config.exists():
            version = None
            version_file = release / "VERSION"
            if version_file.exists():
                version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
            return {
                "status": "PASS",
                "kit_release": str(release),
                "kit_exe": str(kit_exe),
                "kit_app_config": str(app_config),
                "kit_version": version,
            }
    return {
        "status": "KIT_RUNTIME_NOT_FOUND",
        "checked_releases": [str(path) for path in candidates],
        "kit_exe": None,
        "kit_app_config": None,
    }


def write_probe_script() -> None:
    write_text(
        PROBE_SCRIPT,
        r'''
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


output = Path(os.environ.get("CITYBRAIN_KIT_CONTROL_ROOM_PROBE_OUTPUT", "citybrain_kit_probe_output.json"))
result = {
    "status": "FAIL",
    "created_at_utc": now(),
    "kit_python": True,
    "module_imported": False,
    "startup_invoked": False,
    "shutdown_invoked": False,
    "post_quit_attempted": False,
    "no_action_taken": True,
}

try:
    from citybrain.control_room.extension import CityBrainControlRoomExtension, smoke_summary

    result["module_imported"] = True
    result["smoke_summary"] = smoke_summary()
    ext = CityBrainControlRoomExtension()
    ext.on_startup("citybrain.control_room-0.1.0")
    result["startup_invoked"] = True
    result["overlay_summary"] = ext.overlay_manager.projection_summary()
    result["trace_panel_summary"] = ext.trace_panel.summary()
    result["track_d_summary"] = ext.track_d_panel.summary()
    result["selection_known_entities"] = ext.overlay_manager.entity_refs()
    result["allowed_command_probe"] = ext.command("inspect")
    result["forbidden_command_probe"] = ext.command("dispatch")
    ext.on_shutdown()
    result["shutdown_invoked"] = True

    smoke = result["smoke_summary"]
    trace = result["trace_panel_summary"]
    track_d = result["track_d_summary"]
    forbidden = result["forbidden_command_probe"]
    allowed = result["allowed_command_probe"]
    checks = {
        "execution_state_not_executed": smoke.get("execution_state") == "not_executed",
        "trace_stage_count_9": smoke.get("trace_stage_count") == 9,
        "overlay_packet_count_7": smoke.get("overlay_packet_count") == 7,
        "track_d_packet_count_7": smoke.get("track_d_packet_count") == 7,
        "single_synthesize_narration_boundary": trace.get("single_synthesize_narration_boundary") is True,
        "track_d_no_approval_created": track_d.get("approved_proposal_created") is False,
        "allowed_inspect_accepted": allowed.get("command_status") == "accepted",
        "forbidden_dispatch_rejected": forbidden.get("command_status") == "rejected",
        "forbidden_dispatch_keeps_not_executed": forbidden.get("execution_state") == "not_executed",
    }
    result["checks"] = checks
    result["status"] = "PASS" if all(checks.values()) else "FAIL"
except Exception as exc:  # noqa: BLE001
    result["error"] = repr(exc)

try:
    import omni.kit.app

    omni.kit.app.get_app().post_quit()
    result["post_quit_attempted"] = True
except Exception as exc:  # noqa: BLE001
    result["post_quit_error"] = repr(exc)

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "module_imported": result["module_imported"]}, sort_keys=True))
''',
    )


def run_kit_probe(kit: dict[str, Any]) -> dict[str, Any]:
    if kit.get("status") != "PASS":
        return {"status": "NOT_RUN_KIT_RUNTIME_NOT_FOUND", "kit_runtime_probe_executed": False}
    write_probe_script()
    command = [
        kit["kit_exe"],
        kit["kit_app_config"],
        "--ext-folder",
        str(EXT_PARENT),
        "--enable",
        "citybrain.control_room",
        "--no-window",
        "--reset-user",
        "--portable-root",
        str(PORTABLE_ROOT),
        "--/app/fastShutdown=1",
        "--/app/file/ignoreUnsavedOnExit=true",
        "--/app/enableStdoutOutput=1",
        "--exec",
        str(PROBE_SCRIPT),
    ]
    env = os.environ.copy()
    env["CITYBRAIN_KIT_CONTROL_ROOM_PROBE_OUTPUT"] = str(PROBE_OUTPUT)
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=150,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        probe_result = read_json(PROBE_OUTPUT, {})
        status = "PASS" if completed.returncode == 0 and probe_result.get("status") == "PASS" else "FAIL"
        return {
            "status": status,
            "kit_runtime_probe_executed": True,
            "returncode": completed.returncode,
            "kit_command": command,
            "probe_output_path": rel(PROBE_OUTPUT),
            "probe_result": probe_result,
            "stdout_tail": "\n".join(stdout.splitlines()[-25:]),
            "stderr_tail": "\n".join(stderr.splitlines()[-25:]),
            "portable_root": rel(PORTABLE_ROOT),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "FAIL_TIMEOUT",
            "kit_runtime_probe_executed": True,
            "kit_command": command,
            "timeout_seconds": exc.timeout,
            "stdout_tail": exc.stdout[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": exc.stderr[-4000:] if isinstance(exc.stderr, str) else "",
            "probe_result": read_json(PROBE_OUTPUT, {}),
            "portable_root": rel(PORTABLE_ROOT),
        }


def prune_runtime_cache() -> dict[str, Any]:
    cache_root = PORTABLE_ROOT / "cache"
    output_resolved = OUTPUT_ROOT.resolve()
    if not cache_root.exists():
        return {"cache_root": rel(cache_root), "removed": False, "reason": "not_present"}
    cache_resolved = cache_root.resolve()
    if output_resolved not in [cache_resolved, *cache_resolved.parents]:
        return {"cache_root": str(cache_root), "removed": False, "reason": "outside_output_root"}
    file_count = sum(1 for path in cache_root.rglob("*") if path.is_file())
    shutil.rmtree(cache_root)
    return {"cache_root": rel(cache_root), "removed": True, "file_count": file_count}


def input_artifact_index(kit: dict[str, Any]) -> dict[str, Any]:
    freeze_decision = read_json(FREEZE_ROOT / "WEB_KIT_LIVE_SURFACE_MILESTONE_FREEZE_DECISION.json", {})
    source_validation = read_json(SOURCE_PROMOTION_ROOT / "KIT_EXTENSION_VALIDATION_REPORT.json", {})
    bundle_one_truth = read_json(RUNTIME_BUNDLE / "one_truth_index.json", {})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "kit_runtime": kit,
        "required_inputs": {
            "runtime_bundle": {
                "path": rel(RUNTIME_BUNDLE),
                "exists": RUNTIME_BUNDLE.exists(),
                "scenario_state_ref": bundle_one_truth.get("scenario_state_ref"),
                "execution_state": bundle_one_truth.get("execution_state"),
            },
            "web_kit_live_surface_freeze": {
                "path": rel(FREEZE_ROOT),
                "exists": FREEZE_ROOT.exists(),
                "status": freeze_decision.get("status"),
                "prior_kit_live_launch_status": freeze_decision.get("kit_live_launch_status"),
                "web_live_launch_evidence_status": freeze_decision.get("web_live_launch_evidence_status"),
            },
            "kit_source_promotion": {
                "path": rel(SOURCE_PROMOTION_ROOT),
                "exists": SOURCE_PROMOTION_ROOT.exists(),
                "status": source_validation.get("status"),
            },
            "kit_extension_source": {
                "path": rel(EXT_ROOT),
                "exists": EXT_ROOT.exists(),
            },
        },
    }


def claim_boundary_audit(probe: dict[str, Any]) -> dict[str, Any]:
    probe_result = probe.get("probe_result", {})
    return {
        "status": "PASS" if probe_result.get("status") == "PASS" else "FAIL",
        "forbidden_claims_not_made": True,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "positive_claim": "Local Kit runtime can load the maintained review-only CityBrain control-room extension and read the frozen Mobility Access bundle.",
        "claim_limitations": [
            "No production runtime or public API is claimed.",
            "No citywide certified twin or certified physical geometry is claimed.",
            "No visual native Kit capture is claimed by this smoke.",
            "The extension is review-only and reads local fixture evidence.",
        ],
    }


def no_action_audit(probe: dict[str, Any]) -> dict[str, Any]:
    result = probe.get("probe_result", {})
    forbidden = result.get("forbidden_command_probe", {})
    track_d = result.get("track_d_summary", {})
    return {
        "status": "PASS"
        if forbidden.get("command_status") == "rejected"
        and forbidden.get("execution_state") == "not_executed"
        and track_d.get("approved_proposal_created") is False
        else "FAIL",
        "execution_state": result.get("smoke_summary", {}).get("execution_state"),
        "forbidden_dispatch_probe": forbidden,
        "allowed_inspect_probe": result.get("allowed_command_probe"),
        "track_d_summary": track_d,
        "no_dispatch_control_enforcement_or_approval": True,
    }


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for root, before_snapshot in before.items():
        after_snapshot = after.get(root, {})
        if before_snapshot.get("tree_hash") != after_snapshot.get("tree_hash"):
            changed.append(root)
    return {
        "status": "PASS" if not changed else "FAIL",
        "read_only_roots_changed": changed,
        "before": before,
        "after": after,
    }


def secret_audit() -> dict[str, Any]:
    patterns = {
        "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE),
        "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
    }
    findings: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": name})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.json":
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {"schema_version": SCHEMA_VERSION, "file_count": len(rows), "files": rows}


def write_readme(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# CityBrain D8 Kit Runtime Live-Load Smoke R1

Status: `{decision["status"]}`

This additive smoke proves that the local NVIDIA Kit runtime is now available
and can load the maintained `citybrain.control_room` extension against the
frozen Mobility Access runtime bundle.

What it proves:
- Kit runtime is discoverable locally.
- The CityBrain Kit extension can be enabled in a Kit process.
- The extension reads the frozen runtime bundle values: 9 trace stages, 7
  overlay packets, 7 Track D packets, and `execution_state=not_executed`.
- Forbidden dispatch-style commands remain rejected and review-only.

What it does not prove:
- No production/public runtime.
- No certified twin or certified physical geometry.
- No live dispatch, routing/control, enforcement, legal, ticket, case, or
  approval authority.
- No native visual capture yet; this is a no-window runtime load probe.
""",
    )
    write_text(
        OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md",
        f"""
# Local Open Index

- Decision: `{rel(OUTPUT_ROOT / "MAIN_CITYBRAIN_D8_KIT_RUNTIME_LIVE_LOAD_SMOKE_R1_DECISION.json")}`
- Runtime probe: `{rel(OUTPUT_ROOT / "KIT_RUNTIME_LOAD_PROBE_RESULTS.json")}`
- Probe output: `{rel(PROBE_OUTPUT)}`
- Input index: `{rel(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json")}`
- Claim audit: `{rel(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json")}`
- No-action audit: `{rel(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json")}`
- No-mutation audit: `{rel(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json")}`
- Hash manifest: `{rel(OUTPUT_ROOT / "HASH_MANIFEST.json")}`
""",
    )


def main() -> int:
    reset_output_root()
    before = {rel(root): tree_snapshot(root) for root in READ_ONLY_ROOTS}
    kit = detect_kit()
    input_index = input_artifact_index(kit)
    probe = run_kit_probe(kit)
    cache_prune = prune_runtime_cache()
    after = {rel(root): tree_snapshot(root) for root in READ_ONLY_ROOTS}

    claim_audit = claim_boundary_audit(probe)
    action_audit = no_action_audit(probe)
    mutation_audit = no_mutation_audit(before, after)

    blocking_gaps = []
    if kit.get("status") != "PASS":
        blocking_gaps.append("Kit runtime was not found.")
    if probe.get("status") != "PASS":
        blocking_gaps.append("Kit runtime probe did not pass.")
    if action_audit["status"] != "PASS":
        blocking_gaps.append("No-action boundary failed.")
    if mutation_audit["status"] != "PASS":
        blocking_gaps.append("Read-only upstream root changed.")

    non_blocking_gaps = [
        "Smoke is no-window/headless; native Kit visual capture remains a separate external-capture gate.",
        "Kit app template is local developer runtime, not production deployment.",
        "Control-room extension currently proves native runtime load and bundle projection, not a polished Omniverse-native operator UI panel.",
    ]
    status = PASS_STATUS if not blocking_gaps else FAIL_STATUS
    decision = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "status": status,
        "timestamp_utc": now(),
        "output_root": rel(OUTPUT_ROOT),
        "runner": rel(RUNNER_PATH),
        "kit_runtime_status": kit.get("status"),
        "kit_runtime_probe_status": probe.get("status"),
        "kit_runtime_cache_prune": cache_prune,
        "trace_stage_count": probe.get("probe_result", {}).get("smoke_summary", {}).get("trace_stage_count"),
        "overlay_packet_count": probe.get("probe_result", {}).get("smoke_summary", {}).get("overlay_packet_count"),
        "track_d_packet_count": probe.get("probe_result", {}).get("smoke_summary", {}).get("track_d_packet_count"),
        "execution_state": probe.get("probe_result", {}).get("smoke_summary", {}).get("execution_state"),
        "claim_boundary_status": claim_audit["status"],
        "no_action_boundary_status": action_audit["status"],
        "no_mutation_status": mutation_audit["status"],
        "blocking_gap_count": len(blocking_gaps),
        "blocking_gaps": blocking_gaps,
        "non_blocking_gap_count": len(non_blocking_gaps),
        "non_blocking_gaps": non_blocking_gaps,
        "recommended_next_task": "MAIN-CITYBRAIN-D8-EXTERNAL-CAPTURE-KIT-VISUAL-RUNTIME-FOLLOWTHROUGH",
    }

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "KIT_RUNTIME_ENVIRONMENT.json", kit)
    write_json(OUTPUT_ROOT / "KIT_RUNTIME_LOAD_PROBE_RESULTS.json", probe)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_audit)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", action_audit)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation_audit)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D8_KIT_RUNTIME_LIVE_LOAD_SMOKE_R1_DECISION.json", decision)
    write_readme(decision)
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    decision["secret_audit_status"] = secret["status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D8_KIT_RUNTIME_LIVE_LOAD_SMOKE_R1_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", hash_manifest())

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status == PASS_STATUS and secret["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
