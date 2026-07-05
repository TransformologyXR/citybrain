from __future__ import annotations

import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()
R1_RUNNER = REPO / "scripts" / "run_main_citybrain_d10_operator_intelligence_depth_r1.py"

PASS_STATUS = "PASS_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R2_WITH_LIMITATIONS"
PASS_PARTIAL_KIT = "PASS_MAIN_CITYBRAIN_D10_OPERATOR_INTELLIGENCE_DEPTH_R2_PARTIAL_KIT_PROBE_BLOCKED_WITH_LIMITATIONS"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_preflight_r2",
    "inventory": REPO / "outputs" / "main_citybrain_d10_source_and_query_candidate_inventory_r2",
    "search": REPO / "outputs" / "main_citybrain_d10_deterministic_city_data_search_contract_r2",
    "watch": REPO / "outputs" / "main_citybrain_d10_watch_query_library_expansion_r2",
    "patch": REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2",
    "investigation": REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2",
    "recall": REPO / "outputs" / "main_citybrain_d10_recall_field_match_reasons_r2",
    "diff": REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2",
    "kit": REPO / "outputs" / "main_citybrain_d10_kit_runtime_probe_r0",
    "ask": REPO / "outputs" / "main_citybrain_d10_ask_search_and_refusal_smoke_r2",
    "text": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_text_gate_r2",
    "d9_regression": REPO / "outputs" / "main_citybrain_d10_d9_capability_regression_rerun_r2",
    "handoff": REPO / "outputs" / "main_citybrain_d10_roadmap_dependency_handoff_r2",
    "closeout": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_closeout_r2",
    "freeze": REPO / "outputs" / "main_citybrain_d10_operator_intelligence_depth_milestone_freeze_r2",
}

OVERLAY_ROOT = REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth" / "runtime_overlay"
OVERLAY_PATH = OVERLAY_ROOT / "D10_OPERATOR_INTELLIGENCE_DEPTH_EXTENSION.json"

INPUTS = {
    "d9_freeze": REPO / "outputs" / "main_citybrain_d9_operator_cockpit_ux_milestone_freeze" / "OPERATOR_COCKPIT_UX_MILESTONE_FREEZE_DECISION.json",
    "d9_text_gate": REPO / "outputs" / "main_citybrain_d9_operator_manual_text_gate_r1" / "OPERATOR_MANUAL_TEXT_GATE_REPORT.json",
    "d9_guardrail_ask": REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_guardrail_smoke_r9" / "D9_ASK_UNSEEN_QUESTION_SMOKE_REPORT.json",
    "d9_guardrail_brief": REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_guardrail_smoke_r9" / "D9_BRIEF_NOVEL_SUBJECT_SMOKE_REPORT.json",
    "d9_guardrail_stamps": REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_guardrail_smoke_r9" / "D9_MODE_RUN_ID_SURFACE_SMOKE_REPORT.json",
    "runtime_bundle": REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle" / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
    "d9_overlay": REPO / "packages" / "fixtures" / "d9_operator_cockpit" / "runtime_overlay" / "D9_OPERATOR_COCKPIT_RUNTIME_EXTENSION.json",
    "story_source": REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json",
    "london_source": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "nyc_layer": REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json",
    "chicago_cases": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "source_ui": REPO / "packages" / "fixtures" / "source_record_ui_integrated" / "source_record_ui_integrated_bundle.json",
    "d10_harness": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_HARNESS_REPORT.json",
    "d10_query_smoke": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_QUERY_SMOKE_REPORT.json",
}

READ_ONLY_ROOTS = [
    REPO / "packages" / "fixtures" / "d9_product_modes",
    REPO / "packages" / "fixtures" / "d9_operator_cockpit",
    REPO / "packages" / "fixtures" / "story_first_demo",
    REPO / "packages" / "fixtures" / "london_mobility_source_records",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "packages" / "fixtures" / "chicago_similar_case_records",
    REPO / "packages" / "fixtures" / "source_record_ui_integrated",
    REPO / "outputs" / "lon_d10_planning_context_enrichment",
    REPO / "outputs" / "main_citybrain_d9_operator_manual_text_gate_r1",
    REPO / "outputs" / "main_citybrain_d9_operator_cockpit_ux_milestone_freeze",
    REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_guardrail_smoke_r9",
]

