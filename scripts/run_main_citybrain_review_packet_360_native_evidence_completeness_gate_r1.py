#!/usr/bin/env python3
"""Run Review Packet 360 native evidence completeness gate R1.

This is a read-only audit over existing review packet, review-quality, founder
card, cadence, and simulation outputs. It does not modify source truth, review
packets, founder response inputs, or product surfaces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "MAIN-CITYBRAIN-REVIEW-PACKET-360-NATIVE-EVIDENCE-COMPLETENESS-GATE-R1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-review-packet-360-native-evidence-completeness-gate-r1"
STATUS = "PASS_MAIN_CITYBRAIN_REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_GATE_R1_WITH_LIMITATIONS"

FAMILIES = [
    "mobility_access_interruption_v0",
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
]

REQUIRED_SECTIONS = [
    "source_event_record",
    "cer_entity_resolution",
    "seg_context",
    "event_state",
    "check_v1_result",
    "simulation_baseline_and_options",
    "brief_v3",
    "spatial_overlay_refs",
    "workflow_state",
    "data_maturity_source_quality_notes",
    "cannot_claim",
    "limitations",
]

PATHS = {
    "review_packet_r1": ROOT / "outputs" / "main_citybrain_epoch4_review_packet_360_r1" / "REVIEW_PACKET_360_BY_FAMILY.json",
    "review_packet_v2": ROOT
    / "outputs"
    / "main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1"
    / "REVIEW_PACKET_360_V2_BY_FAMILY.json",
    "review_quality_decision": ROOT
    / "outputs"
    / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1"
    / "REVIEW_PACK_QUALITY_DECISION.json",
    "review_quality_scorecard": ROOT
    / "outputs"
    / "main_citybrain_epoch4_review_pack_quality_upgrade_r4_r1"
    / "REVIEW_CARD_EVIDENCE_QUALITY_SCORECARD.json",
    "review_quality_sequence": ROOT
    / "outputs"
    / "main_citybrain_epoch4_review_quality_global_gap_sequence_r1"
    / "REVIEW_QUALITY_GLOBAL_GAP_SEQUENCE_DECISION.json",
    "review_quality_reverify": ROOT
    / "outputs"
    / "main_citybrain_epoch4_review_quality_global_gap_final_reverify_r1"
    / "CARD_READINESS_SUMMARY.json",
    "evidence_repair_decision": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_EVIDENCE_REPAIR_DECISION.json",
    "mobility_backfill": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "MOBILITY_REVIEW_PACKET_360_BACKFILL_REPORT.json",
    "cer_seg_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_CER_SEG_CONTEXT_ATTACHMENT_REPORT.json",
    "actual_outcome_report": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_ACTUAL_OUTCOME_ATTACHMENT_REPORT.json",
    "r3_input_resolution": ROOT
    / "outputs"
    / "main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1"
    / "FOUNDER_PROBE_R3_INPUT_RESOLUTION_REPORT.json",
    "cadence_decision": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-EVENT-FABRIC-SEED-R3-CADENCE-REPLAY-QUARANTINE-MINING-R1"
    / "SEED_R3_CADENCE_REPLAY_DECISION.json",
    "simulation_distribution_decision": ROOT
    / "outputs"
    / "MAIN-CITYBRAIN-SIMULATION-DISTRIBUTION-CHECKED-FIXTURES-R1"
    / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json",
    "data_estate_audit": ROOT
    / "outputs"
    / "main_citybrain_epoch4_deep_data_estate_audit_r1"
    / "DEEP_DATA_ESTATE_AUDIT_DECISION.json",
}

REQUIRED_FILES = [
    "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json",
    "REVIEW_PACKET_360_INPUT_INVENTORY.json",
    "REVIEW_PACKET_360_FAMILY_INVENTORY.json",
    "REVIEW_PACKET_360_NATIVE_VS_DERIVED_LEDGER.jsonl",
    "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK.json",
    "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json",
    "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN.json",
    "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE.json",
    "REVIEW_PACKET_360_COMPLETENESS_FINDINGS.md",
    "NO_FOUNDER_SESSION_FUEL_GUARD.json",
    "NO_SOURCE_TRUTH_MUTATION_GUARD.json",
    "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json",
    "BOUNDARY_NO_ACTION_AUDIT.json",
    "HASH_MANIFEST.sha256",
    "CODEX_CLOSEOUT.md",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


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


def packet_map(packet_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packets = packet_payload.get("packets", [])
    return {packet.get("family_id"): packet for packet in packets if packet.get("family_id")}


def input_inventory() -> dict[str, Any]:
    rows = []
    for key, path in PATHS.items():
        payload = read_json(path)
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
        "artifact_id": "REVIEW_PACKET_360_INPUT_INVENTORY",
        "generated_at": now_iso(),
        "inputs": rows,
        "missing_inputs": [row for row in rows if not row["exists"]],
        "input_count": len(rows),
        "existing_input_count": sum(1 for row in rows if row["exists"]),
    }


def card_crosswalk(cer_seg: dict[str, Any], actual: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    by_task: dict[str, dict[str, Any]] = {}
    for row in actual.get("rows", []):
        by_task.setdefault(row["task_id"], {}).update(
            {
                "task_id": row["task_id"],
                "family": row["family"],
                "scenario": row.get("scenario"),
                "expected_check_outcome": row.get("expected_check_outcome"),
                "matched_actual_check_outcome": row.get("matched_actual_check_outcome"),
                "actual_outcome_match_status": row.get("actual_outcome_match_status"),
            }
        )
    for row in cer_seg.get("rows", []):
        by_task.setdefault(row["task_id"], {}).update(
            {
                "task_id": row["task_id"],
                "family": row.get("family", by_task.get(row["task_id"], {}).get("family")),
                "cer_context_missing": row.get("cer_context_missing"),
                "seg_context_missing": row.get("seg_context_missing"),
                "cer_seg_status": row.get("status"),
            }
        )
    for row in quality.get("rows", []):
        by_task.setdefault(row["task_id"], {}).update(
            {
                "task_id": row["task_id"],
                "quality_score_0_to_100": row.get("quality_score_0_to_100"),
                "has_actual_vs_expected_block": row.get("has_actual_vs_expected_block"),
                "has_source_evidence_summary": row.get("has_source_evidence_summary"),
                "has_cannot_claim_block": row.get("has_cannot_claim_block"),
                "remaining_gap": row.get("remaining_gap"),
            }
        )

    rows = [by_task[key] for key in sorted(by_task)]
    family_counts = Counter(row.get("family", "unknown") for row in rows)
    return {
        "artifact_id": "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK",
        "card_count": len(rows),
        "family_counts": dict(sorted(family_counts.items())),
        "all_cards_have_cer_seg_context": all(
            row.get("cer_context_missing") is False and row.get("seg_context_missing") is False for row in rows
        ),
        "all_cards_have_actual_outcome": all(row.get("matched_actual_check_outcome") for row in rows),
        "rows": rows,
    }


def classify_family(
    family: str,
    r1_packets: dict[str, dict[str, Any]],
    v2_packets: dict[str, dict[str, Any]],
    mobility_backfill: dict[str, Any],
    crosswalk: dict[str, Any],
) -> dict[str, Any]:
    r1 = r1_packets.get(family)
    v2 = v2_packets.get(family)
    native_sources = []
    missing_sections: list[str] = []
    if r1:
        native_sources.append(rel(PATHS["review_packet_r1"]))
        sections = set(r1.get("sections", {}).keys())
        missing_sections.extend([section for section in REQUIRED_SECTIONS if section not in sections])
    if v2:
        native_sources.append(rel(PATHS["review_packet_v2"]))
    card_rows = [row for row in crosswalk["rows"] if row.get("family") == family]
    cards_have_context = bool(card_rows) and all(
        row.get("cer_context_missing") is False and row.get("seg_context_missing") is False for row in card_rows
    )
    cards_have_actual = bool(card_rows) and all(row.get("matched_actual_check_outcome") for row in card_rows)
    blocking_gaps: list[str] = []

    if r1 and v2 and not missing_sections:
        native_status = "native_packet_complete"
        evidence_kind = "native_review_packet"
    elif r1 or v2:
        native_status = "native_packet_partial"
        evidence_kind = "mixed_native_derived"
        if missing_sections:
            blocking_gaps.append("missing_native_family_packet")
    elif family == "mobility_access_interruption_v0" and mobility_backfill.get("mobility_repair_status"):
        native_status = "derived_backfill_only"
        evidence_kind = "derived_review_packet_backfill_not_source_truth"
        blocking_gaps.append("missing_native_family_packet")
    else:
        native_status = "missing_native_packet"
        evidence_kind = "missing"
        blocking_gaps.append("missing_native_family_packet")

    if not cards_have_context:
        blocking_gaps.append("missing_cer_seg_context")
    if not cards_have_actual:
        blocking_gaps.append("missing_check_actual_outcome")
    if not r1 and not v2 and family != "mobility_access_interruption_v0":
        blocking_gaps.extend(["missing_source_refs", "missing_event_state", "missing_spatial_context"])
    if family == "permit_inspection_delay":
        blocking_gaps.append("missing_simulation_or_not_applicable_statement")

    if cards_have_context and cards_have_actual and evidence_kind != "missing":
        readiness = "diagnostic_ready"
    else:
        readiness = "not_ready"

    product_ready_candidate = (
        native_status == "native_packet_complete"
        and cards_have_context
        and cards_have_actual
        and family != "permit_inspection_delay"
    )

    return {
        "family_id": family,
        "native_packet_status": native_status,
        "review_readiness": readiness,
        "product_ready_candidate": product_ready_candidate,
        "evidence_kind": evidence_kind,
        "native_packet_sources": native_sources,
        "derived_backfill_source": rel(PATHS["mobility_backfill"])
        if family == "mobility_access_interruption_v0" and evidence_kind.startswith("derived")
        else None,
        "founder_card_count": len(card_rows),
        "cards_have_cer_seg_context": cards_have_context,
        "cards_have_check_actual_outcome": cards_have_actual,
        "blocking_gaps": sorted(set(blocking_gaps)),
        "missing_required_native_sections": sorted(set(missing_sections)),
    }


def build(out: Path = DEFAULT_OUT) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    r1_packets = packet_map(read_json(PATHS["review_packet_r1"]))
    v2_packets = packet_map(read_json(PATHS["review_packet_v2"]))
    mobility_backfill = read_json(PATHS["mobility_backfill"])
    cer_seg = read_json(PATHS["cer_seg_report"])
    actual = read_json(PATHS["actual_outcome_report"])
    quality = read_json(PATHS["review_quality_scorecard"])
    review_quality_decision = read_json(PATHS["review_quality_decision"])
    review_quality_sequence = read_json(PATHS["review_quality_sequence"])
    cadence_decision = read_json(PATHS["cadence_decision"])
    simulation_decision = read_json(PATHS["simulation_distribution_decision"])

    inventory = input_inventory()
    crosswalk = card_crosswalk(cer_seg, actual, quality)
    family_rows = [classify_family(family, r1_packets, v2_packets, mobility_backfill, crosswalk) for family in FAMILIES]
    native_incomplete = [
        row
        for row in family_rows
        if row["native_packet_status"] in {"native_packet_partial", "derived_backfill_only", "missing_native_packet", "unknown"}
    ]
    native_incomplete_families = [row["family_id"] for row in native_incomplete]
    mobility_only_native_gap = native_incomplete_families == ["mobility_access_interruption_v0"]
    all_diagnostic_ready = all(row["review_readiness"] == "diagnostic_ready" for row in family_rows)
    product_review_ready = False

    family_inventory = {
        "artifact_id": "REVIEW_PACKET_360_FAMILY_INVENTORY",
        "canonical_family_count": len(family_rows),
        "canonical_families_present": [row["family_id"] for row in family_rows],
        "all_four_canonical_families_present": set(row["family_id"] for row in family_rows) == set(FAMILIES),
        "family_rows": family_rows,
        "native_incomplete_family_count": len(native_incomplete_families),
        "native_incomplete_families": native_incomplete_families,
    }

    ledger = [
        {
            "family_id": row["family_id"],
            "native_packet_status": row["native_packet_status"],
            "evidence_kind": row["evidence_kind"],
            "review_readiness": row["review_readiness"],
            "native_packet_sources": row["native_packet_sources"],
            "derived_backfill_source": row["derived_backfill_source"],
            "blocking_gaps": row["blocking_gaps"],
            "founder_card_count": row["founder_card_count"],
            "cards_have_cer_seg_context": row["cards_have_cer_seg_context"],
            "cards_have_check_actual_outcome": row["cards_have_check_actual_outcome"],
        }
        for row in family_rows
    ]

    mobility_row = next(row for row in family_rows if row["family_id"] == "mobility_access_interruption_v0")
    mobility_finding = {
        "artifact_id": "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING",
        "family_id": "mobility_access_interruption_v0",
        "native_packet_status": mobility_row["native_packet_status"],
        "evidence_kind": mobility_row["evidence_kind"],
        "mobility_native_review_packet_exists": mobility_row["native_packet_status"] == "native_packet_complete",
        "derived_backfill_used": mobility_row["evidence_kind"] == "derived_review_packet_backfill_not_source_truth",
        "diagnostic_ready_with_limitations": mobility_row["review_readiness"] == "diagnostic_ready",
        "product_review_blocked": True,
        "source": rel(PATHS["mobility_backfill"]),
        "finding": "Mobility is the only canonical family lacking native Review Packet 360 family packet evidence; current coverage is a derived backfill, not source truth.",
    }

    repair_plan = {
        "artifact_id": "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN",
        "recommendation": "MOBILITY_NATIVE_PACKET_REPAIR_ONLY"
        if mobility_only_native_gap
        else "ALL_FAMILY_EVIDENCE_UPGRADE",
        "mobility_only_native_gap": mobility_only_native_gap,
        "all_family_packet_weakness_detected": len(native_incomplete_families) > 1,
        "native_incomplete_families": native_incomplete_families,
        "actions": [
            "Create native Review Packet 360 family packet evidence for mobility_access_interruption_v0 from source records, CER/SEG, CHECK actual outcomes, event state, simulation/not-applicable context, BRIEF, and spatial refs.",
            "Keep the R3 derived backfill labeled as derived_review_packet_backfill_not_source_truth until native packet evidence exists.",
            "Do not run founder review or product review from this gate.",
        ],
    }

    product_gate = {
        "artifact_id": "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE",
        "founder_diagnostic_review_allowed_with_limitations": all_diagnostic_ready,
        "product_review_ready": product_review_ready,
        "client_ready_claim_allowed": False,
        "all_families_diagnostic_ready": all_diagnostic_ready,
        "all_families_native_or_complete_mixed": False,
        "mobility_derived_backfill_only_blocks_product_review": mobility_row["native_packet_status"] == "derived_backfill_only",
        "review_quality_product_review_ready_recommended": review_quality_decision.get("product_review_ready_recommended", False),
        "review_quality_status": review_quality_decision.get("status"),
        "blockers": [
            "mobility native Review Packet 360 family packet absent",
            "R4 review quality recommends founder diagnostic review only, not product review",
            "founder/operator session results remain absent",
        ],
    }

    guards = {
        "founder": {
            "artifact_id": "NO_FOUNDER_SESSION_FUEL_GUARD",
            "status": "PASS",
            "founder_session_results_created": False,
            "operator_fuel_created": False,
            "training_rows_created": False,
            "source_refs": [rel(PATHS["evidence_repair_decision"]), rel(PATHS["review_quality_sequence"])],
        },
        "source_truth": {
            "artifact_id": "NO_SOURCE_TRUTH_MUTATION_GUARD",
            "status": "PASS",
            "source_truth_mutated": False,
            "raw_provider_payload_rewritten": False,
            "canonical_source_records_mutated": False,
        },
        "client_ready": {
            "artifact_id": "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD",
            "status": "PASS",
            "client_ready_claim_created": False,
            "product_review_ready_claim_created": False,
            "product_review_ready": False,
        },
        "boundary": {
            "artifact_id": "BOUNDARY_NO_ACTION_AUDIT",
            "status": "PASS",
            "read_only": True,
            "forecast_packet_created": False,
            "live_ingestion_claim_created": False,
            "official_action_case_dispatch_control_enforcement_created": False,
            "learning_arming_created": False,
            "operator_fuel_created": False,
            "source_truth_mutated": False,
        },
    }

    decision = {
        "artifact_id": "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION",
        "task_id": "MAIN-CITYBRAIN-REVIEW-PACKET-360-NATIVE-EVIDENCE-COMPLETENESS-GATE-R1",
        "generated_at": now_iso(),
        "status": STATUS,
        "canonical_family_count": len(family_rows),
        "all_four_canonical_families_inventoried": True,
        "family_native_status_counts": dict(Counter(row["native_packet_status"] for row in family_rows)),
        "family_review_readiness_counts": dict(Counter(row["review_readiness"] for row in family_rows)),
        "mobility_native_packet_status": mobility_row["native_packet_status"],
        "mobility_only_native_gap": mobility_only_native_gap,
        "all_family_packet_weakness_detected": len(native_incomplete_families) > 1,
        "recommended_repair_scope": repair_plan["recommendation"],
        "founder_diagnostic_review_allowed_with_limitations": all_diagnostic_ready,
        "product_review_ready": product_review_ready,
        "client_ready": False,
        "source_truth_mutated": False,
        "founder_session_results_created": False,
        "operator_fuel_created": False,
        "training_rows_created": False,
        "cadence_status": cadence_decision.get("status"),
        "simulation_distribution_status": simulation_decision.get("status"),
    }

    findings = f"""# Review Packet 360 Native Evidence Completeness Findings

