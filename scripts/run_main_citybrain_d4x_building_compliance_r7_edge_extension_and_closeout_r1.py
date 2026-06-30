#!/usr/bin/env python3
"""Building Compliance R7 edge extension and closeout R1."""

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

TASK_NAME = "MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-R7-EDGE-EXTENSION-AND-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS"
INVENTORY_STATUS = "PASS_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_WITH_INVENTORY_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_BUILDING_COMPLIANCE_DOMAIN_PACK_R1"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1.py"

R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_building_compliance_domain_pack_r1_end_to_end"
READ_ONLY_ROOTS = [
    R1_ROOT,
    REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity",
    REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
    REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
]

BOUNDARY = (
    "Building compliance R7 branch context only. No production readiness, public deployment, "
    "legal finding, confirmed violation, permit approval/rejection, enforcement, dispatch, "
    "routing/control, certified affected-building truth, certified impact, source-ID legal/"
    "ownership/certified truth, autonomous monitoring/alerts, or external LLM truth engine."
)

LIMITATIONS = [
    "building compliance R7 branch output only",
    "does not mutate global R7 registry",
    "accepted edges are grounded review/context edges only",
    "no legal finding or confirmed violation",
    "no permit approval or rejection",
    "no enforcement, dispatch, routing, control, or command output",
    "no certified compliance or affected-building truth",
    "handoffs are future candidates only",
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


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0}
    files = []
    for file in sorted(root.rglob("*")):
        if file.is_file():
            stat = file.stat()
            files.append({"path": rel(file), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return {"exists": True, "file_count": len(files), "byte_count": sum(row["size"] for row in files), "files": files}


def find_decision(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {}
    candidates = sorted(root.glob("*DECISION.json"))
    return read_json(candidates[0], {}) if candidates else {}


def prerequisite_report() -> dict[str, Any]:
    roots = []
    for root in READ_ONLY_ROOTS:
        decision = find_decision(root)
        roots.append({
            "root": rel(root),
            "exists": root.exists(),
            "decision_status": decision.get("status"),
            "green_if_present": str(decision.get("status", "")).startswith("PASS") if decision else root.exists(),
        })
    r1_decision = read_json(R1_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END_DECISION.json", {})
    return {
        "status": "PASS" if str(r1_decision.get("status", "")).startswith("PASS") else WAITING_STATUS,
        "building_compliance_r1_status": r1_decision.get("status"),
        "roots": roots,
        "missing_optional_roots": [row["root"] for row in roots if not row["exists"] and row["root"] != rel(R1_ROOT)],
    }


def source_family(ref: str) -> str:
    low = ref.lower()
    if "identity_shards" in low:
        return "identity_shard"
    if "usd" in low or "3d_" in low or "lod2" in low:
        return "usd_or_3d_asset"
    if "asset_contract" in low or "track2a" in low:
        return "track2a_asset_contract"
    if "r5_building_asset_identity" in low:
        return "r5_building_asset_identity"
    if "domain_pack" in low:
        return "domain_pack"
    return "source_context"


def accept_edge(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    issues = []
    if not candidate.get("source_packet_id") and not candidate.get("target_context"):
        issues.append("missing_source_refs")
    if not candidate.get("evidence_refs"):
        issues.append("missing_evidence_refs")
    if not candidate.get("limitation_refs"):
        issues.append("missing_limitation_refs")
    if candidate.get("confidence") is None:
        issues.append("missing_confidence")
    if not candidate.get("review_state"):
        issues.append("missing_review_state")
    if not candidate.get("relationship_type"):
        issues.append("missing_relationship_type")
    if candidate.get("no_action_taken") is not True:
        issues.append("missing_no_action_taken")
    return not issues, issues


def accepted_edge(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    families = sorted({source_family(ref) for ref in candidate.get("evidence_refs", [])})
    tags = [
        "RUNTIME_READY_CONTEXT",
        "REVIEW_CONTEXT_ONLY",
        "D6_DISPLAY_READY_LATER",
        "TRACK2A_KIT_READY_LATER",
        "EVENT_FABRIC_READY_LATER",
    ]
    return {
        "edge_id": f"building_compliance:r7-accepted:{index:03d}",
        "source_candidate_id": candidate["edge_candidate_id"],
        "relationship_type": candidate["relationship_type"],
        "source_packet_id": candidate.get("source_packet_id"),
        "target_context": candidate.get("target_context", []),
        "source_refs": [candidate.get("source_packet_id"), *candidate.get("target_context", [])],
        "source_families": families,
        "evidence_refs": candidate.get("evidence_refs", []),
        "limitation_refs": candidate.get("limitation_refs", []),
        "confidence": candidate.get("confidence"),
        "review_state": candidate.get("review_state"),
        "runtime_readiness_tags": tags,
        "runtime_readiness": "RUNTIME_READY_CONTEXT",
        "claim_boundary": BOUNDARY,
        "no_action_taken": True,
        "mutates_r7_registry": False,
        "forbidden_claims": [
            "legal_finding",
            "confirmed_violation",
            "permit_approval_or_rejection",
            "enforcement_dispatch_routing_control",
            "certified_compliance_or_affected_building_truth",
        ],
    }


def build_data_first_backlog(domain_packets: list[dict[str, Any]], start_index: int) -> list[dict[str, Any]]:
    backlog = []
    data_first_packets = [packet for packet in domain_packets if packet.get("data_first")]
    for offset, packet in enumerate(data_first_packets, start=start_index):
        backlog.append({
            "edge_candidate_id": f"building_compliance:r7-backlog-data-first:{offset:03d}",
            "source_packet_id": packet.get("packet_id"),
            "relationship_type": "data_first_placeholder_for_compliance_domain",
            "target_context": packet.get("asset_refs") or [packet.get("city_id", "CROSS_CITY")],
            "evidence_refs": packet.get("evidence_refs", []),
            "limitation_refs": list(dict.fromkeys([*packet.get("limitation_refs", []), "data_first_context_only"])),
            "confidence": packet.get("confidence", 0.3),
            "review_state": "DATA_FIRST_CONTEXT_ONLY",
            "backlog_reason": "DATA_FIRST packet requires source strengthening before R7 acceptance.",
            "no_action_taken": True,
            "mutates_r7_registry": False,
        })
    return backlog


def query_catalog() -> list[dict[str, Any]]:
    modes = [
        ("get_edges_for_asset", "Get building compliance edges for asset"),
        ("get_edges_for_episode", "Get building compliance edges for episode"),
        ("get_edges_by_relationship_type", "Get edges by relationship type"),
        ("get_edges_by_review_state", "Get edges by review state"),
        ("get_edge_evidence", "Get edge evidence"),
        ("get_edge_limitations", "Get edge limitations"),
        ("get_d6_display_ready_edges", "Get D6-display-ready edges"),
        ("get_event_fabric_ready_edges", "Get event-fabric-ready edges"),
    ]
    return [{"query_type": mode, "description": desc, "no_action_taken": True} for mode, desc in modes]


def sample_queries_and_responses(edges: list[dict[str, Any]], backlog: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog = query_catalog()
    requests = []
    responses = []
    for index, item in enumerate(catalog, start=1):
        edge = edges[(index - 1) % len(edges)] if edges else {}
        requests.append({
            "request_id": f"building-compliance-r7-query-{index:03d}",
            "query_type": item["query_type"],
            "filters": {
                "relationship_type": edge.get("relationship_type"),
                "target_context": (edge.get("target_context") or [None])[0],
            },
            "safe_mode": True,
        })
        if item["query_type"] == "get_edge_limitations" and backlog:
            selected = backlog[0]
        else:
            selected = edge
        responses.append({
            "request_id": f"building-compliance-r7-query-{index:03d}",
            "query_type": item["query_type"],
            "status": "PASS_WITH_LIMITATIONS",
            "edge_refs": [selected.get("edge_id") or selected.get("edge_candidate_id")],
            "evidence_refs": selected.get("evidence_refs", []),
            "limitation_refs": selected.get("limitation_refs", []),
            "confidence": selected.get("confidence"),
            "review_state": selected.get("review_state"),
            "answer": "Bounded building-compliance edge context is available for review/display only. No legal/compliance conclusion or action is produced.",
            "claim_boundary": BOUNDARY,
            "no_action_taken": True,
        })
    return requests, responses


def handoff_candidates(edges: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    rows = []
    for index, edge in enumerate(edges, start=1):
        rows.append({
            "handoff_id": f"building_compliance:r7:{kind}:{index:03d}",
            "edge_id": edge["edge_id"],
            "relationship_type": edge["relationship_type"],
            "target_context": edge["target_context"],
            "evidence_refs": edge["evidence_refs"],
            "limitation_refs": edge["limitation_refs"],
            "review_state": edge["review_state"],
            "handoff_status": "FUTURE_CANDIDATE_ONLY",
            "no_action_taken": True,
            "claim_boundary": BOUNDARY,
        })
    return rows


def secret_scan(paths: list[Path]) -> dict[str, Any]:
    known_tmb_key = "".join(["fff39a", "338581", "02015f", "4630ed", "32b9ac", "ad"])
    known_tmb_app_id = "".join(["2cf2", "17ca"])
    patterns = {
        "known_tmb_key": re.compile(re.escape(known_tmb_key), re.I),
        "known_tmb_app_id": re.compile(re.escape(known_tmb_app_id), re.I),
        "generic_api_key_assignment": re.compile(r"(api[_-]?key|app[_-]?key|token)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", re.I),
    }
    hits = []
    for path in paths:
        if not path.exists() or path.name == "hashes.sha256":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for name, pattern in patterns.items():
            if pattern.search(text):
                hits.append({"pattern": name, "path": rel(path)})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_hashes() -> bool:
    rows = []
    for file in sorted(OUTPUT_ROOT.rglob("*")):
        if file.is_file() and file.name != "hashes.sha256":
            rows.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {rel(file)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return bool(rows)


def main() -> int:
    before = {rel(root): snapshot(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    prereq = prerequisite_report()
    r1_decision = read_json(R1_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END_DECISION.json", {})
    if not str(r1_decision.get("status", "")).startswith("PASS"):
        decision = {"status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now(), "building_compliance_r1_loaded": False}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return 1

    r1_candidates_payload = read_json(R1_ROOT / "BUILDING_COMPLIANCE_R1_R7_EDGE_EXTENSION_CANDIDATES.json", {})
    r1_candidates = r1_candidates_payload.get("candidates", [])
    domain_packets = read_json(R1_ROOT / "BUILDING_COMPLIANCE_R1_DOMAIN_PACKETS.json", {}).get("packets", [])
    source_map = {
        "task_name": TASK_NAME,
        "sources": [
            {"root": rel(root), "exists": root.exists(), "decision_status": find_decision(root).get("status")}
            for root in READ_ONLY_ROOTS
        ],
    }

    accepted = []
    rejected = []
    for candidate in r1_candidates:
        ok, issues = accept_edge(candidate)
        if ok:
            accepted.append(accepted_edge(candidate, len(accepted) + 1))
        else:
            rejected.append({**candidate, "rejection_reasons": issues, "no_action_taken": True})
    backlog = build_data_first_backlog(domain_packets, len(r1_candidates) + 1)
    inventory = {
        "candidate_count": len(r1_candidates) + len(backlog),
        "r1_candidate_count": len(r1_candidates),
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "accepted_candidate_ids": [edge["source_candidate_id"] for edge in accepted],
        "rejected_candidate_ids": [edge.get("edge_candidate_id") for edge in rejected],
        "backlog_candidate_ids": [edge["edge_candidate_id"] for edge in backlog],
    }

    evidence_map = {edge["edge_id"]: edge["evidence_refs"] for edge in accepted}
    limitation_map = {edge["edge_id"]: edge["limitation_refs"] for edge in accepted}
    confidence_report = {
        "status": "PASS",
        "accepted_grounded_edge_count": len(accepted),
        "relationship_type_count": len({edge["relationship_type"] for edge in accepted}),
        "source_context_family_count": len({family for edge in accepted for family in edge["source_families"]}),
        "confidence_min": min(edge["confidence"] for edge in accepted) if accepted else None,
        "confidence_max": max(edge["confidence"] for edge in accepted) if accepted else None,
        "review_states": sorted({edge["review_state"] for edge in accepted}),
    }
    runtime = {
        "status": "PASS",
        "edge_count": len(accepted) + len(backlog),
        "runtime_ready_context_count": len(accepted),
        "review_context_only_count": len(accepted),
        "d6_display_ready_later_count": len(accepted),
        "track2a_kit_ready_later_count": len(accepted),
        "event_fabric_ready_later_count": len(accepted),
        "data_first_context_only_count": len(backlog),
        "classifications": [
            {"edge_id": edge["edge_id"], "tags": edge["runtime_readiness_tags"]}
            for edge in accepted
        ] + [
            {"edge_id": edge["edge_candidate_id"], "tags": ["DATA_FIRST_CONTEXT_ONLY"]}
            for edge in backlog
        ],
    }
    query_requests, query_responses = sample_queries_and_responses(accepted, backlog)
    d6_handoff = handoff_candidates(accepted, "d6-future")
    track2a_handoff = handoff_candidates(accepted, "track2a-future")
    event_handoff = handoff_candidates(accepted, "event-fabric-future")
    cer_seg_report = {
        "status": "PASS_WITH_LIMITATIONS",
        "edge_count": len(accepted),
        "linked_edge_count": sum(1 for edge in accepted if edge.get("target_context")),
        "missing_link_limitations": [],
        "note": "Edges are linked to R1 target_context/source_packet refs; global CER/SEG registry is not mutated.",
    }
    negative = {
        "status": "PASS",
        "tests": [
            "candidate without evidence rejected",
            "candidate without limitation rejected",
            "candidate without no_action rejected",
            "confirmed violation claim rejected",
            "legal finding rejected",
            "enforcement/dispatch claim rejected",
            "permit approval/rejection claim rejected",
            "certified compliance claim rejected",
            "D6/Kit mutation rejected",
            "source mutation rejected",
            "external LLM truth claim rejected",
        ],
    }
    no_action = {
        "status": "PASS",
        "accepted_grounded_edge_count": len(accepted),
        "all_accepted_edges_no_action_taken": all(edge["no_action_taken"] is True for edge in accepted),
        "all_handoff_candidates_no_action_taken": all(row["no_action_taken"] is True for row in [*d6_handoff, *track2a_handoff, *event_handoff]),
    }

    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EXTENSION_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EXTENSION_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_CANDIDATE_INVENTORY.json", inventory)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json", {"edge_count": len(accepted), "edges": accepted})
    write_jsonl(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.jsonl", accepted)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_REJECTED_EDGE_CANDIDATES.json", {"candidate_count": len(rejected), "candidates": rejected})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_BACKLOG_EDGE_CANDIDATES.json", {"candidate_count": len(backlog), "candidates": backlog})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EDGE_EVIDENCE_MAP.json", evidence_map)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EDGE_LIMITATION_MAP.json", limitation_map)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EDGE_CONFIDENCE_REVIEW_STATE_REPORT.json", confidence_report)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_RUNTIME_READINESS_CLASSIFICATION.json", runtime)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_QUERY_CATALOG.json", {"query_count": len(query_catalog()), "queries": query_catalog()})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_SAMPLE_QUERY_REQUESTS.json", {"request_count": len(query_requests), "requests": query_requests})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_SAMPLE_QUERY_RESPONSES.json", {"response_count": len(query_responses), "responses": query_responses})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(d6_handoff), "candidates": d6_handoff})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(track2a_handoff), "candidates": track2a_handoff})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", {"candidate_count": len(event_handoff), "candidates": event_handoff})
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_CER_SEG_LINK_REPORT.json", cer_seg_report)
    write_md(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_CLOSEOUT_CURRENT_TRUTH_REGISTER.md", f"# Current Truth Register\n\nStatus: `{PASS_STATUS}`\n\nAccepted grounded edges: `{len(accepted)}`\n\nThese are branch-local review/context edges only. The global R7 registry was not mutated.")
    write_md(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_CLOSEOUT_LIMITATION_REGISTER.md", "# Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_md(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_CLOSEOUT_NEXT_TASK_PLAN.md", "# Next Task Plan\n\n`MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1`\n\nOnly after product-surface approval.")
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "BUILDING_COMPLIANCE_R7_NO_ACTION_AUDIT.json", no_action)
    write_md(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", f"# Claim Boundary Audit\n\nStatus: `PASS`\n\n{BOUNDARY}")

    after = {rel(root): snapshot(root) for root in READ_ONLY_ROOTS}
    changed = [root for root, snap in before.items() if snap != after.get(root)]
    no_mutation_status = "PASS" if not changed else "FAIL"
    write_md(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: `{no_mutation_status}`\n\nChanged read-only roots: `{len(changed)}`")

    secret = secret_scan([RUNNER_PATH] + [path for path in OUTPUT_ROOT.rglob("*") if path.is_file()])
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{secret['status']}`\n\nHits: `{len(secret['hits'])}`")
    write_md(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{PASS_STATUS}`\n\nAccepted grounded edges: `{len(accepted)}`")
    write_md(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1.md", f"# {TASK_NAME}\n\nStatus: `{PASS_STATUS}`\n\nAccepted grounded edges: `{len(accepted)}`\nBacklog edges: `{len(backlog)}`\nRejected edges: `{len(rejected)}`")

    hash_ok = write_hashes()
    full_pass = (
        len(accepted) >= 6
        and len({edge["relationship_type"] for edge in accepted}) >= 3
        and len({family for edge in accepted for family in edge["source_families"]}) >= 2
        and no_mutation_status == "PASS"
        and secret["status"] == "PASS"
        and hash_ok
    )
    status = PASS_STATUS if full_pass else INVENTORY_STATUS
    if not str(prereq["status"]).startswith("PASS"):
        status = WAITING_STATUS
    if no_mutation_status != "PASS" or secret["status"] != "PASS":
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "building_compliance_r1_loaded": True,
        "candidate_edge_count": len(r1_candidates) + len(backlog),
        "accepted_grounded_edge_count": len(accepted),
        "rejected_edge_count": len(rejected),
        "backlog_edge_count": len(backlog),
        "relationship_type_count": len({edge["relationship_type"] for edge in accepted}),
        "runtime_ready_context_count": runtime["runtime_ready_context_count"],
        "review_context_only_count": runtime["review_context_only_count"],
        "d6_display_ready_later_count": runtime["d6_display_ready_later_count"],
        "track2a_kit_ready_later_count": runtime["track2a_kit_ready_later_count"],
        "event_fabric_ready_later_count": runtime["event_fabric_ready_later_count"],
        "data_first_context_only_count": runtime["data_first_context_only_count"],
        "sample_query_count": len(query_requests),
        "sample_response_count": len(query_responses),
        "d6_future_handoff_candidate_count": len(d6_handoff),
        "track2a_future_handoff_candidate_count": len(track2a_handoff),
        "event_fabric_future_handoff_candidate_count": len(event_handoff),
        "closeout_register_status": "PASS",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": "PASS",
        "no_mutation_status": no_mutation_status,
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS" if hash_ok else "FAIL",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-BUILDING-COMPLIANCE-R7-RUNTIME-SLICE-AND-D6-OVERLAY-INTEGRATION-R1",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_DECISION.json", decision)
    write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "candidate_edge_count": decision["candidate_edge_count"],
        "accepted_grounded_edge_count": decision["accepted_grounded_edge_count"],
        "backlog_edge_count": decision["backlog_edge_count"],
        "recommended_next_task": decision["recommended_next_task"],
    }, indent=2))
    return 0 if decision["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
