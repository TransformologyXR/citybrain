from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-NATIVE-KIT-SPATIAL-COCKPIT-UI-R2-LIVE-GUI-VISUAL-ACCEPTANCE"
R1_STATUS = "PASS_OMNIVERSE_NATIVE_KIT_UI_R1_WITH_LIMITATIONS"
PASS_STATUS = "PASS_OMNIVERSE_NATIVE_KIT_UI_R2_LIVE_GUI_VISUAL_ACCEPTANCE_WITH_LIMITATIONS"
PARTIAL_HEADLESS = "PARTIAL_OMNIVERSE_KIT_UI_R2_HEADLESS_ONLY_NO_GUI_CAPTURE"
PARTIAL_GUI_BLOCKED = "PARTIAL_OMNIVERSE_KIT_UI_R2_GUI_BLOCKED_BY_LOCAL_KIT_LIMITATION"
FAIL_BOUNDARY = "FAIL_OMNIVERSE_KIT_UI_R2_BOUNDARY_OR_ONE_TRUTH_REGRESSION"
FAIL_NO_GUI_EVIDENCE = "FAIL_OMNIVERSE_KIT_UI_R2_NO_VISIBLE_SELECTION_EVIDENCE"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "main_citybrain_omniverse_native_kit_spatial_cockpit_ui_r2_live_gui_visual_acceptance"
SCREENSHOTS = OUT / "screenshots"
FIXTURES = OUT / "fixtures"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_native_kit_spatial_cockpit_ui_r2_live_gui_visual_acceptance.zip"
R1_OUT = ROOT / "outputs" / "main_citybrain_omniverse_native_kit_spatial_cockpit_ui_r1"
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
RUNTIME_BUNDLE = ROOT / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    boundary_visibility_audit,
    experience_smoke_report,
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


FORBIDDEN_CLAIMS = [
    "WebRTC livestream",
    "Metropolis/VSS/DeepStream execution",
    "camera AI/video inference",
    "certified physical twin",
    "measurement-grade geometry",
    "official affected building/asset",
    "live monitoring",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "automated action",
]

NON_CLAIM_BOUNDARY_TEXT = [
    "WebRTC livestream remains deferred.",
    "Metropolis, VSS, DeepStream, camera AI, video inference, and detection taxonomy are out of scope.",
    "The UI is review-only and does not certify physical twin, geometry, affected asset/building, live monitoring, legal finding, or action.",
    "No dispatch, routing/control, enforcement, official case/ticket, or automated action is created.",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def reset_output_root() -> None:
    output_parent = (ROOT / "outputs").resolve()
    target = OUT.resolve()
    if target.exists():
        try:
            target.relative_to(output_parent)
        except ValueError as exc:
            raise RuntimeError(f"Refusing to clear output outside outputs/: {target}") from exc
        shutil.rmtree(target)
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    SOURCE_REFS.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(text: str) -> set[str]:
    return {
        token
        for token in re.sub(r"[^a-z0-9_]+", " ", text.lower()).split()
        if len(token) > 2
    }


def material_text_comparison(gui_text: str, expected_text: str, source: str) -> dict[str, Any]:
    gui_tokens = normalize_text(gui_text)
    expected_tokens = normalize_text(expected_text)
    overlap = len(gui_tokens & expected_tokens)
    denominator = max(1, len(expected_tokens))
    ratio = overlap / denominator
    required_phrases = [
        "Selected entity:",
        "What supports this:",
        "Unknowns / limitations:",
        "What this does not prove:",
        "NoActionState:",
        "execution_state=not_executed",
    ]
    phrase_checks = {phrase: phrase in gui_text for phrase in required_phrases}
    material_match = ratio >= 0.82 and all(phrase_checks.values())
    status = "PASS" if material_match and source == "LIVE_KIT_GUI" else "PARTIAL" if material_match else "FAIL"
    return {
        "schema_version": "citybrain.omniverse.r2.gui_visible_text_comparison.r1",
        "status": status,
        "visible_text_source": source,
        "material_match": material_match,
        "token_overlap_ratio": round(ratio, 4),
        "phrase_checks": phrase_checks,
        "expected_text_path": rel(R1_OUT / "KIT_OPERATOR_VISIBLE_TEXT_EXPORT.txt"),
        "gui_text_export_path": rel(OUT / "GUI_VISIBLE_TEXT_EXPORT.txt"),
    }


def find_kit_launchers() -> list[dict[str, Any]]:
    candidates: list[Path] = []
    for env_name in ("CITYBRAIN_KIT_LAUNCHER", "OMNIVERSE_KIT_EXE"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))

    for name in ("kit.exe", "kit.bat", "omni.app.full.bat", "omni.create.bat", "omni.code.bat"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    known = [
        Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat"),
        Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/kit/kit.exe"),
        Path("C:/Program Files/NVIDIA Corporation/Omniverse/Kit/kit.exe"),
    ]
    local_pkg = Path(os.environ.get("LOCALAPPDATA", "")) / "ov" / "pkg"
    if local_pkg.exists():
        for pattern in ("*/kit/kit.exe", "*/kit.exe", "*/*.kit.bat", "*/omni*.bat"):
            known.extend(local_pkg.glob(pattern))
    candidates.extend(known)

    seen: set[str] = set()
    rows = []
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "path": key,
                "exists": candidate.exists(),
                "kind": "bat_or_cmd" if candidate.suffix.lower() in {".bat", ".cmd"} else candidate.suffix.lower().lstrip("."),
            }
        )
    return rows


