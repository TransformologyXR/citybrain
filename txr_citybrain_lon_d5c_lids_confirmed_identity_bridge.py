from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_lon_d4_identity_backbone_ingest import iter_csv_rows, local_header_member


TASK_NAME = "LON-D5c LIDS-Confirmed PLD Identity Bridge"
DEFAULT_LON_D4_DIR = "outputs/lon_d4_identity_backbone_ingest"
DEFAULT_LON_D5_DIR = "outputs/lon_d5_pld_planning_ingest"
DEFAULT_LON_D5B_DIR = "outputs/lon_d5b_pld_uprn_backfill"
DEFAULT_OS_SAMPLE_DIR = (
    "LON_D2_identity_backbone_sample_fixture_v0_1/"
    "lon_d2_identity_backbone_fixture/lon_d3_os_identity_samples"
)
DEFAULT_OUTPUT_DIR = "outputs/lon_d5c_lids_confirmed_identity_bridge"

BOUNDARY_STRINGS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "LON-D5c creates LIDS-confirmed UPRN identity stubs, not OpenUPRN geometry-backed entities.",
    "LON-D5c uses LIDS-confirmed UPRN identity stubs, not OpenUPRN geometry-backed entities.",
    "Geometry is missing unless separately resolved through OpenUPRN or another official geometry source.",
    "LON-D5c is a sampled identity-bridge repair only.",
    "LON-D5c does not prove complete London planning coverage.",
    "LON-D5c does not ingest enforcement notices.",
    "LON-D5c does not ingest building-control records.",
    "LON-D5c does not ingest enforcement or building-control records.",
    "LON-D5c does not create a London hero cascade.",
]
OUT_OF_SCOPE_TOKENS = {
    "enforcement_notice",
    "building_control_application",
    "stop_work_order",
    "violation",
}
FORBIDDEN_ID_TOKENS = {"bbl", "bin", "dob"}
ID_PATTERNS = {
    "parcel": re.compile(r"^parcel:uk-london:uprn:\d+$"),
    "building": re.compile(r"^building:uk-london:toid:osgb[0-9A-Za-z]+$"),
    "road_segment": re.compile(r"^road_segment:uk-london:usrn:\d+$"),
    "permit": re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$"),
}

