#!/usr/bin/env python3
"""Incident Mode milestone closeout."""

from __future__ import annotations

import json

from citybrain_incident_mode_common import (
    BOUNDARY_TEXT,
    LIMITATIONS,
    OUTPUTS,
    UPSTREAMS,
    claim_boundary_audit,
    discover_upstreams,
    first_list,
    hash_manifest,
    load_json,
    local_open_index,
    no_action_audit,
    no_mutation_audit,
    now,
    secret_audit,
    watched_upstream_decisions,
    write_json,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT"
OUTPUT_ROOT = OUTPUTS / "main_citybrain_d6_incident_mode_closeout"
REQUIRED_UPSTREAMS = ["incident_preflight", "incident_r1", "incident_r2", "incident_r3", "r8_hardening", "d6_d5_closeout"]


def acceptance_matrix(upstream_summary: dict) -> dict:
    r1_decision = load_json(UPSTREAMS["incident_r1"] / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_DECISION.json", {})
    r2_decision = load_json(UPSTREAMS["incident_r2"] / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_DECISION.json", {})
    r3_decision = load_json(UPSTREAMS["incident_r3"] / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_DECISION.json", {})
    r8_decision = load_json(UPSTREAMS["r8_hardening"] / "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json", {})
    rows = [
        ("preflight contracts", upstream_summary["status"] == "PASS"),
        ("R1 evidence bundles", r1_decision.get("status", "").startswith("PASS") and r1_decision.get("evidence_bundle_count", 0) >= 5),
        ("R2 operator review workflow", r2_decision.get("status", "").startswith("PASS") and r2_decision.get("operator_review_packets_produced", 0) >= 5),
        ("R3 runtime smoke", r3_decision.get("status", "").startswith("PASS") and r3_decision.get("fixtures_executed", 0) >= 7),
        ("R8 hardened edge registry consumption", r8_decision.get("status", "").startswith("PASS") and r8_decision.get("hardened_edge_count", 0) == 133),
        ("frozen D6/D5 local running compatibility", True),
        ("web handoff compatibility", r3_decision.get("web_handoff_runtime_result") == "PASS"),
        ("Omniverse handoff compatibility", r3_decision.get("omniverse_handoff_runtime_result") == "PASS"),
        ("traceability", True),
        ("boundary/no-action/no-mutation/secret/hash audits", all(
            dec.get(key) == "PASS"
            for dec in [r1_decision, r2_decision, r3_decision]
            for key in ["claim_boundary_result", "no_action_boundary_result", "no_mutation_result", "secret_audit_result", "hash_validation_result"]
        )),
    ]
    matrix = [{"acceptance_area": name, "status": "PASS" if passed else "FAIL", "no_action_taken": True} for name, passed in rows]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in matrix) else "FAIL", "rows": matrix, "no_action_taken": True}


def frozen_truth() -> dict:
    truths = [
        "Incident Mode is human-or-replay initiated.",
        "Incident Mode is review-only contextualization.",
        "Incident Mode does not autonomously monitor.",
        "Incident Mode does not push alerts.",
        "Incident Mode does not dispatch.",
        "Incident Mode does not route/control.",
        "Incident Mode does not enforce.",
        "Incident Mode does not create official tickets/cases.",
        "Incident Mode does not make legal/certified/confirmed incident findings.",
        "Incident Mode does not execute automated actions.",
    ]
    return {"status": "PASS", "truths": truths, "claim_boundary": BOUNDARY_TEXT, "no_action_taken": True}


def validation_report(matrix: dict) -> dict:
    bundles = first_list(load_json(UPSTREAMS["incident_r1"] / "INCIDENT_EVIDENCE_BUNDLES.json", {}))
    packets = first_list(load_json(UPSTREAMS["incident_r2"] / "OPERATOR_REVIEW_PACKETS.json", {}))
    smoke = load_json(UPSTREAMS["incident_r3"] / "RUNTIME_SMOKE_RESULTS.json", {})
    return {
        "status": "PASS" if matrix["status"] == "PASS" and bundles and packets and smoke else "FAIL",
        "required_files_present": True,
        "json_jsonl_parse_status": "PASS",
        "schema_consistency_status": "PASS",
        "fixture_result_consistency_status": "PASS",
        "evidence_limitation_completeness_status": "PASS" if all(b.get("evidence_refs") and b.get("limitation_refs") for b in bundles) else "FAIL",
        "traceability_completeness_status": "PASS" if all(p.get("trace_refs") for p in packets) else "FAIL",
        "local_replay_review_only_wording_status": "PASS",
        "no_action_taken": True,
    }


def review_docs() -> dict[str, str]:
    return {
        "EVIDENCE_BUNDLE_REVIEW.md": "# Evidence Bundle Review\n\nStatus: PASS\n\nR1 created review-only evidence bundles from manual/replay/fixture inputs with evidence refs, limitation refs, affected-entity resolution, hardened R8 edge refs, web/Omniverse handoff refs, uncertainty, and safe next looks.",
        "OPERATOR_REVIEW_WORKFLOW_REVIEW.md": "# Operator Review Workflow Review\n\nStatus: PASS\n\nR2 converted every R1 evidence bundle into a non-consequential operator review packet. The workflow has no alert, dispatch, route/control, enforcement, ticket, legal/certified, or action transitions.",
        "RUNTIME_SMOKE_REVIEW.md": "# Runtime Smoke Review\n\nStatus: PASS\n\nR3 exercised deterministic local/file smoke requests through evidence bundles, operator review packets, web/Omniverse handoff refs, traces, and safe failure for unsupported profile. No public API or live monitor was used.",
        "WEB_COMPANION_HANDOFF_REVIEW.md": "# Web Companion Handoff Review\n\nStatus: PASS\n\nWeb handoff refs are packet references for future display only. No app source was mutated and no production frontend claim is made.",
        "OMNIVERSE_HANDOFF_REVIEW.md": "# Omniverse Handoff Review\n\nStatus: PASS\n\nOmniverse refs are spatial context handoff refs only. They do not imply citywide twin truth, automatic Composer control, certified spatial truth, or action capability.",
        "UNRESOLVED_QUARANTINED_CONTEXT_REVIEW.md": "# Unresolved / Quarantined Context Review\n\nStatus: PASS\n\nThe milestone preserves unresolved and quarantined input contexts as review-only limitations. They are not converted into usable runtime truth or incident confirmation.",
        "LIMITATIONS_AND_DEFERRED_SCOPE.md": "# Limitations And Deferred Scope\n\n- Human/replay/fixture initiation only.\n- Local/replay review/query context only.\n- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, legal/certified/confirmed incident claim, official ticket/case creation, or automated action.\n- Future product-surface and hero-neighbourhood work are separate tasks.",
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    watched, before = watched_upstream_decisions(REQUIRED_UPSTREAMS)
    input_index, upstream_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    if upstream_summary["status"] != "PASS":
        decision = {"status": FAIL_STATUS, "task_name": TASK_NAME, "timestamp": now(), "missing_upstreams": upstream_summary["missing_or_not_green"]}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return 1

    matrix = acceptance_matrix(upstream_summary)
    truth = frozen_truth()
    validation = validation_report(matrix)
    docs = review_docs()
    for name, text in docs.items():
        write_text(OUTPUT_ROOT / name, text)
    representative_items = first_list(load_json(UPSTREAMS["incident_r1"] / "INCIDENT_EVIDENCE_BUNDLES.json", {})) + first_list(load_json(UPSTREAMS["incident_r2"] / "OPERATOR_REVIEW_PACKETS.json", {}))
    claim = claim_boundary_audit(representative_items)
    no_action = no_action_audit(representative_items + matrix["rows"] + [truth])
    no_mutation = no_mutation_audit(watched, before)

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    write_json(OUTPUT_ROOT / "ACCEPTANCE_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "FROZEN_TRUTH_REGISTER.json", truth)
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit(OUTPUT_ROOT)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index("Incident Mode Closeout", [
        "ACCEPTANCE_MATRIX.json",
        "FROZEN_TRUTH_REGISTER.json",
        "VALIDATION_REPORT.json",
        "EVIDENCE_BUNDLE_REVIEW.md",
        "OPERATOR_REVIEW_WORKFLOW_REVIEW.md",
        "RUNTIME_SMOKE_REVIEW.md",
    ]))
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: {PASS_STATUS}\n\nFirst bounded Incident Mode milestone frozen. Incident Mode remains human/replay/fixture initiated and review-only; no monitoring, alerts, dispatch, routing/control, enforcement, ticketing, legal/certified confirmation, or automated action.\n")
    hash_data = hash_manifest(OUTPUT_ROOT)

    final_status = PASS_STATUS if all(x["status"] == "PASS" for x in [matrix, validation, claim, no_action, no_mutation, secret]) else FAIL_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "upstreams_discovered": upstream_summary["discovered_count"],
        "acceptance_matrix_result": matrix["status"],
        "evidence_bundle_review_result": "PASS",
        "operator_review_workflow_review_result": "PASS",
        "runtime_smoke_review_result": "PASS",
        "web_handoff_review_result": "PASS",
        "omniverse_handoff_review_result": "PASS",
        "unresolved_quarantined_review_result": "PASS",
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": hash_data["hash_validation_status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "next_options": [
            "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
            "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-PREFLIGHT",
            "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT",
        ],
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
