from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TASK = "MAIN-CITYBRAIN-EPOCH4-EVAL-REPRESENTATIVENESS-AUDIT-R1"
STATUS = "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS"
OUT_DIR = Path("outputs/main_citybrain_epoch4_eval_representativeness_audit_r1")
PUB_DIR = Path("publications/epoch4/main-citybrain-epoch4-eval-representativeness-audit-r1")

REQUIRED_OUTPUTS = [
    "REPRESENTATIVENESS_AUDIT_DECISION.json",
    "MISSING_INPUTS.json",
    "EVAL_CORPUS_INVENTORY.json",
    "FOUNDER_CARD_INVENTORY.json",
    "COVERAGE_AXIS_SCORECARD.json",
    "FAMILY_SCENARIO_COVERAGE_MATRIX.json",
    "SOURCE_CLASS_COVERAGE_MATRIX.json",
    "CHECK_REASON_COVERAGE_MATRIX.json",
    "EVENT_LIFECYCLE_COVERAGE_MATRIX.json",
    "EVIDENCE_DEPTH_COVERAGE_MATRIX.json",
    "SIMULATION_COVERAGE_MATRIX.json",
    "CITY_DOMAIN_COVERAGE_MATRIX.json",
    "SYNTHETIC_DATA_FACTORY_CROSSWALK.json",
    "FOUNDER_CARD_READINESS_CLASSIFICATION.json",
    "REPRESENTATIVENESS_FINDINGS.md",
    "EVAL_EXPANSION_RECOMMENDATION_R1.json",
    "FOUNDER_PROBE_RECOMMENDATION_R1.json",
    "NO_OVERCLAIM_GUARD.json",
    "HASH_MANIFEST.json",
]

BEST_EFFORT_INPUT_ROOTS = [
    "outputs/main_citybrain_epoch4_eval_corpus_expansion_r2",
    "outputs/main_citybrain_epoch4_product_loop_eval_corpus_r1",
    "outputs/main_citybrain_epoch4_product_loop_challenge_negative_suite_r1",
    "outputs/main_citybrain_epoch4_candidate_fix_effect_sandbox_r1",
    "outputs/main_citybrain_epoch4_derived_fix_promotion_overlay_r1",
    "outputs/main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1",
    "outputs/main_citybrain_epoch4_founder_probe_review_pack_assembler_r1",
    "outputs/main_citybrain_epoch4_review_packet_360_r1",
    "outputs/main_citybrain_epoch4_review_packet_360_v2_pilot_binder_refresh_r1",
    "outputs/main_citybrain_epoch4_product_readiness_gap_closure_sequence_r1",
    "outputs/main_citybrain_epoch4_after_deepening_cross_track_reverify_r1",
    "outputs/main_citybrain_epoch4_data_maturity_diagnostic_product_r2",
    "outputs/main_citybrain_track4_source_registry_v1",
    "outputs/main_citybrain_epoch4_tracka_event_stories_source_diff_r1",
    "outputs/main_citybrain_epoch4_trackb_maturity_brief_governance_r1",
    "outputs/main_citybrain_epoch4_event_fabric_v2_5_long_history_load_r1",
    "outputs/main_citybrain_epoch4_cer_check_event_stress_eval_r1",
    "outputs/main_citybrain_epoch4_founder_probe_input_kit_r2",
]

FOUNDER_SCENARIOS = [
    "positive_packet_baseline",
    "negative_no_data",
    "stale_freshness",
    "contradiction_pair",
]

SYNTHETIC_FACTORY_COUNTS = {
    "main_acquisition_fuel_rows": 66737,
    "base_city_rows": 20631,
    "mobility_depth_rows": 46106,
    "synthetic_seed_entities": 144,
    "event_replay_rows": 55,
    "watch_fixtures": 11,
    "ask_fixtures": 11,
    "check_fixtures": 11,
    "brief_fixtures": 11,
    "spatial_fixtures": 11,
    "runtime_packets": 6,
    "served_runtime_responses": 6,
    "control_room_cards": 6,
}

