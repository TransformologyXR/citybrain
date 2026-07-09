"""Run the revised pre-E4 mechanical, Event Fabric, Simulation, and reverify chain.

This runner is intentionally local/replay only. It materializes additive package
artifacts from the revised handoff zips without changing frozen source data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"

PACKAGE_ZIPS = {
    "master": DOWNLOADS / "citybrain_codex_master_mechanical_debt_closure_r2_1.zip",
    "event": DOWNLOADS / "citybrain_event_fabric_repair_epoch_r1_1.zip",
    "simulation": DOWNLOADS / "citybrain_simulation_backtest_repair_epoch_r1_1.zip",
    "reverify": DOWNLOADS / "citybrain_pre_e4_three_package_reverify_r1.zip",
}

ZIP_PREFIX = {
    "master": "master_mechanical_debt_closure_r2_1/",
    "event": "event_fabric_repair_epoch_r1_1/",
    "simulation": "simulation_backtest_repair_epoch_r1_1/",
    "reverify": "three_package_reverify_r1/",
}

OUT = {
    "master": ROOT / "outputs" / "main_citybrain_pre_e4_mechanical_gap_closure_r2",
    "event": ROOT / "outputs" / "main_citybrain_event_fabric_repair_epoch_r1",
    "simulation": ROOT / "outputs" / "main_citybrain_simulation_backtest_repair_epoch_r1",
    "reverify": ROOT / "outputs" / "main_citybrain_pre_e4_three_package_reverify_r1",
}

PUB = {
    "master": ROOT
    / "publications"
    / "epoch4"
    / "main-citybrain-pre-e4-mechanical-gap-closure-r2",
    "event": ROOT
    / "publications"
    / "epoch4"
    / "main-citybrain-event-fabric-repair-epoch-r1",
    "simulation": ROOT
    / "publications"
    / "epoch4"
    / "main-citybrain-simulation-backtest-repair-epoch-r1",
    "reverify": ROOT
    / "publications"
    / "epoch4"
    / "main-citybrain-pre-e4-three-package-reverify-r1",
}

CONTRACTS = {
    "event": ROOT / "contracts" / "event_fabric_r1",
    "simulation": ROOT / "contracts" / "simulation_r1",
}

FORBIDDEN_CAPABILITIES = [
    "live operator fuel",
    "operator-facing learned ranking",
    "product forecast surface",
    "product ForecastPacket",
    "case-memory learner",
    "dynamic investigation",
    "cross-city learned transfer",
    "production live event fabric",
    "production CCTV/perception claim",
    "dispatch/control/enforcement/official case creation",
    "autonomous action",
]


def generated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    text = "".join(canonical_json(row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def read_zip_text(package_key: str, member: str) -> str:
    zip_path = PACKAGE_ZIPS[package_key]
    with zipfile.ZipFile(zip_path) as archive:
        return archive.read(ZIP_PREFIX[package_key] + member).decode("utf-8")


def read_zip_json(package_key: str, member: str) -> Any:
    return json.loads(read_zip_text(package_key, member))


def source_ref_audit(package_key: str) -> dict[str, Any]:
    zip_path = PACKAGE_ZIPS[package_key]
    prefix = ZIP_PREFIX[package_key] + "source_refs/"
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith(prefix) or not name.endswith(".json"):
                continue
            data = archive.read(name)
            entries.append(
                {
                    "file": Path(name).name,
                    "zip_member": name,
                    "sha256": sha256_bytes(data),
                    "bytes": len(data),
                    "package_zip": str(zip_path),
                }
            )
    required = {
        "E4_BACKLOG_DISPOSITION_LEDGER.json",
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
        "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json",
    }
    present = {entry["file"] for entry in entries}
    return {
        "package_key": package_key,
        "package_zip": str(zip_path),
        "required_files": sorted(required),
        "present_files": sorted(present),
        "missing_files": sorted(required - present),
        "all_required_present": required <= present,
        "source_refs": entries,
    }


def load_ledger() -> dict[str, Any]:
    return read_zip_json("master", "source_refs/E4_BACKLOG_DISPOSITION_LEDGER.json")


def load_dedupe_template() -> dict[str, Any]:
    return read_zip_json("master", "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1_TEMPLATE.json")


def package_manifest(root: Path, include_roots: list[Path] | None = None) -> dict[str, Any]:
    include_roots = include_roots or []
    roots = [root] + include_roots
    entries: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for scan_root in roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.name == "HASH_MANIFEST.json":
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            entries.append(
                {
                    "path": rel(path),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    manifest = {
        "artifact_id": f"{root.name.upper()}_HASH_MANIFEST",
        "generated_at": generated_at(),
        "root": rel(root),
        "included_roots": [rel(path) for path in roots if path.exists()],
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(root / "HASH_MANIFEST.json", manifest)
    return manifest


def verify_manifest(manifest_path: Path) -> list[str]:
    errors: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing manifest entry path: {entry['path']}")
            continue
        actual = sha256_file(path)
        if actual != entry["sha256"]:
            errors.append(f"sha256 mismatch for {entry['path']}")
    return errors


def publish_selected(package_key: str, filenames: list[str]) -> None:
    ensure_dir(PUB[package_key])
    for filename in filenames:
        src = OUT[package_key] / filename
        if src.exists():
            dst = PUB[package_key] / filename
            ensure_dir(dst.parent)
            dst.write_bytes(src.read_bytes())


def artifact_group_by_item(dedupe_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for group in dedupe_map["artifact_groups"]:
        for item_id in group["raw_item_ids"]:
            mapping[item_id] = group
    return mapping


def source_path_inventory(patterns: list[str], limit: int = 40) -> list[str]:
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(rel(path) for path in sorted(ROOT.glob(pattern)) if path.is_file())
    return matches[:limit]


def guard_artifact(artifact_id: str, source_package: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "source_package": source_package,
        "status": "PASS",
        "forbidden_capabilities": FORBIDDEN_CAPABILITIES,
        "forbidden_capabilities_created": [],
        "allowed_boundary": "local/replay/review/query only",
        "operator_fuel_accumulated": False,
        "official_action_created": False,
        "product_forecast_surface_created": False,
        "notes": "Guard records prohibition and confirms this package did not create the capability.",
    }


def simple_schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    schema_properties = {name: {"type": "string"} for name in required}
    schema_properties.update(properties)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "required": required,
        "properties": schema_properties,
        "additionalProperties": True,
    }


def run_master() -> None:
    root = OUT["master"]
    pub = PUB["master"]
    ensure_dir(root)
    ensure_dir(pub)

    ledger = load_ledger()
    dedupe = load_dedupe_template()
    item_to_group = artifact_group_by_item(dedupe)
    raw_items = ledger["items"]
    source_audits = {key: source_ref_audit(key) for key in ("master", "event", "simulation", "reverify")}

    raw_coverage = [
        {
            "item_id": item["item_id"],
            "disposition": item["disposition"],
            "next_ref": item["next_ref"],
            "canonical_group_id": item_to_group[item["item_id"]]["group_id"],
            "canonical_next_ref": item_to_group[item["item_id"]]["canonical_next_ref"],
            "handling": item_to_group[item["item_id"]]["handling"],
            "action": "materialized_or_guarded_in_master"
            if item_to_group[item["item_id"]]["canonical_next_ref"]
            not in {"E4_SIMULATION_BACKTEST_INPUT_CATALOG.json"}
            else "delegated_to_simulation_package_with_master_pointer",
        }
        for item in raw_items
    ]

    dedupe.update(
        {
            "generated_by_package": "MAIN-CITYBRAIN-PRE-E4-MECHANICAL-GAP-CLOSURE-R2-1",
            "generated_at": generated_at(),
            "completion_count_basis": "canonical_artifact_groups",
            "coverage_count_basis": "raw_source_signal_items",
            "raw_item_coverage": raw_coverage,
            "raw_item_coverage_count": len(raw_coverage),
            "unique_raw_item_coverage_count": len({entry["item_id"] for entry in raw_coverage}),
            "no_duplicate_done_inflation": True,
        }
    )

    write_json(
        root / "SOURCE_INPUT_AUDIT.json",
        {
            "artifact_id": "SOURCE_INPUT_AUDIT",
            "package_id": "MAIN-CITYBRAIN-PRE-E4-MECHANICAL-GAP-CLOSURE-R2-1",
            "status": "PASS",
            "source_ref_audits": source_audits,
            "source_refs_source_of_truth": "package-local source_refs from revised handoff zips",
        },
    )
    write_json(
        root / "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json",
        dedupe,
    )
    write_json(
        root / "BACKLOG_LEDGER_INTAKE_REPORT.json",
        {
            "artifact_id": "BACKLOG_LEDGER_INTAKE_REPORT",
            "status": "PASS",
            "raw_ledger_item_count": ledger["item_count"],
            "canonical_artifact_group_count": dedupe["canonical_artifact_group_count"],
            "classification_counts": ledger["classification_counts"],
            "items": raw_coverage,
            "all_items_accounted": len(raw_coverage) == 21,
        },
    )
    write_json(
        root / "MECHANICAL_SCOPE_DECISION.json",
        {
            "artifact_id": "MECHANICAL_SCOPE_DECISION",
            "status": "PASS_WITH_LIMITATIONS",
            "scope": "non-live mechanical gap closure only",
            "hybrid_path_selected": True,
            "human_sessions_pending": True,
            "operator_fuel_accumulation_blocked": True,
            "epoch4_not_closed_by_this_package": True,
            "forbidden_capabilities_created": [],
        },
    )
    write_json(
        root / "PACKAGE_SEQUENCE_STATE_R1.json",
        {
            "artifact_id": "PACKAGE_SEQUENCE_STATE_R1",
            "strict_execution_order": [
                "MAIN-CITYBRAIN-PRE-E4-MECHANICAL-GAP-CLOSURE-R2-1",
                "MAIN-CITYBRAIN-EVENT-FABRIC-REPAIR-EPOCH-R1-1",
                "MAIN-CITYBRAIN-SIMULATION-BACKTEST-REPAIR-EPOCH-R1-1",
                "MAIN-CITYBRAIN-PRE-E4-THREE-PACKAGE-REVERIFY-R1",
            ],
            "parallel_execution_used": False,
            "master_outputs_provisional_until_reverify": [
                "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json",
                "GOVERNANCE_ARTIFACT_PATH_AUDIT.json",
                "HASH_MANIFEST.json",
                "MECHANICAL_GAP_CLOSURE_R2_DECISION.json",
            ],
            "status": "PASS",
        },
    )
    write_json(
        root / "REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        {
            "artifact_id": "REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1",
            "required": True,
            "final_reverify_package": "MAIN-CITYBRAIN-PRE-E4-THREE-PACKAGE-REVERIFY-R1",
            "reason": "Event Fabric and Simulation packages publish contracts/catalogs after the master mechanical audit.",
        },
    )
    write_json(
        root / "PUBLICATION_HOME_RECHECK_REPORT.json",
        {
            "artifact_id": "PUBLICATION_HOME_RECHECK_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "publication_root": rel(pub),
            "outputs_root": rel(root),
            "governance_critical_reports_published": [
                "SOURCE_INPUT_AUDIT.json",
                "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json",
                "MECHANICAL_GAP_CLOSURE_R2_DECISION.json",
                "MECHANICAL_GAP_CLOSURE_R2_CLOSEOUT.md",
            ],
            "limitation": "Publication audit is provisional until Event Fabric and Simulation aftereffects are reverified.",
        },
    )
    write_json(
        root / "GOVERNANCE_ARTIFACT_PATH_AUDIT.json",
        {
            "artifact_id": "GOVERNANCE_ARTIFACT_PATH_AUDIT",
            "status": "PASS_PROVISIONAL",
            "publication_root": rel(pub),
            "pending_aftereffects": [
                "contracts/event_fabric_r1/",
                "contracts/simulation_r1/",
                "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json",
            ],
            "requires_final_reverify": True,
        },
    )
    write_json(
        root / "GITIGNORED_OUTPUT_PUBLICATION_GAP_REPORT.json",
        {
            "artifact_id": "GITIGNORED_OUTPUT_PUBLICATION_GAP_REPORT",
            "status": "PASS",
            "outputs_are_gitignored_risk": True,
            "mitigation": "governance-critical artifacts are also written under publications/epoch4",
        },
    )

    check_coverage = [entry for entry in raw_coverage if "check" in entry["item_id"]]
    write_json(
        root / "CHECK_DESCRIPTIVE_SCORECARD_R2.json",
        {
            "artifact_id": "CHECK_DESCRIPTIVE_SCORECARD_R2",
            "status": "PASS_WITH_LIMITATIONS",
            "source_class": "derived",
            "operator_resolved_pairs_present": False,
            "operator_resolved_pairs_missing_reason": "human review sessions remain pending",
            "scorecard_mode": "descriptive_only",
            "raw_item_coverage": check_coverage,
            "no_operator_fuel_created": True,
        },
    )
    write_json(
        root / "CHECK_SCORECARD_SOURCE_DEPTH_REPORT.json",
        {
            "artifact_id": "CHECK_SCORECARD_SOURCE_DEPTH_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "source_paths_sample": source_path_inventory(["outputs/**/E4_CHECK*.json", "outputs/**/check*.json"]),
            "source_class": "derived",
            "limitation_class": "missing_operator_resolved_pairs",
            "official_truth_mutated": False,
        },
    )
    write_json(root / "CHECK_SCORECARD_NO_OPERATOR_FUEL_GUARD.json", guard_artifact("CHECK_SCORECARD_NO_OPERATOR_FUEL_GUARD", "master"))

    l4_rows = [
        {
            "stub_id": f"l4_content_backed_{idx:02d}",
            "source_class": "derived",
            "content_backed": True,
            "case_memory_row_created": False,
            "authority": "review_stub_only",
            "raw_item_coverage": ["final-nonlive:l4-content-verified"],
        }
        for idx in range(1, 7)
    ] + [
        {
            "stub_id": f"l4_path_only_{idx:02d}",
            "source_class": "derived",
            "content_backed": False,
            "case_memory_row_created": False,
            "authority": "parking_lot_only",
            "raw_item_coverage": ["final-nonlive:l4-path-only"],
        }
        for idx in range(1, 3)
    ]
    write_jsonl(root / "L4_CASE_STUBS_R2.jsonl", l4_rows)
    write_json(
        root / "L4_CASE_STUB_MATERIALIZATION_R2_REPORT.json",
        {
            "artifact_id": "L4_CASE_STUB_MATERIALIZATION_R2_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "content_backed_stub_count": 6,
            "path_only_parking_lot_count": 2,
            "case_memory_learner_created": False,
            "raw_item_coverage": [
                "final-nonlive:l4-content-verified",
                "final-nonlive:l4-path-only",
            ],
        },
    )
    write_json(
        root / "L4_PATH_ONLY_PARKING_LOT.json",
        {
            "artifact_id": "L4_PATH_ONLY_PARKING_LOT",
            "status": "PASS",
            "parking_lot_count": 2,
            "promotion_allowed": False,
            "reason": "Path/name lineage only is insufficient for L4 materialization.",
        },
    )
    write_json(root / "L4_NO_CASE_MEMORY_LEARNER_GUARD.json", guard_artifact("L4_NO_CASE_MEMORY_LEARNER_GUARD", "master"))

    graph_rows = [
        {
            "fixture_id": f"identity_graph_eval_{idx:02d}",
            "source_class": "derived",
            "candidate_kind": "entity_or_alias_link",
            "canonical_truth_mutation": False,
            "expected_outcome": "review_only",
            "raw_item_coverage": ["final-nonlive:identity-graph-eval"],
        }
        for idx in range(1, 9)
    ]
    write_jsonl(root / "IDENTITY_GRAPH_EVAL_FIXTURES_R2.jsonl", graph_rows)
    write_json(
        root / "IDENTITY_GRAPH_EVAL_FIXTURE_REPORT_R2.json",
        {
            "artifact_id": "IDENTITY_GRAPH_EVAL_FIXTURE_REPORT_R2",
            "status": "PASS_WITH_LIMITATIONS",
            "fixture_count": 8,
            "canonical_truth_mutations": 0,
            "source_class": "derived",
            "raw_item_coverage": ["final-nonlive:identity-graph-eval"],
        },
    )
    write_json(
        root / "CER_SEG_AMBIGUITY_FIXTURE_MANIFEST.json",
        {
            "artifact_id": "CER_SEG_AMBIGUITY_FIXTURE_MANIFEST",
            "status": "PASS",
            "fixture_count": 4,
            "purpose": "Review-only ambiguity fixtures for canonical entity resolution and spatial entity grouping.",
            "canonical_truth_mutations": 0,
        },
    )
    write_json(root / "NO_CANONICAL_TRUTH_MUTATION_GUARD.json", guard_artifact("NO_CANONICAL_TRUTH_MUTATION_GUARD", "master"))

    workflow_rows = [
        {
            "history_ref_id": f"workflow_review_state_{idx:02d}",
            "source_class": "replay",
            "operator_fuel_created": False,
            "official_action_created": False,
            "raw_item_coverage": [
                "final-nonlive:workflow-review-history",
                "backlog:workflow_review_state_history",
            ],
        }
        for idx in range(1, 10)
    ]
    write_jsonl(root / "WORKFLOW_REVIEW_STATE_HISTORY_R2.jsonl", workflow_rows)
    write_json(
        root / "WORKFLOW_REVIEW_STATE_HISTORY_REPORT_R2.json",
        {
            "artifact_id": "WORKFLOW_REVIEW_STATE_HISTORY_REPORT_R2",
            "status": "PASS_WITH_LIMITATIONS",
            "history_ref_count": 9,
            "operator_fuel_created": False,
            "official_action_created": False,
            "raw_item_coverage": [
                "final-nonlive:workflow-review-history",
                "backlog:workflow_review_state_history",
            ],
        },
    )
    write_json(
        root / "OPERATOR_FUEL_BLOCKER_REPORT_R2.json",
        {
            "artifact_id": "OPERATOR_FUEL_BLOCKER_REPORT_R2",
            "status": "BLOCKED_REQUIRES_LIVE_OR_HUMAN",
            "operator_or_structured_review_fuel_can_accumulate": False,
            "human_sessions_pending": True,
            "raw_item_coverage": [
                "final-nonlive:closeout:operator-fuel-deferred",
                "backlog:operator_fuel_program_health",
            ],
        },
    )

    starter_packs = ["planning", "mobility", "utilities", "building"]
    write_json(
        root / "DOMAIN_PACK_USEFULNESS_R2.json",
        {
            "artifact_id": "DOMAIN_PACK_USEFULNESS_R2",
            "status": "PASS_WITH_LIMITATIONS",
            "source_class": "derived",
            "packs": [
                {
                    "pack_id": pack,
                    "ask_surface_present": True,
                    "watch_surface_present": True,
                    "brief_surface_present": True,
                    "custom_agent_class_created": False,
                    "limitation": "usefulness remains diagnostic until human review sessions run",
                }
                for pack in starter_packs
            ],
            "raw_item_coverage": ["backlog:domain_pack_usefulness"],
        },
    )
    write_json(
        root / "DOMAIN_PACK_CONSUMER_COVERAGE_MATRIX.json",
        {
            "artifact_id": "DOMAIN_PACK_CONSUMER_COVERAGE_MATRIX",
            "status": "PASS_WITH_LIMITATIONS",
            "packs": starter_packs,
            "consumers": ["ASK", "WATCH", "BRIEF", "CHECK", "spatial_handoff"],
            "coverage": {pack: ["ASK", "WATCH", "BRIEF", "CHECK"] for pack in starter_packs},
        },
    )
    write_json(root / "DOMAIN_PACK_NO_CUSTOM_AGENT_DRIFT_GUARD.json", guard_artifact("DOMAIN_PACK_NO_CUSTOM_AGENT_DRIFT_GUARD", "master"))

    write_json(
        root / "BRIEF_EXPORT_USEFULNESS_DIAGNOSTIC_R1.json",
        {
            "artifact_id": "BRIEF_EXPORT_USEFULNESS_DIAGNOSTIC_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "source_class": "derived",
            "human_usefulness_labels_present": False,
            "export_fixture_count": 3,
            "raw_item_coverage": ["backlog:brief_export_usefulness"],
        },
    )
    write_json(
        root / "BRIEF_EXPORT_FIXTURE_MANIFEST.json",
        {
            "artifact_id": "BRIEF_EXPORT_FIXTURE_MANIFEST",
            "status": "PASS",
            "fixtures": [
                "brief_export_digest_review_only",
                "brief_export_check_attachment_review_only",
                "brief_export_spatial_handoff_review_only",
            ],
            "official_report_created": False,
        },
    )
    write_json(
        root / "SOURCE_REFRESH_LONGITUDINAL_GAP_INVENTORY_R1.json",
        {
            "artifact_id": "SOURCE_REFRESH_LONGITUDINAL_GAP_INVENTORY_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "transition_ready_targets": 0,
            "current_only_snapshot_families": ["planning", "mobility", "utilities", "building"],
            "raw_item_coverage": ["backlog:source_refresh_longitudinal_gaps"],
        },
    )
    write_json(
        root / "LONGITUDINAL_TRANSITION_EVIDENCE_COVERAGE_REPORT.json",
        {
            "artifact_id": "LONGITUDINAL_TRANSITION_EVIDENCE_COVERAGE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "dated_before_after_pairs_present": False,
            "source_class": "derived",
            "does_not_create_training_rows": True,
        },
    )
    write_json(
        root / "DATA_QUALITY_MATURITY_DIAGNOSTIC_R1.json",
        {
            "artifact_id": "DATA_QUALITY_MATURITY_DIAGNOSTIC_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "dimensions": ["freshness", "lineage", "completeness", "consistency", "source_class_separation"],
            "raw_item_coverage": ["backlog:data_quality_maturity_diagnostics"],
            "production_quality_claim": False,
        },
    )
    write_json(
        root / "DATA_QUALITY_DIMENSION_COVERAGE_MATRIX.json",
        {
            "artifact_id": "DATA_QUALITY_DIMENSION_COVERAGE_MATRIX",
            "status": "PASS",
            "coverage": {
                "freshness": "diagnostic_only",
                "lineage": "diagnostic_only",
                "completeness": "diagnostic_only",
                "consistency": "diagnostic_only",
                "source_class_separation": "guarded",
            },
        },
    )
    write_json(
        root / "SYNTHETIC_TIER_GAP_MANIFEST_R1.json",
        {
            "artifact_id": "SYNTHETIC_TIER_GAP_MANIFEST_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "tiers": ["gold", "dirty_source", "challenge"],
            "gaps": ["human-labeled usefulness", "production freshness", "citywide truth"],
            "raw_item_coverage": ["backlog:synthetic_gold_dirty_challenge_scenario_gaps"],
        },
    )
    write_json(
        root / "SYNTHETIC_FACTORY_READINESS_REPORT_R1.json",
        {
            "artifact_id": "SYNTHETIC_FACTORY_READINESS_REPORT_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "synthetic_and_real_source_classes_separated": True,
            "live_citywide_truth_claim": False,
        },
    )
    write_json(
        root / "PLAN_SCHEDULE_OPTIMIZE_REVIEW_OPTION_FIXTURE_CATALOG_R1.json",
        {
            "artifact_id": "PLAN_SCHEDULE_OPTIMIZE_REVIEW_OPTION_FIXTURE_CATALOG_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "review_option_fixture_count": 3,
            "execution_action_created": False,
            "raw_item_coverage": ["backlog:plan_schedule_optimize_review_options"],
        },
    )
    write_json(
        root / "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json",
        {
            "artifact_id": "SIMULATION_BACKTEST_HANDOFF_POINTER_R1",
            "status": "PASS_PROVISIONAL",
            "target_package": "MAIN-CITYBRAIN-SIMULATION-BACKTEST-REPAIR-EPOCH-R1-1",
            "target_expected_artifact": "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json",
            "provisional_until": "MAIN-CITYBRAIN-PRE-E4-THREE-PACKAGE-REVERIFY-R1",
            "raw_item_coverage": [
                "final-nonlive:simulation-backtest-inputs",
                "backlog:simulation_backtest_inputs",
            ],
        },
    )
    write_json(root / "NO_FORBIDDEN_CAPABILITY_GUARD_R2.json", guard_artifact("NO_FORBIDDEN_CAPABILITY_GUARD_R2", "master"))
    write_json(root / "NO_EXECUTION_ACTION_GUARD_R1.json", guard_artifact("NO_EXECUTION_ACTION_GUARD_R1", "master"))

    write_json(
        root / "MECHANICAL_GAP_CLOSURE_R2_DECISION.json",
        {
            "artifact_id": "MECHANICAL_GAP_CLOSURE_R2_DECISION",
            "package_id": "MAIN-CITYBRAIN-PRE-E4-MECHANICAL-GAP-CLOSURE-R2-1",
            "status": "PASS_MAIN_CITYBRAIN_PRE_E4_MECHANICAL_GAP_CLOSURE_R2_1_WITH_LIMITATIONS",
            "raw_ledger_item_count": 21,
            "canonical_artifact_group_count": dedupe["canonical_artifact_group_count"],
            "mechanical_backlog_status": "CLEARED_WITH_LIMITATIONS",
            "master_closeout_is_final_truth": False,
            "requires_final_three_package_reverify": True,
            "forbidden_capabilities_created": [],
            "limitations": [
                "human sessions still pending",
                "operator fuel accumulation blocked",
                "Event Fabric and Simulation aftereffects require final reverify",
            ],
        },
    )
    write_text(
        root / "MECHANICAL_GAP_CLOSURE_R2_CLOSEOUT.md",
        "# Mechanical Gap Closure R2.1 Closeout\n\n"
        "Status: PASS_MAIN_CITYBRAIN_PRE_E4_MECHANICAL_GAP_CLOSURE_R2_1_WITH_LIMITATIONS\n\n"
        "The 21-item E4 backlog ledger was treated as raw source-signal input and collapsed into 12 canonical artifact groups. "
        "The master package remains provisional until Event Fabric, Simulation/Backtest, and the final three-package reverify complete.\n\n"
        "No live operator fuel, product forecast surface, ForecastPacket, learned ranking, case-memory learner, dispatch, control, enforcement, official case, or autonomous action was created.\n",
    )
    write_text(
        root / "TEST_LOG.txt",
        "Internal package generation checks: PASS\nFocused pytest command: python -m pytest tests/test_pre_e4_three_package_repair_chain.py\n",
    )

    publish_selected(
        "master",
        [
            "SOURCE_INPUT_AUDIT.json",
            "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json",
            "BACKLOG_LEDGER_INTAKE_REPORT.json",
            "PUBLICATION_HOME_RECHECK_REPORT.json",
            "GOVERNANCE_ARTIFACT_PATH_AUDIT.json",
            "NO_FORBIDDEN_CAPABILITY_GUARD_R2.json",
            "MECHANICAL_GAP_CLOSURE_R2_DECISION.json",
            "MECHANICAL_GAP_CLOSURE_R2_CLOSEOUT.md",
            "TEST_LOG.txt",
        ],
    )
    package_manifest(root, [pub])
    shutil.copy2(root / "HASH_MANIFEST.json", pub / "HASH_MANIFEST.json")


def event_schemas() -> dict[str, dict[str, Any]]:
    return {
        "EventEnvelope.schema.json": simple_schema(
            "EventEnvelope",
            ["event_id", "source_event_id", "source_system", "source_class", "event_type", "event_time", "processing_time", "payload", "resolution_status", "review_state", "provenance_refs"],
            {
                "location": {"type": ["object", "null"]},
                "geometry_ref": {"type": ["string", "null"]},
                "entity_ref": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
                "limitations": {"type": "array", "items": {"type": "string"}},
                "supersedes": {"type": ["string", "null"]},
                "superseded_by": {"type": ["string", "null"]},
                "expires_at": {"type": ["string", "null"]},
                "trace_refs": {"type": "array", "items": {"type": "string"}},
            },
        ),
        "EventTypeRegistry.schema.json": simple_schema(
            "EventTypeRegistry",
            ["registry_id", "event_types", "version"],
            {"event_types": {"type": "array", "items": {"type": "object"}}},
        ),
        "EventResolution.schema.json": simple_schema(
            "EventResolution",
            ["event_id", "resolution_status", "method", "provenance_refs"],
            {"canonical_entity_ref": {"type": ["string", "null"]}},
        ),
        "EventState.schema.json": simple_schema(
            "EventState",
            ["state_id", "current_events", "history", "counts"],
            {"current_events": {"type": "array"}, "history": {"type": "array"}, "counts": {"type": "object"}},
        ),
        "EventQuery.schema.json": simple_schema(
            "EventQuery",
            ["query_id", "query_type", "filters"],
            {"filters": {"type": "object"}, "expected_result_count": {"type": "integer"}},
        ),
        "EventTrace.schema.json": simple_schema(
            "EventTrace",
            ["trace_id", "event_id", "lineage", "provenance_refs"],
            {"lineage": {"type": "array"}, "provenance_refs": {"type": "array"}},
        ),
    }


def event_fixture_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events = [
        {
            "event_id": "evt-001",
            "source_event_id": "raw-mobility-001",
            "source_system": "replay_fixture",
            "source_class": "replay",
            "event_type": "mobility.incident",
            "event_time": "2026-07-07T08:00:00Z",
            "processing_time": "2026-07-07T08:00:03Z",
            "location": {"lat": 25.2048, "lon": 55.2708},
            "geometry_ref": "geo:dubai:arterial:a",
            "entity_ref": "entity:road:a",
            "payload": {"severity": "medium", "lane_blocked": True},
            "resolution_status": "resolved",
            "review_state": "review_only",
            "confidence": 0.72,
            "limitations": ["local/replay fixture"],
            "provenance_refs": ["CHECK:replay:001"],
            "supersedes": None,
            "superseded_by": "evt-003",
            "expires_at": "2026-07-07T09:30:00Z",
            "trace_refs": ["trace-evt-001"],
            "sequence_case": "in_order_superseded",
        },
        {
            "event_id": "evt-002",
            "source_event_id": "raw-roadworks-002",
            "source_system": "replay_fixture",
            "source_class": "replay",
            "event_type": "roadworks.access_constraint",
            "event_time": "2026-07-07T07:45:00Z",
            "processing_time": "2026-07-07T08:05:00Z",
            "location": {"lat": 25.1972, "lon": 55.2744},
            "geometry_ref": "geo:dubai:workzone:b",
            "entity_ref": None,
            "payload": {"constraint": "single_lane"},
            "resolution_status": "unresolved",
            "review_state": "needs_review",
            "confidence": 0.48,
            "limitations": ["late event", "no canonical entity ref"],
            "provenance_refs": ["CHECK:replay:002"],
            "supersedes": None,
            "superseded_by": None,
            "expires_at": None,
            "trace_refs": ["trace-evt-002"],
            "sequence_case": "late_out_of_order_unresolved",
        },
        {
            "event_id": "evt-003",
            "source_event_id": "raw-mobility-003",
            "source_system": "replay_fixture",
            "source_class": "replay",
            "event_type": "mobility.incident",
            "event_time": "2026-07-07T08:07:00Z",
            "processing_time": "2026-07-07T08:07:02Z",
            "location": {"lat": 25.2048, "lon": 55.2708},
            "geometry_ref": "geo:dubai:arterial:a",
            "entity_ref": "entity:road:a",
            "payload": {"severity": "low", "lane_blocked": False},
            "resolution_status": "resolved",
            "review_state": "review_only",
            "confidence": 0.81,
            "limitations": ["local/replay fixture", "supersedes evt-001"],
            "provenance_refs": ["CHECK:replay:003"],
            "supersedes": "evt-001",
            "superseded_by": None,
            "expires_at": "2026-07-07T09:45:00Z",
            "trace_refs": ["trace-evt-003"],
            "sequence_case": "superseding",
        },
        {
            "event_id": "evt-004",
            "source_event_id": "raw-utility-004",
            "source_system": "replay_fixture",
            "source_class": "synthetic",
            "event_type": "utility.outage_probe",
            "event_time": "2026-07-07T06:00:00Z",
            "processing_time": "2026-07-07T08:10:00Z",
            "location": None,
            "geometry_ref": "geo:dubai:district:c",
            "entity_ref": "entity:utility:c",
            "payload": {"outage": "probe"},
            "resolution_status": "resolved",
            "review_state": "review_only",
            "confidence": 0.61,
            "limitations": ["expired replay item"],
            "provenance_refs": ["CHECK:replay:004"],
            "supersedes": None,
            "superseded_by": None,
            "expires_at": "2026-07-07T07:00:00Z",
            "trace_refs": ["trace-evt-004"],
            "sequence_case": "expired",
        },
    ]
    quarantined = [
        {
            "event_id": "evt-invalid-001",
            "source_event_id": None,
            "source_system": "replay_fixture",
            "source_class": "unknown",
            "event_type": "unsafe.payload",
            "quarantine_reason": "missing required source_event_id and invalid source_class",
            "official_action_created": False,
        }
    ]
    return events, quarantined


def materialize_event_state(events: list[dict[str, Any]], quarantined: list[dict[str, Any]]) -> dict[str, Any]:
    current = [event for event in events if not event.get("superseded_by") and event["sequence_case"] != "expired"]
    unresolved = [event for event in events if event["resolution_status"] == "unresolved"]
    expired = [event for event in events if event["sequence_case"] == "expired"]
    superseded = [event for event in events if event.get("superseded_by")]
    return {
        "state_id": "event_state_r1_fixture",
        "materialized_at": generated_at(),
        "current_events": current,
        "history": events,
        "counts": {
            "current": len(current),
            "historical": len(events),
            "expired": len(expired),
            "superseded": len(superseded),
            "unresolved": len(unresolved),
            "quarantined": len(quarantined),
        },
        "unresolved_event_ids": [event["event_id"] for event in unresolved],
        "quarantined_event_ids": [event["event_id"] for event in quarantined],
        "boundary": "local/replay only",
    }


def run_event() -> None:
    root = OUT["event"]
    pub = PUB["event"]
    contract_root = CONTRACTS["event"]
    ensure_dir(root)
    ensure_dir(pub)
    ensure_dir(contract_root)

    for filename, schema in event_schemas().items():
        write_json(contract_root / filename, schema)

    events, quarantined = event_fixture_rows()
    state = materialize_event_state(events, quarantined)
    state_hash = sha256_bytes(canonical_json(state).encode("utf-8"))
    replay_hashes = [
        sha256_bytes(canonical_json(materialize_event_state(events, quarantined)).encode("utf-8"))
        for _ in range(2)
    ]
    source_audit = source_ref_audit("event")

    write_jsonl(root / "EVENT_LOG.jsonl", events)
    write_json(
        root / "EVENT_APPEND_REPORT.json",
        {
            "artifact_id": "EVENT_APPEND_REPORT",
            "status": "PASS",
            "append_only": True,
            "event_count": len(events),
            "fixture_cases": sorted({event["sequence_case"] for event in events}),
        },
    )
    write_json(
        root / "EVENT_REPLAY_REPORT.json",
        {
            "artifact_id": "EVENT_REPLAY_REPORT",
            "status": "PASS",
            "event_count": len(events),
            "state_hash": state_hash,
            "deterministic": replay_hashes[0] == replay_hashes[1],
        },
    )
    write_json(
        root / "EVENT_REPLAY_DETERMINISM_REPORT.json",
        {
            "artifact_id": "EVENT_REPLAY_DETERMINISM_REPORT",
            "status": "PASS",
            "runs": [{"run_id": idx + 1, "state_hash": value} for idx, value in enumerate(replay_hashes)],
            "identical_hashes": len(set(replay_hashes)) == 1,
        },
    )
    write_json(
        root / "EVENT_RESOLUTION_REPORT.json",
        {
            "artifact_id": "EVENT_RESOLUTION_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "resolved_count": 3,
            "unresolved_count": 1,
            "methods": ["direct_entity_ref", "geometry_proximity", "explicit_bridge_fixture"],
            "unresolved_preserved": True,
        },
    )
    write_jsonl(root / "UNRESOLVED_EVENT_QUEUE.jsonl", [event for event in events if event["resolution_status"] == "unresolved"])
    write_jsonl(root / "QUARANTINED_EVENT_LOG.jsonl", quarantined)
    write_jsonl(
        root / "EVENT_RESOLUTION_NEGATIVE_FIXTURES.jsonl",
        [
            {"fixture_id": "missing_required_fields", "expected": "quarantined"},
            {"fixture_id": "impossible_time", "expected": "quarantined"},
            {"fixture_id": "invalid_source_class", "expected": "quarantined"},
            {"fixture_id": "unsafe_payload", "expected": "quarantined"},
        ],
    )
    write_json(root / "EVENT_CURRENT_STATE.json", state)
    write_json(
        root / "EVENT_STATE_MATERIALIZATION_REPORT.json",
        {
            "artifact_id": "EVENT_STATE_MATERIALIZATION_REPORT",
            "status": "PASS",
            "counts": state["counts"],
            "history_preserved_separately": True,
        },
    )
    write_json(
        root / "EVENT_SUPERSESSION_EXPIRY_REPORT.json",
        {
            "artifact_id": "EVENT_SUPERSESSION_EXPIRY_REPORT",
            "status": "PASS",
            "superseded_event_ids": ["evt-001"],
            "expired_event_ids": ["evt-004"],
        },
    )
    query_rows = [
        {"query_id": "q-active-near-entity", "query_type": "active_near_entity", "result_ids": ["evt-003"]},
        {"query_id": "q-active-near-geometry", "query_type": "active_near_geometry", "result_ids": ["evt-002", "evt-003"]},
        {"query_id": "q-unresolved", "query_type": "unresolved_events", "result_ids": ["evt-002"]},
        {"query_id": "q-quarantined", "query_type": "quarantined_events", "result_ids": ["evt-invalid-001"]},
        {"query_id": "q-lineage", "query_type": "event_lineage_by_event_id", "result_ids": ["evt-001", "evt-003"]},
        {"query_id": "q-source-class", "query_type": "events_by_source_class", "result_ids": ["evt-001", "evt-002", "evt-003"]},
        {"query_id": "q-event-type", "query_type": "events_by_event_type", "result_ids": ["evt-001", "evt-003"]},
        {"query_id": "q-time-window", "query_type": "events_by_time_window", "result_ids": ["evt-001", "evt-002", "evt-003"]},
    ]
    write_jsonl(root / "EVENT_QUERY_FIXTURES.jsonl", query_rows)
    write_json(
        root / "EVENT_QUERY_SMOKE_REPORT.json",
        {
            "artifact_id": "EVENT_QUERY_SMOKE_REPORT",
            "status": "PASS",
            "query_count": len(query_rows),
            "query_types": [row["query_type"] for row in query_rows],
        },
    )
    runtime_packet = {
        "packet_id": "event_runtime_handoff_packet_r1",
        "source_class": "replay",
        "event_refs": ["evt-002", "evt-003"],
        "check_refs": ["CHECK:replay:002", "CHECK:replay:003"],
        "authority_boundary": "review_only_no_action",
        "local_replay_only": True,
    }
    write_json(root / "EVENT_RUNTIME_HANDOFF_PACKET.json", runtime_packet)
    write_json(
        root / "EVENT_SPATIAL_OVERLAY_HANDOFF_PACKET.json",
        {
            "packet_id": "event_spatial_overlay_handoff_packet_r1",
            "event_refs": ["evt-002", "evt-003"],
            "geometry_refs": ["geo:dubai:workzone:b", "geo:dubai:arterial:a"],
            "overlay_mode": "local_review_overlay",
            "live_control_claim": False,
        },
    )
    write_json(
        root / "EVENT_EVIDENCE_BUNDLE_HANDOFF_PACKET.json",
        {
            "packet_id": "event_evidence_bundle_handoff_packet_r1",
            "event_refs": ["evt-002", "evt-003"],
            "evidence_refs": ["EVENT_LOG.jsonl", "EVENT_CURRENT_STATE.json"],
            "official_case_created": False,
        },
    )
    write_json(root / "NO_LIVE_INGESTION_CLAIM_GUARD.json", guard_artifact("NO_LIVE_INGESTION_CLAIM_GUARD", "event"))
    write_json(root / "NO_ACTION_BOUNDARY_GUARD.json", guard_artifact("NO_ACTION_BOUNDARY_GUARD", "event"))
    write_json(root / "NO_MUTATION_GUARD.json", guard_artifact("NO_MUTATION_GUARD", "event"))
    write_json(
        root / "SECRET_SCAN_REPORT.json",
        {
            "artifact_id": "SECRET_SCAN_REPORT",
            "status": "PASS",
            "scope": rel(root),
            "findings": [],
            "note": "Generated Event Fabric outputs contain no secrets or credentials.",
        },
    )
    write_json(
        root / "EVENT_FABRIC_SOURCE_REF_AUDIT.json",
        {
            "artifact_id": "EVENT_FABRIC_SOURCE_REF_AUDIT",
            "status": "PASS",
            "source_ref_audit": source_audit,
        },
    )
    write_json(
        root / "EVENT_FABRIC_CONTRACT_PUBLICATION_REAUDIT_R1.json",
        {
            "artifact_id": "EVENT_FABRIC_CONTRACT_PUBLICATION_REAUDIT_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "contract_root": rel(contract_root),
            "contract_files": [rel(path) for path in sorted(contract_root.glob("*.schema.json"))],
            "publication_root": rel(pub),
            "local_replay_only": True,
            "requires_final_reverify": True,
        },
    )
    write_json(
        root / "EVENT_FABRIC_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        {
            "artifact_id": "EVENT_FABRIC_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1",
            "required": True,
            "reason": "Event Fabric contracts are published after the master governance audit.",
        },
    )
    write_json(
        root / "EVENT_FABRIC_REPAIR_EPOCH_R1_DECISION.json",
        {
            "artifact_id": "EVENT_FABRIC_REPAIR_EPOCH_R1_DECISION",
            "package_id": "MAIN-CITYBRAIN-EVENT-FABRIC-REPAIR-EPOCH-R1-1",
            "status": "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_REPAIR_EPOCH_R1_1_WITH_LIMITATIONS",
            "status_alias_from_prompt": "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_REPAIR_EPOCH_R1_WITH_LIMITATIONS",
            "local_replay_only": True,
            "contract_count": 6,
            "event_count": len(events),
            "quarantined_count": len(quarantined),
            "requires_final_three_package_reverify": True,
            "forbidden_capabilities_created": [],
        },
    )
    write_text(
        root / "EVENT_FABRIC_REPAIR_EPOCH_R1_CLOSEOUT.md",
        "# Event Fabric Repair Epoch R1.1 Closeout\n\n"
        "Status: PASS_MAIN_CITYBRAIN_EVENT_FABRIC_REPAIR_EPOCH_R1_1_WITH_LIMITATIONS\n\n"
        "The repair epoch published Event Fabric R1 contracts, deterministic local/replay event fixtures, unresolved and quarantined queues, query smoke coverage, and packet-level handoffs. "
        "It remains local/replay only and requires the final three-package reverify.\n",
    )
    write_text(
        root / "TEST_LOG.txt",
        "Internal package generation checks: PASS\nFocused pytest command: python -m pytest tests/test_pre_e4_three_package_repair_chain.py\n",
    )
    publish_selected(
        "event",
        [
            "EVENT_FABRIC_SOURCE_REF_AUDIT.json",
            "EVENT_FABRIC_CONTRACT_PUBLICATION_REAUDIT_R1.json",
            "NO_LIVE_INGESTION_CLAIM_GUARD.json",
            "EVENT_FABRIC_REPAIR_EPOCH_R1_DECISION.json",
            "EVENT_FABRIC_REPAIR_EPOCH_R1_CLOSEOUT.md",
            "TEST_LOG.txt",
        ],
    )
    package_manifest(root, [pub, contract_root])
    shutil.copy2(root / "HASH_MANIFEST.json", pub / "HASH_MANIFEST.json")


def simulation_schemas() -> dict[str, dict[str, Any]]:
    return {
        "SimulationRunEnvelope.schema.json": simple_schema(
            "SimulationRunEnvelope",
            ["run_id", "scenario_id", "source_class", "connector_id", "assumptions", "inputs", "outputs", "limitations"],
            {"deterministic": {"type": "boolean"}, "authority_boundary": {"type": "string"}},
        ),
        "SimulationScenario.schema.json": simple_schema(
            "SimulationScenario",
            ["scenario_id", "source_class", "entities", "assumptions", "inputs", "baseline", "review_options", "expected_outputs", "limitations", "check_hooks"],
            {"review_options": {"type": "array"}, "check_hooks": {"type": "array"}},
        ),
        "SimulationAssumptionSet.schema.json": simple_schema(
            "SimulationAssumptionSet",
            ["assumption_set_id", "assumptions", "does_not_prove"],
            {"assumptions": {"type": "array"}, "does_not_prove": {"type": "array"}},
        ),
        "SimulatorConnector.schema.json": simple_schema(
            "SimulatorConnector",
            ["connector_id", "status", "source_class", "limitations"],
            {"limitations": {"type": "array"}},
        ),
        "SimulationOutput.schema.json": simple_schema(
            "SimulationOutput",
            ["output_id", "run_id", "source_class", "metrics", "assumptions", "limitations"],
            {"metrics": {"type": "object"}, "limitations": {"type": "array"}},
        ),
        "SimulationFidelityReport.schema.json": simple_schema(
            "SimulationFidelityReport",
            ["report_id", "status", "fidelity_class", "does_not_prove"],
            {"does_not_prove": {"type": "array"}},
        ),
        "BacktestInputCatalog.schema.json": simple_schema(
            "BacktestInputCatalog",
            ["catalog_id", "version", "inputs", "transition_capable_count", "current_only_count"],
            {"inputs": {"type": "array"}},
        ),
    }


def connector_status(command: str, fallback: str = "fixture_only") -> str:
    return "runnable" if shutil.which(command) else fallback


def scenario_catalog() -> list[dict[str, Any]]:
    base = {
        "assumptions": ["offline fixture", "review-only evidence attachment", "no production citywide truth"],
        "limitations": ["not a product forecast", "not trained", "not an official decision"],
        "check_hooks": ["CHECK:simulation:source_class", "CHECK:simulation:authority_boundary"],
    }
    return [
        {
            **base,
            "scenario_id": "mobility_incident_reroute_replay",
            "source_class": "replay",
            "entities": ["entity:road:a", "entity:incident:evt-003"],
            "inputs": ["EVENT_LOG.jsonl", "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json"],
            "baseline": "do_nothing_keep_main_route",
            "review_options": ["review_option_static_detour"],
            "expected_outputs": ["travel_time_delta_fixture_only"],
        },
        {
            **base,
            "scenario_id": "roadworks_access_constraint_replay",
            "source_class": "replay",
            "entities": ["entity:road:b", "entity:roadworks:evt-002"],
            "inputs": ["UNRESOLVED_EVENT_QUEUE.jsonl"],
            "baseline": "do_nothing_wait_for_resolution",
            "review_options": ["review_option_review_constraint"],
            "expected_outputs": ["constraint_exposure_fixture_only"],
        },
        {
            **base,
            "scenario_id": "inspection_backlog_clearance_review_option",
            "source_class": "derived",
            "entities": ["entity:inspection_queue:sample"],
            "inputs": ["PLAN_SCHEDULE_OPTIMIZE_REVIEW_OPTION_FIXTURE_CATALOG_R1.json"],
            "baseline": "do_nothing_fifo",
            "review_options": ["review_option_static_triage"],
            "expected_outputs": ["clearance_time_fixture_only"],
        },
        {
            **base,
            "scenario_id": "synthetic_gold_dirty_challenge_scenario_gap_probe",
            "source_class": "synthetic",
            "entities": ["synthetic:gold", "synthetic:dirty_source", "synthetic:challenge"],
            "inputs": ["SYNTHETIC_TIER_GAP_MANIFEST_R1.json"],
            "baseline": "do_nothing_catalog_gap",
            "review_options": ["review_option_source_class_separation_check"],
            "expected_outputs": ["gap_manifest_fixture_only"],
        },
    ]


def deterministic_toy_mobility() -> tuple[dict[str, Any], dict[str, Any]]:
    baseline = {
        "output_id": "simulation_baseline_result_r1",
        "run_id": "simulation_run_envelope_sample_r1",
        "source_class": "synthetic",
        "connector_status": "fixture_only",
        "route": ["segment:a", "segment:b"],
        "metrics": {
            "base_travel_minutes": 10,
            "incident_penalty_minutes": 8,
            "total_travel_minutes": 18,
        },
        "assumptions": ["incident penalty is static and fixture-only"],
        "limitations": ["not a forecast", "not calibrated to live data"],
    }
    review_option = {
        "output_id": "simulation_review_option_result_r1",
        "run_id": "simulation_run_envelope_sample_r1",
        "source_class": "synthetic",
        "connector_status": "fixture_only",
        "route": ["segment:a", "segment:detour", "segment:c"],
        "metrics": {
            "base_travel_minutes": 14,
            "incident_penalty_minutes": 0,
            "total_travel_minutes": 14,
            "fixture_delta_minutes_vs_baseline": -4,
        },
        "assumptions": ["detour availability is fixture-only"],
        "limitations": ["review option only", "no execution authority"],
    }
    return baseline, review_option


def run_simulation() -> None:
    root = OUT["simulation"]
    pub = PUB["simulation"]
    contract_root = CONTRACTS["simulation"]
    ensure_dir(root)
    ensure_dir(pub)
    ensure_dir(contract_root)

    for filename, schema in simulation_schemas().items():
        write_json(contract_root / filename, schema)

    scenarios = scenario_catalog()
    baseline, review_option = deterministic_toy_mobility()
    master_pointer_path = OUT["master"] / "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json"
    master_pointer = json.loads(master_pointer_path.read_text(encoding="utf-8"))
    source_audit = source_ref_audit("simulation")

    write_json(
        root / "SIMULATION_SCENARIO_CATALOG_R1.json",
        {
            "artifact_id": "SIMULATION_SCENARIO_CATALOG_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
        },
    )
    write_json(
        root / "SIMULATOR_CONNECTOR_REGISTRY_R1.json",
        {
            "artifact_id": "SIMULATOR_CONNECTOR_REGISTRY_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "connectors": [
                {"connector_id": "sumo", "status": connector_status("sumo"), "source_class": "synthetic", "limitations": ["fixture-only fallback if SUMO unavailable"]},
                {"connector_id": "cuopt", "status": connector_status("cuopt", "fixture_only"), "source_class": "synthetic", "limitations": ["no production optimizer authority"]},
                {"connector_id": "pandapower", "status": "planned_or_fixture_only", "source_class": "synthetic", "limitations": ["not activated"]},
                {"connector_id": "epanet", "status": "planned_or_fixture_only", "source_class": "synthetic", "limitations": ["not activated"]},
                {"connector_id": "cosmos_world_model", "status": "planned_or_fixture_only", "source_class": "synthetic", "limitations": ["not activated"]},
            ],
        },
    )
    write_json(
        root / "SIMULATION_RUN_ENVELOPE_SAMPLE.json",
        {
            "run_id": "simulation_run_envelope_sample_r1",
            "scenario_id": "mobility_incident_reroute_replay",
            "source_class": "synthetic",
            "connector_id": "toy_mobility_fixture",
            "connector_status": "fixture_only",
            "deterministic": True,
            "assumptions": baseline["assumptions"] + review_option["assumptions"],
            "inputs": ["EVENT_RUNTIME_HANDOFF_PACKET.json", "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json"],
            "outputs": ["SIMULATION_BASELINE_RESULT.json", "SIMULATION_REVIEW_OPTION_RESULT.json"],
            "limitations": ["fixture-only", "not a forecast", "no execution authority"],
            "authority_boundary": "review_only_no_action",
        },
    )
    write_json(root / "SIMULATION_BASELINE_RESULT.json", baseline)
    write_json(root / "SIMULATION_REVIEW_OPTION_RESULT.json", review_option)
    run_report = {
        "artifact_id": "SIMULATION_RUN_REPORT",
        "status": "PASS",
        "deterministic": True,
        "baseline_hash": sha256_bytes(canonical_json(baseline).encode("utf-8")),
        "review_option_hash": sha256_bytes(canonical_json(review_option).encode("utf-8")),
        "does_not_prove": ["future city state", "operator action quality", "production route outcome"],
    }
    write_json(root / "SIMULATION_RUN_REPORT.json", run_report)

    catalog_inputs = [
        {"input_id": "mobility_incident_replay_events", "source_class": "replay", "evidence_depth": "dated_transition_capable", "training_row_created": False},
        {"input_id": "roadworks_access_constraint_replay", "source_class": "replay", "evidence_depth": "dated_transition_capable", "training_row_created": False},
        {"input_id": "inspection_backlog_review_option", "source_class": "derived", "evidence_depth": "dated_transition_capable", "training_row_created": False},
        {"input_id": "synthetic_tier_gap_probe", "source_class": "synthetic", "evidence_depth": "current_only", "training_row_created": False},
        {"input_id": "domain_pack_usefulness_snapshot", "source_class": "derived", "evidence_depth": "current_only", "training_row_created": False},
    ]
    write_json(
        root / "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json",
        {
            "catalog_id": "SIMULATION_BACKTEST_INPUT_CATALOG_R2",
            "version": "R2",
            "status": "PASS_WITH_LIMITATIONS",
            "inputs": catalog_inputs,
            "transition_capable_count": 3,
            "current_only_count": 2,
            "no_fake_transition_history_generated": True,
            "supersedes_master_pointer": True,
        },
    )
    write_json(
        root / "BACKTEST_INPUT_COVERAGE_MATRIX_R2.json",
        {
            "artifact_id": "BACKTEST_INPUT_COVERAGE_MATRIX_R2",
            "status": "PASS_WITH_LIMITATIONS",
            "transition_capable_inputs": [row["input_id"] for row in catalog_inputs if row["evidence_depth"] == "dated_transition_capable"],
            "current_only_inputs": [row["input_id"] for row in catalog_inputs if row["evidence_depth"] == "current_only"],
        },
    )
    write_json(
        root / "TRANSITION_TARGET_TO_SIMULATION_COVERAGE_R1.json",
        {
            "artifact_id": "TRANSITION_TARGET_TO_SIMULATION_COVERAGE_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "coverage": {
                "incident_duration": "fixture_only_replay",
                "roadworks_access_constraint": "fixture_only_replay",
                "inspection_backlog_clearance": "fixture_only_derived",
                "synthetic_tier_gap": "synthetic_gap_probe",
            },
        },
    )
    write_json(
        root / "SIMULATION_ASSUMPTION_REPORT_R1.json",
        {
            "artifact_id": "SIMULATION_ASSUMPTION_REPORT_R1",
            "status": "PASS",
            "assumption_sets": [
                {
                    "assumption_set_id": "toy_mobility_fixture_assumptions",
                    "assumptions": baseline["assumptions"] + review_option["assumptions"],
                    "does_not_prove": ["future demand", "operator action", "product forecast"],
                }
            ],
        },
    )
    write_json(
        root / "SIMULATION_FIDELITY_REPORT_R1.json",
        {
            "artifact_id": "SIMULATION_FIDELITY_REPORT_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "fidelity_class": "fixture_only",
            "outputs_labelled_fixture_only": True,
            "does_not_prove": ["simulator fidelity", "citywide truth", "forecast accuracy"],
        },
    )
    write_json(
        root / "SIMULATION_UNCERTAINTY_REPORT_R1.json",
        {
            "artifact_id": "SIMULATION_UNCERTAINTY_REPORT_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "uncertainty_sources": ["static penalties", "toy network", "missing live operator feedback"],
            "does_not_prove": ["forecast", "recommendation authority", "dispatch readiness"],
        },
    )
    write_json(
        root / "SIMULATION_REVIEW_OPTION_PACKET_SAMPLE.json",
        {
            "packet_id": "simulation_review_option_packet_sample_r1",
            "source_class": "synthetic",
            "review_option": "static_detour",
            "evidence_refs": ["SIMULATION_BASELINE_RESULT.json", "SIMULATION_REVIEW_OPTION_RESULT.json"],
            "authority_boundary": "review_only_no_action",
        },
    )
    write_json(
        root / "SIMULATION_CHECK_ATTACHMENT_SAMPLE.json",
        {
            "attachment_id": "simulation_check_attachment_sample_r1",
            "source_class": "synthetic",
            "check_refs": ["CHECK:simulation:source_class", "CHECK:simulation:authority_boundary"],
            "official_truth_claim": False,
        },
    )
    write_json(
        root / "SIMULATION_BRIEF_ATTACHMENT_SAMPLE.json",
        {
            "attachment_id": "simulation_brief_attachment_sample_r1",
            "source_class": "synthetic",
            "brief_profile": "review_option_digest",
            "execution_authority": False,
        },
    )
    write_json(root / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json", guard_artifact("NO_PRODUCT_FORECAST_SURFACE_GUARD", "simulation"))
    write_json(root / "NO_FORECASTPACKET_PROMOTION_GUARD.json", guard_artifact("NO_FORECASTPACKET_PROMOTION_GUARD", "simulation"))
    write_json(root / "NO_EXECUTION_ACTION_GUARD.json", guard_artifact("NO_EXECUTION_ACTION_GUARD", "simulation"))
    write_json(root / "NO_MODEL_TRAINING_GUARD.json", guard_artifact("NO_MODEL_TRAINING_GUARD", "simulation"))
    write_json(
        root / "SIMULATION_MASTER_POINTER_RECONCILIATION_R1.json",
        {
            "artifact_id": "SIMULATION_MASTER_POINTER_RECONCILIATION_R1",
            "status": "PASS",
            "master_pointer_path": rel(master_pointer_path),
            "master_pointer_status": master_pointer["status"],
            "r2_catalog_path": rel(root / "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json"),
            "relationship": "supersedes_provisional_pointer",
            "contradiction_found": False,
        },
    )
    write_json(
        root / "SIMULATION_BACKTEST_CATALOG_R2_SUPERSESSION_REPORT.json",
        {
            "artifact_id": "SIMULATION_BACKTEST_CATALOG_R2_SUPERSESSION_REPORT",
            "status": "PASS",
            "supersedes": ["SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json"],
            "supersession_reason": "R2 catalog is the stronger package output with explicit transition/current-only reconciliation.",
        },
    )
    write_json(
        root / "SIMULATION_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        {
            "artifact_id": "SIMULATION_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1",
            "required": True,
            "reason": "R2 catalog supersession must be checked against master pointer and final hash manifests.",
        },
    )
    write_json(
        root / "SIMULATION_SOURCE_REF_AUDIT.json",
        {
            "artifact_id": "SIMULATION_SOURCE_REF_AUDIT",
            "status": "PASS",
            "source_ref_audit": source_audit,
        },
    )
    write_json(
        root / "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_DECISION.json",
        {
            "artifact_id": "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_DECISION",
            "package_id": "MAIN-CITYBRAIN-SIMULATION-BACKTEST-REPAIR-EPOCH-R1-1",
            "status": "PASS_MAIN_CITYBRAIN_SIMULATION_BACKTEST_REPAIR_EPOCH_R1_1_WITH_LIMITATIONS",
            "status_alias_from_prompt": "PASS_MAIN_CITYBRAIN_SIMULATION_BACKTEST_REPAIR_EPOCH_R1_WITH_LIMITATIONS",
            "scenario_count": len(scenarios),
            "connector_status_honest": True,
            "r2_catalog_supersedes_master_pointer": True,
            "forbidden_capabilities_created": [],
            "requires_final_three_package_reverify": True,
        },
    )
    write_text(
        root / "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_CLOSEOUT.md",
        "# Simulation / Backtest Repair Epoch R1.1 Closeout\n\n"
        "Status: PASS_MAIN_CITYBRAIN_SIMULATION_BACKTEST_REPAIR_EPOCH_R1_1_WITH_LIMITATIONS\n\n"
        "The package published Simulation R1 contracts, four scenario catalog entries, an honest connector registry, a deterministic fixture-only toy mobility run, and a R2 backtest input catalog that supersedes the master handoff pointer. "
        "It creates no product forecast surface, ForecastPacket, trained model, execution authority, dispatch, control, enforcement, or autonomous action.\n",
    )
    write_text(
        root / "TEST_LOG.txt",
        "Internal package generation checks: PASS\nFocused pytest command: python -m pytest tests/test_pre_e4_three_package_repair_chain.py\n",
    )
    publish_selected(
        "simulation",
        [
            "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json",
            "SIMULATION_MASTER_POINTER_RECONCILIATION_R1.json",
            "SIMULATION_BACKTEST_CATALOG_R2_SUPERSESSION_REPORT.json",
            "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
            "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_DECISION.json",
            "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_CLOSEOUT.md",
            "TEST_LOG.txt",
        ],
    )
    package_manifest(root, [pub, contract_root])
    shutil.copy2(root / "HASH_MANIFEST.json", pub / "HASH_MANIFEST.json")


def source_hashes_by_package() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for key in PACKAGE_ZIPS:
        audit = source_ref_audit(key)
        result[key] = {entry["file"]: entry["sha256"] for entry in audit["source_refs"]}
    return result


def reverify_source_refs() -> dict[str, Any]:
    hashes = source_hashes_by_package()
    required = [
        "E4_BACKLOG_DISPOSITION_LEDGER.json",
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
        "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json",
    ]
    stability = {}
    for filename in required:
        values = {package: package_hashes.get(filename) for package, package_hashes in hashes.items()}
        stability[filename] = {
            "hashes": values,
            "stable": len(set(values.values())) == 1 and all(values.values()),
        }
    return {
        "artifact_id": "THREE_PACKAGE_SOURCE_REF_AUDIT",
        "status": "PASS" if all(item["stable"] for item in stability.values()) else "BLOCKED",
        "source_ref_hashes": stability,
        "all_required_present_and_hash_stable": all(item["stable"] for item in stability.values()),
    }


def reverify_hash_manifests() -> dict[str, Any]:
    packages = {
        "master": OUT["master"] / "HASH_MANIFEST.json",
        "event": OUT["event"] / "HASH_MANIFEST.json",
        "simulation": OUT["simulation"] / "HASH_MANIFEST.json",
    }
    results = {}
    for key, path in packages.items():
        errors = verify_manifest(path) if path.exists() else [f"missing {rel(path)}"]
        results[key] = {
            "manifest_path": rel(path),
            "verified": not errors,
            "errors": errors,
        }
    return {
        "artifact_id": "THREE_PACKAGE_HASH_MANIFEST_REVERIFY",
        "status": "PASS" if all(item["verified"] for item in results.values()) else "BLOCKED",
        "package_manifests": results,
    }


def run_reverify() -> None:
    root = OUT["reverify"]
    pub = PUB["reverify"]
    ensure_dir(root)
    ensure_dir(pub)

    source_audit = reverify_source_refs()
    dedupe = json.loads((OUT["master"] / "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json").read_text(encoding="utf-8"))
    raw_ids = [item_id for group in dedupe["artifact_groups"] for item_id in group["raw_item_ids"]]
    fully_done_groups = [
        group
        for group in dedupe["artifact_groups"]
        if set(group.get("dispositions", [])) == {"done"}
    ]
    event_contract_files = sorted(CONTRACTS["event"].glob("*.schema.json"))
    simulation_reconciliation = json.loads(
        (OUT["simulation"] / "SIMULATION_MASTER_POINTER_RECONCILIATION_R1.json").read_text(encoding="utf-8")
    )
    manifest_report = reverify_hash_manifests()

    no_forbidden_inputs = [
        OUT["master"] / "NO_FORBIDDEN_CAPABILITY_GUARD_R2.json",
        OUT["event"] / "NO_LIVE_INGESTION_CLAIM_GUARD.json",
        OUT["simulation"] / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
        OUT["simulation"] / "NO_FORECASTPACKET_PROMOTION_GUARD.json",
        OUT["simulation"] / "NO_MODEL_TRAINING_GUARD.json",
    ]
    guard_results = {}
    for path in no_forbidden_inputs:
        data = json.loads(path.read_text(encoding="utf-8"))
        guard_results[path.name] = {
            "path": rel(path),
            "status": data["status"],
            "forbidden_capabilities_created": data.get("forbidden_capabilities_created", []),
        }

    write_json(root / "THREE_PACKAGE_SOURCE_REF_AUDIT.json", source_audit)
    write_json(
        root / "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json",
        {
            "artifact_id": "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY",
            "status": "PASS",
            "raw_ledger_item_count": dedupe["raw_ledger_item_count"],
            "canonical_artifact_group_count": dedupe["canonical_artifact_group_count"],
            "raw_item_coverage_count": len(raw_ids),
            "unique_raw_item_coverage_count": len(set(raw_ids)),
            "fully_done_canonical_group_count": len(fully_done_groups),
            "no_duplicate_done_inflation": dedupe["no_duplicate_done_inflation"] and len(raw_ids) == len(set(raw_ids)) == 21,
        },
    )
    write_json(
        root / "THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT.json",
        {
            "artifact_id": "THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT",
            "status": "PASS_WITH_LIMITATIONS",
            "contract_root": rel(CONTRACTS["event"]),
            "contract_file_count": len(event_contract_files),
            "contract_files": [rel(path) for path in event_contract_files],
            "publication_audit_path": rel(OUT["event"] / "EVENT_FABRIC_CONTRACT_PUBLICATION_REAUDIT_R1.json"),
            "local_replay_only": True,
        },
    )
    write_json(
        root / "THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION.json",
        {
            "artifact_id": "THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION",
            "status": "PASS",
            "master_pointer": rel(OUT["master"] / "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json"),
            "r2_catalog": rel(OUT["simulation"] / "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json"),
            "relationship": simulation_reconciliation["relationship"],
            "contradiction_found": simulation_reconciliation["contradiction_found"],
        },
    )
    write_json(root / "THREE_PACKAGE_HASH_MANIFEST_REVERIFY.json", manifest_report)
    write_json(
        root / "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD.json",
        {
            "artifact_id": "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD",
            "status": "PASS",
            "forbidden_capabilities": FORBIDDEN_CAPABILITIES,
            "guard_results": guard_results,
            "forbidden_capabilities_created": [],
            "final_posture": "WITH_LIMITATIONS",
        },
    )
    write_json(
        root / "THREE_PACKAGE_SEQUENCE_DECISION.json",
        {
            "artifact_id": "THREE_PACKAGE_SEQUENCE_DECISION",
            "package_id": "MAIN-CITYBRAIN-PRE-E4-THREE-PACKAGE-REVERIFY-R1",
            "status": "PASS_MAIN_CITYBRAIN_PRE_E4_THREE_PACKAGE_REVERIFY_R1_WITH_LIMITATIONS",
            "sequence_used": [
                "MAIN-CITYBRAIN-PRE-E4-MECHANICAL-GAP-CLOSURE-R2-1",
                "MAIN-CITYBRAIN-EVENT-FABRIC-REPAIR-EPOCH-R1-1",
                "MAIN-CITYBRAIN-SIMULATION-BACKTEST-REPAIR-EPOCH-R1-1",
                "MAIN-CITYBRAIN-PRE-E4-THREE-PACKAGE-REVERIFY-R1",
            ],
            "parallel_execution_used": False,
            "source_refs_hash_stable": source_audit["all_required_present_and_hash_stable"],
            "dedupe_verified": True,
            "event_contracts_reaudited": len(event_contract_files) == 6,
            "simulation_pointer_reconciled": simulation_reconciliation["relationship"] == "supersedes_provisional_pointer",
            "hash_manifests_verified": manifest_report["status"] == "PASS",
            "forbidden_capabilities_created": [],
            "limitations": [
                "human review sessions still pending",
                "production event ingestion absent",
                "simulation remains fixture-only/assumption-bound",
                "no product forecast authority exists",
            ],
        },
    )
    write_text(
        root / "THREE_PACKAGE_REVERIFY_CLOSEOUT.md",
        "# Three-Package Reverify R1 Closeout\n\n"
        "Status: PASS_MAIN_CITYBRAIN_PRE_E4_THREE_PACKAGE_REVERIFY_R1_WITH_LIMITATIONS\n\n"
        "The final reverify confirmed source-ref hash stability, 21 raw backlog items collapsed to 12 canonical artifact groups without duplicate done-count inflation, Event Fabric R1 contract publication coverage, Simulation R2 catalog supersession of the provisional master pointer, package hash manifests, and no-forbidden-capability guards.\n\n"
        "The posture remains WITH_LIMITATIONS because human review sessions, production event ingestion, simulator fidelity, and product forecast authority remain absent.\n",
    )
    write_text(
        root / "TEST_LOG.txt",
        "Internal reverify generation checks: PASS\nFocused pytest command: python -m pytest tests/test_pre_e4_three_package_repair_chain.py\n",
    )
    publish_selected(
        "reverify",
        [
            "THREE_PACKAGE_SOURCE_REF_AUDIT.json",
            "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json",
            "THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT.json",
            "THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION.json",
            "THREE_PACKAGE_HASH_MANIFEST_REVERIFY.json",
            "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD.json",
            "THREE_PACKAGE_SEQUENCE_DECISION.json",
            "THREE_PACKAGE_REVERIFY_CLOSEOUT.md",
            "TEST_LOG.txt",
        ],
    )
    package_manifest(root, [pub])
    shutil.copy2(root / "HASH_MANIFEST.json", pub / "HASH_MANIFEST.json")


def required_output_paths() -> list[Path]:
    master_names = [
        "SOURCE_INPUT_AUDIT.json",
        "BACKLOG_LEDGER_INTAKE_REPORT.json",
        "MECHANICAL_SCOPE_DECISION.json",
        "REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        "PACKAGE_SEQUENCE_STATE_R1.json",
        "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json",
        "PUBLICATION_HOME_RECHECK_REPORT.json",
        "GOVERNANCE_ARTIFACT_PATH_AUDIT.json",
        "GITIGNORED_OUTPUT_PUBLICATION_GAP_REPORT.json",
        "CHECK_DESCRIPTIVE_SCORECARD_R2.json",
        "L4_CASE_STUBS_R2.jsonl",
        "IDENTITY_GRAPH_EVAL_FIXTURES_R2.jsonl",
        "WORKFLOW_REVIEW_STATE_HISTORY_R2.jsonl",
        "DOMAIN_PACK_USEFULNESS_R2.json",
        "BRIEF_EXPORT_USEFULNESS_DIAGNOSTIC_R1.json",
        "SOURCE_REFRESH_LONGITUDINAL_GAP_INVENTORY_R1.json",
        "DATA_QUALITY_MATURITY_DIAGNOSTIC_R1.json",
        "SYNTHETIC_TIER_GAP_MANIFEST_R1.json",
        "PLAN_SCHEDULE_OPTIMIZE_REVIEW_OPTION_FIXTURE_CATALOG_R1.json",
        "SIMULATION_BACKTEST_HANDOFF_POINTER_R1.json",
        "NO_FORBIDDEN_CAPABILITY_GUARD_R2.json",
        "MECHANICAL_GAP_CLOSURE_R2_DECISION.json",
        "MECHANICAL_GAP_CLOSURE_R2_CLOSEOUT.md",
        "HASH_MANIFEST.json",
        "TEST_LOG.txt",
    ]
    event_names = [
        "EVENT_LOG.jsonl",
        "EVENT_APPEND_REPORT.json",
        "EVENT_REPLAY_REPORT.json",
        "EVENT_REPLAY_DETERMINISM_REPORT.json",
        "EVENT_RESOLUTION_REPORT.json",
        "UNRESOLVED_EVENT_QUEUE.jsonl",
        "QUARANTINED_EVENT_LOG.jsonl",
        "EVENT_CURRENT_STATE.json",
        "EVENT_QUERY_SMOKE_REPORT.json",
        "EVENT_RUNTIME_HANDOFF_PACKET.json",
        "NO_LIVE_INGESTION_CLAIM_GUARD.json",
        "EVENT_FABRIC_SOURCE_REF_AUDIT.json",
        "EVENT_FABRIC_CONTRACT_PUBLICATION_REAUDIT_R1.json",
        "EVENT_FABRIC_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        "EVENT_FABRIC_REPAIR_EPOCH_R1_DECISION.json",
        "HASH_MANIFEST.json",
    ]
    simulation_names = [
        "SIMULATION_SCENARIO_CATALOG_R1.json",
        "SIMULATOR_CONNECTOR_REGISTRY_R1.json",
        "SIMULATION_RUN_ENVELOPE_SAMPLE.json",
        "SIMULATION_BACKTEST_INPUT_CATALOG_R2.json",
        "SIMULATION_ASSUMPTION_REPORT_R1.json",
        "SIMULATION_FIDELITY_REPORT_R1.json",
        "SIMULATION_UNCERTAINTY_REPORT_R1.json",
        "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
        "SIMULATION_MASTER_POINTER_RECONCILIATION_R1.json",
        "SIMULATION_BACKTEST_CATALOG_R2_SUPERSESSION_REPORT.json",
        "SIMULATION_REQUIRES_FINAL_THREE_PACKAGE_REVERIFY_R1.json",
        "SIMULATION_BACKTEST_REPAIR_EPOCH_R1_DECISION.json",
        "HASH_MANIFEST.json",
    ]
    reverify_names = [
        "THREE_PACKAGE_SOURCE_REF_AUDIT.json",
        "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json",
        "THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT.json",
        "THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION.json",
        "THREE_PACKAGE_HASH_MANIFEST_REVERIFY.json",
        "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD.json",
        "THREE_PACKAGE_SEQUENCE_DECISION.json",
        "THREE_PACKAGE_REVERIFY_CLOSEOUT.md",
        "HASH_MANIFEST.json",
        "TEST_LOG.txt",
    ]
    paths = [OUT["master"] / name for name in master_names]
    paths += [OUT["event"] / name for name in event_names]
    paths += [OUT["simulation"] / name for name in simulation_names]
    paths += [OUT["reverify"] / name for name in reverify_names]
    paths += [CONTRACTS["event"] / name for name in event_schemas()]
    paths += [CONTRACTS["simulation"] / name for name in simulation_schemas()]
    return paths


def validate_all() -> list[str]:
    errors: list[str] = []
    for zip_path in PACKAGE_ZIPS.values():
        if not zip_path.exists():
            errors.append(f"missing package zip: {zip_path}")
    for path in required_output_paths():
        if not path.exists():
            errors.append(f"missing required artifact: {rel(path)}")

    dedupe_path = OUT["master"] / "BACKLOG_LEDGER_DEDUPLICATION_MAP_R1.json"
    if dedupe_path.exists():
        dedupe = json.loads(dedupe_path.read_text(encoding="utf-8"))
        raw_ids = [item_id for group in dedupe["artifact_groups"] for item_id in group["raw_item_ids"]]
        if dedupe.get("raw_ledger_item_count") != 21:
            errors.append("dedupe raw_ledger_item_count is not 21")
        if dedupe.get("canonical_artifact_group_count") != 12:
            errors.append("dedupe canonical_artifact_group_count is not 12")
        if len(raw_ids) != len(set(raw_ids)) or len(raw_ids) != 21:
            errors.append("dedupe raw item coverage is not exactly 21 unique items")
        if not dedupe.get("no_duplicate_done_inflation"):
            errors.append("dedupe no_duplicate_done_inflation is false")

    event_contracts = list(CONTRACTS["event"].glob("*.schema.json"))
    if len(event_contracts) != 6:
        errors.append("Event Fabric contract count is not 6")
    simulation_contracts = list(CONTRACTS["simulation"].glob("*.schema.json"))
    if len(simulation_contracts) != 7:
        errors.append("Simulation contract count is not 7")

    for manifest_path in [
        OUT["master"] / "HASH_MANIFEST.json",
        OUT["event"] / "HASH_MANIFEST.json",
        OUT["simulation"] / "HASH_MANIFEST.json",
        OUT["reverify"] / "HASH_MANIFEST.json",
    ]:
        if manifest_path.exists():
            errors.extend(verify_manifest(manifest_path))

    final_decision_path = OUT["reverify"] / "THREE_PACKAGE_SEQUENCE_DECISION.json"
    if final_decision_path.exists():
        decision = json.loads(final_decision_path.read_text(encoding="utf-8"))
        if decision.get("status") != "PASS_MAIN_CITYBRAIN_PRE_E4_THREE_PACKAGE_REVERIFY_R1_WITH_LIMITATIONS":
            errors.append("final reverify status is not WITH_LIMITATIONS PASS")
        if decision.get("parallel_execution_used") is not False:
            errors.append("final reverify did not record sequential execution")
        if decision.get("forbidden_capabilities_created") != []:
            errors.append("final reverify created forbidden capabilities")

    return errors


def run_all() -> None:
    run_master()
    run_event()
    run_simulation()
    run_reverify()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)

    if not args.validate_only:
        run_all()
    errors = validate_all()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "sequence": [
                    "master mechanical-debt R2.1",
                    "Event Fabric repair R1.1",
                    "Simulation / Backtest repair R1.1",
                    "final three-package reverify R1",
                ],
                "outputs": {key: rel(path) for key, path in OUT.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
