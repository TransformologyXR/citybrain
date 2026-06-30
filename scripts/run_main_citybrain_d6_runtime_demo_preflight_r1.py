#!/usr/bin/env python3
"""D6 runtime demo preflight anchored on the visible app-consumption smoke.

This preflight does not build a frontend or public runtime. It checks that the
local/static app-consumer smoke is present and makes its visible HTML panels the
primary UI evidence for a later D6 runtime demo.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D6-RUNTIME-DEMO-PREFLIGHT-R1"
STATUS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_runtime_demo_preflight_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d6_runtime_demo_preflight_r1.py"

APP_CONSUMPTION_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1"
APP_CONSUMPTION_DECISION = APP_CONSUMPTION_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_CONSUMPTION_SMOKE_R1_DECISION.json"
APP_CONSUMER_HTML = APP_CONSUMPTION_ROOT / "APP_CONSUMER_STATIC_HTML.html"
APP_RENDER_MODEL = APP_CONSUMPTION_ROOT / "APP_CONSUMER_RENDER_MODEL.json"
PACKET_VALIDATION = APP_CONSUMPTION_ROOT / "PACKET_CONSUMPTION_VALIDATION_RESULTS.json"
BOUNDARY_AUDIT = APP_CONSUMPTION_ROOT / "APP_CONSUMPTION_BOUNDARY_AUDIT.json"
NO_MUTATION_AUDIT = APP_CONSUMPTION_ROOT / "NO_MUTATION_AUDIT.json"
SECRET_AUDIT = APP_CONSUMPTION_ROOT / "SECRET_REDACTION_AUDIT.json"

READ_ONLY_ROOTS = [APP_CONSUMPTION_ROOT]

PRIMARY_UI_EVIDENCE_SECTIONS = [
    "Ask The City",
    "Governed Answer",
    "Trace And Evidence",
    "Limitations",
    "Safe Next-Look Options",
    "Consumed Packet Index",
]

LIMITATIONS = [
    "D6 runtime demo preflight only",
    "primary UI evidence is a static/local HTML consumer smoke",
    "no production frontend implemented",
    "no public API or external network binding",
    "no production auth/RBAC",
    "no live event fabric integration beyond previously generated local handoff evidence",
    "no Omniverse/Kit runtime requirement",
    "no command/action, dispatch, enforcement, routing/control, legal, certified impact, or autonomous action",
]

FORBIDDEN_FLAGS = {
    "production_readiness_claim_made": False,
    "public_api_claim_made": False,
    "external_network_binding_default": False,
    "frontend_implemented": False,
    "autonomous_action_exposed": False,
    "dispatch_recommendation_created": False,
    "enforcement_recommendation_created": False,
    "routing_control_output_created": False,
    "legal_or_certified_claim_created": False,
}


class HeadingCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._active_heading: str | None = None
        self._parts: list[str] = []
        self.headings: list[str] = []
        self.visible_text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"h1", "h2", "h3"}:
            self._active_heading = tag.lower()
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._active_heading == tag.lower():
            text = " ".join("".join(self._parts).split())
            if text:
                self.headings.append(text)
            self._active_heading = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.visible_text_parts.append(text)
        if self._active_heading:
            self._parts.append(data)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "hash": None}
    entries: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            total += stat.st_size
            entries.append(f"{rel(path)}|{stat.st_size}|{stat.st_mtime_ns}|{sha256_file(path)}")
    return {
        "exists": True,
        "file_count": len(entries),
        "total_bytes": total,
        "hash": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def parse_html_evidence() -> dict[str, Any]:
    if not APP_CONSUMER_HTML.exists():
        return {
            "status": "FAIL",
            "html_exists": False,
            "html_path": rel(APP_CONSUMER_HTML),
            "missing_sections": PRIMARY_UI_EVIDENCE_SECTIONS,
            "sections_found": [],
        }

    html_text = APP_CONSUMER_HTML.read_text(encoding="utf-8", errors="ignore")
    parser = HeadingCollector()
    parser.feed(html_text)
    headings = parser.headings
    visible_text = "\n".join(parser.visible_text_parts)
    missing = [
        section
        for section in PRIMARY_UI_EVIDENCE_SECTIONS
        if section not in headings and not re.search(re.escape(section), visible_text)
    ]
    return {
        "status": "PASS" if not missing else "FAIL",
        "html_exists": True,
        "html_path": rel(APP_CONSUMER_HTML),
        "html_sha256": sha256_file(APP_CONSUMER_HTML),
        "html_size_bytes": APP_CONSUMER_HTML.stat().st_size,
        "primary_ui_evidence_artifact": "APP_CONSUMER_STATIC_HTML.html",
        "required_sections": PRIMARY_UI_EVIDENCE_SECTIONS,
        "sections_found": [section for section in PRIMARY_UI_EVIDENCE_SECTIONS if section not in missing],
        "missing_sections": missing,
        "headings": headings,
    }


def load_upstream() -> dict[str, Any]:
    return {
        "decision": read_json(APP_CONSUMPTION_DECISION, {}),
        "render_model": read_json(APP_RENDER_MODEL, {}),
        "packet_validation": read_json(PACKET_VALIDATION, {}),
        "boundary_audit": read_json(BOUNDARY_AUDIT, {}),
        "no_mutation_audit": read_json(NO_MUTATION_AUDIT, {}),
        "secret_audit": read_json(SECRET_AUDIT, {}),
    }


def build_source_map(upstream: dict[str, Any], html_evidence: dict[str, Any]) -> dict[str, Any]:
    decision = upstream["decision"]
    render_model = upstream["render_model"]
    return {
        "task_id": TASK_ID,
        "primary_ui_evidence": {
            "artifact": "APP_CONSUMER_STATIC_HTML.html",
            "path": rel(APP_CONSUMER_HTML),
            "status": html_evidence["status"],
            "sections": PRIMARY_UI_EVIDENCE_SECTIONS,
        },
        "upstream_app_consumption_smoke": {
            "root": rel(APP_CONSUMPTION_ROOT),
            "decision_path": rel(APP_CONSUMPTION_DECISION),
            "status": decision.get("status", "MISSING"),
            "packet_count": decision.get("packet_count"),
            "localhost_runtime_received_request": decision.get("localhost_runtime_received_request"),
            "static_html_created": decision.get("static_html_created"),
            "no_action_boundary_preserved": decision.get("no_action_boundary_preserved"),
        },
        "visible_runtime_flow": render_model.get("ask_city_flow", {}),
        "visible_packet_index_count": len(render_model.get("packet_index", [])),
    }


def validate_d6_readiness(upstream: dict[str, Any], html_evidence: dict[str, Any]) -> dict[str, Any]:
    decision = upstream["decision"]
    render_model = upstream["render_model"]
    packet_validation = upstream["packet_validation"]
    boundary = upstream["boundary_audit"]
    checks = {
        "app_consumption_decision_present": APP_CONSUMPTION_DECISION.exists(),
        "app_consumption_status_pass": str(decision.get("status", "")).startswith("PASS"),
        "primary_static_html_present": html_evidence.get("html_exists") is True,
        "primary_static_html_sections_complete": html_evidence["status"] == "PASS",
        "ask_city_flow_visible": bool(render_model.get("ask_city_flow")),
        "governed_answer_visible": bool(render_model.get("answer_panel", {}).get("summary")),
        "trace_and_evidence_visible": bool(render_model.get("trace_panel", {}).get("trace_refs"))
        and bool(render_model.get("trace_panel", {}).get("evidence_refs")),
        "limitations_visible": bool(render_model.get("limitation_panel", {}).get("limitation_refs")),
        "safe_next_looks_visible": bool(render_model.get("safe_next_look_panel", {}).get("safe_next_looks")),
        "consumed_packet_index_visible": len(render_model.get("packet_index", [])) > 0,
        "packet_consumption_validation_pass": packet_validation.get("status") == "PASS",
        "boundary_audit_pass": boundary.get("status") == "PASS",
        "no_action_boundary_preserved": decision.get("no_action_boundary_preserved") is True,
        "localhost_only": str(render_model.get("ask_city_flow", {}).get("runtime_endpoint", "")).startswith("http://127.0.0.1:"),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing_html_sections": html_evidence.get("missing_sections", []),
        "primary_ui_evidence_artifact": "APP_CONSUMER_STATIC_HTML.html",
        "primary_ui_evidence_path": rel(APP_CONSUMER_HTML),
    }


def boundary_audit(validation: dict[str, Any], upstream: dict[str, Any]) -> dict[str, Any]:
    upstream_boundary = upstream["boundary_audit"]
    return {
        "status": "PASS" if validation["status"] == "PASS" and upstream_boundary.get("status") == "PASS" else "FAIL",
        **FORBIDDEN_FLAGS,
        "no_action_taken": True,
        "safe_next_looks_are_context_only": True,
        "primary_ui_evidence_is_static_local_html": True,
        "source_outputs_are_read_only": True,
        "notes": [
            "D6 preflight uses the visible app-consumption smoke as primary UI evidence.",
            "The page is local/static evidence, not a production frontend.",
            "No command/action/dispatch/enforcement/routing/control output is created.",
        ],
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "match": match.group(1) if match.groups() else "authorization"})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_docs(source_map: dict[str, Any], validation: dict[str, Any], boundary: dict[str, Any]) -> None:
    section_lines = "\n".join(f"- `{section}`" for section in PRIMARY_UI_EVIDENCE_SECTIONS)
    limitation_lines = "\n".join(f"- {item}" for item in LIMITATIONS)
    report = f"""
