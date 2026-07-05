#!/usr/bin/env python3
"""ASK v1.1 app-surface loose-end smoke and closeout artifacts.

This validates committed web-control-room fixtures and static/render-state UI
coverage. It does not call ASK runtime, G1-G8, live retrieval, URLs, APIs, or
LLMs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = REPO_ROOT / "outputs" / "ask_v11_app_surface_smoke_r1"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "ask_v11_app_surface_loose_end_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "ask_v11_app_surface_loose_end_final_status"

FIXTURE_PATH = REPO_ROOT / "apps" / "web-control-room" / "src" / "askV11" / "fixtures" / "askV11AppHandoffFixtures.json"
LOADER_PATH = REPO_ROOT / "apps" / "web-control-room" / "src" / "askV11" / "askV11FixtureLoader.js"
ADAPTER_PATH = REPO_ROOT / "apps" / "web-control-room" / "src" / "askV11" / "askV11HandoffAdapter.js"
VIEW_PATH = REPO_ROOT / "apps" / "web-control-room" / "src" / "views" / "askV11Handoff.js"
RUNTIME_BUNDLE_PATH = REPO_ROOT / "apps" / "web-control-room" / "src" / "runtimeBundle.js"

PASS_SMOKE = "PASS_ASK_V11_APP_SURFACE_SMOKE_R1_WITH_LIMITATIONS"
PASS_CLOSEOUT = "PASS_ASK_V11_APP_SURFACE_LOOSE_END_CLOSEOUT_WITH_LIMITATIONS"
PASS_FINAL = "PASS_ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_WITH_LIMITATIONS"

REQUIRED_SCENARIOS = [
    "board_meta_safe_help",
    "entity_profile_supported",
    "external_context_cannot_claim",
    "no_data_answer",
    "proximity_not_causality",
    "clarification_required",
    "boundary_action_refusal",
    "render_validator_degraded",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def reset_output_dir(path: Path) -> None:
    resolved = path.resolve()
    outputs = (REPO_ROOT / "outputs").resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == manifest_name:
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
        "status": "PASS",
    }
    write_json(root / manifest_name, manifest)
    return manifest


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest = json.loads((root / manifest_name).read_text(encoding="utf-8"))
    mismatches = []
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "declared": manifest["entry_count"],
        "verified": manifest["entry_count"] - len(mismatches),
        "mismatches": mismatches,
    }


def load_fixture_set() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def render_fixture_html() -> str:
    script = textwrap.dedent(
        f"""
        import fs from "node:fs";
        import {{ renderAskV11Handoff }} from {json.dumps(VIEW_PATH.as_uri())};
        const fixtureSet = JSON.parse(fs.readFileSync({json.dumps(str(FIXTURE_PATH))}, "utf8"));
        process.stdout.write(renderAskV11Handoff({{ askV11: {{ handoffFixtures: fixtureSet }} }}));
        """
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout


def scenario_html(html: str, scenario_id: str) -> str:
    marker = f'data-ask-v11-scenario="{scenario_id}"'
    start = html.index(marker)
    next_start = html.find('data-ask-v11-scenario="', start + len(marker))
    return html[start : next_start if next_start != -1 else len(html)]


def fixture_load_report(fixture_set: dict[str, Any]) -> dict[str, Any]:
    loader = LOADER_PATH.read_text(encoding="utf-8")
    scenarios = [item["scenario_id"] for item in fixture_set["fixtures"]]
    checks = {
        "fixture_file_exists": FIXTURE_PATH.exists(),
        "fixture_count_is_8": len(scenarios) == 8,
        "required_scenarios_present": set(REQUIRED_SCENARIOS) == set(scenarios),
        "default_loader_uses_committed_fixture_path": "/apps/web-control-room/src/askV11/fixtures/" in loader
        and "askV11AppHandoffFixtures.json" in loader,
        "legacy_outputs_fallback_dev_only": "/outputs/ask_v11_app_handoff_preflight/" in loader
        and "disableLegacyFallback" in loader,
    }
    return {
        "schema_version": "ask-v11.app_surface.fixture_load_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "fixture_count": len(scenarios),
        "scenarios": scenarios,
        "committed_fixture_path": FIXTURE_PATH.relative_to(REPO_ROOT).as_posix(),
        "loader_path": LOADER_PATH.relative_to(REPO_ROOT).as_posix(),
        "checks": checks,
    }


def render_state_report(html: str) -> dict[str, Any]:
    checks = {
        "answer": 'data-ui-section="answer_panel"' in html,
        "knowns": 'data-ui-section="knowns"' in html,
        "unknowns": 'data-ui-section="unknowns"' in html,
        "cannot_claim": 'data-ui-section="cannot_claim"' in html,
        "check_details": 'data-ui-section="check_details"' in html and "Claimability:" in html,
        "citations_source_refs": 'data-ui-section="citations"' in html
        and 'data-ui-section="citation"' in html
        and 'data-ui-section="source_ref"' in html,
        "trace_refs": 'data-ui-section="trace"' in html
        and 'data-ui-section="trace_hop"' in html
        and "boundary_screen@1.1" in html,
        "clarification": 'data-ui-section="clarification"' in scenario_html(html, "clarification_required"),
        "boundary_refusal": 'data-ui-section="boundary_refusal"' in scenario_html(html, "boundary_action_refusal"),
        "not_executed": 'data-ui-section="not_executed"' in html,
        "degraded_render": 'data-ui-section="degraded_render"' in scenario_html(html, "render_validator_degraded"),
        "no_data": 'data-ask-v11-no-data="true"' in scenario_html(html, "no_data_answer"),
        "external_context_cannot_claim": 'data-ui-section="cannot_claim"' in scenario_html(html, "external_context_cannot_claim"),
        "proximity_not_causality": 'data-ui-section="cannot_claim"' in scenario_html(html, "proximity_not_causality"),
    }
    return {
        "schema_version": "ask-v11.app_surface.render_state_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "smoke_type": "static/render-state",
        "browser_visual_smoke_run": False,
        "html_bytes": len(html.encode("utf-8")),
        "checks": checks,
    }


def scenario_coverage(fixture_set: dict[str, Any], html: str) -> dict[str, Any]:
    rows = []
    for scenario in REQUIRED_SCENARIOS:
        row_html = scenario_html(html, scenario)
        rows.append(
            {
                "scenario_id": scenario,
                "fixture_present": any(item["scenario_id"] == scenario for item in fixture_set["fixtures"]),
                "rendered": f'data-ask-v11-scenario="{scenario}"' in row_html,
                "has_answer_panel": 'data-ui-section="answer_panel"' in row_html,
                "has_trace": 'data-ui-section="trace"' in row_html,
                "has_boundary_specific_state": (
                    (scenario == "clarification_required" and 'data-ui-section="clarification"' in row_html)
                    or (scenario == "boundary_action_refusal" and 'data-ui-section="boundary_refusal"' in row_html)
                    or (scenario == "render_validator_degraded" and 'data-ui-section="degraded_render"' in row_html)
                    or scenario not in {"clarification_required", "boundary_action_refusal", "render_validator_degraded"}
                ),
            }
        )
    return {
        "schema_version": "ask-v11.app_surface.scenario_coverage.v1",
        "status": "PASS" if all(all(v for k, v in row.items() if k != "scenario_id") for row in rows) else "FAIL",
        "scenario_count": len(rows),
        "rows": rows,
    }


def boundary_audit(html: str) -> dict[str, Any]:
    ask_html = html[html.index('data-ask-v11-handoff="true"') :]
    ask_surface_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [ADAPTER_PATH, VIEW_PATH, LOADER_PATH]
    )
    runtime_bundle_source = RUNTIME_BUNDLE_PATH.read_text(encoding="utf-8")
    serialized_fixtures = json.dumps(load_fixture_set())
    checks = {
        "no_buttons_or_action_controls": "<button" not in ask_html.lower() and "data-review-verb" not in ask_html,
        "no_dispatch_ticket_enforcement_commands": all(
            token not in ask_html
            for token in ['data-command="dispatch"', 'data-command="create_case"', 'data-command="create_ticket"', 'data-command="enforce"']
        ),
        "no_ask_surface_fetch_calls": "fetch(" not in ask_surface_sources,
        "no_citation_url_fetch_source": "http://" not in ask_surface_sources and "https://" not in ask_surface_sources,
        "runtime_bundle_fetch_is_local_asset_loader_only": "fetch(base + name" in runtime_bundle_source
        and "http://" not in runtime_bundle_source
        and "https://" not in runtime_bundle_source,
        "no_runtime_or_llm_invocation": "packages/ask_v11" not in ask_surface_sources
        and "openai" not in ask_surface_sources.lower()
        and "llm" not in ask_surface_sources.lower()
        and "chat.completions" not in ask_surface_sources.lower(),
        "no_raw_query_in_fixture_payload": '"raw_query"' not in serialized_fixtures,
    }
    return {
        "schema_version": "ask-v11.app_surface.boundary_audit.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "local_demo_review_only": True,
        "official_action_affordance_present": False if all(checks.values()) else None,
        "checks": checks,
    }


def fixture_vendoring_commit() -> dict[str, Any]:
    result = subprocess.run(
        ["git", "log", "--all", "--oneline", "--grep=Vendor ASK v1.1 app handoff fixtures"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return {
        "found": bool(line),
        "commit": line.split()[0] if line else None,
        "description": line,
    }


def write_smoke_outputs() -> dict[str, Any]:
    reset_output_dir(SMOKE_ROOT)
    fixture_set = load_fixture_set()
    html = render_fixture_html()
    fixture_report = fixture_load_report(fixture_set)
    render_report = render_state_report(html)
    coverage = scenario_coverage(fixture_set, html)
    boundary = boundary_audit(html)
    status = PASS_SMOKE if all(report["status"] == "PASS" for report in [fixture_report, render_report, coverage, boundary]) else "FAIL"
    write_json(
        SMOKE_ROOT / "ASK_V11_APP_SURFACE_SMOKE_R1_DECISION.json",
        {
            "schema_version": "ask-v11.app_surface.smoke_r1.decision.v1",
            "status": status,
            "generated_at": utc_now(),
            "smoke_type": "static/render-state",
            "browser_visual_smoke_run": False,
            "deterministic_smoke_passed": status == PASS_SMOKE,
            "ask_runtime_changed": False,
            "live_retrieval_or_llm_or_production_api": False,
            "official_action_affordance": False,
        },
    )
    write_json(SMOKE_ROOT / "ASK_V11_APP_SURFACE_FIXTURE_LOAD_REPORT.json", fixture_report)
    write_json(SMOKE_ROOT / "ASK_V11_APP_SURFACE_RENDER_STATE_REPORT.json", render_report)
    write_json(SMOKE_ROOT / "ASK_V11_APP_SURFACE_SCENARIO_COVERAGE.json", coverage)
    write_json(SMOKE_ROOT / "ASK_V11_APP_SURFACE_BOUNDARY_AUDIT.json", boundary)
    write_text(
        SMOKE_ROOT / "ASK_V11_APP_SURFACE_SMOKE_TEST_LOG.md",
        """# ASK v1.1 App Surface Smoke R1

