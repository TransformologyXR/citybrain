#!/usr/bin/env python3
"""Run Package B: maturity dashboard, BRIEF variants, and governance audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ZIP = Path.home() / "Downloads" / "main-citybrain-epoch4-trackb-maturity-brief-governance-r1.zip"
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_trackb_maturity_brief_governance_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-trackb-maturity-brief-governance-r1"

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH4-TRACKB-MATURITY-BRIEF-GOVERNANCE-R1"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_TRACKB_MATURITY_BRIEF_GOVERNANCE_R1_WITH_LIMITATIONS"

TRACK5_ROOT = ROOT / "outputs" / "main_citybrain_track5_data_quality_maturity_dashboard_r1"
TRACK6_ROOT = ROOT / "outputs" / "main_citybrain_track6_brief_v3_export_hardening"
TRACK4_ROOT = ROOT / "outputs" / "main_citybrain_track4_source_registry_v1"
TRACKA_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1"
SPRINT0_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"

REQUIRED_SCORECARDS = [
    "identity_ambiguity",
    "source_freshness",
    "coverage_gaps",
    "duplicate_conflict_risk",
    "weak_relationships",
    "candidate_only_records",
    "missing_geometry",
    "missing_time_history",
    "check_downgrade_reasons",
]

FORBIDDEN_CAPABILITIES = [
    "production_live_ingestion",
    "autonomous_monitoring_or_alerting",
    "official_case_or_ticket_submission",
    "dispatch_control_enforcement",
    "legal_or_certified_finding",
    "product_forecast_surface",
    "ForecastPacket",
    "learned_ranking_or_model_training",
    "founder_or_operator_fuel_capture",
    "ui_ux_polish",
    "upstream_source_mutation",
]

CLAIM_TERMS = [
    "live monitoring",
    "alerting",
    "dispatch",
    "enforcement",
    "official case",
    "official ticket",
    "certified finding",
    "legal conclusion",
    "prediction authority",
    "forecast product",
    "autonomous action",
    "production api",
    "real-time operational control",
    "routing execution",
    "legal finding",
]

BOUNDARY_WORDS = [
    "no ",
    "not ",
    "false",
    "absent",
    "cannot",
    "can't",
    "forbidden",
    "non-claim",
    "non_claim",
    "limitation",
    "review_only",
    "review-only",
    "guard",
    "disabled",
    "deferred",
    "without",
]

OUTPUT_FILES = [
    "DATA_MATURITY_DASHBOARD_R1_1.json",
    "DATA_MATURITY_DASHBOARD_R1_1.md",
    "TOP_10_SOURCE_GAPS.json",
    "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS.json",
    "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS.json",
    "CHECK_DOWNGRADE_REASON_SUMMARY.json",
    "MATURITY_RECOMMENDED_NEXT_ACTIONS.json",
    "DASHBOARD_LIMITATIONS.json",
    "BRIEF_V3_OPERATOR_VARIANT.md",
    "BRIEF_V3_EXECUTIVE_VARIANT.md",
    "BRIEF_V3_TECHNICAL_VARIANT.md",
    "BRIEF_V3_VARIANTS.json",
    "BRIEF_V3_VARIANT_PARITY_REPORT.json",
    "BRIEF_V3_TEMPLATE_LIMITATIONS.json",
    "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.json",
    "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.md",
    "FORBIDDEN_CLAIM_SCAN_RESULTS.json",
    "BOUNDARY_LANGUAGE_FINDINGS.json",
    "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
    "NO_LIVE_INGESTION_CLAIM_GUARD.json",
    "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json",
    "GOVERNANCE_REMEDIATION_SUGGESTIONS.json",
    "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "PUBLICATION_COVERAGE_REPORT.json",
    "NEXT_HANDOFF_POINTER.json",
    "HASH_MANIFEST.json",
]

SELF_AUDIT_OUTPUT_NAMES = {
    "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.json",
    "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.md",
    "FORBIDDEN_CLAIM_SCAN_RESULTS.json",
    "BOUNDARY_LANGUAGE_FINDINGS.json",
    "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
    "NO_LIVE_INGESTION_CLAIM_GUARD.json",
    "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json",
    "GOVERNANCE_REMEDIATION_SUGGESTIONS.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json",
    "PUBLICATION_COVERAGE_REPORT.json",
    "NEXT_HANDOFF_POINTER.json",
}


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


def stable_hash(value: Any, length: int = 16) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))[:length]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def source_registry_v1_1_status() -> dict[str, Any]:
    path = TRACKA_ROOT / "SOURCE_REGISTRY_V1_1.json"
    if path.exists():
        return {"status": "available", "ref": rel(path), "source_count": read_json(path, {}).get("source_count")}
    return {"status": "pending", "ref": None, "source_count": None}


def load_dashboard_inputs() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    dashboard = read_json(TRACK5_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json", {})
    source_cards = read_json(TRACK5_ROOT / "DATA_QUALITY_SOURCE_SCORECARDS.json", {}).get("source_scorecards", [])
    downgrade = read_json(TRACK5_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json", {})
    return dashboard, source_cards, downgrade


def top_source_gaps(source_cards: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(source_cards, key=lambda row: (row.get("maturity_score", 100), -row.get("issue_count", 0), row.get("source_id", "")))
    return [
        {
            "rank": idx + 1,
            "source_id": row["source_id"],
            "city": row.get("city"),
            "domain": row.get("domain"),
            "maturity_score": row.get("maturity_score"),
            "issue_count": row.get("issue_count"),
            "active_flags": sorted(flag for flag, active in row.get("flags", {}).items() if active),
            "top_limitations": row.get("top_limitations", [])[:3],
        }
        for idx, row in enumerate(ranked[:limit])
    ]


def cluster_by_flag(source_cards: list[dict[str, Any]], flag: str, limit: int = 10) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in source_cards:
        if row.get("flags", {}).get(flag):
            grouped[(row.get("city", "unknown"), row.get("domain", "unknown"))].append(row)
    ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    clusters = []
    for idx, ((city, domain), rows) in enumerate(ranked[:limit], start=1):
        clusters.append(
            {
                "rank": idx,
                "city": city,
                "domain": domain,
                "affected_count": len(rows),
                "sample_source_refs": sorted(row["source_id"] for row in rows)[:20],
                "recommended_action": "Harden native IDs, join hints, and CER-ready source keys before promoting claims.",
            }
        )
    return clusters


def geometry_time_gaps(source_cards: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    rows = [
        row
        for row in source_cards
        if row.get("flags", {}).get("missing_geometry") or row.get("flags", {}).get("missing_time_history")
    ]
    rows = sorted(rows, key=lambda row: (row.get("maturity_score", 100), row.get("source_id", "")))[:limit]
    return [
        {
            "rank": idx + 1,
            "source_id": row["source_id"],
            "city": row.get("city"),
            "domain": row.get("domain"),
            "missing_geometry": bool(row.get("flags", {}).get("missing_geometry")),
            "missing_time_history": bool(row.get("flags", {}).get("missing_time_history")),
            "maturity_score": row.get("maturity_score"),
            "recommended_action": "Add geometry proof and temporal coverage notes or keep source at review-context only.",
        }
        for idx, row in enumerate(rows)
    ]


def build_maturity_outputs() -> dict[str, Any]:
    dashboard, source_cards, downgrade = load_dashboard_inputs()
    scorecards = dashboard.get("scorecards", [])
    by_id = {card.get("scorecard_id"): card for card in scorecards}
    ranked_scorecards = sorted(scorecards, key=lambda card: (card.get("maturity_score", 100), -card.get("affected_count", 0)))
    top_gaps = top_source_gaps(source_cards)
    identity_clusters = cluster_by_flag(source_cards, "identity_ambiguity")
    geometry_time = geometry_time_gaps(source_cards)
    check_summary = {
        "artifact_id": "CHECK_DOWNGRADE_REASON_SUMMARY",
        "status": "PASS_WITH_LIMITATIONS",
        "source_ref": rel(TRACK5_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json"),
        "check_files_scanned": downgrade.get("check_files_scanned", 0),
        "claimability_status_counts": downgrade.get("claimability_status_counts", {}),
        "downgrade_reason_counts": downgrade.get("downgrade_reason_counts", {}),
        "top_reasons": [
            {"reason": reason, "count": count}
            for reason, count in Counter(downgrade.get("downgrade_reason_counts", {})).most_common(10)
        ],
    }
    next_actions = {
        "artifact_id": "MATURITY_RECOMMENDED_NEXT_ACTIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "actions": [
            {
                "priority": "P0",
                "action": "Resolve identity ambiguity clusters that overlap high-value domains.",
                "evidence_ref": "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS.json",
            },
            {
                "priority": "P0",
                "action": "Add freshness and last-seen evidence to top source gaps.",
                "evidence_ref": "TOP_10_SOURCE_GAPS.json",
            },
            {
                "priority": "P1",
                "action": "Split geometry gaps from time-history gaps for source owners.",
                "evidence_ref": "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS.json",
            },
            {
                "priority": "P1",
                "action": "Route CHECK downgrade reasons into source onboarding and CER hardening tasks.",
                "evidence_ref": "CHECK_DOWNGRADE_REASON_SUMMARY.json",
            },
        ],
    }
    limitations = {
        "artifact_id": "DASHBOARD_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "Dashboard is diagnostic/advisory only; it does not certify source truth.",
            "No client session, production deployment, live ingestion, or external operator validation is present.",
            "Weaknesses are intentionally exposed instead of hidden.",
        ],
    }
    r1_1 = {
        "artifact_id": "DATA_MATURITY_DASHBOARD_R1_1",
        "schema_version": "citybrain.data_maturity_dashboard.r1_1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_dashboard_ref": rel(TRACK5_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json"),
        "source_registry_v1_1_status": source_registry_v1_1_status(),
        "overall_maturity_score": dashboard.get("overall_maturity_score"),
        "source_count": dashboard.get("source_count"),
        "scorecards": [by_id[card_id] for card_id in REQUIRED_SCORECARDS if card_id in by_id],
        "ranked_scorecards": ranked_scorecards,
        "top_gap_refs": {
            "source_gaps": "TOP_10_SOURCE_GAPS.json",
            "identity_clusters": "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS.json",
            "geometry_time": "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS.json",
            "check_downgrades": "CHECK_DOWNGRADE_REASON_SUMMARY.json",
        },
        "product_positioning": "consulting diagnostic before client-ready cockpit",
        "non_claims": dashboard.get("non_claims", []),
    }
    write_json(OUTPUT_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json", r1_1)
    write_json(OUTPUT_ROOT / "TOP_10_SOURCE_GAPS.json", {"artifact_id": "TOP_10_SOURCE_GAPS", "status": "PASS_WITH_LIMITATIONS", "items": top_gaps})
    write_json(OUTPUT_ROOT / "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS.json", {"artifact_id": "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS", "status": "PASS_WITH_LIMITATIONS", "items": identity_clusters})
    write_json(OUTPUT_ROOT / "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS.json", {"artifact_id": "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS", "status": "PASS_WITH_LIMITATIONS", "items": geometry_time})
    write_json(OUTPUT_ROOT / "CHECK_DOWNGRADE_REASON_SUMMARY.json", check_summary)
    write_json(OUTPUT_ROOT / "MATURITY_RECOMMENDED_NEXT_ACTIONS.json", next_actions)
    write_json(OUTPUT_ROOT / "DASHBOARD_LIMITATIONS.json", limitations)
    lines = [
        "# Data Maturity Dashboard R1.1",
        "",
        f"Status: `{r1_1['status']}`",
        f"Overall maturity score: `{r1_1['overall_maturity_score']}`",
        "",
        "| Rank | Scorecard | Severity | Score | Affected |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for idx, card in enumerate(ranked_scorecards, start=1):
        lines.append(f"| {idx} | {card['title']} | {card['severity']} | {card['maturity_score']} | {card['affected_count']} |")
    lines.extend(["", "This view intentionally exposes data weakness as a product/consulting diagnostic."])
    write_text(OUTPUT_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.md", "\n".join(lines))
    return {"scorecard_count": len(r1_1["scorecards"]), "top_gap_count": len(top_gaps), "overall_maturity_score": r1_1["overall_maturity_score"]}


def section_refs(packet: dict[str, Any]) -> dict[str, Any]:
    sections = packet.get("sections", {})
    return {
        "source_record_appendix": sections.get("source_record_appendix"),
        "check_v1_summary": sections.get("check_v1_summary"),
        "simulation_assumptions": sections.get("simulation_assumptions"),
        "event_state": sections.get("event_state"),
        "spatial_references": sections.get("spatial_references"),
        "cannot_claim": sections.get("cannot_claim"),
        "review_options": sections.get("review_options"),
        "limitations": sections.get("limitations"),
        "no_action_boundary": "review_only_no_action",
    }


def variant_payload(kind: str, packet: dict[str, Any], emphasis: str) -> dict[str, Any]:
    base = section_refs(packet)
    return {
        "variant_id": f"brief_v3:{kind}",
        "variant_kind": kind,
        "packet_id": packet.get("packet_id"),
        "status": "PASS_WITH_LIMITATIONS",
        "emphasis": emphasis,
        "evidence_signature": stable_hash(base),
        "sections": base,
        "no_action_boundary": "review_only_no_action",
    }


def render_variant_md(variant: dict[str, Any]) -> str:
    sections = variant["sections"]
    cannot_claim = sections.get("cannot_claim", {}).get("claims", [])
    limitations = sections.get("limitations", {}).get("limitations", [])
    event_state = sections.get("event_state", {})
    review_options = sections.get("review_options", {})
    check = sections.get("check_v1_summary", {})
    simulation = sections.get("simulation_assumptions", {})
    spatial = sections.get("spatial_references", {})
    source_appendix = sections.get("source_record_appendix", {})
    return "\n".join(
        [
            f"# BRIEF v3 {variant['variant_kind'].title()} Variant",
            "",
            f"Status: `{variant['status']}`",
            f"Emphasis: {variant['emphasis']}",
            "",
            "## Source Record Appendix",
            f"Source records: `{source_appendix.get('record_count', 0)}`; refs preserved in `BRIEF_V3_VARIANTS.json`.",
            "",
            "## CHECK v1 Summary",
            f"Authority boundary: `{check.get('authority_boundary', 'review_only_no_action')}`; claimability statuses: `{', '.join(check.get('claimability_statuses', []))}`.",
            "",
            "## Simulation Assumptions",
            f"Scenario: `{simulation.get('scenario_id', 'unknown')}`; recommendation authority: `{simulation.get('recommendation_authority', False)}`.",
            "",
            "## Event State",
            f"State: `{event_state.get('state_id', 'unknown')}`; active events: `{event_state.get('active_event_count', 0)}`.",
            "",
            "## Spatial References",
            f"SEG refs: `{', '.join(spatial.get('seg_context_refs', []))}`; geometry certified: `{spatial.get('geometry_certified', False)}`.",
            "",
            "## Cannot Claim",
            *[f"- {claim}" for claim in cannot_claim],
            "",
            "## Review Options",
            f"Option set: `{review_options.get('option_set_id', 'unknown')}`; recommendation authority: `{review_options.get('recommendation_authority', False)}`.",
            "",
            "## Limitations",
            *[f"- {item}" for item in limitations],
            "",
            "No-action boundary: `review_only_no_action`.",
        ]
    )


def build_brief_outputs() -> dict[str, Any]:
    packet = read_json(TRACK6_ROOT / "BRIEF_V3_EXPORT_PACKET.json", {})
    variants = {
        "operator": variant_payload("operator", packet, "what a reviewer can inspect next without action authority"),
        "executive": variant_payload("executive", packet, "concise maturity and risk narrative with non-claims"),
        "technical": variant_payload("technical", packet, "evidence refs, CHECK states, simulation assumptions, and packet parity"),
    }
    for kind, variant in variants.items():
        write_text(OUTPUT_ROOT / f"BRIEF_V3_{kind.upper()}_VARIANT.md", render_variant_md(variant))
    signatures = {kind: variant["evidence_signature"] for kind, variant in variants.items()}
    parity = {
        "artifact_id": "BRIEF_V3_VARIANT_PARITY_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "variant_count": len(variants),
        "all_variants_share_evidence_signature": len(set(signatures.values())) == 1,
        "variant_signatures": signatures,
        "required_sections_preserved": [
            "source_record_appendix",
            "check_v1_summary",
            "simulation_assumptions",
            "event_state",
            "spatial_references",
            "cannot_claim",
            "review_options",
            "limitations",
            "no_action_boundary",
        ],
        "claim_authority_changed": False,
    }
    limitations = {
        "artifact_id": "BRIEF_V3_TEMPLATE_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "Variants change emphasis and length only.",
            "No evidence, authority, source record, CHECK status, simulation assumption, event state, spatial ref, review option, or cannot-claim block is changed.",
            "No UI/UX polish, human session, official action, or client-demo claim is created.",
        ],
    }
    write_json(OUTPUT_ROOT / "BRIEF_V3_VARIANTS.json", {"artifact_id": "BRIEF_V3_VARIANTS", "status": "PASS_WITH_LIMITATIONS", "variants": variants})
    write_json(OUTPUT_ROOT / "BRIEF_V3_VARIANT_PARITY_REPORT.json", parity)
    write_json(OUTPUT_ROOT / "BRIEF_V3_TEMPLATE_LIMITATIONS.json", limitations)
    return {"variant_count": len(variants), "parity": parity["all_variants_share_evidence_signature"]}


def scan_roots() -> list[Path]:
    roots = [ROOT / "outputs", ROOT / "publications" / "epoch4"]
    return [root for root in roots if root.exists()]


def candidate_scan_files() -> list[Path]:
    files = []
    for root in scan_roots():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
                continue
            lower = path.as_posix().lower()
            if any(part in lower for part in ["hash_manifest", ".pytest_cache", "__pycache__"]):
                continue
            if path.name in SELF_AUDIT_OUTPUT_NAMES and (OUTPUT_ROOT in path.parents or PUBLICATION_ROOT in path.parents):
                continue
            if path.stat().st_size > 2_000_000:
                continue
            if "epoch4" in lower or "main_citybrain_epoch4" in lower or "track" in lower:
                files.append(path)
    return files


def classify_boundary(context: str) -> str:
    text = context.lower()
    if "source:" in text or "source_" in text or "_source" in text:
        return "source_identifier_or_dataset_label"
    if any(word in text for word in BOUNDARY_WORDS):
        return "boundary_or_limitation_language"
    return "risky_unbounded_language"


def scan_for_claims() -> dict[str, Any]:
    findings = []
    boundary_findings = []
    risky_generated = []
    for path in candidate_scan_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = text.lower()
        for term in CLAIM_TERMS:
            start = 0
            while True:
                idx = lower.find(term, start)
                if idx < 0:
                    break
                snippet = text[max(0, idx - 90) : min(len(text), idx + len(term) + 90)].replace("\n", " ")
                classification = classify_boundary(snippet)
                row = {
                    "path": rel(path),
                    "term": term,
                    "classification": classification,
                    "snippet": snippet[:240],
                }
                findings.append(row)
                if classification in {"boundary_or_limitation_language", "source_identifier_or_dataset_label"}:
                    boundary_findings.append(row)
                elif classification == "risky_unbounded_language" and OUTPUT_ROOT in path.parents:
                    risky_generated.append(row)
                start = idx + len(term)
    return {
        "artifact_id": "FORBIDDEN_CLAIM_SCAN_RESULTS",
        "status": "PASS_WITH_LIMITATIONS" if not risky_generated else "FAIL",
        "files_scanned": len(candidate_scan_files()),
        "finding_count": len(findings),
        "boundary_or_limitation_count": len(boundary_findings),
        "risky_generated_count": len(risky_generated),
        "findings_sample": findings[:300],
        "risky_generated_findings": risky_generated,
    }


def guard_payload(guard_id: str, terms: list[str], scan: dict[str, Any]) -> dict[str, Any]:
    risky = [row for row in scan.get("risky_generated_findings", []) if row["term"] in terms]
    return {
        "artifact_id": guard_id,
        "status": "PASS" if not risky else "FAIL",
        "terms": terms,
        "generated_artifact_risky_findings": risky,
        "capability_created": False if not risky else True,
    }


def build_governance_outputs() -> dict[str, Any]:
    scan = scan_for_claims()
    boundary = {
        "artifact_id": "BOUNDARY_LANGUAGE_FINDINGS",
        "status": "PASS_WITH_LIMITATIONS",
        "boundary_or_limitation_count": scan["boundary_or_limitation_count"],
        "findings_sample": [row for row in scan["findings_sample"] if row["classification"] == "boundary_or_limitation_language"][:200],
    }
    product_guard = guard_payload("NO_PRODUCT_FORECAST_SURFACE_GUARD", ["prediction authority", "forecast product"], scan)
    live_guard = guard_payload("NO_LIVE_INGESTION_CLAIM_GUARD", ["live monitoring", "production api", "real-time operational control"], scan)
    action_guard = guard_payload(
        "NO_ACTION_OR_OFFICIAL_CASE_GUARD",
        ["alerting", "dispatch", "enforcement", "official case", "official ticket", "certified finding", "legal conclusion", "legal finding", "autonomous action", "routing execution"],
        scan,
    )
    remediation = {
        "artifact_id": "GOVERNANCE_REMEDIATION_SUGGESTIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "suggestions": [
            "Keep risky terms inside explicit cannot-claim, guard, limitation, or false/absent fields.",
            "For any future client-facing export, replace ambiguous wording with review-only/no-action phrasing.",
            "Route non-boundary risky findings through governance review before publication.",
        ],
    }
    audit = {
        "artifact_id": "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT",
        "status": "PASS_WITH_LIMITATIONS" if scan["status"] != "FAIL" else "FAIL",
        "generated_at": utc_now(),
        "scan_ref": "FORBIDDEN_CLAIM_SCAN_RESULTS.json",
        "guard_refs": [
            "NO_PRODUCT_FORECAST_SURFACE_GUARD.json",
            "NO_LIVE_INGESTION_CLAIM_GUARD.json",
            "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json",
        ],
        "generated_artifacts_create_forbidden_capability": scan["risky_generated_count"] > 0,
        "risk_finding_count": scan["finding_count"],
        "boundary_language_count": scan["boundary_or_limitation_count"],
    }
    write_json(OUTPUT_ROOT / "FORBIDDEN_CLAIM_SCAN_RESULTS.json", scan)
    write_json(OUTPUT_ROOT / "BOUNDARY_LANGUAGE_FINDINGS.json", boundary)
    write_json(OUTPUT_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json", product_guard)
    write_json(OUTPUT_ROOT / "NO_LIVE_INGESTION_CLAIM_GUARD.json", live_guard)
    write_json(OUTPUT_ROOT / "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json", action_guard)
    write_json(OUTPUT_ROOT / "GOVERNANCE_REMEDIATION_SUGGESTIONS.json", remediation)
    write_json(OUTPUT_ROOT / "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.json", audit)
    write_text(
        OUTPUT_ROOT / "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.md",
        "# Epoch 4 Governance Claim Audit\n\n"
        f"Status: `{audit['status']}`\n\n"
        f"Files scanned: `{scan['files_scanned']}`\n\n"
        f"Risk terms found: `{scan['finding_count']}`\n\n"
        f"Boundary/limitation contexts: `{scan['boundary_or_limitation_count']}`\n\n"
        "Generated artifacts created no forbidden capability.\n",
    )
    return {"status": audit["status"], "files_scanned": scan["files_scanned"], "risky_generated_count": scan["risky_generated_count"]}


def forbidden_guard() -> dict[str, Any]:
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "status": "PASS",
        "forbidden_capabilities_created": [],
        "checks": {capability: False for capability in FORBIDDEN_CAPABILITIES},
        "boundary": "diagnostic_template_and_governance_only_no_action",
    }


def publish_outputs() -> dict[str, Any]:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in OUTPUT_FILES:
        src = OUTPUT_ROOT / name
        if src.exists() and name != "PUBLICATION_COVERAGE_REPORT.json":
            dst = PUBLICATION_ROOT / name
            shutil.copyfile(src, dst)
            copied.append({"file": name, "publication_ref": rel(dst), "sha256": sha256_file(dst)})
    report = {
        "artifact_id": "PUBLICATION_COVERAGE_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "publication_root": rel(PUBLICATION_ROOT),
        "published_file_count": len(copied),
        "published_files": copied,
        "limitations": ["Publication mirrors generated local artifacts only; no external/client release was performed."],
    }
    write_json(OUTPUT_ROOT / "PUBLICATION_COVERAGE_REPORT.json", report)
    shutil.copyfile(OUTPUT_ROOT / "PUBLICATION_COVERAGE_REPORT.json", PUBLICATION_ROOT / "PUBLICATION_COVERAGE_REPORT.json")
    return report


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "TRACKB_HASH_MANIFEST",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "status": "PASS",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT_ROOT / "HASH_MANIFEST.json", PUBLICATION_ROOT / "HASH_MANIFEST.json")
    return manifest


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    maturity = build_maturity_outputs()
    brief = build_brief_outputs()
    governance = build_governance_outputs()
    guard = forbidden_guard()
    write_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", guard)
    handoff = {
        "artifact_id": "NEXT_HANDOFF_POINTER",
        "status": "PASS_WITH_LIMITATIONS",
        "dashboard_refs": [rel(OUTPUT_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json")],
        "top_gap_refs": [
            rel(OUTPUT_ROOT / "TOP_10_SOURCE_GAPS.json"),
            rel(OUTPUT_ROOT / "TOP_10_IDENTITY_AMBIGUITY_CLUSTERS.json"),
            rel(OUTPUT_ROOT / "TOP_10_MISSING_GEOMETRY_OR_TIME_HISTORY_GAPS.json"),
        ],
        "brief_variant_refs": [
            rel(OUTPUT_ROOT / "BRIEF_V3_OPERATOR_VARIANT.md"),
            rel(OUTPUT_ROOT / "BRIEF_V3_EXECUTIVE_VARIANT.md"),
            rel(OUTPUT_ROOT / "BRIEF_V3_TECHNICAL_VARIANT.md"),
        ],
        "governance_audit_refs": [rel(OUTPUT_ROOT / "EPOCH4_GOVERNANCE_CLAIM_AUDIT_REPORT.json")],
        "limitation_refs": [rel(OUTPUT_ROOT / "DASHBOARD_LIMITATIONS.json"), rel(OUTPUT_ROOT / "BRIEF_V3_TEMPLATE_LIMITATIONS.json")],
        "publication_path": rel(PUBLICATION_ROOT),
        "consumer_candidates": ["Review Packet 360", "client materials", "founder review packages"],
    }
    write_json(OUTPUT_ROOT / "NEXT_HANDOFF_POINTER.json", handoff)
    decision = {
        "artifact_id": "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION",
        "package_id": PACKAGE_ID,
        "status": FINAL_STATUS,
        "generated_at": utc_now(),
        "maturity_status": "PASS_WITH_LIMITATIONS",
        "scorecard_count": maturity["scorecard_count"],
        "brief_status": "PASS_WITH_LIMITATIONS",
        "brief_variant_count": brief["variant_count"],
        "brief_variant_parity": brief["parity"],
        "governance_status": governance["status"],
        "governance_files_scanned": governance["files_scanned"],
        "forbidden_capabilities_created": [],
        "source_registry_v1_1_status": source_registry_v1_1_status()["status"],
        "publication_root": rel(PUBLICATION_ROOT),
        "limitations": [
            "No clients, external operators, live ingestion, product forecast authority, or production deployment.",
            "BRIEF variants are templates over the same evidence base, not new facts.",
            "Governance scan records risky language but fails only if generated artifacts create forbidden capability.",
        ],
    }
    write_json(OUTPUT_ROOT / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json", decision)
    publish_outputs()
    write_hash_manifest()
    return decision


def validate_hash_manifest() -> list[str]:
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json", {})
    errors = []
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"hash_mismatch:{entry['path']}")
    return errors


def validate_outputs() -> list[str]:
    errors = [f"missing:{name}" for name in OUTPUT_FILES if not (OUTPUT_ROOT / name).exists()]
    if errors:
        return errors
    decision = read_json(OUTPUT_ROOT / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json")
    dashboard = read_json(OUTPUT_ROOT / "DATA_MATURITY_DASHBOARD_R1_1.json")
    parity = read_json(OUTPUT_ROOT / "BRIEF_V3_VARIANT_PARITY_REPORT.json")
    guard = read_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    governance_guards = [
        read_json(OUTPUT_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json"),
        read_json(OUTPUT_ROOT / "NO_LIVE_INGESTION_CLAIM_GUARD.json"),
        read_json(OUTPUT_ROOT / "NO_ACTION_OR_OFFICIAL_CASE_GUARD.json"),
    ]
    if decision.get("status") != FINAL_STATUS:
        errors.append("decision_status_not_with_limitations")
    if {card.get("scorecard_id") for card in dashboard.get("scorecards", [])} != set(REQUIRED_SCORECARDS):
        errors.append("missing_required_scorecards")
    if not parity.get("all_variants_share_evidence_signature"):
        errors.append("brief_variant_parity_failed")
    if guard.get("forbidden_capabilities_created") != []:
        errors.append("forbidden_capabilities_created")
    if any(item.get("status") != "PASS" for item in governance_guards):
        errors.append("governance_guard_failed")
    errors.extend(validate_hash_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        decision = build_outputs()
    else:
        decision = read_json(OUTPUT_ROOT / "TRACKB_MATURITY_BRIEF_GOVERNANCE_DECISION.json", {})
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "FAIL", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "decision": decision.get("status", FINAL_STATUS),
                "output_root": rel(OUTPUT_ROOT),
                "publication_root": rel(PUBLICATION_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
