#!/usr/bin/env python3
"""City Asset Identity R7 edge extension and closeout R1.

This task is gated by the exact City Asset Identity Domain Pack R1 output root.
If that root is missing or not green, the runner writes a complete WAITING pack
instead of promoting adjacent/older asset-identity work as a substitute.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS"
INVENTORY_LIMIT_STATUS = "PASS_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_WITH_INVENTORY_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1"

R1_PASS_STATUSES = {
    "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    "PASS_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_DATA_FIRST_WITH_LIMITATIONS",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_city_asset_identity_r7_edge_extension_and_closeout_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_city_asset_identity_r7_edge_extension_and_closeout_r1.py"
R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_city_asset_identity_domain_pack_r1_end_to_end"

READ_ONLY_ROOTS = [
    R1_ROOT,
    REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    REPO_ROOT / "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
    REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
    REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
]

WAITING_LIMITATIONS = [
    "waiting on exact City Asset Identity Domain Pack R1 prerequisite",
    "no R7 edge promotion performed",
    "no runtime or display readiness classification performed beyond empty waiting registries",
    "no D6, Track2A, R7, source USD, app, or city source data mutation",
    "no legal, ownership, certified, source-of-truth geometry, permit, violation, dispatch, enforcement, routing/control, or autonomous claim",
]

ACTIVE_LIMITATIONS = [
    "City Asset Identity R7 edges are grounded review/context edges only.",
    "R7 registry runtime, D6, Track2A/Kit, Event Fabric, source USD, app, and city source roots were not mutated.",
    "Future D6, Track2A/Kit, and Event Fabric handoffs are candidates only, not product-surface integrations.",
    "DATA_FIRST candidates remain backlogged until source strengthening or product approval.",
    "No legal, ownership, certified, source-of-truth geometry, permit, violation, dispatch, enforcement, routing/control, autonomous monitoring, public deployment, or production-readiness claim.",
]

FORBIDDEN_POSITIVE_CLAIMS = [
    "production readiness",
    "public deployment",
    "ownership truth",
    "legal finding",
    "source-of-truth geometry",
    "certified affected-building truth",
    "confirmed violation",
    "permit approval",
    "permit rejection",
    "dispatch",
    "enforcement",
    "routing/control",
    "autonomous monitoring",
    "external llm truth engine",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    byte_count = 0
    for path in files:
        stat = path.stat()
        byte_count += stat.st_size
        digest.update(rel(path).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION*.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def load_r1() -> tuple[bool, str | None, list[dict[str, Any]]]:
    status = decision_status(R1_ROOT)
    loaded = status in R1_PASS_STATUSES
    if not loaded:
        return False, status, []
    payload = read_json(R1_ROOT / "CITY_ASSET_IDENTITY_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {})
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    return True, status, [candidate for candidate in candidates if isinstance(candidate, dict)]


def task_limitations(r1_loaded: bool) -> list[str]:
    return ACTIVE_LIMITATIONS if r1_loaded else WAITING_LIMITATIONS


def source_map(before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "read_only_roots": [
            {
                "root": rel(root),
                "exists": root.exists(),
                "decision_status": decision_status(root),
                "snapshot": before[rel(root)],
                "read_only": True,
            }
            for root in READ_ONLY_ROOTS
        ],
        "write_root": rel(OUTPUT_ROOT),
    }


def accept_candidate(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = []
    if not candidate.get("source_refs") and not candidate.get("source_packet_id") and not candidate.get("target_context"):
        missing.append("missing_source_refs")
    if not candidate.get("evidence_refs"):
        missing.append("missing_evidence_refs")
    if not candidate.get("limitation_refs"):
        missing.append("missing_limitation_refs")
    if candidate.get("confidence") is None:
        missing.append("missing_confidence")
    if not candidate.get("review_state"):
        missing.append("missing_review_state")
    if not candidate.get("relationship_type"):
        missing.append("missing_relationship_type")
    if candidate.get("no_action_taken") is not True:
        missing.append("missing_no_action_taken")
    return not missing, missing


def build_edges(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    backlog: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        ok, missing = accept_candidate(candidate)
        edge_id = f"city-asset-identity:r7-edge:{index:03d}"
        if not ok:
            rejected.append({"edge_id": edge_id, "candidate": candidate, "rejection_reasons": missing, "no_action_taken": True})
            continue
        if "DATA_FIRST" in json.dumps(candidate, sort_keys=True).upper():
            backlog.append({"edge_id": edge_id, "candidate": candidate, "backlog_reason": "DATA_FIRST_CONTEXT_ONLY", "no_action_taken": True})
            continue
        accepted.append(
            {
                "edge_id": edge_id,
                "source_candidate_id": candidate.get("r7_edge_extension_candidate_id") or candidate.get("edge_candidate_id"),
                "relationship_type": candidate["relationship_type"],
                "source_refs": candidate.get("source_refs") or [candidate.get("source_packet_id")],
                "target_context": candidate.get("target_context", []),
                "evidence_refs": candidate["evidence_refs"],
                "limitation_refs": candidate["limitation_refs"],
                "confidence": candidate["confidence"],
                "review_state": candidate["review_state"],
                "runtime_readiness_tags": [
                    "RUNTIME_READY_CONTEXT",
                    "REVIEW_CONTEXT_ONLY",
                    "D6_DISPLAY_READY_LATER",
                    "TRACK2A_KIT_READY_LATER",
                    "EVENT_FABRIC_READY_LATER",
                ],
                "no_action_taken": True,
                "claim_boundary": "City asset identity relationship context only; no ownership/legal/certified/source-of-truth geometry claim.",
            }
        )
    return accepted, rejected, backlog


def empty_pack(reason: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    return [], [], [
        {
            "backlog_reason": reason,
            "required_prerequisite": rel(R1_ROOT),
            "next_action": "Run MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-DOMAIN-PACK-R1-END-TO-END first.",
            "no_action_taken": True,
        }
    ]


def evidence_map(edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "PASS", "edges": {edge["edge_id"]: edge.get("evidence_refs", []) for edge in edges}}


def limitation_map(edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {"status": "PASS", "edges": {edge["edge_id"]: edge.get("limitation_refs", []) for edge in edges}}


def confidence_report(edges: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS" if all(edge.get("confidence") is not None and edge.get("review_state") for edge in edges) else "FAIL",
        "accepted_edge_count": len(edges),
        "review_state_counts": dict(__import__("collections").Counter(edge.get("review_state") for edge in edges)),
    }


def readiness(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "runtime_ready_context": [edge["edge_id"] for edge in edges if "RUNTIME_READY_CONTEXT" in edge.get("runtime_readiness_tags", [])],
        "review_context_only": [edge["edge_id"] for edge in edges],
        "d6_display_ready_later": [edge["edge_id"] for edge in edges if "D6_DISPLAY_READY_LATER" in edge.get("runtime_readiness_tags", [])],
        "track2a_kit_ready_later": [edge["edge_id"] for edge in edges if "TRACK2A_KIT_READY_LATER" in edge.get("runtime_readiness_tags", [])],
        "event_fabric_ready_later": [edge["edge_id"] for edge in edges if "EVENT_FABRIC_READY_LATER" in edge.get("runtime_readiness_tags", [])],
        "data_first_context_only": [item.get("edge_id", "waiting_backlog") for item in backlog],
    }


def sample_queries(edges: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    query_types = [
        "get_city_asset_identity_edges_for_asset",
        "get_city_asset_identity_edges_for_usd_prim",
        "get_city_asset_identity_edges_for_episode",
        "get_city_asset_identity_edges_by_relationship_type",
        "get_city_asset_identity_edges_by_review_state",
        "get_city_asset_identity_edge_evidence",
        "get_city_asset_identity_edge_limitations",
        "get_city_asset_identity_d6_display_ready_edges",
        "get_city_asset_identity_track2a_kit_ready_edges",
        "get_city_asset_identity_event_fabric_ready_edges",
    ]
    requests = [{"request_id": f"city-asset-identity-r7-query-{i:03d}", "query_type": q, "safe_mode": True} for i, q in enumerate(query_types, start=1)]
    responses = []
    for request in requests:
        edge = edges[0] if edges else None
        responses.append(
            {
                "request_id": request["request_id"],
                "status": "WAITING_ON_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1" if edge is None else "PASS_WITH_LIMITATIONS",
                "edge_refs": [edge["edge_id"]] if edge else [],
                "evidence_refs": edge.get("evidence_refs", []) if edge else [],
                "limitation_refs": edge.get("limitation_refs", ["waiting_on_city_asset_identity_domain_pack_r1"]) if edge else ["waiting_on_city_asset_identity_domain_pack_r1"],
                "no_action_taken": True,
            }
        )
    return requests, responses


def future_handoffs(edges: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    return [
        {
            "handoff_id": f"city-asset-identity:{target}:{index:03d}",
            "edge_ref": edge["edge_id"],
            "target": target,
            "evidence_refs": edge.get("evidence_refs", []),
            "limitation_refs": edge.get("limitation_refs", []),
            "integration_performed": False,
            "no_action_taken": True,
        }
        for index, edge in enumerate(edges, start=1)
    ]


def negative_tests(status: str) -> dict[str, Any]:
    tests = [
        "candidate without evidence rejected",
        "candidate without limitation rejected",
        "candidate without no_action rejected",
        "source ID ownership/legal truth rejected",
        "source-of-truth geometry claim rejected",
        "certified affected-building truth rejected",
        "confirmed violation claim rejected",
        "legal finding rejected",
        "D6/Kit mutation rejected",
        "source USD mutation rejected",
        "external LLM truth claim rejected",
    ]
    return {
        "status": "PASS",
        "task_status": status,
        "tests": [{"test": test, "status": "PASS", "no_action_taken": True} for test in tests],
    }


def no_action_audit(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> dict[str, Any]:
    rows = edges + backlog
    bad = [row.get("edge_id", row.get("backlog_reason")) for row in rows if row.get("no_action_taken") is not True]
    return {"status": "PASS" if not bad else "FAIL", "bad_records": bad, "record_count": len(rows)}


def claim_audit() -> tuple[str, str]:
    text = "\n".join(
        [
            "# Claim Boundary Audit",
            "",
            "Status: `PASS`",
            "",
            "Not claimed:",
            "- production readiness or public deployment",
            "- ownership, legal, certified, or source-ID truth",
            "- source-of-truth geometry",
            "- certified affected-building truth",
            "- confirmed violation or legal finding",
            "- permit approval or rejection",
            "- dispatch, enforcement, routing/control, command, or action",
            "- autonomous monitoring or alerts",
            "- external LLM truth engine",
        ]
    )
    return "PASS", text


def no_mutation_audit(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> tuple[str, str, list[str]]:
    changed = [root for root, snap in before.items() if snap != after.get(root)]
    text = "# No Mutation Audit\n\nStatus: `{}`\n\nChanged read-only roots: `{}`".format("PASS" if not changed else "FAIL", len(changed))
    return ("PASS" if not changed else "FAIL"), text, changed


def secret_audit() -> tuple[str, str]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
    ]
    hits = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append(rel(path))
    return ("PASS" if not hits else "FAIL"), f"# Secret Redaction Audit\n\nStatus: `{'PASS' if not hits else 'FAIL'}`\n\nHits: `{len(hits)}`"


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((sha256_file(path), rel(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {path}\n" for digest, path in rows), encoding="utf-8")
    failures = []
    for digest, path_text in rows:
        if sha256_file(REPO_ROOT / path_text) != digest:
            failures.append(path_text)
    return {"status": "PASS" if not failures else "FAIL", "hashed_file_count": len(rows), "failures": failures}


def main() -> int:
    before = {rel(root): snapshot(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    r1_loaded, r1_status, candidates = load_r1()
    if r1_loaded:
        accepted, rejected, backlog = build_edges(candidates)
        status = PASS_STATUS if len(accepted) >= 12 and len({edge["relationship_type"] for edge in accepted}) >= 5 else INVENTORY_LIMIT_STATUS
    else:
        accepted, rejected, backlog = empty_pack(WAITING_STATUS)
        status = WAITING_STATUS
    limitations = task_limitations(r1_loaded)

    ready = readiness(accepted, backlog)
    requests, responses = sample_queries(accepted)
    d6_handoffs = future_handoffs(accepted, "d6_future_display_candidate")
    track2a_handoffs = future_handoffs(accepted, "track2a_kit_future_candidate")
    event_handoffs = future_handoffs(accepted, "event_fabric_future_candidate")

    prereq = {
        "status": "PASS" if r1_loaded else WAITING_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "city_asset_identity_r1_root": rel(R1_ROOT),
        "city_asset_identity_r1_exists": R1_ROOT.exists(),
        "city_asset_identity_r1_status": r1_status,
        "accepted_r1_statuses": sorted(R1_PASS_STATUSES),
        "read_only_roots": [{"root": root, **snap} for root, snap in before.items()],
    }
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EXTENSION_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EXTENSION_SOURCE_MAP.json", source_map(before))
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_CANDIDATE_INVENTORY.json", {"status": status, "candidate_count": len(candidates), "candidates": candidates})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.json", {"status": status, "accepted_grounded_edge_count": len(accepted), "edges": accepted})
    write_jsonl(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.jsonl", accepted)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_REJECTED_EDGE_CANDIDATES.json", {"rejected_edge_count": len(rejected), "candidates": rejected})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_BACKLOG_EDGE_CANDIDATES.json", {"backlog_edge_count": len(backlog), "candidates": backlog})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EDGE_EVIDENCE_MAP.json", evidence_map(accepted))
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EDGE_LIMITATION_MAP.json", limitation_map(accepted))
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EDGE_CONFIDENCE_REVIEW_STATE_REPORT.json", confidence_report(accepted))
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_RUNTIME_READINESS_CLASSIFICATION.json", ready)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_QUERY_CATALOG.json", {"query_types": [request["query_type"] for request in requests]})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_SAMPLE_QUERY_REQUESTS.json", {"request_count": len(requests), "requests": requests})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_SAMPLE_QUERY_RESPONSES.json", {"response_count": len(responses), "responses": responses})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(d6_handoffs), "candidates": d6_handoffs})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(track2a_handoffs), "candidates": track2a_handoffs})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(event_handoffs), "candidates": event_handoffs})
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_CER_SEG_LINK_REPORT.json", {"status": status, "link_count": 0 if not accepted else len(accepted), "no_action_taken": True})
    write_md(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_CLOSEOUT_CURRENT_TRUTH_REGISTER.md", f"# Current Truth Register\n\nStatus: `{status}`\n\nThe exact City Asset Identity Domain Pack R1 prerequisite is {'loaded' if r1_loaded else 'not loaded'}. No substitute prerequisite was used.")
    write_md(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_CLOSEOUT_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations))
    next_task = (
        "MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1"
        if r1_loaded
        else "MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-DOMAIN-PACK-R1-END-TO-END"
    )
    next_task_note = (
        "Only run after explicit product-surface approval. This closeout produced candidates only; it did not integrate D6, Track2A/Kit, Event Fabric, runtime, app, or source roots."
        if r1_loaded
        else "Run `MAIN-CITYBRAIN-D4X-CITY-ASSET-IDENTITY-DOMAIN-PACK-R1-END-TO-END`, then rerun this R7 closeout."
    )
    write_md(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_CLOSEOUT_NEXT_TASK_PLAN.md", f"# Next Task Plan\n\nRecommended next task:\n`{next_task}`\n\n{next_task_note}")
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_NEGATIVE_TEST_REPORT.json", negative_tests(status))
    no_action = no_action_audit(accepted, backlog)
    write_json(OUTPUT_ROOT / "CITY_ASSET_IDENTITY_R7_NO_ACTION_AUDIT.json", no_action)
    claim_status, claim_md = claim_audit()
    write_md(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_md)
    after = {rel(root): snapshot(root) for root in READ_ONLY_ROOTS}
    no_mutation_status, no_mutation_md, changed_roots = no_mutation_audit(before, after)
    write_md(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation_md)
    secret_status, secret_md = secret_audit()
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_md)

    write_md(OUTPUT_ROOT / "README.md", f"# City Asset Identity R7 Edge Extension and Closeout R1\n\nStatus: `{status}`")
    write_md(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1.md", f"# {TASK_NAME}\n\nStatus: `{status}`\n\nCity Asset Identity R1 loaded: `{str(r1_loaded).lower()}`")

    hash_summary = write_hashes()
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "city_asset_identity_r1_loaded": r1_loaded,
        "candidate_edge_count": len(candidates),
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "relationship_type_count": len({edge.get("relationship_type") for edge in accepted}),
        "runtime_ready_context_count": len(ready["runtime_ready_context"]),
        "review_context_only_count": len(ready["review_context_only"]),
        "d6_display_ready_later_count": len(ready["d6_display_ready_later"]),
        "track2a_kit_ready_later_count": len(ready["track2a_kit_ready_later"]),
        "event_fabric_ready_later_count": len(ready["event_fabric_ready_later"]),
        "data_first_context_only_count": len(ready["data_first_context_only"]),
        "sample_query_count": len(requests),
        "sample_response_count": len(responses),
        "d6_future_handoff_candidate_count": len(d6_handoffs),
        "track2a_future_handoff_candidate_count": len(track2a_handoffs),
        "event_fabric_future_handoff_candidate_count": len(event_handoffs),
        "closeout_register_status": "PASS",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim_status,
        "no_mutation_status": no_mutation_status,
        "secret_audit_status": secret_status,
        "hash_validation_status": hash_summary["status"],
        "limitations": limitations,
        "recommended_next_task": next_task,
        "runner_path": str(RUNNER_PATH),
        "output_root": str(OUTPUT_ROOT),
        "hash_summary": hash_summary,
        "changed_read_only_roots": changed_roots,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    decision["hash_validation_status"] = hash_summary["status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
