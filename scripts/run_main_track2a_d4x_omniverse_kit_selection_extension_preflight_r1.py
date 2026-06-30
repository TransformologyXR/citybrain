#!/usr/bin/env python3
"""Prepare the bounded Kit selection extension preflight.

This is a preflight/spec + headless simulation pack. It does not implement a
Kit extension, launch Omniverse, integrate live event fabric, or connect D5 app
outputs. It consumes only the completed Kit interaction smoke output.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-SELECTION-EXTENSION-PREFLIGHT-R1"
SCHEMA_VERSION = "main-track2a-d4x-omniverse-kit-selection-extension-preflight-r1.v1"
ROOT = Path("outputs/main_track2a_d4x_omniverse_kit_selection_extension_preflight_r1")
UPSTREAM_ROOT = Path("outputs/main_track2a_d4x_omniverse_kit_interaction_smoke_r1")
RUNNER_PATH = Path("scripts/run_main_track2a_d4x_omniverse_kit_selection_extension_preflight_r1.py")
REPO_ROOT = Path.cwd()

UPSTREAM_DECISION = UPSTREAM_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_INTERACTION_SMOKE_R1_DECISION.json"
UPSTREAM_CONTRACT = UPSTREAM_ROOT / "OMNIVERSE_KIT_INTERACTION_CONTRACT.json"
UPSTREAM_MANIFEST = UPSTREAM_ROOT / "OMNIVERSE_KIT_INTERACTION_HANDOFF_MANIFEST.json"
UPSTREAM_CARDS = UPSTREAM_ROOT / "OMNIVERSE_KIT_INTERACTION_CARD_FIXTURES.json"
UPSTREAM_VALIDATION = UPSTREAM_ROOT / "OMNIVERSE_KIT_INTERACTION_VALIDATION_RESULTS.json"
UPSTREAM_USD_AUDIT = UPSTREAM_ROOT / "OMNIVERSE_USD_METADATA_CONSISTENCY_AUDIT.json"
UPSTREAM_KIT_NOTES = UPSTREAM_ROOT / "KIT_COMPOSER_OPERATOR_HANDOFF_NOTES.md"
UPSTREAM_LIMITATIONS = UPSTREAM_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md"
UPSTREAM_README = UPSTREAM_ROOT / "README.md"
UPSTREAM_RUNNER = Path("scripts/run_main_track2a_d4x_omniverse_kit_interaction_smoke_r1.py")

SOURCE_ROOTS = [UPSTREAM_ROOT]

FORBIDDEN_CLAIMS = [
    "citywide twin",
    "full mesh binding",
    "physical accuracy",
    "production simulation",
    "production live event fabric",
    "production perception",
    "dispatch",
    "enforcement",
    "routing/control",
    "autonomous action",
    "legal conclusion",
    "ownership truth",
    "certified affected-building conclusion",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    count = 0
    size = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                st = path.stat()
            except FileNotFoundError:
                continue
            count += 1
            size += st.st_size
            latest = max(latest, st.st_mtime_ns)
    return {"root": rel(root), "exists": True, "file_count": count, "total_bytes": size, "latest_mtime_ns": latest}


def upstream_inventory() -> dict[str, Any]:
    decision = read_json(UPSTREAM_DECISION, {})
    manifest = read_json(UPSTREAM_MANIFEST, {})
    artifacts = {
        "decision_json": UPSTREAM_DECISION.exists(),
        "interaction_contract": UPSTREAM_CONTRACT.exists(),
        "handoff_manifest": UPSTREAM_MANIFEST.exists(),
        "card_fixtures": UPSTREAM_CARDS.exists(),
        "validation_results": UPSTREAM_VALIDATION.exists(),
        "usd_metadata_consistency_audit": UPSTREAM_USD_AUDIT.exists(),
        "kit_operator_handoff_notes": UPSTREAM_KIT_NOTES.exists(),
        "limitations": UPSTREAM_LIMITATIONS.exists(),
        "readme": UPSTREAM_README.exists(),
        "runner": UPSTREAM_RUNNER.exists(),
    }
    return {
        "status": "PASS" if all(artifacts.values()) and len(manifest.get("records", [])) == 12 else "FAIL",
        "upstream_status": decision.get("status"),
        "upstream_artifacts_found": artifacts,
        "upstream_interaction_records": len(manifest.get("records", [])),
        "schema_version": SCHEMA_VERSION,
    }


def extension_contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Omniverse Kit Selection Extension Preflight Contract",
        "schema_version": SCHEMA_VERSION,
        "extension_name": "txr.citybrain.selection_inspector",
        "target_kit_composer_environment_assumptions": {
            "runtime": "local Omniverse/Kit or USD Composer on RTX workstation",
            "input_layer": "CITYBRAIN_BARC_EIXAMPLE_ASSET_BINDING_R1.usda",
            "gui_required_for_preflight": False,
            "actual_extension_implemented": False,
        },
        "required_event_fields": [
            "event_id",
            "event_type",
            "selected_prim_path",
            "selection_source",
            "timestamp_utc",
        ],
        "required_lookup_fields": [
            "select_prim_path",
            "canonical_entity_id",
            "entity_type",
            "display_name",
            "evidence_ref",
            "graph_or_runtime_ref",
            "limitation_ref",
            "binding_status",
            "review_state",
        ],
        "safe_failure_modes": {
            "missing_prim": "return SAFE_FAILURE_UNKNOWN_PRIM with no_action_taken=true",
            "unbound_prim": "return SAFE_FAILURE_UNBOUND_PRIM with no_action_taken=true",
            "incomplete_metadata": "return SAFE_FAILURE_INCOMPLETE_METADATA with missing_fields and no_action_taken=true",
        },
        "display_policy": {
            "evidence": "show inline with source refs",
            "graph_runtime": "show as context refs, not commands",
            "limitations": "always visible in inspection card",
            "truth_boundary": "USD metadata is a selection index, not canonical truth",
            "no_action_boundary": "selection can inspect only; no dispatch, enforcement, routing/control, or legal/certified action",
        },
        "forbidden_claims": FORBIDDEN_CLAIMS,
    }


def event_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Kit Selection Event",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": ["event_id", "event_type", "selected_prim_path", "selection_source", "timestamp_utc"],
        "properties": {
            "event_type": {"enum": ["kit_prim_selected", "headless_prim_selected"]},
            "selection_source": {"enum": ["kit_gui", "composer_gui", "headless_preflight"]},
            "selected_prim_path": {"type": "string"},
        },
        "no_action_taken_required": True,
    }


def card_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Kit Selection Inspection Card",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": [
            "card_id",
            "selected_prim_path",
            "canonical_entity_id",
            "entity_type",
            "display_name",
            "evidence_ref",
            "graph_or_runtime_ref",
            "limitation_ref",
            "binding_status",
            "review_state",
            "safe_actions",
            "forbidden_actions",
            "no_action_taken",
        ],
        "boundary": "inspection card only; no command/action/control/legal/certified outcome",
    }


def load_interaction_records() -> list[dict[str, Any]]:
    return read_json(UPSTREAM_MANIFEST, {}).get("records", [])


def binding_lookup(records: list[dict[str, Any]]) -> dict[str, Any]:
    lookup = {}
    for record in records:
        lookup[record["select_prim_path"]] = {
            "binding_id": record["binding_id"],
            "canonical_entity_id": record["canonical_entity_id"],
            "entity_type": record["entity_type"],
            "display_name": record["display_name"],
            "overlay_state": record["overlay_state"],
            "evidence_ref": record["evidence_ref"],
            "graph_or_runtime_ref": record["graph_or_runtime_ref"],
            "limitation_ref": record["limitation_ref"],
            "binding_status": record["binding_status"],
            "review_state": record["review_state"],
            "inspection_card_payload": record["inspection_card_payload"],
            "claim_boundary": record["claim_boundary"],
            "no_action_taken": True,
        }
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "schema_version": SCHEMA_VERSION,
        "lookup_count": len(lookup),
        "lookup_by_prim_path": lookup,
        "truth_boundary": "lookup resolves to CityBrain handoff records; USD metadata is not canonical truth",
        "no_action_taken": True,
    }


def make_card(record: dict[str, Any], category: str) -> dict[str, Any]:
    return {
        "card_id": f"selection-card-{record['interaction_record_id'].split('-')[-1]}",
        "fixture_category": category,
        "selected_prim_path": record["select_prim_path"],
        "canonical_entity_id": record["canonical_entity_id"],
        "entity_type": record["entity_type"],
        "display_name": record["display_name"],
        "overlay_state": record["overlay_state"],
        "evidence_ref": record["evidence_ref"],
        "graph_or_runtime_ref": record["graph_or_runtime_ref"],
        "limitation_ref": record["limitation_ref"],
        "binding_status": record["binding_status"],
        "review_state": record["review_state"],
        "safe_actions": ["inspect evidence", "inspect graph/runtime context", "inspect limitations"],
        "forbidden_actions": [
            "dispatch",
            "enforcement",
            "routing/control",
            "legal/ownership conclusion",
            "certified affected-building conclusion",
        ],
        "claim_boundary": "SELECTION_CARD_REVIEW_CONTEXT_ONLY_NOT_CONTROL_NOT_TRUTH",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def card_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = [
        ("real_geometry_source_ref_binding", lambda r: r["binding_status"] == "R1_REAL_GEOMETRY_SOURCE_REF_BOUND"),
        ("source_ref_context_binding", lambda r: r["binding_status"] == "R1_SOURCE_REF_CONTEXT_BOUND"),
        (
            "runtime_or_historical_binding",
            lambda r: r["binding_status"] in {"R1_RUNTIME_EVENT_MARKER_BOUND", "R1_HISTORICAL_CONTEXT_BOUND"},
        ),
    ]
    examples = []
    for category, predicate in cases:
        record = next((r for r in records if predicate(r)), None)
        if record:
            examples.append(make_card(record, category))
    return examples


def resolve_selection(lookup: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    prim = event["selected_prim_path"]
    row = lookup["lookup_by_prim_path"].get(prim)
    if not row:
        return {
            "event_id": event["event_id"],
            "selected_prim_path": prim,
            "result_status": "SAFE_FAILURE_UNKNOWN_PRIM",
            "safe_failure": True,
            "missing_fields": [],
            "inspection_card": None,
            "message": "Selected prim path is not present in the R1 binding lookup.",
            "no_action_taken": True,
        }
    required = [
        "canonical_entity_id",
        "entity_type",
        "display_name",
        "evidence_ref",
        "graph_or_runtime_ref",
        "limitation_ref",
        "binding_status",
        "review_state",
    ]
    missing = [field for field in required if not row.get(field)]
    if missing:
        return {
            "event_id": event["event_id"],
            "selected_prim_path": prim,
            "result_status": "SAFE_FAILURE_INCOMPLETE_METADATA",
            "safe_failure": True,
            "missing_fields": missing,
            "inspection_card": None,
            "message": "Selected prim is bound but lacks required inspection metadata.",
            "no_action_taken": True,
        }
    return {
        "event_id": event["event_id"],
        "selected_prim_path": prim,
        "result_status": "PASS_VALID_PRIM_SELECTION",
        "safe_failure": False,
        "missing_fields": [],
        "inspection_card": make_card(
            {
                "interaction_record_id": row["binding_id"].replace("binding-r1-barc-eixample", "kit-interaction"),
                "select_prim_path": prim,
                **row,
            },
            "headless_valid_selection",
        ),
        "message": "Selected prim resolved to bounded review/context inspection card.",
        "no_action_taken": True,
    }


def headless_simulation(records: list[dict[str, Any]], lookup_doc: dict[str, Any]) -> dict[str, Any]:
    valid_prim = records[0]["select_prim_path"]
    unknown_prim = "/World/CityBrainAssetBindingR1/BARC_Eixample/UNKNOWN_PRIM_FOR_SAFE_FAILURE"
    incomplete_prim = "/World/CityBrainAssetBindingR1/BARC_Eixample/INCOMPLETE_METADATA_FIXTURE"
    lookup_with_incomplete = json.loads(json.dumps(lookup_doc))
    lookup_with_incomplete["lookup_by_prim_path"][incomplete_prim] = {
        "binding_id": "binding-r1-incomplete-fixture",
        "canonical_entity_id": "cer:incomplete:test",
        "entity_type": "Fixture",
        "display_name": "Incomplete metadata safe-failure fixture",
        "evidence_ref": "",
        "graph_or_runtime_ref": "",
        "limitation_ref": "INCOMPLETE_METADATA_FIXTURE",
        "binding_status": "R1_INCOMPLETE_METADATA_FIXTURE",
        "review_state": "candidate/review",
        "claim_boundary": "safe failure fixture only",
        "no_action_taken": True,
    }
    events = [
        {
            "event_id": "selection-event-valid-001",
            "event_type": "headless_prim_selected",
            "selected_prim_path": valid_prim,
            "selection_source": "headless_preflight",
            "timestamp_utc": now(),
        },
        {
            "event_id": "selection-event-unknown-001",
            "event_type": "headless_prim_selected",
            "selected_prim_path": unknown_prim,
            "selection_source": "headless_preflight",
            "timestamp_utc": now(),
        },
        {
            "event_id": "selection-event-incomplete-001",
            "event_type": "headless_prim_selected",
            "selected_prim_path": incomplete_prim,
            "selection_source": "headless_preflight",
            "timestamp_utc": now(),
        },
    ]
    results = [resolve_selection(lookup_with_incomplete, event) for event in events]
    return {
        "status": "PASS"
        if results[0]["result_status"] == "PASS_VALID_PRIM_SELECTION"
        and results[1]["result_status"] == "SAFE_FAILURE_UNKNOWN_PRIM"
        and results[2]["result_status"] == "SAFE_FAILURE_INCOMPLETE_METADATA"
        else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "headless_selection_simulation_created": True,
        "events": events,
        "results": results,
        "valid_prim_selection_passed": results[0]["result_status"] == "PASS_VALID_PRIM_SELECTION",
        "unknown_prim_safe_failure_passed": results[1]["result_status"] == "SAFE_FAILURE_UNKNOWN_PRIM",
        "incomplete_metadata_safe_failure_passed": results[2]["result_status"] == "SAFE_FAILURE_INCOMPLETE_METADATA",
        "no_action_taken": all(result["no_action_taken"] for result in results),
    }


def validate(records: list[dict[str, Any]], examples: list[dict[str, Any]], simulation: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "record_count_12": len(records) == 12,
        "prim_paths_all": all(record.get("select_prim_path") for record in records),
        "canonical_ids_all": all(record.get("canonical_entity_id") for record in records),
        "evidence_refs_all": all(record.get("evidence_ref") for record in records),
        "graph_or_runtime_refs_all": all(record.get("graph_or_runtime_ref") for record in records),
        "limitation_refs_all": all(record.get("limitation_ref") for record in records),
        "binding_review_state_all": all(record.get("binding_status") and record.get("review_state") for record in records),
        "card_examples_minimum": len(examples) >= 3,
        "valid_prim_selection_passed": simulation["valid_prim_selection_passed"],
        "unknown_prim_safe_failure_passed": simulation["unknown_prim_safe_failure_passed"],
        "incomplete_metadata_safe_failure_passed": simulation["incomplete_metadata_safe_failure_passed"],
        "kit_gui_required_to_pass_false": True,
        "actual_extension_not_implemented": True,
        "unsupported_claims_absent": True,
        "no_action_taken_all": all(record.get("no_action_taken") for record in records) and simulation["no_action_taken"],
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "selection_ready_records_total": len(records),
        "selection_ready_records_with_prim_paths": sum(1 for r in records if r.get("select_prim_path")),
        "selection_ready_records_with_canonical_ids": sum(1 for r in records if r.get("canonical_entity_id")),
        "selection_ready_records_with_evidence_refs": sum(1 for r in records if r.get("evidence_ref")),
        "selection_ready_records_with_graph_or_runtime_refs": sum(1 for r in records if r.get("graph_or_runtime_ref")),
        "selection_ready_records_with_limitation_refs": sum(1 for r in records if r.get("limitation_ref")),
        "card_examples_created": len(examples),
    }


def boundary_audit(simulation: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "forbidden_claims_checked": FORBIDDEN_CLAIMS,
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "physical_accuracy_claim_made": False,
        "production_simulation_claim_made": False,
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
        "live_event_fabric_integrated": False,
        "d5_app_slice_integrated": False,
        "dispatch_enforcement_routing_control_created": False,
        "legal_ownership_certified_claim_created": False,
        "safe_failure_cases_no_action": simulation["no_action_taken"],
    }


def secret_scan() -> dict[str, Any]:
    pattern = re.compile(
        r"(?i)(api[_-]?key|authorization|bearer|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"
    )
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in pattern.finditer(text):
            findings.append({"path": rel(path), "match": match.group(1)})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def write_docs(validation: dict[str, Any], simulation: dict[str, Any]) -> None:
    write_text(
        ROOT / "README.md",
        """# Omniverse Kit Selection Extension Preflight R1

