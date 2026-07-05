from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_ask_v11_app_surface_smoke_r1.py"
spec = importlib.util.spec_from_file_location("ask_surface_smoke", SCRIPT_PATH)
smoke = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(smoke)


class AskV11AppSurfaceSmokeR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = smoke.write_all_outputs()

    def test_smoke_decision_passes_with_static_render_state(self) -> None:
        decision = json.loads((smoke.SMOKE_ROOT / "ASK_V11_APP_SURFACE_SMOKE_R1_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["status"], smoke.PASS_SMOKE)
        self.assertEqual(decision["smoke_type"], "static/render-state")
        self.assertFalse(decision["browser_visual_smoke_run"])
        self.assertTrue(decision["deterministic_smoke_passed"])

    def test_fixture_load_report_confirms_vendored_fixture(self) -> None:
        report = json.loads((smoke.SMOKE_ROOT / "ASK_V11_APP_SURFACE_FIXTURE_LOAD_REPORT.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["fixture_count"], 8)
        self.assertEqual(set(report["scenarios"]), set(smoke.REQUIRED_SCENARIOS))
        self.assertTrue(report["checks"]["default_loader_uses_committed_fixture_path"])

    def test_render_state_covers_required_ui_sections(self) -> None:
        report = json.loads((smoke.SMOKE_ROOT / "ASK_V11_APP_SURFACE_RENDER_STATE_REPORT.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(all(report["checks"].values()))

    def test_boundary_audit_blocks_live_or_official_affordances(self) -> None:
        audit = json.loads((smoke.SMOKE_ROOT / "ASK_V11_APP_SURFACE_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(audit["checks"].values()))

    def test_closeout_and_final_status_exist(self) -> None:
        closeout = json.loads((smoke.CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((smoke.FINAL_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(closeout["status"], smoke.PASS_CLOSEOUT)
        self.assertEqual(final["status"], smoke.PASS_FINAL)
        self.assertTrue(closeout["fixture_vendoring_commit_found"])

    def test_hash_manifests_verify(self) -> None:
        self.assertEqual(smoke.verify_hash_manifest(smoke.SMOKE_ROOT, "ASK_V11_APP_SURFACE_SMOKE_HASH_MANIFEST.json")["status"], "PASS")
        self.assertEqual(smoke.verify_hash_manifest(smoke.CLOSEOUT_ROOT, "ASK_V11_APP_SURFACE_LOOSE_END_HASH_MANIFEST.json")["status"], "PASS")
        self.assertEqual(smoke.verify_hash_manifest(smoke.FINAL_ROOT, "ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_HASH_MANIFEST.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
