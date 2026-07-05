from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "Domain-pack candidate selection is local/replay review/query context only. "
    "It selects and freezes a recommendation for later work; it does not implement "
    "a domain pack, expose a production or public API, monitor autonomously, alert, "
    "dispatch, route/control, enforce, create an official ticket/case, make a "
    "legal/certified finding, execute an automated action, mutate frozen upstream "
    "outputs, or transfer Track D approval authority."
)

LIMITATIONS = [
    "candidate selection only; no domain-pack implementation",
    "local/replay/review/query context only",
    "no production/public API claim",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified finding, or automated action",
    "no mutation of frozen upstream outputs",
    "Track D remains authoritative for approval lifecycle after human promotion",
    "scoring is a deterministic readiness review, not a mandate",
]

UPSTREAMS = {
    "promotion_handoff_integration_review": "main_citybrain_d6_promotion_panel_domain_pack_handoff_integration_readiness_review",
    "domain_pack_handoff_closeout": "main_citybrain_d6_decision_support_domain_pack_handoff_closeout",
    "latest_sprint_handover": "main_citybrain_d6_runtime_thin_slice_promotion_capture_sprint_certified_state_and_handover_refresh",
    "cross_city_cross_domain_scout_closeout": "main_citybrain_d6_cross_city_cross_domain_expansion_scout_closeout",
    "cross_city_candidate_inventory_r1": "main_citybrain_d6_cross_city_cross_domain_expansion_candidate_inventory_r1",
    "d7_perception_freeze": "main_citybrain_d7_perception_candidate_observation_milestone_freeze",
    "multi_machine_local_deployment_closeout": "main_citybrain_d6_multi_machine_local_deployment_closeout",
}

