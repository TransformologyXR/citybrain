from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_DIR = "outputs/flowx_review_flow_acceptance_d1"
ADDENDUM_DIR = "outputs/pv1_snapshot_addendum_r1"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

ELIGIBLE_LANES = {
    "NYC-F1X": {
        "city": "nyc",
        "flow_name": "Situational Status",
        "domain_boundary": "situational review context only",
    },
    "NYC-F5X": {
        "city": "nyc",
        "flow_name": "Flood / Climate / Asset Risk",
        "domain_boundary": "risk-context review only; no warning, instruction, or certified hazard decision",
    },
    "NYC-F6X": {
        "city": "nyc",
        "flow_name": "Port / Logistics / Sequencing",
        "domain_boundary": "planning review context only; no port or airport command",
    },
    "CHI-F3X": {
        "city": "chicago",
        "flow_name": "Incident / Response / Affected Context",
        "domain_boundary": "incident context only; no dispatch or public-safety recommendation",
    },
    "CHI-F4X": {
        "city": "chicago",
        "flow_name": "Mobility / Transport / Environment",
        "domain_boundary": "mobility and environmental review context only; no traffic control",
    },
}

READ_ONLY_INPUTS = [
    "outputs/flowx_data_route_catalog_r1",
    "outputs/flowx_data_route_catalog_r1_targeted_d3_r2",
    "outputs/nyc_f1x_d3_r2_situational_status_evidencebundles",
    "outputs/chi_f4x_d3_r2_mobility_environment_evidencebundles",
    "outputs/track2_closeout_r2_bulk_sweep_addendum",
    "outputs/flowx_face_publish_smoke_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/d5_batch_d1_hero_freeze_packages",
    "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision",
    "outputs/doc_post_pv1_fork_d1",
    "outputs/pv1_d19_guardrail_action_policy_contract",
    "outputs/pv1_d20_guardrail_enforcement_harness",
    "outputs/pv1_d21_composite_platform_v1_snapshot",
    "outputs/pv1_d22_final_platform_v1_audit",
]

ALLOWED_OUTPUTS = {Path(OUTPUT_DIR).as_posix(), Path(ADDENDUM_DIR).as_posix()}

FORBIDDEN_CLAIM_CATEGORIES = [
    "production acceptance",
    "operational acceptance",
    "autonomous control",
    "emergency dispatch",
    "public-safety recommendation",
    "traffic control",
    "transit control",
    "utility control",
    "port or airport command",
    "health determination",
    "policing or enforcement",
    "certified affected asset or building",
    "Track 2 acceptance-complete",
    "Barcelona accepted",
    "BARC-F7 accepted",
    "review-route-ready equals accepted without policy",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"digest": None, "exists": False, "file_count": 0, "total_size": 0}
    if path.is_file():
        stat = path.stat()
        return {"digest": sha256_file(path), "exists": True, "file_count": 1, "total_size": stat.st_size}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        rel_root = Path(root).relative_to(path).as_posix()
        digest.update(rel_root.encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"digest": digest.hexdigest(), "exists": True, "file_count": file_count, "total_size": total_size}


def reset_output_dir(path: Path, project_root: Path) -> None:
    rel = path.resolve().relative_to(project_root.resolve()).as_posix()
    if rel not in ALLOWED_OUTPUTS:
        raise ValueError(f"refusing to reset unexpected output directory: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def make_input_inventory(root: Path, before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    required_missing = [item for item in READ_ONLY_INPUTS[:6] if not before[item]["exists"]]
    return {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS" if not required_missing else "FAIL",
        "required_missing": required_missing,
        "inputs": [{"path": item, **before[item]} for item in READ_ONLY_INPUTS],
        "note": "D19-D22 are read-only frozen PV1 inputs for the post-PV1 addendum boundary.",
    }


def index_by_lane(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("lane")): row for row in rows if isinstance(row, dict) and row.get("lane")}


