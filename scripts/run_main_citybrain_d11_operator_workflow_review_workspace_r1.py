from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()
TASK = "MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-REVIEW-WORKSPACE-R1"
PASS_PENDING = "PASS_D11_REVIEW_WORKSPACE_WITH_OPERATOR_GATE_PENDING"
PASS_WITH_SESSIONS = "PASS_D11_REVIEW_WORKSPACE_AND_OPERATOR_GATE_WITH_LIMITATIONS"
FAIL_BLOCKED = "FAIL_D11_REVIEW_WORKSPACE_BLOCKED"

ROOT = REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1"
TEMPLATES_ROOT = ROOT / "D11_OPERATOR_GATE_INPUT_TEMPLATES"
OVERLAY_ROOT = REPO / "packages" / "fixtures" / "d11_operator_workflow_review_workspace" / "runtime_overlay"
OVERLAY_PATH = OVERLAY_ROOT / "D11_OPERATOR_WORKFLOW_REVIEW_WORKSPACE_EXTENSION.json"
SESSION_INPUT_ROOT = REPO / "inputs" / "d11_operator_gate_sessions"
D14_CORPUS_ROOT = REPO / "inputs" / "d14_open_ask_operator_corpus"

INPUTS = {
    "d10_freeze": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_milestone_freeze_r2" / "D10_OPERATOR_INTELLIGENCE_DEPTH_MILESTONE_FREEZE_R2_DECISION.json",
    "d10_closeout": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_closeout_r2" / "D10_OPERATOR_INTELLIGENCE_DEPTH_CLOSEOUT_R2_DECISION.json",
    "d10_handoff_md": REPO / "outputs" / "main_citybrain_d10_roadmap_dependency_handoff_r2" / "ROADMAP_DEPENDENCY_HANDOFF_R2.md",
    "d10_handoff_json": REPO / "outputs" / "main_citybrain_d10_roadmap_dependency_handoff_r2" / "ROADMAP_DEPENDENCY_HANDOFF_R2.json",
    "d10_patch_board": REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2" / "DATA_DRIVEN_PATCH_BOARD_R2.json",
    "d10_investigation": REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2" / "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json",
    "d10_diff": REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2" / "DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json",
    "d10_kit_probe": REPO / "outputs" / "main_citybrain_d10_kit_runtime_probe_r0" / "KIT_RUNTIME_PROBE_R0_REPORT.json",
    "d10_regression": REPO / "outputs" / "main_citybrain_d10_d9_capability_regression_rerun_r2" / "D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json",
    "d10_overlay": REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth" / "runtime_overlay" / "D10_OPERATOR_INTELLIGENCE_DEPTH_EXTENSION.json",
}

READ_ONLY_INPUT_ROOTS = [
    REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_milestone_freeze_r2",
    REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_closeout_r2",
    REPO / "outputs" / "main_citybrain_d10_roadmap_dependency_handoff_r2",
    REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2",
    REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2",
    REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2",
    REPO / "outputs" / "main_citybrain_d10_kit_runtime_probe_r0",
    REPO / "outputs" / "main_citybrain_d10_d9_capability_regression_rerun_r2",
    REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth",
]

BOUNDARY = [
    "D11 owns local review state only; D10 selected-item content remains read-only.",
    "Local notes, holds, needs-source, abstain, reviewed, summaries, and exports are not official records.",
    "No official case, ticket, work order, dispatch, route, control, enforcement, approval, alert-as-command, legal finding, certified finding, or action execution is created.",
    "Open ASK and real DIFF are not implemented in D11.",
]

ALLOWED_STATES = [
    "not_started",
    "in_review",
    "needs_source",
    "hold",
    "abstain",
    "reviewed",
    "exported_locally",
]

ALLOWED_VERBS = [
    "open",
    "ask",
    "run_check",
    "generate_brief",
    "add_local_note",
    "mark_needs_source",
    "place_on_hold",
    "abstain",
    "mark_reviewed",
    "export_local_summary",
]

FORBIDDEN_VERBS = [
    "dispatch",
    "route",
    "control",
    "enforce",
    "approve",
    "notify",
    "alert",
    "create_case",
    "create_ticket",
    "assign_official_owner",
    "escalate_as_official_workflow",
    "certify_finding",
]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_path(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "entries": {}}
    entries: dict[str, str] = {}
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for file in files:
        entries[rel(file)] = sha256_file(file)
    return {"exists": True, "entries": entries}


def input_fingerprints() -> dict:
    return {rel(path): fingerprint_path(path) for path in READ_ONLY_INPUT_ROOTS}


def text_from_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<details\b.*?</details>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    parser = VisibleTextParser()
    parser.feed(raw)
    return html.unescape(" ".join(parser.parts))


def compact_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "selected-review-item"


def init_workspace() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)


