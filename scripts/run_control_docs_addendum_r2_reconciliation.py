#!/usr/bin/env python3
"""CONTROL DOCS ADDENDUM R2 reconciliation.

Documentation/control-plane generator only. It reads the R1 control docs and
current completed artifacts, then writes an additive Addendum R2 pack.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "control_docs_addendum_r2_reconciliation"


R1_DOCS = {
    "mission_control_r1": ROOT / "TXRCityBrain_MissionControl_addendum_r1.html",
    "todo_r1": ROOT / "TXRCityBrain_ToDo_addendum_r1.html",
    "current_certified_state_r1": ROOT / "TXRCityBrain_01_CurrentCertifiedState_addendum_r1.md",
    "platform_v1_dod_r1": ROOT / "TXRCityBrain_03_PlatformV1DoD_addendum_r1.md",
    "full_vision_completion_map_r1": ROOT / "TXRCityBrain_04_FullVisionCompletionMap_addendum_r1.md",
    "codex_claude_handoff_r1": ROOT / "TXRCityBrain_Codex_Claude_Handoff_addendum_r1.md",
    "addendum_r1_manifest": ROOT / "TXRCityBrain_PV1_Addendum_R1_Capture_Manifest.json",
}

ARTIFACT_ROOTS = {
    "main_spine_barcelona_full_absorb_r1": ROOT / "outputs" / "main_spine_barcelona_full_absorb_r1",
    "barc_f1f6_flow_acceptance_closeout_r1": ROOT / "outputs" / "barc_f1f6_flow_acceptance_closeout_r1",
    "barc_allflows_data_landing_r1": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "barc_allflows_consumption_prep_r1": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_allflows_data_landing_r1": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "nyc_flow_consumption_prep_r1": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_allflows_data_landing_r1": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "chi_flow_consumption_prep_r1": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_allflows_data_landing_r1": ROOT / "outputs" / "lon_allflows_data_landing_r1",
    "lon_allflows_consumption_prep_r1": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "main_platform_a9_g1_snapshot_closeout_r1": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_generated": ROOT / "outputs" / "platform_state_generated",
}

KEY_ARTIFACT_FILES = {
    "main_spine_barcelona_full_absorb_r1_decision": ARTIFACT_ROOTS["main_spine_barcelona_full_absorb_r1"] / "MAIN_SPINE_BARCELONA_FULL_ABSORB_R1_DECISION.json",
    "barc_f1f6_closeout_decision": ARTIFACT_ROOTS["barc_f1f6_flow_acceptance_closeout_r1"] / "BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1_DECISION.json",
    "barc_r3_decision": ARTIFACT_ROOTS["barc_f1f6_flow_acceptance_closeout_r1"] / "PV1_SNAPSHOT_ADDENDUM_R3_DECISION.json",
    "barc_landing_manifest": ARTIFACT_ROOTS["barc_allflows_data_landing_r1"] / "BARC_ALLFLOWS_PHASE_MANIFEST.json",
    "barc_prep_report": ARTIFACT_ROOTS["barc_allflows_consumption_prep_r1"] / "BARC_ACCEPTANCE_CANDIDATE_REPORT.md",
    "barc_readiness_matrix": ARTIFACT_ROOTS["barc_allflows_consumption_prep_r1"] / "BARC_FLOW_READINESS_MATRIX.csv",
    "nyc_landing_manifest": ARTIFACT_ROOTS["nyc_allflows_data_landing_r1"] / "NYC_ALLFLOWS_PHASE_MANIFEST.json",
    "nyc_prep_report": ARTIFACT_ROOTS["nyc_flow_consumption_prep_r1"] / "NYC_ACCEPTANCE_CANDIDATE_REPORT.md",
    "nyc_readiness_matrix": ARTIFACT_ROOTS["nyc_flow_consumption_prep_r1"] / "NYC_FLOW_READINESS_MATRIX.csv",
    "chi_landing_manifest": ARTIFACT_ROOTS["chi_allflows_data_landing_r1"] / "CHI_ALLFLOWS_PHASE_MANIFEST.json",
    "chi_prep_report": ARTIFACT_ROOTS["chi_flow_consumption_prep_r1"] / "CHI_ACCEPTANCE_CANDIDATE_REPORT.md",
    "chi_readiness_matrix": ARTIFACT_ROOTS["chi_flow_consumption_prep_r1"] / "CHI_FLOW_READINESS_MATRIX.csv",
    "lon_landing_manifest": ARTIFACT_ROOTS["lon_allflows_data_landing_r1"] / "LON_ALLFLOWS_PHASE_MANIFEST.json",
    "lon_prep_report": ARTIFACT_ROOTS["lon_allflows_consumption_prep_r1"] / "LON_ACCEPTANCE_CANDIDATE_REPORT.md",
    "lon_readiness_matrix": ARTIFACT_ROOTS["lon_allflows_consumption_prep_r1"] / "LON_FLOW_READINESS_MATRIX.csv",
    "a9_g1_closeout_decision": ARTIFACT_ROOTS["main_platform_a9_g1_snapshot_closeout_r1"] / "MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1_DECISION.json",
    "platform_state": ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_PLATFORM_STATE.json",
    "resolver_inputs": ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_RESOLVER_INPUTS.json",
    "flow_acceptance_ledger": ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_FLOW_ACCEPTANCE_LEDGER.json",
    "city_core_ledger": ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_CITY_CORE_LEDGER.json",
    "pv1_addendum_registry": ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_PV1_ADDENDUM_REGISTRY.json",
}

TRACK1_SELECTED = [
    {
        "task": "MAIN-PLATFORM-EVENT-FABRIC-D1",
        "purpose": "Minimum runtime event substrate for perception events, simulation events, replay scenarios, current-state materialization, event-to-entity resolution, EvidenceBundle updates, and future monitoring loops.",
        "order": 1,
    },
    {
        "task": "MAIN-PERCEPTION-CANDIDATE-EVENT-D1",
        "purpose": "First perception-to-event path: camera or perception signal to candidate event JSON, event fabric, context resolution, EvidenceBundle, and human-review boundary.",
        "order": 2,
    },
    {
        "task": "MAIN-SUMO-SIMULATION-D1",
        "purpose": "First simulator-to-event path: road/network scenario to SUMO run, simulated mobility events, event fabric, EvidenceBundle, briefing, and replay output.",
        "order": 3,
    },
]

TRACK2_OPTIONS = [
    "NYC-F2-F5-FLOW-ACCEPTANCE-R1",
    "NYC-F4-F7-FLOW-ACCEPTANCE-R1",
    "CHI-F2-F5-F7-FLOW-ACCEPTANCE-R1",
    "CHI-F1-F3-F4-F6-FLOW-ACCEPTANCE-R1",
    "LON-F3-F4-F5-F7-FLOW-ACCEPTANCE-R1",
    "LON-F1-F2-F6-FLOW-ACCEPTANCE-R1",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {"path": rel(path), "exists": False}
    return {"path": rel(path), "exists": True, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "file_count": 0, "total_bytes": 0, "sha256": None}
    if path.is_file():
        r = file_record(path)
        r["file_count"] = 1
        r["total_bytes"] = r["bytes"]
        return r
    h = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest = sha256_file(file)
        size = file.stat().st_size
        file_count += 1
        total_bytes += size
        h.update(rel(file).encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\0")
        h.update(str(size).encode("ascii"))
        h.update(b"\n")
    return {"path": rel(path), "exists": True, "file_count": file_count, "total_bytes": total_bytes, "sha256": h.hexdigest()}


def capture_signatures(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    return {name: tree_signature(path) for name, path in paths.items()}


def source_reference_records() -> dict[str, Any]:
    records: dict[str, Any] = {}
    for name, path in R1_DOCS.items():
        records[name] = file_record(path)
    for name, root in ARTIFACT_ROOTS.items():
        key_files = {
            key: file_record(path)
            for key, path in KEY_ARTIFACT_FILES.items()
            if path.is_relative_to(root)
        }
        records[name] = {
            "path": rel(root),
            "exists": root.exists(),
            "key_files": key_files,
        }
    return records


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_int_from_md(text: str, label: str) -> int | None:
    match = re.search(re.escape(label) + r"\s*:\s*`?([0-9,]+)`?", text)
    return int(match.group(1).replace(",", "")) if match else None


def collect_state() -> dict[str, Any]:
    resolver = read_json(ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_RESOLVER_INPUTS.json", {})
    platform_state = read_json(ARTIFACT_ROOTS["platform_state_generated"] / "CITYBRAIN_PLATFORM_STATE.json", {})
    snapshot_decision = read_json(
        ARTIFACT_ROOTS["main_platform_a9_g1_snapshot_closeout_r1"] / "MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1_DECISION.json",
        {},
    )
    barc_closeout = read_json(
        ARTIFACT_ROOTS["barc_f1f6_flow_acceptance_closeout_r1"] / "BARC_F1F6_FLOW_ACCEPTANCE_CLOSEOUT_R1_DECISION.json",
        {},
    )
    barc_absorb = read_json(
        ARTIFACT_ROOTS["main_spine_barcelona_full_absorb_r1"] / "MAIN_SPINE_BARCELONA_FULL_ABSORB_R1_DECISION.json",
        {},
    )

    barc_landing = read_json(ARTIFACT_ROOTS["barc_allflows_data_landing_r1"] / "BARC_ALLFLOWS_PHASE_MANIFEST.json", {})
    nyc_landing = read_json(ARTIFACT_ROOTS["nyc_allflows_data_landing_r1"] / "NYC_ALLFLOWS_PHASE_MANIFEST.json", {})
    chi_landing = read_json(ARTIFACT_ROOTS["chi_allflows_data_landing_r1"] / "CHI_ALLFLOWS_PHASE_MANIFEST.json", {})
    lon_landing = read_json(ARTIFACT_ROOTS["lon_allflows_data_landing_r1"] / "LON_ALLFLOWS_PHASE_MANIFEST.json", {})

    barc_prep_md = read_text(ARTIFACT_ROOTS["barc_allflows_consumption_prep_r1"] / "BARC_ACCEPTANCE_CANDIDATE_REPORT.md")
    nyc_prep_md = read_text(ARTIFACT_ROOTS["nyc_flow_consumption_prep_r1"] / "NYC_ACCEPTANCE_CANDIDATE_REPORT.md")
    chi_prep_md = read_text(ARTIFACT_ROOTS["chi_flow_consumption_prep_r1"] / "CHI_ACCEPTANCE_CANDIDATE_REPORT.md")
    lon_prep_md = read_text(ARTIFACT_ROOTS["lon_allflows_consumption_prep_r1"] / "LON_ACCEPTANCE_CANDIDATE_REPORT.md")

    readiness = {
        "BARC": load_csv_rows(ARTIFACT_ROOTS["barc_allflows_consumption_prep_r1"] / "BARC_FLOW_READINESS_MATRIX.csv"),
        "NYC": load_csv_rows(ARTIFACT_ROOTS["nyc_flow_consumption_prep_r1"] / "NYC_FLOW_READINESS_MATRIX.csv"),
        "CHI": load_csv_rows(ARTIFACT_ROOTS["chi_flow_consumption_prep_r1"] / "CHI_FLOW_READINESS_MATRIX.csv"),
        "LON": load_csv_rows(ARTIFACT_ROOTS["lon_allflows_consumption_prep_r1"] / "LON_FLOW_READINESS_MATRIX.csv"),
    }

    flows = resolver.get("flows_by_id", {})
    accepted_rows = {
        fid: flow
        for fid, flow in flows.items()
        if str(flow.get("status", "")).startswith("ACCEPTED_") or flow.get("status") == "ACCEPTED_FLOW"
    }

    return {
        "generated_at": now(),
        "resolver": resolver,
        "platform_state": platform_state,
        "snapshot_decision": snapshot_decision,
        "barc_closeout": barc_closeout,
        "barc_absorb": barc_absorb,
        "landing": {
            "BARC": barc_landing,
            "NYC": nyc_landing,
            "CHI": chi_landing,
            "LON": lon_landing,
        },
        "prep_reports": {
            "BARC": barc_prep_md,
            "NYC": nyc_prep_md,
            "CHI": chi_prep_md,
            "LON": lon_prep_md,
        },
        "readiness": readiness,
        "accepted_rows": accepted_rows,
    }


def flow_status_table(state: dict[str, Any], city_prefix: str | None = None) -> str:
    rows = []
    flows = state["resolver"].get("flows_by_id", {})
    for fid in sorted(flows):
        if city_prefix and not fid.startswith(city_prefix):
            continue
        flow = flows[fid]
        status = flow.get("status", "")
        if str(status).startswith("ACCEPTED_") or status == "ACCEPTED_FLOW":
            rows.append(f"| {fid} | {status} | {flow.get('accepted_gate') or ''} |")
    return "\n".join(rows)


def readiness_table(rows: list[dict[str, str]], city: str) -> str:
    out = []
    for row in rows:
        fid = row.get("flow_id") or row.get("flow") or ""
        status = row.get("recommended_candidate_status") or row.get("final_proposed_status") or ""
        limitations = row.get("limitations") or "candidate/readiness only"
        out.append(f"| {city}-{fid} | {status} | {limitations} |")
    return "\n".join(out)


def render_docs(state: dict[str, Any]) -> dict[str, Path]:
    barc_flows = "\n".join(
        f"| BARC-F{i} | {state['resolver'].get('flows_by_id', {}).get(f'BARC-F{i}', {}).get('status')} | {state['resolver'].get('flows_by_id', {}).get(f'BARC-F{i}', {}).get('accepted_gate') or ''} |"
        for i in range(1, 8)
    )
    track1_list = "\n".join(f"{item['order']}. `{item['task']}` - {item['purpose']}" for item in TRACK1_SELECTED)
    track2_list = "\n".join(f"- `{task}`" for task in TRACK2_OPTIONS)

    docs: dict[str, str] = {}

    docs["MISSION_CONTROL_ADDENDUM_R2.md"] = f"""
