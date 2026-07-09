#!/usr/bin/env python3
"""Build Data Quality / Maturity Dashboard R1 from SourceRegistry v1."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_track5_data_quality_maturity_dashboard_r1"
TRACK4_SCRIPT = ROOT / "scripts" / "run_main_citybrain_track4_source_registry_v1.py"
TRACK4_OUTPUT_ROOT = ROOT / "outputs" / "main_citybrain_track4_source_registry_v1"
SOURCE_REGISTRY_PATH = TRACK4_OUTPUT_ROOT / "SOURCE_REGISTRY_V1.json"

FINAL_STATUS = "PASS_MAIN_CITYBRAIN_TRACK5_DATA_QUALITY_MATURITY_DASHBOARD_R1_WITH_LIMITATIONS"
MAX_CHECK_BYTES = 8_000_000

SCORECARD_IDS = [
    "identity_ambiguity",
    "source_freshness",
    "coverage_gaps",
    "duplicate_conflict_risk",
    "weak_relationships",
    "candidate_only_records",
    "missing_geometry",
    "missing_time_history",
    "check_downgrade_reasons",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


def import_track4_runner():
    spec = importlib.util.spec_from_file_location("track4_source_registry", TRACK4_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def ensure_source_registry() -> dict[str, Any]:
    if not SOURCE_REGISTRY_PATH.exists():
        track4 = import_track4_runner()
        track4.build_outputs()
        errors = track4.validate_outputs()
        if errors:
            raise RuntimeError(f"SourceRegistry v1 prerequisite failed: {errors}")
    registry = read_json(SOURCE_REGISTRY_PATH)
    if not registry.get("sources"):
        raise RuntimeError("SourceRegistry v1 exists but has no sources")
    return registry


def check_candidate_files() -> list[Path]:
    files: list[Path] = []
    for root in [ROOT / "outputs", ROOT / "publications"]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            lower = path.as_posix().lower()
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            if "main_citybrain_track5_data_quality_maturity_dashboard_r1" in lower:
                continue
            if "check" in path.name.lower() and path.stat().st_size <= MAX_CHECK_BYTES:
                files.append(path)
    return files


def iter_dicts(value: Any, max_depth: int = 4) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(item: Any, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(item, dict):
            rows.append(item)
            for nested in item.values():
                if isinstance(nested, (dict, list)):
                    walk(nested, depth + 1)
        elif isinstance(item, list):
            for nested in item:
                if isinstance(nested, (dict, list)):
                    walk(nested, depth + 1)

    walk(value, 0)
    return rows


def load_check_payload(path: Path) -> Any:
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def extract_check_downgrades() -> dict[str, Any]:
    reason_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    report_refs: dict[str, list[str]] = defaultdict(list)
    scanned = 0
    parse_errors: list[str] = []
    for path in check_candidate_files():
        try:
            payload = load_check_payload(path)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
            parse_errors.append(f"{rel(path)}:{exc.__class__.__name__}")
            continue
        scanned += 1
        for row in iter_dicts(payload):
            status = row.get("claimability_status") or row.get("status")
            if isinstance(status, str) and ("downgraded" in status or "blocked" in status or status in {"WARN", "FAIL"}):
                status_counts[status] += 1
                report_refs[status].append(rel(path))
            reason = row.get("downgrade_reason") or row.get("reason") or row.get("finding_type")
            if isinstance(reason, str) and reason:
                reason_counts[reason] += 1
                report_refs[reason].append(rel(path))
            for result in row.get("rule_results", []) if isinstance(row.get("rule_results"), list) else []:
                if isinstance(result, dict):
                    result_status = result.get("status")
                    downgrade = result.get("downgrade_reason")
                    if result_status in {"WARN", "FAIL"} and downgrade:
                        reason_counts[str(downgrade)] += 1
                        report_refs[str(downgrade)].append(rel(path))
    return {
        "artifact_id": "CHECK_DOWNGRADE_REASON_INDEX",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "check_files_scanned": scanned,
        "parse_errors": parse_errors[:100],
        "claimability_status_counts": dict(sorted(status_counts.items())),
        "downgrade_reason_counts": dict(sorted(reason_counts.items())),
        "reason_refs": {key: sorted(set(values))[:20] for key, values in sorted(report_refs.items())},
    }


def source_flags(source: dict[str, Any]) -> dict[str, bool]:
    return {
        "identity_ambiguity": source.get("identity_status", {}).get("status") in {"missing_or_unknown", "join_hints_only"},
        "source_freshness": source.get("freshness", {}).get("status") in {"unknown", "stale", "blocked_or_unavailable", "dated_snapshot"},
        "coverage_gaps": bool(
            source.get("schema_status", {}).get("status") != "present"
            or source.get("coverage", {}).get("source_status") not in (None, "PASS", "OK", "FULL", "CAPPED_REQUIRES_D2_FULL_PULL")
        ),
        "weak_relationships": not source.get("consuming_flows") or source.get("identity_status", {}).get("status") == "missing_or_unknown",
        "candidate_only_records": bool(source.get("candidate_only")),
        "missing_geometry": source.get("geometry_status", {}).get("status") != "present",
        "missing_time_history": source.get("time_coverage", {}).get("status") in {"missing_or_unknown", "snapshot_only"},
    }


def per_source_scorecards(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for source in sources:
        flags = source_flags(source)
        issue_count = sum(1 for value in flags.values() if value)
        score = max(0, 100 - issue_count * 12)
        cards.append(
            {
                "source_id": source["source_id"],
                "city": source["city"],
                "domain": source["domain"],
                "source_class": source["source_class"],
                "maturity_score": score,
                "issue_count": issue_count,
                "flags": flags,
                "top_limitations": source.get("known_limitations", [])[:5],
                "consuming_flows": source.get("consuming_flows", []),
            }
        )
    return sorted(cards, key=lambda item: (item["maturity_score"], item["city"], item["domain"], item["source_id"]))


def duplicate_conflict_sources(sources: list[dict[str, Any]], downgrade_index: dict[str, Any]) -> list[str]:
    seen: dict[str, list[str]] = defaultdict(list)
    for source in sources:
        key = "|".join(
            [
                source.get("city", ""),
                str(source.get("url") or source.get("source_key") or source.get("source_name", "")).lower(),
            ]
        )
        seen[key].append(source["source_id"])
    duplicates = sorted({source_id for values in seen.values() if len(values) > 1 for source_id in values})
    conflict_count = sum(count for reason, count in downgrade_index.get("downgrade_reason_counts", {}).items() if "conflict" in reason.lower() or "contradiction" in reason.lower())
    if conflict_count and not duplicates:
        return ["check:conflict_or_contradiction_downgrades_present"]
    return duplicates


def scorecard(card_id: str, title: str, affected: list[str], total: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    ratio = len(affected) / total if total else 0
    if ratio >= 0.5:
        severity = "high"
    elif ratio >= 0.2:
        severity = "medium"
    elif affected:
        severity = "low"
    else:
        severity = "clear"
    score = max(0, round(100 - ratio * 100))
    return {
        "scorecard_id": card_id,
        "title": title,
        "status": "PASS_WITH_LIMITATIONS",
        "severity": severity,
        "maturity_score": score,
        "affected_count": len(affected),
        "total_sources": total,
        "affected_source_refs": sorted(affected)[:200],
        **(extra or {}),
    }


def build_dashboard(registry: dict[str, Any], downgrade_index: dict[str, Any]) -> dict[str, Any]:
    sources = registry["sources"]
    total = len(sources)
    flag_to_sources: dict[str, list[str]] = {card_id: [] for card_id in SCORECARD_IDS if card_id != "duplicate_conflict_risk" and card_id != "check_downgrade_reasons"}
    for source in sources:
        for flag, active in source_flags(source).items():
            if active:
                flag_to_sources[flag].append(source["source_id"])

    duplicate_sources = duplicate_conflict_sources(sources, downgrade_index)
    check_reason_count = sum(downgrade_index.get("downgrade_reason_counts", {}).values()) + sum(downgrade_index.get("claimability_status_counts", {}).values())
    check_affected = sorted(downgrade_index.get("reason_refs", {}).keys())[:200] if check_reason_count else []

    cards = [
        scorecard("identity_ambiguity", "Identity ambiguity", flag_to_sources["identity_ambiguity"], total),
        scorecard("source_freshness", "Source freshness", flag_to_sources["source_freshness"], total),
        scorecard("coverage_gaps", "Coverage gaps", flag_to_sources["coverage_gaps"], total),
        scorecard("duplicate_conflict_risk", "Duplicate/conflict risk", duplicate_sources, total),
        scorecard("weak_relationships", "Weak relationships", flag_to_sources["weak_relationships"], total),
        scorecard("candidate_only_records", "Candidate-only records", flag_to_sources["candidate_only_records"], total),
        scorecard("missing_geometry", "Missing geometry", flag_to_sources["missing_geometry"], total),
        scorecard("missing_time_history", "Missing time history", flag_to_sources["missing_time_history"], total),
        scorecard(
            "check_downgrade_reasons",
            "CHECK downgrade reasons",
            check_affected,
            max(1, total),
            {
                "downgrade_reason_counts": downgrade_index.get("downgrade_reason_counts", {}),
                "claimability_status_counts": downgrade_index.get("claimability_status_counts", {}),
            },
        ),
    ]
    weighted_scores = [card["maturity_score"] for card in cards]
    overall_score = round(sum(weighted_scores) / len(weighted_scores), 1) if weighted_scores else 0
    risk_counts = Counter(card["severity"] for card in cards)
    return {
        "artifact_id": "DATA_QUALITY_MATURITY_DASHBOARD_R1",
        "schema_version": "citybrain.data_quality_maturity_dashboard.r1",
        "generated_at": utc_now(),
        "status": "PASS_WITH_LIMITATIONS",
        "source_registry_ref": rel(SOURCE_REGISTRY_PATH),
        "source_count": total,
        "overall_maturity_score": overall_score,
        "risk_counts": dict(sorted(risk_counts.items())),
        "scorecards": cards,
        "recommendations": [
            "Use SourceRegistry v1 as the required source trust input for CHECK, CER, Event Fabric, DIFF, diagnostics, and future live-source onboarding.",
            "Treat unknown freshness, missing geometry, missing time history, and weak identity fields as visible client-facing maturity work, not hidden implementation debt.",
            "Prioritize sources with high consuming-flow value and low maturity score for source refresh, schema proof, geometry proof, and native-id hardening.",
        ],
        "non_claims": [
            "The dashboard is advisory and diagnostic only.",
            "It does not certify official source truth, legal findings, dispatch, enforcement, or production monitoring.",
            "It does not mutate source records or upstream data.",
        ],
    }


def write_view(dashboard: dict[str, Any]) -> None:
    rows = [
        "| Scorecard | Severity | Score | Affected |",
        "| --- | --- | ---: | ---: |",
    ]
    for card in dashboard["scorecards"]:
        rows.append(f"| {card['title']} | {card['severity']} | {card['maturity_score']} | {card['affected_count']} |")
    write_text(
        OUTPUT_ROOT / "DATA_QUALITY_MATURITY_VIEW.md",
        "# Track 5 Data Quality / Maturity Dashboard R1\n\n"
        f"Status: `{dashboard['status']}`\n\n"
        f"Overall maturity score: `{dashboard['overall_maturity_score']}`\n\n"
        + "\n".join(rows)
        + "\n\nThis is a diagnostic product surface over SourceRegistry v1. It exposes hidden weakness as a consultative asset without making official or operational claims.\n",
    )


def write_hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "artifact_id": "TRACK5_DATA_QUALITY_MATURITY_HASH_MANIFEST",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "status": "PASS",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def build_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    registry = ensure_source_registry()
    downgrade_index = extract_check_downgrades()
    source_scorecards = per_source_scorecards(registry["sources"])
    dashboard = build_dashboard(registry, downgrade_index)

    write_json(OUTPUT_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json", downgrade_index)
    write_json(OUTPUT_ROOT / "DATA_QUALITY_SOURCE_SCORECARDS.json", {"artifact_id": "DATA_QUALITY_SOURCE_SCORECARDS", "source_scorecards": source_scorecards})
    write_json(OUTPUT_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json", dashboard)
    write_view(dashboard)
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Track 5 Data Quality / Maturity Dashboard R1

Status: `{dashboard['status']}`

SourceRegistry input: `{rel(SOURCE_REGISTRY_PATH)}`

Sources scored: `{dashboard['source_count']}`

Overall maturity score: `{dashboard['overall_maturity_score']}`

The dashboard turns source weakness into a product-readable maturity surface across identity ambiguity, freshness, coverage, duplicate/conflict risk, weak relationships, candidate-only records, geometry, time history, and CHECK downgrade reasons.
""",
    )
    decision = {
        "artifact_id": "TRACK5_DATA_QUALITY_MATURITY_DASHBOARD_R1_DECISION",
        "status": FINAL_STATUS,
        "generated_at": utc_now(),
        "output_root": rel(OUTPUT_ROOT),
        "source_registry_ref": rel(SOURCE_REGISTRY_PATH),
        "scorecard_count": len(dashboard["scorecards"]),
        "overall_maturity_score": dashboard["overall_maturity_score"],
        "limitations": dashboard["non_claims"],
    }
    write_json(OUTPUT_ROOT / "DECISION.json", decision)
    write_hash_manifest()
    return decision