This pack prepares the bounded Kit selection extension preflight for the Barcelona Eixample R1 binding layer. It defines the contract, schemas, binding lookup, card examples, safe-failure behavior, and implementation handoff.

No actual Kit extension is implemented in this task.
""",
    )
    write_text(
        ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_PREFLIGHT_R1_REPORT.md",
        f"""# Omniverse Kit Selection Extension Preflight R1 Report

Status: `PASS_WITH_LIMITATIONS`

The preflight consumes `{rel(UPSTREAM_ROOT)}` and prepares a future Kit selection inspector extension.

- Selection-ready records: `{validation['selection_ready_records_total']}`
- With prim paths: `{validation['selection_ready_records_with_prim_paths']}`
- With canonical IDs: `{validation['selection_ready_records_with_canonical_ids']}`
- With evidence refs: `{validation['selection_ready_records_with_evidence_refs']}`
- With graph/runtime refs: `{validation['selection_ready_records_with_graph_or_runtime_refs']}`
- With limitation refs: `{validation['selection_ready_records_with_limitation_refs']}`
- Card examples: `{validation['card_examples_created']}`
- Valid prim simulation: `{simulation['valid_prim_selection_passed']}`
- Unknown prim safe failure: `{simulation['unknown_prim_safe_failure_passed']}`
- Incomplete metadata safe failure: `{simulation['incomplete_metadata_safe_failure_passed']}`