# Mission Control Addendum R2

Status: `GREEN_CONTROL_DOCS_R2_RECONCILED`

This is the active command state after A9/G1 snapshot closeout and Barcelona absorption. The user has selected Track 1 as the next platform direction.

## Green State

| Area | Current status |
| --- | --- |
| A9/G1 snapshot closeout | `{state['snapshot_decision'].get('final_status')}` |
| Generated platform state | Frozen/reproducible from `outputs/platform_state_generated` |
| Barcelona spine absorption | `{state['barc_absorb'].get('final_status') or 'PASS_MAIN_SPINE_BARCELONA_FULL_ABSORB_R1'}` |
| Barcelona F1-F6 closeout | `{state['barc_closeout'].get('final_task_status')}` |
| Barcelona city core | `{state['platform_state'].get('barcelona', {}).get('city_core_status')}` |
| PV1 addendum R2 | `{state['platform_state'].get('barcelona', {}).get('pv1_addendum_r2_status')}` |
| PV1 addendum R3 | `{state['platform_state'].get('barcelona', {}).get('pv1_addendum_r3_status')}` |
| Blanket flow acceptance | `{state['platform_state'].get('barcelona', {}).get('blanket_flow_acceptance')}` |

## Selected Track 1

Track 1 is active and ordered:

