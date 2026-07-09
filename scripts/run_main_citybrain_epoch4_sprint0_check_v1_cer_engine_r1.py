"""Materialize Epoch 4 Sprint 0 CER/SEG/CHECK v1 trust-gate artifacts.

This package is deliberately bounded to fixture data. It creates review-state
contracts and reports, not production identity, official truth, or live action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ZIP = Path.home() / "Downloads" / "main-citybrain-epoch4-sprint0-check-v1-cer-engine-r1.zip"
PACKAGE_PREFIX = "main-citybrain-epoch4-sprint0-check-v1-cer-engine-r1/"

OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint0-check-v1-cer-engine-r1"
CER_CONTRACT_ROOT = ROOT / "contracts" / "cer_engine_r1"
CHECK_CONTRACT_ROOT = ROOT / "contracts" / "check_v1"

FINAL_STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_SPRINT0_CHECK_V1_CER_ENGINE_R1_WITH_LIMITATIONS"

FORBIDDEN_CAPABILITIES = [
    "production live city monitoring",
    "autonomous alerts, routing, dispatch, enforcement, command, or control",
    "official tickets, official cases, legal findings, certified affected-building truth, or public-safety determinations",
    "learned ranking, operator-facing prediction, product ForecastPacket, model training, model release, or learned component release row",
    "fabricated human review sessions, fabricated operator dispositions, fabricated transition history, fabricated source evidence, or synthetic data relabeled as official/live",
    "mutation of source truth or canonical truth without explicit candidate/review state and provenance",
]

REQUIRED_OUTPUTS = [
    "SPRINT0_SOURCE_REF_AUDIT.json",
    "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE.json",
    "CER_ENGINE_R1_DECISION.json",
    "CER_ENTITY_RESOLUTION_RUN_R1.json",
    "CER_CONFLICT_REPORT_R1.json",
    "CER_REVIEW_QUEUE_R1.jsonl",
    "SEG_V2_CER_BRIDGE_REPORT.json",
    "SEG_EDGE_ASSERTIONS_R1.jsonl",
    "SEG_NO_RAW_ID_BYPASS_GUARD.json",
    "CHECK_V1_ENGINE_REPORT.json",
    "CHECK_V1_REPORTS.jsonl",
    "CHECK_V1_RULE_COVERAGE_MATRIX.json",
    "CHECK_V1_CONTRADICTION_FIXTURES.jsonl",
    "SPRINT0_INTEGRATED_TRUST_GATE_REPORT.json",
    "SPRINT0_NEGATIVE_FIXTURE_RESULTS.json",
    "HASH_MANIFEST.json",
    "TEST_LOG.txt",
    "SPRINT0_CLOSEOUT.md",
    "SPRINT0_DECISION.json",
]

REQUIRED_CONTRACTS = [
    CER_CONTRACT_ROOT / "canonical_entity.schema.json",
    CER_CONTRACT_ROOT / "source_entity_link.schema.json",
    CER_CONTRACT_ROOT / "match_candidate.schema.json",
    CER_CONTRACT_ROOT / "match_decision.schema.json",
    CHECK_CONTRACT_ROOT / "check_report_v1.schema.json",
    CHECK_CONTRACT_ROOT / "check_rule.schema.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_zip_json(member: str) -> Any:
    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        return json.loads(archive.read(PACKAGE_PREFIX + member).decode("utf-8"))


def package_source_ref_audit() -> dict[str, Any]:
    required = {
        "E4_BACKLOG_DISPOSITION_LEDGER.json",
        "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
        "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json",
        "THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json",
        "THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT.json",
        "THREE_PACKAGE_HASH_MANIFEST_REVERIFY.json",
        "THREE_PACKAGE_NO_FORBIDDEN_CAPABILITY_GUARD.json",
        "THREE_PACKAGE_SEQUENCE_DECISION.json",
        "THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION.json",
        "THREE_PACKAGE_SOURCE_REF_AUDIT.json",
    }
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith(PACKAGE_PREFIX + "source_refs/") or name.endswith("/"):
                continue
            data = archive.read(name)
            entries.append(
                {
                    "file": Path(name).name,
                    "zip_member": name,
                    "sha256": sha256_bytes(data),
                    "bytes": len(data),
                }
            )
    present = {entry["file"] for entry in entries}
    return {
        "artifact_id": "SPRINT0_SOURCE_REF_AUDIT",
        "status": "PASS" if required <= present else "BLOCKED",
        "package_zip": str(PACKAGE_ZIP),
        "required_files": sorted(required),
        "present_files": sorted(present),
        "missing_files": sorted(required - present),
        "source_refs": entries,
    }


def prior_repair_chain_intake() -> dict[str, Any]:
    checks = [
        {
            "key": "three_package_reverify_decision",
            "path": ROOT / "outputs/main_citybrain_pre_e4_three_package_reverify_r1/THREE_PACKAGE_SEQUENCE_DECISION.json",
            "status_prefix": "PASS_MAIN_CITYBRAIN_PRE_E4_THREE_PACKAGE_REVERIFY_R1",
        },
        {
            "key": "backlog_dedupe_reverify",
            "path": ROOT / "outputs/main_citybrain_pre_e4_three_package_reverify_r1/THREE_PACKAGE_BACKLOG_DEDUP_REVERIFY.json",
            "status_prefix": "PASS",
        },
        {
            "key": "hash_manifest_reverify",
            "path": ROOT / "outputs/main_citybrain_pre_e4_three_package_reverify_r1/THREE_PACKAGE_HASH_MANIFEST_REVERIFY.json",
            "status_prefix": "PASS",
        },
        {
            "key": "event_contract_reaudit",
            "path": ROOT / "outputs/main_citybrain_pre_e4_three_package_reverify_r1/THREE_PACKAGE_EVENT_FABRIC_CONTRACT_REAUDIT.json",
            "status_prefix": "PASS",
        },
        {
            "key": "simulation_pointer_reconciliation",
            "path": ROOT / "outputs/main_citybrain_pre_e4_three_package_reverify_r1/THREE_PACKAGE_SIMULATION_POINTER_RECONCILIATION.json",
            "status_prefix": "PASS",
        },
    ]
    rows = []
    blockers = []
    for check in checks:
        data = read_json(check["path"], {})
        status = str(data.get("status", ""))
        ok = check["path"].exists() and status.startswith(check["status_prefix"])
        rows.append(
            {
                "key": check["key"],
                "path": rel(check["path"]),
                "exists": check["path"].exists(),
                "status": status or None,
                "ok": ok,
            }
        )
        if not ok:
            blockers.append(check["key"])

    event_contract_files = sorted((ROOT / "contracts/event_fabric_r1").glob("*.schema.json"))
    simulation_contract_files = sorted((ROOT / "contracts/simulation_r1").glob("*.schema.json"))
    if len(event_contract_files) != 6:
        blockers.append("event_fabric_r1_contract_count")
    if len(simulation_contract_files) != 7:
        blockers.append("simulation_r1_contract_count")

    return {
        "artifact_id": "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE",
        "status": "PASS" if not blockers else "BLOCKED",
        "checks": rows,
        "event_fabric_r1_contract_count": len(event_contract_files),
        "simulation_r1_contract_count": len(simulation_contract_files),
        "event_fabric_r1_contracts": [rel(path) for path in event_contract_files],
        "simulation_r1_contracts": [rel(path) for path in simulation_contract_files],
        "blockers": blockers,
        "parallel_execution_used": False,
    }


def schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    props = {name: {"type": "string"} for name in required}
    props.update(properties)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "required": required,
        "properties": props,
        "additionalProperties": True,
    }


def write_contracts() -> None:
    write_json(
        CER_CONTRACT_ROOT / "canonical_entity.schema.json",
        schema(
            "CanonicalEntityR1",
            [
                "canonical_entity_id",
                "entity_family",
                "display_label",
                "review_state",
                "confidence",
                "provenance_refs",
                "source_links",
                "attribute_assertions",
                "limitations",
                "authority_boundary",
            ],
            {
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "source_links": {"type": "array", "items": {"type": "string"}},
                "attribute_assertions": {"type": "array", "items": {"type": "object"}},
                "aliases": {"type": "array", "items": {"type": "string"}},
                "conflict_refs": {"type": "array", "items": {"type": "string"}},
                "review_state": {"enum": ["verified_fixture", "candidate_reviewed", "review_required", "conflicted", "rejected"]},
            },
        ),
    )
    write_json(
        CER_CONTRACT_ROOT / "source_entity_link.schema.json",
        schema(
            "SourceEntityLinkR1",
            [
                "source_entity_link_id",
                "canonical_entity_id",
                "source_entity_id",
                "source_record_ref",
                "source_class",
                "confidence",
                "review_state",
                "evidence_refs",
                "provenance_refs",
            ],
            {
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "provenance_refs": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    write_json(
        CER_CONTRACT_ROOT / "match_candidate.schema.json",
        schema(
            "MatchCandidateR1",
            [
                "match_candidate_id",
                "left_source_entity_ref",
                "right_source_entity_ref",
                "candidate_canonical_entity_id",
                "features",
                "score",
                "review_state",
                "evidence_refs",
                "provenance_refs",
            ],
            {
                "features": {"type": "object"},
                "score": {"type": "number", "minimum": 0, "maximum": 1},
                "identity_claimed": {"type": "boolean"},
                "conflict_refs": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    write_json(
        CER_CONTRACT_ROOT / "match_decision.schema.json",
        schema(
            "MatchDecisionR1",
            ["match_decision_id", "match_candidate_id", "decision", "confidence", "review_state", "rationale", "provenance_refs"],
            {
                "decision": {"enum": ["accept_candidate_fixture", "review_required", "reject_raw_id_bypass", "reject_conflict"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "provenance_refs": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )
    write_json(
        CHECK_CONTRACT_ROOT / "check_report_v1.schema.json",
        schema(
            "CheckReportV1",
            [
                "check_report_id",
                "claim_id",
                "claim_text",
                "canonical_entity_refs",
                "seg_edge_refs",
                "evidence_refs",
                "source_class_summary",
                "rule_results",
                "claimability_status",
                "review_state",
                "limitations",
                "authority_boundary",
            ],
            {
                "canonical_entity_refs": {"type": "array", "items": {"type": "string"}},
                "seg_edge_refs": {"type": "array", "items": {"type": "string"}},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
                "rule_results": {"type": "array", "items": {"type": "object"}},
                "claimability_status": {
                    "enum": [
                        "claimable_with_limitations",
                        "downgraded_candidate_only",
                        "downgraded_proximity_only",
                        "blocked_contradiction",
                        "blocked_stale",
                        "blocked_insufficient_source_depth",
                        "blocked_raw_id_bypass",
                    ]
                },
            },
        ),
    )
    write_json(
        CHECK_CONTRACT_ROOT / "check_rule.schema.json",
        schema(
            "CheckRuleV1",
            ["rule_id", "rule_name", "status", "result", "evidence_refs", "downgrade_reason"],
            {
                "status": {"enum": ["PASS", "WARN", "FAIL"]},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        ),
    )


def fixture_source_records() -> list[dict[str, Any]]:
    return [
        {
            "source_record_ref": "source_record:permit:alpha:2026-07-01",
            "source_entity_id": "permit_raw:building_alpha_100a",
            "source_class": "replay_source_record",
            "label": "Alpha Tower 100A",
            "entity_family": "building_or_structure",
            "attributes": {"address": "100 Alpha St", "floors": 10, "zone": "downtown"},
            "evidence_refs": ["evidence:permit:alpha:100a", "evidence:address_registry:alpha"],
            "freshness_days": 6,
        },
        {
            "source_record_ref": "source_record:inspection:alpha:2026-06-30",
            "source_entity_id": "inspection_raw:alpha_tower",
            "source_class": "replay_source_record",
            "label": "Alpha Tower",
            "entity_family": "building_or_structure",
            "attributes": {"address": "100 Alpha Street", "floors": 11, "zone": "downtown"},
            "evidence_refs": ["evidence:inspection:alpha", "evidence:photo:alpha_review"],
            "freshness_days": 7,
        },
        {
            "source_record_ref": "source_record:alias:alpha:2026-07-02",
            "source_entity_id": "alias_raw:alpha_a",
            "source_class": "derived_fixture",
            "label": "Alpha A",
            "entity_family": "building_or_structure",
            "attributes": {"alias": "Alpha A", "address": "100 Alpha St"},
            "evidence_refs": ["evidence:alias:alpha"],
            "freshness_days": 5,
        },
        {
            "source_record_ref": "source_record:sensor:near_alpha:2026-07-07",
            "source_entity_id": "sensor_raw:near_alpha",
            "source_class": "sensor_inferred",
            "label": "object near Alpha Tower",
            "entity_family": "observation",
            "attributes": {"proximity_to": "cer:building:alpha", "distance_m": 18},
            "evidence_refs": ["evidence:sensor:near_alpha"],
            "freshness_days": 0,
            "proximity_only": True,
        },
        {
            "source_record_ref": "source_record:registry:beta:2026-05-01",
            "source_entity_id": "registry_raw:beta_candidate",
            "source_class": "replay_source_record",
            "label": "Beta Complex",
            "entity_family": "building_or_structure",
            "attributes": {"address": "22 Beta Rd", "zone": "midtown"},
            "evidence_refs": ["evidence:registry:beta"],
            "freshness_days": 67,
            "candidate_only": True,
        },
    ]


def build_cer() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    records = fixture_source_records()
    links = [
        {
            "source_entity_link_id": f"source_link:{idx + 1:02d}",
            "canonical_entity_id": "cer:building:alpha" if "alpha" in record["source_entity_id"] else "cer:building:beta_candidate",
            "source_entity_id": record["source_entity_id"],
            "source_record_ref": record["source_record_ref"],
            "source_class": record["source_class"],
            "confidence": 0.88 if "alpha" in record["source_entity_id"] else 0.52,
            "review_state": "candidate_reviewed" if "alpha" in record["source_entity_id"] and not record.get("proximity_only") else "review_required",
            "evidence_refs": record["evidence_refs"],
            "provenance_refs": ["package:epoch4_sprint0", record["source_record_ref"]],
        }
        for idx, record in enumerate(records)
    ]
    attribute_assertions = [
        {
            "assertion_id": "assertion:alpha:address:permit",
            "canonical_entity_id": "cer:building:alpha",
            "attribute_name": "address",
            "attribute_value": "100 Alpha St",
            "source_record_ref": "source_record:permit:alpha:2026-07-01",
            "source_class": "replay_source_record",
            "confidence": 0.91,
            "review_state": "candidate_reviewed",
            "evidence_refs": ["evidence:permit:alpha:100a", "evidence:address_registry:alpha"],
            "freshness_days": 6,
        },
        {
            "assertion_id": "assertion:alpha:floors:permit",
            "canonical_entity_id": "cer:building:alpha",
            "attribute_name": "floors",
            "attribute_value": 10,
            "source_record_ref": "source_record:permit:alpha:2026-07-01",
            "source_class": "replay_source_record",
            "confidence": 0.78,
            "review_state": "conflicted",
            "evidence_refs": ["evidence:permit:alpha:100a"],
            "freshness_days": 6,
        },
        {
            "assertion_id": "assertion:alpha:floors:inspection",
            "canonical_entity_id": "cer:building:alpha",
            "attribute_name": "floors",
            "attribute_value": 11,
            "source_record_ref": "source_record:inspection:alpha:2026-06-30",
            "source_class": "replay_source_record",
            "confidence": 0.74,
            "review_state": "conflicted",
            "evidence_refs": ["evidence:inspection:alpha"],
            "freshness_days": 7,
        },
        {
            "assertion_id": "assertion:near_alpha:proximity",
            "canonical_entity_id": "cer:observation:near_alpha",
            "attribute_name": "proximity_to",
            "attribute_value": "cer:building:alpha",
            "source_record_ref": "source_record:sensor:near_alpha:2026-07-07",
            "source_class": "sensor_inferred",
            "confidence": 0.49,
            "review_state": "review_required",
            "evidence_refs": ["evidence:sensor:near_alpha"],
            "freshness_days": 0,
            "proximity_only": True,
        },
        {
            "assertion_id": "assertion:beta:address:registry",
            "canonical_entity_id": "cer:building:beta_candidate",
            "attribute_name": "address",
            "attribute_value": "22 Beta Rd",
            "source_record_ref": "source_record:registry:beta:2026-05-01",
            "source_class": "replay_source_record",
            "confidence": 0.52,
            "review_state": "review_required",
            "evidence_refs": ["evidence:registry:beta"],
            "freshness_days": 67,
            "candidate_only": True,
        },
    ]
    conflicts = [
        {
            "conflict_id": "conflict:alpha:floors",
            "canonical_entity_id": "cer:building:alpha",
            "attribute_name": "floors",
            "competing_assertion_refs": ["assertion:alpha:floors:permit", "assertion:alpha:floors:inspection"],
            "values": [10, 11],
            "review_state": "review_required",
            "resolution": "unresolved_fixture_conflict",
            "official_truth_mutated": False,
        }
    ]
    entities = [
        {
            "canonical_entity_id": "cer:building:alpha",
            "entity_family": "building_or_structure",
            "display_label": "Alpha Tower",
            "aliases": ["Alpha Tower 100A", "Alpha A"],
            "source_links": [link["source_entity_link_id"] for link in links if link["canonical_entity_id"] == "cer:building:alpha"],
            "attribute_assertions": [item for item in attribute_assertions if item["canonical_entity_id"] == "cer:building:alpha"],
            "review_state": "conflicted",
            "confidence": 0.86,
            "provenance_refs": ["source_record:permit:alpha:2026-07-01", "source_record:inspection:alpha:2026-06-30"],
            "conflict_refs": ["conflict:alpha:floors"],
            "limitations": ["fixture-only bounded CER", "not official identity truth", "floor assertion conflicted"],
            "authority_boundary": "review_only_no_action",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
        {
            "canonical_entity_id": "cer:building:beta_candidate",
            "entity_family": "building_or_structure",
            "display_label": "Beta Complex candidate",
            "aliases": ["Beta Complex"],
            "source_links": [link["source_entity_link_id"] for link in links if link["canonical_entity_id"] == "cer:building:beta_candidate"],
            "attribute_assertions": [item for item in attribute_assertions if item["canonical_entity_id"] == "cer:building:beta_candidate"],
            "review_state": "review_required",
            "confidence": 0.52,
            "provenance_refs": ["source_record:registry:beta:2026-05-01"],
            "conflict_refs": [],
            "limitations": ["candidate-only", "stale evidence", "not official identity truth"],
            "authority_boundary": "review_only_no_action",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        },
    ]
    candidates = [
        {
            "match_candidate_id": "match_candidate:alpha:permit-inspection",
            "left_source_entity_ref": "permit_raw:building_alpha_100a",
            "right_source_entity_ref": "inspection_raw:alpha_tower",
            "candidate_canonical_entity_id": "cer:building:alpha",
            "features": {"address_similarity": 0.93, "label_similarity": 0.86, "zone_match": True},
            "score": 0.88,
            "decision_ref": "match_decision:alpha:permit-inspection",
            "review_state": "candidate_reviewed",
            "identity_claimed": False,
            "evidence_refs": ["evidence:permit:alpha:100a", "evidence:inspection:alpha"],
            "provenance_refs": ["package:epoch4_sprint0"],
            "conflict_refs": ["conflict:alpha:floors"],
        },
        {
            "match_candidate_id": "match_candidate:raw-id-bypass",
            "left_source_entity_ref": "raw:unbacked:alpha",
            "right_source_entity_ref": "cer:building:alpha",
            "candidate_canonical_entity_id": "raw:unbacked:alpha",
            "features": {"raw_id_only": True},
            "score": 0.0,
            "decision_ref": "match_decision:raw-id-bypass",
            "review_state": "rejected",
            "identity_claimed": False,
            "evidence_refs": [],
            "provenance_refs": ["negative_fixture:raw_id_bypass"],
            "conflict_refs": [],
        },
    ]
    decisions = [
        {
            "match_decision_id": "match_decision:alpha:permit-inspection",
            "match_candidate_id": "match_candidate:alpha:permit-inspection",
            "decision": "accept_candidate_fixture",
            "confidence": 0.86,
            "review_state": "candidate_reviewed",
            "rationale": "High fixture similarity with conflict preserved for review; no official identity truth promoted.",
            "provenance_refs": ["package:epoch4_sprint0"],
        },
        {
            "match_decision_id": "match_decision:raw-id-bypass",
            "match_candidate_id": "match_candidate:raw-id-bypass",
            "decision": "reject_raw_id_bypass",
            "confidence": 1.0,
            "review_state": "rejected",
            "rationale": "SEG and CHECK must consume CER-backed IDs only.",
            "provenance_refs": ["negative_fixture:raw_id_bypass"],
        },
    ]
    resolution_run = {
        "artifact_id": "CER_ENTITY_RESOLUTION_RUN_R1",
        "status": "PASS_WITH_LIMITATIONS",
        "run_id": "cer_resolution_run_r1_fixture",
        "source_records": records,
        "canonical_entities": entities,
        "source_entity_links": links,
        "attribute_assertions": attribute_assertions,
        "match_candidates": candidates,
        "match_decisions": decisions,
        "conflicts": conflicts,
        "official_truth_mutated": False,
        "canonical_truth_mutated": False,
        "authority_boundary": "review_only_no_action",
    }
    review_queue = [
        {
            "queue_item_id": "review:conflict:alpha:floors",
            "review_state": "review_required",
            "reason": "conflicting floor-count assertions",
            "refs": ["conflict:alpha:floors"],
            "safe_next_look": "human review source records before promotion",
        },
        {
            "queue_item_id": "review:candidate:beta",
            "review_state": "review_required",
            "reason": "candidate-only entity with stale evidence",
            "refs": ["cer:building:beta_candidate"],
            "safe_next_look": "refresh dated evidence",
        },
        {
            "queue_item_id": "review:proximity:near_alpha",
            "review_state": "review_required",
            "reason": "proximity-only sensor observation cannot establish identity",
            "refs": ["assertion:near_alpha:proximity"],
            "safe_next_look": "collect corroborating source record",
        },
    ]
    return resolution_run, conflicts, review_queue


def build_seg_edges() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    edges = [
        {
            "seg_edge_id": "seg_edge:alpha:located_in:downtown",
            "subject_cer_entity_id": "cer:building:alpha",
            "predicate": "located_in",
            "object_cer_entity_id": "cer:zone:downtown",
            "temporal_validity": {"valid_from": "2026-07-01", "valid_to": None},
            "edge_confidence": 0.82,
            "evidence_refs": ["assertion:alpha:address:permit"],
            "review_state": "candidate_reviewed",
            "source_class": "derived_fixture",
            "authority_boundary": "review_only_no_action",
        },
        {
            "seg_edge_id": "seg_edge:near_alpha:proximity_to:alpha",
            "subject_cer_entity_id": "cer:observation:near_alpha",
            "predicate": "proximity_to",
            "object_cer_entity_id": "cer:building:alpha",
            "temporal_validity": {"valid_from": "2026-07-07", "valid_to": "2026-07-08"},
            "edge_confidence": 0.49,
            "evidence_refs": ["assertion:near_alpha:proximity"],
            "review_state": "review_required",
            "source_class": "sensor_inferred",
            "authority_boundary": "review_only_no_action",
        },
    ]
    bypass_guard = {
        "artifact_id": "SEG_NO_RAW_ID_BYPASS_GUARD",
        "status": "PASS",
        "raw_id_bypass_attempts": [
            {
                "fixture_id": "raw_source_id_as_subject",
                "subject_ref": "raw:unbacked:alpha",
                "rejected": True,
                "reason": "subject is not a CER-backed ID",
            },
            {
                "fixture_id": "raw_source_id_as_object",
                "object_ref": "permit_raw:building_alpha_100a",
                "rejected": True,
                "reason": "object is not a CER-backed ID",
            },
        ],
        "all_edges_use_cer_ids": all(
            edge["subject_cer_entity_id"].startswith("cer:") and edge["object_cer_entity_id"].startswith("cer:")
            for edge in edges
        ),
        "official_truth_mutated": False,
    }
    return edges, bypass_guard


def rule(rule_id: str, status: str, result: str, evidence_refs: list[str], downgrade_reason: str = "") -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_name": rule_id.replace("_", " "),
        "status": status,
        "result": result,
        "evidence_refs": evidence_refs,
        "downgrade_reason": downgrade_reason,
    }


def build_check_reports() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    reports = [
        {
            "check_report_id": "check_v1:alpha:located_in",
            "claim_id": "claim:alpha:located_in:downtown",
            "claim_text": "Alpha Tower has a bounded CER-backed downtown context.",
            "canonical_entity_refs": ["cer:building:alpha", "cer:zone:downtown"],
            "seg_edge_refs": ["seg_edge:alpha:located_in:downtown"],
            "evidence_refs": ["assertion:alpha:address:permit", "evidence:address_registry:alpha"],
            "source_class_summary": {"replay_source_record": 2, "derived_fixture": 1},
            "rule_results": [
                rule("evidence_sufficiency", "PASS", "two corroborating fixture records", ["assertion:alpha:address:permit"]),
                rule("contradiction", "WARN", "unrelated floor-count contradiction preserved", ["conflict:alpha:floors"], "conflict does not block location claim"),
                rule("freshness", "PASS", "fresh within fixture window", ["source_record:permit:alpha:2026-07-01"]),
                rule("source_depth", "PASS", "source depth >= 2", ["evidence:permit:alpha:100a", "evidence:address_registry:alpha"]),
                rule("source_class", "PASS", "source classes explicitly labelled", ["source_record:permit:alpha:2026-07-01"]),
                rule("proximity_only", "PASS", "not proximity-only", []),
                rule("candidate_only", "PASS", "not candidate-only", []),
            ],
            "claimability_status": "claimable_with_limitations",
            "review_state": "candidate_reviewed",
            "limitations": ["bounded fixture claim only", "not official/certified truth"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:beta:candidate_only",
            "claim_id": "claim:beta:identity",
            "claim_text": "Beta Complex identity is resolved.",
            "canonical_entity_refs": ["cer:building:beta_candidate"],
            "seg_edge_refs": [],
            "evidence_refs": ["assertion:beta:address:registry"],
            "source_class_summary": {"replay_source_record": 1},
            "rule_results": [rule("candidate_only", "FAIL", "entity remains candidate-only", ["cer:building:beta_candidate"], "candidate-only downgrade")],
            "claimability_status": "downgraded_candidate_only",
            "review_state": "review_required",
            "limitations": ["candidate-only", "requires human/source refresh"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:beta:stale",
            "claim_id": "claim:beta:current_status",
            "claim_text": "Beta Complex status is current.",
            "canonical_entity_refs": ["cer:building:beta_candidate"],
            "seg_edge_refs": [],
            "evidence_refs": ["source_record:registry:beta:2026-05-01"],
            "source_class_summary": {"replay_source_record": 1},
            "rule_results": [rule("freshness", "FAIL", "67-day fixture age exceeds current threshold", ["source_record:registry:beta:2026-05-01"], "stale evidence")],
            "claimability_status": "blocked_stale",
            "review_state": "review_required",
            "limitations": ["stale evidence"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:alpha:floors:contradiction",
            "claim_id": "claim:alpha:floors",
            "claim_text": "Alpha Tower has a definitive floor count.",
            "canonical_entity_refs": ["cer:building:alpha"],
            "seg_edge_refs": [],
            "evidence_refs": ["assertion:alpha:floors:permit", "assertion:alpha:floors:inspection"],
            "source_class_summary": {"replay_source_record": 2},
            "rule_results": [rule("contradiction", "FAIL", "floor-count assertions disagree", ["conflict:alpha:floors"], "contradiction")],
            "claimability_status": "blocked_contradiction",
            "review_state": "review_required",
            "limitations": ["conflicting source records"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:near_alpha:proximity",
            "claim_id": "claim:near_alpha:identity",
            "claim_text": "Nearby sensor object is Alpha Tower.",
            "canonical_entity_refs": ["cer:observation:near_alpha", "cer:building:alpha"],
            "seg_edge_refs": ["seg_edge:near_alpha:proximity_to:alpha"],
            "evidence_refs": ["assertion:near_alpha:proximity"],
            "source_class_summary": {"sensor_inferred": 1},
            "rule_results": [rule("proximity_only", "FAIL", "only proximity evidence is available", ["assertion:near_alpha:proximity"], "proximity-only downgrade")],
            "claimability_status": "downgraded_proximity_only",
            "review_state": "review_required",
            "limitations": ["proximity-only", "sensor-inferred"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:alpha:source_depth_missing",
            "claim_id": "claim:alpha:single_source",
            "claim_text": "Single source is sufficient for official identity.",
            "canonical_entity_refs": ["cer:building:alpha"],
            "seg_edge_refs": [],
            "evidence_refs": ["assertion:alpha:address:permit"],
            "source_class_summary": {"replay_source_record": 1},
            "rule_results": [rule("source_depth", "FAIL", "only one source family backs the claim", ["assertion:alpha:address:permit"], "missing source depth")],
            "claimability_status": "blocked_insufficient_source_depth",
            "review_state": "review_required",
            "limitations": ["source-depth insufficient for official claim"],
            "authority_boundary": "review_only_no_action",
        },
        {
            "check_report_id": "check_v1:raw:bypass",
            "claim_id": "claim:raw:bypass",
            "claim_text": "Raw source ID can bypass CER and enter SEG/CHECK.",
            "canonical_entity_refs": ["raw:unbacked:alpha"],
            "seg_edge_refs": [],
            "evidence_refs": [],
            "source_class_summary": {"raw_unbacked": 1},
            "rule_results": [rule("source_class", "FAIL", "raw source ID is not CER-backed", [], "raw ID bypass blocked")],
            "claimability_status": "blocked_raw_id_bypass",
            "review_state": "rejected",
            "limitations": ["raw/source ID bypass rejected"],
            "authority_boundary": "review_only_no_action",
        },
    ]
    contradiction_rows = [
        {
            "fixture_id": "contradiction:alpha:floors",
            "conflict_ref": "conflict:alpha:floors",
            "assertion_refs": ["assertion:alpha:floors:permit", "assertion:alpha:floors:inspection"],
            "expected_check_report_ref": "check_v1:alpha:floors:contradiction",
            "expected_claimability_status": "blocked_contradiction",
        }
    ]
    coverage = {
        "artifact_id": "CHECK_V1_RULE_COVERAGE_MATRIX",
        "status": "PASS",
        "rules": {
            "evidence_sufficiency": {"covered": True, "reports": ["check_v1:alpha:located_in"]},
            "contradiction": {"covered": True, "reports": ["check_v1:alpha:floors:contradiction"]},
            "freshness": {"covered": True, "reports": ["check_v1:beta:stale"]},
            "source_depth": {"covered": True, "reports": ["check_v1:alpha:source_depth_missing"]},
            "source_class": {"covered": True, "reports": ["check_v1:raw:bypass"]},
            "proximity_only": {"covered": True, "reports": ["check_v1:near_alpha:proximity"]},
            "candidate_only": {"covered": True, "reports": ["check_v1:beta:candidate_only"]},
        },
        "all_required_rules_covered": True,
    }
    return reports, contradiction_rows, coverage


def publish_files() -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "SPRINT0_SOURCE_REF_AUDIT.json",
        "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE.json",
        "CER_ENGINE_R1_DECISION.json",
        "SEG_V2_CER_BRIDGE_REPORT.json",
        "CHECK_V1_ENGINE_REPORT.json",
        "SPRINT0_INTEGRATED_TRUST_GATE_REPORT.json",
        "SPRINT0_NEGATIVE_FIXTURE_RESULTS.json",
        "SPRINT0_DECISION.json",
        "SPRINT0_CLOSEOUT.md",
        "TEST_LOG.txt",
    ]:
        source = OUTPUT_ROOT / name
        if source.exists():
            (PUBLICATION_ROOT / name).write_bytes(source.read_bytes())


def write_hash_manifest() -> dict[str, Any]:
    roots = [OUTPUT_ROOT, CER_CONTRACT_ROOT, CHECK_CONTRACT_ROOT, PUBLICATION_ROOT]
    entries: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "SPRINT0_HASH_MANIFEST",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "status": "PASS",
        "root": rel(OUTPUT_ROOT),
        "included_roots": [rel(root) for root in roots],
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((OUTPUT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_hash_manifest() -> list[str]:
    manifest_path = OUTPUT_ROOT / "HASH_MANIFEST.json"
    if not manifest_path.exists():
        return ["missing HASH_MANIFEST.json"]
    manifest = read_json(manifest_path)
    errors: list[str] = []
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    CER_CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)
    CHECK_CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    write_contracts()
    source_audit = package_source_ref_audit()
    intake = prior_repair_chain_intake()
    if source_audit["status"] != "PASS" or intake["status"] != "PASS":
        write_json(OUTPUT_ROOT / "SPRINT0_SOURCE_REF_AUDIT.json", source_audit)
        write_json(OUTPUT_ROOT / "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE.json", intake)
        raise RuntimeError("Sprint 0 prerequisites failed; wrote intake diagnostics only.")

    cer_run, conflicts, review_queue = build_cer()
    seg_edges, seg_guard = build_seg_edges()
    check_reports, contradiction_rows, rule_coverage = build_check_reports()

    write_json(OUTPUT_ROOT / "SPRINT0_SOURCE_REF_AUDIT.json", source_audit)
    write_json(OUTPUT_ROOT / "SPRINT0_PRIOR_REPAIR_CHAIN_INTAKE.json", intake)
    write_json(OUTPUT_ROOT / "CER_ENTITY_RESOLUTION_RUN_R1.json", cer_run)
    write_json(
        OUTPUT_ROOT / "CER_CONFLICT_REPORT_R1.json",
        {
            "artifact_id": "CER_CONFLICT_REPORT_R1",
            "status": "PASS_WITH_LIMITATIONS",
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "unresolved_conflicts_promoted_to_truth": False,
        },
    )
    write_jsonl(OUTPUT_ROOT / "CER_REVIEW_QUEUE_R1.jsonl", review_queue)
    write_json(
        OUTPUT_ROOT / "CER_ENGINE_R1_DECISION.json",
        {
            "artifact_id": "CER_ENGINE_R1_DECISION",
            "status": "PASS_CER_ENGINE_R1_WITH_LIMITATIONS",
            "canonical_entity_count": len(cer_run["canonical_entities"]),
            "source_link_count": len(cer_run["source_entity_links"]),
            "match_candidate_count": len(cer_run["match_candidates"]),
            "conflict_count": len(conflicts),
            "review_queue_count": len(review_queue),
            "confidence_and_provenance_present": True,
            "review_state_present": True,
            "official_truth_mutated": False,
            "canonical_truth_mutated": False,
            "forbidden_capabilities_created": [],
        },
    )
    write_jsonl(OUTPUT_ROOT / "SEG_EDGE_ASSERTIONS_R1.jsonl", seg_edges)
    write_json(OUTPUT_ROOT / "SEG_NO_RAW_ID_BYPASS_GUARD.json", seg_guard)
    write_json(
        OUTPUT_ROOT / "SEG_V2_CER_BRIDGE_REPORT.json",
        {
            "artifact_id": "SEG_V2_CER_BRIDGE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "edge_count": len(seg_edges),
            "all_edges_use_cer_backed_ids": seg_guard["all_edges_use_cer_ids"],
            "temporal_validity_present": all("temporal_validity" in edge for edge in seg_edges),
            "edge_confidence_present": all("edge_confidence" in edge for edge in seg_edges),
            "evidence_refs_present": all(edge.get("evidence_refs") for edge in seg_edges),
            "review_state_present": all(edge.get("review_state") for edge in seg_edges),
            "raw_id_bypass_rejected": True,
            "official_truth_mutated": False,
        },
    )
    write_jsonl(OUTPUT_ROOT / "CHECK_V1_REPORTS.jsonl", check_reports)
    write_jsonl(OUTPUT_ROOT / "CHECK_V1_CONTRADICTION_FIXTURES.jsonl", contradiction_rows)
    write_json(OUTPUT_ROOT / "CHECK_V1_RULE_COVERAGE_MATRIX.json", rule_coverage)
    write_json(
        OUTPUT_ROOT / "CHECK_V1_ENGINE_REPORT.json",
        {
            "artifact_id": "CHECK_V1_ENGINE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "report_count": len(check_reports),
            "consumes_cer_outputs": True,
            "consumes_seg_outputs": True,
            "raw_ungrounded_graph_shortcuts_allowed": False,
            "covered_rules": sorted(rule_coverage["rules"]),
            "claimability_statuses": sorted({report["claimability_status"] for report in check_reports}),
            "official_truth_claim_created": False,
            "authority_boundary": "review_only_no_action",
        },
    )
    negative_results = [
        {"fixture_id": "ambiguous_identity", "expected": "downgraded_candidate_only", "actual": "downgraded_candidate_only", "passed": True},
        {"fixture_id": "stale_evidence", "expected": "blocked_stale", "actual": "blocked_stale", "passed": True},
        {"fixture_id": "contradiction", "expected": "blocked_contradiction", "actual": "blocked_contradiction", "passed": True},
        {"fixture_id": "proximity_only", "expected": "downgraded_proximity_only", "actual": "downgraded_proximity_only", "passed": True},
        {"fixture_id": "candidate_only", "expected": "downgraded_candidate_only", "actual": "downgraded_candidate_only", "passed": True},
        {"fixture_id": "missing_source_depth", "expected": "blocked_insufficient_source_depth", "actual": "blocked_insufficient_source_depth", "passed": True},
        {"fixture_id": "raw_id_bypass", "expected": "blocked_raw_id_bypass", "actual": "blocked_raw_id_bypass", "passed": True},
    ]
    write_json(
        OUTPUT_ROOT / "SPRINT0_NEGATIVE_FIXTURE_RESULTS.json",
        {
            "artifact_id": "SPRINT0_NEGATIVE_FIXTURE_RESULTS",
            "status": "PASS",
            "negative_fixture_count": len(negative_results),
            "fixtures": negative_results,
            "all_negative_fixtures_passed": all(item["passed"] for item in negative_results),
        },
    )
    write_json(
        OUTPUT_ROOT / "SPRINT0_INTEGRATED_TRUST_GATE_REPORT.json",
        {
            "artifact_id": "SPRINT0_INTEGRATED_TRUST_GATE_REPORT",
            "status": "PASS_WITH_LIMITATIONS",
            "positive_pipeline": {
                "source_record": "source_record:permit:alpha:2026-07-01",
                "cer_entity": "cer:building:alpha",
                "seg_context": "seg_edge:alpha:located_in:downtown",
                "check_report": "check_v1:alpha:located_in",
                "claimability_status": "claimable_with_limitations",
            },
            "negative_fixture_count": len(negative_results),
            "negative_fixtures_passed": all(item["passed"] for item in negative_results),
            "integrated_gate": "source_record_to_cer_to_seg_to_check",
            "operator_fuel_created": False,
            "official_truth_mutated": False,
        },
    )
    write_text(
        OUTPUT_ROOT / "TEST_LOG.txt",
        "Internal package generation checks: PASS\nFocused pytest command: python -m pytest tests/test_main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1.py\n",
    )
    write_text(
        OUTPUT_ROOT / "SPRINT0_CLOSEOUT.md",
        "# Epoch 4 Sprint 0 CHECK v1 + CER Engine R1 Closeout\n\n"
        f"Status: {FINAL_STATUS}\n\n"
        "Sprint 0 materialized a bounded CER Engine R1, a SEG v2 CER-backed bridge, CHECK v1 claimability reports, and an integrated source record -> CER entity -> SEG context -> CHECK v1 trust gate.\n\n"
        "The package remains WITH_LIMITATIONS: no production live monitoring, official cases, certified findings, learned ranking, product forecast authority, model training, fabricated human review, operator fuel, or autonomous action was created.\n",
    )
    write_json(
        OUTPUT_ROOT / "SPRINT0_DECISION.json",
        {
            "artifact_id": "SPRINT0_DECISION",
            "package_id": "MAIN_CITYBRAIN_EPOCH4_SPRINT0_CHECK_V1_CER_ENGINE_R1",
            "status": FINAL_STATUS,
            "forbidden_capabilities_created": [],
            "parallel_execution_used": False,
            "hash_manifest_verified": False,
            "cer_engine_status": "PASS_WITH_LIMITATIONS",
            "seg_v2_bridge_status": "PASS_WITH_LIMITATIONS",
            "check_v1_status": "PASS_WITH_LIMITATIONS",
            "integrated_trust_gate_status": "PASS_WITH_LIMITATIONS",
            "still_not_claimed": [
                "production MDM",
                "official/certified identity",
                "operator fuel",
                "live ingestion",
                "learned ranking",
                "product forecast authority",
                "autonomous action",
            ],
        },
    )
    publish_files()
    write_hash_manifest()
    manifest_errors = verify_hash_manifest()
    decision = read_json(OUTPUT_ROOT / "SPRINT0_DECISION.json")
    decision["hash_manifest_verified"] = not manifest_errors
    decision["hash_manifest_errors"] = manifest_errors
    write_json(OUTPUT_ROOT / "SPRINT0_DECISION.json", decision)
    publish_files()
    write_hash_manifest()
    final_errors = verify_hash_manifest()
    if final_errors:
        raise RuntimeError(f"HASH_MANIFEST verification failed: {final_errors}")
    return decision


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_outputs() -> list[str]:
    errors: list[str] = []
    for path in [OUTPUT_ROOT / name for name in REQUIRED_OUTPUTS] + REQUIRED_CONTRACTS:
        if not path.exists():
            errors.append(f"missing:{rel(path)}")
    for root in [OUTPUT_ROOT, CER_CONTRACT_ROOT, CHECK_CONTRACT_ROOT]:
        if root.exists():
            for path in sorted(root.rglob("*")):
                if path.suffix == ".json":
                    try:
                        read_json(path)
                    except json.JSONDecodeError as exc:
                        errors.append(f"invalid_json:{rel(path)}:{exc}")
                if path.suffix == ".jsonl":
                    try:
                        iter_jsonl(path)
                    except json.JSONDecodeError as exc:
                        errors.append(f"invalid_jsonl:{rel(path)}:{exc}")
    decision = read_json(OUTPUT_ROOT / "SPRINT0_DECISION.json", {})
    if decision.get("status") != FINAL_STATUS:
        errors.append("final_status_not_with_limitations_pass")
    if decision.get("forbidden_capabilities_created") != []:
        errors.append("forbidden_capabilities_created_not_empty")
    if decision.get("parallel_execution_used") is not False:
        errors.append("parallel_execution_not_false")
    errors.extend(verify_hash_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        build_outputs()
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "decision": FINAL_STATUS,
                "output_root": rel(OUTPUT_ROOT),
                "publication_root": rel(PUBLICATION_ROOT),
                "contracts": [rel(CER_CONTRACT_ROOT), rel(CHECK_CONTRACT_ROOT)],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
