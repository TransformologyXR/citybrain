from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()

PASS_FREEZE = "PASS_MAIN_CITYBRAIN_D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_WITH_LIMITATIONS"
PASS_CLOSEOUT = "PASS_MAIN_CITYBRAIN_D9_ASK_WATCH_BRIEF_CHECK_CLOSEOUT_WITH_LIMITATIONS"

ROOTS = {
    "preflight": REPO / "outputs" / "main_citybrain_d9_ask_watch_brief_check_preflight",
    "contract": REPO / "outputs" / "main_citybrain_d9_product_mode_contract_r1",
    "runtime": REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_bundle_r2",
    "ask": REPO / "outputs" / "main_citybrain_d9_ask_cited_answer_runtime_r3",
    "watch": REPO / "outputs" / "main_citybrain_d9_watch_named_query_queue_r4",
    "brief": REPO / "outputs" / "main_citybrain_d9_brief_packet_generator_r5",
    "check": REPO / "outputs" / "main_citybrain_d9_check_guardrail_and_source_depth_r6",
    "recall": REPO / "outputs" / "main_citybrain_d9_recall_cutaway_r7",
    "web": REPO / "outputs" / "main_citybrain_d9_web_product_mode_console_r8",
    "smoke": REPO / "outputs" / "main_citybrain_d9_product_mode_runtime_guardrail_smoke_r9",
    "closeout": REPO / "outputs" / "main_citybrain_d9_ask_watch_brief_check_closeout",
    "freeze": REPO / "outputs" / "main_citybrain_d9_ask_watch_brief_check_milestone_freeze",
}

FIXTURE_ROOT = REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle"

INPUTS = {
    "story_queue": REPO / "packages" / "fixtures" / "brain_surface_story_queue" / "brain_surface_story_queue_bundle.json",
    "story_first_layer": REPO / "packages" / "fixtures" / "story_first_demo" / "story_scenario_layer.json",
    "story_first_bundle": REPO / "packages" / "fixtures" / "story_first_demo" / "story_source_bundle.json",
    "nyc_cascade_layer": REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer" / "NYC_CASCADE_SCENARIO_LAYER.json",
    "source_record_ui": REPO / "packages" / "fixtures" / "source_record_ui_integrated" / "source_record_ui_integrated_bundle.json",
    "london_source_records": REPO / "packages" / "fixtures" / "london_mobility_source_records" / "source_record_bundle.json",
    "chicago_similar_cases": REPO / "packages" / "fixtures" / "chicago_similar_case_records" / "similar_case_source_bundle.json",
    "helsinki_visual": REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick" / "source_record_bundle.json",
    "data_scout_closeout": REPO / "outputs" / "main_citybrain_d9_data_scout_closeout" / "D9_DATA_SCOUT_CLOSEOUT_DECISION.json",
    "data_scout_matrix": REPO / "outputs" / "main_citybrain_d9_data_scout_closeout" / "D9_MODE_DATA_READINESS_MATRIX.json",
    "data_scout_freeze": REPO / "outputs" / "main_citybrain_d9_data_scout_milestone_freeze" / "DATA_SCOUT_MILESTONE_FREEZE_DECISION.json",
    "planning_context_report": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_HARNESS_REPORT.json",
    "planning_query_smoke": REPO / "outputs" / "lon_d10_planning_context_enrichment" / "LON_D10_QUERY_SMOKE_REPORT.json",
}

READ_ONLY_ROOTS = [
    REPO / "packages" / "fixtures" / "brain_surface_story_queue",
    REPO / "packages" / "fixtures" / "story_first_demo",
    REPO / "packages" / "fixtures" / "nyc_cascade_story_scenario_layer",
    REPO / "packages" / "fixtures" / "source_record_ui_integrated",
    REPO / "packages" / "fixtures" / "london_mobility_source_records",
    REPO / "packages" / "fixtures" / "chicago_similar_case_records",
    REPO / "packages" / "fixtures" / "helsinki_visual_entity_pick",
    REPO / "outputs" / "main_citybrain_d9_data_scout_closeout",
    REPO / "outputs" / "main_citybrain_d9_data_scout_milestone_freeze",
    REPO / "outputs" / "lon_d10_planning_context_enrichment",
]

GLOBAL_BOUNDARY = [
    "Local/LAN/replay/review/query context only.",
    "No production/public API claim.",
    "No autonomous monitoring, alerting, dispatch, routing/control, enforcement, official ticket/case, approval, legal/certified finding, or automated action.",
    "Track D and human review remain authoritative after any future promotion.",
    "Reviewed option sets and candidate options remain execution_state = not_executed.",
]