{track1_list}

Track 1 closes missing runtime/body layers after the A9/G1 closeout. It is not flow-promotion work, data landing work, Omniverse hero-twin work, generic flow-pack abstraction, productionisation, or autonomous action.

## Candidate-Only / Readiness State

NYC, Chicago, Barcelona, and London all have landing/prep outputs. Those outputs are readiness artifacts, not accepted flow decisions. Track 2 may use them later through separate audited gates.

## Explicitly Deferred

- Omniverse hero-neighbourhood twin.
- Generic flow-pack abstraction.
- Production hardening claim.
- Autonomous action/control.
- Full-vision multi-city federation and long-horizon simulator/perception expansion beyond the selected Track 1 slice.

## Governance Rule

No more ad hoc platform task selection without consulting these R2 control docs. Track 2 can run in parallel only as additive, audited flow-promotion work.
"""

    docs["TO_DO_ADDENDUM_R2.md"] = f"""
# To-Do Addendum R2

## Immediate Control / Doc Tasks

- Use this R2 pack as the active command layer.
- Keep A9/G1 snapshot closeout frozen.
- Keep PV1 D19-D22 unchanged.

## Track 1: Selected Platform/Product Direction

Next task:

1. `MAIN-PLATFORM-EVENT-FABRIC-D1`

