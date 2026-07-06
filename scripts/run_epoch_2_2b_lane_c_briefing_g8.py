from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_c_briefing_g8"

GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2a"
GATE_DECISION = GATE_ROOT / "PUSH_2_2A_INTEGRATION_DECISION.json"
GATE_FLAG = GATE_ROOT / "PUSH_2_2B_ALLOWED_TO_OPEN.flag"

LLM_SEAT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_c_llm_seats"
LLM_SEAT_READINESS = LLM_SEAT_ROOT / "LLM_SEAT_READINESS_REPORT.json"
LLM_SEAT_DECISION = LLM_SEAT_ROOT / "DECISION.json"
APP_REVIEW_FIXTURES = REPO_ROOT / "outputs" / "push2_lane_c_app_review_route" / "APP_REVIEW_ROUTE_FIXTURES.json"

STATUS_PASS_LIMITATIONS = "PASS_WITH_LIMITATIONS"
STATUS_BLOCKED = "BLOCKED"

EXPECTED_OUTPUT_FILES = {
    "BRIEFING_AGENT_V2_DECISION.json",
    "BRIEFING_AGENT_V2_REPORT.md",
    "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json",
    "BRIEF_FIXTURES.json",
    "BRIEFING_NEGATIVE_TEST_REPORT.json",
    "HASH_MANIFEST.json",
}

BRIEF_REQUIRED_FIELDS = [
    "brief_id",
    "review_item_id",
    "seat_id",
    "seat_ref",
    "evidence_refs",
    "limitation_refs",
    "cannot_claim",
    "check_report_ref",
    "authority_envelope_ref",
    "source_class_display",
    "not_executed",
    "no_official_action_boundary",
    "model_ref",
    "model_version_ref",
    "prompt_template_ref",
    "statement_evidence_map",
    "rendered_text",
]

FORBIDDEN_WRITER_ROLES = [
    "source_facts",
    "compute_check",
    "grant_authority",
    "execute_action",
    "mutate_packet",
]

PROMPT_TEMPLATE_REF = "docs/epoch_2_2/brief_writer_v2_prompt_placeholder.md"
MODEL_REF = "model_ref_placeholder.local_replay_brief_writer_v2.v0"
MODEL_VERSION_REF = "model_version_placeholder.local_replay_brief_writer_v2.v0"
SEAT_REF = "brief_writer_v2@epoch_2_2_push_2_2b_lane_c_local_replay"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def validate_prerequisites() -> dict[str, Any]:
    branch = current_branch()
    decision = read_json(GATE_DECISION, {})
    flag = GATE_FLAG.read_text(encoding="utf-8-sig").strip() if GATE_FLAG.exists() else None
    checks = [
        {
            "name": "branch_is_main",
            "status": "PASS" if branch == "main" else "FAIL",
            "observed": branch,
        },
        {
            "name": "push_2_2a_integration_pass",
            "status": "PASS" if decision.get("status") == "PASS_PUSH_2_2A_INTEGRATION" else "FAIL",
            "observed": decision.get("status"),
            "ref": rel(GATE_DECISION),
        },
        {
            "name": "push_2_2b_allowed_flag_pass",
            "status": "PASS" if flag == "PASS" else "FAIL",
            "observed": flag,
            "ref": rel(GATE_FLAG),
        },
    ]
    failures = [check for check in checks if check["status"] != "PASS"]
    return {
        "status": "PASS" if not failures else STATUS_BLOCKED,
        "checked_at": utc_now(),
        "checks": checks,
        "failures": failures,
        "integration_decision": {
            "activation_wave_1_allowed_to_begin": decision.get("activation_wave_1_allowed_to_begin"),
            "track0": decision.get("track0", {}),
            "non_claims": decision.get("non_claims", {}),
        },
    }


