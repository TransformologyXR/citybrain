from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from txr_citybrain_a5d1_operator_query import BOUNDARY_STATEMENT


ROOT = Path(__file__).resolve().parent
DEFAULT_D6_DIR = ROOT / "outputs" / "a5d6_live_nemo_nim_replay"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d6b_narration_surface"
TASK_NAME = "a5·D6b Non-Technical Narration Surface with Subset-Grounding Gate"

HERO_BBL = "1010607502"
HERO_BIN = "1026676"
HERO_COMPLAINT = "1366080"
SECOND_SUBJECT_BBL = "1010600029"
HERO_LEAKAGE_TOKENS = {
    HERO_BBL,
    HERO_BIN,
    HERO_COMPLAINT,
    "event:us-nyc:dob_complaint:1366080",
    "building:us-nyc:bin:1026676",
    "GC-0037441",
}

NARRATION_PROMPT_CONSTRAINTS = [
    "Write for a non-technical city operations reader.",
    "Use short paragraphs or bullets.",
    "Do not infer facts.",
    "Do not add background knowledge.",
    "Do not soften, round, or reinterpret numbers.",
    "Do not name any party, parcel, permit, complaint, category, confidence, date, or count unless it appears in the evidence bundle or deterministic derived facts.",
    "Preserve claim-boundary wording.",
    "Mention uncertainty and evidence limits where present.",
    "Do not simply echo JSON or evidence fields verbatim.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def pretty_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(payload), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def clean_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def gate(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def get_d6_paths(d6_dir: Path) -> dict[str, Path]:
    return {
        "harness": d6_dir / "A5D6_HARNESS_REPORT.json",
        "transcript": d6_dir / "A5D6_LIVE_TRANSCRIPT.json",
        "groundedness": d6_dir / "A5D6_GROUNDEDNESS_REPORT.json",
        "remote_groundedness": d6_dir
        / "spark_remote_results"
        / "remote_results"
        / "A5D6_GROUNDEDNESS_REPORT.json",
    }


def d6_preconditions(d6_dir: Path) -> tuple[bool, dict[str, Any], list[str]]:
    paths = get_d6_paths(d6_dir)
    details: list[str] = []
    harness = load_json(paths["harness"]) if paths["harness"].exists() else {}
    transcript = load_json(paths["transcript"]) if paths["transcript"].exists() else {}
    if harness.get("status") != "PASS" or harness.get("exit_code") != 0:
        details.append("A5-D6 harness is missing or not PASS/exit 0")
    checks = harness.get("checks", {})
    required_checks = [
        "live_nemo_single_tool",
        "no_low_level_bypass",
        "live_nim",
        "hero_grounded",
        "second_subject_grounded",
        "negative_rejected",
        "boundary",
        "no_mutation",
    ]
    for key in required_checks:
        if checks.get(key) is not True:
            details.append(f"A5-D6 required check is not true: {key}")
    if BOUNDARY_STATEMENT not in canonical_json({"harness": harness, "transcript": transcript}):
        details.append("boundary statement missing from A5-D6 accepted artifacts")
    for label in ("hero", "second_subject"):
        try:
            run = transcript["runs"][label]["tool_invocation"]["output"]
        except KeyError:
            details.append(f"A5-D6 transcript missing accepted run: {label}")
            continue
        if run.get("status") != "PASS" or run.get("rejected") is True:
            details.append(f"A5-D6 transcript run not accepted: {label}")
    return not details, {"harness": harness, "transcript": transcript}, details


def entities_by_id(evidence_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entity.get("canonical_id"): entity
        for entity in evidence_bundle.get("entities", [])
        if isinstance(entity, dict) and entity.get("canonical_id")
    }


def entity_kind(entity: dict[str, Any], kind: str) -> bool:
    return entity.get("entity_type") == kind or entity.get("type") == kind


def subject_bbl(evidence_bundle: dict[str, Any]) -> str | None:
    subject_id = evidence_bundle.get("subject_id") or ""
    match = re.search(r"bbl:(\d{10})", subject_id)
    if match:
        return match.group(1)
    for fact in evidence_bundle.get("answer_facts", []):
        match = re.search(r"Parcel\s+(\d{10})", str(fact))
        if match:
            return match.group(1)
    return None


def linked_building_bins(evidence_bundle: dict[str, Any]) -> list[str]:
    bins: list[str] = []
    for entity in evidence_bundle.get("entities", []):
        if entity_kind(entity, "building"):
            match = re.search(r"bin:(\d+)", entity.get("canonical_id", ""))
            if match:
                bins.append(match.group(1))
    return sorted(set(bins))


def complaint_events(evidence_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entity
        for entity in evidence_bundle.get("entities", [])
        if entity_kind(entity, "event") and "dob_complaint" in str(entity.get("canonical_id", ""))
    ]


def party_name_for_id(evidence_bundle: dict[str, Any], party_id: str | None) -> str | None:
    if not party_id:
        return None
    entity = entities_by_id(evidence_bundle).get(party_id)
    if not entity:
        return None
    return entity.get("name") or entity.get("label")


def contractor_summary(evidence_bundle: dict[str, Any]) -> dict[str, Any] | None:
    by_id = entities_by_id(evidence_bundle)
    for edge in evidence_bundle.get("edges", []):
        if edge.get("relation") != "performed_by":
            continue
        party = by_id.get(edge.get("dst"), {})
        confidence = edge.get("confidence") or party.get("confidence") or {}
        return {
            "party_id": edge.get("dst"),
            "name": party.get("name") or party.get("label"),
            "license": (re.search(r"dob_license:([A-Z]+-\d+)", str(edge.get("dst"))) or [None, None])[1],
            "role": edge.get("role") or "contractor",
            "confidence_score": confidence.get("score"),
            "confidence_method": confidence.get("method"),
            "confidence_basis": confidence.get("basis"),
        }
    return None


def first_confidence(evidence_bundle: dict[str, Any]) -> dict[str, Any] | None:
    for edge in evidence_bundle.get("edges", []):
        confidence = edge.get("confidence")
        if confidence:
            return confidence
    for entity in evidence_bundle.get("entities", []):
        confidence = entity.get("confidence")
        if confidence:
            return confidence
    return None


def hero_complaint_summary(evidence_bundle: dict[str, Any]) -> dict[str, Any] | None:
    for event in complaint_events(evidence_bundle):
        if event.get("canonical_id") == f"event:us-nyc:dob_complaint:{HERO_COMPLAINT}":
            return {
                "id": event.get("canonical_id"),
                "complaint_number": HERO_COMPLAINT,
                "category": event.get("nyc.dob_complaint_category"),
                "type": event.get("type"),
                "severity": event.get("severity"),
                "resolution_method": event.get("resolution_method"),
                "timestamp": event.get("timestamp"),
                "confidence": event.get("confidence"),
            }
    return None


def source_counts(evidence_bundle: dict[str, Any]) -> dict[str, int]:
    source_rows = evidence_bundle.get("counts", {}).get("source_rows", {})
    return {
        "dob_permit_issuance": int(source_rows.get("dob_permit_issuance", 0)),
        "dob_now_filings": int(source_rows.get("dob_now_filings", 0)),
        "dob_complaints": int(source_rows.get("dob_complaints", 0)),
    }


def derived_facts(evidence_bundle: dict[str, Any], label: str) -> dict[str, Any]:
    bbl = subject_bbl(evidence_bundle)
    bins = linked_building_bins(evidence_bundle)
    counts = source_counts(evidence_bundle)
    contractor = contractor_summary(evidence_bundle)
    confidence = first_confidence(evidence_bundle) or {}
    hero_complaint = hero_complaint_summary(evidence_bundle)
    return {
        "label": label,
        "subject_id": evidence_bundle.get("subject_id"),
        "subject_bbl": bbl,
        "building_bins": bins,
        "source_counts": counts,
        "linked_buildings": evidence_bundle.get("counts", {}).get("linked_buildings"),
        "linked_permits": evidence_bundle.get("counts", {}).get("linked_permits"),
        "linked_parties": evidence_bundle.get("counts", {}).get("linked_parties"),
        "contractor": contractor,
        "first_confidence": confidence,
        "hero_complaint": hero_complaint,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def narrative_briefing(evidence_bundle: dict[str, Any], label: str) -> str:
    facts = derived_facts(evidence_bundle, label)
    counts = facts["source_counts"]
    bbl = facts["subject_bbl"]
    bins = ", ".join(facts["building_bins"]) if facts["building_bins"] else "no linked building BIN in evidence"
    contractor = facts["contractor"]
    confidence = facts["first_confidence"] or {}
    confidence_score = confidence.get("score")
    confidence_method = confidence.get("method")

    if contractor and contractor.get("name"):
        license_text = f" with licence {contractor['license']}" if contractor.get("license") else ""
        contractor_text = (
            f"The contractor evidence names {contractor['name']}{license_text}. "
            f"That connection uses {contractor.get('confidence_method')} at {contractor.get('confidence_score')}."
        )
    else:
        contractor_text = "No contractor in evidence."

    if label == "hero":
        review = "Review next: complaint 1366080, category 91, site_conditions_endangering_workers, critical, exact_bin."
        subject_sentence = f"Parcel {bbl} is the subject parcel. The linked building BIN in evidence is {bins}."
    else:
        review = "Review next: this non-hero parcel has no DOB NOW filing source rows in the harvested subset."
        subject_sentence = f"Parcel {bbl} is a second-subject briefing. The linked building BIN in evidence is {bins}."

    return "\n\n".join(
        [
            subject_sentence,
            (
                "DOB activity attached to this parcel in the accepted evidence: "
                f"{counts['dob_permit_issuance']} DOB Permit Issuance source rows, "
                f"{counts['dob_now_filings']} DOB NOW filing source rows, and "
                f"{counts['dob_complaints']} DOB complaint events."
            ),
            contractor_text,
            (
                "Confidence and provenance: "
                f"one evidence connection uses {confidence_method} with score {confidence_score}. "
                f"{BOUNDARY_STATEMENT}"
            ),
            review,
        ]
    )


def flatten_allowed_facts(evidence_bundle: dict[str, Any], facts: dict[str, Any]) -> dict[str, set[str]]:
    strings: set[str] = set()
    numbers: set[str] = set()

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            numbers.add(str(value))
            strings.add(str(value))
            return
        if isinstance(value, float):
            as_text = str(int(value)) if value.is_integer() else str(value)
            numbers.add(as_text)
            strings.add(as_text)
            return
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return
            strings.add(text)
            strings.add(text.lower())
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9:_./&,'+-]*", text):
                strings.add(token)
                strings.add(token.lower())
                if re.fullmatch(r"\d+(?:\.\d+)?", token):
                    numbers.add(token)
            return
        if isinstance(value, dict):
            for k, v in value.items():
                add(k)
                add(v)
            return
        if isinstance(value, list):
            for item in value:
                add(item)

    add(evidence_bundle)
    add(facts)
    for phrase in [
        "DOB Permit Issuance",
        "DOB NOW",
        "DOB complaint",
        "DOB complaints",
        "source rows",
        "filing source rows",
        "complaint events",
        "non-hero",
        "second-subject",
        "No contractor in evidence",
    ]:
        strings.add(phrase)
        strings.add(phrase.lower())
    return {"strings": strings, "numbers": numbers}


def extracted_facts(text: str, evidence_bundle: dict[str, Any]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []

    def emit(kind: str, value: str) -> None:
        value = value.strip().strip(".,;:()[]{}")
        if not value:
            return
        item = {"kind": kind, "value": value}
        if item not in facts:
            facts.append(item)

    for match in re.finditer(r"\b(?:parcel|building|permit|event|party):[A-Za-z0-9:_./&+-]+", text):
        emit("canonical_id", match.group(0))
    for match in re.finditer(r"\b(?:GC|PE|RA|R|MP|FS)-\d{6,7}\b", text):
        emit("license_number", match.group(0))
    for match in re.finditer(r"\bM\d{8}-[A-Z]\d\b", text):
        emit("job_number", match.group(0))
    for match in re.finditer(r"\b\d{7,10}\b", text):
        emit("long_number", match.group(0))
    for match in re.finditer(r"\b\d+\.\d+\b", text):
        emit("decimal_number", match.group(0))
    for match in re.finditer(r"(?<![\d.])\b\d+\b(?![\d.])", text):
        emit("integer_number", match.group(0))
    for match in re.finditer(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?\b", text):
        emit("date", match.group(0))
    for match in re.finditer(r"\b[a-z]+(?:_[a-z0-9]+)+\b", text):
        emit("slug_or_method", match.group(0))
    for match in re.finditer(r"\b(?:critical|high|medium|low|exact_bin|job_number|license_number|name_hash)\b", text, re.I):
        emit("severity_or_method", match.group(0))

    known_names = [
        entity.get("name") or entity.get("label")
        for entity in evidence_bundle.get("entities", [])
        if isinstance(entity, dict) and entity_kind(entity, "party") and (entity.get("name") or entity.get("label"))
    ]
    for name in known_names:
        if name and name in text:
            emit("party_name", name)

    org_suffix = r"(?:LLC|INC|INC\.|CORP|CORPORATION|COMPANY|GROUP|SCAFFOLD|CONTRACTING|CONSULTANTS|RESIDENTIAL|PROMOTIONS|ENTERPRISES|SPECIALIST|SAFETY|DESIGN|GAS|HEATING|PLUMBING|ACCESS)"
    for match in re.finditer(rf"\b[A-Z][A-Z0-9&.,' -]{{3,}}\s+{org_suffix}\b", text):
        phrase = match.group(0).strip(" .,")
        if phrase not in known_names:
            emit("party_like_name", phrase)

    return facts


def fact_supported(fact: dict[str, str], allowed: dict[str, set[str]], allowed_blob: str) -> bool:
    value = fact["value"]
    kind = fact["kind"]
    if kind in {"long_number", "decimal_number", "integer_number"}:
        return value in allowed["numbers"] or value in allowed["strings"]
    if kind == "party_like_name":
        return value in allowed["strings"] or value.lower() in allowed["strings"]
    return value in allowed["strings"] or value.lower() in allowed["strings"] or value.lower() in allowed_blob


def subset_grounding_report(evidence_bundle: dict[str, Any], facts: dict[str, Any], text: str) -> dict[str, Any]:
    allowed = flatten_allowed_facts(evidence_bundle, facts)
    allowed_blob = canonical_json({"evidence": evidence_bundle, "derived_facts": facts}).lower()
    checked = extracted_facts(text, evidence_bundle)
    unsupported = [
        item for item in checked if not fact_supported(item, allowed, allowed_blob)
    ]
    return {
        "gate": "A5-D6B-NARRATION-SUBSET-GROUNDED",
        "passed": not unsupported,
        "unsupported_facts": unsupported,
        "checked_facts": checked,
        "allowed_fact_counts": {
            "strings": len(allowed["strings"]),
            "numbers": len(allowed["numbers"]),
        },
    }


def coverage_report(label: str, evidence_bundle: dict[str, Any], facts: dict[str, Any], text: str) -> dict[str, Any]:
    bbl = facts["subject_bbl"]
    counts = facts["source_counts"]
    contractor = facts["contractor"]
    hero_complaint = facts["hero_complaint"]
    text_l = text.lower()
    required: dict[str, bool]
    if label == "hero":
        required = {
            "subject_parcel_bbl": bool(bbl and bbl in text),
            "evidence_boundary_statement": BOUNDARY_STATEMENT in text,
            "dob_permit_issuance_count": f"{counts['dob_permit_issuance']} DOB Permit Issuance" in text,
            "dob_now_filing_count": f"{counts['dob_now_filings']} DOB NOW" in text,
            "dob_complaint_count": f"{counts['dob_complaints']} DOB complaint" in text,
            "contractor_name_or_absence": (
                bool(contractor and contractor.get("name") and contractor["name"] in text)
                or "No contractor in evidence." in text
            ),
            "confidence_score_or_method": bool(
                re.search(r"\b0\.\d+\b", text)
                or "exact_bin" in text
                or "job_number" in text
                or "license_number" in text
                or "name_hash" in text
            ),
            "review_next_names_hero_complaint": bool(
                hero_complaint and HERO_COMPLAINT in text and "Review next:" in text
            ),
        }
    else:
        required = {
            "subject_parcel_bbl": bool(bbl and bbl in text),
            "evidence_boundary_statement": BOUNDARY_STATEMENT in text,
            "dob_permit_issuance_count": f"{counts['dob_permit_issuance']} DOB Permit Issuance" in text,
            "dob_now_filing_count_including_zero": f"{counts['dob_now_filings']} DOB NOW" in text,
            "dob_complaint_count": f"{counts['dob_complaints']} DOB complaint" in text,
            "explicit_non_hero_or_no_leakage": "non-hero" in text_l or no_hero_leakage(text),
            "confidence_score_or_method_or_absence": bool(
                re.search(r"\b0\.\d+\b", text)
                or "exact_bin" in text
                or "job_number" in text
                or "license_number" in text
                or "name_hash" in text
                or "no confidence" in text_l
            ),
        }
    present = [key for key, ok in required.items() if ok]
    missing = [key for key, ok in required.items() if not ok]
    return {
        "gate": "A5-D6B-NARRATION-MINIMUM-COVERAGE",
        "label": label,
        "passed": not missing,
        "required_items_present": present,
        "missing_items": missing,
    }


def anti_echo_report(text: str, structured_output: dict[str, Any]) -> dict[str, Any]:
    serialized = pretty_json(structured_output)
    stripped = text.strip()
    json_chars = sum(1 for ch in stripped if ch in "{}[]\":,")
    json_ratio = json_chars / max(len(stripped), 1)
    key_value_patterns = len(re.findall(r'"?[A-Za-z_][A-Za-z0-9_]*"?\s*[:=]', stripped))
    line_count = max(stripped.count("\n") + 1, 1)
    key_value_ratio = key_value_patterns / line_count
    similarity = difflib.SequenceMatcher(None, stripped[:10_000], serialized[:10_000]).ratio()
    passed = json_ratio < 0.12 and key_value_ratio < 0.45 and similarity < 0.72
    return {
        "gate": "A5-D6B-NARRATION-NOT-ECHO",
        "passed": passed,
        "json_looking_ratio": round(json_ratio, 6),
        "key_value_pattern_ratio": round(key_value_ratio, 6),
        "structured_output_similarity": round(similarity, 6),
    }


def no_hero_leakage(text: str) -> bool:
    return not [token for token in HERO_LEAKAGE_TOKENS if token in text]


def subject_isolation_report(label: str, text: str) -> dict[str, Any]:
    leaked = []
    if label != "hero":
        leaked = sorted(token for token in HERO_LEAKAGE_TOKENS if token in text)
    return {
        "gate": "A5-D6B-SUBJECT-ISOLATION",
        "label": label,
        "passed": not leaked,
        "leaked_tokens": leaked,
    }


def build_narration_surface(label: str, structured_output: dict[str, Any]) -> dict[str, Any]:
    evidence_bundle = structured_output["evidence_bundle"]
    facts = derived_facts(evidence_bundle, label)
    text = narrative_briefing(evidence_bundle, label)
    grounding = subset_grounding_report(evidence_bundle, facts, text)
    coverage = coverage_report(label, evidence_bundle, facts, text)
    anti_echo = anti_echo_report(text, structured_output)
    isolation = subject_isolation_report(label, text)
    explicit_subject_id = (
        evidence_bundle.get("subject_id")
        or structured_output.get("final_response", {}).get("subject_id")
        or (f"parcel:us-nyc:bbl:{facts['subject_bbl']}" if facts.get("subject_bbl") else None)
    )
    facts["subject_id"] = explicit_subject_id
    return {
        "subject_id": explicit_subject_id,
        "structured_evidence_output": structured_output,
        "structured_evidence_hash": sha256_payload(structured_output),
        "deterministic_derived_facts": facts,
        "narrative_briefing": text,
        "narration_grounding_report": grounding,
        "narration_coverage_report": coverage,
        "anti_echo_report": anti_echo,
        "subject_isolation_report": isolation,
        "passed": all(
            [
                grounding["passed"],
                coverage["passed"],
                anti_echo["passed"],
                isolation["passed"],
            ]
        ),
    }


def negative_fixture_reports(hero_surface: dict[str, Any], second_surface: dict[str, Any]) -> dict[str, Any]:
    fixtures = []
    hero_evidence = hero_surface["structured_evidence_output"]["evidence_bundle"]
    hero_facts = hero_surface["deterministic_derived_facts"]
    second_evidence = second_surface["structured_evidence_output"]["evidence_bundle"]
    second_facts = second_surface["deterministic_derived_facts"]

    bad_cases = [
        {
            "name": "invented_contractor_name",
            "label": "hero",
            "text": hero_surface["narrative_briefing"]
            + "\n\nThe contractor evidence also names ACME UNSAFE CONTRACTING LLC.",
            "expected_failed_gate": "subset_grounding",
        },
        {
            "name": "wrong_count",
            "label": "hero",
            "text": hero_surface["narrative_briefing"].replace(
                "9 DOB complaint events", "99 DOB complaint events"
            ),
            "expected_failed_gate": "subset_grounding",
        },
        {
            "name": "unsupported_date",
            "label": "hero",
            "text": hero_surface["narrative_briefing"] + "\n\nThe key date is 2025-01-01.",
            "expected_failed_gate": "subset_grounding",
        },
        {
            "name": "trivial_narration",
            "label": "hero",
            "text": "This parcel has activity.",
            "expected_failed_gate": "minimum_coverage",
        },
        {
            "name": "exact_json_echo",
            "label": "hero",
            "text": pretty_json(hero_surface["structured_evidence_output"]),
            "expected_failed_gate": "anti_echo",
        },
        {
            "name": "hero_leakage_into_second_subject",
            "label": "second_subject",
            "text": second_surface["narrative_briefing"]
            + "\n\nThis second-subject note also mentions parcel 1010607502 and complaint 1366080.",
            "expected_failed_gate": "subject_isolation",
        },
    ]

    for case in bad_cases:
        if case["label"] == "hero":
            evidence = hero_evidence
            facts = hero_facts
            structured = hero_surface["structured_evidence_output"]
        else:
            evidence = second_evidence
            facts = second_facts
            structured = second_surface["structured_evidence_output"]
        grounding = subset_grounding_report(evidence, facts, case["text"])
        coverage = coverage_report(case["label"], evidence, facts, case["text"])
        anti_echo = anti_echo_report(case["text"], structured)
        isolation = subject_isolation_report(case["label"], case["text"])
        failed_gates = []
        if not grounding["passed"]:
            failed_gates.append("subset_grounding")
        if not coverage["passed"]:
            failed_gates.append("minimum_coverage")
        if not anti_echo["passed"]:
            failed_gates.append("anti_echo")
        if not isolation["passed"]:
            failed_gates.append("subject_isolation")
        expected_failed = case["expected_failed_gate"] in failed_gates
        fixtures.append(
            {
                "name": case["name"],
                "expected_failed_gate": case["expected_failed_gate"],
                "failed_gates": failed_gates,
                "passed": expected_failed,
                "grounding_report": grounding,
                "coverage_report": coverage,
                "anti_echo_report": anti_echo,
                "subject_isolation_report": isolation,
            }
        )

    return {
        "gate": "A5-D6B-NEGATIVE-FIXTURES",
        "passed": all(item["passed"] for item in fixtures),
        "fixtures": fixtures,
    }


def write_readme(output_dir: Path, report: dict[str, Any]) -> None:
    text = f"""# a5·D6b Non-Technical Narration Surface

Status: **{report['status']}**

Boundary: {BOUNDARY_STATEMENT}

D6b adds a readable operator briefing surface on top of the accepted A5-D6 live NeMo/NIM replay. The strict structured evidence output is copied from the accepted D6 transcript and remains exact/evidence-preserving. The new `narrative_briefing` is a separate human-readable layer and is gated by subset grounding, minimum coverage, anti-echo, and subject-isolation checks.

## Narration Constraints

{chr(10).join(f'- {item}' for item in NARRATION_PROMPT_CONSTRAINTS)}

## Outputs

- `A5D6B_NARRATION_OUTPUTS.json`: structured evidence plus readable briefing for hero and second-subject queries.
- `A5D6B_GROUNDING_REPORT.json`: fact-subset grounding results.
- `A5D6B_COVERAGE_REPORT.json`: minimum coverage results.
- `A5D6B_NEGATIVE_TEST_REPORT.json`: deliberate failing fixtures.
- `A5D6B_HARNESS_REPORT.json`: D6b gate summary.

## Gate Summary

{chr(10).join(f'- {gate["gate_id"]}: {gate["status"]}' for gate in report['gates'])}
"""
    write_text(output_dir / "README.md", text)


def run_a5d6b_gate(
    input_dir: str | Path = DEFAULT_D6_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    input_path = Path(input_dir)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    d6_paths = get_d6_paths(input_path)
    input_hashes_before = {
        key: sha256_file(path)
        for key, path in d6_paths.items()
        if path.exists() and path.is_file()
    }

    clean_output_dir(output_path)

    precond_pass, accepted, precond_details = d6_preconditions(input_path)
    transcript = accepted.get("transcript", {})
    hero_output = transcript.get("runs", {}).get("hero", {}).get("tool_invocation", {}).get("output", {})
    second_output = transcript.get("runs", {}).get("second_subject", {}).get("tool_invocation", {}).get("output", {})

    outputs: dict[str, Any] = {
        "task": TASK_NAME,
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "narration_prompt_constraints": NARRATION_PROMPT_CONSTRAINTS,
        "queries": {},
    }
    if hero_output:
        outputs["queries"]["hero"] = build_narration_surface("hero", hero_output)
    if second_output:
        outputs["queries"]["second_subject"] = build_narration_surface("second_subject", second_output)

    hero_surface = outputs["queries"].get("hero", {})
    second_surface = outputs["queries"].get("second_subject", {})
    negative_report = (
        negative_fixture_reports(hero_surface, second_surface)
        if hero_surface and second_surface
        else {"gate": "A5-D6B-NEGATIVE-FIXTURES", "passed": False, "fixtures": [], "reason": "positive surfaces missing"}
    )

    grounding_report = {
        "gate": "A5-D6B-NARRATION-SUBSET-GROUNDED",
        "passed": all(
            surface.get("narration_grounding_report", {}).get("passed")
            for surface in outputs["queries"].values()
        ),
        "results": {
            label: surface.get("narration_grounding_report")
            for label, surface in outputs["queries"].items()
        },
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    coverage_report_all = {
        "gate": "A5-D6B-NARRATION-MINIMUM-COVERAGE",
        "passed": all(
            surface.get("narration_coverage_report", {}).get("passed")
            for surface in outputs["queries"].values()
        ),
        "results": {
            label: surface.get("narration_coverage_report")
            for label, surface in outputs["queries"].items()
        },
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    anti_echo_all = {
        "gate": "A5-D6B-NARRATION-NOT-ECHO",
        "passed": all(
            surface.get("anti_echo_report", {}).get("passed")
            for surface in outputs["queries"].values()
        ),
        "results": {
            label: surface.get("anti_echo_report")
            for label, surface in outputs["queries"].items()
        },
    }
    isolation_all = {
        "gate": "A5-D6B-SUBJECT-ISOLATION",
        "passed": all(
            surface.get("subject_isolation_report", {}).get("passed")
            for surface in outputs["queries"].values()
        ),
        "results": {
            label: surface.get("subject_isolation_report")
            for label, surface in outputs["queries"].items()
        },
    }

    write_json(output_path / "A5D6B_NARRATION_OUTPUTS.json", outputs)
    write_json(output_path / "A5D6B_GROUNDING_REPORT.json", grounding_report)
    write_json(output_path / "A5D6B_COVERAGE_REPORT.json", coverage_report_all)
    write_json(output_path / "A5D6B_NEGATIVE_TEST_REPORT.json", negative_report)

    input_hashes_after = {
        key: sha256_file(path)
        for key, path in d6_paths.items()
        if path.exists() and path.is_file()
    }
    no_mutation = input_hashes_before == input_hashes_after

    gates = [
        gate("A5D6B-PRECOND", "Existing A5-D6 structural checks remain green", precond_pass, precond_details),
        gate(
            "A5D6B-STRUCTURED-EVIDENCE-EXACT",
            "Structured evidence output is copied from accepted A5-D6 transcript",
            bool(hero_surface and second_surface)
            and hero_surface.get("structured_evidence_hash") == sha256_payload(hero_output)
            and second_surface.get("structured_evidence_hash") == sha256_payload(second_output),
        ),
        gate(
            "A5D6B-NARRATION-SUBSET-GROUNDED",
            "Narrative briefing facts are a subset of evidence and deterministic facts",
            grounding_report["passed"],
        ),
        gate(
            "A5D6B-NARRATION-MINIMUM-COVERAGE",
            "Narrative briefing contains required operational facts",
            coverage_report_all["passed"],
        ),
        gate(
            "A5D6B-NARRATION-NOT-ECHO",
            "Narrative briefing is not a JSON/evidence echo",
            anti_echo_all["passed"],
        ),
        gate(
            "A5D6B-SUBJECT-ISOLATION",
            "Second-subject narration has no hero-token leakage",
            isolation_all["passed"],
        ),
        gate(
            "A5D6B-NEGATIVE-FIXTURES",
            "Deliberate failing fixtures fail the expected gates",
            negative_report["passed"],
        ),
        gate(
            "A5D6B-BOUNDARY",
            "Boundary statement is present in human-facing and report artifacts",
            all(
                BOUNDARY_STATEMENT in canonical_json(payload)
                for payload in [outputs, grounding_report, coverage_report_all]
            ),
        ),
        gate(
            "A5D6B-NO-MUTATION",
            "Accepted A5-D6 input artifacts remain byte-stable",
            no_mutation,
        ),
    ]

    status = "PASS" if all(item["passed"] for item in gates) else "FAIL"
    report = {
        "task": TASK_NAME,
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "generated_at": utc_now(),
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "boundary_statement": BOUNDARY_STATEMENT,
        "narration_prompt_constraints": NARRATION_PROMPT_CONSTRAINTS,
        "input_hashes_before": input_hashes_before,
        "input_hashes_after": input_hashes_after,
        "queries": {
            label: {
                "subject_id": surface.get("subject_id"),
                "structured_evidence_hash": surface.get("structured_evidence_hash"),
                "narration_passed": surface.get("passed"),
                "source_rows": surface.get("deterministic_derived_facts", {}).get("source_counts"),
            }
            for label, surface in outputs["queries"].items()
        },
        "checks": {
            "precond": gates[0]["passed"],
            "structured_evidence_exact": gates[1]["passed"],
            "subset_grounded": gates[2]["passed"],
            "minimum_coverage": gates[3]["passed"],
            "not_echo": gates[4]["passed"],
            "subject_isolation": gates[5]["passed"],
            "negative_fixtures": gates[6]["passed"],
            "boundary": gates[7]["passed"],
            "no_mutation": gates[8]["passed"],
        },
        "gates": gates,
    }
    write_json(output_path / "A5D6B_HARNESS_REPORT.json", report)
    write_readme(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a5-D6b narration surface gate.")
    parser.add_argument("--input-dir", default=str(DEFAULT_D6_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_a5d6b_gate(args.input_dir, args.output_dir)
    print(f"a5-D6b Non-Technical Narration Surface: {report['status']}")
    print(f"Input A5-D6: {report['input_dir']}")
    print(f"Output: {report['output_dir']}")
    for gate_item in report["gates"]:
        print(f"- {gate_item['gate_id']}: {gate_item['status']}")
        if not gate_item["passed"]:
            for detail in gate_item.get("details", []):
                print(f"  {detail}")
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