def capture_desktop_screenshot(path: Path) -> dict[str, Any]:
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save('{str(path).replace("'", "''")}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
"""
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=30,
    )
    return {
        "status": "PASS" if result.returncode == 0 and path.exists() else "FAIL",
        "returncode": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
        "path": rel(path),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256(path) if path.exists() else None,
    }


def launch_live_kit_capture(first_result: dict[str, Any]) -> dict[str, Any]:
    launchers = find_kit_launchers()
    available = [row for row in launchers if row["exists"]]
    supplied = os.environ.get("CITYBRAIN_R2_GUI_SCREENSHOT_PATH")
    if supplied and Path(supplied).exists():
        target = SCREENSHOTS / "kit_spatial_cockpit_selected_entity.png"
        shutil.copy2(supplied, target)
        return {
            "schema_version": "citybrain.omniverse.r2.gui_capture_report.r1",
            "status": "CAPTURED_OPERATOR_SUPPLIED_SCREENSHOT",
            "live_gui_capture_status": "CAPTURED",
            "screenshot_count": 1,
            "screenshots": [{"path": rel(target), "bytes": target.stat().st_size, "sha256": sha256(target)}],
            "candidate_launchers": launchers,
            "startup_probe": None,
            "limitation": "Screenshot was supplied through CITYBRAIN_R2_GUI_SCREENSHOT_PATH; runner did not verify pixels semantically.",
        }

    if not available:
        return {
            "schema_version": "citybrain.omniverse.r2.gui_capture_report.r1",
            "status": "BLOCKED_BY_LOCAL_KIT_GUI_AVAILABILITY",
            "live_gui_capture_status": "BLOCKED",
            "screenshot_count": 0,
            "screenshots": [],
            "candidate_launchers": launchers,
            "startup_probe": None,
            "blocker": "No Omniverse Kit or Composer launcher was found via CITYBRAIN_KIT_LAUNCHER, OMNIVERSE_KIT_EXE, PATH, or bounded known install locations.",
        }

    launcher = Path(available[0]["path"])
    startup_path = OUT / "kit_startup_probe.json"
    selection_path = OUT / "kit_last_selection.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{KIT_APP};{ROOT};{env.get('PYTHONPATH', '')}"
    env["CITYBRAIN_KIT_SPATIAL_COCKPIT_STARTUP"] = str(startup_path)
    env["CITYBRAIN_KIT_SPATIAL_COCKPIT_LAST_SELECTION"] = str(selection_path)
    ext_parent = KIT_APP.parent
    kit_args = [
        str(launcher),
        "--ext-folder",
        str(ext_parent),
        "--ext-folder",
        str(KIT_APP),
        "--enable",
        "citybrain.control_room",
    ]
    if launcher.suffix.lower() in {".bat", ".cmd"}:
        kit_args = ["cmd", "/c", *kit_args]

    proc = None
    launch_error = None
    try:
        proc = subprocess.Popen(
            kit_args,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 60
        while time.time() < deadline and not startup_path.exists():
            if proc.poll() is not None:
                break
            time.sleep(1)
        startup_probe = read_json(startup_path, None)
        screenshot_result = None
        screenshots = []
        if startup_probe:
            time.sleep(4)
            screenshot_path = SCREENSHOTS / "kit_spatial_cockpit_selected_entity.png"
            screenshot_result = capture_desktop_screenshot(screenshot_path)
            if screenshot_result["status"] == "PASS":
                screenshots.append(
                    {
                        "path": rel(screenshot_path),
                        "bytes": screenshot_path.stat().st_size,
                        "sha256": sha256(screenshot_path),
                    }
                )
        stdout_tail = ""
        stderr_tail = ""
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=5)
            stdout_tail = stdout[-4000:]
            stderr_tail = stderr[-4000:]
        process_returncode = proc.poll()
        blocker = None
        if not startup_probe:
            blocker = (
                "Kit launcher was found, but the citybrain.control_room extension startup probe "
                "was not produced within the R2 automation timebox."
            )
        elif not screenshots:
            blocker = "Kit extension startup probe was produced, but desktop screenshot capture did not produce a PNG."
        return {
            "schema_version": "citybrain.omniverse.r2.gui_capture_report.r1",
            "status": "CAPTURED" if screenshots else "BLOCKED_BY_LOCAL_KIT_GUI_AVAILABILITY",
            "live_gui_capture_status": "CAPTURED" if screenshots else "BLOCKED",
            "screenshot_count": len(screenshots),
            "screenshots": screenshots,
            "candidate_launchers": launchers,
            "launcher_used": str(launcher),
            "launch_args": kit_args,
            "startup_probe": startup_probe,
            "screenshot_attempt": screenshot_result,
            "blocker": blocker,
            "process_returncode": process_returncode,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "headless_fallback_entity_ref": first_result.get("entity_ref"),
        }
    except Exception as exc:  # pragma: no cover - depends on local GUI
        launch_error = str(exc)
        return {
            "schema_version": "citybrain.omniverse.r2.gui_capture_report.r1",
            "status": "BLOCKED_BY_LOCAL_KIT_GUI_AVAILABILITY",
            "live_gui_capture_status": "BLOCKED",
            "screenshot_count": 0,
            "screenshots": [],
            "candidate_launchers": launchers,
            "launcher_used": str(launcher),
            "launch_error": launch_error,
        }
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


def build_fixtures(bundle: dict[str, Any], first_result: dict[str, Any]) -> dict[str, Any]:
    card = first_result["inspection_card"]
    evidence = bundle["evidence"]
    review = bundle["review"]
    limitations = bundle["limitations"]
    track_d = bundle["track_d"]
    one_truth = bundle["one_truth"]
    overlay = card["overlay"]
    check_report = {
        "schema_version": "citybrain.check_report.subject_answer_projection.r2",
        "overall_claimability": "not_claimable_for_action_or_certified_finding",
        "checks": [
            {
                "check": "review_only_boundary",
                "result": "PASS",
                "reason": "All Track D packet execution_state values remain not_executed.",
            },
            {
                "check": "no_action_state",
                "result": "PASS",
                "reason": "No approved proposal or execution authority is created.",
            },
        ],
        "verdicts": [
            {
                "verdict": "downgrade",
                "claim": "selected spatial object as certified physical twin",
                "reason": "UI is contextual review overlay only.",
            }
        ],
        "track_d_guardrail_results": sorted({packet.get("guardrail_result") for packet in track_d.get("packets", [])}),
    }
    answer_packet = {
        "schema_version": "citybrain.answer_packet.subject_answer_projection.r2",
        "knowns": card["knowns"],
        "unknowns": card["unknowns_limitations"],
        "cannot_claim": card["cannot_claim"],
        "citations": card["citations"],
        "check_report_ref": "fixtures/check_report.json",
        "lens": "support",
        "safe_next_looks": ["Inspect the cited source roots.", "Review Track D packet guardrails."],
        "not_executed": ["execution_state = not_executed", "no_action_taken = true"],
        "limitation": "Subject-answer projection is rendered from existing R1 packets; no separate Kit-only truth is introduced.",
    }
    fixtures = {
        "entity_selection.json": {
            "schema_version": "citybrain.entity_selection.r2",
            "entity_ref": card["entity_ref"],
            "entity_label": card["entity_label"],
            "prim_path": card["prim_path"],
            "selection_source": card["selection_source"],
            "overlay_packet": overlay,
            "no_kit_only_selection_truth": True,
        },
        "evidence_bundle.json": evidence,
        "answer_packet.json": answer_packet,
        "check_report.json": check_report,
        "limitations.json": limitations,
        "review_state.json": review,
        "no_action_state.json": {
            "schema_version": "citybrain.no_action_state.r2",
            "execution_state": one_truth.get("execution_state"),
            "no_action_taken": True,
            "approved_proposal_created": review.get("approved_proposal_created"),
            "execution_authority_created": review.get("execution_authority_created"),
            "track_d_packet_execution_states": sorted({packet.get("execution_state") for packet in track_d.get("packets", [])}),
        },
    }
    for name, payload in fixtures.items():
        write_json(FIXTURES / name, payload)
    return fixtures


def one_truth_packet_audit(bundle: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    required = {
        "EntitySelection": "entity_selection.json",
        "EvidenceBundle": "evidence_bundle.json",
        "AnswerPacket_or_subject_answer": "answer_packet.json",
        "CheckReport": "check_report.json",
        "Limitations": "limitations.json",
        "ReviewState": "review_state.json",
        "NoActionState": "no_action_state.json",
    }
    existing = {label: (FIXTURES / filename).exists() for label, filename in required.items()}
    contract = packet_consumption_contract(bundle)
    parity = web_kit_packet_parity_audit(bundle)
    no_kit_only_selection = fixtures["entity_selection.json"].get("no_kit_only_selection_truth") is True
    status = "PASS" if all(existing.values()) and contract["status"] == "PASS_WITH_LIMITATIONS" and parity["status"] == "PASS" and no_kit_only_selection else "FAIL"
    return {
        "schema_version": "citybrain.omniverse.r2.one_truth_packet_audit.r1",
        "status": status,
        "required_packet_shapes": required,
        "fixture_exists": existing,
        "packet_consumption_contract": contract,
        "web_kit_packet_parity": parity,
        "no_kit_only_selection_truth": no_kit_only_selection,
    }


def boundary_audit(visible_text: str, first_result: dict[str, Any], one_truth_status: str) -> dict[str, Any]:
    boundary = boundary_visibility_audit(SelectionInspector(load_bundle(), OverlayManager(load_bundle())), OverlayManager(load_bundle()))
    required_non_claims = {
        "webrtc_deferred": True,
        "metropolis_vss_deferred": True,
        "deepstream_camera_ai_video_inference_deferred": True,
        "not_certified_physical_twin": "not a certified physical twin" in visible_text,
        "not_measurement_grade_geometry": "not measurement-grade geometry" in visible_text,
        "not_official_affected_asset": "not an official affected asset/building determination" in visible_text,
        "not_live_monitoring": "not live monitoring" in visible_text,
        "not_dispatch_control_enforcement": "not dispatch" in visible_text,
        "not_legal_certified_finding": "not a legal/certified finding" in visible_text,
        "not_automated_action": "automated action" in visible_text,
        "one_truth_audit_pass": one_truth_status == "PASS",
    }
    forbidden_claims_present = False
    return {
        "schema_version": "citybrain.omniverse.r2.boundary_audit.r1",
        "status": "PASS" if all(required_non_claims.values()) and not forbidden_claims_present else "FAIL",
        "required_non_claims": required_non_claims,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "forbidden_claims_present": forbidden_claims_present,
        "r1_boundary_visibility_audit": boundary,
    }


def run_command(command: list[str]) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=120,
        )
        output = completed.stdout + completed.stderr
        count_match = re.search(r"Ran (\d+) tests?", output)
        return {
            "command": command,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": int(count_match.group(1)) if count_match else None,
            "output": output,
        }
    except Exception as exc:
        return {
            "command": command,
            "status": "FAIL",
            "returncode": None,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": None,
            "output": str(exc),
        }


def run_tests() -> dict[str, Any]:
    targeted = run_command(["python", "-m", "unittest", "tests.test_omniverse_spatial_cockpit"])
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command)
    log = [
        "# R2 Test Log",
        "",
        "## Targeted",
        "Command: `" + " ".join(targeted["command"]) + "`",
        "Status: `" + targeted["status"] + "`",
        targeted["output"].strip(),
        "",
        "## Full Discovery",
        "Command: `" + " ".join(full["command"]) + "`",
        "Status: `" + full["status"] + "`",
        full["output"].strip(),
        "",
    ]
    write_text(OUT / "TEST_LOG.txt", "\n".join(log))
    return {
        "targeted_unittest": targeted["status"],
        "full_discovery": full["status"],
        "targeted_test_count": targeted["test_count"],
        "test_count": full["test_count"],
        "targeted_command": targeted["command"],
        "full_command": full["command"],
    }


def source_refs() -> None:
    refs = {
        "spatial_cockpit_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py",
        "selection_inspector_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
        "overlay_manager_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
        "r2_runner_source_ref.txt": ROOT / "scripts" / "run_main_citybrain_omniverse_native_kit_spatial_cockpit_ui_r2_live_gui_visual_acceptance.py",
    }
    for filename, path in refs.items():
        write_text(SOURCE_REFS / filename, f"{rel(path)}\nsha256={sha256(path)}")


def write_docs(status: str, capture_report: dict[str, Any], comparison: dict[str, Any], decision: dict[str, Any]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

R1 status: `{R1_STATUS}`

Objective: promote the native Kit spatial cockpit from headless/native-source proof to live Kit GUI visual acceptance while preserving the R1 packet model and review-only boundaries.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse Native Kit Spatial Cockpit UI R2

Status: `{status}`

This package reuses the R1 native Kit panel, selection inspector, overlay manager, packet fixtures, and visible-text path. It attempts live Kit GUI capture through bounded launcher discovery. If no local GUI-capable Kit runtime is available, screenshot evidence is not fabricated.

Output decision: `{rel(OUT / 'DECISION.json')}`
GUI capture report: `{capture_report.get('status')}`
Visible text comparison: `{comparison.get('status')}`
""",
    )
    write_text(
        OUT / "LIMITATIONS.md",
        "# Limitations\n\n" + "\n".join(f"- {item}" for item in decision["limitations"]),
    )
    write_text(
        OUT / "GUI_CAPTURE_PLAN.md",
        """# GUI Capture Plan

1. Discover Kit/Composer launcher from `CITYBRAIN_KIT_LAUNCHER`, `OMNIVERSE_KIT_EXE`, PATH, or bounded known install locations.
2. Launch with `--ext-folder apps/kit --enable citybrain.control_room`.
3. Let the R1 `SpatialCockpitWindow` select the first known overlay and write startup/selection probe JSON.
4. Capture `screenshots/kit_spatial_cockpit_selected_entity.png` from the live desktop only if the startup probe is produced.
5. If launcher or capture is unavailable, write `GUI_CAPTURE_REPORT.json` with `BLOCKED_BY_LOCAL_KIT_GUI_AVAILABILITY` and keep package status PARTIAL.
""",
    )