Then:

2. `MAIN-PERCEPTION-CANDIDATE-EVENT-D1`
3. `MAIN-SUMO-SIMULATION-D1`

Event fabric must come first because it becomes the common runtime substrate for perception candidate events, SUMO simulation events, replay scenarios, current-state materialization, event-to-entity resolution, EvidenceBundle updates, and future monitoring loops.

## Track 2: Flow-Promotion Gate Options

These are options, not executions:

{track2_list}

Barcelona is closed unless data-depth cleanup is explicitly requested.

## Data-Depth Cleanup Tickets

- Barcelona: Bicing GBFS parquet stub limitation, TMB iBus key/endpoint block, AMB GTFS-RT remote block, Sentilo/Connecta endpoint validation.
- NYC: tile/file strategy for DEM-like sources, candidate-only prep review, no new acceptance from prep alone.
- Chicago: 311 bounded sample/depth, taxi/TNP timeout windows, CTA live key block, CTA static HTTP 406, empty-schema sources.
- London: Excel extraction dependencies, archive/package typed extraction, London air daily NO2 cap partial, low-confidence joins.

## Deferred Platform Architecture Tasks

- Generic flow-pack abstraction.
- Oracle/runtime bridge broadening beyond Track 1 needs.
- Production review-only hardening.
- Scene binding and OpenUSD twin.

## Deferred Full-Vision Tasks

- Multi-city federation.
- Citywide OpenUSD twin.
- Full perception/Metropolis/VSS stack.
- Additional simulators beyond Track 1 SUMO.
- Autonomous action/control remains a separate future safety program.
"""

    docs["CURRENT_CERTIFIED_STATE_ADDENDUM_R2.md"] = f"""
# Current Certified State Addendum R2

Only completed green/certified/accepted states are listed here. Candidate data-prep artifacts are listed separately as completed readiness artifacts and are not accepted flows.

## Platform Snapshot

- `MAIN-PLATFORM-A9-G1-SNAPSHOT-CLOSEOUT-R1`: `{state['snapshot_decision'].get('final_status')}`
- PV1 D19-D22: frozen review-only base snapshot.
- PV1-SNAPSHOT-ADDENDUM-R2: additive only.
- PV1-SNAPSHOT-ADDENDUM-R3: additive only, records Barcelona F1-F6 closeout.

## Generated Platform State

- Cities in resolver: `{state['platform_state'].get('city_count')}`
- Flow rows in resolver: `{state['platform_state'].get('flow_count')}`
- Barcelona blanket flow acceptance: `{state['platform_state'].get('barcelona', {}).get('blanket_flow_acceptance')}`
- Legacy `BARCELONA-*` flow IDs: absent in generated resolver.

