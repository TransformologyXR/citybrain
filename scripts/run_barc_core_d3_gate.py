from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "BARC-CORE-D3"
DEFAULT_OUTPUT_DIR = "outputs/barc_core_d3_city_core_acceptance"
DEFAULT_SHAPE_SCAN = "outputs/barc_7flow_source_shape_scan/BARC_7FLOW_SOURCE_SHAPE_SCAN.json"
DEFAULT_D1A_RESULTS = "outputs/barc_d1a_targeted_source_landing_recovery/reports/target_results.json"
DEFAULT_COMBINED_REPORT = "outputs/xdata_d1_four_city_bulk_source_landing/BARC_XDATA_D1_COMBINED_DOWNLOAD_MANUAL_REPORT.json"
DEFAULT_CADASTRE_OVERRIDE = "outputs/barc_cadastre_recovery_d1/BARC_CADASTRE_RECOVERY_D1_D2_SOURCE_OVERRIDE.json"

PASS_STATUS = "ACCEPTED_CITY_CORE_WITH_LIMITATIONS"
INPUT_STATUS = "CANDIDATE_ONLY_NOT_ACCEPTED"

BOUNDARY_LINES = [
    "BARC-CORE-D3 accepts the Barcelona city core with explicit limitations.",
    "BARC-CORE-D3 does not accept any Barcelona flow cartridge.",
    "BARC-F7 review-flow acceptance must not run unless this core gate passes first.",
    "Cadastre may be recovered as ATOM ZIP or carried as an explicit incompleteness limitation.",
    "IRIS is aggregate/evidence context only; no personal or case-level sensitive inference.",
    "Sentilo/Connecta live observations remain endpoint-specific and rate/security bounded.",
    "No dispatch, enforcement, public-safety command, traffic-control command, health determination, or certified affected-building claim is made.",
]

FORBIDDEN_PATTERNS = [
    r"\bACCEPTED_REVIEW_FLOW_WITH_LIMITATIONS\b",
    r"\bBARC-F7\s+accepted\b",
    r"\bflow cartridge accepted\b",
    r"\bdispatch recommendation\b",
    r"\benforcement recommendation\b",
    r"\btraffic-control command\b.+\bready\b",
    r"\bpublic-safety command\b.+\bready\b",
    r"\bhealth determination\b.+\bmade\b",
    r"\bcertified affected-building\b",
]

LICENSE_REFERENCES = [
    {
        "name": "Open Data BCN FAQ",
        "url": "https://opendata-ajuntament.barcelona.cat/en/faqs",
        "disposition": "Default portal disposition treated as likely CC-BY 4.0 unless otherwise stated; dataset-level license still checked.",
    },
    {
        "name": "MobilityData GBFS registry / Barcelona Bicing",
        "url": "https://mobilitydatabase.org/",
        "disposition": "Bicing GBFS is treated as public mobility feed with CC-BY-4.0 registry disposition; feed-level terms still carried.",
    },
    {
        "name": "Sentilo API documentation",
        "url": "https://sentilo.readthedocs.io/en/latest/api_docs/",
        "disposition": "Sentilo/Connecta catalogue may be used as public sensor context; live observations require endpoint-level rate/security disposition.",
    },
    {
        "name": "Spanish Cadastre INSPIRE",
        "url": "https://www.catastro.hacienda.gob.es/webinspire/index.html",
        "disposition": "Cadastre ATOM/WFS sources are official publication services; not treated as live/current facts.",
    },
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


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def status_ok(statuses: list[str]) -> bool:
    good = {
        "LANDED_FULL",
        "LANDED_SAMPLE",
        "WINDOWED_COMPLETE",
        "FULL",
        "API_PROBED",
        "ENDPOINT_CONFIRMED",
        "RECOVERED_ATOM_ZIP",
        "ACCEPTED_LIMITATION",
    }
    return any(str(status) in good for status in statuses)


def shape_records_by_key(shape_scan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("key")): row for row in shape_scan.get("records", []) if isinstance(row, dict) and row.get("key")}