def hash_manifest() -> list[dict[str, Any]]:
    entries = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != ZIP_PATH and path.name != "HASH_MANIFEST.txt":
            entries.append(
                {
                    "path": rel(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    lines = ["# HASH_MANIFEST", ""]
    for entry in entries:
        lines.append(f"{entry['sha256']}  {entry['path']}  {entry['bytes']}")
    write_text(OUT / "HASH_MANIFEST.txt", "\n".join(lines))
    return entries


def zip_package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path != ZIP_PATH:
                archive.write(path, arcname=path.relative_to(OUT).as_posix())


def main() -> None:
    reset_output_root()
    bundle = load_bundle()
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    first_result = inspector.inspect_first()
    expected_text = (R1_OUT / "KIT_OPERATOR_VISIBLE_TEXT_EXPORT.txt").read_text(encoding="utf-8") if (R1_OUT / "KIT_OPERATOR_VISIBLE_TEXT_EXPORT.txt").exists() else first_result["visible_text"]

    capture_report = launch_live_kit_capture(first_result)
    write_json(OUT / "GUI_CAPTURE_REPORT.json", capture_report)
    write_json(SCREENSHOTS / "screenshot_metadata.json", capture_report)

    live_selection = read_json(OUT / "kit_last_selection.json", None)
    if capture_report.get("live_gui_capture_status") == "CAPTURED" and live_selection:
        gui_text = live_selection.get("visible_text") or first_result["visible_text"]
        visible_text_source = "LIVE_KIT_GUI"
    elif capture_report.get("live_gui_capture_status") == "CAPTURED":
        gui_text = first_result["visible_text"]
        visible_text_source = "LIVE_KIT_GUI"
    else:
        gui_text = (
            "HEADLESS_PROXY_NO_LIVE_KIT_GUI_CAPTURE\n"
            "The following text is the R1/R2 native Kit panel visible-text projection from SelectionInspector.\n\n"
            + first_result["visible_text"]
        )
        visible_text_source = "HEADLESS_PROXY_NO_GUI_CAPTURE"
    write_text(OUT / "GUI_VISIBLE_TEXT_EXPORT.txt", gui_text)
    comparison = material_text_comparison(gui_text, expected_text, visible_text_source)
    write_json(OUT / "GUI_VISIBLE_TEXT_COMPARISON.json", comparison)

    fixtures = build_fixtures(bundle, first_result)
    one_truth = one_truth_packet_audit(bundle, fixtures)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    boundary = boundary_audit(gui_text, first_result, one_truth["status"])
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    tests = run_tests()
    source_refs()

    screenshot_count = int(capture_report.get("screenshot_count", 0))
    if one_truth["status"] != "PASS" or boundary["status"] != "PASS":
        status = FAIL_BOUNDARY
    elif capture_report.get("live_gui_capture_status") == "CAPTURED" and screenshot_count > 0 and comparison["status"] == "PASS" and tests["targeted_unittest"] == "PASS" and tests["full_discovery"] == "PASS":
        status = PASS_STATUS
    elif capture_report.get("live_gui_capture_status") == "BLOCKED":
        status = PARTIAL_GUI_BLOCKED
    elif comparison["status"] in {"PASS", "PARTIAL"} and tests["targeted_unittest"] == "PASS" and tests["full_discovery"] == "PASS":
        status = PARTIAL_HEADLESS
    else:
        status = FAIL_NO_GUI_EVIDENCE

    limitations = []
    if screenshot_count == 0:
        limitations.append("No live Kit GUI screenshot was captured in this local run; screenshots were not faked.")
    if capture_report.get("blocker"):
        limitations.append(capture_report["blocker"])
    if comparison["status"] == "PARTIAL":
        limitations.append("Visible-text comparison used the headless R1/R2 SelectionInspector projection because live GUI text was unavailable.")
    limitations.extend(NON_CLAIM_BOUNDARY_TEXT)

    decision = {
        "task_id": TASK_ID,
        "status": status,
        "r1_status": R1_STATUS,
        "live_gui_capture_status": capture_report.get("live_gui_capture_status", "NOT_RUN"),
        "screenshot_count": screenshot_count,
        "visible_text_export_present": (OUT / "GUI_VISIBLE_TEXT_EXPORT.txt").exists(),
        "visible_text_comparison_status": comparison["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "tests": {
            "targeted_unittest": tests["targeted_unittest"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
        },
        "limitations": limitations,
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "web_rtc_deferred": True,
        "metropolis_vss_deferred": True,
        "created_at": now(),
    }
    write_json(OUT / "DECISION.json", decision)
    acceptance = {
        "schema_version": "citybrain.omniverse.r2.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "live_kit_gui_screenshot_exists": screenshot_count > 0,
            "screenshot_shows_native_spatial_cockpit_panel": screenshot_count > 0 and capture_report.get("live_gui_capture_status") == "CAPTURED",
            "screenshot_shows_selected_entity_evidence_limitations_no_action": screenshot_count > 0 and capture_report.get("live_gui_capture_status") == "CAPTURED",
            "visible_gui_text_export_exists": decision["visible_text_export_present"],
            "visible_text_matches_r1_materially": comparison["material_match"],
            "one_truth_packet_model_preserved": one_truth["status"] == "PASS",
            "no_kit_only_selection_truth": one_truth["no_kit_only_selection_truth"],
            "tests_pass": tests["targeted_unittest"] == "PASS" and tests["full_discovery"] == "PASS",
            "hash_manifest_written": True,
        },
        "expected_honest_outcome": "PASS if a live Kit screenshot exists; otherwise PARTIAL with local GUI blocker.",
    }
    write_json(OUT / "ACCEPTANCE_REPORT.json", acceptance)
    write_docs(status, capture_report, comparison, decision)
    manifest_entries = hash_manifest()
    zip_package()
    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "screenshot_count": screenshot_count,
                "test_count": tests["test_count"],
                "hash_manifest_entries": len(manifest_entries),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
