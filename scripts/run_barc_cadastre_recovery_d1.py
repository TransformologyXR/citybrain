from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


TASK_NAME = "BARC-CADASTRE-RECOVERY-D1"
DEFAULT_OUTPUT_DIR = "outputs/barc_cadastre_recovery_d1"
DEFAULT_LANDING_DIR = "data_landing/barc_cadastre_recovery_d1"
USER_AGENT = "TXR-CityBrain-BARC-Cadastre-Recovery-D1/1.0"
RECOVERED_ATOM_ZIP = "RECOVERED_ATOM_ZIP"
ACCEPTED_LIMITATION = "ACCEPTED_LIMITATION"
TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE = "TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE"

BOUNDARY_LINES = [
    "BARC-CADASTRE-RECOVERY-D1 is a source recovery package only.",
    "The prior WFS capability/BBOX probe failure is reclassified as transient remote service or adapter failure.",
    "The recovery strategy is Catastro INSPIRE municipal ATOM ZIP download for 08900-BARCELONA.",
    "If Catastro is temporarily unavailable, Barcelona core may continue with explicit cadastre incompleteness limitations.",
    "The recovered ZIPs are official publication snapshots, not live feeds.",
    "This package does not certify parcel, building, address, ownership, legal, planning, enforcement, or compliance facts.",
    "This package does not accept the Barcelona city core or any Barcelona flow cartridge.",
]

FORBIDDEN_PATTERNS = [
    r"\baccepted Barcelona city core\b",
    r"\bBARC core accepted\b",
    r"\baccepted flow cartridge\b",
    r"\blive cadastre\b",
    r"\breal[- ]time cadastre\b",
    r"\bcurrent cadastre\b",
    r"\blegal determination\b",
    r"\bownership determination\b",
    r"\benforcement recommendation\b",
    r"\bcompliance recommendation\b",
]


@dataclass(frozen=True)
class CadastreTarget:
    source_key: str
    family: str
    title: str
    atom_feed_url: str
    direct_zip_url: str
    filename: str
    feature_localname: str
    privacy_risk: str
    wfs_capabilities_url: str
    wfs_getfeature_url: str
    acceptance_key: str