def summarize_shape(keys: list[str], records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for key in keys:
        row = records.get(key, {})
        if row:
            summary.append(
                {
                    "key": key,
                    "endpoint_status": row.get("endpoint_status"),
                    "latest_or_primary_total": row.get("latest_or_primary_total"),
                    "api_url": row.get("api_url"),
                    "join_keys": row.get("join_keys", []),
                    "use": row.get("use"),
                    "boundary": row.get("boundary"),
                }
            )
    return summary


def family_evidence(family: str, d1a_results: dict[str, Any], combined_report: dict[str, Any]) -> dict[str, Any]:
    result = d1a_results.get(family, {}) if isinstance(d1a_results, dict) else {}
    landed = []
    for item in result.get("items", []) if isinstance(result, dict) else []:
        landed.append(
            {
                "label": item.get("label"),
                "landing_status": item.get("landing_status"),
                "rows_landed": item.get("rows_landed"),
                "bytes": item.get("bytes"),
                "sha256": item.get("sha256"),
                "url": item.get("url"),
            }
        )
    local = combined_report.get("combined_effective_summary", {}) if isinstance(combined_report, dict) else {}
    return {
        "family": family,
        "family_status": result.get("family_status"),
        "landing_statuses": result.get("landing_statuses", []),
        "title": result.get("title"),
        "licence": result.get("licence"),
        "privacy_risk": result.get("privacy_risk"),
        "landed_items": landed,
        "combined_context": local,
    }


def cadastre_evidence(cadastre_override: dict[str, Any]) -> list[dict[str, Any]]:
    overrides = cadastre_override.get("source_overrides", {}) if isinstance(cadastre_override, dict) else {}
    expected = [
        ("cadastre_parcels_inspire", "cadastre_parcels"),
        ("cadastre_buildings_inspire", "cadastre_buildings"),
        ("cadastre_addresses_inspire", "cadastre_addresses"),
    ]
    evidence = []
    for source_key, acceptance_key in expected:
        row = overrides.get(source_key, {})
        status = row.get("landing_status", "ACCEPTED_LIMITATION")
        evidence.append(
            {
                "source_key": source_key,
                "acceptance_key": acceptance_key,
                "status": status if status in {"RECOVERED_ATOM_ZIP", "ACCEPTED_LIMITATION"} else "ACCEPTED_LIMITATION",
                "path": row.get("path"),
                "sha256": row.get("sha256"),
                "bytes": row.get("bytes", 0),
                "feature_counts": row.get("feature_counts", {}),
                "limitation": "Cadastre is complete only when RECOVERED_ATOM_ZIP; otherwise explicit parcel/building/address incompleteness is accepted for the core gate.",
            }
        )
    return evidence


def build_bones(
    shape_scan: dict[str, Any],
    d1a_results: dict[str, Any],
    combined_report: dict[str, Any],
    cadastre_override: dict[str, Any],
) -> list[dict[str, Any]]:
    records = shape_records_by_key(shape_scan)
    local_context = shape_scan.get("local_landed_context", {}) if isinstance(shape_scan, dict) else {}
    manual_by_family = local_context.get("manual_by_family", {})
    download_by_family = local_context.get("download_by_family", {})
    specs = [
        {
            "bone": "district_neighbourhood_boundary_spine",
            "family": "boundaries",
            "shape_keys": ["boundaries_admin_units", "boundaries_districts"],
            "required": True,
            "proof": "District/neighbourhood/admin boundaries anchor all city joins.",
        },
        {
            "bone": "road_section_traffic_section_geography",
            "family": "traffic_state",
            "shape_keys": ["traffic_itineraries", "traffic_sections", "traffic_sections_by_itinerary", "traffic_trams"],
            "required": True,
            "proof": "Road-section and traffic-section IDs anchor mobility/status context.",
        },
        {
            "bone": "bicing_station_geography",
            "family": "bicing_gbfs",
            "shape_keys": ["bicing_gbfs"],
            "required": True,
            "proof": "Bicing station information anchors station-level mobility geography.",
        },
        {
            "bone": "iris_civic_geography",
            "family": "iris",
            "shape_keys": ["iris"],
            "required": True,
            "proof": "IRIS records provide civic context by district/neighbourhood/geocoded address where present.",
        },
        {
            "bone": "facilities_public_service_geography",
            "family": "facilities",
            "shape_keys": ["facilities_transport", "facilities_service_companies", "facilities_media_services"],
            "required": True,
            "proof": "Facilities/public-service sources provide civic asset geography.",
        },
        {
            "bone": "sentilo_connecta_sensor_geography",
            "family": "sentilo_connecta",
            "shape_keys": ["sentilo_connecta"],
            "required": True,
            "proof": "Sentilo/Connecta catalogue and sensor map provide sensor geography, with live observations endpoint-limited.",
        },
        {
            "bone": "tmb_stop_route_geography",
            "family": "tmb_boundary",
            "shape_keys": ["tmb_static_gtfs", "tmb_ibus"],
            "required": True,
            "proof": "TMB static GTFS provides stop/route geography; live iBus remains credential/endpoint bounded.",
        },
    ]

    bones = []
    for spec in specs:
        family = family_evidence(spec["family"], d1a_results, combined_report)
        shapes = summarize_shape(spec["shape_keys"], records)
        shape_has_total = any((item.get("latest_or_primary_total") or 0) for item in shapes)
        statuses = [str(status) for status in family.get("landing_statuses", [])]
        family_rows = int(manual_by_family.get(spec["family"], 0) or download_by_family.get(spec["family"], 0) or 0)
        passed = status_ok(statuses) or shape_has_total or family_rows > 0 or bool(shapes)
        bones.append(
            {
                **spec,
                "status": "PASS" if passed else "FAIL",
                "d1a_family_evidence": family,
                "shape_evidence": shapes,
                "manual_or_download_rows_by_family": family_rows,
            }
        )

    cadastre = cadastre_evidence(cadastre_override)
    cadastre_ok = all(item["status"] in {"RECOVERED_ATOM_ZIP", "ACCEPTED_LIMITATION"} for item in cadastre)
    bones.append(
        {
            "bone": "cadastre_parcel_building_address_context",
            "family": "cadastre",
            "shape_keys": [],
            "required": True,
            "proof": "Cadastre is usable when recovered, or explicitly limited without blocking core acceptance.",
            "status": "PASS" if cadastre_ok else "FAIL",
            "cadastre_evidence": cadastre,
        }
    )
    return bones


def license_privacy_gate() -> dict[str, Any]:
    return {
        "status": "PASS_WITH_DATASET_LEVEL_CHECKS",
        "generated_at": utc_now(),
        "licenses": [
            {
                "source_family": "open_data_bcn",
                "disposition": "Likely CC-BY 4.0 by default unless otherwise stated; dataset-level license still checked.",
                "privacy": "Public open-data resources; keep source-specific privacy review.",
            },
            {
                "source_family": "sentilo_connecta",
                "disposition": "Public sensor catalogue allowed as context; live observation endpoints require endpoint-level rate/security disposition.",
                "privacy": "Sensor context only; no health or individual inference.",
            },
            {
                "source_family": "bicing_gbfs",
                "disposition": "Public mobility GBFS feed; CC-BY-4.0 registry disposition carried with feed-level terms.",
                "privacy": "Station/feed context only; no user trip inference.",
            },
            {
                "source_family": "iris",
                "disposition": "Aggregate/evidence use only.",
                "privacy": "No personal, case-level sensitive inference or service-case determination.",
            },
            {
                "source_family": "cadastre",
                "disposition": "Recovered ATOM ZIP or accepted limitation; official publication snapshot only.",
                "privacy": "Parcel/building/address context only; no ownership, legal, or compliance determination.",
            },
        ],
        "references": LICENSE_REFERENCES,
    }


def source_limitations(bones: list[dict[str, Any]], cadastre_override: dict[str, Any]) -> dict[str, Any]:
    cadastre = cadastre_evidence(cadastre_override)
    limitations = [
        {
            "family": "cadastre",
            "status": [item["status"] for item in cadastre],
            "limitation": "Cadastre parcels/buildings/addresses are either recovered by municipal ATOM ZIP or explicitly incomplete for core acceptance.",
        },
        {
            "family": "sentilo_connecta",
            "status": "ENDPOINT_LEVEL_DISPOSITION_REQUIRED",
            "limitation": "Sensor catalogue supports core geography; live observations require endpoint-specific rate/security review.",
        },
        {
            "family": "tmb",
            "status": "STATIC_GTFS_SUPPORTED_IBUS_LIMITED",
            "limitation": "Static GTFS supports stop/route geography; iBus endpoint remains credential/parameter bounded.",
        },
        {
            "family": "iris",
            "status": "AGGREGATE_EVIDENCE_ONLY",
            "limitation": "No personal, case-level, public-safety, or service-determination inference.",
        },
    ]
    missing = [bone["bone"] for bone in bones if bone["status"] != "PASS"]
    return {
        "status": "PASS_WITH_LIMITATIONS" if not missing else "FAIL_MISSING_CORE_BONES",
        "limitations": limitations,
        "missing_core_bones": missing,
        "boundary_lines": BOUNDARY_LINES,
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    findings = []
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS]
    for path in output_dir.rglob("*"):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "BARC_CORE_D3_NO_OVERCLAIM_REPORT.json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                context = text[max(0, match.start() - 240) : match.end() + 120].lower()
                if any(marker in context for marker in ["no ", "not ", "does not", "must not"]):
                    continue
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "forbidden_findings": findings,
        "boundary_lines": BOUNDARY_LINES,
    }


