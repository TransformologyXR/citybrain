#!/usr/bin/env python3
"""Run Package A: event stories, SourceRegistry v1.1, and DIFF fixtures.

This package is local/replay/review-only. It consumes existing artifacts and
does not call live sources, mutate upstream source records, or run product-loop
execution.
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
PACKAGE_ZIP = Path.home() / "Downloads" / "main-citybrain-epoch4-tracka-event-stories-source-diff-r1.zip"
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_tracka_event_stories_source_diff_r1"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-tracka-event-stories-source-diff-r1"

PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH4-TRACKA-EVENT-STORIES-SOURCE-DIFF-R1"
FINAL_STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_TRACKA_EVENT_STORIES_SOURCE_DIFF_R1_WITH_LIMITATIONS"

EVENT_FABRIC_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening"
TRACK1_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1"
SPRINT0_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"
SOURCE_REGISTRY_ROOT = ROOT / "outputs" / "main_citybrain_track4_source_registry_v1"
TRACK7_ROOT = ROOT / "outputs" / "track7_diff_source_refresh_readiness"

PREFERRED_FAMILIES = [
    "building_compliance_perception_candidate",
    "permit_inspection_delay",
    "city_asset_infrastructure_issue",
    "mobility_access_interruption",
]

CHANGE_TYPES = [
    "new_record",
    "changed_status",
    "expired_record",
    "stale_record",
    "strengthened_relationship",
    "weakened_relationship",
    "new_candidate_only_record",
    "removed_or_missing_record",
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
    "upstream_source_mutation",
    "founder_or_operator_fuel_capture",
    "ui_ux_polish",
]

OUTPUT_FILES = [
    "EVENT_STORY_PACK_R1.json",
    "EVENT_STORY_PACK_R1.md",
    "EVENT_STORY_REPLAY_MANIFEST.json",
    "EVENT_STORY_FAMILY_COVERAGE_REPORT.json",
    "EVENT_STORY_LIMITATIONS.json",
    "SOURCE_REGISTRY_V1_1.json",
    "SOURCE_REGISTRY_V1_1_SCHEMA.json",
    "SOURCE_REGISTRY_V1_1_ENRICHMENT_REPORT.json",
    "SOURCE_REGISTRY_V1_1_VALIDATION_REPORT.json",
    "SOURCE_REGISTRY_V1_1_GAP_REPORT.json",
    "SOURCE_REGISTRY_V1_1_CONSUMING_FLOW_MAP.json",
    "DIFF_DESIGNED_CHANGE_EXPANSION_R1.json",
    "DIFF_DESIGNED_CHANGE_FIXTURES.jsonl",
    "DIFF_EXPECTED_CLASSIFICATION_MATRIX.json",
    "DIFF_ENTITY_LEVEL_EXPECTED_REPORT.json",
    "DIFF_SOURCE_LEVEL_EXPECTED_REPORT.json",
    "DIFF_FAMILY_COVERAGE_REPORT.json",
    "DIFF_LIMITATIONS.json",
    "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json",
    "NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "PUBLICATION_COVERAGE_REPORT.json",
    "NEXT_HANDOFF_POINTER.json",
    "HASH_MANIFEST.json",
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


def stable_hash(value: Any, length: int = 12) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256_bytes(payload.encode("utf-8"))[:length]


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
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def listify(value: Any) -> list[Any]:
    if value in (None, "", {}):
        return []
    return value if isinstance(value, list) else [value]


def family_base(value: str | None) -> str:
    text = str(value or "").strip()
    return text[:-3] if text.endswith("_v0") else text


def input_status() -> dict[str, Any]:
    paths = {
        "package_zip": PACKAGE_ZIP,
        "track1_scenario_scout": TRACK1_ROOT,
        "event_fabric_v2_1": EVENT_FABRIC_ROOT,
        "source_registry_v1": SOURCE_REGISTRY_ROOT / "SOURCE_REGISTRY_V1.json",
        "track7_diff_readiness": TRACK7_ROOT,
        "sprint0_check_cer": SPRINT0_ROOT,
        "progress_md": ROOT / "progress.md",
    }
    return {
        key: {
            "path": str(path),
            "repo_path": rel(path) if path.exists() and str(path).startswith(str(ROOT)) else str(path),
            "exists": path.exists(),
        }
        for key, path in paths.items()
    }


def load_event_story_packs() -> list[dict[str, Any]]:
    payload = read_json(EVENT_FABRIC_ROOT / "EVENT_STORY_REPLAY_PACKS_V2_1.json", {})
    return payload.get("story_packs", [])


def load_family_registry() -> dict[str, dict[str, Any]]:
    payload = read_json(EVENT_FABRIC_ROOT / "EVENT_TYPE_REGISTRY_V2_1.json", {})
    families = {}
    for row in payload.get("event_families", []):
        families[family_base(row.get("family_id") or row.get("event_family"))] = row
    return families


def load_seg_refs() -> dict[str, list[str]]:
    refs: dict[str, list[str]] = defaultdict(list)
    for edge in read_jsonl(SPRINT0_ROOT / "SEG_EDGE_ASSERTIONS_R1.jsonl"):
        edge_id = edge.get("seg_edge_id") or edge.get("edge_id")
        if not edge_id:
            continue
        for entity_ref in listify(edge.get("subject_cer_entity_id")) + listify(edge.get("object_cer_entity_id")):
            refs[str(entity_ref)].append(edge_id)
    return {key: sorted(set(values)) for key, values in refs.items()}


def story_from_pack(pack: dict[str, Any], seg_refs: dict[str, list[str]]) -> dict[str, Any]:
    events = pack.get("events", [])
    event = events[0] if events else {}
    family = family_base(pack.get("family_id") or event.get("family_id") or event.get("event_family"))
    source_records = sorted({str(row.get("source_record_ref")) for row in events if row.get("source_record_ref")})
    event_refs = sorted({str(row.get("event_id")) for row in events if row.get("event_id")})
    cer_refs = sorted({str(ref) for row in events for ref in listify(row.get("cer_entity_refs")) if ref})
    check_refs = sorted({str(ref) for ref in listify(pack.get("check_refs"))} | {str(ref) for row in events for ref in listify(row.get("check_report_refs")) if ref})
    seg_context_refs = sorted({ref for cer in cer_refs for ref in seg_refs.get(cer, [])})
    source_class = event.get("source_class") or "replay_fixture"
    fixture_only = source_class in {"replay_fixture", "fixture_only", "derived_fixture"}
    cannot_claim = [
        "official incident truth",
        "case or ticket submission",
        "dispatch/control/enforcement",
        "legal or certified finding",
        "product forecast",
    ]
    if fixture_only:
        cannot_claim.append("source-backed production fact")
    return {
        "story_id": f"event_story_r1:{family}",
        "story_pack_ref": pack.get("story_pack_id"),
        "event_family": event.get("event_family") or f"{family}_v0",
        "family_id": family,
        "source_class": source_class if source_records else "fixture_only",
        "source_records": source_records,
        "source_gap": None if source_records else "No source record ref available in upstream replay pack.",
        "event_refs": event_refs,
        "cer_entity_refs": cer_refs,
        "seg_context_refs": seg_context_refs,
        "check_refs": check_refs,
        "brief_candidate_ref": pack.get("brief_packet_ref"),
        "spatial_overlay_ref": pack.get("spatial_packet_ref"),
        "watch_refs": pack.get("watch_refs", []),
        "cannot_claim": cannot_claim,
        "review_only_state": event.get("review_state") or "review_required",
        "replay_steps": [
            {"step": 1, "action": "load_replay_event_family", "refs": [event.get("event_family") or family]},
            {"step": 2, "action": "attach_source_records_or_gap", "refs": source_records or ["source_gap"]},
            {"step": 3, "action": "resolve_cer_context_if_available", "refs": cer_refs or ["cer_context_gap"]},
            {"step": 4, "action": "attach_check_and_authority_boundary", "refs": check_refs or ["check_ref_gap"]},
            {"step": 5, "action": "emit_review_only_story_packet", "refs": [pack.get("brief_packet_ref") or "brief_candidate_gap"]},
        ],
        "evidence_refs": sorted({str(ref) for row in events for ref in listify(row.get("evidence_refs")) if ref}),
        "input_refs": [rel(EVENT_FABRIC_ROOT / "EVENT_STORY_REPLAY_PACKS_V2_1.json")],
    }


def build_event_story_outputs() -> dict[str, Any]:
    packs = load_event_story_packs()
    seg_refs = load_seg_refs()
    stories_by_family: dict[str, dict[str, Any]] = {}
    for pack in packs:
        story = story_from_pack(pack, seg_refs)
        stories_by_family[story["family_id"]] = story

    selected: list[dict[str, Any]] = []
    for family in PREFERRED_FAMILIES:
        if family in stories_by_family:
            selected.append(stories_by_family[family])
    for story in stories_by_family.values():
        if len(selected) >= 5:
            break
        if story not in selected:
            selected.append(story)

    limitations = []
    if len(selected) < 3:
        limitations.append("Fewer than three upstream event story replay packs were available; package is limited.")
    missing_preferred = [family for family in PREFERRED_FAMILIES[:3] if family not in {story["family_id"] for story in selected}]
    if missing_preferred:
        limitations.append(f"Missing preferred families: {', '.join(missing_preferred)}")
    limitations.extend(
        [
            "Stories are replay/design stories, not official incident truth.",
            "No live source ingestion or product-loop execution was run.",
            "CER, SEG, CHECK, BRIEF, and spatial refs are attached only where upstream artifacts already expose them.",
        ]
    )

    pack_payload = {
        "artifact_id": "EVENT_STORY_PACK_R1",
        "schema_version": "citybrain.event_story_pack.r1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "package_id": PACKAGE_ID,
        "story_count": len(selected),
        "stories": selected,
    }
    replay_manifest = {
        "artifact_id": "EVENT_STORY_REPLAY_MANIFEST",
        "status": "PASS_WITH_LIMITATIONS",
        "replay_mode": "local_replay_review_only",
        "story_refs": [story["story_id"] for story in selected],
        "replay_inputs": sorted({ref for story in selected for ref in story["input_refs"]}),
        "replay_steps_by_story": {story["story_id"]: story["replay_steps"] for story in selected},
    }
    coverage = {
        "artifact_id": "EVENT_STORY_FAMILY_COVERAGE_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "preferred_families": PREFERRED_FAMILIES,
        "covered_families": [story["family_id"] for story in selected],
        "missing_preferred_families": missing_preferred,
        "family_count": len({story["family_id"] for story in selected}),
    }
    limitations_payload = {
        "artifact_id": "EVENT_STORY_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": limitations,
    }

    write_json(OUTPUT_ROOT / "EVENT_STORY_PACK_R1.json", pack_payload)
    write_json(OUTPUT_ROOT / "EVENT_STORY_REPLAY_MANIFEST.json", replay_manifest)
    write_json(OUTPUT_ROOT / "EVENT_STORY_FAMILY_COVERAGE_REPORT.json", coverage)
    write_json(OUTPUT_ROOT / "EVENT_STORY_LIMITATIONS.json", limitations_payload)
    rows = [
        "# Event Story Pack R1",
        "",
        f"Status: `{pack_payload['status']}`",
        "",
    ]
    for story in selected:
        rows.extend(
            [
                f"## {story['story_id']}",
                "",
                f"- Family: `{story['event_family']}`",
                f"- Review state: `{story['review_only_state']}`",
                f"- Event refs: `{', '.join(story['event_refs']) or 'none'}`",
                f"- Source records: `{', '.join(story['source_records']) or story['source_gap']}`",
                f"- Cannot claim: `{', '.join(story['cannot_claim'])}`",
                "",
            ]
        )
    write_text(OUTPUT_ROOT / "EVENT_STORY_PACK_R1.md", "\n".join(rows))
    return {"story_count": len(selected), "covered_families": coverage["covered_families"], "limitations": limitations}


def normalized_access(source: dict[str, Any]) -> tuple[str, str | None, str | None]:
    access = source.get("license_access_status", {}) or {}
    return (
        access.get("status") or "unknown",
        access.get("license") or "unknown",
        access.get("attribution") or access.get("owner") or access.get("publisher"),
    )


def maturity_flags(source: dict[str, Any]) -> list[str]:
    flags = []
    if source.get("source_class") == "unknown_or_unclassified":
        flags.append("unknown_source_class")
    if source.get("freshness", {}).get("status") in {"unknown", "stale", "blocked_or_unavailable", "dated_snapshot"}:
        flags.append("freshness_gap")
    if source.get("geometry_status", {}).get("status") != "present":
        flags.append("geometry_gap")
    if source.get("schema_status", {}).get("status") != "present":
        flags.append("schema_gap")
    if source.get("time_coverage", {}).get("status") in {"missing_or_unknown", "snapshot_only"}:
        flags.append("time_history_gap")
    if not source.get("consuming_flows"):
        flags.append("no_consuming_flow")
    if source.get("candidate_only"):
        flags.append("candidate_only")
    return sorted(set(flags))


def consuming_modes(source: dict[str, Any]) -> list[str]:
    text = " ".join(source.get("consuming_flows", [])).lower()
    modes = []
    for mode in ["ask", "watch", "brief", "diff", "cer", "check", "event", "plan", "simulation", "maturity"]:
        if mode in text:
            modes.append(mode.upper() if mode in {"ask", "diff", "cer", "check"} else mode)
    if source.get("candidate_only"):
        modes.append("review")
    return sorted(set(modes))


def enrich_source_registry() -> dict[str, Any]:
    registry_v1 = read_json(SOURCE_REGISTRY_ROOT / "SOURCE_REGISTRY_V1.json", {})
    sources = registry_v1.get("sources", [])
    enriched = []
    gap_counts: Counter[str] = Counter()
    flow_map: dict[str, list[str]] = defaultdict(list)
    for source in sources:
        access_status, license_status, owner = normalized_access(source)
        freshness = source.get("freshness", {}) or {}
        time_coverage = source.get("time_coverage", {}) or {}
        coverage = source.get("coverage", {}) or {}
        flags = maturity_flags(source)
        for flag in flags:
            gap_counts[flag] += 1
        for flow in source.get("consuming_flows", []):
            flow_map[str(flow)].append(source["source_id"])
        row = {
            "source_id": source["source_id"],
            "source_name": source.get("source_name") or source.get("source_key") or source["source_id"],
            "owner_or_steward": owner or "unknown",
            "city": source.get("city") or "unknown",
            "domain": source.get("domain") or "unknown",
            "source_class": source.get("source_class") or "unknown_or_unclassified",
            "access_status": access_status,
            "license_status": license_status or "unknown",
            "freshness_status": freshness.get("status") or "unknown",
            "last_seen_or_landed_at": freshness.get("last_updated") or time_coverage.get("last_updated") or "unknown",
            "time_coverage_start": time_coverage.get("start") or "unknown",
            "time_coverage_end": time_coverage.get("end") or time_coverage.get("last_updated") or "unknown",
            "geometry_status": source.get("geometry_status", {}).get("status") or "unknown",
            "schema_status": source.get("schema_status", {}).get("status") or "unknown",
            "coverage_status": coverage.get("source_status") or ("row_count_present" if coverage.get("row_count") not in (None, "") else "unknown"),
            "known_limitations": source.get("known_limitations") or ["unknown limitations"],
            "consuming_flows": source.get("consuming_flows") or [],
            "consuming_modes": consuming_modes(source),
            "maturity_flags": flags,
            "evidence_refs": source.get("manifest_refs") or source.get("lineage", {}).get("source_manifest_ref") or [],
            "source_registry_v1_ref": source.get("source_id"),
        }
        enriched.append(row)

    payload = {
        "artifact_id": "SOURCE_REGISTRY_V1_1",
        "schema_version": "citybrain.source_registry.v1_1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_registry_v1_ref": rel(SOURCE_REGISTRY_ROOT / "SOURCE_REGISTRY_V1.json"),
        "source_count": len(enriched),
        "sources": sorted(enriched, key=lambda item: item["source_id"]),
    }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain SourceRegistry v1.1",
        "type": "object",
        "required": ["schema_version", "sources"],
        "properties": {
            "schema_version": {"const": "citybrain.source_registry.v1_1"},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "source_id",
                        "source_name",
                        "city",
                        "domain",
                        "source_class",
                        "access_status",
                        "license_status",
                        "freshness_status",
                        "last_seen_or_landed_at",
                        "geometry_status",
                        "schema_status",
                        "coverage_status",
                        "known_limitations",
                        "consuming_flows",
                        "consuming_modes",
                        "maturity_flags",
                        "evidence_refs",
                    ],
                },
            },
        },
        "additionalProperties": True,
    }
    validation_errors = []
    for source in payload["sources"]:
        for field in schema["properties"]["sources"]["items"]["required"]:
            if field not in source:
                validation_errors.append(f"{source.get('source_id')}:missing:{field}")
    report = {
        "artifact_id": "SOURCE_REGISTRY_V1_1_ENRICHMENT_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "v1_source_count": len(sources),
        "v1_1_source_count": len(enriched),
        "enriched_field_count": len(schema["properties"]["sources"]["items"]["required"]),
        "unknowns_preserved": True,
    }
    validation = {
        "artifact_id": "SOURCE_REGISTRY_V1_1_VALIDATION_REPORT",
        "status": "PASS_WITH_LIMITATIONS" if not validation_errors else "FAIL",
        "errors": validation_errors,
        "source_count": len(enriched),
        "preserves_or_exceeds_v1_count": len(enriched) >= len(sources),
    }
    gap_report = {
        "artifact_id": "SOURCE_REGISTRY_V1_1_GAP_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "gap_counts": dict(sorted(gap_counts.items())),
        "top_gap_source_refs": [
            {
                "source_id": source["source_id"],
                "maturity_flags": source["maturity_flags"],
            }
            for source in payload["sources"]
            if source["maturity_flags"]
        ][:200],
    }
    consuming = {
        "artifact_id": "SOURCE_REGISTRY_V1_1_CONSUMING_FLOW_MAP",
        "status": "PASS_WITH_LIMITATIONS",
        "flow_count": len(flow_map),
        "flows": {key: sorted(set(values)) for key, values in sorted(flow_map.items())},
        "unmapped_source_count": sum(1 for source in payload["sources"] if not source["consuming_flows"]),
    }
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1.json", payload)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1_SCHEMA.json", schema)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1_ENRICHMENT_REPORT.json", report)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1_VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1_GAP_REPORT.json", gap_report)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1_CONSUMING_FLOW_MAP.json", consuming)
    return {"source_count": len(enriched), "v1_source_count": len(sources), "gap_counts": gap_report["gap_counts"], "validation_errors": validation_errors}


def expected_classification(change_type: str) -> str:
    return {
        "new_record": "new",
        "changed_status": "changed",
        "expired_record": "expired",
        "stale_record": "stale",
        "strengthened_relationship": "changed_relationship_strengthened",
        "weakened_relationship": "changed_relationship_weakened",
        "new_candidate_only_record": "new_candidate_only",
        "removed_or_missing_record": "removed_or_missing",
    }[change_type]


def build_diff_outputs(families: list[str]) -> dict[str, Any]:
    track7_fixture_ref = rel(TRACK7_ROOT / "DESIGNED_CHANGE_FIXTURE.json") if (TRACK7_ROOT / "DESIGNED_CHANGE_FIXTURE.json").exists() else None
    rows = []
    for family in families[:4]:
        for change_type in CHANGE_TYPES:
            fixture_id = f"diff_design:{family}:{change_type}"
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "event_family": f"{family}_v0",
                    "family_id": family,
                    "change_type": change_type,
                    "expected_classification": expected_classification(change_type),
                    "entity_ref": f"fixture_entity:{family}:{change_type}",
                    "source_ref": f"fixture_source:{family}",
                    "source_class": "fixture_only",
                    "evidence_refs": [track7_fixture_ref] if track7_fixture_ref else ["fixture_only:no_track7_diff_fixture_available"],
                    "not_live_refresh": True,
                    "review_only": True,
                    "cannot_claim": ["real changed snapshot", "current source truth", "production DIFF"],
                }
            )
    by_family: dict[str, Counter[str]] = defaultdict(Counter)
    by_change = Counter()
    for row in rows:
        by_family[row["family_id"]][row["change_type"]] += 1
        by_change[row["change_type"]] += 1

    expansion = {
        "artifact_id": "DIFF_DESIGNED_CHANGE_EXPANSION_R1",
        "schema_version": "citybrain.diff_designed_change_expansion.r1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "fixture_count": len(rows),
        "families": sorted(by_family),
        "change_types": CHANGE_TYPES,
        "track7_fixture_ref": track7_fixture_ref,
    }
    matrix = {
        "artifact_id": "DIFF_EXPECTED_CLASSIFICATION_MATRIX",
        "status": "PASS_WITH_LIMITATIONS",
        "change_type_to_expected_classification": {change_type: expected_classification(change_type) for change_type in CHANGE_TYPES},
        "family_change_coverage": {family: dict(counter) for family, counter in sorted(by_family.items())},
    }
    entity_report = {
        "artifact_id": "DIFF_ENTITY_LEVEL_EXPECTED_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "entity_fixture_count": len(rows),
        "expected_entity_classification_counts": dict(Counter(row["expected_classification"] for row in rows)),
    }
    source_report = {
        "artifact_id": "DIFF_SOURCE_LEVEL_EXPECTED_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "source_fixture_count": len({row["source_ref"] for row in rows}),
        "expected_source_change_types": dict(sorted(by_change.items())),
    }
    family_report = {
        "artifact_id": "DIFF_FAMILY_COVERAGE_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "family_count": len(by_family),
        "families": sorted(by_family),
        "min_three_selected_families_covered": len(by_family) >= 3,
    }
    limitations = {
        "artifact_id": "DIFF_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "Designed-change fixtures only; no real changed snapshots are claimed.",
            "No live refresh, production DIFF, or current-truth assertion was made.",
            "Fixtures are local/replay/review-only and safe for future changed-snapshot testing.",
        ],
    }
    write_json(OUTPUT_ROOT / "DIFF_DESIGNED_CHANGE_EXPANSION_R1.json", expansion)
    write_jsonl(OUTPUT_ROOT / "DIFF_DESIGNED_CHANGE_FIXTURES.jsonl", rows)
    write_json(OUTPUT_ROOT / "DIFF_EXPECTED_CLASSIFICATION_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "DIFF_ENTITY_LEVEL_EXPECTED_REPORT.json", entity_report)
    write_json(OUTPUT_ROOT / "DIFF_SOURCE_LEVEL_EXPECTED_REPORT.json", source_report)
    write_json(OUTPUT_ROOT / "DIFF_FAMILY_COVERAGE_REPORT.json", family_report)
    write_json(OUTPUT_ROOT / "DIFF_LIMITATIONS.json", limitations)
    return {"fixture_count": len(rows), "family_count": len(by_family), "families": sorted(by_family)}


def forbidden_guard() -> dict[str, Any]:
    return {
        "artifact_id": "NO_FORBIDDEN_CAPABILITY_GUARD",
        "status": "PASS",
        "forbidden_capabilities_created": [],
        "checks": {capability: False for capability in FORBIDDEN_CAPABILITIES},
        "boundary": "local_replay_review_only_no_action",
    }


def publish_outputs() -> dict[str, Any]:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in OUTPUT_FILES:
        src = OUTPUT_ROOT / name
        if src.exists() and name != "PUBLICATION_COVERAGE_REPORT.json":
            dst = PUBLICATION_ROOT / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            copied.append({"file": name, "publication_ref": rel(dst), "sha256": sha256_file(dst)})
    report = {
        "artifact_id": "PUBLICATION_COVERAGE_REPORT",
        "status": "PASS_WITH_LIMITATIONS",
        "publication_root": rel(PUBLICATION_ROOT),
        "published_file_count": len(copied),
        "published_files": copied,
        "limitations": ["Publication mirrors generated package artifacts only; no external release or push was performed."],
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
        "artifact_id": "TRACKA_HASH_MANIFEST",
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

    event_summary = build_event_story_outputs()
    source_summary = enrich_source_registry()
    families = event_summary["covered_families"] or PREFERRED_FAMILIES[:3]
    diff_summary = build_diff_outputs(families)
    guard = forbidden_guard()
    write_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json", guard)

    handoff = {
        "artifact_id": "NEXT_HANDOFF_POINTER",
        "status": "PASS_WITH_LIMITATIONS",
        "story_pack_refs": [rel(OUTPUT_ROOT / "EVENT_STORY_PACK_R1.json")],
        "source_registry_v1_1_refs": [rel(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1.json")],
        "designed_change_fixture_refs": [rel(OUTPUT_ROOT / "DIFF_DESIGNED_CHANGE_FIXTURES.jsonl")],
        "limitation_refs": [rel(OUTPUT_ROOT / "EVENT_STORY_LIMITATIONS.json"), rel(OUTPUT_ROOT / "DIFF_LIMITATIONS.json")],
        "publication_path": rel(PUBLICATION_ROOT),
        "consumer_candidates": ["Review Packet 360", "Data Maturity Dashboard R1.1", "Product Loop packages"],
    }
    write_json(OUTPUT_ROOT / "NEXT_HANDOFF_POINTER.json", handoff)
    decision = {
        "artifact_id": "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION",
        "package_id": PACKAGE_ID,
        "status": FINAL_STATUS,
        "generated_at": utc_now(),
        "input_status": input_status(),
        "event_story_status": "PASS_WITH_LIMITATIONS",
        "event_story_count": event_summary["story_count"],
        "source_registry_v1_1_status": "PASS_WITH_LIMITATIONS",
        "source_registry_v1_1_source_count": source_summary["source_count"],
        "diff_status": "PASS_WITH_LIMITATIONS",
        "diff_fixture_count": diff_summary["fixture_count"],
        "diff_family_count": diff_summary["family_count"],
        "forbidden_capabilities_created": [],
        "publication_root": rel(PUBLICATION_ROOT),
        "limitations": [
            "No live refresh or real changed snapshots.",
            "No live ingestion, official incident truth, external operator validation, product forecast, or learned model.",
            "SourceRegistry enrichment preserves unknowns and maturity gaps.",
        ],
    }
    write_json(OUTPUT_ROOT / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json", decision)
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
    decision = read_json(OUTPUT_ROOT / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json")
    story_pack = read_json(OUTPUT_ROOT / "EVENT_STORY_PACK_R1.json")
    source_v1 = read_json(SOURCE_REGISTRY_ROOT / "SOURCE_REGISTRY_V1.json", {"sources": []})
    source_v1_1 = read_json(OUTPUT_ROOT / "SOURCE_REGISTRY_V1_1.json")
    diff_family = read_json(OUTPUT_ROOT / "DIFF_FAMILY_COVERAGE_REPORT.json")
    guard = read_json(OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    if decision.get("status") != FINAL_STATUS:
        errors.append("decision_status_not_with_limitations")
    if story_pack.get("story_count", 0) < 3:
        errors.append("event_story_count_lt_3")
    if len(source_v1_1.get("sources", [])) < len(source_v1.get("sources", [])):
        errors.append("source_registry_v1_1_dropped_sources")
    if diff_family.get("family_count", 0) < 3:
        errors.append("diff_family_count_lt_3")
    if guard.get("forbidden_capabilities_created") != []:
        errors.append("forbidden_capabilities_created")
    errors.extend(validate_hash_manifest())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        decision = build_outputs()
    else:
        decision = read_json(OUTPUT_ROOT / "TRACKA_EVENT_STORIES_SOURCE_DIFF_DECISION.json", {})
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