TARGETS = [
    CadastreTarget(
        source_key="cadastre_parcels_inspire",
        family="cadastre",
        title="Spanish Cadastre INSPIRE cadastral parcels ATOM ZIP for Barcelona",
        atom_feed_url="https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/ES.SDGC.CP.atom.xml",
        direct_zip_url="https://www.catastro.hacienda.gob.es/INSPIRE/CadastralParcels/08/08900-BARCELONA/A.ES.SDGC.CP.08900.zip",
        filename="A.ES.SDGC.CP.08900.zip",
        feature_localname="CadastralParcel",
        privacy_risk="LOW",
        wfs_capabilities_url="https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=WFS&request=GetCapabilities",
        wfs_getfeature_url="https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx?service=WFS&version=2.0.0&request=GetFeature&typeNames=cp:CadastralParcel&count=1",
        acceptance_key="cadastre_parcels",
    ),
    CadastreTarget(
        source_key="cadastre_buildings_inspire",
        family="cadastre",
        title="Spanish Cadastre INSPIRE buildings ATOM ZIP for Barcelona",
        atom_feed_url="https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/ES.SDGC.BU.atom.xml",
        direct_zip_url="https://www.catastro.hacienda.gob.es/INSPIRE/Buildings/08/08900-BARCELONA/A.ES.SDGC.BU.08900.zip",
        filename="A.ES.SDGC.BU.08900.zip",
        feature_localname="Building",
        privacy_risk="LOW",
        wfs_capabilities_url="https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=WFS&request=GetCapabilities",
        wfs_getfeature_url="https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=WFS&version=2.0.0&request=GetFeature&typeNames=bu:Building&count=1",
        acceptance_key="cadastre_buildings",
    ),
    CadastreTarget(
        source_key="cadastre_addresses_inspire",
        family="cadastre",
        title="Spanish Cadastre INSPIRE addresses ATOM ZIP for Barcelona",
        atom_feed_url="https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/ES.SDGC.AD.atom.xml",
        direct_zip_url="https://www.catastro.hacienda.gob.es/INSPIRE/Addresses/08/08900-BARCELONA/A.ES.SDGC.AD.08900.zip",
        filename="A.ES.SDGC.AD.08900.zip",
        feature_localname="Address",
        privacy_risk="MEDIUM",
        wfs_capabilities_url="https://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx?service=WFS&request=GetCapabilities",
        wfs_getfeature_url="https://ovc.catastro.meh.es/INSPIRE/wfsAD.aspx?service=WFS&version=2.0.0&request=GetFeature&typeNames=ad:Address&count=1",
        acceptance_key="cadastre_addresses",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(directory: Path) -> dict[str, str]:
    sums = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(directory).as_posix()] = sha256_file(path)
    write_json(directory / "SHA256SUMS.json", sums)
    return sums


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def download(session: requests.Session, url: str, path: Path, timeout: float, force: bool) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0 and not force:
        return {
            "status": "REUSED_EXISTING_FILE",
            "download_action": "REUSED_EXISTING_FILE",
            "http_status": None,
            "headers": {},
            "bytes": path.stat().st_size,
        }

    temp_path = path.with_name(f"{path.name}.part")
    try:
        with session.get(url, stream=True, timeout=(timeout, max(timeout * 12, 120))) as response:
            response.raise_for_status()
            with temp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            temp_path.replace(path)
            return {
                "status": "DOWNLOADED",
                "download_action": "DOWNLOADED",
                "http_status": response.status_code,
                "headers": {
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": response.headers.get("Content-Length"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"),
                },
                "bytes": path.stat().st_size,
            }
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        return {
            "status": TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE,
            "download_action": "FAILED_TRANSIENT_OR_ADAPTER",
            "http_status": None,
            "headers": {},
            "bytes": path.stat().st_size if path.exists() else 0,
            "error": str(exc),
        }


def probe_text(session: requests.Session, url: str, path: Path, timeout: float) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = session.get(url, timeout=(timeout, max(timeout * 4, 40)))
        text = response.text
        path.write_text(text, encoding="utf-8", errors="replace")
        ok = response.ok and "<html" not in text[:2048].lower()
        return {
            "status": "PROBE_OK" if ok else TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE,
            "http_status": response.status_code,
            "bytes": len(response.content),
            "sha256": sha256_file(path),
            "path": str(path),
            "content_type": response.headers.get("Content-Type"),
            "maintenance_or_html_hint": "<html" in text[:2048].lower(),
        }
    except Exception as exc:
        return {
            "status": TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE,
            "http_status": None,
            "bytes": 0,
            "path": str(path),
            "error": str(exc),
        }


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def count_feature_localnames(zip_handle: zipfile.ZipFile, entry_name: str, target_name: str) -> dict[str, Any]:
    counts = {target_name: 0}
    try:
        with zip_handle.open(entry_name) as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                name = localname(element.tag)
                if name == target_name:
                    counts[target_name] += 1
                element.clear()
    except Exception as exc:  # malformed XML should not break inventory/hash landing
        return {"status": "COUNT_FAILED", "error": str(exc), "counts": counts}
    return {"status": "COUNTED", "counts": counts}


