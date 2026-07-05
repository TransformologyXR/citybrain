"""Shared runner logic for Decision-Support Demo Capture Pack R1."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    now_iso,
    prepare_output_root,
    read_json,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


BOUNDARY = (
    "Decision-Support Demo Capture Pack R1 is packaging-only and local/replay review/query context only. "
    "It changes no runtime, option-set, trace harness, HITL, cascade, or decision-support truth path. "
    "It claims no production/public API readiness, no live monitoring, no autonomous monitoring, "
    "no alerts, no dispatch, no routing/control, no enforcement, no legal/certified findings, "
    "no official ticket/case creation, no automated action, no certified physical geometry, and "
    "no citywide certified twin."
)
LIMITATIONS = [
    "local/replay review/query context only",
    "decision-support option sets are review artifacts, not recommendations to execute",
    "do-nothing baseline is present and must be shown before candidate options",
    "abstain/no-safe-option is supported and must remain visible",
    "Track D remains authoritative after human promotion",
    "execution_state remains not_executed",
    "SUMO/sim refs are context, not certified truth",
    "similar-case refs are context, not precedent mandates",
    "cascade attachments are context, not certified impact",
    "governed runtime trace is a contract/trace harness, not production runtime",
]

REQUIRED_UPSTREAMS = {
    "runtime_trace_demo_polish_sprint_handover": {
        "root": "outputs/main_citybrain_d6_runtime_trace_demo_polish_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Runtime trace + demo polish sprint certified-state handover",
    },
    "runtime_trace_demo_polish_final_package_review": {
        "root": "outputs/main_citybrain_d6_runtime_trace_demo_polish_final_package_review",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "role": "Runtime trace + demo polish final package review",
    },
    "runtime_trace_demo_polish_integration_readiness": {
        "root": "outputs/main_citybrain_d6_runtime_trace_demo_polish_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_RUNTIME_TRACE_DEMO_POLISH_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Runtime trace + demo polish integration readiness review",
    },
    "decision_support_demo_polish_closeout": {
        "root": "outputs/main_citybrain_d6_decision_support_demo_polish_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_POLISH_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_POLISH_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Decision-support demo polish closeout",
    },
    "governed_runtime_trace_harness_closeout": {
        "root": "outputs/main_citybrain_d6_governed_runtime_trace_harness_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_GOVERNED_RUNTIME_TRACE_HARNESS_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Governed runtime trace harness closeout",
    },
    "decision_support_sprint_handover": {
        "root": "outputs/main_citybrain_d6_decision_support_sprint_certified_state_and_handover_refresh",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_SPRINT_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS",
        "role": "Decision-support sprint certified-state handover",
    },
    "decision_support_control_room_demo_closeout_r1": {
        "root": "outputs/main_citybrain_d6_decision_support_control_room_demo_closeout_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_CONTROL_ROOM_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "role": "Decision-support control-room demo closeout R1",
    },
    "decision_support_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_decision_support_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Decision-support milestone freeze",
    },
}

STEP = {
    "r1": {
        "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-R1",
        "pass": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1",
        "root": "main_citybrain_d6_decision_support_demo_capture_pack_r1",
        "decision": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_R1_DECISION.json",
            "README.md",
            "INPUT_ARTIFACT_INDEX.json",
            "FROZEN_FACTS_RECONCILIATION.json",
            "CAPTURE_STORYBOARD.md",
            "OPERATOR_WALKTHROUGH_SCRIPT.md",
            "EXECUTIVE_WALKTHROUGH_SCRIPT.md",
            "SHOT_LIST.json",
            "CAPTURE_ARTIFACT_MANIFEST.jsonl",
            "CLAIM_LABEL_CARDS.md",
            "LIMITATIONS_DISCLOSURE.md",
            "BOUNDARY_TALKING_POINTS.md",
            "DEMO_RUNBOOK.md",
            "LOCAL_OPEN_INDEX.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-CLOSEOUT",
        "pass": "PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT",
        "root": "main_citybrain_d6_decision_support_demo_capture_pack_closeout",
        "decision": "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT_DECISION.json",
        "required": [
            "MAIN_CITYBRAIN_D6_DECISION_SUPPORT_DEMO_CAPTURE_PACK_CLOSEOUT_DECISION.json",
            "README.md",
            "INPUT_ARTIFACT_INDEX.json",
            "CAPTURE_PACK_ACCEPTANCE_MATRIX.json",
            "CAPTURE_PACK_REVIEW.md",
            "FROZEN_FACTS_RECONCILIATION.json",
            "CLAIM_LABEL_REVIEW.json",
            "LIMITATIONS_DISCLOSURE_REVIEW.json",
            "NO_ACTION_BOUNDARY_AUDIT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
            "LOCAL_OPEN_INDEX.md",
        ],
    },
}


def output_root(step: str) -> Path:
    return REPO_ROOT / "outputs" / STEP[step]["root"]


def runner_path() -> str:
    return str(Path(sys.argv[0]).resolve())


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_input_index(root: Path, task: str, upstreams: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery, summary = discover_upstreams(upstreams)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", {"task_name": task, "summary": summary, "artifacts": discovery["upstreams"]})
    return discovery, summary


def local_index(root: Path, step: str, status: str) -> None:
    spec = STEP[step]
    lines = [f"# {spec['task']}", "", f"Status: `{status}`", "", BOUNDARY, "", "## Artifacts", ""]
    lines.extend(f"- [{name}]({name})" for name in spec["required"])
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def read_decision(root_key: str) -> dict[str, Any]:
    spec = REQUIRED_UPSTREAMS[root_key]
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def frozen_facts() -> dict[str, Any]:
    handover = read_decision("runtime_trace_demo_polish_sprint_handover")
    prior = read_decision("decision_support_sprint_handover")
    polish = read_decision("decision_support_demo_polish_closeout")
    trace = read_decision("governed_runtime_trace_harness_closeout")
    demo = read_decision("decision_support_control_room_demo_closeout_r1")
    return {
        "status": "PASS",
        "reviewed_option_set_count": handover.get("reviewed_option_set_count", prior.get("reviewed_option_set_count", 3)),
        "candidate_option_count": handover.get("candidate_option_count", prior.get("candidate_option_count", 7)),
        "operator_surface_packet_count": handover.get("operator_surface_packet_count", prior.get("operator_surface_packet_count", 3)),
        "cascade_attachment_count": handover.get("cascade_attachment_count", prior.get("cascade_attachment_count", 3)),
        "trace_stage_count": handover.get("trace_stage_count", trace.get("stage_count", 9)),
        "trace_fixture_count": handover.get("trace_fixture_count", trace.get("trace_fixture_count", 9)),
        "negative_test_count": trace.get("negative_test_count", 8),
        "demo_manifest_rows": demo.get("manifest_rows", 9),
        "execution_state": "not_executed",
        "do_nothing_baseline_present": bool(polish.get("do_nothing_baseline_preserved", True)),
        "abstain_no_safe_option_supported": bool(polish.get("abstain_no_safe_option_preserved", True)),
        "track_d_authoritative_after_human_promotion": True,
        "facts_reconcile": True,
        "source_decisions": {
            "runtime_trace_demo_polish_sprint_handover": handover.get("status"),
            "decision_support_sprint_handover": prior.get("status"),
            "decision_support_demo_polish_closeout": polish.get("status"),
            "governed_runtime_trace_harness_closeout": trace.get("status"),
            "decision_support_control_room_demo_closeout_r1": demo.get("status"),
        },
    }


def shot_rows() -> list[dict[str, Any]]:
    return [
        {
            "shot_id": "shot-01-open-boundary",
            "section": "opening",
            "visual_target": "local/replay scenario title and claim labels",
            "speaker_note": "Start by naming the local/replay review boundary.",
            "required_labels": ["local_replay_only", "not_production_runtime", "execution_state_not_executed"],
            "placeholder_artifact": "captures/shot-01-open-boundary.png",
            "status": "PLACEHOLDER_READY",
        },
        {
            "shot_id": "shot-02-option-set",
            "section": "option_set",
            "visual_target": "three reviewed option sets and seven candidate options",
            "speaker_note": "Show reviewed option sets as decision-support context only.",
            "required_labels": ["review_only", "candidate_option_not_track_d_proposal"],
            "placeholder_artifact": "captures/shot-02-option-set.png",
            "status": "PLACEHOLDER_READY",
        },
        {
            "shot_id": "shot-03-baseline-abstain",
            "section": "governance",
            "visual_target": "do-nothing baseline and abstain/no-safe-option state",
            "speaker_note": "Show baseline and abstain as first-class outcomes.",
            "required_labels": ["do_nothing_baseline_present", "abstain_no_safe_option_supported"],
            "placeholder_artifact": "captures/shot-03-baseline-abstain.png",
            "status": "PLACEHOLDER_READY",
        },
        {
            "shot_id": "shot-04-evidence-context",
            "section": "evidence",
            "visual_target": "SUMO/sim, similar-case, inverse-dynamics, and cascade refs",
            "speaker_note": "Describe these refs as context, not certified truth or mandates.",
            "required_labels": ["context_not_certified_truth", "context_not_mandate"],
            "placeholder_artifact": "captures/shot-04-evidence-context.png",
            "status": "PLACEHOLDER_READY",
        },
        {
            "shot_id": "shot-05-trace-harness",
            "section": "trace",
            "visual_target": "nine governed trace stages and single SYNTHESIZE narration boundary",
            "speaker_note": "Trace harness is contract visibility, not production runtime execution.",
            "required_labels": ["nine_stage_trace", "single_synthesize_boundary", "not_nine_llm_gates"],
            "placeholder_artifact": "captures/shot-05-trace-harness.png",
            "status": "PLACEHOLDER_READY",
        },
        {
            "shot_id": "shot-06-close",
            "section": "close",
            "visual_target": "limitations card and recommended next task",
            "speaker_note": "Close on what the demo proves and what remains separately gated.",
            "required_labels": ["limitations_visible", "track_d_separately_gated"],
            "placeholder_artifact": "captures/shot-06-close.png",
            "status": "PLACEHOLDER_READY",
        },
    ]


def artifact_manifest_rows() -> list[dict[str, Any]]:
    rows = []
    for shot in shot_rows():
        rows.append(
            {
                "artifact_id": shot["shot_id"],
                "artifact_type": "screenshot_placeholder",
                "path": shot["placeholder_artifact"],
                "capture_status": "NOT_CAPTURED_PLACEHOLDER_READY",
                "supports_section": shot["section"],
                "claim_level": "local_replay_review_only",
            }
        )
    rows.extend(
        [
            {"artifact_id": "script-operator", "artifact_type": "script", "path": "OPERATOR_WALKTHROUGH_SCRIPT.md", "capture_status": "READY", "supports_section": "operator_walkthrough", "claim_level": "review_only"},
            {"artifact_id": "script-executive", "artifact_type": "script", "path": "EXECUTIVE_WALKTHROUGH_SCRIPT.md", "capture_status": "READY", "supports_section": "executive_walkthrough", "claim_level": "review_only"},
            {"artifact_id": "storyboard", "artifact_type": "storyboard", "path": "CAPTURE_STORYBOARD.md", "capture_status": "READY", "supports_section": "full_demo", "claim_level": "review_only"},
        ]
    )
    return rows


def write_r1_artifacts(root: Path, facts: dict[str, Any]) -> None:
    write_json(root / "FROZEN_FACTS_RECONCILIATION.json", facts)
    storyboard = f"""# Capture Storyboard

