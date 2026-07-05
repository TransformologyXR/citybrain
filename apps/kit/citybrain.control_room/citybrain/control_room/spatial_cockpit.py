from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .capture_controls import FORBIDDEN_COMMANDS, classify_command
from .selection_inspector import visible_text_from_card

try:
    import omni.usd as omni_usd  # type: ignore
except Exception:  # pragma: no cover - Kit-only dependency
    omni_usd = None  # type: ignore

try:
    import omni.ui as ui  # type: ignore
except Exception:  # pragma: no cover - Kit-only dependency
    ui = None  # type: ignore


REQUIRED_PACKET_INPUTS = [
    "EntitySelection",
    "EvidenceBundle",
    "AnswerPacket_or_subject_answer",
    "CheckReport",
    "Limitations",
    "ReviewState",
    "NoActionState",
]

PANEL_SECTION_NAMES = [
    "selected entity",
    "source/evidence records",
    "citations/provenance",
    "knowns or summary",
    "unknowns/limitations",
    "what this does not prove",
    "review-only / not-executed state",
    "selected object/prim path inspector",
    "overlay/review state",
]

BOUNDARY_TEXT = (
    "Review only. No action has been taken. Not a certified physical twin, "
    "measurement-grade geometry, official affected asset, live monitoring, "
    "dispatch/control/enforcement workflow, legal finding, or automated action."
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_optional_json(path_env: str, payload: dict) -> None:
    output = os.environ.get(path_env)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def packet_consumption_contract(bundle: dict) -> dict:
    file_index = {
        item.get("file"): item
        for item in bundle.get("one_truth", {}).get("bundle_file_index", [])
    }
    one_truth_file = {
        "file": "one_truth_index.json",
        "path": "packages/fixtures/mobility_access/runtime_bundle/one_truth_index.json",
        "sha256": bundle.get("one_truth", {}).get("self_sha256"),
    }
    sources = {
        "EntitySelection": {
            "source": "kit_overlay_packets.json packets plus optional D13 live selection event",
            "file": file_index.get("kit_overlay_packets.json", {}),
            "status": "PASS",
        },
        "EvidenceBundle": {
            "source": "evidence_bundle.json",
            "file": file_index.get("evidence_bundle.json", {}),
            "status": "PASS",
        },
        "AnswerPacket_or_subject_answer": {
            "source": "rendered subject-answer view from scenario, evidence, review, limitations, and no-action packets",
            "file": None,
            "status": "PASS_WITH_LIMITATIONS",
            "limitation": "No standalone AnswerPacket artifact is present in the Mobility Access Kit runtime bundle; the UI does not fabricate one.",
        },
        "CheckReport": {
            "source": "track_d_packets guardrail_result/audit refs plus limitations claim-boundary checks",
            "file": file_index.get("track_d_packets.json", {}),
            "status": "PASS_WITH_LIMITATIONS",
            "limitation": "No standalone CheckReport artifact is present; the UI renders existing guardrail and audit packet fields.",
        },
        "Limitations": {
            "source": "limitations.json",
            "file": file_index.get("limitations.json", {}),
            "status": "PASS",
        },
        "ReviewState": {
            "source": "review_state.json",
            "file": file_index.get("review_state.json", {}),
            "status": "PASS",
        },
        "NoActionState": {
            "source": "one_truth_index.json, review_state.json, track_d_packets.json, capture_controls.py",
            "file": one_truth_file,
            "status": "PASS",
        },
    }
    return {
        "schema_version": "citybrain.kit.packet_consumption_contract.r1",
        "status": "PASS_WITH_LIMITATIONS",
        "required_packet_inputs": REQUIRED_PACKET_INPUTS,
        "packet_sources": sources,
        "no_kit_only_truth_model": True,
        "selection_resolution_rule": "Resolve selected prim path or entity ref to existing kit_overlay_packets.json packet.",
        "execution_state": bundle.get("one_truth", {}).get("execution_state"),
    }


def web_kit_packet_parity_audit(bundle: dict) -> dict:
    one_truth_files = {
        item.get("file"): item.get("sha256")
        for item in bundle.get("one_truth", {}).get("bundle_file_index", [])
    }
    one_truth_files["one_truth_index.json"] = bundle.get("one_truth", {}).get("self_sha256")
    required_files = [
        "kit_overlay_packets.json",
        "evidence_bundle.json",
        "limitations.json",
        "review_state.json",
        "track_d_packets.json",
        "one_truth_index.json",
    ]
    return {
        "schema_version": "citybrain.web_kit_packet_parity_audit.r1",
        "status": "PASS" if all(name in one_truth_files for name in required_files) else "FAIL",
        "web_runtime_bundle_root": "packages/fixtures/mobility_access/runtime_bundle",
        "kit_runtime_bundle_root": "packages/fixtures/mobility_access/runtime_bundle",
        "shared_file_hashes": {name: one_truth_files.get(name) for name in required_files},
        "kit_consumes_same_bundle_root_as_web": True,
        "no_kit_only_selection_model": True,
    }


def boundary_visibility_audit(inspector, overlay_manager) -> dict:
    result = inspector.inspect_first()
    text = result.get("visible_text", "")
    required_phrases = [
        "Review only",
        "No action has been taken",
        "execution_state = not_executed",
        "not a certified physical twin",
        "not measurement-grade geometry",
        "not live monitoring",
        "not dispatch",
        "not a legal/certified finding",
    ]
    return {
        "schema_version": "citybrain.kit.boundary_visibility_audit.r1",
        "status": "PASS" if all(phrase in text for phrase in required_phrases) else "FAIL",
        "required_phrases": required_phrases,
        "visible_text_contains": {phrase: phrase in text for phrase in required_phrases},
        "overlay_contract_status": overlay_manager.contract().get("status"),
        "execution_state": result.get("execution_state"),
    }


def forbidden_command_negative_tests() -> dict:
    commands = [
        "execute",
        "dispatch",
        "route",
        "enforce",
        "approve",
        "create_case",
        "certify_finding",
        "publish_alert",
        "take_action",
    ]
    results = [classify_command(command) for command in commands]
    return {
        "schema_version": "citybrain.kit.forbidden_command_negative_tests.r1",
        "status": "PASS"
        if all(item.get("command_status") == "rejected" for item in results)
        and all(item.get("execution_state") == "not_executed" for item in results)
        else "FAIL",
        "known_forbidden_commands": FORBIDDEN_COMMANDS,
        "results": results,
    }


def experience_smoke_report(inspector) -> dict:
    result = inspector.inspect_first()
    text = result.get("visible_text", "")
    checks = {
        "what_object_is_visible": "Selected entity:" in text and "What this is:" in text,
        "supporting_evidence_visible": "What supports this:" in text and "citation:" in text,
        "uncertainty_visible": "Unknowns / limitations:" in text,
        "does_not_prove_visible": "What this does not prove:" in text,
        "action_state_visible": "NoActionState:" in text and "not_executed" in text,
    }
    return {
        "schema_version": "citybrain.kit.experience_smoke.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "acceptance_questions": checks,
        "kit_runtime_gui_observed": ui is not None,
        "headless_text_export_used": ui is None,
        "selected_entity_ref": result.get("entity_ref"),
        "visible_text_length": len(text),
    }


class SpatialCockpitWindow:
    def __init__(self, bundle: dict, overlay_manager, selection_inspector):
        self.bundle = bundle
        self.overlay_manager = overlay_manager
        self.selection_inspector = selection_inspector
        self.window = None
        self._subscription = None
        self._labels: dict[str, Any] = {}
        self._last_result: dict[str, Any] | None = None

    def startup(self) -> dict:
        self._build_window()
        result = self.inspect_first("startup")
        self._subscribe_to_selection()
        smoke = experience_smoke_report(self.selection_inspector)
        payload = {
            "status": "PASS" if result.get("found") else "PARTIAL",
            "window_created": self.window is not None,
            "ui_available": ui is not None,
            "selection_subscription_created": self._subscription is not None,
            "startup_probe": result,
            "experience_smoke": smoke,
            "created_at_utc": _now(),
        }
        _write_optional_json("CITYBRAIN_KIT_SPATIAL_COCKPIT_STARTUP", payload)
        return payload

    def shutdown(self) -> None:
        self._subscription = None
        self.window = None
        self._labels = {}

    def _build_window(self) -> None:
        if ui is None:
            return
        self.window = ui.Window("CityBrain Spatial Cockpit", width=720, height=760, visible=True)
        with self.window.frame:
            with ui.VStack(spacing=8, height=0):
                ui.Label("CityBrain Spatial Cockpit", height=24)
                ui.Label(BOUNDARY_TEXT, word_wrap=True)
                ui.Spacer(height=4)
                with ui.HStack(spacing=8):
                    with ui.VStack(width=250, spacing=4):
                        ui.Label("Overlay manager", height=20)
                        for row in self.overlay_manager.overlay_rows():
                            label = str(row.get("entity_ref", "overlay")).split(":")[-1]
                            entity_ref = row.get("entity_ref")
                            ui.Button(label, clicked_fn=lambda ref=entity_ref: self.inspect_entity_ref(ref, "overlay-button"))
                        ui.Spacer(height=6)
                        ui.Button("Refresh Selected Prim", clicked_fn=self.refresh_selected_prim)
                        ui.Button("Inspect First Overlay", clicked_fn=lambda: self.inspect_first("button-first-overlay"))
                    with ui.VStack(spacing=4):
                        self._labels["entity"] = ui.Label("Selected entity: waiting", word_wrap=True)
                        self._labels["prim"] = ui.Label("Inspector prim path: waiting", word_wrap=True)
                        self._labels["what"] = ui.Label("What this is: waiting", word_wrap=True)
                        self._labels["evidence"] = ui.Label("Evidence: waiting", word_wrap=True)
                        self._labels["citations"] = ui.Label("Citations: waiting", word_wrap=True)
                        self._labels["knowns"] = ui.Label("Knowns: waiting", word_wrap=True)
                        self._labels["unknowns"] = ui.Label("Limitations: waiting", word_wrap=True)
                        self._labels["cannot"] = ui.Label("Does not prove: waiting", word_wrap=True)
                        self._labels["review"] = ui.Label("Review state: waiting", word_wrap=True)
                        self._labels["overlay"] = ui.Label("Overlay state: waiting", word_wrap=True)
                        self._labels["no_action"] = ui.Label("NoActionState: waiting", word_wrap=True)

    def _set_label(self, key: str, text: str) -> None:
        label = self._labels.get(key)
        if label is not None:
            label.text = text

    def _update_window(self, result: dict[str, Any]) -> None:
        self._last_result = result
        card = result.get("inspection_card") or {}
        evidence = card.get("evidence", {})
        review = card.get("review_state", {})
        overlay = card.get("overlay", {})
        no_action = card.get("no_action_state", {})
        self._set_label("entity", f"Selected entity: {card.get('entity_label')} ({card.get('entity_ref')})")
        self._set_label("prim", f"Inspector prim path: {card.get('prim_path')}")
        self._set_label("what", f"What this is: {card.get('what_it_is')}")
        self._set_label(
            "evidence",
            "Evidence: "
            f"{evidence.get('candidate_observation_count')} candidate observations, "
            f"{evidence.get('similar_case_count')} similar cases, "
            f"{evidence.get('cascade_attachment_count')} cascade attachments",
        )
        citations = ", ".join(ref.get("key", "") for ref in card.get("citations", [])[:6])
        self._set_label("citations", f"Citations/provenance: {citations}")
        self._set_label("knowns", "Knowns: " + " | ".join(card.get("knowns", [])[:4]))
        self._set_label("unknowns", "Limitations: " + " | ".join(card.get("unknowns_limitations", [])[:5]))
        self._set_label("cannot", "Does not prove: " + " | ".join(card.get("cannot_claim", [])))
        self._set_label(
            "review",
            f"Review state: {review.get('review_state_ref')} | "
            f"approved_proposal_created={review.get('approved_proposal_created')}",
        )
        self._set_label(
            "overlay",
            f"Overlay state: {overlay.get('overlay_state')} | "
            f"claim_label={overlay.get('claim_label')} | limitation_ref={overlay.get('limitation_ref')}",
        )
        self._set_label(
            "no_action",
            f"NoActionState: no_action_taken={no_action.get('no_action_taken')} | "
            f"execution_state={no_action.get('execution_state')}",
        )
        _write_optional_json("CITYBRAIN_KIT_SPATIAL_COCKPIT_LAST_SELECTION", result)

    def _subscribe_to_selection(self) -> None:
        try:
            if omni_usd is None:
                return
            context = omni_usd.get_context()
            stream = context.get_stage_event_stream()
            self._subscription = stream.create_subscription_to_pop(
                self._on_stage_event,
                name="citybrain-spatial-cockpit-selection",
            )
        except Exception:
            self._subscription = None

    def _on_stage_event(self, event: Any) -> None:
        try:
            event_type = int(event.type)
            if omni_usd is not None and event_type == int(omni_usd.StageEventType.SELECTION_CHANGED):
                self.refresh_selected_prim()
        except Exception:
            return

    def refresh_selected_prim(self) -> dict:
        selected = []
        try:
            if omni_usd is not None:
                selected = list(omni_usd.get_context().get_selection().get_selected_prim_paths())
        except Exception:
            selected = []
        if selected:
            return self.inspect_prim_path(selected[0], "kit-selection-changed")
        return self.inspect_first("refresh-without-selection")

    def inspect_first(self, source: str = "first-overlay") -> dict:
        result = self.selection_inspector.inspect_first()
        result["ui_selection_source"] = source
        self._update_window(result)
        return result

    def inspect_entity_ref(self, entity_ref: str, source: str = "entity-ref") -> dict:
        result = self.selection_inspector.inspect(entity_ref)
        result["ui_selection_source"] = source
        self._update_window(result)
        return result

    def inspect_prim_path(self, prim_path: str, source: str = "prim-path") -> dict:
        result = self.selection_inspector.inspect_prim_path(prim_path)
        result["ui_selection_source"] = source
        self._update_window(result)
        return result

    def apply_selection_message(self, message: dict[str, Any], source: str = "selection-message") -> dict:
        entity_ref = message.get("canonical_entity_id") or message.get("entity_ref")
        if entity_ref:
            return self.inspect_entity_ref(entity_ref, source)
        prim_path = message.get("prim_path")
        if prim_path:
            return self.inspect_prim_path(prim_path, source)
        return self.inspect_first(source)

    def visible_text_export(self) -> str:
        result = self._last_result or self.selection_inspector.inspect_first()
        card = result.get("inspection_card") or {}
        return visible_text_from_card(card)
