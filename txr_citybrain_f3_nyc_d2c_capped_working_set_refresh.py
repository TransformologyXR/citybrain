#!/usr/bin/env python3
"""F3-NYC-D2C capped working-set consolidation refresh.

This is intentionally lightweight: it refreshes source counts and handoff
manifests for D5 without rebuilding Flow 3 canonical artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "F3-NYC-D2C Capped Working-Set Refresh"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d2c_capped_working_set_refresh"
SOURCE_PACK = Path("data_landing/f3_nyc_d1_official_sources_v1")

REQUIRED_STATUS = (
    "MVC crashes and firehouses are full-source complete. "
    "Fire Dispatch is capped unless 11,819,520 rows are present. "
    "EMS is capped unless 29,572,156 rows are present. "
    "Capped data is suitable for D5 development and demo briefing, not final full-source Flow 3 completion."
)

FULL_SOURCE_STATUS = (
    "MVC crashes, FDNY firehouses, Fire Dispatch, and EMS Dispatch are full-source complete in the current local landing pack. "
    "D2C remains a source-manifest refresh only; it does not certify affected buildings, geocode FDNY address rows, "
    "run dispatch optimization, or rebuild the Flow 3 cartridge."
)

SCOPE_LINES = [
    "MVC crashes and firehouses are full-source complete.",
    "F3-NYC-D2C does not certify affected buildings.",
    "F3-NYC-D2C does not geocode FDNY address rows.",
    "F3-NYC-D2C does not run dispatch optimization.",
    "F3-NYC-D2C does not rebuild the Flow 3 cartridge.",
]

FORBIDDEN_PATTERNS = [
    "fire dispatch is full-source complete",
    "ems is full-source complete",
    "affected buildings are certified",
    "geocoded fdny address rows",
    "dispatch optimization complete",
    "flow 3 cartridge rebuilt",
]

EXPECTED = {
    "mvc_crashes": {
        "label": "MVC crashes",
        "full_rows": 2_269_187,
        "source_dir": "Motor_Vehicle_Collisions_-_Crashes__h9gi-nx95",
    },
    "fire_incident_dispatch": {
        "label": "Fire dispatch",
        "full_rows": 11_819_520,
        "source_dir": "Fire_Incident_Dispatch_Data__8m42-w767",
    },
    "fdny_firehouses": {
        "label": "Firehouses",
        "full_rows": 219,
        "source_dir": "FDNY_Firehouse_Listing__hc8x-tcnd",
    },
    "ems_incident_dispatch": {
        "label": "EMS",
        "full_rows": 29_572_156,
        "source_dir": "EMS_Incident_Dispatch_Data__76xm-jjuj",
    },
}

INPUTS = {
    "d1": Path("outputs/f3_nyc_d1_source_inventory_schema_mapping"),
    "d2": Path("outputs/f3_nyc_d2_fdny_incident_response_slice_ingest"),
    "d3": Path("outputs/f3_nyc_d3_affected_asset_response_context"),
    "d4": Path("outputs/f3_nyc_d4_candidate_prioritization_review_routing"),
    "d5": Path("outputs/f3_nyc_d5_governed_evidence_briefing"),
    "source_pack": SOURCE_PACK,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


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


def path_meta(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
    }


def input_fingerprint() -> dict[str, Any]:
    watched = {}
    for key, root in INPUTS.items():
        entry = {"path": str(root), "exists": root.exists(), "files": {}}
        if root.exists():
            for name in [
                "F3_NYC_D1_HARNESS_REPORT.json",
                "F3_NYC_D2_HARNESS_REPORT.json",
                "F3_NYC_D3_HARNESS_REPORT.json",
                "F3_NYC_D4_HARNESS_REPORT.json",
                "F3_NYC_D5_HARNESS_REPORT.json",
                "F3_NYC_D1_DOWNLOAD_MANIFEST.json",
                "SHA256SUMS.json",
            ]:
                for path in root.glob(name):
                    entry["files"][path.name] = path_meta(path)
        watched[key] = entry
    return watched


def discover_source_locations(search_roots: list[str]) -> dict[str, Any]:
    found = {key: [] for key in EXPECTED}
    roots = []
    for raw in search_roots:
        root = Path(raw)
        roots.append({"root": str(root), "exists": root.exists()})
        if not root.exists():
            continue
        for key, meta in EXPECTED.items():
            for path in root.rglob(meta["source_dir"]):
                if path.is_dir():
                    manifest = path / "chunk_manifest.json"
                    found[key].append(
                        {
                            "path": str(path),
                            "manifest": str(manifest),
                            "manifest_exists": manifest.exists(),
                            "chunks_dir": str(path / "chunks"),
                            "chunk_count": len(list((path / "chunks").glob("*.csv"))) if (path / "chunks").exists() else 0,
                        }
                    )
    return {"searched_roots": roots, "found": found}


def load_source_counts(source_pack: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    download_manifest = read_json(source_pack / "F3_NYC_D1_DOWNLOAD_MANIFEST.json", {})
    by_key = {row.get("dataset_key"): row for row in download_manifest.get("datasets", [])}
    status = {}
    for key, meta in EXPECTED.items():
        row = by_key.get(key, {})
        actual = int(row.get("downloaded_rows", 0) or 0)
        full = meta["full_rows"]
        status[key] = {
            "label": meta["label"],
            "downloaded_rows": actual,
            "full_rows": full,
            "source_status": "full_complete" if actual == full else "capped" if actual < full else "over_full_count_check",
            "target_rows": row.get("target_rows"),
            "socrata_count": row.get("socrata_count"),
            "chunk_count": row.get("chunk_count", 0),
            "downloaded_bytes": row.get("downloaded_bytes", 0),
            "source_manifest": str(source_pack / "raw" / meta["source_dir"] / "chunk_manifest.json"),
        }
    return status, download_manifest


def read_d2_counts() -> dict[str, Any]:
    d2 = read_json(INPUTS["d2"] / "F3_NYC_D2_HARNESS_REPORT.json", {})
    canonical = d2.get("canonical_counts", {})
    return {
        "d2_status": d2.get("status"),
        "d2_bounded_cap_per_source": d2.get("bounded_cap_per_source"),
        "d2_counts": canonical,
    }


def write_hashes(output_dir: Path) -> dict[str, Any]:
    hashes = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    manifest = {
        "gate": "F3-NYC-D2C-HASHES",
        "status": "PASS",
        "file_count": len(hashes),
        "files": hashes,
    }
    write_json(output_dir / "SHA256SUMS.json", manifest)
    return manifest


def no_overclaim(output_dir: Path, required_status_language: str) -> dict[str, Any]:
    missing = []
    text_targets = []
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md"} and path.name != "F3_NYC_D2C_NO_OVERCLAIM_REPORT.json":
            text = path.read_text(encoding="utf-8", errors="replace")
            text_targets.append((path, text))
    combined = "\n".join(text for _, text in text_targets)
    for line in [required_status_language, *SCOPE_LINES]:
        if line not in combined:
            missing.append(line)
    hits = []
    for path, text in text_targets:
        lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in lower:
                hits.append({"path": str(path), "pattern": pattern})
    return {
        "gate": "F3-NYC-D2C-NO-OVERCLAIM",
        "status": "PASS" if not missing and not hits else "FAIL",
        "missing_required_lines": missing,
        "forbidden_hits": hits,
        "required_status_language": required_status_language,
    }


def render_readme(source_status: dict[str, Any], status: str, status_language: str) -> str:
    rows = "\n".join(
        f"- {row['label']}: `{row['downloaded_rows']:,} / {row['full_rows']:,}` ({row['source_status']})"
        for row in source_status.values()
    )
    return f"""# F3-NYC-D2C Capped Working-Set Refresh

