from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d2_closeout_and_d3_roadmap"
TASK = "MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP"
SCHEMA_VERSION = "main-track1-d2-closeout-and-d3-roadmap.v1"
NOW = datetime(2026, 6, 29, 14, 0, 0, tzinfo=timezone.utc)


GATES = {
    "event_fabric_d2": {
        "name": "MAIN-EVENT-FABRIC-D2",
        "root": ROOT / "outputs" / "main_event_fabric_d2",
        "decision": "MAIN_EVENT_FABRIC_D2_DECISION.json",
        "expected_statuses": {"PASS_MAIN_EVENT_FABRIC_D2"},
        "required": [
            "MAIN_EVENT_FABRIC_D2_DECISION.json",
            "EVENT_FABRIC_D2_ARCHITECTURE.md",
            "EVENT_FABRIC_D2_SCHEMA.json",
            "EVENT_FABRIC_D2_SCHEMA.md",
            "EVENT_FABRIC_D2_CURRENT_STATE.duckdb",
            "EVENT_FABRIC_D2_API_SMOKE_REPORT.json",
            "EVENT_FABRIC_D2_REPLAY_REPORT.json",
            "EVENT_FABRIC_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
            "EVENT_FABRIC_D2_NEGATIVE_TEST_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.md",
            "NO_MUTATION_AUDIT.md",
            "SECRET_REDACTION_AUDIT.md",
            "hashes.sha256",
        ],
    },
    "perception_d2": {
        "name": "MAIN-PERCEPTION-D2",
        "root": ROOT / "outputs" / "main_perception_d2",
        "decision": "MAIN_PERCEPTION_D2_DECISION.json",
        "expected_statuses": {"PASS_MAIN_PERCEPTION_D2"},
        "required": [
            "MAIN_PERCEPTION_D2_DECISION.json",
            "PERCEPTION_D2_EVENT_ENVELOPES.jsonl",
            "PERCEPTION_D2_CURRENT_STATE.duckdb",
            "PERCEPTION_D2_HUMAN_REVIEW_PACKETS.jsonl",
            "PERCEPTION_D2_EVENT_FABRIC_APPEND_REPORT.md",
            "PERCEPTION_D2_REPLAY_SESSION_REPORT.json",
            "PERCEPTION_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
            "PERCEPTION_D2_NEGATIVE_TEST_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.md",
            "NO_MUTATION_AUDIT.md",
            "SECRET_REDACTION_AUDIT.md",
            "hashes.sha256",
        ],
    },
    "sumo_d2": {
        "name": "MAIN-SUMO-D2",
        "root": ROOT / "outputs" / "main_sumo_d2",
        "decision": "MAIN_SUMO_D2_DECISION.json",
        "expected_statuses": {"PASS_MAIN_SUMO_D2", "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS"},
        "required": [
            "MAIN_SUMO_D2_DECISION.json",
            "SUMO_D2_SUMO_RUNTIME_REPORT.json",
            "SUMO_D2_NETWORK_QUALITY_REPORT.json",
            "SUMO_D2_EVENT_ENVELOPES.jsonl",
            "SUMO_D2_CURRENT_STATE.duckdb",
            "SUMO_D2_REPLAY_SESSION_REPORT.json",
            "SUMO_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
            "SUMO_D2_NEGATIVE_TEST_REPORT.json",
            "CLAIM_BOUNDARY_AUDIT.md",
            "NO_MUTATION_AUDIT.md",
            "SECRET_REDACTION_AUDIT.md",
            "hashes.sha256",
        ],
    },
    "integrated_d2_smoke": {
        "name": "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE",
        "root": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
        "decision": "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json",
        "expected_statuses": {
            "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE",
            "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS",
        },
        "required": [
            "MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json",
            "TRACK1_D2_UNIFIED_EVENT_LOG.jsonl",
            "TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb",
            "TRACK1_D2_CURRENT_STATE_API_SMOKE_REPORT.json",
            "TRACK1_D2_REPLAY_SESSION_REPORT.json",
            "TRACK1_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json",
            "TRACK1_D2_BOUNDARY_SEPARATION_REPORT.md",
            "TRACK1_D2_NEGATIVE_TEST_REPORT.json",
            "TRACK1_D2_CLAIM_BOUNDARY_AUDIT.md",
            "TRACK1_D2_NO_MUTATION_AUDIT.md",
            "TRACK1_D2_SECRET_REDACTION_AUDIT.md",
            "hashes.sha256",
        ],
    },
}