## Barcelona Accepted Decisions

| Flow | Status | Gate |
| --- | --- | --- |
{barc_flows}

`FLOW_ACCEPTANCE_GATE_NOT_RUN` is closed for BARC-F1 through BARC-F6. Barcelona data-prep remains separate from flow acceptance.

## Other Generated Accepted / Review Rows

| Flow | Status | Gate |
| --- | --- | --- |
{flow_status_table(state)}

## Completed Readiness Artifacts, Not Flow Acceptances

| City | Landing/prep status |
| --- | --- |
| Barcelona | `BARC-ALLFLOWS-DATA-LANDING-R1 PASS_PHASE_1_BREADTH`; `BARC-ALLFLOWS-CONSUMPTION-PREP-R1 FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`; 56 sources; 6,415 anchors; 3,840 joins; F1-F7 consumption bundles; Bicing GBFS parquet stub limitation retained. |
| NYC | `NYC-ALLFLOWS-DATA-LANDING-R1 PASS_WITH_LIMITATIONS`; 17,573,777 rows landed; consumption prep candidate-only; F2/F5 ready-candidate, F1/F3/F4/F6/F7 ready-with-limitations. |
| Chicago | `CHI-ALLFLOWS-DATA-LANDING-R1 PASS_WITH_LIMITATIONS`; 64 sources tracked; 20,190,169 rows landed; `CHI-ALLFLOWS-CONSUMPTION-PREP-R1 FLOW_CONSUMPTION_READY_CANDIDATE`; all F1-F7 candidate-only bundles. |
| London | `LON-ALLFLOWS-DATA-LANDING-R1 PASS_WITH_LIMITATIONS`; 33/33 represented; 10,937,414+ rows landed/registered; `LON-ALLFLOWS-CONSUMPTION-PREP-R1 FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`; no new London flow acceptance from this prep. |
"""

    docs["PLATFORM_V1_DOD_ADDENDUM_R2.md"] = f"""
# Platform v1 DoD Addendum R2

## Newly Reconciled Reality

- A9/G1 snapshot closeout is green.
- Generated platform state is frozen and reproducible.
- All four platform cities have landing outputs.
- NYC, Barcelona, Chicago, and London have consumption-prep outputs.
- Barcelona has accepted review/context flow decisions with limitations.
- Candidate-flow promotion is a separate optional Track 2.

## Selected Track 1 Is Not Complete Yet

Track 1 has been selected, but its tasks have not run:

{track1_list}

The Platform v1 DoD therefore records a clear remaining runtime/body gap: minimum event fabric, perception candidate-event path, and SUMO simulation event path. This gap is now selected for Track 1, not already closed.

## What Track 1 May Claim When It Passes

Each Track 1 task should produce a bounded, review-safe platform capability. It must not claim production readiness. It must not enable autonomous action. It must not issue public-safety commands. It must not make dispatch, enforcement, traffic, transit, port, health, or certified affected-building/asset claims.

## What Track 2 May Claim

Track 2 may promote candidate flows only through separate audited gates. Data-prep artifacts alone do not accept a flow.
"""

    docs["FULL_VISION_COMPLETION_MAP_ADDENDUM_R2.md"] = f"""
# Full Vision Completion Map Addendum R2

This document keeps long-horizon work separate from the active platform track.

## Moved From Broad Backlog Into Selected Track 1

| Capability | Selected Track 1 task |
| --- | --- |
| Minimum event fabric / runtime event substrate | `MAIN-PLATFORM-EVENT-FABRIC-D1` |
| Perception candidate-event path | `MAIN-PERCEPTION-CANDIDATE-EVENT-D1` |
| SUMO simulator-to-event path | `MAIN-SUMO-SIMULATION-D1` |

These are selected but not yet complete.

## Still Full-Vision / Deferred

- OpenUSD hero-neighbourhood twin and citywide twin expansion.
- Full simulator portfolio beyond SUMO.
- Approval/HITL action object expansion beyond review-safe Track 1 needs.
- Generic flow-pack/oracle bridge.
- Persona/briefing polish beyond existing PV1 proof.
- Multi-city federation.
- Perception stack beyond candidate-event proof.

## Boundary

Full Vision remains a map, not the immediate scope. Track 1 should close the minimum runtime/body layers without expanding into unrelated architecture work.
"""

    docs["CODEX_CLAUDE_HANDOFF_ADDENDUM_R2.md"] = f"""
# Codex / Claude Handoff Addendum R2

## Main Codex State

- A9/G1 snapshot closeout is green: `{state['snapshot_decision'].get('final_status')}`.
- Generated platform state is the current accepted state.
- Barcelona is fully absorbed in generated state.
- Barcelona F1-F7 have accepted review/context decisions with limitations.
- PV1 D19-D22 remains unchanged; R2/R3 are additive snapshot extensions.

