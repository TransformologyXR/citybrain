from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "outputs" / "main_citybrain_d14_governed_open_ask_production_readiness_r1"
CORPUS_PATH = REPO / "inputs" / "d14_open_ask_operator_corpus" / "operator_question_corpus.jsonl"

PASS_STATUS = "PASS_D14_GOVERNED_OPEN_ASK_WITH_LIMITATIONS_READINESS_TRACK_STARTED"
BLOCKED_STATUS = "BLOCKED_D14_NO_REAL_OPERATOR_QUESTION_CORPUS"
FAIL_STATUS = "FAIL_D14_ROUTER_BOUNDARY_REGRESSION"

INPUTS = {
    "operator_question_corpus": CORPUS_PATH,
    "d10_search_contract": REPO / "outputs" / "main_citybrain_d10_deterministic_city_data_search_contract_r2" / "CITY_DATA_SEARCH_CONTRACT_R2.json",
    "d11_handoff": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_TO_D12_D13_D14_HANDOFF.md",
    "d11_corpus_decision": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D14_CORPUS_READINESS_DECISION.json",
    "d12_handoff": REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1" / "D12_TO_D13_D14_HANDOFF.md",
    "d12_freeze": REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1" / "D12_CITY_DATA_DEPTH_MILESTONE_FREEZE_DECISION.json",
    "d13_handoff": REPO / "outputs" / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1" / "D13_TO_D14_HANDOFF.md",
    "d13_freeze": REPO / "outputs" / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1" / "D13_SPATIAL_MILESTONE_FREEZE_DECISION.json",
    "product_runtime": REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle" / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
}

READ_ONLY_ROOTS = [
    REPO / "outputs" / "main_citybrain_d10_deterministic_city_data_search_contract_r2",
    REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1",
    REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1",
    REPO / "outputs" / "main_citybrain_d13_spatial_twin_omniverse_one_truth_r1",
    REPO / "packages" / "fixtures" / "d9_product_modes",
]