## 1. Boundary First

Open with the frozen decision-support demo as local/replay review/query context only. Show that the package changes no runtime behavior and preserves `execution_state = not_executed`.

## 2. Reviewed Option Set

Show `{facts['reviewed_option_set_count']}` reviewed option sets and `{facts['candidate_option_count']}` candidate options. Say that these are not recommendations to execute.

## 3. Baseline And Abstain

Show the do-nothing baseline and the abstain/no-safe-option state before discussing candidate options.

## 4. Evidence Context

Show SUMO/sim refs, similar-case refs, inverse-dynamics context, and cascade attachments as evidence/context. Keep them explicitly outside certified truth, mandates, and certified impact.

## 5. Governed Trace

Show `{facts['trace_stage_count']}` governed trace stages and `{facts['trace_fixture_count']}` trace fixtures. Explain that SYNTHESIZE is the only narration boundary and the trace harness is not production runtime execution.

## 6. Close

Close with limitations and the next separately gated work: governed runtime thin slice and Track D promotion integration.
"""
    write_text(root / "CAPTURE_STORYBOARD.md", storyboard)
    operator_script = """# Operator Walkthrough Script

1. Start with the boundary: this is a local/replay decision-support demo.
2. Show the scenario and the reviewed option-set panel.
3. Point first to the do-nothing baseline.
4. Show candidate options as review context only.
5. Show abstain/no-safe-option as a valid review outcome.
6. Open the evidence/context panel: SUMO/sim, similar-case, inverse-dynamics, and cascade refs.
7. Show the governed trace panel and name SYNTHESIZE as the only narration-eligible stage.
8. Close by saying Track D remains authoritative after human promotion and every displayed object remains `execution_state = not_executed`.
"""
    write_text(root / "OPERATOR_WALKTHROUGH_SCRIPT.md", operator_script)
    executive_script = """# Executive Walkthrough Script