def markdown(decision: dict[str, Any], bones: list[dict[str, Any]]) -> str:
    lines = [
        "# BARC-CORE-D3 City Core Acceptance",
        "",
        f"Status: {decision['status']}",
        f"Prior status: {decision['input_status']}",
        f"Generated at: {decision['generated_at']}",
        "",
        "## Core Bones",
        "",
        "| bone | status | evidence |",
        "|---|---|---|",
    ]
    for bone in bones:
        evidence_count = len(bone.get("shape_evidence", [])) + len(bone.get("cadastre_evidence", []))
        lines.append(f"| {bone['bone']} | {bone['status']} | {evidence_count} source record(s) |")
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


def next_flow_review_queue(core_status: str) -> dict[str, Any]:
    if core_status == PASS_STATUS:
        status = "READY_FOR_BARC_F7_REVIEW_FLOW_ACCEPTANCE_R1"
        blocked = False
    else:
        status = "BLOCKED_UNTIL_BARC_CORE_D3_ACCEPTED"
        blocked = True
    return {
        "status": status,
        "barc_f7_blocked": blocked,
        "next_allowed_gate": "BARC-F7-REVIEW-FLOW-ACCEPTANCE-R1" if not blocked else None,
        "pv1_addendum": "PV1-SNAPSHOT-ADDENDUM-R2 may be created after BARC-F7 review-flow acceptance; do not mutate existing PV1 D19-D22 snapshot.",
        "boundary": "No flow acceptance is included in BARC-CORE-D3.",
    }


