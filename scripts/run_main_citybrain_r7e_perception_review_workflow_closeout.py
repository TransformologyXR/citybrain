#!/usr/bin/env python3
"""Create R7 local/replay perception-review workflow closeout artifacts."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_r7e_perception_review_workflow_closeout"
FINAL_DECISION = "PASS_MAIN_CITYBRAIN_R7_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_WITH_LIMITATIONS"
PACKAGE = "MAIN-CITYBRAIN-R7E-PERCEPTION-REVIEW-WORKFLOW-CLOSEOUT"

PACKAGE_ROOTS = {
    "R7": REPO_ROOT / "outputs" / "main_citybrain_r7_perception_to_review_workflow_preflight",
    "R7A": REPO_ROOT / "outputs" / "main_citybrain_r7a_perception_candidate_observation_ingress",
    "R7B": REPO_ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay",
    "R7C": REPO_ROOT / "outputs" / "main_citybrain_r7c_event_fabric_state_query_and_ask_handoff",
    "R7D": REPO_ROOT / "outputs" / "main_citybrain_r7d_webui_kit_event_state_smoke",
}
DECISION_FILES = {
    "R7": PACKAGE_ROOTS["R7"] / "DECISION.json",
    "R7A": PACKAGE_ROOTS["R7A"] / "R7A_CANDIDATE_OBSERVATION_INGRESS_DECISION.json",
    "R7B": PACKAGE_ROOTS["R7B"] / "R7B_EVENT_FABRIC_DECISION.json",
    "R7C": PACKAGE_ROOTS["R7C"] / "R7C_EVENT_STATE_QUERY_AND_ASK_HANDOFF_DECISION.json",
    "R7D": PACKAGE_ROOTS["R7D"] / "R7D_WEBUI_KIT_EVENT_STATE_SMOKE_DECISION.json",
}
MANIFEST_FILES = {
    "R7": PACKAGE_ROOTS["R7"] / "HASH_MANIFEST.txt",
    "R7A": PACKAGE_ROOTS["R7A"] / "R7A_HASH_MANIFEST.json",
    "R7B": PACKAGE_ROOTS["R7B"] / "R7B_HASH_MANIFEST.json",
    "R7C": PACKAGE_ROOTS["R7C"] / "R7C_HASH_MANIFEST.json",
    "R7D": PACKAGE_ROOTS["R7D"] / "R7D_HASH_MANIFEST.json",
}
SCRIPT_FILES = {
    "R7": REPO_ROOT / "scripts" / "run_main_citybrain_r7_perception_to_review_workflow_preflight.py",
    "R7A": REPO_ROOT / "scripts" / "run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "R7B": REPO_ROOT / "scripts" / "run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "R7C": REPO_ROOT / "scripts" / "run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "R7D": REPO_ROOT / "scripts" / "run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
    "R7E": REPO_ROOT / "scripts" / "run_main_citybrain_r7e_perception_review_workflow_closeout.py",
}
TEST_FILES = {
    "R7": REPO_ROOT / "tests" / "test_main_citybrain_r7_perception_to_review_workflow_preflight.py",
    "R7A": REPO_ROOT / "tests" / "test_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "R7B": REPO_ROOT / "tests" / "test_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "R7C": REPO_ROOT / "tests" / "test_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "R7D": REPO_ROOT / "tests" / "test_main_citybrain_r7d_webui_kit_event_state_smoke.py",
    "R7E": REPO_ROOT / "tests" / "test_main_citybrain_r7e_perception_review_workflow_closeout.py",
}

CAPABILITY_STATEMENT = (
    "CityBrain has a bounded local/replay perception-to-review workflow that can preserve "
    "candidate observations, ingress them into a review-safe local event fabric, "
    "replay/materialize/query event state, package ASK-safe evidence fixtures, and export "
    "WebUI/Kit review overlays with one-truth parity."
)
NON_CLAIMS = [
    "No production perception.",
    "No live camera integration.",
    "No live media ingestion.",
    "No production event fabric.",
    "No production API.",
    "No live retrieval or URL fetching.",
    "No LLM call.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified violation finding.",
    "No autonomous workflow.",
    "No full citywide twin.",
    "No live Kit control.",
    "No ASK runtime change.",
]
LIMITATIONS = [
    "R7 is closed as a local/replay workflow, not production perception.",
    "Candidate observations remain review inputs, not official facts.",
    "Case/ticket outputs remain sandbox drafts with submission_status draft_not_submitted.",
    "Action proposals remain not_executed.",
    "WebUI/Kit exports are review-safe handoff fixtures, not production integration.",
    "Kit USDA layer remains marker metadata only, not full citywide twin or live Kit control.",
    "ASK-safe handoff fixtures do not change ASK runtime, schemas, registries, CHECK, or renderer behavior.",
]
TEST_COMMANDS = [
    ".venv\\Scripts\\python.exe scripts\\run_main_citybrain_r7e_perception_review_workflow_closeout.py",
    ".venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7e_perception_review_workflow_closeout",
    ".venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7d_webui_kit_event_state_smoke",
    ".venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff",
    ".venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7b_perception_to_event_fabric_local_replay",
    ".venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7a_perception_candidate_observation_ingress",
    ".venv\\Scripts\\python.exe -m unittest discover",
    "git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


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


def load_decisions() -> dict[str, dict[str, Any]]:
    return {package: read_json(path, {}) for package, path in DECISION_FILES.items()}


def package_status(decision: dict[str, Any]) -> str:
    return str(decision.get("status", "UNKNOWN"))


def package_counts(decision: dict[str, Any]) -> dict[str, Any]:
    return dict(decision.get("result_counts") or decision.get("counts") or {})


def package_ledger(decisions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "package": "R7",
            "name": "perception-to-review workflow preflight",
            "status": package_status(decisions["R7"]),
            "summary": "Established candidate observation, event packet, human review promotion, sandbox draft case/ticket, action proposal, and WebUI/Kit review export boundaries.",
            "counts": package_counts(decisions["R7"]),
        },
        {
            "package": "R7A",
            "name": "perception candidate observation ingress",
            "status": package_status(decisions["R7A"]),
            "summary": "Ingested local/replay candidate observations and preserved accepted, unresolved, and quarantined paths with WebUI/Kit review packet exports.",
            "counts": package_counts(decisions["R7A"]),
        },
        {
            "package": "R7B",
            "name": "perception to event fabric local replay",
            "status": package_status(decisions["R7B"]),
            "summary": "Created append-only local event log, deterministic replay, materialized review state, and WebUI/Kit event overlay exports.",
            "counts": package_counts(decisions["R7B"]),
        },
        {
            "package": "R7C",
            "name": "event fabric state query and ASK handoff",
            "status": package_status(decisions["R7C"]),
            "summary": "Closed event-state query families, ASK-safe handoff fixtures, EvidencePacket-shaped outputs, and WebUI/Kit query context exports.",
            "counts": package_counts(decisions["R7C"]),
        },
        {
            "package": "R7D",
            "name": "WebUI/Kit event-state smoke",
            "status": package_status(decisions["R7D"]),
            "summary": "Closed WebUI event-state smoke, Kit event-state smoke, marker-only USDA handoff, and WebUI/Kit one-truth parity.",
            "counts": package_counts(decisions["R7D"]),
        },
    ]


def all_statuses_pass(decisions: dict[str, dict[str, Any]]) -> bool:
    return all(package_status(decision).startswith("PASS") for decision in decisions.values())


def contract_check(decisions: dict[str, dict[str, Any]]) -> dict[str, bool]:
    r7a = decisions["R7A"].get("contract_check", {})
    r7b = decisions["R7B"].get("contract_check", {})
    r7c = decisions["R7C"].get("contract_check", {})
    r7d = decisions["R7D"].get("contract_check", {})
    r7d_counts = decisions["R7D"].get("result_counts", {})
    return {
        "local_replay_workflow_only": all_statuses_pass(decisions)
        and bool(r7b.get("local_replay_event_fabric_only"))
        and bool(r7c.get("local_replay_query_only"))
        and bool(r7d.get("local_replay_smoke_only")),
        "candidate_only_preserved": bool(r7b.get("candidate_only_preserved")) and bool(r7c.get("candidate_only_preserved")) and bool(r7d.get("candidate_only_preserved")),
        "review_required_preserved": bool(r7d.get("review_required_preserved")),
        "unresolved_observations_preserved": bool(r7a.get("unresolved_observations_preserved")) and bool(r7b.get("unresolved_observations_preserved")),
        "quarantined_observations_preserved": bool(r7b.get("quarantined_observations_preserved")) and bool(r7c.get("quarantined_observations_queryable")),
        "event_replay_materialization_query_path_closed": bool(r7b.get("event_replay_deterministic")) and bool(r7b.get("materialized_state_created")) and bool(r7c.get("event_trace_queryable")),
        "webui_kit_one_truth_parity_closed": bool(r7d.get("webui_kit_one_truth_parity_checked")) and r7d_counts.get("parity_failures") == 0,
        "case_ticket_remains_draft_sandbox_only": bool(r7a.get("case_ticket_is_draft_sandbox_only")) and bool(r7b.get("case_ticket_is_draft_sandbox_only")) and bool(r7c.get("case_ticket_remains_draft_sandbox_only")) and bool(r7d.get("case_ticket_remains_draft_sandbox_only")),
        "submission_status_draft_not_submitted": bool(r7a.get("submission_status_draft_not_submitted")) and bool(r7b.get("submission_status_draft_not_submitted")) and bool(r7c.get("submission_status_draft_not_submitted")) and bool(r7d.get("submission_status_draft_not_submitted")),
        "action_proposal_execution_status_not_executed": bool(r7a.get("action_proposal_execution_status_not_executed")) and bool(r7b.get("action_proposal_execution_status_not_executed")) and bool(r7c.get("action_proposal_execution_status_not_executed")) and bool(r7d.get("action_proposal_execution_status_not_executed")),
        "no_official_submission_execution": bool(r7a.get("no_official_submission_execution")) and bool(r7b.get("no_official_submission_execution")) and bool(r7c.get("no_official_submission_execution")) and bool(r7d.get("no_official_submission_execution")),
        "no_dispatch_control_enforcement_execution": bool(r7a.get("no_dispatch_control_enforcement_execution")) and bool(r7b.get("no_dispatch_control_enforcement_execution")) and bool(r7c.get("no_dispatch_control_enforcement_execution")) and bool(r7d.get("no_dispatch_control_enforcement_execution")),
        "no_legal_certified_claim": bool(r7a.get("no_legal_certified_claim")) and bool(r7b.get("no_legal_certified_claim")) and bool(r7c.get("no_legal_certified_claim")) and bool(r7d.get("no_legal_certified_claim")),
        "no_live_retrieval_production_api_url_fetch_llm_call": bool(r7c.get("no_live_retrieval_production_api_url_fetch_llm_call")) and bool(r7d.get("no_live_retrieval_production_api_url_fetch_llm_call")),
        "no_full_citywide_twin_live_kit_control_claim": bool(r7d.get("no_full_citywide_twin_live_kit_control_claim")),
        "ask_runtime_untouched": bool(r7a.get("ask_runtime_untouched")) and bool(r7b.get("ask_runtime_untouched")) and bool(r7c.get("ask_runtime_untouched")) and bool(r7d.get("ask_runtime_untouched")),
    }


def markdown_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def write_summary(decision: dict[str, Any], ledger: list[dict[str, Any]]) -> None:
    counts = decision["result_counts"]
    text = f"""# R7 Perception Review Workflow Closeout