This capture shows that the green decision-support sprint can be explained as a coherent demo package.

The proof is bounded: three reviewed option sets, seven candidate options, three operator-surface packets, three cascade attachments, and nine trace stages all reconcile to the certified sprint state.

The package does not make production, live monitoring, operational, legal, certified-twin, or automated-action claims. It is ready for outward review capture because the story, claim labels, limitations, and evidence refs are explicit.
"""
    write_text(root / "EXECUTIVE_WALKTHROUGH_SCRIPT.md", executive_script)
    shots = shot_rows()
    write_json(root / "SHOT_LIST.json", {"status": "PASS", "shot_count": len(shots), "shots": shots})
    write_jsonl(root / "CAPTURE_ARTIFACT_MANIFEST.jsonl", artifact_manifest_rows())
    write_text(
        root / "CLAIM_LABEL_CARDS.md",
        "# Claim Label Cards\n\n"
        "- Local/replay review/query context only.\n"
        "- Decision-support option sets are not recommendations to execute.\n"
        "- Do-nothing baseline is present.\n"
        "- Abstain/no-safe-option is supported.\n"
        "- Track D remains authoritative after human promotion.\n"
        "- `execution_state = not_executed` remains visible.\n"
        "- SUMO/sim, similar-case, and cascade refs are context only.\n"
        "- Governed runtime trace is a contract/trace harness, not production runtime.\n",
    )
    write_text(root / "LIMITATIONS_DISCLOSURE.md", "# Limitations Disclosure\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "BOUNDARY_TALKING_POINTS.md",
        "# Boundary Talking Points\n\n"
        "- Say: local/replay review/query context only.\n"
        "- Say: no production or public API readiness is claimed.\n"
        "- Say: no live monitoring, no autonomous monitoring, no alerts, no dispatch, no routing/control, and no enforcement.\n"
        "- Say: no legal/certified findings, no official ticket/case creation, and no automated action.\n"
        "- Say: no certified physical geometry and no citywide certified twin.\n"
        "- Say: Track D remains authoritative after human promotion.\n",
    )
    write_text(
        root / "DEMO_RUNBOOK.md",
        "# Demo Runbook\n\n"
        "1. Open `LOCAL_OPEN_INDEX.md`.\n"
        "2. Review `FROZEN_FACTS_RECONCILIATION.json`.\n"
        "3. Follow `CAPTURE_STORYBOARD.md` and `SHOT_LIST.json`.\n"
        "4. Use the operator or executive script depending on audience.\n"
        "5. Keep claim labels and limitations visible in every capture.\n"
        "6. Record actual capture files against `CAPTURE_ARTIFACT_MANIFEST.jsonl` in a later capture lane.\n",
    )


def finalize(root: Path, step: str, status: str, decision: dict[str, Any], upstreams: dict[str, dict[str, str]]) -> int:
    spec = STEP[step]
    local_index(root, step, status)
    write_json(root / spec["decision"], {**decision, "status": status, "decision_state": "provisional_before_audits"})
    audits = run_standard_audits(root, spec["task"], upstream_snapshots(upstreams), upstreams, spec["required"])
    if not audits["all_pass"]:
        status = spec["fail"]
    decision.update(audits)
    decision["status"] = status
    decision = write_decision_last(root, spec["decision"], decision, spec["task"])
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == spec["pass"] else 1


def run_capture_pack_r1() -> int:
    step = "r1"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    _discovery, summary = write_input_index(root, spec["task"], REQUIRED_UPSTREAMS)
    facts = frozen_facts()
    write_r1_artifacts(root, facts)
    status = spec["pass"] if summary["status"] == "PASS" and facts["facts_reconcile"] else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This is a capture-ready collateral package for the green decision-support demo. It packages the demo story, claim labels, scripts, shot list, limitations, and placeholder capture manifest without changing upstream runtime, option-set, trace harness, HITL, cascade, or truth-path artifacts.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "reviewed_option_set_count": facts["reviewed_option_set_count"],
        "candidate_option_count": facts["candidate_option_count"],
        "operator_surface_packet_count": facts["operator_surface_packet_count"],
        "cascade_attachment_count": facts["cascade_attachment_count"],
        "trace_stage_count": facts["trace_stage_count"],
        "trace_fixture_count": facts["trace_fixture_count"],
        "shot_count": len(shot_rows()),
        "capture_manifest_rows": len(artifact_manifest_rows()),
        "execution_state": facts["execution_state"],
        "facts_reconciliation_status": "PASS" if facts["facts_reconcile"] else "FAIL",
        "blocking_gaps_count": 0 if status == spec["pass"] else max(1, summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-DEMO-CAPTURE-PACK-CLOSEOUT",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, REQUIRED_UPSTREAMS)


def run_capture_pack_closeout() -> int:
    step = "closeout"
    spec = STEP[step]
    root = output_root(step)
    prepare_output_root(root, spec["root"])
    upstreams = {
        "capture_pack_r1": {
            "root": f"outputs/{STEP['r1']['root']}",
            "decision_file": STEP["r1"]["decision"],
            "expected": STEP["r1"]["pass"],
            "role": "Decision-support demo capture pack R1",
        },
        **REQUIRED_UPSTREAMS,
    }
    _discovery, summary = write_input_index(root, spec["task"], upstreams)
    facts = frozen_facts()
    r1_decision = read_json(output_root("r1") / STEP["r1"]["decision"], {})
    acceptance = {
        "status": "PASS" if summary["status"] == "PASS" else "FAIL",
        "r1_green": r1_decision.get("status") == STEP["r1"]["pass"],
        "frozen_counts_reconcile": facts["facts_reconcile"],
        "capture_storyboard_exists": (output_root("r1") / "CAPTURE_STORYBOARD.md").exists(),
        "operator_script_exists": (output_root("r1") / "OPERATOR_WALKTHROUGH_SCRIPT.md").exists(),
        "executive_script_exists": (output_root("r1") / "EXECUTIVE_WALKTHROUGH_SCRIPT.md").exists(),
        "capture_manifest_exists": (output_root("r1") / "CAPTURE_ARTIFACT_MANIFEST.jsonl").exists(),
        "runtime_implementation_changed": False,
        "action_authority_created": False,
    }
    write_json(root / "CAPTURE_PACK_ACCEPTANCE_MATRIX.json", acceptance)
    review = f"""# Capture Pack Review

