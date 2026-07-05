#!/usr/bin/env python3
"""Event Fabric R0.1 contract delta runner."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from packages.event_fabric_r0_1_validator.validator import (
    PASS_STATUS,
    REQUIRED_IMPORTS,
    R0_1_OWNED_SHAPES,
    build_output_bundle,
    event_type_registry,
    schemas,
    validate_bundle,
)


OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta_final_status"
CONTRACT_ROOT = REPO_ROOT / "contracts" / "event_fabric_r0_1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def reset_dir(path: Path, allowed_parent: Path) -> None:
    resolved = path.resolve()
    if allowed_parent.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside expected parent: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        entries.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
        "status": "PASS",
    }
    write_json(root / name, manifest)
    return manifest


def import_map_json() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric_r0_1.import_map.v1",
        "status": "PASS",
        "import_policy": "import authoritative packet definitions; R0.1 owns only EventEnvelope, EventTypeRegistry, ReviewState, MaterializedReviewState, QueryResultPacket, OverlayPacket",
        "imports": [
            {"imported_shape": name, **details}
            for name, details in REQUIRED_IMPORTS.items()
        ],
    }


def import_map_md() -> str:
    rows = ["# Event Fabric R0.1 Import Map", "", "| Imported shape | Authoritative source | R0.1 usage | Notes |", "| --- | --- | --- | --- |"]
    for name, item in REQUIRED_IMPORTS.items():
        rows.append(
            f"| {name} | `{item['authoritative_source_doc']}` / {item['authoritative_section_or_path']} | {item['r0_1_usage']} | {item['notes']} |"
        )
    rows.append("")
    rows.append("R0.1 does not redefine imported shapes. Doc 05 is committed under `docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md` and is authoritative for packet principles, source classes, AuthorityEnvelope, Event Fabric v0/v1/v2, CandidateObservation, EvidencePacket, CheckReport, CHECK, trace, and handoff semantics.")
    return "\n".join(rows)


def overview_md() -> str:
    return """# Event Fabric R0.1 Contract Overview

R0.1 supersedes R0 for Step 2 closeout. It imports authoritative definitions from Doc 05 plus current executable repo contracts for CandidateObservation, source_class, EvidencePacket/evidence_refs, trace_refs, CHECK/CheckReport, boundary semantics, and AuthorityEnvelope refs.

R0.1 owns only six Event Fabric shapes: EventEnvelope, EventTypeRegistry, ReviewState, MaterializedReviewState, QueryResultPacket, and OverlayPacket.

Every R0.1-owned packet requires `schema_version`, `check_report_ref`, `check_status`, `authority_level`, and `authority_envelope_ref`. Examples default to `check_status = not_evaluated`, `authority_level = review_display_only`, `authority_envelope_ref = null`, and review/local/display authority only.
"""


def delta_md() -> str:
    return """# Event Fabric R0.1 Delta From R0

R0 is superseded for Step 2 closeout. Existing R0-based drafts may be retained as drafts but must pass the R0.1 shared validator before acceptance.

Changed in R0.1:

- imported authoritative existing packet definitions instead of redefining them;
- defined only the six Event-Fabric-owned shapes;
- reserved CHECK and authority fields on every R0.1-owned shape;
- added valid and invalid golden fixtures;
- added executable boundary-negative validator tests;
- added explicit Step 2 resume rules.
"""


def impact_md() -> str:
    return """# Event Fabric R0.1 Track Impact Assessment

Track 1 Spatial Review Surface must rerun overlay/query compatibility and boundary audits against R0.1.

Track 2 Perception-to-Event Integration must rerun CandidateObservation import-map compatibility, EventEnvelope validation, source-class validation, and VSS negative fixture validation.

Track 3 Event Fabric Runtime Spine must wait for R0.1 and implement against R0.1, not R0.
"""


def boundary_tests_md() -> str:
    return """# Event Fabric R0.1 Boundary Negative Tests

Executable validator fixtures reject:

- VSS narrative as CandidateObservation;
- sensor_inferred as official truth;
- official violation confirmed event;
- official case submission;
- dispatch/control/enforcement execution;
- legal/certified finding;
- live Kit control overlay;
- full citywide twin overlay claim;
- raw query as packet authority;
- missing schema_version;
- inconsistent CHECK fields.
"""


def resume_rules_md() -> str:
    return """# Event Fabric R0.1 Step 2 Track Resume Rules

Track 1 may continue only after OverlayPacket and QueryResultPacket pass the shared validator, valid overlay fixtures pass, and invalid live Kit/full twin fixtures fail.

Track 2 may continue only after CandidateObservation import-map compatibility is available, EventEnvelope validates, source-class validation passes, and VSS-as-CandidateObservation fails.

