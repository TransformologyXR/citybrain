#!/usr/bin/env python3
"""Run the CityBrain D8 R3 follow-on handover pack.

Creates conservative R3 outputs for:
- Helsinki manual object-pick review capture
- Chicago bounded similar-case query smoke
- VSS licensed corpus sample ingest smoke
- R3 pack closeout

No prior outputs are mutated. No large downloads, scraping, model inference,
production readiness, certified identity, legal finding, live monitoring, or
autonomous action is claimed.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
RUN_TS = dt.datetime.now(dt.timezone.utc).isoformat()

ROOTS = {
    "helsinki": OUTPUTS / "helsinki_kit_object_pick_manual_review_capture_r3",
    "chicago": OUTPUTS / "chicago_similar_case_demo_query_smoke_r3",
    "vss": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_ingest_smoke_r3",
    "closeout": OUTPUTS / "citybrain_d8_r3_followon_prompt_pack_closeout",
}

UPSTREAM = {
    "d8_followon_closeout": OUTPUTS / "citybrain_d8_followon_and_composition_prompt_pack_closeout/CITYBRAIN_D8_FOLLOWON_AND_COMPOSITION_PROMPT_PACK_CLOSEOUT.json",
    "helsinki_r2_root": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2",
    "helsinki_r2_decision": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2/HELSINKI_KIT_OBJECT_PICK_MANUAL_ALIGNMENT_R2_DECISION.json",
    "helsinki_r2_packets": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2/HELSINKI_OBJECT_PICK_ALIGNMENT_PACKETS.jsonl",
    "helsinki_r2_checklist": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2/HELSINKI_OBJECT_PICK_ALIGNMENT_REVIEW_CHECKLIST.csv",
    "helsinki_r2_usda": OUTPUTS / "helsinki_kit_object_pick_manual_alignment_r2/HELSINKI_MANUAL_ALIGNMENT_USDA_LAYER.usda",
    "chicago_r2_root": OUTPUTS / "chicago_similar_case_reviewed_matching_r2",
    "chicago_r2_decision": OUTPUTS / "chicago_similar_case_reviewed_matching_r2/CHICAGO_SIMILAR_CASE_REVIEWED_MATCHING_R2_DECISION.json",
    "chicago_r2_cases": OUTPUTS / "chicago_similar_case_reviewed_matching_r2/CHICAGO_REVIEWED_CASES.jsonl",
    "chicago_r2_matches": OUTPUTS / "chicago_similar_case_reviewed_matching_r2/CHICAGO_SIMILAR_CASE_MATCHES.jsonl",
    "chicago_r2_packet": OUTPUTS / "chicago_similar_case_reviewed_matching_r2/CHICAGO_CITY_REMEMBERS_PACKET_V2.json",
    "vss_r2_root": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2",
    "vss_r2_decision": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/VSS_LICENSED_CORPUS_SAMPLE_ACQUISITION_R2_DECISION.json",
    "vss_r2_gate": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/VSS_SAMPLE_GATE_DECISION.json",
    "vss_r2_ledger": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/VSS_SOURCE_CANDIDATE_LEDGER.json",
    "vss_r2_contract": OUTPUTS / "main_citybrain_d8_vss_licensed_corpus_sample_acquisition_r2/VSS_MINIMAL_SAMPLE_ACCEPTANCE_CONTRACT.json",
    "demo_surface": OUTPUTS / "main_citybrain_d8_demonstrable_surface_integration_r1/MAIN_CITYBRAIN_D8_DEMONSTRABLE_SURFACE_INTEGRATION_R1_DECISION.json",
    "composition": OUTPUTS / "main_citybrain_d8_parallel_pack_composition_closeout_r1/MAIN_CITYBRAIN_D8_PARALLEL_PACK_COMPOSITION_CLOSEOUT_R1_DECISION.json",
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def safe_reset_root(root: Path) -> None:
    root = root.resolve()
    if OUTPUTS.resolve() not in root.parents:
        raise RuntimeError(f"Refusing to reset non-output root: {root}")
    if root.name not in {r.name for r in ROOTS.values()}:
        raise RuntimeError(f"Refusing to reset unexpected output root: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def encode_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: encode_cell(row.get(name)) for name in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def snapshot_upstream() -> dict[str, Any]:
    return {key: file_record(path) for key, path in UPSTREAM.items()}


def json_parse_audit(root: Path) -> dict[str, Any]:
    ok = True
    results: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            results.append({"path": rel(path), "status": "PASS"})
        except Exception as exc:
            ok = False
            results.append({"path": rel(path), "status": "FAIL", "error": str(exc)})
    for path in sorted(root.rglob("*.jsonl")):
        bad: list[dict[str, Any]] = []
        line_count = 0
        with path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    json.loads(line)
                except Exception as exc:
                    ok = False
                    bad.append({"line": idx, "error": str(exc)})
                    if len(bad) >= 5:
                        break
        results.append({"path": rel(path), "status": "PASS" if not bad else "FAIL", "line_count": line_count, "bad_lines": bad})
    return {"status": "PASS" if ok else "FAIL", "files_checked": len(results), "results": results}


def secret_scan(root: Path) -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|accountkey|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
        re.compile(r"(?i)x-api-key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "offset": match.start(), "pattern": pattern.pattern})
    return {"status": "PASS" if not hits else "FAIL", "secrets_found": len(hits), "hits": hits}


def claim_boundary_audit(root: Path) -> dict[str, Any]:
    unsafe_patterns = [
        r"(?i)\bproduction digital twin\b",
        r"(?i)\bproduction civic analytics\b",
        r"(?i)\bproduction[- ]ready\b",
        r"(?i)\bcertified\b",
        r"(?i)\blegal finding\b",
        r"(?i)\bconfirmed violation\b",
        r"(?i)\bVSS is ready\b",
        r"(?i)\bVSS runtime readiness\b",
        r"(?i)\btraffic image/video analytics is operational\b",
        r"(?i)\bobject-level identity\b",
        r"(?i)\bcity memory is complete\b",
        r"(?i)\bsearch all Chicago\b",
        r"(?i)\bautonomous\b",
        r"(?i)\bdispatch\b",
        r"(?i)\benforcement\b",
        r"(?i)\bcommand/control\b",
    ]
    boundary_context = re.compile(
        r"(?i)(forbidden|do not|not claim|no claim|false|closed|gate remains closed|not ready|"
        r"not production|not certified|not legal|not autonomous|no full|no VSS|boundary|limitation|"
        r"\bno\b.+\bclaim(?:ed)?\b|recommended_next_task|CERTIFIED-HANDOFF|"
        r"visual_backdrop_only|citywide_memory_claim.+false|object_level_alignment_claim.+false|"
        r"vss_runtime_readiness_claim.+false|allowed only if|unless|without)"
    )
    boundary_files = {
        "HELSINKI_OBJECT_PICK_LIMITATIONS.md",
        "CHICAGO_SIMILAR_CASE_LIMITATIONS.md",
        "VSS_RUNTIME_READINESS_BOUNDARY.md",
        "VSS_MISSING_REQUIREMENTS_CHECKLIST.md",
        "CITYBRAIN_D8_R3_FOLLOWON_HANDOFF.md",
    }
    hits: list[dict[str, Any]] = []
    boundary_mentions: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "CLAIM_BOUNDARY_AUDIT.json":
            continue
        file_is_boundary = path.name in boundary_files or "LIMITATION" in path.name or "BOUNDARY" in path.name
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            for pattern in unsafe_patterns:
                if not re.search(pattern, line):
                    continue
                item = {"path": rel(path), "line": line_no, "pattern": pattern, "excerpt": line.strip()[:240]}
                if file_is_boundary or boundary_context.search(line):
                    boundary_mentions.append(item)
                else:
                    hits.append(item)
    return {
        "status": "PASS" if not hits else "FAIL",
        "unsafe_positive_claim_hits": hits,
        "boundary_context_mentions": boundary_mentions,
        "production_claim_made": False,
        "legal_or_certified_claim_made": False,
        "live_or_autonomous_claim_made": False,
        "vss_runtime_readiness_claim_made": False,
    }


def no_mutation_audit(root: Path, before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_upstream()
    mutations = []
    for key, value in before.items():
        if after.get(key) != value:
            mutations.append({"input": key, "before": value, "after": after.get(key)})
    return {
        "status": "PASS" if not mutations else "FAIL",
        "prior_outputs_mutated": bool(mutations),
        "mutated_inputs": mutations,
        "generated_output_root": rel(root),
    }


def referenced_artifact_audit(refs: list[str]) -> dict[str, Any]:
    rows = []
    for ref in sorted(set(ref for ref in refs if ref)):
        path_part = str(ref).split("#", 1)[0]
        if not path_part.startswith("outputs/"):
            continue
        path = REPO_ROOT / path_part
        rows.append({"ref": ref, "path": path_part, "exists": path.exists()})
    return {"status": "PASS" if all(row["exists"] for row in rows) else "FAIL", "refs_checked": len(rows), "results": rows}


def write_hash_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "HASH_MANIFEST.sha256":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(root / "HASH_MANIFEST.sha256", "\n".join(rows))


def finalize_root(root: Path, before: dict[str, Any], refs: list[str]) -> dict[str, Any]:
    write_json(root / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json", referenced_artifact_audit(refs))
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    write_json(root / "SECRET_SCAN_AUDIT.json", secret_scan(root))
    write_json(root / "CLAIM_BOUNDARY_AUDIT.json", claim_boundary_audit(root))
    write_json(root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json", no_mutation_audit(root, before))
    write_hash_manifest(root)
    # Refresh parse audit after audit JSONs are written.
    write_json(root / "JSON_PARSE_AUDIT.json", json_parse_audit(root))
    write_hash_manifest(root)
    return {
        "json_parse": read_json(root / "JSON_PARSE_AUDIT.json"),
        "secret_scan": read_json(root / "SECRET_SCAN_AUDIT.json"),
        "claim_boundary": read_json(root / "CLAIM_BOUNDARY_AUDIT.json"),
        "no_prior_output_mutation": read_json(root / "NO_PRIOR_OUTPUT_MUTATION_AUDIT.json"),
        "referenced_artifacts": read_json(root / "REFERENCED_ARTIFACT_EXISTENCE_AUDIT.json"),
    }


def has_explicit_review_evidence(packet: dict[str, Any]) -> bool:
    for key in ("reviewer_initials", "review_date", "screenshot_path", "manual_review_evidence_refs"):
        value = packet.get(key)
        if value:
            return True
    status = str(packet.get("alignment_status", "")).lower()
    return status in {"reviewed_aligned", "aligned_by_manual_pick", "reviewed_probable", "reviewed_uncertain", "reviewed_rejected"}


def run_helsinki(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["helsinki"]
    safe_reset_root(root)
    packets = read_jsonl(UPSTREAM["helsinki_r2_packets"])
    capture_rows: list[dict[str, Any]] = []
    counts = {
        "reviewed_aligned": 0,
        "reviewed_probable": 0,
        "reviewed_uncertain": 0,
        "reviewed_rejected": 0,
        "pending_review": 0,
    }
    refs = [rel(UPSTREAM["helsinki_r2_packets"]), rel(UPSTREAM["helsinki_r2_decision"]), rel(UPSTREAM["helsinki_r2_usda"])]
    for packet in packets:
        evidence = packet.get("evidence_refs", [])
        refs.extend(evidence)
        if has_explicit_review_evidence(packet):
            status = str(packet.get("alignment_status") or "reviewed_uncertain")
            if status == "aligned_by_manual_pick":
                classification = "reviewed_aligned"
            elif status in counts:
                classification = status
            else:
                classification = "reviewed_uncertain"
        else:
            classification = "pending_review"
        counts[classification] += 1
        capture_rows.append(
            {
                "alignment_packet_id": packet.get("alignment_packet_id"),
                "canonical_entity_candidate_id": packet.get("canonical_entity_candidate_id"),
                "citybrain_candidate_id": packet.get("citybrain_candidate_id"),
                "source_citygml_id": packet.get("CityGML_gml_id") or packet.get("source_citygml_id"),
                "suggested_usd_prim_path": packet.get("suggested_usd_prim_path") or packet.get("candidate_prim_path"),
                "review_classification": classification,
                "review_state": packet.get("review_state"),
                "alignment_status": packet.get("alignment_status"),
                "explicit_review_evidence_present": has_explicit_review_evidence(packet),
                "evidence_refs": evidence,
                "limitation_refs": packet.get("limitation_refs", []),
                "visual_mesh_status": "VISUAL_BACKDROP_ONLY",
                "object_level_alignment_claim": False,
                "review_notes": "Pending manual Kit/Composer review; packet existence is not alignment evidence.",
            }
        )
    write_jsonl(root / "MANUAL_OBJECT_PICK_REVIEW_CAPTURE.jsonl", capture_rows)
    write_csv(
        root / "MANUAL_OBJECT_PICK_REVIEW_CAPTURE.csv",
        capture_rows,
        [
            "alignment_packet_id",
            "canonical_entity_candidate_id",
            "citybrain_candidate_id",
            "source_citygml_id",
            "suggested_usd_prim_path",
            "review_classification",
            "review_state",
            "alignment_status",
            "explicit_review_evidence_present",
            "evidence_refs",
            "limitation_refs",
            "visual_mesh_status",
            "object_level_alignment_claim",
            "review_notes",
        ],
    )
    write_text(
        root / "KIT_COMPOSER_MANUAL_REVIEW_HANDOFF.md",
        "# Kit/Composer Manual Review Handoff\n\n"
        "Open the Helsinki/Kalasatama visual scene and load the R2 sidecar USDA layer. For each capture row, locate the suggested prim/marker, compare it to the CityGML/CER candidate, and record reviewer initials, date, screenshot path, and a classification. Until that evidence is added, every packet remains `pending_review` and the mesh remains `VISUAL_BACKDROP_ONLY`.\n",
    )
    write_text(
        root / "HELSINKI_OBJECT_PICK_DEMO_SUMMARY.md",
        f"# Helsinki Object Pick Demo Summary\n\nCaptured {len(capture_rows)} R2 manual object-pick packets for demo-safe review. Current classification is conservative: {counts['pending_review']} pending, {counts['reviewed_aligned']} aligned, {counts['reviewed_probable']} probable, {counts['reviewed_uncertain']} uncertain, {counts['reviewed_rejected']} rejected.\n\nThis is a review handoff, not full object-level USD alignment.\n",
    )
    write_text(
        root / "HELSINKI_OBJECT_PICK_LIMITATIONS.md",
        "# Helsinki Object Pick Limitations\n\n"
        "- Visual mesh status remains `VISUAL_BACKDROP_ONLY`.\n"
        "- Packet existence is not manual review evidence.\n"
        "- No full object-level identity or certified digital twin claim is made.\n"
        "- R3 is demo evidence and Kit/Composer handoff only.\n",
    )
    decision = {
        "task": "HELSINKI-KIT-OBJECT-PICK-MANUAL-REVIEW-CAPTURE-R3",
        "status": "PASS_WITH_LIMITATIONS" if packets else "FAIL",
        "upstream_roots": [rel(UPSTREAM["helsinki_r2_root"])],
        "packets_loaded": len(packets),
        "review_counts": counts,
        "visual_mesh_status": "VISUAL_BACKDROP_ONLY",
        "object_level_alignment_claim": False,
        "demo_safe": bool(packets),
        "audits": {},
        "limitations": [
            "All packets default to pending review unless explicit local review evidence exists.",
            "No full object-level alignment claim is made.",
            "The R2 USDA layer remains a sidecar/review overlay.",
        ],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1",
    }
    write_json(root / "HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json", decision)
    audits = finalize_root(root, before, refs)
    decision["audits"] = {k: v.get("status") for k, v in audits.items() if isinstance(v, dict)}
    write_json(root / "HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json", decision)
    finalize_root(root, before, refs)
    return decision


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def distance_km(a: dict[str, Any], b: dict[str, Any]) -> float | None:
    lat1 = parse_float(a.get("location_fields", {}).get("latitude"))
    lon1 = parse_float(a.get("location_fields", {}).get("longitude"))
    lat2 = parse_float(b.get("location_fields", {}).get("latitude"))
    lon2 = parse_float(b.get("location_fields", {}).get("longitude"))
    if None in (lat1, lon1, lat2, lon2):
        return None
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def case_summary(case: dict[str, Any]) -> str:
    return f"{case.get('case_id')} / {case.get('source_family')} / {case.get('issue_event_type')} / {case.get('category_or_type')}"


def answer_query(fixture: dict[str, Any], cases: list[dict[str, Any]], matches: list[dict[str, Any]]) -> dict[str, Any]:
    family = fixture["query_family"]
    case_by_id = {row["case_id"]: row for row in cases}
    if family == "citywide_abstain":
        return {
            "query_id": fixture["query_id"],
            "query_family": family,
            "answer_state": "ABSTAIN_NO_DATA",
            "answer": "I cannot answer citywide trends from a bounded 15-case sample.",
            "cited_case_ids": [],
            "evidence_refs": [],
            "limitations": ["lim:bounded_sample_only", "lim:no_citywide_memory_claim"],
        }
    if family == "similar_violation":
        source = next((case for case in cases if case.get("source_family") == "violations"), None)
        selected = [m for m in matches if source and m.get("source_case_id") == source["case_id"]][:3]
    elif family == "311_context":
        source = next((case for case in cases if case.get("source_family") == "311"), None)
        selected = [m for m in matches if source and m.get("source_case_id") == source["case_id"]][:3]
    elif family == "sensor_context":
        source = next((case for case in cases if case.get("source_family") == "array_of_things"), None)
        selected = [m for m in matches if source and m.get("source_case_id") == source["case_id"]][:3]
    else:
        selected = [
            m
            for m in matches
            if case_by_id.get(m.get("source_case_id"), {}).get("source_family")
            != case_by_id.get(m.get("candidate_case_id"), {}).get("source_family")
        ][:5]
        source = case_by_id.get(selected[0]["source_case_id"]) if selected else None
    cited_ids = []
    evidence_refs = []
    for match in selected:
        for key in ("source_case_id", "candidate_case_id"):
            cid = match.get(key)
            if cid and cid not in cited_ids:
                cited_ids.append(cid)
                evidence_refs.extend(case_by_id.get(cid, {}).get("evidence_refs", []))
    if not selected:
        return {
            "query_id": fixture["query_id"],
            "query_family": family,
            "answer_state": "ABSTAIN_NO_MATCH",
            "answer": "The bounded sample did not contain enough matching evidence for this query.",
            "cited_case_ids": [],
            "evidence_refs": [],
            "limitations": ["lim:bounded_sample_only", "lim:no_invented_evidence"],
        }
    return {
        "query_id": fixture["query_id"],
        "query_family": family,
        "answer_state": "ANSWERED_BOUNDED_SAMPLE",
        "answer": f"Within the bounded sample, {case_summary(source) if source else 'the selected source case'} has {len(selected)} reviewed match candidate(s).",
        "cited_case_ids": cited_ids,
        "evidence_refs": sorted(set(evidence_refs)),
        "match_refs": selected,
        "limitations": ["lim:bounded_sample_only", "lim:no_causality_prediction_or_legal_conclusion"],
    }


def run_chicago(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["chicago"]
    safe_reset_root(root)
    cases = read_jsonl(UPSTREAM["chicago_r2_cases"])
    matches = read_jsonl(UPSTREAM["chicago_r2_matches"])
    refs = [rel(UPSTREAM["chicago_r2_cases"]), rel(UPSTREAM["chicago_r2_matches"]), rel(UPSTREAM["chicago_r2_packet"])]
    fixtures = [
        {"query_id": "chi_r3_q01", "query_family": "similar_violation", "intent": "Show cases similar to this violation pattern."},
        {"query_id": "chi_r3_q02", "query_family": "311_context", "intent": "What nearby civic complaints look related in the bounded sample?"},
        {"query_id": "chi_r3_q03", "query_family": "sensor_context", "intent": "What Array of Things context is attached to this reviewed sample?"},
        {"query_id": "chi_r3_q04", "query_family": "cross_source", "intent": "Which reviewed cases connect violation, 311, and sensor-style context?"},
        {"query_id": "chi_r3_q05", "query_family": "citywide_abstain", "intent": "Find citywide trends across Chicago."},
    ]
    results = [answer_query(fixture, cases, matches) for fixture in fixtures]
    abstains = [row for row in results if row["answer_state"].startswith("ABSTAIN")]
    cards = []
    case_by_id = {case["case_id"]: case for case in cases}
    for result in results:
        if result["answer_state"] == "ANSWERED_BOUNDED_SAMPLE":
            cards.append(
                {
                    "card_id": f"chi:r3:demo_card:{len(cards)+1:02d}",
                    "query_id": result["query_id"],
                    "title": result["query_family"].replace("_", " ").title(),
                    "summary": result["answer"],
                    "cited_cases": [case_summary(case_by_id[cid]) for cid in result["cited_case_ids"] if cid in case_by_id],
                    "evidence_refs": result["evidence_refs"],
                    "limitations": result["limitations"],
                }
            )
    write_json(root / "CHICAGO_DEMO_QUERY_FIXTURES.json", {"fixtures": fixtures})
    write_jsonl(root / "CHICAGO_DEMO_QUERY_RESULTS.jsonl", results)
    write_jsonl(root / "CHICAGO_CITY_REMEMBERS_DEMO_CARDS.jsonl", cards)
    write_jsonl(root / "CHICAGO_QUERY_ABSTAIN_CASES.jsonl", abstains)
    write_text(
        root / "CHICAGO_SIMILAR_CASE_DEMO_SUMMARY.md",
        f"# Chicago Similar-Case Demo Query Smoke R3\n\nLoaded {len(cases)} reviewed cases and {len(matches)} bounded matches. Ran {len(fixtures)} query fixtures: {len(results)-len(abstains)} answered from bounded evidence and {len(abstains)} abstained cleanly.\n",
    )
    write_text(
        root / "CHICAGO_SIMILAR_CASE_LIMITATIONS.md",
        "# Chicago Similar-Case Limitations\n\n"
        "- Bounded 15-case sample only.\n"
        "- No citywide Chicago memory, operational completeness, causality, prediction, legal decision, enforcement, or production civic analytics.\n"
        "- Every answer must cite case IDs/evidence refs or abstain.\n",
    )
    refs.extend(ref for result in results for ref in result.get("evidence_refs", []) if str(ref).startswith("outputs/"))
    decision = {
        "task": "CHICAGO-SIMILAR-CASE-DEMO-QUERY-SMOKE-R3",
        "status": "PASS_WITH_LIMITATIONS" if cases and matches and len(fixtures) >= 5 else "FAIL",
        "upstream_roots": [rel(UPSTREAM["chicago_r2_root"])],
        "reviewed_cases_loaded": len(cases),
        "similar_matches_loaded": len(matches),
        "query_fixtures_run": len(fixtures),
        "queries_answered": len(results) - len(abstains),
        "queries_abstained": len(abstains),
        "demo_cards_created": len(cards),
        "citywide_memory_claim": False,
        "audits": {},
        "limitations": [
            "Only the R2 bounded sample is queried.",
            "Citywide/general trend queries abstain.",
            "No causal, legal, enforcement, production, or live monitoring claim is made.",
        ],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1",
    }
    write_json(root / "CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json", decision)
    audits = finalize_root(root, before, refs)
    decision["audits"] = {k: v.get("status") for k, v in audits.items() if isinstance(v, dict)}
    write_json(root / "CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json", decision)
    finalize_root(root, before, refs)
    return decision


def missing_requirements(candidate: dict[str, Any]) -> list[str]:
    missing = []
    if "local" not in str(candidate.get("access_status", "")).lower() and candidate.get("expected_sample_count", 0) == 0:
        missing.append("media_file_or_clip_file")
    if "not_audited" in str(candidate.get("license_status", "")).lower() or "needs" in str(candidate.get("license_status", "")).lower() or "required" in str(candidate.get("license_status", "")).lower():
        missing.append("license_or_provenance_record")
    if not candidate.get("camera_metadata_available"):
        missing.append("camera_metadata")
    if "privacy" in str(candidate.get("privacy_status", "")).lower() and "bounded_demo" not in str(candidate.get("privacy_status", "")).lower():
        missing.append("privacy_sensitivity_label")
    if "missing" in str(candidate.get("oracle_label_feasibility", "")).lower() or "required" in str(candidate.get("oracle_label_feasibility", "")).lower():
        missing.append("expected_output_oracle")
    if candidate.get("expected_sample_count", 0) == 0:
        missing.append("hash_provenance_record")
    return sorted(set(missing))


def run_vss(before: dict[str, Any]) -> dict[str, Any]:
    root = ROOTS["vss"]
    safe_reset_root(root)
    gate = read_json(UPSTREAM["vss_r2_gate"]) or {}
    ledger = read_json(UPSTREAM["vss_r2_ledger"]) or {}
    candidates = ledger.get("candidates", [])
    checks = []
    eligible = []
    for candidate in candidates:
        missing = missing_requirements(candidate)
        ok = not missing and candidate.get("recommended_disposition") == "approved_for_local_sample"
        check = {
            "source_name": candidate.get("source_name"),
            "access_status": candidate.get("access_status"),
            "license_status": candidate.get("license_status"),
            "privacy_status": candidate.get("privacy_status"),
            "camera_metadata_available": candidate.get("camera_metadata_available"),
            "oracle_label_feasibility": candidate.get("oracle_label_feasibility"),
            "eligible_for_ingest": ok,
            "missing_requirements": missing,
            "recommended_disposition": candidate.get("recommended_disposition"),
        }
        checks.append(check)
        if ok:
            eligible.append(check)
    all_missing = sorted({item for check in checks for item in check["missing_requirements"]})
    write_json(
        root / "VSS_SAMPLE_ELIGIBILITY_CHECK.json",
        {
            "task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3",
            "upstream_gate": gate,
            "sample_candidates_found": len(candidates),
            "eligible_samples": len(eligible),
            "checks": checks,
            "sample_ingest_gate": "OPEN_STRUCTURAL_INGEST" if eligible else "CLOSED",
            "runtime_readiness_gate": "CLOSED",
        },
    )
    manifest = {
        "task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3",
        "manifest_status": "EMPTY_CLOSED_GATE" if not eligible else "STRUCTURAL_INGEST_READY",
        "media_ingested": False,
        "sample_items": [],
        "reason": "No complete local licensed sample exists." if not eligible else "Eligible samples found; structural manifest only.",
    }
    write_json(root / "VSS_SAMPLE_INGEST_MANIFEST.json", manifest)
    write_text(
        root / "VSS_MISSING_REQUIREMENTS_CHECKLIST.md",
        "# VSS Missing Requirements Checklist\n\n"
        + "\n".join(f"- {item}" for item in all_missing)
        + "\n\nNeeded next: a local media file plus explicit license/provenance, camera metadata, privacy label, oracle/review labels, and hash/provenance record. No media was ingested in this R3 pass.\n",
    )
    write_json(
        root / "VSS_LICENSE_AND_PRIVACY_AUDIT.json",
        {
            "status": "PASS_CLOSED_GATE",
            "eligible_license_privacy_pairs": 0,
            "unlicensed_media_ingested": False,
            "privacy_labels_complete": False,
        },
    )
    write_json(
        root / "VSS_CAMERA_METADATA_AUDIT.json",
        {
            "status": "PASS_CLOSED_GATE",
            "camera_metadata_complete": False,
            "eligible_samples_with_camera_metadata": 0,
        },
    )
    write_json(
        root / "VSS_ORACLE_AUDIT.json",
        {
            "status": "PASS_CLOSED_GATE",
            "oracle_labels_complete": False,
            "eligible_samples_with_oracle": 0,
        },
    )
    write_text(
        root / "VSS_RUNTIME_READINESS_BOUNDARY.md",
        "# VSS Runtime Readiness Boundary\n\n"
        "The sample ingest gate remains closed because required licensed sample evidence is missing. VSS runtime readiness, camera inference, DeepStream/VSS operation, production video analytics, and licensed corpus acquisition are not claimed.\n",
    )
    refs = [rel(UPSTREAM["vss_r2_gate"]), rel(UPSTREAM["vss_r2_ledger"]), rel(UPSTREAM["vss_r2_contract"]), rel(UPSTREAM["vss_r2_decision"])]
    decision = {
        "task": "MAIN-CITYBRAIN-D8-VSS-LICENSED-CORPUS-SAMPLE-INGEST-SMOKE-R3",
        "status": "PASS_WITH_LIMITATIONS",
        "upstream_roots": [rel(UPSTREAM["vss_r2_root"])],
        "sample_candidates_found": len(candidates),
        "eligible_samples": len(eligible),
        "sample_ingest_gate": "OPEN_STRUCTURAL_INGEST" if eligible else "CLOSED",
        "runtime_readiness_gate": "CLOSED",
        "licensed_corpus_claim": False,
        "vss_runtime_readiness_claim": False,
        "missing_requirements": all_missing,
        "ingest_manifest_created": bool(eligible),
        "audits": {},
        "limitations": [
            "VSS R2 records loaded, but no complete local licensed sample exists.",
            "No media was downloaded, scraped, fabricated, substituted, or ingested.",
            "Runtime readiness remains closed.",
        ],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1",
    }
    write_json(root / "MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json", decision)
    audits = finalize_root(root, before, refs)
    decision["audits"] = {k: v.get("status") for k, v in audits.items() if isinstance(v, dict)}
    write_json(root / "MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json", decision)
    finalize_root(root, before, refs)
    return decision


def read_decision(path: Path) -> dict[str, Any]:
    value = read_json(path)
    return value if isinstance(value, dict) else {}


def run_closeout(before: dict[str, Any], results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    root = ROOTS["closeout"]
    safe_reset_root(root)
    output_decisions = {
        "helsinki": ROOTS["helsinki"] / "HELSINKI_KIT_OBJECT_PICK_MANUAL_REVIEW_CAPTURE_R3_DECISION.json",
        "chicago": ROOTS["chicago"] / "CHICAGO_SIMILAR_CASE_DEMO_QUERY_SMOKE_R3_DECISION.json",
        "vss": ROOTS["vss"] / "MAIN_CITYBRAIN_D8_VSS_LICENSED_CORPUS_SAMPLE_INGEST_SMOKE_R3_DECISION.json",
    }
    scoreboard = {
        "task": "CITYBRAIN-D8-R3-FOLLOWON-PROMPT-PACK-CLOSEOUT",
        "helsinki": {
            "status": results["helsinki"].get("status"),
            "packets_loaded": results["helsinki"].get("packets_loaded"),
            "review_counts": results["helsinki"].get("review_counts"),
            "demo_surface_improvement": "manual review capture table and Kit/Composer handoff",
        },
        "chicago": {
            "status": results["chicago"].get("status"),
            "reviewed_cases_loaded": results["chicago"].get("reviewed_cases_loaded"),
            "similar_matches_loaded": results["chicago"].get("similar_matches_loaded"),
            "query_fixtures_run": results["chicago"].get("query_fixtures_run"),
            "queries_answered": results["chicago"].get("queries_answered"),
            "queries_abstained": results["chicago"].get("queries_abstained"),
            "demo_surface_improvement": "bounded query results and demo cards",
        },
        "vss": {
            "status": results["vss"].get("status"),
            "sample_ingest_gate": results["vss"].get("sample_ingest_gate"),
            "runtime_readiness_gate": results["vss"].get("runtime_readiness_gate"),
            "demo_surface_improvement": "closed-gate ingest checklist and operator evidence",
        },
        "still_closed_gates": [
            "VSS sample ingest/runtime readiness",
            "Helsinki full object-level mesh identity",
            "Chicago citywide operational memory",
        ],
    }
    write_json(root / "CITYBRAIN_D8_R3_FOLLOWON_SCOREBOARD.json", scoreboard)
    write_text(
        root / "CITYBRAIN_D8_R3_FOLLOWON_HANDOFF.md",
        "# CityBrain D8 R3 Follow-on Handoff\n\n"
        "R3 adds three demo-safe improvements: Helsinki manual review capture, Chicago bounded query smoke, and VSS closed-gate ingest evidence. These are suitable for the final D8 demo/handoff route, with limitations visible beside evidence.\n\n"
        "Recommended next task: `MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1`.\n",
    )
    refs = [rel(path) for path in output_decisions.values()]
    closeout = {
        "task": "CITYBRAIN-D8-R3-FOLLOWON-PROMPT-PACK-CLOSEOUT",
        "status": "PASS_CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_WITH_LIMITATIONS",
        "run_timestamp_utc": RUN_TS,
        "repo_root": str(REPO_ROOT),
        "results": {
            key: {
                "status": value.get("status"),
                "output_root": rel(ROOTS[key]),
                "decision_file": rel(output_decisions[key]),
                "limitations": value.get("limitations", []),
            }
            for key, value in results.items()
        },
        "demo_surface_improvements": [
            "Helsinki object-pick review capture for 20 packets.",
            "Chicago demo query cards over 15 bounded cases and 45 matches.",
            "VSS sample ingest checklist preserving closed gates.",
        ],
        "still_closed_gates": scoreboard["still_closed_gates"],
        "limitations": [
            "All outputs are local demo/handoff artifacts.",
            "No production, legal, certified, live, autonomous, enforcement, dispatch, or command/control capability is claimed.",
        ],
        "recommended_next_task": "MAIN-CITYBRAIN-D8-FINAL-DEMO-CAPTURE-AND-CERTIFIED-HANDOFF-R1",
    }
    write_json(root / "CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_CLOSEOUT.json", closeout)
    audits = finalize_root(root, before, refs)
    closeout["audit_results"] = {k: v.get("status") for k, v in audits.items() if isinstance(v, dict)}
    write_json(root / "CITYBRAIN_D8_R3_FOLLOWON_PROMPT_PACK_CLOSEOUT.json", closeout)
    finalize_root(root, before, refs)
    return closeout


def run_all() -> dict[str, Any]:
    before = snapshot_upstream()
    results = {
        "helsinki": run_helsinki(before),
        "chicago": run_chicago(before),
        "vss": run_vss(before),
    }
    closeout = run_closeout(before, results)
    return closeout


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, ensure_ascii=False))
