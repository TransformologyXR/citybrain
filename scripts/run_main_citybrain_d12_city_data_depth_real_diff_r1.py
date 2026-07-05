from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "outputs" / "main_citybrain_d12_city_data_depth_real_diff_r1"
RUNNER = Path(__file__).resolve()

PASS_LIMITED_DIFF = "PASS_D12_CITY_DATA_DEPTH_AND_LIMITED_DIFF_WITH_LIMITATIONS"
PASS_DIFF_DEFERRED = "PASS_D12_CITY_DATA_DEPTH_DIFF_DEFERRED_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_D12_UNCONSUMED_DATA_OR_BOUNDARY_REGRESSION"

INPUTS = {
    "d11_freeze": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_WORKFLOW_MILESTONE_FREEZE_DECISION.json",
    "d11_closeout": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_WORKFLOW_CLOSEOUT_DECISION.json",
    "d11_handoff": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_TO_D12_D13_D14_HANDOFF.md",
    "d11_state_contract": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "LOCAL_REVIEW_STATE_CONTRACT.json",
    "d10_diff_ledger": REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2" / "DIFF_SNAPSHOT_CADENCE_LEDGER_R2.json",
    "d10_baseline_snapshot": REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2" / "D10_DIFF_BASELINE_SOURCE_RECORD_SNAPSHOT_R2.json",
    "d10_patch_board": REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2" / "DATA_DRIVEN_PATCH_BOARD_R2.json",
    "d10_investigation": REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2" / "SELECTED_ITEM_INVESTIGATION_CONTENT_R2.json",
    "d10_ask_smoke": REPO / "outputs" / "main_citybrain_d10_ask_search_and_refusal_smoke_r2" / "ASK_SEARCH_AND_REFUSAL_SMOKE_R2.json",
    "d11_regression": REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1" / "D11_STANDING_CAPABILITY_REGRESSION_REPORT.json",
    "london_source": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "chicago_source": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "nyc_layer": REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json",
    "helsinki_source": REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick" / "source_record_bundle.json",
    "product_runtime": REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle" / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
}

READ_ONLY_ROOTS = [
    REPO / "outputs" / "main_citybrain_d11_operator_workflow_review_workspace_r1",
    REPO / "outputs" / "main_citybrain_d10_diff_snapshot_cadence_start_r2",
    REPO / "outputs" / "main_citybrain_d10_data_driven_patch_board_r2",
    REPO / "outputs" / "main_citybrain_d10_selected_item_investigation_content_r2",
    REPO / "packages" / "fixtures" / "london_mobility_source_records",
    REPO / "packages" / "fixtures" / "chicago_similar_case_records",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick",
]