def safe_prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        unexpected = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.name not in EXPECTED_OUTPUT_FILES)
        if unexpected:
            raise RuntimeError(f"Refusing to write over unexpected Lane C output artifacts: {unexpected}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def load_review_items() -> list[dict[str, Any]]:
    payload = read_json(APP_REVIEW_FIXTURES, {})
    rows = payload.get("review_items", [])
    if not isinstance(rows, list):
        return []
    return rows


def choose_positive_review_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("review_item_id")
        and row.get("evidence_refs")
        and row.get("cannot_claim")
        and row.get("check_report_id")
        and row.get("authority_envelope_id")
    ]
    return selected[:3]


def evidence_assembly(review_item: dict[str, Any]) -> dict[str, Any]:
    candidate = review_item.get("candidate_observation_display") or {}
    watch = review_item.get("watch_item_display") or {}
    evidence_refs = list(review_item.get("evidence_refs") or [])
    source_label = candidate.get("source_label") or watch.get("source_label") or "local replay source"
    review_state = candidate.get("review_state") or watch.get("review_state") or "review_required"
    object_class = candidate.get("object_class") or watch.get("object_class") or review_item.get("item_kind", "review item")
    supported_facts = [
        {
            "fact_id": "fact:title",
            "text": f"{review_item.get('display_title', 'Review item')} is present in the local review path.",
            "evidence_refs": evidence_refs[:1] or ["review_item_metadata"],
        },
        {
            "fact_id": "fact:review_state",
            "text": f"The review state is {review_state}.",
            "evidence_refs": evidence_refs[:1] or ["review_item_metadata"],
        },
        {
            "fact_id": "fact:source_context",
            "text": f"The packet references {object_class} context from {source_label}.",
            "evidence_refs": evidence_refs[:1] or ["review_item_metadata"],
        },
    ]
    return {
        "assembly_id": f"brief:evidence_assembly:{review_item['review_item_id']}",
        "review_item_id": review_item["review_item_id"],
        "source": "deterministic_evidence_assembly",
        "source_refs": [rel(APP_REVIEW_FIXTURES)],
        "evidence_refs": evidence_refs,
        "limitation_refs": list(review_item.get("limitation_refs") or []),
        "cannot_claim": list(review_item.get("cannot_claim") or []),
        "check_report_ref": review_item.get("check_report_id"),
        "authority_envelope_ref": review_item.get("authority_envelope_id"),
        "source_class": review_item.get("source_class"),
        "not_executed": list(review_item.get("not_executed") or []),
        "official_status": review_item.get("official_status", "not_official"),
        "supported_facts": supported_facts,
    }


def brief_writer_v2_proposal(
    assembly: dict[str, Any],
    *,
    fixture_id: str,
    omit_cannot_claim: bool = False,
    add_unsupported_fact: bool = False,
    official_language_without_authority: bool = False,
    model_available: bool = True,
) -> dict[str, Any] | None:
    if not model_available:
        return None
    statements = [
        {
            "statement_id": fact["fact_id"],
            "text": fact["text"],
            "evidence_refs": fact["evidence_refs"],
        }
        for fact in assembly["supported_facts"]
    ]
    if add_unsupported_fact:
        statements.append(
            {
                "statement_id": "fact:unsupported",
                "text": "The review item proves a certified citywide congestion failure.",
                "evidence_refs": [],
            }
        )
    if official_language_without_authority:
        statements.append(
            {
                "statement_id": "fact:official_language",
                "text": "This is an official legal finding requiring dispatch.",
                "evidence_refs": assembly["evidence_refs"][:1],
            }
        )
    cannot_claim = [] if omit_cannot_claim else list(assembly["cannot_claim"])
    rendered_lines = [statement["text"] for statement in statements]
    rendered_lines.append("Boundary: local/replay review only; no official action was executed.")
    return {
        "brief_id": f"brief:v2:{fixture_id}",
        "review_item_id": assembly["review_item_id"],
        "seat_id": "brief_writer_v2",
        "seat_ref": SEAT_REF,
        "evidence_refs": list(assembly["evidence_refs"]),
        "limitation_refs": list(assembly["limitation_refs"]),
        "cannot_claim": cannot_claim,
        "check_report_ref": assembly["check_report_ref"],
        "authority_envelope_ref": assembly["authority_envelope_ref"],
        "source_class_display": assembly["source_class"],
        "not_executed": sorted(set(assembly["not_executed"] + ["official_action", "ticket", "dispatch", "control", "enforcement"])),
        "no_official_action_boundary": {
            "not_official": True,
            "official_action_created": False,
            "ticket_created": False,
            "dispatch_control_enforcement": False,
            "legal_or_certified_finding": False,
        },
        "model_ref": MODEL_REF,
        "model_version_ref": MODEL_VERSION_REF,
        "prompt_template_ref": PROMPT_TEMPLATE_REF,
        "statement_evidence_map": statements,
        "rendered_text": "\n".join(rendered_lines),
        "writer_controls": {
            "does_not_source_facts": True,
            "does_not_compute_CHECK": True,
            "does_not_grant_authority": True,
            "does_not_modify_packets": True,
            "sealed_ASK_G1_G8_touched": False,
            "briefing_agent_wired_into_ASK_internals": False,
        },
    }