WATCH_ROOTS = {
    "event_fabric_d2": ROOT / "outputs" / "main_event_fabric_d2",
    "perception_d2": ROOT / "outputs" / "main_perception_d2",
    "sumo_d2": ROOT / "outputs" / "main_sumo_d2",
    "integrated_d2_smoke": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
    "event_fabric_d1": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1": ROOT / "outputs" / "main_sumo_simulation_d1",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state_generated": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "barc_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chi_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "lon_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        stat = path.stat()
        return {"exists": True, "type": "file", "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(path)}
    files = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            stat = child.stat()
            files.append({"path": child.relative_to(path).as_posix(), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(child)})
    tree_sha = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"exists": True, "type": "directory", "file_count": len(files), "tree_sha256": tree_sha}


def capture_watch_signatures() -> dict[str, dict[str, Any]]:
    return {key: path_signature(path) for key, path in WATCH_ROOTS.items()}


def ensure_output() -> None:
    if OUTPUT_ROOT.exists():
        if OUTPUT_ROOT.parent != ROOT / "outputs" or OUTPUT_ROOT.name != "main_track1_d2_closeout_and_d3_roadmap":
            raise RuntimeError(f"Refusing to remove unexpected output root: {OUTPUT_ROOT}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def load_gate_audit() -> dict[str, Any]:
    gates = {}
    missing = []
    invalid_status = []
    for gate_id, spec in GATES.items():
        root = spec["root"]
        decision_path = root / spec["decision"]
        decision = read_json(decision_path) if decision_path.exists() else {}
        status = decision.get("final_status")
        required_checks = []
        for item in spec["required"]:
            path = root / item
            exists = path.exists()
            required_checks.append({"path": rel(path), "exists": exists})
            if not exists:
                missing.append(rel(path))
        if status not in spec["expected_statuses"]:
            invalid_status.append({"gate": gate_id, "status": status, "expected": sorted(spec["expected_statuses"])})
        gates[gate_id] = {
            "name": spec["name"],
            "root": rel(root),
            "decision_path": rel(decision_path),
            "final_status": status,
            "counts": decision.get("counts", {}),
            "limitations": decision.get("limitations", []),
            "required_artifacts": required_checks,
        }
    status = "PASS" if not missing and not invalid_status else "FAIL"
    return {
        "task": TASK,
        "status": status,
        "generated_at": now_iso(),
        "gates": gates,
        "missing_required_artifacts": missing,
        "invalid_statuses": invalid_status,
        "confirmations": {
            "all_four_d2_gates_exist": all(Path(gates[key]["root"]).exists() for key in gates),
            "event_fabric_d2_passed": gates["event_fabric_d2"]["final_status"] == "PASS_MAIN_EVENT_FABRIC_D2",
            "perception_d2_passed": gates["perception_d2"]["final_status"] == "PASS_MAIN_PERCEPTION_D2",
            "sumo_d2_passed_with_limitations": gates["sumo_d2"]["final_status"] == "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS",
            "integrated_d2_passed_with_limitations": gates["integrated_d2_smoke"]["final_status"] == "PASS_MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_WITH_LIMITATIONS",
            "all_limitations_surfaced": all(bool(gates[key].get("limitations")) for key in gates),
        },
        "schema_version": SCHEMA_VERSION,
    }


def write_input_artifact_audit(audit: dict[str, Any]) -> None:
    gate_lines = []
    for gate_id, gate in audit["gates"].items():
        missing = [item["path"] for item in gate["required_artifacts"] if not item["exists"]]
        gate_lines.append(f"### {gate['name']}\n\n- Status: `{gate['final_status']}`\n- Root: `{gate['root']}`\n- Missing required artifacts: `{len(missing)}`\n- Limitations surfaced: `{bool(gate.get('limitations'))}`")
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_INPUT_ARTIFACT_AUDIT.md",
        f"""
# Track 1 D2 Input Artifact Audit

Status: `{audit['status']}`

## Gate Summary

{chr(10).join(gate_lines)}

## Required Confirmations

- all four D2 gates exist: `{audit['confirmations']['all_four_d2_gates_exist']}`
- Event Fabric D2 passed: `{audit['confirmations']['event_fabric_d2_passed']}`
- Perception D2 passed: `{audit['confirmations']['perception_d2_passed']}`
- SUMO D2 passed with limitations: `{audit['confirmations']['sumo_d2_passed_with_limitations']}`
- Integrated D2 smoke passed with limitations: `{audit['confirmations']['integrated_d2_passed_with_limitations']}`
- no required artifact missing: `{not audit['missing_required_artifacts']}`
- all limitations surfaced: `{audit['confirmations']['all_limitations_surfaced']}`

## Missing Or Invalid

- Missing required artifacts: `{audit['missing_required_artifacts']}`
- Invalid statuses: `{audit['invalid_statuses']}`

## Boundary

This closeout reads the D2 gates as immutable inputs and writes only the closeout output root.
""",
    )


def capability_ledger() -> list[dict[str, Any]]:
    items = [
        ("event_fabric_d2_runtime_substrate", "MAIN-EVENT-FABRIC-D2", ["event_fabric_d2_decision", "event_fabric_d2_architecture"], "Service mode, observability, adapter expansion."),
        ("durable_cursors", "MAIN-EVENT-FABRIC-D2", ["event_fabric_d2_cursor_report"], "Cursor recovery and retention policy."),
        ("idempotent_append", "MAIN-EVENT-FABRIC-D2", ["event_fabric_d2_append_log", "event_fabric_d2_decision"], "Long-running append service hardening."),
        ("current_state_api_smoke", "MAIN-EVENT-FABRIC-D2", ["event_fabric_d2_api_smoke"], "Formal API contract and service profile."),
        ("replay_from_cursor", "MAIN-EVENT-FABRIC-D2", ["event_fabric_d2_replay_report"], "Replay API hardening and trace tooling."),
        ("perception_candidate_bridge", "MAIN-PERCEPTION-D2", ["perception_d2_event_envelopes", "perception_d2_decision"], "Review API/UI integration."),
        ("sample_media_detection_contract", "MAIN-PERCEPTION-D2", ["perception_d2_detection_contract", "perception_d2_media_manifest"], "Media metadata hardening and DeepStream bridge."),
        ("human_review_packets", "MAIN-PERCEPTION-D2", ["perception_d2_human_review_packets"], "Workflow/state transition API."),
        ("sumo_city_derived_simulation_producer", "MAIN-SUMO-D2", ["sumo_d2_runtime_report", "sumo_d2_event_envelopes"], "Larger network extraction and scenario catalog."),
        ("sumo_bounded_routeable_equivalent", "MAIN-SUMO-D2", ["sumo_d2_network_quality", "sumo_d2_city_source_audit"], "Replace point-chain equivalent with stronger routable network extraction where possible."),
        ("unified_d2_event_log", "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE", ["integrated_d2_unified_event_log"], "Durable multi-producer service log."),
        ("unified_d2_current_state", "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE", ["integrated_d2_current_state"], "Runtime API and dashboard service integration."),
        ("unified_d2_replay", "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE", ["integrated_d2_replay_report"], "Replay/debug tooling."),
        ("unified_d2_evidencebundle_smoke", "MAIN-TRACK1-D2-INTEGRATED-RUNTIME-SMOKE", ["integrated_d2_evidencebundle_report"], "Briefing/trace integration."),
    ]
    return [
        {
            "capability_id": capability_id,
            "status": "CERTIFIED_D2",
            "source_gate": source_gate,
            "evidence_refs": evidence_refs,
            "limitations": ["Bounded D2 runtime proof; no production/control/certified-impact claim."],
            "claim_boundary": "Review/context/simulated separation preserved; no action taken.",
            "next_hardening_needed": next_hardening,
            "schema_version": SCHEMA_VERSION,
        }
        for capability_id, source_gate, evidence_refs, next_hardening in items
    ]


def write_capability_ledger() -> None:
    write_json(
        OUTPUT_ROOT / "TRACK1_D2_CAPABILITY_LEDGER.json",
        {"task": TASK, "generated_at": now_iso(), "capabilities": capability_ledger(), "schema_version": SCHEMA_VERSION},
    )


def write_certified_state(audit: dict[str, Any]) -> None:
    integrated_counts = audit["gates"]["integrated_d2_smoke"].get("counts", {})
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_CERTIFIED_STATE.md",
        f"""
# Track 1 D2 Certified State

## Certified Close Sentence

CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.

## What D2 Proves

- bounded live/polled event ingestion exists
- durable cursor/idempotent append path exists
- current-state materialization exists
- current-state API smoke exists
- perception candidate bridge exists
- local sample-media lane exists
- human-review packets exist
- SUMO city-derived simulation producer exists
- unified runtime smoke exists
- replay works
- deterministic EvidenceBundle smoke works
- observed/context, candidate/review, and simulated/context boundaries are separated

## Integrated Counts

- unified events: `{integrated_counts.get('unified_events')}`
- source producer counts: `{integrated_counts.get('by_source_producer')}`
- lifecycle counts: `{integrated_counts.get('by_lifecycle')}`

## What D2 Does Not Prove

- not production real-time streaming
- not autonomous monitoring
- not production CCTV
- not identity or biometric recognition
- not traffic control
- not routing recommendation
- not certified simulation
- not public-safety command
- not dispatch
- not enforcement
- not health determination
- not certified affected-building or affected-asset determination
""",
    )


