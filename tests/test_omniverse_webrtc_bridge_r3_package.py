from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from scripts.run_main_citybrain_omniverse_webrtc_live_webui_bridge_r1 import (  # noqa: E402
    FAIL_BOUNDARY,
    FORBIDDEN_PRODUCTION_CLAIMS,
    PARTIAL_CONFIG_ONLY,
    PASS_STATUS,
    SIGNAL_PORT,
    STREAM_PORT,
    TASK_ID,
    boundary_audit,
    one_truth_packet_audit,
    webui_stream_client_audit,
)


class OmniverseWebRtcBridgeR3PackageTests(unittest.TestCase):
    def test_task_identity_is_r3_webrtc_bridge(self) -> None:
        self.assertIn("R3-WEBRTC-LIVE-WEBUI-BRIDGE", TASK_ID)
        self.assertTrue(PASS_STATUS.startswith("PASS_OMNIVERSE_WEBRTC"))
        self.assertIn("LOCAL_CONFIG_ONLY", PARTIAL_CONFIG_ONLY)
        self.assertIn("BOUNDARY", FAIL_BOUNDARY)

    def test_kit_ports_are_local_dev_webrtc_ports(self) -> None:
        self.assertEqual(SIGNAL_PORT, 49100)
        self.assertEqual(STREAM_PORT, 47998)

    def test_webui_stream_client_is_packet_backed_and_review_only(self) -> None:
        audit = webui_stream_client_audit()
        self.assertEqual(audit["status"], "PASS")
        checks = audit["checks"]
        self.assertTrue(checks["appstreamer_entrypoint"])
        self.assertTrue(checks["local_dev_config"])
        self.assertTrue(checks["message_contracts_present"])
        self.assertTrue(checks["action_like_messages_rejected"])
        self.assertTrue(checks["pixel_truth_rejected"])

    def test_one_truth_packet_audit_preserves_required_shapes(self) -> None:
        audit = one_truth_packet_audit(load_bundle())
        self.assertEqual(audit["status"], "PASS")
        for shape in [
            "EntitySelection",
            "EvidenceBundle",
            "AnswerPacket / subject-answer",
            "CheckReport",
            "Limitations",
            "ReviewState",
            "NoActionState",
        ]:
            self.assertTrue(audit["checks"][shape])
        self.assertTrue(audit["checks"]["no_pixel_derived_truth"])

    def test_boundary_audit_allows_local_webrtc_but_blocks_production_claims(self) -> None:
        ok = boundary_audit(
            "local/dev local_dev_only",
            '"public_internet": false',
            '"live_monitoring": false',
            "No dispatch, control, enforcement, legal finding, or automated action.",
            "streamed_pixels_are_not_citybrain_evidence_or_action_truth",
            "NoActionState execution_state=not_executed",
        )
        self.assertEqual(ok["status"], "PASS")
        bad = boundary_audit(
            "local/dev local_dev_only",
            '"public_internet": false',
            '"live_monitoring": false',
            "streamed_pixels_are_not_citybrain_evidence_or_action_truth",
            "NoActionState execution_state=not_executed",
            "production streaming is implemented and latency SLA is met",
        )
        self.assertEqual(bad["status"], "FAIL")

    def test_forbidden_production_claims_cover_user_caveat(self) -> None:
        joined = " ".join(FORBIDDEN_PRODUCTION_CLAIMS)
        self.assertIn("OKAS", joined)
        self.assertIn("public internet", joined)
        self.assertIn("latency SLA", joined)
        self.assertIn("live monitoring", joined)
        self.assertIn("automated action", joined)


if __name__ == "__main__":
    unittest.main()