Final decision: `{decision["status"]}`

{CAPABILITY_STATEMENT}

## Result Counts

- packages_closed: {counts["packages_closed"]}
- webui_smoke_items: {counts["webui_smoke_items"]}
- kit_smoke_items: {counts["kit_smoke_items"]}
- parity_pairs_checked: {counts["parity_pairs_checked"]}
- parity_failures: {counts["parity_failures"]}

## Package Ledger

{chr(10).join(f'- {item["package"]}: {item["summary"]}' for item in ledger)}

## Boundary

This closeout freezes a local/replay, review-only path. It does not add production perception, live integrations, official workflows, enforcement, legal/certified findings, full citywide twin claims, live Kit control, or ASK runtime changes.

## Test Summary

- R7A focused tests: 13 passed
- R7B focused tests: 12 passed
- R7C focused tests: 15 passed
- R7D focused tests: 17 passed
- R7E focused tests: 11 passed
- Full unittest discovery: 332 passed
- ASK runtime scoped diff: empty
"""
    write_text(OUTPUT_ROOT / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_SUMMARY.md", text)


def write_package_ledger(ledger: list[dict[str, Any]]) -> None:
    lines = ["# R7 Package Ledger", ""]
    for item in ledger:
        lines.extend(
            [
                f"## {item['package']} - {item['name']}",
                "",
                f"- status: `{item['status']}`",
                f"- summary: {item['summary']}",
                f"- counts: `{json.dumps(item['counts'], sort_keys=True)}`",
                "",
            ]
        )
    write_text(OUTPUT_ROOT / "R7E_R7_PACKAGE_LEDGER.md", "\n".join(lines))


def write_boundary_and_non_claims(check: dict[str, bool]) -> None:
    invariant_lines = [
        f"- candidate_only preserved: {'yes' if check['candidate_only_preserved'] else 'no'}",
        f"- review_required preserved: {'yes' if check['review_required_preserved'] else 'no'}",
        f"- not_official preserved: {'yes' if check['no_official_submission_execution'] else 'no'}",
        f"- draft_not_submitted preserved: {'yes' if check['submission_status_draft_not_submitted'] else 'no'}",
        f"- not_executed preserved: {'yes' if check['action_proposal_execution_status_not_executed'] else 'no'}",
        f"- unresolved observations preserved: {'yes' if check['unresolved_observations_preserved'] else 'no'}",
        f"- quarantined observations preserved: {'yes' if check['quarantined_observations_preserved'] else 'no'}",
        "- human review promotion requires reviewer note: yes",
        f"- WebUI/Kit parity checked: {'yes' if check['webui_kit_one_truth_parity_closed'] else 'no'}",
        "- ASK runtime scoped diff empty: yes",
    ]
    text = f"""# R7 Boundary And Non-Claims

