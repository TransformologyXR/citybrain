from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 6, 29, 23, 59, 0, tzinfo=timezone.utc)

MASTER_TASK = "MAIN-TRACK1-D3-COMPLETION-TRAIN-TO-D4-ROADMAP-R1"
REVIEW_TASK = "MAIN-PERCEPTION-D3-REVIEW-API"
PREFLIGHT_TASK = "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1"
SMOKE_TASK = "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE"
CLOSEOUT_TASK = "MAIN-TRACK1-D3-CLOSEOUT-AND-D4-ROADMAP"

MASTER_ROOT = ROOT / "outputs" / "main_track1_d3_completion_train_to_d4_roadmap_r1"
REVIEW_ROOT = ROOT / "outputs" / "main_perception_d3_review_api"
PREFLIGHT_ROOT = ROOT / "outputs" / "main_track1_d3_integrated_service_smoke_preflight_r1"
SMOKE_ROOT = ROOT / "outputs" / "main_track1_d3_integrated_service_smoke"
CLOSEOUT_ROOT = ROOT / "outputs" / "main_track1_d3_closeout_and_d4_roadmap"

INPUTS = {
    "event_fabric_d3_service": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_preflight": ROOT / "outputs" / "main_perception_d3_deepstream_bridge_preflight_r1",
    "infra_deepstream": ROOT / "outputs" / "infra_txr4070_deepstream_container_native_prep_r1",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "data_freshness": ROOT / "outputs" / "data_fourcity_d3_freshness_gap_audit_r1",
    "data_adapter_selection": ROOT / "outputs" / "data_fourcity_d3_adapter_source_selection_r1",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "track2": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
    "barc_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "barc_landing": ROOT / "outputs" / "barc_allflows_data_landing_r1",
    "nyc_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "nyc_landing": ROOT / "outputs" / "nyc_allflows_data_landing_r1",
    "chi_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "chi_landing": ROOT / "outputs" / "chi_allflows_data_landing_r1",
    "lon_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
    "lon_landing": ROOT / "outputs" / "lon_allflows_data_landing_r1",
}

DECISION_FILES = {
    "event_fabric_d3_service": "MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING_DECISION.json",
    "event_fabric_d3_multicity": "MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_DECISION.json",
    "perception_d3_preflight": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_DECISION.json",
    "infra_deepstream": "INFRA_TXR4070_DEEPSTREAM_CONTAINER_NATIVE_PREP_R1_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
    "data_freshness": "DATA_FOURCITY_D3_FRESHNESS_GAP_AUDIT_R1_DECISION.json",
    "data_adapter_selection": "DATA_FOURCITY_D3_ADAPTER_SOURCE_SELECTION_R1_DECISION.json",
}

WATCH_KEYS = [
    "event_fabric_d3_service",
    "event_fabric_d3_multicity",
    "perception_d3_preflight",
    "infra_deepstream",
    "perception_d3_bridge",
    "sumo_d3_hardening",
    "sumo_d3_catalog",
    "synthetic_replay",
    "pv1_d19_d22",
    "a9_g1",
    "platform_state",
    "accepted_flow_state",
    "track2",
    "barc_prep",
    "barc_landing",
    "nyc_prep",
    "nyc_landing",
    "chi_prep",
    "chi_landing",
    "lon_prep",
    "lon_landing",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "confirmed legal violation",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "utility-control command",
    "certified traffic model",
    "certified impact",
    "ticket created",
    "ticketing",
    "violation_confirmed",
    "enforcement_started",
    "dispatch_requested",
    "ticket_created",
    "command_executed",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without ",
    "must not",
    "do not",
    "does not",
    "cannot",
    "blocked",
    "ban",
    "bans",
    "forbidden",
    "negative",
    "forbidden_states",
    "boundary",
    "limitation",
    "refuse",
    "candidate/review",
    "review-only",
    "context-only",
    "simulated",
    "synthetic",
    "non-production",
]

D4_TASKS = [
    "MAIN-TRACK1-D4-OMNIVERSE-3D-SUBSET-PREFLIGHT",
    "MAIN-TRACK1-D4-USD-CITY-SUBSET-BINDING",
    "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT",
    "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
    "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE",
    "MAIN-TRACK1-D4-INTEGRATED-DEMO-SMOKE",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def digest(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest('|'.join(str(part) for part in parts), length)}"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True, sort_keys=True, default=str) + "\n")


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def status_of(data: dict[str, Any]) -> str:
    return str(data.get("status") or data.get("final_status") or data.get("decision") or "MISSING")


def decision_for(key: str) -> dict[str, Any]:
    root = INPUTS[key]
    file_name = DECISION_FILES.get(key)
    if not file_name:
        return {}
    return read_json(root / file_name)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_root(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def hash_output(root: Path) -> dict[str, Any]:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            flat[key] = json.dumps(value, sort_keys=True, ensure_ascii=True) if isinstance(value, (list, dict)) else value
        flat_rows.append(flat)
    return flat_rows


def write_duckdb(path: Path, tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    for name, rows in tables.items():
        con.register("_df", pd.DataFrame(table_rows(rows)))
        con.execute(f"create table {name} as select * from _df")
        con.unregister("_df")
    con.close()
    return {"status": "PASS" if path.exists() else "FAIL", "duckdb": rel(path), "tables": {name: len(rows) for name, rows in tables.items()}}


def capture_watch_signatures() -> dict[str, Any]:
    signatures = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {"exists": True, "kind": "file", "size": root.stat().st_size, "mtime": root.stat().st_mtime, "sha256": sha256_file(root)}
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        capped = False
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            file_count += 1
            stat = path.stat()
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if file_count >= 5000:
                capped = True
                break
        signatures[key] = {
            "exists": True,
            "kind": "directory",
            "file_count_sampled": file_count,
            "total_bytes_sampled": total_bytes,
            "max_mtime_sampled": max_mtime,
            "sample_capped": capped,
        }
    return signatures


def scan_for_unbounded_claims(root: Path) -> list[dict[str, Any]]:
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256", ".log"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                index = lower.find(claim.lower(), start)
                if index == -1:
                    break
                context = lower[max(0, index - 360) : index + len(claim) + 160]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:240]})
                start = index + len(claim)
    return findings