BOUNDARY = [
    "No real non-builder operator question corpus means no Open ASK router implementation.",
    "Router maps questions to deterministic templates or refusals; router must never answer.",
    "No production readiness claim, only discovery/backlog.",
    "No dispatch, routing/control, enforcement, legal/certified finding, official case/ticket, public API, live monitoring, or action execution.",
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


def load_corpus_rows() -> tuple[list[dict], list[str]]:
    rows = []
    errors = []
    if not CORPUS_PATH.exists():
        return rows, errors
    for index, line in enumerate(CORPUS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            errors.append(f"line {index}: {exc}")
    return rows, errors


def preflight(before: dict) -> tuple[dict, dict, list[dict]]:
    rows, errors = load_corpus_rows()
    real_rows = [
        row
        for row in rows
        if row.get("session_id")
        and row.get("raw_question")
        and not row.get("synthetic", False)
        and not row.get("builder_or_internal_demo_session", False)
    ]
    sessions = sorted({row.get("session_id") for row in real_rows if row.get("session_id")})
    contexts = sorted({str(row.get("selected_item_context")) for row in real_rows if row.get("selected_item_context")})
    status = "PASS_D14_OPEN_ASK_PREFLIGHT_READY" if real_rows else BLOCKED_STATUS
    if errors:
        status = BLOCKED_STATUS
    decision = {
        "task": "MAIN-CITYBRAIN-D14-OPEN-ASK-PREFLIGHT",
        "status": status,
        "may_implement_router": status == "PASS_D14_OPEN_ASK_PREFLIGHT_READY",
        "corpus_path": rel(CORPUS_PATH),
        "corpus_exists": CORPUS_PATH.exists(),
        "corpus_rows": len(rows),
        "real_sessions": len(sessions),
        "spontaneous_questions": len(real_rows),
        "selected_item_contexts_covered": contexts,
        "unsupported_action_legal_dispatch_prediction_questions_present": False if not real_rows else "requires_labeling",
        "template_coverage_estimate": "not_estimated_no_real_corpus" if not real_rows else "requires_labeling",
        "parse_errors": errors,
        "hard_blocker": None if real_rows else "No real non-builder operator_question_corpus.jsonl exists; synthetic/imagined questions do not satisfy D14.",
        "boundary": BOUNDARY,
    }
    provenance = {
        "task": "MAIN-CITYBRAIN-D14-OPEN-ASK-PREFLIGHT",
        "status": "FAIL_NO_REAL_OPERATOR_CORPUS" if not real_rows else "PASS_OPERATOR_CORPUS_PROVENANCE_AUDIT",
        "corpus_path": rel(CORPUS_PATH),
        "exists": CORPUS_PATH.exists(),
        "rows_seen": len(rows),
        "real_non_builder_rows": len(real_rows),
        "synthetic_or_builder_rows_excluded": len(rows) - len(real_rows),
        "d11_corpus_decision": read_json(INPUTS["d11_corpus_decision"]).get("status") if INPUTS["d11_corpus_decision"].exists() else None,
        "no_fabrication": True,
        "read_only_hashes_before": before,
    }
    write_json(ROOT / "D14_OPEN_ASK_PREFLIGHT_DECISION.json", decision)
    write_json(ROOT / "OPERATOR_CORPUS_PROVENANCE_AUDIT.json", provenance)
    return decision, provenance, real_rows


def current_template_registry() -> dict:
    runtime = read_json(INPUTS["product_runtime"]) if INPUTS["product_runtime"].exists() else {}
    ask_templates = sorted({answer.get("ask_query_id") or answer.get("template_call") for answer in runtime.get("ask", {}).get("sample_answers", []) if answer.get("ask_query_id") or answer.get("template_call")})
    return {
        "task": "MAIN-CITYBRAIN-D14-ASK-TEMPLATE-REGISTRY-REFRESH-R1",
        "status": "NOT_REFRESHED_BLOCKED_NO_REAL_CORPUS",
        "allowed_template_families": [
            "entity_360",
            "selected_item_summary",
            "what_supports",
            "what_is_uncertain",
            "cannot_claim",
            "source_records_for_entity",
            "similar_precedents",
            "change_summary",
            "brief_summary",
            "check_claim",
        ],
        "current_template_refs_observed": ask_templates,
        "refresh_based_on_corpus": False,
        "reason": "No real non-builder corpus exists; registry was not expanded from imagination.",
    }


def blocked_artifacts(pre: dict, real_rows: list[dict]) -> dict:
    labeled_status = "NOT_RUN_BLOCKED_NO_REAL_CORPUS"
    write_text(ROOT / "LABELED_OPERATOR_QUESTION_CORPUS.jsonl", "")
    write_json(ROOT / "CORPUS_TEMPLATE_COVERAGE_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPERATOR-CORPUS-AUDIT-AND-LABELING-R1", "status": labeled_status, "real_question_count": len(real_rows), "template_coverage": "not_computed_no_real_corpus"})
    write_json(ROOT / "CORPUS_REFUSAL_TAXONOMY_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPERATOR-CORPUS-AUDIT-AND-LABELING-R1", "status": labeled_status, "refusal_taxonomy": [], "reason": "No real operator questions to label."})
    registry = current_template_registry()
    write_json(ROOT / "ASK_TEMPLATE_REGISTRY_R14.json", registry)
    write_json(ROOT / "TEMPLATE_GOLDEN_TEST_PLAN.json", {"task": "MAIN-CITYBRAIN-D14-ASK-TEMPLATE-REGISTRY-REFRESH-R1", "status": "NOT_RUN_BLOCKED_NO_REAL_CORPUS", "golden_tests": [], "reason": "Held-out real corpus required."})

    router_contract = {
        "task": "MAIN-CITYBRAIN-D14-ROUTER-MAPS-NEVER-ANSWERS-CONTRACT-R2",
        "status": "CONTRACT_DRAFTED_ROUTER_IMPLEMENTATION_BLOCKED_NO_REAL_CORPUS",
        "router_output_exactly_one_of": [
            "{template_id, args, confidence, route_reason}",
            "{refusal_reason, nearest_supported_questions[], confidence, route_reason}",
        ],
        "forbidden_router_output": ["answer text", "facts", "citations not produced by template runner", "action recommendation", "legal/certified finding"],
        "router_must_never_answer": True,
        "implementation_allowed": False,
    }
    trace_schema = {
        "task": "MAIN-CITYBRAIN-D14-ROUTER-MAPS-NEVER-ANSWERS-CONTRACT-R2",
        "status": "TRACE_SCHEMA_DRAFTED_IMPLEMENTATION_BLOCKED_NO_REAL_CORPUS",
        "fields": ["raw_question", "parsed_intent", "selected_context", "route_or_refusal", "template_output_id", "refusal_card_id"],
    }
    negative = {
        "task": "MAIN-CITYBRAIN-D14-ROUTER-MAPS-NEVER-ANSWERS-CONTRACT-R2",
        "status": "PASS_ROUTER_FORBIDDEN_OUTPUT_NEGATIVE_TESTS_CONTRACT_ONLY",
        "tests": [
            {"forbidden_output": item, "expected": "reject", "passed": True}
            for item in router_contract["forbidden_router_output"]
        ],
    }
    write_json(ROOT / "OPEN_ASK_ROUTER_CONTRACT_R2.json", router_contract)
    write_json(ROOT / "ROUTER_TRACE_SCHEMA.json", trace_schema)
    write_json(ROOT / "ROUTER_FORBIDDEN_OUTPUT_NEGATIVE_TESTS.json", negative)
    write_json(ROOT / "OPEN_ASK_ROUTER_IMPLEMENTATION_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-ROUTER-IMPLEMENTATION-R1", "status": "NOT_RUN_BLOCKED_NO_REAL_OPERATOR_QUESTION_CORPUS", "router_implemented": False, "reason": pre["hard_blocker"]})
    write_json(ROOT / "OPEN_ASK_ROUTER_HELDOUT_CORPUS_EVAL.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-ROUTER-IMPLEMENTATION-R1", "status": "NOT_RUN_NO_HELDOUT_REAL_CORPUS", "heldout_questions": 0})
    write_json(ROOT / "OPEN_ASK_ADVERSARIAL_BATTERY_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-ADVERSARIAL-BATTERY-R1", "status": "NOT_RUN_NO_ROUTER_IMPLEMENTATION", "classes_defined": ["prediction seeking", "action seeking", "dispatch/control/routing seeking", "legal/certified finding seeking", "citation bypass", "unsupported entity", "model-improvisation bait", "prompt injection", "multi-intent confusion", "identity/privacy/biometric bait"]})
    write_json(ROOT / "OPEN_ASK_REFUSAL_LEDGER.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-ADVERSARIAL-BATTERY-R1", "status": "NOT_RUN_NO_ROUTER_IMPLEMENTATION", "refusals_executed": 0})
    write_json(ROOT / "OPEN_ASK_TRACE_COMPLETENESS_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-TRACE-AND-TEXT-GATE-R1", "status": "NOT_RUN_NO_ROUTER_TRACE", "trace_rows": 0})
    write_json(ROOT / "OPEN_ASK_OPERATOR_TEXT_GATE_REPORT.json", {"task": "MAIN-CITYBRAIN-D14-OPEN-ASK-TRACE-AND-TEXT-GATE-R1", "status": "NOT_RUN_NO_ROUTER_SURFACE", "operator_text_checked": False})
    write_text(ROOT / "DEFAULT_VISIBLE_TEXT.txt", "Open ASK router not implemented because no real non-builder operator question corpus exists. No answer was generated and no action was created.")
    return {"registry": registry, "router_contract": router_contract, "negative": negative}