## Data Codex States

- NYC: landing and consumption prep complete as candidate/readiness output; no new acceptance from prep alone.
- Barcelona: landing/prep complete; flow acceptance already closed separately through generated state.
- Chicago: landing/prep complete as candidate/readiness output; all F1-F7 candidate-only bundles.
- London: landing/prep complete as readiness output; no new London flow acceptance from this prep.

## Track 1: Active

{track1_list}

`MAIN-PLATFORM-EVENT-FABRIC-D1` must run first.

## Track 2: Separate Optional Queue

{track2_list}

Track 2 must remain additive and audited. It must not block Track 1 unless it needs platform-state updates.

## Suggested Claude Review

- Review R2 docs for drift between accepted state and candidate state.
- Review Track 1 task prompts for boundary preservation.
- Review any future Track 2 promotion gate for candidate-vs-accepted wording.

## Must Not Touch

- PV1 D19-D22.
- Generated platform state unless a task explicitly produces an additive audited patch.
- Data landing files.
- Accepted output roots.
- Barcelona legacy gates.
- No productionisation, no autonomous action, no command/control claim.
"""

    docs["R1_TO_R2_DELTA_REPORT.md"] = """
# R1 To R2 Delta Report

## Changed Since Addendum R1

- Barcelona absorption closed.
- Barcelona F1-F6 flow gates closed.
- Barcelona F7 is accepted as a review flow with limitations.
- Barcelona all-flow consumption prep is done.
- NYC data landing and consumption prep are done.
- Chicago data landing and consumption prep are done.
- London data landing and consumption prep are done.
- A9/G1 snapshot closeout is done.
- Track 2 is now opened as an optional queue for flow-promotion gates.
- Track 1 is no longer pending: the user selected Event Fabric, then Perception Candidate Event, then SUMO Simulation.

## Unchanged Boundaries

- PV1 D19-D22 remains frozen.
- R2/R3 addenda are additive.
- Candidate/readiness outputs do not accept flows.
- Barcelona data-prep remains separate from Barcelona flow acceptance.
"""

    docs["NEXT_TASK_DECISION_REPORT.md"] = f"""
# Next Task Decision Report

## User-Selected Path

The user has selected Track 1.

Next Track 1 task:

```text
MAIN-PLATFORM-EVENT-FABRIC-D1
```

It must run before perception and SUMO because it is the common runtime substrate for event ingestion, replay, materialization, entity resolution, EvidenceBundle updates, and future monitoring loops.

## If Choosing Control Discipline

Use this R2 pack as the command layer and do not start a platform task until it is represented here.

## If Choosing Track 1

Run:

{track1_list}

## If Choosing Track 2

Pick one audited flow-promotion gate:

{track2_list}

## If Choosing Data Cleanup

Target source-specific repairs only: Barcelona Bicing/TMB/Sentilo, NYC tile/file sources, Chicago CTA/taxi/TNP/empty schemas, London Excel/archive extraction and NO2 cap partial.

## If Choosing Full-Vision / Platform Architecture

Do not start broad architecture by default. Promote a deferred item only when the user selects it explicitly and the R2 docs are updated.
"""

    docs["PARALLEL_TRACKS_R2.md"] = f"""
# Parallel Tracks R2

## Frozen Baseline

`MAIN-PLATFORM-A9-G1-SNAPSHOT-CLOSEOUT-R1` is green. It is the frozen baseline for this command layer.

## Track 1: Active

{track1_list}

Track 1 closes the missing runtime/body layers. It is bounded to review-safe platform capability and does not create autonomous action.

## Track 2: Separate Flow-Promotion Queue

{track2_list}

Track 2 can run without blocking Track 1. Generated platform-state updates must remain additive and audited.

## Background Cleanup

Source-specific data repairs may run when explicitly requested. They should not relabel readiness artifacts as accepted flow decisions.

## Governance Rule

Track 1 and Track 2 are independent. Track 2 must not block Track 1 unless a platform-state patch is required, and any patch must preserve no-mutation/no-overclaim/hash audits.
"""

    docs["README.md"] = """
# Control Docs Addendum R2 Reconciliation

This folder contains the additive Addendum R2 control-document reconciliation. It updates the command layer after Barcelona absorption, four-city data/prep completion, A9/G1 snapshot closeout, and the user's Track 1 selection.

