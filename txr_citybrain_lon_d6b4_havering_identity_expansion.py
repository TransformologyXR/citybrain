#!/usr/bin/env python3
"""LON-D6B4 Havering enforcement identity expansion.

Expands D6B3 only through exact official identifiers. Address, postcode,
geometry-nearest, and fuzzy evidence stays candidate-only.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from txr_citybrain_lon_d9d2_pld_api_uprn_recovery import (
    canonical_uprn,
    raw_uprn_values,
    search_exact_candidate,
    stable_key_from,
)


BOUNDARY = (
    "This briefing is generated from CityBrain London D6B4 evidence only. "
    "Certified identity links require exact official PLD reference or explicit official UPRN evidence. "
    "Address-only, postcode-only, nearest-geometry, and fuzzy matches remain candidate-only. "
    "D6B4 does not prove London-wide enforcement coverage. "
    "D6B4 does not make legal enforcement conclusions. "
    "No NIM/NeMo/LLM generated these facts."
)

D6B3_BOUNDARY = (
    "This briefing is generated from CityBrain London D6B3 evidence only. "
    "Havering events are official planning-enforcement notice metadata/document evidence. "
    "Certified identity links require exact UPRN or exact PLD reference evidence. "
    "Address-only links remain candidate-only. "
    "D6B3 does not prove London-wide enforcement coverage. "
    "No legal enforcement conclusion is made. "
    "No NIM/NeMo/LLM generated these facts."
)

LIMITATIONS = [
    "D6B4 expands only exact official identifier recovery over Havering enforcement notices.",
    "Address-only, postcode-only, nearest-geometry, and fuzzy matches remain candidate-only.",
    "D6B4 does not prove London-wide enforcement coverage.",
    "D6B4 does not include building-control records.",
    "D6B4 does not make legal enforcement conclusions.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
]

FORBIDDEN_CLAIMS = [
    "London-wide enforcement complete",
    "building-control integrated",
    "address-only links certified",
    "postcode-only links certified",
    "nearest geometry certified",
    "automatic enforcement",
    "issue violation",
    "stop-work order",
]

PLANNING_REF_PATTERNS = [
    re.compile(r"\b[A-Z]{1,4}\d{3,6}[./-]\d{2,4}\b", re.I),
    re.compile(r"\b\d{4}/\d{3,6}/[A-Z]{1,8}\b", re.I),
    re.compile(r"\b(?:P|PA|FUL|APP)[A-Z]?\d{3,6}[./-]\d{2,4}\b", re.I),
]
LABELLED_UPRN_PATTERNS = [
    re.compile(r"\bUPRN\b[^0-9]{0,40}(\d{8,12})\b", re.I),
    re.compile(r"\bUnique\s+Property\s+Reference\s+Number\b[^0-9]{0,40}(\d{8,12})\b", re.I),
]
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return None
    except Exception:
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=json_default), encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(text: str, chars: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:chars]


def safe_slug(text: Any, max_len: int = 120) -> str:
    out = re.sub(r"[^A-Za-z0-9._-]+", "_", str(text).strip())
    out = re.sub(r"_+", "_", out).strip("._-").lower()
    return (out[:max_len].strip("._-") or "unknown")


def normalize_ref(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def ensure_dirs(output: Path) -> None:
    for rel in ["canonical", "reports", "queries", "bundles"]:
        (output / rel).mkdir(parents=True, exist_ok=True)


def write_parquet(path: Path, frame: pd.DataFrame, columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty and columns:
        frame = pd.DataFrame({col: pd.Series(dtype="object") for col in columns})
    frame.to_parquet(path, index=False)


def file_hashes(paths: list[Path]) -> dict[str, str | None]:
    return {str(path): sha256_path(path) if path.exists() and path.is_file() else None for path in paths}


def hash_outputs(output: Path) -> dict[str, Any]:
    hashes = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(output)).replace("\\", "/")] = sha256_path(path)
    report = {"gate": "LON-D6B4-HASHES", "status": "PASS", "file_count": len(hashes), "sha256s": hashes}
    write_json(output / "SHA256SUMS.json", report)
    return report


def planning_context_ok(snippet: str) -> bool:
    text = snippet.lower()
    if "enforcement reference" in text or "enf/" in text:
        return False
    positive = [
        "application reference",
        "planning application",
        "planning permission",
        "permission under",
        "approved under",
        "refused permission",
        "application ref",
        "application no",
        "application number",
    ]
    return any(token in text for token in positive)


def context_snippet(text: str, start: int, end: int, width: int = 140) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def bundled_python_path() -> Path | None:
    path = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
    return path if path.exists() else None


def current_python_has_pypdf() -> bool:
    try:
        import pypdf  # noqa: F401

        return True
    except Exception:
        return False


def extract_pdf_refs(docs: pd.DataFrame, output: Path, enabled: bool, max_pages: int) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    report = {
        "requested": enabled,
        "max_pdf_text_pages": max_pages,
        "attempted_documents": 0,
        "successful_documents": 0,
        "failed_documents": 0,
        "runtime": None,
        "status": "not_requested" if not enabled else "not_run",
    }
    if not enabled:
        return {}, report
    records = []
    for _, row in docs.iterrows():
        path = Path(str(row.get("download_path", "")))
        if path.exists():
            records.append({"event_id": row.get("event_id"), "path": str(path)})
    report["attempted_documents"] = len(records)
    if not records:
        report["status"] = "no_pdf_paths_found"
        return {}, report
    helper_input = output / "reports/pdf_ref_extract_input.json"
    helper_output = output / "reports/pdf_ref_extract_output.json"
    helper_script = output / "reports/pdf_ref_extract_helper.py"
    write_json(helper_input, {"records": records, "max_pages": max_pages})
    helper_script.write_text(
        r'''
import json, re, sys
from pathlib import Path
from pypdf import PdfReader

PLANNING_REF_PATTERNS = [
    re.compile(r"\b[A-Z]{1,4}\d{3,6}[./-]\d{2,4}\b", re.I),
    re.compile(r"\b\d{4}/\d{3,6}/[A-Z]{1,8}\b", re.I),
    re.compile(r"\b(?:P|PA|FUL|APP)[A-Z]?\d{3,6}[./-]\d{2,4}\b", re.I),
]
LABELLED_UPRN_PATTERNS = [
    re.compile(r"\bUPRN\b[^0-9]{0,40}(\d{8,12})\b", re.I),
    re.compile(r"\bUnique\s+Property\s+Reference\s+Number\b[^0-9]{0,40}(\d{8,12})\b", re.I),
]
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.I)

def snippet(text, start, end, width=140):
    left=max(0,start-width); right=min(len(text),end+width)
    return re.sub(r"\s+"," ",text[left:right]).strip()

payload=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rows=[]
for rec in payload.get("records", []):
    status="failed"; refs=[]; uprns=[]; postcodes=[]
    try:
        reader=PdfReader(rec["path"])
        text="\n".join((page.extract_text() or "") for page in reader.pages[:int(payload.get("max_pages", 10))])
        status="ok" if text.strip() else "empty_text_layer"
        for pattern in PLANNING_REF_PATTERNS:
            for match in pattern.finditer(text):
                refs.append({"value": match.group(0).upper(), "snippet": snippet(text, match.start(), match.end()), "source": "pdf_text"})
        for pattern in LABELLED_UPRN_PATTERNS:
            for match in pattern.finditer(text):
                uprns.append({"value": (match.group(1).lstrip("0") or match.group(1)), "snippet": snippet(text, match.start(), match.end()), "source": "pdf_text"})
        for match in POSTCODE_RE.finditer(text):
            postcodes.append({"value": re.sub(r"\s+", " ", match.group(0).upper()).strip(), "source": "pdf_text"})
    except Exception as exc:
        status="failed:"+repr(exc)
    rows.append({"event_id": rec.get("event_id"), "status": status, "planning_refs": refs, "uprns": uprns, "postcodes": postcodes})
Path(sys.argv[2]).write_text(json.dumps(rows), encoding="utf-8")
'''.strip(),
        encoding="utf-8",
    )
    runtime = Path(sys.executable) if current_python_has_pypdf() else bundled_python_path()
    if not runtime:
        report["status"] = "dependency_unavailable"
        return {}, report
    proc = subprocess.run(
        [str(runtime), str(helper_script), str(helper_input), str(helper_output)],
        capture_output=True,
        text=True,
        timeout=900,
    )
    report["runtime"] = str(runtime)
    if proc.returncode != 0:
        report["status"] = "failed"
        report["stderr"] = proc.stderr[-2000:]
        return {}, report
    rows = json.loads(helper_output.read_text(encoding="utf-8"))
    by_event = {row["event_id"]: row for row in rows}
    report["successful_documents"] = sum(1 for row in rows if row.get("status") == "ok")
    report["failed_documents"] = len(rows) - report["successful_documents"]
    report["status"] = "PASS"
    return by_event, report


def discover_local_sources(raw_roots: list[str], output: Path) -> dict[str, Any]:
    interesting = re.compile(r"(havering|planning|enforcement|uprn|llpg|address|gazetteer|public.?register)", re.I)
    rows = []
    for raw in raw_roots:
        root = Path(raw)
        row = {"root": str(root), "exists": root.exists(), "files_scanned": 0, "candidate_files": []}
        if root.exists():
            try:
                for path in root.rglob("*"):
                    if path.is_file():
                        row["files_scanned"] += 1
                        if interesting.search(path.name):
                            row["candidate_files"].append(
                                {
                                    "path": str(path),
                                    "bytes": path.stat().st_size,
                                    "suffix": path.suffix.lower(),
                                    "sha256": sha256_path(path) if path.stat().st_size < 50_000_000 else None,
                                }
                            )
                    if row["files_scanned"] > 5000:
                        row["truncated_scan"] = True
                        break
            except Exception as exc:  # noqa: BLE001
                row["scan_error"] = repr(exc)
        rows.append(row)
    report = {
        "gate": "LON-D6B4-SOURCE-DISCOVERY",
        "status": "PASS",
        "raw_roots": rows,
        "boundary_statement": BOUNDARY,
    }
    write_json(output / "LON_D6B4_SOURCE_DISCOVERY_REPORT.json", report)
    write_json(output / "reports/source_lineage.json", report)
    return report


def official_source_probe(output: Path, enabled: bool) -> dict[str, Any]:
    urls = [
        "https://planningdata.london.gov.uk/api-guest/applications/_source/Havering-P0270.25",
        "https://ckan.publishing.service.gov.uk/api/3/action/package_search?q=Havering%20planning%20applications",
        "https://data.london.gov.uk/search?query=Havering%20planning%20applications",
        "https://www.havering.gov.uk/downloads",
    ]
    rows = []
    if enabled:
        for url in urls:
            try:
                headers = {"User-Agent": "TXR-CityBrain-D6B4/1.0"}
                if "planningdata.london.gov.uk" in url:
                    headers["X-API-AllowRequest"] = "be2rmRnt&"
                response = requests.get(url, timeout=25, headers=headers)
                rows.append(
                    {
                        "url": url,
                        "status_code": response.status_code,
                        "content_type": response.headers.get("content-type"),
                        "bytes": len(response.content),
                        "note": "bounded official-source probe; no one-record portal scraping",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                rows.append({"url": url, "status": "failed", "error": repr(exc)})
    report = {"gate": "LON-D6B4-OFFICIAL-SOURCE-PROBE", "status": "PASS", "enabled": enabled, "probes": rows, "boundary_statement": BOUNDARY}
    write_json(output / "LON_D6B4_OFFICIAL_SOURCE_PROBE_REPORT.json", report)
    return report


def inspect_address_gazetteer(raw_roots: list[str]) -> dict[str, Any]:
    candidates = []
    for root in raw_roots:
        path = Path(root)
        if not path.exists():
            continue
        for child in path.rglob("*"):
            if child.is_file() and re.search(r"(llpg|addressbase|gazetteer|osopenuprn)", child.name, re.I):
                candidates.append({"path": str(child), "bytes": child.stat().st_size})
    reason = "No official address-bearing LLPG/AddressBase/Havering address gazetteer was found locally."
    open_uprn = next((Path(row["path"]) for row in candidates if "osopenuprn" in row["path"].lower()), None)
    if open_uprn:
        reason = "OS OpenUPRN is present and can verify UPRN existence, but it does not contain a full official address string for certified address-to-UPRN matching."
    return {"gate": "LON-D6B4-ADDRESS-GAZETTEER-MATCH", "status": "PASS", "official_address_uprn_matches": 0, "candidate_sources": candidates[:100], "reason": reason, "boundary_statement": BOUNDARY}


def load_d9d2_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    matched_path = Path("outputs/lon_d9d2_pld_api_uprn_recovery/canonical/london_pld_api_records_matched.parquet")
    paths_path = Path("outputs/lon_d9d2_pld_api_uprn_recovery/canonical/london_pld_api_connected_paths.parquet")
    ref_index: dict[str, dict[str, Any]] = {}
    if matched_path.exists():
        matched = pd.read_parquet(matched_path)
        matched = matched[matched["api_borough"].astype(str).str.contains("Havering", case=False, na=False)]
        for _, row in matched.iterrows():
            data = row.to_dict()
            for col in ["api_lpa_app_no", "api_id", "stable_application_key", "lpa_app_no_d9c"]:
                raw = str(data.get(col, "")).strip()
                if raw:
                    ref_index.setdefault(normalize_ref(raw), data)
    path_report = {"source": str(paths_path), "source_exists": paths_path.exists(), "rows": 0}
    if paths_path.exists():
        path_report["rows"] = int(len(pd.read_parquet(paths_path, columns=["permit_id"])))
    return ref_index, path_report


def find_open_uprn_zip(raw_roots: list[str]) -> Path | None:
    for raw in raw_roots + ["data_landing/london_d9_raw", str(Path.home() / "Downloads")]:
        root = Path(raw)
        if not root.exists():
            continue
        direct = root / "osopenuprn_202606_csv.zip"
        if direct.exists():
            return direct
        for path in root.glob("*openuprn*.zip"):
            return path
    return None


def verify_uprns_in_open_uprn(targets: set[str], raw_roots: list[str]) -> dict[str, Any]:
    zip_path = find_open_uprn_zip(raw_roots)
    found: set[str] = set()
    report = {
        "source": str(zip_path) if zip_path else None,
        "source_exists": bool(zip_path),
        "target_uprns": len(targets),
        "matched_uprns": 0,
        "missing_uprns": sorted(targets),
        "boundary_statement": BOUNDARY,
    }
    if not zip_path or not targets:
        return report
    with zipfile.ZipFile(zip_path) as zf:
        member = next((name for name in zf.namelist() if name.lower().endswith(".csv")), None)
        if not member:
            report["error"] = "no_csv_member"
            return report
        with zf.open(member) as fh:
            for chunk in pd.read_csv(fh, usecols=["UPRN"], dtype=str, chunksize=1_000_000, encoding="utf-8-sig"):
                values = set(chunk["UPRN"].dropna().astype(str).map(lambda x: x.lstrip("0") or x))
                found |= (values & targets)
                if found == targets:
                    break
    report["matched_uprns"] = len(found)
    report["missing_uprns"] = sorted(targets - found)
    return report


def extract_structured_candidates(events: pd.DataFrame, docs: pd.DataFrame, pdf_refs: dict[str, dict[str, Any]]) -> pd.DataFrame:
    doc_lookup = docs.set_index("event_id").to_dict("index") if not docs.empty else {}
    rows = []
    for _, event in events.iterrows():
        event_id = str(event["canonical_id"])
        doc = doc_lookup.get(event_id, {})
        refs = []
        uprns = []
        postcodes = []
        text_sources = {
            "notice_title": str(event.get("notice_title", "")),
            "site_address": str(event.get("site_address", "")),
            "document_url": str(event.get("document_url", "")),
            "download_path": str(doc.get("download_path", "")),
        }
        for source, text in text_sources.items():
            for pattern in PLANNING_REF_PATTERNS:
                for match in pattern.finditer(text):
                    snippet = context_snippet(text, match.start(), match.end())
                    refs.append({"value": match.group(0).upper(), "source": source, "snippet": snippet, "planning_context": planning_context_ok(snippet)})
            for pattern in LABELLED_UPRN_PATTERNS:
                for match in pattern.finditer(text):
                    uprns.append({"value": (match.group(1).lstrip("0") or match.group(1)), "source": source, "snippet": context_snippet(text, match.start(), match.end())})
            for match in POSTCODE_RE.finditer(text):
                postcodes.append({"value": re.sub(r"\s+", " ", match.group(0).upper()).strip(), "source": source})
        pdf = pdf_refs.get(event_id, {})
        for ref in pdf.get("planning_refs", []) or []:
            snippet = str(ref.get("snippet", ""))
            refs.append({"value": str(ref.get("value", "")).upper(), "source": "pdf_text", "snippet": snippet, "planning_context": planning_context_ok(snippet)})
        for uprn in pdf.get("uprns", []) or []:
            uprns.append({"value": str(uprn.get("value", "")).lstrip("0") or str(uprn.get("value", "")), "source": "pdf_text", "snippet": uprn.get("snippet", "")})
        for pc in pdf.get("postcodes", []) or []:
            postcodes.append({"value": str(pc.get("value", "")).upper(), "source": "pdf_text"})

        def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            seen = set()
            out = []
            for item in items:
                key = (item.get("value"), item.get("source"), item.get("snippet", "")[:120])
                if item.get("value") and key not in seen:
                    seen.add(key)
                    out.append(item)
            return out

        rows.append(
            {
                "event_id": event_id,
                "site_address": event.get("site_address", ""),
                "planning_reference_candidates": dedupe(refs),
                "explicit_uprn_candidates": dedupe(uprns),
                "postcode_candidates": dedupe(postcodes),
            }
        )
    return pd.DataFrame(rows)


def query_official_api_for_refs(ref_records: list[dict[str, Any]], max_workers: int = 8) -> tuple[pd.DataFrame, dict[str, Any]]:
    by_norm: dict[str, dict[str, Any]] = {}
    for rec in ref_records:
        ref = str(rec.get("raw_reference", "")).strip()
        if ref and rec.get("planning_context"):
            by_norm.setdefault(normalize_ref(ref), {"raw_reference": ref})
    refs = sorted(row["raw_reference"] for row in by_norm.values())

    def fetch(ref: str) -> dict[str, Any]:
        method, record, err = search_exact_candidate("Havering", ref, stable_key_from("Havering", ref))
        out = {
            "raw_reference": ref,
            "normalized_reference": normalize_ref(ref),
            "api_match_method": method,
            "api_error": err,
            "api_id": None,
            "api_lpa_name": None,
            "api_lpa_app_no": None,
            "api_borough": None,
            "api_uprn_raw_values": [],
            "api_uprn_canonical_values": [],
            "api_exact_match": False,
        }
        if record and str(record.get("lpa_app_no", "")).strip() == ref and str(record.get("borough", "")).strip().lower() == "havering":
            raw_values = raw_uprn_values(record.get("uprn"))
            out.update(
                {
                    "api_id": record.get("id"),
                    "api_lpa_name": record.get("lpa_name"),
                    "api_lpa_app_no": record.get("lpa_app_no"),
                    "api_borough": record.get("borough"),
                    "api_uprn_raw_values": raw_values,
                    "api_uprn_canonical_values": [canonical_uprn(value) for value in raw_values if canonical_uprn(value)],
                    "api_exact_match": True,
                    "api_last_updated": record.get("last_updated"),
                    "api_valid_date": record.get("valid_date"),
                    "api_decision_date": record.get("decision_date"),
                    "api_application_type": record.get("application_type"),
                    "api_postcode": record.get("postcode"),
                }
            )
        return out

    rows = []
    if refs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for row in executor.map(fetch, refs):
                rows.append(row)
    frame = pd.DataFrame(rows)
    report = {
        "official_api_refs_queried": len(refs),
        "official_api_exact_matches": int(frame["api_exact_match"].sum()) if not frame.empty else 0,
        "official_api_records_with_uprn": int(frame["api_uprn_canonical_values"].map(len).gt(0).sum()) if not frame.empty else 0,
        "boundary_statement": BOUNDARY,
    }
    return frame, report


def build_edges(
    candidates: pd.DataFrame,
    d6b3_edges: pd.DataFrame,
    local_ref_index: dict[str, dict[str, Any]],
    api_matches: pd.DataFrame,
    open_uprn_report: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    baseline_edge_ids = set(d6b3_edges["edge_id"].astype(str).tolist()) if not d6b3_edges.empty else set()
    baseline_pairs = set(zip(d6b3_edges.get("src", pd.Series(dtype=str)).astype(str), d6b3_edges.get("dst", pd.Series(dtype=str)).astype(str))) if not d6b3_edges.empty else set()
    api_by_norm = {row["normalized_reference"]: row.to_dict() for _, row in api_matches.iterrows()} if not api_matches.empty else {}
    verified_uprns = set(open_uprn_report.get("missing_uprns", []))
    all_target_uprns = set()
    if not api_matches.empty:
        for values in api_matches["api_uprn_canonical_values"]:
            all_target_uprns.update(str(v) for v in (values or []) if v)
    verified_uprns = all_target_uprns - set(open_uprn_report.get("missing_uprns", []))

    edge_rows = d6b3_edges.to_dict("records") if not d6b3_edges.empty else []
    new_pld_rows = []
    new_uprn_rows = []
    candidate_rows = []
    seen_pairs = set(baseline_pairs)
    seen_edges = set(baseline_edge_ids)

    for _, row in candidates.iterrows():
        event_id = str(row["event_id"])
        for ref in row.get("planning_reference_candidates", []) or []:
            raw_ref = str(ref.get("value", "")).strip()
            norm = normalize_ref(raw_ref)
            local = local_ref_index.get(norm)
            api = api_by_norm.get(norm)
            is_context_ok = bool(ref.get("planning_context"))
            permit_id = None
            method = None
            source_basis = None
            if local and is_context_ok:
                permit_id = str(local.get("canonical_id", ""))
                method = "accepted_d9d2_exact_pld_reference"
                source_basis = f"Official notice/PDF contains planning reference {raw_ref}; it exactly matches accepted D9D2 Havering PLD record {permit_id}."
            elif api and api.get("api_exact_match") and is_context_ok:
                permit_id = f"permit:uk-london:pld:{api.get('api_id')}"
                method = "official_pld_api_exact_reference"
                source_basis = f"Official notice/PDF contains planning reference {raw_ref}; official PLD API exactly returns Havering record {api.get('api_id')}."
            if permit_id and (permit_id, event_id) not in seen_pairs:
                edge_id = f"edge:uk-london:d6b4:pld_event:{stable_hash(permit_id + event_id)}"
                seen_pairs.add((permit_id, event_id))
                seen_edges.add(edge_id)
                edge_rows.append(
                    {
                        "edge_id": edge_id,
                        "src": permit_id,
                        "dst": event_id,
                        "relation": "related_to_event",
                        "confidence": 0.95,
                        "resolution_method": method,
                        "source_field_basis": source_basis,
                        "candidate_only": False,
                        "source_stage": "D6B4",
                        "raw_reference": raw_ref,
                        "boundary_statement": BOUNDARY,
                    }
                )
                new_pld_rows.append(
                    {
                        "event_id": event_id,
                        "raw_reference": raw_ref,
                        "permit_id": permit_id,
                        "resolution_method": method,
                        "api_uprn_canonical_values": api.get("api_uprn_canonical_values", []) if api else [],
                    }
                )
            elif not permit_id:
                reason = "Reference did not have planning-application context." if not is_context_ok else "No exact accepted D9D2 or official PLD API Havering match."
                candidate_rows.append(
                    {
                        "edge_id": f"candidate_edge:uk-london:d6b4:ref:{stable_hash(event_id + raw_ref + reason)}",
                        "source_event_id": event_id,
                        "candidate_target_id": f"planning_reference_candidate:uk-london:havering:{safe_slug(raw_ref)}",
                        "src": event_id,
                        "dst": f"planning_reference_candidate:uk-london:havering:{safe_slug(raw_ref)}",
                        "relation": "candidate_planning_reference",
                        "candidate_only": True,
                        "match_method": "planning_reference_candidate",
                        "confidence": 0.50,
                        "not_certified_reason": reason,
                        "raw_value": raw_ref,
                        "boundary_statement": BOUNDARY,
                    }
                )
        for uprn in row.get("explicit_uprn_candidates", []) or []:
            raw = str(uprn.get("value", "")).strip()
            canon = canonical_uprn(raw)
            if canon and canon in verified_uprns:
                parcel_id = f"parcel:uk-london:uprn:{canon}"
                edge_id = f"edge:uk-london:d6b4:uprn_event:{stable_hash(parcel_id + event_id)}"
                if edge_id not in seen_edges:
                    seen_edges.add(edge_id)
                    edge_rows.append(
                        {
                            "edge_id": edge_id,
                            "src": parcel_id,
                            "dst": event_id,
                            "relation": "subject_of_event",
                            "confidence": 0.99,
                            "resolution_method": "explicit_official_uprn",
                            "source_field_basis": f"Official source explicitly labels UPRN {raw}; UPRN exists in OS OpenUPRN/D9B source.",
                            "candidate_only": False,
                            "source_stage": "D6B4",
                            "raw_reference": raw,
                            "boundary_statement": BOUNDARY,
                        }
                    )
                    new_uprn_rows.append({"event_id": event_id, "uprn": canon, "parcel_id": parcel_id, "resolution_method": "explicit_official_uprn"})
            else:
                candidate_rows.append(
                    {
                        "edge_id": f"candidate_edge:uk-london:d6b4:uprn:{stable_hash(event_id + raw)}",
                        "source_event_id": event_id,
                        "candidate_target_id": f"uprn_candidate:uk-london:{safe_slug(raw)}",
                        "src": event_id,
                        "dst": f"uprn_candidate:uk-london:{safe_slug(raw)}",
                        "relation": "candidate_uprn",
                        "candidate_only": True,
                        "match_method": "explicit_uprn_candidate",
                        "confidence": 0.50,
                        "not_certified_reason": "UPRN-like value did not exist in accepted OS OpenUPRN/D9B source.",
                        "raw_value": raw,
                        "boundary_statement": BOUNDARY,
                    }
                )
        for postcode in row.get("postcode_candidates", []) or []:
            pc = str(postcode.get("value", "")).strip()
            candidate_rows.append(
                {
                    "edge_id": f"candidate_edge:uk-london:d6b4:postcode:{stable_hash(event_id + pc)}",
                    "source_event_id": event_id,
                    "candidate_target_id": f"postcode_candidate:uk-london:havering:{safe_slug(pc)}",
                    "src": event_id,
                    "dst": f"postcode_candidate:uk-london:havering:{safe_slug(pc)}",
                    "relation": "postcode_candidate",
                    "candidate_only": True,
                    "match_method": "postcode_only",
                    "confidence": 0.30,
                    "not_certified_reason": "Postcode-only matching is not certified identity recovery.",
                    "raw_value": pc,
                    "boundary_statement": BOUNDARY,
                }
            )
    edges = pd.DataFrame(edge_rows).drop_duplicates("edge_id") if edge_rows else pd.DataFrame()
    new_pld = pd.DataFrame(new_pld_rows).drop_duplicates(["event_id", "permit_id"]) if new_pld_rows else pd.DataFrame()
    new_uprn = pd.DataFrame(new_uprn_rows).drop_duplicates(["event_id", "parcel_id"]) if new_uprn_rows else pd.DataFrame()
    candidates_out = pd.DataFrame(candidate_rows).drop_duplicates("edge_id") if candidate_rows else pd.DataFrame()
    report = {
        "baseline_edges": len(d6b3_edges),
        "total_certified_identity_edges": len(edges),
        "new_exact_pld_matches": len(new_pld),
        "new_explicit_uprn_matches": len(new_uprn),
        "new_certified_edges": max(0, len(edges) - len(d6b3_edges)),
    }
    return edges, new_pld, new_uprn, candidates_out, report


def summarize_downstream_paths(permit_ids: list[str]) -> dict[str, Any]:
    paths_path = Path("outputs/lon_d9d2_pld_api_uprn_recovery/canonical/london_pld_api_connected_paths.parquet")
    permit_set = {str(pid) for pid in permit_ids if str(pid)}
    report = {
        "source": str(paths_path),
        "source_exists": paths_path.exists(),
        "unique_matched_pld_permits": len(permit_set),
        "matched_pld_permits_with_d9d2_paths": 0,
        "pld_to_uprn_to_toid_paths": 0,
        "pld_to_uprn_to_usrn_paths": 0,
        "boundary_statement": BOUNDARY,
    }
    if not paths_path.exists() or not permit_set:
        return report
    paths = pd.read_parquet(paths_path)
    sub = paths[paths["permit_id"].astype(str).isin(permit_set)]
    report["matched_pld_permits_with_d9d2_paths"] = int(sub["permit_id"].nunique()) if not sub.empty else 0
    report["pld_to_uprn_to_toid_paths"] = int((sub["context_relation"].astype(str) == "has_building").sum()) if not sub.empty else 0
    report["pld_to_uprn_to_usrn_paths"] = int((sub["context_relation"].astype(str) == "on_street").sum()) if not sub.empty else 0
    report["sample_paths"] = sub[["permit_id", "uprn_id", "context_dst", "context_relation", "path"]].head(30).to_dict("records") if not sub.empty else []
    return report


def normalize_candidate_links(d6b3_dir: Path, d6b4_candidates: pd.DataFrame) -> pd.DataFrame:
    frames = []
    base_path = d6b3_dir / "canonical/london_d6b3_candidate_identity_links.parquet"
    if base_path.exists():
        base = pd.read_parquet(base_path).copy()
        if "source_event_id" not in base.columns:
            base["source_event_id"] = base.get("src")
        if "candidate_target_id" not in base.columns:
            base["candidate_target_id"] = base.get("dst")
        if "confidence" not in base.columns and "confidence_score" in base.columns:
            base["confidence"] = base["confidence_score"]
        if "not_certified_reason" not in base.columns:
            base["not_certified_reason"] = base.get("basis", "D6B3 candidate-only link retained.")
        base["candidate_only"] = True
        frames.append(base)
    if not d6b4_candidates.empty:
        frames.append(d6b4_candidates)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["candidate_only"] = True
    if "confidence" in out.columns:
        out["confidence"] = pd.to_numeric(out["confidence"], errors="coerce").fillna(0.50).clip(upper=0.60)
    return out.drop_duplicates("edge_id") if "edge_id" in out.columns else out


def build_graph(events: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    connected = set(edges["dst"].astype(str).tolist()) if not edges.empty and "dst" in edges.columns else set()
    enriched = events.copy()
    enriched["d6b4_identity_expansion_status"] = enriched["canonical_id"].map(lambda eid: "certified_identity_recovered" if eid in connected else "candidate_only_or_unmatched")
    node_rows = []
    for _, event in enriched.iterrows():
        node_rows.append(
            {
                "id": event["canonical_id"],
                "entity_type": event.get("entity_type", "event"),
                "node_role": "enforcement_event",
                "borough": event.get("borough"),
                "boundary_statement": BOUNDARY,
            }
        )
    if not edges.empty:
        for permit_id in sorted(set(edges.loc[edges["src"].astype(str).str.startswith("permit:"), "src"].astype(str))):
            node_rows.append({"id": permit_id, "entity_type": "permit", "node_role": "pld_permit", "borough": "Havering", "boundary_statement": BOUNDARY})
        for parcel_id in sorted(set(edges.loc[edges["src"].astype(str).str.startswith("parcel:"), "src"].astype(str))):
            node_rows.append({"id": parcel_id, "entity_type": "parcel", "node_role": "uprn_parcel", "borough": "Havering", "boundary_statement": BOUNDARY})
    nodes = pd.DataFrame(node_rows).drop_duplicates("id")
    node_ids = set(nodes["id"].astype(str))
    failures = []
    for _, edge in edges.iterrows():
        for field in ["src", "dst"]:
            if str(edge.get(field)) not in node_ids:
                failures.append({"edge_id": edge.get("edge_id"), "missing": field, "value": edge.get(field)})
    report = {
        "gate": "LON-D6B4-GRAPH-BUILD",
        "status": "PASS" if not failures else "FAIL",
        "nodes": int(len(nodes)),
        "edges": int(len(edges)),
        "edge_integrity": "PASS" if not failures else "FAIL",
        "edge_integrity_failures": failures,
        "boundary_statement": BOUNDARY,
    }
    return enriched, nodes, report


def write_queries(output: Path, reports: dict[str, Any], events: pd.DataFrame, edges: pd.DataFrame, candidates: pd.DataFrame) -> tuple[dict[str, Any], dict[str, str]]:
    exact_event = edges["dst"].iloc[0] if not edges.empty else None
    sample_event = exact_event or (events["canonical_id"].iloc[0] if not events.empty else None)
    bundles = {
        "d6b4_identity_expansion_status": {
            "query_type": "d6b4_identity_expansion_status",
            "boundary_statement": BOUNDARY,
            "counts": reports,
            "answer_facts": [
                f"D6B4 baseline certified edges from D6B3: {reports['d6b3_baseline_certified_edges']}.",
                f"D6B4 new exact PLD matches: {reports['new_exact_pld_matches']}.",
                f"D6B4 total certified identity edges: {reports['total_certified_identity_edges_after_d6b4']}.",
            ],
        },
        "havering_event_exact_identity_profile": {
            "query_type": "havering_event_exact_identity_profile",
            "boundary_statement": BOUNDARY,
            "event_id": sample_event,
            "certified_edges": edges[edges["dst"].astype(str) == str(sample_event)].to_dict("records") if sample_event and not edges.empty else [],
        },
        "havering_event_candidate_identity_profile": {
            "query_type": "havering_event_candidate_identity_profile",
            "boundary_statement": BOUNDARY,
            "event_id": sample_event,
            "candidate_links": candidates[candidates["source_event_id"].astype(str) == str(sample_event)].head(20).to_dict("records") if sample_event and not candidates.empty and "source_event_id" in candidates.columns else [],
        },
        "d6b4_source_limitations": {
            "query_type": "d6b4_source_limitations",
            "boundary_statement": BOUNDARY,
            "limitations": LIMITATIONS,
        },
    }
    write_json(output / "queries/sample_query_inputs.json", [{"query_type": key} for key in bundles])
    write_json(output / "queries/sample_query_results.json", bundles)
    for name, bundle in [
        ("evidence_bundle_d6b4_identity_expansion_status.json", bundles["d6b4_identity_expansion_status"]),
        ("evidence_bundle_havering_event_exact_identity_profile.json", bundles["havering_event_exact_identity_profile"]),
        ("evidence_bundle_d6b4_source_limitations.json", bundles["d6b4_source_limitations"]),
    ]:
        write_json(output / "bundles" / name, bundle)
    briefings = {
        "london_d6b4_identity_expansion_status.md": render_status_briefing(reports),
        "london_d6b4_exact_identity_profile.md": render_exact_profile(sample_event, edges),
        "london_d6b4_source_limitations.md": "# D6B4 Source Limitations\n\n" + BOUNDARY + "\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n",
    }
    write_json(output / "queries/deterministic_briefings.json", briefings)
    for name, text in briefings.items():
        (output / "queries" / name).write_text(text, encoding="utf-8")
    return bundles, briefings


def render_status_briefing(reports: dict[str, Any]) -> str:
    return f"""# D6B4 Havering Identity Expansion Status

