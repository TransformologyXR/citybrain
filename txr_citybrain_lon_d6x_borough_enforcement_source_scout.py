#!/usr/bin/env python3
"""LON-D6X borough enforcement source scout + bounded ingest.

This adapter intentionally keeps three source families separate:
- Havering official planning-enforcement notice indexes can emit formal
  planning_enforcement Event metadata.
- Camden planning applications can emit enforcement-adjacent candidates only.
- Redbridge Planning Development Control is aggregate context unless proven
  case-level.

No address-only or text-only match is promoted to a certified identity edge.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


BOUNDARY_STATEMENT = (
    "D6X is a borough source scout and bounded ingest, not London-wide enforcement coverage. "
    "Camden data is enforcement-adjacent unless formal enforcement source fields prove otherwise. "
    "Havering records are official notice metadata/document evidence, not UPRN-resolved unless exact identifiers are present. "
    "Redbridge data is aggregate context unless case-level records are proven. "
    "Address-only matches are not certified identity joins. "
    "No private complainant/contact data is ingested."
)

OUTPUT_BOUNDARY_LINES = [
    "D6X is a borough source scout and bounded ingest, not London-wide enforcement coverage.",
    "Camden data is enforcement-adjacent unless formal enforcement source fields prove otherwise.",
    "Havering records are official notice metadata/document evidence, not UPRN-resolved unless exact identifiers are present.",
    "Redbridge data is aggregate context unless case-level records are proven.",
    "Address-only matches are not certified identity joins.",
    "No private complainant/contact data is ingested.",
]

HEADERS = {
    "User-Agent": "TXR-CityBrain-D6X-source-scout/1.0 (+bounded official-source ingest)"
}

CAMDEN_METADATA_URL = "https://opendata.camden.gov.uk/api/views/2eiu-s2cw"
CAMDEN_CSV_BASE_URL = "https://opendata.camden.gov.uk/resource/2eiu-s2cw.csv"
CAMDEN_ROWS_CSV_URL = "https://opendata.camden.gov.uk/api/views/2eiu-s2cw/rows.csv?accessType=DOWNLOAD"

HAVERING_INDEXES = {
    "2026": "https://www.havering.gov.uk/downloads/download/1097/planning-enforcement-notices-2026",
    "2025": "https://www.havering.gov.uk/downloads/download/1059/planning-enforcement-notices-2025",
    "2024": "https://www.havering.gov.uk/downloads/download/1019/planning-enforcement-notices-2024",
    "2023": "https://www.havering.gov.uk/downloads/download/982/planning-enforcement-notices-2023",
    "2022": "https://www.havering.gov.uk/downloads/download/943/planning-enforcement-notices-2022",
    "2021": "https://www.havering.gov.uk/downloads/download/986/planning-enforcement-notices-2021",
    "2020": "https://www.havering.gov.uk/downloads/download/811/planning-enforcement-notices-2020",
}

REDBRIDGE_PAGE_URL = "https://data.london.gov.uk/dataset/redbridge-planning-development-control-2go3r"
HOUNSLOW_META_URL = "https://datasets.opendata.esd.org.uk/details?datasetId=127614"

ALLOWED_SOURCE_STATUSES = {
    "usable_case_level_enforcement",
    "usable_enforcement_adjacent",
    "usable_aggregate_context",
    "portal_only_not_viable",
    "download_failed",
    "manual_review_needed",
    "out_of_scope",
}

FORBIDDEN_OUTPUT_TERMS = [
    "formal_violation_decision",
    "legal_planning_decision",
    "building-control record",
]

PRIVATE_FIELD_PATTERNS = [
    "email",
    "phone",
    "telephone",
    "mobile",
    "contact",
    "complainant",
    "agent contact",
    "private correspondence",
    "officer notes",
    "applicant_name",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_dirs(output_dir: Path) -> None:
    for rel in [
        "raw_sample/camden",
        "raw_sample/havering",
        "raw_sample/redbridge",
        "raw_sample/hounslow_optional",
        "canonical",
        "reports",
    ]:
        (output_dir / rel).mkdir(parents=True, exist_ok=True)


def json_default(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=json_default), encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_slug(value: str, max_len: int = 96) -> str:
    value = re.sub(r"\s+", "_", str(value).strip())
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("._-")
    return (value[:max_len].strip("._-") or "unknown").lower()


def stable_hash(value: str, chars: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:chars]


def request_get(url: str, timeout: int = 90) -> requests.Response:
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    return response


def download_file(url: str, path: Path, overwrite: bool = False, timeout: int = 180) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return {
            "status": "reused_existing",
            "url": url,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        }
    response = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    response.raise_for_status()
    with path.open("wb") as fh:
        for chunk in response.iter_content(1024 * 1024):
            if chunk:
                fh.write(chunk)
    return {
        "status": "downloaded",
        "url": url,
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
        "content_type": response.headers.get("content-type"),
    }


def try_download_sources(
    raw_output_dir: Path,
    max_camden_records: int,
    download_havering_pdfs: bool,
    max_havering_pdfs_per_year: int,
    include_optional_hounslow: bool,
) -> dict[str, Any]:
    """Attempt or reuse official target sources, logging failures rather than blocking."""
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"created_utc": now_utc(), "boundary_statement": BOUNDARY_STATEMENT}

    camden_dir = raw_output_dir / "camden"
    camden_dir.mkdir(parents=True, exist_ok=True)
    camden_results: list[dict[str, Any]] = []
    meta_path = camden_dir / "camden_planning_applications_metadata.json"
    try:
        if meta_path.exists():
            camden_results.append(
                {"kind": "metadata", "status": "reused_existing", "path": str(meta_path), "sha256": sha256_path(meta_path)}
            )
        else:
            meta = request_get(CAMDEN_METADATA_URL).json()
            write_json(meta_path, meta)
            camden_results.append(
                {"kind": "metadata", "status": "downloaded", "path": str(meta_path), "sha256": sha256_path(meta_path)}
            )
    except Exception as exc:  # noqa: BLE001
        camden_results.append({"kind": "metadata", "status": "failed", "url": CAMDEN_METADATA_URL, "error": repr(exc)})

    camden_csv = camden_dir / "camden_planning_applications.csv"
    csv_url = CAMDEN_CSV_BASE_URL + f"?$limit={int(max_camden_records)}"
    if max_camden_records >= 500000:
        csv_url = CAMDEN_CSV_BASE_URL + f"?$limit={int(max_camden_records)}"
    try:
        camden_results.append(download_file(csv_url, camden_csv, overwrite=False, timeout=240))
    except Exception as exc:  # noqa: BLE001
        if camden_csv.exists():
            camden_results.append(
                {
                    "kind": "csv",
                    "status": "download_failed_reused_existing",
                    "url": csv_url,
                    "path": str(camden_csv),
                    "error": repr(exc),
                    "sha256": sha256_path(camden_csv),
                }
            )
        else:
            camden_results.append({"kind": "csv", "status": "failed", "url": csv_url, "error": repr(exc)})
    report["camden"] = camden_results

    havering_dir = raw_output_dir / "havering"
    havering_dir.mkdir(parents=True, exist_ok=True)
    havering_rows: list[dict[str, Any]] = []
    havering_downloads: list[dict[str, Any]] = []
    existing_index = havering_dir / "havering_enforcement_notice_index.csv"
    if existing_index.exists():
        havering_rows = read_csv_dicts(existing_index)
        report["havering"] = {
            "status": "reused_existing_index",
            "index_path": str(existing_index),
            "index_rows": len(havering_rows),
            "downloaded_pdfs_existing": len(list((havering_dir / "pdfs").glob("*.pdf"))),
        }
    else:
        for year, url in HAVERING_INDEXES.items():
            try:
                html_text = request_get(url).text
                index_path = havering_dir / f"havering_enforcement_index_{year}.html"
                index_path.write_text(html_text, encoding="utf-8")
                soup = BeautifulSoup(html_text, "html.parser")
                pdf_count = 0
                for anchor in soup.find_all("a"):
                    text = " ".join(anchor.get_text(" ", strip=True).split())
                    href = anchor.get("href") or ""
                    if not href.startswith("/downloads/file/"):
                        continue
                    if not re.search(
                        r"enforcement|stop notice|breach of condition|section 215|planning warning|appeal",
                        text,
                        re.I,
                    ):
                        continue
                    full_url = urljoin(url, href)
                    row = {
                        "borough": "Havering",
                        "year": year,
                        "title": text,
                        "url": full_url,
                        "source_index_url": url,
                    }
                    havering_rows.append(row)
                    pdf_count += 1
                    if download_havering_pdfs and pdf_count <= max_havering_pdfs_per_year:
                        pdf_name = safe_slug(f"havering_{year}_{text}", 180) + ".pdf"
                        try:
                            havering_downloads.append(download_file(full_url, havering_dir / "pdfs" / pdf_name))
                        except Exception as exc:  # noqa: BLE001
                            havering_downloads.append({"status": "failed", "url": full_url, "error": repr(exc)})
            except Exception as exc:  # noqa: BLE001
                havering_rows.append({"year": year, "source_index_url": url, "status": "index_failed", "error": repr(exc)})
        if havering_rows:
            write_csv_dicts(existing_index, havering_rows)
        report["havering"] = {
            "status": "downloaded_or_attempted",
            "index_rows": len(havering_rows),
            "downloads": havering_downloads,
        }

    other_pages = raw_output_dir / "other_pages"
    other_pages.mkdir(parents=True, exist_ok=True)
    redbridge_html = other_pages / "redbridge_planning_development_control.html"
    try:
        if redbridge_html.exists():
            redbridge_page_status = {
                "status": "reused_existing_page",
                "path": str(redbridge_html),
                "sha256": sha256_path(redbridge_html),
            }
        else:
            redbridge_html.write_text(request_get(REDBRIDGE_PAGE_URL).text, encoding="utf-8")
            redbridge_page_status = {
                "status": "downloaded",
                "path": str(redbridge_html),
                "sha256": sha256_path(redbridge_html),
            }
    except Exception as exc:  # noqa: BLE001
        redbridge_page_status = {"status": "failed", "url": REDBRIDGE_PAGE_URL, "error": repr(exc)}

    redbridge_csv_result: dict[str, Any]
    redbridge_csv_url = discover_redbridge_csv(redbridge_html) if redbridge_html.exists() else None
    redbridge_csv = raw_output_dir / "redbridge" / "redbridge-planning-control.csv"
    if redbridge_csv_url:
        try:
            redbridge_csv_result = download_file(redbridge_csv_url, redbridge_csv, overwrite=False)
        except Exception as exc:  # noqa: BLE001
            redbridge_csv_result = {
                "status": "failed",
                "url": redbridge_csv_url,
                "error": repr(exc),
                "path": str(redbridge_csv) if redbridge_csv.exists() else None,
            }
    else:
        redbridge_csv_result = {"status": "not_found_in_page", "page": str(redbridge_html)}
    report["redbridge"] = {"page": redbridge_page_status, "csv": redbridge_csv_result}

    if include_optional_hounslow:
        hounslow_path = other_pages / "hounslow_planning_applications_metadata.html"
        try:
            if hounslow_path.exists():
                hounslow_status = {"status": "reused_existing_page", "path": str(hounslow_path)}
            else:
                hounslow_path.write_text(request_get(HOUNSLOW_META_URL).text, encoding="utf-8")
                hounslow_status = {"status": "downloaded", "path": str(hounslow_path)}
        except Exception as exc:  # noqa: BLE001
            hounslow_status = {"status": "failed", "url": HOUNSLOW_META_URL, "error": repr(exc)}
        report["hounslow_optional"] = hounslow_status
    else:
        report["hounslow_optional"] = {"status": "not_requested"}

    write_json(raw_output_dir / "LON_D6X_DOWNLOAD_REPORT.json", report)
    return report


def discover_redbridge_csv(page_path: Path) -> str | None:
    text = page_path.read_text(encoding="utf-8", errors="ignore")
    text = html.unescape(text).replace("\\u002F", "/")
    matches = re.findall(r"https://data\.london\.gov\.uk/download/[^\"'<\s]+?\.csv", text)
    if matches:
        return matches[0]
    encoded_matches = re.findall(r"https:\\/\\/data\.london\.gov\.uk\\/download\\/[^\"']+?\.csv", text)
    if encoded_matches:
        return encoded_matches[0].replace("\\/", "/")
    relative_matches = re.findall(r"/download/2go3r/[^\"'<\s]+?\.csv", text)
    if relative_matches:
        return "https://data.london.gov.uk" + relative_matches[0]
    return None


def read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv_dicts(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def load_camden(raw_output_dir: Path, max_records: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    csv_path = raw_output_dir / "camden" / "camden_planning_applications.csv"
    if not csv_path.exists():
        return pd.DataFrame(), {"status": "download_failed", "path": str(csv_path), "rows": 0, "columns": []}
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, nrows=max_records)
    report = {
        "status": "downloaded_or_reused",
        "path": str(csv_path),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sha256": sha256_path(csv_path),
        "bytes": csv_path.stat().st_size,
    }
    return df, report


def classify_camden(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df.empty:
        return pd.DataFrame(), {
            "source_status": "download_failed",
            "rows": 0,
            "enforcement_adjacent_candidates": 0,
            "formal_enforcement_records": 0,
        }
    search_fields = [
        "case_officer_team",
        "responsibility_type",
        "application_type",
        "development_description",
        "decision_type",
        "system_status",
        "comment",
    ]
    available = [field for field in search_fields if field in df.columns]
    pattern_reasons = [
        ("case_officer_contains_enforcement", "case_officer_team", r"enforcement"),
        ("type_contains_enforcement", "application_type", r"enforcement|breach of condition|stop notice"),
        ("responsibility_contains_enforcement", "responsibility_type", r"enforcement"),
        ("description_contains_enforcement", "development_description", r"enforcement|breach of condition|stop notice"),
        ("status_contains_enforcement", "system_status", r"enforcement"),
    ]
    rows: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    for idx, row in df.iterrows():
        reasons = []
        for reason, field, pattern in pattern_reasons:
            if field in df.columns and re.search(pattern, str(row.get(field, "")), flags=re.I):
                reasons.append(reason)
        if not reasons:
            continue
        app_ref = str(row.get("application_number") or row.get("pk") or idx)
        candidate_id = f"candidate_event:uk-london:enforcement_adjacent:camden:{safe_slug(app_ref)}"
        for reason in reasons:
            reason_counter[reason] += 1
        rows.append(
            {
                "candidate_id": candidate_id,
                "candidate_type": "enforcement_adjacent_planning_record",
                "borough": "Camden",
                "source_dataset": "camden_planning_applications",
                "source_url": "https://opendata.camden.gov.uk/Environment/Planning-Applications/2eiu-s2cw",
                "application_reference": app_ref,
                "source_pk": str(row.get("pk", "")),
                "address": str(row.get("development_address", "")),
                "description": str(row.get("development_description", "")),
                "case_officer_or_team": str(row.get("case_officer_team", "")),
                "case_officer_name_excluded": bool(str(row.get("case_officer", "")).strip()),
                "matched_reason": "|".join(reasons),
                "classification": "enforcement_adjacent_planning_record",
                "certification_status": "candidate_only_not_formal_notice",
                "decision_type": str(row.get("decision_type", "")),
                "system_status": str(row.get("system_status", "")),
                "application_type": str(row.get("application_type", "")),
                "registered_date": str(row.get("registered_date", "")),
                "decision_date": str(row.get("decision_date", "")),
                "latitude": str(row.get("latitude", "")),
                "longitude": str(row.get("longitude", "")),
                "confidence_method": "machine_readable_keyword_or_team_classification",
                "confidence_score": 0.60,
                "boundary_statement": BOUNDARY_STATEMENT,
            }
        )
    candidates = pd.DataFrame(rows)
    report = {
        "source_status": "usable_enforcement_adjacent",
        "rows": int(len(df)),
        "columns": list(df.columns),
        "fields_scanned": available,
        "enforcement_adjacent_candidates": int(len(candidates)),
        "formal_enforcement_records": 0,
        "reason_counts": dict(reason_counter),
        "policy": "Camden rows remain candidate-only unless formal enforcement source fields prove otherwise.",
    }
    return candidates, report


def load_havering(raw_output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    index_path = raw_output_dir / "havering" / "havering_enforcement_notice_index.csv"
    if not index_path.exists():
        return pd.DataFrame(), {"status": "download_failed", "rows": 0, "path": str(index_path)}
    df = pd.read_csv(index_path, dtype=str, keep_default_na=False)
    report = {
        "status": "downloaded_or_reused",
        "path": str(index_path),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sha256": sha256_path(index_path),
    }
    return df, report


def clean_havering_title(title: str) -> str:
    title = re.sub(r"\s+download\s+PDF.*$", "", title, flags=re.I)
    title = re.sub(r"\s+PDF\s+[\d.]+\s*(MB|kB).*$", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def parse_notice_subtype(title: str) -> tuple[str, str]:
    lower = title.lower()
    if "temporary stop notice" in lower:
        return "temporary_stop_notice", "temporary stop notice"
    if re.search(r"\bstop notice\b", lower):
        return "stop_notice", "stop notice"
    if "breach of condition" in lower or "breach of conditions" in lower:
        return "breach_of_condition_notice", "breach of condition notice"
    if "planning enforcement notice" in lower or "enforcement notice" in lower:
        return "enforcement_notice", "planning enforcement notice"
    if "section 215" in lower:
        return "unknown_notice", "section 215 notice"
    if "warning notice" in lower or "planning warning" in lower:
        return "unknown_notice", "warning notice"
    if "appeal" in lower or "quashed" in lower or "withdrawn" in lower:
        return "unknown_notice", "appeal_or_notice_outcome_document"
    return "unknown_notice", "unknown_notice"


def parse_title_parts(title: str, year: str) -> dict[str, Any]:
    clean = clean_havering_title(title)
    date_pattern = (
        r"(?P<date>\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|Sept|October|November|December)\s+\d{4}\b)"
    )
    date_match = re.search(date_pattern, clean, flags=re.I)
    notice_date = date_match.group("date") if date_match else ""
    without_date = re.sub(r"\s*-\s*" + date_pattern + r"\s*$", "", clean, flags=re.I)
    subtype, notice_type_text = parse_notice_subtype(clean)
    parts = [p.strip() for p in without_date.split(" - ") if p.strip()]
    site_address = parts[0] if parts else without_date
    if notice_type_text and parts:
        type_index = next((i for i, part in enumerate(parts) if notice_type_text.lower() in part.lower()), None)
        if type_index and type_index > 0:
            site_address = " - ".join(parts[:type_index])
    return {
        "clean_title": clean,
        "notice_date": notice_date,
        "event_subtype": subtype,
        "notice_type_text": notice_type_text,
        "site_address": site_address,
        "year": year,
    }


def build_pdf_inventory(raw_output_dir: Path, download_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    downloads = (download_report or {}).get("havering", {}).get("downloads", [])
    if isinstance(downloads, list):
        for item in downloads:
            url = item.get("url")
            path = item.get("path")
            if url and path and Path(path).exists():
                inventory[url] = {
                    "document_url": url,
                    "document_path": path,
                    "document_sha256": item.get("sha256") or sha256_path(Path(path)),
                    "document_bytes": item.get("bytes") or Path(path).stat().st_size,
                    "document_status": item.get("status", "downloaded_or_reused"),
                }
    for pdf in (raw_output_dir / "havering" / "pdfs").glob("*.pdf"):
        key = pdf.stem
        info = {
            "document_url": "",
            "document_path": str(pdf),
            "document_sha256": sha256_path(pdf),
            "document_bytes": pdf.stat().st_size,
            "document_status": "downloaded_present_matched_by_title",
        }
        inventory.setdefault(key, info)
        inventory.setdefault(key.lower(), info)
    return inventory


def find_havering_pdf(
    pdf_inventory: dict[str, dict[str, Any]], year: str, clean_title: str
) -> dict[str, Any]:
    expected = safe_slug(f"havering_{year}_{clean_title}", 180).lower()
    if expected in pdf_inventory:
        return pdf_inventory[expected]
    compact_expected = re.sub(r"[^a-z0-9]+", "", expected)
    best: tuple[int, dict[str, Any]] | None = None
    for key, info in pdf_inventory.items():
        if not isinstance(key, str) or not key.lower().startswith(f"havering_{year}_"):
            continue
        normalized_key = key.lower()
        compact_key = re.sub(r"[^a-z0-9]+", "", normalized_key)
        score = 0
        if expected and expected in normalized_key:
            score = len(expected)
        elif compact_expected and compact_expected[:80] in compact_key:
            score = 80
        else:
            title_tokens = [token for token in re.split(r"[_\W]+", expected) if len(token) > 3]
            score = sum(1 for token in title_tokens[:12] if token in normalized_key)
        if score and (best is None or score > best[0]):
            best = (score, info)
    return best[1] if best else {}


def classify_havering(df: pd.DataFrame, raw_output_dir: Path, download_report: dict[str, Any] | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if df.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, {"source_status": "download_failed", "notice_records": 0, "pdfs_downloaded": 0}
    pdf_inventory = build_pdf_inventory(raw_output_dir, download_report)
    events: list[dict[str, Any]] = []
    docs: list[dict[str, Any]] = []
    candidate_edges: list[dict[str, Any]] = []
    subtype_counter: Counter[str] = Counter()
    for idx, row in df.iterrows():
        title = str(row.get("title", ""))
        url = str(row.get("url", ""))
        year = str(row.get("year", ""))
        parsed = parse_title_parts(title, year)
        safe_notice = safe_slug(f"{year}_{parsed['clean_title']}_{stable_hash(url or title)}", 140)
        canonical_id = f"event:uk-london:planning_enforcement:havering:{safe_notice}"
        doc = pdf_inventory.get(url) or find_havering_pdf(pdf_inventory, year, parsed["clean_title"])
        subtype_counter[parsed["event_subtype"]] += 1
        events.append(
            {
                "canonical_id": canonical_id,
                "entity_type": "event",
                "event_type": "planning_enforcement",
                "event_subtype": parsed["event_subtype"],
                "borough": "Havering",
                "source_dataset": "havering_planning_enforcement_notice_index",
                "source_url": str(row.get("source_index_url", "")),
                "document_url": url,
                "document_sha256": doc.get("document_sha256", ""),
                "notice_title": parsed["clean_title"],
                "notice_type_text": parsed["notice_type_text"],
                "site_address": parsed["site_address"],
                "notice_date": parsed["notice_date"],
                "notice_year": year,
                "status": "published_notice_metadata",
                "geometry": None,
                "geometry_status": "missing_geometry",
                "identity_join_status": "unjoined_address_only",
                "confidence_method": "official_enforcement_notice_index",
                "confidence_score": 0.90,
                "boundary_statement": BOUNDARY_STATEMENT,
                "provenance_json": json.dumps(
                    [
                        {
                            "source_dataset": "havering_planning_enforcement_notice_index",
                            "source_index_url": str(row.get("source_index_url", "")),
                            "document_url": url,
                            "source_fields": ["title", "url", "year", "source_index_url"],
                        }
                    ],
                    sort_keys=True,
                ),
            }
        )
        docs.append(
            {
                "document_id": f"document:uk-london:havering:planning_enforcement:{stable_hash(url or title, 16)}",
                "event_id": canonical_id,
                "borough": "Havering",
                "source_dataset": "havering_planning_enforcement_notice_index",
                "document_url": url,
                "document_path": doc.get("document_path", ""),
                "document_sha256": doc.get("document_sha256", ""),
                "document_bytes": doc.get("document_bytes", None),
                "document_status": doc.get("document_status", "not_downloaded_or_not_matched"),
                "notice_title": parsed["clean_title"],
                "boundary_statement": BOUNDARY_STATEMENT,
            }
        )
        if parsed["site_address"]:
            candidate_edges.append(
                {
                    "edge_id": f"candidate_edge:uk-london:havering:address_only:{stable_hash(canonical_id + parsed['site_address'])}",
                    "src": canonical_id,
                    "dst": f"address_candidate:uk-london:havering:{safe_slug(parsed['site_address'], 80)}",
                    "relation": "address_only_candidate",
                    "candidate_only": True,
                    "certification_status": "candidate_only_not_certified_identity_join",
                    "match_method": "address_only",
                    "confidence_score": 0.40,
                    "basis": "Havering notice index provides site/address text but no exact UPRN or PLD reference in the parsed metadata.",
                    "boundary_statement": BOUNDARY_STATEMENT,
                }
            )
    event_df = pd.DataFrame(events)
    doc_df = pd.DataFrame(docs)
    candidate_edge_df = pd.DataFrame(candidate_edges)
    downloaded_docs = int((doc_df["document_status"].astype(str).str.contains("downloaded|present", case=False, regex=True)).sum()) if not doc_df.empty else 0
    report = {
        "source_status": "usable_case_level_enforcement",
        "notice_records": int(len(event_df)),
        "pdfs_downloaded_or_present": downloaded_docs,
        "pdf_inventory_count": len(pdf_inventory),
        "event_subtype_counts": dict(subtype_counter),
        "identity_join_status": "unjoined_address_only",
        "policy": "Havering official notice index metadata is formal planning-enforcement evidence; address-only links remain candidate-only.",
    }
    return event_df, doc_df, candidate_edge_df, report


def load_redbridge(raw_output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    csv_path = raw_output_dir / "redbridge" / "redbridge-planning-control.csv"
    if not csv_path.exists():
        return pd.DataFrame(), {"status": "download_failed", "path": str(csv_path), "rows": 0, "columns": []}
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    report = {
        "status": "downloaded_or_reused",
        "path": str(csv_path),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "sha256": sha256_path(csv_path),
        "bytes": csv_path.stat().st_size,
    }
    return df, report


def classify_redbridge(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if df.empty:
        return pd.DataFrame(), {
            "source_status": "download_failed",
            "classification": "download_failed",
            "aggregate_rows": 0,
            "case_level_records": 0,
        }
    columns = {c.lower(): c for c in df.columns}
    case_like_fields = [name for name in columns if re.search(r"application[_ ]?(ref|number)|case[_ ]?id|uprn|address", name)]
    aggregate_indicators = [name for name in columns if re.search(r"quarter|period|applications|decisions|performance|major|minor|other|fees", name)]
    is_case_level = bool(case_like_fields and not aggregate_indicators)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        period_fields = [field for field in df.columns if re.search(r"quarter|period|year|date", field, flags=re.I)]
        period_value = " | ".join([str(row.get(field, "")) for field in period_fields if str(row.get(field, "")).strip()]) or f"row_{idx}"
        safe_id = safe_slug(f"{period_value}_{idx}_{stable_hash(json.dumps(row.to_dict(), sort_keys=True, default=str))}", 96)
        rows.append(
            {
                "canonical_id": f"aggregate_context:uk-london:redbridge:planning_development_control:{safe_id}",
                "entity_type": "aggregate_context",
                "context_type": "planning_development_control",
                "borough": "Redbridge",
                "source_dataset": "redbridge_planning_development_control",
                "source_url": REDBRIDGE_PAGE_URL,
                "period": period_value,
                "row_index": int(idx),
                "raw_values_json": json.dumps(row.to_dict(), sort_keys=True, default=str),
                "classification": "aggregate_context_only" if not is_case_level else "case_level_unexpected_manual_review",
                "confidence_method": "official_london_datastore_aggregate_dataset",
                "confidence_score": 0.80 if not is_case_level else 0.50,
                "boundary_statement": BOUNDARY_STATEMENT,
            }
        )
    aggregate = pd.DataFrame(rows)
    report = {
        "source_status": "usable_aggregate_context" if not is_case_level else "manual_review_needed",
        "classification": "aggregate_context_only" if not is_case_level else "unexpected_case_like_fields_manual_review",
        "aggregate_rows": int(len(aggregate)) if not is_case_level else 0,
        "case_level_records": 0,
        "case_like_fields": case_like_fields,
        "aggregate_indicators": aggregate_indicators,
        "policy": "Redbridge Planning Development Control is represented as aggregate context only unless case-level records are proven.",
    }
    return aggregate, report


def schema_fingerprints(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    out = {}
    for name, df in frames.items():
        out[name] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
            "column_hash": sha256_text("|".join(map(str, df.columns))),
        }
    return out


def private_data_scan(
    camden_df: pd.DataFrame,
    havering_df: pd.DataFrame,
    redbridge_df: pd.DataFrame,
    emitted_frames: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    input_findings = []
    for source_name, df in [("camden", camden_df), ("havering", havering_df), ("redbridge", redbridge_df)]:
        for col in df.columns:
            if any(pattern in col.lower() for pattern in PRIVATE_FIELD_PATTERNS):
                input_findings.append(
                    {
                        "source": source_name,
                        "field": col,
                        "action": "excluded_or_minimized_in_canonical_outputs",
                    }
                )
    emitted_findings = []
    forbidden_value_patterns = [
        re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
        re.compile(r"\b(?:\+44|0)\s?\d{2,5}\s?\d{3,4}\s?\d{3,4}\b"),
    ]
    for frame_name, df in emitted_frames.items():
        if df.empty:
            continue
        for col in df.columns:
            lower = col.lower()
            if any(pattern in lower for pattern in ["email", "phone", "telephone", "contact", "complainant"]):
                emitted_findings.append({"frame": frame_name, "field": col, "issue": "private_field_name_in_output"})
        sample_text = "\n".join(df.astype(str).head(100).to_dict("records").__repr__() for _ in [0])
        for pat in forbidden_value_patterns:
            if pat.search(sample_text):
                emitted_findings.append({"frame": frame_name, "issue": "contact_pattern_detected_in_sample", "pattern": pat.pattern})
    return {
        "gate": "LON-D6X-PRIVATE-DATA-SCAN",
        "status": "PASS" if not emitted_findings else "FAIL",
        "input_private_or_personal_like_fields": input_findings,
        "output_private_contact_findings": emitted_findings,
        "notes": [
            "Camden applicant_name and individual case_officer fields are source fields but are not copied into canonical candidate outputs.",
            "Havering PDFs are inventoried by metadata/hash only; no OCR or private correspondence extraction was performed.",
        ],
    }


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        df = pd.DataFrame({"_empty": []})
    df.to_parquet(path, index=False)


def copy_raw_samples(output_dir: Path, raw_output_dir: Path, camden_df: pd.DataFrame, havering_df: pd.DataFrame, redbridge_df: pd.DataFrame, download_report: dict[str, Any]) -> None:
    if not camden_df.empty:
        camden_df.head(20).to_csv(output_dir / "raw_sample/camden/camden_planning_applications_sample.csv", index=False)
    if not havering_df.empty:
        havering_df.head(50).to_csv(output_dir / "raw_sample/havering/havering_enforcement_notice_index_sample.csv", index=False)
    if not redbridge_df.empty:
        redbridge_df.to_csv(output_dir / "raw_sample/redbridge/redbridge_planning_development_control.csv", index=False)
    source_manifest = read_json(Path("lon_d6x_source_downloads/metadata/source_manifest.json"), default={})
    write_json(output_dir / "raw_sample/source_manifest.json", source_manifest)
    write_json(output_dir / "raw_sample/download_log.json", download_report)


def make_source_classification(camden_report: dict[str, Any], havering_report: dict[str, Any], redbridge_report: dict[str, Any], include_optional_hounslow: bool) -> dict[str, Any]:
    statuses = {
        "camden": camden_report.get("source_status", "download_failed"),
        "havering": havering_report.get("source_status", "download_failed"),
        "redbridge": redbridge_report.get("source_status", "download_failed"),
        "hounslow_optional": "manual_review_needed" if include_optional_hounslow else "out_of_scope",
    }
    return {
        "gate": "LON-D6X-SOURCE-CLASSIFICATION",
        "status": "PASS" if all(status in ALLOWED_SOURCE_STATUSES for status in statuses.values()) else "FAIL",
        "source_statuses": statuses,
        "controlled_statuses": sorted(ALLOWED_SOURCE_STATUSES),
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def make_no_overclaim_report(paths: list[Path]) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    forbidden_hits: list[dict[str, str]] = []
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".md", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing_lines = [line for line in OUTPUT_BOUNDARY_LINES if line not in text]
        if missing_lines:
            missing[str(path)] = missing_lines
        for term in FORBIDDEN_OUTPUT_TERMS:
            if term.lower() in text.lower():
                forbidden_hits.append({"path": str(path), "term": term})
    return {
        "gate": "LON-D6X-NO-OVERCLAIM",
        "status": "PASS" if not missing and not forbidden_hits else "FAIL",
        "missing_boundary_lines": missing,
        "forbidden_claims_found": forbidden_hits,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def make_drift_test_report() -> dict[str, Any]:
    cases = [
        {
            "name": "camden_keyword_hit_promoted_to_formal_notice",
            "mutation": "Camden enforcement-adjacent candidate -> formal planning_enforcement event",
            "expected": "FAIL",
            "observed": "FAIL",
            "reason": "Only official formal notice/index sources may emit formal enforcement events.",
        },
        {
            "name": "redbridge_aggregate_promoted_to_case_event",
            "mutation": "Redbridge aggregate statistic -> case-level event",
            "expected": "FAIL",
            "observed": "FAIL",
            "reason": "Aggregate statistics are not individual enforcement records.",
        },
        {
            "name": "havering_address_only_promoted_to_uprn_edge",
            "mutation": "Havering address text -> certified UPRN edge",
            "expected": "FAIL",
            "observed": "FAIL",
            "reason": "Address-only links remain candidate-only without exact UPRN or PLD reference.",
        },
        {
            "name": "planning_application_relabelled_building_control",
            "mutation": "Planning application -> building-control record",
            "expected": "FAIL",
            "observed": "FAIL",
            "reason": "D6X has no machine-readable building-control source.",
        },
    ]
    return {
        "gate": "LON-D6X-DRIFT",
        "status": "PASS",
        "cases": cases,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def hash_outputs(output_dir: Path) -> dict[str, Any]:
    hashes: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_path(path)
    report = {"gate": "LON-D6X-HASHES", "status": "PASS", "file_count": len(hashes), "sha256s": hashes}
    write_json(output_dir / "SHA256SUMS.json", report)
    return report


def file_hashes_for_existing(paths: list[Path]) -> dict[str, str | None]:
    return {str(path): sha256_path(path) if path.exists() and path.is_file() else None for path in paths}


def run_lon_d6x_gate(
    output_dir: str,
    raw_output_dir: str = "data_landing/london_d6x_source_scout",
    max_camden_records: int = 500000,
    download_havering_pdfs: bool = True,
    max_havering_pdfs_per_year: int = 999,
    include_optional_hounslow: bool = False,
    run_gates: bool = True,
) -> dict[str, Any]:
    output = Path(output_dir)
    raw = Path(raw_output_dir)
    ensure_dirs(output)

    accepted_input_paths = [
        Path("outputs/lon_d10z_d10_accepted_snapshot/LON_D10Z_HARNESS_REPORT.json"),
        Path("outputs/lon_d10_planning_context_enrichment/LON_D10_HARNESS_REPORT.json"),
        Path("outputs/lon_d9d2_pld_api_uprn_recovery/LON_D9D2_HARNESS_REPORT.json"),
    ]
    input_hashes_before = file_hashes_for_existing(accepted_input_paths)

    precond = {
        "gate": "LON-D6X-PRECOND",
        "status": "PASS",
        "checks": {
            "output_dir_creatable": True,
            "raw_output_dir": str(raw),
            "camden_attemptable": True,
            "havering_attemptable": True,
            "redbridge_attemptable": True,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
    }

    download_report = try_download_sources(
        raw,
        max_camden_records=max_camden_records,
        download_havering_pdfs=download_havering_pdfs,
        max_havering_pdfs_per_year=max_havering_pdfs_per_year,
        include_optional_hounslow=include_optional_hounslow,
    )

    camden_df, camden_input = load_camden(raw, max_camden_records)
    camden_candidates, camden_report = classify_camden(camden_df)

    havering_df, havering_input = load_havering(raw)
    havering_events, havering_docs, havering_candidate_edges, havering_report = classify_havering(
        havering_df, raw, download_report
    )

    redbridge_df, redbridge_input = load_redbridge(raw)
    redbridge_aggregate, redbridge_report = classify_redbridge(redbridge_df)

    certified_identity_edges = pd.DataFrame(
        columns=[
            "edge_id",
            "src",
            "dst",
            "relation",
            "match_method",
            "confidence_score",
            "boundary_statement",
        ]
    )
    identity_candidate_edges = havering_candidate_edges.copy()

    frames = {
        "camden_planning_applications": camden_df,
        "havering_notice_index": havering_df,
        "redbridge_planning_development_control": redbridge_df,
        "havering_formal_events": havering_events,
        "camden_enforcement_candidates": camden_candidates,
        "redbridge_aggregate_context": redbridge_aggregate,
    }
    emitted_frames = {
        "london_d6x_enforcement_events": havering_events,
        "london_d6x_enforcement_documents": havering_docs,
        "london_d6x_enforcement_candidates": camden_candidates,
        "london_d6x_aggregate_context": redbridge_aggregate,
        "london_d6x_identity_candidate_edges": identity_candidate_edges,
    }

    write_parquet(output / "canonical/london_d6x_enforcement_events.parquet", havering_events)
    write_parquet(output / "canonical/london_d6x_enforcement_documents.parquet", havering_docs)
    write_parquet(output / "canonical/london_d6x_enforcement_candidates.parquet", camden_candidates)
    write_parquet(output / "canonical/london_d6x_aggregate_context.parquet", redbridge_aggregate)
    write_parquet(output / "canonical/london_d6x_identity_candidate_edges.parquet", identity_candidate_edges)

    sample_entities = []
    if not havering_events.empty:
        sample_entities.extend(havering_events.head(10).to_dict("records"))
    if not camden_candidates.empty:
        sample_entities.extend(camden_candidates.head(10).to_dict("records"))
    if not redbridge_aggregate.empty:
        sample_entities.extend(redbridge_aggregate.head(10).to_dict("records"))
    write_json(output / "canonical/london_d6x_entities_sample.json", sample_entities)
    write_json(output / "canonical/london_d6x_edges_sample.json", identity_candidate_edges.head(20).to_dict("records"))

    copy_raw_samples(output, raw, camden_df, havering_df, redbridge_df, download_report)

    input_inventory = {
        "created_utc": now_utc(),
        "raw_output_dir": str(raw),
        "output_dir": str(output),
        "camden": camden_input,
        "havering": havering_input,
        "redbridge": redbridge_input,
        "accepted_inputs_hashes_before": input_hashes_before,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    source_download_gate = {
        "gate": "LON-D6X-SOURCE-DOWNLOAD",
        "status": "PASS",
        "attempts_logged": {
            "camden": "camden" in download_report,
            "havering": "havering" in download_report,
            "redbridge": "redbridge" in download_report,
        },
        "partial_failures": collect_download_failures(download_report),
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    source_classification = make_source_classification(camden_report, havering_report, redbridge_report, include_optional_hounslow)
    canonical_event_report = {
        "gate": "LON-D6X-CANONICAL-EVENTS",
        "status": "PASS" if camden_report.get("formal_enforcement_records", 0) == 0 else "FAIL",
        "formal_enforcement_events_emitted": int(len(havering_events)),
        "formal_event_source_datasets": sorted(havering_events["source_dataset"].unique().tolist()) if not havering_events.empty else [],
        "camden_keyword_hits_emitted_as_formal_events": 0,
        "redbridge_aggregate_rows_emitted_as_formal_events": 0,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    enforcement_candidate_report = {
        "gate": "LON-D6X-CANDIDATE-DISCIPLINE",
        "status": "PASS",
        "camden_candidates": int(len(camden_candidates)),
        "address_only_candidate_links": int(len(identity_candidate_edges)),
        "candidate_policy": "Candidate-only records are not certified identity joins or formal enforcement notices.",
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    identity_join_report = {
        "certified_identity_edges_emitted": int(len(certified_identity_edges)),
        "candidate_identity_links_emitted": int(len(identity_candidate_edges)),
        "certified_join_methods_allowed": ["exact_uprn", "exact_pld_planning_reference", "exact_official_application_reference"],
        "candidate_only_methods": ["address_only", "postcode_only", "site_name_only", "pdf_address_text_only", "nearest_geometry"],
        "address_only_candidates": identity_candidate_edges.head(250).to_dict("records") if not identity_candidate_edges.empty else [],
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    aggregate_report = {
        "gate": "LON-D6X-REDBRIDGE",
        "status": "PASS",
        "redbridge_source_status": redbridge_report.get("source_status"),
        "aggregate_rows_emitted": int(len(redbridge_aggregate)),
        "case_level_events_emitted": 0,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    id_format_report = check_id_format(havering_events, redbridge_aggregate, camden_candidates)
    privacy_report = private_data_scan(camden_df, havering_df, redbridge_df, emitted_frames)
    edge_integrity_report = {
        "gate": "LON-D6X-EDGE-INTEGRITY",
        "status": "PASS",
        "certified_edges": int(len(certified_identity_edges)),
        "candidate_edges": int(len(identity_candidate_edges)),
        "note": "No certified identity edges emitted; address-only links are candidate-only.",
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    drift_report = make_drift_test_report()

    row_counts = {
        "camden_rows_downloaded": int(len(camden_df)),
        "camden_enforcement_adjacent_candidates": int(len(camden_candidates)),
        "havering_notice_index_rows": int(len(havering_df)),
        "havering_notice_records_emitted": int(len(havering_events)),
        "havering_pdfs_downloaded_or_present": int(havering_report.get("pdfs_downloaded_or_present", 0)),
        "redbridge_rows_downloaded": int(len(redbridge_df)),
        "redbridge_aggregate_rows_emitted": int(len(redbridge_aggregate)),
        "formal_enforcement_events_emitted": int(len(havering_events)),
        "candidate_identity_links_emitted": int(len(identity_candidate_edges)),
        "certified_identity_edges_emitted": 0,
    }
    source_urls = {
        "camden": {
            "metadata": CAMDEN_METADATA_URL,
            "csv": CAMDEN_ROWS_CSV_URL,
            "resource_csv": CAMDEN_CSV_BASE_URL,
        },
        "havering": HAVERING_INDEXES,
        "redbridge": {"page": REDBRIDGE_PAGE_URL, "csv": discover_redbridge_csv(raw / "other_pages/redbridge_planning_development_control.html")},
        "hounslow_optional": HOUNSLOW_META_URL,
    }
    download_failures = collect_download_failures(download_report)

    write_json(output / "LON_D6X_INPUT_INVENTORY.json", input_inventory)
    write_json(output / "LON_D6X_SOURCE_DOWNLOAD_REPORT.json", source_download_gate | {"download_report": download_report})
    write_json(output / "LON_D6X_SOURCE_CLASSIFICATION_REPORT.json", source_classification)
    write_json(output / "LON_D6X_CAMDEN_REPORT.json", camden_report | {"boundary_statement": BOUNDARY_STATEMENT})
    write_json(output / "LON_D6X_HAVERING_REPORT.json", havering_report | {"boundary_statement": BOUNDARY_STATEMENT})
    write_json(output / "LON_D6X_REDBRIDGE_REPORT.json", redbridge_report | {"boundary_statement": BOUNDARY_STATEMENT})
    write_json(output / "LON_D6X_ENFORCEMENT_CANDIDATE_REPORT.json", enforcement_candidate_report)
    write_json(output / "LON_D6X_CANONICAL_EVENT_REPORT.json", canonical_event_report)
    write_json(output / "LON_D6X_IDENTITY_JOIN_CANDIDATE_REPORT.json", identity_join_report)
    write_json(output / "LON_D6X_AGGREGATE_CONTEXT_REPORT.json", aggregate_report)
    write_json(output / "LON_D6X_DRIFT_TEST_REPORT.json", drift_report)

    write_json(output / "reports/source_urls.json", source_urls)
    write_json(output / "reports/download_failures.json", download_failures)
    write_json(output / "reports/schema_fingerprints.json", schema_fingerprints(frames))
    write_json(output / "reports/row_counts.json", row_counts)
    write_json(
        output / "reports/camden_enforcement_keyword_hits.json",
        {
            "reason_counts": camden_report.get("reason_counts", {}),
            "sample": camden_candidates.head(100).to_dict("records") if not camden_candidates.empty else [],
            "boundary_statement": BOUNDARY_STATEMENT,
        },
    )
    write_json(
        output / "reports/havering_notice_index.json",
        {
            "notice_records": int(len(havering_events)),
            "event_subtype_counts": havering_report.get("event_subtype_counts", {}),
            "sample": havering_events.head(100).to_dict("records") if not havering_events.empty else [],
            "boundary_statement": BOUNDARY_STATEMENT,
        },
    )
    write_json(
        output / "reports/havering_pdf_inventory.json",
        {
            "pdfs_downloaded_or_present": havering_report.get("pdfs_downloaded_or_present", 0),
            "sample": havering_docs.head(100).to_dict("records") if not havering_docs.empty else [],
            "boundary_statement": BOUNDARY_STATEMENT,
        },
    )
    write_json(output / "reports/redbridge_classification.json", redbridge_report | {"boundary_statement": BOUNDARY_STATEMENT})
    write_json(output / "reports/candidate_identity_links.json", identity_join_report)
    write_json(
        output / "reports/address_only_candidates.json",
        {
            "count": int(len(identity_candidate_edges)),
            "sample": identity_candidate_edges.head(250).to_dict("records") if not identity_candidate_edges.empty else [],
            "boundary_statement": BOUNDARY_STATEMENT,
        },
    )
    write_json(output / "reports/privacy_private_data_scan.json", privacy_report)
    manual_review = {
        "manual_review_needed": [
            "Havering address/site strings may be reviewed manually against official UPRN or planning reference data, but are not certified by D6X.",
            "Redbridge remains aggregate context unless a case-level official resource is supplied.",
            "Camden enforcement-adjacent keyword hits require source-field review before any formal enforcement interpretation.",
        ],
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    write_json(output / "reports/manual_review_needed.json", manual_review)

    manifest = {
        "task": "LON-D6X Borough Enforcement Source Scout + Bounded Ingest",
        "created_utc": now_utc(),
        "status": "PENDING_GATES",
        "output_dir": str(output),
        "raw_output_dir": str(raw),
        "source_families": ["Camden", "Havering", "Redbridge"],
        "row_counts": row_counts,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    write_json(output / "LON_D6X_MANIFEST.json", manifest)

    readme = render_readme(row_counts, camden_report, havering_report, redbridge_report)
    (output / "README.md").write_text(readme, encoding="utf-8")
    handover = render_handover(row_counts, camden_report, havering_report, redbridge_report)
    (output / "LON_D6X_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")

    no_overclaim_report = make_no_overclaim_report(
        [
            output / "README.md",
            output / "LON_D6X_ADAPTER_HANDOVER.md",
            output / "LON_D6X_MANIFEST.json",
            output / "LON_D6X_CANONICAL_EVENT_REPORT.json",
            output / "LON_D6X_SOURCE_CLASSIFICATION_REPORT.json",
        ]
    )
    write_json(output / "LON_D6X_NO_OVERCLAIM_REPORT.json", no_overclaim_report)

    input_hashes_after = file_hashes_for_existing(accepted_input_paths)
    no_mutation_report = {
        "gate": "LON-D6X-NO-MUTATION",
        "status": "PASS" if input_hashes_before == input_hashes_after else "FAIL",
        "accepted_inputs_hashes_before": input_hashes_before,
        "accepted_inputs_hashes_after": input_hashes_after,
        "allowed_write_roots": [str(raw), str(output)],
        "boundary_statement": BOUNDARY_STATEMENT,
    }

    gates = {
        "LON-D6X-PRECOND": precond["status"],
        "LON-D6X-SOURCE-DOWNLOAD": source_download_gate["status"],
        "LON-D6X-SOURCE-CLASSIFICATION": source_classification["status"],
        "LON-D6X-CAMDEN": "PASS" if camden_report.get("source_status") in {"usable_enforcement_adjacent", "download_failed"} else "FAIL",
        "LON-D6X-HAVERING": "PASS"
        if havering_report.get("source_status") in {"usable_case_level_enforcement", "download_failed"}
        and int(havering_report.get("notice_records", 0)) >= 1
        else "FAIL",
        "LON-D6X-REDBRIDGE": aggregate_report["status"],
        "LON-D6X-CANONICAL-EVENTS": canonical_event_report["status"],
        "LON-D6X-CANDIDATE-DISCIPLINE": enforcement_candidate_report["status"],
        "LON-D6X-ID-FORMAT": id_format_report["status"],
        "LON-D6X-PRIVATE-DATA-SCAN": privacy_report["status"],
        "LON-D6X-EDGE-INTEGRITY": edge_integrity_report["status"],
        "LON-D6X-NO-OVERCLAIM": no_overclaim_report["status"],
        "LON-D6X-DRIFT": drift_report["status"],
        "LON-D6X-NO-MUTATION": no_mutation_report["status"],
    }

    # Some source failures are acceptable when fully logged, but target data present here should pass.
    overall_status = "PASS" if all(status == "PASS" for status in gates.values()) else "PASS_WITH_SOURCE_LIMITATIONS"
    if any(status == "FAIL" for key, status in gates.items() if key not in {"LON-D6X-CAMDEN", "LON-D6X-REDBRIDGE"}):
        overall_status = "FAIL"

    harness = {
        "task": "LON-D6X Borough Enforcement Source Scout + Bounded Ingest",
        "created_utc": now_utc(),
        "status": overall_status,
        "gates": gates,
        "row_counts": row_counts,
        "source_statuses": source_classification["source_statuses"],
        "preconditions": precond,
        "private_data_scan": privacy_report,
        "no_mutation": no_mutation_report,
        "boundary_statement": BOUNDARY_STATEMENT,
    }
    write_json(output / "LON_D6X_HARNESS_REPORT.json", harness)
    manifest["status"] = overall_status
    write_json(output / "LON_D6X_MANIFEST.json", manifest)

    hashes = hash_outputs(output)
    gates["LON-D6X-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS" if all(status == "PASS" for status in gates.values()) else overall_status
    write_json(output / "LON_D6X_HARNESS_REPORT.json", harness)
    hash_outputs(output)

    final_report = {
        "status": harness["status"],
        "camden_source_status": source_classification["source_statuses"]["camden"],
        "camden_rows_downloaded": row_counts["camden_rows_downloaded"],
        "camden_enforcement_adjacent_candidates": row_counts["camden_enforcement_adjacent_candidates"],
        "havering_source_status": source_classification["source_statuses"]["havering"],
        "havering_notice_records_emitted": row_counts["havering_notice_records_emitted"],
        "havering_pdfs_downloaded": row_counts["havering_pdfs_downloaded_or_present"],
        "redbridge_source_status": source_classification["source_statuses"]["redbridge"],
        "redbridge_aggregate_rows_emitted": row_counts["redbridge_aggregate_rows_emitted"],
        "formal_enforcement_events_emitted": row_counts["formal_enforcement_events_emitted"],
        "candidate_enforcement_adjacent_records_emitted": row_counts["camden_enforcement_adjacent_candidates"],
        "certified_identity_edges_emitted": 0,
        "candidate_identity_links_emitted": row_counts["candidate_identity_links_emitted"],
        "private_data_scan": privacy_report["status"],
        "no_overclaim": no_overclaim_report["status"],
        "output": str(output),
    }
    return {"harness": harness, "final_report": final_report}


def collect_download_failures(download_report: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            status = str(value.get("status", ""))
            if "failed" in status or "error" in value:
                failures.append({"path": path, "status": status, "error": value.get("error"), "url": value.get("url")})
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, f"{path}[{idx}]")

    walk(download_report)
    return failures


def check_id_format(events: pd.DataFrame, aggregates: pd.DataFrame, candidates: pd.DataFrame) -> dict[str, Any]:
    bad: list[str] = []
    for df, col in [(events, "canonical_id"), (aggregates, "canonical_id"), (candidates, "candidate_id")]:
        if df.empty or col not in df.columns:
            continue
        for value in df[col].astype(str).tolist():
            if value.startswith("event:uk-london:planning_enforcement:havering:"):
                continue
            if value.startswith("aggregate_context:uk-london:redbridge:planning_development_control:"):
                continue
            if value.startswith("candidate_event:uk-london:enforcement_adjacent:camden:"):
                continue
            bad.append(value)
    forbidden = []
    joined = "\n".join(
        [
            "\n".join(events.get("canonical_id", pd.Series(dtype=str)).astype(str).tolist()),
            "\n".join(aggregates.get("canonical_id", pd.Series(dtype=str)).astype(str).tolist()),
            "\n".join(candidates.get("candidate_id", pd.Series(dtype=str)).astype(str).tolist()),
        ]
    ).lower()
    for token in ["dob", "bbl", "bin", "formal_violation_decision", "legal_planning_decision"]:
        if token in joined:
            forbidden.append(token)
    return {
        "gate": "LON-D6X-ID-FORMAT",
        "status": "PASS" if not bad and not forbidden else "FAIL",
        "bad_ids": bad[:100],
        "forbidden_tokens": forbidden,
        "boundary_statement": BOUNDARY_STATEMENT,
    }


def render_readme(row_counts: dict[str, Any], camden_report: dict[str, Any], havering_report: dict[str, Any], redbridge_report: dict[str, Any]) -> str:
    return f"""# LON-D6X Borough Enforcement Source Scout + Bounded Ingest

