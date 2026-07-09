#!/usr/bin/env python3
"""Repair Review Packet 360 mobility native evidence when supportable."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_GATE_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-NATIVE-EVIDENCE-COMPLETENESS-GATE-R1"
DEFAULT_EXPANDED_CORPUS_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1"
DEFAULT_EXPANDED_CADENCE_ROOT = ROOT / "outputs" / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2"
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-review-packet-360-mobility-native-repair-r1"

STATUS_PASS = "PASS_MAIN_CITYBRAIN_REVIEW_PACKET_360_MOBILITY_NATIVE_REPAIR_R1_WITH_LIMITATIONS"
STATUS_BLOCKED = "PASS_MAIN_CITYBRAIN_REVIEW_PACKET_360_MOBILITY_NATIVE_REPAIR_R1_BLOCKED_WITH_LIMITATIONS"
FAMILY = "mobility_access_interruption_v0"
FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

PATHS = {
    "mobility_backfill": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "MOBILITY_REVIEW_PACKET_360_BACKFILL_REPORT.json",
    "actual_outcomes": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_ACTUAL_OUTCOME_ATTACHMENT_REPORT.json",
    "cer_seg": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_CER_SEG_CONTEXT_ATTACHMENT_REPORT.json",
    "simulation_mobility": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1"
    / "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json",
}

REQUIRED_FILES = [
    "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json",
    "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json",
    "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.md",
    "MOBILITY_REVIEW_PACKET_360_NATIVE_EVIDENCE_LEDGER.jsonl",
    "MOBILITY_REVIEW_PACKET_360_NATIVE_INPUT_INVENTORY.json",
    "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json",
    "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS.json",
    "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json",
    "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json",
    "FOUNDER_CARD_MOBILITY_REFRESH_CANDIDATES.json",
    "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
    "NO_FOUNDER_SESSION_FUEL_GUARD.json",
    "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
]


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "SEED_R3_ADAPTER_CORPUS_EXPANSION_DECISION.json",
        "feed": root / "SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
        "canonical": root / "SEED_R3_EXPANDED_CANONICAL_RESOLUTION_REPORT.json",
        "unresolved": root / "SEED_R3_EXPANDED_UNRESOLVED_QUEUE.jsonl",
        "quarantine": root / "SEED_R3_EXPANDED_QUARANTINE_QUEUE.jsonl",
        "reason_distribution": root / "SEED_R3_EXPANDED_QUEUE_REASON_DISTRIBUTION.json",
    }


def cadence_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
        "hashes": root / "EXPANDED_CORPUS_CADENCE_MODE_STATE_HASHES.json",
        "queue": root / "EXPANDED_CORPUS_QUEUE_MINING_REPORT.json",
        "canonical": root / "EXPANDED_CORPUS_CANONICAL_RESOLUTION_REPLAY_VALIDATED.json",
        "state": root / "EXPANDED_CORPUS_REPLAY_MATERIALIZED_STATE.jsonl",
    }


def gate_paths(root: Path) -> dict[str, Path]:
    return {
        "decision": root / "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json",
        "family": root / "REVIEW_PACKET_360_FAMILY_INVENTORY.json",
        "mobility": root / "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json",
        "crosswalk": root / "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK.json",
    }


def input_inventory(packet_gate_root: Path, expanded_corpus_root: Path, expanded_cadence_root: Path) -> dict[str, Any]:
    inputs = {
        **{f"packet_gate:{key}": path for key, path in gate_paths(packet_gate_root).items()},
        **{f"expanded_corpus:{key}": path for key, path in corpus_paths(expanded_corpus_root).items()},
        **{f"expanded_cadence:{key}": path for key, path in cadence_paths(expanded_cadence_root).items()},
        **{f"prior:{key}": path for key, path in PATHS.items()},
    }
    rows = []
    for key, path in inputs.items():
        payload = read_json(path) if path.suffix == ".json" else {}
        rows.append(
            {
                "key": key,
                "path": rel(path),
                "exists": path.exists(),
                "status": payload.get("status") if isinstance(payload, dict) else None,
                "artifact_id": payload.get("artifact_id") if isinstance(payload, dict) else None,
            }
        )
    return {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_NATIVE_INPUT_INVENTORY",
        "inputs": rows,
        "missing_inputs": [row for row in rows if not row["exists"]],
        "existing_input_count": sum(1 for row in rows if row["exists"]),
        "input_count": len(rows),
    }


def mobility_rows(feed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in feed if row.get("canonical_loop_family_id") == FAMILY]


def evidence_support(
    packet_gate_root: Path,
    expanded_corpus_root: Path,
    expanded_cadence_root: Path,
) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    gate_decision = read_json(gate_paths(packet_gate_root)["decision"])
    mobility_finding = read_json(gate_paths(packet_gate_root)["mobility"])
    corpus_decision = read_json(corpus_paths(expanded_corpus_root)["decision"])
    feed = read_jsonl(corpus_paths(expanded_corpus_root)["feed"])
    cadence_decision = read_json(cadence_paths(expanded_cadence_root)["decision"])
    hashes = read_json(cadence_paths(expanded_cadence_root)["hashes"])
    actual = read_json(PATHS["actual_outcomes"])
    cer_seg = read_json(PATHS["cer_seg"])
    sim = read_json(PATHS["simulation_mobility"])

    blockers: list[dict[str, Any]] = []
    if gate_decision.get("mobility_only_native_gap") is not True:
        blockers.append({"blocker": "packet_gate_did_not_identify_mobility_only_gap"})
    if mobility_finding.get("native_packet_status") != "derived_backfill_only":
        blockers.append({"blocker": "prior_mobility_gap_status_not_derived_backfill_only"})
    if corpus_decision.get("status") != "PASS_MAIN_CITYBRAIN_SEED_R3_ADAPTER_CORPUS_EXPANSION_R1_WITH_LIMITATIONS":
        blockers.append({"blocker": "expanded_corpus_not_passed"})
    rows = mobility_rows(feed)
    if len(rows) < 20:
        blockers.append({"blocker": "insufficient_native_mobility_expanded_corpus_events", "count": len(rows)})
    if cadence_decision.get("status") != "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_SEED_R3_EXPANDED_CORPUS_CADENCE_REPLAY_MINING_R2_WITH_LIMITATIONS":
        blockers.append({"blocker": "expanded_cadence_not_passed"})
    if hashes.get("identical_final_state_hash") is not True:
        blockers.append({"blocker": "expanded_cadence_hashes_not_identical"})
    actual_rows = [row for row in actual.get("rows", []) if row.get("family") == FAMILY]
    if len(actual_rows) < 4:
        blockers.append({"blocker": "missing_mobility_check_actual_outcomes", "count": len(actual_rows)})
    cer_rows = [row for row in cer_seg.get("rows", []) if row.get("family") == FAMILY]
    if len(cer_rows) < 4:
        blockers.append({"blocker": "missing_mobility_cer_seg_context", "count": len(cer_rows)})
    if sim.get("status") != "CHECKED_WITH_LIMITATIONS":
        blockers.append({"blocker": "missing_mobility_simulation_distribution_context"})

    return not blockers, blockers, {
        "mobility_events": rows,
        "actual_rows": actual_rows,
        "cer_rows": cer_rows,
        "simulation": sim,
        "cadence_decision": cadence_decision,
        "cadence_hashes": hashes,
        "corpus_decision": corpus_decision,
    }


def build_native_packet(packet_gate_root: Path, expanded_corpus_root: Path, expanded_cadence_root: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    corpus = corpus_paths(expanded_corpus_root)
    cadence = cadence_paths(expanded_cadence_root)
    canonical = read_json(corpus["canonical"])
    unresolved = [row for row in read_jsonl(corpus["unresolved"]) if row.get("family_id") == FAMILY]
    quarantine = [row for row in read_jsonl(corpus["quarantine"]) if row.get("family_id") == FAMILY]
    reasons = read_json(corpus["reason_distribution"]).get("by_family", {}).get(FAMILY, {})
    mobility_events = evidence["mobility_events"]
    resolved_events = [row for row in mobility_events if row.get("resolution_outcome") == "resolved"]
    cannot_claim = [
        "product/client readiness",
        "founder/operator validation",
        "official action/case/ticket",
        "dispatch/control/enforcement",
        "forecast or ForecastPacket",
        "city calibration",
        "source truth mutation",
    ]
    return {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET",
        "family_id": FAMILY,
        "native_packet_status": "native_packet_complete",
        "evidence_kind": "native_review_packet",
        "authority_boundary": "local_replay_review_only_no_action",
        "native_event_fabric_refs": [row["event_id"] for row in mobility_events[:20]],
        "native_event_fabric_source_ref": rel(corpus["feed"]),
        "expanded_cadence_decision_ref": rel(cadence["decision"]),
        "expanded_cadence_final_state_hash": evidence["cadence_hashes"]["final_state_hash_values"][0],
        "cer_seg_context": {
            "cer_style_canonical_refs": canonical.get("canonical_refs_by_family", {}).get(FAMILY, []),
            "cer_seg_card_rows": evidence["cer_rows"],
        },
        "check_actual_outcomes": evidence["actual_rows"],
        "resolution_summary": {
            "event_count": len(mobility_events),
            "resolved_count": len(resolved_events),
            "unresolved_review_count": len(unresolved),
            "quarantine_expected_count": len(quarantine),
            "reason_counts": reasons,
        },
        "unresolved_queue_refs": [row["event_id"] for row in unresolved],
        "quarantine_queue_refs": [row["event_id"] for row in quarantine],
        "spatial_context_refs": [
            row.get("candidate_geometry_ref")
            for row in mobility_events
            if row.get("candidate_geometry_ref")
        ][:8],
        "simulation_context": {
            "status": evidence["simulation"].get("status"),
            "claim_boundary": evidence["simulation"].get("claim_boundary"),
            "named_donor_distributions_used": evidence["simulation"].get("named_donor_distributions_used", []),
            "comparison_metrics": evidence["simulation"].get("comparison_metrics", []),
        },
        "source_refs_with_provenance": [
            {"ref": rel(corpus["feed"]), "kind": "native_event_fabric_expanded_adapter_feed"},
            {"ref": rel(cadence["decision"]), "kind": "native_cadence_replay_validation"},
            {"ref": rel(corpus["canonical"]), "kind": "canonical_resolution_report"},
            {"ref": rel(PATHS["actual_outcomes"]), "kind": "check_actual_outcome_attachment"},
            {"ref": rel(PATHS["simulation_mobility"]), "kind": "simulation_donor_distribution_context"},
            {"ref": rel(PATHS["mobility_backfill"]), "kind": "derived_backfill_comparison_only"},
        ],
        "cannot_claim": cannot_claim,
        "derived_backfill_comparison": {
            "source_ref": rel(PATHS["mobility_backfill"]),
            "label": "derived_review_packet_backfill_not_source_truth",
            "used_as_native_evidence": False,
        },
    }


def evidence_ledger(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ref in packet["native_event_fabric_refs"]:
        rows.append(
            {
                "evidence_id": ref,
                "family_id": FAMILY,
                "evidence_type": "native_event_fabric_expanded_adapter_event",
                "source_ref": packet["native_event_fabric_source_ref"],
                "native_evidence": True,
                "derived_backfill": False,
            }
        )
    for row in packet["check_actual_outcomes"]:
        rows.append(
            {
                "evidence_id": row["task_id"],
                "family_id": FAMILY,
                "evidence_type": "check_actual_outcome",
                "source_ref": row.get("source"),
                "native_evidence": True,
                "derived_backfill": False,
            }
        )
    rows.append(
        {
            "evidence_id": "mobility_derived_backfill_comparison",
            "family_id": FAMILY,
            "evidence_type": "derived_backfill_comparison_only",
            "source_ref": packet["derived_backfill_comparison"]["source_ref"],
            "native_evidence": False,
            "derived_backfill": True,
        }
    )
    return rows


def family_status_after(packet_gate_root: Path, repair_supported: bool) -> dict[str, Any]:
    family_inventory = read_json(gate_paths(packet_gate_root)["family"])
    rows = []
    for row in family_inventory.get("family_rows", []):
        updated = dict(row)
        if row.get("family_id") == FAMILY and repair_supported:
            updated.update(
                {
                    "native_packet_status": "native_packet_complete",
                    "evidence_kind": "native_review_packet",
                    "blocking_gaps": [],
                    "native_packet_sources": [
                        "outputs/MAIN-CITYBRAIN-SEED-R3-ADAPTER-CORPUS-EXPANSION-R1/SEED_R3_EXPANDED_ADAPTER_FEED.jsonl",
                        "outputs/MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-EXPANDED-CORPUS-CADENCE-REPLAY-MINING-R2/EXPANDED_CORPUS_CADENCE_REPLAY_MINING_DECISION.json",
                    ],
                    "derived_backfill_source": row.get("derived_backfill_source"),
                    "derived_backfill_source_used_as_native": False,
                }
            )
        rows.append(updated)
    return {
        "artifact_id": "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR",
        "family_rows": rows,
        "canonical_family_count": len(rows),
        "all_four_families_inventoried": set(row["family_id"] for row in rows) == set(FAMILIES),
        "family_native_status_counts": dict(Counter(row["native_packet_status"] for row in rows)),
        "mobility_repair_supported": repair_supported,
    }


def product_recheck(repair_supported: bool) -> dict[str, Any]:
    return {
        "artifact_id": "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK",
        "mobility_native_repair_status": "native_packet_complete" if repair_supported else "native_packet_blocked_missing_native_evidence",
        "founder_diagnostic_review_allowed_with_limitations": True,
        "product_review_ready": False,
        "client_ready": False,
        "product_review_blockers": [
            "No founder/operator validation session result exists.",
            "No operator fuel, dispositions, or external validation rows exist.",
            "This package repairs evidence packet structure only; it does not authorize product/client readiness.",
        ],
    }


def refresh_candidates(actual_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_id": "FOUNDER_CARD_MOBILITY_REFRESH_CANDIDATES",
        "candidate_count": len(actual_rows),
        "status": "CANDIDATES_ONLY_NO_SESSION_RESULT",
        "rows": [
            {
                "task_id": row["task_id"],
                "family": row["family"],
                "scenario": row.get("scenario"),
                "refresh_reason": "attach native mobility Review Packet 360 refs from expanded corpus and R2 cadence validation",
                "session_result_created": False,
                "operator_fuel_created": False,
            }
            for row in actual_rows
        ],
    }


def write_manifest(out: Path) -> None:
    manifest = out / "HASH_MANIFEST.sha256"
    rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path != manifest:
            rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(manifest, "\n".join(rows))


def verify_manifest(manifest: Path) -> list[str]:
    failures: list[str] = []
    if not manifest.exists():
        return [f"Missing manifest: {rel(manifest)}"]
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, file_ref = line.split("  ", 1)
        path = ROOT / file_ref
        if not path.exists():
            failures.append(f"Manifest path missing: {file_ref}")
            continue
        if sha256_file(path) != expected:
            failures.append(f"Hash mismatch: {file_ref}")
    return failures


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json",
        "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json",
        "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.md",
        "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json",
        "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS.json",
        "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json",
        "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json",
        "BOUNDARY_NO_ACTION_AUDIT.json",
        "CODEX_CLOSEOUT.md",
        "HASH_MANIFEST.sha256",
    ]:
        src = out / name
        if src.exists():
            shutil.copy2(src, PUBLICATION_ROOT / name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def build(
    packet_gate_root: Path = DEFAULT_PACKET_GATE_ROOT,
    expanded_corpus_root: Path = DEFAULT_EXPANDED_CORPUS_ROOT,
    expanded_cadence_root: Path = DEFAULT_EXPANDED_CADENCE_ROOT,
    out: Path = DEFAULT_OUT,
) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    inventory = input_inventory(packet_gate_root, expanded_corpus_root, expanded_cadence_root)
    supported, blockers, evidence = evidence_support(packet_gate_root, expanded_corpus_root, expanded_cadence_root)
    packet = build_native_packet(packet_gate_root, expanded_corpus_root, expanded_cadence_root, evidence) if supported else {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET",
        "family_id": FAMILY,
        "native_packet_status": "native_packet_blocked_missing_native_evidence",
        "evidence_kind": "derived_review_packet_backfill_not_source_truth",
        "derived_backfill_comparison": {
            "source_ref": rel(PATHS["mobility_backfill"]),
            "label": "derived_review_packet_backfill_not_source_truth",
            "used_as_native_evidence": False,
        },
        "cannot_claim": ["native packet complete", "product/client readiness"],
    }
    ledger = evidence_ledger(packet) if supported else []
    provenance = {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT",
        "mobility_repair_supported": supported,
        "native_evidence_sources": [row for row in ledger if row.get("native_evidence")],
        "derived_backfill_sources": [row for row in ledger if row.get("derived_backfill")],
        "derived_backfill_relabelled_as_native": False,
        "derived_backfill_used_as_comparison_only": True,
        "status": "PASS",
    }
    blockers_payload = {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS",
        "blocker_count": len(blockers),
        "blockers": blockers,
        "status": "NO_BLOCKERS" if not blockers else "BLOCKED_WITH_LIMITATIONS",
    }
    family_status = family_status_after(packet_gate_root, supported)
    product_gate = product_recheck(supported)
    refresh = refresh_candidates(evidence.get("actual_rows", []))
    guards = {
        "source": {
            "artifact_id": "NO_SOURCE_TRUTH_MUTATION_GUARD",
            "status": "PASS",
            "source_truth_mutated": False,
            "raw_provider_payload_rewritten": False,
            "existing_review_packet_files_mutated": False,
            "derived_backfill_relabelled_as_native": False,
        },
        "fuel": {
            "artifact_id": "NO_FOUNDER_SESSION_FUEL_GUARD",
            "status": "PASS",
            "founder_responses_created": False,
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
        },
        "client": {
            "artifact_id": "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD",
            "status": "PASS",
            "product_review_ready_claim_created": False,
            "client_ready_claim_created": False,
            "product_review_ready": False,
            "client_ready": False,
        },
        "boundary": {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "status": "PASS",
            "source_truth_mutated": False,
            "forecast_packet_created": False,
            "live_ingestion_created": False,
            "official_workflow_case_action_created": False,
            "dispatch_control_enforcement_created": False,
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "product_client_ready_claim_created": False,
        },
    }
    status = STATUS_PASS if supported else STATUS_BLOCKED
    decision = {
        "artifact_id": "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION",
        "task_id": "MAIN-CITYBRAIN-REVIEW-PACKET-360-MOBILITY-NATIVE-REPAIR-R1",
        "status": status,
        "mobility_native_packet_status": packet["native_packet_status"],
        "mobility_repair_supported": supported,
        "product_review_ready": False,
        "client_ready": False,
        "founder_diagnostic_review_allowed_with_limitations": True,
        "derived_backfill_relabelled_as_native": False,
        "missing_native_evidence_blocker_count": len(blockers),
        "native_mobility_event_count": len(evidence.get("mobility_events", [])),
        "expanded_cadence_status": evidence.get("cadence_decision", {}).get("status"),
        "source_truth_mutated": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "founder_session_results_created": False,
    }
    packet_md = f"""# Mobility Review Packet 360 Native Packet