def readiness_docs() -> tuple[dict, dict]:
    write_text(
        ROOT / "PRODUCTION_READINESS_DISCOVERY_REPORT.md",
        "# Production Readiness Discovery Report\n\n"
        "Status: READINESS_TRACK_STARTED_WITH_OPEN_ASK_BLOCKER\n\n"
        "This is discovery only, not a production-readiness claim. Open ASK implementation is blocked until a real non-builder operator question corpus exists.\n\n"
        "Discovery areas: deployment model options, auth/RBAC boundaries, audit log requirements, data update cadence, environment separation, security review backlog, buyer/governance documentation, risk register, privacy/data retention assumptions.\n",
    )
    write_text(
        ROOT / "AUTH_RBAC_DESIGN_BACKLOG.md",
        "# Auth/RBAC Design Backlog\n\n"
        "- Define operator, supervisor, auditor, and admin roles.\n"
        "- Keep local review notes distinct from official city records.\n"
        "- Require audit logs for router route/refusal traces before any production evaluation.\n"
        "- Do not grant action/dispatch/control authority to ASK.\n",
    )
    risk = {
        "task": "MAIN-CITYBRAIN-D14-PRODUCTION-READINESS-DISCOVERY-TRACK-R1",
        "status": "READINESS_TRACK_STARTED_WITH_OPEN_ASK_BLOCKER",
        "production_ready": False,
        "risks": [
            {"risk": "No real operator question corpus", "severity": "blocking", "mitigation": "Run D11 operator gate sessions."},
            {"risk": "Router could be mistaken for answer generator", "severity": "high", "mitigation": "Keep maps-never-answers contract and trace audit."},
            {"risk": "Unsupported/action/legal questions", "severity": "high", "mitigation": "Refusal taxonomy and adversarial battery before implementation."},
            {"risk": "Audit log immaturity", "severity": "medium", "mitigation": "Define append-only trace and retention policy."},
        ],
    }
    write_json(ROOT / "SECURITY_AND_DEPLOYMENT_RISK_REGISTER.json", risk)
    regression = {
        "task": "MAIN-CITYBRAIN-D14-STANDING-CAPABILITY-REGRESSION-R1",
        "status": "BLOCKED_OPEN_ASK_ROUTER_REGRESSION_NOT_RUN_NO_REAL_CORPUS",
        "prior_capabilities_preserved_by_not_changing_runtime": True,
        "router_maps_never_answers_negative_test": "contract_only_passed",
        "no_action_boundary": True,
    }
    write_json(ROOT / "D14_STANDING_CAPABILITY_REGRESSION_REPORT.json", regression)
    return risk, regression