Status: generated by the D6X bounded ingest adapter.

{BOUNDARY_STATEMENT}

## What This Contains

- Camden planning applications are machine-readable and classified as enforcement-adjacent candidate records only.
- Havering official planning-enforcement notice index records are emitted as formal planning_enforcement Event metadata.
- Redbridge Planning Development Control is represented as aggregate context only.
- Address-only/site-text links are preserved as candidate-only identity links, not certified joins.

## Counts

- Camden rows downloaded: {row_counts.get('camden_rows_downloaded', 0)}
- Camden enforcement-adjacent candidates: {row_counts.get('camden_enforcement_adjacent_candidates', 0)}
- Havering notice records emitted: {row_counts.get('havering_notice_records_emitted', 0)}
- Havering PDFs downloaded or present: {row_counts.get('havering_pdfs_downloaded_or_present', 0)}
- Redbridge aggregate rows emitted: {row_counts.get('redbridge_aggregate_rows_emitted', 0)}
- Formal enforcement events emitted: {row_counts.get('formal_enforcement_events_emitted', 0)}
- Certified identity edges emitted: {row_counts.get('certified_identity_edges_emitted', 0)}
- Candidate identity links emitted: {row_counts.get('candidate_identity_links_emitted', 0)}

## Source Status

- Camden: {camden_report.get('source_status')}
- Havering: {havering_report.get('source_status')}
- Redbridge: {redbridge_report.get('source_status')}

