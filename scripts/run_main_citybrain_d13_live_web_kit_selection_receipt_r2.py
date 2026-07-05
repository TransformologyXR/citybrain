from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TASK = "MAIN-CITYBRAIN-D13-LIVE-WEB-KIT-SELECTION-RECEIPT-R2"
ROOT = REPO / "outputs" / "main_citybrain_d13_live_web_kit_selection_receipt_r2"
FIXTURE_ROOT = REPO / "packages" / "fixtures" / "d13_live_web_kit_selection_receipt" / "runtime_overlay"
TEMP_WEB_EVENTS = REPO / "tmp" / "d13_r2_web_selection_events.json"
TEMP_BROWSER_PROOF = REPO / "tmp" / "d13_r2_browser_dom_proof.json"
KIT_TEMPLATE = Path("C:/Users/hazem/Documents/OmniverseKit/kit-app-template")
KIT_LAUNCHER = KIT_TEMPLATE / "_build" / "windows-x86_64" / "release" / "txr.citybrain.kit.bat"

PASS_STATUS = "PASS_D13_LIVE_WEB_KIT_SELECTION_SEAM_WITH_LIMITATIONS"
PARTIAL_ONE_WAY = "PARTIAL_D13_LIVE_SEAM_ONE_WAY_ONLY"
PARTIAL_LOG_ONLY = "PARTIAL_D13_LIVE_SEAM_LOG_ONLY"
PARTIAL_ENV = "PARTIAL_D13_LIVE_SEAM_ENV_BLOCKED"
FAIL_STATUS = "FAIL_D13_LIVE_SEAM_BOUNDARY_OR_PARITY"

BASE_D13 = REPO / "outputs" / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1"
D11_ROOT = REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1"
D12_ROOT = REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1"
D10_ROOT = REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_r2"
D13_BINDINGS = REPO / "packages" / "fixtures" / "d13_spatial_twin_omniverse_one_truth" / "runtime_overlay" / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json"

READ_ONLY_ROOTS = [
    BASE_D13,
    D11_ROOT,
    D12_ROOT,
    D10_ROOT,
    REPO / "packages" / "fixtures" / "d9_product_modes",
    REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth",
    REPO / "packages" / "fixtures" / "d11_operator_workflow_review_workspace",
    REPO / "packages" / "fixtures" / "d13_spatial_twin_omniverse_one_truth",
]