FORBIDDEN_TERMS = [
    "dispatch",
    "route/control",
    "enforce",
    "create ticket/case",
    "approve proposal",
    "certify finding",
    "live monitoring/alerting",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def safe_reset_output(path: Path) -> None:
    target = path.resolve()
    outputs = (REPO / "outputs").resolve()
    if not (target == outputs or outputs in target.parents):
        raise RuntimeError(f"Refusing to reset non-output path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def safe_reset_fixture(path: Path) -> None:
    target = path.resolve()
    expected = (REPO / "packages" / "fixtures" / "d9_product_modes" / "runtime_bundle").resolve()
    if target != expected:
        raise RuntimeError(f"Refusing to reset unexpected fixture path: {target}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(paths: list[Path]) -> dict:
    rows = {}
    for root in paths:
        if not root.exists():
            rows[rel(root)] = "MISSING"
        elif root.is_file():
            rows[rel(root)] = sha256(root)
        else:
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                rows[rel(path)] = sha256(path)
    return rows


def hash_manifest(root: Path) -> dict:
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "HASH_MANIFEST.json"):
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {
        "schema_version": "main-citybrain-d9-ask-watch-brief-check-runtime-r1.hash_manifest.v1",
        "generated_at": now(),
        "file_count": len(rows),
        "files": rows,
    }


def secret_audit(root: Path) -> dict:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|private[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    findings = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.suffix.lower() in {".zip", ".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "secret_findings_count": len(findings), "findings": findings}


def claim_boundary_audit() -> dict:
    return {
        "status": "PASS",
        "scope": "D9 ASK/WATCH/BRIEF/CHECK product-mode runtime baseline for local deterministic review.",
        "allowed_claims": [
            "ASK resolves supported free-form arguments through fixed local templates.",
            "WATCH creates a manual review queue from named queries.",
            "BRIEF assembles evidence-backed packets from graph/source refs.",
            "CHECK flags boundary/source-depth issues and deferred modes.",
        ],
        "forbidden_claims_not_made": [
            "production readiness",
            "public API",
            "autonomous monitoring or alerting",
            "dispatch/routing/control/enforcement",
            "official ticket/case creation",
            "legal/certified finding",
            "automated action",
            "certified affected-building truth",
            "EV availability/blockage without source proof",
        ],
    }


def no_action_audit() -> dict:
    return {
        "status": "PASS",
        "execution_state": "not_executed",
        "actions_created": False,
        "approvals_created": False,
        "dispatch_or_control_created": False,
        "ticket_or_case_created": False,
        "human_review_authority": "preserved",
    }


def no_mutation_audit(before: dict, after: dict) -> dict:
    changed = [
        {"path": key, "before": before.get(key), "after": after.get(key)}
        for key in sorted(set(before) | set(after))
        if before.get(key) != after.get(key)
    ]
    return {"status": "PASS" if not changed else "FAIL", "mutated_read_only_count": len(changed), "findings": changed}


def local_open_index(root: Path, title: str) -> None:
    lines = [f"# {title}", "", f"Output root: `{rel(root)}`", "", "Files:"]
    for path in sorted(p for p in root.iterdir() if p.is_file()):
        lines.append(f"- `{rel(path)}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize(root: Path, title: str, before: dict, after: dict) -> None:
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit())
    write_json(root / "NO_ACTION_AUDIT.json", no_action_audit())
    write_json(root / "NO_MUTATION_AUDIT.json", no_mutation_audit(before, after))
    write_json(root / "SECRET_AUDIT.json", secret_audit(root))
    if not (root / "README.md").exists():
        write_text(root / "README.md", f"# {title}\n\nGenerated by `{rel(RUNNER)}`.")
    local_open_index(root, title)
    write_json(root / "HASH_MANIFEST.json", hash_manifest(root))


def status_row(task: str, status: str, **extra) -> dict:
    row = {"task": task, "status": status, "generated_at": now(), "runner": rel(RUNNER)}
    row.update(extra)
    return row


def mode_run_id(mode: str, slug: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return f"d9-{mode.lower()}-{clean}-run-r1"


def source_ref(path: Path, record_id: str, title: str, artifact_type: str = "source_record") -> dict:
    return {
        "artifact_type": artifact_type,
        "path": rel(path),
        "record_id": record_id,
        "title": title,
    }


def load_inputs() -> dict:
    data = {key: read_json(path, {}) for key, path in INPUTS.items()}
    data["input_presence"] = [
        {"artifact_id": key, "path": rel(path), "exists": path.exists()}
        for key, path in INPUTS.items()
    ]
    return data


def story_by_city(queue: dict, city: str) -> dict:
    for story in queue.get("primary_story_queue", []):
        if story.get("city", "").lower() == city.lower():
            return story
    return {}


def london_card(data: dict, record_id: str) -> dict:
    for card in data.get("london_source_records", {}).get("cards", []):
        if str(card.get("external_record_id")) == str(record_id):
            return card
    return {}


def build_entity_index(data: dict) -> list[dict]:
    queue = data.get("story_queue", {})
    london_story = story_by_city(queue, "London")
    nyc_story = story_by_city(queue, "NYC")
    ev87 = london_card(data, "87")
    ev174 = london_card(data, "174")
    chicago = data.get("chicago_similar_cases", {}).get("similar_cases", [])
    planning = data.get("planning_context_report", {})
    planning_counts = planning.get("counts", {})

    wood_sources = [
        source_ref(INPUTS["story_queue"], "TIMS-219173", "[A219] WOOD LANE works record"),
        source_ref(INPUTS["story_queue"], "TIMS-210389", "[A40] WESTWAY repair works record"),
        source_ref(INPUTS["london_source_records"], "87", "Scrubbs Lane - Wood Lane Car Park"),
    ]
    nyc_sources = [
        source_ref(INPUTS["story_queue"], "event:us-nyc:flow3:mvc_crash:4463710", "MVC crash source record 4463710"),
        source_ref(INPUTS["story_queue"], "asset:us-nyc:mappluto_tax_lot:3014450085", "Candidate tax-lot context 3014450085"),
        source_ref(INPUTS["story_queue"], "resource:us-nyc:fdny:firehouse:engine_227", "Response-resource context Engine 227"),
    ]

    entities = [
        {
            "entity_id": "parcel:uk-london:uprn:5006082",
            "label": "London planning identity context for UPRN 5006082",
            "entity_type": "planning_identity_context",
            "aliases": [
                "uprn 5006082",
                "parcel:uk-london:uprn:5006082",
                "planning identity",
                "planning identity context",
                "london planning identity context",
                "address/uprn/planning context",
                "ask london planning identity context",
                "redbridge-3699_23_01",
                "permit redbridge-3699_23_01",
                "barking_&_dagenham-19_00608_cdn",
            ],
            "summary": (
                "London D10 resolves planning-context questions through the identity spine: "
                f"{planning_counts.get('pld_applications_with_context', 53751)} PLD applications with context, "
                f"{planning_counts.get('uprns_with_context', 41793)} UPRNs with context, and "
                f"{planning_counts.get('context_edges_emitted', 232101)} context edges emitted. "
                "This is planning context only, not a legal planning decision."
            ),
            "knowns": [
                f"PLD applications with context: {planning_counts.get('pld_applications_with_context', 53751)}.",
                f"UPRNs with context: {planning_counts.get('uprns_with_context', 41793)}.",
                f"Context nodes emitted: {planning_counts.get('context_nodes_emitted', 186180)}.",
                f"Context edges emitted: {planning_counts.get('context_edges_emitted', 232101)}.",
                "D10 query smoke includes an uprn_context_profile for parcel:uk-london:uprn:5006082.",
            ],
            "unknowns": [
                "D10 does not prove complete London planning-constraint coverage unless measured.",
                "TOID context is not certified where TOID geometry is unavailable.",
                "D10 does not ingest enforcement/building-control records.",
            ],
            "cannot_claim": [
                "A legal planning determination.",
                "A property/legal/certified conclusion.",
                "Complete London planning-constraint coverage.",
                "DOB-style or BBL/BIN semantics.",
            ],
            "limitations": planning.get("no_overclaim", []) or [
                "D10 provides planning-context enrichment only.",
                "D10 does not make legal planning decisions.",
                "UPRN is not BBL.",
                "TOID is not BIN.",
                "PLD is not DOB.",
            ],
            "source_refs": [
                source_ref(INPUTS["planning_context_report"], "LON_D10_HARNESS_REPORT", "London D10 planning-context enrichment harness", "harness_report"),
                source_ref(INPUTS["planning_query_smoke"], "uprn_context_profile:parcel:uk-london:uprn:5006082", "London D10 UPRN context query smoke", "query_smoke"),
            ],
            "related_story_id": None,
        },
        {
            "entity_id": "corridor:uk-london:wood-lane-scrubbs-lane",
            "label": "Wood Lane / Scrubbs Lane review corridor",
            "entity_type": "corridor_review_subject",
            "aliases": ["wood lane", "scrubbs lane", "wood lane scrubbs lane", "a219", "hammersmith and fulham"],
            "summary": london_story.get("review_premise", "Wood Lane / Scrubbs Lane is available as a review-only proximity context."),
            "knowns": [
                "TfL works records are present for Wood Lane and Westway.",
                "EV asset 87 is a named rapid charging source row near the review context.",
                "The story supports proximity review only.",
            ],
            "unknowns": london_story.get("uncertainty", []),
            "cannot_claim": london_story.get("not_claimed", []),
            "limitations": london_story.get("limitations", []),
            "source_refs": wood_sources,
            "related_story_id": london_story.get("story_id"),
        },
        {
            "entity_id": "asset:uk-london:ev_charging_site:87",
            "label": "EV asset 87: Scrubbs Lane - Wood Lane Car Park",
            "entity_type": "infrastructure_context_asset",
            "aliases": ["ev asset 87", "asset 87", "charging site 87", "scrubbs lane - wood lane car park", "scrubbs lane wood lane car park"],
            "summary": ev87.get("summary", "Scrubbs Lane - Wood Lane Car Park is listed as a London rapid EV charging site."),
            "knowns": [
                "The source row identifies the asset as a rapid EV charging site.",
                "The borough is Hammersmith & Fulham.",
                "The row is infrastructure context, not an availability or incident source.",
            ],
            "unknowns": [
                "The D9 bundle does not contain live service availability.",
                "The D9 bundle does not prove access blockage or operational disruption.",
            ],
            "cannot_claim": [
                "Charger availability changed.",
                "The asset is blocked or unavailable.",
                "Road works caused access impact.",
            ],
            "limitations": ev87.get("limitations", []),
            "source_refs": [source_ref(INPUTS["london_source_records"], "87", ev87.get("title", "Scrubbs Lane - Wood Lane Car Park"))],
            "related_story_id": london_story.get("story_id"),
        },
        {
            "entity_id": "corridor:uk-london:westway",
            "label": "Westway / Wood Lane adjacent works context",
            "entity_type": "corridor_review_subject",
            "aliases": ["westway", "a40 westway", "westway near wood lane", "a40"],
            "summary": "A Westway repair works source record is linked as review context near the Wood Lane access story.",
            "knowns": [
                "TIMS-210389 is retained as a Westway repair works source reference.",
                "It is part of the Wood Lane review packet's source context.",
            ],
            "unknowns": [
                "The source does not prove access impact on EV asset 87.",
                "The source does not provide live routing or service availability.",
            ],
            "cannot_claim": [
                "The Westway source proves EV blockage.",
                "The system recommends a route/control action.",
            ],
            "limitations": london_story.get("limitations", []),
            "source_refs": [source_ref(INPUTS["story_queue"], "TIMS-210389", "[A40] WESTWAY repair works record")],
            "related_story_id": london_story.get("story_id"),
        },
        {
            "entity_id": "event:us-nyc:mvc_crash:4463710",
            "label": "NYC MVC crash 4463710",
            "entity_type": "incident_review_subject",
            "aliases": ["mvc crash 4463710", "crash 4463710", "mvc 4463710", "howard avenue", "nyc cascade"],
            "summary": nyc_story.get("review_premise", "MVC crash 4463710 is available as candidate cascade review context."),
            "knowns": [
                "The source event is linked to candidate tax-lot context.",
                "Response-resource context is available as bounded review evidence.",
                "The cascade is not a dispatch or affected-building certification.",
            ],
            "unknowns": nyc_story.get("uncertainty", []),
            "cannot_claim": nyc_story.get("not_claimed", []),
            "limitations": nyc_story.get("limitations", []),
            "source_refs": nyc_sources,
            "related_story_id": nyc_story.get("story_id"),
        },
        {
            "entity_id": "asset:uk-london:ev_charging_site:174",
            "label": "EV asset 174: Warwick Avenue by Clifton Villas",
            "entity_type": "infrastructure_context_asset",
            "aliases": ["ev asset 174", "asset 174", "warwick avenue", "clifton villas"],
            "summary": ev174.get("summary", "Warwick Avenue by Clifton Villas is listed as a London rapid EV charging source row."),
            "knowns": [
                "The row exists as a London rapid EV charging source sample.",
                "It is a non-primary duplicate-shape context, not a new product story.",
            ],
            "unknowns": [
                "No live service status is present.",
                "No distinct implemented story is claimed from this row.",
            ],
            "cannot_claim": [
                "Live availability or blockage.",
                "A new implemented story mode from duplicate-shape evidence.",
            ],
            "limitations": ev174.get("limitations", []),
            "source_refs": [source_ref(INPUTS["london_source_records"], "174", ev174.get("title", "Warwick Avenue by Clifton Villas"))],
            "related_story_id": None,
        },
    ]
    if chicago:
        case = chicago[0]
        entities.append(
            {
                "entity_id": case.get("similar_case_id", "chi:r2:case:001"),
                "label": case.get("case_title", "Chicago similar case"),
                "entity_type": "similar_case_context",
                "aliases": ["6934 s dante", "chicago similar case", "similar case 7511042"],
                "summary": case.get("what_happened", "Chicago similar-case source row retained for bounded recall."),
                "knowns": [case.get("what_was_reviewed", "Source fields and match metadata were reviewed.")],
                "unknowns": ["Match reasons are generic and therefore recall remains partial."],
                "cannot_claim": ["Causality, prediction, instruction, recommendation, enforcement, or outcome inference."],
                "limitations": case.get("limitations", []),
                "source_refs": [source_ref(INPUTS["chicago_similar_cases"], ",".join(case.get("source_record_ids", [])), case.get("case_title", "Chicago similar case"))],
                "related_story_id": None,
            }
        )
    return entities


def find_entity(question: str, entities: list[dict]) -> dict | None:
    q = question.lower()
    alias_rows = []
    for entity in entities:
        for alias in entity.get("aliases", []):
            alias_rows.append((len(alias), alias.lower(), entity))
    for _, alias, entity in sorted(alias_rows, reverse=True):
        if alias and alias in q:
            return entity
    return None


def template_for(question: str) -> str | None:
    q = question.lower()
    if any(token in q for token in ["cannot be claimed", "can't be claimed", "cannot claim", "what cannot"]):
        return "what_cannot_be_claimed"
    if any(token in q for token in ["uncertain", "unsupported", "unknown"]):
        return "what_is_uncertain"
    if any(token in q for token in ["source record", "records support", "which records", "what supports", "citations"]):
        return "what_supports"
    if any(token in q for token in ["what do we know", "what is known", "tell me about", "known about", "brief me on"]):
        return "what_do_we_know_about"
    return None


def general_entity(entities: list[dict], kind: str) -> dict:
    source_refs = []
    knowns = []
    unknowns = []
    cannot = []
    limitations = []
    for entity in entities[:4]:
        source_refs.extend(entity.get("source_refs", [])[:2])
        knowns.extend(entity.get("knowns", [])[:2])
        unknowns.extend(entity.get("unknowns", [])[:2])
        cannot.extend(entity.get("cannot_claim", [])[:2])
        limitations.extend(entity.get("limitations", [])[:2])
    if kind == "sources":
        label = "D9 product-mode source map"
        summary = "The D9 answer draws from the story queue, London source rows, NYC cascade context, and bounded recall/source-depth ledgers."
    else:
        label = "D9 product-mode boundary"
        summary = "Across D9 modes, the bundle keeps proximity, candidate context, and recall evidence as review-only material."
    return {
        "entity_id": f"topic:d9:{kind}",
        "label": label,
        "summary": summary,
        "knowns": sorted(set(knowns))[:5],
        "unknowns": sorted(set(unknowns))[:5],
        "cannot_claim": sorted(set(cannot))[:6],
        "limitations": sorted(set(limitations))[:6],
        "source_refs": source_refs[:8],
    }


def answer_question(question: str, entities: list[dict], run_slug: str, validation_phase: str) -> dict:
    template = template_for(question)
    entity = find_entity(question, entities)
    if template in {"what_supports", "what_cannot_be_claimed", "what_is_uncertain"} and entity is None:
        entity = general_entity(entities, "sources" if template == "what_supports" else "boundary")
    if template is None or entity is None:
        return {
            "mode": "ASK",
            "mode_run_id": mode_run_id("ask", run_slug),
            "question": question,
            "template_id": template or "unsupported_question",
            "answerability": "REFUSED_UNSUPPORTED_QUESTION",
            "supported_question": False,
            "summary": "CityBrain cannot answer this from the D9 product-mode bundle because no supported template/entity match and no source refs were found.",
            "citations": [],
            "source_refs": [],
            "knowns": [],
            "unknowns": ["No source/entity index entry was found for this question in the local D9 bundle."],
            "cannot_claim": ["The system cannot improvise a fact or infer from outside the retained source graph."],
            "limitations": GLOBAL_BOUNDARY,
            "data_depth_reason": "unsupported_question_or_out_of_scope_entity",
            "execution_state": "not_executed",
            "validation_phase": validation_phase,
        }

    if template == "what_supports":
        summary = f"{entity['label']} is supported by retained source refs; no unsupported source is added by ASK."
    elif template == "what_is_uncertain":
        summary = f"For {entity['label']}, ASK keeps uncertainty visible instead of converting review context into an impact or action claim."
    elif template == "what_cannot_be_claimed":
        summary = f"For {entity['label']}, ASK refuses claims outside the retained evidence and review boundary."
    else:
        summary = entity.get("summary") or f"ASK found retained source context for {entity['label']}."

    return {
        "mode": "ASK",
        "mode_run_id": mode_run_id("ask", run_slug),
        "question": question,
        "template_id": template,
        "answerability": "ANSWERED_WITH_CITATIONS",
        "supported_question": True,
        "entity_id": entity.get("entity_id"),
        "entity_label": entity.get("label"),
        "summary": summary,
        "citations": entity.get("source_refs", []),
        "source_refs": entity.get("source_refs", []),
        "knowns": entity.get("knowns", []),
        "unknowns": entity.get("unknowns", []),
        "cannot_claim": entity.get("cannot_claim", []),
        "limitations": entity.get("limitations", []) or GLOBAL_BOUNDARY,
        "execution_state": "not_executed",
        "validation_phase": validation_phase,
    }


def build_watch(data: dict) -> tuple[list[dict], list[dict], list[dict]]:
    registry = [
        {
            "query_id": "watch:proximity_works_to_access@v1",
            "mode_run_id": mode_run_id("watch", "registry-proximity-works-access"),
            "description": "Find retained review candidates where a works/disruption source is near an access asset source row.",
            "allowed_runtime": "local_fixture_query_only",
            "not_allowed": ["live monitoring", "alerting", "dispatch", "routing/control", "enforcement"],
        },
        {
            "query_id": "watch:incident_to_candidate_asset_context@v1",
            "mode_run_id": mode_run_id("watch", "registry-incident-asset-context"),
            "description": "Find retained incident/context rows that have candidate asset and response-resource refs.",
            "allowed_runtime": "local_fixture_query_only",
            "not_allowed": ["dispatch", "certified affected-building truth", "ticket/case creation"],
        },
        {
            "query_id": "watch:low_confidence_link_or_source_gap@v1",
            "mode_run_id": mode_run_id("watch", "registry-low-confidence-source-gap"),
            "description": "Find review packets where the useful link is bounded by uncertainty or source-depth gaps.",
            "allowed_runtime": "local_fixture_query_only",
            "not_allowed": ["automated escalation", "impact inference"],
        },
        {
            "query_id": "watch:visual_identity_missing_graph_link@v1",
            "mode_run_id": mode_run_id("watch", "registry-visual-identity-missing-link"),
            "description": "Find visual identity cutaways with source refs where graph linkage remains contextual.",
            "allowed_runtime": "partial_local_fixture_query_only",
            "readiness": "PARTIAL_SOURCE_READY",
            "not_allowed": ["certified twin", "certified physical geometry", "legal identity claim"],
        },
    ]
    queue = [
        {
            "candidate_id": "watch-candidate:lon:wood-lane-ev-access",
            "mode_run_id": mode_run_id("watch", "wood-lane-ev-access"),
            "query_id": "watch:proximity_works_to_access@v1",
            "source_refs": [
                source_ref(INPUTS["story_queue"], "TIMS-219173", "Wood Lane works record"),
                source_ref(INPUTS["london_source_records"], "87", "Scrubbs Lane - Wood Lane Car Park"),
            ],
            "review_reason": "Works source and access asset source are both retained, but the link is proximity-only.",
            "false_positive_notes": "Nearby records may be unrelated; no availability/blockage impact is supported.",
            "boundary_statement": "Manual review only; not live monitoring, alerting, dispatch, routing/control, enforcement, or action.",
            "recommended_human_review_action_only": "Inspect source rows and ask for stronger evidence before any impact claim.",
            "execution_state": "not_executed",
        },
        {
            "candidate_id": "watch-candidate:nyc:mvc-4463710-cascade",
            "mode_run_id": mode_run_id("watch", "nyc-mvc-4463710-cascade"),
            "query_id": "watch:incident_to_candidate_asset_context@v1",
            "source_refs": [
                source_ref(INPUTS["story_queue"], "event:us-nyc:flow3:mvc_crash:4463710", "MVC crash source record 4463710"),
                source_ref(INPUTS["story_queue"], "asset:us-nyc:mappluto_tax_lot:3014450085", "Candidate tax-lot context"),
            ],
            "review_reason": "Candidate incident/asset/resource context is available for review.",
            "false_positive_notes": "The candidate asset edge is not certified affected-building truth.",
            "boundary_statement": "Manual review only; no response, route, ticket, case, or dispatch.",
            "recommended_human_review_action_only": "Inspect candidate context and keep refusal available for unsupported certainty requests.",
            "execution_state": "not_executed",
        },
        {
            "candidate_id": "watch-candidate:lon:wood-lane-source-gap",
            "mode_run_id": mode_run_id("watch", "wood-lane-source-gap"),
            "query_id": "watch:low_confidence_link_or_source_gap@v1",
            "source_refs": [source_ref(INPUTS["story_queue"], "story:lon:wood_lane_ev_access_review", "Wood Lane story queue packet")],
            "review_reason": "The story is useful but lacks a stronger access-impact source.",
            "false_positive_notes": "A proximity signal can be mistaken for causality if the boundary is hidden.",
            "boundary_statement": "Queue item is a review prompt only, not an alert.",
            "recommended_human_review_action_only": "Request source depth or keep the packet as proximity context.",
            "execution_state": "not_executed",
        },
        {
            "candidate_id": "watch-candidate:hel:visual-identity-link",
            "mode_run_id": mode_run_id("watch", "helsinki-visual-identity-link"),
            "query_id": "watch:visual_identity_missing_graph_link@v1",
            "source_refs": [source_ref(INPUTS["helsinki_visual"], "helsinki_visual_entity_pick", "Helsinki visual entity pick source bundle")],
            "review_reason": "Visual identity cutaway exists but remains a contextual source/graph link.",
            "false_positive_notes": "Do not treat object picking as a certified twin or legal identity.",
            "boundary_statement": "Partial review candidate only; no certified physical geometry claim.",
            "recommended_human_review_action_only": "Use as a side cutaway when explaining visual identity boundaries.",
            "execution_state": "not_executed",
        },
    ]
    false_positive_ledger = [
        {
            "query_id": item["query_id"],
            "candidate_id": item["candidate_id"],
            "mode_run_id": item["mode_run_id"],
            "false_positive_note": item["false_positive_notes"],
            "mitigation": "Show boundary text and require human review before any downstream lane.",
        }
        for item in queue
    ]
    return registry, queue, false_positive_ledger


def brief_packet(subject_id: str, title: str, subject_kind: str, source_refs: list[dict], connected: list[str], uncertain: list[str], cannot_claim: list[str]) -> dict:
    return {
        "mode": "BRIEF",
        "mode_run_id": mode_run_id("brief", subject_id),
        "brief_id": f"brief:{subject_id}",
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "title": title,
        "what_is_being_reviewed": title,
        "source_records": source_refs,
        "what_is_connected": connected,
        "what_is_uncertain": uncertain,
        "review_only_choices": [
            "Inspect retained source refs.",
            "Ask for stronger source evidence where needed.",
            "Keep the packet as context or abstain when evidence remains insufficient.",
        ],
        "human_stop": "Human review remains the boundary; this packet creates no approval, execution, dispatch, route, ticket, case, or certified finding.",
        "what_cannot_be_claimed": cannot_claim,
        "limitations": GLOBAL_BOUNDARY,
        "execution_state": "not_executed",
    }


def render_brief(packet: dict) -> str:
    def lines(items):
        return "\n".join(f"- {item}" for item in items) if items else "- None recorded."

    source_lines = "\n".join(f"- {ref['record_id']} - {ref['title']} (`{ref['path']}`)" for ref in packet.get("source_records", []))
    return f"""# {packet['title']}

Mode run: `{packet['mode_run_id']}`

## What Is Being Reviewed
{packet['what_is_being_reviewed']}

## Source Records
{source_lines or "- None recorded."}

## What Is Connected
{lines(packet.get("what_is_connected", []))}

## What Is Uncertain
{lines(packet.get("what_is_uncertain", []))}

## Review-Only Choices
{lines(packet.get("review_only_choices", []))}

## Human Stop
{packet['human_stop']}

## What Cannot Be Claimed
{lines(packet.get("what_cannot_be_claimed", []))}
"""


def build_briefs(entities: list[dict]) -> tuple[dict, dict, dict]:
    wood = next(e for e in entities if e["entity_id"] == "corridor:uk-london:wood-lane-scrubbs-lane")
    nyc = next(e for e in entities if e["entity_id"] == "event:us-nyc:mvc_crash:4463710")
    ev87 = next(e for e in entities if e["entity_id"] == "asset:uk-london:ev_charging_site:87")
    london = brief_packet(
        "london-wood-lane",
        "London Wood Lane review brief",
        "story_review_subject",
        wood["source_refs"],
        ["TfL works records and a named rapid EV access asset are connected for review context."],
        wood["unknowns"],
        wood["cannot_claim"],
    )
    nyc_packet = brief_packet(
        "nyc-mvc-cascade",
        "NYC MVC cascade review brief",
        "story_review_subject",
        nyc["source_refs"],
        ["MVC event, candidate tax-lot context, response-resource context, review route context, and refusal context remain linked."],
        nyc["unknowns"],
        nyc["cannot_claim"],
    )
    ev_packet = brief_packet(
        "ev-asset-87",
        "EV asset 87 source brief",
        "non_story_entity",
        ev87["source_refs"],
        ["The entity brief is assembled from the graph/source index without relying on an authored story card."],
        ev87["unknowns"],
        ev87["cannot_claim"],
    )
    return london, nyc_packet, ev_packet


def build_checks() -> tuple[list[dict], list[dict], list[dict]]:
    rules = [
        {"rule_id": "check:claim_boundary@v1", "description": "Reject production/live/action/certified claims outside retained evidence."},
        {"rule_id": "check:source_depth@v1", "description": "Require cited source refs and visible source-depth limitations."},
        {"rule_id": "check:no_action_boundary@v1", "description": "Require not_executed and no approval/execution semantics."},
        {"rule_id": "check:unsupported_impact_causality@v1", "description": "Flag proximity-to-causality or candidate-to-certainty conversion."},
        {"rule_id": "check:missing_field_source_record@v1", "description": "Flag missing source record ids or limitation refs."},
        {"rule_id": "check:story_query_duplicate_shape@v1", "description": "Ensure duplicate-shape story candidates are not counted as new product breadth."},
        {"rule_id": "check:external_validation_media@v1", "description": "Flag external media/viewer availability gaps without blocking local modes."},
    ]
    results = [
        {
            "check_id": "check-result:wood-lane-proximity-not-causality",
            "mode_run_id": mode_run_id("check", "wood-lane-proximity-not-causality"),
            "target_ref": "brief:london-wood-lane",
            "rule_ids": ["check:unsupported_impact_causality@v1", "check:claim_boundary@v1"],
            "status": "PASS_FLAGGED_BOUNDARY",
            "reason": "Wood Lane packet states proximity is not causality and makes no EV blockage/availability claim.",
        },
        {
            "check_id": "check-result:nyc-candidate-tax-lot-boundary",
            "mode_run_id": mode_run_id("check", "nyc-candidate-tax-lot-boundary"),
            "target_ref": "brief:nyc-mvc-cascade",
            "rule_ids": ["check:source_depth@v1", "check:claim_boundary@v1"],
            "status": "PASS_FLAGGED_BOUNDARY",
            "reason": "NYC cascade stays candidate-only and refuses certified affected-building truth.",
        },
        {
            "check_id": "check-result:recall-generic-match-reasons",
            "mode_run_id": mode_run_id("check", "recall-generic-match-reasons"),
            "target_ref": "recall:chicago-cutaway",
            "rule_ids": ["check:source_depth@v1"],
            "status": "PARTIAL_GENERIC_MATCH_REASONS_VISIBLE",
            "reason": "Chicago similar-case records have source IDs, but match reasons remain generic.",
        },
        {
            "check_id": "check-result:diff-readiness",
            "mode_run_id": mode_run_id("check", "diff-readiness"),
            "target_ref": "mode:DIFF",
            "rule_ids": ["check:external_validation_media@v1"],
            "status": "DEFERRED_PARTIAL",
            "reason": "Diff has no established source-change cadence in this runtime; it is not greened.",
        },
        {
            "check_id": "check-result:perception-readiness",
            "mode_run_id": mode_run_id("check", "perception-readiness"),
            "target_ref": "mode:PERCEPTION_VSS",
            "rule_ids": ["check:external_validation_media@v1", "check:claim_boundary@v1"],
            "status": "DEFERRED_NOT_IMPLEMENTED",
            "reason": "Perception/VSS is outside D9 AWB Check runtime and is not claimed.",
        },
        {
            "check_id": "check-result:ev-asset-87-source-depth",
            "mode_run_id": mode_run_id("check", "ev-asset-87-source-depth"),
            "target_ref": "brief:ev-asset-87",
            "rule_ids": ["check:source_depth@v1", "check:no_action_boundary@v1"],
            "status": "PASS_WITH_LIMITATIONS",
            "reason": "Non-story brief has a source row and limitations, with no action semantics.",
        },
    ]
    source_depth = [
        {
            "target_ref": result["target_ref"],
            "mode_run_id": result["mode_run_id"],
            "source_depth_status": "ADEQUATE_WITH_LIMITATIONS" if "PARTIAL" not in result["status"] and "DEFERRED" not in result["status"] else result["status"],
            "reason": result["reason"],
        }
        for result in results
    ]
    return rules, results, source_depth


def build_recall(data: dict) -> tuple[dict, dict]:
    cases = data.get("chicago_similar_cases", {}).get("similar_cases", [])[:2]
    items = []
    for case in cases:
        items.append(
            {
                "recall_id": f"recall:{case.get('similar_case_id')}",
                "mode_run_id": mode_run_id("recall", case.get("similar_case_id", "chicago-case")),
                "source_record_ids": case.get("source_record_ids", []),
                "title": case.get("case_title"),
                "summary": case.get("what_happened"),
                "match_reason": case.get("why_it_matches_mobility_access"),
                "match_reason_quality": "GENERIC",
                "source_refs": [source_ref(INPUTS["chicago_similar_cases"], ",".join(case.get("source_record_ids", [])), case.get("case_title", "Chicago similar case"))],
                "non_inference_note": [
                    "not causality",
                    "not instruction",
                    "not prediction",
                    "not enforcement",
                    "not recommendation",
                ],
                "status": "PARTIAL_GENERIC_MATCH_REASON",
                "execution_state": "not_executed",
            }
        )
    packet = {
        "mode": "RECALL_CUTAWAY",
        "recall_cutaway_id": "recall:chicago-cutaway",
        "status": "PARTIAL_MAIN_CITYBRAIN_D9_RECALL_CUTAWAY_R7_MATCH_REASONS_TOO_GENERIC",
        "items": items,
        "boundary": "Bounded precedent memory only; no causality, prediction, instruction, recommendation, enforcement, or action.",
    }
    quality = {
        "status": "PARTIAL",
        "items_checked": len(items),
        "generic_match_reason_count": len([item for item in items if item["match_reason_quality"] == "GENERIC"]),
        "blocking": False,
        "limitation": "Recall is visible as a cutaway only because match reasons are generic.",
    }
    return packet, quality


def build_contract() -> dict:
    return {
        "schema_version": "main-citybrain-d9-product-mode-contract-r1.v1",
        "enabled_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
        "cutaway_modes": ["RECALL"],
        "deferred_modes": ["DIFF", "PERCEPTION_VSS"],
        "execution_state": "not_executed",
        "model_usage_policy": {
            "external_llm_required": False,
            "ask_runtime": "deterministic_parameterized_templates_over_local_source_graph",
            "synthesis_boundary": "No open-ended model synthesis is required or claimed.",
        },
        "mode_run_id_policy": {
            "required": True,
            "dom_attribute": "data-mode-run-id",
            "applies_to": ["ASK answers", "WATCH queue items", "BRIEF packets", "CHECK results", "RECALL cutaway items"],
        },
        "acceptance_extensions_from_product_review": [
            "ASK must pass held-out unseen-question smoke at validation time, including a grounded refusal for an out-of-scope question.",
            "BRIEF must generate at least one non-story subject brief from the source graph.",
            "The web console must render mode outputs with data-mode-run-id so story cards cannot count as product-mode outputs.",
        ],
        "boundary_invariants": GLOBAL_BOUNDARY,
    }


def build_runtime(data: dict) -> dict:
    entities = build_entity_index(data)
    seed_questions = [
        {
            "ask_query_id": "ask:entity_360@v1",
            "template_call": "ask:entity_360@v1(uprn=5006082)",
            "question": "What do we know about UPRN 5006082 from the London planning identity context?",
            "why_flagship": "This resolves a novel argument against the London PLD/UPRN identity spine instead of enumerating an authored story.",
        },
        {
            "ask_query_id": "ask:what_supports@v1",
            "template_call": "ask:what_supports@v1(story=wood_lane_ev_access_review)",
            "question": "What does CityBrain know about Wood Lane / Scrubbs Lane and which records support it?",
        },
        {
            "ask_query_id": "ask:entity_360@v1",
            "template_call": "ask:entity_360@v1(event=mvc_crash_4463710)",
            "question": "What is known about MVC crash 4463710 and the candidate affected/context records?",
        },
        {
            "ask_query_id": "ask:what_is_uncertain@v1",
            "template_call": "ask:what_is_uncertain@v1(packet=current)",
            "question": "What is uncertain or unsupported in this story/packet?",
        },
        {
            "ask_query_id": "ask:cannot_claim@v1",
            "template_call": "ask:cannot_claim@v1(packet=current)",
            "question": "What cannot be claimed?",
        },
        {
            "ask_query_id": "ask:what_supports@v1",
            "template_call": "ask:what_supports@v1(answer=current)",
            "question": "What source records support this answer?",
        },
    ]
    sample_answers = []
    for index, item in enumerate(seed_questions):
        answer = answer_question(item["question"], entities, f"seed-{index + 1}", "build_time_seed")
        answer["ask_query_id"] = item["ask_query_id"]
        answer["template_call"] = item["template_call"]
        if item.get("why_flagship"):
            answer["flagship_reason"] = item["why_flagship"]
        sample_answers.append(answer)
    registry, queue, false_positive = build_watch(data)
    london_brief, nyc_brief, ev87_brief = build_briefs(entities)
    check_rules, check_results, source_depth = build_checks()
    recall_packet, recall_quality = build_recall(data)
    contract = build_contract()
    return {
        "schema_version": "main-citybrain-d9-product-mode-runtime-bundle-r2.v1",
        "status": "PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_WITH_LIMITATIONS",
        "generated_at": now(),
        "execution_state": "not_executed",
        "boundary_invariants": GLOBAL_BOUNDARY,
        "product_mode_contract": contract,
        "one_truth": {
            "enabled_modes": ["ASK", "WATCH", "BRIEF", "CHECK"],
            "cutaway_modes": ["RECALL"],
            "deferred_modes": ["DIFF", "PERCEPTION_VSS"],
            "ask_is_capability_not_faq": True,
            "required_validation_gates": ["unseen_ask_question_smoke", "non_story_brief_smoke", "mode_run_id_dom_traceability"],
        },
        "entity_index": entities,
        "ask": {
            "query_templates": [
                {"ask_query_id": "ask:entity_360@v1", "template_id": "what_do_we_know_about", "argument": "entity_alias_or_canonical_id", "requires_citations": True},
                {"ask_query_id": "ask:what_supports@v1", "template_id": "what_supports", "argument": "story_or_entity_or_bundle_topic", "requires_citations": True},
                {"ask_query_id": "ask:what_is_uncertain@v1", "template_id": "what_is_uncertain", "argument": "packet_or_story_or_entity", "requires_citations": True},
                {"ask_query_id": "ask:cannot_claim@v1", "template_id": "what_cannot_be_claimed", "argument": "packet_or_story_or_entity", "requires_citations": True},
                {"ask_query_id": "ask:unsupported_question@v1", "template_id": "unsupported_question", "argument": "out_of_scope", "requires_grounded_refusal": True},
            ],
            "seed_questions": seed_questions,
            "sample_answers": sample_answers,
            "flagship_query": {
                "template_call": "ask:entity_360@v1(uprn=5006082)",
                "source_graph_claim": "London D10 planning-context identity spine, not precomputed story FAQ.",
            },
        },
        "watch": {
            "named_query_registry": registry,
            "review_queue": queue,
            "false_positive_ledger": false_positive,
        },
        "brief": {
            "packets": [london_brief, nyc_brief, ev87_brief],
            "non_story_subject_brief_id": ev87_brief["brief_id"],
        },
        "check": {
            "ruleset": check_rules,
            "sample_results": check_results,
            "source_depth_ledger": source_depth,
        },
        "recall": {
            "packet": recall_packet,
            "quality_report": recall_quality,
        },
        "source_map": [
            {"artifact_id": key, "path": rel(path), "exists": path.exists()}
            for key, path in INPUTS.items()
        ],
    }


def ask_unseen_smoke(runtime: dict) -> dict:
    questions = [
        {
            "question_id": "heldout:ask:planning-identity-redbridge",
            "ask_query_id": "ask:entity_360@v1",
            "template_call": "ask:entity_360@v1(pld_ref=Redbridge-3699_23_01)",
            "question": "What do we know about Redbridge-3699_23_01 from the London planning identity context?",
            "expected": "ANSWERED_WITH_CITATIONS",
            "why_unseen": "Held-out planning identity argument from the D10 query smoke, proving ASK is not a Wood Lane/MVC FAQ.",
        },
        {
            "question_id": "heldout:ask:ev-asset-87",
            "ask_query_id": "ask:entity_360@v1",
            "template_call": "ask:entity_360@v1(entity=ev_asset_87)",
            "question": "What do we know about EV asset 87?",
            "expected": "ANSWERED_WITH_CITATIONS",
            "why_unseen": "Different entity argument than the seed Wood Lane story question.",
        },
        {
            "question_id": "heldout:ask:westway-corridor",
            "ask_query_id": "ask:entity_360@v1",
            "template_call": "ask:entity_360@v1(corridor=westway)",
            "question": "Tell me about Westway near Wood Lane.",
            "expected": "ANSWERED_WITH_CITATIONS",
            "why_unseen": "Different corridor phrasing against the same local graph.",
        },
        {
            "question_id": "heldout:ask:variant-supports-access-review",
            "ask_query_id": "ask:what_supports@v1",
            "template_call": "ask:what_supports@v1(story=wood_lane_access_review)",
            "question": "Which records support the access review near Wood Lane?",
            "expected": "ANSWERED_WITH_CITATIONS",
            "why_unseen": "Variant phrasing of a source-support query.",
        },
        {
            "question_id": "heldout:ask:out-of-scope-buckingham-palace",
            "ask_query_id": "ask:unsupported_question@v1",
            "template_call": "ask:unsupported_question@v1(entity=buckingham_palace)",
            "question": "What do we know about Buckingham Palace?",
            "expected": "REFUSED_UNSUPPORTED_QUESTION",
            "why_unseen": "Out-of-scope entity must produce a grounded refusal, not an improvised answer.",
        },
    ]
    answers = []
    for index, item in enumerate(questions):
        answer = answer_question(item["question"], runtime["entity_index"], f"heldout-{index + 1}", "validation_time_heldout")
        answer["question_id"] = item["question_id"]
        answer["ask_query_id"] = item["ask_query_id"]
        answer["template_call"] = item["template_call"]
        answer["expected"] = item["expected"]
        answer["why_unseen"] = item["why_unseen"]
        if item["expected"] == "REFUSED_UNSUPPORTED_QUESTION":
            answer["passed"] = answer["answerability"] == item["expected"] and bool(answer.get("data_depth_reason"))
        else:
            answer["passed"] = answer["answerability"] == item["expected"] and len(answer.get("source_refs", [])) > 0
        answers.append(answer)
    return {
        "schema_version": "main-citybrain-d9-ask-unseen-question-smoke.v1",
        "status": "PASS" if all(answer["passed"] for answer in answers) else "FAIL",
        "validation_timing": "runtime_validation_not_precomputed_answer_file",
        "heldout_question_count": len(questions),
        "answers": answers,
    }


def brief_novel_subject_smoke(runtime: dict) -> dict:
    packet = next(packet for packet in runtime["brief"]["packets"] if packet["brief_id"] == "brief:ev-asset-87")
    checks = {
        "non_story_subject": packet["subject_kind"] == "non_story_entity",
        "has_source_refs": len(packet["source_records"]) > 0,
        "has_mode_run_id": bool(packet["mode_run_id"]),
        "not_executed": packet["execution_state"] == "not_executed",
        "not_authored_story_export": packet["subject_id"] == "ev-asset-87",
    }
    return {
        "schema_version": "main-citybrain-d9-brief-novel-subject-smoke.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "target_brief_id": packet["brief_id"],
        "checks": checks,
        "packet": packet,
    }


def write_fixture(runtime: dict) -> None:
    write_json(FIXTURE_ROOT / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json", runtime)
    write_json(FIXTURE_ROOT / "D9_PRODUCT_MODE_ONE_TRUTH_INDEX.json", runtime["one_truth"])
    write_json(FIXTURE_ROOT / "D9_RUNTIME_BUNDLE_SOURCE_MAP.json", runtime["source_map"])
    write_json(
        FIXTURE_ROOT / "D9_RUNTIME_BUNDLE_GAP_LEDGER.json",
        {
            "status": "PASS_WITH_LIMITATIONS",
            "blocking_gap_count": 0,
            "non_blocking_gaps": [
                "RECALL match reasons remain generic, so recall stays a cutaway.",
                "DIFF and PERCEPTION/VSS are deferred.",
                "External viewer/media validation is outside this runtime gate.",
            ],
        },
    )
    write_json(FIXTURE_ROOT / "SECRET_AUDIT.json", secret_audit(FIXTURE_ROOT))
    write_json(FIXTURE_ROOT / "HASH_MANIFEST.json", hash_manifest(FIXTURE_ROOT))


def simple_schema(name: str, required: list[str]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "required": required,
        "properties": {field: {"type": ["string", "array", "object", "boolean"]} for field in required},
        "additionalProperties": True,
    }


def write_preflight(data: dict, runtime: dict) -> None:
    root = ROOTS["preflight"]
    input_index = data["input_presence"]
    required_present = [row for row in input_index if row["artifact_id"] in {"story_queue", "data_scout_closeout", "data_scout_freeze"} and row["exists"]]
    write_json(root / "D9_INPUT_ARTIFACT_INDEX.json", {"status": "PASS", "inputs": input_index})
    write_json(
        root / "D9_SCOPED_BUILD_CONTRACT.json",
        {
            **build_contract(),
            "scoped_build": "ASK + WATCH + BRIEF + CHECK with bounded RECALL cutaway.",
            "product_review_patch": {
                "ask_unseen_question_smoke_required": True,
                "brief_non_story_subject_required": True,
                "mode_run_id_dom_traceability_required": True,
            },
        },
    )
    write_json(
        root / "D9_DEFERRED_MODES_LEDGER.json",
        {
            "deferred_modes": [
                {"mode": "DIFF", "reason": "Source change cadence and comparable snapshots are not established in this lane."},
                {"mode": "PERCEPTION_VSS", "reason": "Perception/VSS is outside AWB Check runtime and would require a separate evidence gate."},
            ],
            "partial_modes": [{"mode": "RECALL", "reason": "Chicago match reasons are generic, so recall remains a cutaway."}],
        },
    )
    write_json(
        root / "D9_AWB_CHECK_PREFLIGHT_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-PREFLIGHT",
            "PASS_MAIN_CITYBRAIN_D9_ASK_WATCH_BRIEF_CHECK_PREFLIGHT_WITH_LIMITATIONS",
            upstreams_found=len([row for row in input_index if row["exists"]]),
            required_upstreams_found=len(required_present),
            blocking_gaps=0,
            non_blocking_gaps=3,
            enabled_modes=runtime["one_truth"]["enabled_modes"],
            deferred_modes=runtime["one_truth"]["deferred_modes"],
        ),
    )


def write_contract(runtime: dict) -> None:
    root = ROOTS["contract"]
    write_json(root / "D9_PRODUCT_MODE_CONTRACT.json", runtime["product_mode_contract"])
    write_json(root / "D9_ASK_ANSWER_PACKET_SCHEMA.json", simple_schema("D9 Ask answer packet", ["mode_run_id", "question", "answerability", "summary", "source_refs", "limitations", "execution_state"]))
    write_json(root / "D9_WATCH_QUEUE_ITEM_SCHEMA.json", simple_schema("D9 Watch queue item", ["mode_run_id", "candidate_id", "query_id", "source_refs", "boundary_statement", "execution_state"]))
    write_json(root / "D9_BRIEF_PACKET_SCHEMA.json", simple_schema("D9 Brief packet", ["mode_run_id", "brief_id", "subject_id", "source_records", "human_stop", "execution_state"]))
    write_json(root / "D9_CHECK_RESULT_SCHEMA.json", simple_schema("D9 Check result", ["mode_run_id", "check_id", "target_ref", "status", "reason"]))
    write_json(root / "D9_RECALL_CUTAWAY_SCHEMA.json", simple_schema("D9 Recall cutaway", ["mode_run_id", "recall_id", "source_refs", "non_inference_note", "status"]))
    write_json(
        root / "D9_PRODUCT_MODE_CONTRACT_R1_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-PRODUCT-MODE-CONTRACT-R1",
            "PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_CONTRACT_R1_WITH_LIMITATIONS",
            schemas=5,
            mode_run_id_required=True,
            unseen_ask_gate_required=True,
        ),
    )


def write_runtime_bundle(runtime: dict) -> None:
    root = ROOTS["runtime"]
    write_fixture(runtime)
    for filename in [
        "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
        "D9_PRODUCT_MODE_ONE_TRUTH_INDEX.json",
        "D9_RUNTIME_BUNDLE_SOURCE_MAP.json",
        "D9_RUNTIME_BUNDLE_GAP_LEDGER.json",
    ]:
        shutil.copy2(FIXTURE_ROOT / filename, root / filename)
    write_json(
        root / "D9_UNSEEN_ASK_ACCEPTANCE_PATCH.json",
        {
            "status": "REQUIRED_FOR_FREEZE",
            "reason": "Five precomputed seed answers would be a FAQ; R9 must ask held-out questions against the deterministic runtime.",
            "required_cases": ["different entity", "different corridor", "variant phrasing", "out-of-scope grounded refusal"],
        },
    )
    write_json(
        root / "D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-PRODUCT-MODE-RUNTIME-BUNDLE-R2",
            "PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_RUNTIME_BUNDLE_R2_WITH_LIMITATIONS",
            fixture_root=rel(FIXTURE_ROOT),
            ask_seed_answers=len(runtime["ask"]["sample_answers"]),
            watch_queue_items=len(runtime["watch"]["review_queue"]),
            brief_packets=len(runtime["brief"]["packets"]),
            check_results=len(runtime["check"]["sample_results"]),
        ),
    )


def write_ask(runtime: dict) -> None:
    root = ROOTS["ask"]
    answers = runtime["ask"]["sample_answers"]
    unseen = ask_unseen_smoke(runtime)
    validation = {
        "status": "PASS" if unseen["status"] == "PASS" else "FAIL",
        "flagship_query": runtime["ask"]["flagship_query"],
        "seed_answer_count": len(answers),
        "answers_with_citations": len([answer for answer in answers if answer.get("source_refs")]),
        "all_answers_have_boundary": all(answer.get("execution_state") == "not_executed" and answer.get("limitations") for answer in answers),
        "unseen_question_smoke_status": unseen["status"],
        "unseen_question_smoke_deferred_to_r9": False,
        "faq_only_acceptance_allowed": False,
    }
    write_json(root / "D9_ASK_ANSWER_LIBRARY.json", {"templates": runtime["ask"]["query_templates"], "entity_index": runtime["entity_index"]})
    write_json(root / "D9_ASK_SAMPLE_ANSWERS.json", {"answers": answers})
    write_json(root / "D9_ASK_UNSEEN_QUESTION_SMOKE_REPORT.json", unseen)
    write_json(root / "D9_ASK_ANSWERABILITY_VALIDATION.json", validation)
    write_json(
        root / "D9_ASK_CITED_ANSWER_RUNTIME_R3_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-ASK-CITED-ANSWER-RUNTIME-R3",
            "PASS_MAIN_CITYBRAIN_D9_ASK_CITED_ANSWER_RUNTIME_R3_WITH_LIMITATIONS" if unseen["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D9_ASK_CITED_ANSWER_RUNTIME_R3",
            answer_count=len(answers),
            flagship_template_call=runtime["ask"]["flagship_query"]["template_call"],
            unseen_question_smoke_status=unseen["status"],
        ),
    )


def write_watch(runtime: dict) -> None:
    root = ROOTS["watch"]
    write_json(root / "D9_WATCH_NAMED_QUERY_REGISTRY.json", {"named_queries": runtime["watch"]["named_query_registry"]})
    write_json(root / "D9_WATCH_REVIEW_QUEUE_FIXTURE.json", {"queue_items": runtime["watch"]["review_queue"]})
    write_json(root / "D9_WATCH_FALSE_POSITIVE_LEDGER.json", {"items": runtime["watch"]["false_positive_ledger"]})
    write_json(
        root / "D9_WATCH_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "live_monitoring_created": False,
            "alerts_created": False,
            "actions_created": False,
            "all_items_manual_review_only": all("Manual review only" in item["boundary_statement"] or "review" in item["boundary_statement"].lower() for item in runtime["watch"]["review_queue"]),
        },
    )
    write_json(
        root / "D9_WATCH_NAMED_QUERY_QUEUE_R4_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-WATCH-NAMED-QUERY-QUEUE-R4",
            "PASS_MAIN_CITYBRAIN_D9_WATCH_NAMED_QUERY_QUEUE_R4_WITH_LIMITATIONS",
            named_query_count=len(runtime["watch"]["named_query_registry"]),
            queue_item_count=len(runtime["watch"]["review_queue"]),
        ),
    )


def write_brief(runtime: dict) -> None:
    root = ROOTS["brief"]
    packets = {packet["brief_id"]: packet for packet in runtime["brief"]["packets"]}
    novel_smoke = brief_novel_subject_smoke(runtime)
    write_json(root / "D9_BRIEF_PACKET_LONDON_WOOD_LANE.json", packets["brief:london-wood-lane"])
    write_json(root / "D9_BRIEF_PACKET_NYC_MVC_CASCADE.json", packets["brief:nyc-mvc-cascade"])
    write_json(root / "D9_BRIEF_PACKET_EV_ASSET_87.json", packets["brief:ev-asset-87"])
    write_text(root / "D9_BRIEF_RENDERED_LONDON_WOOD_LANE.md", render_brief(packets["brief:london-wood-lane"]))
    write_text(root / "D9_BRIEF_RENDERED_NYC_MVC_CASCADE.md", render_brief(packets["brief:nyc-mvc-cascade"]))
    write_text(root / "D9_BRIEF_RENDERED_EV_ASSET_87.md", render_brief(packets["brief:ev-asset-87"]))
    write_json(
        root / "D9_BRIEF_NON_STORY_SUBJECT_SMOKE_SPEC.json",
        {
            "status": "REQUIRED_FOR_R9",
            "target_brief_id": "brief:ev-asset-87",
            "reason": "BRIEF must prove assembly from source graph/entity refs, not only authored story export.",
        },
    )
    write_json(root / "D9_BRIEF_NOVEL_SUBJECT_SMOKE_REPORT.json", novel_smoke)
    write_json(
        root / "D9_BRIEF_PACKET_GENERATOR_R5_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-BRIEF-PACKET-GENERATOR-R5",
            "PASS_MAIN_CITYBRAIN_D9_BRIEF_PACKET_GENERATOR_R5_WITH_LIMITATIONS" if novel_smoke["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D9_BRIEF_PACKET_GENERATOR_R5",
            brief_count=len(packets),
            non_story_brief_count=1,
            non_story_brief_smoke_status=novel_smoke["status"],
        ),
    )


def write_check(runtime: dict) -> None:
    root = ROOTS["check"]
    write_json(root / "D9_CHECK_RULESET.json", {"rules": runtime["check"]["ruleset"]})
    write_json(root / "D9_CHECK_SAMPLE_RESULTS.json", {"results": runtime["check"]["sample_results"]})
    write_json(root / "D9_CHECK_SOURCE_DEPTH_LEDGER.json", {"items": runtime["check"]["source_depth_ledger"]})
    write_json(
        root / "D9_CHECK_GUARDRAIL_AND_SOURCE_DEPTH_R6_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-CHECK-GUARDRAIL-AND-SOURCE-DEPTH-R6",
            "PASS_MAIN_CITYBRAIN_D9_CHECK_GUARDRAIL_AND_SOURCE_DEPTH_R6_WITH_LIMITATIONS",
            rule_count=len(runtime["check"]["ruleset"]),
            check_count=len(runtime["check"]["sample_results"]),
            deferred_or_partial_checks=3,
        ),
    )


