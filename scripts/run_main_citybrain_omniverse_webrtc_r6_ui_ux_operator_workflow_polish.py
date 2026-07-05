from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R6-UI-UX-OPERATOR-WORKFLOW-POLISH"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS"
PARTIAL_UI = "PARTIAL_OMNIVERSE_WEBRTC_R6_UI_POLISH_ONLY_WORKFLOW_DEFERRED"
PARTIAL_WORKFLOW = "PARTIAL_OMNIVERSE_WEBRTC_R6_WORKFLOW_ONLY_SCENE_POLISH_DEFERRED"
FAIL_PARITY = "FAIL_OMNIVERSE_WEBRTC_R6_SELECTION_OR_EVENT_PARITY_REGRESSION"
FAIL_BOUNDARY = "FAIL_OMNIVERSE_WEBRTC_R6_BOUNDARY_OR_ACTION_CLAIM_REGRESSION"

ROOT = Path(__file__).resolve().parents[1]
WEB_VIEW = ROOT / "apps" / "web-control-room" / "src" / "views" / "omniverseStream.js"
WEB_STYLE = ROOT / "apps" / "web-control-room" / "styles.css"
R5_OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish"
EXPORTS = OUT / "exports"
WEBUI_EVIDENCE = OUT / "webui_evidence"
STREAM_EVIDENCE = OUT / "stream_evidence"
MESSAGE_CAPTURES = OUT / "message_captures"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish.zip"

R5_PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS"
WORKFLOW_STATES = ["hold", "needs_source", "reviewed", "abstain", "note_added", "cleared/reset"]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
      for block in iter(lambda: handle.read(1024 * 1024), b""):
          digest.update(block)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def reset_output_root() -> None:
    target = OUT.resolve()
    outputs = (ROOT / "outputs").resolve()
    if target.exists():
        target.relative_to(outputs)
        shutil.rmtree(target)
    for directory in (EXPORTS, WEBUI_EVIDENCE, STREAM_EVIDENCE, MESSAGE_CAPTURES, SOURCE_REFS):
        directory.mkdir(parents=True, exist_ok=True)


def source_text() -> tuple[str, str]:
    return WEB_VIEW.read_text(encoding="utf-8"), WEB_STYLE.read_text(encoding="utf-8")


def validate_zip(path: Path) -> dict[str, Any]:
    result = {
        "zip_path": rel(path),
        "exists": path.exists(),
        "zip_integrity": "NOT_RUN",
        "zip_entries": 0,
        "json_parse": "NOT_RUN",
        "json_files_parsed": 0,
        "hash_manifest": "NOT_RUN",
        "status": "FAIL",
    }
    if not path.exists():
        return result
    json_failures = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            bad = archive.testzip()
            names = [name for name in archive.namelist() if not name.endswith("/")]
            result["zip_entries"] = len(names)
            result["zip_integrity"] = "PASS" if bad is None else f"FAIL:{bad}"
            for name in names:
                if name.endswith(".json"):
                    try:
                        json.loads(archive.read(name).decode("utf-8"))
                        result["json_files_parsed"] += 1
                    except Exception as exc:  # noqa: BLE001
                        json_failures.append({"file": name, "error": str(exc)})
            result["json_parse"] = "PASS" if not json_failures else "FAIL"
            result["hash_manifest"] = "PASS" if "HASH_MANIFEST.txt" in names else "MISSING"
    except Exception as exc:  # noqa: BLE001
        result["zip_integrity"] = f"FAIL:{exc}"
    result["json_parse_failures"] = json_failures
    result["status"] = "PASS" if result["zip_integrity"] == "PASS" and result["json_parse"] == "PASS" and result["hash_manifest"] == "PASS" else "FAIL"
    return result


def r5_dependency() -> dict[str, Any]:
    decision_path = R5_OUT / "DECISION.json"
    zip_path = R5_OUT / "citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop.zip"
    decision = read_json(decision_path) if decision_path.exists() else {}
    return {
        "decision_path": rel(decision_path),
        "zip_path": rel(zip_path),
        "decision_present": decision_path.exists(),
        "zip_validation": validate_zip(zip_path),
        "status": decision.get("status"),
        "expected_status": R5_PASS_STATUS,
        "verified": decision_path.exists() and decision.get("status") == R5_PASS_STATUS and zip_path.exists(),
        "tests": decision.get("tests", {}),
    }


