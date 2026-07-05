from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.capture_controls import classify_command  # noqa: E402
from citybrain.control_room.extension import smoke_summary  # noqa: E402
from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    boundary_visibility_audit,
    experience_smoke_report,
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


class OmniverseSpatialCockpitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_bundle()
        self.overlay = OverlayManager(self.bundle)
        self.inspector = SelectionInspector(self.bundle, self.overlay)

    def test_selection_card_contains_operator_required_sections(self) -> None:
        result = self.inspector.inspect_first()
        card = result["inspection_card"]
        self.assertTrue(result["found"])
        self.assertTrue(card["entity_ref"])
        self.assertTrue(card["evidence"]["source_records"])
        self.assertTrue(card["citations"])
        self.assertTrue(card["knowns"])
        self.assertTrue(card["unknowns_limitations"])
        self.assertIn("not a certified physical twin", card["cannot_claim"])
        self.assertEqual(card["no_action_state"]["execution_state"], "not_executed")
        self.assertTrue(card["prim_path"])

    def test_experience_smoke_answers_five_acceptance_questions(self) -> None:
        report = experience_smoke_report(self.inspector)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(all(report["acceptance_questions"].values()))

    def test_boundary_visible_and_forbidden_commands_rejected(self) -> None:
        audit = boundary_visibility_audit(self.inspector, self.overlay)
        self.assertEqual(audit["status"], "PASS")
        for command in ["execute", "dispatch", "route", "enforce", "approve", "create_case", "publish_alert"]:
            result = classify_command(command)
            self.assertEqual(result["command_status"], "rejected")
            self.assertEqual(result["execution_state"], "not_executed")

    def test_overlay_manager_is_review_context_only(self) -> None:
        contract = self.overlay.contract()
        smoke = self.overlay.smoke_report()
        self.assertEqual(contract["status"], "PASS")
        self.assertEqual(smoke["status"], "PASS")
        self.assertFalse(contract["forbidden_semantic_hits"])

    def test_packet_contract_and_parity_are_shared_bundle(self) -> None:
        contract = packet_consumption_contract(self.bundle)
        parity = web_kit_packet_parity_audit(self.bundle)
        self.assertEqual(contract["status"], "PASS_WITH_LIMITATIONS")
        self.assertTrue(contract["no_kit_only_truth_model"])
        self.assertEqual(parity["status"], "PASS")
        self.assertTrue(parity["kit_consumes_same_bundle_root_as_web"])

    def test_extension_smoke_summary_includes_native_panel_surface(self) -> None:
        summary = smoke_summary()
        self.assertEqual(summary["experience_smoke"]["status"], "PASS")
        self.assertIn("source/evidence records", summary["native_panel_sections"])
        self.assertTrue(summary["default_selection_found"])


if __name__ == "__main__":
    unittest.main()
