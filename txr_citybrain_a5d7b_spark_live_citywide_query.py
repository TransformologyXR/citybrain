from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(os.environ.get("CITYBRAIN_A5D7B_ROOT", "/home/txr/works/citybrain-a5d7b-live-citywide-query"))
DEFAULT_DB = DEFAULT_ROOT / "data" / "a8d2_citywide_map_v1" / "citywide_map_cache.sqlite"
DEFAULT_A4D3B_SUMMARY = DEFAULT_ROOT / "data" / "a4d3b_citywide_v1" / "A4D3B_CITYWIDE_SUMMARY.json"
DEFAULT_BUNDLE_DIR = DEFAULT_ROOT / "data" / "a5d7_citywide_briefings_v1"
DEFAULT_OUTPUT_DIR = DEFAULT_ROOT / "outputs"
DEFAULT_NIM_ENDPOINT = "http://127.0.0.1:8000/v1"
DEFAULT_NIM_MODEL = "meta/llama-3.1-8b-instruct"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8095

TASK_NAME = "A5-D7B live citywide operator query"
BOUNDARY_FALLBACK = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped "
    "depending on local harvest status. Discovery and projection counts are not claims about complete "
    "NYC history unless the dataset is marked full in the inventory."
)
HERO_BLOCK_KEY = "1-01060"
HERO_LEAK_TOKENS = {
    "1010607502",
    "1026676",
    "1366080",
    "event:us-nyc:dob_complaint:1366080",
    "GC-0037441",
    "S&E BRIDGE & SCAFFOLD LLC",
}
BOROUGH_NAMES = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(payload) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_block_key(value: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"[1-5]-\d{5}", value):
        raise ValueError("block must use active citywide block_key format like 1-01060")
    return value


def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def metadata(con: sqlite3.Connection) -> dict[str, str]:
    return {row["key"]: row["value"] for row in con.execute("SELECT key, value FROM metadata")}


def boundary_statement(summary_path: Path, con: sqlite3.Connection | None = None) -> str:
    if summary_path.exists():
        try:
            summary = read_json(summary_path)
            if summary.get("boundary_statement"):
                return str(summary["boundary_statement"])
        except (OSError, ValueError):
            pass
    if con is not None:
        try:
            meta = metadata(con)
            if meta.get("boundary_statement"):
                return str(meta["boundary_statement"])
        except sqlite3.Error:
            pass
    return BOUNDARY_FALLBACK


def parse_feature(row: sqlite3.Row) -> dict[str, Any]:
    try:
        return json.loads(row["feature_json"] or "{}")
    except ValueError:
        return {}


def top_contractors(row: sqlite3.Row, feature: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        contractors = json.loads(row["top_contractors_json"] or "[]")
    except ValueError:
        contractors = []
    if not contractors:
        props = feature.get("properties") or {}
        contractors = props.get("top_contractors") or []
    return [item for item in contractors if isinstance(item, dict)]


def block_row(db_path: Path, block_key: str) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, str]]:
    with connect(db_path) as con:
        meta = metadata(con)
        row = con.execute("SELECT * FROM blocks WHERE block_key = ?", (block_key,)).fetchone()
        if row is None:
            return None, {}, meta
        feature = parse_feature(row)
        payload = {key: row[key] for key in row.keys() if key not in {"feature_json", "top_contractors_json"}}
        payload["feature"] = feature
        payload["top_contractors"] = top_contractors(row, feature)
        props = feature.get("properties") or {}
        for key in ("dob_now_filing_count", "dob_permit_issuance_count", "borough_name", "geometry_label"):
            if key in props:
                payload[key] = props[key]
        return payload, feature, meta


def active_block_count(db_path: Path) -> int:
    with connect(db_path) as con:
        return int(con.execute("SELECT COUNT(*) FROM blocks").fetchone()[0])