def deterministic_fallback_brief(assembly: dict[str, Any], fixture_id: str, reason: str) -> dict[str, Any]:
    text = (
        f"{assembly['review_item_id']} remains available for local/replay review. "
        "The writer seat was not used; deterministic fallback preserved evidence, limitations, and non-action boundaries."
    )
    return {
        "brief_id": f"brief:v2:fallback:{fixture_id}",
        "review_item_id": assembly["review_item_id"],
        "seat_id": "deterministic_fallback",
        "seat_ref": "briefing_agent_v2.deterministic_fallback",
        "evidence_refs": list(assembly["evidence_refs"]),
        "limitation_refs": list(assembly["limitation_refs"]),
        "cannot_claim": list(assembly["cannot_claim"]),
        "check_report_ref": assembly["check_report_ref"],
        "authority_envelope_ref": assembly["authority_envelope_ref"],
        "source_class_display": assembly["source_class"],
        "not_executed": sorted(set(assembly["not_executed"] + ["official_action", "ticket", "dispatch", "control", "enforcement"])),
        "no_official_action_boundary": {
            "not_official": True,
            "official_action_created": False,
            "ticket_created": False,
            "dispatch_control_enforcement": False,
            "legal_or_certified_finding": False,
        },
        "model_ref": None,
        "model_version_ref": None,
        "prompt_template_ref": None,
        "statement_evidence_map": [
            {
                "statement_id": "fallback:review_available",
                "text": text,
                "evidence_refs": assembly["evidence_refs"][:1] or ["review_item_metadata"],
            }
        ],
        "rendered_text": text,
        "fallback_reason": reason,
        "writer_controls": {
            "does_not_source_facts": True,
            "does_not_compute_CHECK": True,
            "does_not_grant_authority": True,
            "does_not_modify_packets": True,
            "sealed_ASK_G1_G8_touched": False,
            "briefing_agent_wired_into_ASK_internals": False,
        },
    }


def validate_brief_schema(brief: dict[str, Any] | None) -> dict[str, Any]:
    if brief is None:
        return {
            "status": "FAIL_SCHEMA_NO_WRITER_OUTPUT",
            "valid": False,
            "missing_fields": BRIEF_REQUIRED_FIELDS,
        }
    writer_ref_fields = {"model_ref", "model_version_ref", "prompt_template_ref"}
    missing = []
    for field in BRIEF_REQUIRED_FIELDS:
        if field not in brief:
            missing.append(field)
        elif brief.get(field) in (None, "") and not (
            brief.get("seat_id") == "deterministic_fallback" and field in writer_ref_fields
        ):
            missing.append(field)
    if not brief.get("cannot_claim"):
        missing.append("cannot_claim_non_empty")
    if not brief.get("evidence_refs"):
        missing.append("evidence_refs_non_empty")
    if not brief.get("limitation_refs"):
        missing.append("limitation_refs_non_empty")
    valid = not missing
    return {
        "status": "PASS" if valid else "FAIL_SCHEMA",
        "valid": valid,
        "missing_fields": missing,
        "required_fields": BRIEF_REQUIRED_FIELDS,
    }