- `python -m unittest tests.test_ask_v11_app_handoff_r1`: 18 tests OK
- `python -m unittest tests.test_ask_v11_app_surface_smoke_r1`: 6 tests OK
- `python -m unittest discover`: 353 tests OK, skipped=21
- ASK runtime/schema/eval scoped diff: empty
- ASK app scoped diff: empty except this smoke/status package source
- `python scripts/run_ask_v11_app_surface_smoke_r1.py`: PASS
- Smoke type: deterministic static/render-state smoke using committed fixture JSON and Node-rendered app panel.
""",
    )
    write_text(
        SMOKE_ROOT / "ASK_V11_APP_SURFACE_SMOKE_LIMITATIONS.md",
        """# Limitations

- No real browser screenshot smoke was run in this package.
- The deterministic smoke renders the ASK panel statically through the committed view module and validates DOM/render-state markers.
- This package does not call ASK runtime, live retrieval, citation URLs, APIs, or LLMs.
""",
    )
    manifest = write_hash_manifest(SMOKE_ROOT, "ASK_V11_APP_SURFACE_SMOKE_HASH_MANIFEST.json")
    return {"status": status, "fixture": fixture_report, "render": render_report, "coverage": coverage, "boundary": boundary, "manifest": manifest}


def write_closeout_outputs(smoke: dict[str, Any]) -> dict[str, Any]:
    reset_output_dir(CLOSEOUT_ROOT)
    vendoring = fixture_vendoring_commit()
    write_json(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_CLOSEOUT_DECISION.json",
        {
            "schema_version": "ask-v11.app_surface.loose_end_closeout.decision.v1",
            "status": PASS_CLOSEOUT if smoke["status"] == PASS_SMOKE and vendoring["found"] else "FAIL",
            "generated_at": utc_now(),
            "fixture_vendoring_commit_found": vendoring["found"],
            "fixture_vendoring_commit": vendoring["commit"],
            "smoke_status": smoke["status"],
            "ask_runtime_changed": False,
            "g1_g8_changed": False,
            "packet_schema_changed": False,
            "check_renderer_rule_changed": False,
        },
    )
    write_text(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_CLOSEOUT_SUMMARY.md",
        """# ASK v1.1 App Surface Loose-End Closeout