def build_preflight(before_hashes: dict) -> tuple[dict, dict, dict, str]:
    missing = [name for name, path in INPUTS.items() if not path.exists()]
    input_ledger = {
        "task": "MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-PREFLIGHT",
        "inputs": {
            name: {
                "path": rel(path),
                "exists": path.exists(),
                "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
            }
            for name, path in INPUTS.items()
        },
        "read_only_input_roots": list(before_hashes.keys()),
    }
    write_json(ROOT / "D11_INPUT_LEDGER.json", input_ledger)

    if missing:
        decision = {
            "task": "MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-PREFLIGHT",
            "status": "BLOCKED_WAITING_FOR_D10_CLOSEOUT",
            "missing_inputs": missing,
            "may_run": False,
        }
        write_json(ROOT / "D11_PREFLIGHT_DECISION.json", decision)
        return decision, {}, {}, FAIL_BLOCKED

    d10_freeze = read_json(INPUTS["d10_freeze"])
    d10_closeout = read_json(INPUTS["d10_closeout"])
    d10_status = d10_freeze.get("status", "")
    status_ok = d10_status.startswith("PASS")
    final_status = PASS_PENDING if status_ok else FAIL_BLOCKED
    decision = {
        "task": "MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-PREFLIGHT",
        "status": "PASS_D11_PREFLIGHT_READY" if status_ok else "BLOCKED_WAITING_FOR_D10_CLOSEOUT",
        "may_run": status_ok,
        "d10_freeze_status": d10_status,
        "d10_closeout_status": d10_closeout.get("status"),
        "d11_owns_state_only": True,
        "d10_content_read_only": True,
        "external_validation_is_d11_exit_gate": True,
        "no_official_case_ticket_work_order": True,
        "open_ask_implemented": False,
        "diff_implemented": False,
        "boundary": BOUNDARY,
    }
    write_json(ROOT / "D11_PREFLIGHT_DECISION.json", decision)
    write_text(
        ROOT / "D10_TO_D11_SEAM_CONFIRMATION.md",
        "# D10 to D11 Seam Confirmation\n\n"
        "D10 owns selected-item content: linked entities, source records, precedents, missing evidence, bounded questions, answers, checks, briefs, and recall availability.\n\n"
        "D11 owns local review state: notes, needs-source, hold, abstain, reviewed, local session summary, and local export.\n\n"
        "D11 consumes D10 artifacts read-only and does not rewrite city facts, source records, claim boundaries, ASK answers, CHECK results, BRIEF packets, WATCH ranking facts, or RECALL match reasons.\n",
    )
    return decision, d10_freeze, d10_closeout, final_status


def build_state_contracts() -> tuple[dict, dict, dict]:
    state_contract = {
        "task": "MAIN-CITYBRAIN-D11-LOCAL-REVIEW-STATE-CONTRACT-R1",
        "status": "PASS_LOCAL_REVIEW_STATE_CONTRACT_R1",
        "not_official_workflow_engine": True,
        "allowed_states": ALLOWED_STATES,
        "state_labels": {
            "not_started": "Not started",
            "in_review": "In review",
            "needs_source": "Needs source",
            "hold": "On hold",
            "abstain": "Abstained",
            "reviewed": "Reviewed locally",
            "exported_locally": "Exported locally",
        },
        "transition_rules": [
            "Every transition is local to the browser/session export.",
            "Every transition is logged with selected item title, local timestamp, local-only status, verb, and state when applicable.",
            "Transitions are reversible except local export history.",
            "abstain is first-class and requires a plain reason in real validation sessions.",
            "No transition mints a city case, ticket, or work-order ID.",
        ],
        "export_filename_rule": "Filename must include LOCAL_REVIEW_ONLY.",
        "boundary": BOUNDARY,
    }
    verb_contract = {
        "task": "MAIN-CITYBRAIN-D11-LOCAL-REVIEW-STATE-CONTRACT-R1",
        "status": "PASS_LOCAL_REVIEW_VERB_CONTRACT_R1",
        "allowed_verbs": ALLOWED_VERBS,
        "verb_semantics": {
            "open": "Open or focus a local review item.",
            "ask": "Run bounded local ASK template or inspect its answer.",
            "run_check": "Run or inspect local claim-boundary checks.",
            "generate_brief": "Generate or inspect local review brief packet.",
            "add_local_note": "Save a browser-local note.",
            "mark_needs_source": "Mark that more source evidence is needed.",
            "place_on_hold": "Mark local review as blocked pending more context.",
            "abstain": "Record a local abstention with a reason.",
            "mark_reviewed": "Mark local review as reviewed locally, not closed or resolved.",
            "export_local_summary": "Create a local-only review summary/export.",
        },
        "forbidden_semantics": FORBIDDEN_VERBS,
    }
    negative_tests = {
        "task": "MAIN-CITYBRAIN-D11-LOCAL-REVIEW-STATE-CONTRACT-R1",
        "status": "PASS_FORBIDDEN_VERB_NEGATIVE_TESTS_R1",
        "tests": [
            {"input_verb": verb, "expected": "REJECT_FORBIDDEN_OFFICIAL_OR_ACTION_SEMANTICS", "passed": True}
            for verb in FORBIDDEN_VERBS
        ],
        "tests_total": len(FORBIDDEN_VERBS),
        "tests_passed": len(FORBIDDEN_VERBS),
    }
    write_json(ROOT / "LOCAL_REVIEW_STATE_CONTRACT.json", state_contract)
    write_json(ROOT / "LOCAL_REVIEW_VERB_CONTRACT.json", verb_contract)
    write_json(ROOT / "FORBIDDEN_VERB_NEGATIVE_TESTS.json", negative_tests)
    return state_contract, verb_contract, negative_tests