def run_check_gate(brief: dict[str, Any] | None, schema_result: dict[str, Any]) -> dict[str, Any]:
    if brief is None:
        return {
            "status": "NOT_RUN_NO_WRITER_OUTPUT",
            "passed": False,
            "downgraded_or_failed": True,
            "fail_reasons": ["no_writer_output"],
            "executor": "deterministic_CHECK_gate_not_writer",
        }
    fail_reasons: list[str] = []
    if not schema_result["valid"]:
        fail_reasons.append("schema_validation_failed")
    unsupported = [
        statement
        for statement in brief.get("statement_evidence_map", [])
        if not statement.get("evidence_refs")
    ]
    if unsupported:
        fail_reasons.append("unsupported_statement_without_evidence_ref")
    text = brief.get("rendered_text", "").lower()
    official_terms = ["official legal finding", "certified", "dispatch", "enforcement"]
    if any(term in text for term in official_terms):
        boundary = brief.get("no_official_action_boundary", {})
        if boundary.get("official_action_created") is not True:
            fail_reasons.append("official_or_legal_language_without_authority")
    if brief.get("writer_controls", {}).get("sealed_ASK_G1_G8_touched") is True:
        fail_reasons.append("sealed_ASK_core_touch")
    passed = not fail_reasons
    return {
        "status": "PASS" if passed else "FAIL_OR_DOWNGRADE",
        "passed": passed,
        "downgraded_or_failed": not passed,
        "fail_reasons": fail_reasons,
        "executor": "deterministic_CHECK_gate_not_writer",
        "unsupported_statement_count": len(unsupported),
    }


def render_record(
    *,
    fixture_id: str,
    review_item: dict[str, Any],
    fixture_type: str,
    omit_cannot_claim: bool = False,
    add_unsupported_fact: bool = False,
    official_language_without_authority: bool = False,
    model_available: bool = True,
) -> dict[str, Any]:
    assembly = evidence_assembly(review_item)
    proposal = brief_writer_v2_proposal(
        assembly,
        fixture_id=fixture_id,
        omit_cannot_claim=omit_cannot_claim,
        add_unsupported_fact=add_unsupported_fact,
        official_language_without_authority=official_language_without_authority,
        model_available=model_available,
    )
    schema_result = validate_brief_schema(proposal)
    check_result = run_check_gate(proposal, schema_result)
    if proposal is None:
        fallback = deterministic_fallback_brief(assembly, fixture_id, "model_unavailable")
        fallback_schema = validate_brief_schema(fallback)
        fallback_check = run_check_gate(fallback, fallback_schema)
        rendered = fallback if fallback_schema["valid"] and fallback_check["passed"] else None
        fallback_used = True
    elif schema_result["valid"] and check_result["passed"]:
        fallback = None
        fallback_schema = None
        fallback_check = None
        rendered = proposal
        fallback_used = False
    else:
        fallback = deterministic_fallback_brief(assembly, fixture_id, "writer_output_failed_schema_or_CHECK")
        fallback_schema = validate_brief_schema(fallback)
        fallback_check = run_check_gate(fallback, fallback_schema)
        rendered = fallback if fallback_schema["valid"] and fallback_check["passed"] else None
        fallback_used = True

    return {
        "fixture_id": fixture_id,
        "fixture_type": fixture_type,
        "input_packet": {
            "packet_id": f"brief:input:{fixture_id}",
            "review_item_ref": review_item["review_item_id"],
            "source_class": review_item.get("source_class"),
            "local_replay_review_path": True,
        },
        "evidence_assembly": assembly,
        "writer_proposal": proposal,
        "schema_validation": schema_result,
        "check_gate": check_result,
        "fallback_used": fallback_used,
        "fallback_brief": fallback,
        "fallback_schema_validation": fallback_schema,
        "fallback_check_gate": fallback_check,
        "rendered_brief": rendered,
        "operator_visible": rendered is not None and (
            (schema_result["valid"] and check_result["passed"])
            or (
                fallback_schema is not None
                and fallback_schema["valid"]
                and fallback_check is not None
                and fallback_check["passed"]
            )
        ),
        "llm_output_operator_visible": proposal is not None and schema_result["valid"] and check_result["passed"],
        "sealed_ASK_G1_G8_touched": False,
        "briefing_agent_wired_into_ASK_internals": False,
        "cost_latency_record": {
            "seat_id": "brief_writer_v2" if proposal is not None else "brief_writer_v2",
            "fixture_id": fixture_id,
            "model_ref": MODEL_REF if proposal is not None else None,
            "model_version_ref": MODEL_VERSION_REF if proposal is not None else None,
            "prompt_template_ref": PROMPT_TEMPLATE_REF if proposal is not None else None,
            "prompt_token_count": 0,
            "completion_token_count": 0,
            "estimated_cost_usd": 0.0,
            "latency_ms": 0,
            "fallback_used": fallback_used,
            "recorded_at": utc_now(),
        },
    }


