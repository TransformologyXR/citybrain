from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import requests


TASK_NAME = "LON-D9 Datastore Context Layer Download"
DEFAULT_SITEMAP_URL = "https://data.london.gov.uk/sitemap.xml"
DEFAULT_RAW_ROOT = "data_landing/london_d9_raw"
DEFAULT_OUTPUT_DIR = "outputs/lon_d9_datastore_context_download"

BOUNDARY = (
    "Downloaded/captured files are source landing artifacts from London Datastore pages discovered via "
    "https://data.london.gov.uk/sitemap.xml. Service-backed datasets may be captured as REST metadata "
    "unless a direct downloadable file is exposed by the source page."
)

DATASETS: list[dict[str, Any]] = [
    {
        "priority": 1,
        "family": "London Boroughs",
        "slug_hint": "london-boroughs",
        "dataset_url": "https://data.london.gov.uk/dataset/london-boroughs-e55pw",
        "ingest_timing": "D9B core",
    },
    {
        "priority": 1,
        "family": "Statistical GIS Boundary Files",
        "slug_hint": "statistical-gis-boundary-files-for-london",
        "dataset_url": "https://data.london.gov.uk/dataset/statistical-gis-boundary-files-for-london-20od9",
        "ingest_timing": "D9B/D9E",
    },
    {
        "priority": 1,
        "family": "Planning Local Plan Data",
        "slug_hint": "planning-local-plan-data",
        "dataset_url": "https://data.london.gov.uk/dataset/planning-local-plan-data-2zjmn",
        "ingest_timing": "D9C/D9E",
    },
    {
        "priority": 1,
        "family": "Planning Data Map / Planning Constraints Map",
        "slug_hint": "planning-data-map",
        "dataset_url": "https://data.london.gov.uk/dataset/planning-data-map-2lzrg",
        "ingest_timing": "D9A catalogue, D9E selected layers",
    },
    {
        "priority": 2,
        "family": "Opportunity Areas",
        "slug_hint": "opportunity-areas",
        "dataset_url": "https://data.london.gov.uk/dataset/opportunity-areas-epr7z",
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "Areas of Intensification",
        "slug_hint": "areas-of-intensification",
        "dataset_url": "https://data.london.gov.uk/dataset/areas-of-intensification-vdjql",
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "Strategic Industrial Land / SIL",
        "slug_hint": "strategic-industrial-land-sil",
        "dataset_url": "https://data.london.gov.uk/dataset/strategic-industrial-land-sil-2y5xy",
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "Town Centre Boundaries",
        "slug_hint": "town-centre-boundaries",
        "dataset_url": "https://data.london.gov.uk/dataset/town-centre-boundaries-e55z7",
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "Designated Open Space",
        "slug_hint": "designated-open-space",
        "dataset_url": "https://data.london.gov.uk/dataset/designated-open-space-e195k",
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "LVMF Protected Vistas",
        "slug_hint": "lvmf-protected-vistas-gis-files",
        "dataset_url": "https://data.london.gov.uk/dataset/lvmf-protected-vistas-gis-files-2yjmq",
        "alternate_dataset_urls": [
            "https://data.london.gov.uk/dataset/london-views-management-framework-lvmf-extended-background-vista-2r4o4"
        ],
        "ingest_timing": "D9E",
    },
    {
        "priority": 2,
        "family": "Biodiversity Hotspots for Planning",
        "slug_hint": "biodiversity-hotspots-for-planning",
        "dataset_url": "https://data.london.gov.uk/dataset/biodiversity-hotspots-for-planning-v8w4q",
        "ingest_timing": "D9E or later",
    },
    {
        "priority": 3,
        "family": "PTAL — Public Transport Accessibility Levels",
        "slug_hint": "public-transport-accessibility-levels",
        "dataset_url": "https://data.london.gov.uk/dataset/public-transport-accessibility-levels-24rz6",
        "ingest_timing": "D9E/D10",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str, max_len: int = 160) -> str:
    value = unquote(value)
    value = value.split("?")[0].split("#")[0]
    value = Path(value).name or "resource"
    value = re.sub(r"[^\w.\- ()]+", "_", value, flags=re.UNICODE).strip("._ ")
    return (value or "resource")[:max_len]


def family_dir_name(family: str) -> str:
    name = family.lower()
    name = name.replace("—", " ")
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts}:
            raise ValueError(f"refusing to delete unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    output_dir.mkdir(parents=True, exist_ok=True)


def get(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=90, allow_redirects=True, headers={"User-Agent": "TXR-CityBrain-D9/1.0"})
    response.raise_for_status()
    return response


def extract_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        links.append(urljoin(base_url, match.group(1)))
    seen: set[str] = set()
    unique: list[str] = []
    for link in links:
        if link not in seen:
            unique.append(link)
            seen.add(link)
    return unique


def classify_link(url: str) -> str:
    lower = unquote(url).lower()
    if "data.london.gov.uk/download/" in lower or re.search(r"/download/[0-9a-z-]+/", lower):
        return "download"
    if "featureserver" in lower:
        return "feature_server"
    if "mapserver" in lower:
        return "map_server"
    if "maps.london.gov.uk/planning" in lower or "webcat" in lower:
        return "external_tool"
    return "other"


def extension_from_url(url: str) -> str:
    name = safe_name(url)
    suffix = Path(name).suffix.lower().lstrip(".")
    return suffix or "unknown"


def wanted_download(url: str) -> bool:
    ext = extension_from_url(url)
    return ext in {"zip", "gpkg", "csv", "pdf", "png", "jpg", "jpeg", "geojson", "json", "xlsx", "xls"}


def service_metadata_url(url: str) -> str:
    return url + ("?f=pjson" if "?" not in url else "&f=pjson")


def download_file(session: requests.Session, url: str, dest: Path) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    start = time.time()
    with session.get(url, timeout=180, stream=True, allow_redirects=True, headers={"User-Agent": "TXR-CityBrain-D9/1.0"}) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp.replace(dest)
    return {
        "path": str(dest),
        "bytes": dest.stat().st_size,
        "sha256": sha256_file(dest),
        "download_seconds": round(time.time() - start, 3),
        "status": "downloaded",
    }


def capture_service_metadata(session: requests.Session, url: str, dest: Path) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta_url = service_metadata_url(url)
    response = get(session, meta_url)
    content_type = response.headers.get("content-type", "")
    text = response.text
    metadata: Any
    try:
        metadata = response.json()
    except Exception:
        metadata = {"raw_text": text[:100000], "content_type": content_type}
    dest.write_text(pretty_json(metadata) + "\n", encoding="utf-8")
    layer_count = len(metadata.get("layers", [])) if isinstance(metadata, dict) else None
    return {
        "path": str(dest),
        "bytes": dest.stat().st_size,
        "sha256": sha256_file(dest),
        "metadata_url": meta_url,
        "layer_count": layer_count,
        "status": "metadata_captured",
    }


def discover_dataset_url(sitemap_text: str, slug_hint: str, fallback: str) -> dict[str, Any]:
    pattern = re.compile(r"<loc>([^<]*" + re.escape(slug_hint) + r"[^<]*)</loc>", re.I)
    matches = pattern.findall(sitemap_text)
    return {
        "resolved_url": matches[0] if matches else fallback,
        "sitemap_match_count": len(matches),
        "sitemap_matches": matches[:10],
    }


def run_download(raw_root: Path, output_dir: Path, sitemap_url: str = DEFAULT_SITEMAP_URL) -> dict[str, Any]:
    raw_root.mkdir(parents=True, exist_ok=True)
    reset_output_dir(output_dir)
    session = requests.Session()
    started_at = utc_now()

    sitemap_response = get(session, sitemap_url)
    sitemap_text = sitemap_response.text
    sitemap_path = raw_root / "london_datastore_sitemap.xml"
    sitemap_path.write_text(sitemap_text, encoding="utf-8")

    manifest: dict[str, Any] = {
        "task": TASK_NAME,
        "status": "PASS",
        "started_at": started_at,
        "finished_at": None,
        "boundary": BOUNDARY,
        "sitemap_url": sitemap_url,
        "sitemap_path": str(sitemap_path),
        "datasets": [],
        "errors": [],
    }

    for dataset in DATASETS:
        family = dataset["family"]
        family_dir = raw_root / family_dir_name(family)
        pages_dir = family_dir / "_pages"
        services_dir = family_dir / "_services"
        pages_dir.mkdir(parents=True, exist_ok=True)
        services_dir.mkdir(parents=True, exist_ok=True)

        discovered = discover_dataset_url(sitemap_text, dataset["slug_hint"], dataset["dataset_url"])
        page_urls = [discovered["resolved_url"]] + dataset.get("alternate_dataset_urls", [])
        dataset_record: dict[str, Any] = {
            **dataset,
            "discovery": discovered,
            "raw_dir": str(family_dir),
            "page_urls": page_urls,
            "resources": [],
            "services": [],
            "external_tools": [],
            "errors": [],
        }

        for page_url in page_urls:
            try:
                page_response = get(session, page_url)
                html = page_response.text
                page_path = pages_dir / (family_dir_name(Path(urlparse(page_url).path).name) + ".html")
                page_path.write_text(html, encoding="utf-8")
                links = extract_links(html, page_url)
                dataset_record.setdefault("page_captures", []).append(
                    {
                        "url": page_url,
                        "path": str(page_path),
                        "bytes": page_path.stat().st_size,
                        "sha256": sha256_file(page_path),
                        "link_count": len(links),
                    }
                )
            except Exception as exc:
                err = {"url": page_url, "error": f"{type(exc).__name__}: {exc}"}
                dataset_record["errors"].append(err)
                manifest["errors"].append({"family": family, **err})
                continue

            for link in links:
                kind = classify_link(link)
                if kind == "download" and wanted_download(link):
                    filename = safe_name(link)
                    dest = family_dir / filename
                    resource = {
                        "url": link,
                        "kind": kind,
                        "format": extension_from_url(link),
                        "file_name": filename,
                    }
                    try:
                        if dest.exists() and dest.stat().st_size > 0:
                            result = {
                                "path": str(dest),
                                "bytes": dest.stat().st_size,
                                "sha256": sha256_file(dest),
                                "status": "already_present",
                            }
                        else:
                            result = download_file(session, link, dest)
                        resource.update(result)
                    except Exception as exc:
                        resource.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
                        manifest["errors"].append({"family": family, "url": link, "error": resource["error"]})
                    dataset_record["resources"].append(resource)
                elif kind in {"map_server", "feature_server"}:
                    service_name = safe_name(link.rstrip("/").replace("/", "_")) + ".json"
                    dest = services_dir / service_name
                    service = {"url": link, "kind": kind}
                    try:
                        result = capture_service_metadata(session, link, dest)
                        service.update(result)
                    except Exception as exc:
                        service.update({"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
                        manifest["errors"].append({"family": family, "url": link, "error": service["error"]})
                    dataset_record["services"].append(service)
                elif kind == "external_tool":
                    dataset_record["external_tools"].append({"url": link, "kind": kind})

        # Deduplicate records by URL.
        for key in ("resources", "services", "external_tools"):
            seen: set[str] = set()
            unique = []
            for item in dataset_record[key]:
                url = item.get("url")
                if url not in seen:
                    unique.append(item)
                    seen.add(url)
            dataset_record[key] = unique

        dataset_record["resource_count"] = len(dataset_record["resources"])
        dataset_record["service_count"] = len(dataset_record["services"])
        dataset_record["downloaded_file_count"] = sum(
            1 for item in dataset_record["resources"] if item.get("status") in {"downloaded", "already_present"}
        )
        manifest["datasets"].append(dataset_record)

    manifest["finished_at"] = utc_now()
    manifest["status"] = "PASS" if not manifest["errors"] else "PASS_WITH_WARNINGS"
    write_json(output_dir / "LON_D9_DATASTORE_CONTEXT_DOWNLOAD_MANIFEST.json", manifest)

    files = []
    for path in sorted(raw_root.rglob("*")):
        if path.is_file() and any(family_dir_name(d["family"]) in [part.lower() for part in path.parts] for d in DATASETS):
            files.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(output_dir / "LON_D9_DATASTORE_CONTEXT_SHA256SUMS.json", files)

    report_lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: **{manifest['status']}**",
        "",
        BOUNDARY,
        "",
        "## Dataset Summary",
        "",
        "| Priority | Family | Files | Services | Ingest timing |",
        "|---:|---|---:|---:|---|",
    ]
    for item in manifest["datasets"]:
        report_lines.append(
            f"| {item['priority']} | {item['family']} | {item['downloaded_file_count']} | {item['service_count']} | {item['ingest_timing']} |"
        )
    report_lines.extend(
        [
            "",
            "## Warnings",
            "",
            "Service-only resources are intentionally catalogued as REST metadata when the Datastore page does not expose a direct file download.",
        ]
    )
    if manifest["errors"]:
        report_lines.append("")
        report_lines.append("## Errors / Warnings")
        for err in manifest["errors"]:
            report_lines.append(f"- {err.get('family')}: {err.get('url')} — {err.get('error')}")
    (output_dir / "README.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sitemap-url", default=DEFAULT_SITEMAP_URL)
    args = parser.parse_args()
    result = run_download(Path(args.raw_root), Path(args.output_dir), args.sitemap_url)
    print(pretty_json({"status": result["status"], "datasets": len(result["datasets"]), "errors": len(result["errors"])}))
    return 0 if result["status"] in {"PASS", "PASS_WITH_WARNINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
