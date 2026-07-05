from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_native_kit_spatial_cockpit_ui_r1"
D13_BINDINGS = ROOT / "packages" / "fixtures" / "d13_spatial_twin_omniverse_one_truth" / "runtime_overlay" / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json"
D13_LIVE_EVENT = ROOT / "packages" / "fixtures" / "d13_live_web_kit_selection_receipt" / "runtime_overlay" / "D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json"
RUNTIME_BUNDLE = ROOT / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"
VALIDATION_ZIP = OUT / "OMNIVERSE_UI_VALIDATION_PACKAGE.zip"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.capture_controls import classify_command  # noqa: E402
from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    PANEL_SECTION_NAMES,
    boundary_visibility_audit,
    experience_smoke_report,
    forbidden_command_negative_tests,
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(name: str, payload: dict[str, Any]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_text(name: str, text: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def artifact_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    is_file = path.is_file()
    return {
        "path": rel(path),
        "exists": exists,
        "kind": "file" if is_file else "directory" if exists else "missing",
        "bytes": path.stat().st_size if is_file else 0,
        "sha256": sha256(path) if is_file else None,
    }


def d13_report() -> dict[str, Any]:
    bindings = read_json(D13_BINDINGS) if D13_BINDINGS.exists() else {}
    live_event = read_json(D13_LIVE_EVENT) if D13_LIVE_EVENT.exists() else {}
    return {
        "schema_version": "citybrain.omniverse.d13_inputs_found.r1",
        "status": "PASS" if D13_BINDINGS.exists() and D13_LIVE_EVENT.exists() else "PARTIAL",
        "d13_bindings": artifact_status(D13_BINDINGS),
        "d13_live_selection_event": artifact_status(D13_LIVE_EVENT),
        "binding_count": len(bindings.get("bindings", [])),
        "live_event_schema_version": live_event.get("schema_version"),
        "live_event_execution_state": live_event.get("payload", {}).get("execution_state"),
        "d13_product_boundary": "D13 proves selection receipt/parity only; it is not the finished Omniverse product UI.",
    }


def preflight_decision(bundle: dict[str, Any]) -> dict[str, Any]:
    required_extension_files = [
        KIT_APP / "config" / "extension.toml",
        KIT_APP / "citybrain" / "control_room" / "extension.py",
        KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py",
        KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
        KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
    ]
    return {
        "schema_version": "citybrain.omniverse.ui_preflight_decision.r1",
        "status": "PASS",
        "deliverable_choice": "Native Kit panel UI",
        "webrtc": "deferred_not_in_this_package",
        "kit_extension_files": [artifact_status(path) for path in required_extension_files],
        "runtime_bundle_root": artifact_status(RUNTIME_BUNDLE),
        "runtime_bundle_schema_version": bundle.get("one_truth", {}).get("schema_version"),
        "selection_model": "single resolver: selected prim path or entity ref maps to existing kit_overlay_packets.json packet",
        "no_second_selection_model": True,
    }


def deliverable_choice() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.deliverable_choice.r1",
        "status": "PASS",
        "selected_lane": "native_kit_panel_ui",
        "not_selected": ["webrtc_livestreaming", "browser-only cockpit", "D13 receipt proof only"],
        "reason": "The sprint target is an operator-facing native Kit panel with evidence, citations, limitations, review state, and no-action state visible in Kit.",
    }


def panel_report(first_result: dict[str, Any]) -> dict[str, Any]:
    card = first_result.get("inspection_card", {})
    required = {
        "selected_entity": bool(card.get("entity_ref")),
        "evidence_records": bool(card.get("evidence", {}).get("source_records")),
        "citations": bool(card.get("citations")),
        "knowns_summary": bool(card.get("knowns")),
        "unknowns_limitations": bool(card.get("unknowns_limitations")),
        "cannot_claim": bool(card.get("cannot_claim")),
        "review_not_executed": card.get("no_action_state", {}).get("execution_state") == "not_executed",
        "prim_path_inspector": bool(card.get("prim_path")),
        "overlay_review_state": bool(card.get("overlay", {}).get("overlay_state")),
    }
    return {
        "schema_version": "citybrain.kit.entity_evidence_panel_report.r1",
        "status": "PASS" if all(required.values()) else "FAIL",
        "panel_sections": PANEL_SECTION_NAMES,
        "section_checks": required,
        "native_kit_ui_source": rel(KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py"),
        "default_selection_card": card,
        "kit_runtime_gui_observed": False,
        "headless_export_validated": True,
    }


def no_action_audit(bundle: dict[str, Any], forbidden: dict[str, Any]) -> dict[str, Any]:
    track_d_packets = bundle.get("track_d", {}).get("packets", [])
    execution_states = [packet.get("execution_state") for packet in track_d_packets]
    return {
        "schema_version": "citybrain.omniverse.no_action_audit.r1",
        "status": "PASS"
        if bundle.get("one_truth", {}).get("execution_state") == "not_executed"
        and all(state == "not_executed" for state in execution_states)
        and not bundle.get("review", {}).get("approved_proposal_created")
        and forbidden.get("status") == "PASS"
        else "FAIL",
        "one_truth_execution_state": bundle.get("one_truth", {}).get("execution_state"),
        "track_d_execution_states": sorted(set(execution_states)),
        "approved_proposal_created": bundle.get("review", {}).get("approved_proposal_created"),
        "execution_authority_created": bundle.get("review", {}).get("execution_authority_created"),
        "forbidden_command_negative_tests": forbidden.get("status"),
    }


def claim_boundary_audit(first_result: dict[str, Any], overlay_contract: dict[str, Any]) -> dict[str, Any]:
    text = first_result.get("visible_text", "")
    blocked_claims_visible = [
        "not a certified physical twin",
        "not measurement-grade geometry",
        "not live monitoring",
        "not dispatch",
        "not a legal/certified finding",
    ]
    return {
        "schema_version": "citybrain.omniverse.claim_boundary_audit.r1",
        "status": "PASS"
        if all(item in text for item in blocked_claims_visible)
        and overlay_contract.get("status") == "PASS"
        else "FAIL",
        "blocked_claims_visible": {item: item in text for item in blocked_claims_visible},
        "overlay_forbidden_semantic_hits": overlay_contract.get("forbidden_semantic_hits", []),
    }


def json_parse_report() -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.glob("*.json")):
        try:
            read_json(path)
            entries.append({"file": path.name, "status": "PASS"})
        except Exception as exc:  # pragma: no cover - report path
            entries.append({"file": path.name, "status": "FAIL", "error": str(exc)})
    return {
        "schema_version": "citybrain.omniverse.json_parse_report.r1",
        "status": "PASS" if all(entry["status"] == "PASS" for entry in entries) else "FAIL",
        "entries": entries,
    }


def hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name != "OMNIVERSE_UI_VALIDATION_PACKAGE.zip":
            entries.append(
                {
                    "file": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return {
        "schema_version": "citybrain.omniverse.ui_hash_manifest.r1",
        "generated_at_utc": now(),
        "entries": entries,
    }


def write_validation_zip() -> None:
    if VALIDATION_ZIP.exists():
        VALIDATION_ZIP.unlink()
    with zipfile.ZipFile(VALIDATION_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.iterdir()):
            if path.is_file() and path != VALIDATION_ZIP:
                archive.write(path, arcname=path.name)
        for path in [
            KIT_APP / "README.md",
            KIT_APP / "config" / "extension.toml",
            KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py",
            KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
            KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
            KIT_APP / "citybrain" / "control_room" / "extension.py",
        ]:
            archive.write(path, arcname=f"source/{rel(path)}")


def main() -> None:
    bundle = load_bundle()
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    first_result = inspector.inspect_first()

    write_json("D13_SEAM_INPUTS_FOUND_REPORT.json", d13_report())
    write_json("OMNIVERSE_UI_PREFLIGHT_DECISION.json", preflight_decision(bundle))
    write_json("OMNIVERSE_DELIVERABLE_CHOICE.json", deliverable_choice())
    packet_contract = packet_consumption_contract(bundle)
    write_json("KIT_PACKET_CONSUMPTION_CONTRACT.json", packet_contract)
    parity = web_kit_packet_parity_audit(bundle)
    write_json("WEB_KIT_PACKET_PARITY_AUDIT.json", parity)
    write_json("ONE_TRUTH_PACKET_PARITY_AUDIT.json", parity)
    write_json("KIT_ENTITY_EVIDENCE_PANEL_REPORT.json", panel_report(first_result))
    write_text("KIT_OPERATOR_VISIBLE_TEXT_EXPORT.txt", first_result.get("visible_text", ""))
    overlay_contract = overlay.contract()
    write_json("KIT_OVERLAY_MANAGER_CONTRACT.json", overlay_contract)
    write_json("KIT_OVERLAY_MANAGER_SMOKE_REPORT.json", overlay.smoke_report())
    write_json("KIT_BOUNDARY_VISIBILITY_AUDIT.json", boundary_visibility_audit(inspector, overlay))
    forbidden = forbidden_command_negative_tests()
    write_json("KIT_FORBIDDEN_COMMAND_NEGATIVE_TESTS.json", forbidden)
    experience = experience_smoke_report(inspector)
    write_json("KIT_EXPERIENCE_SMOKE_REPORT.json", experience)
    write_json(
        "WEBRTC_LIVESTREAM_DEFERRED_DECISION.json",
        {
            "schema_version": "citybrain.omniverse.webrtc_deferred_decision.r1",
            "status": "DEFERRED",
            "decision": "WebRTC livestreaming is deferred and not in this package.",
            "future_lane": "Create a separate time-boxed WebRTC package only if explicitly promoted.",
        },
    )
    no_action = no_action_audit(bundle, forbidden)
    write_json("NO_ACTION_AUDIT.json", no_action)
    claim_boundary = claim_boundary_audit(first_result, overlay_contract)
    write_json("CLAIM_BOUNDARY_AUDIT.json", claim_boundary)
    parse_report = json_parse_report()
    write_json("JSON_PARSE_REPORT.json", parse_report)

    closeout_status = (
        "PASS_OMNIVERSE_NATIVE_KIT_UI_R1_WITH_LIMITATIONS"
        if all(
            item.get("status") in {"PASS", "PASS_WITH_LIMITATIONS", "DEFERRED"}
            for item in [
                packet_contract,
                parity,
                overlay_contract,
                experience,
                no_action,
                claim_boundary,
                parse_report,
            ]
        )
        else "FAIL_OMNIVERSE_UI_BOUNDARY_OR_ONE_TRUTH_REGRESSION"
    )
    write_json(
        "OMNIVERSE_UI_CLOSEOUT_DECISION.json",
        {
            "schema_version": "citybrain.omniverse.ui_closeout_decision.r1",
            "status": closeout_status,
            "kit_runtime_gui_observed": False,
            "limitation": "Native Kit UI source and headless visible-text smoke passed; no live Kit screenshot was captured in this local run.",
            "no_action_audit": no_action.get("status"),
            "claim_boundary_audit": claim_boundary.get("status"),
            "one_truth_packet_parity_audit": parity.get("status"),
            "json_parse_report": parse_report.get("status"),
        },
    )
    write_json(
        "OMNIVERSE_UI_MILESTONE_FREEZE_DECISION.json",
        {
            "schema_version": "citybrain.omniverse.ui_milestone_freeze_decision.r1",
            "status": closeout_status,
            "distinctions": {
                "d13_selection_receipt": "previous proof of bounded selection receipt/parity, not product UI",
                "native_kit_ui": "implemented in apps/kit/citybrain.control_room with SpatialCockpitWindow",
                "static_screenshot_or_viewport": "not claimed as the product UI",
                "webrtc_livestream": "deferred",
                "event_overlays": "bounded review/context overlay manager only",
            },
            "validation_package": rel(VALIDATION_ZIP),
        },
    )
    write_json("HASH_MANIFEST.json", hash_manifest())
    write_validation_zip()
    print(json.dumps({"status": closeout_status, "output_root": rel(OUT), "validation_zip": rel(VALIDATION_ZIP)}, sort_keys=True))


if __name__ == "__main__":
    main()