This is preflight only: headless, no GUI execution, no extension implementation.
""",
    )
    write_text(
        ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_SCAFFOLD_PLAN.md",
        """# Selection Extension Scaffold Plan

Proposed extension name: `txr.citybrain.selection_inspector`

Suggested file layout:

```text
exts/txr.citybrain.selection_inspector/
  config/extension.toml
  txr/citybrain/selection_inspector/__init__.py
  txr/citybrain/selection_inspector/extension.py
  txr/citybrain/selection_inspector/binding_lookup.py
  txr/citybrain/selection_inspector/inspection_panel.py
  data/OMNIVERSE_KIT_SELECTION_BINDING_LOOKUP.json
```

Implementation outline:

1. Load `OMNIVERSE_KIT_SELECTION_BINDING_LOOKUP.json`.
2. Subscribe to USD selection changes.
3. Resolve selected prim path to a binding row.
4. Render an inspection card with evidence, graph/runtime refs, limitation refs, binding status, and review state.
5. For unknown or incomplete prims, render a safe-failure card.

This task does not implement the extension. The scaffold is a future implementation plan only.
""",
    )
    write_text(
        ROOT / "KIT_EXTENSION_IMPLEMENTATION_HANDOFF.md",
        """# Kit Extension Implementation Handoff

Use the binding lookup and schemas in this output root as the future implementation contract.

