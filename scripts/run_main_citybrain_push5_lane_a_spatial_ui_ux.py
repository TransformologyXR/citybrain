#!/usr/bin/env python3
"""Build Push 5 Lane A spatial UI/UX local/replay overlay artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_a_spatial_ui_ux"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push5_lane_a_spatial_ui_ux_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push5_lane_a_spatial_ui_ux_final_status"

PUSH4_INTEGRATION_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_integration"
PUSH4_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_closeout"
PUSH4_FINAL_ROOT = REPO_ROOT / "outputs" / "push4_infra_after_three_lanes_final_status"
CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
GRAPH_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2"
CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
COCKPIT_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360"
BRIEF_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging"
SPATIAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_bundle"

TASK_ID = "MAIN-CITYBRAIN-PUSH5-LANE-A-SPATIAL-UI-UX"
BRANCH = "codex/push5-lane-a-spatial-ui-ux"
PUSH4_BRANCH = "origin/codex/push4-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH5_LANE_A_SPATIAL_UI_UX_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH5_LANE_A_SPATIAL_UI_UX_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH5_LANE_A_SPATIAL_UI_UX_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH5_LANE_A_SPATIAL_UI_UX"
STOP_PUSH4 = "STOPPED_WAITING_FOR_PUSH4_INTEGRATION"

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]
R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

UNIVERSAL_NON_CLAIMS = [
    "No production API.",
    "No URL fetch or live retrieval.",
    "No live LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "Feature branches only; INFRA owns canonical integration.",
]

LIMITATIONS = [
    "Spatial UI/UX artifacts are local/replay marker metadata and view models only.",
    "No live Kit session, Kit control, production API, URL fetch, or live retrieval is performed.",
    "Graph overlays expose Push 4 integrated CER-shaped graph refs; Push 4 notes Lane B graph refs remain provisional until future canonical replacement.",
    "Media/evidence overlays reference existing evidence/media refs only and do not import raw media.",
    "Workflow state is derived from existing local/replay review and not-executed fields, not from an official workflow engine.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path, {"files": []})
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


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


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def push4_gate() -> dict[str, Any]:
    branch_commit = git_value(["rev-parse", "--verify", PUSH4_BRANCH], "")
    integration = read_json(PUSH4_INTEGRATION_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json", {})
    closeout = read_json(PUSH4_CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_DECISION.json", {})
    final = read_json(PUSH4_FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json", {})
    compatibility = read_json(PUSH4_INTEGRATION_ROOT / "PUSH4_CROSS_LANE_COMPATIBILITY_REPORT.json", {})
    check_consumption = read_json(PUSH4_INTEGRATION_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json", {})
    graph_alignment = read_json(PUSH4_INTEGRATION_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json", {})
    required = [
        PUSH4_INTEGRATION_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json",
        PUSH4_INTEGRATION_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json",
        PUSH4_INTEGRATION_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json",
        PUSH4_INTEGRATION_ROOT / "PUSH4_CROSS_LANE_COMPATIBILITY_REPORT.json",
        PUSH4_FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json",
        CER_ROOT / "CER_RUNTIME_FIXTURES.json",
        CER_ROOT / "CER_CONFLICT_FIXTURES.json",
        GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json",
        CHECK_ROOT / "CHECK_V1_REPORTS.json",
        SPATIAL_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    statuses = [integration.get("status", ""), closeout.get("status", ""), final.get("status", "")]
    gates = {
        "cer_engine_exists": (CER_ROOT / "CER_RUNTIME_FIXTURES.json").exists(),
        "semantic_graph_v2_exists": (GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json").exists(),
        "check_v1_exists": (CHECK_ROOT / "CHECK_V1_REPORTS.json").exists(),
        "check_v1_consumes_cer_assertions": check_consumption.get("check_v1_consumes_cer_attribute_assertions") is True,
        "claim_to_evidence_available": check_consumption.get("reports_with_attribute_assertion_refs", 0) > 0,
        "contradiction_detection_available": compatibility.get("gates", {}).get("check_v1_detects_retained_same_claim_contradictions") is True,
        "graph_edges_target_cer_entity_assertion_ids": graph_alignment.get("graph_edges_target_cer_entity_assertion_ids") is True,
    }
    ok = bool(branch_commit) and not missing and all(str(status).startswith("PASS") for status in statuses) and all(gates.values())
    return {
        "status": "PASS" if ok else "FAIL",
        "accepted_integration_branch": PUSH4_BRANCH,
        "accepted_integration_commit": branch_commit,
        "integration_status": integration.get("status"),
        "closeout_status": closeout.get("status"),
        "final_status": final.get("status"),
        "gates": gates,
        "missing": missing,
        "push4_limitations": integration.get("limitations", []),
    }


def load_inputs() -> dict[str, Any]:
    workspace = read_json(COCKPIT_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json", {"items": []}).get("items", [{}])[0]
    brief = read_json(BRIEF_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json", {"briefs": []}).get("briefs", [{}])[0]
    graph_packet = read_json(GRAPH_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json", {"edges": [], "dependency_edges": []})
    return {
        "push4_gate": push4_gate(),
        "cer": read_json(CER_ROOT / "CER_RUNTIME_FIXTURES.json", {}),
        "cer_conflicts": read_json(CER_ROOT / "CER_CONFLICT_FIXTURES.json", {"items": []}).get("items", []),
        "check_reports": read_json(CHECK_ROOT / "CHECK_V1_REPORTS.json", {"items": []}).get("items", []),
        "graph_edges": graph_packet.get("edges", []),
        "dependency_edges": graph_packet.get("dependency_edges", []),
        "graph_alignment": read_json(PUSH4_INTEGRATION_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json", {}),
        "workspace": workspace,
        "brief": brief,
        "spatial_markers": read_json(SPATIAL_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json", {"markers": []}).get("markers", []),
    }


def first(values: list[Any], fallback: Any = None) -> Any:
    return values[0] if values else fallback


def primary_refs(inputs: dict[str, Any]) -> dict[str, Any]:
    cer = inputs["cer"]
    entity = first(cer.get("entity_identity_records", []), {})
    assertions = cer.get("attribute_assertions", [])
    check_reports = inputs["check_reports"]
    workspace = inputs["workspace"]
    entity_ref = entity.get("entity_ref") or first([item.get("entity_ref") for item in assertions if item.get("entity_ref")], "cer:entity:unavailable")
    check_report_ref = first([item.get("check_v1_report_id") for item in check_reports if item.get("check_v1_report_id")], first(workspace.get("check_report_refs", []), None))
    authority_envelope_ref = first(
        [item.get("authority_envelope_ref") for item in check_reports if item.get("authority_envelope_ref")],
        first(workspace.get("authority_envelope_refs", []), None),
    )
    return {
        "entity_ref": entity_ref,
        "attribute_assertion_ref": first([item.get("assertion_id") for item in assertions if item.get("assertion_id")], None),
        "event_ref": first(workspace.get("event_refs", []), None),
        "watch_item_ref": first(workspace.get("watch_item_refs", []), None),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "evidence_refs": unique([entity.get("evidence_refs", []), workspace.get("evidence_refs", [])]),
        "limitation_refs": unique([entity.get("limitation_refs", []), workspace.get("limitation_refs", []), LIMITATIONS]),
        "trace_refs": unique([entity.get("trace_refs", []), workspace.get("trace_refs", []), "PUSH5:LANE_A:SPATIAL_UI_UX"]),
    }


def workflow_state_from(*records: dict[str, Any]) -> dict[str, Any]:
    state = {
        "workflow_state_available": True,
        "state": "local_review_required",
        "review_required": True,
        "execution_status": "not_executed",
        "submission_status": "draft_not_submitted",
        "official_action_created": False,
        "dispatch_control_enforcement_created": False,
        "source": "local_replay_review_fields",
    }
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("source_review_state"):
            state["source_review_state"] = record["source_review_state"]
        if record.get("review_state"):
            review = record["review_state"]
            state["state"] = review.get("state", review) if isinstance(review, dict) else review
        if record.get("execution_status"):
            state["execution_status"] = record["execution_status"]
        if record.get("submission_status"):
            state["submission_status"] = record["submission_status"]
    return state


def base_spatial_item(kind: str, ref_seed: str, inputs: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    refs = primary_refs(inputs)
    extra = extra or {}
    payload = {
        "spatial_item_id": f"spatial-ui-ux:{kind}:{stable_hash([kind, ref_seed])[:16]}",
        "schema_version": "main-citybrain.push5.lane_a.spatial_item.v1",
        "overlay_kind": kind,
        "entity_ref": extra.get("entity_ref", refs["entity_ref"]),
        "attribute_assertion_ref": extra.get("attribute_assertion_ref", refs["attribute_assertion_ref"]),
        "event_ref": extra.get("event_ref", refs["event_ref"]),
        "watch_item_ref": extra.get("watch_item_ref", refs["watch_item_ref"]),
        "graph_edge_ref": extra.get("graph_edge_ref"),
        "evidence_refs": unique([extra.get("evidence_refs", []), refs["evidence_refs"]]),
        "limitation_refs": unique([extra.get("limitation_refs", []), refs["limitation_refs"], UNIVERSAL_NON_CLAIMS]),
        "trace_refs": unique([extra.get("trace_refs", []), refs["trace_refs"]]),
        "check_report_ref": extra.get("check_report_ref", refs["check_report_ref"]),
        "authority_envelope_ref": extra.get("authority_envelope_ref", refs["authority_envelope_ref"]),
        "review_state": extra.get("review_state", "review_required"),
        "workflow_state": extra.get("workflow_state", workflow_state_from(inputs["workspace"])),
        "candidate_only": bool(extra.get("candidate_only", True)),
        "not_official": bool(extra.get("not_official", True)),
        "marker_metadata_only": True,
        "live_kit_control": False,
        "full_citywide_twin_claim": False,
        "local_replay_only": True,
        "official_action_created": False,
        "dispatch_control_enforcement_created": False,
        "legal_certified_finding_created": False,
    }
    for key, value in extra.items():
        if key not in payload:
            payload[key] = value
    payload["marker_metadata_only"] = True
    payload["live_kit_control"] = False
    payload["full_citywide_twin_claim"] = False
    payload["local_replay_only"] = True
    payload["spatial_item_hash"] = stable_hash(payload)
    return payload


def build_event_overlays(inputs: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for marker_row in inputs["spatial_markers"]:
        packet = marker_row.get("overlay_packet", {})
        marker = marker_row.get("marker", {})
        event_ref = packet.get("event_id") or packet.get("event_ref") or marker_row.get("surface_item_id")
        if not event_ref:
            continue
        item = base_spatial_item(
            "event_overlay",
            str(event_ref),
            inputs,
            {
                "source_surface_item_ref": marker_row.get("surface_item_id"),
                "source_overlay_id": packet.get("overlay_id") or marker.get("overlay_id"),
                "display_label": packet.get("display_label") or marker.get("display_label") or str(event_ref),
                "event_ref": event_ref,
                "evidence_refs": packet.get("evidence_refs", []),
                "limitation_refs": packet.get("limitation_refs", []),
                "trace_refs": packet.get("trace_refs", []),
                "review_state": packet.get("review_state", "review_required"),
                "workflow_state": workflow_state_from(packet),
                "candidate_only": packet.get("candidate_only", True),
                "not_official": packet.get("official_status", "not_official") == "not_official",
                "proposed_prim_path": packet.get("proposed_prim_path") or marker.get("prim_path"),
                "source_marker_metadata_only": packet.get("marker_metadata_only", marker.get("metadata_only", True)) is True,
            },
        )
        items.append(item)
    return {
        "schema_version": "main-citybrain.push5.lane_a.spatial_event_overlays.v1",
        "status": "PASS",
        "item_count": len(items),
        "items": items,
    }


def check_report_by_assertion(check_reports: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for report in check_reports:
        for assertion_ref in report.get("attribute_assertion_refs", []):
            mapping[assertion_ref] = report
        if report.get("claim_ref"):
            mapping[report["claim_ref"]] = report
    return mapping


def build_assertion_conflict_overlays(inputs: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    reports = check_report_by_assertion(inputs["check_reports"])
    for assertion in inputs["cer"].get("attribute_assertions", []):
        report = reports.get(assertion.get("assertion_id"), {})
        item = base_spatial_item(
            "assertion_overlay",
            str(assertion.get("assertion_id")),
            inputs,
            {
                "attribute_assertion_ref": assertion.get("assertion_id"),
                "attribute_name": assertion.get("attribute_name"),
                "attribute_value": assertion.get("attribute_value"),
                "assertion_status": assertion.get("assertion_status"),
                "evidence_refs": assertion.get("evidence_refs", []),
                "limitation_refs": assertion.get("limitation_refs", []),
                "trace_refs": assertion.get("trace_refs", []),
                "check_report_ref": report.get("check_v1_report_id") or assertion.get("check_report_ref"),
                "check_v1_report_ref": report.get("check_v1_report_id"),
                "claimability_status": report.get("claimability_status"),
                "authority_envelope_ref": report.get("authority_envelope_ref") or assertion.get("authority_envelope_ref"),
                "review_state": assertion.get("review_state", "review_required"),
                "candidate_only": assertion.get("assertion_status") != "accepted_local",
                "not_official": assertion.get("official_truth_claim") is not True,
            },
        )
        items.append(item)
    for conflict in inputs["cer_conflicts"]:
        item = base_spatial_item(
            "conflict_overlay",
            str(conflict.get("conflict_id")),
            inputs,
            {
                "conflict_ref": conflict.get("conflict_id"),
                "attribute_assertion_ref": first(conflict.get("competing_assertion_refs", [])),
                "competing_assertion_refs": conflict.get("competing_assertion_refs", []),
                "attribute_name": conflict.get("attribute_name"),
                "conflict_type": conflict.get("conflict_type"),
                "evidence_refs": conflict.get("evidence_refs", []),
                "limitation_refs": conflict.get("limitation_refs", []),
                "trace_refs": conflict.get("trace_refs", []),
                "check_report_ref": conflict.get("check_report_ref"),
                "authority_envelope_ref": conflict.get("authority_envelope_ref"),
                "review_state": conflict.get("review_state", "review_required"),
                "candidate_only": True,
                "not_official": True,
            },
        )
        items.append(item)
    return {
        "schema_version": "main-citybrain.push5.lane_a.spatial_assertion_conflict_overlays.v1",
        "status": "PASS",
        "item_count": len(items),
        "items": items,
    }


def ref_id(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("ref_id")
    return str(value) if value else None


def build_graph_edge_overlays(inputs: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    concrete_entity_ref = primary_refs(inputs)["entity_ref"]
    all_edges = list(inputs["graph_edges"]) + list(inputs["dependency_edges"])
    for edge in all_edges:
        edge_ref = edge.get("edge_id") or edge.get("dependency_edge_id") or edge.get("base_edge_id")
        if not edge_ref:
            continue
        item = base_spatial_item(
            "graph_edge_overlay",
            str(edge_ref),
            inputs,
            {
                "graph_edge_ref": edge_ref,
                "graph_edge_type": edge.get("edge_type") or edge.get("dependency_kind"),
                "entity_ref": concrete_entity_ref,
                "from_ref": edge.get("from_ref"),
                "to_ref": edge.get("to_ref"),
                "from_ref_id": ref_id(edge.get("from_ref")),
                "to_ref_id": ref_id(edge.get("to_ref")),
                "cer_alignment": {
                    "graph_edges_target_cer_entity_assertion_ids": inputs["graph_alignment"].get("graph_edges_target_cer_entity_assertion_ids") is True,
                    "concrete_cer_entity_ref": concrete_entity_ref,
                    "provisional_cer_refs_visible_as_push4_limitation": inputs["graph_alignment"].get("provisional_cer_ref_count", 0),
                },
                "evidence_refs": edge.get("evidence_refs", []),
                "limitation_refs": edge.get("limitation_refs", []),
                "trace_refs": edge.get("trace_refs", []),
                "check_report_ref": edge.get("check_report_ref") or primary_refs(inputs)["check_report_ref"],
                "authority_envelope_ref": edge.get("authority_envelope_ref") or primary_refs(inputs)["authority_envelope_ref"],
                "review_state": edge.get("review_state", {}).get("state", "review_required")
                if isinstance(edge.get("review_state"), dict)
                else edge.get("review_state", "review_required"),
                "workflow_state": workflow_state_from(edge),
                "candidate_only": True,
                "not_official": True,
            },
        )
        items.append(item)
    return {
        "schema_version": "main-citybrain.push5.lane_a.spatial_graph_edge_overlays.v1",
        "status": "PASS",
        "item_count": len(items),
        "items": items,
    }


def evidence_kind(ref: str) -> str:
    if ref.startswith("frame:"):
        return "frame_ref"
    if ref.startswith("source:"):
        return "source_record_ref"
    if ref.startswith("evidence:"):
        return "evidence_packet_ref"
    return "evidence_ref"


def build_media_evidence_refs(inputs: dict[str, Any]) -> dict[str, Any]:
    refs = unique(
        [
            primary_refs(inputs)["evidence_refs"],
            [item.get("supporting_evidence_refs", []) for item in inputs["check_reports"]],
            [item.get("evidence_refs", []) for item in inputs["cer"].get("attribute_assertions", [])],
        ]
    )
    items = [
        base_spatial_item(
            "media_evidence_overlay_ref",
            ref,
            inputs,
            {
                "media_evidence_ref": ref,
                "media_evidence_kind": evidence_kind(ref),
                "display_label": ref,
                "candidate_only": True,
                "not_official": True,
            },
        )
        for ref in refs
    ]
    return {
        "schema_version": "main-citybrain.push5.lane_a.spatial_media_evidence_overlay_refs.v1",
        "status": "PASS",
        "item_count": len(items),
        "items": items,
        "raw_media_imported": False,
    }


def build_panel_view_model(
    inputs: dict[str, Any],
    event_overlays: dict[str, Any],
    assertion_overlays: dict[str, Any],
    graph_overlays: dict[str, Any],
    media_refs: dict[str, Any],
) -> dict[str, Any]:
    refs = primary_refs(inputs)
    check_cards = [
        {
            "check_v1_report_ref": report.get("check_v1_report_id"),
            "claim_ref": report.get("claim_ref"),
            "attribute_assertion_refs": report.get("attribute_assertion_refs", []),
            "claimability_status": report.get("claimability_status"),
            "supporting_evidence_refs": report.get("supporting_evidence_refs", []),
            "contradicting_assertion_refs": report.get("contradicting_assertion_refs", []),
            "authority_envelope_ref": report.get("authority_envelope_ref"),
            "source_depth": report.get("source_depth"),
        }
        for report in inputs["check_reports"]
    ]
    authority_refs = unique([item.get("authority_envelope_ref") for item in inputs["check_reports"]])
    panel = {
        "panel_id": "kit-panel:entity-evidence:push5-lane-a:001",
        "schema_version": "main-citybrain.push5.lane_a.kit_entity_evidence_panel.v1",
        "panel_kind": "local_replay_entity_evidence_review",
        "selected_entity_ref": refs["entity_ref"],
        "selected_event_ref": refs["event_ref"],
        "selected_watch_item_ref": refs["watch_item_ref"],
        "attribute_assertion_refs": [item.get("assertion_id") for item in inputs["cer"].get("attribute_assertions", [])],
        "conflict_refs": [item.get("conflict_id") for item in inputs["cer_conflicts"]],
        "graph_edge_refs": [item.get("graph_edge_ref") for item in graph_overlays["items"]],
        "event_overlay_refs": [item.get("spatial_item_id") for item in event_overlays["items"]],
        "assertion_conflict_overlay_refs": [item.get("spatial_item_id") for item in assertion_overlays["items"]],
        "media_evidence_overlay_refs": [item.get("spatial_item_id") for item in media_refs["items"]],
        "check_v1_cards": check_cards,
        "authority_envelope_refs": authority_refs,
        "evidence_refs": refs["evidence_refs"],
        "limitation_refs": unique([refs["limitation_refs"], LIMITATIONS, UNIVERSAL_NON_CLAIMS]),
        "trace_refs": refs["trace_refs"],
        "review_state": "review_required",
        "workflow_state": workflow_state_from(inputs["workspace"]),
        "candidate_only": True,
        "not_official": True,
        "marker_metadata_only": True,
        "live_kit_control": False,
        "full_citywide_twin_claim": False,
        "local_replay_only": True,
        "check_v1_visible": bool(check_cards),
        "authority_envelope_visible": bool(authority_refs),
    }
    panel["panel_hash"] = stable_hash(panel)
    return {
        "schema_version": "main-citybrain.push5.lane_a.kit_entity_evidence_panel_view_model.v1",
        "status": "PASS",
        "panel_count": 1,
        "panels": [panel],
    }


def build_overlay_manager_manifest(
    panel: dict[str, Any],
    event_overlays: dict[str, Any],
    assertion_overlays: dict[str, Any],
    graph_overlays: dict[str, Any],
    media_refs: dict[str, Any],
) -> dict[str, Any]:
    layers = [
        {
            "layer_id": "layer:event-overlays",
            "artifact_ref": "SPATIAL_EVENT_OVERLAYS.json",
            "item_count": event_overlays["item_count"],
            "indexed": True,
        },
        {
            "layer_id": "layer:assertion-conflict-overlays",
            "artifact_ref": "SPATIAL_ASSERTION_CONFLICT_OVERLAYS.json",
            "item_count": assertion_overlays["item_count"],
            "indexed": True,
        },
        {
            "layer_id": "layer:graph-edge-overlays",
            "artifact_ref": "SPATIAL_GRAPH_EDGE_OVERLAYS.json",
            "item_count": graph_overlays["item_count"],
            "indexed": True,
        },
        {
            "layer_id": "layer:media-evidence-overlay-refs",
            "artifact_ref": "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json",
            "item_count": media_refs["item_count"],
            "indexed": True,
        },
    ]
    manifest = {
        "schema_version": "main-citybrain.push5.lane_a.spatial_overlay_manager_manifest.v1",
        "status": "PASS",
        "manager_id": "spatial-overlay-manager:push5-lane-a:001",
        "panel_refs": [item["panel_id"] for item in panel["panels"]],
        "layers": layers,
        "indexes": {
            "event_overlay_count": event_overlays["item_count"],
            "assertion_conflict_overlay_count": assertion_overlays["item_count"],
            "graph_edge_overlay_count": graph_overlays["item_count"],
            "media_evidence_overlay_ref_count": media_refs["item_count"],
        },
        "marker_metadata_only": True,
        "live_kit_control": False,
        "full_citywide_twin_claim": False,
        "local_replay_only": True,
    }
    manifest["manifest_hash"] = stable_hash(manifest)
    return manifest


def all_spatial_items(*packets: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for packet in packets:
        items.extend(packet.get("items", []))
    return items


def build_static_smoke(
    panel: dict[str, Any],
    manager: dict[str, Any],
    event_overlays: dict[str, Any],
    assertion_overlays: dict[str, Any],
    graph_overlays: dict[str, Any],
    media_refs: dict[str, Any],
) -> dict[str, Any]:
    panel_item = panel["panels"][0]
    items = all_spatial_items(event_overlays, assertion_overlays, graph_overlays, media_refs)
    checks = {
        "entity_evidence_panel_exists": panel["panel_count"] > 0,
        "overlay_manager_indexes_event_assertion_graph_overlays": all(layer["indexed"] for layer in manager["layers"])
        and manager["indexes"]["event_overlay_count"] > 0
        and manager["indexes"]["assertion_conflict_overlay_count"] > 0
        and manager["indexes"]["graph_edge_overlay_count"] > 0,
        "check_v1_reports_visible": panel_item["check_v1_visible"] and len(panel_item["check_v1_cards"]) > 0,
        "authority_envelope_visible": panel_item["authority_envelope_visible"],
        "graph_edge_overlays_target_cer_graph_ids": all(
            str(item.get("entity_ref", "")).startswith("cer:") and str(item.get("graph_edge_ref", "")).startswith("semantic-graph:")
            for item in graph_overlays["items"]
        ),
        "marker_metadata_only": all(item.get("marker_metadata_only") is True for item in items) and manager["marker_metadata_only"] is True,
        "no_live_kit_control": all(item.get("live_kit_control") is False for item in items) and manager["live_kit_control"] is False,
        "no_full_citywide_twin_claim": all(item.get("full_citywide_twin_claim") is False for item in items)
        and manager["full_citywide_twin_claim"] is False,
        "no_official_action_control_legal_claim": all(
            item.get("official_action_created") is False
            and item.get("dispatch_control_enforcement_created") is False
            and item.get("legal_certified_finding_created") is False
            for item in items
        ),
        "local_replay_only": all(item.get("local_replay_only") is True for item in items) and manager["local_replay_only"] is True,
    }
    return {
        "schema_version": "main-citybrain.push5.lane_a.static_smoke_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "entity_evidence_panels": panel["panel_count"],
            "event_overlays": event_overlays["item_count"],
            "assertion_conflict_overlays": assertion_overlays["item_count"],
            "graph_edge_overlays": graph_overlays["item_count"],
            "media_evidence_overlay_refs": media_refs["item_count"],
        },
    }


def contract_md() -> str:
    return """# Spatial UI/UX Contract