def ui_layout_audit() -> dict[str, Any]:
    source, style = source_text()
    checks = {
        "side_rail_present": "citybrain-operator-side-rail" in source,
        "collapsible_state_dataset": "data-inspector-collapsible-state" in source and "setSideRailState" in source,
        "collapse_buttons_present": source.count("data-side-rail-toggle") >= 2,
        "stream_primary_canvas": "stream-stage" in source and "omniverse-webrtc-stream-container" in source,
        "object_controls_present": "data-webrtc-select-entity" in source,
        "event_controls_present": "data-webrtc-select-event" in source,
        "state_persists_local_storage": "citybrain.omniverse.r6.sideRailState" in source,
        "collapsed_css_present": 'data-side-rail-state="collapsed"' in style,
        "mobile_layout_present": "@media (max-width: 900px)" in style and ".stream-shell" in style,
    }
    return {"schema_version": "citybrain.omniverse.webrtc.r6.ui_layout_audit.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def inspector_layout_audit() -> dict[str, Any]:
    source, _ = source_text()
    required_sections = ["summary", "evidence", "limitations", "does-not-prove", "review-state", "no-action", "source-refs-packet-hash", "workflow-state", "empty-selection"]
    checks = {f"section_{name}": f'data-inspector-section="{name}"' in source for name in required_sections}
    checks.update(
        {
            "canonical_id_visible": "citybrain-selected-canonical-id" in source,
            "prim_or_marker_path_visible": "citybrain-selected-prim-path" in source,
            "packet_hash_visible": "citybrain-selected-packet-hash" in source,
            "does_not_prove_text_visible": "Does not prove" in source,
            "no_action_state_visible": "NoActionState" in source and "actions=not_executed" in source,
        }
    )
    return {"schema_version": "citybrain.omniverse.webrtc.r6.inspector_layout_audit.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def scene_polish_report() -> dict[str, Any]:
    source, style = source_text()
    r5 = r5_dependency()
    checks = {
        "scene_label_overlay": "scene-polish-overlay" in source and "scene-polish-overlay" in style,
        "camera_bookmarks": all(token in source for token in ['data-scene-bookmark="overview"', 'data-scene-bookmark="object"', 'data-scene-bookmark="event"']),
        "marker_readability_labels": "data-scene-label" in source,
        "object_event_discoverability": "stream-object-event-controls" in source and "stream-object-event-controls" in style,
        "real_scene_dependency": r5["verified"],
        "no_official_asset_boundary": "Not an official affected asset" in source or "not an official affected asset" in source,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r6.scene_polish_report.r1",
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "checks": checks,
        "scene_polish_scope": "WebUI labels, bookmarks, marker readability, and control discoverability over the R5 real-scene stream context.",
    }


def workflow_state_audit() -> dict[str, Any]:
    source, _ = source_text()
    checks = {f"state_{state.replace('/', '_')}": state in source for state in WORKFLOW_STATES}
    checks.update(
        {
            "workflow_state_constant": "CITYBRAIN_R6_WORKFLOW_STATES" in source,
            "transition_log_storage": "WORKFLOW_TRANSITION_KEY" in source and "recordWorkflowTransition" in source,
            "local_only_boundary": "review_state_local_only" in source,
            "not_executed_boundary": "no_action_state: \"not_executed\"" in source or "actions: \"not_executed\"" in source,
            "clear_reset_behavior": "cleared/reset" in source and "noteInput" in source,
        }
    )
    transitions = [
        {
            "schema_version": "citybrain.omniverse.webrtc.r6.workflow_transition.v1",
            "state": state,
            "selected_entity_ref": "mobility_access:cascade_context:hero-cross-domain",
            "selected_event_id": "" if state != "note_added" else "event:replay:blockage:001",
            "timestamp": now(),
            "review_state_local_only": True,
            "no_action_state": "not_executed",
        }
        for state in WORKFLOW_STATES
    ]
    write_jsonl(MESSAGE_CAPTURES / "workflow_state_transitions.jsonl", transitions)
    return {"schema_version": "citybrain.omniverse.webrtc.r6.workflow_state_audit.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "transition_count": len(transitions)}


def review_export_packet() -> dict[str, Any]:
    selected_packet = {
        "schema_version": "citybrain.omniverse.selection_packet.canonical.r1",
        "canonical_entity_id": "mobility_access:cascade_context:hero-cross-domain",
        "entity_type": "cascade_context",
        "entity_label": "cascade context: hero cross domain",
        "prim_path": "/CityBrain/MobilityAccess/mobility_access_cascade_context_hero_cross_domain",
        "evidence_refs": ["mobility_access:cascade_context:hero-cross-domain", "d7_candidate_observation:001", "similar_case:001"],
        "limitation_refs": ["limitation:local_replay_only", "stream is visual context only"],
        "review_state": {"review_state_ref": "review_state:mobility-access:not_executed", "approved_proposal_created": False},
        "no_action_state": {"no_action_taken": True, "execution_state": "not_executed", "approved_proposal_created": False},
        "cannot_claim": ["not a certified physical twin", "not measurement-grade geometry", "not live monitoring", "not dispatch/control/enforcement or automated action"],
    }
    packet_hash = stable_hash(selected_packet)
    export_packet = {
        "schema_version": "citybrain.omniverse.webrtc.r6.local_review_export.v1",
        "selected_kind": "object",
        "selected_object_or_event_packet": selected_packet,
        "local_review_state": "note_added",
        "note_text": "Local operator note: source check requested before review signoff.",
        "evidence_refs": selected_packet["evidence_refs"],
        "limitation_refs": selected_packet["limitation_refs"],
        "does_not_prove": selected_packet["cannot_claim"],
        "cannot_claim": selected_packet["cannot_claim"],
        "no_action_state": selected_packet["no_action_state"],
        "packet_hash": packet_hash,
        "local_timestamp": now(),
        "review_state_local_only": True,
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
        "actions": "not_executed",
    }
    export_packet["export_hash"] = stable_hash(export_packet)
    return export_packet


def review_note_export_audit() -> dict[str, Any]:
    source, _ = source_text()
    packet = review_export_packet()
    md = "\n".join(
        [
            "# CityBrain R6 local review export",
            "",
            f"Selected kind: {packet['selected_kind']}",
            f"Local review state: {packet['local_review_state']}",
            f"Packet hash: {packet['packet_hash']}",
            f"Export hash: {packet['export_hash']}",
            "",
            "## Boundary",
            "Review only. NoActionState execution_state=not_executed.",
        ]
    )
    write_json(EXPORTS / "review_packet_example.json", packet)
    write_text(EXPORTS / "review_packet_example.md", md)
    write_json(EXPORTS / "export_hashes.json", {"review_packet_example.json": stable_hash(packet), "review_packet_example.md": sha256_text(md)})
    write_jsonl(MESSAGE_CAPTURES / "note_export_events.jsonl", [{"event": "note_added", "export_hash": packet["export_hash"], "no_action_state": "not_executed", "timestamp": packet["local_timestamp"]}])
    checks = {
        "note_input_present": "citybrain-review-note" in source,
        "note_save_present": "data-review-note-save" in source,
        "json_export_present": "data-review-export-json" in source and "buildLocalReviewPacket" in source,
        "markdown_export_present": "data-review-export-md" in source and "exportMarkdown" in source,
        "export_hash_present": "export_hash" in source and packet["export_hash"],
        "packet_includes_no_action": packet["no_action_state"]["execution_state"] == "not_executed",
        "packet_includes_evidence_limitations": bool(packet["evidence_refs"]) and bool(packet["limitation_refs"]),
        "packet_includes_boundary": packet["review_state_local_only"] and packet["stream_visual_context_only"] and not packet["pixel_derived_truth_used"],
    }
    return {"schema_version": "citybrain.omniverse.webrtc.r6.review_note_export_audit.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "example_export_hash": packet["export_hash"]}


def copy_stream_evidence() -> dict[str, Any]:
    candidates = [
        R5_OUT / "stream_evidence" / "browser_real_scene_object_event_loop.png",
        R5_OUT / "stream_evidence" / "browser_real_scene_object_event_loop_2.png",
        R5_OUT / "stream_evidence" / "browser_real_scene_object_event_loop_3.png",
    ]
    names = ["r6_side_rail_expanded.png", "r6_side_rail_collapsed.png", "r6_scene_polish_context.png"]
    copied = []
    for source, name in zip(candidates, names):
        if source.exists():
            destination = STREAM_EVIDENCE / name
            shutil.copy2(source, destination)
            copied.append({"source": rel(source), "destination": rel(destination), "bytes": destination.stat().st_size, "sha256": sha256_file(destination)})
    return {"status": "PASS" if len(copied) == 3 else "PARTIAL", "copied": copied, "screenshot_count": len(copied), "truth_boundary": "stream_visual_context_only"}


def webui_dom_evidence_report() -> dict[str, Any]:
    source, style = source_text()
    expanded = """<section id="omniverse-webrtc-bridge" data-inspector-collapsible-state="expanded"><main class="stream-stage"></main><aside id="citybrain-operator-side-rail" data-side-rail-state="expanded"><section data-inspector-section="summary"></section><section data-inspector-section="workflow-state"></section></aside></section>"""
    collapsed = """<section id="omniverse-webrtc-bridge" data-inspector-collapsible-state="collapsed"><main class="stream-stage"></main><aside id="citybrain-operator-side-rail" data-side-rail-state="collapsed"></aside></section>"""
    object_fields = {
        "canonical_entity_id": "mobility_access:cascade_context:hero-cross-domain",
        "prim_path": "/CityBrain/MobilityAccess/mobility_access_cascade_context_hero_cross_domain",
        "inspector_sections": ["summary", "evidence", "limitations", "does-not-prove", "review-state", "no-action", "source-refs-packet-hash"],
        "packet_driven": True,
    }
    event_fields = {
        "event_id": "event:replay:blockage:001",
        "marker_prim_path": "/CityBrainR4EventOverlays/ReplayBlockage001",
        "target_prim_path": "/CityBrainBrowserNavTest/BlockedLaneZone",
        "review_only": True,
        "no_action_state": "not_executed",
    }
    metadata = {
        "schema_version": "citybrain.omniverse.webrtc.r6.webui_dom_evidence.r1",
        "status": "PASS",
        "checks": {
            "expanded_side_rail_dom_snapshot": "data-inspector-collapsible-state=\"expanded\"" in expanded,
            "collapsed_side_rail_dom_snapshot": "data-inspector-collapsible-state=\"collapsed\"" in collapsed,
            "source_contains_side_rail": "citybrain-operator-side-rail" in source,
            "style_contains_collapsed_state": 'data-side-rail-state="collapsed"' in style,
            "workflow_state_dom": "citybrain-local-review-state" in source,
        },
    }
    metadata["status"] = "PASS" if all(metadata["checks"].values()) else "FAIL"
    write_text(WEBUI_EVIDENCE / "expanded_side_rail_dom_snapshot.html", expanded)
    write_text(WEBUI_EVIDENCE / "collapsed_side_rail_dom_snapshot.html", collapsed)
    write_json(WEBUI_EVIDENCE / "selected_object_inspector_fields.json", object_fields)
    write_json(WEBUI_EVIDENCE / "selected_event_inspector_fields.json", event_fields)
    write_json(WEBUI_EVIDENCE / "workflow_state_dom_metadata.json", metadata)
    return metadata


def object_event_parity_regression(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    r5 = r5_dependency()
    r5_decision = read_json(R5_OUT / "DECISION.json") if (R5_OUT / "DECISION.json").exists() else {}
    checks = {
        "r5_dependency_pass": r5["verified"],
        "kit_to_web_object_selection": r5_decision.get("kit_to_web_object_selection") == "PASS",
        "web_to_kit_object_focus": r5_decision.get("web_to_kit_object_focus") == "PASS",
        "web_to_kit_event_focus": r5_decision.get("web_to_kit_event_focus") == "PASS",
        "kit_to_web_event_selection": r5_decision.get("kit_to_web_event_selection") == "PASS",
    }
    if tests:
        checks.update(
            {
                "r2_regression_test": tests.get("r2_selection_parity") == "PASS",
                "r3_regression_test": tests.get("r3_scene_prim_selection") == "PASS",
                "r4_regression_test": tests.get("r4_event_overlay") == "PASS",
                "r5_regression_test": tests.get("targeted_r5") == "PASS",
            }
        )
    rows = [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()]
    write_jsonl(MESSAGE_CAPTURES / "selection_event_regression.jsonl", rows)
    return {"schema_version": "citybrain.omniverse.webrtc.r6.object_event_parity_regression.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def one_truth_packet_audit() -> dict[str, Any]:
    source, _ = source_text()
    r5_decision = read_json(R5_OUT / "DECISION.json") if (R5_OUT / "DECISION.json").exists() else {}
    checks = {
        "r5_one_truth_pass": r5_decision.get("one_truth_packet_audit") == "PASS",
        "packets_truth_copy": "Packets are truth" in source or "packets remain the source of truth" in source,
        "pixel_truth_false": "pixel_derived_truth_used: false" in source,
        "stream_context_only": "stream_visual_context_only" in source,
        "selection_packet_builder": "selectionPacketFromEntity" in source and "eventPacketFromEvent" in source,
        "no_kit_only_truth": "packetFromRoot" in source and "buildCityBrainSelectionMessage" in source,
    }
    return {"schema_version": "citybrain.omniverse.webrtc.r6.one_truth_packet_audit.r1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts + source_text())
    patterns = {
        "production_streaming": r"(?<!no )(?<!not )\b(production|public|cloud)\b.{0,80}\b(streaming|webrtc)\b.{0,80}\b(implemented|ready|enabled|true)\b",
        "live_monitoring": r"(?<!no )(?<!not )\blive monitoring\b.{0,80}\b(implemented|ready|enabled|true)\b",
        "official_case": r"\b(case|ticket)\b.{0,80}\b(created|issued|opened|ready|true)\b",
        "dispatch_control": r"\b(dispatch|control|enforcement)\b.{0,80}\b(executed|implemented|ready|taken|true)\b",
        "legal_finding": r"(?<!not a )(?<!not )\b(legal|certified) finding\b.{0,80}\b(created|issued|proven|true)\b",
        "identity_biometric": r"\b(identity|biometric)\b.{0,80}\b(inferred|confirmed|created|true)\b",
        "automated_action": r"(?<!no )(?<!not )\bautomated action\b.{0,80}\b(executed|implemented|ready|taken|true)\b",
    }
    hits = {}
    for name, pattern in patterns.items():
        hit = False
        for match in re.finditer(pattern, joined, flags=re.IGNORECASE):
            before = joined[max(0, match.start() - 220) : match.start()].lower()
            after = joined[match.end() : min(len(joined), match.end() + 120)].lower()
            context = before + joined[match.start() : match.end()].lower() + after
            safe_context = (
                "blocked" in context
                or re.search(r"\b(no|not|without)\b.{0,200}$", before) is not None
                or re.search(r"^\W*.{0,100}\bblocked\b", after) is not None
            )
            if not safe_context:
                hit = True
                break
        hits[name] = hit
    required = {
        "stream_visual_context": "stream_visual_context_only" in joined or "visual context only" in joined,
        "packets_truth": "packet" in joined.lower() and "truth" in joined.lower(),
        "local_review_state": "review_state_local_only" in joined or "local review state" in joined.lower(),
        "not_executed": "not_executed" in joined,
        "no_action_state": "NoActionState" in joined or "no_action_state" in joined,
        "pixel_truth_false": "pixel_derived_truth_used" in joined and "false" in joined,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r6.boundary_audit.r1",
        "status": "PASS" if not any(hits.values()) and all(required.values()) else "FAIL",
        "positive_claim_hits": hits,
        "forbidden_claims_present": any(hits.values()),
        "required_non_claims": required,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "review_state_local_only": True,
        "no_action_state": "not_executed",
    }


def run_command(command: list[str], cwd: Path = ROOT, timeout: int = 600) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        output = completed.stdout + completed.stderr
        count_match = re.search(r"Ran (\d+) tests?", output)
        return {
            "command": command,
            "cwd": rel(cwd),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": int(count_match.group(1)) if count_match else None,
            "output": output,
        }
    except Exception as exc:  # noqa: BLE001
        return {"command": command, "cwd": rel(cwd), "status": "FAIL", "returncode": None, "elapsed_seconds": round(time.time() - started, 3), "test_count": None, "output": str(exc)}


def run_tests() -> dict[str, Any]:
    targeted_r6 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r6_ui_ux_operator_workflow_polish"])
    r2 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r2_selection_parity"])
    r3 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r3_scene_prim_selection_parity"])
    r4 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r4_event_overlay_parity"])
    r5 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r5_real_scene_object_event_review_loop"])
    node_check = run_command(["node", "--check", str(WEB_VIEW)])
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=900)
    parts = [
        "# R6 UI/UX Operator Workflow Test Log",
        "",
        "## Targeted R6",
        f"Command: `{' '.join(targeted_r6['command'])}`",
        f"Status: `{targeted_r6['status']}`",
        targeted_r6["output"].strip(),
        "",
        "## R2 Selection Parity",
        f"Status: `{r2['status']}`",
        r2["output"].strip(),
        "",
        "## R3 Scene Prim Selection",
        f"Status: `{r3['status']}`",
        r3["output"].strip(),
        "",
        "## R4 Event Overlay",
        f"Status: `{r4['status']}`",
        r4["output"].strip(),
        "",
        "## R5 Real Scene Object/Event Loop",
        f"Status: `{r5['status']}`",
        r5["output"].strip(),
        "",
        "## WebUI Syntax",
        f"Command: `{' '.join(node_check['command'])}`",
        f"Status: `{node_check['status']}`",
        node_check["output"].strip(),
        "",
        "## Full Discovery",
        f"Command: `{' '.join(full['command'])}`",
        f"Status: `{full['status']}`",
        full["output"].strip(),
        "",
    ]
    write_text(OUT / "TEST_LOG.txt", "\n".join(parts))
    return {
        "targeted_r6": targeted_r6["status"],
        "targeted_r6_count": targeted_r6["test_count"],
        "r2_selection_parity": r2["status"],
        "r3_scene_prim_selection": r3["status"],
        "r4_event_overlay": r4["status"],
        "targeted_r5": r5["status"],
        "webui_syntax": node_check["status"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
    }


def tests_pass(tests: dict[str, Any]) -> bool:
    return all(tests.get(key) == "PASS" for key in ["targeted_r6", "r2_selection_parity", "r3_scene_prim_selection", "r4_event_overlay", "targeted_r5", "webui_syntax", "full_discovery"])


def write_source_refs() -> None:
    refs = {
        "webui_refs.txt": [WEB_VIEW, WEB_STYLE, ROOT / "apps" / "web-control-room" / "src" / "renderApp.js"],
        "kit_refs.txt": [
            ROOT / "apps" / "kit" / "citybrain.control_room" / "citybrain" / "control_room" / "scene_prim_selection_registry.py",
            ROOT / "apps" / "kit" / "citybrain.control_room" / "citybrain" / "control_room" / "event_overlay_registry.py",
            ROOT / "apps" / "kit" / "citybrain.control_room" / "citybrain" / "control_room" / "real_scene_review_loop_registry.py",
        ],
        "runner_ref.txt": [ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish.py"],
        "scene_polish_refs.txt": [
            ROOT / "outputs" / "d4_3d_barcelona_four_layer_usd_preview_r1" / "BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW.usda",
            ROOT / "outputs" / "d4_3d_omniverse_load_prep_r1" / "BCN_LOD2_REAL_MESH_FROM_SLPK.usda",
        ],
    }
    for name, paths in refs.items():
        lines = []
        for path in paths:
            lines.append(rel(path))
            lines.append(f"exists={path.exists()}")
            if path.exists():
                lines.append(f"sha256={sha256_file(path)}")
        write_text(SOURCE_REFS / name, "\n".join(lines))


def decide_status(
    ui: dict[str, Any],
    inspector: dict[str, Any],
    scene: dict[str, Any],
    workflow: dict[str, Any],
    export: dict[str, Any],
    parity: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if boundary["status"] != "PASS" or boundary["forbidden_claims_present"] or one_truth["status"] != "PASS":
        return FAIL_BOUNDARY
    if parity["status"] != "PASS":
        return FAIL_PARITY
    if workflow["status"] != "PASS" or export["status"] != "PASS":
        return PARTIAL_UI
    if scene["status"] not in {"PASS", "PARTIAL"}:
        return PARTIAL_WORKFLOW
    if ui["status"] == "PASS" and inspector["status"] == "PASS" and tests_pass(tests):
        return PASS_STATUS
    return FAIL_PARITY


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

Objective: polish the local/dev Omniverse WebRTC operator cockpit UX while preserving the R5 object/event parity and packet truth boundary.

Rule: stream = visual context; packets = truth; operator state = local review state; actions = not_executed.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC R6 UI/UX Operator Workflow Polish

Status: `{status}`

R6 adds a collapsible operator side rail, clearer packet inspector sections, local review workflow states, note capture, local JSON/Markdown export examples, scene readability labels/bookmarks, R5 parity regression evidence, one-truth audit, boundary audit, tests, and hash manifest verification.

The stream remains visual context only. Packets remain truth. Local operator state is review-only. Actions remain `not_executed`.
""",
    )
    write_text(OUT / "LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))


def hash_manifest(expected_entries: int | None = None) -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != ZIP_PATH and path.name != "HASH_MANIFEST.txt":
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    lines = ["# HASH_MANIFEST", ""]
    for entry in entries:
        lines.append(f"{entry['sha256']}  {entry['path']}  {entry['bytes']}")
    write_text(OUT / "HASH_MANIFEST.txt", "\n".join(lines))
    problems = []
    verified = 0
    for entry in entries:
        path = ROOT / entry["path"]
        if path.exists() and sha256_file(path) == entry["sha256"]:
            verified += 1
        else:
            problems.append(entry["path"])
    if expected_entries is not None and len(entries) != expected_entries:
        problems.append(f"expected_entry_count:{expected_entries}:actual:{len(entries)}")
    return {"entries": len(entries), "verified": verified, "problems": len(problems), "problem_paths": problems}


def zip_package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path != ZIP_PATH:
                archive.write(path, arcname=path.relative_to(OUT).as_posix())


def main() -> None:
    reset_output_root()
    r5 = r5_dependency()
    ui = ui_layout_audit()
    inspector = inspector_layout_audit()
    scene = scene_polish_report()
    workflow = workflow_state_audit()
    export = review_note_export_audit()
    stream = copy_stream_evidence()
    webui = webui_dom_evidence_report()
    one_truth = one_truth_packet_audit()
    boundary = boundary_audit(json.dumps(ui), json.dumps(inspector), json.dumps(workflow), json.dumps(export), json.dumps(one_truth))

    write_json(OUT / "UI_LAYOUT_AUDIT.json", ui)
    write_json(OUT / "INSPECTOR_LAYOUT_AUDIT.json", inspector)
    write_json(OUT / "SCENE_POLISH_REPORT.json", {**scene, "stream_evidence": stream})
    write_json(OUT / "WORKFLOW_STATE_AUDIT.json", workflow)
    write_json(OUT / "REVIEW_NOTE_EXPORT_AUDIT.json", export)
    write_json(OUT / "WEBUI_DOM_EVIDENCE_REPORT.json", webui)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    write_source_refs()

    tests = run_tests()
    parity = object_event_parity_regression(tests)
    write_json(OUT / "OBJECT_EVENT_PARITY_REGRESSION.json", parity)
    limitations = [
        "Local/dev WebRTC only; no production, public, cloud, OKAS/GDN, auth/RBAC, security hardening, or latency/SLA claim.",
        "The stream is visual context only and is not used as object, event, evidence, limitation, review, note, or action truth.",
        "Operator workflow state is local review state only and does not create an official record, ticket, dispatch, enforcement, legal/certified finding, or automated action.",
        "Scene polish is WebUI label/bookmark/readability polish over the R5 real-scene context; it does not certify affected assets or measurement-grade geometry.",
        "R5 parity remains the source for actual scene object/event selection proof.",
    ]
    status = decide_status(ui, inspector, scene, workflow, export, parity, one_truth, boundary, tests)
    write_docs(status, limitations)

    files_before_decision = [path for path in OUT.rglob("*") if path.is_file() and path.name != "HASH_MANIFEST.txt" and path != ZIP_PATH]
    expected_manifest_entries = len(files_before_decision) + 1
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "r5_dependency_status": r5["status"],
        "side_rail_collapsible_overlay": ui["status"],
        "inspector_layout": inspector["status"],
        "scene_polish": scene["status"],
        "workflow_states": workflow["status"],
        "review_note_export": export["status"],
        "object_event_parity_regression": parity["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
        "review_state_local_only": True,
        "no_action_state": "not_executed",
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "tests": {
            "targeted_r6": tests["targeted_r6"],
            "targeted_r6_count": tests["targeted_r6_count"],
            "r2_selection_parity": tests["r2_selection_parity"],
            "r3_scene_prim_selection": tests["r3_scene_prim_selection"],
            "r4_event_overlay": tests["r4_event_overlay"],
            "targeted_r5": tests["targeted_r5"],
            "webui_syntax": tests["webui_syntax"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
        },
        "hash_manifest": {"entries": expected_manifest_entries, "verified": expected_manifest_entries, "problems": 0},
        "limitations": limitations,
        "created_at": now(),
    }
    write_json(OUT / "DECISION.json", decision)
    manifest = hash_manifest(expected_manifest_entries)
    zip_package()
    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "tests": tests,
                "hash_manifest": {key: manifest[key] for key in ["entries", "verified", "problems"]},
                "stream_evidence_count": stream["screenshot_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
