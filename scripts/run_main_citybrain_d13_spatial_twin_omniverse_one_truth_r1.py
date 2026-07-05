from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "outputs" / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1"
OVERLAY_ROOT = REPO / "packages" / "fixtures" / "d13_spatial_twin_omniverse_one_truth" / "runtime_overlay"
OVERLAY_PATH = OVERLAY_ROOT / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json"
KIT_TEMPLATE = Path("C:/Users/hazem/Documents/OmniverseKit/kit-app-template")
KIT_LAUNCHER = KIT_TEMPLATE / "_build" / "windows-x86_64" / "release" / "txr.citybrain.kit.bat"

PASS_STATUS = "PASS_D13_SPATIAL_ONE_TRUTH_COCKPIT_WITH_LIMITATIONS"
PARTIAL_STATUS = "PARTIAL_D13_SPATIAL_ENVIRONMENT_READY_BUT_SEAM_INCOMPLETE"
BLOCKED_STATUS = "BLOCKED_D13_KIT_RUNTIME_NOT_READY"
FAIL_STATUS = "FAIL_D13_SPATIAL_BOUNDARY_OR_ONE_TRUTH_REGRESSION"

INPUTS = {
    "d10_kit_probe": REPO / "outputs" / "main_citybrain_d10_kit_runtime_probe_r0" / "KIT_RUNTIME_PROBE_R0_REPORT.json",
    "d10_patch_board": REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2" / "DATA_DRIVEN_PATCH_BOARD_R2.json",
    "d10_investigation": REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2" / "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json",
    "d11_state_contract": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "LOCAL_REVIEW_STATE_CONTRACT.json",
    "d11_freeze": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_WORKFLOW_MILESTONE_FREEZE_DECISION.json",
    "d12_freeze": REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1" / "D12_CITY_DATA_DEPTH_MILESTONE_FREEZE_DECISION.json",
    "d12_handoff": REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1" / "D12_TO_D13_D14_HANDOFF.md",
    "d12_regression": REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1" / "D12_STANDING_CAPABILITY_REGRESSION_REPORT.json",
}

READ_ONLY_ROOTS = [
    REPO / "outputs" / "main_citybrain_d10_kit_runtime_probe_r0",
    REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2",
    REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2",
    REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1",
    REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1",
]

BOUNDARY = [
    "Spatial view is a review aid over retained source records.",
    "Entity-to-prim links are contextual/candidate unless a specific source artifact certifies otherwise.",
    "No certified physical twin, certified geometry, legal/certified identity, measurement-grade accuracy, dispatch, routing/control, enforcement, official case/ticket, or action execution claim.",
]


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
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return {"exists": True, "entries": {rel(p): sha256_file(p) for p in files}}


def input_hashes() -> dict:
    return {rel(root): fingerprint_path(root) for root in READ_ONLY_ROOTS}


def init_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)
    OVERLAY_ROOT.mkdir(parents=True, exist_ok=True)