ENTITY_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "geometry",
    "geometry_status",
    "source_reason",
    "native_identity_type",
    "schema_compatibility_role",
    "confidence",
    "provenance",
]
BRIDGE_EDGE_COLUMNS = [
    "edge_id",
    "src",
    "dst",
    "relation",
    "confidence",
    "provenance",
    "semantic_caveat",
    "source_uprn",
    "source_target_id",
    "source_confidence_text",
]
PLD_EDGE_COLUMNS = [
    "edge_id",
    "src",
    "relation",
    "dst",
    "role",
    "confidence",
    "provenance",
    "source_uprn",
    "source_application_id",
    "semantic_caveat",
]
PATH_COLUMNS = [
    "path_id",
    "path_strength",
    "permit_id",
    "uprn_id",
    "context_id",
    "context_relation",
    "pld_edge_id",
    "context_edge_id",
    "confidence_score",
    "path_summary",
    "provenance",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_col(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_json_col(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str):
        return json.loads(value) if value else None
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def frame_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    records = df.head(limit).to_dict(orient="records")
    for record in records:
        for key in ("geometry", "confidence", "provenance", "uprn_refs"):
            if key in record:
                try:
                    record[key] = parse_json_col(record[key])
                except Exception:
                    pass
    return records


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {part.lower() for part in resolved.parts} or "lon_d5c" not in resolved.name.lower():
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        last_error: Exception | None = None
        for _ in range(3):
            try:
                shutil.rmtree(resolved)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error:
            raise last_error
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def normalize_uprn(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return None
    return text.lstrip("0") or "0"


def provenance(source_dataset: str, source_id: str, source_file: str, source_fields: list[str], derivation: str) -> list[dict[str, Any]]:
    return [
        {
            "source_dataset": source_dataset,
            "source_id": source_id,
            "source_file": source_file,
            "source_fields": source_fields,
            "derivation": derivation,
            "observed_at": utc_now(),
        }
    ]


def collect_tracked_inputs(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5b_dir: Path, os_sample_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for root in [lon_d4_dir, lon_d5_dir, lon_d5b_dir, os_sample_dir]:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file() and ".venv" not in path.parts)
    for extra in [
        Path("LON_D1_identity_backbone_inventory_v0_1.zip"),
        Path("LON_D2_identity_backbone_sample_fixture_v0_1.zip"),
        Path("LON_D3_probe_review_v0_2.zip"),
    ]:
        if extra.exists() and extra.is_file():
            paths.append(extra)
    return sorted({path.resolve() for path in paths})


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists() and path.is_file()}


def inventory_inputs(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5b_dir: Path, os_sample_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "lon_d5b_dir": str(lon_d5b_dir),
        "os_sample_dir": str(os_sample_dir),
        "files": [
            {"path": str(path), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in tracked_inputs
            if path.exists() and path.is_file()
        ],
    }


def load_target_uprns(lon_d5b_dir: Path, pld_entities: pd.DataFrame) -> list[str]:
    target_path = lon_d5b_dir / "LON_D5B_TARGET_UPRN_LIST.json"
    if target_path.exists():
        value = read_json(target_path)
        targets = [normalize_uprn(item) for item in value.get("target_uprns", [])]
        return [item for item in targets if item]
    targets = []
    seen = set()
    for value in pld_entities["uprn_refs"]:
        for ref in parse_json_col(value) or []:
            normalized = normalize_uprn(ref)
            if normalized and normalized not in seen:
                seen.add(normalized)
                targets.append(normalized)
    return targets


def pld_uprns_by_record(pld_entities: pd.DataFrame) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    for row in pld_entities.to_dict(orient="records"):
        for ref in parse_json_col(row.get("uprn_refs")) or []:
            normalized = normalize_uprn(ref)
            if normalized:
                mapping[str(row["canonical_id"])].add(normalized)
    return mapping


def scan_lids_rows(os_sample_dir: Path, target_uprns: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    specs = {
        "toid": {
            "path": os_sample_dir / "lids_uprn_topographicarea_toid_download_probe.bin",
            "relation": "has_building",
            "target_type": "toid",
            "source_dataset": "OS Open Linked Identifiers BLPU-UPRN-TopographicArea-TOID",
        },
        "usrn": {
            "path": os_sample_dir / "lids_uprn_usrn_download_probe.bin",
            "relation": "on_street",
            "target_type": "usrn",
            "source_dataset": "OS Open Linked Identifiers BLPU-UPRN-Street-USRN",
        },
    }
    found: dict[str, list[dict[str, Any]]] = {"toid": [], "usrn": []}
    report: dict[str, Any] = {
        "gate": "LON-D5C-LIDS-TARGET-ROWS",
        "target_uprns_total": len(target_uprns),
        "sources": {},
    }
    for key, spec in specs.items():
        path = spec["path"]
        seen_pairs: set[tuple[str, str]] = set()
        stats = {
            "source_file": str(path),
            "attempted": path.exists(),
            "total_rows_seen": 0,
            "matched_target_rows": 0,
            "unique_pairs": 0,
            "unique_target_uprns": 0,
            "zip_member": None,
        }
        if not path.exists():
            stats["status"] = "MISSING_SOURCE"
            report["sources"][key] = stats
            continue
        stats["zip_member"] = local_header_member(path, 0)
        for row in iter_csv_rows(path, 0):
            stats["total_rows_seen"] += 1
            uprn = normalize_uprn(row.get("IDENTIFIER_1"))
            target = str(row.get("IDENTIFIER_2", "")).strip()
            if not uprn or uprn not in target_uprns or not target:
                continue
            stats["matched_target_rows"] += 1
            pair = (uprn, target)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            found[key].append(
                {
                    "uprn": uprn,
                    "target_id": target,
                    "relation": spec["relation"],
                    "target_type": spec["target_type"],
                    "source_dataset": spec["source_dataset"],
                    "source_file": path.name,
                    "source_member": stats["zip_member"]["name"],
                    "correlation_id": row.get("CORRELATION_ID"),
                    "uprn_version_date": row.get("VERSION_DATE_1"),
                    "target_version_date": row.get("VERSION_DATE_2"),
                    "confidence_text": row.get("CONFIDENCE"),
                }
            )
        stats["status"] = "SEARCHED"
        stats["unique_pairs"] = len(found[key])
        stats["unique_target_uprns"] = len({row["uprn"] for row in found[key]})
        report["sources"][key] = stats
    toid_uprns = {row["uprn"] for row in found["toid"]}
    usrn_uprns = {row["uprn"] for row in found["usrn"]}
    report.update(
        {
            "target_uprns_with_toid_rows": len(toid_uprns),
            "target_uprns_with_usrn_rows": len(usrn_uprns),
            "target_uprns_with_any_lids_rows": len(toid_uprns | usrn_uprns),
            "toid_rows_found": report["sources"]["toid"]["matched_target_rows"],
            "usrn_rows_found": report["sources"]["usrn"]["matched_target_rows"],
            "toid_unique_pairs": len(found["toid"]),
            "usrn_unique_pairs": len(found["usrn"]),
        }
    )
    report["status"] = "PASS" if report["target_uprns_with_any_lids_rows"] > 0 else "FAIL"
    return found["toid"], found["usrn"], report


def entity_confidence(method: str, score: float, basis: str) -> str:
    return json_col({"method": method, "score": score, "basis": basis})


def make_uprn_stubs(lids_rows: list[dict[str, Any]]) -> pd.DataFrame:
    by_uprn: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in lids_rows:
        by_uprn[row["uprn"]].append(row)
    records = []
    for uprn, rows in sorted(by_uprn.items(), key=lambda item: (len(item[0]), item[0])):
        records.append(
            {
                "canonical_id": f"parcel:uk-london:uprn:{uprn}",
                "entity_type": "parcel",
                "id_system": "uprn",
                "native_id": uprn,
                "city": "london",
                "country": "uk",
                "borough": "Lambeth",
                "geometry": None,
                "geometry_status": "missing_geometry_lids_identity_stub",
                "source_reason": "pld_target_uprn_confirmed_in_lids",
                "native_identity_type": "addressable_location",
                "schema_compatibility_role": "parcel_compatible_identity_node",
                "confidence": entity_confidence("official_lids_uprn_reference", 0.95, "UPRN appears in official OS Open Linked Identifiers rows for a PLD target UPRN."),
                "provenance": json_col(
                    [
                        {
                            "source_dataset": row["source_dataset"],
                            "source_id": f"{row['uprn']}_{row['target_id']}",
                            "source_file": row["source_file"],
                            "source_member": row["source_member"],
                            "source_fields": ["IDENTIFIER_1", "IDENTIFIER_2", "CORRELATION_ID", "CONFIDENCE"],
                            "derivation": "LIDS-confirmed UPRN identity stub emitted for a PLD target UPRN; no OpenUPRN geometry is claimed.",
                            "observed_at": utc_now(),
                        }
                        for row in rows[:10]
                    ]
                ),
            }
        )
    return pd.DataFrame(records, columns=ENTITY_COLUMNS)


def make_context_entity_stub(row: dict[str, Any], existing_ids: set[str]) -> dict[str, Any] | None:
    if row["target_type"] == "toid":
        canonical_id = f"building:uk-london:toid:{row['target_id']}"
        if canonical_id in existing_ids:
            return None
        return {
            "canonical_id": canonical_id,
            "entity_type": "building",
            "id_system": "toid",
            "native_id": row["target_id"],
            "city": "london",
            "country": "uk",
            "borough": "Lambeth",
            "geometry": None,
            "geometry_status": "toid_identity_only_no_polygon",
            "source_reason": "lids_context_for_pld_target_uprn",
            "native_identity_type": "topographic_area_or_building_reference",
            "schema_compatibility_role": "building_compatible_identity_node",
            "confidence": entity_confidence("official_lids_toid_reference", 0.95, "TOID appears in an official LIDS context row for a PLD target UPRN."),
            "provenance": json_col(
                provenance(
                    row["source_dataset"],
                    row["target_id"],
                    f"{row['source_file']}::{row['source_member']}",
                    ["IDENTIFIER_1", "IDENTIFIER_2", "CORRELATION_ID", "CONFIDENCE"],
                    "TOID identity stub emitted only to resolve LIDS context for a PLD target UPRN; no polygon is claimed.",
                )
            ),
        }
    canonical_id = f"road_segment:uk-london:usrn:{row['target_id']}"
    if canonical_id in existing_ids:
        return None
    return {
        "canonical_id": canonical_id,
        "entity_type": "road_segment",
        "id_system": "usrn",
        "native_id": row["target_id"],
        "city": "london",
        "country": "uk",
        "borough": "Lambeth",
        "geometry": None,
        "geometry_status": "usrn_identity_only_no_geometry",
        "source_reason": "lids_context_for_pld_target_uprn",
        "native_identity_type": "street_reference",
        "schema_compatibility_role": "road_segment_compatible_identity_node",
        "confidence": entity_confidence("official_lids_usrn_reference", 0.95, "USRN appears in an official LIDS context row for a PLD target UPRN."),
        "provenance": json_col(
            provenance(
                row["source_dataset"],
                row["target_id"],
                f"{row['source_file']}::{row['source_member']}",
                ["IDENTIFIER_1", "IDENTIFIER_2", "CORRELATION_ID", "CONFIDENCE"],
                "USRN identity stub emitted only to resolve LIDS context for a PLD target UPRN; no geometry is claimed.",
            )
        ),
    }


def make_context_stubs(toid_rows: list[dict[str, Any]], usrn_rows: list[dict[str, Any]], d4_building_ids: set[str], d4_road_ids: set[str]) -> pd.DataFrame:
    existing_ids = set(d4_building_ids) | set(d4_road_ids)
    records = []
    emitted = set()
    for row in toid_rows + usrn_rows:
        stub = make_context_entity_stub(row, existing_ids)
        if stub and stub["canonical_id"] not in emitted:
            emitted.add(stub["canonical_id"])
            records.append(stub)
    return pd.DataFrame(records, columns=ENTITY_COLUMNS)


def make_bridge_edges(toid_rows: list[dict[str, Any]], usrn_rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = []
    seen = set()
    for row in toid_rows + usrn_rows:
        dst = f"building:uk-london:toid:{row['target_id']}" if row["target_type"] == "toid" else f"road_segment:uk-london:usrn:{row['target_id']}"
        key = (row["uprn"], row["relation"], dst)
        if key in seen:
            continue
        seen.add(key)
        method = "official_lids_uprn_toid_link" if row["target_type"] == "toid" else "official_lids_uprn_usrn_link"
        basis = "Official LIDS exact UPRN-to-TOID link for a PLD target UPRN." if row["target_type"] == "toid" else "Official LIDS exact UPRN-to-USRN link for a PLD target UPRN."
        records.append(
            {
                "edge_id": f"edge:uk-london:d5c-lids:{stable_hash({'uprn': row['uprn'], 'relation': row['relation'], 'dst': dst})}",
                "src": f"parcel:uk-london:uprn:{row['uprn']}",
                "dst": dst,
                "relation": row["relation"],
                "confidence": entity_confidence(method, 0.95, basis),
                "provenance": json_col(
                    provenance(
                        row["source_dataset"],
                        f"{row['uprn']}_{row['target_id']}",
                        f"{row['source_file']}::{row['source_member']}",
                        ["IDENTIFIER_1", "IDENTIFIER_2", "CORRELATION_ID", "CONFIDENCE"],
                        "Canonical context edge emitted from official LIDS row for a PLD target UPRN.",
                    )
                ),
                "semantic_caveat": "LIDS context edge from UPRN identity stub; no direct PLD-to-TOID or PLD-to-USRN edge is created.",
                "source_uprn": row["uprn"],
                "source_target_id": row["target_id"],
                "source_confidence_text": row.get("confidence_text"),
            }
        )
    return pd.DataFrame(records, columns=BRIDGE_EDGE_COLUMNS)


def make_pld_rejoin_edges(pld_entities: pd.DataFrame, confirmed_uprns: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    records = []
    attached_records = set()
    for row in pld_entities.to_dict(orient="records"):
        refs = {normalize_uprn(ref) for ref in (parse_json_col(row.get("uprn_refs")) or [])}
        refs = {ref for ref in refs if ref}
        for uprn in sorted(refs & confirmed_uprns, key=lambda item: (len(item), item)):
            permit_id = str(row["canonical_id"])
            attached_records.add(permit_id)
            records.append(
                {
                    "edge_id": f"edge:uk-london:d5c-pld-uprn:{stable_hash({'uprn': uprn, 'permit': permit_id})}",
                    "src": f"parcel:uk-london:uprn:{uprn}",
                    "relation": "subject_of_permit",
                    "dst": permit_id,
                    "role": "planning_application_subject",
                    "confidence": entity_confidence("pld_uprn_exact_match_to_lids_confirmed_stub", 0.90, "PLD UPRN exactly matches a LIDS-confirmed UPRN identity stub."),
                    "provenance": json_col(
                        [
                            {
                                "source_dataset": "Planning London Datahub + OS Open Linked Identifiers",
                                "source_id": row.get("native_id"),
                                "source_uprn": uprn,
                                "derivation": "PLD application rejoined to a LIDS-confirmed UPRN identity stub by exact UPRN.",
                                "observed_at": utc_now(),
                            }
                        ]
                    ),
                    "source_uprn": uprn,
                    "source_application_id": row.get("native_id"),
                    "semantic_caveat": "Exact PLD UPRN to LIDS-confirmed UPRN stub only; no OpenUPRN geometry is claimed.",
                }
            )
    edge_df = pd.DataFrame(records, columns=PLD_EDGE_COLUMNS)
    pld_with_uprn = sum(1 for refs in pld_entities["uprn_refs"] if parse_json_col(refs))
    report = {
        "gate": "LON-D5C-PLD-REJOIN",
        "status": "PASS" if len(edge_df) > 0 else "FAIL",
        "pld_records_total": len(pld_entities),
        "pld_records_with_uprn": pld_with_uprn,
        "target_uprns_total": len({ref for refs in pld_entities["uprn_refs"] for ref in (parse_json_col(refs) or [])}),
        "lids_confirmed_uprns": len(confirmed_uprns),
        "pld_to_uprn_edges_emitted": len(edge_df),
        "records_attached": len(attached_records),
        "records_still_unattached": len(pld_entities) - len(attached_records),
        "join_rate_over_target_uprns": len(confirmed_uprns) / len({ref for refs in pld_entities["uprn_refs"] for ref in (parse_json_col(refs) or [])}) if len({ref for refs in pld_entities["uprn_refs"] for ref in (parse_json_col(refs) or [])}) else 0.0,
    }
    return edge_df, report


def make_connected_paths(pld_edges: pd.DataFrame, bridge_edges: pd.DataFrame, max_paths: int) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    pld_by_uprn: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pld_edges.to_dict(orient="records"):
        pld_by_uprn[str(row["source_uprn"])].append(row)
    records = []
    strong = 0
    medium = 0
    for ctx in bridge_edges.to_dict(orient="records"):
        for pld in pld_by_uprn.get(str(ctx["source_uprn"]), []):
            strength = "STRONG" if ctx["relation"] == "has_building" else "MEDIUM"
            if strength == "STRONG":
                strong += 1
            else:
                medium += 1
            records.append(
                {
                    "path_id": f"path:uk-london:d5c:{stable_hash({'pld': pld['edge_id'], 'ctx': ctx['edge_id']})}",
                    "path_strength": strength,
                    "permit_id": pld["dst"],
                    "uprn_id": pld["src"],
                    "context_id": ctx["dst"],
                    "context_relation": ctx["relation"],
                    "pld_edge_id": pld["edge_id"],
                    "context_edge_id": ctx["edge_id"],
                    "confidence_score": min(0.90, 0.95),
                    "path_summary": f"{pld['dst']} <- subject_of_permit - {pld['src']} - {ctx['relation']} -> {ctx['dst']}",
                    "provenance": json_col(
                        [
                            {
                                "source_dataset": "LON-D5c connected path derivation",
                                "source_edges": [pld["edge_id"], ctx["edge_id"]],
                                "derivation": "Connected PLD-to-UPRN-to-context path from exact PLD UPRN and official LIDS row.",
                                "observed_at": utc_now(),
                            }
                        ]
                    ),
                }
            )
            if len(records) >= max_paths:
                break
        if len(records) >= max_paths:
            break
    path_df = pd.DataFrame(records, columns=PATH_COLUMNS)
    if strong and medium:
        result = "BOTH"
    elif strong:
        result = "STRONG"
    elif medium:
        result = "MEDIUM"
    else:
        result = "FAIL"
    smoke = {
        "gate": "LON-D5C-CONNECTED-PATH-SMOKE",
        "status": "PASS" if result != "FAIL" else "FAIL",
        "result": result,
        "strong_paths_available": strong,
        "medium_paths_available": medium,
        "paths_emitted": len(path_df),
        "sample_paths": frame_to_records(path_df, 5),
    }
    examples = {
        "status": smoke["status"],
        "result": result,
        "max_paths": max_paths,
        "paths_emitted": len(path_df),
        "examples": frame_to_records(path_df, 25),
    }
    return path_df, smoke, examples


def preconditions(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5b_dir: Path, pld_entities: pd.DataFrame, target_uprns: list[str], lids_report: dict[str, Any]) -> dict[str, Any]:
    d4_harness = lon_d4_dir / "LON_D4_HARNESS_REPORT.json"
    d5_harness = lon_d5_dir / "LON_D5_HARNESS_REPORT.json"
    d5b_harness = lon_d5b_dir / "LON_D5B_HARNESS_REPORT.json"
    checks = {
        "lon_d4_harness_report_exists": d4_harness.exists(),
        "lon_d4_harness_report_status_pass": read_json(d4_harness).get("status") == "PASS" if d4_harness.exists() else False,
        "lon_d5_harness_report_exists": d5_harness.exists(),
        "lon_d5_harness_report_status_pass": read_json(d5_harness).get("status") == "PASS" if d5_harness.exists() else False,
        "lon_d5b_harness_report_exists": d5b_harness.exists(),
        "lon_d5b_harness_report_status_pass": read_json(d5b_harness).get("status") == "PASS" if d5b_harness.exists() else False,
        "lon_d5_pld_entities_exist": len(pld_entities) > 0,
        "lon_d5b_target_uprn_list_exists": (lon_d5b_dir / "LON_D5B_TARGET_UPRN_LIST.json").exists(),
        "lids_rows_for_target_uprns_available": lids_report.get("target_uprns_with_any_lids_rows", 0) > 0,
        "target_pld_uprns_available": len(target_uprns) > 0,
    }
    return {"gate": "LON-D5C-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def stub_gate(uprn_stubs: pd.DataFrame, target_uprns: set[str], lids_confirmed_uprns: set[str]) -> dict[str, Any]:
    emitted = set(uprn_stubs["native_id"].astype(str)) if not uprn_stubs.empty else set()
    invalid = sorted(emitted - target_uprns)
    not_confirmed = sorted(emitted - lids_confirmed_uprns)
    missing_confirmed = sorted(lids_confirmed_uprns - emitted)
    passed = bool(emitted) and not invalid and not not_confirmed and not missing_confirmed
    return {
        "gate": "LON-D5C-UPRN-STUBS",
        "status": "PASS" if passed else "FAIL",
        "uprn_stubs_emitted": len(emitted),
        "lids_confirmed_uprns": len(lids_confirmed_uprns),
        "invalid_non_target_stubs": invalid[:20],
        "not_lids_confirmed": not_confirmed[:20],
        "missing_confirmed_stubs": missing_confirmed[:20],
    }


def id_format_gate(entities: pd.DataFrame, bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame, pld_permit_ids: set[str]) -> dict[str, Any]:
    failures = []
    for row in entities.to_dict(orient="records"):
        canonical_id = str(row["canonical_id"])
        pattern = ID_PATTERNS.get(str(row["entity_type"]))
        parts = set(canonical_id.lower().split(":"))
        if not pattern or not pattern.match(canonical_id) or bool(parts & FORBIDDEN_ID_TOKENS):
            failures.append(canonical_id)
    for permit_id in pld_permit_ids:
        parts = set(permit_id.lower().split(":"))
        if not ID_PATTERNS["permit"].match(permit_id) or bool(parts & FORBIDDEN_ID_TOKENS):
            failures.append(permit_id)
    for df in [bridge_edges, pld_edges]:
        for row in df.to_dict(orient="records"):
            for endpoint in [str(row.get("src")), str(row.get("dst"))]:
                parts = endpoint.lower().split(":")
                if any(token in parts for token in FORBIDDEN_ID_TOKENS):
                    failures.append(endpoint)
    return {"gate": "LON-D5C-ID-FORMAT", "status": "PASS" if not failures else "FAIL", "ids_checked": len(entities) + len(pld_permit_ids), "failures": failures[:20]}


def edge_integrity(bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame, registry: set[str], pld_permit_ids: set[str]) -> dict[str, Any]:
    failures = []
    for row in bridge_edges.to_dict(orient="records"):
        if row["src"] not in registry:
            failures.append(f"{row['edge_id']} missing src {row['src']}")
        if row["dst"] not in registry:
            failures.append(f"{row['edge_id']} missing dst {row['dst']}")
    for row in pld_edges.to_dict(orient="records"):
        if row["src"] not in registry:
            failures.append(f"{row['edge_id']} missing src {row['src']}")
        if row["dst"] not in pld_permit_ids:
            failures.append(f"{row['edge_id']} missing permit dst {row['dst']}")
    return {
        "gate": "LON-D5C-CONTEXT-EDGES",
        "status": "PASS" if not failures and len(bridge_edges) > 0 else "FAIL",
        "bridge_edges_checked": len(bridge_edges),
        "pld_edges_checked": len(pld_edges),
        "dangling_references": len(failures),
        "details": failures[:20],
    }


def geometry_honesty(entities: pd.DataFrame) -> dict[str, Any]:
    allowed = {
        "parcel": "missing_geometry_lids_identity_stub",
        "building": "toid_identity_only_no_polygon",
        "road_segment": "usrn_identity_only_no_geometry",
    }
    failures = []
    for row in entities.to_dict(orient="records"):
        expected = allowed.get(row["entity_type"])
        if row.get("geometry_status") != expected:
            failures.append(f"{row['canonical_id']} bad geometry_status={row.get('geometry_status')}")
        geometry = row.get("geometry")
        if geometry is not None and not (isinstance(geometry, float) and pd.isna(geometry)):
            parsed = parse_json_col(geometry)
            if parsed not in (None, {}):
                failures.append(f"{row['canonical_id']} invented geometry payload")
    return {
        "gate": "LON-D5C-GEOMETRY-HONESTY",
        "status": "PASS" if not failures else "FAIL",
        "allowed_missing_geometry_statuses": sorted(set(allowed.values())),
        "entities_checked": len(entities),
        "failures": failures[:20],
    }


def compatibility_harness(entities: pd.DataFrame, bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame, registry: set[str], pld_permit_ids: set[str]) -> dict[str, Any]:
    entity_records = entities.to_dict(orient="records")
    edge_records = bridge_edges.to_dict(orient="records") + pld_edges.to_dict(orient="records")
    gates = []

    def add(gate_id: str, passed: bool, checked: int, failed: int, details: list[str] | None = None) -> None:
        gates.append({"gate_id": gate_id, "status": "PASS" if passed else "FAIL", "checked": checked, "failed": failed, "details": details or []})

    schema_failures = []
    required_entity_cols = {"canonical_id", "entity_type", "id_system", "native_id", "city", "country", "geometry_status", "confidence", "provenance", "source_reason"}
    for idx, row in enumerate(entity_records):
        missing = sorted(required_entity_cols - set(row))
        if missing:
            schema_failures.append(f"entity[{idx}] missing {missing}")
        if row.get("entity_type") not in {"parcel", "building", "road_segment"}:
            schema_failures.append(f"entity[{idx}] unsupported entity_type {row.get('entity_type')}")
        try:
            parse_json_col(row.get("confidence"))
            parse_json_col(row.get("provenance"))
        except Exception as exc:
            schema_failures.append(f"entity[{idx}] JSON parse failed: {exc}")
    for idx, row in enumerate(edge_records):
        for field in ("edge_id", "src", "dst", "relation", "confidence", "provenance"):
            if field not in row:
                schema_failures.append(f"edge[{idx}] missing {field}")
        if row.get("relation") not in {"subject_of_permit", "has_building", "on_street"}:
            schema_failures.append(f"edge[{idx}] unsupported relation {row.get('relation')}")
    add("G-SCHEMA", not schema_failures, len(entity_records) + len(edge_records), len(schema_failures), schema_failures[:10])

    id_failures = []
    for row in entity_records:
        pattern = ID_PATTERNS.get(row["entity_type"])
        canonical_id = str(row["canonical_id"])
        if not pattern or not pattern.match(canonical_id):
            id_failures.append(canonical_id)
    add("G-ID", not id_failures, len(entity_records), len(id_failures), id_failures[:10])

    triad_failures = []
    for row in entity_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance_value:
            triad_failures.append(str(row.get("canonical_id")))
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not confidence or not confidence.get("method") or confidence.get("score") is None or not provenance_value:
            triad_failures.append(str(row.get("edge_id")))
    add("G-TRIAD", not triad_failures, len(entity_records) + len(edge_records), len(triad_failures), triad_failures[:10])

    geo = geometry_honesty(entities)
    add("G-GEO", geo["status"] == "PASS", geo["entities_checked"], len(geo["failures"]), geo["failures"][:10])

    ref_failures = []
    for row in bridge_edges.to_dict(orient="records"):
        if row["src"] not in registry:
            ref_failures.append(f"{row['edge_id']} missing src {row['src']}")
        if row["dst"] not in registry:
            ref_failures.append(f"{row['edge_id']} missing dst {row['dst']}")
    for row in pld_edges.to_dict(orient="records"):
        if row["src"] not in registry:
            ref_failures.append(f"{row['edge_id']} missing src {row['src']}")
        if row["dst"] not in pld_permit_ids:
            ref_failures.append(f"{row['edge_id']} missing PLD dst {row['dst']}")
    add("G-REF", not ref_failures, len(edge_records) * 2, len(ref_failures), ref_failures[:10])

    edge_failures = []
    for row in edge_records:
        confidence = parse_json_col(row.get("confidence"))
        if not confidence or float(confidence.get("score", 0)) <= 0:
            edge_failures.append(str(row.get("edge_id")))
        if row.get("relation") == "subject_of_permit" and row.get("role") != "planning_application_subject":
            edge_failures.append(str(row.get("edge_id")))
    add("G-EDGE", not edge_failures, len(edge_records), len(edge_failures), edge_failures[:10])

    return {
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "compatibility_marker": "a2_binary_unavailable_compatibility_harness_used",
        "reason": "The local A2 binary is the NYC Flow-2 acceptance harness; LON-D5c uses the same invariant names over London LIDS-confirmed stubs and PLD bridge edges without claiming exact NYC binary acceptance.",
        "gates": gates,
    }


def drift_test(entities: pd.DataFrame, bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame, registry: set[str], pld_permit_ids: set[str]) -> dict[str, Any]:
    mutated_entities = entities.copy()
    mutated_bridge = bridge_edges.copy()
    mutated_pld = pld_edges.copy()
    if not mutated_entities.empty:
        idx = mutated_entities.index[0]
        native = str(mutated_entities.loc[idx, "native_id"])
        mutated_entities.loc[idx, "entity_type"] = "uprn_entity"
        mutated_entities.loc[idx, "canonical_id"] = f"uprn_entity:uk-london:uprn:{native}"
    if not mutated_pld.empty:
        mutated_pld.loc[mutated_pld.index[0], "relation"] = "subject_of_planning_application"
    if not mutated_bridge.empty:
        idx = mutated_bridge.index[0]
        relation = mutated_bridge.loc[idx, "relation"]
        mutated_bridge.loc[idx, "relation"] = "linked_to_toid" if relation == "has_building" else "linked_to_usrn"
    result = compatibility_harness(mutated_entities, mutated_bridge, mutated_pld, registry, pld_permit_ids)
    failing_gates = [gate["gate_id"] for gate in result["gates"] if gate["status"] == "FAIL"]
    return {
        "gate": "LON-D5C-DRIFT",
        "status": "PASS" if result["status"] == "FAIL" and failing_gates else "FAIL",
        "drift_mutation": {
            "parcel:uk-london:uprn:{id}": "uprn_entity:uk-london:uprn:{id}",
            "subject_of_permit": "subject_of_planning_application",
            "has_building": "linked_to_toid",
            "on_street": "linked_to_usrn",
        },
        "mutated_harness_status": result["status"],
        "failing_gates": failing_gates,
    }


def confidence_summary(entities: pd.DataFrame, bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame) -> dict[str, Any]:
    methods: Counter[str] = Counter()
    scores: dict[str, list[float]] = defaultdict(list)
    for df in [entities, bridge_edges, pld_edges]:
        if df.empty or "confidence" not in df:
            continue
        for value in df["confidence"]:
            confidence = parse_json_col(value)
            if not isinstance(confidence, dict):
                continue
            method = str(confidence.get("method"))
            methods[method] += 1
            if confidence.get("score") is not None:
                scores[method].append(float(confidence["score"]))
    return {
        "status": "PASS",
        "policy": {
            "LIDS-confirmed UPRN stub": 0.95,
            "PLD->UPRN exact join to LIDS-confirmed stub": 0.90,
            "UPRN->TOID from official LIDS exact link": 0.95,
            "UPRN->USRN from official LIDS exact link": 0.95,
            "TOID/USRN identity stubs from official LIDS refs": 0.95,
            "No geometry confidence when geometry is missing": True,
        },
        "method_counts": dict(methods),
        "score_ranges": {method: {"min": min(values), "max": max(values)} for method, values in scores.items() if values},
    }


def out_of_scope_report(entities: pd.DataFrame, bridge_edges: pd.DataFrame, pld_edges: pd.DataFrame, paths: pd.DataFrame) -> dict[str, Any]:
    payload = "\n".join(
        [
            entities.to_json(orient="records"),
            bridge_edges.to_json(orient="records"),
            pld_edges.to_json(orient="records"),
            paths.to_json(orient="records"),
        ]
    ).lower()
    found = sorted(token for token in OUT_OF_SCOPE_TOKENS if token in payload)
    return {
        "gate": "LON-D5C-OUT-OF-SCOPE",
        "status": "PASS" if not found else "FAIL",
        "found_forbidden_payload_terms": found,
        "exception": "Forbidden wording may appear in no-overclaim reports and docs, but not as canonical entities.",
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    required_files = {
        "README.md": output_dir / "README.md",
        "LON_D5C_MANIFEST.json": output_dir / "LON_D5C_MANIFEST.json",
        "LON_D5C_HARNESS_REPORT.json": output_dir / "LON_D5C_HARNESS_REPORT.json",
        "LON_D5C_ADAPTER_HANDOVER.md": output_dir / "LON_D5C_ADAPTER_HANDOVER.md",
    }
    files = {}
    passed = True
    for name, path in required_files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in BOUNDARY_STRINGS if item not in text]
        files[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {"gate": "LON-D5C-NO-OVERCLAIM", "status": "PASS" if passed else "FAIL", "boundary_strings": BOUNDARY_STRINGS, "files": files}


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D5C-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_docs(
    output_dir: Path,
    counts: dict[str, Any],
    lids_report: dict[str, Any],
    join_report: dict[str, Any],
    smoke: dict[str, Any],
    geometry_report: dict[str, Any],
    a2_report: dict[str, Any],
) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    readme = f"""# LON-D5c LIDS-Confirmed PLD Identity Bridge

{boundary}

LON-D5c creates a bounded connected planning identity bridge from PLD applications to UPRN identity stubs that are confirmed by official OS Open Linked Identifiers rows. It intentionally does not claim OpenUPRN geometry for those UPRNs.

## Result

- Target PLD UPRNs: {counts['target_pld_uprns']}
- LIDS-confirmed UPRNs: {counts['lids_confirmed_uprns']}
- TOID context rows: {lids_report['toid_rows_found']}
- USRN context rows: {lids_report['usrn_rows_found']}
- UPRN stubs emitted: {counts['uprn_stubs']}
- PLD to UPRN edges emitted: {counts['pld_uprn_edges']}
- UPRN to TOID edges emitted: {counts['uprn_toid_edges']}
- UPRN to USRN edges emitted: {counts['uprn_usrn_edges']}
- Connected path smoke: {smoke['result']}

## Geometry Honesty

All D5c-created identity stubs use explicit missing-geometry statuses. UPRN stubs use `missing_geometry_lids_identity_stub`; TOID stubs use `toid_identity_only_no_polygon`; USRN stubs use `usrn_identity_only_no_geometry`.

## Compatibility

A2-style invariant gates ran with marker `{a2_report.get('compatibility_marker')}`.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    handover = f"""# LON-D5c Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d5c_lids_confirmed_identity_bridge.py`

```bash
python txr_citybrain_lon_d5c_lids_confirmed_identity_bridge.py --lon-d4-dir outputs/lon_d4_identity_backbone_ingest --lon-d5-dir outputs/lon_d5_pld_planning_ingest --lon-d5b-dir outputs/lon_d5b_pld_uprn_backfill --os-sample-dir LON_D2_identity_backbone_sample_fixture_v0_1/lon_d2_identity_backbone_fixture/lon_d3_os_identity_samples --output-dir outputs/lon_d5c_lids_confirmed_identity_bridge --run-gates
```

## Evidence

- Target UPRNs total: {counts['target_pld_uprns']}
- LIDS-confirmed UPRN stubs: {counts['lids_confirmed_uprns']}
- TOID rows found: {lids_report['toid_rows_found']}
- USRN rows found: {lids_report['usrn_rows_found']}
- PLD to UPRN rejoin edges: {join_report['pld_to_uprn_edges_emitted']}
- Records still unattached: {join_report['records_still_unattached']}
- Connected path smoke: {smoke['result']}

## Confidence Policy

- LIDS-confirmed UPRN stub: 0.95
- PLD to UPRN exact join to LIDS-confirmed stub: 0.90
- UPRN to TOID from official LIDS exact link: 0.95
- UPRN to USRN from official LIDS exact link: 0.95
- TOID/USRN identity stubs from official LIDS refs: 0.95
- No geometry confidence when geometry is missing.
"""
    (output_dir / "LON_D5C_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_identity_stub_policy(output_dir: Path) -> dict[str, Any]:
    policy = {
        "task": TASK_NAME,
        "boundary_strings": BOUNDARY_STRINGS,
        "uprn_stub_policy": {
            "canonical_id": "parcel:uk-london:uprn:{uprn}",
            "entity_type": "parcel",
            "id_system": "uprn",
            "geometry_status": "missing_geometry_lids_identity_stub",
            "source_reason": "pld_target_uprn_confirmed_in_lids",
            "confidence_method": "official_lids_uprn_reference",
            "confidence_score": 0.95,
            "does_not_claim": ["OpenUPRN geometry", "true land parcel aggregation", "BBL/BIN/DOB semantics"],
        },
        "context_stub_policy": {
            "building": "building:uk-london:toid:{toid}; toid_identity_only_no_polygon",
            "road_segment": "road_segment:uk-london:usrn:{usrn}; usrn_identity_only_no_geometry",
        },
    }
    write_json(output_dir / "LON_D5C_IDENTITY_STUB_POLICY.json", policy)
    return policy


def write_manifest(output_dir: Path, lon_d4_dir: Path, lon_d5_dir: Path, lon_d5b_dir: Path, os_sample_dir: Path, counts: dict[str, Any], status: str) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "lon_d5b_dir": str(lon_d5b_dir),
        "os_sample_dir": str(os_sample_dir),
        "output_dir": str(output_dir),
        "boundary_strings": BOUNDARY_STRINGS,
        "scope": "sampled LIDS-confirmed identity-bridge repair only",
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D5C_MANIFEST.json",
            "LON_D5C_HARNESS_REPORT.json",
            "LON_D5C_INPUT_INVENTORY.json",
            "LON_D5C_LIDS_TARGET_ROWS_REPORT.json",
            "LON_D5C_IDENTITY_STUB_POLICY.json",
            "LON_D5C_JOIN_REPORT.json",
            "LON_D5C_CONNECTED_PATH_SMOKE.json",
            "LON_D5C_NO_OVERCLAIM_REPORT.json",
            "LON_D5C_DRIFT_TEST_REPORT.json",
            "LON_D5C_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
            "canonical/london_lids_confirmed_uprn_stubs.parquet",
            "canonical/london_lids_context_entity_stubs.parquet",
            "canonical/london_lids_bridge_edges.parquet",
            "canonical/london_pld_rejoined_lids_edges.parquet",
            "canonical/london_lids_connected_paths.parquet",
            "canonical/london_lids_bridge_entities_sample.json",
            "canonical/london_lids_bridge_edges_sample.json",
            "reports/target_lids_row_counts.json",
            "reports/identity_stub_counts.json",
            "reports/pld_rejoin_rates.json",
            "reports/toid_context_coverage.json",
            "reports/usrn_context_coverage.json",
            "reports/connected_path_examples.json",
            "reports/confidence_summary.json",
            "reports/geometry_limitations.json",
        ],
    }
    write_json(output_dir / "LON_D5C_MANIFEST.json", manifest)
    return manifest


def run_lon_d5c_gate(
    lon_d4_dir: str,
    lon_d5_dir: str,
    lon_d5b_dir: str,
    os_sample_dir: str,
    output_dir: str,
    max_paths: int = 100,
) -> dict:
    lon_d4_path = Path(lon_d4_dir)
    lon_d5_path = Path(lon_d5_dir)
    lon_d5b_path = Path(lon_d5b_dir)
    os_sample_path = Path(os_sample_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(lon_d4_path, lon_d5_path, lon_d5b_path, os_sample_path)
    before_hashes = input_hashes(tracked_inputs)

    d4_buildings = pd.read_parquet(lon_d4_path / "canonical" / "london_buildings_toid.parquet")
    d4_roads = pd.read_parquet(lon_d4_path / "canonical" / "london_road_segments_usrn.parquet")
    pld_entities = pd.read_parquet(lon_d5_path / "canonical" / "london_planning_applications.parquet")
    target_uprns = load_target_uprns(lon_d5b_path, pld_entities)
    target_set = set(target_uprns)
    toid_rows, usrn_rows, lids_report = scan_lids_rows(os_sample_path, target_set)
    precond_report = preconditions(lon_d4_path, lon_d5_path, lon_d5b_path, pld_entities, target_uprns, lids_report)

    all_lids_rows = toid_rows + usrn_rows
    confirmed_uprns = {row["uprn"] for row in all_lids_rows}
    uprn_stubs = make_uprn_stubs(all_lids_rows)
    d4_building_ids = set(d4_buildings["canonical_id"].astype(str))
    d4_road_ids = set(d4_roads["canonical_id"].astype(str))
    context_stubs = make_context_stubs(toid_rows, usrn_rows, d4_building_ids, d4_road_ids)
    generated_entities = pd.concat([uprn_stubs, context_stubs], ignore_index=True) if not context_stubs.empty else uprn_stubs.copy()
    bridge_edges = make_bridge_edges(toid_rows, usrn_rows)
    pld_edges, join_report = make_pld_rejoin_edges(pld_entities, confirmed_uprns)
    paths, smoke, path_examples = make_connected_paths(pld_edges, bridge_edges, max_paths)

    registry = set(generated_entities["canonical_id"].astype(str)) | d4_building_ids | d4_road_ids
    pld_permit_ids = set(pld_entities["canonical_id"].astype(str))
    stub_report = stub_gate(uprn_stubs, target_set, confirmed_uprns)
    id_report = id_format_gate(generated_entities, bridge_edges, pld_edges, pld_permit_ids)
    edge_report = edge_integrity(bridge_edges, pld_edges, registry, pld_permit_ids)
    geometry_report = geometry_honesty(generated_entities)
    a2_report = compatibility_harness(generated_entities, bridge_edges, pld_edges, registry, pld_permit_ids)
    drift = drift_test(generated_entities, bridge_edges, pld_edges, registry, pld_permit_ids)
    confidence = confidence_summary(generated_entities, bridge_edges, pld_edges)
    out_scope = out_of_scope_report(generated_entities, bridge_edges, pld_edges, paths)

    toid_context = {
        "status": "PASS" if len(toid_rows) > 0 else "NO_TOID_ROWS",
        "target_uprns_total": len(target_uprns),
        "target_uprns_with_toid_rows": lids_report["target_uprns_with_toid_rows"],
        "toid_rows_found": lids_report["toid_rows_found"],
        "uprn_toid_edges_emitted": int((bridge_edges["relation"] == "has_building").sum()) if not bridge_edges.empty else 0,
        "coverage_over_target_uprns": lids_report["target_uprns_with_toid_rows"] / len(target_uprns) if target_uprns else 0.0,
    }
    usrn_context = {
        "status": "PASS" if len(usrn_rows) > 0 else "NO_USRN_ROWS",
        "target_uprns_total": len(target_uprns),
        "target_uprns_with_usrn_rows": lids_report["target_uprns_with_usrn_rows"],
        "usrn_rows_found": lids_report["usrn_rows_found"],
        "uprn_usrn_edges_emitted": int((bridge_edges["relation"] == "on_street").sum()) if not bridge_edges.empty else 0,
        "coverage_over_target_uprns": lids_report["target_uprns_with_usrn_rows"] / len(target_uprns) if target_uprns else 0.0,
    }
    stub_counts = {
        "status": stub_report["status"],
        "uprn_stubs": len(uprn_stubs),
        "context_entity_stubs": len(context_stubs),
        "toid_context_stubs": int((context_stubs["entity_type"] == "building").sum()) if not context_stubs.empty else 0,
        "usrn_context_stubs": int((context_stubs["entity_type"] == "road_segment").sum()) if not context_stubs.empty else 0,
        "existing_d4_toid_refs_used": len({edge["dst"] for edge in bridge_edges.to_dict(orient="records") if edge["relation"] == "has_building" and edge["dst"] in d4_building_ids}),
        "existing_d4_usrn_refs_used": len({edge["dst"] for edge in bridge_edges.to_dict(orient="records") if edge["relation"] == "on_street" and edge["dst"] in d4_road_ids}),
    }
    geometry_limitations = {
        "gate": "LON-D5C-GEOMETRY-HONESTY",
        "status": geometry_report["status"],
        "limitation": "Geometry is missing for LIDS-confirmed identity stubs unless separately resolved through OpenUPRN or another official geometry source.",
        "geometry_status_counts": dict(Counter(generated_entities["geometry_status"].astype(str))) if not generated_entities.empty else {},
        "invented_geometry_failures": geometry_report["failures"],
    }

    write_parquet(output_path / "canonical" / "london_lids_confirmed_uprn_stubs.parquet", uprn_stubs)
    write_parquet(output_path / "canonical" / "london_lids_context_entity_stubs.parquet", context_stubs)
    write_parquet(output_path / "canonical" / "london_lids_bridge_edges.parquet", bridge_edges)
    write_parquet(output_path / "canonical" / "london_pld_rejoined_lids_edges.parquet", pld_edges)
    write_parquet(output_path / "canonical" / "london_lids_connected_paths.parquet", paths)
    write_json(output_path / "canonical" / "london_lids_bridge_entities_sample.json", {"uprn_stubs": frame_to_records(uprn_stubs), "context_stubs": frame_to_records(context_stubs)})
    write_json(output_path / "canonical" / "london_lids_bridge_edges_sample.json", {"pld_edges": frame_to_records(pld_edges), "bridge_edges": frame_to_records(bridge_edges)})
    write_json(output_path / "LON_D5C_LIDS_TARGET_ROWS_REPORT.json", lids_report)
    write_identity_stub_policy(output_path)
    write_json(output_path / "LON_D5C_JOIN_REPORT.json", join_report)
    write_json(output_path / "LON_D5C_CONNECTED_PATH_SMOKE.json", smoke)
    write_json(output_path / "LON_D5C_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "LON_D5C_INPUT_INVENTORY.json", inventory_inputs(lon_d4_path, lon_d5_path, lon_d5b_path, os_sample_path, tracked_inputs))
    write_json(output_path / "reports" / "target_lids_row_counts.json", lids_report)
    write_json(output_path / "reports" / "identity_stub_counts.json", stub_counts)
    write_json(output_path / "reports" / "pld_rejoin_rates.json", join_report)
    write_json(output_path / "reports" / "toid_context_coverage.json", toid_context)
    write_json(output_path / "reports" / "usrn_context_coverage.json", usrn_context)
    write_json(output_path / "reports" / "connected_path_examples.json", path_examples)
    write_json(output_path / "reports" / "confidence_summary.json", confidence)
    write_json(output_path / "reports" / "geometry_limitations.json", geometry_limitations)

    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D5C-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }
    counts = {
        "target_pld_uprns": len(target_uprns),
        "lids_confirmed_uprns": len(confirmed_uprns),
        "toid_context_rows": lids_report["toid_rows_found"],
        "usrn_context_rows": lids_report["usrn_rows_found"],
        "uprn_stubs": len(uprn_stubs),
        "context_entity_stubs": len(context_stubs),
        "pld_uprn_edges": len(pld_edges),
        "uprn_toid_edges": toid_context["uprn_toid_edges_emitted"],
        "uprn_usrn_edges": usrn_context["uprn_usrn_edges_emitted"],
        "connected_paths_emitted": len(paths),
    }
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5b_path, os_sample_path, counts, "PENDING")
    preliminary = {
        "task": TASK_NAME,
        "status": "PENDING",
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "preconditions": precond_report,
        "lids_target_rows": lids_report,
        "connected_path_smoke": smoke,
    }
    write_json(output_path / "LON_D5C_HARNESS_REPORT.json", preliminary)
    write_docs(output_path, counts, lids_report, join_report, smoke, geometry_report, a2_report)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5C_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = {
        "LON-D5C-PRECOND": precond_report["status"],
        "LON-D5C-LIDS-TARGET-ROWS": lids_report["status"],
        "LON-D5C-UPRN-STUBS": stub_report["status"],
        "LON-D5C-ID-FORMAT": id_report["status"],
        "LON-D5C-PLD-REJOIN": join_report["status"],
        "LON-D5C-CONTEXT-EDGES": edge_report["status"],
        "LON-D5C-CONNECTED-PATH-SMOKE": smoke["status"],
        "LON-D5C-GEOMETRY-HONESTY": geometry_report["status"],
        "LON-D5C-A2-COMPATIBILITY": a2_report["status"],
        "LON-D5C-DRIFT": drift["status"],
        "LON-D5C-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D5C-OUT-OF-SCOPE": out_scope["status"],
        "LON-D5C-NO-MUTATION": no_mutation["status"],
        "LON-D5C-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "lon_d4_dir": str(lon_d4_path),
        "lon_d5_dir": str(lon_d5_path),
        "lon_d5b_dir": str(lon_d5b_path),
        "os_sample_dir": str(os_sample_path),
        "output_dir": str(output_path),
        "counts": counts,
        "preconditions": precond_report,
        "lids_target_rows": lids_report,
        "identity_stubs": stub_report,
        "identity_stub_counts": stub_counts,
        "id_format": id_report,
        "pld_rejoin": join_report,
        "context_edges": edge_report,
        "toid_context": toid_context,
        "usrn_context": usrn_context,
        "connected_path_smoke": smoke,
        "geometry_honesty": geometry_report,
        "geometry_limitations": geometry_limitations,
        "confidence_summary": confidence,
        "a2_compatibility": a2_report,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
        "hashes": {"gate": "LON-D5C-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D5C_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5b_path, os_sample_path, counts, overall)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D5C_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D5C-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D5C_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5b_path, os_sample_path, counts, harness["status"])
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5b-dir", default=DEFAULT_LON_D5B_DIR)
    parser.add_argument("--os-sample-dir", default=DEFAULT_OS_SAMPLE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-paths", type=int, default=100)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d5c_gate(args.lon_d4_dir, args.lon_d5_dir, args.lon_d5b_dir, args.os_sample_dir, args.output_dir, args.max_paths)
    counts = report["counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input LON-D5b: {report['preconditions']['checks']['lon_d5b_harness_report_status_pass'] and 'PASS' or 'FAIL'}")
    print(f"Target PLD UPRNs: {counts['target_pld_uprns']}")
    print(f"LIDS-confirmed UPRNs: {counts['lids_confirmed_uprns']}")
    print(f"TOID context rows: {counts['toid_context_rows']}")
    print(f"USRN context rows: {counts['usrn_context_rows']}")
    print(f"UPRN stubs emitted: {counts['uprn_stubs']}")
    print(f"PLD->UPRN edges emitted: {counts['pld_uprn_edges']}")
    print(f"UPRN->TOID edges emitted: {counts['uprn_toid_edges']}")
    print(f"UPRN->USRN edges emitted: {counts['uprn_usrn_edges']}")
    print(f"Connected path smoke: {report['connected_path_smoke']['result']}")
    print(f"A2 compatibility gates: {report['a2_compatibility']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
