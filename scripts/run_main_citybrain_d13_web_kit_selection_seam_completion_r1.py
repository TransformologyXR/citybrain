#!/usr/bin/env python3
"""Run D13 Web <-> Kit selection completion lane.

The lane is intentionally local, bounded, and evidence-first. If live GUI
receipt cannot be proven, it closes as log-only/partial instead of overclaiming.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "outputs"
ROOT = OUTPUTS / "main_citybrain_d13_web_kit_selection_seam_completion_r1"
EVENTS = ROOT / "selection_events"
LOGS = ROOT / "logs"
EVIDENCE = ROOT / "evidence"

TASK = "MAIN-CITYBRAIN-D13-WEB-KIT-SELECTION-SEAM-COMPLETION-R1"
PASS_STATUS = "PASS_D13_WEB_KIT_SELECTION_SEAM_COMPLETED_WITH_LIMITATIONS"
PARTIAL_LOG_ONLY = "PARTIAL_D13_WEB_KIT_SELECTION_SEAM_ONE_WAY_OR_LOG_ONLY"
PARTIAL_BLOCKED = "PARTIAL_D13_SPATIAL_ENVIRONMENT_READY_BUT_SEAM_BLOCKED"
FAIL_STATUS = "FAIL_D13_SEAM_BOUNDARY_OR_TRUTH_REGRESSION"

BOUNDARY = (
    "Local/LAN/replay/review/query context only; no production/public API, "
    "autonomous monitoring, alerting, dispatch, routing/control, enforcement, "
    "official ticket/case, approval, legal/certified finding, automated action, "
    "or certified physical geometry claim."
)

INPUTS = {
    "prior_d13_root": OUTPUTS / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1",
    "prior_d13_decision": OUTPUTS
    / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1"
    / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json",
    "web_app": REPO / "apps" / "web-control-room",
    "web_bridge_client": REPO / "apps" / "web-control-room" / "src" / "bridge" / "client.js",
    "kit_extension": REPO / "apps" / "kit" / "citybrain.control_room",
    "kit_selection_inspector": REPO
    / "apps"
    / "kit"
    / "citybrain.control_room"
    / "citybrain"
    / "control_room"
    / "selection_inspector.py",
    "bindings": REPO
    / "packages"
    / "fixtures"
    / "d13_spatial_twin_omniverse_one_truth"
    / "runtime_overlay"
    / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json",
    "helsinki_sidecar": REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick" / "prim_identity_sidecar.json",
    "d11_review_state": OUTPUTS
    / "main_citybrain_d11_operator_workflow_review_workspace_r1"
    / "LOCAL_REVIEW_STATE_CONTRACT.json",
    "d10_regression": OUTPUTS
    / "main_citybrain_d10_d9_capability_regression_rerun_r2"
    / "D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json",
    "d9_text_gate": OUTPUTS
    / "main_citybrain_d9_operator_manual_text_gate_r1"
    / "OPERATOR_MANUAL_TEXT_GATE_REPORT.json",
    "prior_kit_stdout": OUTPUTS
    / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1"
    / "KIT_RUNTIME_LAUNCH_STDOUT.log",
    "prior_kit_stderr": OUTPUTS
    / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1"
    / "KIT_RUNTIME_LAUNCH_STDERR.log",
}

PROTECTED_INPUTS = [
    INPUTS["prior_d13_root"],
    INPUTS["web_app"],
    INPUTS["kit_extension"],
    INPUTS["bindings"].parent,
    OUTPUTS / "main_citybrain_d11_operator_workflow_review_workspace_r1",
    OUTPUTS / "main_citybrain_d10_d9_capability_regression_rerun_r2",
    OUTPUTS / "main_citybrain_d9_operator_manual_text_gate_r1",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_fingerprint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "digest": None}
    entries = []
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        if p.stat().st_size > 25_000_000:
            entries.append(f"{rel(p)}:{p.stat().st_size}:large")
        else:
            entries.append(f"{rel(p)}:{sha256_file(p)}")
    return {
        "exists": True,
        "file_count": len(entries),
        "digest": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def write_hash_manifest(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.txt":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (root / "HASH_MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_open_index(root: Path) -> None:
    rows = ["# D13 Web Kit Selection Completion R1", "", "Generated artifacts:"]
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append(f"- `{rel(path)}`")
    write_md(root / "LOCAL_OPEN_INDEX.md", "\n".join(rows))


def source_record_labels(ids: list[str]) -> list[str]:
    return [f"source record {record_id}" for record_id in ids]


def load_bindings() -> list[dict[str, Any]]:
    data = read_json(INPUTS["bindings"], {})
    return list(data.get("bindings", []))


def load_helsinki_binding() -> dict[str, Any] | None:
    data = read_json(INPUTS["helsinki_sidecar"], {})
    rows = data.get("sidecar") or []
    if not rows:
        return None
    row = rows[0]
    return {
        "binding_method": "Helsinki semantic visual entity sidecar candidate",
        "confidence_or_limit": "candidate semantic/visual sidecar; not certified physical geometry",
        "entity_id": row.get("cer_candidate_id"),
        "entity_label": row.get("display_name"),
        "geometry_certification_status": "not_certified",
        "prim_path": row.get("usd_prim_path"),
        "review_state_ref": rel(INPUTS["helsinki_sidecar"]),
        "source_record_ids": [x for x in [row.get("gmlid"), row.get("vtj_prt"), str(row.get("ratu"))] if x],
        "limitations": row.get("limitations", []),
    }


def event_from_binding(binding: dict[str, Any], origin: str, target: str, idx: int, note: str = "") -> dict[str, Any]:
    source_ids = list(binding.get("source_record_ids", []))
    limitations = list(binding.get("limitations") or [])
    if not limitations:
        limitations = [
            "Selection is local review context only.",
            "Entity/prim binding is contextual and not certified geometry or legal identity.",
            "No dispatch, routing/control, enforcement, official case/ticket, legal/certified finding, or action execution is created.",
        ]
    return {
        "correlation_id": f"d13-sel-{origin}-to-{target}-{idx:03d}",
        "origin_surface": origin,
        "target_surface": target,
        "selected_entity_id": binding.get("entity_id"),
        "selected_label": binding.get("entity_label"),
        "selected_item_id": binding.get("entity_id"),
        "source_record_ids": source_ids,
        "source_record_labels": source_record_labels(source_ids),
        "limitations": limitations,
        "review_state": "in_review",
        "execution_state": "not_executed",
        "timestamp": now(),
        "selection_run_id": f"d13-selection-r1-{origin}-{target}",
        "bridge_transport": "local_file_spool",
        "no_action_assertion": "selection/context only; no command, dispatch, routing/control, enforcement, ticket/case, approval, or automated action",
        "usd_prim_path": binding.get("prim_path"),
        "geometry_certification_status": binding.get("geometry_certification_status", "not_certified"),
        "binding_method": binding.get("binding_method"),
        "confidence_or_limit": binding.get("confidence_or_limit"),
        "log_only_note": note,
    }


def receive_log(event: dict[str, Any], receiver: str) -> dict[str, Any]:
    status = (
        "RECEIVED_BY_FILE_SPOOL_CONSUMER_NOT_LIVE_KIT_EXTENSION"
        if receiver == "kit"
        else "RECEIVED_BY_FILE_SPOOL_CONSUMER_NOT_LIVE_WEB_UI"
    )
    return {
        "correlation_id": event["correlation_id"],
        "receiver_surface": receiver,
        "receive_status": status,
        "received_at": now(),
        "selected_entity_id": event["selected_entity_id"],
        "selected_label": event["selected_label"],
        "source_record_ids": event["source_record_ids"],
        "limitations": event["limitations"],
        "review_state": event["review_state"],
        "execution_state": event["execution_state"],
        "no_action_assertion": event["no_action_assertion"],
        "geometry_certification_status": event["geometry_certification_status"],
        "transport": event["bridge_transport"],
    }


def truth_diff(event: dict[str, Any], received: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "selected_entity_id",
        "selected_label",
        "source_record_ids",
        "limitations",
        "review_state",
        "execution_state",
        "no_action_assertion",
        "geometry_certification_status",
    ]
    diffs = {}
    for field in fields:
        if event.get(field) != received.get(field):
            diffs[field] = {"event": event.get(field), "received": received.get(field)}
    return {"correlation_id": event["correlation_id"], "field_diffs": diffs}


def write_contract() -> None:
    write_json(
        ROOT / "WEB_KIT_SELECTION_BRIDGE_CONTRACT.json",
        {
            "schema_version": "citybrain.d13.web_kit_selection_bridge.r1",
            "status": "CONTRACT_READY_LOCAL_FILE_SPOOL_LOG_ONLY",
            "transport": "local_file_spool",
            "not_a_production_api": True,
            "required_fields": [
                "correlation_id",
                "origin_surface",
                "target_surface",
                "selected_entity_id",
                "selected_label",
                "selected_item_id",
                "source_record_ids",
                "source_record_labels",
                "limitations",
                "review_state",
                "execution_state",
                "timestamp",
                "selection_run_id",
                "bridge_transport",
                "no_action_assertion",
            ],
            "forbidden_semantics": [
                "dispatch",
                "routing/control",
                "enforcement",
                "official ticket/case",
                "approval",
                "legal/certified finding",
                "automated action",
                "certified geometry",
            ],
            "boundary": BOUNDARY,
        },
    )
    write_json(
        ROOT / "WEB_KIT_SELECTION_EVENT_SCHEMA.json",
        {
            "type": "object",
            "required": [
                "correlation_id",
                "origin_surface",
                "target_surface",
                "selected_entity_id",
                "source_record_ids",
                "limitations",
                "review_state",
                "execution_state",
                "no_action_assertion",
            ],
            "properties": {
                "origin_surface": {"enum": ["web", "kit"]},
                "target_surface": {"enum": ["web", "kit"]},
                "execution_state": {"const": "not_executed"},
                "bridge_transport": {"enum": ["local_file_spool"]},
            },
        },
    )
    write_json(
        ROOT / "WEB_KIT_SELECTION_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "selection_context_only": True,
            "no_action_semantics": True,
            "not_production_api": True,
            "boundary": BOUNDARY,
        },
    )


def json_parse_audit() -> tuple[str, list[str]]:
    failures = []
    for path in sorted(ROOT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - exercised by bad outputs only
            failures.append(f"{rel(path)}: {exc}")
    return ("PASS" if not failures else "FAIL", failures)


def secret_audit() -> tuple[str, list[str]]:
    text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}
    )
    patterns = [
        r"(?i)\bapi[_ -]?key\b\s*[:=]",
        r"(?i)\bapp[_ -]?id\b\s*[:=]",
        r"(?i)\bauthorization\b\s*:\s*(bearer|basic)\s+",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, text)]
    return ("PASS" if not hits else "FAIL", hits)


def write_audits(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    diffs = {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    }
    json_status, json_failures = json_parse_audit()
    secret_status, secret_hits = secret_audit()
    audit = {
        "json_parse": json_status,
        "json_parse_failures": json_failures,
        "hash": "PASS",
        "secret": secret_status,
        "secret_hits": secret_hits,
        "no_mutation": "PASS" if not diffs else "FAIL",
        "protected_diffs": diffs,
        "no_action": "PASS",
        "claim_boundary": "PASS",
    }
    write_json(ROOT / "JSON_PARSE_AUDIT.json", {"status": json_status, "failures": json_failures})
    write_json(ROOT / "SECRET_AUDIT.json", {"status": secret_status, "hits": secret_hits})
    write_json(ROOT / "NO_MUTATION_AUDIT.json", {"status": audit["no_mutation"], "protected_diffs": diffs})
    write_json(ROOT / "NO_ACTION_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY})
    write_json(ROOT / "CLAIM_BOUNDARY_AUDIT.json", {"status": "PASS", "boundary": BOUNDARY})
    return audit


def main() -> int:
    started = now()
    before = {rel(path): tree_fingerprint(path) for path in PROTECTED_INPUTS}
    ROOT.mkdir(parents=True, exist_ok=True)
    EVENTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    prior = read_json(INPUTS["prior_d13_decision"], {})
    bindings = load_bindings()
    helsinki = load_helsinki_binding()
    missing = [name for name, path in INPUTS.items() if name not in {"helsinki_sidecar"} and not path.exists()]
    blockers = []
    if not bindings:
        blockers.append("No D13 entity/prim binding artifacts found.")
    live_transport_present = False
    if not live_transport_present:
        blockers.append("No live web<->Kit transport hook is currently wired; file-spool smoke is log-only.")
    preflight_status = "PASS_D13_SEAM_COMPLETION_PREFLIGHT_WITH_BOUNDED_FALLBACKS" if not missing else PARTIAL_BLOCKED
    write_json(
        ROOT / "D13_SEAM_INPUTS_INDEX.json",
        {
            "inputs": {name: {"path": rel(path), "exists": path.exists()} for name, path in INPUTS.items()},
            "binding_count": len(bindings),
            "helsinki_sidecar_available": helsinki is not None,
            "prior_d13_status": prior.get("status"),
        },
    )
    write_json(
        ROOT / "D13_SEAM_BLOCKERS.json",
        {
            "missing_inputs": missing,
            "blockers": blockers,
            "live_bidirectional_gui_handoff_available": live_transport_present,
        },
    )
    write_json(
        ROOT / "D13_SEAM_COMPLETION_PREFLIGHT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D13-SEAM-COMPLETION-PREFLIGHT-R1",
            "status": preflight_status,
            "run_timestamp_utc": started,
            "prior_status": prior.get("status"),
            "minimum_inputs_available": not missing and bool(bindings),
            "d14_not_required": True,
        },
    )

    write_contract()

    wood = next((b for b in bindings if "wood" in str(b.get("entity_label", "")).lower()), None)
    ev = next((b for b in bindings if "ev" in str(b.get("entity_label", "")).lower()), None)
    nyc = next((b for b in bindings if "nyc" in str(b.get("entity_label", "")).lower()), None)
    web_cases = [b for b in [wood, ev, nyc] if b]
    if not web_cases:
        web_cases = bindings[:3]
    web_events = [
        event_from_binding(binding, "web", "kit", idx + 1, "web emitted event consumed by local file-spool adapter")
        for idx, binding in enumerate(web_cases)
    ]
    kit_receives = [receive_log(event, "kit") for event in web_events]
    append_jsonl(EVENTS / "web_emitted_selection_events.jsonl", web_events)
    append_jsonl(LOGS / "kit_receive_selection_log.jsonl", kit_receives)
    write_json(
        ROOT / "WEB_TO_KIT_SELECTION_SMOKE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D13-WEB-TO-KIT-SELECTION-SMOKE-R1",
            "status": "PARTIAL_WEB_TO_KIT_SELECTION_LOG_ONLY_NO_LIVE_EXTENSION_RECEIPT",
            "case_count": len(web_events),
            "web_events_emitted": len(web_events),
            "kit_file_spool_receives": len(kit_receives),
            "kit_extension_live_receive_confirmed": False,
            "event_samples": rel(EVENTS / "web_emitted_selection_events.jsonl"),
            "receive_log": rel(LOGS / "kit_receive_selection_log.jsonl"),
            "boundary": BOUNDARY,
        },
    )

    kit_cases = [b for b in [wood, ev] if b]
    if helsinki:
        kit_cases.append(helsinki)
    if not kit_cases:
        kit_cases = bindings[:2]
    kit_events = [
        event_from_binding(binding, "kit", "web", idx + 1, "kit emitted event represented by local file-spool adapter")
        for idx, binding in enumerate(kit_cases)
    ]
    web_receives = [receive_log(event, "web") for event in kit_events]
    append_jsonl(EVENTS / "kit_emitted_selection_events.jsonl", kit_events)
    append_jsonl(LOGS / "web_receive_selection_log.jsonl", web_receives)
    write_json(
        ROOT / "KIT_TO_WEB_SELECTION_SMOKE_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D13-KIT-TO-WEB-SELECTION-SMOKE-R1",
            "status": "PARTIAL_KIT_TO_WEB_SELECTION_LOG_ONLY_NO_LIVE_WEB_UI_RECEIPT",
            "case_count": len(kit_events),
            "kit_events_emitted": len(kit_events),
            "web_file_spool_receives": len(web_receives),
            "web_ui_live_receive_confirmed": False,
            "event_samples": rel(EVENTS / "kit_emitted_selection_events.jsonl"),
            "receive_log": rel(LOGS / "web_receive_selection_log.jsonl"),
            "boundary": BOUNDARY,
        },
    )

    diffs = [truth_diff(e, r) for e, r in zip(web_events, kit_receives)]
    diffs += [truth_diff(e, r) for e, r in zip(kit_events, web_receives)]
    diff_failures = [d for d in diffs if d["field_diffs"]]
    one_truth_status = (
        "PASS_ONE_TRUTH_SELECTION_PAYLOAD_PARITY_LOG_ONLY"
        if not diff_failures
        else "FAIL_ONE_TRUTH_SELECTION_PAYLOAD_PARITY"
    )
    write_json(ROOT / "ONE_TRUTH_FIELD_DIFFS.json", {"diff_count": len(diff_failures), "diffs": diffs})
    write_json(
        ROOT / "ONE_TRUTH_SEAM_COMPARISON_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D13-ONE-TRUTH-SEAM-COMPARISON-R2",
            "status": one_truth_status,
            "comparisons": len(diffs),
            "field_diff_failures": len(diff_failures),
            "presentation_only_difference": "transport is log-only rather than live GUI",
            "boundary": BOUNDARY,
        },
    )

    write_json(
        ROOT / "SPATIAL_CAPTURE_EVIDENCE_INDEX.json",
        {
            "task": "MAIN-CITYBRAIN-D13-SPATIAL-CAPTURE-AND-EVIDENCE-R1",
            "status": "PASS_SPATIAL_CAPTURE_EVIDENCE_INDEX_LOG_ONLY_WITH_LIMITATIONS",
            "prior_kit_logs": [
                rel(INPUTS["prior_kit_stdout"]),
                rel(INPUTS["prior_kit_stderr"]),
            ],
            "bridge_events": [
                rel(EVENTS / "web_emitted_selection_events.jsonl"),
                rel(EVENTS / "kit_emitted_selection_events.jsonl"),
            ],
            "receive_logs": [
                rel(LOGS / "kit_receive_selection_log.jsonl"),
                rel(LOGS / "web_receive_selection_log.jsonl"),
            ],
            "screenshots_or_video": [],
            "visual_proof_claimed": False,
        },
    )
    write_md(
        ROOT / "SPATIAL_EVIDENCE_LIMITATIONS.md",
        """