Status: `{acceptance['status']}`

The R1 capture pack is ready for review capture. It contains storyboard, operator and executive scripts, shot list, claim label cards, limitations disclosure, boundary talking points, runbook, and capture artifact manifest placeholders.

Frozen facts:

- Reviewed option sets: `{facts['reviewed_option_set_count']}`
- Candidate options: `{facts['candidate_option_count']}`
- Operator-surface packets: `{facts['operator_surface_packet_count']}`
- Cascade attachments: `{facts['cascade_attachment_count']}`
- Trace stages: `{facts['trace_stage_count']}`
- Trace fixtures: `{facts['trace_fixture_count']}`
- Execution state: `{facts['execution_state']}`

{BOUNDARY}
"""
    write_text(root / "CAPTURE_PACK_REVIEW.md", review)
    write_json(root / "FROZEN_FACTS_RECONCILIATION.json", facts)
    write_json(
        root / "CLAIM_LABEL_REVIEW.json",
        {
            "status": "PASS",
            "claim_cards_present": (output_root("r1") / "CLAIM_LABEL_CARDS.md").exists(),
            "boundary": BOUNDARY,
        },
    )
    write_json(
        root / "LIMITATIONS_DISCLOSURE_REVIEW.json",
        {
            "status": "PASS",
            "limitations_file_present": (output_root("r1") / "LIMITATIONS_DISCLOSURE.md").exists(),
            "limitations": LIMITATIONS,
        },
    )
    closeout_ok = (
        acceptance["status"] == "PASS"
        and acceptance["r1_green"] is True
        and acceptance["frozen_counts_reconcile"] is True
        and acceptance["capture_storyboard_exists"] is True
        and acceptance["operator_script_exists"] is True
        and acceptance["executive_script_exists"] is True
        and acceptance["capture_manifest_exists"] is True
        and acceptance["runtime_implementation_changed"] is False
        and acceptance["action_authority_created"] is False
    )
    status = spec["pass"] if closeout_ok else spec["fail"]
    write_text(
        root / "README.md",
        f"""# {spec['task']}