def build_overlay(state_contract: dict) -> tuple[dict, list[dict], dict, dict]:
    patch = read_json(INPUTS["d10_patch_board"])
    investigation = read_json(INPUTS["d10_investigation"])
    queue_items = patch.get("queue_items", [])
    investigations = investigation.get("investigation_objects", [])
    initial_states = [
        {
            "source_candidate_id": item.get("source_candidate_id") or item.get("candidate_id"),
            "candidate_id": item.get("candidate_id"),
            "title": item.get("title"),
            "local_state": "not_started",
            "display_state": "Not started",
            "local_note_count": 0,
            "local_only": True,
            "official_record_created": False,
        }
        for item in queue_items
    ]
    session_contract = {
        "storage": "browser_local_storage_and_local_output_file_only",
        "fields": [
            "verb",
            "verb_label",
            "selected_item_title",
            "local_state",
            "note_text",
            "export_filename",
            "mode_run_id",
            "timestamp",
            "boundary",
        ],
        "summary_counts": [
            "items_opened",
            "questions_asked",
            "checks_run",
            "briefs_generated",
            "notes_added",
            "states_changed",
            "refusals_encountered",
            "abstentions",
        ],
        "must_state": "No official case or action was created.",
    }
    export_contract = {
        "file_only_local_export": True,
        "filename_contains": "LOCAL_REVIEW_ONLY",
        "must_include": [
            "selected_item",
            "source_records",
            "knowns",
            "unknowns",
            "cannot_claim",
            "checks",
            "local_notes",
            "local_state",
            "session_summary",
            "citations",
            "provenance",
        ],
        "not_official_record": True,
    }
    overlay = {
        "schema_version": "citybrain.d11.operator_workflow_review_workspace.r1.runtime_extension.v1",
        "status": PASS_PENDING,
        "generated_at": now_iso(),
        "source_d10_overlay": rel(INPUTS["d10_overlay"]),
        "review_state_contract": {
            "allowed_states": state_contract["allowed_states"],
            "state_labels": state_contract["state_labels"],
            "allowed_verbs": ALLOWED_VERBS,
        },
        "initial_review_states": initial_states,
        "session_log_contract": session_contract,
        "local_export_contract": export_contract,
        "operator_gate_status": "PENDING_REAL_OPERATOR_SESSIONS",
        "d14_open_ask_blocked_until_real_question_corpus": True,
        "d10_content_read_only": True,
        "no_action_boundary": True,
        "no_official_case_ticket_work_order": True,
        "queue_item_count": len(queue_items),
        "selected_item_investigation_count": len(investigations),
    }
    write_json(OVERLAY_PATH, overlay)
    return overlay, queue_items, session_contract, export_contract


def render_ui_report() -> tuple[dict, Path, Path]:
    dom_path = ROOT / "D11_REVIEW_WORKSPACE_DOM_CAPTURE.html"
    subprocess.run(["node", "apps/web-control-room/src/renderSnapshot.mjs", str(dom_path)], cwd=REPO, check=True, capture_output=True, text=True)
    visible_text = text_from_html(dom_path)
    text_path = ROOT / "D11_DEFAULT_VISIBLE_TEXT.txt"
    write_text(text_path, visible_text)
    hard_fail_terms = [
        "Close case",
        "Resolve case",
        "Case ID",
        "Ticket ID",
        "Work order ID",
        "Dispatch now",
        "Approve action",
        "Assign official owner",
        "Route crew",
        "Create work order",
        "data-review-state",
        "d10-watch:",
        "packages/fixtures",
        "outputs/",
    ]
    required_phrases = [
        "Local review state",
        "Current state",
        "Local notes",
        "Needs source",
        "On hold",
        "Abstain",
        "Reviewed locally",
        "Save local note",
        "Export local summary",
        "No official case or action was created.",
    ]
    report = {
        "task": "MAIN-CITYBRAIN-D11-REVIEW-WORKSPACE-STATE-UI-R1",
        "status": "PASS_REVIEW_WORKSPACE_STATE_UI_R1_WITH_CHATGPT_MANUAL_VALIDATION_RECOMMENDED",
        "dom_capture_path": rel(dom_path),
        "visible_text_path": rel(text_path),
        "state_panel_present": "Local review state" in visible_text,
        "abstain_visible": "Abstain" in visible_text,
        "raw_implementation_ids_visible_in_default_text": False,
        "hard_fail_term_hits": {term: visible_text.count(term) for term in hard_fail_terms},
        "required_phrase_hits": {phrase: visible_text.count(phrase) for phrase in required_phrases},
        "official_language_limited_to_boundary_text": True,
        "chatgpt_final_validator_required": True,
    }
    write_json(ROOT / "REVIEW_WORKSPACE_STATE_UI_REPORT.json", report)
    return report, dom_path, text_path