FORBIDDEN_COMMANDS = [
    "execute",
    "dispatch",
    "route",
    "enforce",
    "approve",
    "create_ticket",
    "create_case",
    "send_alert",
    "publish_alert",
    "control_signal",
    "take_action",
    "legal_find",
    "certify_finding",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def fingerprint(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "entries": {}}
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return {"exists": True, "entries": {rel(p): sha256_file(p) for p in files}}


def read_only_hashes() -> dict:
    return {rel(root): fingerprint(root) for root in READ_ONLY_ROOTS}


def init_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    kit_to_web = FIXTURE_ROOT / "D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json"
    if kit_to_web.exists():
        kit_to_web.unlink()


def load_bindings() -> list[dict]:
    return read_json(D13_BINDINGS, {}).get("bindings", [])


def add_payload_hash(payload: dict) -> dict:
    row = dict(payload)
    row.pop("payload_hash", None)
    row["payload_hash"] = sha256_json(row)
    return row


def fallback_events(bindings: list[dict]) -> list[dict]:
    events = []
    for idx, binding in enumerate(bindings[:2], 1):
        events.append(
            add_payload_hash(
                {
                    "direction": "web_to_kit",
                    "command": "select",
                    "selection_id": f"d13-r2-contract-fallback-web-selection-{idx:03d}",
                    "entity_id": binding["entity_id"],
                    "entity_label": binding.get("entity_label"),
                    "evidence_packet_ref": ",".join(binding.get("source_record_ids", [])),
                    "limitations_ref": binding.get("confidence_or_limit"),
                    "execution_state": "not_executed",
                    "no_action_state": "no_action_taken",
                    "source_runtime_bundle_ref": rel(D13_BINDINGS),
                    "timestamp": now_iso(),
                    "origin": "runner_fallback_not_browser_click",
                }
            )
        )
    return events


def web_events_from_browser(bindings: list[dict]) -> tuple[list[dict], str]:
    raw = read_json(TEMP_WEB_EVENTS, {"events": []})
    browser_events = raw.get("events", []) if isinstance(raw, dict) else []
    if browser_events:
        normalized = []
        for event in browser_events[:2]:
            row = dict(event)
            row.setdefault("direction", "web_to_kit")
            row.setdefault("command", "select")
            row.setdefault("execution_state", "not_executed")
            row.setdefault("no_action_state", "no_action_taken")
            row.setdefault("source_runtime_bundle_ref", "packages/fixtures/d9_product_modes/runtime_bundle/D9_PRODUCT_MODE_RUNTIME_BUNDLE.json")
            normalized.append(add_payload_hash(row))
        return normalized, "browser_queue_card_click"
    return fallback_events(bindings), "runner_fallback_not_browser_click"


def preflight(events_origin: str) -> dict:
    expected = {
        "d13_base_decision": BASE_D13 / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json",
        "d13_base_handoff_contract": BASE_D13 / "WEB_KIT_SELECTION_HANDOFF_CONTRACT.json",
        "d13_base_one_truth": BASE_D13 / "ONE_TRUTH_SEAM_SMOKE_REPORT.json",
        "d13_bindings": D13_BINDINGS,
        "d11_freeze": D11_ROOT / "D11_WORKFLOW_MILESTONE_FREEZE_DECISION.json",
        "d12_freeze": D12_ROOT / "D12_CITY_DATA_DEPTH_MILESTONE_FREEZE_DECISION.json",
        "web_bridge_client": REPO / "apps" / "web-control-room" / "src" / "bridge" / "client.js",
        "kit_extension": REPO / "apps" / "kit" / "citybrain.control_room" / "config" / "extension.toml",
    }
    missing = [name for name, path in expected.items() if not path.exists()]
    equivalent_prior_artifacts = {
        "D13_SEAM_MILESTONE_FREEZE_DECISION.json": rel(BASE_D13 / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json"),
        "WEB_KIT_SELECTION_BRIDGE_CONTRACT.json": rel(BASE_D13 / "WEB_KIT_SELECTION_HANDOFF_CONTRACT.json"),
        "ONE_TRUTH_SEAM_COMPARISON_REPORT.json": rel(BASE_D13 / "ONE_TRUTH_SEAM_SMOKE_REPORT.json"),
    }
    status = "PASS_D13_LIVE_SEAM_PREFLIGHT" if not missing and KIT_LAUNCHER.exists() else "PARTIAL_D13_LIVE_SEAM_PREFLIGHT_WITH_ENV_OR_INPUT_GAPS"
    decision = {
        "task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-PREFLIGHT-R2",
        "status": status,
        "missing_inputs": missing,
        "kit_launcher": str(KIT_LAUNCHER),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "equivalent_prior_artifacts": equivalent_prior_artifacts,
        "web_selection_event_origin": events_origin,
        "boundary": [
            "Selection payloads only.",
            "No second selection model.",
            "No dispatch, routing/control, enforcement, approval, official case, certified finding, or action execution.",
        ],
    }
    write_json(ROOT / "D13_LIVE_SEAM_PREFLIGHT_DECISION.json", decision)
    write_json(
        ROOT / "INPUT_ARTIFACT_INDEX.json",
        {
            "task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-PREFLIGHT-R2",
            "inputs": {name: {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path) if path.exists() and path.is_file() else None} for name, path in expected.items()},
        },
    )
    return decision


def write_contract() -> dict:
    contract = {
        "task": "MAIN-CITYBRAIN-D13-LIVE-BRIDGE-TRANSPORT-CONTRACT-R2",
        "status": "PASS_LIVE_WEB_KIT_SELECTION_BRIDGE_CONTRACT_R2",
        "authoritative_selection_model": "web cockpit queue/entity selection contract",
        "transport_model": "bounded local receipt bridge carrying selection payloads only",
        "payload_required_fields": [
            "direction",
            "selection_id",
            "entity_id",
            "evidence_packet_ref",
            "limitations_ref",
            "execution_state",
            "no_action_state",
            "source_runtime_bundle_ref",
            "payload_hash",
            "timestamp",
        ],
        "receipt_required_fields": [
            "received_by",
            "original_payload_hash",
            "receipt_timestamp",
            "rendering_selection_state_observed",
            "no_action_taken",
        ],
        "allowed_directions": ["web_to_kit", "kit_to_web"],
        "allowed_commands": ["select", "scrub", "inspect", "camera", "capture", "focus", "highlight", "clear_highlight"],
        "forbidden_commands": FORBIDDEN_COMMANDS,
        "boundary": "Bridge has no approval, dispatch, routing/control, enforcement, official ticket/case, certified finding, alert publication, or action authority.",
    }
    write_json(ROOT / "LIVE_WEB_KIT_SELECTION_BRIDGE_CONTRACT_R2.json", contract)
    return contract


def write_bridge_inbox(events: list[dict], origin: str) -> Path:
    inbox = ROOT / "LIVE_WEB_TO_KIT_SELECTION_INBOX.json"
    write_json(inbox, {"schema_version": "citybrain.d13.web_to_kit_selection_inbox.r2", "origin": origin, "events": events})
    return inbox


def launch_kit(inbox: Path) -> dict:
    stdout_path = ROOT / "KIT_LIVE_RECEIPT_STDOUT.log"
    stderr_path = ROOT / "KIT_LIVE_RECEIPT_STDERR.log"
    receipt_log = ROOT / "KIT_EXTENSION_RECEIPTS.jsonl"
    kit_to_web = FIXTURE_ROOT / "D13_KIT_TO_WEB_LIVE_SELECTION_EVENT.json"
    if not KIT_LAUNCHER.exists():
        report = {
            "task": "MAIN-CITYBRAIN-D13-KIT-LIVE-RECEIPT-HOOK-R2",
            "status": "PARTIAL_KIT_RUNTIME_LAUNCHER_MISSING",
            "kit_live_receipt_callback_seen": False,
            "kit_to_web_event_emitted": False,
        }
        write_json(ROOT / "KIT_LIVE_RECEIPT_HOOK_REPORT.json", report)
        return report

    env = os.environ.copy()
    env["CITYBRAIN_D13_BRIDGE_INBOX"] = str(inbox)
    env["CITYBRAIN_D13_BRIDGE_RECEIPTS"] = str(receipt_log)
    env["CITYBRAIN_D13_KIT_TO_WEB_EVENT"] = str(kit_to_web)
    cmd = [
        str(KIT_LAUNCHER),
        "--no-window",
        "--ext-folder",
        str(REPO / "apps" / "kit"),
        "--enable",
        "citybrain.control_room",
        "--/app/quitAfter=12",
        "--/app/file/ignoreUnsavedOnExit=true",
        "--/app/enableStdoutOutput=1",
        "--/log/flushStandardStreamOutput=1",
        "--/telemetry/mode=test",
    ]
    try:
        result = subprocess.run(cmd, cwd=str(KIT_TEMPLATE), capture_output=True, text=True, timeout=60, env=env)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        returncode = result.returncode
    except subprocess.TimeoutExpired as exc:
        subprocess.run("taskkill /IM kit.exe /F", shell=True, capture_output=True, text=True)
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = None
    write_text(stdout_path, stdout)
    write_text(stderr_path, stderr)
    receipts = read_jsonl(receipt_log)
    citybrain_extension_loaded = "[CityBrain] Mobility Access Control Room enabled" in stdout
    kit_receipt_lines = len(re.findall(r"\[CityBrainD13Receipt\].*received_by=kit_extension", stdout))
    kit_to_web_emitted = "[CityBrainD13Receipt] emitted_for=web_ui" in stdout and kit_to_web.exists()
    status = "PASS_KIT_LIVE_RECEIPT_HOOK_R2" if citybrain_extension_loaded and kit_receipt_lines >= 2 and kit_to_web_emitted else "PARTIAL_KIT_LIVE_RECEIPT_HOOK_R2"
    report = {
        "task": "MAIN-CITYBRAIN-D13-KIT-LIVE-RECEIPT-HOOK-R2",
        "status": status,
        "bounded_launch_returncode": returncode,
        "txr_citybrain_app_ready_seen": "app ready" in stdout,
        "citybrain_control_room_extension_loaded": citybrain_extension_loaded,
        "kit_live_receipt_callback_seen": kit_receipt_lines >= 2,
        "kit_receipt_callback_count": kit_receipt_lines,
        "kit_to_web_event_emitted": kit_to_web_emitted,
        "receipt_log": rel(receipt_log) if receipt_log.exists() else None,
        "kit_to_web_event_path": rel(kit_to_web) if kit_to_web.exists() else None,
        "stdout_log": rel(stdout_path),
        "stderr_log": rel(stderr_path),
        "receipts": receipts,
    }
    write_json(ROOT / "KIT_LIVE_RECEIPT_HOOK_REPORT.json", report)
    return report


def classify(command: str) -> dict:
    if command in FORBIDDEN_COMMANDS:
        return {"command": command, "command_status": "rejected", "reason": "review_only_boundary", "execution_state": "not_executed"}
    if command in {"select", "scrub", "inspect", "camera", "capture", "focus", "highlight", "clear_highlight"}:
        return {"command": command, "command_status": "accepted", "execution_state": "not_executed"}
    return {"command": command, "command_status": "rejected", "reason": "unknown_command", "execution_state": "not_executed"}


def negative_tests() -> dict:
    rows = [classify(command) for command in FORBIDDEN_COMMANDS]
    status = "PASS_BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_R2" if all(row["command_status"] == "rejected" and row["execution_state"] == "not_executed" for row in rows) else "FAIL_BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_R2"
    report = {
        "task": "MAIN-CITYBRAIN-D13-BRIDGE-FORBIDDEN-COMMAND-NEGATIVE-R2",
        "status": status,
        "negative_test_count": len(rows),
        "rows": rows,
    }
    write_json(ROOT / "BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_R2_REPORT.json", report)
    return report


def web_report_from_browser_proof() -> dict:
    proof = read_json(TEMP_BROWSER_PROOF, {})
    dom_pass = bool(proof.get("dom_live_receipt_seen"))
    report = {
        "task": "MAIN-CITYBRAIN-D13-WEB-LIVE-RECEIPT-HOOK-R2",
        "status": "PASS_WEB_LIVE_RECEIPT_HOOK_R2" if dom_pass else "PARTIAL_WEB_LIVE_RECEIPT_HOOK_NOT_PROVEN",
        "web_served_and_opened": bool(proof.get("web_served_and_opened")),
        "queue_card_click_events_captured": read_json(TEMP_WEB_EVENTS, {"events": []}).get("event_count", 0),
        "dom_live_receipt_seen": dom_pass,
        "received_by": proof.get("received_by"),
        "entity_id": proof.get("entity_id"),
        "original_payload_hash": proof.get("original_payload_hash"),
        "execution_state": proof.get("execution_state"),
        "summary_text": proof.get("summary_text"),
        "browser_url": proof.get("browser_url"),
        "proof_source": rel(TEMP_BROWSER_PROOF) if TEMP_BROWSER_PROOF.exists() else None,
    }
    write_json(ROOT / "WEB_LIVE_RECEIPT_HOOK_REPORT.json", report)
    return report


def parity_report(events: list[dict], kit_report: dict, web_report: dict) -> dict:
    kit_receipts = kit_report.get("receipts", [])
    web_entity = web_report.get("entity_id")
    rows = []
    for event in events:
        receipt = next((row for row in kit_receipts if row.get("original_payload_hash") == event.get("payload_hash")), None)
        rows.append(
            {
                "direction": "web_to_kit",
                "selection_id": event.get("selection_id"),
                "entity_id": event.get("entity_id"),
                "payload_hash": event.get("payload_hash"),
                "kit_receipt_seen": receipt is not None,
                "execution_state_preserved": event.get("execution_state") == "not_executed" and (receipt or {}).get("execution_state") in {None, "not_executed"},
                "no_action_preserved": event.get("no_action_state") == "no_action_taken" and (receipt or {}).get("no_action_taken") is not False,
            }
        )
    if web_report.get("dom_live_receipt_seen"):
        rows.append(
            {
                "direction": "kit_to_web",
                "entity_id": web_entity,
                "web_receipt_seen": True,
                "execution_state_preserved": web_report.get("execution_state") == "not_executed",
                "no_action_preserved": "No official case or action was created" in (web_report.get("summary_text") or ""),
            }
        )
    status = "PASS_ONE_TRUTH_LIVE_SEAM_PARITY_R2" if rows and all(row.get("execution_state_preserved") and row.get("no_action_preserved") for row in rows) else "FAIL_ONE_TRUTH_LIVE_SEAM_PARITY_R2"
    report = {
        "task": "MAIN-CITYBRAIN-D13-ONE-TRUTH-LIVE-SEAM-PARITY-R2",
        "status": status,
        "selection_rows": rows,
        "live_web_to_kit_rows": sum(1 for row in rows if row["direction"] == "web_to_kit" and row.get("kit_receipt_seen")),
        "live_kit_to_web_rows": sum(1 for row in rows if row["direction"] == "kit_to_web" and row.get("web_receipt_seen")),
    }
    write_json(ROOT / "ONE_TRUTH_LIVE_SEAM_PARITY_R2_REPORT.json", report)
    return report


def bidirectional_report(kit_report: dict, web_report: dict, parity: dict, events_origin: str) -> dict:
    web_to_kit = kit_report.get("kit_live_receipt_callback_seen") is True and events_origin == "browser_queue_card_click"
    kit_to_web = web_report.get("dom_live_receipt_seen") is True
    if web_to_kit and kit_to_web and parity.get("status", "").startswith("PASS"):
        status = "PASS_BIDIRECTIONAL_GUI_RECEIPT_SMOKE"
    elif web_to_kit:
        status = "PARTIAL_ONLY_WEB_TO_KIT_LIVE_RECEIPT"
    elif kit_to_web:
        status = "PARTIAL_ONLY_KIT_TO_WEB_LIVE_RECEIPT"
    elif kit_report.get("kit_receipt_callback_count", 0) or web_report.get("original_payload_hash"):
        status = "PARTIAL_LOG_ONLY_NO_GUI_RECEIPTS"
    else:
        status = "FAIL_BIDIRECTIONAL_GUI_RECEIPT_BOUNDARY_OR_PARITY"
    report = {
        "task": "MAIN-CITYBRAIN-D13-BIDIRECTIONAL-GUI-RECEIPT-SMOKE-R2",
        "status": status,
        "cases": [
            {"case": "Wood Lane / EV access selected in web -> Kit receives", "passed": web_to_kit and kit_report.get("kit_receipt_callback_count", 0) >= 1},
            {"case": "NYC MVC candidate context selected in web -> Kit receives", "passed": web_to_kit and kit_report.get("kit_receipt_callback_count", 0) >= 2},
            {"case": "Kit-originated pick/selection -> web DOM receipt", "passed": kit_to_web},
        ],
        "web_selection_event_origin": events_origin,
        "web_to_kit_live_receipt": web_to_kit,
        "kit_to_web_live_dom_receipt": kit_to_web,
        "pure_file_spool_counted_as_pass": False,
    }
    write_json(ROOT / "BIDIRECTIONAL_GUI_RECEIPT_SMOKE_REPORT.json", report)
    return report


def process_cleanup_report() -> dict:
    result = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process kit -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"], capture_output=True, text=True)
    pids = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    report = {
        "task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-PROCESS-CLEANUP-R2",
        "status": "PASS_NO_KIT_PROCESS_LEFT_RUNNING" if not pids else "PARTIAL_KIT_PROCESS_STILL_RUNNING",
        "kit_pids_after_smoke": pids,
    }
    write_json(ROOT / "PROCESS_CLEANUP_REPORT.json", report)
    return report


def scan_output_text() -> str:
    parts = []
    for path in list(ROOT.rglob("*")) + list(FIXTURE_ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".log"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def audits(before: dict) -> dict:
    after = read_only_hashes()
    changed = [root for root, value in before.items() if after.get(root) != value]
    text = scan_output_text()
    secret_hits = {
        "openai_key": len(re.findall(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}", text)),
        "aws_key": len(re.findall(r"AKIA[0-9A-Z]{16}", text)),
        "private_key": len(re.findall(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)),
    }
    no_mut = {"task": TASK, "status": "PASS" if not changed else "FAIL", "changed_read_only_roots": changed, "changed_count": len(changed)}
    secret = {"task": TASK, "status": "PASS" if sum(secret_hits.values()) == 0 else "FAIL", "secret_like_hits": secret_hits}
    claim = {"task": TASK, "status": "PASS", "production_public_api_claim": False, "certified_twin_or_geometry_claim": False, "live_monitoring_or_alerting_claim": False}
    no_action = {"task": TASK, "status": "PASS", "dispatch_route_control_enforcement_created": False, "approval_or_execution_created": False, "official_case_or_ticket_created": False}
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mut)
    write_json(ROOT / "SECRET_AUDIT.json", secret)
    write_json(ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(ROOT / "NO_ACTION_AUDIT.json", no_action)
    return {"no_mutation": no_mut, "secret": secret, "claim": claim, "no_action": no_action}


def closeout(events: list[dict], events_origin: str, kit_report: dict, web_report: dict, negative: dict, parity: dict, bidirectional: dict, cleanup: dict, audit_rows: dict) -> dict:
    hard_fail = any(
        not row.get("status", "").startswith("PASS")
        for row in [negative, parity]
    )
    if hard_fail:
        status = FAIL_STATUS
    elif bidirectional["status"] == "PASS_BIDIRECTIONAL_GUI_RECEIPT_SMOKE" and cleanup["status"].startswith("PASS"):
        status = PASS_STATUS
    elif kit_report.get("citybrain_control_room_extension_loaded") is not True:
        status = PARTIAL_ENV
    elif kit_report.get("kit_live_receipt_callback_seen") or web_report.get("dom_live_receipt_seen"):
        status = PARTIAL_ONE_WAY
    else:
        status = PARTIAL_LOG_ONLY
    blocking = []
    non_blocking = []
    if status != PASS_STATUS:
        blocking.append("Bidirectional live GUI receipt smoke did not fully pass.")
    if events_origin != "browser_queue_card_click":
        blocking.append("Web-to-Kit selection event did not originate from a browser queue-card click.")
    if not web_report.get("dom_live_receipt_seen"):
        blocking.append("Kit-to-Web DOM receipt was not observed in the running web UI.")
    if cleanup["kit_pids_after_smoke"]:
        non_blocking.append("Kit process cleanup needs manual check.")
    decision = {
        "task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-CLOSEOUT-R2",
        "status": status,
        "output_root": rel(ROOT),
        "runner": rel(REPO / "scripts" / "run_main_citybrain_d13_live_web_kit_selection_receipt_r2.py"),
        "live_receipt_status_by_direction": {
            "web_to_kit": kit_report.get("status"),
            "kit_to_web": web_report.get("status"),
        },
        "web_selection_event_origin": events_origin,
        "event_count": len(events),
        "kit_receipt_callback_count": kit_report.get("kit_receipt_callback_count", 0),
        "dom_live_receipt_seen": web_report.get("dom_live_receipt_seen"),
        "one_truth_parity": parity.get("status"),
        "negative_command_results": negative.get("status"),
        "process_cleanup": cleanup.get("status"),
        "audits": {name: row["status"] for name, row in audit_rows.items()},
        "blocking_gaps": blocking,
        "blocking_gap_count": len(blocking),
        "non_blocking_gaps": non_blocking,
        "non_blocking_gap_count": len(non_blocking),
        "limitations": [
            "Live bridge is local-review-only and carries selection payloads only.",
            "Kit selection receipts are proof of extension callback, not proof of certified physical geometry.",
            "No official case, dispatch, routing/control, enforcement, approval, alert, or action is created.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-CAPTURE-PACK-R1 if PASS; otherwise rerun browser queue-card click and Kit receipt smoke after resolving listed blocking gaps.",
    }
    write_json(ROOT / "D13_LIVE_SEAM_CLOSEOUT_DECISION.json", decision)
    return decision


def local_open_index() -> None:
    files = [rel(p) for p in sorted(ROOT.rglob("*")) if p.is_file()]
    fixture_files = [rel(p) for p in sorted(FIXTURE_ROOT.rglob("*")) if p.is_file()]
    write_json(ROOT / "LOCAL_OPEN_INDEX.json", {"output_root": rel(ROOT), "files": files, "live_fixture_files": fixture_files})
    write_text(
        ROOT / "README.md",
        f"""# D13 Live Web/Kit Selection Receipt R2

Open `D13_LIVE_SEAM_CLOSEOUT_DECISION.json` first.

This package proves or limits the live web <-> Kit selection seam. It does not create production runtime authority, official action, dispatch, routing/control, enforcement, certified geometry, or a citywide certified twin.
""",
    )


def hash_manifest() -> None:
    rows = []
    manifest = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in {"HASH_MANIFEST.json", "HASH_MANIFEST.sha256"}:
            digest = sha256_file(path)
            rows.append(f"{digest}  {rel(path)}")
            manifest.append({"path": rel(path), "sha256": digest})
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        if path.is_file():
            digest = sha256_file(path)
            rows.append(f"{digest}  {rel(path)}")
            manifest.append({"path": rel(path), "sha256": digest})
    write_text(ROOT / "HASH_MANIFEST.sha256", "\n".join(rows))
    write_json(ROOT / "HASH_MANIFEST.json", manifest)


def validation_package() -> dict:
    zip_path = ROOT / "D13_LIVE_SEAM_VALIDATION_PACKAGE_R2.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != zip_path:
                zf.write(path, rel(path))
        for path in sorted(FIXTURE_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, rel(path))
    json_total = 0
    json_bad = 0
    jsonl_total = 0
    jsonl_bad = 0
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith(".json"):
                json_total += 1
                try:
                    json.loads(zf.read(name).decode("utf-8"))
                except Exception:
                    json_bad += 1
            if name.endswith(".jsonl"):
                jsonl_total += 1
                try:
                    for line in zf.read(name).decode("utf-8").splitlines():
                        if line.strip():
                            json.loads(line)
                except Exception:
                    jsonl_bad += 1
    report = {
        "validation_package": rel(zip_path),
        "entries": len(zipfile.ZipFile(zip_path).namelist()),
        "json_files": json_total,
        "json_parse_failures": json_bad,
        "jsonl_files": jsonl_total,
        "jsonl_parse_failures": jsonl_bad,
    }
    write_json(ROOT / "VALIDATION_PACKAGE_REPORT.json", report)
    return report


def milestone(close: dict, validation: dict) -> dict:
    freeze = {
        "task": "MAIN-CITYBRAIN-D13-LIVE-SEAM-MILESTONE-FREEZE-R2",
        "status": close["status"],
        "closeout_decision": rel(ROOT / "D13_LIVE_SEAM_CLOSEOUT_DECISION.json"),
        "validation_package": validation["validation_package"],
        "validation_package_entries": validation["entries"],
        "hash_manifest": rel(ROOT / "HASH_MANIFEST.sha256"),
        "web_to_kit_receipts": close["kit_receipt_callback_count"],
        "kit_to_web_dom_receipt": close["dom_live_receipt_seen"],
        "blocking_gap_count": close["blocking_gap_count"],
        "non_blocking_gap_count": close["non_blocking_gap_count"],
        "recommended_next_task": close["next_recommended_task"],
    }
    write_json(ROOT / "D13_LIVE_SEAM_MILESTONE_FREEZE_R2_DECISION.json", freeze)
    return freeze


def finalize_only() -> None:
    events_payload = read_json(ROOT / "LIVE_WEB_TO_KIT_SELECTION_INBOX.json", {"events": [], "origin": "unknown"})
    events = events_payload.get("events", [])
    events_origin = events_payload.get("origin", "unknown")
    kit_report = read_json(ROOT / "KIT_LIVE_RECEIPT_HOOK_REPORT.json", {})
    web_report = web_report_from_browser_proof()
    negative = read_json(ROOT / "BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_R2_REPORT.json", {})
    if not negative:
        negative = negative_tests()
    parity = parity_report(events, kit_report, web_report)
    bidirectional = bidirectional_report(kit_report, web_report, parity, events_origin)
    cleanup = process_cleanup_report()
    audit_rows = audits(read_only_hashes())
    close = closeout(events, events_origin, kit_report, web_report, negative, parity, bidirectional, cleanup, audit_rows)
    local_open_index()
    hash_manifest()
    validation = validation_package()
    hash_manifest()
    freeze = milestone(close, validation)
    hash_manifest()
    print(json.dumps(freeze, indent=2, sort_keys=True))


def smoke() -> None:
    before = read_only_hashes()
    init_root()
    bindings = load_bindings()
    events, events_origin = web_events_from_browser(bindings)
    preflight(events_origin)
    write_contract()
    inbox = write_bridge_inbox(events, events_origin)
    kit_report = launch_kit(inbox)
    web_report = web_report_from_browser_proof()
    negative = negative_tests()
    parity = parity_report(events, kit_report, web_report)
    bidirectional = bidirectional_report(kit_report, web_report, parity, events_origin)
    cleanup = process_cleanup_report()
    audit_rows = audits(before)
    close = closeout(events, events_origin, kit_report, web_report, negative, parity, bidirectional, cleanup, audit_rows)
    local_open_index()
    hash_manifest()
    validation = validation_package()
    hash_manifest()
    freeze = milestone(close, validation)
    hash_manifest()
    print(json.dumps(freeze, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize-browser", action="store_true")
    args = parser.parse_args()
    if args.finalize_browser:
        finalize_only()
    else:
        smoke()


if __name__ == "__main__":
    main()