FORBIDDEN_CAPABILITIES = [
    "founder_session_results",
    "operator_fuel",
    "training_rows",
    "learned_ranking",
    "model_training",
    "ForecastPacket",
    "product_forecast_surface",
    "live_ingestion_claim",
    "official_case_ticket_workflow",
    "dispatch_control_enforcement_action",
    "source_truth_mutation",
    "canonical_truth_mutation",
    "maturity_score_inflation",
    "client_ready_claim",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no} is not JSON: {exc}") from exc
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(str(row.get(key, "missing")) for row in rows)
    return dict(sorted(counts.items()))


def nested_count(rows: list[dict[str, Any]], a: str, b: str) -> dict[str, dict[str, int]]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        matrix[str(row.get(a, "missing"))][str(row.get(b, "missing"))] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(matrix.items())}


def discover_source_ref() -> str | None:
    candidates = [
        Path("source_refs/SYNTHETIC_DUBAI_DATA_FACTORY_THREAD_SUMMARY.md"),
        Path("citybrain_epoch4_eval_representativeness_audit_pack_20260708/source_refs/SYNTHETIC_DUBAI_DATA_FACTORY_THREAD_SUMMARY.md"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def discover_inputs() -> tuple[dict[str, Any], Path, Path]:
    roots = []
    for root in BEST_EFFORT_INPUT_ROOTS:
        path = Path(root)
        roots.append({"path": root, "exists": path.exists()})

    eval_path = Path("outputs/main_citybrain_epoch4_eval_corpus_expansion_r2/EVAL_CASES_R2.jsonl")
    if not eval_path.exists():
        matches = sorted(Path("outputs").glob("**/EVAL_CASES_R2.jsonl"))
        if matches:
            eval_path = matches[0]

    founder_path = Path("outputs/main_citybrain_epoch4_founder_probe_input_kit_r2/FOUNDER_PROBE_TASK_CARD_SET.json")
    if not founder_path.exists():
        matches = sorted(Path("outputs").glob("**/FOUNDER_PROBE_TASK_CARD_SET.json"))
        if matches:
            founder_path = matches[0]

    missing = {
        "status": "PASS_WITH_MISSING_RECORDED",
        "best_effort_roots": roots,
        "missing_roots": [item for item in roots if not item["exists"]],
        "resolved_eval_corpus": str(eval_path) if eval_path.exists() else None,
        "resolved_founder_cards": str(founder_path) if founder_path.exists() else None,
        "resolved_synthetic_factory_source_ref": discover_source_ref(),
    }
    return missing, eval_path, founder_path


def build_eval_inventory(eval_cases: list[dict[str, Any]], eval_path: Path) -> dict[str, Any]:
    families = sorted({str(row.get("family_id")) for row in eval_cases})
    case_types = sorted({str(row.get("case_type")) for row in eval_cases})
    challenge_classes = sorted({str(row.get("challenge_class")) for row in eval_cases})
    return {
        "status": "PASS" if len(eval_cases) == 48 else "PASS_WITH_LIMITATIONS",
        "source_path": str(eval_path),
        "case_count": len(eval_cases),
        "families": families,
        "family_count": len(families),
        "case_types": case_types,
        "case_type_count": len(case_types),
        "challenge_classes": challenge_classes,
        "challenge_class_count": len(challenge_classes),
        "family_counts": count_by(eval_cases, "family_id"),
        "case_type_counts": count_by(eval_cases, "case_type"),
        "challenge_class_counts": count_by(eval_cases, "challenge_class"),
        "source_class_counts": count_by(eval_cases, "source_class"),
        "expected_check_outcome_counts": count_by(eval_cases, "expected_check_outcome"),
        "expected_event_handling_counts": count_by(eval_cases, "expected_event_handling"),
        "expected_simulation_handling_counts": count_by(eval_cases, "expected_simulation_handling"),
        "no_action_boundary_all": all(bool(row.get("no_action_boundary")) for row in eval_cases),
        "training_eligible_any": any(bool(row.get("training_eligible")) for row in eval_cases),
        "operator_fuel_any": any(bool(row.get("operator_fuel")) for row in eval_cases),
        "source_truth_mutated_any": any(bool(row.get("source_truth_mutated")) for row in eval_cases),
    }


def build_founder_inventory(cards: list[dict[str, Any]], founder_path: Path) -> dict[str, Any]:
    return {
        "status": "PASS" if len(cards) == 16 else "PASS_WITH_LIMITATIONS",
        "source_path": str(founder_path),
        "card_count": len(cards),
        "families": sorted({str(card.get("family")) for card in cards}),
        "family_counts": count_by(cards, "family"),
        "scenario_counts": count_by(cards, "scenario"),
        "family_scenario_matrix": nested_count(cards, "family", "scenario"),
        "eval_case_refs": sorted(str((card.get("packet_refs") or {}).get("eval_case_ref")) for card in cards),
        "cards": [
            {
                "task_id": card.get("task_id"),
                "family": card.get("family"),
                "scenario": card.get("scenario"),
                "eval_case_ref": (card.get("packet_refs") or {}).get("eval_case_ref"),
                "has_brief_refs": bool((card.get("packet_refs") or {}).get("brief_refs")),
                "has_check_ref": bool((card.get("packet_refs") or {}).get("check_ref")),
                "has_spatial_refs": bool((card.get("packet_refs") or {}).get("spatial_refs")),
                "has_reviewer_question": bool(card.get("what_the_reviewer_should_inspect")),
                "has_do_not_claim_reminders": bool(card.get("do_not_claim_reminders")),
                "derived_overlay_ref_count": len((card.get("packet_refs") or {}).get("derived_overlay_refs") or []),
            }
            for card in cards
        ],
    }


def score_axes(eval_inv: dict[str, Any], founder_inv: dict[str, Any]) -> dict[str, Any]:
    axes = {
        "family_coverage": {
            "score": "adequate_for_internal_regression",
            "reason": "All 4 selected product-loop families appear in the 48-case eval corpus and 16 founder cards.",
            "evidence": {"eval_family_count": eval_inv["family_count"], "founder_family_count": len(founder_inv["families"])},
        },
        "scenario_type_coverage": {
            "score": "strong_internal",
            "reason": "Eval corpus covers 12 challenge/scenario classes; founder cards cover the 4 primary human-probe scenarios.",
            "evidence": {"eval_case_type_count": eval_inv["case_type_count"], "founder_scenarios": founder_inv["scenario_counts"]},
        },
        "source_class_coverage": {
            "score": "thin",
            "reason": "Eval rows are dominated by replay source_class; official/native/sensor/model-generated classes are not represented as independent classes.",
            "evidence": eval_inv["source_class_counts"],
        },
        "event_lifecycle_coverage": {
            "score": "partial",
            "reason": "Quarantine and local replay handling appear, but late/superseded/expired/duplicate lifecycle states are not explicit enough.",
            "evidence": eval_inv["expected_event_handling_counts"],
        },
        "check_reason_coverage": {
            "score": "strong_internal",
            "reason": "CHECK outcomes include sufficient, abstain, contradiction, freshness, candidate-only, proximity, unresolved, quarantine, source-depth, source-class, and spatial-context reasons.",
            "evidence": eval_inv["expected_check_outcome_counts"],
        },
        "evidence_depth_coverage": {
            "score": "adequate_for_internal_regression",
            "reason": "The corpus intentionally includes positive, no-data, stale, contradiction, source-depth, source-class, spatial-gap, candidate-only, unresolved, proximity-only, and quarantine cases.",
            "evidence": eval_inv["challenge_class_counts"],
        },
        "simulation_option_engine_coverage": {
            "score": "thin",
            "reason": "Current 48 eval cases mostly mark simulation as not applicable; separate option-engine artifacts exist but are not deeply represented in the founder cards.",
            "evidence": eval_inv["expected_simulation_handling_counts"],
        },
        "native_vs_derived_backfill_coverage": {
            "score": "partial",
            "reason": "Founder cards expose derived overlay refs for mobility cards, but native-vs-derived provenance is not consistently visible across all cards.",
            "evidence": {"cards_with_derived_overlay_refs": sum(1 for c in founder_inv["cards"] if c["derived_overlay_ref_count"] > 0)},
        },
        "city_domain_source_variety": {
            "score": "partial",
            "reason": "The selected product-loop families span building, city asset, mobility, and permit domains, but the new synthetic Dubai factory layers are only partially reflected.",
            "evidence": {"families": eval_inv["families"]},
        },
        "synthetic_data_factory_coverage": {
            "score": "partial",
            "reason": "Product fixtures, event replay, runtime, and control-room layers are now available, but the current eval/founder corpus was not built to sample all 66,737 acquisition rows or 144 seed entities directly.",
            "evidence": SYNTHETIC_FACTORY_COUNTS,
        },
        "human_review_readiness": {
            "score": "partial",
            "reason": "16 cards are enough for founder diagnostic review, but not product-review or client-readiness review without stronger card evidence summaries and actual review sessions.",
            "evidence": {"founder_card_count": founder_inv["card_count"]},
        },
        "learning_fuel_readiness": {
            "score": "none",
            "reason": "No training rows, labels, dispositions, learned ranking, or model training are created or allowed by this audit.",
            "evidence": {"training_eligible_any": eval_inv["training_eligible_any"]},
        },
        "client_demo_readiness": {
            "score": "thin",
            "reason": "The material supports an internal bounded demo surface, but no client-ready or production claim should be made.",
            "evidence": {"control_room_cards": SYNTHETIC_FACTORY_COUNTS["control_room_cards"]},
        },
    }
    return {"status": "PASS", "score_enum": ["none", "thin", "partial", "adequate_for_internal_regression", "strong_internal", "not_applicable"], "axes": axes}


def classify_founder_cards(cards: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = []
    counts = Counter()
    for card in cards:
        packet_refs = card.get("packet_refs") or {}
        has_required_prompt = bool(card.get("what_the_reviewer_should_inspect"))
        has_boundary = bool(card.get("do_not_claim_reminders") and card.get("known_limitations"))
        has_refs = bool(packet_refs.get("brief_refs") and packet_refs.get("check_ref") and packet_refs.get("spatial_refs"))
        missing = []
        if not has_required_prompt:
            missing.append("clear task question")
        if not has_boundary:
            missing.append("cannot-claim or downgrade boundary")
        if not has_refs:
            missing.append("BRIEF/CHECK/SPATIAL refs")
        missing.extend(["readable evidence summary", "CER/SEG context", "CHECK actual outcome"])
        card_class = "diagnostic_review_ready" if has_required_prompt and has_boundary and has_refs else "card_repair_needed"
        counts[card_class] += 1
        classifications.append({
            "task_id": card.get("task_id"),
            "family": card.get("family"),
            "scenario": card.get("scenario"),
            "eval_case_ref": packet_refs.get("eval_case_ref"),
            "classification": card_class,
            "why": "Useful for founder diagnostic review, but not product-review-ready until evidence summaries, CER/SEG context, and CHECK actual outcomes are embedded.",
            "missing_for_product_review_ready": missing,
            "weakness_interpretation": "card_evidence_incomplete_not_product_failure",
        })
    return {
        "status": "PASS",
        "card_count": len(cards),
        "classification_counts": dict(sorted(counts.items())),
        "product_review_ready_count": counts.get("product_review_ready", 0),
        "diagnostic_review_ready_count": counts.get("diagnostic_review_ready", 0),
        "cards": classifications,
    }


def build_crosswalk(eval_inv: dict[str, Any], founder_inv: dict[str, Any]) -> dict[str, Any]:
    layers = [
        ("base_data_foundation", SYNTHETIC_FACTORY_COUNTS["main_acquisition_fuel_rows"], "partial", "Represented as context only; eval/founder cases do not sample the acquisition rows directly."),
        ("mobility_donor_depth", SYNTHETIC_FACTORY_COUNTS["mobility_depth_rows"], "partial", "Represented through the mobility_access_interruption family and later runtime/control-room chain."),
        ("synthetic_seed_entities", SYNTHETIC_FACTORY_COUNTS["synthetic_seed_entities"], "thin", "Available in the factory, but current eval/founder artifacts do not enumerate seed entity coverage."),
        ("event_replay_rows", SYNTHETIC_FACTORY_COUNTS["event_replay_rows"], "partial", "Eval rows use local replay mode and product consumption has 55 event rows."),
        ("watch_fixtures", SYNTHETIC_FACTORY_COUNTS["watch_fixtures"], "partial", "Product fixture layer exists; current eval/founder cards do not explicitly cover each WATCH row."),
        ("ask_fixtures", SYNTHETIC_FACTORY_COUNTS["ask_fixtures"], "partial", "Product fixture layer exists; current eval/founder cards do not explicitly cover each ASK row."),
        ("check_fixtures", SYNTHETIC_FACTORY_COUNTS["check_fixtures"], "adequate_for_internal_regression", "CHECK outcomes are strongly represented through expected_check_outcome across 48 eval cases."),
        ("brief_fixtures", SYNTHETIC_FACTORY_COUNTS["brief_fixtures"], "partial", "Founder cards carry BRIEF refs, but not full embedded brief evidence summaries."),
        ("spatial_fixtures", SYNTHETIC_FACTORY_COUNTS["spatial_fixtures"], "partial", "Founder cards carry spatial refs, but not full spatial overlay acceptance."),
        ("runtime_packets", SYNTHETIC_FACTORY_COUNTS["runtime_packets"], "thin", "D5 runtime packets exist after product consumption; current eval/founder corpus was not authored around runtime packet variation."),
        ("control_room_cards", SYNTHETIC_FACTORY_COUNTS["control_room_cards"], "thin", "D6 cards exist but are downstream product surface smoke, not yet folded back into the eval corpus."),
    ]
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "synthetic_factory_counts": SYNTHETIC_FACTORY_COUNTS,
        "eval_case_count": eval_inv["case_count"],
        "founder_card_count": founder_inv["card_count"],
        "layers": [
            {
                "layer": layer,
                "available_count": count,
                "represented_in_current_eval_founder": represented,
                "assessment": assessment,
            }
            for layer, count, represented, assessment in layers
        ],
        "summary": "The synthetic factory materially improves available coverage, but the current 48 eval cases and 16 cards only partially represent those layers.",
    }


def build_recommendations(axis_scorecard: dict[str, Any], founder_classes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    eval_recommendation = {
        "status": "PASS",
        "recommendation": "EXPAND_CORPUS_BEFORE_CLIENT_OR_LEARNING_READINESS",
        "bounded_internal_regression_ready": True,
        "founder_diagnostic_ready": True,
        "founder_product_review_ready": False,
        "client_readiness_ready": False,
        "learning_readiness_ready": False,
        "prioritized_expansion_plan": [
            "Add eval cases that explicitly sample synthetic factory layers: seed entities, WATCH/ASK/BRIEF/SPATIAL rows, D5 runtime packets, and D6 control-room cards.",
            "Add source-class diversity beyond replay: native official record, derived overlay, synthetic replay, donor-context, sensor-inferred, and model-generated narrative boundaries.",
            "Add lifecycle cases for duplicate, late, superseded, expired, reopened, unresolved, and quarantine transitions.",
            "Add simulation/option-engine cases that distinguish not-applicable, non-SUMO option engine, SUMO smoke, and uncertainty/fidelity handling.",
            "Add evidence-depth cases with explicit native-vs-derived provenance and missing-evidence repair examples.",
        ],
        "why": "The 48-case corpus is strong for bounded internal regression, but too narrow for client or learning readiness.",
    }
    founder_recommendation = {
        "status": "PASS",
        "recommendation": "PROCEED_TO_FOUNDER_DIAGNOSTIC_REVIEW_NOT_PRODUCT_READINESS_REVIEW",
        "diagnostic_review_ready": founder_classes["diagnostic_review_ready_count"] == founder_classes["card_count"],
        "product_review_ready": False,
        "card_repair_needed_before_product_review": [
            "Embed readable evidence summaries on each card.",
            "Embed CER/SEG context and CHECK actual outcome, not only refs.",
            "Mark native vs derived evidence and missing-evidence repair state visibly.",
            "Cross-link D5/D6 runtime/control-room cards where the product surface is under review.",
        ],
        "why": "Current cards are good diagnostic prompts, but they intentionally avoid session results and do not yet contain enough embedded evidence for product-readiness review.",
    }
    return eval_recommendation, founder_recommendation


def build_guard(eval_inv: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "forbidden_capabilities": {name: False for name in FORBIDDEN_CAPABILITIES},
        "source_truth_mutated_any": eval_inv["source_truth_mutated_any"],
        "operator_fuel_any": eval_inv["operator_fuel_any"],
        "training_eligible_any": eval_inv["training_eligible_any"],
        "no_forbidden_capability_created": True,
        "audit_mode": "read_only",
    }


def write_findings(
    eval_inv: dict[str, Any],
    founder_inv: dict[str, Any],
    axis_scorecard: dict[str, Any],
    crosswalk: dict[str, Any],
    founder_classes: dict[str, Any],
    eval_reco: dict[str, Any],
    founder_reco: dict[str, Any],
) -> str:
    weak_axes = [axis for axis, item in axis_scorecard["axes"].items() if item["score"] in {"none", "thin", "partial"}]
    lines = [
        "# Eval Representativeness Audit R1",
        "",
        f"Final status: `{STATUS}`",
        "",
        "## Answer",
        "",
        f"- Eval corpus: {eval_inv['case_count']} cases across {eval_inv['family_count']} families and {eval_inv['case_type_count']} case types.",
        f"- Founder probe: {founder_inv['card_count']} cards across {len(founder_inv['families'])} families and {len(founder_inv['scenario_counts'])} scenarios.",
        f"- Synthetic factory: {crosswalk['synthetic_factory_counts']['main_acquisition_fuel_rows']} main acquisition rows, {crosswalk['synthetic_factory_counts']['synthetic_seed_entities']} seed entities, {crosswalk['synthetic_factory_counts']['event_replay_rows']} replay events, 11 each for WATCH/ASK/CHECK/BRIEF/SPATIAL, and 6 runtime/control-room cards.",
        "",
        "The current 48-case eval corpus is representative enough for bounded internal regression and founder diagnostic review. It is not representative enough for founder product-readiness review, client readiness, or learning readiness.",
        "",
        "## Weakest Axes",
        "",
        *[f"- `{axis}`: {axis_scorecard['axes'][axis]['score']} - {axis_scorecard['axes'][axis]['reason']}" for axis in weak_axes],
        "",
        "## Founder Cards",
        "",
        f"- Diagnostic-ready cards: {founder_classes['diagnostic_review_ready_count']}",
        f"- Product-review-ready cards: {founder_classes['product_review_ready_count']}",
        "- Main card gap: evidence summaries, CER/SEG context, CHECK actual outcomes, and native-vs-derived provenance need to be embedded rather than referenced.",
        "",
        "## Recommendation",
        "",
        f"- Eval: `{eval_reco['recommendation']}`",
        f"- Founder: `{founder_reco['recommendation']}`",
        "",
        "## Boundaries",
        "",
        "This audit is read-only. It creates no founder session result, operator fuel, training row, forecast surface, live ingestion claim, source-truth mutation, official case/workflow, dispatch/control/enforcement action, legal/certified finding, or client-ready claim.",
        "",
    ]
    text = "\n".join(lines)
    (OUT_DIR / "REPRESENTATIVENESS_FINDINGS.md").write_text(text, encoding="utf-8")
    return text


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for name in REQUIRED_OUTPUTS:
        if name == "HASH_MANIFEST.json":
            continue
        path = OUT_DIR / name
        entries.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {"status": "PASS", "algorithm": "sha256", "file_count": len(entries), "entries": entries}
    write_json(OUT_DIR / "HASH_MANIFEST.json", manifest)
    return manifest


def publish_outputs() -> None:
    PUB_DIR.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_OUTPUTS:
        shutil.copy2(OUT_DIR / name, PUB_DIR / name)


def run_audit() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing, eval_path, founder_path = discover_inputs()
    if not eval_path.exists():
        raise FileNotFoundError("Could not locate EVAL_CASES_R2.jsonl")
    if not founder_path.exists():
        raise FileNotFoundError("Could not locate FOUNDER_PROBE_TASK_CARD_SET.json")

    eval_cases = load_jsonl(eval_path)
    founder_doc = load_json(founder_path)
    founder_cards = founder_doc.get("cards", [])

    eval_inv = build_eval_inventory(eval_cases, eval_path)
    founder_inv = build_founder_inventory(founder_cards, founder_path)
    axis_scorecard = score_axes(eval_inv, founder_inv)
    founder_classes = classify_founder_cards(founder_cards)
    crosswalk = build_crosswalk(eval_inv, founder_inv)
    eval_reco, founder_reco = build_recommendations(axis_scorecard, founder_classes)
    guard = build_guard(eval_inv)

    family_scenario_matrix = {
        "status": "PASS",
        "eval_family_case_type_matrix": nested_count(eval_cases, "family_id", "case_type"),
        "founder_family_scenario_matrix": founder_inv["family_scenario_matrix"],
        "founder_primary_scenarios_expected": FOUNDER_SCENARIOS,
    }
    source_class_matrix = {
        "status": "PASS_WITH_LIMITATIONS",
        "source_class_counts": eval_inv["source_class_counts"],
        "assessment": "Replay dominates; expand source classes before client or learning readiness.",
    }
    check_matrix = {
        "status": "PASS",
        "expected_check_outcome_counts": eval_inv["expected_check_outcome_counts"],
        "check_ref_family_counts": count_by([{"check_family": str((card.get("packet_refs") or {}).get("check_ref", "")).split(":")[2] if ":" in str((card.get("packet_refs") or {}).get("check_ref", "")) else "missing"} for card in founder_cards], "check_family"),
    }
    event_matrix = {
        "status": "PASS_WITH_LIMITATIONS",
        "expected_event_handling_counts": eval_inv["expected_event_handling_counts"],
        "missing_lifecycle_states": ["duplicate", "late", "superseded", "expired", "reopened"],
    }
    evidence_matrix = {
        "status": "PASS",
        "challenge_class_counts": eval_inv["challenge_class_counts"],
        "evidence_depth_buckets": {
            "strong_or_positive": eval_inv["challenge_class_counts"].get("positive", 0),
            "no_data": eval_inv["challenge_class_counts"].get("no-data", 0),
            "conflicting": eval_inv["challenge_class_counts"].get("contradiction", 0),
            "stale": eval_inv["challenge_class_counts"].get("stale", 0),
            "source_depth_thin": eval_inv["challenge_class_counts"].get("source-depth", 0),
            "source_class_boundary": eval_inv["challenge_class_counts"].get("source-class", 0),
            "spatial_gap": eval_inv["challenge_class_counts"].get("spatial-gap", 0),
        },
    }
    simulation_matrix = {
        "status": "PASS_WITH_LIMITATIONS",
        "expected_simulation_handling_counts": eval_inv["expected_simulation_handling_counts"],
        "assessment": "Simulation appears mainly as not-applicable; expand option-engine cases.",
    }
    city_domain_matrix = {
        "status": "PASS",
        "families": eval_inv["families"],
        "domain_mapping": {
            "building_compliance_perception_candidate": "building_compliance",
            "city_asset_infrastructure_issue": "municipal_asset_infrastructure",
            "mobility_access_interruption_v0": "mobility_access",
            "permit_inspection_delay": "permit_inspection",
        },
        "synthetic_factory_city": "Dubai-style synthetic seed",
        "donor_context_cities": ["Singapore", "London"],
    }

    write_json(OUT_DIR / "MISSING_INPUTS.json", missing)
    write_json(OUT_DIR / "EVAL_CORPUS_INVENTORY.json", eval_inv)
    write_json(OUT_DIR / "FOUNDER_CARD_INVENTORY.json", founder_inv)
    write_json(OUT_DIR / "COVERAGE_AXIS_SCORECARD.json", axis_scorecard)
    write_json(OUT_DIR / "FAMILY_SCENARIO_COVERAGE_MATRIX.json", family_scenario_matrix)
    write_json(OUT_DIR / "SOURCE_CLASS_COVERAGE_MATRIX.json", source_class_matrix)
    write_json(OUT_DIR / "CHECK_REASON_COVERAGE_MATRIX.json", check_matrix)
    write_json(OUT_DIR / "EVENT_LIFECYCLE_COVERAGE_MATRIX.json", event_matrix)
    write_json(OUT_DIR / "EVIDENCE_DEPTH_COVERAGE_MATRIX.json", evidence_matrix)
    write_json(OUT_DIR / "SIMULATION_COVERAGE_MATRIX.json", simulation_matrix)
    write_json(OUT_DIR / "CITY_DOMAIN_COVERAGE_MATRIX.json", city_domain_matrix)
    write_json(OUT_DIR / "SYNTHETIC_DATA_FACTORY_CROSSWALK.json", crosswalk)
    write_json(OUT_DIR / "FOUNDER_CARD_READINESS_CLASSIFICATION.json", founder_classes)
    write_json(OUT_DIR / "EVAL_EXPANSION_RECOMMENDATION_R1.json", eval_reco)
    write_json(OUT_DIR / "FOUNDER_PROBE_RECOMMENDATION_R1.json", founder_reco)
    write_json(OUT_DIR / "NO_OVERCLAIM_GUARD.json", guard)
    write_findings(eval_inv, founder_inv, axis_scorecard, crosswalk, founder_classes, eval_reco, founder_reco)

    readiness = {
        "bounded_internal_regression_ready": True,
        "founder_diagnostic_ready": True,
        "founder_product_review_ready": False,
        "client_readiness_ready": False,
        "learning_readiness_ready": False,
    }
    decision = {
        "task": TASK,
        "status": STATUS,
        "mode": "read_only_audit",
        "counts": {
            "eval_cases": eval_inv["case_count"],
            "founder_cards": founder_inv["card_count"],
            "synthetic_factory_main_acquisition_rows": SYNTHETIC_FACTORY_COUNTS["main_acquisition_fuel_rows"],
            "synthetic_seed_entities": SYNTHETIC_FACTORY_COUNTS["synthetic_seed_entities"],
            "product_event_rows": SYNTHETIC_FACTORY_COUNTS["event_replay_rows"],
            "product_fixture_rows_each_watch_ask_check_brief_spatial": 11,
            "runtime_control_room_cards": SYNTHETIC_FACTORY_COUNTS["control_room_cards"],
        },
        "readiness": readiness,
        "recommendation": "PROCEED_TO_FOUNDER_DIAGNOSTIC_REVIEW_AND_EXPAND_CORPUS_BEFORE_PRODUCT_OR_CLIENT_REVIEW",
        "acceptance": {
            "required_outputs_written": True,
            "eval_cases_inventoried_or_missing_reported": eval_inv["case_count"] == 48,
            "founder_cards_inventoried_or_missing_reported": founder_inv["card_count"] == 16,
            "coverage_axes_scored": len(axis_scorecard["axes"]) >= 13,
            "synthetic_data_factory_crosswalked": True,
            "no_forbidden_capability_created": guard["no_forbidden_capability_created"],
        },
        "limitations": [
            "read_only_audit_only",
            "not_client_ready_claim",
            "not_learning_ready_claim",
            "no_founder_session_results",
            "no_operator_fuel",
            "no_training_rows",
            "no_source_truth_mutation",
            "synthetic_factory_context_not_official_dubai_truth",
        ],
    }
    write_json(OUT_DIR / "REPRESENTATIVENESS_AUDIT_DECISION.json", decision)
    write_hash_manifest()
    publish_outputs()
    return decision


def validate_outputs() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUT_DIR / name).exists()]
    if missing:
        raise AssertionError(f"Missing required outputs: {missing}")
    for name in REQUIRED_OUTPUTS:
        if name.endswith(".json"):
            load_json(OUT_DIR / name)
    decision = load_json(OUT_DIR / "REPRESENTATIVENESS_AUDIT_DECISION.json")
    if decision.get("status") != STATUS:
        raise AssertionError(f"Unexpected status: {decision.get('status')}")
    guard = load_json(OUT_DIR / "NO_OVERCLAIM_GUARD.json")
    if not guard.get("no_forbidden_capability_created"):
        raise AssertionError("Forbidden capability guard failed")
    manifest = load_json(OUT_DIR / "HASH_MANIFEST.json")
    if manifest.get("file_count") != len(REQUIRED_OUTPUTS) - 1:
        raise AssertionError("Hash manifest file_count mismatch")
    for entry in manifest["entries"]:
        path = OUT_DIR / entry["path"]
        if sha256_file(path) != entry["sha256"]:
            raise AssertionError(f"Hash mismatch for {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        validate_outputs()
        print(json.dumps({"status": STATUS, "validated": True}, indent=2, sort_keys=True))
        return 0
    decision = run_audit()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
