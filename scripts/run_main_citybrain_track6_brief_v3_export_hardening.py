"""Track 6 BRIEF v3 export hardening.

Builds a founder-review ready packet from the existing CHECK v1, Event
Fabric v2, Simulation v2, and incident-plan artifacts. This is packet polish
only: no UI polish, no live monitoring, and no official action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_track6_brief_v3_export_hardening"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-track6-brief-v3-export-hardening"

TASK_ID = "MAIN-CITYBRAIN-TRACK6-BRIEF-V3-EXPORT-HARDENING"
PASS_STATUS = "PASS_TRACK6_BRIEF_V3_EXPORT_HARDENING_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_TRACK6_BRIEF_V3_EXPORT_HARDENING"

CHECK_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint0-check-v1-cer-engine-r1"
EVENT_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint1-event-fabric-v2-product-spine"
SIM_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint2-simulation-v2-review-option-engine"
PLAN_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint3-incident-plan-product-loop"
REVIEW_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-sprint4-human-review-pilot-fuel-capture"
FINAL_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-large-sprint-final-reverify-r1"

SOURCE_FILES = {
    "check_v1_engine_report": CHECK_ROOT / "CHECK_V1_ENGINE_REPORT.json",
    "check_v1_trust_gate": CHECK_ROOT / "SPRINT0_INTEGRATED_TRUST_GATE_REPORT.json",
    "event_state_v2": EVENT_ROOT / "EVENT_CURRENT_STATE_V2.json",
    "event_query_smoke": EVENT_ROOT / "EVENT_QUERY_API_SMOKE_REPORT.json",
    "simulation_scenario_catalog_v2": SIM_ROOT / "SIMULATION_SCENARIO_CATALOG_V2.json",
    "simulation_option_comparison": SIM_ROOT / "SIMULATION_OPTION_COMPARISON_REPORT.json",
    "incident_review_packet": PLAN_ROOT / "INCIDENT_REVIEW_PACKET_R1.json",
    "plan_option_set": PLAN_ROOT / "PLAN_OPTION_SET_R1.json",
    "human_review_pilot_decision": REVIEW_ROOT / "HUMAN_REVIEW_PILOT_DECISION.json",
    "epoch4_final_decision": FINAL_ROOT / "EPOCH4_LARGE_SPRINT_FINAL_DECISION.json",
}

SECTION_ORDER = [
    "source_record_appendix",
    "check_v1_summary",
    "simulation_assumptions",
    "event_state",
    "spatial_references",
    "cannot_claim",
    "review_options",
    "limitations",
]

REQUESTED_OUTPUTS = [
    "BRIEF_V3_EXPORT_PACKET.json",
    "BRIEF_V3_EXPORT_PACKET.md",
    "BRIEF_V3_EXPORT_CONTRACT.json",
    "BRIEF_V3_SOURCE_RECORD_APPENDIX.json",
    "BRIEF_V3_CHECK_V1_SUMMARY_BLOCK.json",
    "BRIEF_V3_SIMULATION_ASSUMPTIONS_BLOCK.json",
    "BRIEF_V3_EVENT_STATE_BLOCK.json",
    "BRIEF_V3_SPATIAL_REFERENCES_BLOCK.json",
    "BRIEF_V3_CANNOT_CLAIM_BLOCK.json",
    "BRIEF_V3_REVIEW_OPTIONS_BLOCK.json",
    "BRIEF_V3_LIMITATIONS_BLOCK.json",
    "BRIEF_V3_EXPORT_HARDENING_DECISION.json",
    "LINE_ENDING_REPORT.json",
    "README.md",
]

CANNOT_CLAIM = [
    "No production or public API claim.",
    "No live monitoring, alerting, dispatch, routing, control, enforcement, or automated action.",
    "No official ticket, case, citation, inspection, legal finding, or certified finding is created.",
    "No citywide certified twin or certified physical geometry claim.",
    "No forecast model, learned ranking, counterfactual learner, case-memory learner, or dynamic investigation agent.",
    "No recommendation authority; review options remain human-owned and may be abstained from.",
    "No source record is converted into official truth without CHECK/CER review boundaries.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def load_sources() -> dict[str, Any]:
    return {key: read_json(path, {}) for key, path in SOURCE_FILES.items()}


def source_file_rows() -> list[dict[str, Any]]:
    rows = []
    for key, path in SOURCE_FILES.items():
        rows.append(
            {
                "source_key": key,
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )
    return rows


def source_record_appendix(sources: dict[str, Any]) -> dict[str, Any]:
    event_state = sources["event_state_v2"]
    records = []
    for event in event_state.get("history", []) + event_state.get("active_events", []):
        records.append(
            {
                "source_record_ref": event.get("source_record_ref"),
                "source_event_id": event.get("source_event_id"),
                "source_class": event.get("source_class"),
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "event_family": event.get("event_family"),
                "observed_at": event.get("observed_at"),
                "evidence_refs": unique(event.get("evidence_refs", [])),
                "check_report_refs": unique(event.get("check_report_refs", [])),
                "authority_boundary": event.get("authority_boundary"),
            }
        )
    deduped: dict[str, dict[str, Any]] = {}
    for record in records:
        key = "|".join(
            [
                str(record.get("source_record_ref")),
                str(record.get("source_event_id")),
                str(record.get("event_id")),
            ]
        )
        deduped[key] = record
    source_files = source_file_rows()
    missing = [row["path"] for row in source_files if not row["exists"]]
    return {
        "block_id": "source_record_appendix",
        "status": "PASS" if not missing and deduped else "PASS_WITH_LIMITATIONS",
        "record_count": len(deduped),
        "records": list(deduped.values()),
        "source_artifact_refs": source_files,
        "missing_source_artifacts": missing,
        "truth_boundary": "Source records remain evidence inputs; CHECK/CER boundaries govern claimability.",
    }


def check_v1_summary_block(sources: dict[str, Any]) -> dict[str, Any]:
    report = sources["check_v1_engine_report"]
    trust_gate = sources["check_v1_trust_gate"]
    return {
        "block_id": "check_v1_summary",
        "status": report.get("status", "UNKNOWN"),
        "authority_boundary": report.get("authority_boundary", "review_only_no_action"),
        "report_count": report.get("report_count", 0),
        "covered_rules": report.get("covered_rules", []),
        "claimability_statuses": report.get("claimability_statuses", []),
        "positive_pipeline": trust_gate.get("positive_pipeline", {}),
        "negative_fixture_count": trust_gate.get("negative_fixture_count", 0),
        "negative_fixtures_passed": trust_gate.get("negative_fixtures_passed", False),
        "official_truth_claim_created": report.get("official_truth_claim_created", False),
        "raw_ungrounded_graph_shortcuts_allowed": report.get("raw_ungrounded_graph_shortcuts_allowed", False),
        "source_refs": [rel(SOURCE_FILES["check_v1_engine_report"]), rel(SOURCE_FILES["check_v1_trust_gate"])],
    }


def simulation_assumptions_block(sources: dict[str, Any]) -> dict[str, Any]:
    catalog = sources["simulation_scenario_catalog_v2"]
    comparison = sources["simulation_option_comparison"]
    plan = sources["plan_option_set"]
    scenarios = catalog.get("scenarios", [])
    scenario = scenarios[0] if scenarios else {}
    return {
        "block_id": "simulation_assumptions",
        "status": catalog.get("status", "UNKNOWN"),
        "scenario_id": scenario.get("scenario_id"),
        "event_family": scenario.get("event_family"),
        "source_class": scenario.get("source_class"),
        "baseline": scenario.get("baseline"),
        "assumptions": scenario.get("assumptions", []),
        "limitations": unique([scenario.get("limitations", []), "fixture-only simulation; not a forecast"]),
        "review_options": scenario.get("review_options", []),
        "comparison_status": comparison.get("status", "UNKNOWN"),
        "best_fixture_delta_option": comparison.get("best_fixture_delta_option"),
        "recommendation_authority": bool(comparison.get("recommendation_authority")) or bool(plan.get("recommendation_authority")),
        "abstain_available": bool(comparison.get("abstain_available") or plan.get("abstain_option", {}).get("available")),
        "source_refs": [
            rel(SOURCE_FILES["simulation_scenario_catalog_v2"]),
            rel(SOURCE_FILES["simulation_option_comparison"]),
            rel(SOURCE_FILES["plan_option_set"]),
        ],
    }


def event_state_block(sources: dict[str, Any]) -> dict[str, Any]:
    state = sources["event_state_v2"]
    smoke = sources["event_query_smoke"]
    active_events = []
    for event in state.get("active_events", []):
        active_events.append(
            {
                "event_id": event.get("event_id"),
                "event_type": event.get("event_type"),
                "event_family": event.get("event_family"),
                "review_state": event.get("review_state"),
                "source_record_ref": event.get("source_record_ref"),
                "check_report_refs": event.get("check_report_refs", []),
                "evidence_refs": event.get("evidence_refs", []),
                "authority_boundary": event.get("authority_boundary"),
                "payload_keys": sorted(event.get("payload", {}).keys()),
            }
        )
    return {
        "block_id": "event_state",
        "status": "PASS_WITH_LIMITATIONS" if state.get("active_events") else "BLOCKED",
        "state_id": state.get("state_id"),
        "materialized_at": state.get("materialized_at"),
        "authority_boundary": state.get("authority_boundary", "review_only_no_action"),
        "counts": state.get("counts", {}),
        "active_event_count": len(active_events),
        "active_events": active_events,
        "query_smoke_status": smoke.get("status"),
        "query_types": smoke.get("query_types", []),
        "source_refs": [rel(SOURCE_FILES["event_state_v2"]), rel(SOURCE_FILES["event_query_smoke"])],
    }


def spatial_references_block(sources: dict[str, Any]) -> dict[str, Any]:
    incident = sources["incident_review_packet"]
    event_state = sources["event_state_v2"]
    active_events = event_state.get("active_events", [])
    cer_refs = unique([incident.get("cer_entity_refs", []), [event.get("cer_entity_refs", []) for event in active_events]])
    check_refs = unique([incident.get("check_report_ref"), [event.get("check_report_refs", []) for event in active_events]])
    return {
        "block_id": "spatial_references",
        "status": "PASS_WITH_LIMITATIONS" if cer_refs else "BLOCKED",
        "cer_entity_refs": cer_refs,
        "seg_context_refs": unique(incident.get("seg_context_refs", [])),
        "check_report_refs": check_refs,
        "event_state_ref": incident.get("event_state_ref"),
        "spatial_overlay_kind": "CER/SEG reference only",
        "geometry_certified": False,
        "citywide_twin_claim": False,
        "source_refs": [rel(SOURCE_FILES["incident_review_packet"]), rel(SOURCE_FILES["event_state_v2"])],
    }


def cannot_claim_block() -> dict[str, Any]:
    return {
        "block_id": "cannot_claim",
        "status": "PASS",
        "claims": CANNOT_CLAIM,
        "official_action_created": False,
        "legal_or_certified_finding_created": False,
        "production_live_monitoring_created": False,
        "ui_polish_performed": False,
    }


def review_options_block(sources: dict[str, Any]) -> dict[str, Any]:
    plan = sources["plan_option_set"]
    options = []
    for option in plan.get("options", []):
        options.append(
            {
                "option_id": option.get("option_id"),
                "scenario_id": option.get("scenario_id"),
                "claim_boundary": option.get("claim_boundary"),
                "feasible": option.get("feasible"),
                "metrics": option.get("metrics", {}),
                "assumptions": option.get("assumptions", []),
                "tradeoffs": option.get("tradeoffs", []),
            }
        )
    return {
        "block_id": "review_options",
        "status": "PASS_WITH_LIMITATIONS" if options else "BLOCKED",
        "option_set_id": plan.get("option_set_id"),
        "recommendation_authority": plan.get("recommendation_authority", False),
        "abstain_option": plan.get("abstain_option", {}),
        "options": options,
        "source_refs": [rel(SOURCE_FILES["plan_option_set"])],
    }


def limitations_block(sources: dict[str, Any]) -> dict[str, Any]:
    final = sources["epoch4_final_decision"]
    human_review = sources["human_review_pilot_decision"]
    limitations = unique(
        [
            final.get("limitations", []),
            [
                "Packet polish only; UI polish is intentionally deferred.",
                "Founder-review packet uses local/replay artifacts and existing publications.",
                "Human review pilot sessions remain pending." if human_review.get("human_sessions_pending") else None,
                "Simulation remains fixture-only and not calibrated.",
                "Review options are presentable but not recommendations.",
            ],
        ]
    )
    return {
        "block_id": "limitations",
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": limitations,
        "human_sessions_pending": human_review.get("human_sessions_pending", True),
        "pilot_ready": human_review.get("pilot_ready", False),
        "source_refs": [rel(SOURCE_FILES["human_review_pilot_decision"]), rel(SOURCE_FILES["epoch4_final_decision"])],
    }


def build_sections(sources: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "source_record_appendix": source_record_appendix(sources),
        "check_v1_summary": check_v1_summary_block(sources),
        "simulation_assumptions": simulation_assumptions_block(sources),
        "event_state": event_state_block(sources),
        "spatial_references": spatial_references_block(sources),
        "cannot_claim": cannot_claim_block(),
        "review_options": review_options_block(sources),
        "limitations": limitations_block(sources),
    }


def export_contract() -> dict[str, Any]:
    return {
        "artifact_id": "BRIEF_V3_EXPORT_CONTRACT",
        "schema_version": "main-citybrain.brief_v3.export_contract.v1",
        "status": "PASS",
        "required_section_order": SECTION_ORDER,
        "required_blocks": [
            "source record appendix",
            "CHECK v1 summary block",
            "simulation assumptions block",
            "event state block",
            "spatial references block",
            "cannot-claim block",
            "review options block",
            "limitations block",
        ],
        "export_formats": ["markdown", "json"],
        "local_replay_review_only": True,
        "ui_polish_in_scope": False,
        "non_claim_policy": CANNOT_CLAIM,
    }


def build_packet(sources: dict[str, Any]) -> dict[str, Any]:
    sections = build_sections(sources)
    missing_sources = [
        row["path"]
        for row in sections["source_record_appendix"]["source_artifact_refs"]
        if not row["exists"]
    ]
    blocked_sections = [key for key in SECTION_ORDER if str(sections[key].get("status")) == "BLOCKED"]
    status = PASS_STATUS if not missing_sources and not blocked_sections else BLOCKED_STATUS
    return {
        "artifact_id": "BRIEF_V3_EXPORT_PACKET",
        "schema_version": "main-citybrain.brief_v3.export_packet.v1",
        "task_id": TASK_ID,
        "status": status,
        "generated_at": now_iso(),
        "packet_id": "brief_v3:founder_review:mobility_access_interruption",
        "packet_title": "CityBrain BRIEF v3 Founder Review Packet",
        "export_kind": "local_replay_review_only",
        "parallel_safe": True,
        "section_order": SECTION_ORDER,
        "sections": sections,
        "source_artifact_count": len(sections["source_record_appendix"]["source_artifact_refs"]),
        "source_record_count": sections["source_record_appendix"]["record_count"],
        "official_action_created": False,
        "legal_or_certified_finding_created": False,
        "production_live_monitoring_created": False,
        "ui_polish_performed": False,
        "blocked_sections": blocked_sections,
        "missing_sources": missing_sources,
    }


def bullet_list(values: list[Any]) -> str:
    if not values:
        return "- None declared."
    return "\n".join(f"- {value}" for value in values)


def render_packet_markdown(packet: dict[str, Any]) -> str:
    sections = packet["sections"]
    check = sections["check_v1_summary"]
    simulation = sections["simulation_assumptions"]
    event_state = sections["event_state"]
    spatial = sections["spatial_references"]
    review = sections["review_options"]
    source_appendix = sections["source_record_appendix"]
    limitations = sections["limitations"]

    option_lines = []
    for option in review.get("options", []):
        metrics = ", ".join(f"{key}: {value}" for key, value in option.get("metrics", {}).items())
        option_lines.append(
            f"`{option.get('option_id')}` - feasible: {option.get('feasible')}; metrics: {metrics or 'none'}; boundary: {option.get('claim_boundary')}"
        )

    event_lines = []
    for event in event_state.get("active_events", []):
        event_lines.append(
            f"`{event.get('event_id')}` - {event.get('event_type')} / {event.get('review_state')} from `{event.get('source_record_ref')}`"
        )

    record_lines = []
    for record in source_appendix.get("records", []):
        record_lines.append(
            f"`{record.get('source_record_ref')}` -> `{record.get('event_id')}`; checks: {', '.join(record.get('check_report_refs', [])) or 'none'}"
        )

    artifact_lines = []
    for row in source_appendix.get("source_artifact_refs", []):
        status = "present" if row.get("exists") else "missing"
        artifact_lines.append(f"`{row['path']}` - {status}")

    return f"""# CityBrain BRIEF v3 Export Packet