def validate_outputs() -> list[str]:
    required = [
        "DATA_QUALITY_MATURITY_DASHBOARD_R1.json",
        "DATA_QUALITY_SOURCE_SCORECARDS.json",
        "CHECK_DOWNGRADE_REASON_INDEX.json",
        "DATA_QUALITY_MATURITY_VIEW.md",
        "SUMMARY.md",
        "DECISION.json",
        "HASH_MANIFEST.json",
    ]
    errors = [f"missing:{name}" for name in required if not (OUTPUT_ROOT / name).exists()]
    if errors:
        return errors
    dashboard = read_json(OUTPUT_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json")
    decision = read_json(OUTPUT_ROOT / "DECISION.json")
    card_ids = {card["scorecard_id"] for card in dashboard.get("scorecards", [])}
    missing_cards = sorted(set(SCORECARD_IDS) - card_ids)
    if missing_cards:
        errors.append(f"missing_scorecards:{','.join(missing_cards)}")
    if dashboard.get("source_count", 0) <= 0:
        errors.append("dashboard_has_no_sources")
    if decision.get("status") != FINAL_STATUS:
        errors.append("decision_status_not_final_pass")
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    for entry in manifest.get("entries", []):
        path = ROOT / entry["path"]
        if not path.exists():
            errors.append(f"hash_missing:{entry['path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"hash_mismatch:{entry['path']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        decision = build_outputs()
    else:
        decision = read_json(OUTPUT_ROOT / "DECISION.json", {})
    errors = validate_outputs()
    if errors:
        print(json.dumps({"status": "BLOCKED", "errors": errors}, indent=2, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "PASS_WITH_LIMITATIONS",
                "decision": decision.get("status", FINAL_STATUS),
                "output_root": rel(OUTPUT_ROOT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