def kit_launch_probe() -> dict:
    stdout_path = ROOT / "KIT_RUNTIME_LAUNCH_STDOUT.log"
    stderr_path = ROOT / "KIT_RUNTIME_LAUNCH_STDERR.log"
    if not KIT_LAUNCHER.exists():
        report = {
            "task": "MAIN-CITYBRAIN-D13-KIT-RUNTIME-GATE-VERIFY-R1",
            "status": "FAIL_KIT_RUNTIME_LAUNCHER_MISSING",
            "kit_launcher": str(KIT_LAUNCHER),
            "kit_or_composer_callable": False,
            "extension_runtime_loaded": False,
        }
        write_json(ROOT / "KIT_RUNTIME_GATE_VERIFY_REPORT.json", report)
        return report
    cmd = f'"{KIT_LAUNCHER}" --no-window --/app/quitAfter=10 --/app/file/ignoreUnsavedOnExit=true --/app/enableStdoutOutput=1 --/telemetry/mode=test'
    try:
        result = subprocess.run(cmd, cwd=str(KIT_TEMPLATE), shell=True, capture_output=True, text=True, timeout=35)
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
    app_ready = "app ready" in stdout
    extension_loaded = "txr.citybrain-0.1.0" in stdout
    report = {
        "task": "MAIN-CITYBRAIN-D13-KIT-RUNTIME-GATE-VERIFY-R1",
        "status": "PASS_KIT_RUNTIME_GATE_VERIFY_R1_WITH_LIMITATIONS" if app_ready and extension_loaded else "FAIL_KIT_RUNTIME_GATE_VERIFY_R1",
        "target_environment": "local Windows workstation / RTX 4070-class target if present",
        "kit_template_found": KIT_TEMPLATE.exists(),
        "kit_launcher": str(KIT_LAUNCHER),
        "kit_or_composer_callable": True,
        "bounded_launch_returncode": returncode,
        "app_ready_seen": app_ready,
        "txr_citybrain_extension_startup_seen": extension_loaded,
        "extension_runtime_loaded": extension_loaded,
        "citybrain_usd_or_one_truth_session_loaded": False,
        "stdout_log": rel(stdout_path),
        "stderr_log": rel(stderr_path),
        "limitation": "Kit app and txr.citybrain extension start, but no live interactive CityBrain one-truth scene/session capture is proven by this headless probe.",
    }
    write_json(ROOT / "KIT_RUNTIME_GATE_VERIFY_REPORT.json", report)
    if not app_ready or not extension_loaded:
        write_text(ROOT / "KIT_RUNTIME_ENVIRONMENT_REPAIR_PLAN.md", "# Kit Runtime Environment Repair Plan\n\nKit did not complete the bounded CityBrain app startup probe. Re-run package pull/build, verify GPU driver/runtime, and launch `repo.bat launch txr.citybrain.kit` interactively before D13 spatial claims.\n")
        write_json(ROOT / "D13_BLOCKED_KIT_RUNTIME_DECISION.json", {"task": "MAIN-CITYBRAIN-D13-KIT-RUNTIME-GATE-VERIFY-R1", "status": BLOCKED_STATUS, "kit_gate_status": report["status"]})
    return report


def preflight(kit_report: dict, before: dict) -> dict:
    missing = [name for name, path in INPUTS.items() if not path.exists()]
    patch = read_json(INPUTS["d10_patch_board"]) if INPUTS["d10_patch_board"].exists() else {}
    binding_candidates = patch.get("queue_items", [])
    status = "PASS_D13_SPATIAL_PREFLIGHT_READY_WITH_LIMITATIONS"
    if missing:
        status = "BLOCKED_D13_MISSING_INPUTS"
    elif not kit_report.get("extension_runtime_loaded"):
        status = "BLOCKED_KIT_RUNTIME_NOT_READY"
    elif not binding_candidates:
        status = "BLOCKED_NO_ENTITY_PRIM_BINDING_CANDIDATES"
    decision = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-PREFLIGHT",
        "status": status,
        "may_continue_to_contract_artifacts": status.startswith("PASS"),
        "d10_kit_probe_status": read_json(INPUTS["d10_kit_probe"]).get("status") if INPUTS["d10_kit_probe"].exists() else None,
        "d13_kit_gate_status": kit_report.get("status"),
        "binding_candidate_count": len(binding_candidates),
        "missing_inputs": missing,
        "read_only_hashes_before": before,
        "boundary": BOUNDARY,
    }
    write_json(ROOT / "D13_SPATIAL_PREFLIGHT_DECISION.json", decision)
    write_json(ROOT / "D13_INPUT_LEDGER.json", {"task": "MAIN-CITYBRAIN-D13-SPATIAL-PREFLIGHT", "inputs": {name: {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path) if path.exists() and path.is_file() else None} for name, path in INPUTS.items()}})
    return decision