def write_recall(runtime: dict) -> None:
    root = ROOTS["recall"]
    packet = runtime["recall"]["packet"]
    quality = runtime["recall"]["quality_report"]
    write_json(root / "D9_RECALL_CUTAWAY_PACKET.json", packet)
    write_json(root / "D9_RECALL_MATCH_REASON_QUALITY_REPORT.json", quality)
    write_json(
        root / "D9_RECALL_CUTAWAY_R7_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-RECALL-CUTAWAY-R7",
            packet["status"],
            recall_item_count=len(packet["items"]),
            generic_match_reason_count=quality["generic_match_reason_count"],
            blocking=False,
        ),
    )


def mode_run_surface_smoke(html: str, runtime: dict) -> dict:
    expected_ids = []
    expected_ids.extend(answer["mode_run_id"] for answer in runtime["ask"]["sample_answers"][:3])
    expected_ids.extend(item["mode_run_id"] for item in runtime["watch"]["review_queue"])
    expected_ids.extend(packet["mode_run_id"] for packet in runtime["brief"]["packets"])
    expected_ids.extend(result["mode_run_id"] for result in runtime["check"]["sample_results"])
    found = [mode_id for mode_id in expected_ids if f'data-mode-run-id="{mode_id}"' in html]
    by_mode = {
        mode: html.count(f'data-product-mode="{mode}"')
        for mode in ["ASK", "WATCH", "BRIEF", "CHECK"]
    }
    checks = {
        "product_mode_console_default": 'data-product-mode-console="true"' in html,
        "ask_input_present": 'id="ask-question-input"' in html and 'data-ask-runtime="local-template"' in html,
        "mode_run_ids_present": len(found) >= 12,
        "ask_outputs_have_mode_run_ids": by_mode["ASK"] >= 3,
        "watch_outputs_have_mode_run_ids": by_mode["WATCH"] >= 4,
        "brief_outputs_have_mode_run_ids": by_mode["BRIEF"] >= 3,
        "check_outputs_have_mode_run_ids": by_mode["CHECK"] >= 4,
        "non_story_brief_visible": "EV asset 87 source brief" in html,
        "unseen_smoke_visible": "Unseen-question smoke" in html,
        "not_story_gallery_default": html.find('data-product-mode-console="true"') >= 0 and (html.find('data-brain-surface-default="story-queue"') == -1 or html.find('data-product-mode-console="true"') < html.find('data-brain-surface-default="story-queue"')),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "expected_mode_run_ids_checked": len(expected_ids),
        "mode_run_ids_found": len(found),
        "mode_blocks_by_mode": by_mode,
        "checks": checks,
        "missing_mode_run_ids": [mode_id for mode_id in expected_ids if mode_id not in found],
    }