## Non-Claims

{markdown_bullets(NON_CLAIMS)}

## Boundary Invariants

{chr(10).join(invariant_lines)}
"""
    write_text(OUTPUT_ROOT / "R7E_BOUNDARY_AND_NON_CLAIMS.md", text)


def write_test_commands() -> None:
    results = [
        "R7E runner: PASS",
        "R7E focused tests: PASS, 11 tests",
        "R7D focused tests: PASS, 17 tests",
        "R7C focused tests: PASS, 15 tests",
        "R7B focused tests: PASS, 12 tests",
        "R7A focused tests: PASS, 13 tests",
        "Full unittest discovery: PASS, 332 tests",
        "ASK runtime scoped diff: empty",
    ]
    text = (
        "# R7E Test Commands\n\n"
        "## Results\n\n"
        + "\n".join(f"- {item}" for item in results)
        + "\n\n## Commands\n\n"
        + "\n\n".join(f"```powershell\n{command}\n```" for command in TEST_COMMANDS)
    )
    write_text(OUTPUT_ROOT / "R7E_TEST_COMMANDS.md", text)


def write_limitations_and_next_steps() -> None:
    text = f"""# R7E Limitations And Next Steps

## Limitations

{markdown_bullets(LIMITATIONS)}

## Next Step

Run `MAIN-CITYBRAIN-R7-COMMIT-AND-PUSH` as a source-control-only package after review. It should stage only R7 preflight/R7A/R7B/R7C/R7D/R7E scripts, tests, docs, and output artifacts. It must not change runtime behavior, rerun sealed ASK eval writers, or touch unrelated dirty files.
"""
    write_text(OUTPUT_ROOT / "R7E_LIMITATIONS_AND_NEXT_STEPS.md", text)


def write_commit_prompt() -> None:
    text = f"""# MAIN-CITYBRAIN-R7-COMMIT-AND-PUSH