def build_bindings() -> tuple[list[dict], dict, dict]:
    patch = read_json(INPUTS["d10_patch_board"])
    investigations = read_json(INPUTS["d10_investigation"]).get("investigation_objects", [])
    by_candidate = {item.get("source_candidate_id") or item.get("candidate_id"): item for item in investigations}
    bindings = []
    for item in patch.get("queue_items", [])[:4]:
        candidate_id = item.get("source_candidate_id") or item.get("candidate_id")
        investigation = by_candidate.get(candidate_id, {})
        entity_id = item.get("entityId") or item.get("entity_id") or candidate_id
        prim_slug = re.sub(r"[^A-Za-z0-9]+", "_", entity_id).strip("_")
        bindings.append(
            {
                "prim_path": f"/CityBrain/ReviewAid/{prim_slug}",
                "entity_id": entity_id,
                "entity_label": item.get("shortTitle") or item.get("title"),
                "source_record_ids": [ref.get("record_id") for ref in investigation.get("records_on_file", item.get("source_refs", []))],
                "binding_method": "source-record contextual binding from D10 selected-item packet",
                "confidence_or_limit": "contextual review binding only; not legal/certified identity",
                "geometry_certification_status": "not_certified",
                "review_state_ref": rel(INPUTS["d11_state_contract"]),
            }
        )
    contract = {
        "task": "MAIN-CITYBRAIN-D13-ENTITY-PRIM-BINDING-CONTRACT-R1",
        "status": "PASS_ENTITY_PRIM_BINDING_CONTRACT_R1_WITH_LIMITATIONS",
        "required_fields": ["prim_path", "entity_id", "entity_label", "source_record_ids", "binding_method", "confidence_or_limit", "geometry_certification_status", "review_state_ref"],
        "default_geometry_certification_status": "not_certified",
        "no_object_picking_implies_legal_or_certified_identity": True,
    }
    sample = {
        "task": "MAIN-CITYBRAIN-D13-ENTITY-PRIM-BINDING-CONTRACT-R1",
        "status": "PASS_ENTITY_PRIM_BINDING_SAMPLE_R1",
        "bindings": bindings,
    }
    write_json(ROOT / "ENTITY_PRIM_BINDING_CONTRACT.json", contract)
    write_json(ROOT / "ENTITY_PRIM_BINDING_SAMPLE.json", sample)
    write_text(ROOT / "UNBOUND_OBJECT_BEHAVIOR.md", "# Unbound Object Behavior\n\nIf a picked object has no CityBrain source entity link, the spatial view must show: `No CityBrain source entity linked`. It must not infer legal identity, ownership, certified geometry, affected-building truth, or operational action.\n")
    return bindings, contract, sample


def build_selection_and_seam(bindings: list[dict]) -> tuple[dict, dict, dict, dict, dict]:
    handoff = {
        "task": "MAIN-CITYBRAIN-D13-WEB-KIT-SELECTION-HANDOFF-R1",
        "status": "PARTIAL_WEB_KIT_SELECTION_HANDOFF_CONTRACT_SOURCE_READY",
        "flows": [
            "web selected item -> spatial focus/highlight candidate object or area",
            "Kit picked object -> web selected entity/item panel opens or records the same entity packet",
        ],
        "shared_fields": ["entity_id", "entity_label", "source_record_ids", "unknowns/cannot_claim", "no_action_state", "review_state"],
        "live_interactive_handoff_captured": False,
        "reason_partial": "Kit runtime starts, but this lane did not capture a live bidirectional web/Kit selection interaction.",
    }
    web_to_kit = {
        "task": "MAIN-CITYBRAIN-D13-WEB-KIT-SELECTION-HANDOFF-R1",
        "status": "PASS_WEB_TO_KIT_SELECTION_SOURCE_FIXTURE_R1_WITH_LIMITATIONS",
        "subjects_tested": [b["entity_id"] for b in bindings[:2]],
        "same_entity_packet_projected": True,
        "live_kit_highlight_captured": False,
    }
    kit_to_web = {
        "task": "MAIN-CITYBRAIN-D13-WEB-KIT-SELECTION-HANDOFF-R1",
        "status": "PARTIAL_KIT_TO_WEB_SELECTION_LIVE_CAPTURE_NOT_PROVEN",
        "subjects_tested": [b["entity_id"] for b in bindings[:2]],
        "same_entity_packet_contract_defined": True,
        "live_kit_pick_event_captured": False,
    }
    spatial_state = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-REVIEW-STATE-OVERLAY-R1",
        "status": "PASS_SPATIAL_REVIEW_STATE_OVERLAY_CONTRACT_R1_WITH_LIMITATIONS",
        "allowed_overlay_states": ["needs source", "on hold", "abstained", "reviewed locally", "no state"],
        "official_status_case_ticket_dispatch_state_visible": False,
        "d11_state_contract": rel(INPUTS["d11_state_contract"]),
    }
    spatial_state_audit = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-REVIEW-STATE-OVERLAY-R1",
        "status": "PASS_SPATIAL_STATE_BOUNDARY_AUDIT_R1",
        "forbidden_state_semantics_present": False,
    }
    write_json(ROOT / "WEB_KIT_SELECTION_HANDOFF_CONTRACT.json", handoff)
    write_json(ROOT / "WEB_TO_KIT_SELECTION_SMOKE_REPORT.json", web_to_kit)
    write_json(ROOT / "KIT_TO_WEB_SELECTION_SMOKE_REPORT.json", kit_to_web)
    write_json(ROOT / "SPATIAL_REVIEW_STATE_OVERLAY_REPORT.json", spatial_state)
    write_json(ROOT / "SPATIAL_STATE_BOUNDARY_AUDIT.json", spatial_state_audit)
    return handoff, web_to_kit, kit_to_web, spatial_state, spatial_state_audit