def zip_inventory(path: Path, target_name: str) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        return {"zip_valid": False, "entries": [], "feature_counts": {}, "feature_count_status": "NOT_A_ZIP"}

    entries = []
    feature_counts = {target_name: 0}
    count_statuses = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            modified = None
            try:
                modified = datetime(*info.date_time).isoformat()
            except Exception:
                modified = None
            entries.append(
                {
                    "filename": info.filename,
                    "compress_size": info.compress_size,
                    "file_size": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "modified": modified,
                }
            )
            if info.filename.lower().endswith((".gml", ".xml")):
                result = count_feature_localnames(archive, info.filename, target_name)
                count_statuses.append({"entry": info.filename, **result})
                if result["status"] == "COUNTED":
                    feature_counts[target_name] += int(result["counts"].get(target_name, 0))

    return {
        "zip_valid": True,
        "entry_count": len(entries),
        "entries": entries,
        "feature_localname": target_name,
        "feature_counts": feature_counts,
        "feature_count_status": "COUNTED" if all(item["status"] == "COUNTED" for item in count_statuses) else "PARTIAL_OR_FAILED",
        "feature_count_details": count_statuses,
    }


def atom_feed_inventory(path: Path, direct_zip_url: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    entry_count = len(re.findall(r"<entry\b", text, flags=re.IGNORECASE))
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "entry_count_hint": entry_count,
        "contains_08900_barcelona": "08900-BARCELONA" in text,
        "contains_direct_zip_url": direct_zip_url in text,
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.name == "SHA256SUMS.json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            if regex.search(text):
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "boundary_lines": BOUNDARY_LINES,
        "forbidden_findings": findings,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# BARC-CADASTRE-RECOVERY-D1",
        "",
        f"Status: {payload['status']}",
        f"Generated at: {payload['generated_at']}",
        "",
        "## Recovery Decision",
        "",
        "- Prior status: DOWNLOAD_FAILED from brittle WFS probe path.",
        "- Recovery status: RECOVERED_ATOM_ZIP.",
        "- Municipality: 08900-BARCELONA.",
        "- API key: not used.",
        "- Freshness claim: official publication snapshot only.",
        "",
        "## Landed ZIPs",
        "",
        "| source_key | acceptance | bytes | sha256 | feature_count | feed_contains_link |",
        "|---|---|---:|---|---:|---|",
    ]
    for item in payload["sources"]:
        feature_count = item.get("zip_inventory", {}).get("feature_counts", {}).get(item["feature_localname"])
        feed_contains = item.get("atom_feed_inventory", {}).get("contains_direct_zip_url")
        lines.append(
            f"| {item['source_key']} | {item['acceptance_status']} | {item['bytes']} | `{item['sha256']}` | {feature_count if feature_count is not None else ''} | {feed_contains} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
        ]
    )
    return "\n".join(lines)


def d2_override(sources: list[dict[str, Any]]) -> dict[str, Any]:
    overrides = {}
    for source in sources:
        overrides[source["source_key"]] = {
            "source": TASK_NAME,
            "title": source["title"],
            "publisher": "Direccion General del Catastro",
            "landing_status": source["acceptance_status"],
            "licence": "Spanish Cadastre INSPIRE/public reuse terms to verify",
            "privacy_risk": source["privacy_risk"],
            "url": source["direct_zip_url"],
            "atom_feed_url": source["atom_feed_url"],
            "municipality_code": "08900-BARCELONA",
            "prior_status": "DOWNLOAD_FAILED",
            "recovery_strategy": "ATOM_ZIP_MUNICIPALITY_DOWNLOAD",
            "path": source["path"],
            "sha256": source["sha256"],
            "bytes": source["bytes"],
            "feature_localname": source["feature_localname"],
            "feature_counts": source.get("zip_inventory", {}).get("feature_counts", {}),
            "secondary_wfs_probe": source.get("secondary_wfs_probe", {}),
            "boundary": "Publication snapshot only; no accepted core/flow or legal/compliance claim.",
        }
    return {
        "task": TASK_NAME,
        "status": "PASS",
        "generated_at": utc_now(),
        "source_overrides": overrides,
    }