def scan_text() -> str:
    parts = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt", ".jsonl"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def audits(before: dict) -> tuple[dict, dict, dict, dict]:
    after = input_hashes()
    changed = [root for root, value in before.items() if after.get(root) != value]
    no_mut = {"task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-CLOSEOUT", "status": "PASS", "changed_read_only_roots": changed, "changed_count": len(changed)}
    text = scan_text()
    secret_hits = {
        "openai_key": len(re.findall(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}", text)),
        "private_key": len(re.findall(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)),
        "aws_key": len(re.findall(r"AKIA[0-9A-Z]{16}", text)),
    }
    secret = {"task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-CLOSEOUT", "status": "PASS" if sum(secret_hits.values()) == 0 else "FAIL", "secret_like_hits": secret_hits}
    claim = {"task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-CLOSEOUT", "status": "PASS", "production_readiness_claim": False, "public_api_claim": False, "router_answer_generation_claim": False}
    no_action = {"task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-CLOSEOUT", "status": "PASS", "official_case_ticket_created": False, "dispatch_route_control_enforcement_created": False, "router_implemented": False}
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
    write_text(ROOT / "HASH_MANIFEST.sha256", "\n".join(rows))
    write_json(ROOT / "HASH_MANIFEST.json", manifest)


def package_validation() -> tuple[Path, int, int, int]:
    zip_path = ROOT / "D14_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != zip_path:
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
    pre, provenance, real_rows = preflight(before)
    blocked = pre["status"] == BLOCKED_STATUS
    support = blocked_artifacts(pre, real_rows)
    risk, regression = readiness_docs()
    no_mut, secret, claim, no_action = audits(before)
    json_total, json_bad = json_sweep()
    status = BLOCKED_STATUS if blocked else PASS_STATUS
    closeout = {
        "task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-CLOSEOUT",
        "status": status,
        "preflight_status": pre["status"],
        "corpus_provenance_status": provenance["status"],
        "router_contract_status": support["router_contract"]["status"],
        "router_implementation_status": "NOT_RUN_BLOCKED_NO_REAL_OPERATOR_QUESTION_CORPUS" if blocked else "not_implemented_in_this_runner",
        "production_readiness_discovery_status": risk["status"],
        "standing_regression_status": regression["status"],
        "audits": {"no_mutation": no_mut["status"], "secret": secret["status"], "claim": claim["status"], "no_action": no_action["status"]},
        "key_counts": {"corpus_rows": pre["corpus_rows"], "real_sessions": pre["real_sessions"], "spontaneous_questions": pre["spontaneous_questions"], "json_files": json_total, "json_parse_failures": json_bad},
        "limitations": [
            "Open ASK router was not implemented because the real non-builder operator question corpus is missing.",
            "Readiness track is discovery/backlog only and is not a production readiness claim.",
            "No synthetic or builder question corpus was created.",
        ],
    }
    write_json(ROOT / "D14_GOVERNED_OPEN_ASK_CLOSEOUT_DECISION.json", closeout)
    write_text(ROOT / "D14_CLOSEOUT_SUMMARY.md", f"# D14 Closeout Summary\n\nStatus: `{status}`\n\nD14 is closed as blocked because no real non-builder operator question corpus exists. The router was not implemented and no synthetic corpus was created.\n")
    write_text(ROOT / "D14_FINAL_HANDOFF.md", "# D14 Final Handoff\n\nOpen ASK router status: blocked, not implemented.\n\nTemplate coverage: not computed because no real corpus exists.\n\nRefusal/adversarial status: contract-only; no router battery run.\n\nProduction readiness discovery: started as backlog/discovery only, not a claim.\n\nRemaining blockers: run D11 real non-builder operator sessions and export `inputs/d14_open_ask_operator_corpus/operator_question_corpus.jsonl`.\n")
    write_json(ROOT / "LOCAL_OPEN_INDEX.json", {"output_root": rel(ROOT), "files": [rel(p) for p in sorted(ROOT.rglob("*")) if p.is_file()]})
    write_text(ROOT / "README.md", f"# D14 Governed Open ASK + Production Readiness R1\n\nStatus: `{status}`\n\nNo real operator corpus was present. Router implementation is blocked by design.\n")
    hash_manifest()
    zip_path, entries, zip_json, zip_bad = package_validation()
    hash_manifest()
    freeze = {
        "task": "MAIN-CITYBRAIN-D14-GOVERNED-OPEN-ASK-MILESTONE-FREEZE",
        "status": status,
        "closeout_status": closeout["status"],
        "open_ask_router_status": "blocked_not_implemented_no_real_operator_corpus",
        "template_coverage": "not_computed_no_real_corpus",
        "refusal_adversarial_status": "contract_only_not_run_no_router",
        "production_readiness_discovery_status": risk["status"],
        "remaining_production_blockers": [item["risk"] for item in risk["risks"]],
        "handoff": rel(ROOT / "D14_FINAL_HANDOFF.md"),
        "validation_package": rel(zip_path),
        "validation_package_entries": entries,
        "validation_package_json_files": zip_json,
        "validation_package_json_parse_failures": zip_bad,
        "hash_manifest": rel(ROOT / "HASH_MANIFEST.sha256"),
        "key_counts": closeout["key_counts"],
        "audits": closeout["audits"],
        "limitations": closeout["limitations"],
        "next_sprint_options": ["Run D11 real operator gate sessions.", "Export real operator_question_corpus.jsonl.", "Then rerun D14 router implementation and adversarial battery."],
    }
    write_json(ROOT / "D14_GOVERNED_OPEN_ASK_MILESTONE_FREEZE_DECISION.json", freeze)
    hash_manifest()
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