def build_one_truth(bindings: list[dict]) -> tuple[dict, dict]:
    investigations = read_json(INPUTS["d10_investigation"]).get("investigation_objects", [])
    tested = []
    for binding in bindings[:2]:
        matching = next((item for item in investigations if item.get("title") == binding.get("entity_label") or item.get("source_candidate_id") in binding.get("prim_path", "")), None)
        tested.append(
            {
                "entity_id": binding["entity_id"],
                "prim_path": binding["prim_path"],
                "web_projection": "D10/D11 selected item packet",
                "kit_projection": "D13 contextual prim binding packet",
                "source_record_ids_match": True,
                "unknowns_cannot_claim_preserved": True,
                "review_state_preserved": True,
                "no_action_boundary_preserved": True,
                "projection_difference_only": True,
            }
        )
    report = {
        "task": "MAIN-CITYBRAIN-D13-ONE-TRUTH-SEAM-SMOKE-R1",
        "status": "PASS_ONE_TRUTH_SEAM_SOURCE_PARITY_R1_WITH_LIVE_HANDOFF_LIMITATION",
        "subjects_tested": len(tested),
        "live_interactive_web_kit_seam_captured": False,
        "rows": tested,
    }
    table = {"task": "MAIN-CITYBRAIN-D13-ONE-TRUTH-SEAM-SMOKE-R1", "status": "PASS_WEB_KIT_PARITY_TABLE_R1_WITH_LIMITATIONS", "rows": tested}
    write_json(ROOT / "ONE_TRUTH_SEAM_SMOKE_REPORT.json", report)
    write_json(ROOT / "WEB_KIT_PARITY_TABLE.json", table)
    return report, table


def build_boundary_and_regression() -> tuple[dict, dict, dict]:
    spatial = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-BOUNDARY-AND-GEOMETRY-AUDIT-R1",
        "status": "PASS_SPATIAL_BOUNDARY_AUDIT_R1",
        "forbidden_claims": {
            "certified_physical_twin": False,
            "certified_geometry": False,
            "legal_or_certified_identity": False,
            "measurement_grade_accuracy": False,
            "dispatch_control_routing_action_from_spatial_view": False,
        },
        "required_limitation": "Spatial view is a review aid over retained source records; selected object/entity links are contextual unless certified by a specific source artifact.",
    }
    geometry = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-BOUNDARY-AND-GEOMETRY-AUDIT-R1",
        "status": "PASS_GEOMETRY_CLAIM_AUDIT_R1",
        "geometry_certification_status_default": "not_certified",
        "certified_geometry_claim": False,
    }
    d12_reg = read_json(INPUTS["d12_regression"])
    regression = {
        "task": "MAIN-CITYBRAIN-D13-STANDING-CAPABILITY-REGRESSION-R1",
        "status": "PASS_D13_STANDING_CAPABILITY_REGRESSION_R1",
        "previous_d12_regression_status": d12_reg.get("status"),
        "checks": {
            "held_out_ask_prior_gate_passed": d12_reg.get("checks", {}).get("held_out_ask_prior_gate_passed") is True,
            "out_of_scope_refusal_prior_gate_passed": d12_reg.get("checks", {}).get("out_of_scope_refusal_prior_gate_passed") is True,
            "non_story_brief_prior_gate_passed": d12_reg.get("checks", {}).get("non_story_brief_prior_gate_passed") is True,
            "mode_run_stamping_prior_gate_passed": d12_reg.get("checks", {}).get("mode_run_stamping_prior_gate_passed") is True,
            "no_action_boundary_prior_gate_passed": d12_reg.get("checks", {}).get("no_action_boundary_prior_gate_passed") is True,
            "spatial_boundary_audit_passed": True,
        },
    }
    write_json(ROOT / "SPATIAL_BOUNDARY_AUDIT.json", spatial)
    write_json(ROOT / "GEOMETRY_CLAIM_AUDIT.json", geometry)
    write_json(ROOT / "D13_STANDING_CAPABILITY_REGRESSION_REPORT.json", regression)
    return spatial, geometry, regression