def indexed_block_keys(bundle_dir: Path) -> list[str]:
    index_path = bundle_dir / "block_index.json"
    if not index_path.exists():
        return []
    try:
        payload = read_json(index_path)
    except (OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    return sorted(key for key in payload if re.fullmatch(r"[1-5]-\d{5}", str(key)))


def active_block_total(db_path: Path, bundle_dir: Path) -> int:
    keys = indexed_block_keys(bundle_dir)
    if keys:
        return len(keys)
    if db_path.exists():
        return active_block_count(db_path)
    return 0


def random_blocks(db_path: Path, count: int, seed: int = 7502, exclude: set[str] | None = None, bundle_dir: Path | None = None) -> list[str]:
    exclude = exclude or set()
    if bundle_dir is not None:
        rows = indexed_block_keys(bundle_dir)
    else:
        rows = []
    if not rows:
        with connect(db_path) as con:
            rows = [row[0] for row in con.execute("SELECT block_key FROM blocks ORDER BY block_key")]
    choices = [item for item in rows if item not in exclude]
    rng = random.Random(seed)
    rng.shuffle(choices)
    return choices[:count]


def citywide_summary(summary_path: Path) -> dict[str, Any]:
    if not summary_path.exists():
        return {}
    try:
        return read_json(summary_path)
    except (OSError, ValueError):
        return {}


def safe_block_name(block_key: str) -> str:
    return block_key.replace("/", "_")


def task2a_evidence_path(block_key: str, bundle_dir: Path) -> Path | None:
    index_path = bundle_dir / "block_index.json"
    if index_path.exists():
        try:
            entry = read_json(index_path).get(block_key)
            if isinstance(entry, dict) and entry.get("evidence"):
                candidate = bundle_dir / str(entry["evidence"])
                if candidate.exists():
                    return candidate
        except (OSError, ValueError, TypeError):
            pass
    candidates = [
        bundle_dir / "evidence_json" / f"block_{safe_block_name(block_key)}_evidence.json",
        bundle_dir / "evidence_bundles" / f"{safe_block_name(block_key)}.json",
        bundle_dir / f"{safe_block_name(block_key)}.json",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def normalize_task2a_bundle(bundle: dict[str, Any], block_key: str, row: dict[str, Any] | None, summary_path: Path) -> dict[str, Any]:
    row = row or {}
    subject = dict(bundle.get("subject") or {})
    metrics = dict(bundle.get("metrics") or {})
    governance = dict(bundle.get("governance") or {})
    boundary = governance.get("boundary_statement") or bundle.get("boundary_statement") or boundary_statement(summary_path)
    geometry_label = (
        governance.get("geometry_caveat")
        or bundle.get("geometry", {}).get("geometry_label")
        or "Adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block boundary polygons."
    )
    borough_code = str(subject.get("borough_code") or row.get("borough_code") or block_key.split("-", 1)[0])
    borough_name = str(subject.get("borough_name") or row.get("borough_name") or BOROUGH_NAMES.get(borough_code, borough_code))
    source_rows = {
        "dob_now_filings": int(metrics.get("dob_now_filing_count") or row.get("dob_now_filing_count") or 0),
        "dob_permit_issuance": int(metrics.get("dob_permit_issuance_count") or row.get("dob_permit_issuance_count") or 0),
    }
    counts = {
        "node_count": int(metrics.get("node_count") or row.get("node_count") or 0),
        "edge_count": int(metrics.get("edge_count") or row.get("edge_count") or 0),
        "complaint_count": int(metrics.get("complaint_count") or row.get("complaint_count") or 0),
        "critical_complaint_count": int(metrics.get("critical_complaint_count") or row.get("critical_complaint_count") or 0),
        "permit_count": int(metrics.get("permit_count") or row.get("permit_count") or 0),
        "source_rows": source_rows,
        "top_contractor_count": len(bundle.get("top_contractors") or []),
    }
    subject.update(
        {
            "subject_type": subject.get("subject_type") or subject.get("type") or "block",
            "subject_id": subject.get("subject_id") or f"block:us-nyc:tax_block:{block_key}",
            "block_key": block_key,
            "borough_code": borough_code,
            "borough_name": borough_name,
        }
    )
    bundle["task"] = TASK_NAME
    bundle["subject"] = subject
    bundle["subject_label"] = "hero_block" if block_key == HERO_BLOCK_KEY else "citywide_block"
    bundle["bundle_id"] = bundle.get("bundle_id") or bundle.get("evidence_id") or f"evidence_bundle:v1:block:{block_key}"
    bundle["boundary_statement"] = str(boundary)
    bundle["truth_policy"] = governance.get("truth_policy") or bundle.get(
        "truth_policy",
        "Counts and block facts are deterministic read-model facts from the accepted citywide projection cache. Narration may only restate evidence facts.",
    )
    bundle["counts"] = counts
    bundle["metrics"] = metrics
    bundle["geometry"] = {
        "bbox": subject.get("bbox") or [row.get("min_lon"), row.get("min_lat"), row.get("max_lon"), row.get("max_lat")],
        "centroid": subject.get("representative_point") or [row.get("centroid_lon"), row.get("centroid_lat")],
        "geometry_label": geometry_label,
    }
    bundle["source_refs"] = bundle.get("source_refs") or [
        {
            "source_dataset": "a5d7_citywide_briefings_v1.evidence_json",
            "source_id": f"block_{safe_block_name(block_key)}_evidence.json",
            "resolution_method": "block_index.json/block_key",
        }
    ]
    bundle["confidence_summary"] = bundle.get("confidence_summary") or [
        "subject:block_key=active_citywide_set",
        "party:per-edge confidence preserved in task-2a trace/evidence",
        "geometry:adapter_bbox",
    ]
    bundle["evidence_source"] = "synced_a5d7_task2a_evidence_bundle"
    bundle["flattened_value_hash"] = sha256_payload(flatten_values(bundle))
    bundle["normalized_hash"] = str(bundle.get("normalized_hash") or sha256_payload(bundle))
    return bundle


def build_cache_evidence_bundle(block_key: str, row: dict[str, Any], feature: dict[str, Any], meta: dict[str, str], summary_path: Path) -> dict[str, Any]:
    summary = citywide_summary(summary_path)
    boundary = boundary_statement(summary_path)
    borough_code = str(row.get("borough_code") or block_key.split("-", 1)[0])
    borough_name = str(row.get("borough_name") or BOROUGH_NAMES.get(borough_code, borough_code))
    top = row.get("top_contractors") or []
    source_counts = {
        "dob_now_filings": int(row.get("dob_now_filing_count") or 0),
        "dob_permit_issuance": int(row.get("dob_permit_issuance_count") or 0),
    }
    counts = {
        "node_count": int(row.get("node_count") or 0),
        "edge_count": int(row.get("edge_count") or 0),
        "complaint_count": int(row.get("complaint_count") or 0),
        "critical_complaint_count": int(row.get("critical_complaint_count") or 0),
        "permit_count": int(row.get("permit_count") or 0),
        "source_rows": source_counts,
        "top_contractor_count": len(top),
        "active_citywide_blocks": int(meta.get("total_blocks") or summary.get("citywide", {}).get("active_blocks") or 0),
    }
    answer_facts = [
        f"Block {block_key} is an active citywide DOB block in borough {borough_code} {borough_name}.",
        (
            f"Deterministic block counts: {counts['node_count']} graph nodes, {counts['edge_count']} graph edges, "
            f"{counts['complaint_count']} DOB complaint records, {counts['critical_complaint_count']} critical DOB complaints, "
            f"and {counts['permit_count']} permit records."
        ),
        (
            f"Source-row split: {source_counts['dob_now_filings']} DOB NOW filing rows and "
            f"{source_counts['dob_permit_issuance']} DOB Permit Issuance rows."
        ),
    ]
    if top:
        names = ", ".join(
            f"{item.get('name') or item.get('party_id')} ({int(item.get('edge_count') or 0)} edges)"
            for item in top[:3]
        )
        answer_facts.append(f"Top linked contractor/license parties by edge count: {names}.")
    else:
        answer_facts.append("Top linked contractor/license parties by edge count: none in this block cache row.")
    answer_facts.append(boundary)
    bundle = {
        "schema_version": "EvidenceBundle.v1",
        "bundle_id": f"evidence_bundle:v1:block:{block_key}",
        "task": TASK_NAME,
        "subject_label": "hero_block" if block_key == HERO_BLOCK_KEY else "citywide_block",
        "subject": {
            "subject_type": "block",
            "subject_id": f"block:us-nyc:tax_block:{block_key}",
            "block_key": block_key,
            "borough_code": borough_code,
            "borough_name": borough_name,
        },
        "tool_name": "citybrain_citywide_block_query",
        "query_type": "block_operational_briefing",
        "query": {"query_type": "block_operational_briefing", "block_key": block_key},
        "boundary_statement": boundary,
        "deterministic_plan": [
            "Validate block_key against the active citywide block cache.",
            "Read one block row from the local A8-D2 citywide SQLite cache.",
            "Use A4-D3b/A8-D2 block metrics as deterministic facts.",
            "Allow NIM to narrate only after deterministic facts are assembled and gated.",
        ],
        "counts": counts,
        "answer_facts": answer_facts,
        "confidence_summary": [
            "subject:block_key=active_citywide_set",
            "geometry:adapter_bbox",
            "party:top_contractors_from_block_cache",
        ],
        "provenance_summary": [
            "A4D3B_CITYWIDE_GPU_GRAPH_PROJECTION",
            "A8D2 citywide_map_cache.sqlite",
        ],
        "geometry": {
            "bbox": [row.get("min_lon"), row.get("min_lat"), row.get("max_lon"), row.get("max_lat")],
            "centroid": [row.get("centroid_lon"), row.get("centroid_lat")],
            "geometry_label": row.get("geometry_label")
            or "Adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block boundary polygons.",
        },
        "feature": feature,
        "top_contractors": top,
        "source_refs": [
            {
                "source_dataset": "a8d2_citywide_map_cache.blocks",
                "source_id": block_key,
                "resolution_method": "block_key",
            },
            {
                "source_dataset": "a4d3b_citywide_v1",
                "source_id": str(summary.get("a4d3b_run_hash") or meta.get("a4d3b_run_hash") or ""),
                "resolution_method": "citywide_projection_snapshot",
            },
        ],
        "truth_policy": "Counts and graph facts are computed by deterministic block-cache lookup. Narration may only restate this EvidenceBundle.",
        "evidence_source": "cache_fallback",
    }
    bundle["flattened_value_hash"] = sha256_payload(flatten_values(bundle))
    bundle["normalized_hash"] = sha256_payload(bundle)
    return bundle


def build_evidence_bundle(block_key: str, db_path: Path = DEFAULT_DB, summary_path: Path = DEFAULT_A4D3B_SUMMARY, bundle_dir: Path = DEFAULT_BUNDLE_DIR) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    block_key = clean_block_key(block_key)
    evidence_path = task2a_evidence_path(block_key, bundle_dir)
    row: dict[str, Any] | None = None
    feature: dict[str, Any] = {}
    meta: dict[str, str] = {}
    if db_path.exists():
        row, feature, meta = block_row(db_path, block_key)
    if evidence_path:
        try:
            bundle = normalize_task2a_bundle(read_json(evidence_path), block_key, row, summary_path)
            bundle["synced_evidence_path"] = str(evidence_path)
            return bundle, None
        except (OSError, ValueError, TypeError) as exc:
            return None, {
                "status": "FAIL",
                "http_status": 503,
                "error": f"active block evidence bundle could not be loaded: {exc}",
                "block_key": block_key,
                "rejected_before_deterministic_execution": False,
            }
    if row is None:
        return None, {
            "status": "FAIL",
            "http_status": 404,
            "error": "block_key not found in active citywide set",
            "block_key": block_key,
            "rejected_before_deterministic_execution": True,
        }
    if os.environ.get("CITYBRAIN_A5D7B_ALLOW_CACHE_FALLBACK") == "1":
        return build_cache_evidence_bundle(block_key, row, feature, meta, summary_path), None
    return None, {
        "status": "FAIL",
        "http_status": 503,
        "error": "active block is present, but synced A5D7 EvidenceBundle is missing",
        "block_key": block_key,
        "bundle_dir": str(bundle_dir),
        "rejected_before_deterministic_execution": False,
    }


def flatten_values(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, val in value.items():
            values.append(str(key))
            values.extend(flatten_values(val))
    elif isinstance(value, list):
        for item in value:
            values.extend(flatten_values(item))
    elif value is not None:
        values.append(str(value))
    return values


def deterministic_narration(bundle: dict[str, Any]) -> str:
    subject = bundle["subject"]
    counts = bundle["counts"]
    metrics = bundle.get("metrics") or {}
    sources = counts.get("source_rows") or {}
    top = bundle.get("top_contractors") or []
    if top:
        top_text = "; ".join(
            f"{item.get('name') or item.get('party_id')} with {int(item.get('edge_count') or 0)} linked edges"
            for item in top[:3]
        )
    else:
        top_text = "no contractor/license party in the block cache row"
    ratio_line = (
        f"Ratios: critical complaint share {float(metrics.get('critical_complaint_share') or 0):.3f}, "
        f"complaint-permit ratio {float(metrics.get('complaint_permit_ratio') or 0):.3f}, "
        f"DOB NOW/issuance ratio {float(metrics.get('now_issuance_ratio') or 0):.3f}."
    )
    lines = [
        (
            f"Operational briefing for block {subject['block_key']} in borough {subject['borough_code']} "
            f"{subject['borough_name']}."
        ),
        (
            f"The deterministic citywide block evidence reports {counts['node_count']} graph nodes, "
            f"{counts['edge_count']} graph edges, {counts['complaint_count']} DOB complaint records, "
            f"{counts['critical_complaint_count']} critical DOB complaints, and {counts['permit_count']} permit records."
        ),
        ratio_line,
        (
            f"Source-row split: {sources.get('dob_now_filings', 0)} DOB NOW filing rows and "
            f"{sources.get('dob_permit_issuance', 0)} DOB Permit Issuance rows."
        ),
    ]
    optimization = bundle.get("optimization") or {}
    if optimization.get("route_status"):
        resource = optimization.get("resource_id") or "unassigned resource"
        route_sequence = optimization.get("route_sequence")
        priority = optimization.get("priority_score")
        priority_text = f"{float(priority):.2f}" if priority is not None else "n/a"
        lines.append(
            f"Review context: A6-D1 route status {optimization.get('route_status')}, resource {resource}, "
            f"suggested order {route_sequence}, priority score {priority_text}."
        )
    lines.extend(
        [
            f"Top linked contractor/license parties by edge count: {top_text}.",
            f"Geometry caveat: {bundle['geometry']['geometry_label']}",
            f"Evidence boundary: {bundle['boundary_statement']}",
        ]
    )
    return "\n\n".join(lines)


def extract_facts(text: str) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []

    def emit(kind: str, value: str) -> None:
        value = value.strip().strip(".,;:()[]{}")
        if value and {"kind": kind, "value": value} not in facts:
            facts.append({"kind": kind, "value": value})

    for match in re.finditer(r"\b[1-5]-\d{5}\b", text):
        emit("block_key", match.group(0))
    for match in re.finditer(r"\b\d+\.\d+\b", text):
        emit("decimal", match.group(0))
    for match in re.finditer(r"(?<![\d.])\b\d+\b(?![\d.])", text):
        emit("integer", match.group(0))
    for match in re.finditer(r"\b(?:block|parcel|building|permit|event|party):[A-Za-z0-9:_./&+-]+", text):
        emit("canonical_id", match.group(0))
    for match in re.finditer(r"\b[A-Z][A-Z0-9&.,' -]{3,}\s+(?:LLC|INC|INC\.|CORP|COMPANY|GROUP|SCAFFOLD|CONSTRUCTION|CONSTRCTION|CONTRACTING|PLUMBING|DESIGN|CONSULTANTS|SAFETY)\b", text):
        emit("party_like_name", match.group(0).strip(" .,"))
    for match in re.finditer(r"\b(?:critical|block_key|adapter_bbox|license_number|name_hash)\b", text, re.I):
        emit("method_or_label", match.group(0))
    return facts


def allowed_tokens(bundle: dict[str, Any]) -> tuple[set[str], set[str], str]:
    values = flatten_values(bundle)
    strings: set[str] = set()
    numbers: set[str] = set()
    for value in values:
        text = str(value)
        strings.add(text)
        strings.add(text.lower())
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                numeric = float(value)
                for formatted in {f"{numeric:.0f}", f"{numeric:.2f}", f"{numeric:.3f}", f"{numeric:.6f}"}:
                    strings.add(formatted)
                    numbers.add(formatted)
            except (TypeError, ValueError):
                pass
        for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9:_./&,'+-]*", text):
            strings.add(token)
            strings.add(token.lower())
            if re.fullmatch(r"\d+(?:\.\d+)?", token):
                numbers.add(token)
                try:
                    numeric = float(token)
                    for formatted in {f"{numeric:.0f}", f"{numeric:.2f}", f"{numeric:.3f}", f"{numeric:.6f}"}:
                        strings.add(formatted)
                        numbers.add(formatted)
                except ValueError:
                    pass
    subject = bundle.get("subject") or {}
    block_key = str(subject.get("block_key") or "")
    for part in block_key.split("-"):
        if part:
            strings.add(part)
            numbers.add(part)
            if part.isdigit():
                strings.add(str(int(part)))
                numbers.add(str(int(part)))
    for phrase in [
        "Operational briefing",
        "DOB NOW",
        "DOB Permit Issuance",
        "DOB complaint",
        "critical DOB complaints",
        "graph nodes",
        "graph edges",
        "permit records",
        "Geometry caveat",
        "Evidence boundary",
        "Top linked contractor/license parties by edge count",
    ]:
        strings.add(phrase)
        strings.add(phrase.lower())
    return strings, numbers, canonical_json(bundle).lower()


def subset_grounded(bundle: dict[str, Any], text: str) -> dict[str, Any]:
    strings, numbers, blob = allowed_tokens(bundle)
    checked = extract_facts(text)
    unsupported = []
    for fact in checked:
        value = fact["value"]
        low = value.lower()
        if fact["kind"] in {"integer", "decimal"}:
            ok = value in numbers or value in strings
        else:
            ok = value in strings or low in strings or low in blob
        if not ok:
            unsupported.append(fact)
    return {
        "gate": "A5D7B-NARRATION-SUBSET-GROUNDED",
        "passed": not unsupported and bundle["boundary_statement"] in text,
        "checked_facts": checked,
        "unsupported_facts": unsupported,
        "boundary_statement_present": bundle["boundary_statement"] in text,
    }


def minimum_coverage(bundle: dict[str, Any], text: str) -> dict[str, Any]:
    subject = bundle["subject"]
    counts = bundle["counts"]
    sources = counts.get("source_rows") or {}
    required = {
        "block_key": subject["block_key"] in text,
        "borough": subject["borough_code"] in text and subject["borough_name"] in text,
        "node_count": str(counts["node_count"]) in text,
        "edge_count": str(counts["edge_count"]) in text,
        "complaint_count": str(counts["complaint_count"]) in text,
        "critical_complaint_count": str(counts["critical_complaint_count"]) in text and "critical" in text.lower(),
        "permit_count": str(counts["permit_count"]) in text,
        "dob_now_source_rows": str(sources.get("dob_now_filings", 0)) in text and "DOB NOW" in text,
        "dob_permit_source_rows": str(sources.get("dob_permit_issuance", 0)) in text and "DOB Permit Issuance" in text,
        "boundary": bundle["boundary_statement"] in text,
    }
    if bundle.get("top_contractors"):
        required["top_contractor"] = any(str(item.get("name") or item.get("party_id")) in text for item in bundle["top_contractors"][:3])
    else:
        required["top_contractor_absence"] = "no contractor/license party" in text
    missing = [key for key, ok in required.items() if not ok]
    return {
        "gate": "A5D7B-NARRATION-MINIMUM-COVERAGE",
        "passed": not missing,
        "required_items_present": [key for key, ok in required.items() if ok],
        "missing_items": missing,
    }


def anti_echo(text: str, structured_output: dict[str, Any]) -> dict[str, Any]:
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
        "gate": "A5D7B-NARRATION-NOT-ECHO",
        "passed": passed,
        "json_looking_ratio": round(json_ratio, 6),
        "key_value_pattern_ratio": round(key_value_ratio, 6),
        "structured_output_similarity": round(similarity, 6),
    }


def subject_isolation(bundle: dict[str, Any], text: str) -> dict[str, Any]:
    block_key = bundle["subject"]["block_key"]
    leaked = []
    if block_key != HERO_BLOCK_KEY:
        leaked = sorted(token for token in HERO_LEAK_TOKENS if token in text)
    return {
        "gate": "A5D7B-SUBJECT-ISOLATION",
        "passed": not leaked,
        "leaked_tokens": leaked,
    }


def health_nim(nim_endpoint: str = DEFAULT_NIM_ENDPOINT) -> dict[str, Any]:
    url = nim_endpoint.rstrip("/")
    if not url.endswith("/models"):
        url = f"{url}/models" if url.endswith("/v1") else f"{url}/v1/models"
    started = utc_now()
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "status": "PASS",
            "started_at": started,
            "finished_at": utc_now(),
            "endpoint": nim_endpoint,
            "models_url": url,
            "models": payload,
        }
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return {
            "status": "FAIL",
            "started_at": started,
            "finished_at": utc_now(),
            "endpoint": nim_endpoint,
            "models_url": url,
            "error": str(exc),
        }


def nim_exact_echo(narration: str, bundle: dict[str, Any], nim_endpoint: str, nim_model: str) -> tuple[str, dict[str, Any]]:
    health = health_nim(nim_endpoint)
    if health["status"] != "PASS":
        return narration, {
            "status": "FAIL",
            "mode": "nim_unhealthy",
            "health": health,
            "used_text": "deterministic_fallback",
        }
    url = nim_endpoint.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions" if url.endswith("/v1") else f"{url}/v1/chat/completions"
    request_payload = {
        "model": nim_model,
        "temperature": 0,
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": "You narrate deterministic city evidence only. Never add facts."},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "instruction": "Return deterministic_narration exactly, byte-for-byte. Do not add facts.",
                        "deterministic_narration": narration,
                        "evidence_hash": bundle.get("normalized_hash"),
                        "boundary_statement": bundle.get("boundary_statement"),
                    },
                    sort_keys=True,
                    ensure_ascii=False,
                ),
            },
        ],
    }
    started = utc_now()
    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = str(payload["choices"][0]["message"]["content"])
        exact = text.strip() == narration.strip()
        return (text if exact else narration), {
            "status": "PASS",
            "mode": "nim",
            "endpoint": nim_endpoint,
            "model": nim_model,
            "started_at": started,
            "finished_at": utc_now(),
            "health": health,
            "response_hash": sha256_payload(payload),
            "used_text": "nim_exact_echo" if exact else "deterministic_guarded_fallback",
            "warnings": [] if exact else ["NIM response was not an exact grounded echo; deterministic narration used."],
        }
    except (OSError, urllib.error.URLError, KeyError, IndexError, ValueError) as exc:
        return narration, {
            "status": "FAIL",
            "mode": "nim_error_fallback_deterministic",
            "endpoint": nim_endpoint,
            "model": nim_model,
            "started_at": started,
            "finished_at": utc_now(),
            "health": health,
            "error": str(exc),
            "used_text": "deterministic_fallback",
        }