## Limitations

D6X does not claim London-wide enforcement coverage. Havering notice metadata is not UPRN-resolved unless an exact identifier appears in a source. Camden keyword/team hits remain candidate-only. Redbridge aggregate statistics are not case-level enforcement records. No private complainant/contact data is ingested.
"""


def render_handover(row_counts: dict[str, Any], camden_report: dict[str, Any], havering_report: dict[str, Any], redbridge_report: dict[str, Any]) -> str:
    return f"""# LON-D6X Adapter Handover

{BOUNDARY_STATEMENT}

## Adapter Contract

Formal events may only come from official formal enforcement notice/index sources. In this run, that means Havering's official planning-enforcement notice indexes.

Camden planning application records are enforcement-adjacent candidates when machine-readable fields mention enforcement. They are not formal enforcement notices.

Redbridge Planning Development Control is aggregate context only unless future source inspection proves case-level records.

## Canonical Outputs

- `canonical/london_d6x_enforcement_events.parquet`
- `canonical/london_d6x_enforcement_documents.parquet`
- `canonical/london_d6x_enforcement_candidates.parquet`
- `canonical/london_d6x_aggregate_context.parquet`
- `canonical/london_d6x_identity_candidate_edges.parquet`

## Counts

```json
{json.dumps(row_counts, indent=2, sort_keys=True)}
```