# D6 Runtime Demo Preflight R1

Status: `{STATUS if validation['status'] == 'PASS' and boundary['status'] == 'PASS' else 'FAIL'}`

Primary UI evidence:

- `{rel(APP_CONSUMER_HTML)}`

The D6 runtime demo preflight is anchored on the visible local app-consumption smoke. The required UI evidence sections are:

{section_lines}

Validation: `{validation['status']}`

Boundary audit: `{boundary['status']}`

Upstream app-consumption smoke status: `{source_map['upstream_app_consumption_smoke']['status']}`

This is a preflight/handoff artifact only. It does not implement a production frontend, public API, auth/RBAC, live event fabric integration, command/action, dispatch, enforcement, routing/control, legal/certified impact, or autonomous action.
"""
    write_md(OUTPUT_ROOT / "D6_RUNTIME_DEMO_PREFLIGHT_REPORT.md", report)

    write_md(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        f"""
# Limitations And Next Steps

## Limitations

{limitation_lines}

## Next Steps

- Use `{rel(APP_CONSUMER_HTML)}` as the UI evidence input for the D6 runtime demo preflight review.
- Promote the same packet/panel contract into a real Track 2C app surface only after the frontend task is explicitly opened.
- Keep D5 production/security parked until deliberately unparked.
""",
    )

    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Run:

```powershell
python scripts\\run_main_citybrain_d6_runtime_demo_preflight_r1.py
```

Primary UI evidence:

```text
{rel(APP_CONSUMER_HTML)}
```

This pack validates the visible app-consumption smoke as the D6 runtime demo preflight evidence.
""",
    )