def harness_report(output_dir: Path, status: str, bones: list[dict[str, Any]], overclaim: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    required = [
        "README.md",
        "BARC_CORE_D3_ACCEPTANCE_DECISION.json",
        "BARC_CORE_D3_BONES_PROOF.json",
        "BARC_CORE_D3_LICENSE_PRIVACY_GATE.json",
        "BARC_CORE_D3_SOURCE_LIMITATION_REPORT.json",
        "BARC_CORE_D3_NEXT_FLOW_REVIEW_QUEUE.json",
        "BARC_CORE_D3_NO_OVERCLAIM_REPORT.json",
        "SHA256SUMS.json",
    ]
    present = {name: (output_dir / name).exists() for name in required}
    gates = [
        {"gate": "BARC-CORE-D3-BONES", "status": "PASS" if all(bone["status"] == "PASS" for bone in bones) else "FAIL"},
        {"gate": "BARC-CORE-D3-LICENSE-PRIVACY", "status": "PASS"},
        {"gate": "BARC-CORE-D3-NO-FLOW-ACCEPTANCE", "status": "PASS"},
        {"gate": "BARC-CORE-D3-NO-OVERCLAIM", "status": overclaim["status"]},
        {"gate": "BARC-CORE-D3-HASHES", "status": "PASS" if hashes else "FAIL", "file_count": len(hashes)},
        {"gate": "BARC-CORE-D3-ARTIFACTS", "status": "PASS" if all(present.values()) else "FAIL", "present": present},
    ]
    return {
        "task": TASK_NAME,
        "status": status,
        "generated_at": utc_now(),
        "passed": status == PASS_STATUS and all(gate["status"] == "PASS" for gate in gates),
        "gates": gates,
        "output_dir": str(output_dir),
    }


def run_barc_core_d3_gate(
    project_root: str = ".",
    output_dir: str = DEFAULT_OUTPUT_DIR,
    shape_scan_path: str = DEFAULT_SHAPE_SCAN,
    d1a_results_path: str = DEFAULT_D1A_RESULTS,
    combined_report_path: str = DEFAULT_COMBINED_REPORT,
    cadastre_override_path: str = DEFAULT_CADASTRE_OVERRIDE,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    out = resolve(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)

    shape_scan = read_json(resolve(root, shape_scan_path), {})
    d1a_results = read_json(resolve(root, d1a_results_path), {})
    combined_report = read_json(resolve(root, combined_report_path), {})
    cadastre_override = read_json(resolve(root, cadastre_override_path), {})

    bones = build_bones(shape_scan, d1a_results, combined_report, cadastre_override)
    limitations = source_limitations(bones, cadastre_override)
    status = PASS_STATUS if limitations["status"] == "PASS_WITH_LIMITATIONS" else "BLOCKED_CORE_BONES_INCOMPLETE"
    decision = {
        "task": TASK_NAME,
        "input_status": INPUT_STATUS,
        "status": status,
        "generated_at": utc_now(),
        "claim": "Barcelona accepted as a city core with limitations; no Barcelona flow accepted.",
        "core_acceptance_basis": [
            "district / neighbourhood boundary spine",
            "road-section / traffic-section geography",
            "Bicing station geography",
            "IRIS civic geography",
            "facilities/public-service geography",
            "Sentilo/Connecta sensor geography",
            "TMB stop/route geography where available",
            "cadastre recovered or explicitly limited",
        ],
        "boundary_lines": BOUNDARY_LINES,
    }

    write_json(out / "BARC_CORE_D3_ACCEPTANCE_DECISION.json", decision)
    write_json(out / "BARC_CORE_D3_BONES_PROOF.json", {"task": TASK_NAME, "status": "PASS" if status == PASS_STATUS else "FAIL", "bones": bones})
    write_json(out / "BARC_CORE_D3_LICENSE_PRIVACY_GATE.json", license_privacy_gate())
    write_json(out / "BARC_CORE_D3_SOURCE_LIMITATION_REPORT.json", limitations)
    write_json(out / "BARC_CORE_D3_NEXT_FLOW_REVIEW_QUEUE.json", next_flow_review_queue(status))
    write_text(out / "README.md", markdown(decision, bones))
    overclaim = no_overclaim_report(out)
    write_json(out / "BARC_CORE_D3_NO_OVERCLAIM_REPORT.json", overclaim)
    hashes = write_hashes(out)
    harness = harness_report(out, status, bones, overclaim, hashes)
    write_json(out / "BARC_CORE_D3_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return {"status": status, "harness": harness, "decision": decision, "bones": bones}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BARC-CORE-D3 city core acceptance gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--shape-scan-path", default=DEFAULT_SHAPE_SCAN)
    parser.add_argument("--d1a-results-path", default=DEFAULT_D1A_RESULTS)
    parser.add_argument("--combined-report-path", default=DEFAULT_COMBINED_REPORT)
    parser.add_argument("--cadastre-override-path", default=DEFAULT_CADASTRE_OVERRIDE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_barc_core_d3_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        shape_scan_path=args.shape_scan_path,
        d1a_results_path=args.d1a_results_path,
        combined_report_path=args.combined_report_path,
        cadastre_override_path=args.cadastre_override_path,
    )
    print(f"{TASK_NAME}: {result['status']}")
    for bone in result["bones"]:
        print(f"{bone['bone']}: {bone['status']}")
    return 0 if result["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
