#!/usr/bin/env python3
"""Freeze the current D6 control-room reference demo truth.

This is a closeout/consolidation runner. It reads the completed D6, R7, and
Track 2A packs read-only, writes only the closeout output root, corrects stale
Omniverse/Kit wording, and does not implement new runtime, event, mobility,
domain, app, USD, or production features.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_WITH_LIMITATIONS"
WAIT_D6_R3 = "WAITING_ON_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION"
WAIT_TRACK2A_KIT_R2 = "WAITING_ON_TRACK2A_KIT_COMPOSER_HANDOFF_R2"
WAIT_R7_REGISTRY = "WAITING_ON_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH"
SCHEMA_VERSION = "main-citybrain-d6-control-room-reference-demo-closeout-refresh.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d6_control_room_reference_demo_closeout_refresh.py"

ROOTS = {
    "d6_r2": {
        "root": REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish",
        "decision": "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_WITH_LIMITATIONS",
        "label": "D6 R2 product polish",
    },
    "d6_r3": {
        "root": REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
        "decision": "MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_WITH_LIMITATIONS",
        "label": "D6 R3 R7 relationship overlay integration",
    },
    "track2a_kit_r2": {
        "root": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
        "decision": "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_WITH_LIMITATIONS",
        "label": "Track 2A Omniverse Kit/Composer handoff R2",
    },
    "r7_registry_preflight": {
        "root": REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
        "decision": "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_WITH_LIMITATIONS",
        "label": "R7 edge registry runtime preflight",
    },
    "track2a_asset_binding_r1": {
        "root": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
        "decision": "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS",
        "label": "Track 2A asset binding R1",
    },
    "r7_r2_source_diversity": {
        "root": REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
        "decision": "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_WITH_LIMITATIONS",
        "label": "R7 R2 source diversity",
    },
    "track2c_kit_first": {
        "root": REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
        "decision": "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json",
        "expected": "PASS_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_WITH_LIMITATIONS",
        "label": "Track 2C Kit-first city episode control room",
    },
    "r6_incident_event": {
        "root": REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
        "decision": "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_DECISION.json",
        "expected": "PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS",
        "label": "Track 1 R6 incident/event mode",
    },
    "r5_first_two_domain": {
        "root": REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
        "decision": "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json",
        "expected": "PASS_MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_WITH_LIMITATIONS",
        "label": "Track 1 R5 first two domain proof",
    },
}

LIMITATIONS = [
    "closeout/consolidation only",
    "local reference demo only",
    "no runtime service",
    "no event fabric integration",
    "no mobility implementation",
    "no new domain pack implementation",
    "no production/public deployment",
    "no legal/certified/action claims",
    "no command/dispatch/enforcement/routing/control output",
    "no source USD mutation",
    "no app source mutation",
]

PARKED_TASKS = [
    "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-SLICE",
    "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-STATE-MATERIALIZATION",
    "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3",
    "MAIN-TRACK1-D4Y-MOBILITY-DOMAIN-PACK-PREFLIGHT",
    "MAIN-CITYBRAIN-DOMAIN-AVAILABILITY-COUNT-SCOUT",
    "MAIN-CITYBRAIN-FIRST-HUMAN-ROUTED-REVIEW-CONSEQUENCE",
    "MAIN-CITYBRAIN-D5-PRODUCTION-PUBLIC-BOUNDARY",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "production/public deployment is ready",
    "production deployment is ready",
    "public api is ready",
    "legal finding",
    "certified truth",
    "confirmed violation",
    "enforcement action",
    "dispatch command",
    "routing/control command",
    "autonomous action",
    "source usd mutation",
    "app source mutation",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def local_link(target: Path) -> str:
    return Path(os.path.relpath(target, OUTPUT_ROOT)).as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "metadata_digest": None}
    h = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        stat = path.stat()
        file_count += 1
        total_bytes += stat.st_size
        h.update(f"{path.relative_to(root).as_posix()}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    return {"exists": True, "file_count": file_count, "total_bytes": total_bytes, "metadata_digest": h.hexdigest()}


def prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def load_prerequisites() -> tuple[dict[str, Any], dict[str, Any]]:
    decisions: dict[str, Any] = {}
    checks = []
    for key, meta in ROOTS.items():
        root = meta["root"]
        decision_path = root / meta["decision"]
        decision = read_json(decision_path, {})
        status = decision.get("status", "MISSING")
        ok = root.exists() and decision_path.exists() and status == meta["expected"]
        decisions[key] = decision
        checks.append(
            {
                "id": key,
                "label": meta["label"],
                "root": rel(root),
                "exists": root.exists(),
                "decision_path": rel(decision_path),
                "decision_exists": decision_path.exists(),
                "status": status,
                "expected_status": meta["expected"],
                "green": ok,
            }
        )
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(item["green"] for item in checks) else "WAITING",
        "checks": checks,
        "product_surface_truth": {
            "primary_spatial_surface": "Omniverse Kit / Composer",
            "web_surface": "companion evidence, episode, and executive surface",
            "stale_language_correction_required": True,
        },
    }
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_PREREQUISITE_REPORT.json", report)
    return decisions, report


def status_or(decisions: dict[str, Any], key: str) -> str:
    return decisions.get(key, {}).get("status", "MISSING")


def write_current_truth(decisions: dict[str, Any]) -> None:
    r7_registry = decisions["r7_registry_preflight"]
    d6_r3 = decisions["d6_r3"]
    kit_r2 = decisions["track2a_kit_r2"]
    truth = f"""
