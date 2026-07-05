from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_main_citybrain_omniverse_native_kit_spatial_cockpit_ui_r2_live_gui_visual_acceptance import (  # noqa: E402
    FAIL_BOUNDARY,
    FORBIDDEN_CLAIMS,
    PARTIAL_GUI_BLOCKED,
    PASS_STATUS,
    TASK_ID,
    material_text_comparison,
)


class OmniverseSpatialCockpitR2PackageTests(unittest.TestCase):
    def test_task_identity_is_r2_live_gui_acceptance(self) -> None:
        self.assertIn("R2-LIVE-GUI-VISUAL-ACCEPTANCE", TASK_ID)

    def test_status_labels_include_pass_partial_and_boundary_fail(self) -> None:
        self.assertTrue(PASS_STATUS.startswith("PASS_OMNIVERSE_NATIVE_KIT_UI_R2"))
        self.assertIn("GUI_BLOCKED", PARTIAL_GUI_BLOCKED)
        self.assertIn("BOUNDARY_OR_ONE_TRUTH", FAIL_BOUNDARY)

    def test_forbidden_claims_cover_non_claim_boundaries(self) -> None:
        joined = " ".join(FORBIDDEN_CLAIMS)
        self.assertIn("WebRTC", joined)
        self.assertIn("DeepStream", joined)
        self.assertIn("certified physical twin", joined)
        self.assertIn("automated action", joined)

    def test_material_text_comparison_passes_matching_live_text(self) -> None:
        expected = "\n".join(
            [
                "Selected entity: route segment",
                "What supports this:",
                "Unknowns / limitations:",
                "What this does not prove:",
                "NoActionState:",
                "execution_state=not_executed",
            ]
        )
        report = material_text_comparison(expected, expected, "LIVE_KIT_GUI")
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["material_match"])


if __name__ == "__main__":
    unittest.main()