Status: `{packet["native_packet_status"]}`

Family: `{FAMILY}`

Native Event Fabric refs: {len(packet.get("native_event_fabric_refs", []))}

Expanded cadence: `{evidence.get("cadence_decision", {}).get("status")}`

Derived backfill comparison: `{packet["derived_backfill_comparison"]["label"]}` and `used_as_native_evidence=false`.

Product review remains closed because this package creates no founder/operator validation, operator fuel, training rows, official action, forecast, or client-ready claim.
"""
    closeout = f"""# Review Packet 360 Mobility Native Repair R1 Closeout

Status: `{status}`

Mobility native repair is {'supported' if supported else 'blocked'} with status `{packet["native_packet_status"]}`. The packet uses native expanded Event Fabric adapter events and R2 cadence validation as native evidence, while preserving the prior mobility backfill as derived comparison only. Product review remains closed.
"""
    write_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json", decision)
    write_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json", packet)
    write_text(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.md", packet_md)
    write_jsonl(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_EVIDENCE_LEDGER.jsonl", ledger)
    write_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_INPUT_INVENTORY.json", inventory)
    write_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json", provenance)
    write_json(out / "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS.json", blockers_payload)
    write_json(out / "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json", family_status)
    write_json(out / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json", product_gate)
    write_json(out / "FOUNDER_CARD_MOBILITY_REFRESH_CANDIDATES.json", refresh)
    write_json(out / "NO_SOURCE_TRUTH_MUTATION_GUARD.json", guards["source"])
    write_json(out / "NO_FOUNDER_SESSION_FUEL_GUARD.json", guards["fuel"])
    write_json(out / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json", guards["client"])
    write_json(out / "BOUNDARY_NO_ACTION_AUDIT.json", guards["boundary"])
    write_text(out / "CODEX_CLOSEOUT.md", closeout)
    write_manifest(out)
    copy_publication(out)
    return decision


def validate(out: Path = DEFAULT_OUT) -> list[str]:
    failures: list[str] = []
    missing = [rel(path) for path in required_paths(out) if not path.exists()]
    failures.extend(f"Missing required output: {path}" for path in missing)
    if missing:
        return failures
    decision = read_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_REPAIR_DECISION.json")
    packet = read_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_PACKET.json")
    ledger = read_jsonl(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_EVIDENCE_LEDGER.jsonl")
    provenance = read_json(out / "MOBILITY_REVIEW_PACKET_360_NATIVE_VS_DERIVED_PROVENANCE_AUDIT.json")
    blockers = read_json(out / "MOBILITY_REVIEW_PACKET_360_MISSING_NATIVE_EVIDENCE_BLOCKERS.json")
    family = read_json(out / "REVIEW_PACKET_360_FAMILY_STATUS_AFTER_MOBILITY_REPAIR.json")
    product = read_json(out / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_RECHECK.json")
    refresh = read_json(out / "FOUNDER_CARD_MOBILITY_REFRESH_CANDIDATES.json")
    source = read_json(out / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    fuel = read_json(out / "NO_FOUNDER_SESSION_FUEL_GUARD.json")
    client = read_json(out / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json")
    boundary = read_json(out / "BOUNDARY_NO_ACTION_AUDIT.json")
    if decision.get("status") not in {STATUS_PASS, STATUS_BLOCKED}:
        failures.append("Unexpected decision status.")
    if decision.get("status") == STATUS_PASS and packet.get("native_packet_status") != "native_packet_complete":
        failures.append("Supported repair must produce native_packet_complete.")
    if packet.get("family_id") != FAMILY:
        failures.append("Native packet family id is wrong.")
    if packet.get("derived_backfill_comparison", {}).get("used_as_native_evidence") is not False:
        failures.append("Derived backfill must not be used as native evidence.")
    if decision.get("status") == STATUS_PASS:
        native_rows = [row for row in ledger if row.get("native_evidence")]
        derived_rows = [row for row in ledger if row.get("derived_backfill")]
        if not native_rows:
            failures.append("Native evidence ledger has no native rows.")
        if not derived_rows:
            failures.append("Native evidence ledger should retain derived comparison row.")
        if blockers.get("blocker_count") != 0:
            failures.append("Supported repair should have zero blockers.")
    if provenance.get("derived_backfill_relabelled_as_native") is not False:
        failures.append("Provenance audit relabelled derived backfill.")
    if family.get("all_four_families_inventoried") is not True:
        failures.append("All four families must remain inventoried.")
    if product.get("product_review_ready") is not False or product.get("client_ready") is not False:
        failures.append("Product/client readiness must remain closed.")
    if refresh.get("status") != "CANDIDATES_ONLY_NO_SESSION_RESULT":
        failures.append("Founder card refresh candidates must not be session results.")
    if source.get("source_truth_mutated") is not False or source.get("derived_backfill_relabelled_as_native") is not False:
        failures.append("Source/provenance guard failed.")
    if fuel.get("founder_session_results_created") is not False or fuel.get("operator_fuel_created") is not False or fuel.get("training_rows_created") is not False:
        failures.append("Founder/fuel/training guard failed.")
    if client.get("client_ready_claim_created") is not False or client.get("product_review_ready_claim_created") is not False:
        failures.append("Product/client claim guard failed.")
    for key in [
        "source_truth_mutated",
        "forecast_packet_created",
        "live_ingestion_created",
        "official_workflow_case_action_created",
        "dispatch_control_enforcement_created",
        "founder_session_results_created",
        "operator_fuel_created",
        "training_rows_created",
        "product_client_ready_claim_created",
    ]:
        if boundary.get(key) is not False:
            failures.append(f"Boundary guard failed: {key}")
    failures.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-gate-root", default=str(DEFAULT_PACKET_GATE_ROOT))
    parser.add_argument("--expanded-corpus-root", default=str(DEFAULT_EXPANDED_CORPUS_ROOT))
    parser.add_argument("--expanded-cadence-root", default=str(DEFAULT_EXPANDED_CADENCE_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    packet_gate_root = Path(args.packet_gate_root)
    expanded_corpus_root = Path(args.expanded_corpus_root)
    expanded_cadence_root = Path(args.expanded_cadence_root)
    out = Path(args.out)
    if not args.validate_only:
        decision = build(packet_gate_root, expanded_corpus_root, expanded_cadence_root, out)
        print(decision["status"])
    failures = validate(out)
    if failures:
        for failure in failures:
            print(f"VALIDATION FAILURE: {failure}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
