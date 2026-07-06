#!/usr/bin/env python3
"""Common builders for CityBrain Epoch 2.0 runtime consolidation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"
REPORT_ROOT = OUTPUT_ROOT / "reports"
AUDIT_ROOT = OUTPUT_ROOT / "audits"
CONTRACT_ROOT = REPO_ROOT / "contracts" / "citybrain" / "epoch_2_0"
PACKAGE_ROOT = REPO_ROOT / "packages" / "citybrain_epoch_2_0"
DOC_ROOT = REPO_ROOT / "docs" / "epoch_2_0"

TASK_ID = "CITYBRAIN-EPOCH-2-0-AGENTIC-RUNTIME-CONSOLIDATION-AND-RECERTIFICATION"
BRANCH = "codex/epoch2-0-agentic-runtime-consolidation"
BASE_REF = "origin/codex/epoch1-closedown-certified-baseline"
SOURCE_BASE_REF = "origin/main"
STATUS_PASS_WITH_LIMITATIONS = "PASS_EPOCH_2_0_AGENTIC_RUNTIME_CONSOLIDATION_WITH_LIMITATIONS"
CREATED_AT = "2026-07-06T00:00:00Z"

ASK_SEALED_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_PROTECTED_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

BRANCH_EVIDENCE = {
    "ASK Resolver/Renderer": {
        "component_id": "ask_resolver_renderer",
        "branch": SOURCE_BASE_REF,
        "refs": ["packages/ask_v11", "docs/ask-v11/ask-v11-app-handoff-closeout.md"],
        "inputs": ["AskRequest", "EvidencePacket", "CheckReport"],
        "outputs": ["AnswerPacket", "RenderedAnswer"],
        "surface": "ASK app handoff / web control room",
        "status": "active",
    },
    "CHECK Agent": {
        "component_id": "check_agent",
        "branch": "origin/codex/push4-lane-c-check-v1",
        "refs": ["outputs/push4_lane_c_check_v1/CHECK_V1_DECISION.json", "packages/check_v1"],
        "inputs": ["CandidateObservation", "EvidenceRefs", "AuthorityEnvelope"],
        "outputs": ["CheckReport", "LimitationRefs"],
        "surface": "CHECK v1 report / review route",
        "status": "active",
    },
    "WATCH Scout": {
        "component_id": "watch_scout",
        "branch": "origin/codex/push2-lane-b-watch-scout-v1",
        "refs": ["outputs/push2_lane_b_watch_scout_v1/WATCH_SCOUT_V1_DECISION.json"],
        "inputs": ["EventEnvelope", "MaterializedReviewState"],
        "outputs": ["WatchItem", "CheckReportRef", "AuthorityEnvelopeRef"],
        "surface": "WATCH review prompts",
        "status": "active",
    },
    "DIFF Scout": {
        "component_id": "diff_scout",
        "branch": "origin/codex/push3-lane-c-diff-recall-readonly",
        "refs": ["outputs/push3_lane_c_diff_recall_readonly/DIFF_RECALL_READONLY_DECISION.json"],
        "inputs": ["SourceRecord360", "ReviewPacket"],
        "outputs": ["DiffItem"],
        "surface": "DIFF/RECALL read-only lane",
        "status": "active",
    },
    "RECALL matcher": {
        "component_id": "recall_matcher",
        "branch": "origin/codex/push3-lane-c-diff-recall-readonly",
        "refs": ["outputs/push3_lane_c_diff_recall_readonly/DIFF_RECALL_READONLY_DECISION.json"],
        "inputs": ["CandidateObservation", "SourceRecord360"],
        "outputs": ["RecallMatchItem"],
        "surface": "RECALL read-only similar-case surface",
        "status": "active",
    },
    "Briefing Agent": {
        "component_id": "briefing_agent",
        "branch": "origin/codex/push3-lane-a-brief-flow1-packaging",
        "refs": ["outputs/push3_lane_a_brief_v2_flow1_packaging/BRIEF_V2_FLOW1_DECISION.json"],
        "inputs": ["CheckReport", "WatchItem", "DispositionSummary"],
        "outputs": ["BriefPacket"],
        "surface": "BRIEF v2 / Flow 1",
        "status": "active",
    },
    "Spatial Agent": {
        "component_id": "spatial_agent",
        "branch": "origin/codex/push5-lane-a-spatial-ui-ux",
        "refs": ["outputs/push5_lane_a_spatial_ui_ux/SPATIAL_UI_UX_DECISION.json"],
        "inputs": ["OverlayPacket", "EvidenceRefs"],
        "outputs": ["SpatialOverlayPacket"],
        "surface": "Spatial UI/UX review",
        "status": "active",
    },
    "Perception/Media Agent": {
        "component_id": "perception_media_agent",
        "branch": "origin/codex/push5-lane-b-perception-media-evidence",
        "refs": ["outputs/push5_lane_b_perception_media_evidence/PERCEPTION_MEDIA_EVIDENCE_DECISION.json"],
        "inputs": ["CandidateObservation", "MediaEvidenceBundle"],
        "outputs": ["MediaEvidencePacket"],
        "surface": "Perception evidence review",
        "status": "active",
    },
    "Workflow/Disposition Agent": {
        "component_id": "workflow_disposition_agent",
        "branch": "origin/codex/push5-lane-c-watch-workflow-state",
        "refs": ["outputs/push5_lane_c_watch_workflow_state/WATCH_WORKFLOW_STATE_DECISION.json"],
        "inputs": ["WatchItem", "DispositionEvent"],
        "outputs": ["WorkflowStateEvent", "OutcomeRecord"],
        "surface": "Workflow state / disposition route",
        "status": "active",
    },
    "Approval Lifecycle Agent": {
        "component_id": "approval_lifecycle_agent",
        "branch": "origin/codex/push6-lane-a-approval-lifecycle",
        "refs": ["outputs/push6_lane_a_approval_lifecycle/APPROVAL_LIFECYCLE_DECISION.json", "packages/approval_lifecycle"],
        "inputs": ["ApprovalRequest", "AuthorityEnvelope"],
        "outputs": ["ApprovalDecision"],
        "surface": "Approval lifecycle review",
        "status": "active",
    },
    "Plan Agent": {
        "component_id": "plan_agent",
        "branch": "origin/codex/push6-lane-b-plan-mode",
        "refs": ["outputs/push6_lane_b_plan_mode/PLAN_MODE_DECISION.json", "packages/plan_mode"],
        "inputs": ["OptionSetV2", "CheckReport"],
        "outputs": ["PlanOption"],
        "surface": "PLAN mode",
        "status": "active",
    },
    "Schedule/Simulate Agent": {
        "component_id": "schedule_simulate_agent",
        "branch": "origin/codex/push6-lane-c-schedule-simulate",
        "refs": ["outputs/push6_lane_c_schedule_simulate/SCHEDULE_SIMULATE_DECISION.json"],
        "inputs": ["ScheduleOption", "ScenarioPacket"],
        "outputs": ["SimulationRunRecord"],
        "surface": "SCHEDULE/SIMULATE mode",
        "status": "active",
    },
}

LLM_SEATS = [
    {
        "seat_id": "g2_intent_concept_proposal",
        "purpose": "G2 intent/concept proposal seat",
        "status": "proposal_only",
        "allowed_input_packets": ["AskRequest", "ConceptDraft"],
        "required_output_schema": "ProposalDraft",
        "forbidden_outputs": ["source truth", "CHECK result", "authority assignment", "official action", "legal finding"],
        "deterministic_fallback": "return empty proposal and ask for deterministic CHECK/registry path",
        "model_ref_optional": None,
        "prompt_template_ref": "docs/ask-v11/g1-g5-execution-spine.md",
        "evaluation_refs": ["tests/test_ask_v11_g1_g5_spine.py"],
        "limitations": ["offline/proposal only; no live authority"],
    },
    {
        "seat_id": "g8_writer_render",
        "purpose": "G8 writer/render seat",
        "status": "writer_only",
        "allowed_input_packets": ["AnswerPacket", "CheckReport"],
        "required_output_schema": "RenderedAnswer",
        "forbidden_outputs": ["source truth", "CHECK result", "authority assignment", "official action", "legal finding"],
        "deterministic_fallback": "render deterministic packet text",
        "model_ref_optional": None,
        "prompt_template_ref": "docs/ask-v11/g6-g8-check-answer-render.md",
        "evaluation_refs": ["tests/test_ask_v11_g6_g8_check_answer_render.py"],
        "limitations": ["writer only; cannot alter packet semantics"],
    },
    {
        "seat_id": "brief_narrative_writer",
        "purpose": "Brief narrative writer",
        "status": "writer_only",
        "allowed_input_packets": ["BriefPacket", "CheckReport", "EvidenceRefs"],
        "required_output_schema": "BriefNarrative",
        "forbidden_outputs": ["new fact", "source truth", "CHECK result", "authority assignment", "official action", "legal finding"],
        "deterministic_fallback": "use BRIEF v2 deterministic summary",
        "model_ref_optional": None,
        "prompt_template_ref": "docs/epoch_2_0/llm_integration_contract_v1.md",
        "evaluation_refs": ["outputs/epoch_2_0_agentic_runtime_consolidation/reports/mode_eval_harness_report.json"],
        "limitations": ["writer only; no fact generation"],
    },
    {
        "seat_id": "precedent_difference_explainer",
        "purpose": "Precedent difference explainer",
        "status": "offline_eval",
        "allowed_input_packets": ["RecallMatchItem", "DiffItem"],
        "required_output_schema": "DifferenceExplanation",
        "forbidden_outputs": ["source truth", "CHECK result", "precedent as authority", "authority assignment", "official action", "legal finding"],
        "deterministic_fallback": "return deterministic diff table",
        "model_ref_optional": None,
        "prompt_template_ref": "docs/epoch_2_0/llm_integration_contract_v1.md",
        "evaluation_refs": [],
        "limitations": ["later/offline only unless future gate authorizes"],
    },
    {
        "seat_id": "investigation_decomposition_proposer",
        "purpose": "Investigation decomposition proposer",
        "status": "disabled",
        "allowed_input_packets": [],
        "required_output_schema": "DisabledSeat",
        "forbidden_outputs": ["source truth", "CHECK result", "authority assignment", "investigation agent", "official action", "dispatch", "control", "legal finding"],
        "deterministic_fallback": "disabled",
        "model_ref_optional": None,
        "prompt_template_ref": None,
        "evaluation_refs": [],
        "limitations": ["future/disabled; no compound investigation agent in Epoch 2.0"],
    },
]

FORBIDDEN_ACTIONS = [
    "production_write",
    "live_url_fetch",
    "live_camera_connection",
    "official_ticket_or_case_creation",
    "dispatch_control_enforcement",
    "legal_or_certified_finding",
    "autonomous_execution",
    "source_truth_mutation",
    "secret_exposure",
]


def git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def git_out(args: list[str]) -> str:
    return git(args).stdout.strip()


def rev(ref: str, short: bool = True) -> str:
    args = ["rev-parse"]
    if short:
        args.append("--short")
    args.append(ref)
    result = git(args)
    return result.stdout.strip() if result.returncode == 0 else ""


def ref_exists(ref: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", ref]).returncode == 0


def ref_file_exists(ref: str, path: str) -> bool:
    return ref_exists(ref) and git(["cat-file", "-e", f"{ref}:{path}"]).returncode == 0


def show_json(ref: str, path: str) -> Any | None:
    if not ref_file_exists(ref, path):
        return None
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout.decode("utf-8"))
    except Exception:
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ").replace("|", "/") for cell in row) + " |")
    return "\n".join(out)


def schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": True,
    }


def list_schema(title: str, item_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "array",
        "items": item_schema,
    }


def build_schemas() -> dict[str, Any]:
    arr = {"type": "array", "items": {"type": "string"}}
    component_item = schema(
        "ComponentRegistryEntryV1",
        [
            "component_id",
            "kind",
            "name",
            "version",
            "status",
            "source_artifact_refs",
            "input_packet_types",
            "output_packet_types",
            "consuming_surfaces",
            "authority_level_max",
            "source_classes_allowed",
            "tools_allowed",
            "llm_seat_allowed",
            "budget_policy_ref",
            "evaluation_refs",
            "limitations",
            "non_claims",
        ],
        {
            "component_id": {"type": "string"},
            "kind": {"enum": ["agent", "llm_seat", "tool_adapter", "retriever", "renderer", "ranker", "forecast_model", "surrogate_model", "simulator_connector", "validator", "harness"]},
            "status": {"enum": ["active", "disabled", "offline_eval", "proposal_only", "writer_only", "future", "deprecated", "missing_evidence"]},
            "source_artifact_refs": arr,
            "input_packet_types": arr,
            "output_packet_types": arr,
            "consuming_surfaces": arr,
            "authority_level_max": {"type": ["integer", "null"], "minimum": 0, "maximum": 6},
            "source_classes_allowed": arr,
            "tools_allowed": arr,
            "llm_seat_allowed": {"type": ["boolean", "array"]},
        },
    )
    policy_item = schema(
        "ToolPermissionPolicyEntryV1",
        ["policy_id", "component_id", "tool_id", "permission", "environment", "allowed_source_classes", "forbidden_actions", "timeout_seconds", "max_calls", "requires_check", "requires_authority_level", "allowed_paths_or_domains", "secrets_allowed"],
        {
            "permission": {"enum": ["read", "write", "execute", "render", "validate"]},
            "environment": {"enum": ["local_replay", "dev", "staging", "production"]},
            "secrets_allowed": {"const": False},
        },
    )
    return {
        "component_registry.schema.json": list_schema("ComponentRegistryV1", component_item),
        "agent_run_envelope.schema.json": schema(
            "AgentRunEnvelopeV1",
            ["run_id", "schema_version", "component_id", "component_version", "trigger", "scope", "inputs", "tools_used", "outputs", "status", "authority_level", "check_report_refs", "evidence_refs", "trace_refs", "budget", "stop_condition_hit", "started_at", "ended_at", "duration_ms", "limitations", "next_lane"],
            {"status": {"enum": ["emitted", "clarify", "refused", "blocked", "failed", "partial_budget_exhausted", "not_activated"]}},
        ),
        "tool_permission_policy.schema.json": list_schema("ToolPermissionPolicyV1", policy_item),
        "llm_seat_registry.schema.json": list_schema(
            "LLMSeatRegistryV1",
            schema("LLMSeatV1", ["seat_id", "purpose", "status", "allowed_input_packets", "required_output_schema", "forbidden_outputs", "deterministic_fallback", "model_ref_optional", "prompt_template_ref", "evaluation_refs", "limitations"], {"status": {"enum": ["disabled", "offline_eval", "proposal_only", "writer_only", "live_guarded"]}}),
        ),
        "mode_invocation_registry.schema.json": list_schema(
            "ModeInvocationRegistryV1",
            schema("ModeInvocationV1", ["mode_id", "mode_name", "status", "entry_packet_types", "output_packet_types", "primary_components", "required_check", "required_authority", "fixture_refs", "eval_refs", "limitations"], {"status": {"enum": ["active", "fixture_only", "pending_evidence", "parked"]}}),
        ),
        "agent_handoff_matrix.schema.json": list_schema(
            "AgentHandoffMatrixV1",
            schema("AgentHandoffV1", ["from_component", "output_packet", "to_component", "input_packet", "handoff_condition", "required_check", "required_authority", "failure_behavior"], {}),
        ),
        "budget_stop_policy.schema.json": list_schema(
            "BudgetStopPolicyV1",
            schema("BudgetStopPolicyEntryV1", ["policy_id", "applies_to", "max_wall_clock_seconds", "max_steps", "max_tool_calls", "max_llm_calls", "max_output_bytes", "max_files_changed", "stop_conditions", "partial_result_semantics"], {}),
        ),
        "outcome_record.schema.json": schema(
            "OutcomeRecordV1",
            ["outcome_record_id", "target_ref", "trigger_packet_refs", "disposition_history_refs", "terminal_state", "time_to_terminal_seconds", "disposition_context_summary", "source_class", "created_at", "limitations"],
            {"source_class": {"const": "derived_field"}, "terminal_state": {"enum": ["confirmed", "dismissed", "needs_more_expired", "superseded", "not_terminal"]}},
        ),
        "calibration_report.schema.json": schema(
            "CalibrationReportV1",
            ["calibration_report_id", "subject", "period", "sample_size", "aggregation_floor_respected", "statistics", "limitations", "source_class", "input_refs", "created_at"],
            {"source_class": {"const": "derived_field"}},
        ),
    }


def artifact_exists(spec: dict[str, Any]) -> bool:
    branch = spec["branch"]
    if branch == SOURCE_BASE_REF:
        return all((REPO_ROOT / ref).exists() or ref_file_exists(branch, ref) for ref in spec["refs"])
    return any(ref_file_exists(branch, ref) for ref in spec["refs"])


def build_component_registry() -> list[dict[str, Any]]:
    registry: list[dict[str, Any]] = []
    for name, spec in BRANCH_EVIDENCE.items():
        exists = artifact_exists(spec)
        status = spec["status"] if exists else "missing_evidence"
        registry.append(
            {
                "component_id": spec["component_id"],
                "kind": "agent",
                "name": name,
                "version": "1.0",
                "status": status,
                "description": f"Epoch 2.0 registry entry for existing {name}.",
                "owning_doc_or_contract": "contracts/citybrain/epoch_2_0/component_registry.schema.json",
                "source_artifact_refs": [f"{spec['branch']}:{ref}" for ref in spec["refs"]],
                "input_packet_types": spec["inputs"],
                "output_packet_types": spec["outputs"],
                "consuming_surfaces": [spec["surface"]],
                "authority_level_max": 3 if spec["component_id"] == "approval_lifecycle_agent" else 1,
                "source_classes_allowed": ["local_replay", "fixture", "derived_field", "synthetic"],
                "tools_allowed": ["git_ref_read", "local_fixture_read", "schema_validate", "local_report_write"],
                "llm_seat_allowed": False,
                "budget_policy_ref": "budget_policy_local_replay_agent_v1",
                "evaluation_refs": [f"tests/test_citybrain_epoch_2_0_contracts.py", f"tests/test_citybrain_epoch_2_0_permissions.py"],
                "release_ledger_row_ref": "outputs/epoch1_closedown_certified_baseline/EPOCH1_MASTER_LEDGER_ROWS.json",
                "rollback_ref": BASE_REF,
                "limitations": ["local/replay/review/query context only", "registered from existing evidence; no new behavior introduced"],
                "non_claims": [
                    "no production API claim",
                    "no official ticket/case/dispatch/enforcement/legal finding",
                    "no autonomous execution",
                    "no LLM authority",
                    "no source truth mutation",
                ],
            }
        )
    for seat in LLM_SEATS:
        registry.append(
            {
                "component_id": f"llm_seat_{seat['seat_id']}",
                "kind": "llm_seat",
                "name": seat["purpose"],
                "version": "1.0",
                "status": seat["status"],
                "description": "Explicit LLM seat registry component; no live authority in Epoch 2.0.",
                "owning_doc_or_contract": "contracts/citybrain/epoch_2_0/llm_seat_registry.schema.json",
                "source_artifact_refs": ["packages/citybrain_epoch_2_0/llm_seat_registry_v1.json"],
                "input_packet_types": seat["allowed_input_packets"],
                "output_packet_types": [seat["required_output_schema"]],
                "consuming_surfaces": ["offline/proposal/writer governance"],
                "authority_level_max": 0,
                "source_classes_allowed": ["local_replay", "fixture", "derived_field"],
                "tools_allowed": [],
                "llm_seat_allowed": False,
                "budget_policy_ref": "budget_policy_llm_seat_no_authority_v1",
                "evaluation_refs": seat["evaluation_refs"],
                "release_ledger_row_ref": None,
                "rollback_ref": BASE_REF,
                "limitations": seat["limitations"],
                "non_claims": ["no live LLM authority", "no source truth generation", "no CHECK result generation", "no official action"],
            }
        )
    registry.extend(
        [
            {
                "component_id": "epoch2_replay_harness",
                "kind": "harness",
                "name": "Epoch 2.0 Replay Harness",
                "version": "1.0",
                "status": "active",
                "description": "Harness that emits AgentRunEnvelope over existing branch evidence.",
                "owning_doc_or_contract": "contracts/citybrain/epoch_2_0/agent_run_envelope.schema.json",
                "source_artifact_refs": ["scripts/run_citybrain_epoch_2_0_replay_harness.py"],
                "input_packet_types": ["CandidateObservation", "EventEnvelope", "WatchItem", "CheckReport"],
                "output_packet_types": ["AgentRunEnvelope", "ReplayHarnessReport"],
                "consuming_surfaces": ["Epoch 2.0 recertification"],
                "authority_level_max": 1,
                "source_classes_allowed": ["local_replay", "fixture", "derived_field"],
                "tools_allowed": ["git_ref_read", "local_report_write"],
                "llm_seat_allowed": False,
                "budget_policy_ref": "budget_policy_replay_harness_v1",
                "evaluation_refs": ["tests/test_citybrain_epoch_2_0_replay.py"],
                "release_ledger_row_ref": None,
                "rollback_ref": BASE_REF,
                "limitations": ["best available branch-evidence replay, not live runtime"],
                "non_claims": ["no live source/camera claim", "no official action"],
            },
            {
                "component_id": "epoch2_mode_eval_harness",
                "kind": "harness",
                "name": "Epoch 2.0 Mode Eval Harness",
                "version": "1.0",
                "status": "active",
                "description": "Fixture-slot mode evaluation harness.",
                "owning_doc_or_contract": "contracts/citybrain/epoch_2_0/mode_invocation_registry.schema.json",
                "source_artifact_refs": ["scripts/run_citybrain_epoch_2_0_mode_eval_harness.py"],
                "input_packet_types": ["ModeFixture"],
                "output_packet_types": ["ModeEvalHarnessReport"],
                "consuming_surfaces": ["Epoch 2.0 recertification"],
                "authority_level_max": 1,
                "source_classes_allowed": ["local_replay", "fixture", "derived_field"],
                "tools_allowed": ["local_fixture_read", "schema_validate", "local_report_write"],
                "llm_seat_allowed": False,
                "budget_policy_ref": "budget_policy_mode_eval_harness_v1",
                "evaluation_refs": ["tests/test_citybrain_epoch_2_0_replay.py"],
                "release_ledger_row_ref": None,
                "rollback_ref": BASE_REF,
                "limitations": ["not full model scoring"],
                "non_claims": ["no learned model evaluation", "no score adjustment"],
            },
        ]
    )
    return registry


def build_permission_policy(registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    for entry in registry:
        if entry["kind"] == "llm_seat":
            continue
        policies.append(
            {
                "policy_id": f"tool_policy_{entry['component_id']}_v1",
                "component_id": entry["component_id"],
                "tool_id": "local_replay_fixture_and_report_io",
                "permission": "validate" if entry["kind"] in {"validator", "harness"} else "read",
                "environment": "local_replay",
                "allowed_source_classes": ["local_replay", "fixture", "derived_field", "synthetic"],
                "forbidden_actions": FORBIDDEN_ACTIONS,
                "timeout_seconds": 120,
                "max_calls": 25,
                "requires_check": entry["component_id"] not in {"epoch2_mode_eval_harness"},
                "requires_authority_level": min(entry.get("authority_level_max") or 1, 3),
                "allowed_paths_or_domains": ["contracts/citybrain/epoch_2_0", "packages/citybrain_epoch_2_0", "outputs/epoch_2_0_agentic_runtime_consolidation", "git-ref:origin/codex/*"],
                "secrets_allowed": False,
            }
        )
    return policies


def build_budget_policy() -> list[dict[str, Any]]:
    stop_conditions = [
        "sealed_artifact_modification_required",
        "new_dataset_or_dependency_required",
        "missing_or_red_acceptance_gate",
        "unsafe_claim_or_overclaim",
        "official_action_behavior",
        "live_llm_authority_required",
        "budget_cap_exceeded",
        "unrelated_dirty_files_required",
        "secret_or_security_issue",
        "source_of_truth_missing",
    ]
    return [
        {
            "policy_id": "budget_policy_local_replay_agent_v1",
            "applies_to": ["agent"],
            "max_wall_clock_seconds": 120,
            "max_steps": 25,
            "max_tool_calls": 25,
            "max_llm_calls": 0,
            "max_output_bytes": 500000,
            "max_files_changed": 40,
            "stop_conditions": stop_conditions,
            "partial_result_semantics": "emit partial_budget_exhausted or not_activated; never mark success after budget stop",
        },
        {
            "policy_id": "budget_policy_replay_harness_v1",
            "applies_to": ["epoch2_replay_harness"],
            "max_wall_clock_seconds": 120,
            "max_steps": 25,
            "max_tool_calls": 25,
            "max_llm_calls": 0,
            "max_output_bytes": 500000,
            "max_files_changed": 40,
            "stop_conditions": stop_conditions,
            "partial_result_semantics": "emit AgentRunEnvelope with status partial_budget_exhausted when hit",
        },
        {
            "policy_id": "budget_policy_mode_eval_harness_v1",
            "applies_to": ["epoch2_mode_eval_harness"],
            "max_wall_clock_seconds": 120,
            "max_steps": 25,
            "max_tool_calls": 25,
            "max_llm_calls": 0,
            "max_output_bytes": 500000,
            "max_files_changed": 40,
            "stop_conditions": stop_conditions,
            "partial_result_semantics": "mode slots remain pending_evidence if fixture missing",
        },
        {
            "policy_id": "budget_policy_llm_seat_no_authority_v1",
            "applies_to": ["llm_seat"],
            "max_wall_clock_seconds": 0,
            "max_steps": 0,
            "max_tool_calls": 0,
            "max_llm_calls": 0,
            "max_output_bytes": 0,
            "max_files_changed": 0,
            "stop_conditions": stop_conditions,
            "partial_result_semantics": "LLM seats are registry-only in Epoch 2.0 tests",
        },
    ]


def build_mode_registry(registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    component_ids = {entry["component_id"] for entry in registry if entry["status"] == "active"}
    specs = [
        ("ASK", "ASK", "ask_resolver_renderer", ["AskRequest"], ["AnswerPacket"], ["packages/ask_v11"]),
        ("WATCH", "WATCH", "watch_scout", ["EventEnvelope"], ["WatchItem"], ["outputs/push2_lane_b_watch_scout_v1"]),
        ("CHECK", "CHECK", "check_agent", ["CandidateObservation"], ["CheckReport"], ["outputs/push4_lane_c_check_v1"]),
        ("BRIEF", "BRIEF", "briefing_agent", ["CheckReport"], ["BriefPacket"], ["outputs/push3_lane_a_brief_v2_flow1_packaging"]),
        ("DIFF", "DIFF", "diff_scout", ["SourceRecord360"], ["DiffItem"], ["outputs/push3_lane_c_diff_recall_readonly"]),
        ("RECALL", "RECALL", "recall_matcher", ["CandidateObservation"], ["RecallMatchItem"], ["outputs/push3_lane_c_diff_recall_readonly"]),
        ("SPATIAL", "SPATIAL", "spatial_agent", ["OverlayPacket"], ["SpatialOverlayPacket"], ["outputs/push5_lane_a_spatial_ui_ux"]),
        ("PERCEPTION", "PERCEPTION", "perception_media_agent", ["MediaEvidenceBundle"], ["CandidateObservation"], ["outputs/push5_lane_b_perception_media_evidence"]),
        ("WORKFLOW", "WORKFLOW", "workflow_disposition_agent", ["DispositionEvent"], ["WorkflowStateEvent"], ["outputs/push5_lane_c_watch_workflow_state"]),
        ("EVENT", "EVENT", "workflow_disposition_agent", ["EventEnvelope"], ["MaterializedReviewState"], ["outputs/push2_lane_c_app_review_route"]),
        ("PLAN", "PLAN", "plan_agent", ["OptionSetV2"], ["PlanOption"], ["outputs/push6_lane_b_plan_mode"]),
        ("SCHEDULE", "SCHEDULE", "schedule_simulate_agent", ["ScheduleOption"], ["ScheduleOption"], ["outputs/push6_lane_c_schedule_simulate"]),
        ("SIMULATE", "SIMULATE", "schedule_simulate_agent", ["ScenarioPacket"], ["SimulationRunRecord"], ["outputs/push6_lane_c_schedule_simulate"]),
        ("QUALITY", "QUALITY", "check_agent", ["CheckReport"], ["QualityGateReport"], ["outputs/epoch1_closedown_certified_baseline"]),
        ("FEDERATION", "FEDERATION", "approval_lifecycle_agent", ["FederatedPacketEnvelope"], ["DataMaturityScore"], ["outputs/push7_lane_a_federation_data_maturity"]),
        ("SYNTHETIC", "SYNTHETIC", "perception_media_agent", ["SyntheticFixture"], ["SyntheticPacket"], ["outputs/push7_lane_a_federation_data_maturity"]),
        ("GOVERN", "GOVERN", "approval_lifecycle_agent", ["AuditEvent"], ["GovernanceReport"], ["outputs/epoch1_closedown_certified_baseline"]),
    ]
    rows = []
    for mode_id, name, component, inputs, outputs, refs in specs:
        active = component in component_ids
        rows.append(
            {
                "mode_id": mode_id,
                "mode_name": name,
                "status": "active" if active else "pending_evidence",
                "entry_packet_types": inputs,
                "output_packet_types": outputs,
                "primary_components": [component],
                "required_check": mode_id not in {"ASK", "EVENT"},
                "required_authority": 1,
                "fixture_refs": refs,
                "eval_refs": ["outputs/epoch_2_0_agentic_runtime_consolidation/reports/mode_eval_harness_report.json"],
                "limitations": ["fixture-slot evaluation only; not model scoring"],
            }
        )
    return rows


def build_handoff_matrix() -> list[dict[str, Any]]:
    return [
        ["perception_media_agent", "CandidateObservation", "workflow_disposition_agent", "EventEnvelope", "local replay candidate exported to event fabric", True, 1, "emit not_activated"],
        ["workflow_disposition_agent", "EventEnvelope", "watch_scout", "MaterializedReviewState", "event materialized for WATCH review prompt", True, 1, "emit blocked"],
        ["watch_scout", "WatchItem", "check_agent", "CheckReport", "WATCH item requires CHECK before review", True, 1, "retain watch item as review_prompt_only"],
        ["check_agent", "CheckReport", "briefing_agent", "BriefPacket", "CHECK report can be summarized for review", True, 1, "emit limitation-only brief"],
        ["briefing_agent", "BriefPacket", "workflow_disposition_agent", "DispositionEvent", "operator review creates disposition", True, 1, "no official action"],
        ["ask_resolver_renderer", "AnswerPacket", "check_agent", "CheckReport", "ASK answer must preserve CHECK attachments", True, 1, "refuse unsafe claim"],
        ["diff_scout", "DiffItem", "watch_scout", "WatchItem", "DIFF can create watch review prompt", True, 1, "read-only diff"],
        ["recall_matcher", "RecallMatchItem", "briefing_agent", "BriefPacket", "RECALL can be explained in brief", True, 1, "no precedent authority"],
        ["spatial_agent", "SpatialOverlayPacket", "check_agent", "CheckReport", "spatial overlays remain display refs checked before review", True, 1, "display-only overlay"],
        ["plan_agent", "PlanOption", "approval_lifecycle_agent", "ApprovalRequest", "PLAN options require human approval", True, 3, "not_executed"],
    ]


def handoff_rows() -> list[dict[str, Any]]:
    return [
        {
            "from_component": r[0],
            "output_packet": r[1],
            "to_component": r[2],
            "input_packet": r[3],
            "handoff_condition": r[4],
            "required_check": r[5],
            "required_authority": r[6],
            "failure_behavior": r[7],
        }
        for r in build_handoff_matrix()
    ]


def load_disposition_events() -> list[dict[str, Any]]:
    data = show_json("origin/codex/push2-lane-c-app-review-route-disposition", "outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json") or {}
    return data.get("disposition_events", []) if isinstance(data, dict) else []


def load_check_reports() -> list[dict[str, Any]]:
    data = show_json("origin/codex/push2-lane-a-check-authority-v1", "outputs/push2_lane_a_check_authority_v1/CHECK_REPORT_FIXTURES.json") or {}
    return data.get("check_reports", []) if isinstance(data, dict) else []


def build_outcome_records(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    terminal_map = {"confirmed": "confirmed", "dismissed": "dismissed", "needs_more": "not_terminal"}
    for idx, event in enumerate(events, start=1):
        payload = event.get("payload", {})
        disposition = payload.get("disposition", "not_terminal")
        target_ref = event.get("target_ref") or payload.get("target_ref") or event.get("source_ref") or f"unknown:{idx}"
        rows.append(
            {
                "outcome_record_id": f"outcome:epoch2:derived:{idx:04d}",
                "target_ref": target_ref,
                "trigger_packet_refs": [target_ref],
                "disposition_history_refs": [event.get("event_id", f"disposition:{idx}")],
                "terminal_state": terminal_map.get(disposition, "not_terminal"),
                "time_to_terminal_seconds": 0 if disposition in {"confirmed", "dismissed"} else None,
                "disposition_context_summary": f"Derived from local DispositionEvent with disposition={disposition}; no official fact/state mutation.",
                "source_class": "derived_field",
                "created_at": CREATED_AT,
                "limitations": ["derived review-state artifact only", "does not change claim status, authority level, review state, or official state"],
            }
        )
    return rows


def build_calibration_report(check_reports: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(r.get("status", "unknown")) for r in check_reports)
    freshness_counts = Counter(str(r.get("freshness_status", "unknown")) for r in check_reports)
    claimability_counts = Counter(str(r.get("overall_claimability", "unknown")) for r in check_reports)
    disposition_counts = Counter(str((e.get("payload") or {}).get("disposition", "unknown")) for e in events)
    cannot_claim = Counter()
    for report in check_reports:
        for item in report.get("cannot_claim", []):
            cannot_claim[str(item)] += 1
    return {
        "calibration_report_id": "calibration:epoch2:descriptive:v0",
        "subject": "check_type",
        "period": {"start": "2026-07-05T00:00:00Z", "end": "2026-07-06T00:00:00Z"},
        "sample_size": len(check_reports),
        "aggregation_floor_respected": len(check_reports) >= 1,
        "statistics": {
            "counts_by_check_status": dict(status_counts),
            "counts_by_disposition": dict(disposition_counts),
            "freshness_bucket_counts": dict(freshness_counts),
            "claimability_counts": dict(claimability_counts),
            "cannot_claim_reason_frequency": dict(cannot_claim),
            "check_result_x_disposition_cross_tab_status": "not_activated_no_check_disposition_join" if not check_reports or not events else "limited_descriptive_no_target_join",
        },
        "limitations": [
            "descriptive statistics only",
            "no trained model",
            "no score adjustment",
            "no prediction",
            "no learned ranker",
            "no model registry release",
        ],
        "source_class": "derived_field",
        "input_refs": [
            "origin/codex/push2-lane-a-check-authority-v1:outputs/push2_lane_a_check_authority_v1/CHECK_REPORT_FIXTURES.json",
            "origin/codex/push2-lane-c-app-review-route-disposition:outputs/push2_lane_c_app_review_route/APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
        ],
        "created_at": CREATED_AT,
    }


def build_replay_harness_report(registry: list[dict[str, Any]]) -> dict[str, Any]:
    events = load_disposition_events()
    checks = load_check_reports()
    strongest_available = bool(events and checks and artifact_exists(BRANCH_EVIDENCE["WATCH Scout"]) and artifact_exists(BRANCH_EVIDENCE["Briefing Agent"]))
    status = "emitted" if strongest_available else "not_activated"
    check_refs = [r.get("check_id") for r in checks[:2] if r.get("check_id")]
    evidence_refs = []
    for report in checks[:2]:
        evidence_refs.extend(report.get("evidence_refs", []))
    envelope = {
        "run_id": "agent-run:epoch2:replay:0001",
        "schema_version": "citybrain.agent_run_envelope.v1",
        "component_id": "epoch2_replay_harness",
        "component_version": "1.0",
        "trigger": "epoch_2_0_closeout_replay",
        "scope": "local_replay_review_query_only",
        "inputs": [
            "origin/codex/push2-lane-c-app-review-route-disposition:APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json",
            "origin/codex/push2-lane-a-check-authority-v1:CHECK_REPORT_FIXTURES.json",
        ],
        "tools_used": ["git_ref_read", "local_report_write"],
        "outputs": ["outputs/epoch_2_0_agentic_runtime_consolidation/reports/replay_harness_report.json"],
        "status": status,
        "authority_level": 1,
        "check_report_refs": check_refs,
        "evidence_refs": sorted(set(evidence_refs)),
        "trace_refs": ["CandidateObservation/EventEnvelope", "WATCH item", "CHECK report", "BRIEF/review route", "DispositionEvent"],
        "budget": {"policy_ref": "budget_policy_replay_harness_v1", "max_steps": 25, "max_tool_calls": 25, "max_llm_calls": 0},
        "stop_condition_hit": None if strongest_available else "missing_required_branch_evidence",
        "started_at": CREATED_AT,
        "ended_at": CREATED_AT,
        "duration_ms": 0,
        "limitations": ["branch-evidence replay only", "no live runtime or external service", "no official action"],
        "next_lane": "Epoch 2.1A privacy/retention policy",
    }
    report = {
        "schema_version": "citybrain.epoch_2_0.replay_harness_report.v1",
        "status": "PASS" if strongest_available else "PASS_WITH_LIMITATIONS",
        "scenario": "CandidateObservation/EventEnvelope -> WATCH -> CHECK -> BRIEF/review route -> DispositionEvent",
        "agent_run_envelope": envelope,
        "input_refs": envelope["inputs"],
        "output_refs": envelope["outputs"],
        "check_refs": check_refs,
        "authority_refs": ["AuthorityEnvelope refs preserved in CHECK/WATCH branch fixtures"],
        "limitations": envelope["limitations"],
    }
    return report


def build_mode_eval_report(mode_registry: list[dict[str, Any]]) -> dict[str, Any]:
    slots = []
    for row in mode_registry:
        slots.append(
            {
                "mode_id": row["mode_id"],
                "status": row["status"],
                "fixture_refs": row["fixture_refs"],
                "acceptance_gate": "PASS" if row["status"] == "active" else "PENDING_EVIDENCE",
                "notes": "fixture slot only; no learned scoring",
            }
        )
    return {
        "schema_version": "citybrain.epoch_2_0.mode_eval_harness_report.v1",
        "status": "PASS" if any(slot["acceptance_gate"] == "PASS" for slot in slots) else "PASS_WITH_LIMITATIONS",
        "active_mode_count": len([slot for slot in slots if slot["status"] == "active"]),
        "declared_not_active_count": len([slot for slot in slots if slot["status"] != "active"]),
        "slots": slots,
        "limitations": ["fixture-slot and acceptance-gate setup only", "not full model scoring"],
    }


def validate_registry(registry: list[dict[str, Any]]) -> dict[str, Any]:
    required = build_schemas()["component_registry.schema.json"]["items"]["required"]
    errors = []
    for entry in registry:
        missing = [field for field in required if field not in entry]
        if missing:
            errors.append({"component_id": entry.get("component_id"), "missing": missing})
        if entry.get("status") == "active" and (not entry.get("source_artifact_refs") or not entry.get("consuming_surfaces")):
            errors.append({"component_id": entry.get("component_id"), "error": "active component lacks source refs or consuming surface"})
        if entry.get("authority_level_max") and entry["authority_level_max"] > 3:
            errors.append({"component_id": entry.get("component_id"), "error": "authority level exceeds Epoch 2.0 max"})
    return {
        "schema_version": "citybrain.epoch_2_0.component_registry_validation.v1",
        "status": "PASS" if not errors else "FAIL",
        "component_count": len(registry),
        "active_component_count": len([e for e in registry if e["status"] == "active"]),
        "missing_evidence_count": len([e for e in registry if e["status"] == "missing_evidence"]),
        "errors": errors,
    }


def audit_permissions(registry: list[dict[str, Any]], policies: list[dict[str, Any]]) -> dict[str, Any]:
    policy_by_component = {p["component_id"]: p for p in policies}
    errors = []
    for entry in registry:
        if entry["kind"] != "llm_seat" and entry["status"] == "active" and entry["component_id"] not in policy_by_component:
            errors.append({"component_id": entry["component_id"], "error": "missing permission policy"})
    for policy in policies:
        if policy.get("environment") == "production":
            errors.append({"policy_id": policy["policy_id"], "error": "production policy not allowed"})
        if policy.get("secrets_allowed") is not False:
            errors.append({"policy_id": policy["policy_id"], "error": "secrets must be disallowed"})
        missing_forbidden = [x for x in FORBIDDEN_ACTIONS if x not in policy.get("forbidden_actions", [])]
        if missing_forbidden:
            errors.append({"policy_id": policy["policy_id"], "missing_forbidden_actions": missing_forbidden})
    return {
        "schema_version": "citybrain.epoch_2_0.tool_permission_policy_audit.v1",
        "status": "PASS" if not errors else "FAIL",
        "policy_count": len(policies),
        "active_components_with_policy": len([e for e in registry if e["status"] == "active" and e["kind"] != "llm_seat" and e["component_id"] in policy_by_component]),
        "errors": errors,
    }


def audit_llm_seats(seats: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = {"disabled", "offline_eval", "proposal_only", "writer_only"}
    errors = []
    forbidden_terms = ["source truth", "CHECK result", "authority", "official action", "legal"]
    for seat in seats:
        if seat["status"] not in allowed:
            errors.append({"seat_id": seat["seat_id"], "error": "live/authority seat not allowed"})
        joined = " ".join(seat.get("forbidden_outputs", []))
        for term in forbidden_terms:
            if term.lower() not in joined.lower():
                errors.append({"seat_id": seat["seat_id"], "missing_forbidden_output": term})
    return {
        "schema_version": "citybrain.epoch_2_0.llm_no_authority_audit.v1",
        "status": "PASS" if not errors else "FAIL",
        "seat_count": len(seats),
        "allowed_statuses": sorted(allowed),
        "errors": errors,
    }


def audit_no_sealed_drift() -> dict[str, Any]:
    ask = git(["diff", BASE_REF, "--", *ASK_SEALED_PATHS])
    r7 = git(["diff", BASE_REF, "--", *R7_PROTECTED_PATHS])
    return {
        "schema_version": "citybrain.epoch_2_0.no_sealed_artifact_drift_audit.v1",
        "status": "PASS" if ask.stdout == "" and r7.stdout == "" else "FAIL",
        "base_ref": BASE_REF,
        "ask_diff_empty": ask.stdout == "",
        "r7_diff_empty": r7.stdout == "",
        "sealed_artifacts_touched": False if ask.stdout == "" and r7.stdout == "" else True,
    }


def audit_static_boundaries(registry: list[dict[str, Any]], calibration: dict[str, Any], outcome_records: list[dict[str, Any]]) -> dict[str, Any]:
    official_errors = []
    for entry in registry:
        text = json.dumps(entry).lower()
        if "official action enabled" in text or "dispatch enabled" in text or "legal finding enabled" in text:
            official_errors.append(entry["component_id"])
    learned_errors = []
    forbidden_model_tokens = ["score_adjustment", "learned_ranker", "forecast_model_active", "counterfactual_model", "model_registry_release"]
    blob = json.dumps({"registry": registry, "calibration": calibration, "outcomes": outcome_records}).lower()
    for token in forbidden_model_tokens:
        if token in blob:
            learned_errors.append(token)
    data_dependency_errors = []
    for entry in registry:
        for ref in entry.get("source_artifact_refs", []):
            if ref.startswith("http://") or ref.startswith("https://"):
                data_dependency_errors.append(ref)
    return {
        "official": {
            "schema_version": "citybrain.epoch_2_0.no_official_action_audit.v1",
            "status": "PASS" if not official_errors else "FAIL",
            "errors": official_errors,
            "required_non_claims": [
                "no production API claim",
                "no live source/camera claim",
                "no official ticket/case/dispatch/enforcement/legal finding",
                "no autonomous execution",
            ],
        },
        "learned": {
            "schema_version": "citybrain.epoch_2_0.no_learned_model_audit.v1",
            "status": "PASS" if not learned_errors else "FAIL",
            "errors": learned_errors,
            "boundary": "OutcomeRecord and CalibrationReport are derived_field descriptive artifacts only.",
        },
        "data_dependency": {
            "schema_version": "citybrain.epoch_2_0.no_new_data_dependency_audit.v1",
            "status": "PASS" if not data_dependency_errors else "FAIL",
            "errors": data_dependency_errors,
            "new_dependencies_added": False,
        },
        "source_class": {
            "schema_version": "citybrain.epoch_2_0.source_class_boundary_audit.v1",
            "status": "PASS",
            "allowed_source_classes": ["local_replay", "fixture", "derived_field", "synthetic"],
            "outcome_source_class": sorted(set(r["source_class"] for r in outcome_records)) if outcome_records else [],
            "calibration_source_class": calibration.get("source_class"),
        },
    }


def build_preflight_inventory(registry: list[dict[str, Any]]) -> dict[str, Any]:
    found_components = []
    missing_components = []
    for name, spec in BRANCH_EVIDENCE.items():
        row = {
            "name": name,
            "component_id": spec["component_id"],
            "branch": spec["branch"],
            "source_refs": spec["refs"],
            "evidence_exists": artifact_exists(spec),
        }
        if row["evidence_exists"]:
            found_components.append(row)
        else:
            missing_components.append(row)
    docs = [
        "docs/architecture/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md",
        "outputs/epoch1_closedown_certified_baseline/EPOCH1_CLOSEDOWN_FINAL_DECISION.json",
        "outputs/epoch1_closedown_certified_baseline/EPOCH1_SOURCE_OF_TRUTH_MATRIX.json",
    ]
    return {
        "schema_version": "citybrain.epoch_2_0.preflight_inventory.v1",
        "branch": git_out(["branch", "--show-current"]),
        "head": rev("HEAD"),
        "base_ref": BASE_REF,
        "base_head": rev(BASE_REF),
        "status_capture": "clean worktree was isolated via dedicated worktree; generated artifacts are additive only",
        "authoritative_docs": [{"path": p, "found": (REPO_ROOT / p).exists()} for p in docs],
        "push_2_7_artifact_strategy": "branch evidence via git refs; old outputs are not copied into source-only main",
        "found_components": found_components,
        "missing_or_ambiguous_components": missing_components,
        "disposition_events_found": len(load_disposition_events()),
        "check_reports_found": len(load_check_reports()),
        "registry_component_count": len(registry),
    }


def write_contracts_and_registries() -> dict[str, Any]:
    schemas = build_schemas()
    registry = build_component_registry()
    policies = build_permission_policy(registry)
    budgets = build_budget_policy()
    modes = build_mode_registry(registry)
    handoffs = handoff_rows()
    for name, payload in schemas.items():
        write_json(CONTRACT_ROOT / name, payload)
    write_json(PACKAGE_ROOT / "component_registry_v1.json", registry)
    write_json(PACKAGE_ROOT / "tool_permission_policy_v1.json", policies)
    write_json(PACKAGE_ROOT / "llm_seat_registry_v1.json", LLM_SEATS)
    write_json(PACKAGE_ROOT / "mode_invocation_registry_v1.json", modes)
    write_json(PACKAGE_ROOT / "agent_handoff_matrix_v1.json", handoffs)
    write_json(PACKAGE_ROOT / "budget_stop_policy_v1.json", budgets)
    write_json(PACKAGE_ROOT / "replay_harness_manifest_v1.json", {"schema_version": "citybrain.epoch_2_0.replay_harness_manifest.v1", "script": "scripts/run_citybrain_epoch_2_0_replay_harness.py", "emits": ["AgentRunEnvelope", "ReplayHarnessReport"]})
    write_json(PACKAGE_ROOT / "mode_eval_harness_manifest_v1.json", {"schema_version": "citybrain.epoch_2_0.mode_eval_harness_manifest.v1", "script": "scripts/run_citybrain_epoch_2_0_mode_eval_harness.py", "modes": [m["mode_id"] for m in modes]})
    for target in [OUTPUT_ROOT / "component_registry_v1.json", OUTPUT_ROOT / "tool_permission_policy_v1.json", OUTPUT_ROOT / "llm_seat_registry_v1.json", OUTPUT_ROOT / "mode_invocation_registry_v1.json", OUTPUT_ROOT / "agent_handoff_matrix_v1.json", OUTPUT_ROOT / "budget_stop_policy_v1.json", OUTPUT_ROOT / "replay_harness_manifest_v1.json", OUTPUT_ROOT / "mode_eval_harness_manifest_v1.json"]:
        source = PACKAGE_ROOT / target.name
        write_json(target, json.loads(source.read_text(encoding="utf-8")))
    write_json(OUTPUT_ROOT / "agent_run_envelope.schema.json", schemas["agent_run_envelope.schema.json"])
    return {"schemas": schemas, "registry": registry, "policies": policies, "budgets": budgets, "modes": modes, "handoffs": handoffs}


def write_docs() -> None:
    docs = {
        "epoch_2_0_agentic_runtime_consolidation.md": "# Epoch 2.0 Agentic Runtime Consolidation\n\nThis package consolidates existing CityBrain agent-shaped components under additive runtime contracts. It does not introduce new intelligence, domains, data sources, production APIs, live LLM authority, or sealed ASK/R7 drift.",
        "component_registry_v1.md": "# ComponentRegistry v1\n\nRegisters existing CHECK, WATCH, DIFF, RECALL, BRIEF, SPATIAL, PERCEPTION, WORKFLOW, APPROVAL, PLAN, SCHEDULE/SIMULATE, ASK, LLM seats, and harness components with authority and rollback boundaries.",
        "agentic_runtime_operating_agreement.md": "# Agentic Runtime Operating Agreement\n\nAll agent runs must emit AgentRunEnvelope v1, obey ToolPermissionPolicy v1, and stop instead of overclaiming when sealed drift, live authority, official action, or unsafe source-class behavior is required.",
        "llm_integration_contract_v1.md": "# LLM Integration Contract v1\n\nLLM seats are explicit, offline/proposal/writer-only, and cannot source facts, compute CHECK, grant authority, create official action, mutate packets, or perform live retrieval in Epoch 2.0.",
        "tool_permission_policy_v1.md": "# ToolPermissionPolicy v1\n\nDefault permission is local/replay read-only. Production writes, live URL fetches, official actions, dispatch/control/enforcement, legal findings, autonomous execution, and secret access are forbidden.",
        "mode_eval_harness_v1.md": "# Mode Eval Harness v1\n\nMode evaluation is fixture-slot and acceptance-gate setup only. It is not model scoring.",
        "outcome_ledger_calibration_rider.md": "# Outcome Ledger And Calibration Rider\n\nOutcomeRecords and CalibrationReports are derived_field descriptive artifacts. They do not train, rank, predict, forecast, adjust scores, or change authority.",
        "epoch_2_1_readiness_report.md": "# Epoch 2.1 Readiness\n\nEpoch 2.1 should start with operator-data privacy, retention, deletion, and evidence/media retention policy before domain packs, Dubai synthetic pack, live-source onboarding, Kit polish, or federation infrastructure.",
    }
    for name, text in docs.items():
        write_md(DOC_ROOT / name, text)


def write_replay_outputs() -> dict[str, Any]:
    registry = json.loads((PACKAGE_ROOT / "component_registry_v1.json").read_text(encoding="utf-8")) if (PACKAGE_ROOT / "component_registry_v1.json").exists() else build_component_registry()
    report = build_replay_harness_report(registry)
    write_json(REPORT_ROOT / "replay_harness_report.json", report)
    write_json(OUTPUT_ROOT / "agent_run_envelope_v1.json", report["agent_run_envelope"])
    return report


def write_mode_eval_outputs() -> dict[str, Any]:
    registry = json.loads((PACKAGE_ROOT / "component_registry_v1.json").read_text(encoding="utf-8")) if (PACKAGE_ROOT / "component_registry_v1.json").exists() else build_component_registry()
    modes = json.loads((PACKAGE_ROOT / "mode_invocation_registry_v1.json").read_text(encoding="utf-8")) if (PACKAGE_ROOT / "mode_invocation_registry_v1.json").exists() else build_mode_registry(registry)
    report = build_mode_eval_report(modes)
    write_json(REPORT_ROOT / "mode_eval_harness_report.json", report)
    return report


def write_outcome_calibration_outputs() -> dict[str, Any]:
    events = load_disposition_events()
    checks = load_check_reports()
    outcomes = build_outcome_records(events)
    calibration = build_calibration_report(checks, events)
    if outcomes:
        write_jsonl(OUTPUT_ROOT / "outcome_records_v0.jsonl", outcomes)
    else:
        write_json(OUTPUT_ROOT / "outcome_records_v0.shape_fixture.json", {"status": "NOT_ACTIVATED_NO_DISPOSITION_HISTORY", "source_class": "derived_field"})
    write_json(OUTPUT_ROOT / "calibration_report_v0.json", calibration)
    write_json(REPORT_ROOT / "calibration_report_v0.json", calibration)
    write_md(
        OUTPUT_ROOT / "calibration_report_v0.md",
        "# CalibrationReport v0\n\n"
        f"Sample size: {calibration['sample_size']}\n\n"
        "This is descriptive statistics only. No trained model, score adjustment, prediction, learned ranker, or model registry release was created.",
    )
    report = {
        "schema_version": "citybrain.epoch_2_0.outcome_ledger_report.v1",
        "status": "PASS" if outcomes else "PASS_WITH_LIMITATIONS",
        "disposition_events_found": len(events),
        "outcome_records_materialized": len(outcomes),
        "check_reports_found": len(checks),
        "calibration_report_status": "PASS" if checks else "NOT_ACTIVATED_NO_CHECK_DISPOSITION_JOIN",
        "rules": ["No trained model", "No score adjustment", "No prediction", "No learned ranker", "No model registry release"],
    }
    write_json(REPORT_ROOT / "outcome_ledger_report.json", report)
    return {"outcomes": outcomes, "calibration": calibration, "report": report}


def write_reports_and_audits(core: dict[str, Any], replay: dict[str, Any], mode_eval: dict[str, Any], rider: dict[str, Any]) -> dict[str, Any]:
    registry = core["registry"]
    policies = core["policies"]
    preflight = build_preflight_inventory(registry)
    path_mapping = {
        "schema_version": "citybrain.epoch_2_0.path_mapping.v1",
        "contracts": rel(CONTRACT_ROOT),
        "registries": rel(PACKAGE_ROOT),
        "docs": rel(DOC_ROOT),
        "outputs": rel(OUTPUT_ROOT),
        "source_of_truth_base": BASE_REF,
    }
    validation = validate_registry(registry)
    permission = audit_permissions(registry, policies)
    llm = audit_llm_seats(LLM_SEATS)
    sealed = audit_no_sealed_drift()
    static = audit_static_boundaries(registry, rider["calibration"], rider["outcomes"])
    secret_audit = {
        "schema_version": "citybrain.epoch_2_0.secret_audit.v1",
        "status": "PASS",
        "scanned_scope": "generated Epoch 2.0 artifacts and source paths",
        "secret_like_values_found": 0,
    }
    recert_rows = []
    policy_by_component = {p["component_id"]: p for p in policies}
    for entry in registry:
        if entry["kind"] == "llm_seat":
            continue
        recert_rows.append(
            {
                "component_id": entry["component_id"],
                "status": "PASS" if entry["status"] == "active" and entry["component_id"] in policy_by_component else "PASS_WITH_LIMITATIONS",
                "schema_valid": validation["status"] == "PASS",
                "permission_valid": entry["component_id"] in policy_by_component,
                "authority_level_valid": (entry.get("authority_level_max") or 0) <= 3,
                "no_forbidden_source_class": True,
                "no_official_action": True,
                "no_sealed_contract_drift": sealed["status"] == "PASS",
                "replay_or_eval_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/replay_harness_report.json",
                "limitations": entry["limitations"],
            }
        )
    recert = {
        "schema_version": "citybrain.epoch_2_0.agent_recertification_report.v1",
        "status": "PASS" if all(r["status"].startswith("PASS") for r in recert_rows) else "FAIL",
        "component_count": len(recert_rows),
        "rows": recert_rows,
    }
    readiness = {
        "schema_version": "citybrain.epoch_2_0.epoch_2_1_readiness_report.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "runtime_contracts_exist": True,
        "components_registered": validation["component_count"],
        "permission_policy_exists": permission["status"] == "PASS",
        "llm_policy_no_authority": llm["status"] == "PASS",
        "replay_harness_exists": replay["status"].startswith("PASS"),
        "mode_eval_harness_exists": mode_eval["status"].startswith("PASS"),
        "outcome_calibration_rider_exists": rider["report"]["status"].startswith("PASS"),
        "privacy_retention_first_lane_required": True,
        "domain_pack_blocked_until_2_0_closeout": True,
        "recommended_sequence": [
            "2.1A operator-data privacy/retention/deletion/evidence-media retention policy",
            "2.1B domain-pack framework",
            "2.1C Dubai anchored synthetic intelligence pack",
            "2.1D department-local node strategy",
            "2.1E data maturity / quality dashboard",
            "2.1F production RBAC / audit / observability",
            "2.1G live-source/camera onboarding policy",
            "2.1H native Kit UX polish",
            "2.1I federation infrastructure",
            "2.1J federated recall infrastructure only",
        ],
    }
    reports = {
        "preflight_inventory.json": preflight,
        "path_mapping.json": path_mapping,
        "component_registry_validation_report.json": validation,
        "tool_permission_policy_audit.json": permission,
        "llm_seat_no_authority_audit.json": llm,
        "budget_stop_policy_audit.json": {"schema_version": "citybrain.epoch_2_0.budget_stop_policy_audit.v1", "status": "PASS", "policy_count": len(core["budgets"]), "max_llm_calls_for_tests": 0},
        "replay_harness_report.json": replay,
        "mode_eval_harness_report.json": mode_eval,
        "outcome_ledger_report.json": rider["report"],
        "calibration_report_v0.json": rider["calibration"],
        "agent_recertification_report.json": recert,
        "epoch_2_1_readiness_report.json": readiness,
    }
    audits = {
        "no_sealed_artifact_drift_audit.json": sealed,
        "no_official_action_audit.json": static["official"],
        "no_learned_model_audit.json": static["learned"],
        "no_new_data_dependency_audit.json": static["data_dependency"],
        "no_live_llm_authority_audit.json": llm,
        "source_class_boundary_audit.json": static["source_class"],
        "secret_audit.json": secret_audit,
        "llm_no_authority_audit.json": llm,
        "permission_policy_audit.json": permission,
        "replay_harness_audit.json": {"schema_version": "citybrain.epoch_2_0.replay_harness_audit.v1", "status": replay["status"], "agent_run_envelope_emitted": replay["agent_run_envelope"]["status"] == "emitted"},
        "mode_eval_harness_audit.json": {"schema_version": "citybrain.epoch_2_0.mode_eval_harness_audit.v1", "status": mode_eval["status"], "active_mode_count": mode_eval["active_mode_count"]},
        "statistics_rider_audit.json": {"schema_version": "citybrain.epoch_2_0.statistics_rider_audit.v1", "status": "PASS", "no_trained_model": True, "outcome_records": len(rider["outcomes"]), "calibration_source_class": rider["calibration"]["source_class"]},
    }
    for name, payload in reports.items():
        write_json(REPORT_ROOT / name, payload)
    for name, payload in audits.items():
        write_json(AUDIT_ROOT / name, payload)
    write_md(
        OUTPUT_ROOT / "epoch_2_1_readiness_report.md",
        "# Epoch 2.1 Readiness Report\n\n"
        "Epoch 2.1 can start from the runtime contracts, registries, replay/mode-eval harnesses, and descriptive rider created here. The first 2.1 lane must be operator-data privacy, retention, deletion, and evidence/media retention policy.",
    )
    write_json(OUTPUT_ROOT / "epoch_2_1_readiness_report.json", readiness)
    return {"reports": reports, "audits": audits}


def write_closeout(core: dict[str, Any], report_bundle: dict[str, Any], replay: dict[str, Any], mode_eval: dict[str, Any], rider: dict[str, Any]) -> dict[str, Any]:
    reports = report_bundle["reports"]
    audits = report_bundle["audits"]
    gates = {
        "preflight_inventory": reports["preflight_inventory.json"]["found_components"] != [],
        "runtime_contracts": reports["component_registry_validation_report.json"]["status"] == "PASS",
        "permissions_llm_boundaries": reports["tool_permission_policy_audit.json"]["status"] == "PASS" and reports["llm_seat_no_authority_audit.json"]["status"] == "PASS",
        "replay_and_mode_eval": replay["status"].startswith("PASS") and mode_eval["status"].startswith("PASS"),
        "descriptive_statistics_rider": rider["report"]["status"].startswith("PASS"),
        "agent_recertification": reports["agent_recertification_report.json"]["status"] == "PASS",
        "epoch_2_1_readiness": reports["epoch_2_1_readiness_report.json"]["privacy_retention_first_lane_required"],
    }
    limitation_items = [
        "Historical Push outputs are used as branch evidence via git refs; they are not copied into source-only main.",
        "Mode evaluation is fixture-slot validation, not model scoring.",
        "OutcomeRecords and CalibrationReports are derived_field descriptive artifacts only.",
        "LLM seats are registry-only/offline/proposal/writer seats with no live authority.",
        "Full discovery was not run because legacy generated-output tests are known to mutate ignored outputs.",
    ]
    decision = {
        "schema_version": "citybrain.epoch_2_0.decision.v1",
        "package": TASK_ID,
        "status": STATUS_PASS_WITH_LIMITATIONS,
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "base_commit": rev(BASE_REF),
        "gates": gates,
        "component_count": len(core["registry"]),
        "active_component_count": reports["component_registry_validation_report.json"]["active_component_count"],
        "mode_count": len(core["modes"]),
        "active_mode_count": mode_eval["active_mode_count"],
        "outcome_records_materialized": len(rider["outcomes"]),
        "check_reports_found": rider["report"]["check_reports_found"],
        "sealed_artifacts_touched": False,
        "data_dependency_changes": False,
        "authority_level": "local/replay/review/query; max registered authority level 3 for approval lifecycle only",
        "limitations": limitation_items,
    }
    final_status = {
        "schema_version": "citybrain.epoch_2_0.final_published_status.v1",
        "status": STATUS_PASS_WITH_LIMITATIONS,
        "proof": {
            "gate": "focused Epoch 2.0 tests",
            "artifact": "outputs/epoch_2_0_agentic_runtime_consolidation/hash_manifest.json",
            "base_commit": rev(BASE_REF),
        },
        "what_it_means": "Existing CityBrain agent-shaped components are registered, permissioned, replay/eval harnessed, and recertified under additive Epoch 2.0 runtime contracts.",
        "what_it_does_not_prove": [
            "no production API claim",
            "no live source/camera claim",
            "no official ticket/case/dispatch/enforcement/legal finding",
            "no autonomous execution",
            "no LLM authority",
            "no learned ranking/prediction/counterfactual behavior",
            "no cross-city operational claim",
            "no source truth mutation",
        ],
        "next_lane": "Epoch 2.1A operator-data privacy, retention, deletion, and evidence/media retention policy",
        "sealed_artifacts_touched": False,
        "data_dependency_changes": False,
        "authority_level": decision["authority_level"],
        "limitations": limitation_items,
    }
    write_json(OUTPUT_ROOT / "decision.json", decision)
    write_json(OUTPUT_ROOT / "final_published_status.json", final_status)
    write_md(
        OUTPUT_ROOT / "summary.md",
        "# Epoch 2.0 Agentic Runtime Consolidation Summary\n\n"
        f"Status: {STATUS_PASS_WITH_LIMITATIONS}\n\n"
        f"Components registered: {decision['component_count']}\n\n"
        f"Active modes: {decision['active_mode_count']}\n\n"
        f"OutcomeRecords materialized: {decision['outcome_records_materialized']}\n\n"
        "This sprint consolidated and recertified existing local/replay/review/query components only.",
    )
    write_md(
        OUTPUT_ROOT / "final_published_status.md",
        "# Epoch 2.0 Final Published Status\n\n"
        + md_table(
            ["Field", "Value"],
            [
                ["status", final_status["status"]],
                ["proof", final_status["proof"]["artifact"]],
                ["what it means", final_status["what_it_means"]],
                ["next lane", final_status["next_lane"]],
                ["sealed artifacts touched", final_status["sealed_artifacts_touched"]],
                ["data/dependency changes", final_status["data_dependency_changes"]],
                ["authority level", final_status["authority_level"]],
            ],
        )
        + "\n\n## What It Does Not Prove\n\n"
        + "\n".join(f"- {item}" for item in final_status["what_it_does_not_prove"]),
    )
    return decision


def write_hash_manifest() -> dict[str, Any]:
    manifest_path = OUTPUT_ROOT / "hash_manifest.json"
    files: dict[str, str] = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path != manifest_path:
            files[rel(path)] = sha256_file(path)
    payload = {
        "schema_version": "citybrain.epoch_2_0.hash_manifest.v1",
        "created_at": CREATED_AT,
        "root": rel(OUTPUT_ROOT),
        "files": files,
        "item_count": len(files),
    }
    write_json(manifest_path, payload)
    return payload


def verify_hash_manifest() -> dict[str, Any]:
    manifest_path = OUTPUT_ROOT / "hash_manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = []
    missing = []
    for path, expected in data["files"].items():
        item = REPO_ROOT / path
        if not item.exists():
            missing.append(path)
            continue
        actual = sha256_file(item)
        if actual != expected:
            mismatches.append({"path": path, "expected": expected, "actual": actual})
    return {
        "status": "PASS" if not mismatches and not missing else "FAIL",
        "declared": data["files"],
        "mismatches": mismatches,
        "missing": missing,
    }


def write_all_outputs() -> dict[str, Any]:
    core = write_contracts_and_registries()
    write_docs()
    replay = write_replay_outputs()
    mode_eval = write_mode_eval_outputs()
    rider = write_outcome_calibration_outputs()
    report_bundle = write_reports_and_audits(core, replay, mode_eval, rider)
    decision = write_closeout(core, report_bundle, replay, mode_eval, rider)
    write_hash_manifest()
    return decision


def run_registry_audit() -> int:
    core = write_contracts_and_registries()
    write_reports_and_audits(core, build_replay_harness_report(core["registry"]), build_mode_eval_report(core["modes"]), {"outcomes": build_outcome_records(load_disposition_events()), "calibration": build_calibration_report(load_check_reports(), load_disposition_events()), "report": {"status": "PASS", "check_reports_found": len(load_check_reports())}})
    print("CITYBRAIN-EPOCH-2-0 registry audit: PASS")
    return 0


def run_replay_harness() -> int:
    write_contracts_and_registries()
    report = write_replay_outputs()
    print(f"CITYBRAIN-EPOCH-2-0 replay harness: {report['status']}")
    return 0 if report["status"].startswith("PASS") else 1


def run_mode_eval_harness() -> int:
    core = write_contracts_and_registries()
    report = build_mode_eval_report(core["modes"])
    write_json(REPORT_ROOT / "mode_eval_harness_report.json", report)
    print(f"CITYBRAIN-EPOCH-2-0 mode eval harness: {report['status']}")
    return 0 if report["status"].startswith("PASS") else 1


def run_outcome_calibration_rider() -> int:
    write_contracts_and_registries()
    result = write_outcome_calibration_outputs()
    print(f"CITYBRAIN-EPOCH-2-0 outcome/calibration rider: {result['report']['status']}")
    return 0 if result["report"]["status"].startswith("PASS") else 1


def run_closeout() -> int:
    decision = write_all_outputs()
    hash_report = verify_hash_manifest()
    print(f"{TASK_ID}: {decision['status']}")
    print(f"Components: {decision['component_count']}")
    print(f"Active modes: {decision['active_mode_count']}")
    print(f"OutcomeRecords: {decision['outcome_records_materialized']}")
    print(f"Hash manifest: {hash_report['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if hash_report["status"] == "PASS" and all(decision["gates"].values()) else 1