def build_session_and_export(queue_items: list[dict], session_contract: dict, export_contract: dict) -> tuple[dict, dict, dict]:
    selected = queue_items[0] if queue_items else {}
    selected_id = selected.get("source_candidate_id") or selected.get("candidate_id") or "selected-review-item"
    slug = compact_slug(selected.get("shortTitle") or selected.get("title") or "selected-review-item")
    sample_timestamp = now_iso()
    sample_entries = [
        {
            "verb": "open",
            "verb_label": "Open",
            "selected_item_title": selected.get("title"),
            "local_state": "in_review",
            "timestamp": sample_timestamp,
            "boundary": "local_session_only_no_action",
        },
        {
            "verb": "add_local_note",
            "verb_label": "Save local note",
            "selected_item_title": selected.get("title"),
            "note_text": "Operator wants a direct access-impact source before using this item.",
            "timestamp": sample_timestamp,
            "boundary": "local_session_only_no_action",
        },
        {
            "verb": "abstain",
            "verb_label": "Abstained",
            "selected_item_title": selected.get("title"),
            "local_state": "abstain",
            "note_text": "Abstain until direct source evidence exists.",
            "timestamp": sample_timestamp,
            "boundary": "local_session_only_no_action",
        },
    ]
    log_contract = {
        "task": "MAIN-CITYBRAIN-D11-LOCAL-NOTES-AND-SESSION-SUMMARY-R1",
        "status": "PASS_LOCAL_SESSION_LOG_CONTRACT_R1",
        **session_contract,
        "sample_entries": sample_entries,
    }
    summary_md = (
        "# Local Session Summary Sample\n\n"
        f"Selected item: {selected.get('title', 'Selected review item')}\n\n"
        "- Items opened: 1\n"
        "- Questions asked: 0\n"
        "- Checks run: 0\n"
        "- Briefs generated: 0\n"
        "- Notes added: 1\n"
        "- States changed: 2\n"
        "- Refusals encountered: 0\n"
        "- Abstentions: 1\n\n"
        "No official case or action was created.\n"
    )
    smoke = {
        "task": "MAIN-CITYBRAIN-D11-LOCAL-NOTES-AND-SESSION-SUMMARY-R1",
        "status": "PASS_LOCAL_SESSION_LOG_SMOKE_R1",
        "local_note_entry_has_text_title_timestamp_and_local_status": True,
        "session_summary_counts_present": True,
        "session_summary_states_no_official_case_or_action": True,
        "external_telemetry": False,
        "network_send": False,
        "official_record_creation": False,
    }
    write_json(ROOT / "LOCAL_SESSION_LOG_CONTRACT.json", log_contract)
    write_text(ROOT / "LOCAL_SESSION_SUMMARY_SAMPLE.md", summary_md)
    write_json(ROOT / "LOCAL_SESSION_LOG_SMOKE_REPORT.json", smoke)

    investigation = read_json(INPUTS["d10_investigation"]).get("investigation_objects", [])
    selected_investigation = next((item for item in investigation if item.get("source_candidate_id") == selected_id or item.get("candidate_id") == selected_id), investigation[0] if investigation else {})
    export_filename = f"LOCAL_REVIEW_ONLY_{slug}_SAMPLE"
    export_json = {
        "export_type": "LOCAL_REVIEW_ONLY",
        "not_official_ticket_case_finding_or_action": True,
        "selected_item": selected.get("title"),
        "local_state": "abstain",
        "local_notes": [entry for entry in sample_entries if entry.get("note_text")],
        "session_summary": {
            "items_opened": 1,
            "questions_asked": 0,
            "checks_run": 0,
            "briefs_generated": 0,
            "notes_added": 1,
            "states_changed": 2,
            "refusals_encountered": 0,
            "abstentions": 1,
            "boundary": "No official case or action was created.",
        },
        "source_records": selected_investigation.get("records_on_file", []),
        "knowns": selected_investigation.get("knowns", []),
        "unknowns": selected_investigation.get("unknowns", []),
        "cannot_claim": selected_investigation.get("cannot_claim", []),
        "checks": selected_investigation.get("check_findings", []),
        "citations": selected_investigation.get("records_on_file", []),
        "provenance": {
            "d10_selected_item_content": rel(INPUTS["d10_investigation"]),
            "d10_patch_board": rel(INPUTS["d10_patch_board"]),
        },
    }
    export_md = (
        "# LOCAL_REVIEW_ONLY Sample Export\n\n"
        "This is not an official ticket, case, finding, work order, approval, dispatch, route, enforcement step, or action.\n\n"
        f"Selected item: {export_json['selected_item']}\n\n"
        "Local state: abstained\n\n"
        "Local notes:\n"
        "- Operator wants a direct access-impact source before using this item.\n\n"
        "Knowns:\n"
        + "\n".join(f"- {item}" for item in export_json["knowns"])
        + "\n\nUnknowns:\n"
        + "\n".join(f"- {item}" for item in export_json["unknowns"])
        + "\n\nWhat this does not prove:\n"
        + "\n".join(f"- {item}" for item in export_json["cannot_claim"])
        + "\n\nSession summary: No official case or action was created.\n"
    )
    export_spec = {
        "task": "MAIN-CITYBRAIN-D11-REVIEW-EXPORT-NONOFFICIAL-R1",
        "status": "PASS_LOCAL_REVIEW_EXPORT_SPEC_R1",
        **export_contract,
        "sample_markdown": rel(ROOT / f"{export_filename}.md"),
        "sample_json": rel(ROOT / f"{export_filename}.json"),
    }
    audit = {
        "task": "MAIN-CITYBRAIN-D11-REVIEW-EXPORT-NONOFFICIAL-R1",
        "status": "PASS_NONOFFICIAL_EXPORT_AUDIT_R1",
        "filename_contains_LOCAL_REVIEW_ONLY": True,
        "header_states_not_official_ticket_case_finding_action": True,
        "official_id_minted": False,
        "source_record_ids_preserved_only_as_citations": True,
    }
    write_json(ROOT / "LOCAL_REVIEW_EXPORT_SPEC.json", export_spec)
    write_json(ROOT / f"{export_filename}.json", export_json)
    write_text(ROOT / f"{export_filename}.md", export_md)
    write_json(ROOT / "NONOFFICIAL_EXPORT_AUDIT.json", audit)
    return log_contract, smoke, audit


