#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PACKAGE_ID = "MAIN-CITYBRAIN-POST-E3-CLOSEOUT-EPOCH4-FORK-PREFLIGHT-R1"
STATUS = "PASS_POST_E3_EPOCH4_FORK_PREFLIGHT_R1_WITH_LIMITATIONS"
CLOSEOUT_TYPE = "POST_E3_PREPARATION_NOT_EPOCH4_START"
CLOSEOUT_PACKAGE_ID = "MAIN-CITYBRAIN-EPOCH3-CLOSEOUT-R1"

OUTPUT_ROOT = REPO_ROOT / "outputs" / "post_e3_epoch4_fork_preflight_r1"
POST_E3_PUBLICATION_ROOT = REPO_ROOT / "publications" / "post_e3"
PUBLICATION_DIR = POST_E3_PUBLICATION_ROOT / "main-citybrain-post-e3-closeout-epoch4-fork-preflight-r1"
E3_PUBLICATION_ROOT = REPO_ROOT / "publications" / "epoch3"
E3_CLOSEOUT_PUBLICATION = E3_PUBLICATION_ROOT / "main-citybrain-epoch3-closeout-r1"
E3_CLOSEOUT_OUTPUT = REPO_ROOT / "outputs" / "epoch3_closeout_r1"

TEXT_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}

REQUIRED_OUTPUTS = (
    "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION.json",
    "POST_E3_CLOSEOUT_ARTIFACT_READINESS_REPORT.json",
    "E4_FORK_DECISION_TEMPLATE.json",
    "E4_ARMING_INHERITANCE_HANDOFF.json",
    "E4_GO_LIVE_REVIEW_PILOT_PATH_SPEC.json",
    "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json",
    "E4_HYBRID_PATH_SPEC.json",
    "E4_DEFERRED_PATH_SPEC.json",
    "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST.json",
    "E4_BACKLOG_HANDOFF.json",
    "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "E4_PUBLICATION_GOVERNANCE_CONTINUITY_ROW.json",
    "POST_E3_EPOCH4_FORK_LIMITATIONS.json",
    "POST_E3_EPOCH4_FORK_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
)

READINESS_INPUTS = {
    "closeout_decision": "E3_CLOSEOUT_DECISION.json",
    "master_ledger": "E3_MASTER_LEDGER.json",
    "learned_component_registry_snapshot": "E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json",
    "arming_handoff": "E3_ARMING_HANDOFF_TO_EPOCH4.json",
    "epoch4_fork_backlog": "E3_EPOCH4_FORK_DECISION_ROW.json",
    "fuel_reality": "E3_FUEL_REALITY_FINDING_ROW.json",
    "forecast_result_framing": "E3_FORECAST_RESULT_FRAMING_ROW.json",
    "no_forbidden_capability_audit": "E3_NO_FORBIDDEN_CAPABILITY_AUDIT.json",
    "closeout_limitations": "E3_CLOSEOUT_LIMITATIONS.json",
}

ALLOWED_FORK_VALUES = [
    "GO_LIVE_REVIEW_PILOT",
    "NONLIVE_MECHANICAL_BACKLOG",
    "HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG",
    "DEFER_EPOCH4_START",
]

DEFERRED_CAPABILITIES = [
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "PRODUCT_FORECAST_SURFACE",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
]