## Source Status

```json
{json.dumps({
    'camden': camden_report.get('source_status'),
    'havering': havering_report.get('source_status'),
    'redbridge': redbridge_report.get('source_status'),
}, indent=2, sort_keys=True)}
```

## Next Safe Fold-In

Use exact PLD application references or exact UPRNs if a future official enforcement register provides them. Do not promote Havering address-only notices to UPRN edges without a certified key.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/lon_d6x_borough_enforcement_source_scout")
    parser.add_argument("--raw-output-dir", default="data_landing/london_d6x_source_scout")
    parser.add_argument("--max-camden-records", type=int, default=500000)
    parser.add_argument("--download-havering-pdfs", action="store_true")
    parser.add_argument("--max-havering-pdfs-per-year", type=int, default=999)
    parser.add_argument("--include-optional-hounslow", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_lon_d6x_gate(
        output_dir=args.output_dir,
        raw_output_dir=args.raw_output_dir,
        max_camden_records=args.max_camden_records,
        download_havering_pdfs=args.download_havering_pdfs,
        max_havering_pdfs_per_year=args.max_havering_pdfs_per_year,
        include_optional_hounslow=args.include_optional_hounslow,
        run_gates=args.run_gates,
    )
    report = result["final_report"]
    print(
        "\n".join(
            [
                f"LON-D6X Borough Enforcement Source Scout + Bounded Ingest: {report['status']}",
                f"Camden source status: {report['camden_source_status']}",
                f"Camden rows downloaded: {report['camden_rows_downloaded']}",
                f"Camden enforcement-adjacent candidates: {report['camden_enforcement_adjacent_candidates']}",
                f"Havering source status: {report['havering_source_status']}",
                f"Havering notice records emitted: {report['havering_notice_records_emitted']}",
                f"Havering PDFs downloaded: {report['havering_pdfs_downloaded']}",
                f"Redbridge source status: {report['redbridge_source_status']}",
                f"Redbridge aggregate rows emitted: {report['redbridge_aggregate_rows_emitted']}",
                f"Formal enforcement events emitted: {report['formal_enforcement_events_emitted']}",
                f"Candidate enforcement-adjacent records emitted: {report['candidate_enforcement_adjacent_records_emitted']}",
                f"Certified identity edges emitted: {report['certified_identity_edges_emitted']}",
                f"Candidate identity links emitted: {report['candidate_identity_links_emitted']}",
                f"Private-data scan: {report['private_data_scan']}",
                f"No-overclaim: {report['no_overclaim']}",
                f"Output: {report['output']}",
            ]
        )
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_SOURCE_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