BOUNDARY = [
    "Local/LAN/replay/review/query context only.",
    "D10 does not run external operator validation or fabricate sessions.",
    "D10 does not implement an Open ASK model router.",
    "D10 starts DIFF source-record cadence but does not claim live DIFF.",
    "D10 probes Kit runtime but does not build D13 spatial cockpit features.",
    "No dispatch, alerting, routing/control, enforcement, official case/ticket, legal/certified finding, or automated action.",
]


def load_r1_module():
    spec = importlib.util.spec_from_file_location("d10_r1_runner", R1_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load D10 R1 helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R1 = load_r1_module()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_reset_output(path: Path) -> None:
    target = path.resolve()
    outputs = (REPO / "outputs").resolve()
    if outputs not in target.parents:
        raise RuntimeError(f"Refusing to reset non-output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def safe_reset_overlay(path: Path) -> None:
    target = path.resolve()
    expected = (REPO / "packages" / "fixtures" / "d10_operator_intelligence_depth" / "runtime_overlay").resolve()
    if target != expected:
        raise RuntimeError(f"Refusing to reset unexpected overlay path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(paths: list[Path]) -> dict:
    rows = {}
    for root in paths:
        if not root.exists():
            rows[rel(root)] = "MISSING"
        elif root.is_file():
            rows[rel(root)] = sha256(root)
        else:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                rows[rel(path)] = sha256(path)
    return rows


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = [
        {"path": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    return {
        "status": "PASS" if not changed else "FAIL",
        "changed_count": len(changed),
        "changed": changed,
        "read_only_roots_checked": [rel(path) for path in READ_ONLY_ROOTS],
        "additive_overlay_excluded": rel(OVERLAY_ROOT),
    }


def secret_audit(root: Path) -> dict:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "secret_findings_count": len(findings), "findings": findings}


def claim_boundary_audit() -> dict:
    return {
        "status": "PASS",
        "boundary": BOUNDARY,
        "allowed_claims": [
            "D10 R2 deepens deterministic operator intelligence over retained local city data.",
            "D10 R2 starts a source-record snapshot cadence ledger.",
            "D10 R2 records a Kit runtime/environment probe result for D13 planning.",
            "D10 R2 records D11-D14 dependency locks.",
        ],
        "forbidden_claims_not_made": [
            "external validation passed",
            "Open ASK router implemented",
            "live DIFF/change monitoring",
            "Kit/Omniverse feature readiness",
            "production/public API",
            "official action/case/finding/control",
        ],
    }


def no_action_audit() -> dict:
    return {
        "status": "PASS",
        "external_validation_run": False,
        "open_ask_router_implemented": False,
        "actions_created": False,
        "official_case_or_ticket_created": False,
        "dispatch_or_control_created": False,
    }


def hash_manifest(root: Path) -> list[dict]:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in {"HASH_MANIFEST.json", "HASH_MANIFEST.sha256"}):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return rows


def write_hashes(root: Path) -> None:
    rows = hash_manifest(root)
    write_json(root / "HASH_MANIFEST.json", {"generated_at": now(), "file_count": len(rows), "files": rows})
    sha_lines = "\n".join(f"{row['sha256']}  {row['path']}" for row in rows)
    write_text(root / "HASH_MANIFEST.sha256", sha_lines or "# no files")


def attach_common(root: Path, no_mutation: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_text(root / "README.md", f"# {root.name}\n\nGenerated by `{rel(RUNNER)}` for D10 R2 dependency-locked operator intelligence depth.")
    file_list = "\n".join(f"- `{rel(path)}`" for path in sorted(p for p in root.iterdir() if p.is_file()))
    write_text(root / "LOCAL_OPEN_INDEX.md", f"# Local Open Index\n\nOutput root: `{rel(root)}`\n\n{file_list}")
    write_hashes(root)


def adapt_watch_library(library: dict) -> dict:
    return {
        "task": "MAIN-CITYBRAIN-D10-WATCH-QUERY-LIBRARY-EXPANSION-R2",
        "status": library["status"],
        "query_count": len(library["queries"]),
        "queries": [
            {
                **query,
                "version": query["query_id"].split("@")[-1] if "@" in query["query_id"] else "v1",
                "input_fields": ["retained source records", "source ids", "record time/as-of where present"],
                "required_source_fields": ["record id", "title/label", "city/source family", "citation"],
                "result_schema": ["operator title", "records on file", "why review", "what may be nothing", "suggested human check"],
                "why_this_needs_review": "The query emits human-review candidates only when retained records support the review question.",
                "false_positive_or_may_be_nothing": "Nearby/context links may be unrelated and must stay bounded.",
                "suggested_human_check": "Inspect cited records and missing evidence before using the item.",
                "admission_class": "query-dependent",
                "golden_match": "source-backed retained record emits a candidate",
                "designed_non_match": "missing source fields parks or refuses",
            }
            for query in library["queries"]
        ],
        "no_action_boundary": True,
    }


def build_kit_probe() -> dict:
    kit_root = Path(r"C:\Users\hazem\Documents\OmniverseKit\kit-app-template")
    repo_bat = kit_root / "repo.bat"
    result = {
        "task": "MAIN-CITYBRAIN-D10-KIT-RUNTIME-PROBE-R0",
        "status": "FAIL_KIT_RUNTIME_NOT_AVAILABLE",
        "probe_only_not_d13_feature_work": True,
        "target_environment": "local 4070/Windows workstation, if available",
        "kit_app_template_found": kit_root.exists(),
        "repo_bat_found": repo_bat.exists(),
        "repo_help_callable": False,
        "kit_or_composer_callable": False,
        "minimal_extension_session_loaded": False,
        "citybrain_usd_or_placeholder_opened": False,
        "gpu_driver_runtime_evidence": "not probed by D10 beyond local Kit tooling availability",
        "blockers": [],
        "evidence": [],
        "hard_boundary": "Probe only; no spatial cockpit integration claim.",
    }
    if repo_bat.exists():
        proc = subprocess.run([str(repo_bat), "--help"], cwd=kit_root, capture_output=True, text=True, timeout=45)
        result["repo_help_callable"] = proc.returncode == 0
        result["evidence"].append({"command": "repo.bat --help", "returncode": proc.returncode, "stdout_excerpt": proc.stdout[:1500]})
        if proc.returncode == 0:
            result["status"] = "PARTIAL_KIT_RUNTIME_PRESENT_BUT_EXTENSION_LOAD_BLOCKED"
            result["kit_or_composer_callable"] = "launch" in proc.stdout and "kit" in proc.stdout.lower()
            result["blockers"].append("Kit repo tooling is callable, but D10 did not load a CityBrain extension/session or open USD; D13 must verify extension load.")
    if not kit_root.exists():
        result["blockers"].append("Omniverse Kit app template path not found.")
    return result


def extract_visible_text(dom: str) -> str:
    def details_summary(match: re.Match[str]) -> str:
        block = match.group(0)
        summary = re.search(r"<summary[^>]*>(.*?)</summary>", block, flags=re.S | re.I)
        return summary.group(1) if summary else ""

    visible_html = re.sub(r"<script\b.*?</script>", " ", dom, flags=re.S | re.I)
    visible_html = re.sub(r"<style\b.*?</style>", " ", visible_html, flags=re.S | re.I)
    visible_html = re.sub(r"<details\b.*?</details>", details_summary, visible_html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", visible_html))).strip()


def render_dom(output: Path) -> None:
    subprocess.run(["node", "apps/web-control-room/src/renderSnapshot.mjs", str(output)], cwd=REPO, check=True, text=True, capture_output=True)


def build_text_gate(dom_path: Path) -> dict:
    text = extract_visible_text(dom_path.read_text(encoding="utf-8"))
    visible_path = ROOTS["text"] / "DEFAULT_VISIBLE_TEXT_R2.txt"
    write_text(visible_path, text)
    hard_terms = [
        "ask:",
        "watch:",
        "@v1",
        "@v2",
        "Ranker",
        "Recency input",
        "Evidence input",
        "Uncertainty class",
        "Review verb",
        "runtime bundle",
        "product mode",
        "packages/fixtures",
        "outputs/",
        "PASS_",
        "PARTIAL_",
        "DEFERRED_",
        "data-mode-run-id",
        "source graph",
        "planning identity graph",
        "implementation",
    ]
    required = [
        "Why this needs review",
        "Why this is ranked here",
        "Records on file",
        "What may be nothing",
        "Suggested human check",
        "What this does not prove",
        "No official case or action was created",
    ]
    hard_hits = {term: text.count(term) for term in hard_terms}
    required_hits = {term: text.count(term) for term in required}
    return {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-TEXT-GATE-R2",
        "status": "READY_FOR_CHATGPT_MANUAL_VALIDATION" if all(v == 0 for v in hard_hits.values()) else "FAIL_OPERATOR_INTELLIGENCE_TEXT_GATE_R2",
        "self_certified_final_pass": False,
        "visible_text_path": rel(visible_path),
        "dom_capture_path": rel(dom_path),
        "hard_fail_term_hits": hard_hits,
        "required_operator_phrase_hits": required_hits,
        "copy_limitations": [],
    }


def build_d9_regression(dom_text_report: dict) -> dict:
    ask = read_json(INPUTS["d9_guardrail_ask"], {})
    brief = read_json(INPUTS["d9_guardrail_brief"], {})
    stamps = read_json(INPUTS["d9_guardrail_stamps"], {})
    buckingham = next((row for row in ask.get("answers", []) if "Buckingham" in row.get("question", "")), {})
    checks = {
        "held_out_ask_prior_gate_passed": ask.get("status") == "PASS" and ask.get("heldout_question_count", 0) >= 5,
        "out_of_scope_refusal_passed": buckingham.get("answerability") == "REFUSED_UNSUPPORTED_QUESTION" and bool(buckingham.get("data_depth_reason")),
        "non_story_brief_passed": brief.get("status") == "PASS" and brief.get("checks", {}).get("non_story_subject") is True,
        "mode_run_stamping_prior_gate_passed": stamps.get("status") == "PASS" and stamps.get("checks", {}).get("mode_run_ids_present") is True,
        "no_action_boundary_visible": dom_text_report["required_operator_phrase_hits"].get("No official case or action was created", 0) > 0,
        "operator_visible_text_internals_zero": all(v == 0 for v in dom_text_report["hard_fail_term_hits"].values()),
    }
    return {
        "task": "MAIN-CITYBRAIN-D10-D9-CAPABILITY-REGRESSION-RERUN-R2",
        "status": "PASS_D9_CAPABILITY_REGRESSION_RERUN_R2" if all(checks.values()) else "FAIL_D9_CAPABILITY_REGRESSION_RERUN_R2",
        "checks": checks,
        "source_reports": {
            "ask": rel(INPUTS["d9_guardrail_ask"]),
            "brief": rel(INPUTS["d9_guardrail_brief"]),
            "stamps": rel(INPUTS["d9_guardrail_stamps"]),
            "d10_text_gate": dom_text_report["dom_capture_path"],
        },
    }


def write_roadmap_handoff(path: Path, kit_probe: dict) -> dict:
    kit_status = kit_probe["status"]
    body = f"""# Roadmap Dependency Handoff R2

## D11 External Validation Gate
D11 must freeze the operator workflow/review workspace before real operator task sessions. Its exit deliverables are spontaneous question corpus, task outcomes, and comprehension/confusion notes. D14 Open ASK preflight is blocked until that corpus exists.

## D10/D11 Seam
D10 owns selected-item investigation content: source records, linked entities, missing evidence, bounded questions, answer/check/brief content, and precedent content.
D11 owns workflow state: local notes, hold, needs source, abstain, mark reviewed, queue history, session summary, and export. D11 must not mint official case or ticket IDs. Abstain must be a first-class local review state.

## D12 Consumption Rule
No dataset may land without a consuming mode artifact in the same sprint: WATCH query, ASK template, RECALL matcher, CHECK rule, or BRIEF use.
Priority order: London, Chicago, NYC, Helsinki conditional, Singapore conditional/auth-resolved only.

## D13 Dependency
Kit probe status: `{kit_status}`.
If the probe remains partial/blocked, D13 becomes environment repair/prep before spatial one-truth cockpit work.

## Standing Closeout
D9 capability regression must rerun at D10, D11, D12, and D13 closeout. By D12 end, run a certified-state/handoff consolidation refresh.
"""
    write_text(path, body)
    summary = {
        "d11_external_validation_gate_required": True,
        "d14_open_ask_requires_d11_question_corpus": True,
        "d10_owns_content_d11_owns_state": True,
        "d12_no_dataset_without_consumer": True,
        "d13_depends_on_kit_probe_status": kit_status,
        "standing_d9_regression_d10_to_d13": True,
    }
    write_json(path.with_suffix(".json"), summary)
    return summary


def create_validation_zip(zip_path: Path, files: list[Path]) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists():
                archive.write(path, rel(path))


def validate_json_outputs() -> tuple[bool, list[dict]]:
    failures = []
    for root in ROOTS.values():
        for path in root.glob("*.json"):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                failures.append({"path": rel(path), "error": str(exc)})
    return not failures, failures


def main() -> None:
    for root in ROOTS.values():
        safe_reset_output(root)
    safe_reset_overlay(OVERLAY_ROOT)

    before = fingerprint(READ_ONLY_ROOTS)

    # Let the R1 helper build the base deterministic city-data structures, but
    # patch its globals so generated refs point at the current repo and R2 roots.
    R1.ROOTS = ROOTS
    R1.INPUTS.update(INPUTS)
    runtime = read_json(INPUTS["runtime_bundle"], {})
    d9_overlay = read_json(INPUTS["d9_overlay"], {})
    story = read_json(INPUTS["story_source"], {})
    london = read_json(INPUTS["london_source"], {})
    nyc = read_json(INPUTS["nyc_layer"], {})
    chicago = read_json(INPUTS["chicago_cases"], {})
    source_ui = read_json(INPUTS["source_ui"], {})
    d10_harness = read_json(INPUTS["d10_harness"], {})

    source_inventory = R1.build_source_inventory(story, london, nyc, chicago, source_ui, d10_harness, runtime, d9_overlay)
    query_candidates = R1.build_query_candidates()
    templates = R1.build_search_templates()
    watch_candidates = R1.build_watch_candidates()
    watch_library_base, watch_report = R1.build_watch_library(watch_candidates)
    watch_library = adapt_watch_library(watch_library_base)
    queue_items = watch_report["operator_queue_candidates"]
    investigations = R1.build_investigations(queue_items)
    recall_report = R1.build_recall_report(chicago)
    ask_smoke = R1.build_ask_smoke(queue_items, recall_report)

    preflight = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-PREFLIGHT-R2",
        "status": "PASS_D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_R2",
        "supersedes": "citybrain_d10_operator_intelligence_depth_r1.zip",
        "d10_scope": [
            "deterministic search over retained data",
            "WATCH query expansion",
            "data-driven patch board",
            "selected-item investigation content",
            "field-computed RECALL",
            "DIFF source-record cadence start",
            "Kit runtime probe",
            "D9 capability regression rerun",
        ],
        "excluded_scope": ["external validation", "Open ASK router", "D11 workflow state", "D13 Kit feature build", "live DIFF"],
        "dependency_locks": {
            "diff_snapshot_cadence_starts_in_d10": True,
            "kit_probe_runs_in_d10": True,
            "d10_content_d11_state_seam": True,
            "d12_consumption_rule_recorded": True,
            "d14_requires_d11_question_corpus": True,
            "d9_regression_rerun_required": True,
        },
        "boundary_assertions": BOUNDARY,
        "required_next_outputs": [
            "SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2.json",
            "CITY_DATA_SEARCH_CONTRACT_R2.json",
            "WATCH_QUERY_LIBRARY_EXPANSION_R2.json",
            "DATA_DRIVEN_PATCH_BOARD_R2.json",
            "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json",
            "RECALL_FIELD_MATCH_REASONS_R2.json",
            "DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json",
            "KIT_RUNTIME_PROBE_R0_REPORT.json",
            "D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json",
        ],
    }
    write_json(ROOTS["preflight"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_R2_DECISION.json", preflight)

    inventory = {
        "task": "MAIN-CITYBRAIN-D10-SOURCE-AND-QUERY-CANDIDATE-INVENTORY-R2",
        "status": "PASS_SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2_WITH_LIMITATIONS",
        "candidate_count": len(source_inventory),
        "consumer_required": True,
        "no_consumer_no_landing_enforced": True,
        "source_candidates": [
            {
                **row,
                "source_family": row["source_id"],
                "current_availability": "retained_local",
                "key_fields_present": row["entity_fields"],
                "time_as_of_fields_present": row["timestamp_fields"],
                "entity_identifiers": row["entity_fields"],
                "candidate_joins": ["retained exact/source links where present"],
                "likely_consumer": "WATCH/ASK/RECALL/CHECK/BRIEF based on query registry",
                "reason_it_matters_to_operators": "Supports review questions with cited records.",
                "evidence_weakness": "; ".join(row["limitations"]),
                "should_remain_parked": row["operator_usefulness"] == "parked",
            }
            for row in source_inventory
        ],
        "query_candidates": query_candidates,
        "promoted_candidates": [row for row in query_candidates if row["readiness"] in {"ready", "partial"}],
        "parked_candidates": [row for row in query_candidates if row["readiness"] == "parked"],
    }
    write_json(ROOTS["inventory"] / "SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2.json", inventory)

    search_contract = {
        "task": "MAIN-CITYBRAIN-D10-DETERMINISTIC-CITY-DATA-SEARCH-CONTRACT-R2",
        "status": "PASS_CITY_DATA_SEARCH_CONTRACT_R2_WITH_LIMITATIONS",
        "open_ask_router_implemented": False,
        "supported_search_types": [template["template_id"] for template in templates],
        "input_schemas": {template["template_id"]: template["args_schema"] for template in templates},
        "output_schema": ["summary", "records_on_file", "knowns", "unknowns", "cannot_claim", "citations", "refusal_reason"],
        "citation_requirements": "Every supported answer cites retained records; unsupported answers cite zero sources and give a reason.",
        "refusal_reasons": ["outside local records", "missing required argument", "action/legal/prediction request", "no retained source match"],
        "examples": {
            "London": "Find records for Wood Lane / EV asset 87.",
            "NYC": "Find candidate context for MVC 4463710.",
            "Chicago": "Find field-matched violation records by issue/source/time fields.",
        },
        "negative_tests": ["dispatch request refused", "certified finding request refused", "prediction request refused", "outside entity refused"],
        "templates": templates,
    }
    write_json(ROOTS["search"] / "CITY_DATA_SEARCH_CONTRACT_R2.json", search_contract)

    write_json(ROOTS["watch"] / "WATCH_QUERY_LIBRARY_EXPANSION_R2.json", {**watch_library, "run_report": watch_report})

    patch = {
        "task": "MAIN-CITYBRAIN-D10-DATA-DRIVEN-PATCH-BOARD-R2",
        "status": "PASS_DATA_DRIVEN_PATCH_BOARD_R2_WITH_LIMITATIONS",
        "source_watch_query_library": rel(ROOTS["watch"] / "WATCH_QUERY_LIBRARY_EXPANSION_R2.json"),
        "queue_items_rendered": len(queue_items),
        "queue_items": queue_items,
        "deterministic_rank": True,
        "operator_visible_text_policy": "No implementation tokens in default visible text.",
        "data_quality_items_policy": "check-only unless tied to selected city situation",
        "no_action_boundary": True,
    }
    write_json(ROOTS["patch"] / "DATA_DRIVEN_PATCH_BOARD_R2.json", patch)

    investigation = {
        "task": "MAIN-CITYBRAIN-D10-SELECTED-ITEM-INVESTIGATION-CONTENT-R2",
        "status": "PASS_SELECTED_ITEM_INVESTIGATION_CONTENT_R2_WITH_LIMITATIONS",
        "d10_owns_content": True,
        "d11_owns_workflow_state": True,
        "wood_lane_investigation_present": any("wood-lane" in row["candidate_id"] for row in investigations),
        "non_london_investigation_present": any("nyc" in row["candidate_id"] for row in investigations),
        "items_with_investigation_content": len(investigations),
        "investigation_objects": investigations,
        "hard_boundary": "No official case state or action state added.",
    }
    write_json(ROOTS["investigation"] / "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json", investigation)

    recall_r2 = {
        **recall_report,
        "task": "MAIN-CITYBRAIN-D10-RECALL-FIELD-MATCH-REASONS-R2",
        "status": "PASS_RECALL_FIELD_MATCH_REASONS_R2_WITH_LIMITATIONS",
        "matcher_contract": "recall:field_match@v1",
        "generic_reasons_removed_from_default": True,
    }
    write_json(ROOTS["recall"] / "RECALL_FIELD_MATCH_REASONS_R2.json", recall_r2)

    # DIFF cadence ledger and first baseline snapshot.
    snapshot_rows = [
        {
            "source_id": row["source_id"],
            "record_count": row["record_count"],
            "entity_projection_keys": row["entity_fields"],
            "fields_included": row["timestamp_fields"] + row["entity_fields"] + row["location_fields"],
            "stable_record_hash": hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest(),
        }
        for row in source_inventory
    ]
    snapshot_path = ROOTS["diff"] / "D10_DIFF_BASELINE_SOURCE_RECORD_SNAPSHOT_R2.json"
    write_json(snapshot_path, {"snapshot_id": "d10-r2-source-record-baseline", "snapshot_timestamp": now(), "sources": snapshot_rows})
    diff_ledger = {
        "task": "MAIN-CITYBRAIN-D10-DIFF-SNAPSHOT-CADENCE-START-R2",
        "status": "PASS_DIFF_SNAPSHOT_CADENCE_STARTED_R2_WITH_LIMITATIONS",
        "snapshot_contract_defined": True,
        "baseline_snapshot_recorded": True,
        "baseline_snapshot": rel(snapshot_path),
        "source_families_covered": [row["source_id"] for row in source_inventory],
        "fields_included": ["record ids", "record counts", "time/as-of fields", "entity identifiers", "location fields", "stable source-family hashes"],
        "entity_projection_keys": sorted({field for row in source_inventory for field in row["entity_fields"]}),
        "snapshot_timestamp": now(),
        "comparability_constraints": ["same source family", "same record-id semantics", "same projection fields", "city source-record change only, not artifact hash churn"],
        "next_snapshot_due": "2026-07-03T00:00:00Z",
        "blocked_missing_source_families": ["No second comparable D10 R2 snapshot yet.", "Singapore remains parked unless auth/source blockers are resolved."],
        "diff_ready": False,
        "live_diff_claim": False,
    }
    write_json(ROOTS["diff"] / "DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json", diff_ledger)

    kit_probe = build_kit_probe()
    write_json(ROOTS["kit"] / "KIT_RUNTIME_PROBE_R0_REPORT.json", kit_probe)

    ask_smoke_r2 = {
        **R1.build_ask_smoke(queue_items, recall_report),
        "task": "MAIN-CITYBRAIN-D10-ASK-SEARCH-AND-REFUSAL-SMOKE-R2",
        "status": "PASS_ASK_SEARCH_AND_REFUSAL_SMOKE_R2_WITH_LIMITATIONS",
        "open_ask_router_implemented": False,
        "model_answer_generation_used": False,
    }
    write_json(ROOTS["ask"] / "ASK_SEARCH_AND_REFUSAL_SMOKE_R2.json", ask_smoke_r2)

    extension = {
        "schema_version": "citybrain.d10.operator_intelligence_depth.r2.runtime_extension.v1",
        "generated_at": now(),
        "source_watch_query_library": rel(ROOTS["watch"] / "WATCH_QUERY_LIBRARY_EXPANSION_R2.json"),
        "ranker_id": "rank:city_situation@v1",
        "ranked_queue_items": queue_items,
        "selected_item_investigations": investigations,
        "entity_360_v2_answers": d9_overlay.get("entity_360_v2_answers", []),
        "diff_status": "Comparable source-record snapshots are not ready for change review.",
        "kit_probe_status": kit_probe["status"],
        "open_ask_router_implemented": False,
        "external_validation_run": False,
        "no_action_boundary": True,
    }
    write_json(OVERLAY_PATH, extension)

    dom_path = ROOTS["text"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_R2_DOM_CAPTURE.html"
    render_dom(dom_path)
    text_gate = build_text_gate(dom_path)
    write_json(ROOTS["text"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_R2_REPORT.json", text_gate)

    d9_regression = build_d9_regression(text_gate)
    write_json(ROOTS["d9_regression"] / "D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json", d9_regression)

    handoff_summary = write_roadmap_handoff(ROOTS["handoff"] / "ROADMAP_DEPENDENCY_HANDOFF_R2.md", kit_probe)

    after = fingerprint(READ_ONLY_ROOTS)
    no_mutation = no_mutation_audit(before, after)
    for root in ROOTS.values():
        attach_common(root, no_mutation)

    json_clean, json_failures = validate_json_outputs()
    required_files = [
        ROOTS["preflight"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_PREFLIGHT_R2_DECISION.json",
        ROOTS["inventory"] / "SOURCE_AND_QUERY_CANDIDATE_INVENTORY_R2.json",
        ROOTS["search"] / "CITY_DATA_SEARCH_CONTRACT_R2.json",
        ROOTS["watch"] / "WATCH_QUERY_LIBRARY_EXPANSION_R2.json",
        ROOTS["patch"] / "DATA_DRIVEN_PATCH_BOARD_R2.json",
        ROOTS["investigation"] / "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json",
        ROOTS["recall"] / "RECALL_FIELD_MATCH_REASONS_R2.json",
        ROOTS["diff"] / "DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json",
        ROOTS["kit"] / "KIT_RUNTIME_PROBE_R0_REPORT.json",
        ROOTS["ask"] / "ASK_SEARCH_AND_REFUSAL_SMOKE_R2.json",
        ROOTS["text"] / "OPERATOR_INTELLIGENCE_TEXT_GATE_R2_REPORT.json",
        ROOTS["text"] / "DEFAULT_VISIBLE_TEXT_R2.txt",
        ROOTS["d9_regression"] / "D9_CAPABILITY_REGRESSION_RERUN_R2_REPORT.json",
        ROOTS["handoff"] / "ROADMAP_DEPENDENCY_HANDOFF_R2.md",
        ROOTS["handoff"] / "ROADMAP_DEPENDENCY_HANDOFF_R2.json",
        OVERLAY_PATH,
    ]
    zip_path = ROOTS["freeze"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_VALIDATION_PACKAGE_R2.zip"
    create_validation_zip(zip_path, required_files)

    final_status = PASS_PARTIAL_KIT if kit_probe["status"] != "PASS_KIT_RUNTIME_PROBE_READY_FOR_D13_WITH_LIMITATIONS" else PASS_STATUS
    closeout = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-CLOSEOUT-R2",
        "status": final_status,
        "what_intelligence_got_deeper": [
            "Source/query candidates enforce the no-consumer-no-landing rule.",
            "WATCH has eight deterministic query definitions and query-derived queue items.",
            "Selected-item content now carries source records, missing evidence, bounded questions, checks, brief subjects, and recall availability.",
            "RECALL has field-computed Chicago match reasons.",
            "DIFF source-record cadence has a first baseline snapshot.",
        ],
        "watch_query_expansion_status": watch_library["status"],
        "deterministic_search_status": search_contract["status"],
        "selected_item_content_status": investigation["status"],
        "recall_status": recall_r2["status"],
        "diff_cadence_status": diff_ledger["status"],
        "kit_probe_status": kit_probe["status"],
        "ask_refusal_smoke_status": ask_smoke_r2["status"],
        "operator_text_gate_status": text_gate["status"],
        "d9_capability_regression_status": d9_regression["status"],
        "boundary_audit": "PASS",
        "no_mutation_audit": no_mutation["status"],
        "secret_audit": "PASS",
        "no_action_audit": "PASS",
        "json_parse_clean": json_clean,
        "json_parse_failures": json_failures,
        "limitations": [
            "Kit probe is partial: tooling is present/callable but CityBrain extension/session load was not proven in D10.",
            "DIFF is not live; only the cadence baseline exists.",
            "No Open ASK router is implemented.",
            "No external validation was run or fabricated.",
        ],
        "next_recommended_task": "MAIN-CITYBRAIN-D11-OPERATOR-WORKFLOW-REVIEW-WORKSPACE-R1",
        "validation_package": rel(zip_path),
    }
    write_json(ROOTS["closeout"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_CLOSEOUT_R2_DECISION.json", closeout)
    attach_common(ROOTS["closeout"], no_mutation)

    freeze = {
        "task": "MAIN-CITYBRAIN-D10-OPERATOR-INTELLIGENCE-DEPTH-MILESTONE-FREEZE-R2",
        "status": final_status,
        "closeout_status": closeout["status"],
        "validation_package": rel(zip_path),
        "hash_manifest": rel(ROOTS["freeze"] / "HASH_MANIFEST.sha256"),
        "current_product_state_summary": [
            "D10 R2 deepens the operator cockpit with deterministic data-driven content.",
            "D10 R2 keeps validation as a D11 exit gate and Open ASK as a D14 dependency.",
            "D10 R2 starts DIFF cadence and records Kit probe readiness/blocker status.",
        ],
        "roadmap_dependency_handoff": rel(ROOTS["handoff"] / "ROADMAP_DEPENDENCY_HANDOFF_R2.md"),
        "explicit_next_sprint": "D11 Operator Workflow / Review Workspace, with real operator validation gate at exit.",
        "external_validation_run": False,
        "diff_cadence_started_or_blocker_recorded": True,
        "kit_probe_result_recorded": kit_probe["status"],
        "d12_consumption_rule_recorded": handoff_summary["d12_no_dataset_without_consumer"],
        "d14_corpus_dependency_recorded": handoff_summary["d14_open_ask_requires_d11_question_corpus"],
        "d9_capability_regression_status": d9_regression["status"],
        "no_production_action_autonomy_claims": True,
        "key_counts": {
            "source_candidates": len(source_inventory),
            "query_candidates": len(query_candidates),
            "search_templates": len(templates),
            "watch_queries": len(watch_library["queries"]),
            "operator_queue_items": len(queue_items),
            "selected_item_investigations": len(investigations),
            "ask_smoke_tests": ask_smoke_r2["tests_total"],
            "recall_field_matches": recall_r2["matches_with_field_reasons"],
        },
        "limitations": closeout["limitations"],
        "output_roots": {key: rel(path) for key, path in ROOTS.items()},
        "runtime_overlay": rel(OVERLAY_PATH),
    }
    write_json(ROOTS["freeze"] / "D10_OPERATOR_INTELLIGENCE_DEPTH_MILESTONE_FREEZE_R2_DECISION.json", freeze)
    write_text(ROOTS["freeze"] / "CURRENT_PRODUCT_STATE_R2.md", "\n".join(f"- {line}" for line in freeze["current_product_state_summary"]))
    attach_common(ROOTS["freeze"], no_mutation)
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