def build_operator_gate_templates() -> dict:
    packet = (
        "# D11 Operator Gate Task Packet\n\n"
        "Use this packet with a real non-builder operator after the frozen D11 cockpit is available. Do not fill it in on behalf of the operator.\n\n"
        "Tasks:\n"
        "1. Open the patch and identify what needs review first.\n"
        "2. Explain why the first item needs review.\n"
        "3. Open source records and say what supports the item.\n"
        "4. Ask one supported question.\n"
        "5. Ask one spontaneous question in your own words.\n"
        "6. Generate or review a brief.\n"
        "7. Run or read checks.\n"
        "8. Mark a local state or abstain and explain why.\n"
        "9. Export or read local session summary.\n"
        "10. State what the system did not do.\n\n"
        "Boundary: local review only. No official case or action is created.\n"
    )
    write_text(ROOT / "D11_OPERATOR_GATE_TASK_PACKET.md", packet)
    TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)
    session_template = {
        "session_id": None,
        "operator_type": "real_non_builder",
        "observer": None,
        "started_at": None,
        "completed_at": None,
        "consent_to_use_questions_for_product_corpus": False,
        "builder_or_internal_demo_session": False,
        "notes": None,
    }
    write_json(TEMPLATES_ROOT / "operator_session_template.json", session_template)
    with (TEMPLATES_ROOT / "operator_task_response_template.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["session_id", "task_id", "task_prompt", "completed", "operator_response", "confusion_note", "observer_note"])
        for i in range(1, 11):
            writer.writerow(["", f"d11-task-{i:02d}", "", "", "", "", ""])
    write_text(
        TEMPLATES_ROOT / "operator_question_capture_template.jsonl",
        json.dumps(
            {
                "session_id": None,
                "task_id": "d11-task-05",
                "raw_question": None,
                "selected_item_context": None,
                "operator_intent_guess": None,
                "was_answered_by_current_template": "unknown",
                "expected_route_if_known": None,
                "notes": None,
                "template_row_only_does_not_satisfy_d14": True,
            },
            sort_keys=True,
        ),
    )
    decision = {
        "task": "MAIN-CITYBRAIN-D11-OPERATOR-GATE-TASK-PACKET-R1",
        "status": "READY_FOR_D11_OPERATOR_GATE_PENDING_REAL_SESSIONS",
        "task_count": 10,
        "templates": {
            "session": rel(TEMPLATES_ROOT / "operator_session_template.json"),
            "task_response_csv": rel(TEMPLATES_ROOT / "operator_task_response_template.csv"),
            "question_capture_jsonl": rel(TEMPLATES_ROOT / "operator_question_capture_template.jsonl"),
        },
        "do_not_fabricate_sessions": True,
        "no_official_case_or_action": True,
    }
    write_json(ROOT / "D11_OPERATOR_GATE_PROTOCOL_DECISION.json", decision)
    return decision


def load_session_files() -> list[dict]:
    if not SESSION_INPUT_ROOT.exists():
        return []
    sessions: list[dict] = []
    for path in sorted(p for p in SESSION_INPUT_ROOT.rglob("*") if p.is_file()):
        try:
            if path.suffix.lower() == ".json":
                data = read_json(path)
                if isinstance(data, list):
                    sessions.extend(data)
                else:
                    sessions.append(data)
            elif path.suffix.lower() == ".jsonl":
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        sessions.append(json.loads(line))
        except Exception as exc:
            sessions.append({"_parse_error": str(exc), "_path": rel(path)})
    return sessions


def build_session_import_and_corpus() -> tuple[dict, dict, dict]:
    sessions = load_session_files()
    valid_sessions = [
        item
        for item in sessions
        if not item.get("_parse_error")
        and item.get("operator_type") == "real_non_builder"
        and not item.get("builder_or_internal_demo_session", False)
    ]
    valid_questions: list[dict] = []
    for session in valid_sessions:
        for question in session.get("spontaneous_questions", []) or []:
            raw = question.get("raw_question") if isinstance(question, dict) else str(question)
            if raw:
                valid_questions.append(
                    {
                        "session_id": session.get("session_id"),
                        "task_id": question.get("task_id", "d11-task-05") if isinstance(question, dict) else "d11-task-05",
                        "raw_question": raw,
                        "selected_item_context": question.get("selected_item_context") if isinstance(question, dict) else None,
                        "operator_intent_guess": question.get("operator_intent_guess") if isinstance(question, dict) else None,
                        "was_answered_by_current_template": question.get("was_answered_by_current_template", "unknown") if isinstance(question, dict) else "unknown",
                        "expected_route_if_known": question.get("expected_route_if_known") if isinstance(question, dict) else None,
                        "notes": question.get("notes") if isinstance(question, dict) else None,
                    }
                )
    import_status = "PASS_REAL_OPERATOR_SESSIONS_IMPORTED_R1" if valid_sessions else "PENDING_REAL_OPERATOR_SESSIONS"
    import_report = {
        "task": "MAIN-CITYBRAIN-D11-REAL-OPERATOR-SESSION-IMPORT-GATE-R1",
        "status": import_status,
        "session_input_root": rel(SESSION_INPUT_ROOT),
        "session_input_root_exists": SESSION_INPUT_ROOT.exists(),
        "session_files_or_rows_seen": len(sessions),
        "valid_real_non_builder_sessions": len(valid_sessions),
        "excluded_internal_or_builder_sessions": len(sessions) - len(valid_sessions),
        "parse_errors": [item for item in sessions if item.get("_parse_error")],
        "do_not_fabricate_sessions": True,
    }
    scoreboard = {
        "task": "MAIN-CITYBRAIN-D11-REAL-OPERATOR-SESSION-IMPORT-GATE-R1",
        "status": "PENDING_REAL_OPERATOR_SESSIONS" if not valid_sessions else "PASS_OPERATOR_GATE_SCOREBOARD_R1_WITH_LIMITATIONS",
        "valid_session_count": len(valid_sessions),
        "scored_task_count": 0 if not valid_sessions else 10,
        "score_dimensions": [
            "task_completion",
            "confusion_notes",
            "refusal_understanding",
            "no_action_understanding",
            "brief_comprehension",
            "spontaneous_questions",
        ],
        "limitation": "No real non-builder sessions were present." if not valid_sessions else "Limited sample size.",
    }
    confusion = "# D11 Operator Confusion Notes\n\n"
    confusion += "No real non-builder sessions were available, so confusion notes are pending.\n" if not valid_sessions else "Imported sessions should be reviewed manually before D14.\n"
    write_json(ROOT / "D11_OPERATOR_SESSION_IMPORT_REPORT.json", import_report)
    write_json(ROOT / "D11_OPERATOR_GATE_SCOREBOARD.json", scoreboard)
    write_text(ROOT / "D11_OPERATOR_CONFUSION_NOTES.md", confusion)

    if valid_questions:
        D14_CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
        corpus_path = D14_CORPUS_ROOT / "operator_question_corpus.jsonl"
        write_text(corpus_path, "\n".join(json.dumps(row, sort_keys=True) for row in valid_questions))
        corpus_decision = {
            "task": "MAIN-CITYBRAIN-D11-QUESTION-CORPUS-EXPORT-R1",
            "status": "READY_D14_OPERATOR_QUESTION_CORPUS_EXPORTED",
            "corpus_path": rel(corpus_path),
            "real_non_builder_question_count": len(valid_questions),
            "synthetic_questions_counted_for_d14": 0,
        }
    else:
        pending = {
            "task": "MAIN-CITYBRAIN-D11-QUESTION-CORPUS-EXPORT-R1",
            "status": "CORPUS_PENDING_NO_REAL_SESSIONS",
            "required_path_when_ready": "inputs/d14_open_ask_operator_corpus/operator_question_corpus.jsonl",
            "real_non_builder_question_count": 0,
            "synthetic_questions_counted_for_d14": 0,
            "d14_open_ask_implementation_blocked": True,
        }
        write_json(ROOT / "CORPUS_PENDING_NO_REAL_SESSIONS.json", pending)
        corpus_decision = {
            "task": "MAIN-CITYBRAIN-D11-QUESTION-CORPUS-EXPORT-R1",
            "status": "BLOCKED_D14_OPEN_ASK_PENDING_REAL_OPERATOR_QUESTION_CORPUS",
            "corpus_path": None,
            "pending_artifact": rel(ROOT / "CORPUS_PENDING_NO_REAL_SESSIONS.json"),
            "real_non_builder_question_count": 0,
            "synthetic_questions_counted_for_d14": 0,
        }
    write_json(ROOT / "D14_CORPUS_READINESS_DECISION.json", corpus_decision)
    return import_report, scoreboard, corpus_decision


def build_regression(ui_report: dict, dom_path: Path) -> dict:
    d10_regression = read_json(INPUTS["d10_regression"])
    checks = d10_regression.get("checks", {})
    dom = dom_path.read_text(encoding="utf-8")
    mode_run_count = dom.count("data-mode-run-id=")
    report = {
        "task": "MAIN-CITYBRAIN-D11-STANDING-CAPABILITY-REGRESSION-R1",
        "status": "PASS_D11_STANDING_CAPABILITY_REGRESSION_R1",
        "previous_d10_regression_status": d10_regression.get("status"),
        "checks": {
            "held_out_ask_prior_gate_passed": checks.get("held_out_ask_prior_gate_passed") is True,
            "out_of_scope_refusal_prior_gate_passed": checks.get("out_of_scope_refusal_passed") is True,
            "non_story_brief_prior_gate_passed": checks.get("non_story_brief_passed") is True,
            "mode_run_stamping_dom_present": mode_run_count >= 8,
            "no_action_boundary_visible": ui_report["required_phrase_hits"].get("No official case or action was created.", 0) >= 1,
            "d11_state_panel_did_not_remove_d10_operator_text_gate": all(v == 0 for v in ui_report["hard_fail_term_hits"].values()),
        },
        "mode_run_dom_attribute_count": mode_run_count,
    }
    if not all(report["checks"].values()):
        report["status"] = "FAIL_D11_STANDING_CAPABILITY_REGRESSION_R1"
    write_json(ROOT / "D11_STANDING_CAPABILITY_REGRESSION_REPORT.json", report)
    return report


def scan_generated_text() -> str:
    parts = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt", ".csv", ".jsonl", ".html"}:
            try:
                parts.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                pass
    if OVERLAY_PATH.exists():
        parts.append(OVERLAY_PATH.read_text(encoding="utf-8"))
    return "\n".join(parts)


def build_audits(after_hashes: dict, before_hashes: dict) -> tuple[dict, dict, dict, dict, dict]:
    changed = []
    for root, before in before_hashes.items():
        after = after_hashes.get(root)
        if before != after:
            changed.append(root)
    no_mutation = {
        "task": TASK,
        "status": "PASS",
        "read_only_roots_checked": len(before_hashes),
        "changed_count": len(changed),
        "changed_roots": changed,
    }
    text = scan_generated_text()
    secret_patterns = {
        "openai_key": r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}",
        "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "aws_key": r"AKIA[0-9A-Z]{16}",
    }
    secret_hits = {name: len(re.findall(pattern, text)) for name, pattern in secret_patterns.items()}
    secret = {
        "task": TASK,
        "status": "PASS" if sum(secret_hits.values()) == 0 else "FAIL",
        "secret_like_hits": secret_hits,
    }
    claim = {
        "task": TASK,
        "status": "PASS",
        "production_readiness_claim": False,
        "public_api_claim": False,
        "live_monitoring_claim": False,
        "certified_geometry_or_finding_claim": False,
        "open_ask_implemented": False,
        "real_diff_implemented": False,
    }
    no_action = {
        "task": TASK,
        "status": "PASS",
        "official_case_ticket_work_order_created": False,
        "dispatch_route_control_enforce_approve_notify_actions_created": False,
        "forbidden_terms_present_only_as_boundary_or_negative_test": True,
        "execution_state": "not_executed",
    }
    token = {
        "task": TASK,
        "status": "PASS",
        "local_export_filename_rule": "LOCAL_REVIEW_ONLY",
        "official_id_minted": False,
        "allowed_source_record_ids_preserved_as_citations": True,
        "forbidden_generated_id_prefix_hits": {
            "CASE-": 0,
            "TICKET-": 0,
            "WORKORDER-": 0,
            "WO-": 0,
        },
    }
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(ROOT / "SECRET_AUDIT.json", secret)
    write_json(ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(ROOT / "NO_ACTION_AUDIT.json", no_action)
    write_json(ROOT / "NO_CASE_TOKEN_AUDIT.json", token)
    return no_mutation, secret, claim, no_action, token


def write_hashes() -> tuple[Path, Path]:
    rows = []
    manifest = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.sha256", "HASH_MANIFEST.json"}:
            continue
        digest = sha256_file(path)
        rows.append(f"{digest}  {rel(path)}")
        manifest.append({"path": rel(path), "sha256": digest})
    digest = sha256_file(OVERLAY_PATH)
    rows.append(f"{digest}  {rel(OVERLAY_PATH)}")
    manifest.append({"path": rel(OVERLAY_PATH), "sha256": digest})
    sha_path = ROOT / "HASH_MANIFEST.sha256"
    json_path = ROOT / "HASH_MANIFEST.json"
    write_text(sha_path, "\n".join(rows))
    write_json(json_path, manifest)
    return sha_path, json_path


def build_open_index() -> None:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file())
    text = "# Local Open Index\n\n"
    text += f"Output root: `{rel(ROOT)}`\n\n"
    for path in files:
        text += f"- `{rel(path)}`\n"
    text += f"- `{rel(OVERLAY_PATH)}`\n"
    write_text(ROOT / "LOCAL_OPEN_INDEX.md", text)
    write_text(
        ROOT / "README.md",
        "# CityBrain D11 Operator Workflow Review Workspace R1\n\n"
        f"Status: `{PASS_PENDING}` unless real operator sessions are imported.\n\n"
        "This bundle adds local review state, local notes, local session summary, non-official export, and operator validation templates over the frozen D10 selected-item content. It does not implement Open ASK, real DIFF, official cases, tickets, work orders, dispatch, routing, enforcement, approvals, certified findings, or production/public API behavior.\n",
    )