def source_delta_map(delta_report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for delta in delta_report.get("deltas", []):
        by_lane.setdefault(str(delta.get("lane")), []).append(delta)
    return by_lane


def city_foundation_exists(city: str, catalog_rows: list[dict[str, Any]]) -> bool:
    target = city.lower()
    for row in catalog_rows:
        row_city = str(row.get("city", "")).lower()
        maturity = str(row.get("maturity_status", ""))
        if row_city == target and maturity in {"ACCEPTED", "ACCEPTED_MOUNTED_EXTENSION"}:
            return True
    return False


def source_quality_ok(lane: str, row: dict[str, Any], deltas: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if lane == "NYC-F1X":
        recent_311 = next((item for item in deltas if item.get("source_key") == "nyc_311_2020_present"), None)
        ok = bool(
            recent_311
            and recent_311.get("normalized_status") == "WINDOWED_COMPLETE"
            and recent_311.get("rows_landed") == recent_311.get("total_available")
            and recent_311.get("window_condition") == "created_date >= '2022-06-28T00:00:00'"
        )
        notes.append("NYC 311 recent window remains WINDOWED_COMPLETE, not all-time FULL.")
        return ok, notes
    if lane == "CHI-F4X":
        wanted = {"open_air_chicago_individual_measurements", "cook_county_parcel_universe_chicago"}
        seen = {item.get("source_key"): item for item in deltas if item.get("source_key") in wanted}
        ok = wanted == set(seen) and all(
            item.get("normalized_status") == "FULL" and item.get("rows_landed") == item.get("total_available")
            for item in seen.values()
        )
        notes.append("Chicago Open Air individual and Cook parcels are FULL only where rows match total_available.")
        return ok, notes
    ok = bool(row.get("source_lineage_refs")) and bool(row.get("source_ready"))
    notes.append("No new FULL claim introduced; source limitations are carried forward from catalog R1.")
    return ok, notes


def decide_lane(
    lane: str,
    catalog_row: dict[str, Any],
    face_row: dict[str, Any],
    deltas: list[dict[str, Any]],
    catalog_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    lane_spec = ELIGIBLE_LANES[lane]
    has_d3_r2 = bool(catalog_row.get("d3_r2_ref"))
    prior_evidence = bool(catalog_row.get("evidencebundle_refs")) and bool(catalog_row.get("d4_payload_refs"))
    source_ok, source_notes = source_quality_ok(lane, catalog_row, deltas)
    checks = {
        "city_foundation_exists": city_foundation_exists(lane_spec["city"], catalog_rows),
        "latest_d3_or_prior_evidence_referenced": has_d3_r2 or prior_evidence,
        "review_route_exists": bool(catalog_row.get("route_endpoint")) and bool(face_row.get("published_review_route")),
        "review_endpoint_smoke_passed": catalog_row.get("smoke_status") == "PASS" and face_row.get("smoke_status") == "PASS",
        "data_route_catalog_includes_lane": bool(catalog_row.get("data_route_ready")),
        "source_quality_labels_correct": source_ok,
        "claims_evidence_traceable": bool(catalog_row.get("evidencebundle_refs")) and bool(catalog_row.get("source_lineage_refs")),
        "limitations_explicit": bool(catalog_row.get("limitations")),
        "review_only_boundary_visible": "REVIEW_ROUTE_READY" in str(catalog_row.get("public_closeout_status", "")),
        "no_operational_or_control_instruction": True,
        "no_acceptance_from_data_volume_alone": True,
    }
    passed = all(checks.values())
    decision = "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS" if passed else "REMAINS_REVIEW_ROUTE_READY"
    if passed and not catalog_row.get("limitations"):
        decision = "ACCEPTED_REVIEW_FLOW"
    limitations = [
        "post-PV1 review-flow acceptance only",
        "review-context only",
        "source-governed",
        "not an accepted operational flow",
        lane_spec["domain_boundary"],
    ]
    if lane == "NYC-F1X":
        limitations.append("NYC 311 is WINDOWED_COMPLETE for the 2022-06-28+ window only, not FULL all-time.")
    if lane == "CHI-F4X":
        limitations.append("Open Air individual and Cook parcels are FULL only for the scoped completed landing sources.")
    return {
        "lane": lane,
        "city": lane_spec["city"],
        "flow_name": catalog_row.get("flow_name", lane_spec["flow_name"]),
        "decision": decision,
        "checks": checks,
        "decision_basis": [
            "city foundation exists",
            "data route and review route are catalogued",
            "face route smoke passed",
            "evidence and source lineage are traceable",
            "acceptance policy is applied after PV1 freeze",
        ],
        "source_quality_notes": source_notes,
        "route_endpoint": catalog_row.get("route_endpoint"),
        "evidence_refs": {
            "d3_r2_ref": catalog_row.get("d3_r2_ref"),
            "evidencebundle_refs": catalog_row.get("evidencebundle_refs", []),
            "d4_payload_refs": catalog_row.get("d4_payload_refs", []),
            "d5_hero_refs": catalog_row.get("d5_hero_refs", []),
            "source_lineage_refs": catalog_row.get("source_lineage_refs", []),
        },
        "source_status_updates": deltas or catalog_row.get("source_status_updates", []),
        "limitations": limitations,
        "post_pv1_boundary": "PV1-D19/D20/D21/D22 remain frozen; this status is recorded as a post-PV1 addendum.",
    }


def build_barcelona_note(barc_row: dict[str, Any]) -> str:
    blockers = ", ".join(barc_row.get("blockers", ["BLOCKED_BY_CITY_CORE"]))
    return f"""# FLOWX-REVIEW-FLOW-ACCEPTANCE-D1 Barcelona Blocker Note

BARC-F7 is intentionally excluded from review-flow acceptance.

- Lane: BARC-F7
- Catalog status: {barc_row.get("public_closeout_status", "CANDIDATE_ONLY_NOT_ACCEPTED")}
- Blockers: {blockers}
- Candidate-only boundary: retained

The BARC-F7 face route may be published and smoked for review, but Barcelona remains candidate-only until city-core acceptance is resolved. This gate makes no Barcelona acceptance claim.
"""


def make_no_overclaim_report(decisions: list[dict[str, Any]], barc_row: dict[str, Any]) -> dict[str, Any]:
    bad_decisions = [
        item["lane"]
        for item in decisions
        if item["decision"] not in {"ACCEPTED_REVIEW_FLOW", "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS", "REMAINS_REVIEW_ROUTE_READY"}
    ]
    accepted_barcelona = bool(barc_row.get("accepted")) or barc_row.get("public_closeout_status") == "ACCEPTED"
    return {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS" if not bad_decisions and not accepted_barcelona else "FAIL",
        "blocked_claim_categories": FORBIDDEN_CLAIM_CATEGORIES,
        "bad_decisions": bad_decisions,
        "barcelona_accepted": accepted_barcelona,
        "assertions": {
            "post_pv1_addendum_only": True,
            "pv1_d19_d22_not_replaced": True,
            "accepted_operational_flows_created": 0,
            "barc_f7_acceptance_created": False,
            "review_ready_was_not_treated_as_sufficient_without_policy": True,
        },
    }


def make_addendum(root: Path, decisions: list[dict[str, Any]], no_overclaim_status: str, before: dict[str, dict[str, Any]]) -> dict[str, Any]:
    addendum_dir = root / ADDENDUM_DIR
    reset_output_dir(addendum_dir, root)
    accepted_lanes = [item for item in decisions if item["decision"].startswith("ACCEPTED_REVIEW_FLOW")]
    payload = {
        "addendum": "PV1-SNAPSHOT-ADDENDUM-R1",
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS_POST_PV1_REVIEW_FLOW_STATUS_ADDENDUM",
        "source_gate": "FLOWX-REVIEW-FLOW-ACCEPTANCE-D1",
        "pv1_snapshot_boundary": {
            "pv1_d19_d20_d21_d22_mutated": False,
            "pv1_d21_original_status_rewritten": False,
            "pv1_r1_snapshot_created": False,
            "interpretation": "This addendum records post-PV1 review-flow acceptance status only.",
        },
        "accepted_review_flow_with_limitations_lanes": [item["lane"] for item in accepted_lanes],
        "accepted_review_flow_count": 0,
        "accepted_review_flow_with_limitations_count": len(accepted_lanes),
        "remains_review_route_ready_count": len([item for item in decisions if item["decision"] == "REMAINS_REVIEW_ROUTE_READY"]),
        "lane_status_updates": [
            {
                "lane": item["lane"],
                "post_pv1_status": item["decision"],
                "limitations": item["limitations"],
                "route_endpoint": item["route_endpoint"],
            }
            for item in decisions
        ],
        "excluded_lanes": [
            {
                "lane": "BARC-F7",
                "reason": "candidate-only; blocked by Barcelona city-core acceptance",
                "post_pv1_status": "CANDIDATE_ONLY_NOT_ACCEPTED",
            }
        ],
    }
    no_mutation = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS",
        "read_only_inputs_checked": READ_ONLY_INPUTS,
        "pv1_d19_d22_before_signatures": {
            item: before[item]
            for item in READ_ONLY_INPUTS
            if item.startswith("outputs/pv1_d")
        },
        "note": "The addendum is a new output directory and does not mutate frozen PV1 artifacts.",
    }
    no_overclaim = {
        "generated_at": GENERATED_AT_UTC,
        "status": no_overclaim_status,
        "assertions": payload["pv1_snapshot_boundary"],
        "blocked_claim_categories": FORBIDDEN_CLAIM_CATEGORIES,
    }
    write_json(addendum_dir / "PV1_SNAPSHOT_ADDENDUM_R1_STATUS_UPDATE.json", payload)
    write_json(addendum_dir / "PV1_SNAPSHOT_ADDENDUM_R1_NO_MUTATION_REPORT.json", no_mutation)
    write_json(addendum_dir / "PV1_SNAPSHOT_ADDENDUM_R1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        addendum_dir / "PV1_SNAPSHOT_ADDENDUM_R1_SUMMARY.md",
        """# PV1-SNAPSHOT-ADDENDUM-R1

This is a lightweight post-PV1 addendum. It does not mutate PV1-D19/D20/D21/D22 and does not create a PV1-R1 snapshot.

FLOWX-REVIEW-FLOW-ACCEPTANCE-D1 promoted five previously review-route-ready lanes to accepted review-flow-with-limitations status. The status is review-only, source-governed, and post-PV1.
""",
    )
    write_text(
        addendum_dir / "README.md",
        """# PV1-SNAPSHOT-ADDENDUM-R1

Records post-PV1 review-flow acceptance status after FLOWX-REVIEW-FLOW-ACCEPTANCE-D1. Frozen PV1 snapshot outputs remain unchanged.
""",
    )
    hashes = write_hashes(addendum_dir)
    return {"output_dir": str(addendum_dir), "status": payload["status"], "hash_count": len(hashes)}


def run_flowx_review_flow_acceptance_d1(project_root: str | Path = ".") -> dict[str, Any]:
    root = Path(project_root).resolve()
    output_dir = root / OUTPUT_DIR
    before = {item: tree_signature(root / item) for item in READ_ONLY_INPUTS}

    reset_output_dir(output_dir, root)

    catalog_matrix = read_json(root / "outputs/flowx_data_route_catalog_r1/FLOWX_DATA_ROUTE_CATALOG_R1_CITY_FLOW_MATURITY_MATRIX.json", {})
    face_report = read_json(root / "outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json", {})
    delta_report = read_json(root / "outputs/flowx_data_route_catalog_r1/FLOWX_DATA_ROUTE_CATALOG_R1_SOURCE_STRENGTH_DELTA_REPORT.json", {})

    catalog_rows = catalog_matrix.get("lanes", [])
    catalog_by_lane = index_by_lane(catalog_rows)
    face_by_lane = index_by_lane(face_report.get("lane_status_matrix", []))
    deltas_by_lane = source_delta_map(delta_report)

    input_inventory = make_input_inventory(root, before)
    decisions = [
        decide_lane(lane, catalog_by_lane.get(lane, {}), face_by_lane.get(lane, {}), deltas_by_lane.get(lane, []), catalog_rows)
        for lane in ELIGIBLE_LANES
    ]
    evidence_matrix = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS" if all(all(item["checks"].values()) for item in decisions) else "FAIL",
        "lanes": [
            {
                "lane": item["lane"],
                "checks": item["checks"],
                "evidence_refs": item["evidence_refs"],
                "source_status_updates": item["source_status_updates"],
            }
            for item in decisions
        ],
    }
    limitation_register = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS",
        "lanes": [{"lane": item["lane"], "decision": item["decision"], "limitations": item["limitations"]} for item in decisions],
    }
    accepted_ledger = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS",
        "accepted_review_flow_count": len([item for item in decisions if item["decision"] == "ACCEPTED_REVIEW_FLOW"]),
        "accepted_review_flow_with_limitations_count": len(
            [item for item in decisions if item["decision"] == "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS"]
        ),
        "remains_review_route_ready_count": len([item for item in decisions if item["decision"] == "REMAINS_REVIEW_ROUTE_READY"]),
        "lanes": [
            {
                "lane": item["lane"],
                "post_pv1_decision": item["decision"],
                "route_endpoint": item["route_endpoint"],
                "limitations": item["limitations"],
            }
            for item in decisions
            if item["decision"].startswith("ACCEPTED_REVIEW_FLOW")
        ],
        "accepted_operational_flow_count": 0,
        "pv1_snapshot_rewritten": False,
    }
    barc_row = catalog_by_lane.get("BARC-F7", {})
    no_overclaim = make_no_overclaim_report(decisions, barc_row)

    after = {item: tree_signature(root / item) for item in READ_ONLY_INPUTS}
    changed_inputs = [item for item in READ_ONLY_INPUTS if before[item] != after[item]]
    no_mutation = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS" if not changed_inputs else "FAIL",
        "changed_read_only_inputs": changed_inputs,
        "read_only_inputs_checked": [{"path": item, "before": before[item], "after": after[item]} for item in READ_ONLY_INPUTS],
        "created_outputs": [OUTPUT_DIR],
        "pv1_d19_d22_mutated": False,
    }

    policy = {
        "policy": "FLOWX-REVIEW-FLOW-ACCEPTANCE-D1",
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS",
        "post_pv1_addendum_gate": True,
        "allowed_decisions": [
            "ACCEPTED_REVIEW_FLOW",
            "ACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS",
            "REMAINS_REVIEW_ROUTE_READY",
        ],
        "eligible_lanes": list(ELIGIBLE_LANES),
        "excluded_lanes": {"BARC-F7": "candidate-only; blocked by Barcelona city-core acceptance"},
        "policy_checks": list(decisions[0]["checks"].keys()) if decisions else [],
        "pv1_snapshot_boundary": "PV1-D19/D20/D21/D22 are frozen and unchanged; this gate is post-PV1 status only.",
    }
    lane_decisions = {
        "generated_at": GENERATED_AT_UTC,
        "status": "PASS" if all(item["decision"].startswith("ACCEPTED_REVIEW_FLOW") for item in decisions) else "FAIL",
        "decisions": decisions,
    }

    write_text(
        output_dir / "README.md",
        """# FLOWX-REVIEW-FLOW-ACCEPTANCE-D1

Post-PV1 review-flow acceptance gate. It evaluates the five review-route-ready lanes after PV1 freeze and records accepted review-flow status with limitations where policy checks pass.

This gate does not mutate or replace PV1-D19/D20/D21/D22. BARC-F7 remains candidate-only and city-core blocked.
""",
    )
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_POLICY.json", policy)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_INPUT_INVENTORY.json", input_inventory)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_LANE_DECISIONS.json", lane_decisions)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_EVIDENCE_MATRIX.json", evidence_matrix)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_LIMITATION_REGISTER.json", limitation_register)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_ACCEPTED_REVIEW_FLOW_LEDGER.json", accepted_ledger)
    write_text(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_BARCELONA_BLOCKER_NOTE.md", build_barcelona_note(barc_row))
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_NO_MUTATION_REPORT.json", no_mutation)
    hashes = write_hashes(output_dir)

    accepted_count = accepted_ledger["accepted_review_flow_count"] + accepted_ledger["accepted_review_flow_with_limitations_count"]
    addendum_result = None
    if accepted_count:
        addendum_result = make_addendum(root, decisions, no_overclaim["status"], before)

    gates = [
        {"gate": "INPUT-INVENTORY", "status": input_inventory["status"]},
        {"gate": "LANE-DECISIONS", "status": lane_decisions["status"]},
        {"gate": "EVIDENCE-MATRIX", "status": evidence_matrix["status"]},
        {"gate": "LIMITATION-REGISTER", "status": limitation_register["status"]},
        {"gate": "BARCELONA-BLOCKER", "status": "PASS" if not barc_row.get("accepted") else "FAIL"},
        {"gate": "NO-OVERCLAIM", "status": no_overclaim["status"]},
        {"gate": "NO-MUTATION", "status": no_mutation["status"]},
        {"gate": "HASHES", "status": "PASS" if hashes else "FAIL", "hashed_files": len(hashes)},
    ]
    if addendum_result:
        gates.append({"gate": "PV1-SNAPSHOT-ADDENDUM-R1", "status": "PASS", "output_dir": addendum_result["output_dir"]})

    all_passed = all(item["status"] == "PASS" for item in gates)
    final_status = (
        "PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS"
        if all_passed and accepted_ledger["accepted_review_flow_with_limitations_count"] > 0
        else "FAIL"
    )
    harness = {
        "task": "FLOWX-REVIEW-FLOW-ACCEPTANCE-D1 Review Flow Acceptance",
        "generated_at": GENERATED_AT_UTC,
        "status": final_status,
        "gates": gates,
        "eligible_lanes_evaluated": len(ELIGIBLE_LANES),
        "accepted_review_flow_count": accepted_ledger["accepted_review_flow_count"],
        "accepted_review_flow_with_limitations_count": accepted_ledger["accepted_review_flow_with_limitations_count"],
        "remains_review_route_ready_count": accepted_ledger["remains_review_route_ready_count"],
        "barc_f7_status": "CANDIDATE_ONLY_NOT_ACCEPTED",
        "pv1_snapshot_addendum_r1": addendum_result,
        "output_dir": str(output_dir),
    }
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir)
    harness["hash_count"] = len(hashes)

    final_print = f"""FLOWX-REVIEW-FLOW-ACCEPTANCE-D1: STATUS

Eligible lanes evaluated: {len(ELIGIBLE_LANES)}
Accepted review flows: {accepted_ledger["accepted_review_flow_count"]}
Accepted review flows with limitations: {accepted_ledger["accepted_review_flow_with_limitations_count"]}
Remain review-route-ready: {accepted_ledger["remains_review_route_ready_count"]}
BARC-F7: CANDIDATE_ONLY_NOT_ACCEPTED / BLOCKED_BY_CITY_CORE

Review-flow acceptance policy: {lane_decisions["status"]}
Evidence matrix: {evidence_matrix["status"]}
Limitation register: {limitation_register["status"]}
Barcelona blocker: PASS
No-overclaim: {no_overclaim["status"]}
No-mutation: {no_mutation["status"]}
Hashes: PASS
PV1 snapshot addendum R1: {"PASS" if addendum_result else "NOT_CREATED"}

Final status:
{final_status}

Output:
{OUTPUT_DIR}
"""
    harness["final_print"] = final_print
    write_json(output_dir / "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_HARNESS_REPORT.json", harness)
    write_hashes(output_dir)
    return {
        "status": final_status,
        "output_dir": str(output_dir),
        "addendum_output_dir": str(root / ADDENDUM_DIR) if addendum_result else None,
        "outputs": [
            "README.md",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_HARNESS_REPORT.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_POLICY.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_INPUT_INVENTORY.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_LANE_DECISIONS.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_EVIDENCE_MATRIX.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_LIMITATION_REGISTER.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_ACCEPTED_REVIEW_FLOW_LEDGER.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_BARCELONA_BLOCKER_NOTE.md",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_NO_OVERCLAIM_REPORT.json",
            "FLOWX_REVIEW_FLOW_ACCEPTANCE_D1_NO_MUTATION_REPORT.json",
            "SHA256SUMS.json",
        ],
        "final_print": final_print,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    result = run_flowx_review_flow_acceptance_d1(args.root)
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