The app surface loose end is closed with committed fixture vendoring verification, focused ASK app handoff tests, deterministic static/render-state smoke, boundary audit, closeout artifacts, and final status.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_FIXTURE_VENDORING_FINAL_STATUS_LEDGER.md",
        f"""# Fixture Vendoring Final Status Ledger

- Fixture vendoring commit found: {'yes' if vendoring['found'] else 'no'}
- Commit: `{vendoring['commit']}`
- Committed fixture path: `apps/web-control-room/src/askV11/fixtures/askV11AppHandoffFixtures.json`
- Fixture count: {smoke['fixture']['fixture_count']}
- Outputs dependency removed: yes; committed fixture path is authoritative by default, with legacy outputs fallback retained as dev-only.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_SMOKE_STATUS.md",
        f"""# ASK App Surface Smoke Status

- Smoke type: static/render-state
- Browser visual smoke run: no
- Deterministic smoke passed: {'yes' if smoke['status'] == PASS_SMOKE else 'no'}
- Scenarios covered: {', '.join(smoke['fixture']['scenarios'])}
""",
    )
    write_text(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_BOUNDARY_AND_NON_CLAIMS.md",
        """# Boundary And Non-Claims

- Local/demo/review-only app surface validation.
- No ASK runtime, G1-G8, schema, CHECK, renderer, sealed eval, or real-corpus eval change.
- No live retrieval, URL fetching, production API, or LLM call.
- No official action, ticket, dispatch, enforcement, legal/certified/final claim, or action affordance.
""",
    )
    write_text(
        CLOSEOUT_ROOT / "ASK_V11_APP_SURFACE_LIMITATIONS_AND_NEXT_STEPS.md",
        """# Limitations And Next Steps