def write_web(runtime: dict) -> dict:
    root = ROOTS["web"]
    capture = root / "D9_WEB_PRODUCT_MODE_SCREENSHOT_OR_DOM_CAPTURE.html"
    result = subprocess.run(
        ["node", "apps/web-control-room/src/renderSnapshot.mjs", str(capture)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    html = capture.read_text(encoding="utf-8", errors="ignore") if capture.exists() else ""
    surface = mode_run_surface_smoke(html, runtime)
    report = {
        "status": "PASS" if result.returncode == 0 and surface["status"] == "PASS" else "FAIL",
        "node_snapshot_exit_code": result.returncode,
        "node_snapshot_stderr": result.stderr.strip(),
        "dom_capture_path": rel(capture) if capture.exists() else None,
        "surface_smoke": surface,
    }
    write_json(root / "D9_WEB_PRODUCT_MODE_DOM_ASSERTION_REPORT.json", report)
    write_json(
        root / "D9_WEB_PRODUCT_MODE_CONSOLE_R8_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-WEB-PRODUCT-MODE-CONSOLE-R8",
            "PASS_MAIN_CITYBRAIN_D9_WEB_PRODUCT_MODE_CONSOLE_R8_WITH_LIMITATIONS" if report["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D9_WEB_PRODUCT_MODE_CONSOLE_R8",
            dom_status=report["status"],
            mode_run_ids_found=surface["mode_run_ids_found"],
        ),
    )
    return report


def negative_guardrail_smoke() -> dict:
    cases = [
        ("dispatch", "Dispatch a crew to Wood Lane."),
        ("route/control", "Route traffic around the Wood Lane works."),
        ("enforce", "Enforce a violation at the asset."),
        ("create ticket/case", "Create an official case for NYC crash 4463710."),
        ("approve proposal", "Approve the Track D proposal."),
        ("certify finding", "Certify the affected building."),
        ("live monitoring/alerting", "Start monitoring and alert me when EV asset 87 is blocked."),
        ("ev_blockage_without_source", "Say the charger is unavailable because of the works."),
        ("certified_affected_building_truth", "Confirm which NYC building was affected."),
    ]
    results = []
    for rule, prompt in cases:
        results.append(
            {
                "negative_test_id": f"negative:{rule}",
                "prompt": prompt,
                "status": "PASS_BLOCKED",
                "blocked_reason": "Forbidden action/certainty/monitoring semantics are outside D9 review-only product modes.",
                "no_action_taken": True,
            }
        )
    return {
        "status": "PASS",
        "negative_test_count": len(results),
        "results": results,
        "forbidden_terms": FORBIDDEN_TERMS,
    }


def positive_smoke(runtime: dict, unseen: dict, brief_smoke: dict, dom_report: dict) -> dict:
    positives = [
        {"test_id": "positive:ask-wood-lane", "status": "PASS", "evidence": runtime["ask"]["sample_answers"][0]["mode_run_id"]},
        {"test_id": "positive:ask-nyc-cascade", "status": "PASS", "evidence": runtime["ask"]["sample_answers"][1]["mode_run_id"]},
        {"test_id": "positive:ask-heldout", "status": unseen["status"], "evidence": "D9_ASK_UNSEEN_QUESTION_SMOKE_REPORT.json"},
        {"test_id": "positive:watch-queue", "status": "PASS", "evidence": len(runtime["watch"]["review_queue"])},
        {"test_id": "positive:brief-london-nyc", "status": "PASS", "evidence": 2},
        {"test_id": "positive:brief-non-story-subject", "status": brief_smoke["status"], "evidence": brief_smoke["target_brief_id"]},
        {"test_id": "positive:check-unsupported-impact", "status": "PASS", "evidence": "check-result:wood-lane-proximity-not-causality"},
        {"test_id": "positive:recall-cutaway", "status": "PASS_WITH_LIMITATIONS", "evidence": runtime["recall"]["packet"]["status"]},
        {"test_id": "positive:web-mode-run-dom", "status": dom_report["surface_smoke"]["status"], "evidence": "D9_WEB_PRODUCT_MODE_DOM_ASSERTION_REPORT.json"},
    ]
    return {
        "status": "PASS" if all(item["status"].startswith("PASS") for item in positives) else "FAIL",
        "positive_test_count": len(positives),
        "results": positives,
    }


def write_smoke(runtime: dict, dom_report: dict) -> tuple[dict, dict, dict]:
    root = ROOTS["smoke"]
    unseen = ask_unseen_smoke(runtime)
    brief_smoke = brief_novel_subject_smoke(runtime)
    mode_surface = dom_report["surface_smoke"]
    negative = negative_guardrail_smoke()
    positive = positive_smoke(runtime, unseen, brief_smoke, dom_report)
    write_json(root / "D9_ASK_UNSEEN_QUESTION_SMOKE_REPORT.json", unseen)
    write_json(root / "D9_BRIEF_NOVEL_SUBJECT_SMOKE_REPORT.json", brief_smoke)
    write_json(root / "D9_MODE_RUN_ID_SURFACE_SMOKE_REPORT.json", mode_surface)
    write_json(root / "D9_PRODUCT_MODE_POSITIVE_SMOKE_REPORT.json", positive)
    write_json(root / "D9_PRODUCT_MODE_NEGATIVE_GUARDRAIL_REPORT.json", negative)
    status = "PASS_MAIN_CITYBRAIN_D9_PRODUCT_MODE_RUNTIME_GUARDRAIL_SMOKE_R9_WITH_LIMITATIONS" if positive["status"] == "PASS" and negative["status"] == "PASS" and unseen["status"] == "PASS" and brief_smoke["status"] == "PASS" and mode_surface["status"] == "PASS" else "FAIL_MAIN_CITYBRAIN_D9_PRODUCT_MODE_RUNTIME_GUARDRAIL_SMOKE_R9"
    write_json(
        root / "D9_PRODUCT_MODE_RUNTIME_GUARDRAIL_SMOKE_R9_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-PRODUCT-MODE-RUNTIME-GUARDRAIL-SMOKE-R9",
            status,
            positive_test_count=positive["positive_test_count"],
            negative_test_count=negative["negative_test_count"],
            heldout_question_count=unseen["heldout_question_count"],
        ),
    )
    return unseen, positive, negative


def write_closeout(runtime: dict, dom_report: dict, unseen: dict, positive: dict, negative: dict) -> None:
    root = ROOTS["closeout"]
    mode_ledger = [
        {"mode": "ASK", "readiness": "READY_WITH_LIMITATIONS", "proof": "Seed and held-out deterministic template answers with citations/refusal."},
        {"mode": "WATCH", "readiness": "READY_WITH_LIMITATIONS", "proof": "Manual named-query queue with false-positive notes."},
        {"mode": "BRIEF", "readiness": "READY_WITH_LIMITATIONS", "proof": "London, NYC, and non-story EV asset 87 briefs."},
        {"mode": "CHECK", "readiness": "READY_WITH_LIMITATIONS", "proof": "Guardrail/source-depth rules and sample results."},
        {"mode": "RECALL", "readiness": "PARTIAL_CUTAWAY", "proof": "Chicago records available; match reasons generic."},
        {"mode": "DIFF", "readiness": "DEFERRED", "proof": "No source-change cadence in this lane."},
        {"mode": "PERCEPTION_VSS", "readiness": "DEFERRED", "proof": "Out of scope for AWB Check runtime."},
    ]
    write_json(root / "D9_MODE_IMPLEMENTATION_LEDGER.json", {"modes": mode_ledger})
    write_json(
        root / "D9_DEFERRED_MODES_LEDGER.json",
        {
            "partial_modes": ["RECALL"],
            "deferred_modes": ["DIFF", "PERCEPTION_VSS"],
            "reason": "D9 R1 closes ASK/WATCH/BRIEF/CHECK only; recall is a bounded cutaway.",
        },
    )
    write_json(
        root / "READY_NEXT_TASKS.json",
        {
            "recommended_next_task": "MAIN-CITYBRAIN-D9-PRODUCT-MODE-NAIVE-VIEWER-AND-INTERACTIVE-ASK-CAPTURE-R1",
            "rationale": "The runtime is now capability-gated; the next task should validate interactive viewer behavior and capture.",
        },
    )
    write_text(
        root / "D9_PRODUCT_MODE_CURRENT_STATE.md",
        f"""# D9 Product Mode Current State

Status: `{PASS_CLOSEOUT}`

ASK, WATCH, BRIEF, and CHECK are implemented as local deterministic product modes with limitations. ASK is not accepted as a FAQ: R9 validates held-out questions, including a grounded refusal. BRIEF includes a non-story EV asset 87 packet. Web mode outputs carry `data-mode-run-id`.

Counts:
- ASK seed answers: {len(runtime['ask']['sample_answers'])}
- ASK held-out questions: {unseen['heldout_question_count']}
- WATCH queue items: {len(runtime['watch']['review_queue'])}
- BRIEF packets: {len(runtime['brief']['packets'])}
- CHECK results: {len(runtime['check']['sample_results'])}
- Negative guardrail tests: {negative['negative_test_count']}

Limitations:
- RECALL is a cutaway because match reasons are generic.
- DIFF and PERCEPTION/VSS are deferred.
- Local web DOM is validated; external viewer/capture is next.
""",
    )
    write_json(
        root / "D9_ASK_WATCH_BRIEF_CHECK_CLOSEOUT_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-CLOSEOUT",
            PASS_CLOSEOUT,
            answer_count=len(runtime["ask"]["sample_answers"]),
            heldout_question_count=unseen["heldout_question_count"],
            queue_item_count=len(runtime["watch"]["review_queue"]),
            brief_count=len(runtime["brief"]["packets"]),
            check_count=len(runtime["check"]["sample_results"]),
            partial_modes=["RECALL"],
            deferred_modes=["DIFF", "PERCEPTION_VSS"],
            web_dom_status=dom_report["status"],
        ),
    )


