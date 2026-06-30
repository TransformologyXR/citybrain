from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "F3-NYC-D5 Governed EvidenceBundle + Deterministic Flow 3 Briefing"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d5_governed_evidence_briefing"
DEFAULT_D4_DIR = "outputs/f3_nyc_d4_candidate_prioritization_review_routing"
DEFAULT_D3_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"
SCHEMA_VERSION = "Flow3EvidenceBundle.v1"

NO_OVERCLAIM_LINES = [
    "F3-NYC-D5 is a deterministic EvidenceBundle and briefing surface only.",
    "D5 does not call live NIM, NeMo, or any LLM.",
    "D5 does not certify affected buildings or affected assets.",
    "D5 presents candidate affected tax-lot context, not certified affected-building truth.",
    "D5 presents operator review routes, not emergency dispatch.",
    "D5 presents score-ordered review itineraries, not navigable routes.",
    "D5 does not make legal, safety, or emergency recommendations.",
    "D5 does not geocode address-only events.",
    "Firehouse/resource context is not dispatched-unit truth.",
    "MVC Vehicles remain event context only, not primary crash events.",
    "D5 uses the bounded D2/D3/D4 working set, not full-source citywide Flow 3 materialization.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"live (?:nim|nemo|llm) (?:called|enabled|available|ready)",
    r"(?:nim|nemo|llm) generated",
    r"affected buildings? (?:are )?certified",
    r"affected assets? (?:are )?certified",
    r"certified affected (?:building|asset)",
    r"emergency dispatch (?:is|ready|available|performed)",
    r"emergency response recommendations? (?:are )?(?:made|available|ready)",
    r"legal recommendations? (?:are )?(?:made|available|ready)",
    r"safety recommendations? (?:are )?(?:made|available|ready)",
    r"navigable routes? (?:are )?(?:generated|ready|available)",
    r"address-only events? (?:are )?geocoded",
    r"(?:is|as|becomes|claims) dispatched-unit truth",
    r"full-source citywide flow 3 materialization (?:is|ready|complete|available)",
    r"mvc vehicles (?:are|is) (?:the )?primary crash events?",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_payload(value: Any) -> str:
    return sha256_text(canonical_json(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D5-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d5" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["canonical", "evidence", "queries", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value is not None else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:120] or fallback


def sample_records(frame: pd.DataFrame, n: int) -> list[dict[str, Any]]:
    if frame.empty or "_empty" in frame.columns:
        return []
    return frame.head(n).where(pd.notna(frame.head(n)), None).to_dict("records")


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [path for path in sorted(root.rglob("*")) if path.is_file()]
        for path in files:
            watched[str(path)] = {
                "exists": True,
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "sha256": sha256_file(path) if path.stat().st_size < 250_000_000 else None,
            }
    return watched


def d4_paths(d4_dir: Path) -> dict[str, Path]:
    canonical = d4_dir / "canonical"
    return {
        "harness": d4_dir / "F3_NYC_D4_HARNESS_REPORT.json",
        "candidates": canonical / "f3_nyc_d4_prioritized_incident_candidates.parquet",
        "routes": canonical / "f3_nyc_d4_operator_review_routes.parquet",
        "stops": canonical / "f3_nyc_d4_route_stops.parquet",
        "review_edges": canonical / "f3_nyc_d4_review_plan_edges.parquet",
    }


def d3_paths(d3_dir: Path) -> dict[str, Path]:
    canonical = d3_dir / "canonical"
    return {
        "harness": d3_dir / "F3_NYC_D3_HARNESS_REPORT.json",
        "asset_edges": canonical / "f3_nyc_d3_incident_asset_candidate_edges.parquet",
        "response_edges": canonical / "f3_nyc_d3_response_resource_context_edges.parquet",
        "asset_candidates": canonical / "f3_nyc_d3_asset_candidates.parquet",
        "location_tiers": canonical / "f3_nyc_d3_location_tiers.parquet",
    }


class Flow3D5QueryEngine:
    def __init__(self, d4_dir: Path, d3_dir: Path):
        self.d4_dir = d4_dir
        self.d3_dir = d3_dir
        self.d4p = d4_paths(d4_dir)
        self.d3p = d3_paths(d3_dir)
        self.d4_harness = read_json(self.d4p["harness"], {})
        self.d3_harness = read_json(self.d3p["harness"], {})
        self.candidates = pd.read_parquet(self.d4p["candidates"])
        self.routes = pd.read_parquet(self.d4p["routes"])
        self.stops = pd.read_parquet(self.d4p["stops"])
        self.review_edges = pd.read_parquet(self.d4p["review_edges"])
        self.asset_edges = pd.read_parquet(self.d3p["asset_edges"])
        self.response_edges = pd.read_parquet(self.d3p["response_edges"])
        self.asset_candidates = pd.read_parquet(self.d3p["asset_candidates"])
        self.location_tiers = pd.read_parquet(self.d3p["location_tiers"])
        self.limitations = NO_OVERCLAIM_LINES + [
            "D5 EvidenceBundles are generated from D3/D4 deterministic outputs.",
            "Priority scores rank operator review candidates, not incident severity or emergency urgency.",
            "Review route proxy distances are straight-line context values, not street-network travel distances.",
        ]
        self.source_lineage = [
            {"source": "F3-NYC-D4 prioritized candidates", "path": str(self.d4p["candidates"])},
            {"source": "F3-NYC-D4 operator review routes", "path": str(self.d4p["routes"])},
            {"source": "F3-NYC-D4 route stops", "path": str(self.d4p["stops"])},
            {"source": "F3-NYC-D3 candidate affected tax-lot edges", "path": str(self.d3p["asset_edges"])},
            {"source": "F3-NYC-D3 response-resource context edges", "path": str(self.d3p["response_edges"])},
            {"source": "F3-NYC-D3 location confidence tiers", "path": str(self.d3p["location_tiers"])},
        ]

    def _bundle(self, query_type: str, query: dict[str, Any], answer_status: str, facts: list[dict[str, Any]], counts: dict[str, Any], entities: list[dict[str, Any]], edges: list[dict[str, Any]], paths: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        subject = query.get("subject") or query.get("source_id") or query.get("route_id") or query_type
        bundle = {
            "schema_version": SCHEMA_VERSION,
            "bundle_id": f"evidence_bundle:us-nyc:flow3:d5:{query_type}:{safe_id(subject)}",
            "tool": "citybrain_flow3_nyc_d5_query",
            "query_type": query_type,
            "query": query,
            "answer_status": answer_status,
            "facts": facts,
            "counts": counts,
            "entities": entities,
            "edges": edges,
            "paths": paths or [],
            "limitations": self.limitations,
            "source_lineage": self.source_lineage,
            "grounding_policy": {
                "model_may_narrate": True,
                "model_may_compute_counts": False,
                "model_may_add_facts": False,
            },
            "governance": {
                "deterministic_only": True,
                "live_nim_called": False,
                "live_nemo_called": False,
                "llm_called": False,
                "briefing_may_only_restate_bundle": True,
            },
        }
        bundle["content_hash"] = sha256_payload({k: v for k, v in bundle.items() if k != "content_hash"})
        return bundle

    def candidate_profile(self, source_id: str) -> dict[str, Any]:
        row = self.candidates[self.candidates["source_id"] == source_id]
        if row.empty:
            return self._bundle(
                "candidate_profile",
                {"source_id": source_id},
                "not_found",
                [{"fact": "Candidate was not found in the D4 prioritized set.", "value": source_id, "source": "F3-NYC-D4 candidates"}],
                {"matches": 0},
                [],
                [],
            )
        candidate = row.iloc[0].to_dict()
        asset_edge_rows = self.asset_edges[self.asset_edges["source_id"] == source_id]
        response_edge_rows = self.response_edges[self.response_edges["source_id"] == source_id].sort_values("rank").head(3)
        asset_rows = self.asset_candidates[self.asset_candidates["canonical_id"] == candidate.get("primary_candidate_asset_id")]
        stop_rows = self.stops[self.stops["source_id"] == source_id]
        route_ids = sorted(stop_rows["route_id"].dropna().unique().tolist()) if not stop_rows.empty else []
        route_rows = self.routes[self.routes["route_id"].isin(route_ids)] if route_ids else pd.DataFrame()
        facts = [
            {"fact": "Event is a D4 operator-review candidate.", "value": candidate.get("source_id"), "source": "F3-NYC-D4 prioritized candidates"},
            {"fact": "Operator review priority score.", "value": candidate.get("operator_review_priority_score"), "source": "F3-NYC-D4 priority model"},
            {"fact": "Location confidence tier.", "value": candidate.get("location_confidence_tier"), "source": "F3-NYC-D3 location tiers"},
            {"fact": "Primary candidate affected tax lot.", "value": candidate.get("primary_candidate_bbl"), "source": "F3-NYC-D3 candidate asset edges"},
            {"fact": "Candidate affected asset status.", "value": candidate.get("asset_edge_status"), "source": "F3-NYC-D3 candidate asset edges"},
            {"fact": "Nearest firehouse/resource context.", "value": candidate.get("nearest_resource_id"), "source": "F3-NYC-D3 response context"},
            {"fact": "D4 route plan eligibility.", "value": candidate.get("route_plan_eligibility"), "source": "F3-NYC-D4 route planning"},
        ]
        entities = [candidate]
        entities.extend(sample_records(asset_rows, 1))
        entities.extend(sample_records(route_rows, 3))
        edges = sample_records(asset_edge_rows, 5) + sample_records(response_edge_rows, 5)
        paths = sample_records(stop_rows, 5)
        counts = {
            "candidate_rows": 1,
            "candidate_asset_edges": int(len(asset_edge_rows)),
            "response_context_edges": int(len(response_edge_rows)),
            "review_routes_containing_candidate": int(len(route_ids)),
            "review_stops_for_candidate": int(len(stop_rows)),
        }
        return self._bundle("candidate_profile", {"source_id": source_id, "subject": source_id}, "answered", facts, counts, entities, edges, paths)

    def route_profile(self, route_id: str) -> dict[str, Any]:
        route = self.routes[self.routes["route_id"] == route_id]
        if route.empty:
            return self._bundle(
                "route_profile",
                {"route_id": route_id},
                "not_found",
                [{"fact": "Route was not found in the D4 review-plan set.", "value": route_id, "source": "F3-NYC-D4 routes"}],
                {"matches": 0},
                [],
                [],
            )
        route_record = route.iloc[0].to_dict()
        stops = self.stops[self.stops["route_id"] == route_id].sort_values("sequence")
        stop_ids = stops["source_id"].dropna().tolist()
        candidate_rows = self.candidates[self.candidates["source_id"].isin(stop_ids)].copy()
        route_edges = self.review_edges[self.review_edges["source_id"] == route_id].sort_values("sequence")
        facts = [
            {"fact": "Route is an operator review plan only.", "value": route_id, "source": "F3-NYC-D4 route plan"},
            {"fact": "Review route stop count.", "value": int(route_record.get("candidate_stop_count") or len(stops)), "source": "F3-NYC-D4 route plan"},
            {"fact": "Anchor firehouse/resource context.", "value": route_record.get("anchor_resource_id"), "source": "F3-NYC-D4 route plan"},
            {"fact": "Route optimization backend.", "value": route_record.get("optimization_backend"), "source": "F3-NYC-D4 route plan"},
            {"fact": "Straight-line review proxy meters.", "value": route_record.get("straight_line_review_proxy_m"), "source": "F3-NYC-D4 route plan"},
            {"fact": "Route plan status.", "value": route_record.get("route_plan_status"), "source": "F3-NYC-D4 route plan"},
        ]
        counts = {
            "routes": 1,
            "review_stops": int(len(stops)),
            "review_plan_edges": int(len(route_edges)),
            "candidate_entities": int(len(candidate_rows)),
        }
        entities = [route_record] + sample_records(candidate_rows, 10)
        edges = sample_records(route_edges, 20)
        paths = sample_records(stops, 20)
        return self._bundle("route_profile", {"route_id": route_id, "subject": route_id}, "answered", facts, counts, entities, edges, paths)

    def route_stop_trace(self, route_id: str, sequence: int) -> dict[str, Any]:
        stops = self.stops[(self.stops["route_id"] == route_id) & (self.stops["sequence"] == sequence)]
        if stops.empty:
            return self._bundle(
                "route_stop_trace",
                {"route_id": route_id, "sequence": sequence},
                "not_found",
                [{"fact": "Route stop was not found in the D4 review-plan set.", "value": f"{route_id}#{sequence}", "source": "F3-NYC-D4 route stops"}],
                {"matches": 0},
                [],
                [],
            )
        stop = stops.iloc[0].to_dict()
        candidate = self.candidates[self.candidates["source_id"] == stop.get("source_id")]
        asset_edges = self.asset_edges[self.asset_edges["source_id"] == stop.get("source_id")]
        response_edges = self.response_edges[self.response_edges["source_id"] == stop.get("source_id")].sort_values("rank").head(3)
        facts = [
            {"fact": "Route stop is a review stop only.", "value": stop.get("source_id"), "source": "F3-NYC-D4 route stops"},
            {"fact": "Stop sequence in review itinerary.", "value": sequence, "source": "F3-NYC-D4 route stops"},
            {"fact": "Segment distance is a straight-line proxy in meters.", "value": stop.get("segment_straight_line_proxy_m"), "source": "F3-NYC-D4 route stops"},
            {"fact": "Primary candidate tax lot BBL.", "value": stop.get("primary_candidate_bbl"), "source": "F3-NYC-D4 route stops"},
            {"fact": "Nearest firehouse/resource context.", "value": stop.get("nearest_resource_id"), "source": "F3-NYC-D4 route stops"},
        ]
        counts = {
            "route_stop_rows": 1,
            "candidate_rows": int(len(candidate)),
            "candidate_asset_edges": int(len(asset_edges)),
            "response_context_edges": int(len(response_edges)),
        }
        entities = [stop] + sample_records(candidate, 1)
        edges = sample_records(asset_edges, 5) + sample_records(response_edges, 5)
        return self._bundle("route_stop_trace", {"route_id": route_id, "sequence": sequence, "subject": f"{route_id}#{sequence}"}, "answered", facts, counts, entities, edges, [stop])

    def source_limitations(self) -> dict[str, Any]:
        d4_counts = {
            "candidate_pool_rows": self.d4_harness.get("candidate_pool_rows"),
            "prioritized_candidate_rows": self.d4_harness.get("prioritized_candidate_rows"),
            "operator_review_routes": self.d4_harness.get("operator_review_routes"),
            "operator_review_stops": self.d4_harness.get("operator_review_stops"),
            "cuopt_backend_called": self.d4_harness.get("cuopt_backend_called"),
        }
        d3_counts = {
            "location_tier_counts": self.d3_harness.get("location_tier_counts"),
            "asset_candidate_edges": self.d3_harness.get("asset_candidate_edges"),
            "response_context_edges": self.d3_harness.get("response_context_edges"),
            "fdny_asset_edges": self.d3_harness.get("fdny_asset_edges"),
        }
        facts = [
            {"fact": "D5 uses D4 deterministic review-plan outputs.", "value": self.d4_harness.get("status"), "source": "F3-NYC-D4 harness"},
            {"fact": "D5 uses D3 candidate context outputs.", "value": self.d3_harness.get("status"), "source": "F3-NYC-D3 harness"},
            {"fact": "cuOpt/backend optimization was not called by D4.", "value": self.d4_harness.get("cuopt_backend_called"), "source": "F3-NYC-D4 harness"},
            {"fact": "FDNY affected-asset edges emitted by D3.", "value": self.d3_harness.get("fdny_asset_edges"), "source": "F3-NYC-D3 harness"},
        ]
        counts = {"d4": d4_counts, "d3": d3_counts, "limitations_count": len(self.limitations)}
        return self._bundle("source_limitations", {"subject": "flow3_d5_limitations"}, "answered", facts, counts, [], [], [])

    def overview(self) -> dict[str, Any]:
        facts = [
            {"fact": "D4 candidate pool rows.", "value": int(self.d4_harness.get("candidate_pool_rows") or 0), "source": "F3-NYC-D4 harness"},
            {"fact": "D4 prioritized candidate rows.", "value": int(self.d4_harness.get("prioritized_candidate_rows") or 0), "source": "F3-NYC-D4 harness"},
            {"fact": "D4 operator review routes.", "value": int(self.d4_harness.get("operator_review_routes") or 0), "source": "F3-NYC-D4 harness"},
            {"fact": "D3 location tier counts.", "value": self.d3_harness.get("location_tier_counts"), "source": "F3-NYC-D3 harness"},
        ]
        counts = {
            "candidates": int(len(self.candidates)),
            "routes": int(len(self.routes)),
            "stops": int(len(self.stops)),
            "asset_edges": int(len(self.asset_edges)),
            "response_edges": int(len(self.response_edges)),
        }
        return self._bundle("flow3_d5_overview", {"subject": "flow3_d5_overview"}, "answered", facts, counts, [], [], [])


def deterministic_briefing(bundle: dict[str, Any]) -> str:
    title = bundle["query_type"].replace("_", " ").title()
    lines = [f"# {title}", ""]
    lines.extend(NO_OVERCLAIM_LINES)
    lines.append("")
    lines.append("This briefing is generated from the F3-NYC-D5 EvidenceBundle only.")
    lines.append("No live NIM, NeMo, or LLM call generated these facts.")
    lines.append("")
    lines.append(f"Bundle: `{bundle['bundle_id']}`")
    lines.append(f"Answer status: `{bundle['answer_status']}`")
    lines.append("")
    lines.append("## Facts")
    for fact in bundle.get("facts", []):
        lines.append(f"- {fact['fact']}: `{fact.get('value')}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("```json")
    lines.append(json.dumps(json_safe(bundle.get("counts", {})), indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Limitations")
    for limitation in bundle.get("limitations", []):
        lines.append(f"- {limitation}")
    lines.append("")
    lines.append(f"Evidence hash: `{bundle['content_hash']}`")
    return "\n".join(lines) + "\n"


def grounding_check(bundle: dict[str, Any], briefing: str) -> dict[str, Any]:
    bundle_text = canonical_json(bundle).lower()
    allowed = bundle_text + "\n" + "\n".join(NO_OVERCLAIM_LINES).lower() + "\nthis briefing is generated from the f3-nyc-d5 evidencebundle only.\nno live nim, nemo, or llm call generated these facts."
    numeric_tokens = sorted(set(re.findall(r"(?<![a-z0-9])[-]?\d+(?:\.\d+)?(?![a-z0-9])", briefing.lower())))
    missing_numbers = [token for token in numeric_tokens if token not in allowed]
    id_tokens = sorted(set(re.findall(r"(?:event|asset|resource|review_route|evidence_bundle):[a-z0-9:_-]+", briefing.lower())))
    missing_ids = [token for token in id_tokens if token not in allowed]
    forbidden_patterns = [
        r"(?:is|as|becomes|claims) certified affected",
        r"emergency dispatch recommendation (?:is|ready|available)",
        r"navigable route generated",
    ]
    forbidden_hits = [pattern for pattern in forbidden_patterns if re.search(pattern, briefing.lower())]
    return {
        "status": "PASS" if not missing_numbers and not missing_ids and not forbidden_hits else "FAIL",
        "numeric_tokens_checked": len(numeric_tokens),
        "id_tokens_checked": len(id_tokens),
        "missing_numbers": missing_numbers,
        "missing_ids": missing_ids,
        "forbidden_hits": forbidden_hits,
        "bundle_hash": bundle.get("content_hash"),
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    texts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json"} and path.name not in {"SHA256SUMS.json", "F3_NYC_D5_NO_OVERCLAIM_REPORT.json"}:
            texts.append((path.relative_to(output_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace").lower()))
    combined = "\n".join(text for _, text in texts)
    missing = [line for line in NO_OVERCLAIM_LINES if line.lower() not in combined]
    forbidden = []
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        for path, text in texts:
            if re.search(pattern, text):
                forbidden.append({"path": path, "pattern": pattern})
    return {
        "status": "PASS" if not missing and not forbidden else "FAIL",
        "required_boundary_lines": NO_OVERCLAIM_LINES,
        "missing_boundary_lines": missing,
        "forbidden_positive_claims_found": forbidden,
    }


def private_data_scan(payload: Any) -> dict[str, Any]:
    text = json.dumps(json_safe(payload), default=str)
    phone = re.search(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)", text) is not None
    return {
        "status": "FAIL" if phone else "PASS",
        "policy": "D5 emits deterministic evidence over event IDs, candidate tax lots, firehouse/resource identifiers, review scores, and route proxy distances. It emits no names, phone numbers, narratives, license fields, or patient-level details.",
        "unredacted_phone_pattern_found": phone,
    }


def gate_report(d4_ok: bool, d3_ok: bool, bundles: dict[str, dict[str, Any]], briefings: dict[str, str], grounding: dict[str, Any], query_smoke: dict[str, Any], privacy: dict[str, Any], overclaim: dict[str, Any], no_mutation: dict[str, Any]) -> dict[str, str]:
    return {
        "F3-NYC-D5-PRECOND": "PASS" if d4_ok and d3_ok else "FAIL",
        "F3-NYC-D5-QUERY-CONTRACT": "PASS" if {"candidate_profile", "route_profile", "route_stop_trace", "source_limitations"} <= set(bundles) else "FAIL",
        "F3-NYC-D5-EVIDENCE-BUNDLES": "PASS" if all(bundle.get("schema_version") == SCHEMA_VERSION and bundle.get("content_hash") for bundle in bundles.values()) else "FAIL",
        "F3-NYC-D5-DETERMINISTIC-BRIEFINGS": "PASS" if len(briefings) >= 4 and all("No live NIM" in text for text in briefings.values()) else "FAIL",
        "F3-NYC-D5-BRIEFING-GROUNDING": grounding.get("status", "FAIL"),
        "F3-NYC-D5-QUERY-SMOKE": query_smoke.get("status", "FAIL"),
        "F3-NYC-D5-NO-LIVE-MODEL": "PASS" if all(not bundle.get("governance", {}).get(key) for bundle in bundles.values() for key in ["live_nim_called", "live_nemo_called", "llm_called"]) else "FAIL",
        "F3-NYC-D5-PRIVATE-DATA": privacy.get("status", "FAIL"),
        "F3-NYC-D5-NO-OVERCLAIM": overclaim.get("status", "FAIL"),
        "F3-NYC-D5-NO-MUTATION": no_mutation.get("status", "FAIL"),
    }


def run_f3_nyc_d5_gate(
    project_root: str,
    d4_dir: str,
    d3_dir: str,
    output_dir: str,
) -> dict:
    project = Path(project_root).resolve()
    d4_path = Path(d4_dir)
    d3_path = Path(d3_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    before = input_snapshot([d4_path, d3_path])

    engine = Flow3D5QueryEngine(d4_path, d3_path)
    d4_ok = engine.d4_harness.get("status") in {"PASS", "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION"}
    d3_ok = engine.d3_harness.get("status") in {"PASS", "PASS_WITH_LOCATION_CONFIDENCE_TIERS"}

    top_candidate_id = str(engine.candidates.iloc[0]["source_id"])
    top_route_id = str(engine.routes.iloc[0]["route_id"])
    first_stop_sequence = int(engine.stops[engine.stops["route_id"] == top_route_id].sort_values("sequence").iloc[0]["sequence"])
    bundles = {
        "candidate_profile": engine.candidate_profile(top_candidate_id),
        "route_profile": engine.route_profile(top_route_id),
        "route_stop_trace": engine.route_stop_trace(top_route_id, first_stop_sequence),
        "source_limitations": engine.source_limitations(),
        "flow3_d5_overview": engine.overview(),
    }
    briefings = {name: deterministic_briefing(bundle) for name, bundle in bundles.items()}
    grounding_items = {}
    for name, bundle in bundles.items():
        bundle_path = output_path / "evidence" / f"evidence_bundle_{name}.json"
        briefing_path = output_path / "queries" / f"deterministic_briefing_{name}.md"
        write_json(bundle_path, bundle)
        write_text(briefing_path, briefings[name])
        grounding_items[name] = grounding_check(bundle, briefings[name])

    grounding_report = {
        "status": "PASS" if all(item["status"] == "PASS" for item in grounding_items.values()) else "FAIL",
        "items": grounding_items,
    }
    sample_query_inputs = {
        "candidate_profile": {"query_type": "candidate_profile", "source_id": top_candidate_id},
        "route_profile": {"query_type": "route_profile", "route_id": top_route_id},
        "route_stop_trace": {"query_type": "route_stop_trace", "route_id": top_route_id, "sequence": first_stop_sequence},
        "source_limitations": {"query_type": "source_limitations"},
    }
    sample_query_results = {name: bundles[name] for name in sample_query_inputs}
    query_smoke = {
        "status": "PASS" if all(bundle.get("answer_status") == "answered" for bundle in sample_query_results.values()) else "FAIL",
        "sample_query_inputs": sample_query_inputs,
        "sample_answer_statuses": {name: bundle.get("answer_status") for name, bundle in sample_query_results.items()},
    }

    query_subjects = pd.DataFrame(
        [
            {"subject_type": "candidate", "subject_id": top_candidate_id, "query_type": "candidate_profile"},
            {"subject_type": "review_route", "subject_id": top_route_id, "query_type": "route_profile"},
            {"subject_type": "route_stop", "subject_id": f"{top_route_id}#{first_stop_sequence}", "query_type": "route_stop_trace"},
            {"subject_type": "system", "subject_id": "flow3_d5_limitations", "query_type": "source_limitations"},
        ]
    )
    bundle_index = pd.DataFrame(
        [
            {
                "bundle_name": name,
                "bundle_id": bundle["bundle_id"],
                "query_type": bundle["query_type"],
                "answer_status": bundle["answer_status"],
                "content_hash": bundle["content_hash"],
                "facts": len(bundle.get("facts", [])),
                "entities": len(bundle.get("entities", [])),
                "edges": len(bundle.get("edges", [])),
                "paths": len(bundle.get("paths", [])),
            }
            for name, bundle in bundles.items()
        ]
    )
    briefing_index = pd.DataFrame(
        [
            {
                "briefing_name": name,
                "query_type": bundles[name]["query_type"],
                "bundle_id": bundles[name]["bundle_id"],
                "briefing_sha256": sha256_text(text),
                "grounding_status": grounding_items[name]["status"],
            }
            for name, text in briefings.items()
        ]
    )
    write_parquet(output_path / "canonical" / "flow3_d5_query_subjects.parquet", query_subjects)
    write_parquet(output_path / "canonical" / "flow3_d5_evidence_bundle_index.parquet", bundle_index)
    write_parquet(output_path / "canonical" / "flow3_d5_briefing_index.parquet", briefing_index)
    write_json(output_path / "queries" / "sample_query_inputs.json", sample_query_inputs)
    write_json(output_path / "queries" / "sample_query_results.json", sample_query_results)
    write_json(output_path / "queries" / "deterministic_briefings.json", briefings)

    query_contract = {
        "status": "PASS",
        "supported_query_types": {
            "candidate_profile": {"input": "source_id", "description": "Return candidate event, candidate tax-lot context, response context, and review-plan membership."},
            "route_profile": {"input": "route_id", "description": "Return operator review route plan, stops, review edges, and route limitations."},
            "route_stop_trace": {"input": "route_id + sequence", "description": "Return one route stop with candidate tax-lot and response-resource context."},
            "source_limitations": {"input": "none", "description": "Return D3/D4 source limits and governance boundaries."},
        },
        "unsupported": ["live_nim", "live_nemo", "emergency_dispatch", "navigable_routing", "certified_affected_building"],
    }
    write_json(output_path / "F3_NYC_D5_INPUT_INVENTORY.json", {"project_root": str(project), "d4_dir": str(d4_path), "d3_dir": str(d3_path), "d4_status": engine.d4_harness.get("status"), "d3_status": engine.d3_harness.get("status")})
    write_json(output_path / "F3_NYC_D5_QUERY_CONTRACT_REPORT.json", query_contract)
    write_json(output_path / "F3_NYC_D5_EVIDENCE_BUNDLE_REPORT.json", {"status": "PASS", "schema_version": SCHEMA_VERSION, "bundles": bundle_index.to_dict("records")})
    write_json(output_path / "F3_NYC_D5_DETERMINISTIC_BRIEFING_REPORT.json", {"status": "PASS", "briefings": briefing_index.to_dict("records")})
    write_json(output_path / "F3_NYC_D5_QUERY_SMOKE_REPORT.json", query_smoke)
    write_json(output_path / "F3_NYC_D5_BRIEFING_GROUNDING_REPORT.json", grounding_report)
    write_json(output_path / "reports" / "source_lineage.json", engine.source_lineage)
    write_json(output_path / "reports" / "bundle_hashes.json", {name: bundle["content_hash"] for name, bundle in bundles.items()})
    write_json(output_path / "reports" / "query_contract.json", query_contract)
    write_json(output_path / "reports" / "briefing_grounding.json", grounding_report)
    write_json(output_path / "reports" / "source_limitations.json", {"limitations": engine.limitations})
    write_json(output_path / "reports" / "confidence_summary.json", {"d3_location_tier_counts": engine.d3_harness.get("location_tier_counts"), "d4_priority_summary": engine.d4_harness.get("priority_summary")})
    write_json(output_path / "reports" / "no_live_model_calls.json", {"live_nim_called": False, "live_nemo_called": False, "llm_called": False, "status": "PASS"})
    write_json(output_path / "reports" / "recommended_d6_plan.json", {"recommended_next": "F3-NYC-D6 can add live Spark/NIM replay over these EvidenceBundles with a grounded narration gate.", "do_not_skip": "Keep D5 deterministic bundle facts as the only source of narrated facts."})

    privacy = private_data_scan({"bundles": bundles, "briefings": briefings})
    write_json(output_path / "F3_NYC_D5_PRIVATE_DATA_SCAN_REPORT.json", privacy)
    readme = "# F3-NYC-D5 Governed EvidenceBundle + Deterministic Flow 3 Briefing\n\nStatus: pending final harness write.\n\n" + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES) + "\n"
    write_text(output_path / "README.md", readme)
    write_text(
        output_path / "F3_NYC_D5_ADAPTER_HANDOVER.md",
        "# F3-NYC-D5 Adapter Handover\n\n"
        + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES)
        + "\n\nD6 should call live Spark/NIM only over these EvidenceBundles, and must keep the grounded narration gate: no new counts, no new facts, no emergency-dispatch language.\n",
    )

    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D5_NO_OVERCLAIM_REPORT.json", overclaim)
    after = input_snapshot([d4_path, d3_path])
    no_mutation = {"gate": "F3-NYC-D5-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "watched_input_count": 2}
    gates = gate_report(d4_ok, d3_ok, bundles, briefings, grounding_report, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS" if hard_pass else "FAIL"

    final_readme = f"""# F3-NYC-D5 Governed EvidenceBundle + Deterministic Flow 3 Briefing

Status: {status}

{chr(10).join(f"- {line}" for line in NO_OVERCLAIM_LINES)}

EvidenceBundles emitted: {len(bundles)}
Deterministic briefings emitted: {len(briefings)}
Supported query types: candidate_profile, route_profile, route_stop_trace, source_limitations
Live model calls: none
"""
    write_text(output_path / "README.md", final_readme)
    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D5_NO_OVERCLAIM_REPORT.json", overclaim)
    gates = gate_report(d4_ok, d3_ok, bundles, briefings, grounding_report, query_smoke, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    status = "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS" if hard_pass else "FAIL"

    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "schema_version": SCHEMA_VERSION,
        "evidence_bundles": len(bundles),
        "deterministic_briefings": len(briefings),
        "supported_query_types": list(query_contract["supported_query_types"].keys()),
        "live_nim_called": False,
        "live_nemo_called": False,
        "llm_called": False,
        "query_smoke": query_smoke,
        "briefing_grounding": grounding_report,
        "private_data_scan": privacy,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
    }
    write_json(output_path / "F3_NYC_D5_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D5-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D5_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D5_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D5 governed EvidenceBundle + deterministic briefing")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d5_gate(args.project_root, args.d4_dir, args.d3_dir, args.output_dir)
    print(f"F3-NYC-D5 Governed EvidenceBundle + Deterministic Flow 3 Briefing: {report['status']}")
    print(f"EvidenceBundles emitted: {report['evidence_bundles']}")
    print(f"Deterministic briefings emitted: {report['deterministic_briefings']}")
    print(f"Supported query types: {', '.join(report['supported_query_types'])}")
    print(f"Query smoke: {report['query_smoke']['status']}")
    print(f"Briefing grounding: {report['briefing_grounding']['status']}")
    print(f"Live NIM/NeMo/LLM calls: {report['live_nim_called']}/{report['live_nemo_called']}/{report['llm_called']}")
    print(f"Private-data scan: {report['private_data_scan']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