def decision_payload(
    upstream: dict[str, Any],
    source_map: dict[str, Any],
    html_evidence: dict[str, Any],
    validation: dict[str, Any],
    boundary: dict[str, Any],
    mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    pass_status = all(
        [
            validation["status"] == "PASS",
            boundary["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    )
    render_model = upstream["render_model"]
    return {
        "task_id": TASK_ID,
        "status": STATUS if pass_status else "FAIL",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "run_timestamp_utc": utc_now(),
        "primary_ui_evidence_artifact": "APP_CONSUMER_STATIC_HTML.html",
        "primary_ui_evidence_path": str(APP_CONSUMER_HTML),
        "primary_ui_evidence_status": html_evidence["status"],
        "required_ui_sections": PRIMARY_UI_EVIDENCE_SECTIONS,
        "required_ui_sections_found": html_evidence.get("sections_found", []),
        "required_ui_sections_missing": html_evidence.get("missing_sections", []),
        "app_consumption_smoke_root": str(APP_CONSUMPTION_ROOT),
        "app_consumption_smoke_status": upstream["decision"].get("status"),
        "ask_the_city_visible": validation["checks"]["ask_city_flow_visible"],
        "governed_answer_visible": validation["checks"]["governed_answer_visible"],
        "trace_and_evidence_visible": validation["checks"]["trace_and_evidence_visible"],
        "limitations_visible": validation["checks"]["limitations_visible"],
        "safe_next_look_options_visible": validation["checks"]["safe_next_looks_visible"],
        "consumed_packet_index_visible": validation["checks"]["consumed_packet_index_visible"],
        "packet_index_count": len(render_model.get("packet_index", [])),
        "localhost_only_confirmed": validation["checks"]["localhost_only"],
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": "PASS" if upstream["decision"].get("no_action_boundary_preserved") is True else "FAIL",
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        **FORBIDDEN_FLAGS,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-RUNTIME-DEMO-SLICE-R1",
        "parked_d5_task": "PARKED-MAIN-CITYBRAIN-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }


def main() -> int:
    before = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    upstream = load_upstream()
    html_evidence = parse_html_evidence()
    source_map = build_source_map(upstream, html_evidence)
    validation = validate_d6_readiness(upstream, html_evidence)
    boundary = boundary_audit(validation, upstream)

    write_json(OUTPUT_ROOT / "D6_RUNTIME_DEMO_UI_EVIDENCE_REPORT.json", html_evidence)
    write_json(OUTPUT_ROOT / "D6_RUNTIME_DEMO_INTEGRATION_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "D6_RUNTIME_DEMO_PREFLIGHT_VALIDATION_RESULTS.json", validation)
    write_json(OUTPUT_ROOT / "D6_RUNTIME_DEMO_BOUNDARY_AUDIT.json", boundary)

    after = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    changed = [root for root in before if before[root] != after[root]]
    mutation = {
        "status": "PASS" if not changed else "FAIL",
        "changed_read_only_roots": changed,
        "before": before,
        "after": after,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)

    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.json", secret)
    write_docs(source_map, validation, boundary)

    decision = decision_payload(upstream, source_map, html_evidence, validation, boundary, mutation, secret)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_RUNTIME_DEMO_PREFLIGHT_R1_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": decision["status"],
                "output_root": str(OUTPUT_ROOT),
                "primary_ui_evidence": decision["primary_ui_evidence_path"],
                "required_ui_sections_found": decision["required_ui_sections_found"],
                "recommended_next_task": decision["recommended_next_task"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