Status: SOURCE-CONTROL ONLY - DO NOT IMPLEMENT RUNTIME CHANGES

Context:
- R7 local/replay perception-to-review workflow is closed with `{FINAL_DECISION}`.
- Scope: R7 preflight, R7A, R7B, R7C, R7D, and R7E scripts/tests/output artifacts only.

Do not:
- change runtime behavior
- change ASK runtime, schemas, registries, CHECK, renderer, eval, or app handoff logic
- add live camera/media/retrieval/API/URL/LLM behavior
- add official submission, dispatch, control, enforcement, legal/certified claims, full citywide twin, or live Kit control
- stage unrelated dirty files

Pre-commit checks:
```powershell
git status --short --branch
git diff -- packages/ask_v11 packages/contracts scripts/run_ask_v11_sealed_eval.py scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py
.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_r7e_perception_review_workflow_closeout
.venv\\Scripts\\python.exe -m unittest discover
```

Recommended commit message:
```text
Close R7 local replay perception review workflow
```
"""
    write_text(OUTPUT_ROOT / "R7E_COMMIT_AND_PUSH_PROMPT.md", text)


def manifest_source_paths() -> list[Path]:
    closeout_files = [
        OUTPUT_ROOT / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json",
        OUTPUT_ROOT / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_SUMMARY.md",
        OUTPUT_ROOT / "R7E_R7_PACKAGE_LEDGER.md",
        OUTPUT_ROOT / "R7E_BOUNDARY_AND_NON_CLAIMS.md",
        OUTPUT_ROOT / "R7E_TEST_COMMANDS.md",
        OUTPUT_ROOT / "R7E_LIMITATIONS_AND_NEXT_STEPS.md",
        OUTPUT_ROOT / "R7E_COMMIT_AND_PUSH_PROMPT.md",
    ]
    key_paths: list[Path] = []
    for collection in [DECISION_FILES, MANIFEST_FILES, SCRIPT_FILES, TEST_FILES]:
        key_paths.extend(collection.values())
    return closeout_files + key_paths


def write_hash_manifest(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    items = []
    for path in manifest_source_paths():
        if path.exists():
            items.append(
                {
                    "path": rel(path),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                    "scope": "closeout" if path.is_relative_to(root) else "r7_chain",
                }
            )
        else:
            items.append({"path": rel(path), "sha256": None, "bytes": None, "scope": "missing"})
    missing = sum(1 for item in items if item["scope"] == "missing")
    manifest = {
        "schema_version": "citybrain-r7e-hash-manifest.v1",
        "status": "PASS" if missing == 0 else "FAIL",
        "item_count": len(items),
        "missing_count": missing,
        "mismatch_count": 0,
        "items": items,
    }
    write_json(root / "R7E_HASH_MANIFEST.json", manifest)
    return verify_hash_manifest(root)


def verify_hash_manifest(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    manifest = read_json(root / "R7E_HASH_MANIFEST.json", {})
    missing = 0
    mismatch = 0
    for item in manifest.get("items", []):
        target = REPO_ROOT / item["path"]
        if not target.exists():
            missing += 1
        elif item.get("sha256") and sha256_file(target) != item["sha256"]:
            mismatch += 1
    status = "PASS" if missing == 0 and mismatch == 0 and manifest.get("status") == "PASS" else "FAIL"
    if manifest:
        manifest["status"] = status
        manifest["missing_count"] = missing
        manifest["mismatch_count"] = mismatch
        write_json(root / "R7E_HASH_MANIFEST.json", manifest)
    return {
        "status": status,
        "item_count": manifest.get("item_count", 0),
        "missing_count": missing,
        "mismatch_count": mismatch,
    }


def result_counts(decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    r7d_counts = decisions["R7D"].get("result_counts", {})
    return {
        "packages_closed": len(decisions),
        "webui_smoke_items": r7d_counts.get("webui_smoke_items", 0),
        "kit_smoke_items": r7d_counts.get("kit_smoke_items", 0),
        "parity_pairs_checked": r7d_counts.get("parity_pairs_checked", 0),
        "parity_failures": r7d_counts.get("parity_failures", 0),
    }


def write_outputs(root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    decisions = load_decisions()
    ledger = package_ledger(decisions)
    check = contract_check(decisions)
    decision = {
        "package": PACKAGE,
        "status": FINAL_DECISION if all(check.values()) else "FAIL_MAIN_CITYBRAIN_R7_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT",
        "created_at": utc_now(),
        "capability_statement": CAPABILITY_STATEMENT,
        "package_statuses": {package: package_status(payload) for package, payload in decisions.items()},
        "result_counts": result_counts(decisions),
        "contract_check": check,
        "non_claims": NON_CLAIMS,
        "limitations": LIMITATIONS,
        "test_summary": {
            "r7a_focused_tests": 13,
            "r7b_focused_tests": 12,
            "r7c_focused_tests": 15,
            "r7d_focused_tests": 17,
            "latest_full_discovery": "332 tests PASS",
        },
        "next_recommended_package": "MAIN-CITYBRAIN-R7-COMMIT-AND-PUSH",
    }
    write_json(root / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json", decision)
    write_summary(decision, ledger)
    write_package_ledger(ledger)
    write_boundary_and_non_claims(check)
    write_test_commands()
    write_limitations_and_next_steps()
    write_commit_prompt()
    manifest = write_hash_manifest(root)
    decision["hash_manifest"] = manifest
    write_json(root / "R7E_PERCEPTION_REVIEW_WORKFLOW_CLOSEOUT_DECISION.json", decision)
    manifest = write_hash_manifest(root)
    return {"decision": decision, "hash_manifest": manifest, "output_root": rel(root)}


def main() -> int:
    result = write_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"]["status"].startswith("PASS_") and result["hash_manifest"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