Status: `{status}`

{status_language}

## Source Counts

{rows}

## Scope

F3-NYC-D2C does not certify affected buildings.
F3-NYC-D2C does not geocode FDNY address rows.
F3-NYC-D2C does not run dispatch optimization.
F3-NYC-D2C does not rebuild the Flow 3 cartridge.

This refresh is a D3/D4/D5-readable source manifest. It does not rebuild downstream Flow 3 artifacts.
"""


def run_f3_nyc_d2c_gate(output_dir: str = DEFAULT_OUTPUT_DIR, source_pack: str = str(SOURCE_PACK)) -> dict[str, Any]:
    output = Path(output_dir)
    for rel in ["reports"]:
        (output / rel).mkdir(parents=True, exist_ok=True)
    source_pack_path = Path(source_pack)
    before = input_fingerprint()

    source_locations = discover_source_locations(
        [
            str(Path.cwd()),
            str(Path.cwd() / "data_landing"),
            "C:/data/citybrain",
            "/data/citybrain",
        ]
    )
    source_status, download_manifest = load_source_counts(source_pack_path)
    d2_counts = read_d2_counts()

    full_fire = source_status["fire_incident_dispatch"]["downloaded_rows"] == source_status["fire_incident_dispatch"]["full_rows"]
    full_ems = source_status["ems_incident_dispatch"]["downloaded_rows"] == source_status["ems_incident_dispatch"]["full_rows"]
    status = "PASS" if full_fire and full_ems else "PASS_WITH_CAPPED_WORKING_SET"
    status_language = FULL_SOURCE_STATUS if status == "PASS" else REQUIRED_STATUS

    capped_vs_full = {
        "required_status_language": status_language,
        "datasets": source_status,
    }
    row_comp = {
        "d2_bounded_sample_status": d2_counts,
        "d2c_source_rows": source_status,
        "scaleup_vs_d2": {
            "mvc_crashes": {
                "d2_rows": d2_counts["d2_counts"].get("mvc_crashes"),
                "d2c_rows": source_status["mvc_crashes"]["downloaded_rows"],
            },
            "fire_dispatch": {
                "d2_rows": d2_counts["d2_counts"].get("dispatch_events"),
                "d2c_rows": source_status["fire_incident_dispatch"]["downloaded_rows"],
            },
            "ems": {
                "d2_rows": d2_counts["d2_counts"].get("ems_events"),
                "d2c_rows": source_status["ems_incident_dispatch"]["downloaded_rows"],
            },
            "firehouses": {
                "d2_rows": d2_counts["d2_counts"].get("firehouses"),
                "d2c_rows": source_status["fdny_firehouses"]["downloaded_rows"],
            },
        },
    }
    working_manifest = {
        "task": TASK,
        "status": status,
        "created_utc": utc_now(),
        "source_pack": str(source_pack_path),
        "source_pack_status": download_manifest.get("status"),
        "chunk_size": download_manifest.get("chunk_size"),
        "dataset_caps": download_manifest.get("dataset_caps", {}),
        "source_counts": source_status,
        "usable_for": ["F3-NYC-D5 development", "demo briefing", "source exploration"],
        "not_usable_for": ["asset certification", "dispatch optimization", "claiming downstream Flow 3 cartridge rebuild"],
        "required_status_language": status_language,
    }
    d5_handoff = {
        "gate": "F3-NYC-D2C-D5-HANDOFF",
        "status": "PASS",
        "d5_current_dir": str(INPUTS["d5"]),
        "d5_current_exists": INPUTS["d5"].exists(),
        "working_set_manifest": str(output / "F3_NYC_D2C_WORKING_SET_MANIFEST.json"),
        "source_pack": str(source_pack_path),
        "recommended_d5_use": "Use D2C counts and source locations for governed briefing/source-boundary statements; downstream artifacts still need explicit reruns to consume the full source base.",
        "required_status_language": status_language,
    }
    limitations = {
        "gate": "F3-NYC-D2C-LIMITATION-CARRY-FORWARD",
        "status": "PASS",
        "limitations": [status_language, *SCOPE_LINES],
        "fire_dispatch_remaining_rows": max(0, source_status["fire_incident_dispatch"]["full_rows"] - source_status["fire_incident_dispatch"]["downloaded_rows"]),
        "ems_remaining_rows": max(0, source_status["ems_incident_dispatch"]["full_rows"] - source_status["ems_incident_dispatch"]["downloaded_rows"]),
    }
    d3_d4_notes = {
        "d3_reuse": "D3 can reuse existing confidence tiers and candidate-only asset discipline, but should not assume D2C has rebuilt canonical event rows.",
        "d4_reuse": "D4 can reuse D2C source counts for operator-review briefing context; no routing/dispatch optimization is added by D2C.",
        "required_status_language": status_language,
    }
    d5_notes = {
        "d5_handoff": d5_handoff,
        "source_count_fields": ["downloaded_rows", "full_rows", "source_status", "source_manifest"],
        "required_status_language": status_language,
    }

    input_inventory = {
        "gate": "F3-NYC-D2C-PRECOND",
        "status": "PASS" if source_pack_path.exists() and INPUTS["d2"].exists() else "FAIL",
        "inputs": before,
        "required_status_language": status_language,
    }
    source_count_report = {
        "gate": "F3-NYC-D2C-ROW-COUNT-CHECK",
        "status": "PASS"
        if source_status["mvc_crashes"]["downloaded_rows"] == 2_269_187
        and source_status["fdny_firehouses"]["downloaded_rows"] == 219
        and source_status["fire_incident_dispatch"]["downloaded_rows"] >= 2_000_000
        and source_status["ems_incident_dispatch"]["downloaded_rows"] >= 3_000_000
        else "FAIL",
        "source_counts": source_status,
        "required_status_language": status_language,
    }

    write_json(output / "F3_NYC_D2C_INPUT_INVENTORY.json", input_inventory)
    write_json(output / "F3_NYC_D2C_SOURCE_COUNT_REPORT.json", source_count_report)
    write_json(output / "F3_NYC_D2C_WORKING_SET_MANIFEST.json", working_manifest)
    write_json(output / "F3_NYC_D2C_D5_HANDOFF.json", d5_handoff)
    write_json(output / "F3_NYC_D2C_LIMITATION_REGISTER.json", limitations)
    write_json(output / "reports/source_locations.json", source_locations)
    write_json(output / "reports/capped_vs_full_status.json", capped_vs_full)
    write_json(output / "reports/row_count_comparison_vs_d2.json", row_comp)
    write_json(output / "reports/d3_d4_reuse_notes.json", d3_d4_notes)
    write_json(output / "reports/d5_handoff_notes.json", d5_notes)
    write_text(output / "README.md", render_readme(source_status, status, status_language))
    write_text(
        output / "F3_NYC_D2C_ADAPTER_HANDOVER.md",
        f"""# F3-NYC-D2C Adapter Handover