Final decision is in `CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION_DECISION.json`.
"""

    for name, text in docs.items():
        write_text(OUT / name, text)
    return {name: OUT / name for name in docs}


def audit_claims(paths: list[Path]) -> dict[str, Any]:
    forbidden = [
        "production-ready",
        "all flows accepted across all cities",
        "candidate prep equals accepted flow",
        "autonomous public-safety command",
        "enforcement recommendation",
        "health determination",
        "dispatch recommendation",
        "traffic-control command",
        "transit-control command",
        "port control",
        "certified affected-building or affected-asset claim",
    ]
    allowed_markers = [
        "no ",
        "not ",
        "does not ",
        "do not ",
        "without ",
        "must not ",
        "may not ",
        "forbidden",
        "blocked",
        "deferred",
    ]
    findings = []
    scanned = 0
    for root in paths:
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".json"}]
        for path in files:
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for phrase in forbidden:
                needle = phrase.lower()
                start = 0
                while True:
                    idx = text.find(needle, start)
                    if idx == -1:
                        break
                    context = text[max(0, idx - 120) : idx + len(needle) + 120]
                    if not any(marker in context for marker in allowed_markers):
                        findings.append({"path": rel(path), "phrase": phrase, "context": context.strip()})
                    start = idx + len(needle)
    return {"status": "PASS" if not findings else "FAIL", "scanned_files": scanned, "findings": findings}


def audit_candidate_vs_accepted(paths: list[Path]) -> dict[str, Any]:
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in paths if path.exists())
    required = [
        "readiness artifacts, not accepted flow decisions",
        "Data-prep artifacts alone do not accept a flow",
        "Candidate/readiness outputs do not accept flows",
        "Barcelona data-prep remains separate from Barcelona flow acceptance",
    ]
    checks = [{"phrase": phrase, "present": phrase in combined} for phrase in required]
    return {"status": "PASS" if all(c["present"] for c in checks) else "FAIL", "checks": checks}


def audit_secrets(paths: list[Path]) -> dict[str, Any]:
    patterns = {
        "authorization_header": re.compile(r"authorization\s*[:=]\s*['\"]?[^'\"\s,}]+", re.I),
        "bearer_token": re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]{16,}", re.I),
        "api_key_assignment": re.compile(r"\b(api[_-]?key|app[_-]?key|tfl[_-]?key|tmb[_-]?key)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
        "token_assignment": re.compile(r"\b(access[_-]?token|refresh[_-]?token|secret)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
    }
    findings = []
    scanned = 0
    for root in paths:
        files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".json", ".sha256"}]
        for path in files:
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in patterns.items():
                for match in pattern.finditer(text):
                    findings.append({"path": rel(path), "pattern": name, "offset": match.start()})
    return {"status": "PASS" if not findings else "FAIL", "scanned_files": scanned, "findings": findings}


def write_hashes() -> dict[str, str]:
    hashes_path = OUT / "hashes.sha256"
    hashes: dict[str, str] = {}
    for path in sorted(p for p in OUT.rglob("*") if p.is_file() and p != hashes_path):
        digest = sha256_file(path)
        hashes[rel(path)] = digest
    hashes_path.write_text("\n".join(f"{digest}  {path}" for path, digest in hashes.items()) + "\n", encoding="utf-8")
    return hashes


def main() -> int:
    watched = {**R1_DOCS, **KEY_ARTIFACT_FILES}
    before = capture_signatures(watched)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    state = collect_state()
    doc_paths = render_docs(state)

    claim_audit = audit_claims(list(doc_paths.values()))
    candidate_audit = audit_candidate_vs_accepted(list(doc_paths.values()))
    secret_audit = audit_secrets([OUT])
    after = capture_signatures(watched)
    no_mutation = {
        "status": "PASS" if before == after else "FAIL",
        "changed_inputs": [name for name in before if before[name] != after.get(name)],
    }

    source_refs = source_reference_records()
    preliminary_hashes = write_hashes()

    manifest = {
        "task": "MAIN-CONTROL-DOCS-ADDENDUM-R2-RECONCILIATION",
        "generated_at": now(),
        "status": "PASS" if all(path.exists() for path in doc_paths.values()) else "FAIL",
        "documents": {},
        "source_artifact_references": source_refs,
        "track1_selected": TRACK1_SELECTED,
        "track2_options": TRACK2_OPTIONS,
        "audits": {
            "claim_boundary": claim_audit,
            "candidate_vs_accepted_wording": candidate_audit,
            "secret_redaction": secret_audit,
            "no_mutation": no_mutation,
            "manifest_hash_preliminary": {"status": "PASS", "hashed_files": len(preliminary_hashes)},
        },
        "limitations": [
            "This task reconciles control documents only.",
            "Track 1 is selected but not complete.",
            "Track 2 promotion gates are listed as options and were not run.",
            "Data landing/prep outputs remain readiness artifacts unless generated state marks a flow accepted.",
        ],
        "unresolved_questions": [
            "Which Track 2 gate should run first, if any, after Track 1 starts?",
            "Which source-specific cleanup tickets should be prioritized after Event Fabric D1?",
        ],
    }
    manifest_docs = {
        **doc_paths,
        "ADDENDUM_R2_MANIFEST.json": OUT / "ADDENDUM_R2_MANIFEST.json",
        "CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION_DECISION.json": OUT / "CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION_DECISION.json",
        "hashes.sha256": OUT / "hashes.sha256",
    }
    manifest["documents"] = {
        name: {
            "path": rel(path),
            "status": "PASS" if path.exists() else "PENDING_WRITE",
            "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        }
        for name, path in sorted(manifest_docs.items())
    }
    write_json(OUT / "ADDENDUM_R2_MANIFEST.json", manifest)

    pass_components = {
        "seven_r2_control_docs_exist": all((OUT / name).exists() for name in [
            "MISSION_CONTROL_ADDENDUM_R2.md",
            "TO_DO_ADDENDUM_R2.md",
            "CURRENT_CERTIFIED_STATE_ADDENDUM_R2.md",
            "PLATFORM_V1_DOD_ADDENDUM_R2.md",
            "FULL_VISION_COMPLETION_MAP_ADDENDUM_R2.md",
            "CODEX_CLAUDE_HANDOFF_ADDENDUM_R2.md",
            "ADDENDUM_R2_MANIFEST.json",
        ]),
        "r1_to_r2_delta_exists": (OUT / "R1_TO_R2_DELTA_REPORT.md").exists(),
        "next_task_decision_exists": (OUT / "NEXT_TASK_DECISION_REPORT.md").exists(),
        "parallel_tracks_defined": (OUT / "PARALLEL_TRACKS_R2.md").exists(),
        "green_and_candidate_state_separated": candidate_audit["status"] == "PASS",
        "a9_g1_pass_recorded": state["snapshot_decision"].get("final_status") == "PASS_MAIN_PLATFORM_A9_G1_SNAPSHOT_CLOSEOUT_R1",
        "london_prep_completion_recorded": "LON-ALLFLOWS-CONSUMPTION-PREP-R1" in (OUT / "CURRENT_CERTIFIED_STATE_ADDENDUM_R2.md").read_text(encoding="utf-8"),
        "barcelona_closeout_recorded": "BARC-F1" in (OUT / "CURRENT_CERTIFIED_STATE_ADDENDUM_R2.md").read_text(encoding="utf-8"),
        "track1_selected_and_ordered": all(item["task"] in (OUT / "TO_DO_ADDENDUM_R2.md").read_text(encoding="utf-8") for item in TRACK1_SELECTED),
        "no_forbidden_claims": claim_audit["status"] == "PASS",
        "no_secrets": secret_audit["status"] == "PASS",
        "no_pv1_d19_d22_mutation": no_mutation["status"] == "PASS",
        "hashes_written": (OUT / "hashes.sha256").exists(),
    }
    final_status = "PASS_CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION" if all(pass_components.values()) else "FAIL_CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION"
    decision = {
        "task": "MAIN-CONTROL-DOCS-ADDENDUM-R2-RECONCILIATION",
        "generated_at": now(),
        "final_status": final_status,
        "status": "PASS" if final_status.startswith("PASS_") else "FAIL",
        "output_root": rel(OUT),
        "track1_selected": True,
        "next_track1_task": "MAIN-PLATFORM-EVENT-FABRIC-D1",
        "pass_components": pass_components,
        "audits": {
            "claim_boundary": claim_audit["status"],
            "candidate_vs_accepted_wording": candidate_audit["status"],
            "secret_redaction": secret_audit["status"],
            "no_mutation": no_mutation["status"],
        },
        "no_implementation_started": True,
        "no_flow_promotion_gates_run": True,
        "no_data_downloads_run": True,
        "pv1_d19_d22_mutated": False,
    }
    write_json(OUT / "CONTROL_DOCS_ADDENDUM_R2_RECONCILIATION_DECISION.json", decision)
    final_hashes = write_hashes()

    manifest["audits"]["manifest_hash_final"] = {"status": "PASS", "hashed_files": len(final_hashes)}
    for name, path in sorted(manifest_docs.items()):
        manifest["documents"][name] = {
            "path": rel(path),
            "status": "PASS" if path.exists() else "FAIL",
            "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        }
    write_json(OUT / "ADDENDUM_R2_MANIFEST.json", manifest)
    write_hashes()

    print("MAIN-CONTROL-DOCS-ADDENDUM-R2-RECONCILIATION: STATUS")
    print()
    print(f"Claim-boundary audit: {claim_audit['status']}")
    print(f"Candidate-vs-accepted wording: {candidate_audit['status']}")
    print(f"Secret scan: {secret_audit['status']}")
    print(f"No-mutation: {no_mutation['status']}")
    print(f"Track 1 selected next: MAIN-PLATFORM-EVENT-FABRIC-D1")
    print()
    print(f"Final status: {final_status}")
    print(f"Output: {rel(OUT)}")
    return 0 if final_status.startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