def execute_block_query(
    block_key: str,
    mode: str = "live",
    db_path: Path = DEFAULT_DB,
    summary_path: Path = DEFAULT_A4D3B_SUMMARY,
    bundle_dir: Path = DEFAULT_BUNDLE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    nim_endpoint: str = DEFAULT_NIM_ENDPOINT,
    nim_model: str = DEFAULT_NIM_MODEL,
    raw_request: str | None = None,
) -> dict[str, Any]:
    try:
        block_key = clean_block_key(block_key)
    except ValueError as exc:
        return {
            "status": "FAIL",
            "http_status": 404,
            "error": str(exc),
            "block_key": str(block_key),
            "rejected_before_deterministic_execution": True,
            "deterministic_executed": False,
        }
    bundle, rejection = build_evidence_bundle(block_key, db_path, summary_path, bundle_dir)
    if rejection is not None:
        rejection["deterministic_executed"] = False
        return rejection
    assert bundle is not None
    deterministic = deterministic_narration(bundle)
    nim_text = deterministic
    nim_call = {"status": "SKIPPED", "mode": "precomputed"}
    if mode == "live":
        nim_text, nim_call = nim_exact_echo(deterministic, bundle, nim_endpoint, nim_model)
    structured = {
        "task": TASK_NAME,
        "status": "PASS",
        "mode": mode,
        "subject_id": bundle["subject"]["subject_id"],
        "block_key": block_key,
        "boundary_statement": bundle["boundary_statement"],
        "deterministic_answer": {
            "counts": bundle["counts"],
            "top_contractors": bundle.get("top_contractors", [])[:3],
            "geometry": bundle.get("geometry"),
            "evidence_bundle_hash": bundle.get("normalized_hash"),
        },
        "evidence_bundle": bundle,
        "narration": nim_text,
        "nim_call": nim_call,
        "raw_request": raw_request or f"what is going on at block {block_key}",
        "generated_at": utc_now(),
    }
    grounding = subset_grounded(bundle, nim_text)
    coverage = minimum_coverage(bundle, nim_text)
    echo = anti_echo(nim_text, structured)
    isolation = subject_isolation(bundle, nim_text)
    gates = [grounding, coverage, echo, isolation]
    structured["grounding_result"] = {
        "status": "PASS" if all(item["passed"] for item in gates) else "FAIL",
        "gates": gates,
    }
    structured["status"] = "PASS" if structured["grounding_result"]["status"] == "PASS" and (mode != "live" or nim_call.get("status") == "PASS") else "FAIL"
    structured["http_status"] = 200 if structured["status"] == "PASS" else 502
    structured["deterministic_executed"] = True
    structured["output_hash"] = sha256_payload(structured)

    safe_key = block_key.replace("-", "_")
    write_json(bundle_dir / "evidence_bundles" / f"{block_key}.json", bundle)
    run_dir = output_dir / "runs" / f"{safe_key}_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    write_json(run_dir / "evidence_bundle.json", bundle)
    write_text(run_dir / "narration.md", nim_text + "\n")
    write_json(run_dir / "response.json", structured)
    return structured