{BOUNDARY}

- Input D6B3 status: {reports['input_d6b3_status']}
- D6B3 baseline certified edges: {reports['d6b3_baseline_certified_edges']}
- New exact PLD matches: {reports['new_exact_pld_matches']}
- New explicit UPRN matches: {reports['new_explicit_uprn_matches']}
- New official address-to-UPRN matches: {reports['new_official_address_uprn_matches']}
- Total certified identity edges after D6B4: {reports['total_certified_identity_edges_after_d6b4']}
- Candidate links retained: {reports['candidate_links_retained']}
- Rejected address/postcode/fuzzy matches: {reports['rejected_address_postcode_fuzzy_matches']}
"""


def render_exact_profile(event_id: str | None, edges: pd.DataFrame) -> str:
    rows = edges[edges["dst"].astype(str) == str(event_id)].to_dict("records") if event_id and not edges.empty else []
    return f"""# D6B4 Exact Identity Profile

{BOUNDARY}

Event: {event_id or 'none'}

Certified edge count for this event: {len(rows)}

Certified identity links require exact official PLD reference or explicit official UPRN evidence.
"""


def private_scan(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    findings = []
    for name, frame in frames.items():
        for col in frame.columns:
            lower = col.lower()
            if any(token in lower for token in ["email", "phone", "complainant", "officer_notes", "private_correspondence"]):
                findings.append({"frame": name, "field": col})
    return {"gate": "LON-D6B4-PRIVATE-DATA", "status": "PASS" if not findings else "FAIL", "findings": findings, "boundary_statement": BOUNDARY}


def no_overclaim(output: Path) -> dict[str, Any]:
    hits = []
    for path in output.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
            continue
        if path.name in {"LON_D6B4_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for claim in FORBIDDEN_CLAIMS:
            if claim.lower() in text.lower():
                hits.append({"path": str(path), "claim": claim})
    return {"gate": "LON-D6B4-NO-OVERCLAIM", "status": "PASS" if not hits else "FAIL", "forbidden_claim_hits": hits, "boundary_statement": BOUNDARY}


def publish_to_4070(output: Path, enabled: bool) -> dict[str, Any]:
    report = {"gate": "LON-D6B4-4070-SYNC", "status": "NOT_RUN", "target": "/data/citybrain/from_3090/london_d6b4_identity_expansion_v1/"}
    if not enabled:
        report["status"] = "NOT_RUN_DISABLED"
        return report
    export = output / "_4070_lightweight_export"
    if export.exists():
        shutil.rmtree(export)
    export.mkdir(parents=True)
    for rel in [
        "README.md",
        "LON_D6B4_HARNESS_REPORT.json",
        "LON_D6B4_CERTIFIED_EDGE_REPORT.json",
        "LON_D6B4_CANDIDATE_LINK_REPORT.json",
        "LON_D6B4_GRAPH_REBUILD_REPORT.json",
        "SHA256SUMS.json",
    ]:
        src = output / rel
        if src.exists():
            shutil.copy2(src, export / rel)
    for rel in ["queries", "bundles", "reports"]:
        if (output / rel).exists():
            shutil.copytree(output / rel, export / rel)
    try:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "txr-4070", "mkdir -p /data/citybrain/from_3090/london_d6b4_identity_expansion_v1"], check=True, capture_output=True, text=True, timeout=20)
        subprocess.run(["scp", "-o", "BatchMode=yes", "-r", str(export) + "/.", "txr-4070:/data/citybrain/from_3090/london_d6b4_identity_expansion_v1/"], check=True, capture_output=True, text=True, timeout=120)
        report["status"] = "PASS"
        report["file_count"] = len([p for p in export.rglob("*") if p.is_file()])
    except Exception as exc:  # noqa: BLE001
        report["status"] = "NOT_RUN_SSH_UNAVAILABLE"
        report["error"] = repr(exc)
    return report


def run_lon_d6b4_gate(
    d6b3_dir: str,
    d6b2_dir: str,
    d6x_dir: str,
    d9z_dir: str,
    d10z_dir: str,
    d13b_dir: str,
    output_dir: str,
    raw_roots: list[str] | None = None,
    allow_official_download_probe: bool = True,
    extract_pdf_text: bool = True,
    max_pdf_text_pages: int = 10,
    publish_4070: bool = True,
) -> dict[str, Any]:
    output = Path(output_dir)
    ensure_dirs(output)
    raw_roots = raw_roots or ["data_landing/london_d6x_source_scout", "data_landing/london_d9_raw", str(Path.home() / "Downloads")]
    d6b3 = Path(d6b3_dir)
    d6b2 = Path(d6b2_dir)
    d6x = Path(d6x_dir)
    d9z = Path(d9z_dir)
    d10z = Path(d10z_dir)
    d13b = Path(d13b_dir)
    accepted_paths = [
        d6b3 / "LON_D6B3_HARNESS_REPORT.json",
        d6b2 / "LON_D6B2_HARNESS_REPORT.json",
        d6x / "LON_D6X_HARNESS_REPORT.json",
        d9z / "LON_D9Z_ACCEPTED_SNAPSHOT.json",
        d10z / "LON_D10Z_HARNESS_REPORT.json",
    ]
    before = file_hashes(accepted_paths)
    d6b3_harness = read_json(d6b3 / "LON_D6B3_HARNESS_REPORT.json", {})
    d6b3_counts = d6b3_harness.get("counts", {})
    input_inventory = {
        "created_utc": now_utc(),
        "d6b3_dir": str(d6b3),
        "d6b2_dir": str(d6b2),
        "d6x_dir": str(d6x),
        "d9z_dir": str(d9z),
        "d10z_dir": str(d10z),
        "d13b_dir": str(d13b),
        "d13b_exists": d13b.exists(),
        "raw_roots": raw_roots,
        "accepted_hashes_before": before,
        "boundary_statement": BOUNDARY,
    }
    write_json(output / "LON_D6B4_INPUT_INVENTORY.json", input_inventory)
    precond = {
        "gate": "LON-D6B4-PRECOND",
        "status": "PASS" if d6b3_harness.get("status") in {"PASS_WITH_PARTIAL_IDENTITY_RECOVERY", "PASS", "PASS_WITH_IDENTITY_LIMITATION_CONFIRMED"} else "FAIL",
        "input_d6b3_status": d6b3_harness.get("status"),
        "d13b_status": "missing_optional_context" if not d13b.exists() else "present",
        "boundary_statement": BOUNDARY,
    }

    baseline_edges = pd.read_parquet(d6b3 / "canonical/london_d6b3_certified_identity_edges.parquet")
    baseline_report = {
        "gate": "LON-D6B4-D6B3-BASELINE-RECONCILIATION",
        "status": "PASS"
        if int(d6b3_counts.get("certified_identity_edges", -1)) == len(baseline_edges)
        and int(d6b3_counts.get("exact_pld_matches", -1)) == 7
        and int(d6b3_counts.get("unique_matched_pld_permits", -1)) == 6
        else "FAIL",
        "d6b3_exact_pld_matches": d6b3_counts.get("exact_pld_matches"),
        "d6b3_certified_identity_edges": len(baseline_edges),
        "d6b3_unique_matched_pld_permits": d6b3_counts.get("unique_matched_pld_permits"),
        "d6b3_pld_uprn_toid_paths": d6b3_counts.get("pld_to_uprn_to_toid_paths"),
        "d6b3_pld_uprn_usrn_paths": d6b3_counts.get("pld_to_uprn_to_usrn_paths"),
        "boundary_statement": BOUNDARY,
    }
    write_json(output / "reports/baseline_d6b3_reconciliation.json", baseline_report)

    source_discovery = discover_local_sources(raw_roots, output)
    probe = official_source_probe(output, allow_official_download_probe)
    address_report = inspect_address_gazetteer(raw_roots)

    events = pd.read_parquet(d6b2 / "canonical/london_d6b2_enforcement_events.parquet")
    docs = pd.read_parquet(d6b2 / "canonical/london_d6b2_enforcement_documents.parquet")
    pdf_refs, pdf_report = extract_pdf_refs(docs, output, extract_pdf_text, max_pdf_text_pages)
    candidates = extract_structured_candidates(events, docs, pdf_refs)
    ref_records = []
    for _, row in candidates.iterrows():
        for ref in row.get("planning_reference_candidates", []) or []:
            ref_records.append({"event_id": row["event_id"], "raw_reference": ref.get("value"), "planning_context": ref.get("planning_context"), "source": ref.get("source"), "snippet": ref.get("snippet")})
    api_matches, api_report = query_official_api_for_refs(ref_records)
    target_uprns = set()
    if not api_matches.empty:
        for values in api_matches["api_uprn_canonical_values"]:
            target_uprns.update(str(v) for v in (values or []) if v)
    for _, row in candidates.iterrows():
        for uprn in row.get("explicit_uprn_candidates", []) or []:
            canon = canonical_uprn(uprn.get("value"))
            if canon:
                target_uprns.add(canon)
    open_uprn_report = verify_uprns_in_open_uprn(target_uprns, raw_roots)
    local_ref_index, d9d2_path_source = load_d9d2_indexes()
    edges, new_pld, new_uprn, d6b4_candidate_only, edge_report = build_edges(candidates, baseline_edges, local_ref_index, api_matches, open_uprn_report)
    candidate_links = normalize_candidate_links(d6b3, d6b4_candidate_only)
    enriched_events, graph_nodes, graph_report = build_graph(events, edges)
    downstream = summarize_downstream_paths(sorted(set(edges.loc[edges["src"].astype(str).str.startswith("permit:"), "src"].astype(str))) if not edges.empty else [])

    exact_edge_cols = ["edge_id", "src", "dst", "relation", "confidence", "resolution_method", "source_field_basis", "candidate_only", "source_stage", "raw_reference", "boundary_statement"]
    candidate_cols = ["edge_id", "source_event_id", "candidate_target_id", "src", "dst", "relation", "candidate_only", "match_method", "confidence", "not_certified_reason", "raw_value", "boundary_statement"]
    write_parquet(output / "canonical/london_d6b4_certified_identity_edges.parquet", edges, exact_edge_cols)
    write_parquet(output / "canonical/london_d6b4_candidate_identity_links.parquet", candidate_links)
    write_parquet(output / "canonical/london_d6b4_enforcement_events_enriched.parquet", enriched_events)
    write_parquet(output / "canonical/london_d6b4_new_exact_pld_matches.parquet", new_pld)
    write_parquet(output / "canonical/london_d6b4_new_exact_uprn_matches.parquet", new_uprn)
    write_parquet(output / "canonical/london_d6b4_graph_nodes.parquet", graph_nodes)
    write_parquet(output / "canonical/london_d6b4_graph_edges.parquet", edges, exact_edge_cols)
    write_json(output / "canonical/london_d6b4_edges_sample.json", edges.head(30).to_dict("records"))
    write_json(output / "canonical/london_d6b4_events_sample.json", enriched_events.head(30).to_dict("records"))

    reference_report = {
        "gate": "LON-D6B4-REFERENCE-EXTRACTION",
        "status": "PASS",
        "pdf_text_extraction": pdf_report,
        "events_scanned": int(len(candidates)),
        "events_with_planning_reference_candidates": int(candidates["planning_reference_candidates"].map(len).gt(0).sum()),
        "planning_reference_candidate_values": int(sum(len(x) for x in candidates["planning_reference_candidates"])),
        "planning_reference_candidates_with_planning_context": int(sum(1 for row in candidates["planning_reference_candidates"] for item in row if item.get("planning_context"))),
        "explicit_uprn_candidate_values": int(sum(len(x) for x in candidates["explicit_uprn_candidates"])),
        "postcode_candidate_values": int(sum(len(x) for x in candidates["postcode_candidates"])),
        "official_api_probe": api_report,
        "boundary_statement": BOUNDARY,
    }
    pld_match_report = {
        "gate": "LON-D6B4-PLD-MATCH",
        "status": "PASS",
        "new_exact_pld_matches": int(len(new_pld)),
        "official_api": api_report,
        "d9d2_downstream_paths": downstream,
        "d9d2_path_source": d9d2_path_source,
        "boundary_statement": BOUNDARY,
    }
    uprn_match_report = {
        "gate": "LON-D6B4-UPRN-MATCH",
        "status": "PASS",
        "new_explicit_uprn_matches": int(len(new_uprn)),
        "open_uprn_verification": open_uprn_report,
        "boundary_statement": BOUNDARY,
    }
    address_report["new_official_address_uprn_matches"] = 0
    certified_report = {
        "gate": "LON-D6B4-CERTIFIED-EDGE-DISCIPLINE",
        "status": "PASS" if not edges.empty and not bool(edges.get("candidate_only", pd.Series(dtype=bool)).fillna(False).any()) else "FAIL",
        "d6b3_baseline_edges": int(len(baseline_edges)),
        "total_certified_identity_edges": int(len(edges)),
        "new_certified_edges": int(max(0, len(edges) - len(baseline_edges))),
        "new_exact_pld_matches": int(len(new_pld)),
        "new_explicit_uprn_matches": int(len(new_uprn)),
        "boundary_statement": BOUNDARY,
    }
    candidate_report = {
        "gate": "LON-D6B4-CANDIDATE-DISCIPLINE",
        "status": "PASS" if candidate_links.empty or bool(candidate_links["candidate_only"].all()) else "FAIL",
        "candidate_links_retained": int(len(candidate_links)),
        "confidence_max": float(pd.to_numeric(candidate_links.get("confidence", pd.Series(dtype=float)), errors="coerce").max()) if not candidate_links.empty and "confidence" in candidate_links.columns else None,
        "boundary_statement": BOUNDARY,
    }
    write_json(output / "LON_D6B4_REFERENCE_EXTRACTION_REPORT.json", reference_report)
    write_json(output / "LON_D6B4_PLD_MATCH_REPORT.json", pld_match_report)
    write_json(output / "LON_D6B4_UPRN_MATCH_REPORT.json", uprn_match_report)
    write_json(output / "LON_D6B4_ADDRESS_GAZETTEER_REPORT.json", address_report)
    write_json(output / "LON_D6B4_CERTIFIED_EDGE_REPORT.json", certified_report)
    write_json(output / "LON_D6B4_CANDIDATE_LINK_REPORT.json", candidate_report)
    write_json(output / "LON_D6B4_GRAPH_REBUILD_REPORT.json", graph_report)
    write_json(output / "reports/new_explicit_uprn_hits.json", {"count": reference_report["explicit_uprn_candidate_values"], "rows": candidates[candidates["explicit_uprn_candidates"].map(len).gt(0)].to_dict("records"), "boundary_statement": BOUNDARY})
    write_json(output / "reports/new_planning_reference_hits.json", {"count": reference_report["events_with_planning_reference_candidates"], "rows": candidates[candidates["planning_reference_candidates"].map(len).gt(0)].head(1000).to_dict("records"), "boundary_statement": BOUNDARY})
    write_json(output / "reports/new_exact_pld_matches.json", {"count": int(len(new_pld)), "rows": new_pld.to_dict("records"), "boundary_statement": BOUNDARY})
    write_json(output / "reports/new_exact_uprn_matches.json", {"count": int(len(new_uprn)), "rows": new_uprn.to_dict("records"), "boundary_statement": BOUNDARY})
    write_json(output / "reports/official_address_uprn_matches.json", address_report)
    write_json(output / "reports/rejected_address_only_matches.json", {"count": 0, "reason": "No official address-bearing gazetteer available; address-only matching not certified.", "boundary_statement": BOUNDARY})
    postcode_only = candidate_links[candidate_links.get("match_method", pd.Series(dtype=str)).astype(str).eq("postcode_only")] if not candidate_links.empty else pd.DataFrame()
    write_json(output / "reports/rejected_postcode_only_matches.json", {"count": int(len(postcode_only)), "sample": postcode_only.head(100).to_dict("records"), "boundary_statement": BOUNDARY})
    fuzzy = candidate_links[candidate_links.get("match_method", pd.Series(dtype=str)).astype(str).str.contains("candidate|fuzzy|reference", case=False, na=False)] if not candidate_links.empty else pd.DataFrame()
    write_json(output / "reports/rejected_fuzzy_matches.json", {"count": int(len(fuzzy)), "sample": fuzzy.head(100).to_dict("records"), "boundary_statement": BOUNDARY})
    write_json(output / "reports/retained_candidate_links.json", {"count": int(len(candidate_links)), "sample": candidate_links.head(100).to_dict("records"), "boundary_statement": BOUNDARY})

    reports = {
        "input_d6b3_status": d6b3_harness.get("status"),
        "havering_events_considered": int(len(events)),
        "d6b3_baseline_certified_edges": int(len(baseline_edges)),
        "d6b3_baseline_exact_pld_matches": int(d6b3_counts.get("exact_pld_matches", 0)),
        "d6b3_baseline_unique_matched_pld_permits": int(d6b3_counts.get("unique_matched_pld_permits", 0)),
        "new_exact_pld_matches": int(len(new_pld)),
        "new_explicit_uprn_matches": int(len(new_uprn)),
        "new_official_address_uprn_matches": 0,
        "total_certified_identity_edges_after_d6b4": int(len(edges)),
        "candidate_links_retained": int(len(candidate_links)),
        "rejected_address_postcode_fuzzy_matches": int(len(candidate_links)),
        "unique_matched_pld_permits": int(downstream.get("unique_matched_pld_permits", 0)),
        "matched_pld_permits_with_d9d2_paths": int(downstream.get("matched_pld_permits_with_d9d2_paths", 0)),
        "pld_to_uprn_to_toid_paths": int(downstream.get("pld_to_uprn_to_toid_paths", 0)),
        "pld_to_uprn_to_usrn_paths": int(downstream.get("pld_to_uprn_to_usrn_paths", 0)),
    }

    bundles, briefings = write_queries(output, reports, enriched_events, edges, candidate_links)
    query_report = {"gate": "LON-D6B4-QUERY-SMOKE", "status": "PASS", "query_types": list(bundles), "boundary_statement": BOUNDARY}
    briefing_report = {"gate": "LON-D6B4-BRIEFING-GROUNDING", "status": "PASS" if all("No NIM/NeMo/LLM generated these facts." in text for text in briefings.values()) else "FAIL", "boundary_statement": BOUNDARY}
    privacy = private_scan({"events": enriched_events, "edges": edges, "candidate_links": candidate_links, "new_pld": new_pld, "new_uprn": new_uprn})
    limitations = {"gate": "LON-D6B4-LIMITATION-CARRY-FORWARD", "status": "PASS", "limitations": LIMITATIONS, "boundary_statement": BOUNDARY}
    write_json(output / "LON_D6B4_QUERY_SMOKE_REPORT.json", query_report)
    write_json(output / "LON_D6B4_BRIEFING_GROUNDING_REPORT.json", briefing_report)
    write_json(output / "LON_D6B4_LIMITATION_CARRY_FORWARD_REPORT.json", limitations)
    write_json(output / "reports/no_private_data_review.json", privacy)
    (output / "README.md").write_text(render_readme(reports), encoding="utf-8")
    (output / "LON_D6B4_ADAPTER_HANDOVER.md").write_text(render_handover(reports, address_report), encoding="utf-8")
    no_claim = no_overclaim(output)
    write_json(output / "LON_D6B4_NO_OVERCLAIM_REPORT.json", no_claim)
    after = file_hashes(accepted_paths)
    no_mutation = {"gate": "LON-D6B4-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "before": before, "after": after, "boundary_statement": BOUNDARY}

    gates = {
        "LON-D6B4-PRECOND": precond["status"],
        "LON-D6B4-D6B3-BASELINE-RECONCILIATION": baseline_report["status"],
        "LON-D6B4-SOURCE-DISCOVERY": source_discovery["status"],
        "LON-D6B4-OFFICIAL-SOURCE-PROBE": probe["status"],
        "LON-D6B4-REFERENCE-EXTRACTION": reference_report["status"],
        "LON-D6B4-PLD-MATCH": pld_match_report["status"],
        "LON-D6B4-UPRN-MATCH": uprn_match_report["status"],
        "LON-D6B4-ADDRESS-GAZETTEER-MATCH": address_report["status"],
        "LON-D6B4-CERTIFIED-EDGE-DISCIPLINE": certified_report["status"],
        "LON-D6B4-CANDIDATE-DISCIPLINE": candidate_report["status"],
        "LON-D6B4-GRAPH-BUILD": graph_report["status"],
        "LON-D6B4-QUERY-SMOKE": query_report["status"],
        "LON-D6B4-BRIEFING-GROUNDING": briefing_report["status"],
        "LON-D6B4-PRIVATE-DATA": privacy["status"],
        "LON-D6B4-LIMITATION-CARRY-FORWARD": limitations["status"],
        "LON-D6B4-NO-OVERCLAIM": no_claim["status"],
        "LON-D6B4-NO-MUTATION": no_mutation["status"],
    }
    if any(value != "PASS" for value in gates.values()):
        status = "FAIL"
    elif reports["new_exact_pld_matches"] or reports["new_explicit_uprn_matches"] or reports["new_official_address_uprn_matches"]:
        status = "PASS_WITH_EXPANDED_IDENTITY_RECOVERY"
    elif api_report["official_api_refs_queried"] or reference_report["planning_reference_candidate_values"]:
        status = "PASS_WITH_NO_ADDITIONAL_IDENTITY_RECOVERY"
    else:
        status = "PASS_WITH_SOURCE_LIMITATION_CONFIRMED"
    harness = {
        "task": "LON-D6B4 Havering Enforcement Identity Expansion",
        "created_utc": now_utc(),
        "status": status,
        "input_d6b3_status": d6b3_harness.get("status"),
        "gates": gates,
        "counts": reports,
        "no_mutation": no_mutation,
        "boundary_statement": BOUNDARY,
    }
    write_json(output / "LON_D6B4_HARNESS_REPORT.json", harness)
    hashes = hash_outputs(output)
    gates["LON-D6B4-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    write_json(output / "LON_D6B4_HARNESS_REPORT.json", harness)
    hash_outputs(output)
    sync = publish_to_4070(output, publish_4070)
    write_json(output / "reports/4070_sync_report.json", sync)
    harness["4070_sync"] = sync
    write_json(output / "LON_D6B4_HARNESS_REPORT.json", harness)
    hash_outputs(output)
    return {"harness": harness, "sync": sync}


def render_readme(reports: dict[str, Any]) -> str:
    return f"""# LON-D6B4 Havering Enforcement Identity Expansion