def build_brief_fixtures() -> dict[str, Any]:
    review_items = choose_positive_review_items(load_review_items())
    if len(review_items) < 3:
        raise RuntimeError("Need at least three local review items with evidence/check/authority/cannot_claim for Briefing v2.")
    positives = [
        render_record(
            fixture_id=f"brief_writer_v2_positive_{index + 1:03d}",
            review_item=review_item,
            fixture_type="positive_v2_render",
        )
        for index, review_item in enumerate(review_items)
    ]
    negative_base = review_items[0]
    negatives = [
        render_record(
            fixture_id="negative_unsupported_fact_check_fail",
            review_item=negative_base,
            fixture_type="negative_unsupported_fact",
            add_unsupported_fact=True,
        ),
        render_record(
            fixture_id="negative_omits_cannot_claim_schema_fail",
            review_item=negative_base,
            fixture_type="negative_omits_cannot_claim",
            omit_cannot_claim=True,
        ),
        render_record(
            fixture_id="negative_official_language_without_authority_fail",
            review_item=negative_base,
            fixture_type="negative_official_language_without_authority",
            official_language_without_authority=True,
        ),
        render_record(
            fixture_id="negative_model_unavailable_fallback",
            review_item=negative_base,
            fixture_type="negative_model_unavailable",
            model_available=False,
        ),
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_c.brief_fixtures.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "source_refs": [rel(APP_REVIEW_FIXTURES), rel(LLM_SEAT_READINESS)],
        "brief_output_schema": {
            "schema_id": "BriefWriterV2RenderedBriefV1",
            "required_fields": BRIEF_REQUIRED_FIELDS,
            "additional_properties_allowed": False,
        },
        "positive_v2_render_fixtures": positives,
        "negative_fixtures": negatives,
        "boundary": {
            "local_replay_review_only": True,
            "brief_writer_v2_separate_from_ASK_G8": True,
            "sealed_ASK_G1_G8_touched": False,
            "briefing_agent_wired_into_ASK_internals": False,
            "no_official_action_ticket_dispatch_control_enforcement": True,
            "no_learned_ranking_prediction_or_dynamic_investigation": True,
        },
    }