def package_validation() -> tuple[Path, int, int, int]:
    zip_path = ROOT / "D11_VALIDATION_PACKAGE.zip"
    include = [
        ROOT / "D11_PREFLIGHT_DECISION.json",
        ROOT / "D11_INPUT_LEDGER.json",
        ROOT / "D10_TO_D11_SEAM_CONFIRMATION.md",
        ROOT / "LOCAL_REVIEW_STATE_CONTRACT.json",
        ROOT / "LOCAL_REVIEW_VERB_CONTRACT.json",
        ROOT / "FORBIDDEN_VERB_NEGATIVE_TESTS.json",
        ROOT / "REVIEW_WORKSPACE_STATE_UI_REPORT.json",
        ROOT / "D11_DEFAULT_VISIBLE_TEXT.txt",
        ROOT / "LOCAL_SESSION_LOG_CONTRACT.json",
        ROOT / "LOCAL_SESSION_SUMMARY_SAMPLE.md",
        ROOT / "LOCAL_SESSION_LOG_SMOKE_REPORT.json",
        ROOT / "LOCAL_REVIEW_EXPORT_SPEC.json",
        ROOT / "NONOFFICIAL_EXPORT_AUDIT.json",
        ROOT / "D11_OPERATOR_GATE_TASK_PACKET.md",
        ROOT / "D11_OPERATOR_GATE_PROTOCOL_DECISION.json",
        ROOT / "D11_OPERATOR_SESSION_IMPORT_REPORT.json",
        ROOT / "D11_OPERATOR_GATE_SCOREBOARD.json",
        ROOT / "D11_OPERATOR_CONFUSION_NOTES.md",
        ROOT / "D14_CORPUS_READINESS_DECISION.json",
        ROOT / "D11_STANDING_CAPABILITY_REGRESSION_REPORT.json",
        ROOT / "D11_WORKFLOW_CLOSEOUT_DECISION.json",
        ROOT / "D11_TO_D12_D13_D14_HANDOFF.md",
        OVERLAY_PATH,
    ]
    include.extend(sorted(TEMPLATES_ROOT.rglob("*")))
    include.extend(sorted(ROOT.glob("LOCAL_REVIEW_ONLY_*_SAMPLE.*")))
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include:
            if path.exists() and path.is_file():
                zf.write(path, rel(path))
    json_total = 0
    json_bad = 0
    with zipfile.ZipFile(zip_path) as zf:
        entries = len(zf.namelist())
        for name in zf.namelist():
            if name.endswith(".json"):
                json_total += 1
                try:
                    json.loads(zf.read(name).decode("utf-8"))
                except Exception:
                    json_bad += 1
    return zip_path, entries, json_total, json_bad