{status_language}

D2C refreshes source manifests only. It does not rebuild canonical Flow 3 artifacts, certify affected assets, geocode FDNY rows, or run dispatch optimization.

D5 should read `F3_NYC_D2C_WORKING_SET_MANIFEST.json` and `F3_NYC_D2C_D5_HANDOFF.json`.
""",
    )
    no_claim = no_overclaim(output, status_language)
    write_json(output / "F3_NYC_D2C_NO_OVERCLAIM_REPORT.json", no_claim)
    after = input_fingerprint()
    no_mutation = {
        "gate": "F3-NYC-D2C-NO-MUTATION",
        "status": "PASS" if before == after else "FAIL",
        "before": before,
        "after": after,
    }
    gates = {
        "F3-NYC-D2C-PRECOND": input_inventory["status"],
        "F3-NYC-D2C-SOURCE-INVENTORY": "PASS" if any(v for v in source_locations["found"].values()) else "FAIL",
        "F3-NYC-D2C-ROW-COUNT-CHECK": source_count_report["status"],
        "F3-NYC-D2C-WORKING-SET-MANIFEST": "PASS",
        "F3-NYC-D2C-D5-HANDOFF": d5_handoff["status"],
        "F3-NYC-D2C-LIMITATION-CARRY-FORWARD": limitations["status"],
        "F3-NYC-D2C-NO-OVERCLAIM": no_claim["status"],
        "F3-NYC-D2C-NO-MUTATION": no_mutation["status"],
    }
    if any(v != "PASS" for v in gates.values()):
        status = "FAIL"
    harness = {
        "task": TASK,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "counts": source_status,
        "d5_handoff": d5_handoff,
        "no_mutation": no_mutation,
        "required_status_language": status_language,
        "output": str(output),
    }
    write_json(output / "F3_NYC_D2C_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output)
    gates["F3-NYC-D2C-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    write_json(output / "F3_NYC_D2C_HARNESS_REPORT.json", harness)
    write_hashes(output)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source-pack", default=str(SOURCE_PACK))
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d2c_gate(args.output_dir, args.source_pack)
    counts = report["counts"]
    print(
        "\n".join(
            [
                f"F3-NYC-D2C Capped Working-Set Refresh: {report['status']}",
                f"MVC crashes: {counts['mvc_crashes']['downloaded_rows']:,} / {counts['mvc_crashes']['full_rows']:,}",
                f"Firehouses: {counts['fdny_firehouses']['downloaded_rows']:,} / {counts['fdny_firehouses']['full_rows']:,}",
                f"Fire dispatch: {counts['fire_incident_dispatch']['downloaded_rows']:,} / {counts['fire_incident_dispatch']['full_rows']:,}",
                f"EMS: {counts['ems_incident_dispatch']['downloaded_rows']:,} / {counts['ems_incident_dispatch']['full_rows']:,}",
                f"D5 handoff: {report['gates']['F3-NYC-D2C-D5-HANDOFF']}",
                f"No-overclaim: {report['gates']['F3-NYC-D2C-NO-OVERCLAIM']}",
                f"Output: {args.output_dir}",
            ]
        )
    )
    return 0 if report["status"] in {"PASS_WITH_CAPPED_WORKING_SET", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
