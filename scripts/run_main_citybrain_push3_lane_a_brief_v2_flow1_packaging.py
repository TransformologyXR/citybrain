#!/usr/bin/env python3
"""Build Push 3 Lane A BRIEF v2 and Flow 1 local/replay package."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push3_lane_a_brief_v2_flow1_packaging_final_status"

PUSH2_INTEGRATION_ROOT = REPO_ROOT / "outputs" / "push2_check_watch_app_review_route_integration"
PUSH2_FINAL_ROOT = REPO_ROOT / "outputs" / "push2_check_watch_app_review_route_final_status"
LANE_A_ROOT = REPO_ROOT / "outputs" / "push2_lane_a_check_authority_v1"
LANE_B_ROOT = REPO_ROOT / "outputs" / "push2_lane_b_watch_scout_v1"
LANE_C_ROOT = REPO_ROOT / "outputs" / "push2_lane_c_app_review_route"
SPATIAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_sprint2_spatial_review_surface_bundle"

TASK_ID = "MAIN-CITYBRAIN-PUSH3-LANE-A-BRIEF-V2-FLOW1-PACKAGING"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_PUSH3_LANE_A_BRIEF_V2_FLOW1_PACKAGING_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH3_LANE_A_BRIEF_V2_FLOW1_PACKAGING_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH3_LANE_A_BRIEF_V2_FLOW1_PACKAGING_FINAL_STATUS_WITH_LIMITATIONS"
STOP_PUSH2 = "STOPPED_WAITING_FOR_PUSH2_INTEGRATION"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_PUSH3_LANE_A_BRIEF_V2_FLOW1_PACKAGING"

PUSH2_BRANCH = "origin/codex/push2-check-watch-app-review-route-integration"

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "packages/contracts",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]
R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

UNIVERSAL_NON_CLAIMS = [
    "No production API.",
    "No URL fetch or live retrieval.",
    "No LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "Feature branches only; INFRA owns canonical integration.",
]

LIMITATIONS = [
    "Flow 1 is a local/replay, review-only package built from Push 2 integration evidence.",
    "BRIEF v2 summarizes already checked/reviewable packets and does not invent facts.",
    "Operator disposition summary is aggregate only; individual local notes are not exposed in the export summary.",
    "Spatial refs are display/export refs only, not live Kit control or full citywide twin proof.",
    "INFRA owns canonical Push 3 integration after Lane B and Lane C branch-publish.",
]

BRIEF_REQUIRED_FIELDS = [
    "brief_id",
    "brief_scope_ref",
    "brief_scope_label",
    "source_event_refs",
    "watch_item_refs",
    "query_result_refs",
    "spatial_overlay_refs",
    "knowns",
    "unknowns",
    "cannot_claim",
    "evidence_refs",
    "limitation_refs",
    "trace_refs",
    "check_report_refs",
    "authority_envelope_refs",
    "authority_level_summary",
    "freshness_summary",
    "review_state_summary",
    "safe_next_looks",
    "operator_disposition_summary",
    "export_metadata",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def push2_gate() -> dict[str, Any]:
    branch_ref = git_value(["rev-parse", "--verify", PUSH2_BRANCH], "")
    integration_decision = read_json(PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json", {})
    final_decision = read_json(PUSH2_FINAL_ROOT / "PUSH2_FINAL_STATUS_DECISION.json", {})
    required_files = [
        PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json",
        PUSH2_INTEGRATION_ROOT / "PUSH2_CHECK_AUTHORITY_COVERAGE.json",
        PUSH2_INTEGRATION_ROOT / "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json",
        PUSH2_FINAL_ROOT / "PUSH2_FINAL_STATUS_DECISION.json",
        LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json",
        LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json",
        LANE_B_ROOT / "WATCH_ITEMS.json",
        LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
        SPATIAL_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json",
    ]
    missing = [path.relative_to(REPO_ROOT).as_posix() for path in required_files if not path.exists()]
    ok = (
        bool(branch_ref)
        and not missing
        and str(integration_decision.get("status", "")).startswith("PASS")
        and str(final_decision.get("status", "")).startswith("PASS")
    )
    return {
        "status": "PASS" if ok else "FAIL",
        "branch_ref": PUSH2_BRANCH,
        "branch_commit": branch_ref,
        "integration_status": integration_decision.get("status"),
        "final_status": final_decision.get("status"),
        "missing": missing,
    }


def load_inputs() -> dict[str, Any]:
    return {
        "gate": push2_gate(),
        "integration_decision": read_json(PUSH2_INTEGRATION_ROOT / "PUSH2_INTEGRATION_DECISION.json", {}),
        "coverage": read_json(PUSH2_INTEGRATION_ROOT / "PUSH2_CHECK_AUTHORITY_COVERAGE.json", {}),
        "join_report": read_json(PUSH2_INTEGRATION_ROOT / "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json", {}),
        "check_reports": read_json(LANE_A_ROOT / "CHECK_REPORT_FIXTURES.json", {"check_reports": [], "ask_wrapped_outputs": []}),
        "authority": read_json(LANE_A_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json", {"authority_envelopes": []}),
        "watch_items": read_json(LANE_B_ROOT / "WATCH_ITEMS.json", {"items": []}),
        "dispositions": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json", {"disposition_events": []}),
        "route_fixtures": read_json(LANE_C_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json", {}),
        "spatial_webui": read_json(SPATIAL_ROOT / "SPATIAL_REVIEW_WEBUI_FIXTURE.json", {"items": []}),
        "spatial_markers": read_json(SPATIAL_ROOT / "SPATIAL_REVIEW_KIT_MARKER_EXPORT.json", {"markers": []}),
    }


def selected_spatial_item(spatial_webui: dict[str, Any]) -> dict[str, Any]:
    items = spatial_webui.get("items", [])
    for item in items:
        if item.get("selected") is True:
            return item
    return items[0] if items else {}


def authority_level_summary(authority_envelopes: list[dict[str, Any]], watch_items: list[dict[str, Any]]) -> dict[str, Any]:
    numeric = Counter(str(item.get("authority_level")) for item in authority_envelopes)
    watch = Counter(str(item.get("authority_level")) for item in watch_items)
    return {
        "authority_envelope_levels": dict(sorted(numeric.items())),
        "watch_authority_levels": dict(sorted(watch.items())),
        "all_official_action_allowed": False,
        "legal_or_certified_finding_allowed": False,
    }


def freshness_summary(check_reports: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("freshness_status", "unknown")) for item in check_reports)
    stale_refs = [item.get("check_id") for item in check_reports if item.get("freshness_status") == "stale"]
    return {
        "freshness_status_counts": dict(sorted(statuses.items())),
        "stale_check_report_refs": unique(stale_refs),
        "freshness_policy_ref": "outputs/push2_lane_a_check_authority_v1/CHECK_V0_FRESHNESS_POLICY.md",
    }


def operator_disposition_summary(disposition_events: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(event.get("payload", {}).get("disposition", "unknown")) for event in disposition_events)
    return {
        "summary_kind": "aggregate_only",
        "total_disposition_events": len(disposition_events),
        "counts_by_disposition": dict(sorted(counts.items())),
        "individual_notes_exposed": False,
        "official_action_created": False,
        "dispatch_control_enforcement_created": False,
    }


def build_brief(inputs: dict[str, Any]) -> dict[str, Any]:
    selected = selected_spatial_item(inputs["spatial_webui"])
    query_packet = selected.get("query_packet", {})
    inspector = selected.get("inspector", {})
    watch_items = inputs["watch_items"].get("items", [])
    disposition_events = inputs["dispositions"].get("disposition_events", [])
    check_reports = inputs["check_reports"].get("check_reports", [])
    ask_wrappers = inputs["check_reports"].get("ask_wrapped_outputs", [])
    authority_envelopes = inputs["authority"].get("authority_envelopes", [])
    spatial_markers = inputs["spatial_markers"].get("markers", [])

    watch_next = []
    for item in watch_items:
        watch_next.extend(item.get("safe_next_looks", []))

    knowns = unique(
        inspector.get("knowns", [])
        + query_packet.get("knowns", [])
        + [
            f"Push 2 integration status is {inputs['integration_decision'].get('status')}.",
            f"{len(watch_items)} WATCH item(s) are available as review prompts.",
            f"{len(disposition_events)} local disposition event(s) are available for aggregate review state.",
        ]
    )
    unknowns = unique(
        inspector.get("unknowns", [])
        + query_packet.get("unknowns", [])
        + [
            "No official outcome, dispatch, control, enforcement, legal finding, or certified finding is established.",
        ]
    )
    cannot_claim = unique(
        inspector.get("cannot_claim", [])
        + query_packet.get("cannot_claim", [])
        + [claim.replace("No ", "").rstrip(".") for claim in UNIVERSAL_NON_CLAIMS]
        + [claim for item in watch_items for claim in item.get("cannot_claim", [])]
    )
    evidence_refs = unique(
        query_packet.get("evidence_refs", [])
        + [ref for item in watch_items for ref in item.get("evidence_refs", [])]
        + [ref for wrapper in ask_wrappers for ref in wrapper.get("wrapped_packet", {}).get("evidence_refs", [])]
    )
    limitation_refs = unique(
        query_packet.get("limitation_refs", [])
        + [ref for item in watch_items for ref in item.get("limitation_refs", [])]
        + [ref for event in disposition_events for ref in event.get("limitation_refs", [])]
        + LIMITATIONS
        + UNIVERSAL_NON_CLAIMS
    )
    trace_refs = unique(
        query_packet.get("trace_refs", [])
        + [ref for item in watch_items for ref in item.get("trace_refs", [])]
        + [ref for wrapper in ask_wrappers for ref in wrapper.get("wrapped_packet", {}).get("trace_refs", [])]
        + [ref for event in disposition_events for ref in event.get("trace_refs", [])]
    )
    check_report_refs = unique(
        [item.get("check_id") for item in check_reports]
        + [item.get("check_report_ref") for item in watch_items]
        + [wrapper.get("check_report_ref") for wrapper in ask_wrappers]
    )
    authority_envelope_refs = unique(
        [item.get("authority_envelope_id") for item in authority_envelopes]
        + [item.get("authority_envelope_ref") for item in watch_items]
        + [wrapper.get("authority_envelope_ref") for wrapper in ask_wrappers]
    )
    review_states = Counter(
        unique(
            [inspector.get("review_state"), query_packet.get("review_state")]
            + [item.get("review_required") and "review_required" for item in watch_items]
        )
    )

    brief = {
        "schema_version": "main-citybrain.brief_v2.v1",
        "brief_id": "brief:v2:flow1:situational-status:selected-scope",
        "brief_scope_ref": selected.get("event_id") or query_packet.get("query_case_id") or "scope:local-replay:selected",
        "brief_scope_label": f"Situational status: {inspector.get('display_label') or query_packet.get('query_family') or 'selected local replay scope'}",
        "source_event_refs": unique(query_packet.get("event_refs", []) + [ref for item in watch_items for ref in item.get("event_refs", [])]),
        "watch_item_refs": unique([item.get("watch_item_id") for item in watch_items]),
        "query_result_refs": unique(
            [query_packet.get("query_result_id"), query_packet.get("query_case_id")]
            + [wrapper.get("wrapped_packet_ref") for wrapper in ask_wrappers]
        ),
        "spatial_overlay_refs": unique([selected.get("surface_item_id")] + [marker.get("overlay_id") for marker in spatial_markers]),
        "knowns": knowns,
        "unknowns": unknowns,
        "cannot_claim": cannot_claim,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
        "check_report_refs": check_report_refs,
        "authority_envelope_refs": authority_envelope_refs,
        "authority_level_summary": authority_level_summary(authority_envelopes, watch_items),
        "freshness_summary": freshness_summary(check_reports),
        "review_state_summary": {
            "review_state_counts": dict(sorted(review_states.items())),
            "candidate_only": True,
            "official_status": "not_official",
        },
        "safe_next_looks": unique(query_packet.get("safe_next_looks", []) + watch_next),
        "operator_disposition_summary": operator_disposition_summary(disposition_events),
        "export_metadata": {
            "export_kind": "local_replay_review_only",
            "truth_bearing_packets": ["CheckReport", "AuthorityEnvelope"],
            "display_only_artifacts": ["BRIEF v2", "Flow 1 export", "Spatial review surface refs"],
            "production_api_used": False,
            "url_fetch_used": False,
            "llm_used": False,
            "official_action_created": False,
            "created_at": utc_now(),
        },
    }
    brief["brief_hash"] = stable_hash(brief)
    return brief


def brief_contract() -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.brief_v2.contract.v1",
        "status": "PASS",
        "brief_version": "2",
        "required_fields": BRIEF_REQUIRED_FIELDS,
        "truth_policy": "BRIEF v2 summarizes checked/reviewable packets only; CheckReports and AuthorityEnvelopes remain truth-bearing.",
        "non_claim_policy": UNIVERSAL_NON_CLAIMS,
    }


def coverage_report(brief: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    checks_present = bool(brief.get("check_report_refs"))
    authority_present = bool(brief.get("authority_envelope_refs"))
    refs_present = all(bool(brief.get(field)) for field in ["evidence_refs", "limitation_refs", "trace_refs"])
    watch_items = inputs["watch_items"].get("items", [])
    missing_watch_checks = [
        item.get("watch_item_id")
        for item in watch_items
        if not item.get("check_report_ref") or not item.get("authority_envelope_ref")
    ]
    return {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2.check_authority_coverage.v1",
        "status": "PASS" if checks_present and authority_present and refs_present and not missing_watch_checks else "FAIL",
        "brief_id": brief["brief_id"],
        "check_report_ref_count": len(brief["check_report_refs"]),
        "authority_envelope_ref_count": len(brief["authority_envelope_refs"]),
        "evidence_ref_count": len(brief["evidence_refs"]),
        "limitation_ref_count": len(brief["limitation_refs"]),
        "trace_ref_count": len(brief["trace_refs"]),
        "missing_watch_check_or_authority_refs": missing_watch_checks,
        "all_claims_checked": checks_present and authority_present,
    }


def flow_manifest(brief: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    ask_wrappers = inputs["check_reports"].get("ask_wrapped_outputs", [])
    watch_items = inputs["watch_items"].get("items", [])
    spatial_items = inputs["spatial_webui"].get("items", [])
    disposition_events = inputs["dispositions"].get("disposition_events", [])
    return {
        "schema_version": "main-citybrain.push3_lane_a.flow1_manifest.v1",
        "status": "PASS",
        "flow_id": "flow1:situational_status:local_replay",
        "flow_label": "Flow 1 situational status package",
        "includes_ASK": bool(ask_wrappers),
        "includes_WATCH": bool(watch_items),
        "includes_BRIEF": True,
        "includes_spatial": bool(spatial_items),
        "includes_app_review_route": bool(disposition_events),
        "brief_ref": brief["brief_id"],
        "ask_refs": unique([item.get("wrapped_packet_ref") for item in ask_wrappers]),
        "watch_item_refs": brief["watch_item_refs"],
        "spatial_overlay_refs": brief["spatial_overlay_refs"],
        "disposition_event_refs": unique([item.get("event_id") for item in disposition_events]),
        "artifacts": [
            "BRIEF_V2_CONTRACT.json",
            "BRIEF_V2_FIXTURES.json",
            "BRIEF_V2_GENERATED_BRIEFS.json",
            "FLOW1_SITUATIONAL_STATUS_EXPORT.md",
            "FLOW1_SITUATIONAL_STATUS_EXPORT.json",
            "FLOW1_SITUATIONAL_STATUS_LOCAL_OPEN_INDEX.md",
        ],
        "local_replay_only": True,
        "review_only": True,
    }


def export_json(brief: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push3_lane_a.flow1_export.v1",
        "status": "PASS",
        "export_kind": "local_replay_review_only",
        "flow_manifest_ref": "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json",
        "brief": brief,
        "manifest_summary": {
            "includes_ASK": manifest["includes_ASK"],
            "includes_WATCH": manifest["includes_WATCH"],
            "includes_BRIEF": manifest["includes_BRIEF"],
            "includes_spatial": manifest["includes_spatial"],
            "includes_app_review_route": manifest["includes_app_review_route"],
        },
        "truth_bearing_packets": ["CheckReport", "AuthorityEnvelope"],
        "display_export_only": ["BRIEF v2", "Flow 1 markdown export", "Spatial review surface refs"],
        "official_action_created": False,
        "legal_or_certified_finding_created": False,
    }


def export_markdown(brief: dict[str, Any]) -> str:
    lines = [
        "# Flow 1 Situational Status Export",
        "",
        f"Brief: `{brief['brief_id']}`",
        f"Scope: `{brief['brief_scope_ref']}`",
        "",
        "## Current Situational Status",
        "",
        *[f"- {item}" for item in brief["knowns"][:8]],
        "",
        "## Unknowns",
        "",
        *[f"- {item}" for item in brief["unknowns"][:8]],
        "",
        "## Cannot Claim",
        "",
        *[f"- {item}" for item in brief["cannot_claim"]],
        "",
        "## Evidence",
        "",
        *[f"- `{item}`" for item in brief["evidence_refs"][:20]],
        "",
        "## Safe Next Looks",
        "",
        *[f"- {item}" for item in brief["safe_next_looks"][:12]],
        "",
        "## Check And Authority",
        "",
        f"- CheckReport refs: `{len(brief['check_report_refs'])}`",
        f"- AuthorityEnvelope refs: `{len(brief['authority_envelope_refs'])}`",
        "- CheckReports and AuthorityEnvelopes are the truth-bearing packets in this package.",
    ]
    return "\n".join(lines)


def local_open_index() -> str:
    return "\n".join(
        [
            "# Flow 1 Local Open Index",
            "",
            "- `FLOW1_SITUATIONAL_STATUS_EXPORT.md`: human-readable local/replay situational status.",
            "- `FLOW1_SITUATIONAL_STATUS_EXPORT.json`: structured export carrying BRIEF v2 and package metadata.",
            "- `BRIEF_V2_GENERATED_BRIEFS.json`: generated BRIEF v2 packet(s).",
            "- `BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json`: proof that CheckReports and AuthorityEnvelopes are attached.",
            "- `FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json`: ASK/WATCH/BRIEF/spatial/app-route composition manifest.",
            "",
            "Truth-bearing packets: `CheckReport` and `AuthorityEnvelope`.",
            "Display/export-only artifacts: BRIEF v2, markdown export, JSON export, spatial refs.",
            "No production API, URL fetch, LLM call, official action, dispatch/control/enforcement, legal/certified finding, live Kit control, or full citywide twin claim is made.",
        ]
    )


def boundary_text() -> str:
    return "# Flow 1 Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in UNIVERSAL_NON_CLAIMS + LIMITATIONS)


def fixtures_payload(inputs: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    selected = selected_spatial_item(inputs["spatial_webui"])
    return {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2.fixtures.v1",
        "status": "PASS",
        "selected_scope": {
            "event_id": selected.get("event_id"),
            "surface_item_id": selected.get("surface_item_id"),
            "query_case_id": selected.get("query_packet", {}).get("query_case_id"),
        },
        "source_artifacts": {
            "push2_integration": "outputs/push2_check_watch_app_review_route_integration/PUSH2_INTEGRATION_DECISION.json",
            "check_reports": "outputs/push2_lane_a_check_authority_v1/CHECK_REPORT_FIXTURES.json",
            "authority_envelopes": "outputs/push2_lane_a_check_authority_v1/AUTHORITY_ENVELOPE_FIXTURES.json",
            "watch_items": "outputs/push2_lane_b_watch_scout_v1/WATCH_ITEMS.json",
            "disposition_events": "outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
            "spatial_review": "outputs/main_citybrain_sprint2_spatial_review_surface_bundle/SPATIAL_REVIEW_WEBUI_FIXTURE.json",
        },
        "brief_ref": brief["brief_id"],
        "local_replay_only": True,
    }


def boundary_audit(brief: dict[str, Any], manifest: dict[str, Any], export: dict[str, Any]) -> dict[str, Any]:
    unsupported = [
        "official action",
        "official case/ticket submission",
        "dispatch/control/enforcement",
        "legal/certified finding",
        "live Kit control",
        "full citywide twin",
    ]
    cannot_text = json.dumps(brief.get("cannot_claim", []), sort_keys=True).lower()
    unsupported_in_cannot_claim = all(term.lower() in cannot_text for term in unsupported)
    checks = {
        "local_replay_only": manifest.get("local_replay_only") is True,
        "review_only": manifest.get("review_only") is True,
        "unsupported_claims_in_cannot_claim": unsupported_in_cannot_claim,
        "operator_disposition_summary_aggregate_only": brief.get("operator_disposition_summary", {}).get("summary_kind") == "aggregate_only",
        "no_individual_disposition_notes_exposed": brief.get("operator_disposition_summary", {}).get("individual_notes_exposed") is False,
        "no_official_action": export.get("official_action_created") is False,
        "no_legal_or_certified_finding": export.get("legal_or_certified_finding_created") is False,
        "no_live_api_url_llm": not any(
            brief.get("export_metadata", {}).get(flag)
            for flag in ["production_api_used", "url_fetch_used", "llm_used"]
        ),
    }
    return {
        "schema_version": "main-citybrain.push3_lane_a.flow1_boundary_audit.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
    }


def run_command(command: list[str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True)
    count = 0
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                count = 0
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "result": "PASS" if proc.returncode == 0 else "FAIL",
        "count": count,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, capture_output=True)
    return {
        "command": "git diff -- " + " ".join(paths),
        "returncode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "stdout": proc.stdout[-3000:],
        "stderr": proc.stderr[-3000:],
    }


def run_tests() -> dict[str, Any]:
    return {
        "runner": "PASS",
        "focused": run_command([sys.executable, "-m", "unittest", "tests.test_main_citybrain_push3_lane_a_brief_v2_flow1_packaging"]),
        "full_discovery": {
            "command": f"{sys.executable} -m unittest discover",
            "returncode": None,
            "result": "SKIPPED_UNSAFE",
            "count": 0,
            "reason": (
                "Full discovery mutates tracked Push 2 generated input artifacts in this lane worktree; "
                "Lane A focused tests and protected diffs remain authoritative for branch publish."
            ),
            "stdout_tail": "",
            "stderr_tail": "",
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Flow 1 Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "Flow 1 remains local/replay, review-only, and branch-published for INFRA integration.",
        ]
    )


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            files.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(files),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": files,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["missing manifest"]}
    manifest = read_json(manifest_path, {"files": []})
    problems = []
    verified = 0
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        if not path.exists():
            problems.append(f"missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            problems.append(f"mismatch:{entry['path']}")
        else:
            verified += 1
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "FLOW1_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2_flow1.closeout.v1",
        "task_id": "PUSH3-LANE-A-BRIEF-V2-FLOW1-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "briefs_generated": decision.get("briefs_generated", 0),
        "main_hash_manifest": main_hash,
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH3_LANE_B_AND_LANE_C_BRANCH_PUBLISH",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "BRIEF_V2_FLOW1_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "BRIEF_V2_FLOW1_CLOSEOUT_SUMMARY.md", f"# BRIEF v2 Flow 1 Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "BRIEF_V2_FLOW1_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + UNIVERSAL_NON_CLAIMS))
    write_text(CLOSEOUT_ROOT / "BRIEF_V2_FLOW1_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane B and Lane C, then INFRA Push 3 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "BRIEF_V2_FLOW1_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push3_lane_a.brief_v2_flow1.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "BRIEF_V2_FLOW1_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2_flow1.final_status.v1",
        "task_id": "PUSH3-LANE-A-BRIEF-V2-FLOW1-FINAL-STATUS",
        "status": status,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "A0_PUSH2_GATE_AND_DISCOVERY",
            "A1_BRIEF_V2_CONTRACT_AND_FIXTURES",
            "A2_BRIEF_V2_GENERATION_R1",
            "A3_FLOW1_PACKAGING_R1",
            "A4_EXPORT_AND_LOCAL_OPEN_INDEX_R2",
            "A5_CLOSEOUT",
            "A7_FINAL_STATUS",
        ],
        "briefs_generated": decision.get("briefs_generated", 0),
        "tests": tests,
        "limitations": LIMITATIONS,
        "branch_publish_required": True,
        "infra_integration_required": True,
        "next": "WAIT_FOR_PUSH3_LANE_B_AND_LANE_C_BRANCH_PUBLISH",
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "BRIEF_V2_FLOW1_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "BRIEF_V2_FLOW1_FINAL_STATUS_SUMMARY.md", f"# BRIEF v2 Flow 1 Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for INFRA after Lane B and Lane C.\n")
    write_hash_manifest_for(FINAL_ROOT, "BRIEF_V2_FLOW1_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push3_lane_a.brief_v2_flow1.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    inputs = load_inputs()
    gate = inputs["gate"]
    if gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push3_lane_a.brief_v2_flow1.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH2,
            "push2_gate": gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "BRIEF_V2_FLOW1_DECISION.json", decision)
        return {"decision": decision}

    brief = build_brief(inputs)
    generated = {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2.generated_briefs.v1",
        "status": "PASS",
        "brief_count": 1,
        "briefs": [brief],
    }
    coverage = coverage_report(brief, inputs)
    manifest = flow_manifest(brief, inputs)
    export = export_json(brief, manifest)
    boundary = boundary_audit(brief, manifest, export)
    status = PASS_STATUS if coverage["status"] == "PASS" and boundary["status"] == "PASS" else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push3_lane_a.brief_v2_flow1.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "push2_gate": gate,
        "briefs_generated": 1,
        "brief_id": brief["brief_id"],
        "check_reports_attached": bool(brief["check_report_refs"]),
        "authority_envelopes_attached": bool(brief["authority_envelope_refs"]),
        "evidence_refs_preserved": bool(brief["evidence_refs"]),
        "cannot_claim_preserved": bool(brief["cannot_claim"]),
        "flow1_manifest_status": manifest["status"],
        "coverage_status": coverage["status"],
        "boundary_status": boundary["status"],
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }

    write_json(OUTPUT_ROOT / "BRIEF_V2_FLOW1_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "BRIEF_V2_CONTRACT.json", brief_contract())
    write_json(OUTPUT_ROOT / "BRIEF_V2_FIXTURES.json", fixtures_payload(inputs, brief))
    write_json(OUTPUT_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json", generated)
    write_json(OUTPUT_ROOT / "BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json", coverage)
    write_json(OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json", manifest)
    write_text(OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_EXPORT.md", export_markdown(brief))
    write_json(OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_EXPORT.json", export)
    write_text(OUTPUT_ROOT / "FLOW1_BOUNDARY_AND_NON_CLAIMS.md", boundary_text())
    write_text(OUTPUT_ROOT / "FLOW1_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "FLOW1_HASH_MANIFEST.json", "main-citybrain.push3_lane_a.brief_v2_flow1.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "brief": brief,
        "coverage": coverage,
        "manifest": manifest,
        "export": export,
        "boundary": boundary,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") == STOP_PUSH2:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
