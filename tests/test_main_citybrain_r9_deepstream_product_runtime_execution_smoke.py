import json
import shutil
import unittest
import zipfile
from pathlib import Path

from scripts.run_main_citybrain_r9_deepstream_product_runtime_execution_smoke import (
    OUTPUT_ROOT,
    PASS_STATUS,
    RAW_ROOT,
    REQUIRED_RAW_FILES,
    build_bundle,
    forbidden_boundary_failures,
    read_jsonl,
    sha256_file,
    verify_hash_manifest,
    write_outputs,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT_ROOT = ROOT / "outputs" / "_test_main_citybrain_r9_deepstream_product_runtime_execution_smoke"
TEST_RAW_ROOT = ROOT / "outputs" / "_test_fixtures" / "r9_deepstream_runtime_raw"


def write_test_raw_runtime_fixture(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    (root / "metadata").mkdir(parents=True, exist_ok=True)
    (root / "R9_DEEPSTREAM_READINESS_SUMMARY.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "host": "txr-4070-test-fixture",
                "host_type": "native_ubuntu",
                "host_os_observed": "Ubuntu 24.04 test fixture",
                "image": "nvcr.io/nvidia/deepstream:8.0-triton-multiarch",
                "sample_video_container_path": "/opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.mp4",
                "run_output_root": "/tmp/citybrain-r9-test-fixture",
                "metadata_file_count": 1,
                "version_lines": ["DeepStreamSDK 8.0.0", "deepstream-app version 8.0.0"],
                "blockers": [],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "deepstream-app-exit-code.txt").write_text("0\n", encoding="utf-8")
    (root / "deepstream-app-sample.log").write_text(
        "Received EOS\nApp run successful\n", encoding="utf-8"
    )
    (root / "deepstream-version-all.txt").write_text(
        "DeepStreamSDK 8.0.0\ndeepstream-app version 8.0.0\n", encoding="utf-8"
    )
    (root / "nvidia-smi-container.txt").write_text(
        "NVIDIA-SMI test fixture\n", encoding="utf-8"
    )
    (root / "output-file-index.tsv").write_text(
        "path\tkind\nmetadata/000000.txt\tkitti_metadata\n", encoding="utf-8"
    )
    (root / "pipeline-status.txt").write_text("PASS\n", encoding="utf-8")
    (root / "r9_source1_file_config.txt").write_text(
        "[source0]\nenable=1\ntype=3\n", encoding="utf-8"
    )
    (root / "metadata" / "000000.txt").write_text(
        "car 0 0 0 10 20 80 100 0 0 0 0 0 0 0.875\n", encoding="utf-8"
    )


class MainCityBrainR9DeepStreamProductRuntimeExecutionSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_OUTPUT_ROOT.exists():
            shutil.rmtree(TEST_OUTPUT_ROOT)
        write_test_raw_runtime_fixture(TEST_RAW_ROOT)
        write_outputs(
            root=TEST_OUTPUT_ROOT,
            raw_source_root=TEST_RAW_ROOT,
            tests={"targeted_r9": "TEST_SETUP", "full_discovery": "TEST_SETUP", "test_count": 0},
        )
        cls.output_root = TEST_OUTPUT_ROOT
        cls.bundle = build_bundle(TEST_OUTPUT_ROOT)

    def test_raw_deepstream_runtime_artifacts_are_present(self):
        raw = self.output_root / "deepstream_runtime_raw"
        for name in REQUIRED_RAW_FILES:
            self.assertTrue((raw / name).exists(), name)
        self.assertGreaterEqual(len(list((raw / "metadata").glob("*.txt"))), 1)
        log_text = (raw / "deepstream-app-sample.log").read_text(encoding="utf-8", errors="replace")
        self.assertIn("Received EOS", log_text)
        self.assertIn("App run successful", log_text)

    def test_runtime_audit_proves_actual_deepstream_product_execution(self):
        audit = json.loads((self.output_root / "DEEPSTREAM_PRODUCT_RUNTIME_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", audit["status"])
        self.assertTrue(audit["deepstream_product_runtime_executed"])
        self.assertEqual("NVIDIA DeepStream deepstream-app", audit["runtime_name"])
        self.assertEqual("0", audit["sample_pipeline_exit_code"])
        self.assertGreaterEqual(audit["metadata_file_count"], 1)

    def test_runtime_metadata_is_sensor_inferred_candidate_evidence(self):
        detections = read_jsonl(self.output_root / "runtime_metadata" / "runtime_detections.jsonl")
        self.assertGreater(len(detections), 0)
        first = detections[0]
        self.assertEqual("sensor_inferred", first["source_class"])
        self.assertEqual("nvidia_deepstream_8_product_runtime", first["source_system"])
        self.assertIn(first["detected_class"], {"car", "person"})
        self.assertGreaterEqual(first["confidence"], 0)
        self.assertLessEqual(first["confidence"], 1)
        self.assertEqual("pixel_xyxy", first["bbox"]["coordinate_space"])

    def test_candidate_observations_remain_review_only_no_action(self):
        observations = read_jsonl(self.output_root / "candidate_observations" / "candidate_observations.jsonl")
        self.assertGreater(len(observations), 0)
        observation = observations[0]
        self.assertEqual("candidate_unreviewed", observation["review_state"])
        self.assertTrue(observation["human_review_required"])
        self.assertEqual("sensor_inferred", observation["source_class"])
        self.assertTrue(observation["sensor_inferred_from_pixels"])
        self.assertFalse(observation["pixel_derived_truth_used"])
        self.assertFalse(observation["vss_output_used_as_truth"])
        self.assertEqual("not_executed", observation["no_action_state"]["execution_status"])
        self.assertFalse(observation["no_action_state"]["official_submission_performed"])
        self.assertFalse(observation["no_action_state"]["autonomous_action_performed"])

    def test_one_truth_and_boundary_audits_pass(self):
        one_truth = json.loads((self.output_root / "ONE_TRUTH_PACKET_AUDIT.json").read_text(encoding="utf-8"))
        boundary = json.loads((self.output_root / "BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", one_truth["status"])
        self.assertIn("CandidateObservation", one_truth["packet_shapes_preserved"])
        self.assertFalse(one_truth["kit_or_web_truth_introduced"])
        self.assertEqual("PASS", boundary["status"])
        self.assertFalse(boundary["forbidden_claims_present"])
        self.assertFalse(boundary["official_submission_performed"])
        self.assertFalse(boundary["dispatch_control_enforcement_executed"])
        self.assertFalse(boundary["autonomous_action_performed"])
        self.assertEqual([], forbidden_boundary_failures(self.bundle))

    def test_decision_and_hash_manifest_verify(self):
        decision = json.loads((self.output_root / "DECISION.json").read_text(encoding="utf-8"))
        self.assertIn(decision["status"], {PASS_STATUS, "PARTIAL_R9_DEEPSTREAM_PRODUCT_RUNTIME_EVIDENCE_INCOMPLETE"})
        self.assertTrue(decision["deepstream_product_runtime_executed"])
        self.assertEqual("sensor_inferred", decision["source_class"])
        self.assertEqual("not_executed", decision["execution_status"])
        report = verify_hash_manifest(self.output_root)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(report["declared"], report["verified"])

    def test_packaged_zip_integrity_and_raw_file_hash(self):
        zip_path = self.output_root / "citybrain_r9_deepstream_product_runtime_execution_smoke.zip"
        self.assertTrue(zip_path.exists())
        with zipfile.ZipFile(zip_path) as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
        self.assertIn("DECISION.json", names)
        self.assertIn("deepstream_runtime_raw/deepstream-app-sample.log", names)
        raw_log = self.output_root / "deepstream_runtime_raw" / "deepstream-app-sample.log"
        self.assertEqual(64, len(sha256_file(raw_log)))


if __name__ == "__main__":
    unittest.main()