PARKED_ITEMS = [
    "dynamic investigation",
    "cross-city learned transfer",
    "product forecast surface",
    "operator-facing ranking",
    "case-memory learner",
    "learned counterfactuals",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gitattributes_has_publication_lf_rule() -> bool:
    attrs = REPO_ROOT / ".gitattributes"
    if not attrs.exists():
        return False
    return "publications/** text eol=lf" in attrs.read_text(encoding="utf-8")


def load_e3_closeout_artifact(name: str) -> dict[str, Any]:
    publication_path = E3_CLOSEOUT_PUBLICATION / name
    if publication_path.exists():
        return read_json(publication_path, {})
    return read_json(E3_CLOSEOUT_OUTPUT / name, {})


def closeout_artifact_readiness_report() -> dict[str, Any]:
    artifacts = []
    missing_durable = []
    for label, filename in READINESS_INPUTS.items():
        publication_path = E3_CLOSEOUT_PUBLICATION / filename
        output_path = E3_CLOSEOUT_OUTPUT / filename
        durable = publication_path.exists()
        artifacts.append(
            {
                "artifact_key": label,
                "filename": filename,
                "publication_path": rel(publication_path) if durable else None,
                "output_fallback_path": rel(output_path) if output_path.exists() else None,
                "durable_in_publication_home": durable,
                "fallback_available": output_path.exists(),
            }
        )
        if not durable:
            missing_durable.append(filename)

    closeout_decision = load_e3_closeout_artifact("E3_CLOSEOUT_DECISION.json")
    durable = E3_CLOSEOUT_PUBLICATION.exists() and not missing_durable
    return {
        "artifact_id": "POST_E3_CLOSEOUT_ARTIFACT_READINESS_REPORT",
        "package_id": PACKAGE_ID,
        "created_at": utc_now(),
        "status": "PASS_E3_CLOSEOUT_PUBLICATION_HOME_READY" if durable else "PASS_WITH_PUBLICATION_LIMITATIONS",
        "e3_closeout_package_id": CLOSEOUT_PACKAGE_ID,
        "e3_closeout_status": closeout_decision.get("status"),
        "e3_closeout_publication_home": rel(E3_PUBLICATION_ROOT) if E3_PUBLICATION_ROOT.exists() else None,
        "e3_closeout_publication_path": rel(E3_CLOSEOUT_PUBLICATION) if E3_CLOSEOUT_PUBLICATION.exists() else None,
        "publication_home_durable": durable,
        "artifact_count": len(artifacts),
        "durable_artifact_count": sum(1 for item in artifacts if item["durable_in_publication_home"]),
        "missing_durable_artifacts": missing_durable,
        "artifacts": artifacts,
        "limitation": None if durable else "One or more Epoch 3 closeout artifacts were only available outside the publication home.",
    }


def fork_decision_template() -> dict[str, Any]:
    return {
        "decision_id": "E4_FORK_DECISION",
        "package_id": PACKAGE_ID,
        "decision_owner": "human_product_owner",
        "decision_required": True,
        "allowed_values": ALLOWED_FORK_VALUES,
        "selected_value": None,
        "decision_rationale": None,
        "signed_by": None,
        "signed_at": None,
        "epoch4_started_by_this_template": False,
        "codex_may_select_value": False,
        "notes": "Codex must not select this value automatically.",
    }


def arming_inheritance_handoff() -> dict[str, Any]:
    e3_handoff = load_e3_closeout_artifact("E3_ARMING_HANDOFF_TO_EPOCH4.json")
    inherited = e3_handoff.get(
        "inherited_infrastructure",
        [
            "arming_status_evaluator",
            "fuel_gauge_snapshot_chain",
            "threshold_definitions",
            "no_model_guard_cadence",
        ],
    )
    return {
        "handoff_id": "E4_ARMING_INHERITANCE_HANDOFF",
        "package_id": PACKAGE_ID,
        "inherits_from": CLOSEOUT_PACKAGE_ID,
        "source_artifact": rel(E3_CLOSEOUT_PUBLICATION / "E3_ARMING_HANDOFF_TO_EPOCH4.json")
        if (E3_CLOSEOUT_PUBLICATION / "E3_ARMING_HANDOFF_TO_EPOCH4.json").exists()
        else None,
        "evaluator_inherited": True,
        "thresholds_inherited": True,
        "fuel_gauge_snapshot_chain_inherited": True,
        "no_model_guard_cadence_inherited": True,
        "inherited_infrastructure": inherited,
        "thresholds_changed": False,
        "threshold_changes_require_governance_delta": True,
        "operator_paced_fuel_program": "blocked_until_live_or_structured_review_pilot",
        "ranking_memory_loop_fuel_requirement": "live_or_structured_review_operator_dispositions",
        "codex_work_can_substitute_for_operator_dispositions": False,
        "deferred_capabilities": DEFERRED_CAPABILITIES,
    }


def path_spec(path_id: str, summary: str, first_packages: list[str], *, live_fuel: bool, mechanical: bool) -> dict[str, Any]:
    return {
        "path_id": path_id,
        "package_id": PACKAGE_ID,
        "summary": summary,
        "human_selection_required": True,
        "selected_by_this_package": False,
        "epoch4_started_by_this_package": False,
        "operator_or_structured_review_fuel_can_accumulate": live_fuel,
        "nonlive_mechanical_work_allowed": mechanical,
        "can_arm_r3a_r3b_l4_from_codex_only": False,
        "ranking_memory_loops_require_operator_dispositions": True,
        "product_forecast_surface_allowed": False,
        "first_package_candidates_after_selection": first_packages,
    }


def all_path_specs() -> dict[str, dict[str, Any]]:
    return {
        "E4_GO_LIVE_REVIEW_PILOT_PATH_SPEC.json": path_spec(
            "GO_LIVE_REVIEW_PILOT",
            "Start real or structured review sessions so operator fuel can accumulate under inherited thresholds.",
            [
                "MAIN-CITYBRAIN-EPOCH4-REVIEW-PILOT-LAUNCH-R1",
                "MAIN-CITYBRAIN-EPOCH4-FUEL-GAUGE-WEEKLY-SNAPSHOT-R1",
                "MAIN-CITYBRAIN-EPOCH4-L1-L4-ARMING-READINESS-R1",
            ],
            live_fuel=True,
            mechanical=True,
        )
        | {
            "required_human_commitments": [
                "review_session_scope",
                "operator_disposition_capture",
                "cadenced_fuel_gauge_publication",
            ],
            "arming_effect": "May accumulate fuel; arming remains governed by inherited evaluator and thresholds.",
        },
        "E4_NONLIVE_MECHANICAL_BACKLOG_PATH_SPEC.json": path_spec(
            "NONLIVE_MECHANICAL_BACKLOG",
            "Keep system non-live and execute offline/mechanical backlog only.",
            [
                "MAIN-CITYBRAIN-EPOCH4-NONLIVE-MECHANICAL-BACKLOG-BATCH-R1",
                "MAIN-CITYBRAIN-EPOCH4-L2-CITY-STRATIFIED-FORECAST-IMPROVEMENT-R2",
                "MAIN-CITYBRAIN-EPOCH4-CHECK-DESCRIPTIVE-SCORECARD-R1",
            ],
            live_fuel=False,
            mechanical=True,
        )
        | {
            "blocked_fuel_effect": "No new operator fuel; R3A/R3B/L4 operator-fuel-dependent capabilities remain unarmed.",
            "mechanical_scope": [
                "city-stratified L2 forecast improvement",
                "transition target materialization",
                "content-backed L4 stubs",
                "CHECK descriptive scorecards",
                "identity/graph evaluation fixtures",
                "simulation/backtest input catalog",
            ],
        },
        "E4_HYBRID_PATH_SPEC.json": path_spec(
            "HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG",
            "Run a small review pilot while continuing non-live mechanical backlog work.",
            [
                "MAIN-CITYBRAIN-EPOCH4-REVIEW-PILOT-LAUNCH-R1",
                "MAIN-CITYBRAIN-EPOCH4-NONLIVE-MECHANICAL-BACKLOG-BATCH-R1",
                "MAIN-CITYBRAIN-EPOCH4-FUEL-GAUGE-WEEKLY-SNAPSHOT-R1",
            ],
            live_fuel=True,
            mechanical=True,
        )
        | {
            "separation_rule": "Pilot-derived operator fuel and non-live mechanical artifacts must remain provenance-separated.",
            "arming_effect": "Fuel can accumulate only from the review-pilot stream; mechanical work cannot be counted as live usage fuel.",
        },
        "E4_DEFERRED_PATH_SPEC.json": path_spec(
            "DEFER_EPOCH4_START",
            "Do not start Epoch 4 execution; maintain publication and arming infrastructure only.",
            ["MAIN-CITYBRAIN-POST-E3-PUBLICATION-MAINTENANCE-R1"],
            live_fuel=False,
            mechanical=False,
        )
        | {
            "maintenance_scope": [
                "publication-home integrity checks",
                "hash and line-ending stability checks",
                "no-model guard cadence",
            ],
            "arming_effect": "No new fuel and no new Epoch 4 capability arming.",
        },
    }


def first_package_sequence_manifest() -> dict[str, Any]:
    return {
        "manifest_id": "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST",
        "package_id": PACKAGE_ID,
        "depends_on_human_fork_decision": True,
        "selected_sequence": None,
        "epoch4_started_by_this_manifest": False,
        "if_GO_LIVE_REVIEW_PILOT": [
            "MAIN-CITYBRAIN-EPOCH4-REVIEW-PILOT-LAUNCH-R1",
            "MAIN-CITYBRAIN-EPOCH4-FUEL-GAUGE-WEEKLY-SNAPSHOT-R1",
            "MAIN-CITYBRAIN-EPOCH4-L1-L4-ARMING-READINESS-R1",
        ],
        "if_NONLIVE_MECHANICAL_BACKLOG": [
            "MAIN-CITYBRAIN-EPOCH4-NONLIVE-MECHANICAL-BACKLOG-BATCH-R1",
            "MAIN-CITYBRAIN-EPOCH4-L2-CITY-STRATIFIED-FORECAST-IMPROVEMENT-R2",
            "MAIN-CITYBRAIN-EPOCH4-CHECK-DESCRIPTIVE-SCORECARD-R1",
        ],
        "if_HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG": [
            "MAIN-CITYBRAIN-EPOCH4-REVIEW-PILOT-LAUNCH-R1",
            "MAIN-CITYBRAIN-EPOCH4-NONLIVE-MECHANICAL-BACKLOG-BATCH-R1",
            "MAIN-CITYBRAIN-EPOCH4-FUEL-GAUGE-WEEKLY-SNAPSHOT-R1",
        ],
        "if_DEFER_EPOCH4_START": ["MAIN-CITYBRAIN-POST-E3-PUBLICATION-MAINTENANCE-R1"],
    }


def backlog_handoff() -> dict[str, Any]:
    return {
        "backlog_id": "E4_BACKLOG_HANDOFF",
        "package_id": PACKAGE_ID,
        "live_review_pilot_dependent": [
            "operator_fuel_program",
            "R3A/R3B ranking arming",
            "L4 aggregation floor",
            "true CHECK calibration from operator-resolved pairs",
        ],
        "nonlive_mechanical": [
            "L2 city-stratified forecast improvement R2",
            "additional transition targets: inspection_delay_v0, violation_resolution_delay_v0, watch_queue_aging_v0, incident_duration_v0, backlog_clearance_time_v0",
            "L4 content-stub materialization from verified candidates",
            "CHECK descriptive scorecard",
            "identity/graph eval fixture promotion",
            "simulation/backtest input catalog",
            "source-refresh longitudinal gap inventory",
            "federation/cross-city comparable artifact catalog without learned transfer",
        ],
        "parked": PARKED_ITEMS,
        "operator_fuel_blocked_without_live_or_review_pilot": True,
        "nonlive_work_cannot_close_ranking_or_memory_loops": True,
    }


def no_forbidden_capability_guard() -> dict[str, Any]:
    return {
        "artifact_id": "E4_NO_FORBIDDEN_CAPABILITY_GUARD",
        "package_id": PACKAGE_ID,
        "status": "PASS",
        "allowed_existing_experimental_component": "forecast.permit_stall_v0.r1",
        "allowed_existing_experimental_component_status": "carried_forward_frozen_replay_only_no_release_row",
        "new_models_created": 0,
        "new_model_training_created": False,
        "new_training_rows_created": 0,
        "new_learned_registry_entries": 0,
        "ranker_created": False,
        "forecast_model_created": False,
        "product_forecast_surface_created": False,
        "product_forecast_packet_created": False,
        "operator_facing_forecast_created": False,
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "dynamic_investigation_created": False,
        "cross_city_learned_transfer_created": False,
        "training_fuel_promoted_from_scout_outputs": False,
        "operator_dispositions_fabricated": False,
        "forbidden_capabilities_created": [],
    }


def publication_governance_continuity_row(readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "E4_PUBLICATION_GOVERNANCE_CONTINUITY_ROW",
        "package_id": PACKAGE_ID,
        "status": "PASS" if readiness["publication_home_durable"] and gitattributes_has_publication_lf_rule() else "PASS_WITH_LIMITATIONS",
        "e3_publication_home": rel(E3_PUBLICATION_ROOT),
        "e3_closeout_publication_path": rel(E3_CLOSEOUT_PUBLICATION),
        "post_e3_publication_home": rel(POST_E3_PUBLICATION_ROOT),
        "post_e3_publication_path": rel(PUBLICATION_DIR),
        "outputs_are_gitignored_and_not_authoritative": True,
        "publication_home_required_for_governance_artifacts": True,
        "publication_lf_rule_present": gitattributes_has_publication_lf_rule(),
        "hash_manifest_required": True,
        "line_ending_report_required": True,
    }


def limitations() -> dict[str, Any]:
    return {
        "artifact_id": "POST_E3_EPOCH4_FORK_LIMITATIONS",
        "package_id": PACKAGE_ID,
        "status": "LIMITATIONS_RECORDED",
        "limitations": [
            "This package does not choose the Epoch 4 fork.",
            "Epoch 4 is not started automatically.",
            "The system is not live; operator-paced fuel remains blocked unless a live or structured-review pilot is selected.",
            "Non-live mechanical work can proceed but cannot arm R3A/R3B or L4 operator-fuel-dependent capabilities.",
            "The existing L2 forecast component remains experimental, frozen-replay-only, and not product deployable.",
            "City divergence requires city-stratified forecast improvement before any future forecast authority work.",
            "Dynamic investigation and cross-city learned transfer remain parked.",
        ],
    }


def preflight_decision(readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION",
        "package_id": PACKAGE_ID,
        "status": STATUS,
        "closeout_type": CLOSEOUT_TYPE,
        "created_at": utc_now(),
        "depends_on": CLOSEOUT_PACKAGE_ID,
        "e3_closeout_status": readiness["e3_closeout_status"],
        "e3_publication_home_durable": readiness["publication_home_durable"],
        "human_fork_decision_made": False,
        "human_fork_decision_required": True,
        "selected_fork": None,
        "epoch4_started": False,
        "new_models_created": 0,
        "new_training_rows_created": 0,
        "new_learned_registry_entries": 0,
        "product_surfaces_created": 0,
        "forbidden_capabilities_created": [],
        "next_required_human_decision": "E4_FORK_DECISION_TEMPLATE",
        "publication_path": rel(PUBLICATION_DIR),
    }


def ledger_row(decision: dict[str, Any]) -> dict[str, Any]:
    proof_artifacts = [name for name in REQUIRED_OUTPUTS if name not in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}]
    return {
        "artifact_id": "POST_E3_EPOCH4_FORK_LEDGER_ROW",
        "package_id": PACKAGE_ID,
        "status": decision["status"],
        "closeout_type": CLOSEOUT_TYPE,
        "publication_path": rel(PUBLICATION_DIR),
        "proof_artifacts": [f"{rel(OUTPUT_ROOT)}/{name}" for name in proof_artifacts],
        "human_decision_required_next": True,
        "selected_fork": None,
        "epoch4_started": False,
        "boundary_outcome": "no_epoch4_start_no_new_learned_or_product_capability",
        "limitations_ref": f"{rel(OUTPUT_ROOT)}/POST_E3_EPOCH4_FORK_LIMITATIONS.json",
    }