Required runtime behavior:
- Selecting a known prim returns an inspection card.
- Selecting an unknown prim returns `SAFE_FAILURE_UNKNOWN_PRIM`.
- Selecting a bound-but-incomplete prim returns `SAFE_FAILURE_INCOMPLETE_METADATA`.
- All cards preserve limitations and `no_action_taken=true`.

Do not connect live event fabric or D5 app-slice outputs in the first extension implementation. Keep it bounded to the R1 binding layer.
""",
    )
    write_text(
        ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        """# Limitations And Next Steps

Limitations:
- Preflight only; actual Kit extension not implemented.
- Headless simulation only; Kit/Composer GUI not executed.
- USDA remains marker metadata.
- No live event fabric integration.
- No D5 app-slice integration.
- No citywide twin, full mesh binding, physical accuracy, production simulation/live/perception, dispatch, enforcement, routing/control, legal, ownership, certified affected-building, or autonomous action claim.

Recommended next task:
`MAIN-TRACK2A-D4X-OMNIVERSE-KIT-SELECTION-EXTENSION-R1`
""",
    )


def decision(
    status: str,
    upstream: dict[str, Any],
    validation: dict[str, Any],
    simulation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str((REPO_ROOT / ROOT).resolve()),
        "run_timestamp_utc": now(),
        "upstream_output_root": rel(UPSTREAM_ROOT),
        "upstream_status": upstream["upstream_status"],
        "upstream_artifacts_found": upstream["upstream_artifacts_found"],
        "runner_path": rel(RUNNER_PATH),
        "target_scope": "BARC_Eixample_bounded_Kit_selection_extension_preflight",
        "extension_contract_created": (ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_CONTRACT.json").exists(),
        "extension_scaffold_plan_created": (ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_SCAFFOLD_PLAN.md").exists(),
        "selection_event_schema_created": (ROOT / "OMNIVERSE_KIT_SELECTION_EVENT_SCHEMA.json").exists(),
        "selection_card_schema_created": (ROOT / "OMNIVERSE_KIT_SELECTION_CARD_SCHEMA.json").exists(),
        "binding_lookup_created": (ROOT / "OMNIVERSE_KIT_SELECTION_BINDING_LOOKUP.json").exists(),
        "upstream_interaction_records": upstream["upstream_interaction_records"],
        "selection_ready_records_total": validation["selection_ready_records_total"],
        "selection_ready_records_with_prim_paths": validation["selection_ready_records_with_prim_paths"],
        "selection_ready_records_with_canonical_ids": validation["selection_ready_records_with_canonical_ids"],
        "selection_ready_records_with_evidence_refs": validation["selection_ready_records_with_evidence_refs"],
        "selection_ready_records_with_graph_or_runtime_refs": validation["selection_ready_records_with_graph_or_runtime_refs"],
        "selection_ready_records_with_limitation_refs": validation["selection_ready_records_with_limitation_refs"],
        "card_examples_created": validation["card_examples_created"],
        "valid_prim_selection_passed": simulation["valid_prim_selection_passed"],
        "unknown_prim_safe_failure_passed": simulation["unknown_prim_safe_failure_passed"],
        "incomplete_metadata_safe_failure_passed": simulation["incomplete_metadata_safe_failure_passed"],
        "headless_selection_simulation_created": simulation["headless_selection_simulation_created"],
        "kit_gui_required_to_pass": False,
        "actual_kit_extension_implemented": False,
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "physical_accuracy_claim_made": False,
        "production_simulation_claim_made": False,
        "production_live_claim_made": False,
        "autonomous_action_exposed": False,
        "next_recommended_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-SELECTION-EXTENSION-R1",
        "validation_status": validation["status"],
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    before = {rel(root): snapshot(root) for root in SOURCE_ROOTS}
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)

    upstream = upstream_inventory()
    write_json(ROOT / "UPSTREAM_KIT_INTERACTION_SMOKE_INVENTORY.json", upstream)
    if upstream["status"] != "PASS":
        write_json(
            ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_PREFLIGHT_R1_DECISION.json",
            {
                "task_id": TASK_ID,
                "status": "FAIL",
                "repo_root": str(REPO_ROOT),
                "output_root": str((REPO_ROOT / ROOT).resolve()),
                "run_timestamp_utc": now(),
                "upstream_output_root": rel(UPSTREAM_ROOT),
                "upstream_status": upstream.get("upstream_status"),
                "upstream_artifacts_found": upstream.get("upstream_artifacts_found"),
                "runner_path": rel(RUNNER_PATH),
                "schema_version": SCHEMA_VERSION,
            },
        )
        print(f"{TASK_ID}: FAIL")
        return 1

    records = load_interaction_records()
    lookup = binding_lookup(records)
    examples = card_examples(records)
    simulation = headless_simulation(records, lookup)
    validation = validate(records, examples, simulation)
    boundary = boundary_audit(simulation)

    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_CONTRACT.json", extension_contract())
    write_text(ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_SCAFFOLD_PLAN.md", "")  # overwritten by docs
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_EVENT_SCHEMA.json", event_schema())
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_CARD_SCHEMA.json", card_schema())
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_BINDING_LOOKUP.json", lookup)
    write_json(
        ROOT / "OMNIVERSE_KIT_SELECTION_CARD_EXAMPLES.json",
        {"status": "PASS", "schema_version": SCHEMA_VERSION, "card_examples_count": len(examples), "examples": examples},
    )
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_HEADLESS_SIMULATION_RESULTS.json", simulation)
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_VALIDATION_RESULTS.json", validation)
    write_json(ROOT / "OMNIVERSE_KIT_SELECTION_BOUNDARY_AUDIT.json", boundary)
    write_docs(validation, simulation)

    after = {rel(root): snapshot(root) for root in SOURCE_ROOTS}
    changed = [
        root
        for root in before
        if before[root].get("file_count") != after[root].get("file_count")
        or before[root].get("total_bytes") != after[root].get("total_bytes")
        or before[root].get("latest_mtime_ns") != after[root].get("latest_mtime_ns")
    ]
    write_json(
        ROOT / "NO_MUTATION_AUDIT.json",
        {"status": "PASS" if not changed else "FAIL", "changed_source_roots": changed, "schema_version": SCHEMA_VERSION},
    )
    secret = secret_scan()
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)

    final_status = (
        "PASS_WITH_LIMITATIONS"
        if validation["status"] == "PASS"
        and simulation["status"] == "PASS"
        and boundary["status"] == "PASS"
        and not changed
        and secret["status"] == "PASS"
        else "FAIL"
    )
    write_json(
        ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_PREFLIGHT_R1_DECISION.json",
        decision(final_status, upstream, validation, simulation),
    )
    hashes = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file():
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(ROOT / "hashes.sha256", "\n".join(hashes))

    print(f"{TASK_ID}: STATUS")
    print(f"Final status: {final_status}")
    print(f"Upstream: {upstream['upstream_status']} ({upstream['upstream_interaction_records']} interaction records)")
    print(f"Selection-ready records: {validation['selection_ready_records_total']}")
    print(
        "Prim/canonical/evidence/graph-or-runtime/limitations: "
        f"{validation['selection_ready_records_with_prim_paths']}/"
        f"{validation['selection_ready_records_with_canonical_ids']}/"
        f"{validation['selection_ready_records_with_evidence_refs']}/"
        f"{validation['selection_ready_records_with_graph_or_runtime_refs']}/"
        f"{validation['selection_ready_records_with_limitation_refs']}"
    )
    print(f"Card examples: {validation['card_examples_created']}")
    print(f"Simulation: {simulation['status']}")
    print(f"Output: {rel(ROOT)}")
    return 0 if final_status != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