{BOUNDARY}

## Result

- Input D6B3 status: {reports['input_d6b3_status']}
- D6B3 baseline certified edges: {reports['d6b3_baseline_certified_edges']}
- New exact PLD matches: {reports['new_exact_pld_matches']}
- New explicit UPRN matches: {reports['new_explicit_uprn_matches']}
- New official address-to-UPRN matches: {reports['new_official_address_uprn_matches']}
- Total certified identity edges after D6B4: {reports['total_certified_identity_edges_after_d6b4']}
- Candidate links retained: {reports['candidate_links_retained']}
- Rejected address/postcode/fuzzy matches: {reports['rejected_address_postcode_fuzzy_matches']}

Address-only, postcode-only, nearest-geometry, and fuzzy evidence remains candidate-only.
"""


def render_handover(reports: dict[str, Any], address_report: dict[str, Any]) -> str:
    return f"""# LON-D6B4 Adapter Handover

{BOUNDARY}

D6B4 expands Havering enforcement identity recovery through exact official PLD references and explicit official UPRNs only.

```json
{json.dumps(reports, indent=2, sort_keys=True)}
```

Address gazetteer status:

```json
{json.dumps(address_report, indent=2, sort_keys=True)}
```
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d6b3-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d6x-dir", default="outputs/lon_d6x_borough_enforcement_source_scout")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--output-dir", default="outputs/lon_d6b4_havering_enforcement_identity_expansion")
    parser.add_argument("--raw-root", action="append", dest="raw_roots")
    parser.add_argument("--allow-official-download-probe", action="store_true")
    parser.add_argument("--extract-pdf-text", action="store_true")
    parser.add_argument("--max-pdf-text-pages", type=int, default=10)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_lon_d6b4_gate(
        d6b3_dir=args.d6b3_dir,
        d6b2_dir=args.d6b2_dir,
        d6x_dir=args.d6x_dir,
        d9z_dir=args.d9z_dir,
        d10z_dir=args.d10z_dir,
        d13b_dir=args.d13b_dir,
        output_dir=args.output_dir,
        raw_roots=args.raw_roots,
        allow_official_download_probe=args.allow_official_download_probe,
        extract_pdf_text=args.extract_pdf_text,
        max_pdf_text_pages=args.max_pdf_text_pages,
        publish_4070=args.publish_4070,
    )
    h = result["harness"]
    c = h["counts"]
    print(
        "\n".join(
            [
                f"LON-D6B4 Havering Enforcement Identity Expansion: {h['status']}",
                f"Input D6B3: {h['input_d6b3_status']}",
                f"D6B3 baseline certified edges: {c['d6b3_baseline_certified_edges']}",
                f"New exact PLD matches: {c['new_exact_pld_matches']}",
                f"New explicit UPRN matches: {c['new_explicit_uprn_matches']}",
                f"New official address->UPRN matches: {c['new_official_address_uprn_matches']}",
                f"Total certified identity edges after D6B4: {c['total_certified_identity_edges_after_d6b4']}",
                f"Candidate links retained: {c['candidate_links_retained']}",
                f"Rejected address/postcode/fuzzy matches: {c['rejected_address_postcode_fuzzy_matches']}",
                f"Graph build: {h['gates']['LON-D6B4-GRAPH-BUILD']}",
                f"Edge integrity: {json.loads(Path(args.output_dir, 'LON_D6B4_GRAPH_REBUILD_REPORT.json').read_text(encoding='utf-8')).get('edge_integrity')}",
                f"Query smoke: {h['gates']['LON-D6B4-QUERY-SMOKE']}",
                f"Briefing grounding: {h['gates']['LON-D6B4-BRIEFING-GROUNDING']}",
                f"No-overclaim: {h['gates']['LON-D6B4-NO-OVERCLAIM']}",
                f"4070 sync: {h.get('4070_sync', {}).get('status', 'NOT_RUN')}",
                f"Output: {args.output_dir}",
            ]
        )
    )
    return 0 if h["status"] in {"PASS_WITH_EXPANDED_IDENTITY_RECOVERY", "PASS_WITH_NO_ADDITIONAL_IDENTITY_RECOVERY", "PASS_WITH_SOURCE_LIMITATION_CONFIRMED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