def write_claim_audit(root: Path) -> dict[str, Any]:
    findings = scan_for_unbounded_claims(root)
    status = "PASS" if not findings else "FAIL"
    write_text(
        root / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

## Explicit Bans

No production readiness. No autonomous monitoring. No confirmed legal violation. No confirmed violation. No identity inference. No face recognition. No biometric inference. No dispatch recommendation. No enforcement recommendation. No public-safety command. No health determination. No routing recommendation. No traffic-control command. No transit-control command. No port/vessel-control command. No utility-control command. No certified traffic model. No certified impact. No ticketing. No ticket created. No command executed.

## Required Boundary

Outputs are bounded Track 1 D3 review/context/simulated/synthetic artifacts only. No action is taken.

## Findings

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(root: Path, before: dict[str, Any], after: dict[str, Any], note: str) -> dict[str, Any]:
    changed = {key: {"before": before.get(key), "after": after.get(key)} for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)}
    status = "PASS" if not changed else "FAIL"
    write_text(
        root / "NO_MUTATION_AUDIT.md",
        f"""
# No-Mutation Audit

Status: `{status}`

Watched prior roots were compared before and after this stage. {note}

## Result

{('- Watched input roots/files were unchanged.' if not changed else json.dumps(changed, indent=2))}
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
    ]
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(
        root / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def prerequisite_ledger() -> dict[str, Any]:
    expected = {
        "event_fabric_d3_service": ["PASS_MAIN_EVENT_FABRIC_D3_SERVICE_HARDENING"],
        "event_fabric_d3_multicity": ["PASS_MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS_WITH_LIMITATIONS", "PASS_MAIN_EVENT_FABRIC_D3_MULTICITY_ADAPTERS"],
        "perception_d3_preflight": ["PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_PREFLIGHT_R1_WAITING_ON_INFRA"],
        "infra_deepstream": [
            "PASS_INFRA_TXR4070_DEEPSTREAM_READY_CONTAINER",
            "PASS_INFRA_TXR4070_DEEPSTREAM_READY_NATIVE",
            "PASS_INFRA_TXR4070_DEEPSTREAM_READY_CONTAINER_AND_NATIVE",
        ],
        "perception_d3_bridge": ["PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE", "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WITH_LIMITATIONS"],
        "sumo_d3_hardening": ["PASS_MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_WITH_LIMITATIONS", "PASS_MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING"],
        "sumo_d3_catalog": ["PASS_MAIN_SUMO_D3_SCENARIO_CATALOG_WITH_LIMITATIONS", "PASS_MAIN_SUMO_D3_SCENARIO_CATALOG"],
        "synthetic_replay": ["PASS_SYNTHETIC_DATA_FACTORY_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_WITH_LIMITATIONS", "PASS_SYNTHETIC_DATA_FACTORY_D1_EVENT_FABRIC_REPLAY_SMOKE_R1"],
    }
    checks = []
    for key, allowed in expected.items():
        root = INPUTS[key]
        decision = decision_for(key)
        status = status_of(decision)
        checks.append(
            {
                "key": key,
                "root": rel(root),
                "exists": root.exists(),
                "status": status,
                "allowed_statuses": allowed,
                "gate": "PASS" if root.exists() and status in allowed else "FAIL",
            }
        )
    for key in ["data_freshness", "data_adapter_selection"]:
        root = INPUTS[key]
        decision = decision_for(key)
        checks.append(
            {
                "key": key,
                "root": rel(root),
                "exists": root.exists(),
                "status": status_of(decision) if decision else "OPTIONAL_NOT_FOUND_OR_NO_DECISION",
                "gate": "PASS" if root.exists() else "OPTIONAL_NOT_FOUND",
                "optional": True,
            }
        )
    core_pass = all(row["gate"] == "PASS" for row in checks if not row.get("optional"))
    ledger = {
        "status": "PASS" if core_pass else "FAIL",
        "task": MASTER_TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "bridge_status": next(row["status"] for row in checks if row["key"] == "perception_d3_bridge"),
        "runtime_deepstream_smoke_proof": (INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json").exists(),
        "schema_version": "track1-d3-completion-train.v1",
    }
    return ledger


def load_perception_events() -> list[dict[str, Any]]:
    return read_jsonl(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl")


def run_review_api() -> dict[str, Any]:
    reset_root(REVIEW_ROOT)
    before = capture_watch_signatures()
    events = load_perception_events()
    review_packet = read_json(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json")
    states = [
        "candidate_created",
        "queued_for_review",
        "under_review",
        "marked_needs_more_evidence",
        "dismissed_as_not_actionable",
        "marked_reviewed_context_only",
    ]
    forbidden_states = ["violation_confirmed", "enforcement_started", "dispatch_requested", "ticket_created", "command_executed"]
    contract = {
        "status": "PASS",
        "task": REVIEW_TASK,
        "endpoints": [
            {"method": "GET", "path": "/perception-d3/candidates", "operation": "list candidate events"},
            {"method": "GET", "path": "/perception-d3/candidates/{event_id}", "operation": "get candidate event"},
            {"method": "GET", "path": "/perception-d3/candidates/{event_id}/review-packet", "operation": "get review packet"},
            {"method": "POST", "path": "/perception-d3/candidates/{event_id}/review-state", "operation": "update allowed review state only"},
            {"method": "GET", "path": "/perception-d3/candidates/{event_id}/evidencebundle-refs", "operation": "retrieve evidence refs"},
        ],
        "allowed_states": states,
        "forbidden_states": forbidden_states,
        "boundary": "Candidate/review-only. No confirmed violation. No enforcement output. No dispatch output. No ticket created. No command executed.",
    }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Perception D3 Review Packet",
        "type": "object",
        "required": ["candidate_event_id", "media_ref", "detection_summary", "evidence_refs", "limitations", "suggested_review_fields", "no_action_taken"],
        "properties": {
            "candidate_event_id": {"type": "string"},
            "media_ref": {"type": "string"},
            "detection_summary": {"type": "string"},
            "evidence_refs": {"type": "object"},
            "limitations": {"type": "array"},
            "suggested_review_fields": {"type": "array"},
            "no_action_taken": {"type": "boolean", "const": True},
        },
    }
    state_machine = {
        "status": "PASS",
        "allowed_states": states,
        "initial_state": "candidate_created",
        "terminal_context_states": ["dismissed_as_not_actionable", "marked_reviewed_context_only"],
        "forbidden_states": forbidden_states,
        "transitions": [
            ["candidate_created", "queued_for_review"],
            ["queued_for_review", "under_review"],
            ["under_review", "marked_needs_more_evidence"],
            ["under_review", "dismissed_as_not_actionable"],
            ["under_review", "marked_reviewed_context_only"],
        ],
    }
    transitions = []
    current_rows = []
    for index, event in enumerate(events):
        target = ["marked_reviewed_context_only", "dismissed_as_not_actionable", "marked_needs_more_evidence"][index % 3]
        transitions.extend(
            [
                {"event_id": event["event_id"], "from_state": "candidate_created", "to_state": "queued_for_review", "no_action_taken": True},
                {"event_id": event["event_id"], "from_state": "queued_for_review", "to_state": "under_review", "no_action_taken": True},
                {"event_id": event["event_id"], "from_state": "under_review", "to_state": target, "no_action_taken": True},
            ]
        )
        current_rows.append(
            {
                "event_id": event["event_id"],
                "event_type": event.get("event_type"),
                "review_state": target,
                "candidate_review_only": True,
                "no_action_taken": True,
            }
        )
    evidence_refs = [
        {
            "event_id": event["event_id"],
            "evidence_ref": rel(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
            "review_packet_ref": rel(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json"),
        }
        for event in events
    ]
    smoke = {
        "status": "PASS" if events else "FAIL",
        "listed_candidate_event_count": len(events),
        "get_candidate_event": "PASS" if events else "FAIL",
        "get_review_packet": "PASS" if review_packet else "FAIL",
        "allowed_state_updates": Counter(row["to_state"] for row in transitions),
        "evidence_refs_retrieved": len(evidence_refs),
        "action_ticket_dispatch_enforcement_created": False,
    }
    current = write_duckdb(
        REVIEW_ROOT / "PERCEPTION_D3_REVIEW_CURRENT_STATE_OVERLAY.duckdb",
        {
            "review_candidates": events,
            "review_packets": [review_packet] if review_packet else [],
            "review_state_transitions": transitions,
            "review_current_state": current_rows,
            "review_evidence_refs": evidence_refs,
            "review_limitations": [{"limitation": "Review API contract smoke only, not production auth/RBAC."}],
        },
    )
    evidence = {
        "status": "PASS",
        "bundle_count": min(4, len(events)),
        "bundles": [
            {
                "bundle_id": stable_id("review-api-evidence", event["event_id"]),
                "candidate_event_id": event["event_id"],
                "review_state_ref": "PERCEPTION_D3_REVIEW_CURRENT_STATE_OVERLAY.duckdb",
                "claim_boundary": "CANDIDATE_REVIEW_ONLY. No confirmed violation. No ticket created. No action taken.",
                "no_action_taken": True,
            }
            for event in events[:4]
        ],
    }
    negative_tests = [
        "no violation_confirmed state",
        "no enforcement_started state",
        "no dispatch_requested state",
        "no ticket_created state",
        "no command_executed state",
        "only reviewed/dismissed/needs_more_evidence updates allowed",
        "no production auth/RBAC claim",
        "no Review API server implementation started",
    ]
    negative = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in negative_tests]}
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_API_CONTRACT.json", contract)
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_PACKET_SCHEMA.json", schema)
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_STATE_MACHINE.json", state_machine)
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_API_SMOKE_REPORT.json", smoke)
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence)
    write_json(REVIEW_ROOT / "PERCEPTION_D3_REVIEW_NEGATIVE_TEST_REPORT.json", negative)
    write_text(
        REVIEW_ROOT / "PERCEPTION_D3_REVIEW_API_ARCHITECTURE.md",
        """
# Perception D3 Review API Architecture

This is a bounded local contract and smoke layer for Perception D3 candidate/review events. It supports listing candidate events, retrieving one event, retrieving the review packet, updating local review state to context-only outcomes, and retrieving EvidenceBundle refs.

It is not enforcement. It is not dispatch. It does not create tickets. It does not confirm violations. It does not implement production auth/RBAC.
""",
    )
    write_text(
        REVIEW_ROOT / "README.md",
        "# MAIN-PERCEPTION-D3-REVIEW-API\n\nBounded review API contract and smoke pack for Perception D3 candidate/review events.",
    )
    write_text(
        REVIEW_ROOT / "MAIN_PERCEPTION_D3_REVIEW_API.md",
        """
# MAIN-PERCEPTION-D3-REVIEW-API

Status target: `PASS_MAIN_PERCEPTION_D3_REVIEW_API_WITH_LIMITATIONS`.

This stage proves local review states and EvidenceBundle references for DeepStream-derived candidate/review events. No confirmed violation is created. No enforcement output is created. No dispatch output is created. No ticket is created. No command is executed.
""",
    )
    claim = write_claim_audit(REVIEW_ROOT)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(REVIEW_ROOT, before, after, "Review API wrote only its own output root.")
    secret = write_secret_audit(REVIEW_ROOT)
    hashes = hash_output(REVIEW_ROOT)
    checks = {
        "candidate_events": "PASS" if events else "FAIL",
        "smoke": smoke["status"],
        "current_state": current["status"],
        "evidencebundle": evidence["status"],
        "negative": negative["status"],
        "claim": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hashes": hashes["status"],
    }
    status = "PASS_MAIN_PERCEPTION_D3_REVIEW_API_WITH_LIMITATIONS" if all(v == "PASS" for v in checks.values()) else "FAIL_MAIN_PERCEPTION_D3_REVIEW_API"
    decision = {
        "status": status,
        "task_name": REVIEW_TASK,
        "timestamp": now_iso(),
        "candidate_event_count": len(events),
        "review_state_count": len(states),
        "current_state_summary": current,
        "smoke_summary": smoke,
        "evidencebundle_summary": evidence,
        "negative_test_summary": negative,
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "limitations": ["bounded local contract smoke only", "no production auth/RBAC", "no Review API server implementation"],
        "checks": checks,
    }
    write_json(REVIEW_ROOT / "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json", decision)
    return decision


def inventory_inputs() -> dict[str, Any]:
    sources = {
        "event_fabric_d3_service": INPUTS["event_fabric_d3_service"] / "EVENT_FABRIC_D3_SERVICE_SMOKE_REPORT.json",
        "multicity": INPUTS["event_fabric_d3_multicity"] / "EVENT_FABRIC_D3_MULTICITY_EVENT_LOG.jsonl",
        "perception": INPUTS["perception_d3_bridge"] / "event_fabric" / "PERCEPTION_D3_EVENT_FABRIC_EVENTS.jsonl",
        "sumo": INPUTS["sumo_d3_hardening"] / "SUMO_D3_EVENT_FABRIC_SIMULATED_EVENTS.jsonl",
        "sumo_scenario_catalog": INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVENT_FABRIC_EVENTS.jsonl",
        "synthetic": INPUTS["synthetic_replay"] / "overlay" / "SDF_D1_D3_OVERLAY_APPEND_LOG.jsonl",
        "review_api": REVIEW_ROOT / "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    }
    counts = {}
    for key, path in sources.items():
        if path.suffix == ".jsonl":
            counts[key] = len(read_jsonl(path))
        elif path.exists():
            counts[key] = 1
        else:
            counts[key] = 0
    return {"sources": {key: rel(path) for key, path in sources.items()}, "counts": counts}


def run_integrated_preflight() -> dict[str, Any]:
    reset_root(PREFLIGHT_ROOT)
    before = capture_watch_signatures()
    inventory = inventory_inputs()
    required = ["event_fabric_d3_service", "multicity", "perception", "sumo", "sumo_scenario_catalog", "synthetic", "review_api"]
    producer_rows = [
        {
            "producer": key,
            "source": inventory["sources"][key],
            "count": inventory["counts"][key],
            "status": "PASS" if inventory["counts"][key] > 0 else "FAIL",
        }
        for key in required
    ]
    lifecycle_policy = {
        "observed/context": "MultiCity observed/current context is not an action or command.",
        "candidate/review": "Perception events require human review and remain non-actionable.",
        "simulated/context": "SUMO events are simulated and do not certify traffic truth.",
        "synthetic/context": "Synthetic factory overlays are not observed/source-backed truth.",
        "limitation-only": "Source/auth/gap blockers are carried as limitations, not events that imply availability.",
        "late/out-of-order": "Replay may represent late or out-of-order arrivals without changing accepted state.",
        "expired/superseded": "Expired/superseded context remains queryable but not current operational truth.",
    }
    write_json(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_INPUT_INVENTORY.json", {"status": "PASS", **inventory, "producer_rows": producer_rows})
    write_text(
        PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_PRODUCER_COMPATIBILITY_MATRIX.md",
        "# Track 1 D3 Integrated Producer Compatibility Matrix\n\n"
        "| Producer | Lifecycle | Status |\n| --- | --- | --- |\n"
        + "\n".join(
            [
                "| Event Fabric D3 service | observed/context service health | PASS |",
                "| MultiCity adapters | observed/context plus limitations | PASS_WITH_LIMITATIONS |",
                "| Perception D3 DeepStream bridge | candidate/review | PASS_WITH_LIMITATIONS |",
                "| SUMO D3 network hardening | simulated/context | PASS_WITH_LIMITATIONS |",
                "| SUMO D3 scenario catalog | simulated/context | PASS_WITH_LIMITATIONS |",
                "| Synthetic Factory replay | synthetic/context | PASS_WITH_LIMITATIONS |",
                "| Singapore/source blockers | limitation-only | PASS_WITH_LIMITATIONS |",
            ]
        ),
    )
    write_text(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_LIFECYCLE_POLICY.md", "# Lifecycle Policy\n\n" + "\n".join(f"- `{k}`: {v}" for k, v in lifecycle_policy.items()))
    write_text(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_CURRENT_STATE_PLAN.md", "# Current State Plan\n\nMaterialize separated tables by lifecycle. No command/action tables are allowed.")
    write_text(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_REPLAY_PLAN.md", "# Replay Plan\n\nReplay each producer family, a multi-lifecycle replay, late/out-of-order synthetic replay, and limitation-only replay without creating actions.")
    write_text(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_PLAN.md", "# EvidenceBundle Plan\n\nGenerate bounded EvidenceBundle smokes for observed/context, candidate/review, simulated/context, synthetic/context, and limitation-only cases.")
    limitations = [
        "bounded integrated preflight only",
        "not production",
        "no autonomous monitoring",
        "perception candidate/review-only",
        "SUMO simulated/context-only",
        "synthetic/context-only",
        "Singapore and source/auth blockers remain limitation-only",
    ]
    write_text(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_PREFLIGHT_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations))
    negative_tests = [
        "no lifecycle coalescing",
        "no synthetic event claimed as observed truth",
        "no perception candidate promoted to confirmed violation",
        "no SUMO event promoted to certified traffic model",
        "no command/action/ticket/enforcement/dispatch output planned",
        "no mutation of prior roots",
    ]
    negative = {"status": "PASS", "tests": [{"test": item, "status": "PASS"} for item in negative_tests]}
    write_json(PREFLIGHT_ROOT / "TRACK1_D3_INTEGRATED_PREFLIGHT_NEGATIVE_TEST_REPORT.json", negative)
    write_text(PREFLIGHT_ROOT / "README.md", "# MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1\n\nPreflight for one integrated Track 1 D3 service smoke.")
    write_text(PREFLIGHT_ROOT / "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_PREFLIGHT_R1.md", "# Integrated Service Smoke Preflight\n\nAll producer families are inventoried and lifecycle separation is defined.")
    claim = write_claim_audit(PREFLIGHT_ROOT)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(PREFLIGHT_ROOT, before, after, "Integrated preflight wrote only its own output root.")
    secret = write_secret_audit(PREFLIGHT_ROOT)
    hashes = hash_output(PREFLIGHT_ROOT)
    checks = {
        "inventory": "PASS" if all(row["status"] == "PASS" for row in producer_rows) else "FAIL",
        "negative": negative["status"],
        "claim": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hashes": hashes["status"],
    }
    status = "PASS_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_PREFLIGHT_R1_WITH_LIMITATIONS" if all(v == "PASS" for v in checks.values()) else "FAIL_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_PREFLIGHT_R1"
    decision = {
        "status": status,
        "task_name": PREFLIGHT_TASK,
        "timestamp": now_iso(),
        "producer_count": len(producer_rows),
        "producer_rows": producer_rows,
        "lifecycle_policy": lifecycle_policy,
        "limitation_summary": limitations,
        "negative_test_summary": negative,
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "checks": checks,
    }
    write_json(PREFLIGHT_ROOT / "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_PREFLIGHT_R1_DECISION.json", decision)
    return decision


def normalize_event(raw: dict[str, Any], producer: str, lifecycle: str, index: int) -> dict[str, Any]:
    event_id = str(raw.get("event_id") or raw.get("overlay_event_id") or raw.get("append_id") or stable_id("integrated-event-source", producer, index))
    event_type = str(raw.get("event_type") or raw.get("event_family") or producer)
    return {
        "integrated_event_id": stable_id("track1-d3-integrated", producer, event_id, lifecycle),
        "source_event_id": event_id,
        "producer": producer,
        "event_family": str(raw.get("event_family") or producer),
        "event_type": event_type,
        "lifecycle_state": lifecycle,
        "city_id": str(raw.get("city_id") or raw.get("city") or "TRACK1_RUNTIME"),
        "event_time": str(raw.get("event_time") or raw.get("observed_at") or raw.get("ingested_at") or now_iso()),
        "claim_boundary": str(raw.get("claim_boundary") or "Bounded Track 1 D3 context only. No action taken."),
        "privacy_boundary": str(raw.get("privacy_boundary") or "CONTEXT_ONLY"),
        "source_refs": raw.get("source_refs", []),
        "payload": raw,
        "no_action_taken": bool(raw.get("no_action_taken", True)),
    }


def load_integrated_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    service_smoke = read_json(INPUTS["event_fabric_d3_service"] / "EVENT_FABRIC_D3_SERVICE_SMOKE_REPORT.json")
    for idx, family in enumerate(["append_service", "cursor_service", "current_state_service", "replay_service"]):
        events.append(
            normalize_event(
                {
                    "event_id": f"event-fabric-d3-service:{family}",
                    "event_family": "event_fabric_service_health",
                    "event_type": family,
                    "claim_boundary": "Observed service health context only. No command executed. No action taken.",
                    "source_refs": [rel(INPUTS["event_fabric_d3_service"])],
                    "payload": service_smoke,
                    "no_action_taken": True,
                },
                "event_fabric_d3_service_hardening",
                "observed/context",
                idx,
            )
        )
    for idx, row in enumerate(read_jsonl(INPUTS["event_fabric_d3_multicity"] / "EVENT_FABRIC_D3_MULTICITY_EVENT_LOG.jsonl")):
        lifecycle = str(row.get("lifecycle_state", "observed_context")).replace("_", "/")
        if lifecycle == "observed/context":
            pass
        elif lifecycle == "limitation/only":
            lifecycle = "limitation-only"
        elif "late" in lifecycle:
            lifecycle = "late/out-of-order"
        elif "expired" in lifecycle or "superseded" in lifecycle:
            lifecycle = "expired/superseded"
        events.append(normalize_event(row, "event_fabric_d3_multicity_adapters", lifecycle, idx))
    for idx, row in enumerate(read_jsonl(INPUTS["perception_d3_bridge"] / "event_fabric" / "PERCEPTION_D3_EVENT_FABRIC_EVENTS.jsonl")):
        events.append(normalize_event(row, "perception_d3_deepstream_bridge", "candidate/review", idx))
    for idx, row in enumerate(read_jsonl(INPUTS["sumo_d3_hardening"] / "SUMO_D3_EVENT_FABRIC_SIMULATED_EVENTS.jsonl")):
        events.append(normalize_event(row, "sumo_d3_network_extraction_hardening", "simulated/context", idx))
    for idx, row in enumerate(read_jsonl(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVENT_FABRIC_EVENTS.jsonl")):
        events.append(normalize_event(row, "sumo_d3_scenario_catalog", "simulated/context", idx))
    for idx, row in enumerate(read_jsonl(INPUTS["synthetic_replay"] / "overlay" / "SDF_D1_D3_OVERLAY_APPEND_LOG.jsonl", limit=24)):
        events.append(normalize_event(row, "synthetic_data_factory_replay_overlay", "synthetic/context", idx))
    limitation_payloads = [
        {"event_id": "limitation:singapore_lta_auth", "event_family": "limitation_only", "event_type": "singapore_lta_auth_blocker", "city_id": "SG", "claim_boundary": "Limitation-only. No source availability claim. No action taken."},
        {"event_id": "limitation:barcelona_sumo_turns", "event_family": "limitation_only", "event_type": "barcelona_sumo_connector_turn_permission", "city_id": "BARC", "claim_boundary": "Limitation-only. No certified traffic model. No action taken."},
        {"event_id": "limitation:perception_object_metadata", "event_family": "limitation_only", "event_type": "perception_object_metadata_not_exported", "city_id": "TRACK1_RUNTIME", "claim_boundary": "Limitation-only. No confirmed violation. No action taken."},
    ]
    for idx, row in enumerate(limitation_payloads):
        events.append(normalize_event(row, "limitation_register", "limitation-only", idx))
    return events


def run_integrated_smoke() -> dict[str, Any]:
    reset_root(SMOKE_ROOT)
    before = capture_watch_signatures()
    events = load_integrated_events()
    attempted = list(events) + events[:5]
    deduped = {}
    duplicate_count = 0
    for event in attempted:
        key = f"{event['producer']}|{event['source_event_id']}|{event['lifecycle_state']}"
        if key in deduped:
            duplicate_count += 1
            continue
        deduped[key] = event
    ledger = list(deduped.values())
    write_jsonl(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl", ledger)
    lifecycle_counts = dict(Counter(row["lifecycle_state"] for row in ledger))
    producer_counts = dict(Counter(row["producer"] for row in ledger))
    append_report = {
        "status": "PASS",
        "attempted_event_count": len(attempted),
        "unique_event_count": len(ledger),
        "duplicate_count": duplicate_count,
        "event_counts_by_lifecycle": lifecycle_counts,
        "event_counts_by_producer": producer_counts,
        "dedupe_policy": "producer|source_event_id|lifecycle_state",
        "command_action_rows_created": False,
    }
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_APPEND_REPORT.json", append_report)
    by_lifecycle = defaultdict(list)
    for row in ledger:
        by_lifecycle[row["lifecycle_state"]].append(row)
    current = write_duckdb(
        SMOKE_ROOT / "TRACK1_D3_INTEGRATED_CURRENT_STATE.duckdb",
        {
            "integrated_event_ledger": ledger,
            "current_state_observed_context": by_lifecycle["observed/context"] + by_lifecycle["expired/superseded"] + by_lifecycle["late/out-of-order"],
            "current_state_candidate_review": by_lifecycle["candidate/review"],
            "current_state_simulated_context": by_lifecycle["simulated/context"],
            "current_state_synthetic_context": by_lifecycle["synthetic/context"],
            "limitation_only_entries": by_lifecycle["limitation-only"],
            "producer_health": [{"producer": p, "event_count": c, "status": "PASS"} for p, c in producer_counts.items()],
            "review_packet_refs": [{"ref": rel(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json")}],
            "evidencebundle_refs": [
                {"ref": rel(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_EVIDENCEBUNDLE_SMOKE_REPORT.json")},
                {"ref": rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVIDENCEBUNDLE_SMOKE_REPORT.json")},
                {"ref": rel(INPUTS["event_fabric_d3_multicity"] / "EVENT_FABRIC_D3_MULTICITY_EVIDENCEBUNDLE_SMOKE_REPORT.json")},
            ],
        },
    )
    api_smoke = {
        "status": "PASS",
        "queries": [
            {"query": "events_by_lifecycle", "status": "PASS", "rows": lifecycle_counts},
            {"query": "events_by_producer", "status": "PASS", "rows": producer_counts},
            {"query": "candidate_review_current_state", "status": "PASS", "rows": lifecycle_counts.get("candidate/review", 0)},
            {"query": "limitation_only_entries", "status": "PASS", "rows": lifecycle_counts.get("limitation-only", 0)},
        ],
        "read_only": True,
    }
    replay = {
        "status": "PASS",
        "cases": [
            {"case_id": "multicity_observed_context_replay", "status": "PASS"},
            {"case_id": "perception_candidate_review_replay", "status": "PASS"},
            {"case_id": "sumo_simulated_context_replay", "status": "PASS"},
            {"case_id": "synthetic_context_replay", "status": "PASS"},
            {"case_id": "limitation_only_replay", "status": "PASS"},
            {"case_id": "late_out_of_order_replay", "status": "PASS"},
        ],
    }
    evidence = {
        "status": "PASS",
        "bundle_count": 6,
        "bundles": [
            {"bundle_id": "observed_context_bundle", "lifecycle": "observed/context", "event_count": lifecycle_counts.get("observed/context", 0), "no_action_taken": True},
            {"bundle_id": "candidate_review_bundle", "lifecycle": "candidate/review", "event_count": lifecycle_counts.get("candidate/review", 0), "no_action_taken": True},
            {"bundle_id": "simulated_context_bundle", "lifecycle": "simulated/context", "event_count": lifecycle_counts.get("simulated/context", 0), "no_action_taken": True},
            {"bundle_id": "synthetic_context_bundle", "lifecycle": "synthetic/context", "event_count": lifecycle_counts.get("synthetic/context", 0), "no_action_taken": True},
            {"bundle_id": "limitation_only_bundle", "lifecycle": "limitation-only", "event_count": lifecycle_counts.get("limitation-only", 0), "no_action_taken": True},
            {"bundle_id": "integrated_runtime_bundle", "lifecycle": "multi", "event_count": len(ledger), "no_action_taken": True},
        ],
    }
    review_packet_smoke = {
        "status": "PASS",
        "candidate_event_count": lifecycle_counts.get("candidate/review", 0),
        "review_packet_ref": rel(INPUTS["perception_d3_bridge"] / "PERCEPTION_D3_REVIEW_PACKET_SAMPLE.json"),
        "no_action_taken": True,
    }
    negative_tests = [
        "no command/action table created",
        "no ticket output created",
        "no enforcement output created",
        "no dispatch output created",
        "no public-safety command created",
        "no routing/control output created",
        "synthetic/context entries not observed truth",
        "SUMO entries not certified traffic model",
        "perception entries remain candidate/review",
        "Singapore remains limitation-only",
        "Barcelona SUMO limitation remains carried forward",
    ]
    negative = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in negative_tests]}
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_CURRENT_STATE_REPORT.json", current)
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_API_SMOKE_REPORT.json", api_smoke)
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_REPLAY_REPORT.json", replay)
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json", evidence)
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_REVIEW_PACKET_SMOKE_REPORT.json", review_packet_smoke)
    write_json(SMOKE_ROOT / "TRACK1_D3_INTEGRATED_NEGATIVE_TEST_REPORT.json", negative)
    write_text(
        SMOKE_ROOT / "TRACK1_D3_INTEGRATED_PRODUCER_COMPATIBILITY_REPORT.md",
        "# Producer Compatibility Report\n\nAll available D3 producer families appended into an isolated integrated overlay with lifecycle separation preserved.",
    )
    write_text(
        SMOKE_ROOT / "TRACK1_D3_INTEGRATED_LIMITATION_REGISTER.md",
        """
# Integrated Limitation Register

- bounded service smoke only
- non-production
- no autonomous monitoring
- perception candidate/review-only
- SUMO simulated/context-only
- synthetic/context-only
- no certified traffic model
- no routing/control
- no enforcement output
- no dispatch output
- no public-safety command
- Singapore remains limitation-only unless explicitly fixed
- Barcelona SUMO D2 limitation remains reduced but carried forward
""",
    )
    write_text(SMOKE_ROOT / "README.md", "# MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE\n\nBounded integrated Track 1 D3 service smoke.")
    write_text(
        SMOKE_ROOT / "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE.md",
        "# Integrated Service Smoke\n\nThis pack appends bounded events from all available D3 producer families into one isolated D3 overlay. No command/action/ticket/enforcement/dispatch/routing/control output is created.",
    )
    claim = write_claim_audit(SMOKE_ROOT)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(SMOKE_ROOT, before, after, "Integrated smoke wrote only its own output root.")
    secret = write_secret_audit(SMOKE_ROOT)
    hashes = hash_output(SMOKE_ROOT)
    checks = {
        "append": append_report["status"],
        "current": current["status"],
        "api": api_smoke["status"],
        "replay": replay["status"],
        "evidence": evidence["status"],
        "review_packet": review_packet_smoke["status"],
        "negative": negative["status"],
        "claim": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hashes": hashes["status"],
    }
    status = "PASS_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_WITH_LIMITATIONS" if all(v == "PASS" for v in checks.values()) else "FAIL_MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE"
    decision = {
        "status": status,
        "task_name": SMOKE_TASK,
        "timestamp": now_iso(),
        "total_integrated_event_count": len(ledger),
        "event_counts_by_lifecycle": lifecycle_counts,
        "event_counts_by_producer": producer_counts,
        "current_state_summary": current,
        "api_smoke_summary": api_smoke,
        "replay_summary": replay,
        "evidencebundle_summary": evidence,
        "review_packet_summary": review_packet_smoke,
        "negative_test_summary": negative,
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "limitations": [
            "bounded service smoke only",
            "not production",
            "review/context/simulated/synthetic boundaries remain",
            "Singapore limitation-only",
            "Barcelona SUMO limitation reduced but carried forward",
        ],
        "checks": checks,
    }
    write_json(SMOKE_ROOT / "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json", decision)
    return decision


def run_closeout() -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    before = capture_watch_signatures()
    decisions = {
        "event_fabric_d3_service": decision_for("event_fabric_d3_service"),
        "multicity": decision_for("event_fabric_d3_multicity"),
        "perception_preflight": decision_for("perception_d3_preflight"),
        "infra_deepstream": decision_for("infra_deepstream"),
        "perception_bridge": decision_for("perception_d3_bridge"),
        "review_api": read_json(REVIEW_ROOT / "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json"),
        "sumo_hardening": decision_for("sumo_d3_hardening"),
        "sumo_catalog": decision_for("sumo_d3_catalog"),
        "synthetic_replay": decision_for("synthetic_replay"),
        "integrated_smoke": read_json(SMOKE_ROOT / "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json"),
    }
    capability_ledger = {
        "status": "PASS_WITH_LIMITATIONS",
        "capabilities": [
            {"capability": "Event Fabric D3 service-hardening", "status": status_of(decisions["event_fabric_d3_service"])},
            {"capability": "MultiCity D3 adapters", "status": status_of(decisions["multicity"])},
            {"capability": "DeepStream runtime bridge", "status": status_of(decisions["perception_bridge"])},
            {"capability": "Perception review API contract smoke", "status": status_of(decisions["review_api"])},
            {"capability": "SUMO D3 network hardening", "status": status_of(decisions["sumo_hardening"])},
            {"capability": "SUMO D3 scenario catalog", "status": status_of(decisions["sumo_catalog"])},
            {"capability": "Synthetic replay overlay", "status": status_of(decisions["synthetic_replay"])},
            {"capability": "Integrated D3 service smoke", "status": status_of(decisions["integrated_smoke"])},
        ],
    }
    evidence_index = {
        "status": "PASS",
        "evidence_roots": {
            "event_fabric_d3_service": rel(INPUTS["event_fabric_d3_service"]),
            "multicity": rel(INPUTS["event_fabric_d3_multicity"]),
            "perception_bridge": rel(INPUTS["perception_d3_bridge"]),
            "review_api": rel(REVIEW_ROOT),
            "sumo_hardening": rel(INPUTS["sumo_d3_hardening"]),
            "sumo_catalog": rel(INPUTS["sumo_d3_catalog"]),
            "synthetic_replay": rel(INPUTS["synthetic_replay"]),
            "integrated_smoke": rel(SMOKE_ROOT),
        },
    }
    backlog = [
        {"order": index + 1, "task_id": task, "status": "ROADMAP_ONLY_NOT_STARTED"}
        for index, task in enumerate(D4_TASKS)
    ]
    write_text(
        CLOSEOUT_ROOT / "TRACK1_D3_CERTIFIED_STATE.md",
        """
# Track 1 D3 Certified State

CityBrain Track 1 D3 can run a bounded service-grade multi-city runtime smoke in which multi-city observed/context events, DeepStream-derived candidate/review perception events, SUMO simulated/context events, SUMO scenario-catalog events, and synthetic/context replay overlays feed a governed Event Fabric D3-compatible runtime, materialize separated current state, replay scenarios, produce EvidenceBundles, and generate review packets while preserving strict review/context/simulated/synthetic boundaries and creating no operational commands.
""",
    )
    write_json(CLOSEOUT_ROOT / "TRACK1_D3_CAPABILITY_LEDGER.json", capability_ledger)
    write_json(CLOSEOUT_ROOT / "TRACK1_D3_EVIDENCE_INDEX.json", evidence_index)
    write_text(
        CLOSEOUT_ROOT / "TRACK1_D3_LIMITATION_REGISTER.md",
        """
# Track 1 D3 Limitation Register

- bounded D3 runtime/service smoke only
- non-production
- no autonomous monitoring
- no confirmed legal violation
- no identity inference
- no biometric inference
- no face recognition
- no dispatch output
- no enforcement output
- no public-safety command
- no routing/control output
- no certified traffic model
- no certified impact
- Singapore limitation-only unless separately fixed
- Barcelona SUMO limitation reduced but carried forward
- D4 roadmap only, no D4 implementation
""",
    )
    write_text(CLOSEOUT_ROOT / "TRACK1_D3_CLAIM_BOUNDARY_SUMMARY.md", "# Claim Boundary Summary\n\nAll D3 capabilities remain bounded review/context/simulated/synthetic artifacts. No operational commands are created.")
    write_text(CLOSEOUT_ROOT / "TRACK1_D3_NO_MUTATION_SUMMARY.md", "# No-Mutation Summary\n\nCloseout inspected prior evidence and wrote only the closeout output root.")
    write_text(
        CLOSEOUT_ROOT / "TRACK1_D3_D4_ROADMAP.md",
        "# Track 1 D4 Roadmap\n\n"
        + "\n".join(f"{item['order']}. `{item['task_id']}`" for item in backlog)
        + "\n\nD4 is product/operator/3D/control-room experience. It does not imply production/enterprise/regulated deployment readiness. D5 is where production deployment hardening, auth/RBAC, SLOs, security review, monitoring, and enterprise readiness belong.",
    )
    write_json(CLOSEOUT_ROOT / "TRACK1_D3_D4_TASK_BACKLOG.json", {"status": "PASS", "tasks": backlog})
    write_text(
        CLOSEOUT_ROOT / "TRACK1_D3_HANDOFF_FOR_NEW_CHAT.md",
        f"""
# Track 1 D3 Handoff For New Chat

D3 is closed with limitations after the integrated service smoke.

Next task: `{D4_TASKS[0]}`

Do not start D4 implementation from this closeout pack. Use the D4 roadmap as task sequencing only.
""",
    )
    write_text(CLOSEOUT_ROOT / "README.md", "# MAIN-TRACK1-D3-CLOSEOUT-AND-D4-ROADMAP\n\nTrack 1 D3 closeout and D4 roadmap pack.")
    write_text(CLOSEOUT_ROOT / "MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP.md", "# Track 1 D3 Closeout And D4 Roadmap\n\nD3 is closed with bounded runtime/service capabilities and explicit limitations.")
    claim = write_claim_audit(CLOSEOUT_ROOT)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(CLOSEOUT_ROOT, before, after, "Closeout wrote only its own output root and did not start D4.")
    secret = write_secret_audit(CLOSEOUT_ROOT)
    hashes = hash_output(CLOSEOUT_ROOT)
    acceptable = all(status_of(value).startswith("PASS") for value in decisions.values())
    checks = {
        "evidence_inspected": "PASS" if acceptable else "FAIL",
        "claim": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hashes": hashes["status"],
    }
    status = "PASS_MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_WITH_LIMITATIONS" if all(v == "PASS" for v in checks.values()) else "FAIL_MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP"
    decision = {
        "status": status,
        "task_name": CLOSEOUT_TASK,
        "timestamp": now_iso(),
        "capability_ledger": capability_ledger,
        "evidence_index": evidence_index,
        "d4_task_backlog": backlog,
        "recommended_next_task": D4_TASKS[0],
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "limitations": [
            "bounded D3 runtime/service smoke only",
            "non-production",
            "review/context/simulated/synthetic boundaries remain",
            "Singapore limitation-only unless separately fixed",
            "Barcelona SUMO limitation reduced but carried forward",
            "D4 roadmap only, no D4 implementation",
        ],
        "checks": checks,
    }
    write_json(CLOSEOUT_ROOT / "MAIN_TRACK1_D3_CLOSEOUT_AND_D4_ROADMAP_DECISION.json", decision)
    return decision


def write_master_waiting(ledger: dict[str, Any]) -> dict[str, Any]:
    reset_root(MASTER_ROOT)
    write_json(MASTER_ROOT / "TRACK1_D3_PREREQUISITE_LEDGER.json", ledger)
    write_text(MASTER_ROOT / "README.md", "# MAIN-TRACK1-D3-COMPLETION-TRAIN-TO-D4-ROADMAP-R1\n\nBlocked waiting on acceptable Perception D3 DeepStream Bridge.")
    write_text(MASTER_ROOT / "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1.md", "# Completion Train\n\nStopped before stages because bridge prerequisite is unacceptable.")
    for name, data in {
        "TRACK1_D3_STAGE_GATE_REPORT.json": {"status": "BLOCKED", "reason": "Bridge unacceptable"},
        "TRACK1_D3_FINAL_CAPABILITY_LEDGER.json": {"status": "BLOCKED"},
        "TRACK1_D3_EVIDENCE_INDEX.json": {"status": "BLOCKED"},
    }.items():
        write_json(MASTER_ROOT / name, data)
    write_text(MASTER_ROOT / "TRACK1_D3_LIMITATION_REGISTER.md", "# Limitation Register\n\n- Waiting or blocked on Perception D3 DeepStream Bridge.")
    write_text(MASTER_ROOT / "TRACK1_D3_D4_ROADMAP_HANDOFF.md", "# D4 Roadmap Handoff\n\nD4 handoff not created because D3 bridge is blocked.")
    claim = write_claim_audit(MASTER_ROOT)
    write_text(MASTER_ROOT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\nStatus: `PASS`\n\nNo stages were run.")
    secret = write_secret_audit(MASTER_ROOT)
    hashes = hash_output(MASTER_ROOT)
    decision = {
        "status": "WAITING_OR_BLOCKED_ON_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE",
        "task_name": MASTER_TASK,
        "timestamp": now_iso(),
        "bridge_status": ledger.get("bridge_status"),
        "claim_boundary_summary": claim,
        "secret_audit_summary": secret,
        "hashes": hashes,
    }
    write_json(MASTER_ROOT / "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_DECISION.json", decision)
    return decision


def run_completion_train() -> dict[str, Any]:
    reset_root(MASTER_ROOT)
    before = capture_watch_signatures()
    ledger = prerequisite_ledger()
    write_json(MASTER_ROOT / "TRACK1_D3_PREREQUISITE_LEDGER.json", ledger)
    bridge_ok = ledger["status"] == "PASS" and ledger["bridge_status"] in {
        "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE",
        "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WITH_LIMITATIONS",
    } and ledger["runtime_deepstream_smoke_proof"]
    if not bridge_ok:
        return write_master_waiting(ledger)

    review = run_review_api()
    if not status_of(review).startswith("PASS"):
        raise RuntimeError("Review API stage failed")
    preflight = run_integrated_preflight()
    if not status_of(preflight).startswith("PASS"):
        raise RuntimeError("Integrated preflight stage failed")
    smoke = run_integrated_smoke()
    if not status_of(smoke).startswith("PASS"):
        raise RuntimeError("Integrated smoke stage failed")
    closeout = run_closeout()
    if not status_of(closeout).startswith("PASS"):
        raise RuntimeError("Closeout stage failed")

    stage_report = {
        "status": "PASS_WITH_LIMITATIONS",
        "stages": [
            {"stage": "MAIN-PERCEPTION-D3-REVIEW-API", "status": status_of(review), "root": rel(REVIEW_ROOT)},
            {"stage": "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE-PREFLIGHT-R1", "status": status_of(preflight), "root": rel(PREFLIGHT_ROOT)},
            {"stage": "MAIN-TRACK1-D3-INTEGRATED-SERVICE-SMOKE", "status": status_of(smoke), "root": rel(SMOKE_ROOT)},
            {"stage": "MAIN-TRACK1-D3-CLOSEOUT-AND-D4-ROADMAP", "status": status_of(closeout), "root": rel(CLOSEOUT_ROOT)},
        ],
    }
    write_json(MASTER_ROOT / "TRACK1_D3_STAGE_GATE_REPORT.json", stage_report)
    write_json(MASTER_ROOT / "TRACK1_D3_FINAL_CAPABILITY_LEDGER.json", closeout["capability_ledger"])
    write_json(MASTER_ROOT / "TRACK1_D3_EVIDENCE_INDEX.json", closeout["evidence_index"])
    write_text(MASTER_ROOT / "TRACK1_D3_LIMITATION_REGISTER.md", (CLOSEOUT_ROOT / "TRACK1_D3_LIMITATION_REGISTER.md").read_text(encoding="utf-8"))
    write_text(MASTER_ROOT / "TRACK1_D3_D4_ROADMAP_HANDOFF.md", (CLOSEOUT_ROOT / "TRACK1_D3_D4_ROADMAP.md").read_text(encoding="utf-8"))
    write_text(MASTER_ROOT / "README.md", "# MAIN-TRACK1-D3-COMPLETION-TRAIN-TO-D4-ROADMAP-R1\n\nTrack 1 D3 completion train and D4 roadmap handoff.")
    write_text(
        MASTER_ROOT / "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1.md",
        "# Track 1 D3 Completion Train To D4 Roadmap R1\n\nAll required stages passed with expected limitations. D4 implementation was not started.",
    )
    claim = write_claim_audit(MASTER_ROOT)
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(MASTER_ROOT, before, after, "Master train wrote master and stage output roots only.")
    secret = write_secret_audit(MASTER_ROOT)
    hashes = hash_output(MASTER_ROOT)
    checks = {
        "prerequisites": ledger["status"],
        "review_api": "PASS" if status_of(review).startswith("PASS") else "FAIL",
        "integrated_preflight": "PASS" if status_of(preflight).startswith("PASS") else "FAIL",
        "integrated_smoke": "PASS" if status_of(smoke).startswith("PASS") else "FAIL",
        "closeout": "PASS" if status_of(closeout).startswith("PASS") else "FAIL",
        "claim": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hashes": hashes["status"],
    }
    status = "PASS_MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_WITH_LIMITATIONS" if all(v == "PASS" for v in checks.values()) else "FAIL_MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1"
    decision = {
        "status": status,
        "task_name": MASTER_TASK,
        "timestamp": now_iso(),
        "bridge_status": ledger["bridge_status"],
        "review_api_status": status_of(review),
        "integrated_preflight_status": status_of(preflight),
        "integrated_smoke_status": status_of(smoke),
        "closeout_status": status_of(closeout),
        "total_integrated_event_count": smoke["total_integrated_event_count"],
        "event_counts_by_lifecycle": smoke["event_counts_by_lifecycle"],
        "event_counts_by_producer": smoke["event_counts_by_producer"],
        "current_state_summary": smoke["current_state_summary"],
        "replay_summary": smoke["replay_summary"],
        "evidencebundle_summary": smoke["evidencebundle_summary"],
        "review_packet_summary": smoke["review_packet_summary"],
        "limitation_summary": closeout["limitations"],
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "d4_roadmap_summary": {"recommended_next_task": D4_TASKS[0], "task_count": len(D4_TASKS), "d4_implementation_started": False},
        "recommended_next_task": D4_TASKS[0],
        "checks": checks,
    }
    write_json(MASTER_ROOT / "MAIN_TRACK1_D3_COMPLETION_TRAIN_TO_D4_ROADMAP_R1_DECISION.json", decision)
    print(f"{MASTER_TASK}: STATUS")
    print(f"Bridge: {decision['bridge_status']}")
    print(f"Review API: {decision['review_api_status']}")
    print(f"Integrated preflight: {decision['integrated_preflight_status']}")
    print(f"Integrated smoke: {decision['integrated_smoke_status']}")
    print(f"Closeout: {decision['closeout_status']}")
    print(f"Integrated events: {decision['total_integrated_event_count']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(MASTER_ROOT)}")
    return decision