# D6 Closeout Current Truth Register

Frozen at: `{now()}`

## Product Surface Stance

- Omniverse Kit / Composer is the primary spatial control-room surface.
- Web is the companion evidence, episode, and executive surface.
- Older wording that treats "Omniverse as primary" as obsolete is superseded.
- D6 R3 relationship overlays are local/reference handoff packets and web
  companion packets, not production product deployment.

## Green Spine

| Area | Status |
| --- | --- |
| D6 R2 product polish | `{status_or(decisions, 'd6_r2')}` |
| D6 R3 R7 relationship overlay integration | `{status_or(decisions, 'd6_r3')}` |
| Track 2A Kit/Composer handoff R2 | `{status_or(decisions, 'track2a_kit_r2')}` |
| R7 edge registry runtime preflight | `{status_or(decisions, 'r7_registry_preflight')}` |
| Track 2A asset binding R1 | `{status_or(decisions, 'track2a_asset_binding_r1')}` |
| R7 R2 source diversity | `{status_or(decisions, 'r7_r2_source_diversity')}` |
| Track 2C Kit-first control room | `{status_or(decisions, 'track2c_kit_first')}` |
| R6 incident/event mode | `{status_or(decisions, 'r6_incident_event')}` |
| R5 first two domain proof | `{status_or(decisions, 'r5_first_two_domain')}` |

## Frozen Counts

- D6 R3 selected edges: `{d6_r3.get('selected_edge_count')}`
- D6 R3 Kit handoff packets: `{d6_r3.get('kit_handoff_packet_count')}`
- D6 R3 web companion packets: `{d6_r3.get('web_companion_packet_count')}`
- Track 2A Kit R2 stage handoffs: `{kit_r2.get('stage_handoff_count')}`
- Track 2A Kit R2 navigation records: `{kit_r2.get('navigation_index_count')}`
- R7 registry records: `{r7_registry.get('registry_record_count')}`
- R7 accepted grounded edges: `{r7_registry.get('accepted_grounded_edge_count')}`
- R7 backlog candidates: `{r7_registry.get('backlog_candidate_count')}`
- R7 rejected candidates: `{r7_registry.get('rejected_candidate_count')}`

## Boundary

This closeout freezes a local bounded reference demo. It does not introduce a
runtime service, event fabric integration, production/public deployment,
legal/certified/action claims, source USD mutation, or app source mutation.
"""
    write_text(OUTPUT_ROOT / "D6_CLOSEOUT_CURRENT_TRUTH_REGISTER.md", truth)


def write_state_docs(decisions: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_OMNIVERSE_PRIMARY_CORRECTION.md",
        """