class CitywideHandler(BaseHTTPRequestHandler):
    db_path: Path = DEFAULT_DB
    summary_path: Path = DEFAULT_A4D3B_SUMMARY
    bundle_dir: Path = DEFAULT_BUNDLE_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    nim_endpoint: str = DEFAULT_NIM_ENDPOINT
    nim_model: str = DEFAULT_NIM_MODEL

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path in {"/health", "/api/health"}:
                health = health_nim(self.nim_endpoint)
                payload = {
                    "status": "PASS",
                    "task": TASK_NAME,
                    "db_exists": self.db_path.exists(),
                    "bundle_dir": str(self.bundle_dir),
                    "block_index_exists": (self.bundle_dir / "block_index.json").exists(),
                    "active_blocks": active_block_total(self.db_path, self.bundle_dir),
                    "nim_health": health,
                }
                self.send_json(200, payload)
                return
            if parsed.path in {"/briefing", "/api/briefing"}:
                block_key = params.get("block", params.get("block_key", [""]))[0]
                mode = params.get("mode", ["live"])[0]
                if mode not in {"live", "precomputed"}:
                    self.send_json(400, {"status": "FAIL", "error": "mode must be live or precomputed"})
                    return
                payload = execute_block_query(
                    block_key,
                    mode=mode,
                    db_path=self.db_path,
                    summary_path=self.summary_path,
                    bundle_dir=self.bundle_dir,
                    output_dir=self.output_dir,
                    nim_endpoint=self.nim_endpoint,
                    nim_model=self.nim_model,
                    raw_request=params.get("q", [None])[0],
                )
                self.send_json(int(payload.get("http_status") or 500), payload)
                return
            if parsed.path == "/random-blocks":
                count = int(params.get("count", ["5"])[0])
                self.send_json(200, {"status": "PASS", "blocks": random_blocks(self.db_path, count, exclude={HERO_BLOCK_KEY}, bundle_dir=self.bundle_dir)})
                return
            self.send_json(404, {"status": "FAIL", "error": "not found"})
        except Exception as exc:  # explicit for harnesses
            self.send_json(500, {"status": "FAIL", "error": str(exc), "path": parsed.path})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