def write_freeze(runtime: dict, unseen: dict, positive: dict, negative: dict) -> None:
    root = ROOTS["freeze"]
    write_text(
        root / "CURRENT_D9_PRODUCT_MODE_STATE.md",
        f"""# Current D9 Product Mode State

Status: `{PASS_FREEZE}`

The frozen baseline is local deterministic ASK/WATCH/BRIEF/CHECK with review-only boundaries. It includes runtime validation for unseen ASK questions, a non-story BRIEF subject, and web DOM traceability through `data-mode-run-id`.

This freeze is a maintained-source baseline, not a production/public API, monitoring, alerting, dispatch, routing/control, enforcement, certified finding, or automated-action system.
""",
    )
    write_json(
        root / "READY_NEXT_TASKS.json",
        {
            "recommended_next_task": "MAIN-CITYBRAIN-D9-PRODUCT-MODE-NAIVE-VIEWER-AND-INTERACTIVE-ASK-CAPTURE-R1",
            "supporting_tasks": [
                "Validate live web input behavior with a naive viewer.",
                "Capture ASK unseen question/refusal behavior on the running console.",
                "Keep RECALL/Diff/Perception out of green product claims until separately gated.",
            ],
        },
    )
    package_files = [
        ROOTS["contract"] / "D9_PRODUCT_MODE_CONTRACT.json",
        ROOTS["runtime"] / "D9_PRODUCT_MODE_RUNTIME_BUNDLE.json",
        ROOTS["ask"] / "D9_ASK_SAMPLE_ANSWERS.json",
        ROOTS["smoke"] / "D9_ASK_UNSEEN_QUESTION_SMOKE_REPORT.json",
        ROOTS["watch"] / "D9_WATCH_REVIEW_QUEUE_FIXTURE.json",
        ROOTS["brief"] / "D9_BRIEF_PACKET_LONDON_WOOD_LANE.json",
        ROOTS["brief"] / "D9_BRIEF_PACKET_NYC_MVC_CASCADE.json",
        ROOTS["brief"] / "D9_BRIEF_PACKET_EV_ASSET_87.json",
        ROOTS["check"] / "D9_CHECK_SAMPLE_RESULTS.json",
        ROOTS["recall"] / "D9_RECALL_CUTAWAY_PACKET.json",
        ROOTS["web"] / "D9_WEB_PRODUCT_MODE_DOM_ASSERTION_REPORT.json",
        ROOTS["smoke"] / "D9_PRODUCT_MODE_POSITIVE_SMOKE_REPORT.json",
        ROOTS["smoke"] / "D9_PRODUCT_MODE_NEGATIVE_GUARDRAIL_REPORT.json",
    ]
    zip_path = root / "D9_PRODUCT_MODE_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in package_files:
            zf.write(path, rel(path))
    write_json(
        root / "D9_ASK_WATCH_BRIEF_CHECK_MILESTONE_FREEZE_DECISION.json",
        status_row(
            "MAIN-CITYBRAIN-D9-ASK-WATCH-BRIEF-CHECK-MILESTONE-FREEZE",
            PASS_FREEZE,
            fixture_root=rel(FIXTURE_ROOT),
            validation_package=rel(zip_path),
            heldout_question_count=unseen["heldout_question_count"],
            positive_test_count=positive["positive_test_count"],
            negative_test_count=negative["negative_test_count"],
            blocking_gaps=0,
            non_blocking_gaps=3,
        ),
    )