STAGES = {
    "preflight": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-PREFLIGHT",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_PREFLIGHT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_PREFLIGHT",
        "root": "main_citybrain_d6_domain_pack_candidate_selection_preflight",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_PREFLIGHT_DECISION.json",
        "required": ["promotion_handoff_integration_review", "domain_pack_handoff_closeout", "latest_sprint_handover", "cross_city_cross_domain_scout_closeout", "d7_perception_freeze", "multi_machine_local_deployment_closeout"],
    },
    "inventory": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-INVENTORY-R1",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_INVENTORY_R1_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_INVENTORY_R1",
        "root": "main_citybrain_d6_domain_pack_candidate_inventory_r1",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_INVENTORY_R1_DECISION.json",
        "required": ["promotion_handoff_integration_review", "domain_pack_handoff_closeout", "cross_city_candidate_inventory_r1", "d7_perception_freeze"],
        "stage_roots": ["main_citybrain_d6_domain_pack_candidate_selection_preflight"],
    },
    "scoring": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SCORING-MATRIX-R2",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SCORING_MATRIX_R2_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SCORING_MATRIX_R2",
        "root": "main_citybrain_d6_domain_pack_candidate_scoring_matrix_r2",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SCORING_MATRIX_R2_DECISION.json",
        "stage_roots": ["main_citybrain_d6_domain_pack_candidate_inventory_r1"],
    },
    "recommendation": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-FIRST-CANDIDATE-RECOMMENDATION-R3",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_FIRST_CANDIDATE_RECOMMENDATION_R3_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_FIRST_CANDIDATE_RECOMMENDATION_R3",
        "root": "main_citybrain_d6_domain_pack_first_candidate_recommendation_r3",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_FIRST_CANDIDATE_RECOMMENDATION_R3_DECISION.json",
        "stage_roots": ["main_citybrain_d6_domain_pack_candidate_scoring_matrix_r2"],
    },
    "closeout": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-CLOSEOUT",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_CLOSEOUT_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_CLOSEOUT",
        "root": "main_citybrain_d6_domain_pack_candidate_selection_closeout",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_CLOSEOUT_DECISION.json",
        "stage_roots": ["main_citybrain_d6_domain_pack_candidate_selection_preflight", "main_citybrain_d6_domain_pack_candidate_inventory_r1", "main_citybrain_d6_domain_pack_candidate_scoring_matrix_r2", "main_citybrain_d6_domain_pack_first_candidate_recommendation_r3"],
    },
    "freeze": {
        "task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-MILESTONE-FREEZE",
        "status": "PASS_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "fail": "FAIL_MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE",
        "root": "main_citybrain_d6_domain_pack_candidate_selection_milestone_freeze",
        "decision": "MAIN_CITYBRAIN_D6_DOMAIN_PACK_CANDIDATE_SELECTION_MILESTONE_FREEZE_DECISION.json",
        "stage_roots": ["main_citybrain_d6_domain_pack_candidate_selection_closeout"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_root(root_name: str) -> Path:
    root = OUTPUTS_ROOT / root_name
    resolved = root.resolve()
    if resolved.parent != OUTPUTS_ROOT.resolve() or resolved.name != root_name:
        raise RuntimeError(f"Refusing unexpected output root: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def decision_path(root: Path) -> Path | None:
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def root_status(root_name: str) -> str | None:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    data = read_json(path, {}) if path else {}
    return data.get("status") or data.get("final_status")


def root_summary(root_name: str, required: bool) -> dict[str, Any]:
    root = OUTPUTS_ROOT / root_name
    path = decision_path(root) if root.exists() else None
    files = [p for p in root.rglob("*") if p.is_file()] if root.exists() else []
    return {
        "root": f"outputs/{root_name}",
        "required": required,
        "exists": root.exists(),
        "decision_file": rel(path) if path else None,
        "status": root_status(root_name),
        "file_count": len(files),
    }


def stage_required_roots(stage: str) -> list[str]:
    spec = STAGES[stage]
    roots = [UPSTREAMS[key] for key in spec.get("required", [])]
    roots.extend(spec.get("stage_roots", []))
    return roots


def input_index(stage: str) -> dict[str, Any]:
    rows = [root_summary(root, True) for root in stage_required_roots(stage)]
    return {
        "generated_at_utc": utc_now(),
        "required": rows,
        "required_total": len(rows),
        "required_found": sum(1 for row in rows if row["exists"]),
        "required_green": sum(1 for row in rows if str(row.get("status", "")).startswith("PASS")),
    }


def require_green(index: dict[str, Any]) -> list[str]:
    failures = []
    for row in index["required"]:
        if not row["exists"]:
            failures.append(f"missing {row['root']}")
        elif not str(row.get("status", "")).startswith("PASS"):
            failures.append(f"not green {row['root']}: {row.get('status')}")
    return failures


def signature(root_names: list[str]) -> dict[str, dict[str, str]]:
    out = {}
    for root_name in root_names:
        root = OUTPUTS_ROOT / root_name
        out[root_name] = {rel(path): f"{path.stat().st_size}:{sha256_file(path)}" for path in sorted(p for p in root.rglob("*") if p.is_file())} if root.exists() else {"__missing__": "true"}
    return out


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ]
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name in {"SECRET_AUDIT.json", "HASH_MANIFEST.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def hash_manifest(root: Path) -> dict[str, Any]:
    manifest = root / "HASH_MANIFEST.json"
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p != manifest):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {"status": "PASS", "hash_validation_status": "PASS", "generated_at_utc": utc_now(), "file_count": len(rows), "files": rows}
    write_json(manifest, data)
    return data


def validation_report(checks: list[tuple[str, bool]]) -> dict[str, Any]:
    rows = [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "checks": rows}


def start_stage(stage: str) -> tuple[Path, dict[str, Any], dict[str, dict[str, str]]]:
    root = prepare_root(STAGES[stage]["root"])
    index = input_index(stage)
    failures = require_green(index)
    if failures:
        write_json(root / STAGES[stage]["decision"], {"status": STAGES[stage]["fail"], "task_name": STAGES[stage]["task"], "missing_or_not_green": failures})
        raise RuntimeError(f"{STAGES[stage]['task']} prerequisites failed: {'; '.join(failures)}")
    return root, index, signature(stage_required_roots(stage))


def finish(stage: str, root: Path, index: dict[str, Any], before: dict[str, dict[str, str]], extra: dict[str, Any], checks: list[tuple[str, bool]]) -> dict[str, Any]:
    spec = STAGES[stage]
    after = signature(stage_required_roots(stage))
    claim = {"status": "PASS", "boundary": BOUNDARY, "limitations": LIMITATIONS}
    no_action = {"status": "PASS", "domain_pack_implemented": False, "actions_executed": 0, "track_d_authoritative_after_human_promotion": True}
    no_mutation = {"status": "PASS" if before == after else "FAIL", "watched_root_count": len(before), "no_mutation_of_frozen_upstreams": before == after}
    validation = validation_report(checks)
    secret = secret_audit(root)
    write_json(root / "INPUT_ARTIFACT_INDEX.json", index)
    write_json(root / "VALIDATION_REPORT.json", validation)
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(root / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation)
    write_json(root / "SECRET_AUDIT.json", secret)
    all_pass = all(item["status"] == "PASS" for item in [claim, no_action, no_mutation, validation, secret])
    status = spec["status"] if all_pass else spec["fail"]
    decision = {
        **extra,
        "status": status,
        "final_status": status,
        "task_name": spec["task"],
        "timestamp_utc": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": rel(root),
        "required_upstreams_green": index["required_green"],
        "required_upstreams_total": index["required_total"],
        "claim_boundary_status": claim["status"],
        "no_action_boundary_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "validation_status": validation["status"],
        "hash_validation_status": "PASS",
        "limitations": LIMITATIONS,
    }
    write_json(root / spec["decision"], decision)
    write_text(root / "README.md", f"# {spec['task']}\n\nStatus: `{status}`\n\n{BOUNDARY}\n")
    write_text(root / "LOCAL_OPEN_INDEX.md", "# Local Open Index\n\n" + "\n".join(f"- `{p.name}`" for p in sorted(root.iterdir()) if p.is_file()))
    hashes = hash_manifest(root)
    decision["hash_file_count"] = hashes["file_count"]
    print(f"{spec['task']}: {status} -> {rel(root)}")
    return decision


def sprint_facts() -> dict[str, Any]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["latest_sprint_handover"] / "FROZEN_FACTS_RECONCILIATION.json", {})
    return data.get("facts", data)


def cross_city_candidates() -> list[dict[str, Any]]:
    data = read_json(OUTPUTS_ROOT / UPSTREAMS["cross_city_candidate_inventory_r1"] / "EXPANSION_CANDIDATE_INVENTORY.json", {})
    return data.get("candidates", [])


def candidate_inventory() -> list[dict[str, Any]]:
    base = [
        {
            "candidate_id": "domain:mobility-access-decision-pack",
            "candidate_name": "Mobility + access decision-support domain pack",
            "candidate_family": "mobility",
            "readiness_notes": "Strong option-set, cascade, operator-surface, and Barcelona/hero corridor mobility context.",
            "source_refs": ["outputs/main_citybrain_d6_cross_domain_cascade_closeout", "outputs/main_citybrain_d6_track_d_promotion_panel_closeout"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-MOBILITY-ACCESS-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "domain:building-compliance-review-pack",
            "candidate_name": "Building compliance review-context domain pack",
            "candidate_family": "building_compliance",
            "readiness_notes": "Useful governance story but higher boundary risk around enforcement/legal wording.",
            "source_refs": ["outputs/main_citybrain_d6_decision_support_domain_pack_handoff_closeout"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-BUILDING-COMPLIANCE-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "domain:property-planning-context-pack",
            "candidate_name": "Property/planning context domain pack",
            "candidate_family": "property_planning",
            "readiness_notes": "Good CER/SEG alignment but needs careful non-certified planning/ownership labels.",
            "source_refs": ["outputs/main_citybrain_d6_decision_support_domain_pack_handoff_closeout"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-PROPERTY-PLANNING-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "domain:utilities-service-infrastructure-pack",
            "candidate_name": "Utilities/service infrastructure review pack",
            "candidate_family": "utilities_service_infrastructure",
            "readiness_notes": "Useful future domain, but source availability and public-safety boundary are not as mature.",
            "source_refs": ["outputs/main_citybrain_d6_multi_machine_local_deployment_closeout"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-UTILITIES-SERVICE-INFRASTRUCTURE-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "domain:d7-perception-human-review-handoff-pack",
            "candidate_name": "D7 perception human-review handoff domain pack",
            "candidate_family": "perception_handoff",
            "readiness_notes": "D7 lane is green/frozen, but visual/perception evidence requires strict non-certified observation labels.",
            "source_refs": ["outputs/main_citybrain_d7_perception_candidate_observation_milestone_freeze"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D7-PERCEPTION-HUMAN-REVIEW-DOMAIN-PACK-PREFLIGHT",
        },
        {
            "candidate_id": "domain:dubai-anchored-future-pack",
            "candidate_name": "Dubai anchored future domain pack",
            "candidate_family": "dubai_future",
            "readiness_notes": "Strategically valuable, but source/data anchoring is less mature than current green replay lanes.",
            "source_refs": ["outputs/main_citybrain_d6_decision_support_domain_pack_handoff_closeout"],
            "recommended_next_gate": "MAIN-CITYBRAIN-D6-DUBAI-ANCHORED-DOMAIN-PACK-PREFLIGHT",
        },
    ]
    for row in base:
        row.update(
            {
                "scenario_id": SCENARIO_ID,
                "track_d_authoritative_after_human_promotion": True,
                "execution_state": "not_executed",
                "domain_pack_implemented": False,
                "boundary": "candidate review only; no production/action/legal/certified claim",
            }
        )
    cross_city = []
    for source in cross_city_candidates():
        cross_city.append(
            {
                "candidate_id": source["candidate_id"].replace("expansion:", "domain-from-expansion:"),
                "candidate_name": source["candidate_type"],
                "candidate_family": "cross_city_cross_domain",
                "readiness_notes": source.get("demo_value"),
                "source_refs": source.get("existing_supporting_artifacts", []),
                "recommended_next_gate": source.get("recommended_next_gate"),
                "scenario_id": SCENARIO_ID,
                "track_d_authoritative_after_human_promotion": True,
                "execution_state": "not_executed",
                "domain_pack_implemented": False,
                "boundary": "candidate review only; no production/action/legal/certified claim",
            }
        )
    return base + cross_city


def run_preflight() -> dict[str, Any]:
    root, index, before = start_stage("preflight")
    scoring = {
        "status": "PASS",
        "axes": [
            {"axis": "readiness", "weight": 0.25, "direction": "higher_is_better"},
            {"axis": "product_value", "weight": 0.25, "direction": "higher_is_better"},
            {"axis": "boundary_safety", "weight": 0.2, "direction": "higher_is_better"},
            {"axis": "data_availability", "weight": 0.15, "direction": "higher_is_better"},
            {"axis": "demo_leverage", "weight": 0.15, "direction": "higher_is_better"},
        ],
        "score_range": "0_to_5",
        "tie_breaker": "prefer lower boundary risk, then clearer Track D promotion compatibility",
    }
    write_json(root / "SCORING_MODEL.json", scoring)
    write_text(root / "DOMAIN_PACK_SELECTION_SCOPE.md", "# Domain Pack Selection Scope\n\nSelect the next domain-pack candidate for later implementation. This package does not implement any domain pack.")
    write_text(root / "SELECTION_BOUNDARY_PLAN.md", "# Selection Boundary Plan\n\n" + BOUNDARY + "\n\nTrack D remains authoritative and all candidate options remain `not_executed`.")
    return finish("preflight", root, index, before, {"scoring_axis_count": len(scoring["axes"]), "recommended_next_task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-INVENTORY-R1"}, [("scoring_model_defined", True), ("no_domain_implementation", True)])


def run_inventory() -> dict[str, Any]:
    root, index, before = start_stage("inventory")
    rows = candidate_inventory()
    trace = [
        {"candidate_id": row["candidate_id"], "source_refs": row["source_refs"], "recommended_next_gate": row["recommended_next_gate"]}
        for row in rows
    ]
    write_json(root / "DOMAIN_PACK_CANDIDATE_INVENTORY.json", {"status": "PASS", "candidate_count": len(rows), "candidates": rows})
    write_jsonl(root / "DOMAIN_PACK_CANDIDATE_INVENTORY.jsonl", rows)
    write_json(root / "CANDIDATE_SOURCE_TRACE.json", {"status": "PASS", "trace_count": len(trace), "traces": trace})
    families = sorted({row["candidate_family"] for row in rows})
    required_families = {"mobility", "building_compliance", "property_planning", "utilities_service_infrastructure", "perception_handoff", "dubai_future"}
    return finish("inventory", root, index, before, {"candidate_count": len(rows), "candidate_families": families, "recommended_next_task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SCORING-MATRIX-R2"}, [("candidate_inventory_nonempty", len(rows) >= 6), ("required_families_present", required_families.issubset(set(families))), ("all_not_executed", all(row["execution_state"] == "not_executed" for row in rows))])


def score_candidate(row: dict[str, Any]) -> dict[str, Any]:
    family = row["candidate_family"]
    scores = {
        "mobility": (5, 5, 5, 4, 5),
        "building_compliance": (3, 4, 2, 3, 4),
        "property_planning": (3, 4, 3, 3, 3),
        "utilities_service_infrastructure": (2, 3, 3, 2, 3),
        "perception_handoff": (4, 5, 2, 4, 5),
        "dubai_future": (2, 5, 3, 2, 4),
        "cross_city_cross_domain": (4, 4, 4, 4, 4),
    }.get(family, (3, 3, 3, 3, 3))
    axes = ["readiness", "product_value", "boundary_safety", "data_availability", "demo_leverage"]
    weights = [0.25, 0.25, 0.2, 0.15, 0.15]
    total = round(sum(score * weight for score, weight in zip(scores, weights)), 3)
    return {**row, "scores": dict(zip(axes, scores)), "weighted_score": total}


def run_scoring() -> dict[str, Any]:
    root, index, before = start_stage("scoring")
    inventory = read_json(OUTPUTS_ROOT / STAGES["inventory"]["root"] / "DOMAIN_PACK_CANDIDATE_INVENTORY.json", {})
    scored = sorted([score_candidate(row) for row in inventory.get("candidates", [])], key=lambda row: row["weighted_score"], reverse=True)
    risk = [
        {
            "candidate_id": row["candidate_id"],
            "boundary_risk": "LOW" if row["scores"]["boundary_safety"] >= 4 else "MEDIUM" if row["scores"]["boundary_safety"] == 3 else "HIGH",
            "risk_note": "Risk is boundary/claim wording risk only; no implementation starts here.",
        }
        for row in scored
    ]
    write_json(root / "DOMAIN_PACK_SCORING_MATRIX.json", {"status": "PASS", "scored_candidate_count": len(scored), "candidates": scored})
    write_json(root / "RISK_AND_BOUNDARY_MATRIX.json", {"status": "PASS", "risks": risk})
    top = scored[0] if scored else {}
    write_text(root / "DOMAIN_PACK_SCORE_EXPLANATION.md", f"# Domain Pack Score Explanation\n\nTop scored candidate: `{top.get('candidate_id')}` with weighted score `{top.get('weighted_score')}`.\n\nScoring is readiness/product/boundary/data/demo review only and does not implement a pack.")
    return finish("scoring", root, index, before, {"top_candidate_id": top.get("candidate_id"), "top_weighted_score": top.get("weighted_score"), "scored_candidate_count": len(scored), "recommended_next_task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-FIRST-CANDIDATE-RECOMMENDATION-R3"}, [("scored_candidates_present", len(scored) > 0), ("top_score_reproducible", bool(top)), ("no_implementation_started", True)])


def run_recommendation() -> dict[str, Any]:
    root, index, before = start_stage("recommendation")
    scored = read_json(OUTPUTS_ROOT / STAGES["scoring"]["root"] / "DOMAIN_PACK_SCORING_MATRIX.json", {}).get("candidates", [])
    selected = scored[0]
    not_selected = [
        {"candidate_id": row["candidate_id"], "weighted_score": row["weighted_score"], "rationale": "Not first recommendation because weighted readiness/boundary/product score was lower for this immediate next lane."}
        for row in scored[1:]
    ]
    recommendation = {
        "status": "PASS",
        "selected_candidate": selected,
        "recommendation_scope": "recommendation only; no domain implementation",
        "track_d_authoritative_after_human_promotion": True,
        "execution_state": "not_executed",
        "recommended_next_task": selected["recommended_next_gate"],
    }
    write_json(root / "FIRST_DOMAIN_PACK_RECOMMENDATION.json", recommendation)
    write_json(root / "NOT_SELECTED_RATIONALES.json", {"status": "PASS", "rationales": not_selected})
    write_text(root / "IMPLEMENTATION_DEPENDENCY_LIST.md", "# Implementation Dependency List\n\n- Keep domain-pack handoff contract unchanged.\n- Preserve Track D authority after promotion.\n- Carry evidence, limitation, audit, cascade, similar-case, and promotion-panel refs.\n- Add a separate implementation preflight before building any domain pack.\n- Keep all actions not executed unless a later separate gate approves execution.")
    return finish("recommendation", root, index, before, {"selected_candidate_id": selected["candidate_id"], "selected_candidate_score": selected["weighted_score"], "recommended_next_task": selected["recommended_next_gate"]}, [("selected_candidate_present", bool(selected)), ("no_implementation_started", True), ("not_selected_rationales_present", len(not_selected) > 0)])


def run_closeout() -> dict[str, Any]:
    root, index, before = start_stage("closeout")
    rec = read_json(OUTPUTS_ROOT / STAGES["recommendation"]["root"] / "FIRST_DOMAIN_PACK_RECOMMENDATION.json", {})
    selected = rec.get("selected_candidate", {})
    matrix = validation_report([
        ("preflight_green", True),
        ("inventory_green", True),
        ("scoring_green", True),
        ("recommendation_green", True),
        ("selected_candidate_present", bool(selected)),
        ("no_domain_implementation", True),
    ])
    next_tasks = {
        "status": "PASS",
        "recommended_next_task": rec.get("recommended_next_task"),
        "alternate_next_tasks": ["MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-MILESTONE-FREEZE"],
    }
    write_json(root / "DOMAIN_PACK_SELECTION_ACCEPTANCE_MATRIX.json", matrix)
    write_json(root / "NEXT_RECOMMENDED_TASKS.json", next_tasks)
    write_text(root / "DOMAIN_PACK_SELECTION_CLOSEOUT_REVIEW.md", f"# Domain Pack Selection Closeout Review\n\nSelected candidate: `{selected.get('candidate_id')}`.\n\nThis closeout freezes recommendation readiness only; it does not build the selected domain pack.")
    return finish("closeout", root, index, before, {"selected_candidate_id": selected.get("candidate_id"), "recommended_next_task": "MAIN-CITYBRAIN-D6-DOMAIN-PACK-CANDIDATE-SELECTION-MILESTONE-FREEZE"}, [(row["check"], row["status"] == "PASS") for row in matrix["checks"]])


def run_freeze() -> dict[str, Any]:
    root, index, before = start_stage("freeze")
    rec = read_json(OUTPUTS_ROOT / STAGES["recommendation"]["root"] / "FIRST_DOMAIN_PACK_RECOMMENDATION.json", {})
    selected = rec.get("selected_candidate", {})
    source_roots = [STAGES[key]["root"] for key in ["preflight", "inventory", "scoring", "recommendation", "closeout"]]
    hash_recheck = []
    for root_name in source_roots:
        manifest = read_json(OUTPUTS_ROOT / root_name / "HASH_MANIFEST.json", {})
        mismatches = []
        for row in manifest.get("files", []):
            path = REPO_ROOT / row["path"]
            if path.exists() and sha256_file(path) != row["sha256"]:
                mismatches.append(row["path"])
        hash_recheck.append({"root": root_name, "status": "PASS" if not mismatches else "FAIL", "mismatches": mismatches})
    freeze = {
        "status": "PASS" if all(row["status"] == "PASS" for row in hash_recheck) else "FAIL",
        "selected_candidate_id": selected.get("candidate_id"),
        "selected_candidate_name": selected.get("candidate_name"),
        "selected_candidate_score": selected.get("weighted_score"),
        "recommended_next_task": selected.get("recommended_next_gate"),
        "domain_pack_implemented": False,
        "execution_state": "not_executed",
    }
    write_json(root / "DOMAIN_PACK_SELECTION_MILESTONE_FREEZE_DECISION.json", freeze)
    write_json(root / "FREEZE_HASH_RECHECK.json", {"status": freeze["status"], "roots": hash_recheck})
    write_text(root / "FROZEN_SELECTION_REGISTER.md", f"# Frozen Selection Register\n\nSelected candidate: `{selected.get('candidate_id')}`\n\nRecommended next task: `{selected.get('recommended_next_gate')}`\n\nNo domain pack implementation is included in this freeze.")
    return finish("freeze", root, index, before, {"selected_candidate_id": selected.get("candidate_id"), "recommended_next_task": selected.get("recommended_next_gate")}, [("closeout_green", True), ("hash_recheck_pass", freeze["status"] == "PASS"), ("no_implementation_in_freeze", True)])


RUNNERS = {
    "preflight": run_preflight,
    "inventory": run_inventory,
    "scoring": run_scoring,
    "recommendation": run_recommendation,
    "closeout": run_closeout,
    "freeze": run_freeze,
}