## Packet Metadata

- Packet: `{packet["packet_id"]}`
- Status: `{packet["status"]}`
- Export kind: `{packet["export_kind"]}`
- Generated at: `{packet["generated_at"]}`
- UI polish performed: `{packet["ui_polish_performed"]}`
- Official action created: `{packet["official_action_created"]}`

## Source Record Appendix

Source records remain evidence inputs and are not converted into official truth.

{bullet_list(record_lines)}

Source artifacts:

{bullet_list(artifact_lines)}

## CHECK v1 Summary

- Status: `{check.get("status")}`
- Authority boundary: `{check.get("authority_boundary")}`
- Report count: `{check.get("report_count")}`
- Covered rules: {", ".join(check.get("covered_rules", []))}
- Negative fixtures passed: `{check.get("negative_fixtures_passed")}`
- Official truth claim created: `{check.get("official_truth_claim_created")}`

## Simulation Assumptions

- Scenario: `{simulation.get("scenario_id")}`
- Baseline: `{simulation.get("baseline")}`
- Best fixture delta option: `{simulation.get("best_fixture_delta_option")}`
- Recommendation authority: `{simulation.get("recommendation_authority")}`
- Abstain available: `{simulation.get("abstain_available")}`

Assumptions:

{bullet_list(simulation.get("assumptions", []))}