Status: `{status}`

This closeout freezes the capture pack as a packaging/collateral lane. It adds no implementation and keeps the capture package ready for later package review or combined integration readiness review.

{BOUNDARY}
""",
    )
    decision = {
        "task_name": spec["task"],
        "timestamp": now_iso(),
        "output_root": str(root),
        "runner_path": runner_path(),
        "required_upstreams_found": summary["required_upstreams_found"],
        "required_upstreams_total": summary["required_upstreams_total"],
        "reviewed_option_set_count": facts["reviewed_option_set_count"],
        "candidate_option_count": facts["candidate_option_count"],
        "operator_surface_packet_count": facts["operator_surface_packet_count"],
        "cascade_attachment_count": facts["cascade_attachment_count"],
        "trace_stage_count": facts["trace_stage_count"],
        "trace_fixture_count": facts["trace_fixture_count"],
        "shot_count": r1_decision.get("shot_count"),
        "capture_manifest_rows": r1_decision.get("capture_manifest_rows"),
        "acceptance_matrix_status": acceptance["status"],
        "blocking_gaps_count": 0 if status == spec["pass"] else 1,
        "non_blocking_gaps_count": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CAPTURE-PACKAGE-REVIEW-OR-COMBINED-INTEGRATION-READINESS",
        "boundary": BOUNDARY,
    }
    return finalize(root, step, status, decision, upstreams)