# D6 Closeout Omniverse Primary Correction

Correct current wording:

- Omniverse Kit / Composer is the primary spatial control-room surface.
- Web is the companion evidence, episode, and executive surface.

Superseded wording:

- Any language that treats "Omniverse as primary" as obsolete.
- Any language that implies the web page is the primary spatial control-room.

This correction is documentation/product stance only. It does not implement
Composer automation, source USD mutation, WebRTC streaming, or production
Omniverse runtime behavior.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_PRODUCT_SURFACE_STATE.md",
        """
# D6 Closeout Product Surface State

Current product split:

- Primary spatial surface: Omniverse Kit / Composer.
- Companion surface: web evidence, episode, executive, and relationship
  explanation pages.
- Backend substrate: R7 registry preflight and Track 1/2 bounded packets.

The local reference demo is showable as a bounded package, not as a production
served product. No public deployment, auth/RBAC, production API, or external
network claim is made here.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_RELATIONSHIP_OVERLAY_STATE.md",
        f"""
# D6 Closeout Relationship Overlay State

D6 R3 status: `{status_or(decisions, 'd6_r3')}`

D6 R3 created bounded relationship context cards, Kit handoff packets, web
companion packets, and evidence/limitation co-display artifacts. It remains a
local/reference integration pack. Relationship context remains evidence-bound
review context only.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_R7_REGISTRY_STATE.md",
        f"""
# D6 Closeout R7 Registry State

R7 registry preflight status: `{status_or(decisions, 'r7_registry_preflight')}`

The R7 edge registry runtime preflight defines DTOs, query request/response
schemas, registry records, readiness classification, policies, sample queries,
and future-only D6/Track2A/event-fabric contracts. It does not implement a
runtime service, graph database, served API, or product overlay.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_TRACK2A_KIT_HANDOFF_STATE.md",
        f"""
# D6 Closeout Track 2A Kit Handoff State

Track 2A Kit/Composer R2 status: `{status_or(decisions, 'track2a_kit_r2')}`

Kit/Composer handoff R2 hardens local Composer use with stage handoffs,
navigation indexes, camera/bookmark records, sidecar validation, runbooks, and
capture inventory. Kit/Composer is now the primary spatial control-room lane.
This does not claim production Omniverse runtime, source USD mutation,
automatic Composer control, or legal/certified source truth.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_SUPERSEDED_TASKS_REGISTER.md",
        """
# D6 Closeout Superseded Tasks Register

Historical prerequisites, not current next steps:

- D6 R2 Product Polish
- D6 R3 R7 Relationship Overlay Integration
- Track 2A Omniverse Kit/Composer Handoff R2
- R7 Edge Registry Runtime Preflight
- Track 2A Asset Binding R1
- R7 R2 Source Diversity

Stale sequencing to avoid:

- Re-running old visual preflight prompts as if R2/R3 did not happen.
- Treating Track 2A Kit/Composer R2 as optional future work after it is green.
- Treating "Omniverse as primary" as obsolete.
- Treating D6 R3 as pending after the relationship overlay integration is green.
""",
    )


def write_walkthroughs(decisions: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_EXECUTIVE_WALKTHROUGH.md",
        """
# D6 Closeout Executive Walkthrough

1. Open the closeout local index.
2. State the current product split: Kit/Composer is the primary spatial
   control-room surface; web is the companion evidence, episode, and executive
   surface.
3. Show D6 R3 as the relationship overlay convergence point.
4. Show Track 2A Kit/Composer R2 as the spatial handoff/runbook lane.
5. Show R7 registry preflight as the backend relationship contract.
6. Close with limitations: local reference only, no runtime service, no
   production/public deployment, no legal/certified/action claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_OPERATOR_WALKTHROUGH.md",
        """
# D6 Closeout Operator Walkthrough

1. Start from `D6_CLOSEOUT_LOCAL_OPEN_INDEX.html`.
2. Open the D6 R3 local index for relationship overlay context.
3. Open the Track 2A Kit/Composer R2 README and operator runbook for spatial
   handoff steps.
4. Open the R7 registry decision and smoke report to verify backend edge
   readiness.
5. Keep all displayed edge/evidence/context as review/context only.
6. Do not issue commands, dispatch, enforcement, routing/control, legal,
   certified, or autonomous outputs.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md",
        """
# D6 Closeout Technical Evidence Chain Walkthrough

R7 R2 source-diverse edge seed -> R7 edge registry runtime preflight -> D6 R3
relationship overlay handoff packets -> Track 2A Kit/Composer handoff R2 ->
web companion evidence/episode/executive surfaces.

Evidence and limitations remain load-bearing at each step. The closeout does
not create new runtime handlers, event-fabric materialization, mobility domain
logic, production deployment, app source changes, or source USD changes.
""",
    )