## Event State

- State: `{event_state.get("state_id")}`
- Materialized at: `{event_state.get("materialized_at")}`
- Active events: `{event_state.get("active_event_count")}`
- Query smoke status: `{event_state.get("query_smoke_status")}`

{bullet_list(event_lines)}

## Spatial References

- CER entities: {", ".join(f"`{ref}`" for ref in spatial.get("cer_entity_refs", []))}
- SEG context: {", ".join(f"`{ref}`" for ref in spatial.get("seg_context_refs", []))}
- Check refs: {", ".join(f"`{ref}`" for ref in spatial.get("check_report_refs", []))}
- Geometry certified: `{spatial.get("geometry_certified")}`
- Citywide twin claim: `{spatial.get("citywide_twin_claim")}`

## Cannot Claim

{bullet_list(sections["cannot_claim"].get("claims", []))}

## Review Options

- Option set: `{review.get("option_set_id")}`
- Recommendation authority: `{review.get("recommendation_authority")}`
- Abstain option: `{review.get("abstain_option", {}).get("option_id")}`

{bullet_list(option_lines)}

## Limitations

{bullet_list(limitations.get("limitations", []))}
"""


def line_ending_report() -> dict[str, Any]:
    rows = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if (
                path.is_file()
                and path.suffix.lower() in {".md", ".json", ".txt"}
                and path.name not in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}
            ):
                data = path.read_bytes()
                rows.append(
                    {
                        "path": rel(path),
                        "crlf_count": data.count(b"\r\n"),
                        "lf_count": data.count(b"\n"),
                    }
                )
    return {
        "artifact_id": "BRIEF_V3_LINE_ENDING_REPORT",
        "status": "PASS" if all(row["crlf_count"] == 0 for row in rows) else "FAIL",
        "files_checked": len(rows),
        "rows": rows,
    }


def publish_outputs() -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in REQUESTED_OUTPUTS:
        source = OUTPUT_ROOT / name
        if source.exists():
            (PUBLICATION_ROOT / name).write_bytes(source.read_bytes())


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "BRIEF_V3_EXPORT_HARDENING_HASH_MANIFEST",
        "status": "PASS",
        "generated_at": now_iso(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((OUTPUT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest() -> list[str]:
    manifest_path = OUTPUT_ROOT / "HASH_MANIFEST.json"
    if not manifest_path.exists():
        return ["missing:HASH_MANIFEST.json"]
    manifest = read_json(manifest_path, {})
    errors: list[str] = []
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def readme_text(packet: dict[str, Any]) -> str:
    return f"""# Track 6 BRIEF v3 Export Hardening

