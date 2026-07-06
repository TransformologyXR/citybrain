import json
import unittest

from scripts.citybrain_epoch_2_0_common import (
    AUDIT_ROOT,
    FORBIDDEN_ACTIONS,
    PACKAGE_ROOT,
    audit_llm_seats,
    audit_permissions,
    write_all_outputs,
)


class CityBrainEpoch20PermissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_all_outputs()
        cls.registry = json.loads((PACKAGE_ROOT / "component_registry_v1.json").read_text(encoding="utf-8"))
        cls.policies = json.loads((PACKAGE_ROOT / "tool_permission_policy_v1.json").read_text(encoding="utf-8"))
        cls.seats = json.loads((PACKAGE_ROOT / "llm_seat_registry_v1.json").read_text(encoding="utf-8"))

    def test_tool_permission_policy_blocks_forbidden_actions(self):
        report = audit_permissions(self.registry, self.policies)
        self.assertEqual("PASS", report["status"], report)
        for policy in self.policies:
            self.assertFalse(policy["secrets_allowed"])
            self.assertNotEqual("production", policy["environment"])
            for action in FORBIDDEN_ACTIONS:
                self.assertIn(action, policy["forbidden_actions"])

    def test_llm_seats_have_no_authority(self):
        report = audit_llm_seats(self.seats)
        self.assertEqual("PASS", report["status"], report)
        allowed = {"disabled", "offline_eval", "proposal_only", "writer_only"}
        self.assertTrue(all(seat["status"] in allowed for seat in self.seats))
        audit = json.loads((AUDIT_ROOT / "no_live_llm_authority_audit.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", audit["status"])


if __name__ == "__main__":
    unittest.main()