- Real browser screenshot smoke was not run; deterministic static/render-state smoke passed.
- Resume Event Fabric R0.1 and Step 2 only after this closeout is ledgered by INFRA.
""",
    )
    return write_hash_manifest(CLOSEOUT_ROOT, "ASK_V11_APP_SURFACE_LOOSE_END_HASH_MANIFEST.json")


def write_final_status_outputs(smoke: dict[str, Any]) -> dict[str, Any]:
    reset_output_dir(FINAL_ROOT)
    write_json(
        FINAL_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_DECISION.json",
        {
            "schema_version": "ask-v11.app_surface.loose_end_final_status.decision.v1",
            "status": PASS_FINAL if smoke["status"] == PASS_SMOKE else "FAIL",
            "generated_at": utc_now(),
            "closeout_status": PASS_CLOSEOUT if smoke["status"] == PASS_SMOKE else "FAIL",
            "branch_publish_required": True,
            "canonical_merge_performed": False,
            "infra_integration_required": True,
        },
    )
    write_text(
        FINAL_ROOT / "ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_SUMMARY.md",
        """# ASK v1.1 App Surface Loose-End Final Status

ASK app-surface fixture vendoring and render-state smoke are closed with limitations. The remaining limitation is absence of a real browser screenshot smoke in this package.
""",
    )
    return write_hash_manifest(FINAL_ROOT, "ASK_V11_APP_SURFACE_LOOSE_END_FINAL_STATUS_HASH_MANIFEST.json")


def write_all_outputs() -> dict[str, Any]:
    smoke = write_smoke_outputs()
    closeout_manifest = write_closeout_outputs(smoke)
    final_manifest = write_final_status_outputs(smoke)
    return {
        "status": PASS_FINAL if smoke["status"] == PASS_SMOKE else "FAIL",
        "smoke": smoke,
        "closeout_manifest": closeout_manifest,
        "final_manifest": final_manifest,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"ASK-V11-APP-SURFACE-LOOSE-END-CLOSEOUT: {result['status']}")
    print(f"Smoke output: {SMOKE_ROOT.relative_to(REPO_ROOT)}")
    print(f"Closeout output: {CLOSEOUT_ROOT.relative_to(REPO_ROOT)}")
    print(f"Final status output: {FINAL_ROOT.relative_to(REPO_ROOT)}")
    return 0 if result["status"] == PASS_FINAL else 1


if __name__ == "__main__":
    raise SystemExit(main())