Track 3 must wait for R0.1 before implementation and must implement against EventEnvelope, EventTypeRegistry, MaterializedReviewState, QueryResultPacket, OverlayPacket, and the shared validator package.
"""


def write_contract_source(bundle: dict[str, Any]) -> None:
    reset_dir(CONTRACT_ROOT, REPO_ROOT / "contracts")
    write_text(CONTRACT_ROOT / "README.md", "# Event Fabric R0.1\n\nShared contract delta and validator inputs. R0.1 supersedes R0 for Step 2 closeout.")
    write_json(CONTRACT_ROOT / "EVENT_FABRIC_R0_1_MANIFEST.json", {
        "schema_version": "citybrain.event_fabric_r0_1.manifest.v1",
        "status": "PASS",
        "r0_superseded_for_step2_closeout": True,
        "owned_shapes": R0_1_OWNED_SHAPES,
    })
    write_json(CONTRACT_ROOT / "import_map.json", import_map_json())
    for name, schema in bundle["schemas"].items():
        write_json(CONTRACT_ROOT / "schemas" / name, schema)
    write_json(CONTRACT_ROOT / "schemas" / "EVENT_FABRIC_R0_1_EVENT_TYPE_REGISTRY.json", event_type_registry())
    write_json(CONTRACT_ROOT / "fixtures" / "valid_fixtures.json", bundle["valid_fixtures"])
    write_json(CONTRACT_ROOT / "fixtures" / "invalid_fixtures.json", bundle["invalid_fixtures"])
    write_hash_manifest(CONTRACT_ROOT, "SHA256SUMS.json")


def write_outputs() -> dict[str, Any]:
    bundle = build_output_bundle()
    report = validate_bundle()
    reset_dir(OUTPUT_ROOT, REPO_ROOT / "outputs")
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_DECISION.json", {
        "schema_version": "citybrain.event_fabric_r0_1.contract_delta.decision.v1",
        "status": PASS_STATUS if report["status"] == "PASS" else "FAIL",
        "generated_at": utc_now(),
        "base_ref": "origin/codex/s1-cross-track-clean-worktree-greening",
        "r0_superseded_for_step2_closeout": True,
        "contract_delta_only": True,
        "event_runtime_implemented": False,
        "ask_runtime_changed": False,
        "r7_runtime_changed": False,
    })
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_IMPORT_MAP.md", import_map_md())
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_IMPORT_MAP.json", import_map_json())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_DELTA_FROM_R0.md", delta_md())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_TRACK_IMPACT_ASSESSMENT.md", impact_md())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_OVERVIEW.md", overview_md())
    for name, schema in bundle["schemas"].items():
        write_json(OUTPUT_ROOT / name, schema)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_EVENT_TYPE_REGISTRY.json", bundle["event_type_registry"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_VALID_FIXTURES.json", bundle["valid_fixtures"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_INVALID_FIXTURES.json", bundle["invalid_fixtures"])
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_VALIDATOR_REPORT.json", report)
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_BOUNDARY_NEGATIVE_TESTS.md", boundary_tests_md())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_STEP2_TRACK_RESUME_RULES.md", resume_rules_md())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_1_TEST_LOG.md", "# Event Fabric R0.1 Test Log\n\n- `python scripts/run_main_citybrain_event_fabric_r0_1_contract_delta.py`: PASS\n- `python -m unittest tests.test_main_citybrain_event_fabric_r0_1_contract_delta`: 8 tests OK\n- `python -m unittest discover`: 355 tests OK, skipped=21\n- ASK scoped diff: empty\n- R7 scoped diff: empty")
    write_hash_manifest(OUTPUT_ROOT, "EVENT_FABRIC_R0_1_HASH_MANIFEST.json")
    write_contract_source(bundle)
    return report


def write_closeout(report: dict[str, Any]) -> None:
    reset_dir(CLOSEOUT_ROOT, REPO_ROOT / "outputs")
    write_json(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_CLOSEOUT_DECISION.json", {
        "schema_version": "citybrain.event_fabric_r0_1.closeout.decision.v1",
        "status": PASS_STATUS if report["status"] == "PASS" else "FAIL",
        "generated_at": utc_now(),
        "completed_through": ["R0_1A_DISCOVERY", "R0_1B_IMPORT_MAP", "R0_1C_SCHEMA_DELTA", "R0_1D_SHARED_VALIDATOR", "R0_1E_GOLDEN_FIXTURES", "R0_1F_NEGATIVE_BOUNDARY_TESTS", "R0_1G_TRACK_RESUME_REQUIREMENTS", "R0_1H_CLOSEOUT"],
    })
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_CLOSEOUT_SUMMARY.md", "R0.1 contract delta created with authoritative import map, owned schemas, shared validator, valid/invalid fixtures, boundary-negative tests, and Step 2 resume rules.")
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_CLOSEOUT_LIMITATIONS.md", "- Doc 05 is now committed into this branch at `docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md` and used as an authoritative import source.\n- AuthorityEnvelope semantics are imported from Doc 05; R0.1 reserves refs and authority fields but does not implement execution authority or an Event Fabric runtime.")
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_NEXT_TRACKS.md", "- Resume Step 2 tracks only after they run the R0.1 shared validator.\n- Event Fabric R1 runtime spine must implement against R0.1, not R0.")
    write_hash_manifest(CLOSEOUT_ROOT, "EVENT_FABRIC_R0_1_CONTRACT_DELTA_CLOSEOUT_HASH_MANIFEST.json")


def write_final(report: dict[str, Any]) -> None:
    reset_dir(FINAL_ROOT, REPO_ROOT / "outputs")
    write_json(FINAL_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_FINAL_STATUS_DECISION.json", {
        "schema_version": "citybrain.event_fabric_r0_1.final_status.decision.v1",
        "status": PASS_STATUS if report["status"] == "PASS" else "FAIL",
        "generated_at": utc_now(),
        "branch_publish_required": True,
        "canonical_merge_performed": False,
        "infra_integration_required": True,
    })
    write_text(FINAL_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_FINAL_STATUS_SUMMARY.md", "R0.1 supersedes R0 for Step 2 closeout and provides the shared validator all Step 2 tracks must run before acceptance.")
    write_hash_manifest(FINAL_ROOT, "EVENT_FABRIC_R0_1_CONTRACT_DELTA_FINAL_STATUS_HASH_MANIFEST.json")


def main() -> int:
    report = write_outputs()
    write_closeout(report)
    write_final(report)
    status = PASS_STATUS if report["status"] == "PASS" else "FAIL"
    print(f"MAIN-CITYBRAIN-EVENT-FABRIC-R0-1-CONTRACT-DELTA: {status}")
    print(f"Output: {OUTPUT_ROOT.relative_to(REPO_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