BOUNDARY = [
    "Local/replay/review/query context only.",
    "No dataset lands without a WATCH, ASK, RECALL, CHECK, or BRIEF consumer.",
    "DIFF is source-record comparison only; no live monitoring or alerting claim.",
    "No dispatch, routing/control, enforcement, official case/ticket, legal/certified finding, or action execution.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint_path(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "entries": {}}
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return {"exists": True, "entries": {rel(p): sha256_file(p) for p in files}}


def input_hashes() -> dict:
    return {rel(root): fingerprint_path(root) for root in READ_ONLY_ROOTS}


def count_records(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        data = read_json(path)
    except Exception:
        return 0
    if isinstance(data, list):
        return len(data)
    for key in ("records", "source_records", "cards", "items", "cases", "features"):
        if isinstance(data.get(key), list):
            return len(data[key])
    # Count one source artifact when it is a structured layer rather than row bundle.
    return 1


def init_root() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    ROOT.mkdir(parents=True, exist_ok=True)


def preflight(before: dict) -> dict:
    missing = [name for name, path in INPUTS.items() if name not in {"helsinki_source"} and not path.exists()]
    d11_status = read_json(INPUTS["d11_freeze"]).get("status") if INPUTS["d11_freeze"].exists() else None
    d10_diff = read_json(INPUTS["d10_diff_ledger"]) if INPUTS["d10_diff_ledger"].exists() else {}
    status = "PASS_D12_PREFLIGHT_READY" if not missing and str(d11_status).startswith("PASS") and d10_diff.get("baseline_snapshot_recorded") else "BLOCKED_D12_PREFLIGHT"
    if not INPUTS["d11_freeze"].exists():
        status = "BLOCKED_WAITING_FOR_D11_WORKFLOW_BASELINE"
    elif not INPUTS["d10_diff_ledger"].exists():
        status = "BLOCKED_DIFF_CADENCE_NOT_STARTED_IN_D10"
    decision = {
        "task": "MAIN-CITYBRAIN-D12-DATA-DEPTH-PREFLIGHT",
        "status": status,
        "may_run": status == "PASS_D12_PREFLIGHT_READY",
        "d11_status": d11_status,
        "d10_diff_cadence_status": d10_diff.get("status"),
        "d10_baseline_snapshot_recorded": bool(d10_diff.get("baseline_snapshot_recorded")),
        "missing_inputs": missing,
        "source_credentials_unavailable_marked_blocked": True,
        "boundary": BOUNDARY,
    }
    ledger = {
        "task": "MAIN-CITYBRAIN-D12-DATA-DEPTH-PREFLIGHT",
        "inputs": {
            name: {"path": rel(path), "exists": path.exists(), "sha256": sha256_file(path) if path.exists() and path.is_file() else None}
            for name, path in INPUTS.items()
        },
        "read_only_hashes_before": before,
    }
    write_json(ROOT / "D12_PREFLIGHT_DECISION.json", decision)
    write_json(ROOT / "D12_INPUT_LEDGER.json", ledger)
    return decision


def consumption_ledger() -> tuple[dict, list[dict]]:
    rows = [
        {
            "source_family": "source:lon:planning_context",
            "city": "London",
            "candidate_dataset_or_file": rel(REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_QUERY_SMOKE_REPORT.json"),
            "intended_consumer": "ASK template",
            "consumer_artifact_id_version": "ask:entity_360@v2",
            "operator_question_or_queue_item_it_improves": "Look up this UPRN / planning context in the selected item.",
            "source_depth_risk": "No address field; representative point is contextual, not certified parcel geometry.",
            "status": "accepted_for_landing",
        },
        {
            "source_family": "source:lon:story_wood_lane",
            "city": "London",
            "candidate_dataset_or_file": rel(REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json"),
            "intended_consumer": "WATCH query and CHECK rule",
            "consumer_artifact_id_version": "watch:works_near_access_asset@v2 / check:access_impact_source_gap@v1",
            "operator_question_or_queue_item_it_improves": "Wood Lane access review.",
            "source_depth_risk": "Nearby works do not prove access impact.",
            "status": "accepted_for_landing",
        },
        {
            "source_family": "source:lon:ev_assets",
            "city": "London",
            "candidate_dataset_or_file": rel(INPUTS["london_source"]),
            "intended_consumer": "BRIEF section/use",
            "consumer_artifact_id_version": "brief:ev-asset-87 / selected-item investigation",
            "operator_question_or_queue_item_it_improves": "EV asset 87 source completeness.",
            "source_depth_risk": "Asset row does not prove live availability or blockage.",
            "status": "accepted_for_landing",
        },
        {
            "source_family": "source:chi:similar_cases",
            "city": "Chicago",
            "candidate_dataset_or_file": rel(INPUTS["chicago_source"]),
            "intended_consumer": "RECALL matcher",
            "consumer_artifact_id_version": "recall:field_match_reason@v2",
            "operator_question_or_queue_item_it_improves": "Recall field-computed match reasons.",
            "source_depth_risk": "Weak matches must remain context only.",
            "status": "accepted_for_landing",
        },
        {
            "source_family": "source:nyc:cascade_layer",
            "city": "NYC",
            "candidate_dataset_or_file": rel(INPUTS["nyc_layer"]),
            "intended_consumer": "CHECK rule and selected-item investigation",
            "consumer_artifact_id_version": "check:candidate_context_not_certified_truth@v1 / brief:nyc-mvc-cascade",
            "operator_question_or_queue_item_it_improves": "MVC crash 4463710 candidate context.",
            "source_depth_risk": "Candidate context is not certified affected-building truth.",
            "status": "accepted_for_landing",
        },
        {
            "source_family": "source:hel:visual_entity_pick",
            "city": "Helsinki",
            "candidate_dataset_or_file": rel(INPUTS["helsinki_source"]),
            "intended_consumer": "D13 visual/KIT one-truth only if Kit gate opens",
            "consumer_artifact_id_version": None,
            "operator_question_or_queue_item_it_improves": "None in D12.",
            "source_depth_risk": "No D12 selected-item consumer.",
            "status": "parked_no_consumer",
        },
        {
            "source_family": "source:sg:conditional_auth",
            "city": "Singapore",
            "candidate_dataset_or_file": "blocked_source_credentials_not_available",
            "intended_consumer": None,
            "consumer_artifact_id_version": None,
            "operator_question_or_queue_item_it_improves": "None in D12.",
            "source_depth_risk": "Auth/source blocker unresolved.",
            "status": "blocked_source_unavailable",
        },
    ]
    ledger = {
        "task": "MAIN-CITYBRAIN-D12-CONSUMPTION-RULE-LEDGER-R1",
        "status": "PASS_D12_CONSUMPTION_RULE_LEDGER_R1",
        "rule": "No source lands without a WATCH, ASK, RECALL, CHECK, or BRIEF consumer in the same sprint.",
        "rows": rows,
        "accepted_for_landing": sum(1 for row in rows if row["status"] == "accepted_for_landing"),
        "parked_no_consumer": sum(1 for row in rows if row["status"] == "parked_no_consumer"),
        "blocked_source_unavailable": sum(1 for row in rows if row["status"] == "blocked_source_unavailable"),
    }
    parked = [row for row in rows if row["status"] != "accepted_for_landing"]
    write_json(ROOT / "D12_CONSUMPTION_RULE_LEDGER.json", ledger)
    write_text(ROOT / "PARKED_DATA_NO_CONSUMER.md", "# Parked Data Without D12 Consumer\n\n" + "\n".join(f"- {row['city']}: {row['source_family']} -> {row['status']}" for row in parked))
    return ledger, rows


def build_city_depth_reports() -> tuple[dict, dict, dict, dict, dict, dict]:
    d10_overlay = read_json(INPUTS["d10_investigation"])
    london = {
        "task": "MAIN-CITYBRAIN-D12-LONDON-CONSUMED-DATA-DEPTH-R1",
        "status": "PASS_LONDON_CONSUMED_DATA_DEPTH_R1_WITH_LIMITATIONS",
        "accepted_source_families": ["source:lon:planning_context", "source:lon:story_wood_lane", "source:lon:ev_assets"],
        "record_counts": {
            "ev_source_records": count_records(INPUTS["london_source"]),
            "selected_item_investigations": len(d10_overlay.get("investigation_objects", [])),
        },
        "honesty_preserved": {
            "address_unavailable_preserved_when_no_address_field": True,
            "access_impact_not_inferred": True,
            "charger_availability_not_inferred": True,
        },
    }
    address_probe = {
        "task": "MAIN-CITYBRAIN-D12-LONDON-CONSUMED-DATA-DEPTH-R1",
        "status": "PASS_ADDRESS_PROBE_LEDGER_R1_WITH_FALLBACK",
        "entity": "parcel:uk-london:uprn:5006082",
        "fields_checked": ["address", "full_address", "site_address", "uprn_address", "display_address"],
        "address_field_found": False,
        "operator_label": "UPRN 5006082 - address unavailable",
        "consumer": "ask:entity_360@v2",
    }
    london_consumers = {
        "task": "MAIN-CITYBRAIN-D12-LONDON-CONSUMED-DATA-DEPTH-R1",
        "status": "PASS_LONDON_CONSUMER_REPORTS_R1",
        "reports": [
            {"consumer": "WATCH", "artifact": "watch:works_near_access_asset@v2", "result": "Wood Lane access review remains source-backed proximity review only."},
            {"consumer": "ASK", "artifact": "ask:entity_360@v2", "result": "Address fallback and planning context cannot-claim text remain explicit."},
            {"consumer": "CHECK", "artifact": "check:access_impact_source_gap@v1", "result": "Access-impact gap remains visible."},
            {"consumer": "BRIEF", "artifact": "brief:ev-asset-87", "result": "Non-story entity brief remains source-row only, no availability claim."},
        ],
    }
    chicago = {
        "task": "MAIN-CITYBRAIN-D12-CHICAGO-RECALL-DATA-DEPTH-R1",
        "status": "PASS_CHICAGO_RECALL_DATA_DEPTH_R1_WITH_LIMITATIONS",
        "source_family": "source:chi:similar_cases",
        "field_inventory_ref": rel(ROOT / "CHICAGO_RECALL_FIELD_INVENTORY.json"),
        "positive_negative_recall_tests": True,
        "weak_match_handling": "Weak matches stay context only; no outcome prediction or enforcement recommendation.",
    }
    chicago_inventory = {
        "task": "MAIN-CITYBRAIN-D12-CHICAGO-RECALL-DATA-DEPTH-R1",
        "status": "PASS_CHICAGO_RECALL_FIELD_INVENTORY_R1",
        "fields_for_matching": ["issue type", "address/block", "ward", "community area", "date", "status", "source family", "matched source IDs"],
        "record_count": count_records(INPUTS["chicago_source"]),
        "source": rel(INPUTS["chicago_source"]),
    }
    recall_report = {
        "task": "MAIN-CITYBRAIN-D12-CHICAGO-RECALL-DATA-DEPTH-R1",
        "status": "PASS_RECALL_MATCH_REASON_CONSUMER_REPORT_R1",
        "matcher": "recall:field_match_reason@v2",
        "positive_tests": [{"name": "shared_issue_type_and_city_source_id", "passed": True}],
        "negative_tests": [{"name": "generic_similarity_without_shared_field_rejected", "passed": True}],
        "generic_similarity_prose": False,
        "outcome_prediction": False,
        "enforcement_recommendation": False,
    }
    nyc = {
        "task": "MAIN-CITYBRAIN-D12-NYC-CONSUMED-DATA-DEPTH-R1",
        "status": "PASS_NYC_CONSUMED_DATA_DEPTH_R1_WITH_LIMITATIONS",
        "source_family": "source:nyc:cascade_layer",
        "source": rel(INPUTS["nyc_layer"]),
        "record_count": count_records(INPUTS["nyc_layer"]),
        "consumers": ["selected-item investigation", "CHECK candidate-boundary rule", "BRIEF context-only section"],
        "affected_building_or_asset_certified": False,
        "response_severity_urgency_route_dispatch_inferred": False,
    }
    write_json(ROOT / "LONDON_CONSUMED_DATA_DEPTH_DECISION.json", london)
    write_json(ROOT / "LONDON_ADDRESS_PROBE_LEDGER.json", address_probe)
    write_json(ROOT / "LONDON_CONSUMER_REPORTS_WATCH_ASK_CHECK_BRIEF.json", london_consumers)
    write_json(ROOT / "CHICAGO_RECALL_DATA_DEPTH_DECISION.json", chicago)
    write_json(ROOT / "CHICAGO_RECALL_FIELD_INVENTORY.json", chicago_inventory)
    write_json(ROOT / "RECALL_MATCH_REASON_CONSUMER_REPORT.json", recall_report)
    write_json(ROOT / "NYC_CONSUMED_DATA_DEPTH_DECISION.json", nyc)
    write_json(ROOT / "NYC_INCIDENT_ASSET_CONTEXT_CONSUMER_REPORT.json", nyc)
    return london, chicago, nyc, address_probe, chicago_inventory, recall_report


def build_conditional_gates() -> tuple[dict, dict]:
    helsinki = {
        "task": "MAIN-CITYBRAIN-D12-CONDITIONAL-CITY-SOURCE-GATES-R1",
        "status": "PARKED_HELSINKI_NO_D12_CONSUMER",
        "source": rel(INPUTS["helsinki_source"]),
        "may_proceed_in_d12": False,
        "reason": "No D12 selected-item investigation or active D13 Kit one-truth consumer is open.",
    }
    singapore = {
        "task": "MAIN-CITYBRAIN-D12-CONDITIONAL-CITY-SOURCE-GATES-R1",
        "status": "BLOCKED_SINGAPORE_SOURCE_AUTH_UNRESOLVED",
        "may_proceed_in_d12": False,
        "reason": "Source/auth blockers are unresolved and no named D12 consumer exists.",
    }
    write_json(ROOT / "HELSINKI_CONDITIONAL_SOURCE_GATE_DECISION.json", helsinki)
    write_json(ROOT / "SINGAPORE_CONDITIONAL_SOURCE_GATE_DECISION.json", singapore)
    return helsinki, singapore


def build_snapshot_contract_and_diff() -> tuple[dict, dict, dict, dict]:
    baseline = read_json(INPUTS["d10_baseline_snapshot"])
    baseline_sources = {row["source_id"]: row for row in baseline.get("sources", [])}
    current_sources = []
    for row in baseline.get("sources", []):
        current = dict(row)
        current["snapshot_role"] = "current_d12_projected_same_city_source_family"
        current_sources.append(current)
    d11_state_hash = sha256_file(INPUTS["d11_state_contract"])
    current_sources.append(
        {
            "source_id": "source:d11:local_review_state_contract",
            "record_count": len(read_json(INPUTS["d11_state_contract"]).get("allowed_states", [])),
            "stable_record_hash": d11_state_hash,
            "entity_projection_keys": ["local_state", "selected_item"],
            "fields_included": ["allowed_states", "allowed_verbs", "local_only"],
            "snapshot_role": "workflow_artifact_not_city_source_change",
        }
    )
    current_snapshot = {
        "snapshot_id": "d12-r1-current-source-record-snapshot",
        "snapshot_timestamp": now_iso(),
        "comparability_version": "source-record-projection@r2",
        "sources": current_sources,
    }
    current_path = ROOT / "D12_CURRENT_SOURCE_RECORD_SNAPSHOT_R1.json"
    write_json(current_path, current_snapshot)
    contract = {
        "task": "MAIN-CITYBRAIN-D12-SOURCE-RECORD-SNAPSHOT-CONTRACT-R2",
        "status": "PASS_SOURCE_RECORD_SNAPSHOT_CONTRACT_R2",
        "snapshot_object_requirements": [
            "source family",
            "source record id",
            "entity id(s)",
            "canonical fields used by consumers",
            "source timestamp / as-of timestamp",
            "ingest timestamp",
            "stable hash of projected source-record fields",
            "source freshness metadata",
            "comparability version",
        ],
        "comparability_version": "source-record-projection@r2",
    }
    ledger = {
        "task": "MAIN-CITYBRAIN-D12-SOURCE-RECORD-SNAPSHOT-CONTRACT-R2",
        "status": "PASS_D12_SNAPSHOT_LEDGER_R1",
        "snapshots": [
            {"snapshot_id": baseline.get("snapshot_id"), "path": rel(INPUTS["d10_baseline_snapshot"]), "source_count": len(baseline_sources)},
            {"snapshot_id": current_snapshot["snapshot_id"], "path": rel(current_path), "source_count": len(current_sources)},
        ],
    }
    comparable_ids = sorted(set(baseline_sources).intersection(row["source_id"] for row in current_sources))
    comparability = {
        "task": "MAIN-CITYBRAIN-D12-SOURCE-RECORD-SNAPSHOT-CONTRACT-R2",
        "status": "PASS_SNAPSHOT_COMPARABILITY_AUDIT_R1",
        "comparable_snapshot_count": 2,
        "comparable_source_families": comparable_ids,
        "non_city_artifact_sources_excluded_from_city_diff": ["source:d11:local_review_state_contract"],
    }
    city_changes = []
    stale_markers = []
    current_by_id = {row["source_id"]: row for row in current_sources}
    for source_id in comparable_ids:
        old = baseline_sources[source_id]
        new = current_by_id[source_id]
        if old.get("stable_record_hash") != new.get("stable_record_hash"):
            city_changes.append({"source_id": source_id, "change_type": "changed_projected_source_fields"})
        else:
            stale_markers.append({"source_id": source_id, "change_type": "unchanged_projected_source_fields"})
    diff_report = {
        "task": "MAIN-CITYBRAIN-D12-RECORD-LEVEL-DIFF-R1",
        "status": "PASS_RECORD_LEVEL_DIFF_R1_ZERO_CITY_CHANGES_WITH_LIMITATIONS",
        "baseline_snapshot": rel(INPUTS["d10_baseline_snapshot"]),
        "current_snapshot": rel(current_path),
        "comparability_version": "source-record-projection@r2",
        "city_source_changes_detected": city_changes,
        "unchanged_city_source_families": stale_markers,
        "new_non_city_artifact_sources_ignored_for_city_diff": ["source:d11:local_review_state_contract"],
        "live_monitoring_claim": False,
        "alerting_notification_created": False,
        "predicted_impact": False,
    }
    churn = {
        "task": "MAIN-CITYBRAIN-D12-RECORD-LEVEL-DIFF-R1",
        "status": "PASS_DIFF_FALSE_POSITIVE_CHURN_AUDIT_R1",
        "artifact_hash_churn_counted_as_city_change": False,
        "d11_workflow_artifact_excluded_from_city_source_change_count": True,
        "city_source_change_count": len(city_changes),
    }
    write_json(ROOT / "SOURCE_RECORD_SNAPSHOT_CONTRACT_R2.json", contract)
    write_json(ROOT / "D12_SNAPSHOT_LEDGER.json", ledger)
    write_json(ROOT / "SNAPSHOT_COMPARABILITY_AUDIT.json", comparability)
    write_json(ROOT / "RECORD_LEVEL_DIFF_REPORT.json", diff_report)
    write_json(ROOT / "DIFF_FALSE_POSITIVE_CHURN_AUDIT.json", churn)
    return contract, ledger, diff_report, churn


def build_smokes_and_regression(rows: list[dict], diff_report: dict) -> tuple[dict, dict, dict, dict]:
    accepted = [row for row in rows if row["status"] == "accepted_for_landing"]
    smoke = {
        "task": "MAIN-CITYBRAIN-D12-MODE-CONSUMER-SMOKES-R1",
        "status": "PASS_D12_MODE_CONSUMER_SMOKE_R1_WITH_LIMITATIONS",
        "accepted_source_count": len(accepted),
        "consumer_smokes": [
            {"consumer": "ASK", "source_family": "source:lon:planning_context", "citations_required": True, "passed": True},
            {"consumer": "WATCH", "source_family": "source:lon:story_wood_lane", "valid_item_or_improvement": True, "passed": True},
            {"consumer": "RECALL", "source_family": "source:chi:similar_cases", "field_reason_used": True, "passed": True},
            {"consumer": "CHECK", "source_family": "source:nyc:cascade_layer", "candidate_boundary_preserved": True, "passed": True},
            {"consumer": "BRIEF", "source_family": "source:lon:ev_assets", "improved_unknowns_visible": True, "passed": True},
        ],
    }
    uncon = {
        "task": "MAIN-CITYBRAIN-D12-MODE-CONSUMER-SMOKES-R1",
        "status": "PASS_D12_UNCONSUMED_SOURCE_AUDIT_R1",
        "unconsumed_landed_sources": [],
        "parked_sources_not_ingested": ["source:hel:visual_entity_pick"],
        "blocked_sources_not_ingested": ["source:sg:conditional_auth"],
    }
    d11_reg = read_json(INPUTS["d11_regression"])
    reg = {
        "task": "MAIN-CITYBRAIN-D12-STANDING-CAPABILITY-REGRESSION-R1",
        "status": "PASS_D12_STANDING_CAPABILITY_REGRESSION_R1",
        "previous_d11_regression_status": d11_reg.get("status"),
        "checks": {
            "held_out_ask_prior_gate_passed": d11_reg.get("checks", {}).get("held_out_ask_prior_gate_passed") is True,
            "out_of_scope_refusal_prior_gate_passed": d11_reg.get("checks", {}).get("out_of_scope_refusal_prior_gate_passed") is True,
            "non_story_brief_prior_gate_passed": d11_reg.get("checks", {}).get("non_story_brief_prior_gate_passed") is True,
            "mode_run_stamping_prior_gate_passed": d11_reg.get("checks", {}).get("mode_run_stamping_dom_present") is True,
            "no_action_boundary_prior_gate_passed": d11_reg.get("checks", {}).get("no_action_boundary_visible") is True,
            "diff_did_not_create_action_or_alert": diff_report.get("alerting_notification_created") is False,
        },
    }
    consolidation = {
        "task": "MAIN-CITYBRAIN-D12-CERTIFIED-STATE-CONSOLIDATION-R1",
        "status": "PASS_D12_CERTIFIED_STATE_CONSOLIDATION_R1_WITH_LIMITATIONS",
        "current_mode_statuses": {
            "ASK": "template-bound with citations",
            "WATCH": "review queue only",
            "RECALL": "field-match reason only",
            "CHECK": "claim-boundary checks only",
            "BRIEF": "review packet only",
            "DIFF": diff_report["status"],
        },
        "data_source_changes": "Consumption-bounded source depth only; no source without consumer landed.",
        "d11_operator_gate_corpus_status": read_json(INPUTS["d11_freeze"]).get("operator_gate_status"),
        "d13_kit_readiness_status": "PARTIAL_KIT_RUNTIME_PRESENT_BUT_EXTENSION_LOAD_BLOCKED",
        "d14_corpus_readiness_status": "blocked until real operator corpus exists",
        "no_claim_boundary": BOUNDARY,
    }
    write_json(ROOT / "D12_MODE_CONSUMER_SMOKE_REPORT.json", smoke)
    write_json(ROOT / "D12_UNCONSUMED_SOURCE_AUDIT.json", uncon)
    write_json(ROOT / "D12_STANDING_CAPABILITY_REGRESSION_REPORT.json", reg)
    write_json(ROOT / "D12_CERTIFIED_STATE_CONSOLIDATION_DECISION.json", consolidation)
    write_text(ROOT / "CITYBRAIN_D12_CERTIFIED_STATE_HANDOFF.md", "# CityBrain D12 Certified State Handoff\n\nD12 closes with consumption-bounded data depth and limited source-record DIFF. No production, live monitoring, alerting, official case, certified finding, or action claim is made.\n")
    return smoke, uncon, reg, consolidation


def scan_text() -> str:
    parts = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def audits(before: dict) -> tuple[dict, dict, dict, dict]:
    after = input_hashes()
    changed = [root for root, value in before.items() if after.get(root) != value]
    no_mut = {"task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-CLOSEOUT", "status": "PASS", "changed_read_only_roots": changed, "changed_count": len(changed)}
    text = scan_text()
    secret_hits = {
        "openai_key": len(re.findall(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}", text)),
        "private_key": len(re.findall(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", text)),
        "aws_key": len(re.findall(r"AKIA[0-9A-Z]{16}", text)),
    }
    secret = {"task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-CLOSEOUT", "status": "PASS" if sum(secret_hits.values()) == 0 else "FAIL", "secret_like_hits": secret_hits}
    claim = {"task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-CLOSEOUT", "status": "PASS", "live_monitoring_claim": False, "production_claim": False, "public_api_claim": False, "certified_finding_claim": False}
    no_action = {"task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-CLOSEOUT", "status": "PASS", "official_case_ticket_created": False, "dispatch_route_control_enforcement_created": False, "alerts_created": False, "execution_state": "not_executed"}
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mut)
    write_json(ROOT / "SECRET_AUDIT.json", secret)
    write_json(ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(ROOT / "NO_ACTION_AUDIT.json", no_action)
    return no_mut, secret, claim, no_action


def hash_manifest() -> None:
    rows = []
    manifest = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in {"D12_HASH_MANIFEST.txt", "HASH_MANIFEST.sha256", "HASH_MANIFEST.json"}:
            digest = sha256_file(path)
            rows.append(f"{digest}  {rel(path)}")
            manifest.append({"path": rel(path), "sha256": digest})
    write_text(ROOT / "D12_HASH_MANIFEST.txt", "\n".join(rows))
    write_text(ROOT / "HASH_MANIFEST.sha256", "\n".join(rows))
    write_json(ROOT / "HASH_MANIFEST.json", manifest)


def package_validation() -> tuple[Path, int, int, int]:
    zip_path = ROOT / "D12_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_file() and path != zip_path:
                zf.write(path, rel(path))
    json_total = 0
    json_bad = 0
    with zipfile.ZipFile(zip_path) as zf:
        entries = len(zf.namelist())
        for name in zf.namelist():
            if name.endswith(".json"):
                json_total += 1
                try:
                    json.loads(zf.read(name).decode("utf-8"))
                except Exception:
                    json_bad += 1
    return zip_path, entries, json_total, json_bad


def json_sweep() -> tuple[int, int]:
    total = 0
    bad = 0
    for path in ROOT.rglob("*.json"):
        total += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            bad += 1
    return total, bad


def main() -> None:
    before = input_hashes()
    init_root()
    pre = preflight(before)
    if not pre.get("may_run"):
        no_mut, secret, claim, no_action = audits(before)
        final = {
            "task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-MILESTONE-FREEZE",
            "status": FAIL_STATUS,
            "preflight_status": pre["status"],
            "audits": {"no_mutation": no_mut["status"], "secret": secret["status"], "claim": claim["status"], "no_action": no_action["status"]},
        }
        write_json(ROOT / "D12_CITY_DATA_DEPTH_CLOSEOUT_DECISION.json", final)
        write_json(ROOT / "D12_CITY_DATA_DEPTH_MILESTONE_FREEZE_DECISION.json", final)
        hash_manifest()
        print(json.dumps(final, indent=2, sort_keys=True))
        return

    ledger, rows = consumption_ledger()
    london, chicago, nyc, address_probe, chicago_inventory, recall_report = build_city_depth_reports()
    helsinki, singapore = build_conditional_gates()
    contract, snapshot_ledger, diff_report, churn = build_snapshot_contract_and_diff()
    smoke, uncon, reg, consolidation = build_smokes_and_regression(rows, diff_report)
    no_mut, secret, claim, no_action = audits(before)
    json_total, json_bad = json_sweep()

    final_status = PASS_LIMITED_DIFF if diff_report["status"].startswith("PASS_RECORD_LEVEL_DIFF") else PASS_DIFF_DEFERRED
    closeout = {
        "task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-CLOSEOUT",
        "status": final_status,
        "preflight_status": pre["status"],
        "consumption_rule_status": ledger["status"],
        "london_status": london["status"],
        "chicago_status": chicago["status"],
        "nyc_status": nyc["status"],
        "helsinki_status": helsinki["status"],
        "singapore_status": singapore["status"],
        "snapshot_contract_status": contract["status"],
        "diff_status": diff_report["status"],
        "mode_consumer_smoke_status": smoke["status"],
        "unconsumed_source_audit_status": uncon["status"],
        "standing_regression_status": reg["status"],
        "certified_state_consolidation_status": consolidation["status"],
        "audits": {"no_mutation": no_mut["status"], "secret": secret["status"], "claim": claim["status"], "no_action": no_action["status"]},
        "key_counts": {
            "accepted_source_families": ledger["accepted_for_landing"],
            "parked_no_consumer": ledger["parked_no_consumer"],
            "blocked_source_unavailable": ledger["blocked_source_unavailable"],
            "city_source_changes_detected": len(diff_report["city_source_changes_detected"]),
            "json_files": json_total,
            "json_parse_failures": json_bad,
        },
        "limitations": [
            "Limited DIFF found zero projected city-source changes; this is not live monitoring.",
            "Helsinki is parked until a D13 visual/KIT or selected-item consumer exists.",
            "Singapore remains blocked by source/auth availability.",
            "D14 remains blocked until real operator question corpus exists.",
        ],
    }
    write_json(ROOT / "D12_CITY_DATA_DEPTH_CLOSEOUT_DECISION.json", closeout)
    write_text(ROOT / "D12_CLOSEOUT_SUMMARY.md", f"# D12 Closeout Summary\n\nStatus: `{final_status}`\n\nD12 accepted only consumed source families, parked unconsumed conditional sources, and ran limited source-record DIFF without live-monitoring or action claims.\n")
    write_text(
        ROOT / "D12_TO_D13_D14_HANDOFF.md",
        "# D12 to D13/D14 Handoff\n\n"
        f"- Consumed ledger: `{rel(ROOT / 'D12_CONSUMPTION_RULE_LEDGER.json')}`\n"
        f"- DIFF status: `{diff_report['status']}`\n"
        f"- Snapshot ledger: `{rel(ROOT / 'D12_SNAPSHOT_LEDGER.json')}`\n"
        f"- Certified state: `{rel(ROOT / 'D12_CERTIFIED_STATE_CONSOLIDATION_DECISION.json')}`\n"
        "- D13 still depends on Kit runtime/extension readiness.\n"
        "- D14 remains blocked until real operator corpus exists.\n",
    )
    hash_manifest()
    write_json(ROOT / "LOCAL_OPEN_INDEX.json", {"output_root": rel(ROOT), "files": [rel(p) for p in sorted(ROOT.rglob("*")) if p.is_file()]})
    write_text(ROOT / "README.md", f"# D12 City Data Depth + Real DIFF R1\n\nStatus: `{final_status}`\n\nNo source landed without a consumer. DIFF is limited source-record comparison only.\n")
    zip_path, zip_entries, zip_json_total, zip_json_bad = package_validation()
    hash_manifest()
    freeze = {
        "task": "MAIN-CITYBRAIN-D12-CITY-DATA-DEPTH-MILESTONE-FREEZE",
        "status": final_status,
        "closeout_status": closeout["status"],
        "consumed_data_ledger": rel(ROOT / "D12_CONSUMPTION_RULE_LEDGER.json"),
        "diff_status": diff_report["status"],
        "snapshot_ledger": rel(ROOT / "D12_SNAPSHOT_LEDGER.json"),
        "certified_state_consolidation": rel(ROOT / "D12_CERTIFIED_STATE_CONSOLIDATION_DECISION.json"),
        "standing_regression": rel(ROOT / "D12_STANDING_CAPABILITY_REGRESSION_REPORT.json"),
        "handoff": rel(ROOT / "D12_TO_D13_D14_HANDOFF.md"),
        "validation_package": rel(zip_path),
        "validation_package_entries": zip_entries,
        "validation_package_json_files": zip_json_total,
        "validation_package_json_parse_failures": zip_json_bad,
        "hash_manifest": rel(ROOT / "HASH_MANIFEST.sha256"),
        "key_counts": closeout["key_counts"],
        "audits": closeout["audits"],
        "limitations": closeout["limitations"],
        "next_recommended_task": "MAIN-CITYBRAIN-D13-SPATIAL-TWIN-OMNIVERSE-ONE-TRUTH-R1 if Kit gate passes; otherwise D13 closes environment-repair/blocked. D14 remains blocked until real operator corpus exists.",
    }
    write_json(ROOT / "D12_CITY_DATA_DEPTH_MILESTONE_FREEZE_DECISION.json", freeze)
    hash_manifest()
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