def serve(args: argparse.Namespace) -> int:
    CitywideHandler.db_path = Path(args.db)
    CitywideHandler.summary_path = Path(args.summary)
    CitywideHandler.bundle_dir = Path(args.bundle_dir)
    CitywideHandler.output_dir = Path(args.output_dir)
    CitywideHandler.nim_endpoint = args.nim_endpoint
    CitywideHandler.nim_model = args.nim_model
    server = ThreadingHTTPServer((args.host, args.port), CitywideHandler)
    print(f"{TASK_NAME} listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()
    return 0


def export_index(db_path: Path, bundle_dir: Path, summary_path: Path) -> dict[str, Any]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as con:
        meta = metadata(con)
        rows = con.execute(
            "SELECT block_key, borough_code, node_count, edge_count, complaint_count, critical_complaint_count, permit_count FROM blocks ORDER BY block_key"
        ).fetchall()
    index = {
        "task": TASK_NAME,
        "status": "PASS",
        "generated_at": utc_now(),
        "boundary_statement": boundary_statement(summary_path),
        "active_block_count": len(rows),
        "map_cache_sha256": sha256_file(db_path) if db_path.exists() else None,
        "blocks": [dict(row) for row in rows],
        "metadata": meta,
    }
    index["index_hash"] = sha256_payload(index)
    write_json(bundle_dir / "active_blocks_index.json", index)
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--summary", default=str(DEFAULT_A4D3B_SUMMARY))
    parser.add_argument("--bundle-dir", default=str(DEFAULT_BUNDLE_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--nim-endpoint", default=DEFAULT_NIM_ENDPOINT)
    parser.add_argument("--nim-model", default=DEFAULT_NIM_MODEL)
    parser.add_argument("--block", default=None)
    parser.add_argument("--mode", choices=["live", "precomputed"], default="live")
    parser.add_argument("--random-blocks", type=int, default=0)
    parser.add_argument("--export-index", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if args.serve:
        return serve(args)
    if args.export_index:
        index = export_index(Path(args.db), Path(args.bundle_dir), Path(args.summary))
        print(pretty_json(index))
        return 0
    if args.random_blocks:
        print(pretty_json({"status": "PASS", "blocks": random_blocks(Path(args.db), args.random_blocks, exclude={HERO_BLOCK_KEY}, bundle_dir=Path(args.bundle_dir))}))
        return 0
    if args.block:
        result = execute_block_query(
            args.block,
            mode=args.mode,
            db_path=Path(args.db),
            summary_path=Path(args.summary),
            bundle_dir=Path(args.bundle_dir),
            output_dir=Path(args.output_dir),
            nim_endpoint=args.nim_endpoint,
            nim_model=args.nim_model,
        )
        print(pretty_json(result))
        return 0 if result.get("status") == "PASS" else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