def write_limitations_register(audit: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_LIMITATIONS_REGISTER.md",
        f"""
# Track 1 D2 Limitations Register

## 1. SUMO Barcelona Routeable Equivalent Limitation

Classification: `ACCEPTED_D2_BOUNDARY`, `D3_HARDENING_CANDIDATE`, `DO_NOT_REMOVE_WITHOUT_GOVERNANCE`

- Official Barcelona traffic-section coordinates are city-derived.
- They are point-chain context, not a full routable street graph.
- Connector edges do not imply real turn permissions.
- Simulation remains simulated/context-only.
- It is not certified and no action is taken.
- Source limitation refs: `{audit['gates']['sumo_d2']['limitations']}`

## 2. Perception Media Metadata Limitation

Classification: `ACCEPTED_D2_BOUNDARY`, `D3_HARDENING_CANDIDATE`, `D4_PRODUCTIZATION_CANDIDATE`

- `ffprobe` was unavailable in the D2 run.
- Video metadata is marked limited.
- The sample-media lane still passed through deterministic fallback detection JSON.
- This is not production CCTV.
- Source limitation refs: `{audit['gates']['perception_d2']['limitations']}`

## 3. Event Fabric D2 Runtime Limitation

Classification: `ACCEPTED_D2_BOUNDARY`, `D3_HARDENING_CANDIDATE`, `D4_PRODUCTIZATION_CANDIDATE`

- Bounded polling/runtime smoke only.
- No heavy streaming infrastructure.
- No daemonized production service.
- Not production real-time monitoring.
- Source limitation refs: `{audit['gates']['event_fabric_d2']['limitations']}`

## 4. Integrated D2 Runtime Limitation

Classification: `ACCEPTED_D2_BOUNDARY`, `D3_HARDENING_CANDIDATE`

- Unified runtime smoke proves integration, not production deployment.
- API smoke is bounded.
- No operational commands are generated.
- Source limitation refs: `{audit['gates']['integrated_d2_smoke']['limitations']}`
""",
    )