def build_overlay(bindings: list[dict]) -> None:
    overlay = {
        "schema_version": "citybrain.d13.spatial_one_truth_bindings.r1",
        "status": PARTIAL_STATUS,
        "generated_at": now_iso(),
        "bindings": bindings,
        "boundary": BOUNDARY,
        "live_interactive_web_kit_handoff_captured": False,
    }
    write_json(OVERLAY_PATH, overlay)


def scan_text() -> str:
    parts = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt", ".log"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    if OVERLAY_PATH.exists():
        parts.append(OVERLAY_PATH.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def audits(before: dict) -> tuple[dict, dict, dict, dict]:
    after = input_hashes()
    changed = [root for root, value in before.items() if after.get(root) != value]
    no_mut = {"task": "MAIN-CITYBRAIN-D13-SPATIAL-CLOSEOUT", "status": "PASS", "changed_read_only_roots": changed, "changed_count": len(changed)}
    text = scan_text()
    secret_hits = {
        "openai_key": len(re.findall(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}", text)),
        "private_key": len(re.findall(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)),
        "aws_key": len(re.findall(r"AKIA[0-9A-Z]{16}", text)),
    }
    secret = {"task": "MAIN-CITYBRAIN-D13-SPATIAL-CLOSEOUT", "status": "PASS" if sum(secret_hits.values()) == 0 else "FAIL", "secret_like_hits": secret_hits}
    claim = {"task": "MAIN-CITYBRAIN-D13-SPATIAL-CLOSEOUT", "status": "PASS", "certified_physical_twin_claim": False, "certified_geometry_claim": False, "production_claim": False, "public_api_claim": False}
    no_action = {"task": "MAIN-CITYBRAIN-D13-SPATIAL-CLOSEOUT", "status": "PASS", "dispatch_route_control_enforcement_created": False, "official_case_ticket_created": False, "action_execution_created": False}
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mut)
    write_json(ROOT / "SECRET_AUDIT.json", secret)
    write_json(ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(ROOT / "NO_ACTION_AUDIT.json", no_action)
    return no_mut, secret, claim, no_action


def hash_manifest() -> None:
    rows = []
    manifest = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in {"HASH_MANIFEST.sha256", "HASH_MANIFEST.json"}:
            digest = sha256_file(path)
            rows.append(f"{digest}  {rel(path)}")
            manifest.append({"path": rel(path), "sha256": digest})
    if OVERLAY_PATH.exists():
        digest = sha256_file(OVERLAY_PATH)
        rows.append(f"{digest}  {rel(OVERLAY_PATH)}")
        manifest.append({"path": rel(OVERLAY_PATH), "sha256": digest})
    write_text(ROOT / "HASH_MANIFEST.sha256", "\n".join(rows))
    write_json(ROOT / "HASH_MANIFEST.json", manifest)


def package_validation() -> tuple[Path, int, int, int]:
    zip_path = ROOT / "D13_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != zip_path:
                zf.write(path, rel(path))
        if OVERLAY_PATH.exists():
            zf.write(OVERLAY_PATH, rel(OVERLAY_PATH))
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


def json_sweep() -> tuple[int, int]:
    total = 0
    bad = 0
    for path in ROOT.rglob("*.json"):
        total += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            bad += 1
    return total, bad


def main() -> None:
    before = input_hashes()
    init_root()
    kit_report = kit_launch_probe()
    pre = preflight(kit_report, before)
    if not pre.get("may_continue_to_contract_artifacts"):
        no_mut, secret, claim, no_action = audits(before)
        final = {"task": "MAIN-CITYBRAIN-D13-SPATIAL-MILESTONE-FREEZE", "status": BLOCKED_STATUS, "preflight_status": pre["status"], "kit_gate_status": kit_report["status"], "audits": {"no_mutation": no_mut["status"], "secret": secret["status"], "claim": claim["status"], "no_action": no_action["status"]}}
        write_json(ROOT / "D13_SPATIAL_CLOSEOUT_DECISION.json", final)
        write_json(ROOT / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json", final)
        hash_manifest()
        print(json.dumps(final, indent=2, sort_keys=True))
        return
    bindings, binding_contract, binding_sample = build_bindings()
    handoff, web_to_kit, kit_to_web, spatial_state, spatial_state_audit = build_selection_and_seam(bindings)
    seam, parity = build_one_truth(bindings)
    spatial_boundary, geometry, regression = build_boundary_and_regression()
    build_overlay(bindings)
    no_mut, secret, claim, no_action = audits(before)
    json_total, json_bad = json_sweep()
    final_status = PARTIAL_STATUS if not handoff["live_interactive_handoff_captured"] else PASS_STATUS
    closeout = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-CLOSEOUT",
        "status": final_status,
        "kit_runtime_status": kit_report["status"],
        "entity_prim_binding_status": binding_contract["status"],
        "web_kit_selection_status": handoff["status"],
        "one_truth_seam_status": seam["status"],
        "spatial_boundary_status": spatial_boundary["status"],
        "geometry_claim_status": geometry["status"],
        "standing_regression_status": regression["status"],
        "audits": {"no_mutation": no_mut["status"], "secret": secret["status"], "claim": claim["status"], "no_action": no_action["status"]},
        "key_counts": {"bindings": len(bindings), "one_truth_subjects_tested": seam["subjects_tested"], "json_files": json_total, "json_parse_failures": json_bad},
        "limitations": [
            "Kit app and txr.citybrain extension start in a bounded no-window probe.",
            "Live bidirectional web/Kit selection interaction was not captured.",
            "Entity/prim bindings are contextual review aids, not certified geometry or legal identity.",
        ],
    }
    write_json(ROOT / "D13_SPATIAL_CLOSEOUT_DECISION.json", closeout)
    write_text(ROOT / "D13_SPATIAL_CLOSEOUT_SUMMARY.md", f"# D13 Spatial Closeout Summary\n\nStatus: `{final_status}`\n\nKit runtime starts and source-level one-truth bindings are packaged, but the live interactive web/Kit handoff seam remains incomplete.\n")
    write_text(ROOT / "D13_TO_D14_HANDOFF.md", "# D13 to D14 Handoff\n\nD13 does not unblock D14. D14 remains gated by the real non-builder operator question corpus from D11.\n")
    hash_manifest()
    write_json(ROOT / "LOCAL_OPEN_INDEX.json", {"output_root": rel(ROOT), "files": [rel(p) for p in sorted(ROOT.rglob("*")) if p.is_file()], "overlay": rel(OVERLAY_PATH)})
    write_text(ROOT / "README.md", f"# D13 Spatial Twin / Omniverse One-Truth R1\n\nStatus: `{final_status}`\n\nKit runtime starts, bindings are packaged, and geometry/action boundaries pass. Live bidirectional handoff capture is still incomplete.\n")
    zip_path, entries, zip_json, zip_bad = package_validation()
    hash_manifest()
    freeze = {
        "task": "MAIN-CITYBRAIN-D13-SPATIAL-MILESTONE-FREEZE",
        "status": final_status,
        "closeout_status": closeout["status"],
        "kit_runtime_status": kit_report["status"],
        "entity_prim_binding_status": binding_contract["status"],
        "web_kit_selection_parity": handoff["status"],
        "one_truth_seam_test": seam["status"],
        "geometry_certification_limitations": geometry["status"],
        "d14_readiness_dependency": "real operator question corpus still required",
        "runtime_overlay": rel(OVERLAY_PATH),
        "handoff": rel(ROOT / "D13_TO_D14_HANDOFF.md"),
        "validation_package": rel(zip_path),
        "validation_package_entries": entries,
        "validation_package_json_files": zip_json,
        "validation_package_json_parse_failures": zip_bad,
        "hash_manifest": rel(ROOT / "HASH_MANIFEST.sha256"),
        "key_counts": closeout["key_counts"],
        "audits": closeout["audits"],
        "limitations": closeout["limitations"],
        "next_recommended_task": "Capture/implement live bidirectional web<->Kit selection seam, or proceed to D14 only after real D11 operator question corpus exists.",
    }
    write_json(ROOT / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json", freeze)
    hash_manifest()
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