def write_readme() -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        "\n".join(
            [
                "# Post-E3 / Epoch 4 Fork Preflight R1",
                "",
                f"Package: `{PACKAGE_ID}`",
                f"Status: `{STATUS}`",
                "",
                "This preflight prepares the human-owned Epoch 4 fork decision. It does not start Epoch 4, choose a path, create training rows, add learned registry entries, or expose product forecast/ranking/case-memory surfaces.",
                "",
            ]
        ),
    )


def sync_publication() -> list[str]:
    PUBLICATION_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(OUTPUT_ROOT.iterdir(), key=lambda p: p.name):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        target = PUBLICATION_DIR / path.name
        shutil.copyfile(path, target)
        copied.append(rel(target))
    write_json(
        PUBLICATION_DIR / "PUBLICATION_SUMMARY.json",
        {
            "artifact_id": "PUBLICATION_SUMMARY",
            "package_id": PACKAGE_ID,
            "status": "PUBLISHED",
            "created_at": utc_now(),
            "source_root": rel(OUTPUT_ROOT),
            "publication_path": rel(PUBLICATION_DIR),
            "copied_files": copied,
        },
    )
    return copied


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for root in [OUTPUT_ROOT, PUBLICATION_DIR]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            data = path.read_bytes()
            crlf_count = data.count(b"\r\n")
            checked.append({"path": rel(path), "bytes": len(data), "crlf_count": crlf_count})
            if crlf_count:
                crlf_paths.append(rel(path))
    return {
        "artifact_id": "LINE_ENDING_REPORT",
        "package_id": PACKAGE_ID,
        "status": "PASS_LF_STABLE_FOR_POST_E3_EPOCH4_FORK_PREFLIGHT_R1" if not crlf_paths else "FAIL_CRLF_PRESENT",
        "created_at": utc_now(),
        "checked_files": checked,
        "crlf_paths": crlf_paths,
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "HASH_MANIFEST",
        "package_id": PACKAGE_ID,
        "schema_version": "citybrain.hash_manifest.v1",
        "created_at": utc_now(),
        "artifact_root": rel(OUTPUT_ROOT),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    readiness = closeout_artifact_readiness_report()
    decision = preflight_decision(readiness)
    handoff = arming_inheritance_handoff()
    sequence = first_package_sequence_manifest()
    backlog = backlog_handoff()
    guard = no_forbidden_capability_guard()
    continuity = publication_governance_continuity_row(readiness)
    limits = limitations()
    ledger = ledger_row(decision)

    payloads = {
        "POST_E3_EPOCH4_FORK_PREFLIGHT_DECISION.json": decision,
        "POST_E3_CLOSEOUT_ARTIFACT_READINESS_REPORT.json": readiness,
        "E4_FORK_DECISION_TEMPLATE.json": fork_decision_template(),
        "E4_ARMING_INHERITANCE_HANDOFF.json": handoff,
        "E4_FIRST_PACKAGE_SEQUENCE_MANIFEST.json": sequence,
        "E4_BACKLOG_HANDOFF.json": backlog,
        "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json": guard,
        "E4_PUBLICATION_GOVERNANCE_CONTINUITY_ROW.json": continuity,
        "POST_E3_EPOCH4_FORK_LIMITATIONS.json": limits,
        "POST_E3_EPOCH4_FORK_LEDGER_ROW.json": ledger,
    }
    payloads.update(all_path_specs())

    for filename, payload in payloads.items():
        write_json(OUTPUT_ROOT / filename, payload)
    write_readme()

    sync_publication()
    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)
    hash_manifest = build_hash_manifest()
    sync_publication()
    lf = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf)
    hash_manifest = build_hash_manifest()
    sync_publication()

    return {
        "decision": decision,
        "readiness": readiness,
        "handoff": handoff,
        "sequence": sequence,
        "backlog": backlog,
        "guard": guard,
        "continuity": continuity,
        "limitations": limits,
        "ledger": ledger,
        "line_endings": lf,
        "hash_manifest": hash_manifest,
        "publication_files": [rel(PUBLICATION_DIR / name) for name in REQUIRED_OUTPUTS if (PUBLICATION_DIR / name).exists()],
    }


def main() -> int:
    result = write_all_outputs()
    print(f"Post-E3 Epoch 4 fork preflight: {result['decision']['status']}")
    print(f"Human fork selected: {result['decision']['human_fork_decision_made']}")
    print(f"E3 closeout publication durable: {result['readiness']['publication_home_durable']}")
    print(f"Publication: {rel(PUBLICATION_DIR)}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if result["decision"]["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