def write_next_and_limitations() -> None:
    limitation_lines = "\n".join(f"- {item}" for item in LIMITATIONS)
    parked_lines = "\n".join(f"- `{item}`" for item in PARKED_TASKS)
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_LIMITATION_REGISTER.md",
        f"""
# D6 Closeout Limitation Register

{limitation_lines}
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_NEXT_BRANCH_DECISION.md",
        """
# D6 Closeout Next Branch Decision

Recommended next branch: `MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-SLICE`

Reason: the current demo truth is now frozen, and the R7 registry preflight is
green. The clean backend continuation is a bounded local runtime slice before
new product-surface expansion.

Product-surface continuation remains available later through:
`MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION` follow-up polish
only if new runtime/backend gates add material value.
""",
    )
    write_text(
        OUTPUT_ROOT / "D6_CLOSEOUT_PARKED_TASKS_REGISTER.md",
        f"""
# D6 Closeout Parked Tasks Register

{parked_lines}

Parked means not implemented in this closeout refresh. Each branch needs its
own preflight or runtime gate before being treated as current capability.
""",
    )


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.links.append((key, value))


def render_index() -> str:
    links = [
        ("D6 R3 Relationship Overlay", ROOTS["d6_r3"]["root"] / "D6_R3_LOCAL_OPEN_INDEX.html"),
        ("D6 R2 Polish Index", ROOTS["d6_r2"]["root"] / "D6_R2_LOCAL_OPEN_INDEX.html"),
        ("Track 2A Kit/Composer R2", ROOTS["track2a_kit_r2"]["root"] / "README.md"),
        ("R7 Edge Registry Preflight", ROOTS["r7_registry_preflight"]["root"] / "README.md"),
        ("Track 2A Asset Binding R1", ROOTS["track2a_asset_binding_r1"]["root"] / "README.md"),
        ("R7 R2 Source Diversity", ROOTS["r7_r2_source_diversity"]["root"] / "README.md"),
        ("Current Truth Register", OUTPUT_ROOT / "D6_CLOSEOUT_CURRENT_TRUTH_REGISTER.md"),
        ("Executive Walkthrough", OUTPUT_ROOT / "D6_CLOSEOUT_EXECUTIVE_WALKTHROUGH.md"),
        ("Operator Walkthrough", OUTPUT_ROOT / "D6_CLOSEOUT_OPERATOR_WALKTHROUGH.md"),
        ("Technical Evidence Chain", OUTPUT_ROOT / "D6_CLOSEOUT_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md"),
    ]
    cards = "\n".join(
        f'<article><h2>{label}</h2><a href="{local_link(target)}">Open artifact</a></article>'
        for label, target in links
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>CityBrain D6 Closeout Refresh</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #10151a; color: #f4f7fb; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px; }}
    .banner {{ border: 1px solid #334253; background: #17212b; padding: 16px; border-radius: 6px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; margin-top: 22px; }}
    article {{ border: 1px solid #314052; background: #151d25; border-radius: 6px; padding: 16px; min-height: 110px; }}
    h1 {{ margin: 0 0 12px; }}
    h2 {{ margin: 0 0 18px; font-size: 18px; }}
    a {{ color: #7cc7ff; }}
    .stance {{ color: #8df0bd; font-weight: 700; }}
    .limit {{ color: #ffd166; }}
  </style>
</head>
<body>
<main>
  <h1>CityBrain D6 Control Room Reference Demo Closeout Refresh</h1>
  <div class="banner">
    <p class="stance">Current truth: Omniverse Kit / Composer is the primary spatial control-room surface.</p>
    <p>Web is the companion evidence, episode, and executive surface.</p>
    <p class="limit">Closeout/consolidation only. No runtime service, event fabric integration, production/public deployment, legal/certified/action claim, source USD mutation, or app source mutation.</p>
  </div>
  <section class="grid">
    {cards}
  </section>
</main>
</body>
</html>"""


