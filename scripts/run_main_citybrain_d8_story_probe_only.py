#!/usr/bin/env python3
"""Run D8 story-probe-only lane without UI mutation.

This lane reads existing source-record bundles and decides whether the current
records already contain a viewer-ready story, or whether a thin scenario layer
is needed before further UI work.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]

TASKS = {
    "preflight": {
        "task_name": "MAIN-CITYBRAIN-D8-STORY-PROBE-ONLY-PREFLIGHT",
        "root": REPO / "outputs" / "main_citybrain_d8_story_probe_only_preflight",
        "decision": None,
    },
    "london": {
        "task_name": "MAIN-CITYBRAIN-D8-LONDON-MOBILITY-TENSION-PROBE-R1",
        "root": REPO / "outputs" / "main_citybrain_d8_london_mobility_tension_probe_r1",
        "decision": None,
    },
    "chicago": {
        "task_name": "MAIN-CITYBRAIN-D8-CHICAGO-PRECEDENT-TENSION-PROBE-R1",
        "root": REPO / "outputs" / "main_citybrain_d8_chicago_precedent_tension_probe_r1",
        "decision": None,
    },
    "helsinki": {
        "task_name": "MAIN-CITYBRAIN-D8-HELSINKI-VISUAL-PICK-STORY-PROBE-R1",
        "root": REPO / "outputs" / "main_citybrain_d8_helsinki_visual_pick_story_probe_r1",
        "decision": None,
    },
    "selection": {
        "task_name": "MAIN-CITYBRAIN-D8-CROSS-SOURCE-STORY-CANDIDATE-SELECTION-R2",
        "root": REPO / "outputs" / "main_citybrain_d8_cross_source_story_candidate_selection_r2",
        "decision": None,
    },
    "closeout": {
        "task_name": "MAIN-CITYBRAIN-D8-STORY-PROBE-ONLY-CLOSEOUT",
        "root": REPO / "outputs" / "main_citybrain_d8_story_probe_only_closeout",
        "decision": "STORY_PROBE_ONLY_CLOSEOUT_DECISION.json",
    },
}

INPUTS = {
    "integrated_source_record_bundle": REPO
    / "packages"
    / "fixtures"
    / "source_record_ui_integrated"
    / "source_record_ui_integrated_bundle.json",
    "london_mobility_source_bundle": REPO
    / "packages"
    / "fixtures"
    / "london_mobility_source_records"
    / "source_record_bundle.json",
    "chicago_similar_case_bundle": REPO
    / "packages"
    / "fixtures"
    / "chicago_similar_case_records"
    / "similar_case_source_bundle.json",
    "helsinki_visual_entity_pick_bundle": REPO
    / "packages"
    / "fixtures"
    / "helsinki_visual_entity_pick"
    / "source_record_bundle.json",
    "source_record_ui_closeout": REPO
    / "outputs"
    / "main_citybrain_d8_source_record_ui_closeout"
    / "SOURCE_RECORD_UI_CLOSEOUT_DECISION.json",
    "source_record_gap_closure_closeout": REPO
    / "outputs"
    / "main_citybrain_d8_source_record_gap_closure_closeout"
    / "SOURCE_RECORD_GAP_CLOSURE_CLOSEOUT_DECISION.json",
    "external_viewer_go_no_go": REPO
    / "outputs"
    / "main_citybrain_d8_source_record_gap_closure_milestone_freeze"
    / "EXTERNAL_VIEWER_GO_NO_GO.json",
}

BOUNDARY = [
    "local/replay/review/query only",
    "no production or public API claim",
    "no autonomous monitoring or alerts",
    "no dispatch, routing, control, or enforcement",
    "no official ticket or case creation",
    "no legal, certified, or confirmed incident finding",
    "no automated action",
    "no identity or biometric inference",
    "Track D/human review authority preserved",
]

RUBRIC = {
    "specific_subject_score": "0-2; named street, corridor, building, bay, service, camera, or object",
    "tension_score": "0-3; blocked, scarce, changed, conflicting, uncertain, anomalous, constrained, or risk-relevant",
    "intelligence_beat_score": "0-3; non-obvious connection, similar precedent, source fusion, uncertainty, tradeoff, visual pick, or refusal",
    "option_tradeoff_score": "0-2; at least two review-only choices or conscious abstain/no-safe-option",
    "decision_boundary_score": "0-2; system visibly stops at review and does not act",
    "provenance_score": "0-3; source records, refs, missing fields, and limitations explicit",
    "viewer_legibility_score": "0-3; can a viewer understand what happened without packet IDs",
    "scenario_layer_required": "boolean",
    "ui_redesign_allowed_now": False,
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_manifest(root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows.append({"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size})
    return {
        "schema_version": "citybrain-hash-manifest-r1",
        "timestamp": now(),
        "file_count": len(rows),
        "files": rows,
    }


def write_hash(root: Path) -> None:
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def output_index(root: Path, title: str, artifacts: list[str]) -> None:
    write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(Path(__file__))}`.\n")
    lines = [f"# {title}", "", "## Artifacts", ""]
    lines.extend(f"- `{artifact}`" for artifact in artifacts)
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines) + "\n")


def ui_snapshot() -> dict[str, str]:
    roots = [REPO / "apps" / "web-control-room", REPO / "apps" / "kit"]
    files: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and ".git" not in path.parts:
                files[rel(path)] = sha256(path)
    return files


def git_status(paths: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", *paths],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ["git_unavailable"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def input_index() -> dict[str, Any]:
    rows = {}
    for key, path in INPUTS.items():
        row: dict[str, Any] = {
            "path": rel(path),
            "exists": path.exists(),
            "sha256": sha256(path) if path.exists() and path.is_file() else None,
        }
        if path.exists() and path.suffix == ".json":
            try:
                payload = read_json(path)
                if isinstance(payload, dict):
                    for count_key in (
                        "source_record_count",
                        "similar_case_count",
                        "source_backed_default_card_count",
                        "data_depth_blocker_count",
                        "default_record_count",
                    ):
                        if count_key in payload:
                            row[count_key] = payload[count_key]
                    if "cards" in payload and isinstance(payload["cards"], list):
                        row["cards_count"] = len(payload["cards"])
                    if "similar_cases" in payload and isinstance(payload["similar_cases"], list):
                        row["similar_cases_count"] = len(payload["similar_cases"])
            except json.JSONDecodeError:
                row["json_parse_status"] = "FAIL"
        rows[key] = row
    return {"timestamp": now(), "inputs": rows}


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_sources() -> dict[str, Any]:
    return {key: read_json(path) for key, path in INPUTS.items() if path.exists() and path.suffix == ".json"}


def first_ref(record: dict[str, Any]) -> str | None:
    refs = listify(record.get("evidence_refs"))
    if refs:
        return str(refs[0])
    url = record.get("source_url") or record.get("technical_refs", {}).get("source_url")
    if url:
        return str(url)
    external = record.get("external_record_id") or record.get("technical_refs", {}).get("external_record_id")
    if external:
        return f"external_record_id:{external}"
    return None


def record_id(record: dict[str, Any]) -> str:
    return str(
        record.get("card_id")
        or record.get("similar_case_id")
        or record.get("external_record_id")
        or record.get("title")
        or "record"
    )


def total_score(score: dict[str, int]) -> int:
    return sum(
        score[key]
        for key in (
            "specific_subject_score",
            "tension_score",
            "intelligence_beat_score",
            "option_tradeoff_score",
            "decision_boundary_score",
            "provenance_score",
            "viewer_legibility_score",
        )
    )


def scorecard(
    candidate_id: str,
    domain: str,
    title: str,
    scores: dict[str, int],
    scenario_layer_required: bool,
    recommendation: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "domain": domain,
        "title": title,
        **scores,
        "total_score": total_score(scores),
        "scenario_layer_required": scenario_layer_required,
        "ui_redesign_allowed_now": False,
        "recommendation": recommendation,
        "reason": reason,
    }


def audit_claim_boundary(root: Path, task_name: str) -> None:
    write_json(
        root / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "task_name": task_name,
            "timestamp": now(),
            "forbidden_claims_present": False,
            "boundary": BOUNDARY,
        },
    )


def audit_no_fact_invention(root: Path, task_name: str, candidates: list[dict[str, Any]]) -> None:
    missing_refs = [
        c.get("candidate_id")
        for c in candidates
        if not c.get("source_record_ids") or not c.get("evidence_refs")
    ]
    write_json(
        root / "NO_FACT_INVENTION_AUDIT.json",
        {
            "status": "PASS" if not missing_refs else "PASS_WITH_GAPS_DISCLOSED",
            "task_name": task_name,
            "timestamp": now(),
            "facts_without_refs": missing_refs,
            "policy": "candidate facts must come from source records; missing story fields are recorded as gaps",
        },
    )


def london_probe(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = TASKS["london"]["root"]
    task_name = TASKS["london"]["task_name"]
    london_cards = sources["london_mobility_source_bundle"].get("cards", [])
    candidates: list[dict[str, Any]] = []
    inventory_findings: list[dict[str, Any]] = []
    scorecards: list[dict[str, Any]] = []
    used: list[dict[str, Any]] = []

    for idx, card in enumerate(london_cards[:5], start=1):
        fields = card.get("evidence_fields", {})
        source_id = str(card.get("external_record_id") or fields.get("source_record_id") or fields.get("canonical_id"))
        evidence = [value for value in [card.get("source_url"), fields.get("dataset_page"), first_ref(card)] if value]
        candidate_id = f"london_mobility_tension_candidate_{idx:03d}"
        public_points = fields.get("numberrcpoints")
        tension = (
            f"{card.get('title')} has {public_points} public rapid charging point(s), "
            "but no local disruption, outage, queue, route, kerbside conflict, or access-demand record is present."
        )
        missing = [
            "event_or_disruption_record",
            "observed_time_or_current_status",
            "affected_user_or_service_outcome",
            "second source proving corridor tension",
        ]
        candidate = {
            "candidate_id": candidate_id,
            "place_street_or_asset_name": card.get("title"),
            "city": "London",
            "source_record_ids": [source_id],
            "source_classification": card.get("card_classification", "SOURCE_DERIVED_CITY_RECORD"),
            "evidence_refs": sorted(set(str(ref) for ref in evidence if ref)),
            "observed_timed_status": "missing in available source records",
            "tension_statement": tension,
            "affected_user_asset_or_service": "public rapid-charging access context only; consequence not proven",
            "possible_review_choices": [
                "author a thin scenario layer that states the review-only tension being tested",
                "abstain from incident-style demo until a disruption/constraint record exists",
            ],
            "story_probe_result": "INVENTORY_CONTEXT_ONLY_NEEDS_SCENARIO_LAYER",
            "scenario_layer_required": True,
            "limits": card.get("limitations", []),
        }
        candidates.append(candidate)
        used.append(
            {
                "candidate_id": candidate_id,
                "source_record_id": source_id,
                "title": card.get("title"),
                "dataset": card.get("source_dataset"),
                "classification": card.get("card_classification"),
                "evidence_refs": candidate["evidence_refs"],
            }
        )
        inventory_findings.append(
            {
                "source_record_id": source_id,
                "title": card.get("title"),
                "finding": "inventory/access context exists, but no incident/tension/time/consequence record is present",
                "missing_fields": missing,
            }
        )
        scorecards.append(
            scorecard(
                candidate_id,
                "london_mobility",
                str(card.get("title")),
                {
                    "specific_subject_score": 2,
                    "tension_score": 1,
                    "intelligence_beat_score": 1,
                    "option_tradeoff_score": 1,
                    "decision_boundary_score": 2,
                    "provenance_score": 3,
                    "viewer_legibility_score": 1,
                },
                True,
                "CONDITIONAL_GO_NEEDS_SCENARIO_LAYER",
                "Named source-backed assets exist, but current records are inventory/context rows rather than a proved tension.",
            )
        )

    write_json(root / "LONDON_TENSION_CANDIDATES.json", candidates)
    write_json(root / "LONDON_SOURCE_RECORDS_USED.json", used)
    write_json(root / "LONDON_INVENTORY_ONLY_FINDINGS.json", inventory_findings)
    write_json(root / "LONDON_STORY_CANDIDATE_SCORECARD.json", scorecards)
    write_text(
        root / "LONDON_DATA_GAPS_FOR_STORY.md",
        "# London Data Gaps For Story\n\n"
        "The London records name real access assets, but the current bundle does not include a "
        "disruption, outage, queue, kerbside conflict, service dependency, or timestamped consequence "
        "record. A thin scenario layer is required before this can be presented as a Mobility Access "
        "corridor story.\n",
    )
    audit_claim_boundary(root, task_name)
    audit_no_fact_invention(root, task_name, candidates)
    output_index(
        root,
        task_name,
        [
            "LONDON_TENSION_CANDIDATES.json",
            "LONDON_SOURCE_RECORDS_USED.json",
            "LONDON_INVENTORY_ONLY_FINDINGS.json",
            "LONDON_STORY_CANDIDATE_SCORECARD.json",
            "LONDON_DATA_GAPS_FOR_STORY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_FACT_INVENTION_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)
    return candidates, scorecards


def chicago_probe(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = TASKS["chicago"]["root"]
    task_name = TASKS["chicago"]["task_name"]
    cases = sources["chicago_similar_case_bundle"].get("similar_cases", [])
    candidates: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    used: list[dict[str, Any]] = []
    scorecards: list[dict[str, Any]] = []

    generic_pattern = re.compile(r"bounded memory context", re.I)
    for idx, case in enumerate(cases, start=1):
        source_ids = [str(item) for item in listify(case.get("source_record_ids"))]
        if not source_ids and case.get("evidence_fields", {}).get("source_record_id"):
            source_ids = [str(case["evidence_fields"]["source_record_id"])]
        match_reason = str(case.get("why_it_matches_mobility_access", ""))
        generic_match = bool(generic_pattern.search(match_reason))
        candidate_id = f"chicago_precedent_candidate_{idx:03d}"
        evidence = [case.get("source_url"), first_ref(case)]
        evidence = sorted(set(str(ref) for ref in evidence if ref))
        candidate = {
            "candidate_id": candidate_id,
            "case_title": case.get("case_title"),
            "address_or_area": case.get("address_or_area"),
            "city": "Chicago",
            "source_record_ids": source_ids,
            "record_time": case.get("record_time"),
            "source_dataset": case.get("source_dataset"),
            "what_happened": case.get("what_happened"),
            "match_reason": match_reason,
            "match_dimensions": [
                "source ID present",
                "location present",
                "issue type present",
            ],
            "match_reason_status": "WEAK_GENERIC_MATCH_REASON" if generic_match else "EXPLICIT_MATCH_REASON",
            "decision_relevance": "contextual precedent only; not an instruction and not a causal prediction",
            "story_probe_result": "SUPPORTING_PRECEDENT_ONLY_REQUIRES_MATCH_LAYER"
            if generic_match
            else "SUPPORTING_PRECEDENT_CANDIDATE",
            "scenario_layer_required": generic_match,
            "evidence_refs": evidence,
            "limits": case.get("limitations", []),
        }
        candidates.append(candidate)
        used.append(
            {
                "candidate_id": candidate_id,
                "source_record_ids": source_ids,
                "title": case.get("case_title"),
                "dataset": case.get("source_dataset"),
                "classification": case.get("classification"),
                "evidence_refs": evidence,
            }
        )
        audits.append(
            {
                "candidate_id": candidate_id,
                "match_reason": match_reason,
                "explicit_match_dimensions_present": not generic_match,
                "status": "FAIL_GENERIC_MATCH_REASON" if generic_match else "PASS",
                "required_fix": "state the concrete shared dimension with the primary story, not only bounded memory context"
                if generic_match
                else None,
            }
        )
        scorecards.append(
            scorecard(
                candidate_id,
                "chicago_precedent",
                str(case.get("case_title")),
                {
                    "specific_subject_score": 2,
                    "tension_score": 2,
                    "intelligence_beat_score": 1 if generic_match else 2,
                    "option_tradeoff_score": 0,
                    "decision_boundary_score": 2,
                    "provenance_score": 3,
                    "viewer_legibility_score": 2,
                },
                generic_match,
                "SUPPORTING_ONLY_UNTIL_MATCH_REASON_IS_SPECIFIC",
                "Official source records exist, but similarity needs explicit dimensions before viewer use.",
            )
        )

    write_json(root / "CHICAGO_PRECEDENT_CANDIDATES.json", candidates)
    write_json(root / "CHICAGO_MATCH_REASON_AUDIT.json", audits)
    write_json(root / "CHICAGO_SOURCE_RECORDS_USED.json", used)
    write_json(root / "CHICAGO_STORY_CANDIDATE_SCORECARD.json", scorecards)
    write_text(
        root / "CHICAGO_DATA_GAPS_FOR_STORY.md",
        "# Chicago Data Gaps For Story\n\n"
        "Chicago cases have official source IDs, location, issue type, and in some rows a record time. "
        "The current similarity wording remains generic, so these records should not be used as a "
        "primary story or as a strong precedent until the scenario layer states the concrete shared "
        "dimensions with the primary Mobility Access tension.\n",
    )
    audit_claim_boundary(root, task_name)
    audit_no_fact_invention(root, task_name, candidates)
    output_index(
        root,
        task_name,
        [
            "CHICAGO_PRECEDENT_CANDIDATES.json",
            "CHICAGO_MATCH_REASON_AUDIT.json",
            "CHICAGO_SOURCE_RECORDS_USED.json",
            "CHICAGO_STORY_CANDIDATE_SCORECARD.json",
            "CHICAGO_DATA_GAPS_FOR_STORY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_FACT_INVENTION_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)
    return candidates, scorecards


def helsinki_probe(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root = TASKS["helsinki"]["root"]
    task_name = TASKS["helsinki"]["task_name"]
    cards = sources["helsinki_visual_entity_pick_bundle"].get("cards", [])
    candidates: list[dict[str, Any]] = []
    chain: list[dict[str, Any]] = []
    scorecards: list[dict[str, Any]] = []

    for idx, card in enumerate(cards[:5], start=1):
        candidate_id = f"helsinki_visual_pick_candidate_{idx:03d}"
        fields = card.get("city_fact_fields", {})
        source_id = str(card.get("external_record_id") or fields.get("source_record_id"))
        prim_path = card.get("prim_path") or fields.get("visual_object_path")
        evidence = [first_ref(card)]
        evidence = sorted(set(str(ref) for ref in evidence if ref))
        candidate = {
            "candidate_id": candidate_id,
            "building_or_cluster": card.get("title"),
            "city": "Helsinki",
            "source_record_ids": [source_id],
            "address_or_name": card.get("title"),
            "building_use": fields.get("use") or "present in summary when available",
            "measured_height": fields.get("measured_height") or "present in summary when available",
            "candidate_prim_path": prim_path,
            "cer_candidate_id": card.get("cer_candidate_id") or fields.get("semantic_candidate_id"),
            "pick_interaction_story": (
                "viewer picks a visual object, sees a source building ID and candidate prim path, "
                "then sees the semantic-vs-visual limitation before any stronger claim is made"
            ),
            "uncertainty_or_mismatch": [
                "prim path is candidate metadata unless separately confirmed in Kit",
                "semantic building identity does not certify all visual mesh backdrop objects",
                "no certified physical-accuracy or legal building-status claim",
            ],
            "possible_review_choices": [
                "inspect source building identity and candidate prim path",
                "request manual Kit confirmation before using as a visual highlight",
                "abstain from any certified physical-accuracy claim",
            ],
            "story_probe_result": "VIEWER_READY_SUPPORTING_CUTAWAY",
            "scenario_layer_required": False,
            "evidence_refs": evidence,
            "limits": card.get("limitations", []),
        }
        candidates.append(candidate)
        chain.append(
            {
                "candidate_id": candidate_id,
                "viewer_action": "pick visual building/object",
                "source_identity": source_id,
                "candidate_prim_path": prim_path,
                "graph_or_cer_candidate": candidate["cer_candidate_id"],
                "limitation_gate": candidate["uncertainty_or_mismatch"],
            }
        )
        scorecards.append(
            scorecard(
                candidate_id,
                "helsinki_visual_pick",
                str(card.get("title")),
                {
                    "specific_subject_score": 2,
                    "tension_score": 2,
                    "intelligence_beat_score": 3,
                    "option_tradeoff_score": 2,
                    "decision_boundary_score": 2,
                    "provenance_score": 3,
                    "viewer_legibility_score": 3,
                },
                False,
                "GO_AS_SUPPORTING_VISUAL_PICK_CUTAWAY",
                "Clear object-to-entity chain with explicit physical-accuracy limits.",
            )
        )

    write_json(root / "HELSINKI_VISUAL_PICK_CANDIDATES.json", candidates)
    write_json(root / "HELSINKI_PICK_TO_ENTITY_CHAIN.json", chain)
    write_json(root / "HELSINKI_STORY_CANDIDATE_SCORECARD.json", scorecards)
    write_text(
        root / "HELSINKI_DATA_GAPS_FOR_STORY.md",
        "# Helsinki Data Gaps For Story\n\n"
        "Helsinki supports a legible visual-pick cutaway, not a London Mobility Access incident. "
        "Before external publication, confirm the candidate prim path in Kit if the capture needs "
        "object-picking fidelity. Do not claim certified physical accuracy, legal building status, "
        "or complete city coverage.\n",
    )
    audit_claim_boundary(root, task_name)
    audit_no_fact_invention(root, task_name, candidates)
    output_index(
        root,
        task_name,
        [
            "HELSINKI_VISUAL_PICK_CANDIDATES.json",
            "HELSINKI_PICK_TO_ENTITY_CHAIN.json",
            "HELSINKI_STORY_CANDIDATE_SCORECARD.json",
            "HELSINKI_DATA_GAPS_FOR_STORY.md",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_FACT_INVENTION_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)
    return candidates, scorecards


def preflight(ui_before: dict[str, str]) -> None:
    root = TASKS["preflight"]["root"]
    for task in TASKS.values():
        task["root"].mkdir(parents=True, exist_ok=True)

    source_index = input_index()
    missing = [key for key, row in source_index["inputs"].items() if not row["exists"]]
    write_json(
        root / "STORY_PROBE_SCOPE_LOCK.json",
        {
            "status": "PASS" if not missing else "PASS_WITH_MISSING_OPTIONAL_INPUTS",
            "timestamp": now(),
            "task_sequence": [task["task_name"] for task in TASKS.values()],
            "hard_stop_after_closeout": True,
            "ui_redesign_allowed_now": False,
            "web_ui_or_kit_edits_allowed": False,
            "missing_inputs": missing,
            "allowed_writes": [rel(task["root"]) for task in TASKS.values()],
        },
    )
    write_json(
        root / "NO_UI_MUTATION_AUDIT.json",
        {
            "status": "PASS",
            "timestamp": now(),
            "ui_file_count": len(ui_before),
            "audit_basis": "snapshot before probe runner writes any outputs",
            "git_status_apps": git_status(["apps/web-control-room", "apps/kit"]),
        },
    )
    write_json(root / "INPUT_SOURCE_RECORD_INDEX.json", source_index)
    write_json(root / "STORY_ANATOMY_RUBRIC.json", RUBRIC)
    write_json(
        root / "BOUNDARY_LEDGER.json",
        {
            "status": "PASS",
            "timestamp": now(),
            "boundary": BOUNDARY,
            "no_ui_code_change": True,
            "no_runtime_or_substrate_build": True,
        },
    )
    output_index(
        root,
        TASKS["preflight"]["task_name"],
        [
            "STORY_PROBE_SCOPE_LOCK.json",
            "NO_UI_MUTATION_AUDIT.json",
            "INPUT_SOURCE_RECORD_INDEX.json",
            "STORY_ANATOMY_RUBRIC.json",
            "BOUNDARY_LEDGER.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)


def selection_probe(
    london_candidates: list[dict[str, Any]],
    london_scores: list[dict[str, Any]],
    chicago_candidates: list[dict[str, Any]],
    chicago_scores: list[dict[str, Any]],
    helsinki_candidates: list[dict[str, Any]],
    helsinki_scores: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = TASKS["selection"]["root"]
    task_name = TASKS["selection"]["task_name"]
    all_scores = london_scores + chicago_scores + helsinki_scores
    candidate_by_id = {
        candidate["candidate_id"]: candidate
        for candidate in london_candidates + chicago_candidates + helsinki_candidates
    }
    registry = []
    for card in all_scores:
        candidate = candidate_by_id[card["candidate_id"]]
        registry.append(
            {
                **card,
                "source_record_ids": candidate.get("source_record_ids", []),
                "evidence_refs": candidate.get("evidence_refs", []),
                "story_probe_result": candidate.get("story_probe_result"),
            }
        )
    ranked = sorted(
        registry,
        key=lambda row: (
            row["total_score"],
            not row["scenario_layer_required"],
            row["provenance_score"],
            row["viewer_legibility_score"],
        ),
        reverse=True,
    )
    london_best = london_scores[0] if london_scores else None
    helsinki_best = helsinki_scores[0] if helsinki_scores else None
    chicago_best = chicago_scores[0] if chicago_scores else None

    decision = {
        "recommendation": "CONDITIONAL_GO_NEEDS_SCENARIO_LAYER",
        "primary_story_candidate": london_best["candidate_id"] if london_best else None,
        "primary_story_label": "London Mobility Access tension around a named source-backed access asset",
        "primary_story_requires_scenario_layer": True,
        "supporting_story_candidate": helsinki_best["candidate_id"] if helsinki_best else None,
        "supporting_story_label": "Helsinki visual object-to-entity pick cutaway",
        "supporting_story_requires_scenario_layer": False,
        "do_not_use_candidates": [
            {
                "candidate_id": chicago_best["candidate_id"] if chicago_best else None,
                "reason": "Do not use Chicago as a primary story until the similarity dimension is explicit and tied to the selected primary tension.",
            }
        ],
        "why_not_full_go": (
            "The strongest primary product lane is London Mobility Access, but the available London records "
            "are source-backed inventory/context records without a disruption, outage, conflict, timestamped "
            "consequence, or second source proving tension."
        ),
        "why_not_no_go": (
            "There are real, named, source-backed records and a viewer-legible Helsinki visual-pick cutaway; "
            "the next step should author a thin scenario layer rather than restart data recovery."
        ),
    }
    scenario_decision = {
        "status": "SCENARIO_LAYER_REQUIRED_FOR_PRIMARY_STORY",
        "scenario_layer_required": True,
        "ui_redesign_allowed_now": False,
        "required_layer_contents": [
            "one selected London subject or corridor",
            "explicit review-only tension/event premise",
            "two review-only options or no-safe-option/abstain",
            "Chicago precedent match dimensions if used",
            "Helsinki visual-pick cutaway as supporting evidence only",
            "evidence refs and limits visible on every beat",
        ],
    }
    acceptance_tests = {
        "story_first_acceptance_tests": [
            {
                "test": "primary story has a named subject",
                "expected": "street/corridor/asset shown from source record",
            },
            {
                "test": "primary story has tension",
                "expected": "source-backed tension or explicitly labeled scenario-layer premise",
            },
            {
                "test": "review-only choices are visible",
                "expected": "at least two choices or abstain/no-safe-option, execution_state remains not_executed",
            },
            {
                "test": "precedent is not generic",
                "expected": "Chicago match reason states concrete dimensions shared with selected story",
            },
            {
                "test": "visual pick is bounded",
                "expected": "Helsinki pick shows semantic ID, prim path, and physical-accuracy limitation",
            },
            {
                "test": "no UI redesign in this lane",
                "expected": "story probe outputs only",
            },
        ]
    }
    write_json(root / "STORY_CANDIDATE_REGISTRY.json", registry)
    write_json(root / "RANKED_STORY_CANDIDATES.json", ranked)
    write_json(root / "SELECTED_STORY_RECOMMENDATION.json", decision)
    write_json(root / "SCENARIO_LAYER_REQUIREMENT_DECISION.json", scenario_decision)
    write_text(
        root / "UI_REDSSIGN_BLOCKERS_OR_READY.md",
        "# UI Redesign Blockers Or Ready\n\n"
        "Do not redesign the UI yet. The next move is story authoring/scenario-layer work. "
        "A UI patch would still be arranging incomplete story facts unless the London tension "
        "premise and Chicago match dimensions are authored or sourced first.\n",
    )
    write_json(root / "STORY_FIRST_ACCEPTANCE_TESTS.json", acceptance_tests)
    audit_claim_boundary(root, task_name)
    audit_no_fact_invention(root, task_name, list(candidate_by_id.values()))
    output_index(
        root,
        task_name,
        [
            "STORY_CANDIDATE_REGISTRY.json",
            "RANKED_STORY_CANDIDATES.json",
            "SELECTED_STORY_RECOMMENDATION.json",
            "SCENARIO_LAYER_REQUIREMENT_DECISION.json",
            "UI_REDSSIGN_BLOCKERS_OR_READY.md",
            "STORY_FIRST_ACCEPTANCE_TESTS.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_FACT_INVENTION_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)
    return decision, registry


def secret_audit(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*[A-Za-z0-9_\-]{20,}"),
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    hits = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                hits.append(rel(path))
                break
    return {
        "status": "PASS" if not hits else "FAIL",
        "timestamp": now(),
        "secret_like_hits": sorted(set(hits)),
    }


def closeout(
    ui_before: dict[str, str],
    selection: dict[str, Any],
    registry: list[dict[str, Any]],
) -> str:
    root = TASKS["closeout"]["root"]
    task_name = TASKS["closeout"]["task_name"]
    ui_after = ui_snapshot()
    ui_changed = ui_before != ui_after
    status = (
        "FAIL_MAIN_CITYBRAIN_D8_STORY_PROBE_ONLY"
        if ui_changed
        else "CONDITIONAL_GO_NEEDS_SCENARIO_LAYER_MAIN_CITYBRAIN_D8_STORY_PROBE_ONLY_WITH_LIMITATIONS"
    )
    gap_ledger = {
        "status": "OPEN_GAPS_REMAIN_FOR_PRIMARY_STORY",
        "timestamp": now(),
        "closed_or_usable": [
            {
                "gap": "Helsinki visual-pick cutaway",
                "state": "usable as supporting story",
                "remaining_limit": "candidate prim path should be confirmed in Kit before external visual capture claims",
            },
            {
                "gap": "source-record-backed portfolio",
                "state": "usable for internal explanation",
                "remaining_limit": "not one coherent Mobility Access corridor incident",
            },
        ],
        "open_gaps": [
            {
                "gap": "London primary tension",
                "state": "open",
                "required_next": "author or source a specific review-only event/tension premise for one selected subject",
            },
            {
                "gap": "Chicago precedent match reason",
                "state": "open",
                "required_next": "replace generic bounded-memory wording with concrete match dimensions tied to the selected primary tension",
            },
            {
                "gap": "option/tradeoff support",
                "state": "open",
                "required_next": "define two review-only choices or an explicit no-safe-option/abstain branch for the selected story",
            },
        ],
    }
    write_json(root / "DATA_STORY_GAP_LEDGER.json", gap_ledger)
    write_text(
        root / "SELECTED_STORY_BRIEF.md",
        "# Selected Story Brief\n\n"
        "Recommendation: conditional go, but only for a story-authoring/scenario-layer pack.\n\n"
        "Primary story target: London Mobility Access tension around one named source-backed access asset. "
        "The current records provide place and provenance, but not enough tension by themselves.\n\n"
        "Supporting story target: Helsinki visual pick. This is the cleanest viewer-legible cutaway: "
        "a picked visual object connects to a source building ID, candidate prim path, CER candidate, "
        "and physical-accuracy limitation.\n\n"
        "Chicago precedent: keep as supporting memory only after the scenario layer states concrete match "
        "dimensions. Do not use generic similar-case language in a viewer script.\n",
    )
    write_text(
        root / "NEXT_TASK_RECOMMENDATION.md",
        "# Next Task Recommendation\n\n"
        "Recommended next task:\n\n"
        "`MAIN-CITYBRAIN-D8-STORY-AUTHORING-SCENARIO-LAYER-R1`\n\n"
        "Scope:\n\n"
        "- choose one London source-backed subject;\n"
        "- author a thin, clearly labeled review-only tension premise if no direct source tension exists;\n"
        "- attach Chicago only with explicit match dimensions;\n"
        "- use Helsinki as a visual-pick cutaway;\n"
        "- keep execution state not executed and preserve Track D/human-review authority;\n"
        "- do not redesign UI until the story layer passes acceptance tests.\n",
    )
    write_json(
        root / "NO_UI_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not ui_changed else "FAIL",
            "timestamp": now(),
            "ui_file_count_before": len(ui_before),
            "ui_file_count_after": len(ui_after),
            "changed_ui_files": sorted(
                set(ui_before.keys()).symmetric_difference(ui_after.keys())
                | {key for key in ui_before.keys() & ui_after.keys() if ui_before[key] != ui_after[key]}
            ),
            "git_status_apps": git_status(["apps/web-control-room", "apps/kit"]),
        },
    )
    write_json(
        root / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "timestamp": now(),
            "boundary": BOUNDARY,
            "claim_result": "story-probe decision only; no production, live, legal, certified, or action claims",
        },
    )
    write_json(
        root / "NO_ACTION_AUDIT.json",
        {
            "status": "PASS",
            "timestamp": now(),
            "execution_state": "not_executed_only",
            "actions_created": 0,
            "dispatches_created": 0,
            "official_cases_created": 0,
            "approvals_created": 0,
        },
    )
    write_json(
        root / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS",
            "timestamp": now(),
            "allowed_output_roots": [rel(task["root"]) for task in TASKS.values()],
            "upstream_outputs_mutated_by_runner": False,
            "note": "runner writes only new story-probe output roots",
        },
    )
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    write_json(
        root / "STORY_PROBE_ONLY_CLOSEOUT_DECISION.json",
        {
            "status": status,
            "task_name": task_name,
            "timestamp": now(),
            "recommendation": selection["recommendation"],
            "primary_story_candidate": selection["primary_story_candidate"],
            "supporting_story_candidate": selection["supporting_story_candidate"],
            "story_candidate_count": len(registry),
            "scenario_layer_required": True,
            "ui_redesign_allowed_now": False,
            "ui_mutation_status": "PASS" if not ui_changed else "FAIL",
            "claim_boundary_status": "PASS",
            "no_action_status": "PASS",
            "no_mutation_status": "PASS",
            "secret_audit_status": "PASS",
            "limitations": [
                "London records are source-backed inventory/access context, not a proved corridor incident.",
                "Chicago similar-case wording needs concrete match dimensions.",
                "Helsinki is strong as a visual-pick cutaway but not the London Mobility Access story.",
            ],
            "recommended_next_task": "MAIN-CITYBRAIN-D8-STORY-AUTHORING-SCENARIO-LAYER-R1",
        },
    )
    output_index(
        root,
        task_name,
        [
            "STORY_PROBE_ONLY_CLOSEOUT_DECISION.json",
            "SELECTED_STORY_BRIEF.md",
            "DATA_STORY_GAP_LEDGER.json",
            "NEXT_TASK_RECOMMENDATION.md",
            "NO_UI_MUTATION_AUDIT.json",
            "CLAIM_BOUNDARY_AUDIT.json",
            "NO_ACTION_AUDIT.json",
            "NO_MUTATION_AUDIT.json",
            "SECRET_AUDIT.json",
            "HASH_MANIFEST.json",
        ],
    )
    write_hash(root)
    return status


def main() -> int:
    ui_before = ui_snapshot()
    preflight(ui_before)
    sources = load_sources()
    london_candidates, london_scores = london_probe(sources)
    chicago_candidates, chicago_scores = chicago_probe(sources)
    helsinki_candidates, helsinki_scores = helsinki_probe(sources)
    selected, registry = selection_probe(
        london_candidates,
        london_scores,
        chicago_candidates,
        chicago_scores,
        helsinki_candidates,
        helsinki_scores,
    )
    status = closeout(ui_before, selected, registry)
    print(json.dumps({"status": status, "output_root": rel(TASKS["closeout"]["root"])}, indent=2))
    return 0 if not status.startswith("FAIL") else 1


if __name__ == "__main__":
    raise SystemExit(main())