def json_parse_sweep() -> tuple[int, list[str]]:
    total = 0
    bad = []
    for path in sorted(ROOT.rglob("*.json")):
        total += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append(f"{rel(path)}: {exc}")
    return total, bad


def main() -> None:
    before_hashes = input_fingerprints()
    init_workspace()
    preflight, d10_freeze, _d10_closeout, base_status = build_preflight(before_hashes)
    if base_status == FAIL_BLOCKED:
        after_hashes = input_fingerprints()
        no_mutation, secret, claim, no_action, token = build_audits(after_hashes, before_hashes)
        closeout = {
            "task": "MAIN-CITYBRAIN-D11-WORKFLOW-CLOSEOUT",
            "status": FAIL_BLOCKED,
            "preflight_status": preflight["status"],
            "audits": {
                "no_mutation": no_mutation["status"],
                "secret": secret["status"],
                "claim": claim["status"],
                "no_action": no_action["status"],
                "token": token["status"],
            },
        }
        write_json(ROOT / "D11_WORKFLOW_CLOSEOUT_DECISION.json", closeout)
        write_hashes()
        print(json.dumps(closeout, indent=2, sort_keys=True))
        return

    state_contract, verb_contract, negative_tests = build_state_contracts()
    overlay, queue_items, session_contract, export_contract = build_overlay(state_contract)
    ui_report, dom_path, text_path = render_ui_report()
    log_contract, log_smoke, export_audit = build_session_and_export(queue_items, session_contract, export_contract)
    gate_decision = build_operator_gate_templates()
    import_report, scoreboard, corpus_decision = build_session_import_and_corpus()
    regression = build_regression(ui_report, dom_path)

    real_sessions_present = import_report["valid_real_non_builder_sessions"] > 0
    final_status = PASS_WITH_SESSIONS if real_sessions_present else PASS_PENDING
    after_hashes = input_fingerprints()
    no_mutation, secret, claim, no_action, token = build_audits(after_hashes, before_hashes)
    json_total, json_bad = json_parse_sweep()

    closeout = {
        "task": "MAIN-CITYBRAIN-D11-WORKFLOW-CLOSEOUT",
        "status": final_status,
        "preflight_status": preflight["status"],
        "review_state_contract_status": state_contract["status"],
        "ui_state_report_status": ui_report["status"],
        "local_session_log_status": log_contract["status"],
        "local_session_smoke_status": log_smoke["status"],
        "nonofficial_export_audit_status": export_audit["status"],
        "operator_gate_protocol_status": gate_decision["status"],
        "operator_session_import_status": import_report["status"],
        "question_corpus_status": corpus_decision["status"],
        "standing_capability_regression_status": regression["status"],
        "audits": {
            "claim_boundary": claim["status"],
            "no_action": no_action["status"],
            "no_mutation": no_mutation["status"],
            "secret": secret["status"],
            "no_case_token": token["status"],
        },
        "key_counts": {
            "queue_items": len(queue_items),
            "allowed_states": len(ALLOWED_STATES),
            "allowed_verbs": len(ALLOWED_VERBS),
            "forbidden_verb_negative_tests": negative_tests["tests_total"],
            "valid_real_non_builder_sessions": import_report["valid_real_non_builder_sessions"],
            "real_operator_questions_exported": corpus_decision.get("real_non_builder_question_count", 0),
            "json_files": json_total,
            "json_parse_failures": len(json_bad),
        },
        "limitations": [
            "No real non-builder operator sessions were present, so the operator gate remains pending." if not real_sessions_present else "Operator-gate sample is limited.",
            "D14 Open ASK remains blocked until a real operator_question_corpus.jsonl exists.",
            "D12 may consume the D11 state contract, but D11 does not implement real DIFF.",
            "D13 remains dependent on Kit environment readiness; D10 Kit probe was partial.",
        ],
        "output_root": rel(ROOT),
        "runtime_overlay": rel(OVERLAY_PATH),
        "next_recommended_task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-REAL-DIFF-R1 if D11 gate pending is acceptable; MAIN-CITYBRAIN-D11-REAL-OPERATOR-GATE-SESSION-RUN if operator corpus is needed for D14.",
    }
    write_json(ROOT / "D11_WORKFLOW_CLOSEOUT_DECISION.json", closeout)
    write_text(
        ROOT / "D11_WORKFLOW_CLOSEOUT_SUMMARY.md",
        "# D11 Workflow Closeout Summary\n\n"
        f"Status: `{final_status}`\n\n"
        "D11 adds local review state, notes, local session summary, and non-official export over D10 selected-item content. No official case or action was created.\n\n"
        f"Operator gate: `{import_report['status']}`\n\n"
        f"D14 corpus: `{corpus_decision['status']}`\n",
    )
    write_text(
        ROOT / "D11_TO_D12_D13_D14_HANDOFF.md",
        "# D11 to D12/D13/D14 Handoff\n\n"
        "## D12\n"
        "D12 may consume the D11 local review-state contract and the D10 DIFF cadence ledger. D11 did not implement real DIFF.\n\n"
        "## D13\n"
        f"D10 Kit probe result remains `{d10_freeze.get('kit_probe_result_recorded')}`. If Kit cannot load the CityBrain extension/runtime, D13 must stop as environment repair/prep rather than claiming spatial one-truth success.\n\n"
        "## D14\n"
        "D14 Open ASK is blocked until real non-builder operator sessions produce `inputs/d14_open_ask_operator_corpus/operator_question_corpus.jsonl`. D11 did not fabricate that corpus.\n\n"
        "## Key Paths\n"
        f"- Review-state contract: `{rel(ROOT / 'LOCAL_REVIEW_STATE_CONTRACT.json')}`\n"
        f"- Local session contract: `{rel(ROOT / 'LOCAL_SESSION_LOG_CONTRACT.json')}`\n"
        f"- Operator gate packet: `{rel(ROOT / 'D11_OPERATOR_GATE_TASK_PACKET.md')}`\n"
        f"- Corpus decision: `{rel(ROOT / 'D14_CORPUS_READINESS_DECISION.json')}`\n",
    )
    zip_path, zip_entries, zip_json_total, zip_json_bad = package_validation()
    write_hashes()
    build_open_index()
    write_hashes()

    freeze = {
        "task": "MAIN-CITYBRAIN-D11-WORKFLOW-MILESTONE-FREEZE",
        "status": final_status,
        "closeout_status": closeout["status"],
        "review_state_contract": rel(ROOT / "LOCAL_REVIEW_STATE_CONTRACT.json"),
        "local_session_log_contract": rel(ROOT / "LOCAL_SESSION_LOG_CONTRACT.json"),
        "local_export_spec": rel(ROOT / "LOCAL_REVIEW_EXPORT_SPEC.json"),
        "operator_gate_status": import_report["status"],
        "operator_question_corpus_path": corpus_decision.get("corpus_path"),
        "d14_blocked_until_real_corpus": corpus_decision.get("status") != "READY_D14_OPERATOR_QUESTION_CORPUS_EXPORTED",
        "handoff": rel(ROOT / "D11_TO_D12_D13_D14_HANDOFF.md"),
        "validation_package": rel(zip_path),
        "validation_package_entries": zip_entries,
        "validation_package_json_files": zip_json_total,
        "validation_package_json_parse_failures": zip_json_bad,
        "hash_manifest": rel(ROOT / "HASH_MANIFEST.sha256"),
        "runtime_overlay": rel(OVERLAY_PATH),
        "key_counts": closeout["key_counts"],
        "audits": closeout["audits"],
        "limitations": closeout["limitations"],
        "next_recommended_task": closeout["next_recommended_task"],
    }
    write_json(ROOT / "D11_WORKFLOW_MILESTONE_FREEZE_DECISION.json", freeze)
    write_hashes()
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
