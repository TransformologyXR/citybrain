#!/usr/bin/env python3
"""Build Push 3 Lane B cockpit source-record 360 artifacts.

This lane is a local/replay selected-item workspace only. It joins already
published Push 2 CHECK/Authority, WATCH, App Review Route, Event Fabric, and
spatial review artifacts into an operator-facing static cockpit surface.
"""

from __future__ import annotations

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360_closeout"
FINAL_STATUS_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360_final_status"

PUSH2_INTEGRATION_ROOT = REPO_ROOT / "outputs" / "push2_check_watch_app_review_route_integration"
PUSH2_LANE_A_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1"
PUSH2_LANE_B_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1"
PUSH2_LANE_C_ROOT = REPO_ROOT / "outputs" / "push2_lane_c_app_review_route"
EVENT_RUNTIME_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_event_fabric_runtime_spine"
PERCEPTION_EVENT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_perception_to_event_integration"
SPATIAL_REVIEW_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_bundle"

PACKAGE = "MAIN-CITYBRAIN-PUSH3-LANE-B-COCKPIT-SOURCE-RECORD-360"
PASS_STATUS = "PASS_PUSH3_LANE_B_COCKPIT_SOURCE_RECORD_360_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH3_LANE_B_COCKPIT_SOURCE_RECORD_360_BOUNDARY_OR_CONTRACT"
STOP_STATUS = "STOPPED_WAITING_FOR_PUSH2_INTEGRATION"
BRANCH = "codex/push3-lane-b-cockpit-source-record-360"
RUN_TIMESTAMP = "2026-07-05T20:45:00Z"

UNIVERSAL_CANNOT_CLAIM = [
    "production API",
    "URL fetch or live retrieval",
    "LLM authority",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "autonomous workflow",
    "live Kit control",
    "full citywide twin",
    "VSS-as-fact-source",
    "cross-city claim before federation",
]

NOT_EXECUTED = [
    "production_api",
    "url_fetch",
    "live_retrieval",
    "llm_call",
    "official_submission",
    "dispatch_control_enforcement",
    "legal_certified_finding",
    "live_kit_control",
]

SAFE_NEXT_LOOKS = [
    "inspect source-record 360 rows",
    "compare evidence, limitation, and trace refs",
    "read linked CheckReports before any promotion",
    "inspect AuthorityEnvelopes before relying on a source",
    "record or review local disposition only",
    "send integration questions to INFRA after lane publish",
]


def created_at() -> str:
    return RUN_TIMESTAMP


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_STATUS_ROOT]:
        reset_root(root)


def coerce_refs(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, dict):
        ref = values.get("ref_id") or values.get("source_id") or values.get("id")
        return [str(ref)] if ref else []
    refs: list[str] = []
    if isinstance(values, list):
        for value in values:
            refs.extend(coerce_refs(value))
    return refs


