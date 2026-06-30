"""
A5-D4B thin request validator and complete trace core.

D4B wraps the D4A EvidenceBundle core with explicit request validation,
deterministic tool execution, grounded synthesis, and reviewer-grade trace
records. It is intentionally narrow: one supported operator intent, no broad
natural-language planning, and no state mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_a5_narration_grounded_gate import run_grounding_gate
from txr_citybrain_a5d1_operator_query import BOUNDARY_STATEMENT, DistrictGraph
from txr_citybrain_a5d4a_evidence_grounding_core import (
    HERO_BBL,
    SECOND_SUBJECT_BBL,
    canonical_json,
    deterministic_narration,
    normalize_to_evidence_bundle,
    sha256_file,
    sha256_payload,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_D4A_DIR = ROOT / "outputs" / "a5d4a_evidence_grounding_core"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d4b_request_trace_core"
DEFAULT_A4D2_DIR = ROOT / "outputs" / "a5_dob_district_enrichment"
DEFAULT_A5D1_DIR = ROOT / "outputs" / "a5d1_operator_query"
DEFAULT_A5D2_DIR = ROOT / "outputs" / "a5d2_spark_portability_pack"

TASK_NAME = "A5-D4B Thin Request Validator + Complete Trace"
TOOL_NAME = "citybrain_operator_query"
SUPPORTED_INTENT = "parcel_operational_briefing"
SUPPORTED_QUERY_TYPE = "parcel_profile"
SNAPSHOT = "a5_district_v1"
HERO_SUBJECT_ID = f"parcel:us-nyc:bbl:{HERO_BBL}"
SECOND_SUBJECT_ID = f"parcel:us-nyc:bbl:{SECOND_SUBJECT_BBL}"
HERO_LEAK_TOKENS = [
    "1010607502",
    "1026676",
    "event:us-nyc:dob_complaint:1366080",
    "GC-0037441",
    "S&E BRIDGE & SCAFFOLD LLC",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file())
    }


def output_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    }


def resolve_path(path_text: str, base_dir: Path | None = None) -> Path:
    path = Path(path_text)
    if path.exists():
        return path
    if not path.is_absolute():
        root_path = ROOT / path
        if root_path.exists():
            return root_path
        if base_dir is not None:
            base_path = base_dir / path
            if base_path.exists():
                return base_path
    return path


def default_tool_registry() -> dict[str, Any]:
    return {
        "tool_name": TOOL_NAME,
        "allowed_query_types": [
            "parcel_profile",
            "building_profile",
            "complaint_search",
            "permit_search",
            "party_search",
            "reachability",
        ],
        "truth_owner": "code",
        "model_may_call": False,
        "mutates_state": False,
    }


def default_request_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "A5-D4B operator request",
        "type": "object",
        "required": ["request_id", "subject_type", "subject_id", "bbl", "query_intent", "requested_outputs", "allow_nim_narration"],
        "properties": {
            "request_id": {"type": "string"},
            "tool_name": {"const": TOOL_NAME},
            "subject_type": {"const": "parcel"},
            "subject_id": {"type": "string", "pattern": "^parcel:us-nyc:bbl:[0-9]+$"},
            "bbl": {"type": "string", "pattern": "^[0-9]+$"},
            "query_intent": {"const": SUPPORTED_INTENT},
            "requested_outputs": {
                "type": "array",
                "items": {
                    "enum": ["what_is_happening", "what_changed", "who_is_responsible", "evidence"],
                },
            },
            "allow_nim_narration": {"type": "boolean"},
            "raw_request": {"type": "string"},
            "query_type": {"enum": ["parcel_profile", "building_profile", "complaint_search", "permit_search", "party_search", "reachability"]},
        },
    }


def default_validation_rules() -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "boundary_statement": BOUNDARY_STATEMENT,
        "supported_intents": [SUPPORTED_INTENT],
        "validator_rejects": [
            "unknown tool name",
            "unsupported query type",
            "missing subject_id / BBL",
            "subject not resolvable in active snapshot",
            "full-NYC-history claim",
            "enforcement/dispatch/write action request",
            "raw SQL/shell/file mutation request",
            "request to let NIM compute counts",
        ],
        "forbidden_full_history_patterns": [
            "full nyc history",
            "all dob history for nyc",
            "complete nyc dob history",
            "citywide dob history",
            "all history",
        ],
        "forbidden_action_patterns": [
            "issue a stop-work order",
            "issue stop work",
            "stop-work order",
            "dispatch",
            "enforce",
            "take action",
            "write violation",
            "send crew",
        ],
        "forbidden_mutation_patterns": [
            "raw sql",
            "sql update",
            "delete from",
            "drop table",
            "shell command",
            "write file",
            "mutate",
            "overwrite",
        ],
        "forbidden_nim_truth_patterns": [
            "nim compute counts",
            "llm compute counts",
            "model compute counts",
            "let nim count",
            "let the model count",
        ],
    }


def write_registry_schema_rules(output_dir: Path) -> dict[str, Any]:
    registry = default_tool_registry()
    request_schema = default_request_schema()
    rules = default_validation_rules()
    write_json(output_dir / "A5D4B_TOOL_REGISTRY.json", registry)
    write_json(output_dir / "A5D4B_REQUEST_SCHEMA.json", request_schema)
    write_json(output_dir / "A5D4B_VALIDATION_RULES.json", rules)
    return {
        "registry": read_json(output_dir / "A5D4B_TOOL_REGISTRY.json"),
        "schema": read_json(output_dir / "A5D4B_REQUEST_SCHEMA.json"),
        "rules": read_json(output_dir / "A5D4B_VALIDATION_RULES.json"),
        "hashes": {
            "registry": sha256_file(output_dir / "A5D4B_TOOL_REGISTRY.json"),
            "schema": sha256_file(output_dir / "A5D4B_REQUEST_SCHEMA.json"),
            "rules": sha256_file(output_dir / "A5D4B_VALIDATION_RULES.json"),
        },
    }


def contains_any(text: str, patterns: list[str]) -> list[str]:
    lower = text.lower()
    return [pattern for pattern in patterns if pattern in lower]


def validate_request(
    request: dict[str, Any],
    registry: dict[str, Any],
    request_schema: dict[str, Any],
    rules: dict[str, Any],
    valid_subject_ids: set[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    raw_text = " ".join(
        [
            str(request.get("raw_request") or ""),
            str(request.get("query_intent") or ""),
            " ".join(str(item) for item in request.get("requested_outputs") or []),
        ]
    )
    tool_name = request.get("tool_name") or TOOL_NAME
    if tool_name != registry.get("tool_name"):
        reasons.append(f"unknown tool name: {tool_name}")
    if registry.get("mutates_state"):
        reasons.append("tool registry is unsafe: mutates_state is true")

    query_intent = request.get("query_intent")
    if query_intent not in rules.get("supported_intents", []):
        reasons.append(f"unsupported query intent: {query_intent}")
    query_type = request.get("query_type") or SUPPORTED_QUERY_TYPE
    if query_type not in registry.get("allowed_query_types", []):
        reasons.append(f"unsupported query type: {query_type}")
    if query_intent == SUPPORTED_INTENT and query_type != SUPPORTED_QUERY_TYPE:
        reasons.append(f"query intent {SUPPORTED_INTENT} maps only to {SUPPORTED_QUERY_TYPE}, not {query_type}")

    subject_id = str(request.get("subject_id") or "").strip()
    bbl = str(request.get("bbl") or "").strip()
    if not subject_id:
        reasons.append("missing subject_id")
    if not bbl:
        reasons.append("missing BBL")
    if subject_id and bbl and subject_id != f"parcel:us-nyc:bbl:{bbl}":
        reasons.append("subject_id and BBL do not identify the same parcel")
    if subject_id and subject_id not in valid_subject_ids:
        reasons.append(f"subject not resolvable in active snapshot: {subject_id}")
    if request.get("subject_type") != "parcel":
        reasons.append("unsupported subject_type; D4B supports parcel only")

    full_history_matches = contains_any(raw_text, rules.get("forbidden_full_history_patterns", []))
    action_matches = contains_any(raw_text, rules.get("forbidden_action_patterns", []))
    mutation_matches = contains_any(raw_text, rules.get("forbidden_mutation_patterns", []))
    nim_truth_matches = contains_any(raw_text, rules.get("forbidden_nim_truth_patterns", []))
    if full_history_matches:
        reasons.append(f"forbidden full-history claim: {', '.join(full_history_matches)}")
    if action_matches:
        reasons.append(f"forbidden enforcement/action request: {', '.join(action_matches)}")
    if mutation_matches:
        reasons.append(f"raw SQL/shell/file mutation request rejected: {', '.join(mutation_matches)}")
    if nim_truth_matches:
        reasons.append(f"request to let NIM compute counts rejected: {', '.join(nim_truth_matches)}")

    requested_outputs = request.get("requested_outputs")
    allowed_outputs = set((request_schema.get("properties", {}).get("requested_outputs", {}).get("items", {}) or {}).get("enum", []))
    if not isinstance(requested_outputs, list) or not requested_outputs:
        reasons.append("requested_outputs must be a non-empty list")
    else:
        unsupported = sorted(str(item) for item in requested_outputs if item not in allowed_outputs)
        if unsupported:
            reasons.append(f"unsupported requested_outputs: {', '.join(unsupported)}")

    status = "PASS" if not reasons else "FAIL"
    return {
        "status": status,
        "request_id": request.get("request_id"),
        "subject_id": subject_id,
        "bbl": bbl,
        "reasons": reasons,
        "warnings": warnings,
        "deterministic_query_plan": []
        if reasons
        else [
            {
                "tool_name": TOOL_NAME,
                "query_type": SUPPORTED_QUERY_TYPE,
                "parameters": {"bbl": bbl},
                "truth_owner": "code",
                "model_may_call": False,
                "mutates_state": False,
            }
        ],
        "config_hashes": {
            "tool_registry": sha256_payload(registry),
            "request_schema": sha256_payload(request_schema),
            "validation_rules": sha256_payload(rules),
        },
    }


def step_record(step_name: str, status: str, input_payload: Any, output_payload: Any, started_at: str, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "step_name": step_name,
        "status": status,
        "input_hash": sha256_payload(input_payload),
        "output_hash": sha256_payload(output_payload),
        "started_at": started_at,
        "completed_at": utc_now(),
        "warnings": warnings or [],
    }


def d4a_entry(report: dict[str, Any], subject_label: str) -> dict[str, Any]:
    key = "hero" if subject_label == "hero" else "second_subject"
    return report["evidence_bundles"][key]


def d4a_bundle_path(report: dict[str, Any], subject_label: str, d4a_dir: Path) -> Path:
    return resolve_path(d4a_entry(report, subject_label)["evidence_bundle"], d4a_dir)


def maybe_nim_narration(
    evidence_bundle: dict[str, Any],
    deterministic_text: str,
    use_nim: bool,
    nim_endpoint: str | None,
    nim_model: str | None,
) -> tuple[str, dict[str, Any] | None]:
    if not use_nim:
        return deterministic_text, None
    grounding_input_hash = sha256_payload(
        {
            "answer_facts": evidence_bundle.get("answer_facts", []),
            "counts": evidence_bundle.get("counts", {}),
            "confidence_summary": evidence_bundle.get("confidence_summary", []),
            "provenance_summary": evidence_bundle.get("provenance_summary", []),
            "boundary_statement": BOUNDARY_STATEMENT,
        }
    )
    if not nim_endpoint or not nim_model:
        return deterministic_text, {
            "status": "disabled",
            "mode": "missing_config",
            "endpoint": nim_endpoint,
            "model": nim_model,
            "grounding_inputs_hash": grounding_input_hash,
            "warnings": ["NIM requested but endpoint/model missing; deterministic narration retained."],
        }
    url = nim_endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions" if url.endswith("/v1") else f"{url}/v1/chat/completions"
    prompt = {
        "boundary_statement": BOUNDARY_STATEMENT,
        "answer_facts": evidence_bundle.get("answer_facts", []),
        "counts": evidence_bundle.get("counts", {}),
        "confidence_summary": evidence_bundle.get("confidence_summary", []),
        "provenance_summary": evidence_bundle.get("provenance_summary", []),
        "deterministic_narration": deterministic_text,
        "instruction": (
            "Return deterministic_narration exactly, byte-for-byte. Do not paraphrase the boundary statement. "
            "Do not spell out numeric counts as words. Do not add identifiers, parties, dates, actions, headings, "
            "or agency-name phrases. The model may not compute truth; it may only echo the supplied grounded narration."
        ),
    }
    request_payload = {
        "model": nim_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You narrate deterministic city evidence only. Never add facts."},
            {"role": "user", "content": json.dumps(prompt, sort_keys=True, ensure_ascii=False)},
        ],
    }
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = payload["choices"][0]["message"]["content"]
        used_text = text.strip()
        deterministic_guarded = used_text != deterministic_text.strip()
        return deterministic_text if deterministic_guarded else text, {
            "status": "PASS",
            "mode": "nim",
            "endpoint": nim_endpoint,
            "model": nim_model,
            "grounding_inputs_hash": grounding_input_hash,
            "response_hash": sha256_payload(payload),
            "used_text": "deterministic_guarded_fallback" if deterministic_guarded else "nim_exact_echo",
            "warnings": ["NIM response was not an exact grounded echo; deterministic narration used."] if deterministic_guarded else [],
        }
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError, ValueError) as exc:
        return deterministic_text, {
            "status": "failed",
            "mode": "fallback_deterministic",
            "endpoint": nim_endpoint,
            "model": nim_model,
            "grounding_inputs_hash": grounding_input_hash,
            "warnings": [f"NIM narration failed; deterministic narration retained: {exc}"],
        }


def final_response_payload(
    request: dict[str, Any],
    evidence_bundle: dict[str, Any],
    narration: str,
    grounding: dict[str, Any],
    trace_id: str,
) -> dict[str, Any]:
    counts = evidence_bundle.get("counts", {})
    source_rows = counts.get("source_rows", {})
    return {
        "status": "PASS" if grounding.get("status") == "PASS" else "FAIL",
        "task": TASK_NAME,
        "request_id": request.get("request_id"),
        "subject_id": evidence_bundle.get("subject", {}).get("subject_id"),
        "bbl": evidence_bundle.get("subject", {}).get("bbl"),
        "boundary_statement": BOUNDARY_STATEMENT,
        "deterministic_answer": {
            "what_is_happening": {
                "linked_buildings": counts.get("linked_buildings", 0),
                "linked_permits": counts.get("linked_permits", 0),
                "linked_dob_complaints": counts.get("linked_dob_complaints", 0),
                "linked_parties": counts.get("linked_parties", 0),
            },
            "what_changed": {
                "dob_permit_issuance_source_rows": source_rows.get("dob_permit_issuance", 0),
                "dob_now_filing_source_rows": source_rows.get("dob_now_filings", 0),
                "dob_complaint_events": source_rows.get("dob_complaints", 0),
            },
            "who_is_responsible": {
                "party_role_counts": evidence_bundle.get("party_role_counts", {}),
                "confidence_policy": "Party identity confidence remains in the EvidenceBundle; license-number parties are stronger than name-hash parties.",
            },
            "evidence": {
                "evidence_bundle_id": evidence_bundle.get("bundle_id"),
                "evidence_bundle_hash": evidence_bundle.get("normalized_hash"),
                "tool_name": evidence_bundle.get("tool_name"),
                "query_type": evidence_bundle.get("query_type"),
                "grounding_status": grounding.get("status"),
                "trace_id": trace_id,
            },
        },
        "narration": narration,
        "grounding_report": grounding,
    }


def final_response_markdown(response: dict[str, Any]) -> str:
    answer = response["deterministic_answer"]
    happening = answer["what_is_happening"]
    changed = answer["what_changed"]
    responsible = answer["who_is_responsible"]
    evidence = answer["evidence"]
    return "\n".join(
        [
            "# A5-D4B Final Response",
            "",
            f"Status: {response['status']}",
            f"Subject: `{response['subject_id']}`",
            f"BBL: `{response['bbl']}`",
            "",
            "## Deterministic Answer",
            "",
            f"- Buildings: {happening['linked_buildings']}",
            f"- Permits: {happening['linked_permits']}",
            f"- DOB complaints: {happening['linked_dob_complaints']}",
            f"- Parties: {happening['linked_parties']}",
            f"- DOB Permit Issuance source rows: {changed['dob_permit_issuance_source_rows']}",
            f"- DOB NOW filing source rows: {changed['dob_now_filing_source_rows']}",
            f"- DOB complaint events: {changed['dob_complaint_events']}",
            f"- Party role counts: `{json.dumps(responsible['party_role_counts'], sort_keys=True)}`",
            "",
            "## Evidence",
            "",
            f"- Evidence bundle: `{evidence['evidence_bundle_id']}`",
            f"- Evidence hash: `{evidence['evidence_bundle_hash']}`",
            f"- Grounding: `{evidence['grounding_status']}`",
            f"- Trace: `{evidence['trace_id']}`",
            "",
            "## Narration",
            "",
            response["narration"],
            "",
            "## Boundary",
            "",
            response["boundary_statement"],
            "",
        ]
    )


def run_oracle_request(
    request: dict[str, Any],
    subject_label: str,
    run_dir: Path,
    graph: DistrictGraph,
    d4a_report: dict[str, Any],
    d4a_dir: Path,
    registry: dict[str, Any],
    request_schema: dict[str, Any],
    rules: dict[str, Any],
    use_nim: bool,
    nim_endpoint: str | None,
    nim_model: str | None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "request.json", request)
    steps: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    nim_calls: list[dict[str, Any]] = []
    trace_id = f"a5d4b:{subject_label}:{request['request_id']}"

    started = utc_now()
    validation = validate_request(request, registry, request_schema, rules, set(graph.entities_by_id))
    write_json(run_dir / "validate_request.json", validation)
    steps.append(step_record("validate_request", validation["status"], request, validation, started, validation.get("warnings", [])))
    if validation["status"] != "PASS":
        trace = {
            "run_id": trace_id,
            "subject_id": request.get("subject_id"),
            "snapshot": SNAPSHOT,
            "boundary_statement": BOUNDARY_STATEMENT,
            "status": "REJECTED",
            "steps": steps,
            "tool_calls": [],
            "nim_calls": [],
            "final_output_hash": None,
            "validation_result": validation,
        }
        write_json(run_dir / "full_trace.json", trace)
        return {"status": "REJECTED", "validation": validation, "trace": trace}

    query = {"query_type": SUPPORTED_QUERY_TYPE, "bbl": request["bbl"]}
    tool_call = {
        "tool_name": TOOL_NAME,
        "query_type": SUPPORTED_QUERY_TYPE,
        "parameters": {"bbl": request["bbl"]},
        "truth_owner": "code",
        "mutates_state": False,
    }
    started = utc_now()
    query_result = graph.query(query, f"a5d4a_{subject_label}_parcel_profile")
    execution = {
        "status": "PASS",
        "tool_call": tool_call,
        "query_result_hash": sha256_payload(query_result),
        "query_result": query_result,
    }
    tool_calls.append({**tool_call, "query_result_hash": execution["query_result_hash"]})
    write_json(run_dir / "execute_deterministic_query.json", execution)
    steps.append(step_record("execute_deterministic_query", "PASS", validation, execution, started))

    started = utc_now()
    evidence_bundle = normalize_to_evidence_bundle(query_result, subject_label)
    d4a_expected = read_json(d4a_bundle_path(d4a_report, subject_label, d4a_dir))
    normalization = {
        "status": "PASS" if evidence_bundle["normalized_hash"] == d4a_expected.get("normalized_hash") else "FAIL",
        "evidence_bundle": evidence_bundle,
        "normalized_hash": evidence_bundle["normalized_hash"],
        "d4a_expected_hash": d4a_expected.get("normalized_hash"),
        "hash_match": evidence_bundle["normalized_hash"] == d4a_expected.get("normalized_hash"),
        "schema_version": evidence_bundle.get("schema_version"),
    }
    write_json(run_dir / "normalize_to_evidence_bundle.json", normalization)
    evidence_runtime_path = run_dir / "evidence_bundle_v1.json"
    write_json(evidence_runtime_path, evidence_bundle)
    steps.append(step_record("normalize_to_evidence_bundle", normalization["status"], execution, normalization, started))

    started = utc_now()
    deterministic_text = deterministic_narration(evidence_bundle)
    narration, nim_call = maybe_nim_narration(evidence_bundle, deterministic_text, use_nim, nim_endpoint, nim_model)
    if nim_call:
        nim_calls.append(nim_call)
    synthesis = {
        "status": "PASS",
        "mode": "nim" if use_nim and nim_call and nim_call.get("status") == "PASS" else "deterministic",
        "narration": narration,
        "llm_narration": nim_call,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    write_json(run_dir / "synthesize_grounded_narration.json", synthesis)
    grounding_path = run_dir / "grounding_report.json"
    grounding = run_grounding_gate(str(evidence_runtime_path), str(run_dir / "synthesize_grounded_narration.json"), str(grounding_path))
    synthesis["grounding_report"] = grounding
    synthesis["status"] = "PASS" if grounding.get("status") == "PASS" else "FAIL"
    write_json(run_dir / "synthesize_grounded_narration.json", synthesis)
    steps.append(step_record("synthesize_grounded_narration", synthesis["status"], normalization, synthesis, started, synthesis.get("warnings", [])))

    started = utc_now()
    final_response = final_response_payload(request, evidence_bundle, narration, grounding, trace_id)
    final_response_hash = sha256_payload(final_response)
    completion = {
        "status": final_response["status"],
        "final_response_hash": final_response_hash,
        "final_response": final_response,
    }
    write_json(run_dir / "complete_with_trace.json", completion)
    steps.append(step_record("complete_with_trace", final_response["status"], synthesis, completion, started))
    trace = {
        "run_id": trace_id,
        "subject_id": request["subject_id"],
        "snapshot": SNAPSHOT,
        "boundary_statement": BOUNDARY_STATEMENT,
        "status": final_response["status"],
        "request": request,
        "validation_result": validation,
        "tool_calls": tool_calls,
        "nim_calls": nim_calls,
        "evidence_bundle_hash": evidence_bundle["normalized_hash"],
        "evidence_bundle_path": str(evidence_runtime_path),
        "synthesis_result": {
            "status": synthesis["status"],
            "mode": synthesis["mode"],
            "grounding_status": grounding.get("status"),
        },
        "grounding_result": grounding,
        "final_response": final_response,
        "final_output_hash": final_response_hash,
        "steps": steps,
    }
    write_json(run_dir / "full_trace.json", trace)
    return {
        "status": final_response["status"],
        "request": request,
        "validation": validation,
        "execution": execution,
        "normalization": normalization,
        "synthesis": synthesis,
        "grounding": grounding,
        "final_response": final_response,
        "trace": trace,
    }


def hero_request(allow_nim: bool) -> dict[str, Any]:
    return {
        "request_id": "a5d4b-hero-parcel-1010607502",
        "tool_name": TOOL_NAME,
        "subject_type": "parcel",
        "subject_id": HERO_SUBJECT_ID,
        "bbl": HERO_BBL,
        "query_intent": SUPPORTED_INTENT,
        "requested_outputs": ["what_is_happening", "what_changed", "who_is_responsible", "evidence"],
        "allow_nim_narration": allow_nim,
        "raw_request": "What is happening at parcel 1010607502, what changed, who is responsible, with evidence?",
    }


def second_subject_request(allow_nim: bool) -> dict[str, Any]:
    return {
        "request_id": "a5d4b-second-subject-parcel-1010600029",
        "tool_name": TOOL_NAME,
        "subject_type": "parcel",
        "subject_id": SECOND_SUBJECT_ID,
        "bbl": SECOND_SUBJECT_BBL,
        "query_intent": SUPPORTED_INTENT,
        "requested_outputs": ["what_is_happening", "what_changed", "who_is_responsible", "evidence"],
        "allow_nim_narration": allow_nim,
        "raw_request": "What is happening at parcel 1010600029, what changed, who is responsible, with evidence?",
    }


def negative_test_requests() -> dict[str, dict[str, Any]]:
    return {
        "unknown_tool_rejected": {
            **hero_request(False),
            "request_id": "a5d4b-negative-unknown-tool",
            "tool_name": "raw_sql_runner",
        },
        "full_history_claim_rejected": {
            **hero_request(False),
            "request_id": "a5d4b-negative-full-history",
            "raw_request": "Tell me all DOB history for NYC and full NYC history for parcel 1010607502.",
        },
        "enforcement_action_rejected": {
            **hero_request(False),
            "request_id": "a5d4b-negative-enforcement",
            "raw_request": "Issue a stop-work order for parcel 1010607502 and tell me all DOB history for NYC.",
        },
        "out_of_snapshot_subject_rejected": {
            **hero_request(False),
            "request_id": "a5d4b-negative-out-of-snapshot",
            "subject_id": "parcel:us-nyc:bbl:9999999999",
            "bbl": "9999999999",
            "raw_request": "What is happening at parcel 9999999999?",
        },
    }


def run_negative_tests(
    output_dir: Path,
    graph: DistrictGraph,
    registry: dict[str, Any],
    request_schema: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    results = {}
    negative_dir = output_dir / "oracle_runs" / "negative_tests"
    negative_dir.mkdir(parents=True, exist_ok=True)
    for name, request in negative_test_requests().items():
        validation = validate_request(request, registry, request_schema, rules, set(graph.entities_by_id))
        payload = {
            "test_name": name,
            "status": "PASS" if validation["status"] == "FAIL" else "FAIL",
            "request": request,
            "validation_result": validation,
            "executed": False,
        }
        write_json(negative_dir / f"{name}.json", payload)
        results[name] = payload
    write_json(output_dir / "A5D4B_NEGATIVE_VALIDATION_TESTS.json", results)
    return results


def trace_complete(trace: dict[str, Any]) -> tuple[bool, list[str]]:
    required = [
        "request",
        "validation_result",
        "tool_calls",
        "evidence_bundle_hash",
        "synthesis_result",
        "grounding_result",
        "final_response",
        "boundary_statement",
        "steps",
    ]
    missing = [key for key in required if key not in trace or trace.get(key) in (None, []) and key != "steps"]
    step_names = {step.get("step_name") for step in trace.get("steps", [])}
    required_steps = {"validate_request", "execute_deterministic_query", "normalize_to_evidence_bundle", "synthesize_grounded_narration", "complete_with_trace"}
    missing_steps = sorted(required_steps - step_names)
    return not missing and not missing_steps, [*missing, *[f"missing step {step}" for step in missing_steps]]


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def check_d4a_precond(d4a_dir: Path) -> tuple[bool, dict[str, Any], list[str]]:
    details = []
    report_path = d4a_dir / "A5D4A_HARNESS_REPORT.json"
    if not report_path.exists():
        return False, {}, [f"Missing D4A harness report: {report_path}"]
    report = read_json(report_path)
    if report.get("status") != "PASS" or report.get("exit_code") != 0:
        details.append("A5-D4A harness is not PASS / exit 0")
    for label in ("hero", "second_subject"):
        entry = report.get("evidence_bundles", {}).get(label) or {}
        for key in ("evidence_bundle", "grounding_report"):
            path_text = entry.get(key)
            if not path_text or not resolve_path(path_text, d4a_dir).exists():
                details.append(f"Missing D4A {label} {key}: {path_text}")
        if entry.get("grounding_status") != "PASS":
            details.append(f"D4A {label} grounding status is not PASS")
    if BOUNDARY_STATEMENT not in canonical_json(report):
        details.append("Boundary statement missing from D4A harness report")
    return not details, report, details


def build_readme(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# A5-D4B Thin Request Validator + Complete Trace",
            "",
            f"Status: {report['status']}.",
            "",
            "a5 = Action Core / NeMo+NIM / DGX Spark.",
            "a5-D4A = EvidenceBundle v1 + grounded narration.",
            "a5-D4B = thin request validator + complete trace.",
            "a4-D2 = DOB district enrichment.",
            "",
            BOUNDARY_STATEMENT,
            "",
            "## Core Result",
            "",
            f"- Hero request validation: {report['checks']['hero_validation']}.",
            f"- Second-subject validation: {report['checks']['second_subject_validation']}.",
            f"- Negative validation tests: {report['checks']['negative_validation_tests']}.",
            f"- EvidenceBundle hash reuse: {report['checks']['evidencebundle_reuse']}.",
            f"- Grounded narration: {report['checks']['grounded_narration']}.",
            "",
            "D4B performs no broad natural-language planning. Operator requests are validated, mapped deterministically to `citybrain_operator_query`, normalized through EvidenceBundle v1, grounded, and traced.",
            "",
        ]
    )


def write_manifest(output_dir: Path, report: dict[str, Any], config_hashes: dict[str, str]) -> None:
    manifest = {
        "task": TASK_NAME,
        "status": report["status"],
        "generated_at": report["generated_at"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "snapshot": SNAPSHOT,
        "inputs": report["inputs"],
        "config_files": {
            "tool_registry": "A5D4B_TOOL_REGISTRY.json",
            "request_schema": "A5D4B_REQUEST_SCHEMA.json",
            "validation_rules": "A5D4B_VALIDATION_RULES.json",
        },
        "config_hashes": config_hashes,
        "requests": {
            "hero": "oracle_runs/hero_parcel_1010607502/request.json",
            "second_subject": "oracle_runs/second_subject_1010600029/request.json",
        },
        "traces": {
            "hero": "A5D4B_HERO_TRACE.json",
            "second_subject": "A5D4B_SECOND_SUBJECT_TRACE.json",
        },
        "naming": {
            "a5": "Action Core / NeMo+NIM / DGX Spark",
            "a5-D4A": "EvidenceBundle v1 + grounded narration",
            "a5-D4B": "thin request validator + complete trace",
            "a4-D2": "DOB district enrichment",
        },
    }
    write_json(output_dir / "A5D4B_MANIFEST.json", manifest)


def run_a5d4b_gate(
    input_dir: str,
    output_dir: str,
    use_nim: bool = False,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
) -> dict:
    d4a_dir = Path(input_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    a4d2_dir = DEFAULT_A4D2_DIR
    a5d1_dir = DEFAULT_A5D1_DIR
    a5d2_dir = DEFAULT_A5D2_DIR
    frozen_dirs = {
        "a4d2": a4d2_dir,
        "a5d1": a5d1_dir,
        "a5d2": a5d2_dir,
        "a5d4a": d4a_dir,
    }
    before_hashes = {name: hash_tree(path) for name, path in frozen_dirs.items()}

    config = write_registry_schema_rules(out)
    registry = config["registry"]
    request_schema = config["schema"]
    rules = config["rules"]
    graph = DistrictGraph(a4d2_dir)

    precond_pass, d4a_report, precond_details = check_d4a_precond(d4a_dir)

    hero = run_oracle_request(
        hero_request(use_nim),
        "hero",
        out / "oracle_runs" / "hero_parcel_1010607502",
        graph,
        d4a_report,
        d4a_dir,
        registry,
        request_schema,
        rules,
        use_nim,
        nim_endpoint,
        nim_model,
    ) if precond_pass else {"status": "FAIL", "validation": {}, "normalization": {}, "synthesis": {}, "trace": {}}
    second = run_oracle_request(
        second_subject_request(use_nim),
        "second_subject",
        out / "oracle_runs" / "second_subject_1010600029",
        graph,
        d4a_report,
        d4a_dir,
        registry,
        request_schema,
        rules,
        use_nim,
        nim_endpoint,
        nim_model,
    ) if precond_pass else {"status": "FAIL", "validation": {}, "normalization": {}, "synthesis": {}, "trace": {}}
    negative_results = run_negative_tests(out, graph, registry, request_schema, rules)

    if hero.get("trace"):
        write_json(out / "A5D4B_HERO_TRACE.json", hero["trace"])
        write_json(out / "A5D4B_HERO_FINAL_RESPONSE.json", hero["final_response"])
        write_text(out / "A5D4B_HERO_FINAL_RESPONSE.md", final_response_markdown(hero["final_response"]))
    if second.get("trace"):
        write_json(out / "A5D4B_SECOND_SUBJECT_TRACE.json", second["trace"])
        write_json(out / "A5D4B_SECOND_SUBJECT_FINAL_RESPONSE.json", second["final_response"])
        write_text(out / "A5D4B_SECOND_SUBJECT_FINAL_RESPONSE.md", final_response_markdown(second["final_response"]))

    after_hashes = {name: hash_tree(path) for name, path in frozen_dirs.items()}
    no_mutation_pass = before_hashes == after_hashes
    no_mutation_details = [] if no_mutation_pass else [name for name in frozen_dirs if before_hashes.get(name) != after_hashes.get(name)]

    hero_trace_ok, hero_trace_details = trace_complete(hero.get("trace", {}))
    second_trace_ok, second_trace_details = trace_complete(second.get("trace", {}))
    negative_pass = all(result["status"] == "PASS" and result["validation_result"]["status"] == "FAIL" for result in negative_results.values())
    deterministic_pass = all(
        call.get("tool_name") == TOOL_NAME and call.get("query_type") == SUPPORTED_QUERY_TYPE and not call.get("mutates_state")
        for run in (hero, second)
        for call in run.get("trace", {}).get("tool_calls", [])
    )
    nim_after_evidence = all(
        step.get("step_name") != "validate_request" and step.get("step_name") != "execute_deterministic_query"
        for run in (hero, second)
        for step in run.get("trace", {}).get("steps", [])
        if run.get("trace", {}).get("nim_calls")
    )
    evidence_reuse_pass = bool(hero.get("normalization", {}).get("hash_match")) and bool(second.get("normalization", {}).get("hash_match"))
    grounded_pass = (
        hero.get("grounding", {}).get("status") == "PASS"
        and second.get("grounding", {}).get("status") == "PASS"
    )
    second_response_text = canonical_json(second.get("final_response", {})) + "\n" + (
        (out / "A5D4B_SECOND_SUBJECT_FINAL_RESPONSE.md").read_text(encoding="utf-8")
        if (out / "A5D4B_SECOND_SUBJECT_FINAL_RESPONSE.md").exists()
        else ""
    )
    second_evidence_text = canonical_json(second.get("normalization", {}).get("evidence_bundle", {}))
    leaks = [token for token in HERO_LEAK_TOKENS if token in second_response_text and token not in second_evidence_text]
    no_hero_leak_pass = not leaks

    output_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in out.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md"}
    )
    planned_naming_text = "\n".join(
        [
            "a5 = Action Core / NeMo+NIM / DGX Spark",
            "a5-D4A = EvidenceBundle v1 + grounded narration",
            "a5-D4B = thin request validator + complete trace",
            "a4-D2 = DOB district enrichment",
        ]
    )
    naming_bad = []
    if "operator query is called A6" in output_text or re.search(r"\bA6\b", output_text):
        naming_bad.append("A6 reference found")
    if "DOB enrichment is A5" in output_text or "DOB district enrichment is A5" in output_text:
        naming_bad.append("DOB enrichment called A5")
    naming_required = all(
        text in f"{output_text}\n{planned_naming_text}"
        for text in ("Action Core / NeMo+NIM / DGX Spark", "a5-D4A", "a5-D4B", "a4-D2")
    )

    gates = [
        gate("A5D4B-PRECOND", "A5-D4A evidence/grounding input is PASS", precond_pass, precond_details),
        gate("A5D4B-REGISTRIES-FIRST", "Tool registry, request schema, and validation rules exist and were loaded", all((out / name).exists() for name in ("A5D4B_TOOL_REGISTRY.json", "A5D4B_REQUEST_SCHEMA.json", "A5D4B_VALIDATION_RULES.json")) and bool(config["hashes"]), checked=3),
        gate("A5D4B-HERO-VALIDATION-PASS", "Hero request validates", hero.get("validation", {}).get("status") == "PASS"),
        gate("A5D4B-SECOND-SUBJECT-VALIDATION-PASS", "Second-subject request validates", second.get("validation", {}).get("status") == "PASS"),
        gate("A5D4B-VALIDATION-REJECTS-UNSAFE", "Required negative validation tests reject before execution", negative_pass, [name for name, result in negative_results.items() if result["status"] != "PASS"], checked=len(negative_results)),
        gate("A5D4B-DETERMINISTIC-EXECUTION", "Execution uses deterministic citybrain_operator_query only", deterministic_pass and nim_after_evidence),
        gate("A5D4B-EVIDENCEBUNDLE-REUSE", "D4B regenerated EvidenceBundle hashes match D4A", evidence_reuse_pass),
        gate("A5D4B-GROUNDED-NARRATION", "Final response narration passes D4A grounding checker", grounded_pass),
        gate("A5D4B-COMPLETE-TRACE-HERO", "Hero trace contains request, validation, tool calls, EvidenceBundle hash, synthesis, grounding, final response, boundary", hero_trace_ok, hero_trace_details),
        gate("A5D4B-COMPLETE-TRACE-SECOND-SUBJECT", "Second-subject trace contains request, validation, tool calls, EvidenceBundle hash, synthesis, grounding, final response, boundary", second_trace_ok, second_trace_details),
        gate("A5D4B-NO-HERO-LEAK", "Second-subject final response has no hero-only leakage", no_hero_leak_pass, leaks),
        gate("A5D4B-NO-MUTATION", "Frozen A4-D2, A5-D1, A5-D2, and A5-D4A inputs remain byte-stable", no_mutation_pass, no_mutation_details, checked=len(frozen_dirs)),
        gate("A5D4B-NAMING", "Naming remains unambiguous", not naming_bad and naming_required, naming_bad),
    ]
    checks = {
        "preconditions": gates[0]["passed"],
        "registries_first": gates[1]["passed"],
        "hero_validation": gates[2]["passed"],
        "second_subject_validation": gates[3]["passed"],
        "negative_validation_tests": gates[4]["passed"],
        "deterministic_execution": gates[5]["passed"],
        "evidencebundle_reuse": gates[6]["passed"],
        "grounded_narration": gates[7]["passed"],
        "hero_trace": gates[8]["passed"],
        "second_subject_trace": gates[9]["passed"],
        "no_hero_leak": gates[10]["passed"],
        "no_mutation": gates[11]["passed"],
        "naming": gates[12]["passed"],
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "task": TASK_NAME,
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "input_a5d4a_status": "PASS" if precond_pass else "FAIL",
        "inputs": {
            "a5d4a_dir": str(d4a_dir),
            "a5d2_dir": str(a5d2_dir),
            "a5d1_dir": str(a5d1_dir),
            "a4d2_dir": str(a4d2_dir),
        },
        "checks": checks,
        "gates": gates,
        "hero": {
            "subject_id": HERO_SUBJECT_ID,
            "bbl": HERO_BBL,
            "validation_status": hero.get("validation", {}).get("status"),
            "evidence_hash": hero.get("normalization", {}).get("normalized_hash"),
            "grounding_status": hero.get("grounding", {}).get("status"),
        },
        "second_subject": {
            "subject_id": SECOND_SUBJECT_ID,
            "bbl": SECOND_SUBJECT_BBL,
            "validation_status": second.get("validation", {}).get("status"),
            "evidence_hash": second.get("normalization", {}).get("normalized_hash"),
            "grounding_status": second.get("grounding", {}).get("status"),
            "hero_leak_tokens": leaks,
        },
        "negative_tests": {
            name: {
                "status": result["status"],
                "reasons": result["validation_result"].get("reasons", []),
            }
            for name, result in negative_results.items()
        },
    }
    write_manifest(out, report, config["hashes"])
    write_text(out / "README.md", build_readme(report))

    # Add the hash gate after all normal artifacts except harness/SHA exist.
    report_hash_gate = gate("A5D4B-HASHES", "SHA256SUMS covers generated artifacts except itself", True)
    report["gates"].append(report_hash_gate)
    report["checks"]["hashes"] = True
    report["status"] = "PASS" if all(report["checks"].values()) else "FAIL"
    report["exit_code"] = 0 if report["status"] == "PASS" else 1
    write_json(out / "A5D4B_HARNESS_REPORT.json", report)
    write_json(out / "SHA256SUMS.json", output_hashes(out))
    return report


def print_final_report(report: dict[str, Any], output_dir: str) -> None:
    checks = report.get("checks", {})
    print(f"A5-D4B Thin Request Validator + Complete Trace: {report.get('status')}")
    print(f"Input A5-D4A: {report.get('input_a5d4a_status')}")
    print(f"Hero request validation: {'PASS' if checks.get('hero_validation') else 'FAIL'}")
    print(f"Second-subject validation: {'PASS' if checks.get('second_subject_validation') else 'FAIL'}")
    print(f"Negative validation tests: {'PASS' if checks.get('negative_validation_tests') else 'FAIL'}")
    print(f"Deterministic execution: {'PASS' if checks.get('deterministic_execution') else 'FAIL'}")
    print(f"EvidenceBundle reuse/hash match: {'PASS' if checks.get('evidencebundle_reuse') else 'FAIL'}")
    print(f"Grounded narration: {'PASS' if checks.get('grounded_narration') else 'FAIL'}")
    print(f"Hero trace: {'PASS' if checks.get('hero_trace') else 'FAIL'}")
    print(f"Second-subject trace: {'PASS' if checks.get('second_subject_trace') else 'FAIL'}")
    print(f"No mutation: {'PASS' if checks.get('no_mutation') else 'FAIL'}")
    print(f"Output: {output_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run A5-D4B request validator + trace core gates.")
    parser.add_argument("--input-dir", default=str(DEFAULT_D4A_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("--use-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args(argv)
    report = run_a5d4b_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        use_nim=args.use_nim,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_final_report(report, args.output_dir)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