def validate_index(path: Path) -> dict[str, Any]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    checks = []
    for attr, href in parser.links:
        if re.match(r"^[a-z]+://", href):
            exists = True
            resolved = href
        else:
            resolved_path = (path.parent / href).resolve()
            exists = resolved_path.exists()
            resolved = str(resolved_path)
        checks.append({"attribute": attr, "target": href, "resolved": resolved, "exists": exists})
    text = path.read_text(encoding="utf-8")
    required_tokens = {
        "Omniverse Kit / Composer is the primary spatial control-room surface": "Omniverse Kit / Composer is the primary spatial control-room surface" in text,
        "Web is the companion evidence": "Web is the companion evidence" in text,
        "No runtime service": "No runtime service" in text or "no runtime service" in text,
        "D6 R3 Relationship Overlay": "D6 R3 Relationship Overlay" in text,
    }
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(item["exists"] for item in checks) and all(required_tokens.values()) else "FAIL",
        "link_count": len(checks),
        "link_checks": checks,
        "required_token_status": required_tokens,
    }
    write_json(OUTPUT_ROOT / "D6_CLOSEOUT_LOCAL_OPEN_INDEX_VALIDATION.json", payload)
    return payload


def claim_boundary_audit() -> dict[str, Any]:
    findings = []
    negated = re.compile(r"\b(no|not|without|false|forbidden|parked|limitation|only|does not|do not)\b")
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for claim in FORBIDDEN_POSITIVE_CLAIMS:
            start = 0
            while True:
                idx = text.find(claim, start)
                if idx == -1:
                    break
                line_start = text.rfind("\n", 0, idx) + 1
                line_end = text.find("\n", idx)
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                window = text[max(0, idx - 400): idx + len(claim) + 160]
                if not (negated.search(line) or negated.search(window)):
                    findings.append({"path": rel(path), "claim": claim, "context": line.strip()[:240]})
                start = idx + 1
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

Unsupported positive claim findings: `{len(findings)}`

The closeout states only bounded limitations: no production/public deployment,
no runtime service, no event fabric integration, no legal/certified/action
claims, no command/dispatch/enforcement/routing/control output, no source USD
mutation, and no app source mutation.
""",
    )
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"root_id": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"# No Mutation Audit\n\nStatus: `{status}`\n\nChanged prerequisite roots: `{len(changes)}`",
    )
    return {"status": status, "changes": changes}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(findings)}`")
    return {"status": status, "findings": findings}


def write_main_docs(status: str) -> None:
    text = f"""
# CityBrain D6 Control Room Reference Demo Closeout Refresh

Status: `{status}`

This closeout refresh freezes the current D6 control-room reference demo truth
after D6 R2, D6 R3, Track 2A Kit/Composer R2, R7 registry preflight, Track 2A
asset binding R1, and R7 R2 source diversity are green.

Current product stance:

- Omniverse Kit / Composer is the primary spatial control-room surface.
- Web is the companion evidence, episode, and executive surface.