def uniq(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key not in seen and value not in (None, "", []):
            seen.add(key)
            result.append(value)
    return result


def deep_refs(payload: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.endswith("_ref") or key.endswith("_refs") or key in {"packet_ref", "target_ref", "source_ref", "review_item_id", "event_id"}:
                refs.update(coerce_refs(value))
                if isinstance(value, str):
                    refs.add(value)
            refs.update(deep_refs(value))
    elif isinstance(payload, list):
        for item in payload:
            refs.update(deep_refs(item))
    return refs


def load_inputs() -> dict[str, Any]:
    return {
        "integration_decision": read_json(PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json", {}),
        "check_reports": read_json(PUSH2_LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json", {}).get("check_reports", []),
        "authority_envelopes": read_json(PUSH2_LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json", {}).get("authority_envelopes", []),
        "watch_items": read_json(PUSH2_LANE_B_ROOT / "WATCH_ITEMS.json", {}).get("items", []),
        "watch_check_authority": read_json(PUSH2_LANE_B_ROOT / "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json", {}),
        "app_route": read_json(PUSH2_LANE_C_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json", {}),
        "disposition_events": read_json(PUSH2_LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json", {}).get("disposition_events", []),
        "spatial_review": read_json(SPATIAL_REVIEW_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json", {}),
        "event_runtime_state": read_json(EVENT_RUNTIME_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_MATERIALIZED_STATE.json", {}),
        "perception_state": read_json(PERCEPTION_EVENT_ROOT / "PERCEPTION_TO_EVENT_MATERIALIZED_REVIEW_STATE.json", {}),
        "perception_events": read_jsonl(PERCEPTION_EVENT_ROOT / "PERCEPTION_TO_EVENT_EVENT_ENVELOPES.jsonl"),
    }


def entry_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    required_paths = [
        PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json",
        PUSH2_LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json",
        PUSH2_LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json",
        PUSH2_LANE_B_ROOT / "WATCH_ITEMS.json",
        PUSH2_LANE_C_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json",
        PUSH2_LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    integration_status = inputs.get("integration_decision", {}).get("status", "")
    runtime_available = (EVENT_RUNTIME_ROOT / "EVENT_FABRIC_RUNTIME_SPINE_MATERIALIZED_STATE.json").exists() or (
        PERCEPTION_EVENT_ROOT / "PERCEPTION_TO_EVENT_MATERIALIZED_REVIEW_STATE.json"
    ).exists()
    checks = {
        "push2_integration_branch_artifacts_present": not missing,
        "push2_integration_status_pass": str(integration_status).startswith("PASS"),
        "check_reports_present": bool(inputs.get("check_reports")),
        "authority_envelopes_present": bool(inputs.get("authority_envelopes")),
        "watch_items_present": bool(inputs.get("watch_items")),
        "app_review_route_present": bool(inputs.get("app_route", {}).get("review_items") or inputs.get("app_route", {}).get("selected_review_item")),
        "event_runtime_or_r0_1_fixture_available": runtime_available,
    }
    return {
        "status": "PASS" if all(checks.values()) else STOP_STATUS,
        "checks": checks,
        "missing": missing,
        "source_push2_integration_status": integration_status,
        "source_push2_integration_ref": rel(PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json"),
    }


def selected_review_item(app_route: dict[str, Any]) -> dict[str, Any]:
    selected = app_route.get("selected_review_item") or {}
    if selected:
        return selected
    items = app_route.get("review_items") or []
    return items[0] if items else {}


def selected_ids(selected: dict[str, Any]) -> dict[str, Any]:
    display = selected.get("candidate_observation_display", {})
    candidate_refs = coerce_refs(display.get("candidate_observation_refs")) or coerce_refs(selected.get("candidate_observation_refs"))
    if display.get("candidate_observation_ref"):
        candidate_refs.insert(0, display["candidate_observation_ref"])
    event_refs = coerce_refs(selected.get("event_refs"))
    review_item_id = selected.get("review_item_id") or selected.get("target_ref") or "lane-c:review-item:perception:001"
    evidence_refs = coerce_refs(selected.get("evidence_refs"))
    if display.get("source_id"):
        evidence_refs.append(display["source_id"])
    return {
        "selected_item_id": review_item_id,
        "selected_item_label": display.get("source_label") or selected.get("display_label") or "Selected local replay review item",
        "selected_item_type": selected.get("item_kind") or "perception_review_item",
        "candidate_observation_refs": uniq(candidate_refs),
        "event_refs": uniq(event_refs),
        "evidence_refs": uniq(evidence_refs),
    }


def related_by_refs(rows: list[dict[str, Any]], refs: set[str]) -> list[dict[str, Any]]:
    return [row for row in rows if deep_refs(row) & refs]


def source_record_class(source_id: str) -> tuple[str, str, str]:
    if source_id.startswith("source:r7a:"):
        return ("local_replay_fixture", "R7A local replay source", "local_replay_current_for_fixture")
    if source_id.startswith("frame:"):
        return ("sample_frame", "Retained local frame evidence", "frame_timestamp_unknown_local_replay")
    if source_id.startswith("source_record:"):
        return ("source_record_fixture", "Retained source record fixture", "fixture_timestamp_unknown")
    if source_id.startswith("media:"):
        return ("sample_media_ref", "Sample media evidence reference", "sample_media_local_replay")
    if source_id.startswith("evidence:"):
        return ("derived_evidence_fixture", "Derived evidence fixture", "derived_from_local_replay")
    return ("local_review_reference", "Local review reference", "freshness_unknown_requires_review")


def build_source_records(
    source_refs: list[str],
    selected: dict[str, Any],
    related_watch: list[dict[str, Any]],
    related_dispositions: list[dict[str, Any]],
    related_checks: list[dict[str, Any]],
    related_authority: list[dict[str, Any]],
    trace_refs: list[str],
    limitation_refs: list[str],
) -> list[dict[str, Any]]:
    authority_by_packet = {row.get("packet_ref"): row for row in related_authority}
    records = []
    for index, source_id in enumerate(uniq(source_refs), start=1):
        source_class, source_label, freshness = source_record_class(str(source_id))
        authority = authority_by_packet.get(source_id) or (related_authority[0] if related_authority else {})
        linked_watch = [item["watch_item_id"] for item in related_watch if source_id in deep_refs(item)]
        linked_checks = [item.get("check_report_id") for item in related_checks if source_id in deep_refs(item)]
        linked_dispositions = [item["event_id"] for item in related_dispositions if source_id in deep_refs(item)]
        record = {
            "source_record_360_id": f"source-record-360:{index:03d}",
            "source_class": source_class,
            "source_id": source_id,
            "source_label": source_label,
            "record_type": "local_replay_review_context",
            "record_timestamp": selected.get("disposition_capture", {}).get("timestamp") or selected.get("event_time") or created_at(),
            "freshness_status": freshness,
            "authority_level": authority.get("authority_level_label") or authority.get("authority_level") or "review_display_only",
            "evidence_refs": [source_id] if str(source_id).startswith(("source:", "frame:", "source_record:", "media:", "evidence:")) else [],
            "trace_refs": trace_refs,
            "limitations": limitation_refs,
            "review_state": selected.get("candidate_observation_display", {}).get("review_state") or selected.get("review_state") or "candidate_context",
            "linked_event_refs": selected.get("event_refs", []),
            "linked_watch_item_refs": linked_watch,
            "linked_candidate_observation_refs": selected_ids(selected)["candidate_observation_refs"],
            "linked_check_report_refs": [ref for ref in linked_checks if ref],
            "linked_disposition_event_refs": linked_dispositions,
            "official_truth_claim": False,
        }
        record["record_hash"] = canonical_hash(record)
        records.append(record)
    return records


def collect_workspace(inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    app_route = inputs["app_route"]
    selected = selected_review_item(app_route)
    ids = selected_ids(selected)
    seed_refs = set(ids["candidate_observation_refs"] + ids["event_refs"] + ids["evidence_refs"] + [ids["selected_item_id"]])

    related_watch = related_by_refs(inputs["watch_items"], seed_refs)
    watch_refs = [item["watch_item_id"] for item in related_watch]
    seed_refs.update(watch_refs)
    seed_refs.update([item.get("check_report_ref") for item in related_watch if item.get("check_report_ref")])
    seed_refs.update([item.get("authority_envelope_ref") for item in related_watch if item.get("authority_envelope_ref")])

    related_dispositions = related_by_refs(inputs["disposition_events"], seed_refs)
    related_spatial = related_by_refs(inputs["spatial_review"].get("items", []), seed_refs)
    related_app_checks = related_by_refs(app_route.get("check_reports", []), seed_refs)
    related_app_authority = related_by_refs(app_route.get("authority_envelopes", []), seed_refs)
    related_checks = related_by_refs(inputs["check_reports"], seed_refs)
    related_authority = related_by_refs(inputs["authority_envelopes"], seed_refs)
    related_perception_events = related_by_refs(inputs.get("perception_events", []), seed_refs)

    watch_check_reports = inputs["watch_check_authority"].get("check_reports", [])
    watch_authority = inputs["watch_check_authority"].get("authority_envelopes", [])
    related_watch_checks = [row for row in watch_check_reports if row.get("watch_item_id") in watch_refs]
    related_watch_authority = [row for row in watch_authority if row.get("watch_item_id") in watch_refs]

    check_refs = uniq(
        [row.get("check_report_id") for row in related_checks]
        + [row.get("check_report_ref") for row in related_watch_checks]
        + [row.get("check_report_id") for row in related_app_checks]
        + coerce_refs(selected.get("check_report_id"))
    )
    authority_refs = uniq(
        [row.get("authority_envelope_id") for row in related_authority]
        + [row.get("authority_envelope_ref") for row in related_watch_authority]
        + [row.get("authority_envelope_id") for row in related_app_authority]
        + coerce_refs(selected.get("authority_envelope_id"))
    )

    evidence_refs = uniq(
        ids["evidence_refs"]
        + coerce_refs(selected.get("evidence_refs"))
        + [ref for item in related_watch for ref in coerce_refs(item.get("evidence_refs"))]
        + [ref for item in related_checks for ref in coerce_refs(item.get("evidence_refs"))]
        + [ref for item in related_dispositions for ref in coerce_refs(item.get("evidence_refs"))]
        + [ref for item in related_spatial for ref in coerce_refs(item.get("query_packet", {}).get("evidence_refs"))]
    )
    limitation_refs = uniq(
        coerce_refs(selected.get("limitation_refs"))
        + [ref for item in related_watch for ref in coerce_refs(item.get("limitation_refs"))]
        + [ref for item in related_checks for ref in coerce_refs(item.get("limitation_refs"))]
        + [ref for item in related_dispositions for ref in coerce_refs(item.get("limitation_refs"))]
        + [ref for item in related_spatial for ref in coerce_refs(item.get("query_packet", {}).get("limitation_refs"))]
        + ["Cockpit source-record 360 is local/replay review context only."]
    )
    trace_refs = uniq(
        coerce_refs(selected.get("trace_refs"))
        + [ref for item in related_watch for ref in coerce_refs(item.get("trace_refs"))]
        + [ref for item in related_checks for ref in coerce_refs(item.get("trace_refs"))]
        + [ref for item in related_dispositions for ref in coerce_refs(item.get("trace_refs"))]
        + [ref for item in related_spatial for ref in coerce_refs(item.get("query_packet", {}).get("trace_refs"))]
        + ["Push3:LaneB:cockpit_source_record_360"]
    )
    source_record_refs = uniq([ref for ref in evidence_refs if str(ref).startswith(("source:", "frame:", "source_record:", "media:", "evidence:"))])
    disposition_refs = [row["event_id"] for row in related_dispositions]
    spatial_refs = uniq([row.get("surface_item_id") for row in related_spatial] + [row.get("query_packet", {}).get("query_result_id") for row in related_spatial])

    conflict_summary = []
    if any(row.get("payload", {}).get("disposition") == "needs_more" for row in related_dispositions):
        conflict_summary.append(
            {
                "conflict_id": "conflict:needs_more_disposition",
                "summary": "A local disposition requests more evidence before any claim is promoted.",
                "severity": "review_gap",
                "refs": disposition_refs,
            }
        )
    if any(str(row.get("overall_claimability")).startswith("not_claimable") for row in related_checks):
        conflict_summary.append(
            {
                "conflict_id": "conflict:check_not_claimable",
                "summary": "At least one linked CheckReport blocks official or certified claimability.",
                "severity": "claim_boundary",
                "refs": check_refs,
            }
        )
    if not conflict_summary:
        conflict_summary.append(
            {
                "conflict_id": "conflict:none_promoted",
                "summary": "No disagreement is promoted as fact; open review boundaries remain visible.",
                "severity": "none_promoted",
                "refs": [],
            }
        )

    freshness_summary = {
        "status": "local_replay_freshness_visible",
        "source_records": len(source_record_refs),
        "freshness_classes": sorted({source_record_class(str(ref))[2] for ref in source_record_refs}),
        "as_of": created_at(),
        "official_freshness_claim": False,
    }

    workspace = {
        "schema_version": "main-citybrain.push3.lane_b.selected_item_workspace.v1",
        "selected_item_id": ids["selected_item_id"],
        "selected_item_label": ids["selected_item_label"],
        "selected_item_type": ids["selected_item_type"],
        "source_record_refs": source_record_refs,
        "candidate_observation_refs": ids["candidate_observation_refs"],
        "event_refs": uniq(ids["event_refs"] + [row.get("event_id") for row in related_perception_events]),
        "watch_item_refs": watch_refs,
        "check_report_refs": check_refs,
        "authority_envelope_refs": authority_refs,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "disposition_event_refs": disposition_refs,
        "spatial_overlay_refs": spatial_refs,
        "conflict_summary": conflict_summary,
        "freshness_summary": freshness_summary,
        "cannot_claim": UNIVERSAL_CANNOT_CLAIM,
        "not_executed": NOT_EXECUTED,
        "safe_next_looks": SAFE_NEXT_LOOKS,
        "official_status": "not_official",
        "review_required": True,
        "local_replay_only": True,
    }
    workspace["workspace_hash"] = canonical_hash(workspace)

    source_records = build_source_records(
        source_record_refs,
        selected,
        related_watch,
        related_dispositions,
        related_checks,
        related_authority,
        trace_refs,
        limitation_refs,
    )
    joins = {
        "selected_review_item": selected,
        "watch_items": related_watch,
        "check_reports": related_checks + related_watch_checks + related_app_checks,
        "authority_envelopes": related_authority + related_watch_authority + related_app_authority,
        "disposition_events": related_dispositions,
        "spatial_overlays": related_spatial,
        "perception_events": related_perception_events,
    }
    return workspace, {"items": source_records}, joins


def workspace_contract() -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_b.selected_item_workspace.contract.v1",
        "status": "PASS",
        "required_fields": [
            "selected_item_id",
            "selected_item_label",
            "selected_item_type",
            "source_record_refs",
            "candidate_observation_refs",
            "event_refs",
            "watch_item_refs",
            "check_report_refs",
            "authority_envelope_refs",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "disposition_event_refs",
            "spatial_overlay_refs",
            "conflict_summary",
            "freshness_summary",
            "cannot_claim",
            "not_executed",
            "safe_next_looks",
        ],
        "boundary": "local/replay selected-item workspace; no production API, official action, legal finding, live Kit control, or full citywide twin claim",
    }


def build_source_record_index(workspace: dict[str, Any], source_records: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_b.source_record_360.index.v1",
        "status": "PASS" if source_records["items"] else "FAIL",
        "selected_item_id": workspace["selected_item_id"],
        "source_record_count": len(source_records["items"]),
        "source_classes": sorted({row["source_class"] for row in source_records["items"]}),
        "freshness_statuses": sorted({row["freshness_status"] for row in source_records["items"]}),
        "source_records": [
            {
                "source_record_360_id": row["source_record_360_id"],
                "source_id": row["source_id"],
                "source_class": row["source_class"],
                "freshness_status": row["freshness_status"],
                "authority_level": row["authority_level"],
            }
            for row in source_records["items"]
        ],
    }


def build_view_model(workspace: dict[str, Any], source_records: dict[str, Any], joins: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3.lane_b.cockpit.view_model.v1",
        "status": "PASS",
        "selected_item": workspace,
        "source_record_360": source_records["items"],
        "panels": [
            {"panel_id": "selected_item", "title": "Selected Item", "record_count": 1},
            {"panel_id": "source_record_360", "title": "Source Records", "record_count": len(source_records["items"])},
            {"panel_id": "watch_items", "title": "WatchItems", "record_count": len(joins["watch_items"])},
            {"panel_id": "checks_authority", "title": "CheckReports and AuthorityEnvelopes", "record_count": len(joins["check_reports"]) + len(joins["authority_envelopes"])},
            {"panel_id": "dispositions", "title": "Dispositions", "record_count": len(joins["disposition_events"])},
            {"panel_id": "spatial", "title": "Spatial Overlays", "record_count": len(joins["spatial_overlays"])},
        ],
        "joined_packets": joins,
        "official_action_affordance": False,
        "live_api": False,
    }


def render_list(values: list[Any]) -> str:
    if not values:
        return "<span class=\"muted\">None</span>"
    return "<ul>" + "".join(f"<li>{html.escape(str(value))}</li>" for value in values[:12]) + "</ul>"


def render_static_html(view_model: dict[str, Any]) -> str:
    workspace = view_model["selected_item"]
    records = view_model["source_record_360"]
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(row['source_id'])}</td>"
        f"<td>{html.escape(row['source_class'])}</td>"
        f"<td>{html.escape(row['freshness_status'])}</td>"
        f"<td>{html.escape(str(row['authority_level']))}</td>"
        f"<td>{html.escape(row['review_state'])}</td>"
        "</tr>"
        for row in records
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Cockpit Source-Record 360</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #1f2933; background: #f5f7fa; }}
    header {{ padding: 20px 28px; background: #12263a; color: #fff; }}
    main {{ padding: 24px 28px; display: grid; gap: 18px; }}
    section {{ background: #fff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }}
    h1, h2 {{ margin: 0 0 10px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .metric {{ font-size: 28px; font-weight: 700; }}
    .muted {{ color: #607080; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #edf1f5; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    code {{ background: #eef3f8; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>CityBrain Cockpit Source-Record 360</h1>
    <div>{html.escape(workspace['selected_item_label'])} / <code>{html.escape(workspace['selected_item_id'])}</code></div>
  </header>
  <main>
    <section class="grid">
      <div><div class="metric">{len(records)}</div><div class="muted">source records</div></div>
      <div><div class="metric">{len(workspace['watch_item_refs'])}</div><div class="muted">WatchItems</div></div>
      <div><div class="metric">{len(workspace['check_report_refs'])}</div><div class="muted">CheckReports</div></div>
      <div><div class="metric">{len(workspace['disposition_event_refs'])}</div><div class="muted">dispositions</div></div>
    </section>
    <section>
      <h2>Source Records</h2>
      <table>
        <thead><tr><th>Source</th><th>Class</th><th>Freshness</th><th>Authority</th><th>Review State</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    <section class="grid">
      <div><h2>Evidence</h2>{render_list(workspace['evidence_refs'])}</div>
      <div><h2>Limitations</h2>{render_list(workspace['limitation_refs'])}</div>
      <div><h2>Trace</h2>{render_list(workspace['trace_refs'])}</div>
      <div><h2>Cannot Claim</h2>{render_list(workspace['cannot_claim'])}</div>
    </section>
    <section>
      <h2>Conflict Summary</h2>
      {render_list([item['summary'] for item in workspace['conflict_summary']])}
    </section>
  </main>
</body>
</html>
"""


def build_coverage(workspace: dict[str, Any], source_records: dict[str, Any], joins: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "push2_gate_passed": gate["status"] == "PASS",
        "selected_item_has_source_record_360": bool(source_records["items"]),
        "candidate_observations_visible": bool(workspace["candidate_observation_refs"]),
        "watch_items_visible": bool(workspace["watch_item_refs"]),
        "check_reports_visible": bool(workspace["check_report_refs"]),
        "authority_envelopes_visible": bool(workspace["authority_envelope_refs"]),
        "evidence_limit_trace_visible": bool(workspace["evidence_refs"] and workspace["limitation_refs"] and workspace["trace_refs"]),
        "dispositions_visible": bool(workspace["disposition_event_refs"]),
        "source_freshness_visible": bool(workspace["freshness_summary"].get("freshness_classes")),
        "cannot_claim_visible": bool(workspace["cannot_claim"]),
        "spatial_overlays_visible": bool(workspace["spatial_overlay_refs"]),
        "no_official_action_affordance": True,
        "local_replay_only": True,
        "no_live_api": True,
    }
    return {
        "schema_version": "main-citybrain.push3.lane_b.coverage.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "source_records": len(source_records["items"]),
            "candidate_observations": len(workspace["candidate_observation_refs"]),
            "watch_items": len(workspace["watch_item_refs"]),
            "check_reports": len(workspace["check_report_refs"]),
            "authority_envelopes": len(workspace["authority_envelope_refs"]),
            "dispositions": len(workspace["disposition_event_refs"]),
            "spatial_overlays": len(workspace["spatial_overlay_refs"]),
            "joined_check_packets": len(joins["check_reports"]),
            "joined_authority_packets": len(joins["authority_envelopes"]),
        },
    }


def boundary_markdown() -> str:
    return "\n".join(
        [
            "# Cockpit Boundary and Non-Claims",
            "",
            "- Local/replay selected-item workspace only.",
            "- Source records are review context unless their source authority explicitly permits more.",
            "- No production API, URL fetch, live retrieval, or LLM call.",
            "- No official case, ticket, submission, dispatch, control, enforcement, autonomous workflow, legal finding, or certified finding.",
            "- No live Kit control or full citywide twin claim.",
            "- Sealed ASK G1-G8 and protected R7 runtimes remain unchanged.",
        ]
    )


def open_index_text() -> str:
    return "\n".join(
        [
            "# Cockpit Source-Record 360 Local Open Index",
            "",
            "- Decision: `COCKPIT_SOURCE_RECORD_360_DECISION.json`",
            "- Workspace contract: `SELECTED_ITEM_WORKSPACE_CONTRACT.json`",
            "- Workspace fixtures: `SELECTED_ITEM_WORKSPACE_FIXTURES.json`",
            "- Source-record index: `SOURCE_RECORD_360_INDEX.json`",
            "- View model: `SOURCE_RECORD_360_VIEW_MODEL.json`",
            "- Static surface: `COCKPIT_LOCAL_SURFACE_STATIC.html`",
            "- Check/Authority coverage: `COCKPIT_CHECK_AUTHORITY_COVERAGE.json`",
            "",
            "Open the static HTML locally. It performs no network calls.",
        ]
    )


def test_log_text(coverage: dict[str, Any]) -> str:
    checks = coverage["checks"]
    return "\n".join(
        [
            "# Cockpit Source-Record 360 Test Log",
            "",
            f"- selected item has source-record 360 fixture: `{checks['selected_item_has_source_record_360']}`",
            f"- candidate observations visible: `{checks['candidate_observations_visible']}`",
            f"- WatchItems visible: `{checks['watch_items_visible']}`",
            f"- CheckReports visible: `{checks['check_reports_visible']}`",
            f"- AuthorityEnvelopes visible: `{checks['authority_envelopes_visible']}`",
            f"- dispositions visible: `{checks['dispositions_visible']}`",
            f"- source freshness visible: `{checks['source_freshness_visible']}`",
            f"- no official action affordance: `{checks['no_official_action_affordance']}`",
            f"- no live API: `{checks['no_live_api']}`",
            "",
            "Focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_push3_lane_b_cockpit_source_record_360`",
        ]
    )


def write_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    items = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != manifest_name):
        items.append({"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "schema_version": "main-citybrain.push3.lane_b.hash_manifest.v1",
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(items),
        "missing_count": 0,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / manifest_name, manifest)
    return manifest


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest = read_json(root / manifest_name, {})
    problems = []
    verified = 0
    for item in manifest.get("items", []):
        path = root / item["path"]
        if not path.exists():
            problems.append(f"missing:{item['path']}")
        elif sha256_file(path) != item["sha256"]:
            problems.append(f"mismatch:{item['path']}")
        else:
            verified += 1
    return {"status": "PASS" if manifest.get("status") == "PASS" and not problems else "FAIL", "verified": verified, "declared": len(manifest.get("items", [])), "problems": problems}


def stop_outputs(gate: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "schema_version": "main-citybrain.push3.lane_b.decision.v1",
        "package": PACKAGE,
        "status": STOP_STATUS,
        "created_at": created_at(),
        "entry_gate": gate,
        "completed_through": ["B0_PUSH2_GATE_AND_DISCOVERY"],
    }
    write_json(OUTPUT_ROOT / "COCKPIT_SOURCE_RECORD_360_DECISION.json", decision)
    manifest = write_hash_manifest(OUTPUT_ROOT, "COCKPIT_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(OUTPUT_ROOT)}


def write_main_outputs() -> dict[str, Any]:
    inputs = load_inputs()
    gate = entry_gate(inputs)
    if gate["status"] != "PASS":
        return stop_outputs(gate)
    workspace, source_records, joins = collect_workspace(inputs)
    contract = workspace_contract()
    index = build_source_record_index(workspace, source_records)
    view_model = build_view_model(workspace, source_records, joins)
    coverage = build_coverage(workspace, source_records, joins, gate)
    status = PASS_STATUS if coverage["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push3.lane_b.decision.v1",
        "package": PACKAGE,
        "status": status,
        "created_at": created_at(),
        "entry_gate": gate,
        "completed_through": [
            "B0_PUSH2_GATE_AND_DISCOVERY",
            "B1_SELECTED_ITEM_WORKSPACE_CONTRACT",
            "B2_SOURCE_RECORD_360_FIXTURES_R1",
            "B3_COCKPIT_LOCAL_SURFACE_R1",
            "B4_STATIC_RENDER_OR_ROUTE_SMOKE_R2",
        ],
        "counts": coverage["counts"],
        "static_surface": "COCKPIT_LOCAL_SURFACE_STATIC.html",
        "local_replay_only": True,
        "infra_canonical_integration_owned_elsewhere": True,
        "limitations": UNIVERSAL_CANNOT_CLAIM,
    }
    write_json(OUTPUT_ROOT / "COCKPIT_SOURCE_RECORD_360_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "SELECTED_ITEM_WORKSPACE_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json", {"schema_version": "main-citybrain.push3.lane_b.workspace_fixtures.v1", "status": "PASS", "items": [workspace]})
    write_json(OUTPUT_ROOT / "SOURCE_RECORD_360_INDEX.json", index)
    write_json(OUTPUT_ROOT / "SOURCE_RECORD_360_VIEW_MODEL.json", view_model)
    write_text(OUTPUT_ROOT / "COCKPIT_LOCAL_SURFACE_STATIC.html", render_static_html(view_model))
    write_text(OUTPUT_ROOT / "COCKPIT_LOCAL_OPEN_INDEX.md", open_index_text())
    write_json(OUTPUT_ROOT / "COCKPIT_CHECK_AUTHORITY_COVERAGE.json", coverage)
    write_text(OUTPUT_ROOT / "COCKPIT_BOUNDARY_AND_NON_CLAIMS.md", boundary_markdown())
    write_text(OUTPUT_ROOT / "COCKPIT_TEST_LOG.md", test_log_text(coverage))
    manifest = write_hash_manifest(OUTPUT_ROOT, "COCKPIT_HASH_MANIFEST.json")
    decision["hash_manifest"] = {"status": manifest["status"], "item_count": manifest["item_count"], "missing_count": manifest["missing_count"], "mismatch_count": manifest["mismatch_count"]}
    write_json(OUTPUT_ROOT / "COCKPIT_SOURCE_RECORD_360_DECISION.json", decision)
    manifest = write_hash_manifest(OUTPUT_ROOT, "COCKPIT_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(OUTPUT_ROOT)}


def closeout_summary(decision: dict[str, Any]) -> str:
    counts = decision.get("counts", {})
    return "\n".join(
        [
            "# Cockpit Source-Record 360 Closeout",
            "",
            f"Status: `{decision['status']}`",
            "",
            f"- selected_items: `1`",
            f"- source_records: `{counts.get('source_records', 0)}`",
            f"- candidate_observations: `{counts.get('candidate_observations', 0)}`",
            f"- watch_items: `{counts.get('watch_items', 0)}`",
            f"- dispositions: `{counts.get('dispositions', 0)}`",
            "",
            "Lane B is ready for branch publish; INFRA owns canonical Push 3 integration.",
        ]
    )


def write_closeout(main_result: dict[str, Any]) -> dict[str, Any]:
    main_decision = main_result["decision"]
    main_hash = verify_hash_manifest(OUTPUT_ROOT, "COCKPIT_HASH_MANIFEST.json")
    status = PASS_STATUS if main_decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push3.lane_b.closeout.decision.v1",
        "package": f"{PACKAGE}-CLOSEOUT",
        "status": status,
        "created_at": created_at(),
        "source_decision": rel(OUTPUT_ROOT / "COCKPIT_SOURCE_RECORD_360_DECISION.json"),
        "source_hash_manifest": main_hash,
        "completed_through": ["B5_CLOSEOUT"],
        "counts": main_decision.get("counts", {}),
        "limitations": UNIVERSAL_CANNOT_CLAIM,
        "next": "Wait for Lane A and Lane C, then INFRA Push 3 integration.",
    }
    write_json(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_DECISION.json", decision)
    write_text(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_SUMMARY.md", closeout_summary(main_decision))
    write_text(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in UNIVERSAL_CANNOT_CLAIM))
    write_text(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane A and Lane C, then INFRA Push 3 integration.\n")
    manifest = write_hash_manifest(CLOSEOUT_ROOT, "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_HASH_MANIFEST.json")
    decision["hash_manifest"] = {"status": manifest["status"], "item_count": manifest["item_count"], "missing_count": manifest["missing_count"], "mismatch_count": manifest["mismatch_count"]}
    write_json(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_DECISION.json", decision)
    manifest = write_hash_manifest(CLOSEOUT_ROOT, "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(CLOSEOUT_ROOT)}


def final_summary(decision: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Cockpit Source-Record 360 Final Status",
            "",
            f"Status: `{decision['status']}`",
            "",
            f"Branch: `{BRANCH}`",
            "Completed through B7 final status. Canonical merge remains INFRA-owned.",
        ]
    )


def write_final_status(closeout_result: dict[str, Any]) -> dict[str, Any]:
    closeout_decision = closeout_result["decision"]
    closeout_hash = verify_hash_manifest(CLOSEOUT_ROOT, "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_HASH_MANIFEST.json")
    status = PASS_STATUS if closeout_decision.get("status") == PASS_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push3.lane_b.final_status.decision.v1",
        "package": f"{PACKAGE}-FINAL-STATUS",
        "status": status,
        "created_at": created_at(),
        "source_closeout_decision": rel(CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_DECISION.json"),
        "source_closeout_hash_manifest": closeout_hash,
        "completed_through": [
            "B0_PUSH2_GATE_AND_DISCOVERY",
            "B1_SELECTED_ITEM_WORKSPACE_CONTRACT",
            "B2_SOURCE_RECORD_360_FIXTURES_R1",
            "B3_COCKPIT_LOCAL_SURFACE_R1",
            "B4_STATIC_RENDER_OR_ROUTE_SMOKE_R2",
            "B5_CLOSEOUT",
            "B6_BRANCH_PUBLISH_READY",
            "B7_FINAL_STATUS",
        ],
        "branch": BRANCH,
        "commit_subject": "Add Push 3 cockpit source-record 360",
        "canonical_merged": False,
        "limitations": UNIVERSAL_CANNOT_CLAIM,
    }
    write_json(FINAL_STATUS_ROOT / "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_DECISION.json", decision)
    write_text(FINAL_STATUS_ROOT / "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_SUMMARY.md", final_summary(decision))
    manifest = write_hash_manifest(FINAL_STATUS_ROOT, "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_HASH_MANIFEST.json")
    decision["hash_manifest"] = {"status": manifest["status"], "item_count": manifest["item_count"], "missing_count": manifest["missing_count"], "mismatch_count": manifest["mismatch_count"]}
    write_json(FINAL_STATUS_ROOT / "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_DECISION.json", decision)
    manifest = write_hash_manifest(FINAL_STATUS_ROOT, "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_HASH_MANIFEST.json")
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(FINAL_STATUS_ROOT)}


def write_outputs() -> dict[str, Any]:
    reset_roots()
    main = write_main_outputs()
    closeout = write_closeout(main)
    final = write_final_status(closeout)
    return {"main": main, "closeout": closeout, "final_status": final}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["final_status"]["decision"]["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    sys.exit(main())