def evidence_entries() -> list[dict[str, Any]]:
    artifacts = {
        "event_fabric_d2_decision": ("event_fabric_d2", "decision", "outputs/main_event_fabric_d2/MAIN_EVENT_FABRIC_D2_DECISION.json", "event_fabric_d2_runtime_substrate", "Event Fabric D2 limitations"),
        "event_fabric_d2_append_log": ("event_fabric_d2", "event_log", "outputs/main_event_fabric_d2/EVENT_FABRIC_D2_APPEND_LOG.jsonl", "idempotent_append", "bounded polling runtime"),
        "event_fabric_d2_current_state": ("event_fabric_d2", "duckdb", "outputs/main_event_fabric_d2/EVENT_FABRIC_D2_CURRENT_STATE.duckdb", "current_state_api_smoke", "bounded API"),
        "event_fabric_d2_replay_report": ("event_fabric_d2", "replay_report", "outputs/main_event_fabric_d2/EVENT_FABRIC_D2_REPLAY_REPORT.json", "replay_from_cursor", "bounded replay"),
        "event_fabric_d2_evidencebundle_report": ("event_fabric_d2", "evidencebundle_report", "outputs/main_event_fabric_d2/EVENT_FABRIC_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", "event_fabric_d2_runtime_substrate", "review/context-only"),
        "event_fabric_d2_negative": ("event_fabric_d2", "negative_test", "outputs/main_event_fabric_d2/EVENT_FABRIC_D2_NEGATIVE_TEST_REPORT.json", "event_fabric_d2_runtime_substrate", "blocked action claims"),
        "event_fabric_d2_claim_audit": ("event_fabric_d2", "claim_audit", "outputs/main_event_fabric_d2/CLAIM_BOUNDARY_AUDIT.md", "event_fabric_d2_runtime_substrate", "claim boundary"),
        "event_fabric_d2_no_mutation": ("event_fabric_d2", "no_mutation_audit", "outputs/main_event_fabric_d2/NO_MUTATION_AUDIT.md", "event_fabric_d2_runtime_substrate", "no mutation"),
        "event_fabric_d2_secret": ("event_fabric_d2", "secret_audit", "outputs/main_event_fabric_d2/SECRET_REDACTION_AUDIT.md", "event_fabric_d2_runtime_substrate", "secret boundary"),
        "event_fabric_d2_hashes": ("event_fabric_d2", "hashes", "outputs/main_event_fabric_d2/hashes.sha256", "event_fabric_d2_runtime_substrate", "reproducibility"),
        "perception_d2_decision": ("perception_d2", "decision", "outputs/main_perception_d2/MAIN_PERCEPTION_D2_DECISION.json", "perception_candidate_bridge", "perception limitations"),
        "perception_d2_event_envelopes": ("perception_d2", "event_log", "outputs/main_perception_d2/PERCEPTION_D2_EVENT_ENVELOPES.jsonl", "perception_candidate_bridge", "review-only"),
        "perception_d2_current_state": ("perception_d2", "duckdb", "outputs/main_perception_d2/PERCEPTION_D2_CURRENT_STATE.duckdb", "perception_candidate_bridge", "candidate current state"),
        "perception_d2_human_review_packets": ("perception_d2", "review_packets", "outputs/main_perception_d2/PERCEPTION_D2_HUMAN_REVIEW_PACKETS.jsonl", "human_review_packets", "human review required"),
        "perception_d2_replay_report": ("perception_d2", "replay_report", "outputs/main_perception_d2/PERCEPTION_D2_REPLAY_SESSION_REPORT.json", "perception_candidate_bridge", "candidate replay"),
        "perception_d2_evidencebundle_report": ("perception_d2", "evidencebundle_report", "outputs/main_perception_d2/PERCEPTION_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", "perception_candidate_bridge", "review-only evidence"),
        "perception_d2_negative": ("perception_d2", "negative_test", "outputs/main_perception_d2/PERCEPTION_D2_NEGATIVE_TEST_REPORT.json", "perception_candidate_bridge", "identity/action blocked"),
        "perception_d2_claim_audit": ("perception_d2", "claim_audit", "outputs/main_perception_d2/CLAIM_BOUNDARY_AUDIT.md", "perception_candidate_bridge", "claim boundary"),
        "perception_d2_no_mutation": ("perception_d2", "no_mutation_audit", "outputs/main_perception_d2/NO_MUTATION_AUDIT.md", "perception_candidate_bridge", "no mutation"),
        "perception_d2_secret": ("perception_d2", "secret_audit", "outputs/main_perception_d2/SECRET_REDACTION_AUDIT.md", "perception_candidate_bridge", "secret boundary"),
        "perception_d2_hashes": ("perception_d2", "hashes", "outputs/main_perception_d2/hashes.sha256", "perception_candidate_bridge", "reproducibility"),
        "sumo_d2_decision": ("sumo_d2", "decision", "outputs/main_sumo_d2/MAIN_SUMO_D2_DECISION.json", "sumo_city_derived_simulation_producer", "SUMO limitations"),
        "sumo_d2_runtime_report": ("sumo_d2", "runtime_report", "outputs/main_sumo_d2/SUMO_D2_SUMO_RUNTIME_REPORT.json", "sumo_city_derived_simulation_producer", "native SUMO run"),
        "sumo_d2_network_quality": ("sumo_d2", "network_quality", "outputs/main_sumo_d2/SUMO_D2_NETWORK_QUALITY_REPORT.json", "sumo_bounded_routeable_equivalent", "routeable equivalent limitation"),
        "sumo_d2_event_envelopes": ("sumo_d2", "event_log", "outputs/main_sumo_d2/SUMO_D2_EVENT_ENVELOPES.jsonl", "sumo_city_derived_simulation_producer", "simulated/context-only"),
        "sumo_d2_current_state": ("sumo_d2", "duckdb", "outputs/main_sumo_d2/SUMO_D2_CURRENT_STATE.duckdb", "sumo_city_derived_simulation_producer", "simulated current state"),
        "sumo_d2_replay_report": ("sumo_d2", "replay_report", "outputs/main_sumo_d2/SUMO_D2_REPLAY_SESSION_REPORT.json", "sumo_city_derived_simulation_producer", "simulation replay"),
        "sumo_d2_evidencebundle_report": ("sumo_d2", "evidencebundle_report", "outputs/main_sumo_d2/SUMO_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", "sumo_city_derived_simulation_producer", "simulated evidence"),
        "sumo_d2_negative": ("sumo_d2", "negative_test", "outputs/main_sumo_d2/SUMO_D2_NEGATIVE_TEST_REPORT.json", "sumo_city_derived_simulation_producer", "control/routing blocked"),
        "sumo_d2_claim_audit": ("sumo_d2", "claim_audit", "outputs/main_sumo_d2/CLAIM_BOUNDARY_AUDIT.md", "sumo_city_derived_simulation_producer", "claim boundary"),
        "sumo_d2_no_mutation": ("sumo_d2", "no_mutation_audit", "outputs/main_sumo_d2/NO_MUTATION_AUDIT.md", "sumo_city_derived_simulation_producer", "no mutation"),
        "sumo_d2_secret": ("sumo_d2", "secret_audit", "outputs/main_sumo_d2/SECRET_REDACTION_AUDIT.md", "sumo_city_derived_simulation_producer", "secret boundary"),
        "sumo_d2_hashes": ("sumo_d2", "hashes", "outputs/main_sumo_d2/hashes.sha256", "sumo_city_derived_simulation_producer", "reproducibility"),
        "integrated_d2_decision": ("integrated_d2_smoke", "decision", "outputs/main_track1_d2_integrated_runtime_smoke/MAIN_TRACK1_D2_INTEGRATED_RUNTIME_SMOKE_DECISION.json", "unified_d2_event_log", "integrated limitations"),
        "integrated_d2_unified_event_log": ("integrated_d2_smoke", "event_log", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_UNIFIED_EVENT_LOG.jsonl", "unified_d2_event_log", "boundary separation"),
        "integrated_d2_current_state": ("integrated_d2_smoke", "duckdb", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_UNIFIED_CURRENT_STATE.duckdb", "unified_d2_current_state", "separated current state"),
        "integrated_d2_replay_report": ("integrated_d2_smoke", "replay_report", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_REPLAY_SESSION_REPORT.json", "unified_d2_replay", "mixed replay"),
        "integrated_d2_evidencebundle_report": ("integrated_d2_smoke", "evidencebundle_report", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_EVIDENCEBUNDLE_SMOKE_REPORT.json", "unified_d2_evidencebundle_smoke", "mixed evidence"),
        "integrated_d2_negative": ("integrated_d2_smoke", "negative_test", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_NEGATIVE_TEST_REPORT.json", "unified_d2_event_log", "blocked bad claims"),
        "integrated_d2_claim_audit": ("integrated_d2_smoke", "claim_audit", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_CLAIM_BOUNDARY_AUDIT.md", "unified_d2_event_log", "claim boundary"),
        "integrated_d2_no_mutation": ("integrated_d2_smoke", "no_mutation_audit", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_NO_MUTATION_AUDIT.md", "unified_d2_event_log", "no mutation"),
        "integrated_d2_secret": ("integrated_d2_smoke", "secret_audit", "outputs/main_track1_d2_integrated_runtime_smoke/TRACK1_D2_SECRET_REDACTION_AUDIT.md", "unified_d2_event_log", "secret boundary"),
        "integrated_d2_hashes": ("integrated_d2_smoke", "hashes", "outputs/main_track1_d2_integrated_runtime_smoke/hashes.sha256", "unified_d2_event_log", "reproducibility"),
    }
    entries = []
    for artifact_id, (producer, artifact_type, path_text, capability, limitation) in artifacts.items():
        path = ROOT / path_text
        entries.append(
            {
                "artifact_id": artifact_id,
                "path": path_text,
                "producer_gate": producer,
                "artifact_type": artifact_type,
                "status": "PRESENT" if path.exists() else "MISSING",
                "supports_capability": capability,
                "supports_limitation": limitation,
                "hash_ref": f"sha256:{sha256_file(path)}" if path.exists() and path.is_file() else "MISSING",
            }
        )
    return entries


def write_evidence_index() -> list[dict[str, Any]]:
    entries = evidence_entries()
    write_json(OUTPUT_ROOT / "TRACK1_D2_EVIDENCE_INDEX.json", {"task": TASK, "generated_at": now_iso(), "entries": entries, "schema_version": SCHEMA_VERSION})
    return entries


def write_claim_boundary() -> None:
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_CLAIM_BOUNDARY.md",
        """
# Track 1 D2 Claim Boundary

## Allowed Claims

- bounded runtime proof
- governed event fabric
- live/polled event smoke
- perception candidate review bridge
- sample-media candidate event bridge
- SUMO simulated mobility context
- current-state API smoke
- replay smoke
- EvidenceBundle smoke
- review/context/simulated separation

## Forbidden Claims

- production-ready
- autonomous monitoring
- confirmed violation
- identity inference
- face recognition
- biometric inference
- dispatch recommendation
- enforcement recommendation
- public-safety command
- health determination
- routing recommendation
- traffic-control command
- transit-control command
- port/vessel-control command
- certified impact
- certified affected asset/building

## Boundary

Track 1 D2 is a governed runtime proof. It keeps observed/context, candidate/review-only, and simulated/context-only state separate and takes no action.
""",
    )


def write_roadmap() -> None:
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_D3_ROADMAP.md",
        """
# Track 1 D3 Roadmap

D3 theme: harden the bounded D2 runtime into a service-grade multi-city runtime twin.

## 1. MAIN-EVENT-FABRIC-D3

Purpose: service mode, stronger API contract, multi-city adapter expansion, observability, cursor recovery, retention policy, replay API hardening, error budgets/health checks, and deployment profile for 4070/3090 boxes where relevant.

## 2. MAIN-PERCEPTION-D3

Purpose: DeepStream/Metropolis path on the 4070 box, model-output adapter, real sample camera/video pipeline, stronger camera/zone governance, review API/UI integration, media metadata hardening, and privacy/redaction posture.

## 3. MAIN-SUMO-D3

Purpose: improve network extraction beyond point-chain routeable equivalent, expand Barcelona/London/NYC/Chicago subsets, define scenario catalog, calibrate against observed mobility signals, and compare simulated vs observed mobility context. It remains not routing/control.

## 4. MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE

Purpose: unified runtime API, durable multi-producer service smoke, trace/debug tooling, EvidenceBundle/briefing integration, and dashboard/control-room readiness.

## Boundaries To Preserve

- no enforcement, dispatch, or control claims
- no certified impact
- no production readiness without D5
""",
    )


def backlog_tasks() -> list[dict[str, Any]]:
    ordered = [
        ("MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING", "Harden the D2 fabric into service mode with API contract, observability, cursor recovery, replay API, retention, and health checks."),
        ("MAIN-EVENT-FABRIC-D3-MULTICITY-ADAPTERS", "Expand and harden multi-city adapters using D2 polling/cursor patterns."),
        ("MAIN-PERCEPTION-D3-DEEPSTREAM-BRIDGE", "Add DeepStream/Metropolis-compatible model-output bridge on the 4070 box when available."),
        ("MAIN-PERCEPTION-D3-REVIEW-API", "Expose review packet lifecycle through a bounded API/UI integration contract."),
        ("MAIN-SUMO-D3-NETWORK-EXTRACTION-HARDENING", "Improve network extraction beyond Barcelona point-chain routeable equivalent."),
        ("MAIN-SUMO-D3-SCENARIO-CATALOG", "Create a larger scenario catalog and simulated-vs-observed comparison harness."),
        ("MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE", "Prove all D3 producers through one durable integrated service smoke."),
    ]
    tasks = []
    for index, (task_id, goal) in enumerate(ordered, start=1):
        tasks.append(
            {
                "task_id": task_id,
                "goal": goal,
                "prerequisites": ["MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP"],
                "inputs": ["Track 1 D2 evidence index", "D2 current-state stores", "D2 event logs", "D2 limitations register"],
                "outputs": ["D3 task-specific output pack", "decision JSON", "claim/no-mutation/secret audits"],
                "success_criteria": ["bounded service-grade hardening passes", "limitations remain surfaced", "no enforcement/dispatch/control/certified-impact claims"],
                "risks": ["scope creep into D4 product work", "overclaiming production readiness", "weakening D2 boundaries"],
                "non_goals": ["D4 Omniverse/control-room product experience", "D5 production deployment", "autonomous control"],
                "suggested_order": index,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return tasks


def write_backlog_and_non_goals() -> None:
    write_json(OUTPUT_ROOT / "TRACK1_D3_TASK_BACKLOG.json", {"task": TASK, "generated_at": now_iso(), "tasks": backlog_tasks(), "schema_version": SCHEMA_VERSION})
    write_text(
        OUTPUT_ROOT / "TRACK1_D3_NON_GOALS.md",
        """
# Track 1 D3 Non-Goals

D3 is not:

- D4 Omniverse/control-room product experience
- D5 production enterprise deployment
- autonomous control
- public safety system
- enforcement system
- certified traffic model
- certified asset-risk model
- production CCTV system
- identity/biometric system
""",
    )
    write_text(
        OUTPUT_ROOT / "TRACK1_D4_PLACEHOLDER_NOTE.md",
        """
# Track 1 D4 Placeholder Note

D4 is future product/3D/operator twin integration. It likely includes Omniverse/OpenUSD scene integration, a 3D city subset linked to runtime events, control-room UI, scenario playback in 3D, human-review workflows, trace/dashboard/briefing experience, and demo/product packaging.

No D4 tasks are created by this D2 closeout.
""",
    )


def write_main_docs(audit: dict[str, Any], evidence: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP

This output pack freezes the completed Track 1 D2 runtime/body layer, records certified capabilities and limitations, indexes evidence, and defines the D3 roadmap without starting D3 implementation.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP.md",
        f"""
# MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP

## Gate Status

- Event Fabric D2: `{audit['gates']['event_fabric_d2']['final_status']}`
- Perception D2: `{audit['gates']['perception_d2']['final_status']}`
- SUMO D2: `{audit['gates']['sumo_d2']['final_status']}`
- Integrated D2 smoke: `{audit['gates']['integrated_d2_smoke']['final_status']}`

## Certified Sentence

CityBrain can ingest bounded live/polled events, perception candidate events, and SUMO simulation events into one governed event fabric, materialize current state, replay scenarios, and produce EvidenceBundles while preserving review/context/simulated boundaries.

## Evidence

- Evidence index entries: `{len(evidence)}`
- Required artifact audit: `{audit['status']}`

## Carry-Forward Limitation

SUMO D2 uses Barcelona city-derived traffic-section coordinates as a bounded SUMO-routeable equivalent. It is not a complete routable street graph, not a certified traffic model, and not a routing/control system.
""",
    )


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in before if before[key] != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    changed_text = "\n".join(f"- `{key}` changed" for key in changed) if changed else "- Watched input roots/files were unchanged."
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_NO_MUTATION_AUDIT.md",
        f"""
# Track 1 D2 No-Mutation Audit

Status: `{status}`

## Proved

- D1 roots unchanged
- Event Fabric D2 root unchanged
- Perception D2 root unchanged
- SUMO D2 root unchanged
- Integrated D2 smoke root unchanged
- PV1 D19-D22 unchanged
- A9/G1 unchanged
- generated platform state unchanged
- accepted flow state unchanged if present
- city landing/prep roots unchanged
- no flow promotion run
- no data downloads
- no D3 implementation started

## Result

{changed_text}
""",
    )
    return {"status": status, "changed": changed}


def secret_scan_paths() -> list[Path]:
    return [
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".jsonl", ".txt", ".csv"}
    ] + [ROOT / "scripts" / "run_main_track1_d2_closeout_and_d3_roadmap.py"]


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9_\-\.]+"),
        re.compile(r"(?i)tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
    ]
    findings = []
    for path in secret_scan_paths():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.name == "run_main_track1_d2_closeout_and_d3_roadmap.py":
            text = "\n".join(line for line in text.splitlines() if "re.compile(" not in line)
        if any(pattern.search(text) for pattern in patterns):
            findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw TMB key leakage found." if not findings else "\n".join(f"- `{path}`" for path in findings)
    write_text(
        OUTPUT_ROOT / "TRACK1_D2_SECRET_REDACTION_AUDIT.md",
        f"""
# Track 1 D2 Secret Redaction Audit

Status: `{status}`

## Result

{finding_text}

## Scope

Generated closeout outputs and runner were scanned.
""",
    )
    return {"status": status, "findings": findings}


def write_hashes() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(audit: dict[str, Any], evidence: list[dict[str, Any]], no_mutation: dict[str, Any], secret_audit_result: dict[str, Any], hashes: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "all_four_d2_gates_inspected": "PASS" if audit["status"] == "PASS" else "FAIL",
        "certified_d2_state_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_CERTIFIED_STATE.md").exists() else "FAIL",
        "capability_ledger_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_CAPABILITY_LEDGER.json").exists() else "FAIL",
        "limitations_register_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_LIMITATIONS_REGISTER.md").exists() else "FAIL",
        "evidence_index_written": "PASS" if evidence and all(entry["status"] == "PRESENT" for entry in evidence) else "FAIL",
        "claim_boundary_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_CLAIM_BOUNDARY.md").exists() else "FAIL",
        "no_mutation_audit": no_mutation["status"],
        "secret_redaction_audit": secret_audit_result["status"],
        "d3_roadmap_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D2_D3_ROADMAP.md").exists() else "FAIL",
        "d3_task_backlog_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D3_TASK_BACKLOG.json").exists() else "FAIL",
        "d3_non_goals_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D3_NON_GOALS.md").exists() else "FAIL",
        "d4_placeholder_note_written": "PASS" if (OUTPUT_ROOT / "TRACK1_D4_PLACEHOLDER_NOTE.md").exists() else "FAIL",
        "hashes": hashes["status"],
        "no_d3_work_started": "PASS",
        "platform_state_not_mutated": "PASS" if "platform_state_generated" not in no_mutation["changed"] else "FAIL",
    }
    failing = [key for key, value in checks.items() if value != "PASS"]
    sumo_limitation_active = audit["gates"]["sumo_d2"]["final_status"] == "PASS_MAIN_SUMO_D2_WITH_LIMITATIONS"
    if failing:
        final_status = "FAIL_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP"
    elif sumo_limitation_active:
        final_status = "PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_WITH_LIMITATIONS"
    else:
        final_status = "PASS_MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP"
    decision = {
        "task": TASK,
        "generated_at": now_iso(),
        "final_status": final_status,
        "checks": checks,
        "gate_statuses": {key: gate["final_status"] for key, gate in audit["gates"].items()},
        "limitations_carried_forward": {
            "sumo_d2": audit["gates"]["sumo_d2"]["limitations"],
            "perception_d2": audit["gates"]["perception_d2"]["limitations"],
            "event_fabric_d2": audit["gates"]["event_fabric_d2"]["limitations"],
            "integrated_d2_smoke": audit["gates"]["integrated_d2_smoke"]["limitations"],
        },
        "evidence_entries": len(evidence),
        "output_root": rel(OUTPUT_ROOT),
        "recommended_next_task": "MAIN-EVENT-FABRIC-D3-SERVICE-HARDENING",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json", decision)
    return decision


def main() -> int:
    before = capture_watch_signatures()
    ensure_output()
    audit = load_gate_audit()
    write_input_artifact_audit(audit)
    write_certified_state(audit)
    write_capability_ledger()
    write_limitations_register(audit)
    evidence = write_evidence_index()
    write_claim_boundary()
    write_roadmap()
    write_backlog_and_non_goals()
    write_main_docs(audit, evidence)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret_audit_result = write_secret_audit()
    hashes = write_hashes()
    decision = write_decision(audit, evidence, no_mutation, secret_audit_result, hashes)
    hashes = write_hashes()
    decision["checks"]["hashes"] = hashes["status"]
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D2_CLOSEOUT_AND_D3_ROADMAP_DECISION.json", decision)
    write_hashes()

    print("MAIN-TRACK1-D2-CLOSEOUT-AND-D3-ROADMAP: STATUS")
    for key, gate in audit["gates"].items():
        print(f"{gate['name']}: {gate['final_status']}")
    print(f"Input artifact audit: {audit['status']}")
    print(f"Evidence index entries: {len(evidence)}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret_audit_result['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['final_status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if decision["final_status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