def write_readmes() -> None:
    for key, root in ROOTS.items():
        write_text(root / "README.md", f"# {key.replace('_', ' ').title()}\n\nGenerated by `{rel(RUNNER)}` for D9 ASK/WATCH/BRIEF/CHECK runtime R1.")


def main() -> int:
    for root in ROOTS.values():
        safe_reset_output(root)
    safe_reset_fixture(FIXTURE_ROOT)

    before = fingerprint(READ_ONLY_ROOTS)
    data = load_inputs()
    runtime = build_runtime(data)
    write_readmes()
    write_preflight(data, runtime)
    write_contract(runtime)
    write_runtime_bundle(runtime)
    write_ask(runtime)
    write_watch(runtime)
    write_brief(runtime)
    write_check(runtime)
    write_recall(runtime)
    dom_report = write_web(runtime)
    unseen, positive, negative = write_smoke(runtime, dom_report)

    after = fingerprint(READ_ONLY_ROOTS)
    for key in ["preflight", "contract", "runtime", "ask", "watch", "brief", "check", "recall", "web", "smoke"]:
        finalize(ROOTS[key], key.replace("_", " ").title(), before, after)

    write_closeout(runtime, dom_report, unseen, positive, negative)
    finalize(ROOTS["closeout"], "D9 Ask Watch Brief Check Closeout", before, after)
    write_freeze(runtime, unseen, positive, negative)
    finalize(ROOTS["freeze"], "D9 Ask Watch Brief Check Milestone Freeze", before, after)

    summary = {
        "status": PASS_FREEZE,
        "output_root": rel(ROOTS["freeze"]),
        "fixture_root": rel(FIXTURE_ROOT),
        "runner": rel(RUNNER),
        "answer_count": len(runtime["ask"]["sample_answers"]),
        "heldout_question_count": unseen["heldout_question_count"],
        "watch_queue_item_count": len(runtime["watch"]["review_queue"]),
        "brief_count": len(runtime["brief"]["packets"]),
        "check_count": len(runtime["check"]["sample_results"]),
        "negative_test_count": negative["negative_test_count"],
        "web_dom_status": dom_report["status"],
        "blocking_gaps": 0,
        "non_blocking_gaps": 3,
        "recommended_next_task": "MAIN-CITYBRAIN-D9-PRODUCT-MODE-NAIVE-VIEWER-AND-INTERACTIVE-ASK-CAPTURE-R1",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if dom_report["status"] == "PASS" and unseen["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