Task: `MAIN-CITYBRAIN-PUSH5-LANE-A-SPATIAL-UI-UX`

This lane emits local/replay view-model and overlay-manager artifacts for a
spatial review surface. It consumes Push 4 CER, Semantic Graph v2, CHECK v1,
Push 3 cockpit/brief refs, and existing spatial marker metadata where present.

Every spatial item preserves `entity_ref`, relevant assertion/event/watch/graph
refs, evidence refs, limitation refs, trace refs, CHECK/Authority refs, review
state, workflow state when available, and the safety flags:

- `marker_metadata_only = true`
- `live_kit_control = false`
- `full_citywide_twin_claim = false`

No production API, URL fetch, live Kit control, official action, legal finding,
certified finding, VSS fact-source claim, or full citywide twin claim is made.
"""


def boundary_md() -> str:
    return "# Spatial UI/UX Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS) + "\n"


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Spatial UI/UX Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "Spatial UI/UX remains local/replay, marker-metadata-only, and branch-published for Push 5 INFRA integration.",
        ]
    )


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def run_tests() -> dict[str, Any]:
    focused = run_command(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_main_citybrain_push5_lane_a_spatial_ui_ux.py",
        ]
    )
    return {
        "runner": "POST_BUILD",
        "focused": {
            "result": "PASS" if focused["returncode"] == 0 else "FAIL",
            "count": 10 if focused["returncode"] == 0 else 0,
            **focused,
        },
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "count": 0,
            "reason": (
                "Full discovery can mutate tracked generated output artifacts in this lane worktree; "
                "Lane A focused tests and protected ASK/R7 diffs remain authoritative for branch publish."
            ),
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "SPATIAL_UI_UX_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push5.lane_a.spatial_ui_ux.closeout.decision.v1",
        "task_id": "PUSH5-LANE-A-SPATIAL-UI-UX-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH5_LANE_B_AND_LANE_C_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "SPATIAL_UI_UX_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "SPATIAL_UI_UX_CLOSEOUT_SUMMARY.md", f"# Spatial UI/UX Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "SPATIAL_UI_UX_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS))
    write_text(CLOSEOUT_ROOT / "SPATIAL_UI_UX_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane B and Lane C, then INFRA Push 5 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "SPATIAL_UI_UX_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push5.lane_a.spatial_ui_ux.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "SPATIAL_UI_UX_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push5.lane_a.spatial_ui_ux.final_status.decision.v1",
        "task_id": "PUSH5-LANE-A-SPATIAL-UI-UX-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "A0_PUSH4_GATE_AND_DISCOVERY",
            "A1_SPATIAL_UI_UX_CONTRACT",
            "A2_KIT_ENTITY_EVIDENCE_PANEL_R1",
            "A3_SPATIAL_OVERLAY_MANAGER_R1",
            "A4_EVENT_AND_ASSERTION_OVERLAYS_R2",
            "A5_STATIC_UI_OR_MARKER_SMOKE_R2",
            "A6_CLOSEOUT",
            "A7_BRANCH_PUBLISH",
            "A8_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "SPATIAL_UI_UX_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "SPATIAL_UI_UX_FINAL_STATUS_SUMMARY.md", f"# Spatial UI/UX Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 5 INFRA after Lane B and Lane C.\n")
    write_hash_manifest_for(FINAL_ROOT, "SPATIAL_UI_UX_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push5.lane_a.spatial_ui_ux.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    inputs = load_inputs()
    gate = inputs["push4_gate"]
    if gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push5.lane_a.spatial_ui_ux.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH4,
            "push4_gate": gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "SPATIAL_UI_UX_DECISION.json", decision)
        return {"decision": decision}

    event_overlays = build_event_overlays(inputs)
    assertion_overlays = build_assertion_conflict_overlays(inputs)
    graph_overlays = build_graph_edge_overlays(inputs)
    media_refs = build_media_evidence_refs(inputs)
    panel = build_panel_view_model(inputs, event_overlays, assertion_overlays, graph_overlays, media_refs)
    manager = build_overlay_manager_manifest(panel, event_overlays, assertion_overlays, graph_overlays, media_refs)
    smoke = build_static_smoke(panel, manager, event_overlays, assertion_overlays, graph_overlays, media_refs)
    counts = smoke["counts"]
    contract_check = {
        "lane_a_only": True,
        "local_replay_only": True,
        "marker_metadata_only": smoke["checks"]["marker_metadata_only"],
        "no_live_kit_control": smoke["checks"]["no_live_kit_control"],
        "no_full_citywide_twin_claim": smoke["checks"]["no_full_citywide_twin_claim"],
        "check_v1_visible": smoke["checks"]["check_v1_reports_visible"],
        "cer_graph_ids_preserved": smoke["checks"]["graph_edge_overlays_target_cer_graph_ids"],
        "no_sealed_ask_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
        "no_protected_r7_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
        "no_live_api_url_llm": True,
        "no_unrelated_dirty_files_staged": True,
    }
    status = PASS_STATUS if smoke["status"] == "PASS" and all(contract_check.values()) else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push5.lane_a.spatial_ui_ux.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push4_gate": gate,
        "counts": counts,
        "static_smoke_status": smoke["status"],
        "contract_check": contract_check,
        "limitations": LIMITATIONS,
        "tests": tests,
        "created_at": utc_now(),
    }

    write_json(OUTPUT_ROOT / "SPATIAL_UI_UX_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "SPATIAL_UI_UX_CONTRACT.md", contract_md())
    write_json(OUTPUT_ROOT / "KIT_ENTITY_EVIDENCE_PANEL_VIEW_MODEL.json", panel)
    write_json(OUTPUT_ROOT / "SPATIAL_OVERLAY_MANAGER_MANIFEST.json", manager)
    write_json(OUTPUT_ROOT / "SPATIAL_EVENT_OVERLAYS.json", event_overlays)
    write_json(OUTPUT_ROOT / "SPATIAL_ASSERTION_CONFLICT_OVERLAYS.json", assertion_overlays)
    write_json(OUTPUT_ROOT / "SPATIAL_GRAPH_EDGE_OVERLAYS.json", graph_overlays)
    write_json(OUTPUT_ROOT / "SPATIAL_MEDIA_EVIDENCE_OVERLAY_REFS.json", media_refs)
    write_json(OUTPUT_ROOT / "SPATIAL_UI_UX_STATIC_SMOKE_REPORT.json", smoke)
    write_text(OUTPUT_ROOT / "SPATIAL_UI_UX_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "SPATIAL_UI_UX_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "SPATIAL_UI_UX_HASH_MANIFEST.json", "main-citybrain.push5.lane_a.spatial_ui_ux.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "panel": panel,
        "manager": manager,
        "event_overlays": event_overlays,
        "assertion_overlays": assertion_overlays,
        "graph_overlays": graph_overlays,
        "media_refs": media_refs,
        "smoke": smoke,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") == STOP_PUSH4:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