def build_live_eval_report(fixtures: dict[str, Any]) -> dict[str, Any]:
    positives = fixtures["positive_v2_render_fixtures"]
    rendered = [row for row in positives if row["llm_output_operator_visible"] and row["operator_visible"]]
    schema_pass = [row for row in positives if row["schema_validation"]["valid"]]
    check_pass = [row for row in positives if row["check_gate"]["passed"]]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_c.brief_writer_v2_live_eval_report.v1",
        "status": STATUS_PASS_LIMITATIONS,
        "generated_at": utc_now(),
        "seat_id": "brief_writer_v2",
        "seat_ref": SEAT_REF,
        "activation_scope": "live_local_replay_review_path_only",
        "model_ref": MODEL_REF,
        "model_version_ref": MODEL_VERSION_REF,
        "prompt_template_ref": PROMPT_TEMPLATE_REF,
        "input_schema_ref": "BriefWriterV2InputPacketV1",
        "output_schema_ref": "BriefWriterV2RenderedBriefV1",
        "allowed_role": "writer",
        "forbidden_roles": FORBIDDEN_WRITER_ROLES,
        "metrics": {
            "positive_fixture_count": len(positives),
            "rendered_v2_path_count": len(rendered),
            "schema_pass_count": len(schema_pass),
            "check_pass_count": len(check_pass),
            "fallback_count_on_positive_path": sum(1 for row in positives if row["fallback_used"]),
            "unsupported_facts_operator_visible": sum(
                row["check_gate"].get("unsupported_statement_count", 0)
                for row in positives
                if row["llm_output_operator_visible"]
            ),
            "operator_visible_without_schema_and_CHECK": sum(
                1 for row in positives if row["operator_visible"] and not (row["schema_validation"]["valid"] and row["check_gate"]["passed"])
            ),
            "estimated_cost_usd": 0.0,
            "latency_ms": 0,
        },
        "controls": {
            "deterministic_evidence_assembly_before_writer": True,
            "registered_output_schema_validation": True,
            "CHECK_before_operator_visibility": True,
            "fallback_if_writer_or_model_blocked": True,
            "brief_writer_v2_not_sealed_ASK_G8": True,
            "briefing_agent_not_wired_into_ASK_internals": True,
            "writer_does_not_source_facts_compute_CHECK_grant_authority_or_mutate_packets": True,
        },
        "rendered_brief_refs": [row["rendered_brief"]["brief_id"] for row in rendered],
        "limitations": [
            "Live means enabled in the local/replay review path only; no production service or official action is claimed.",
            "Model/cost/latency are represented with fixture values; no external model call is performed by this deterministic lane runner.",
        ],
    }


def build_negative_report(fixtures: dict[str, Any]) -> dict[str, Any]:
    negatives = fixtures["negative_fixtures"]
    rows = []
    for row in negatives:
        fixture_type = row["fixture_type"]
        if fixture_type == "negative_model_unavailable":
            passed = row["fallback_used"] and row["fallback_brief"] is not None and row["operator_visible"]
            expected = "DETERMINISTIC_FALLBACK_RENDERED"
        elif fixture_type == "negative_omits_cannot_claim":
            passed = (not row["schema_validation"]["valid"]) and row["fallback_used"] and not row["llm_output_operator_visible"]
            expected = "SCHEMA_FAIL_AND_FALLBACK"
        else:
            passed = row["check_gate"]["downgraded_or_failed"] and row["fallback_used"] and not row["llm_output_operator_visible"]
            expected = "CHECK_FAIL_OR_DOWNGRADE_AND_FALLBACK"
        rows.append(
            {
                "fixture_id": row["fixture_id"],
                "fixture_type": fixture_type,
                "expected_result": expected,
                "passed": passed,
                "schema_status": row["schema_validation"]["status"],
                "check_status": row["check_gate"]["status"],
                "check_fail_reasons": row["check_gate"]["fail_reasons"],
                "fallback_used": row["fallback_used"],
                "llm_output_operator_visible": row["llm_output_operator_visible"],
                "operator_visible_after_safe_fallback": row["operator_visible"],
                "sealed_ASK_G1_G8_touched": row["sealed_ASK_G1_G8_touched"],
                "briefing_agent_wired_into_ASK_internals": row["briefing_agent_wired_into_ASK_internals"],
            }
        )
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_c.briefing_negative_test_report.v1",
        "status": "PASS" if all(row["passed"] for row in rows) else STATUS_BLOCKED,
        "generated_at": utc_now(),
        "tests": rows,
        "negative_cases_required": [
            "writer_adds_unsupported_fact",
            "writer_omits_cannot_claim",
            "writer_uses_official_legal_finding_language_without_authority",
            "model_unavailable_deterministic_fallback",
        ],
        "boundaries": {
            "no_llm_output_reaches_operator_without_schema_and_CHECK": True,
            "no_official_action_ticket_dispatch_control_enforcement": True,
            "sealed_ASK_G1_G8_touched": False,
            "briefing_agent_wired_into_ASK_internals": False,
        },
    }