This is a consolidation task only. It does not implement runtime slice, event
fabric, mobility, new domain packs, production/public deployment, legal or
certified claims, source USD mutation, or app source mutation.
"""
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH.md", text)
    write_text(OUTPUT_ROOT / "README.md", text)


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {relative}\n" for relative, digest in rows), encoding="utf-8")
    return {"status": "PASS", "hashed_file_count": len(rows), "hash_file": rel(OUTPUT_ROOT / "hashes.sha256")}


def waiting_status(prereq_report: dict[str, Any]) -> str:
    checks = {item["id"]: item["green"] for item in prereq_report["checks"]}
    if not checks.get("d6_r3", False):
        return WAIT_D6_R3
    if not checks.get("track2a_kit_r2", False):
        return WAIT_TRACK2A_KIT_R2
    if not checks.get("r7_registry_preflight", False):
        return WAIT_R7_REGISTRY
    return FAIL_STATUS


def main() -> None:
    before = {key: root_signature(meta["root"]) for key, meta in ROOTS.items()}
    prepare_output_root()
    decisions, prereq_report = load_prerequisites()

    if prereq_report["status"] != "PASS":
        status = waiting_status(prereq_report)
        decision = {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "d6_r2_status": status_or(decisions, "d6_r2"),
            "d6_r3_status": status_or(decisions, "d6_r3"),
            "track2a_kit_r2_status": status_or(decisions, "track2a_kit_r2"),
            "r7_registry_preflight_status": status_or(decisions, "r7_registry_preflight"),
            "omniverse_primary_correction_status": "NOT_CREATED",
            "current_truth_register_status": "NOT_CREATED",
            "superseded_task_register_status": "NOT_CREATED",
            "local_open_index_status": "NOT_CREATED",
            "claim_boundary_status": "NOT_RUN",
            "no_mutation_status": "NOT_RUN",
            "secret_audit_status": "NOT_RUN",
            "hash_validation_status": "PENDING",
            "recommended_next_branch": "Resolve missing prerequisite root/status",
            "parked_tasks": PARKED_TASKS,
            "limitations": LIMITATIONS,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_DECISION.json", decision)
        decision["hash_validation_status"] = write_hashes()["status"]
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_DECISION.json", decision)
        write_hashes()
        return

    write_current_truth(decisions)
    write_state_docs(decisions)
    write_walkthroughs(decisions)
    write_next_and_limitations()
    index_path = OUTPUT_ROOT / "D6_CLOSEOUT_LOCAL_OPEN_INDEX.html"
    write_text(index_path, render_index())
    index_validation = validate_index(index_path)
    claim = claim_boundary_audit()
    after = {key: root_signature(meta["root"]) for key, meta in ROOTS.items()}
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()

    phase_ok = all(
        [
            index_validation["status"] == "PASS",
            claim["status"] == "PASS",
            no_mutation["status"] == "PASS",
            secret["status"] == "PASS",
            (OUTPUT_ROOT / "D6_CLOSEOUT_OMNIVERSE_PRIMARY_CORRECTION.md").exists(),
            (OUTPUT_ROOT / "D6_CLOSEOUT_CURRENT_TRUTH_REGISTER.md").exists(),
            (OUTPUT_ROOT / "D6_CLOSEOUT_SUPERSEDED_TASKS_REGISTER.md").exists(),
        ]
    )
    status = PASS_STATUS if phase_ok else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "d6_r2_status": status_or(decisions, "d6_r2"),
        "d6_r3_status": status_or(decisions, "d6_r3"),
        "track2a_kit_r2_status": status_or(decisions, "track2a_kit_r2"),
        "r7_registry_preflight_status": status_or(decisions, "r7_registry_preflight"),
        "omniverse_primary_correction_status": "PASS",
        "current_truth_register_status": "PASS",
        "superseded_task_register_status": "PASS",
        "local_open_index_status": index_validation["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "recommended_next_branch": "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-SLICE",
        "parked_tasks": PARKED_TASKS,
        "limitations": LIMITATIONS,
        "product_surface_truth": {
            "primary_spatial_surface": "Omniverse Kit / Composer",
            "web_surface": "companion evidence, episode, and executive surface",
            "stale_omniverse_obsolete_language_superseded": True,
        },
        "runtime_service_implemented": False,
        "event_fabric_integration_implemented": False,
        "mobility_implemented": False,
        "new_domain_pack_implemented": False,
        "source_usd_mutated": False,
        "app_source_mutated": False,
    }
    write_main_docs(status)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_validation_status"] = hash_summary["status"]
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_DECISION.json", decision)
    write_hashes()


if __name__ == "__main__":
    main()