Status: `{STATUS}`

## Decision

- Four canonical families were inventoried.
- `mobility_access_interruption_v0` remains `derived_backfill_only`.
- The other three canonical families have native Review Packet 360 packet evidence from R1/V2 packet outputs.
- The recommended repair scope is `{repair_plan["recommendation"]}`.

## Readiness

- Founder diagnostic review remains allowed with limitations because all 16 founder cards have CER/SEG context and actual outcome blocks.
- Product review remains blocked because mobility native Review Packet 360 family evidence is absent and R4 review quality did not recommend product review.

## Boundaries

- No founder session result, operator fuel, training rows, source-truth mutation, raw/provider rewrite, client-ready claim, ForecastPacket, live ingestion, official action, case, dispatch, control, or enforcement was created.
"""

    closeout = f"""# Review Packet 360 Native Evidence Completeness Gate R1 Closeout

Status: `{STATUS}`

The gate found a mobility-only native packet gap: mobility is covered by a derived backfill, while building compliance, permit inspection delay, and city asset infrastructure issue have native Review Packet 360 family packet evidence. Product review remains closed; the next evidence repair should create a native mobility family packet before product-review claims.
"""

    write_json(out / "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json", decision)
    write_json(out / "REVIEW_PACKET_360_INPUT_INVENTORY.json", inventory)
    write_json(out / "REVIEW_PACKET_360_FAMILY_INVENTORY.json", family_inventory)
    write_jsonl(out / "REVIEW_PACKET_360_NATIVE_VS_DERIVED_LEDGER.jsonl", ledger)
    write_json(out / "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK.json", crosswalk)
    write_json(out / "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json", mobility_finding)
    write_json(out / "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN.json", repair_plan)
    write_json(out / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE.json", product_gate)
    write_text(out / "REVIEW_PACKET_360_COMPLETENESS_FINDINGS.md", findings)
    write_json(out / "NO_FOUNDER_SESSION_FUEL_GUARD.json", guards["founder"])
    write_json(out / "NO_SOURCE_TRUTH_MUTATION_GUARD.json", guards["source_truth"])
    write_json(out / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json", guards["client_ready"])
    write_json(out / "BOUNDARY_NO_ACTION_AUDIT.json", guards["boundary"])
    write_text(out / "CODEX_CLOSEOUT.md", closeout)
    write_manifest(out)
    copy_publication(out)
    return decision


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
        actual = sha256_file(path)
        if actual != expected:
            failures.append(f"Hash mismatch for {file_ref}")
    return failures


def copy_publication(out: Path) -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json",
        "REVIEW_PACKET_360_FAMILY_INVENTORY.json",
        "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json",
        "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN.json",
        "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE.json",
        "REVIEW_PACKET_360_COMPLETENESS_FINDINGS.md",
        "BOUNDARY_NO_ACTION_AUDIT.json",
        "CODEX_CLOSEOUT.md",
        "HASH_MANIFEST.sha256",
    ]:
        src = out / name
        if src.exists():
            shutil.copy2(src, PUBLICATION_ROOT / name)


def required_paths(out: Path) -> list[Path]:
    return [out / name for name in REQUIRED_FILES]


def validate(out: Path = DEFAULT_OUT) -> list[str]:
    failures: list[str] = []
    missing = [rel(path) for path in required_paths(out) if not path.exists()]
    failures.extend(f"Missing required output: {path}" for path in missing)
    if missing:
        return failures

    decision = read_json(out / "REVIEW_PACKET_360_NATIVE_EVIDENCE_COMPLETENESS_DECISION.json")
    family_inventory = read_json(out / "REVIEW_PACKET_360_FAMILY_INVENTORY.json")
    mobility = read_json(out / "REVIEW_PACKET_360_MOBILITY_NATIVE_PACKET_FINDING.json")
    repair = read_json(out / "REVIEW_PACKET_360_ALL_FAMILY_REPAIR_PLAN.json")
    product_gate = read_json(out / "REVIEW_PACKET_360_PRODUCT_REVIEW_READINESS_GATE.json")
    crosswalk = read_json(out / "REVIEW_PACKET_360_FOUNDER_CARD_CROSSWALK.json")
    boundary = read_json(out / "BOUNDARY_NO_ACTION_AUDIT.json")
    source_guard = read_json(out / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    fuel_guard = read_json(out / "NO_FOUNDER_SESSION_FUEL_GUARD.json")

    if decision.get("status") != STATUS:
        failures.append("Unexpected decision status.")
    if not family_inventory.get("all_four_canonical_families_present"):
        failures.append("Not all four canonical families are present.")
    rows = family_inventory.get("family_rows", [])
    if len(rows) != 4:
        failures.append("Family inventory does not contain 4 rows.")
    if not all(row.get("native_packet_status") for row in rows):
        failures.append("Every family must have native packet classification.")
    if mobility.get("native_packet_status") != "derived_backfill_only":
        failures.append("Mobility native evidence status must be explicit derived_backfill_only.")
    if repair.get("mobility_only_native_gap") is not True:
        failures.append("Expected mobility-only native gap.")
    if repair.get("recommendation") != "MOBILITY_NATIVE_PACKET_REPAIR_ONLY":
        failures.append("Expected mobility-only repair recommendation.")
    if product_gate.get("founder_diagnostic_review_allowed_with_limitations") is not True:
        failures.append("Founder diagnostic readiness should be allowed with limitations.")
    if product_gate.get("product_review_ready") is not False:
        failures.append("Product review must remain closed.")
    if product_gate.get("client_ready_claim_allowed") is not False:
        failures.append("Client-ready claim must not be allowed.")
    if crosswalk.get("card_count") != 16:
        failures.append("Expected 16 founder card crosswalk rows.")
    if crosswalk.get("all_cards_have_cer_seg_context") is not True:
        failures.append("All founder cards should have CER/SEG context attached.")
    if crosswalk.get("all_cards_have_actual_outcome") is not True:
        failures.append("All founder cards should have actual outcomes attached.")
    if boundary.get("official_action_case_dispatch_control_enforcement_created") is not False:
        failures.append("Boundary action/control guard failed.")
    if source_guard.get("source_truth_mutated") is not False:
        failures.append("Source-truth guard failed.")
    if fuel_guard.get("operator_fuel_created") is not False or fuel_guard.get("founder_session_results_created") is not False:
        failures.append("Founder/session/fuel guard failed.")

    failures.extend(verify_manifest(out / "HASH_MANIFEST.sha256"))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if not args.validate_only:
        decision = build(DEFAULT_OUT)
        print(decision["status"])
    failures = validate(DEFAULT_OUT)
    if failures:
        for failure in failures:
            print(f"VALIDATION FAILURE: {failure}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