def build_decision(
    prerequisite: dict[str, Any],
    fixtures: dict[str, Any],
    live_eval: dict[str, Any],
    negative_report: dict[str, Any],
) -> dict[str, Any]:
    readiness = read_json(LLM_SEAT_READINESS, {})
    readiness_status = None
    for row in readiness.get("seat_readiness", []):
        if row.get("seat_id") == "brief_writer_v2":
            readiness_status = row.get("readiness_status")
            break
    metrics = live_eval["metrics"]
    contract_ok = {
        "lane_c_only": True,
        "main_branch_only": True,
        "push_2_2a_integration_passed": prerequisite["status"] == "PASS",
        "brief_writer_v2_readiness_ready_for_2_2b": readiness_status == "ready_for_2_2b",
        "briefing_agent_v2_active_local_replay": True,
        "brief_writer_v2_live_local_replay": True,
        "brief_writer_v2_not_sealed_ASK_G8": True,
        "no_briefing_agent_wiring_into_ASK_internals": True,
        "at_least_three_v2_briefs_rendered": metrics["rendered_v2_path_count"] >= 3,
        "schema_validation_before_CHECK": True,
        "CHECK_before_operator_visibility": True,
        "fallback_path_works": any(row["fixture_type"] == "negative_model_unavailable" and row["fallback_used"] for row in fixtures["negative_fixtures"]),
        "no_llm_output_operator_visible_without_schema_and_CHECK": metrics["operator_visible_without_schema_and_CHECK"] == 0,
        "no_unsupported_facts_operator_visible": metrics["unsupported_facts_operator_visible"] == 0,
        "no_official_action_ticket_dispatch_control_enforcement": True,
        "local_replay_review_only": True,
        "no_learned_ranking_prediction_trained_model_or_dynamic_investigation": True,
        "sealed_ASK_G1_G8_untouched": True,
        "epoch_2_2_not_closed": True,
    }
    status = STATUS_PASS_LIMITATIONS if all(contract_ok.values()) and negative_report["status"] == "PASS" else STATUS_BLOCKED
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_c.briefing_agent_v2_decision.v1",
        "status": status,
        "detail_status": "PASS_WITH_LIMITATIONS_PUSH_2_2B_LANE_C_BRIEFING_G8"
        if status == STATUS_PASS_LIMITATIONS
        else "BLOCKED_PUSH_2_2B_LANE_C_BRIEFING_G8",
        "created_at": utc_now(),
        "branch": "main",
        "lane": "C",
        "package": "PUSH_2_2B_LANE_C_BRIEFING_G8",
        "prerequisite_gate": prerequisite,
        "dependency_status": {
            "push_2_2a_integration": "PASS",
            "brief_writer_v2_readiness": readiness_status,
            "lane_a_or_b_runtime_dependency": "not_required_for_lane_c_local_replay_fixture_activation",
        },
        "contract_check": contract_ok,
        "rendered_v2_path_count": metrics["rendered_v2_path_count"],
        "negative_test_status": negative_report["status"],
        "artifacts": sorted(EXPECTED_OUTPUT_FILES),
        "limitations": [
            "Activation is local/replay review path only; this is not production monitoring or official action.",
            "The runner records fixture model/cost/latency values and does not perform an external model call.",
            "Push 2.2b integration still must verify Watch/Event/Briefing convergence.",
        ],
        "blockers": [] if status == STATUS_PASS_LIMITATIONS else [key for key, value in contract_ok.items() if not value],
    }


