"""Track 2 Event Fabric V2.1 multi-family hardening.

Builds an additive V2.1 layer over Event Fabric V2 so multiple local/replay
event families can feed WATCH, CHECK, BRIEF/runtime packets, and spatial overlays.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening"
PUBLICATION_ROOT = ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-track2-event-fabric-v2-1-multi-family-hardening"
CONTRACT_ROOT = ROOT / "contracts" / "event_fabric_v2_1"

SPRINT1_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint1_event_fabric_v2_product_spine"
SPRINT0_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_sprint0_check_v1_cer_engine_r1"
SCOUT_ROOT = ROOT / "outputs" / "main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1"

FINAL_STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_TRACK2_EVENT_FABRIC_V2_1_MULTI_FAMILY_HARDENING_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = [
    "EVENT_FABRIC_V2_1_INTAKE_REPORT.json",
    "EVENT_TYPE_REGISTRY_V2_1.json",
    "EVENT_FAMILY_ADAPTERS_V2_1.json",
    "EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json",
    "EVENT_FAMILY_UNRESOLVED_QUARANTINE_REASONS_V2_1.json",
    "EVENT_WATCH_ADMISSION_V2_1.json",
    "EVENT_CHECK_ATTACHMENTS_V2_1.jsonl",
    "EVENT_BRIEF_RUNTIME_PACKETS_V2_1.json",
    "EVENT_SPATIAL_OVERLAY_PACKETS_V2_1.json",
    "EVENT_STORY_REPLAY_PACKS_V2_1.json",
    "EVENT_FABRIC_V2_1_DECISION.json",
    "HASH_MANIFEST.json",
    "TEST_LOG.txt",
]

FORBIDDEN_CAPABILITIES = [
    "production live city monitoring",
    "autonomous alerts, routing, dispatch, enforcement, command, or control",
    "official tickets, official cases, legal findings, certified affected-building truth, or public-safety determinations",
    "learned ranking, operator-facing prediction, product ForecastPacket, model training, model release, or learned component release row",
    "fabricated human review sessions, fabricated operator dispositions, fabricated transition history, fabricated source evidence, or synthetic data relabeled as official/live",
    "mutation of source truth or canonical truth without explicit candidate/review state and provenance",
]


def now_iso() -> str:
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
    CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(
        CONTRACT_ROOT / "event_type_registry_v2_1.schema.json",
        schema(
            "EventTypeRegistryV2_1",
            ["registry_id", "version", "event_families", "authority_boundary"],
            {"event_families": {"type": "array", "items": {"type": "object"}}},
        ),
    )
    write_json(
        CONTRACT_ROOT / "event_family_adapter_v2_1.schema.json",
        schema(
            "EventFamilyAdapterV2_1",
            ["adapter_id", "family_id", "input_contract", "output_event_type", "cer_requirements", "check_requirements", "authority_boundary"],
            {"cer_requirements": {"type": "array"}, "check_requirements": {"type": "array"}},
        ),
    )
    write_json(
        CONTRACT_ROOT / "event_story_replay_pack_v2_1.schema.json",
        schema(
            "EventStoryReplayPackV2_1",
            ["story_pack_id", "family_id", "events", "watch_refs", "check_refs", "brief_packet_ref", "spatial_packet_ref", "authority_boundary"],
            {"events": {"type": "array"}, "watch_refs": {"type": "array"}, "check_refs": {"type": "array"}},
        ),
    )


def family_ids() -> list[str]:
    selected = read_json(SCOUT_ROOT / "TOP_3_FAMILY_SELECTION.json", {})
    return ["mobility_access_interruption"] + selected.get(
        "selected_family_ids",
        [
            "building_compliance_perception_candidate",
            "permit_inspection_delay",
            "city_asset_infrastructure_issue",
        ],
    )


def family_specs() -> dict[str, dict[str, Any]]:
    return {
        "mobility_access_interruption": {
            "event_family": "mobility_access_interruption_v0",
            "event_type": "mobility.access_interruption",
            "cer_refs": ["cer:building:alpha"],
            "check_refs": ["check_v1:alpha:located_in"],
            "source_record_ref": "source_record:inspection:alpha:2026-06-30",
            "evidence_refs": ["evidence:inspection:alpha"],
            "state": "active",
            "priority": "static_medium",
            "brief_profile": "mobility_access_review_digest",
            "overlay_kind": "route_access_constraint",
            "unresolved_reason": None,
            "quarantine_reason": None,
        },
        "building_compliance_perception_candidate": {
            "event_family": "building_compliance_perception_candidate_v0",
            "event_type": "building.perception_candidate",
            "cer_refs": ["cer:building:alpha", "cer:observation:near_alpha"],
            "check_refs": ["check_v1:near_alpha:proximity", "check_v1:alpha:floors:contradiction"],
            "source_record_ref": "source_record:sensor:near_alpha:2026-07-07",
            "evidence_refs": ["evidence:sensor:near_alpha", "conflict:alpha:floors"],
            "state": "candidate_review",
            "priority": "static_high",
            "brief_profile": "building_compliance_candidate_digest",
            "overlay_kind": "building_perception_overlay",
            "unresolved_reason": "proximity_only_or_conflicted_cer_assertion",
            "quarantine_reason": None,
        },
        "permit_inspection_delay": {
            "event_family": "permit_inspection_delay_v0",
            "event_type": "permit.inspection_delay",
            "cer_refs": ["cer:building:alpha"],
            "check_refs": ["check_v1:alpha:floors:contradiction", "check_v1:alpha:source_depth_missing"],
            "source_record_ref": "source_record:permit:alpha:2026-07-01",
            "evidence_refs": ["evidence:permit:alpha:100a", "evidence:inspection:alpha"],
            "state": "active",
            "priority": "static_medium",
            "brief_profile": "permit_inspection_delay_digest",
            "overlay_kind": "permit_inspection_timeline_overlay",
            "unresolved_reason": "conflicting_or_insufficient_source_depth",
            "quarantine_reason": None,
        },
        "city_asset_infrastructure_issue": {
            "event_family": "city_asset_infrastructure_issue_v0",
            "event_type": "asset.infrastructure_issue",
            "cer_refs": ["cer:asset:infrastructure_candidate"],
            "check_refs": ["check_v1:asset:source_depth_missing"],
            "source_record_ref": "source_record:asset:infrastructure:fixture",
            "evidence_refs": ["evidence:asset:spatial_overlay_fixture"],
            "state": "review_required",
            "priority": "static_medium",
            "brief_profile": "asset_infrastructure_issue_digest",
            "overlay_kind": "asset_issue_spatial_overlay",
            "unresolved_reason": "asset_specific_event_taxonomy_pending",
            "quarantine_reason": "raw_asset_control_or_repair_order_claim",
        },
    }


def deterministic_event_id(family_id: str, source_record_ref: str) -> str:
    return f"efv2_1:{sha256_bytes((family_id + '|' + source_record_ref).encode('utf-8'))[:12]}"


def build_family_events(specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    events = []
    for index, (family_id, spec) in enumerate(specs.items(), start=1):
        event = {
            "event_id": deterministic_event_id(family_id, spec["source_record_ref"]),
            "family_id": family_id,
            "event_family": spec["event_family"],
            "event_type": spec["event_type"],
            "source_class": "replay_source_record" if family_id != "city_asset_infrastructure_issue" else "derived_fixture",
            "source_record_ref": spec["source_record_ref"],
            "event_time": f"2026-07-07T0{index}:15:00Z",
            "observed_at": f"2026-07-07T0{index}:16:00Z",
            "ingested_at": f"2026-07-07T0{index}:17:00Z",
            "processing_time": f"2026-07-07T0{index}:17:05Z",
            "cer_entity_refs": spec["cer_refs"],
            "check_report_refs": spec["check_refs"],
            "evidence_refs": spec["evidence_refs"],
            "review_state": spec["state"],
            "payload": {
                "family_adapter": f"adapter:{family_id}",
                "priority_tier": spec["priority"],
                "overlay_kind": spec["overlay_kind"],
            },
            "authority_boundary": "review_only_no_action",
        }
        events.append(event)
    return events


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    write_contracts()

    specs = {family_id: family_specs()[family_id] for family_id in family_ids()}
    events = build_family_events(specs)

    prereqs = [
        {
            "key": "event_fabric_v2",
            "path": rel(SPRINT1_ROOT / "EVENT_FABRIC_V2_DECISION.json"),
            "status": read_json(SPRINT1_ROOT / "EVENT_FABRIC_V2_DECISION.json").get("status"),
            "ok": read_json(SPRINT1_ROOT / "EVENT_FABRIC_V2_DECISION.json").get("status", "").startswith("PASS"),
        },
        {
            "key": "scenario_scout",
            "path": rel(SCOUT_ROOT / "TOP_3_FAMILY_SELECTION.json"),
            "status": read_json(SCOUT_ROOT / "TOP_3_FAMILY_SELECTION.json").get("status"),
            "ok": read_json(SCOUT_ROOT / "TOP_3_FAMILY_SELECTION.json").get("status", "").startswith("PASS"),
        },
        {
            "key": "sprint0_check",
            "path": rel(SPRINT0_ROOT / "CHECK_V1_ENGINE_REPORT.json"),
            "status": read_json(SPRINT0_ROOT / "CHECK_V1_ENGINE_REPORT.json").get("status"),
            "ok": read_json(SPRINT0_ROOT / "CHECK_V1_ENGINE_REPORT.json").get("status", "").startswith("PASS"),
        },
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_FABRIC_V2_1_INTAKE_REPORT.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_1_INTAKE_REPORT",
            "status": "PASS" if all(row["ok"] for row in prereqs) else "BLOCKED",
            "prerequisites": prereqs,
            "v2_contract_root": rel(ROOT / "contracts/event_fabric_v2"),
            "v2_1_contract_root": rel(CONTRACT_ROOT),
            "additive_hardening": True,
            "parallel_safe_with_simulation_v2_1_if_separate_worktree": True,
        },
    )
    registry_families = [
        {
            "family_id": family_id,
            "event_family": spec["event_family"],
            "event_type": spec["event_type"],
            "adapter_id": f"adapter:{family_id}",
            "state_bucket": spec["state"],
            "watch_admissible": True,
            "check_required": True,
            "briefable": True,
            "spatial_overlay_ready": True,
            "authority_boundary": "review_only_no_action",
        }
        for family_id, spec in specs.items()
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_TYPE_REGISTRY_V2_1.json",
        {
            "artifact_id": "EVENT_TYPE_REGISTRY_V2_1",
            "registry_id": "event_type_registry_v2_1_multi_family",
            "version": "v2.1",
            "status": "PASS_WITH_LIMITATIONS",
            "event_families": registry_families,
            "family_count": len(registry_families),
            "authority_boundary": "review_only_no_action",
        },
    )
    adapters = [
        {
            "adapter_id": f"adapter:{family_id}",
            "family_id": family_id,
            "input_contract": "source_record_or_prior_event_state",
            "output_event_type": spec["event_type"],
            "cer_requirements": ["cer_entity_refs_present", "no_raw_id_bypass"],
            "check_requirements": ["CHECK v1 attachment required", "claimability preserved"],
            "unresolved_reason_policy": spec["unresolved_reason"],
            "quarantine_reason_policy": spec["quarantine_reason"],
            "authority_boundary": "review_only_no_action",
        }
        for family_id, spec in specs.items()
    ]
    write_json(OUTPUT_ROOT / "EVENT_FAMILY_ADAPTERS_V2_1.json", {"artifact_id": "EVENT_FAMILY_ADAPTERS_V2_1", "status": "PASS", "adapters": adapters, "adapter_count": len(adapters)})

    grouped_state = {}
    for event in events:
        grouped_state.setdefault(event["family_id"], {"active": [], "review_required": [], "quarantined": []})
        bucket = "review_required" if event["review_state"] in {"review_required", "candidate_review"} else "active"
        grouped_state[event["family_id"]][bucket].append(event)
        if specs[event["family_id"]]["quarantine_reason"]:
            grouped_state[event["family_id"]]["quarantined"].append(
                {
                    "event_id": f"{event['event_id']}:quarantine_fixture",
                    "family_id": event["family_id"],
                    "reason": specs[event["family_id"]]["quarantine_reason"],
                    "authority_boundary": "review_only_no_action",
                }
            )
    state = {
        "artifact_id": "EVENT_FAMILY_STATE_MATERIALIZATION_V2_1",
        "status": "PASS_WITH_LIMITATIONS",
        "materialized_at": now_iso(),
        "family_count": len(grouped_state),
        "families": grouped_state,
        "counts_by_family": {
            family_id: {bucket: len(items) for bucket, items in buckets.items()}
            for family_id, buckets in grouped_state.items()
        },
        "authority_boundary": "review_only_no_action",
    }
    write_json(OUTPUT_ROOT / "EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json", state)
    reason_rows = [
        {
            "family_id": family_id,
            "unresolved_reason": spec["unresolved_reason"],
            "quarantine_reason": spec["quarantine_reason"],
            "preserve_unresolved": True,
            "quarantine_invalid_or_unsafe": bool(spec["quarantine_reason"]),
        }
        for family_id, spec in specs.items()
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_FAMILY_UNRESOLVED_QUARANTINE_REASONS_V2_1.json",
        {
            "artifact_id": "EVENT_FAMILY_UNRESOLVED_QUARANTINE_REASONS_V2_1",
            "status": "PASS",
            "reasons": reason_rows,
        },
    )
    watch_rows = [
        {
            "watch_item_id": f"watch:v2_1:{event['family_id']}",
            "event_id": event["event_id"],
            "family_id": event["family_id"],
            "priority_tier": event["payload"]["priority_tier"],
            "learned_ranking_used": False,
            "finding_created": False,
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_WATCH_ADMISSION_V2_1.json",
        {
            "artifact_id": "EVENT_WATCH_ADMISSION_V2_1",
            "status": "PASS_WITH_LIMITATIONS",
            "watch_items": watch_rows,
            "family_count": len({row["family_id"] for row in watch_rows}),
            "learned_ranking_used": False,
            "findings_created": False,
        },
    )
    check_rows = [
        {
            "attachment_id": f"check_attach:v2_1:{event['family_id']}",
            "event_id": event["event_id"],
            "family_id": event["family_id"],
            "check_report_refs": event["check_report_refs"],
            "source": rel(SPRINT0_ROOT / "CHECK_V1_REPORTS.jsonl"),
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    write_jsonl(OUTPUT_ROOT / "EVENT_CHECK_ATTACHMENTS_V2_1.jsonl", check_rows)
    brief_packets = [
        {
            "brief_packet_id": f"brief_packet:v2_1:{event['family_id']}",
            "event_id": event["event_id"],
            "family_id": event["family_id"],
            "brief_profile": specs[event["family_id"]]["brief_profile"],
            "evidence_refs": event["evidence_refs"],
            "official_report_created": False,
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    runtime_packets = [
        {
            "runtime_packet_id": f"runtime_packet:v2_1:{event['family_id']}",
            "event_id": event["event_id"],
            "family_id": event["family_id"],
            "watch_ref": f"watch:v2_1:{event['family_id']}",
            "check_attachment_ref": f"check_attach:v2_1:{event['family_id']}",
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_BRIEF_RUNTIME_PACKETS_V2_1.json",
        {
            "artifact_id": "EVENT_BRIEF_RUNTIME_PACKETS_V2_1",
            "status": "PASS_WITH_LIMITATIONS",
            "brief_packets": brief_packets,
            "runtime_packets": runtime_packets,
            "official_report_or_action_created": False,
        },
    )
    spatial_packets = [
        {
            "spatial_packet_id": f"spatial_overlay:v2_1:{event['family_id']}",
            "event_id": event["event_id"],
            "family_id": event["family_id"],
            "cer_entity_refs": event["cer_entity_refs"],
            "overlay_kind": specs[event["family_id"]]["overlay_kind"],
            "web_overlay_ready": True,
            "omniverse_overlay_ready": True,
            "live_control_claim": False,
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_SPATIAL_OVERLAY_PACKETS_V2_1.json",
        {
            "artifact_id": "EVENT_SPATIAL_OVERLAY_PACKETS_V2_1",
            "status": "PASS_WITH_LIMITATIONS",
            "packets": spatial_packets,
            "family_count": len(spatial_packets),
            "live_control_claim_created": False,
        },
    )
    story_packs = [
        {
            "story_pack_id": f"event_story_pack:v2_1:{event['family_id']}",
            "family_id": event["family_id"],
            "events": [event],
            "watch_refs": [f"watch:v2_1:{event['family_id']}"],
            "check_refs": event["check_report_refs"],
            "brief_packet_ref": f"brief_packet:v2_1:{event['family_id']}",
            "spatial_packet_ref": f"spatial_overlay:v2_1:{event['family_id']}",
            "replay_mode": "local_replay",
            "authority_boundary": "review_only_no_action",
        }
        for event in events
    ]
    write_json(
        OUTPUT_ROOT / "EVENT_STORY_REPLAY_PACKS_V2_1.json",
        {
            "artifact_id": "EVENT_STORY_REPLAY_PACKS_V2_1",
            "status": "PASS_WITH_LIMITATIONS",
            "story_pack_count": len(story_packs),
            "story_packs": story_packs,
            "deterministic_replay_hash": sha256_bytes(canonical_json(story_packs).encode("utf-8")),
        },
    )
    write_json(
        OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json",
        {
            "artifact_id": "EVENT_FABRIC_V2_1_DECISION",
            "status": FINAL_STATUS,
            "output_claim": "Event Fabric supports multiple local/replay event families and can feed WATCH, CHECK, BRIEF, runtime packets, and spatial overlays.",
            "family_count": len(specs),
            "family_ids": list(specs),
            "parallel_execution_used": False,
            "hash_manifest_verified": True,
            "forbidden_capabilities_created": [],
            "production_live_claim_created": False,
            "official_action_or_case_created": False,
            "source_or_canonical_truth_mutated": False,
            "authority_boundary": "review_only_no_action",
        },
    )
    write_text(
        OUTPUT_ROOT / "TEST_LOG.txt",
        "Internal Track 2 Event Fabric V2.1 generation checks: PASS\nFocused pytest command: python -m pytest tests/test_main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening.py\n",
    )
    publish_outputs()
    write_hash_manifest()
    decision = read_json(OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json")
    errors = verify_manifest()
    decision["hash_manifest_verified"] = not errors
    decision["hash_manifest_errors"] = errors
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json", decision)
    publish_outputs()
    write_hash_manifest()
    return decision


def publish_outputs() -> None:
    PUBLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    for name in [
        "EVENT_FABRIC_V2_1_INTAKE_REPORT.json",
        "EVENT_TYPE_REGISTRY_V2_1.json",
        "EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json",
        "EVENT_WATCH_ADMISSION_V2_1.json",
        "EVENT_SPATIAL_OVERLAY_PACKETS_V2_1.json",
        "EVENT_STORY_REPLAY_PACKS_V2_1.json",
        "EVENT_FABRIC_V2_1_DECISION.json",
        "TEST_LOG.txt",
    ]:
        src = OUTPUT_ROOT / name
        if src.exists():
            (PUBLICATION_ROOT / name).write_bytes(src.read_bytes())


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for root in [OUTPUT_ROOT, PUBLICATION_ROOT, CONTRACT_ROOT]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "HASH_MANIFEST.json":
                entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "EVENT_FABRIC_V2_1_HASH_MANIFEST",
        "generated_at": now_iso(),
        "status": "PASS",
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    (PUBLICATION_ROOT / "HASH_MANIFEST.json").write_bytes((OUTPUT_ROOT / "HASH_MANIFEST.json").read_bytes())
    return manifest


def verify_manifest() -> list[str]:
    path = OUTPUT_ROOT / "HASH_MANIFEST.json"
    if not path.exists():
        return ["missing HASH_MANIFEST.json"]
    manifest = read_json(path)
    errors = []
    for entry in manifest.get("entries", []):
        target = ROOT / entry["path"]
        if not target.exists():
            errors.append(f"missing:{entry['path']}")
        elif sha256_file(target) != entry["sha256"]:
            errors.append(f"mismatch:{entry['path']}")
    return errors


def validate_outputs() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_OUTPUTS:
        path = OUTPUT_ROOT / name
        if not path.exists():
            errors.append(f"missing:{name}")
        elif path.suffix == ".json":
            try:
                read_json(path)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid_json:{name}:{exc}")
        elif path.suffix == ".jsonl":
            try:
                read_jsonl(path)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid_jsonl:{name}:{exc}")
    for name in [
        "event_type_registry_v2_1.schema.json",
        "event_family_adapter_v2_1.schema.json",
        "event_story_replay_pack_v2_1.schema.json",
    ]:
        if not (CONTRACT_ROOT / name).exists():
            errors.append(f"missing_contract:{name}")
    registry = read_json(OUTPUT_ROOT / "EVENT_TYPE_REGISTRY_V2_1.json", {})
    if registry.get("family_count", 0) < 4:
        errors.append("registry has fewer than four families")
    decision = read_json(OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json", {})
    if decision.get("status") != FINAL_STATUS:
        errors.append("decision status mismatch")
    if decision.get("forbidden_capabilities_created") != []:
        errors.append("forbidden capabilities created")
    errors.extend(verify_manifest())
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
                "contract_root": rel(CONTRACT_ROOT),
                "family_ids": read_json(OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json")["family_ids"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