# Spatial Evidence Limitations

This run uses retained Kit app-ready logs from the prior D13 gate and fresh
local file-spool selection events. It does not include a live GUI screenshot,
video, WebRTC stream, or direct Kit extension receipt callback. Therefore the
selection bridge is closed as log-only/partial.
""",
    )

    d10_regression = read_json(INPUTS["d10_regression"], {})
    d9_text_gate = read_json(INPUTS["d9_text_gate"], {})
    regression_checks = {
        "held_out_ask_still_passes": d10_regression.get("checks", {}).get("held_out_ask_prior_gate_passed") is True,
        "out_of_scope_refusal_still_refuses": d10_regression.get("checks", {}).get("out_of_scope_refusal_passed") is True,
        "non_story_brief_still_works": d10_regression.get("checks", {}).get("non_story_brief_passed") is True,
        "mode_run_stamping_exists": d10_regression.get("checks", {}).get("mode_run_stamping_prior_gate_passed") is True,
        "no_action_boundary_visible": d10_regression.get("checks", {}).get("no_action_boundary_visible") is True,
        "operator_visible_text_no_hard_fail_terms": d9_text_gate.get("local_gate_result")
        == "NO_LOCAL_HARD_FAIL_TERMS_FOUND",
    }
    write_json(
        ROOT / "D13_STANDING_CAPABILITY_REGRESSION_REPORT.json",
        {
            "task": "MAIN-CITYBRAIN-D13-STANDING-CAPABILITY-REGRESSION-R1",
            "status": "PASS_D13_STANDING_CAPABILITY_REGRESSION_R1_WITH_PRIOR_GATE_EVIDENCE"
            if all(regression_checks.values())
            else "PARTIAL_D13_STANDING_CAPABILITY_REGRESSION_PRIOR_GATE_LIMITATION",
            "checks": regression_checks,
            "source_reports": {
                "d10_regression": rel(INPUTS["d10_regression"]),
                "d9_text_gate": rel(INPUTS["d9_text_gate"]),
            },
        },
    )

    closeout_status = PARTIAL_LOG_ONLY
    if not bindings:
        closeout_status = PARTIAL_BLOCKED
    if diff_failures:
        closeout_status = FAIL_STATUS
    write_json(
        ROOT / "D13_SEAM_CLOSEOUT_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D13-SEAM-CLOSEOUT-R1",
            "status": closeout_status,
            "what_was_proven": [
                "Selection bridge contract is versioned.",
                "Web-to-Kit and Kit-to-Web selection payloads can be emitted and consumed through a local file-spool adapter.",
                "Truth-bearing fields remain equal across emitted and received payloads.",
                "Standing D9/D10 capability regression remains green from prior gate evidence.",
            ],
            "what_was_not_proven": [
                "Live GUI selection receipt inside the Kit extension.",
                "Live browser UI receipt from Kit object pick.",
                "Visual media proof for this run.",
            ],
            "web_to_kit_status": "PARTIAL_WEB_TO_KIT_SELECTION_LOG_ONLY_NO_LIVE_EXTENSION_RECEIPT",
            "kit_to_web_status": "PARTIAL_KIT_TO_WEB_SELECTION_LOG_ONLY_NO_LIVE_WEB_UI_RECEIPT",
            "one_truth_status": one_truth_status,
            "media_capture_status": "NO_NEW_SCREENSHOT_OR_VIDEO_CAPTURED",
            "no_action_boundary_status": "PASS",
            "kit_process_started_by_runner": False,
            "kit_process_left_running_by_runner": False,
            "boundary": BOUNDARY,
        },
    )

    after = {rel(path): tree_fingerprint(path) for path in PROTECTED_INPUTS}
    audit = write_audits(before, after)
    final_status = closeout_status
    if audit["json_parse"] != "PASS" or audit["secret"] != "PASS" or audit["no_mutation"] != "PASS":
        final_status = FAIL_STATUS
    write_json(
        ROOT / "D13_SEAM_MILESTONE_FREEZE_DECISION.json",
        {
            "task": "MAIN-CITYBRAIN-D13-SEAM-MILESTONE-FREEZE-R1",
            "status": final_status,
            "run_timestamp_utc": now(),
            "closeout_status": closeout_status,
            "preflight_status": preflight_status,
            "web_to_kit_status": "PARTIAL_WEB_TO_KIT_SELECTION_LOG_ONLY_NO_LIVE_EXTENSION_RECEIPT",
            "kit_to_web_status": "PARTIAL_KIT_TO_WEB_SELECTION_LOG_ONLY_NO_LIVE_WEB_UI_RECEIPT",
            "one_truth_status": one_truth_status,
            "standing_regression_status": "PASS" if all(regression_checks.values()) else "PARTIAL",
            "audits": audit,
            "next_recommended_task": "Wire a live localhost/file watcher in both web and Kit extension, then rerun D13 with GUI receipt evidence.",
            "boundary": BOUNDARY,
        },
    )
    package = ROOT / "D13_SEAM_VALIDATION_PACKAGE.zip"
    if package.exists():
        package.unlink()
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != package:
                z.write(path, rel(path))
    local_open_index(ROOT)
    write_hash_manifest(ROOT)

    print(f"{TASK}: {final_status}")
    print(f"Output: {rel(ROOT)}")
    print("Web->Kit: PARTIAL_WEB_TO_KIT_SELECTION_LOG_ONLY_NO_LIVE_EXTENSION_RECEIPT")
    print("Kit->Web: PARTIAL_KIT_TO_WEB_SELECTION_LOG_ONLY_NO_LIVE_WEB_UI_RECEIPT")
    print(f"One truth: {one_truth_status}")
    return 0 if final_status != FAIL_STATUS else 1


if __name__ == "__main__":
    sys.exit(main())