Status: `{packet["status"]}`

This publication hardens the BRIEF output packet for founder review. It produces matching Markdown and JSON exports plus explicit blocks for source records, CHECK v1, simulation assumptions, event state, spatial refs, cannot-claim boundaries, review options, and limitations.

Boundary: local/replay/review-only packet polish. No UI polish, production/public API, live monitoring, official action, dispatch/control/enforcement, legal/certified finding, forecast model, learned ranking, or autonomous workflow was created.
"""


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    packet = build_packet(sources)
    sections = packet["sections"]

    write_json(OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.json", packet)
    write_text(OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.md", render_packet_markdown(packet))
    write_json(OUTPUT_ROOT / "BRIEF_V3_EXPORT_CONTRACT.json", export_contract())
    write_json(OUTPUT_ROOT / "BRIEF_V3_SOURCE_RECORD_APPENDIX.json", sections["source_record_appendix"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_CHECK_V1_SUMMARY_BLOCK.json", sections["check_v1_summary"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_SIMULATION_ASSUMPTIONS_BLOCK.json", sections["simulation_assumptions"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_EVENT_STATE_BLOCK.json", sections["event_state"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_SPATIAL_REFERENCES_BLOCK.json", sections["spatial_references"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_CANNOT_CLAIM_BLOCK.json", sections["cannot_claim"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_REVIEW_OPTIONS_BLOCK.json", sections["review_options"])
    write_json(OUTPUT_ROOT / "BRIEF_V3_LIMITATIONS_BLOCK.json", sections["limitations"])
    decision = {
        "artifact_id": "BRIEF_V3_EXPORT_HARDENING_DECISION",
        "task_id": TASK_ID,
        "status": packet["status"],
        "packet_ref": "BRIEF_V3_EXPORT_PACKET.json",
        "markdown_export_ref": "BRIEF_V3_EXPORT_PACKET.md",
        "json_export_ref": "BRIEF_V3_EXPORT_PACKET.json",
        "section_order": SECTION_ORDER,
        "missing_sources": packet["missing_sources"],
        "blocked_sections": packet["blocked_sections"],
        "no_ui_polish": True,
        "official_action_created": False,
        "legal_or_certified_finding_created": False,
        "created_at": packet["generated_at"],
    }
    write_json(OUTPUT_ROOT / "BRIEF_V3_EXPORT_HARDENING_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "README.md", readme_text(packet))
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", line_ending_report())
    publish_outputs()
    manifest = write_hash_manifest()
    return {"packet": packet, "decision": decision, "manifest": manifest}


def validate_outputs() -> list[str]:
    errors: list[str] = []
    for name in REQUESTED_OUTPUTS + ["HASH_MANIFEST.json"]:
        path = OUTPUT_ROOT / name
        if not path.exists():
            errors.append(f"missing:{name}")
            continue
        if path.suffix == ".json":
            try:
                read_json(path)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid_json:{name}:{exc}")
    packet = read_json(OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.json", {})
    markdown = (OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.md").read_text(encoding="utf-8") if (OUTPUT_ROOT / "BRIEF_V3_EXPORT_PACKET.md").exists() else ""
    if packet.get("section_order") != SECTION_ORDER:
        errors.append("section_order_mismatch")
    sections = packet.get("sections", {})
    for section in SECTION_ORDER:
        if section not in sections:
            errors.append(f"missing_section:{section}")
    for heading in [
        "## Source Record Appendix",
        "## CHECK v1 Summary",
        "## Simulation Assumptions",
        "## Event State",
        "## Spatial References",
        "## Cannot Claim",
        "## Review Options",
        "## Limitations",
    ]:
        if heading not in markdown:
            errors.append(f"missing_markdown_heading:{heading}")
    if packet.get("ui_polish_performed") is not False:
        errors.append("ui_polish_boundary_failed")
    if packet.get("official_action_created") is not False:
        errors.append("official_action_boundary_failed")
    if sections.get("review_options", {}).get("recommendation_authority") is not False:
        errors.append("recommendation_authority_boundary_failed")
    if sections.get("simulation_assumptions", {}).get("recommendation_authority") is not False:
        errors.append("simulation_recommendation_authority_boundary_failed")
    line_report = read_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", {})
    if line_report.get("status") != "PASS":
        errors.append("line_endings_failed")
    errors.extend(verify_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        build_outputs()
    errors = validate_outputs()
    status = BLOCKED_STATUS if errors else PASS_STATUS
    print(
        json.dumps(
            {
                "status": status,
                "errors": errors,
                "output_root": rel(OUTPUT_ROOT),
                "publication_root": rel(PUBLICATION_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