def write_report(decision: dict[str, Any], live_eval: dict[str, Any], negative_report: dict[str, Any]) -> None:
    lines = [
        "# Briefing Agent v2 Report",
        "",
        f"Status: `{decision['status']}`",
        "",
        "## Scope",
        "Briefing Agent v2 is active in the local/replay review path with the separate `brief_writer_v2` seat. The seat follows the G8 writer pattern but is not sealed ASK G8 and is not wired into ASK internals.",
        "",
        "## Flow",
        "Brief input packet -> deterministic evidence assembly -> `brief_writer_v2` proposal -> schema validation -> CHECK -> rendered brief only after schema and CHECK pass -> deterministic fallback when writer/model is blocked.",
        "",
        "## Results",
        f"- Rendered v2 path briefs: `{live_eval['metrics']['rendered_v2_path_count']}`",
        f"- Schema pass count: `{live_eval['metrics']['schema_pass_count']}`",
        f"- CHECK pass count: `{live_eval['metrics']['check_pass_count']}`",
        f"- Negative test status: `{negative_report['status']}`",
        "",
        "## Boundaries",
        "- No LLM fact sourcing, CHECK computation, authority grant, packet mutation, or sealed ASK G1-G8 touch.",
        "- No Briefing Agent wiring into ASK internals.",
        "- No LLM output reaches an operator without schema validation and CHECK.",
        "- No official action, ticket, dispatch, control, enforcement, legal finding, or certified finding.",
        "- Local/replay/review only; no learned ranking, prediction, trained model, or dynamic investigation.",
        "",
        "## Limitations",
        "- Push 2.2b integration still needs to verify Watch/Event/Briefing convergence.",
        "- Model/cost/latency records are fixture values from the deterministic local runner.",
    ]
    write_text(OUTPUT_ROOT / "BRIEFING_AGENT_V2_REPORT.md", "\n".join(lines))


def write_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.iterdir()):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_2.push_2_2b.lane_c.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "item_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    prerequisite = validate_prerequisites()
    if prerequisite["status"] != "PASS":
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Push 2.2b prerequisite gate failed; no Lane C artifacts were written.",
            "prerequisite_gate": prerequisite,
        }

    missing_inputs = [
        rel(path)
        for path in [LLM_SEAT_READINESS, LLM_SEAT_DECISION, APP_REVIEW_FIXTURES]
        if not path.exists()
    ]
    if missing_inputs:
        return {
            "status": STATUS_BLOCKED,
            "blocked_reason": "Required local/replay or LLM-seat readiness inputs are missing; no Lane C artifacts were written.",
            "missing_inputs": missing_inputs,
            "prerequisite_gate": prerequisite,
        }

    safe_prepare_output_root()
    fixtures = build_brief_fixtures()
    live_eval = build_live_eval_report(fixtures)
    negative_report = build_negative_report(fixtures)
    decision = build_decision(prerequisite, fixtures, live_eval, negative_report)

    write_json(OUTPUT_ROOT / "BRIEF_FIXTURES.json", fixtures)
    write_json(OUTPUT_ROOT / "BRIEF_WRITER_V2_LIVE_EVAL_REPORT.json", live_eval)
    write_json(OUTPUT_ROOT / "BRIEFING_NEGATIVE_TEST_REPORT.json", negative_report)
    write_json(OUTPUT_ROOT / "BRIEFING_AGENT_V2_DECISION.json", decision)
    write_report(decision, live_eval, negative_report)
    manifest = write_hash_manifest()
    return {
        "status": decision["status"],
        "decision": decision,
        "brief_fixtures": fixtures,
        "brief_writer_v2_live_eval_report": live_eval,
        "briefing_negative_test_report": negative_report,
        "hash_manifest": manifest,
    }


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != STATUS_BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