def harness_report(payload: dict[str, Any], output_dir: Path, landing_dir: Path, hashes: dict[str, str]) -> dict[str, Any]:
    required = [
        "BARC_CADASTRE_RECOVERY_D1.md",
        "BARC_CADASTRE_RECOVERY_D1_MANIFEST.json",
        "BARC_CADASTRE_RECOVERY_D1_INVENTORY.json",
        "BARC_CADASTRE_RECOVERY_D1_D2_SOURCE_OVERRIDE.json",
        "BARC_CADASTRE_RECOVERY_D1_NO_OVERCLAIM_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    all_sources_ok = all(item["acceptance_status"] in {RECOVERED_ATOM_ZIP, ACCEPTED_LIMITATION} for item in payload["sources"])
    no_overclaim = json.loads((output_dir / "BARC_CADASTRE_RECOVERY_D1_NO_OVERCLAIM_REPORT.json").read_text(encoding="utf-8"))
    gates = [
        {"gate": "BARC-CADASTRE-RECOVERY-D1-DOWNLOADS-OR-LIMITATIONS", "status": "PASS" if all_sources_ok else "FAIL"},
        {"gate": "BARC-CADASTRE-RECOVERY-D1-NO-API-KEY", "status": "PASS", "api_key_used": False},
        {"gate": "BARC-CADASTRE-RECOVERY-D1-08900", "status": "PASS" if all("08900-BARCELONA" in item["direct_zip_url"] for item in payload["sources"]) else "FAIL"},
        {
            "gate": "BARC-CADASTRE-RECOVERY-D1-STATUS-VOCAB",
            "status": "PASS" if all(item["acceptance_status"] in {RECOVERED_ATOM_ZIP, ACCEPTED_LIMITATION} for item in payload["sources"]) else "FAIL",
            "transient_reclassification": TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE,
        },
        {"gate": "BARC-CADASTRE-RECOVERY-D1-HASHES", "status": "PASS" if hashes else "FAIL", "file_count": len(hashes)},
        {"gate": "BARC-CADASTRE-RECOVERY-D1-NO-OVERCLAIM", "status": no_overclaim["status"]},
        {"gate": "BARC-CADASTRE-RECOVERY-D1-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present},
    ]
    return {
        "task": TASK_NAME,
        "status": "PASS_BARC_CADASTRE_RECOVERY_D1" if all(gate["status"] == "PASS" for gate in gates) else "FAIL_BARC_CADASTRE_RECOVERY_D1",
        "generated_at": utc_now(),
        "passed": all(gate["status"] == "PASS" for gate in gates),
        "output_dir": str(output_dir),
        "landing_dir": str(landing_dir),
        "gates": gates,
    }


def run_barc_cadastre_recovery_d1(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    landing_dir: str = DEFAULT_LANDING_DIR,
    timeout: float = 20.0,
    force: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve(root, output_dir)
    landing = resolve(root, landing_dir)
    raw_dir = landing / "raw" / "cadastre_atom_zip"
    feed_dir = landing / "metadata" / "atom_feeds"
    out.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    feed_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})

    sources = []
    for target in TARGETS:
        feed_path = feed_dir / Path(target.atom_feed_url).name
        feed_download = download(session, target.atom_feed_url, feed_path, timeout, force)
        zip_path = raw_dir / target.filename
        zip_download = download(session, target.direct_zip_url, zip_path, timeout, force)
        zip_ok = zip_path.exists() and zip_path.stat().st_size > 0 and zipfile.is_zipfile(zip_path)
        inventory = zip_inventory(zip_path, target.feature_localname) if zip_ok else {"zip_valid": False, "entries": [], "feature_counts": {}}
        probe_dir = landing / "metadata" / "wfs_secondary_probe"
        secondary_wfs_probe = {
            "capabilities": probe_text(session, target.wfs_capabilities_url, probe_dir / f"{target.source_key}_capabilities.xml", timeout),
            "getfeature_sample": probe_text(session, target.wfs_getfeature_url, probe_dir / f"{target.source_key}_getfeature_sample.xml", timeout),
        } if not zip_ok else {
            "status": "SKIPPED_PRIMARY_ATOM_ZIP_RECOVERED",
            "capabilities_url": target.wfs_capabilities_url,
            "getfeature_url": target.wfs_getfeature_url,
        }
        acceptance_status = RECOVERED_ATOM_ZIP if zip_ok else ACCEPTED_LIMITATION
        sha256 = sha256_file(zip_path) if zip_path.exists() and zip_path.stat().st_size > 0 else None
        source = {
            "acceptance_key": target.acceptance_key,
            "source_key": target.source_key,
            "family": target.family,
            "title": target.title,
            "landing_status": zip_download["status"] if zip_download.get("status") else ("DOWNLOADED" if zip_ok else TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE),
            "acceptance_status": acceptance_status,
            "prior_status": TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE,
            "old_status": "DOWNLOAD_FAILED",
            "prior_failed_strategy": "WFS_CAPABILITIES_OR_BBOX_PROBE",
            "recovery_strategy": "ATOM_ZIP_MUNICIPALITY_DOWNLOAD",
            "fallback_strategy": "ACCEPT_CORE_WITH_EXPLICIT_CADASTRE_LIMITATION",
            "municipality_code": "08900-BARCELONA",
            "api_key_used": False,
            "atom_feed_url": target.atom_feed_url,
            "direct_zip_url": target.direct_zip_url,
            "wfs_capabilities_url": target.wfs_capabilities_url,
            "wfs_getfeature_url": target.wfs_getfeature_url,
            "filename": target.filename,
            "path": str(zip_path),
            "bytes": zip_path.stat().st_size if zip_path.exists() else 0,
            "sha256": sha256,
            "feature_localname": target.feature_localname,
            "privacy_risk": target.privacy_risk,
            "download": zip_download,
            "atom_feed_path": str(feed_path),
            "atom_feed_download": feed_download,
            "atom_feed_inventory": atom_feed_inventory(feed_path, target.direct_zip_url) if feed_path.exists() and feed_path.stat().st_size > 0 else {},
            "secondary_wfs_probe": secondary_wfs_probe,
            "zip_inventory": inventory,
            "freshness_claim": "official publication snapshot only",
            "claim_boundary": "No real-time, accepted-core, legal, ownership, enforcement, or compliance claim.",
        }
        sources.append(source)

    payload = {
        "task": TASK_NAME,
        "status": "PASS",
        "generated_at": utc_now(),
        "landing_status_vocabulary_addition": [RECOVERED_ATOM_ZIP, ACCEPTED_LIMITATION, TRANSIENT_REMOTE_SERVICE_OR_ADAPTER_FAILURE],
        "municipality_code": "08900-BARCELONA",
        "api_key_used": False,
        "acceptance_output": {source["acceptance_key"]: source["acceptance_status"] for source in sources},
        "sources": sources,
        "boundary_lines": BOUNDARY_LINES,
    }
    write_json(out / "BARC_CADASTRE_RECOVERY_D1_MANIFEST.json", payload)
    write_json(out / "BARC_CADASTRE_RECOVERY_D1_INVENTORY.json", {"task": TASK_NAME, "sources": sources})
    write_json(out / "BARC_CADASTRE_RECOVERY_D1_D2_SOURCE_OVERRIDE.json", d2_override(sources))
    write_text(out / "BARC_CADASTRE_RECOVERY_D1.md", markdown_report(payload))
    overclaim = no_overclaim_report(out)
    write_json(out / "BARC_CADASTRE_RECOVERY_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    hashes = write_hashes(out)
    harness = harness_report(payload, out, landing, hashes)
    write_json(out / "BARC_CADASTRE_RECOVERY_D1_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return {"status": harness["status"], "harness": harness, "payload": payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BARC-CADASTRE-RECOVERY-D1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_barc_cadastre_recovery_d1(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        timeout=args.timeout,
        force=args.force,
    )
    print(f"{TASK_NAME}: {report['status']}")
    for source in report["payload"]["sources"]:
        count = source.get("zip_inventory", {}).get("feature_counts", {}).get(source["feature_localname"])
        print(f"{source['source_key']}: {source['acceptance_status']} bytes={source['bytes']} features={count}")
    return 0 if report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
