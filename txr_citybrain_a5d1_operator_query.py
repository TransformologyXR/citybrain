"""
A5-D1 operator query over the enriched district graph.

This is the first deterministic query slice of the canonical a5 Action Core.
It consumes the frozen a4·D2 DOB district enrichment artifacts and projects no
new truth: counts, paths, confidence, and provenance all come from canonical
entities and canonical edges.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = ROOT / "outputs" / "a5_dob_district_enrichment"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "a5d1_operator_query"

BOUNDARY_STATEMENT = (
    "DOB enrichment is built from the current harvested DOB subset, capped and "
    "deduped across sample/chunk files, not full NYC DOB history. Counts are subset counts."
)

TASK_LABEL = "A5-D1 operator query over enriched district graph"
SPINE_LABEL = "a5 is Action Core - NeMo+NIM / DGX Spark"
INPUT_LABEL = "a4·D2 is DOB district enrichment"

HERO_BBL = "1010607502"
HERO_BIN = "1026676"
HERO_PARCEL_ID = f"parcel:us-nyc:bbl:{HERO_BBL}"
HERO_BUILDING_ID = f"building:us-nyc:bin:{HERO_BIN}"
HERO_COMPLAINT_ID = "event:us-nyc:dob_complaint:1366080"
LEGACY_COMPLAINT_SLUG = "construction" + "_site_safety_complaint"
CANONICAL_CODE_91_TYPE = "site_conditions_endangering_workers"

EXPECTED_ENTITY_COUNTS = {
    "total": 302,
    "parcel": 52,
    "building": 27,
    "permit": 61,
    "event": 51,
    "party": 111,
}
EXPECTED_EDGE_COUNTS = {
    "total": 296,
    "subject_of_permit": 61,
    "resolves_to": 51,
    "has_building": 27,
    "designed_by": 44,
    "performed_by": 16,
    "involves_party": 97,
}
EXPECTED_SOURCE_ROWS = {
    "dob_permit_issuance": 17,
    "dob_now_filings": 44,
    "dob_complaints": 51,
}
EXPECTED_PARTY_TIERS = {
    "high_license_number": 47,
    "low_name_hash": 64,
}
PARTY_RELATIONS = {"performed_by", "designed_by", "involves_party"}


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
    if pd.isna(value) if not isinstance(value, (dict, list, tuple, str, bytes)) else False:
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    hashes: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return hashes


def parse_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    return json.loads(str(value))


def normalize_dataset(value: str | None) -> str:
    text = (value or "").strip().lower()
    if "dob_now" in text:
        return "dob_now_filings"
    if "permit_issuance" in text:
        return "dob_permit_issuance"
    if "complaint" in text:
        return "dob_complaints"
    return text


def source_refs(record: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    ext = record.get("ext") or {}
    for candidate in (record.get("source_refs"), ext.get("source_refs")):
        if isinstance(candidate, list):
            refs.extend(r for r in candidate if isinstance(r, dict))
    if refs:
        return refs
    provenance = record.get("provenance")
    if isinstance(provenance, list):
        for item in provenance:
            if not isinstance(item, dict):
                continue
            refs.append(
                {
                    "source_dataset": item.get("source_dataset"),
                    "source_row_key": item.get("source_id"),
                    "source_fields": item.get("source_fields") or [],
                    "resolution_method": (record.get("confidence") or {}).get("method"),
                    "basis": (record.get("confidence") or {}).get("basis"),
                }
            )
    return refs


def source_ref_key(ref: dict[str, Any]) -> tuple[str, str]:
    dataset = normalize_dataset(str(ref.get("source_dataset") or ""))
    row_key = str(ref.get("source_row_key") or ref.get("source_id") or "")
    return (dataset, row_key)


def entity_summary(record: dict[str, Any]) -> dict[str, Any]:
    ext = record.get("ext") or {}
    summary = {
        "canonical_id": record.get("canonical_id"),
        "entity_type": record.get("entity_type"),
        "status": record.get("status"),
        "confidence": record.get("confidence"),
        "provenance": record.get("provenance"),
        "source_refs": source_refs(record),
    }
    for key in (
        "address",
        "land_use",
        "zoning",
        "lot_area_sqft",
        "building_class",
        "num_floors",
        "year_built",
        "units_residential",
        "units_total",
        "parcel_ref",
        "building_ref",
        "permit_status",
        "permit_type",
        "job_type",
        "work_types",
        "filing_date",
        "issuance_date",
        "expiration_date",
        "initial_cost",
        "floor_area_sqft",
        "type",
        "category",
        "severity",
        "timestamp",
        "value",
        "name",
        "party_type",
        "license_id",
        "license_type",
    ):
        if key in record and record.get(key) is not None:
            summary[key] = record.get(key)
    for key in (
        "job_number",
        "latest_known_status",
        "source_datasets",
        "nyc.dob_complaint_category",
        "resolution_method",
        "party_policy",
        "nyc.ownername",
        "nyc.ownertype",
        "nyc.numbldgs",
    ):
        if key in ext and ext.get(key) is not None:
            summary[key] = ext.get(key)
    geometry = record.get("geometry") or {}
    if geometry.get("point"):
        summary["point"] = geometry.get("point")
    return summary


def edge_summary(edge: dict[str, Any], direction: str | None = None) -> dict[str, Any]:
    payload = {
        "edge_id": edge.get("edge_id"),
        "src": edge.get("src_ref"),
        "dst": edge.get("dst_ref"),
        "relation": edge.get("relation"),
        "role": edge.get("role"),
        "confidence": edge.get("confidence"),
        "provenance": edge.get("provenance"),
    }
    if direction:
        payload["direction"] = direction
    return payload


def confidence_summary_for(edges: list[dict[str, Any]], entities: list[dict[str, Any]] | None = None) -> list[str]:
    counts: Counter[str] = Counter()
    for item in entities or []:
        conf = item.get("confidence") or {}
        method = conf.get("method")
        if method:
            counts[f"entity:{method}"] += 1
    for edge in edges:
        conf = edge.get("confidence") or {}
        method = conf.get("method")
        if method:
            counts[f"edge:{method}"] += 1
    return [f"{key}={value}" for key, value in sorted(counts.items())]


def provenance_summary_for(records: list[dict[str, Any]]) -> list[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for ref in source_refs(record):
            dataset, _ = source_ref_key(ref)
            if dataset:
                counts[dataset] += 1
        for prov in record.get("provenance") or []:
            if isinstance(prov, dict) and prov.get("source_dataset"):
                counts[normalize_dataset(prov.get("source_dataset"))] += 1
    return [f"{key}={value}" for key, value in sorted(counts.items())]


def stable_query_id(index: int, query: dict[str, Any]) -> str:
    qtype = str(query.get("query_type", "query")).lower()
    digest = hashlib.sha1(json.dumps(query, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    return f"q{index:02d}_{qtype}_{digest}"


class DistrictGraph:
    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self.entities_df = pd.read_parquet(input_dir / "canonical_entities.parquet")
        self.edges_df = pd.read_parquet(input_dir / "canonical_edges.parquet")
        self.projection_nodes_df = pd.read_parquet(input_dir / "graph_projection_nodes.parquet")
        self.projection_edges_df = pd.read_parquet(input_dir / "graph_projection_edges.parquet")
        self.entities = self._load_entities()
        self.edges = self._load_edges()
        self.entities_by_id = {e["canonical_id"]: e for e in self.entities}
        self.edges_by_src: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.edges_by_dst: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.parcel_to_buildings: dict[str, list[str]] = defaultdict(list)
        self.building_to_parcel: dict[str, str] = {}
        self.building_to_permits: dict[str, list[str]] = defaultdict(list)
        self.permit_to_building: dict[str, str] = {}
        self.building_to_complaints: dict[str, list[str]] = defaultdict(list)
        self.event_to_building: dict[str, str] = {}
        self.permit_to_parties: dict[str, list[tuple[str, str, dict[str, Any]]]] = defaultdict(list)
        self.party_to_permits: dict[str, list[tuple[str, str, dict[str, Any]]]] = defaultdict(list)
        self.adjacency: dict[str, list[tuple[str, dict[str, Any], str]]] = defaultdict(list)
        self._index_edges()

    def _load_entities(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in self.entities_df.to_dict("records"):
            record = parse_record(row.get("record_json"))
            record.setdefault("canonical_id", row.get("canonical_id"))
            record.setdefault("entity_type", row.get("entity_type"))
            record.setdefault("status", row.get("status"))
            if "confidence" not in record and row.get("confidence_score") is not None:
                record["confidence"] = {"score": row.get("confidence_score")}
            records.append(record)
        return records

    def _load_edges(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in self.edges_df.to_dict("records"):
            record = parse_record(row.get("record_json"))
            record.setdefault("edge_id", row.get("edge_id"))
            record.setdefault("src_ref", row.get("src_ref"))
            record.setdefault("dst_ref", row.get("dst_ref"))
            record.setdefault("relation", row.get("relation"))
            record.setdefault("role", row.get("role"))
            if "confidence" not in record and row.get("confidence_score") is not None:
                record["confidence"] = {"score": row.get("confidence_score")}
            records.append(record)
        return records

    def _index_edges(self) -> None:
        for edge in self.edges:
            src = edge.get("src_ref")
            dst = edge.get("dst_ref")
            relation = edge.get("relation")
            if not src or not dst:
                continue
            self.edges_by_src[src].append(edge)
            self.edges_by_dst[dst].append(edge)
            self.adjacency[src].append((dst, edge, "forward"))
            self.adjacency[dst].append((src, edge, "inverse"))
            if relation == "has_building":
                self.parcel_to_buildings[src].append(dst)
                self.building_to_parcel[dst] = src
            elif relation == "subject_of_permit":
                self.building_to_permits[src].append(dst)
                self.permit_to_building[dst] = src
            elif relation == "resolves_to":
                self.building_to_complaints[dst].append(src)
                self.event_to_building[src] = dst
            elif relation in PARTY_RELATIONS:
                role = edge.get("role") or relation
                self.permit_to_parties[src].append((dst, role, edge))
                self.party_to_permits[dst].append((src, role, edge))

    def entity_counts(self) -> dict[str, int]:
        counts = Counter(e.get("entity_type") for e in self.entities)
        return {"total": len(self.entities), **{k: int(v) for k, v in sorted(counts.items())}}

    def edge_counts(self) -> dict[str, int]:
        counts = Counter(e.get("relation") for e in self.edges)
        return {"total": len(self.edges), **{k: int(v) for k, v in sorted(counts.items())}}

    def source_counts_for_permits(self, permit_ids: list[str]) -> dict[str, int]:
        seen: set[tuple[str, str]] = set()
        counts: Counter[str] = Counter()
        for permit_id in sorted(set(permit_ids)):
            permit = self.entities_by_id.get(permit_id)
            if not permit:
                continue
            for ref in source_refs(permit):
                key = source_ref_key(ref)
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                counts[key[0]] += 1
        return {key: int(counts.get(key, 0)) for key in ("dob_permit_issuance", "dob_now_filings")}

    def complaint_resolution_counts(self, event_ids: list[str] | None = None) -> dict[str, int]:
        ids = event_ids or [
            e["canonical_id"]
            for e in self.entities
            if e.get("entity_type") == "event" and str(e.get("canonical_id", "")).startswith("event:us-nyc:dob_complaint:")
        ]
        counts: Counter[str] = Counter()
        for event_id in ids:
            event = self.entities_by_id.get(event_id) or {}
            method = (event.get("ext") or {}).get("resolution_method")
            if not method:
                edge = next((e for e in self.edges_by_src.get(event_id, []) if e.get("relation") == "resolves_to"), None)
                method = ((edge or {}).get("confidence") or {}).get("method")
            if method:
                counts[str(method)] += 1
        return {
            "exact_bin": int(counts.get("exact_bin", 0)),
            "address_fallback": int(counts.get("address_fallback", 0)),
            "spatial_fallback": int(counts.get("spatial_fallback", 0)),
        }

    def party_tier(self, party: dict[str, Any]) -> str:
        method = ((party.get("confidence") or {}).get("method") or "").lower()
        party_id = party.get("canonical_id", "")
        if method == "license_number" or ":dob_license:" in party_id:
            return "high_license_number"
        return "low_name_hash"

    def query(self, query: dict[str, Any], query_id: str, nim: dict[str, Any] | None = None) -> dict[str, Any]:
        qtype = query.get("query_type")
        if qtype == "parcel_profile":
            bundle = self.parcel_profile(query_id, query)
        elif qtype == "building_profile":
            bundle = self.building_profile(query_id, query)
        elif qtype == "complaint_search":
            bundle = self.complaint_search(query_id, query)
        elif qtype == "permit_search":
            bundle = self.permit_search(query_id, query)
        elif qtype == "party_search":
            bundle = self.party_search(query_id, query)
        elif qtype == "reachability":
            bundle = self.reachability(query_id, query)
        else:
            bundle = self.bundle(
                query_id,
                str(qtype or "unknown"),
                query,
                ["Reject unsupported query_type."],
                warnings=[f"Unsupported query_type: {qtype}"],
            )
        if nim and not nim.get("disabled"):
            self.apply_nim_narration(bundle, nim)
        return {"query_id": query_id, "query_type": qtype, "input": query, "evidence_bundle": bundle}

    def bundle(
        self,
        query_id: str,
        query_type: str,
        query_input: dict[str, Any],
        deterministic_plan: list[str],
        counts: dict[str, Any] | None = None,
        entities: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        provenance_summary: list[str] | None = None,
        confidence_summary: list[str] | None = None,
        warnings: list[str] | None = None,
        answer_facts: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entity_records = entities or []
        edge_records = edges or []
        payload = {
            "query_id": query_id,
            "query_type": query_type,
            "input": query_input,
            "deterministic_plan": deterministic_plan,
            "boundary_statement": BOUNDARY_STATEMENT,
            "counts": counts or {},
            "entities": [entity_summary(e) for e in entity_records],
            "edges": [edge_summary(e) for e in edge_records],
            "provenance_summary": provenance_summary if provenance_summary is not None else provenance_summary_for(entity_records),
            "confidence_summary": confidence_summary if confidence_summary is not None else confidence_summary_for(edge_records, entity_records),
            "warnings": warnings or [],
            "answer_facts": answer_facts or [],
            "llm_narration": {"enabled": False, "model": None, "text": None},
        }
        if extra:
            payload.update(extra)
        return payload

    def parcel_profile(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        bbl = str(query.get("bbl") or "").strip()
        parcel_id = f"parcel:us-nyc:bbl:{bbl}"
        parcel = self.entities_by_id.get(parcel_id)
        if not parcel:
            return self.bundle(
                query_id,
                "parcel_profile",
                query,
                ["Resolve BBL to canonical Parcel ID.", "Return empty evidence with warning if absent."],
                warnings=[f"Parcel not found for BBL {bbl}"],
            )
        buildings = [self.entities_by_id[b] for b in self.parcel_to_buildings.get(parcel_id, []) if b in self.entities_by_id]
        building_ids = [b["canonical_id"] for b in buildings]
        permit_ids = sorted({pid for bid in building_ids for pid in self.building_to_permits.get(bid, [])})
        permits = [self.entities_by_id[pid] for pid in permit_ids if pid in self.entities_by_id]
        complaint_ids = sorted({eid for bid in building_ids for eid in self.building_to_complaints.get(bid, [])})
        complaints = [self.entities_by_id[eid] for eid in complaint_ids if eid in self.entities_by_id]
        party_edges = [edge for pid in permit_ids for edge in self.edges_by_src.get(pid, []) if edge.get("relation") in PARTY_RELATIONS]
        party_ids = sorted({edge["dst_ref"] for edge in party_edges})
        parties = [self.entities_by_id[pid] for pid in party_ids if pid in self.entities_by_id]
        source_counts = self.source_counts_for_permits(permit_ids)
        counts = {
            "linked_buildings": len(buildings),
            "linked_permits": len(permits),
            "linked_dob_complaints": len(complaints),
            "linked_parties": len(parties),
            "source_rows": {
                "dob_permit_issuance": source_counts["dob_permit_issuance"],
                "dob_now_filings": source_counts["dob_now_filings"],
                "dob_complaints": len(complaints),
            },
        }
        edges = [
            edge
            for edge in self.edges
            if (
                (edge.get("relation") == "has_building" and edge.get("src_ref") == parcel_id)
                or (edge.get("relation") == "subject_of_permit" and edge.get("src_ref") in building_ids)
                or (edge.get("relation") == "resolves_to" and edge.get("dst_ref") in building_ids)
                or (edge.get("relation") in PARTY_RELATIONS and edge.get("src_ref") in permit_ids)
            )
        ]
        facts = [
            f"Parcel {bbl} resolves to {parcel_id}.",
            f"Linked buildings: {len(buildings)}.",
            f"DOB Permit Issuance source rows attached through permits: {source_counts['dob_permit_issuance']}.",
            f"DOB NOW filing source rows attached through permits: {source_counts['dob_now_filings']}.",
            f"DOB complaint events resolving to linked buildings: {len(complaints)}.",
            BOUNDARY_STATEMENT,
        ]
        return self.bundle(
            query_id,
            "parcel_profile",
            query,
            [
                "Resolve BBL to canonical Parcel ID.",
                "Follow has_building to Building.",
                "Follow subject_of_permit to Permit.",
                "Follow resolves_to inverse from Building to complaint Event.",
                "Follow permit party relations to Party.",
                "Count source refs deterministically from canonical Permit and Event records.",
            ],
            counts=counts,
            entities=[parcel, *buildings, *permits, *complaints, *parties],
            edges=edges,
            answer_facts=facts,
            extra={
                "parcel": entity_summary(parcel),
                "linked_buildings": [entity_summary(b) for b in buildings],
                "linked_permits": [entity_summary(p) for p in permits],
                "linked_complaints": [entity_summary(c) for c in complaints],
                "linked_parties_by_role": self.parties_by_role(party_edges),
            },
        )

    def building_profile(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        bin_value = str(query.get("bin") or "").strip()
        building_id = f"building:us-nyc:bin:{bin_value}"
        building = self.entities_by_id.get(building_id)
        if not building:
            return self.bundle(
                query_id,
                "building_profile",
                query,
                ["Resolve BIN to canonical Building ID.", "Return empty evidence with warning if absent."],
                warnings=[f"Building not found for BIN {bin_value}"],
            )
        parcel_id = self.building_to_parcel.get(building_id)
        parcel = self.entities_by_id.get(parcel_id) if parcel_id else None
        permit_ids = sorted(self.building_to_permits.get(building_id, []))
        permits = [self.entities_by_id[pid] for pid in permit_ids if pid in self.entities_by_id]
        complaint_ids = sorted(self.building_to_complaints.get(building_id, []))
        complaints = [self.entities_by_id[eid] for eid in complaint_ids if eid in self.entities_by_id]
        party_edges = [edge for pid in permit_ids for edge in self.edges_by_src.get(pid, []) if edge.get("relation") in PARTY_RELATIONS]
        party_ids = sorted({edge["dst_ref"] for edge in party_edges})
        parties = [self.entities_by_id[pid] for pid in party_ids if pid in self.entities_by_id]
        source_counts = self.source_counts_for_permits(permit_ids)
        counts = {
            "linked_permits": len(permits),
            "linked_dob_complaints": len(complaints),
            "linked_parties": len(parties),
            "source_rows": {
                "dob_permit_issuance": source_counts["dob_permit_issuance"],
                "dob_now_filings": source_counts["dob_now_filings"],
                "dob_complaints": len(complaints),
            },
        }
        edges = [
            edge
            for edge in self.edges
            if (
                (edge.get("relation") == "has_building" and edge.get("dst_ref") == building_id)
                or (edge.get("relation") == "subject_of_permit" and edge.get("src_ref") == building_id)
                or (edge.get("relation") == "resolves_to" and edge.get("dst_ref") == building_id)
                or (edge.get("relation") in PARTY_RELATIONS and edge.get("src_ref") in permit_ids)
            )
        ]
        facts = [
            f"Building {bin_value} resolves to {building_id}.",
            f"Parent parcel: {parcel_id}.",
            f"Linked permits: {len(permits)}.",
            f"Complaint events resolving to building: {len(complaints)}.",
            f"Reachable parties through permit relations: {len(parties)}.",
            BOUNDARY_STATEMENT,
        ]
        entities = [building, *permits, *complaints, *parties]
        if parcel:
            entities.insert(1, parcel)
        return self.bundle(
            query_id,
            "building_profile",
            query,
            [
                "Resolve BIN to canonical Building ID.",
                "Follow inverse has_building to Parcel.",
                "Follow subject_of_permit to Permit.",
                "Follow inverse resolves_to to complaint Event.",
                "Follow permit party relations to Party.",
            ],
            counts=counts,
            entities=entities,
            edges=edges,
            answer_facts=facts,
            extra={
                "building": entity_summary(building),
                "parent_parcel": entity_summary(parcel) if parcel else None,
                "linked_permits": [entity_summary(p) for p in permits],
                "linked_complaints": [entity_summary(c) for c in complaints],
                "linked_parties_by_role": self.parties_by_role(party_edges),
            },
        )

    def complaint_search(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        canonical_type = query.get("canonical_type")
        resolution_method = query.get("resolution_method")
        events: list[dict[str, Any]] = []
        for entity in self.entities:
            if entity.get("entity_type") != "event" or not str(entity.get("canonical_id", "")).startswith("event:us-nyc:dob_complaint:"):
                continue
            if canonical_type and entity.get("type") != canonical_type:
                continue
            method = (entity.get("ext") or {}).get("resolution_method")
            if resolution_method and method != resolution_method:
                continue
            events.append(entity)
        event_ids = [e["canonical_id"] for e in events]
        building_ids = sorted({self.event_to_building[eid] for eid in event_ids if eid in self.event_to_building})
        buildings = [self.entities_by_id[bid] for bid in building_ids if bid in self.entities_by_id]
        parcel_ids = sorted({self.building_to_parcel.get(bid) for bid in building_ids if self.building_to_parcel.get(bid)})
        parcels = [self.entities_by_id[pid] for pid in parcel_ids if pid in self.entities_by_id]
        permit_ids = sorted({pid for bid in building_ids for pid in self.building_to_permits.get(bid, [])})
        permits = [self.entities_by_id[pid] for pid in permit_ids if pid in self.entities_by_id]
        edge_ids = set(event_ids) | set(building_ids) | set(permit_ids) | set(parcel_ids)
        edges = [
            edge
            for edge in self.edges
            if edge.get("src_ref") in edge_ids and edge.get("dst_ref") in edge_ids
        ]
        counts = {
            "matching_complaints": len(events),
            "resolved_buildings": len(buildings),
            "parcel_contexts": len(parcels),
            "reachable_permits": len(permits),
            "resolution_method_counts": self.complaint_resolution_counts(event_ids),
            "legacy_slug_absent": self.legacy_slug_absent([*events, *edges]),
        }
        facts = [
            f"Complaint search matched {len(events)} DOB complaint events.",
            f"Resolution methods in result: {counts['resolution_method_counts']}.",
            f"Resolved building contexts: {len(buildings)}.",
            f"Reachable permit contexts: {len(permits)}.",
            BOUNDARY_STATEMENT,
        ]
        return self.bundle(
            query_id,
            "complaint_search",
            query,
            [
                "Filter canonical Event entities carrying DOB complaint IDs.",
                "Apply canonical type and/or resolution method filters.",
                "Follow resolves_to to Building.",
                "Follow inverse has_building to Parcel and subject_of_permit to related Permit context.",
            ],
            counts=counts,
            entities=[*events, *buildings, *parcels, *permits],
            edges=edges,
            answer_facts=facts,
            extra={
                "matching_complaint_events": [entity_summary(e) for e in events],
                "resolved_buildings": [entity_summary(b) for b in buildings],
                "parcel_context": [entity_summary(p) for p in parcels],
                "related_permits": [entity_summary(p) for p in permits],
            },
        )

    def permit_search(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        target = normalize_dataset(query.get("source_dataset"))
        permits: list[dict[str, Any]] = []
        matching_refs: list[tuple[str, str]] = []
        all_refs: list[tuple[str, str]] = []
        for entity in self.entities:
            if entity.get("entity_type") != "permit":
                continue
            refs = [source_ref_key(ref) for ref in source_refs(entity)]
            all_refs.extend(refs)
            if not target or any(dataset == target for dataset, _ in refs):
                permits.append(entity)
                matching_refs.extend(ref for ref in refs if not target or ref[0] == target)
        permit_ids = [p["canonical_id"] for p in permits]
        building_ids = sorted({self.permit_to_building.get(pid) for pid in permit_ids if self.permit_to_building.get(pid)})
        buildings = [self.entities_by_id[bid] for bid in building_ids if bid in self.entities_by_id]
        parcel_ids = sorted({self.building_to_parcel.get(bid) for bid in building_ids if self.building_to_parcel.get(bid)})
        parcels = [self.entities_by_id[pid] for pid in parcel_ids if pid in self.entities_by_id]
        party_edges = [edge for pid in permit_ids for edge in self.edges_by_src.get(pid, []) if edge.get("relation") in PARTY_RELATIONS]
        party_ids = sorted({edge["dst_ref"] for edge in party_edges})
        parties = [self.entities_by_id[pid] for pid in party_ids if pid in self.entities_by_id]
        grouping = Counter(dataset for dataset, row_key in set(all_refs) if dataset)
        matching_count = len({ref for ref in matching_refs if ref[0]})
        counts = {
            "matching_permits": len(permits),
            "matching_attached_source_rows": matching_count,
            "source_provenance_grouping": {key: int(grouping.get(key, 0)) for key in ("dob_permit_issuance", "dob_now_filings")},
            "unique_merged_permit_entities": len([e for e in self.entities if e.get("entity_type") == "permit"]),
        }
        edges = [
            edge
            for edge in self.edges
            if (
                (edge.get("relation") == "subject_of_permit" and edge.get("dst_ref") in permit_ids)
                or (edge.get("relation") in PARTY_RELATIONS and edge.get("src_ref") in permit_ids)
                or (edge.get("relation") == "has_building" and edge.get("dst_ref") in building_ids)
            )
        ]
        facts = [
            f"Permit search target source dataset: {target or 'all DOB permit sources'}.",
            f"Matching Permit entities: {len(permits)}.",
            f"Attached source rows for target: {matching_count}.",
            f"All unique merged Permit entities in district: {counts['unique_merged_permit_entities']}.",
            BOUNDARY_STATEMENT,
        ]
        return self.bundle(
            query_id,
            "permit_search",
            query,
            [
                "Filter canonical Permit entities by normalized source refs.",
                "Group contributing source refs by source dataset.",
                "Follow inverse subject_of_permit to Building and inverse has_building to Parcel.",
                "Follow permit party relations to Party.",
            ],
            counts=counts,
            entities=[*permits, *buildings, *parcels, *parties],
            edges=edges,
            answer_facts=facts,
            extra={
                "matching_permits": [entity_summary(p) for p in permits],
                "building_context": [entity_summary(b) for b in buildings],
                "parcel_context": [entity_summary(p) for p in parcels],
                "parties_by_role": self.parties_by_role(party_edges),
            },
        )

    def party_search(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        tier = query.get("confidence_tier")
        parties = [
            entity
            for entity in self.entities
            if entity.get("entity_type") == "party" and (not tier or self.party_tier(entity) == tier)
        ]
        party_ids = [p["canonical_id"] for p in parties]
        permit_links = [
            (party_id, permit_id, role, edge)
            for party_id in party_ids
            for permit_id, role, edge in self.party_to_permits.get(party_id, [])
        ]
        permit_ids = sorted({permit_id for _, permit_id, _, _ in permit_links})
        permits = [self.entities_by_id[pid] for pid in permit_ids if pid in self.entities_by_id]
        building_ids = sorted({self.permit_to_building.get(pid) for pid in permit_ids if self.permit_to_building.get(pid)})
        buildings = [self.entities_by_id[bid] for bid in building_ids if bid in self.entities_by_id]
        parcel_ids = sorted({self.building_to_parcel.get(bid) for bid in building_ids if self.building_to_parcel.get(bid)})
        parcels = [self.entities_by_id[pid] for pid in parcel_ids if pid in self.entities_by_id]
        role_counts = Counter(role for _, _, role, _ in permit_links)
        tier_counts = Counter(self.party_tier(entity) for entity in self.entities if entity.get("entity_type") == "party")
        edges = [edge for _, _, _, edge in permit_links]
        counts = {
            "matching_parties": len(parties),
            "roles_found": {key: int(value) for key, value in sorted(role_counts.items())},
            "linked_permits": len(permits),
            "linked_buildings": len(buildings),
            "linked_parcels": len(parcels),
            "party_confidence_tiers": {key: int(tier_counts.get(key, 0)) for key in ("high_license_number", "low_name_hash")},
        }
        policy = {
            "high_license_number": "strong key",
            "low_name_hash": "lower-confidence source-derived party identity",
        }
        facts = [
            f"Party search tier: {tier or 'all'}.",
            f"Matching parties: {len(parties)}.",
            f"High-confidence license-number parties in district: {counts['party_confidence_tiers']['high_license_number']}.",
            f"Low-confidence name-hash parties in district: {counts['party_confidence_tiers']['low_name_hash']}.",
            "Policy: high_license_number is a strong key; low_name_hash is a lower-confidence source-derived party identity.",
            BOUNDARY_STATEMENT,
        ]
        return self.bundle(
            query_id,
            "party_search",
            query,
            [
                "Filter canonical Party entities by uniform confidence tier policy.",
                "Follow incoming permit party relations to Permit.",
                "Follow inverse subject_of_permit to Building and inverse has_building to Parcel.",
            ],
            counts=counts,
            entities=[*parties, *permits, *buildings, *parcels],
            edges=edges,
            answer_facts=facts,
            extra={
                "party_confidence_policy": policy,
                "matching_parties": [entity_summary(p) for p in parties],
                "linked_permits": [entity_summary(p) for p in permits],
                "linked_buildings": [entity_summary(b) for b in buildings],
                "linked_parcels": [entity_summary(p) for p in parcels],
            },
        )

    def reachability(self, query_id: str, query: dict[str, Any]) -> dict[str, Any]:
        start = query.get("start_ref")
        target_types = set(query.get("target_types") or [])
        max_depth = int(query.get("max_depth") or 4)
        paths = self.bfs_paths(start, target_types, max_depth)
        composite = self.hero_composite_path(start)
        reached_types = sorted({path["target_type"] for path in paths})
        edges_by_id = {edge.get("edge_id"): edge for edge in self.edges}
        path_edges: list[dict[str, Any]] = []
        for path in paths:
            for item in path.get("edges", []):
                edge = edges_by_id.get(item.get("edge_id"))
                if edge:
                    path_edges.append(edge)
        composite_edges = [step["edge"] for step in composite.get("steps", []) if step.get("edge")]
        entity_ids = {start}
        for path in paths:
            entity_ids.update(path.get("nodes", []))
        entity_ids.update(composite.get("nodes", []))
        entities = [self.entities_by_id[eid] for eid in sorted(entity_ids) if eid in self.entities_by_id]
        counts = {
            "paths_found": len(paths),
            "reached_entity_types": reached_types,
            "hero_composite_path_found": bool(composite.get("steps")),
            "hero_relation_sequence": composite.get("relation_sequence", []),
        }
        facts = [
            f"Reachability start: {start}.",
            f"Target types reached within depth {max_depth}: {reached_types}.",
            f"Hero composite relation sequence: {composite.get('relation_sequence', [])}.",
            BOUNDARY_STATEMENT,
        ]
        return self.bundle(
            query_id,
            "reachability",
            query,
            [
                "Run deterministic breadth-first traversal over canonical graph edges.",
                "Traverse both forward and inverse edge directions while preserving canonical relation names.",
                "Emit confidence-bearing edge provenance from the canonical edge records.",
            ],
            counts=counts,
            entities=entities,
            edges=[*path_edges, *composite_edges],
            answer_facts=facts,
            extra={
                "paths": paths,
                "hero_composite_path": {
                    "nodes": composite.get("nodes", []),
                    "relation_sequence": composite.get("relation_sequence", []),
                    "steps": [
                        {
                            "from": step.get("from"),
                            "to": step.get("to"),
                            "relation": step.get("relation"),
                            "direction": step.get("direction"),
                            "edge": edge_summary(step["edge"], step.get("direction")) if step.get("edge") else None,
                        }
                        for step in composite.get("steps", [])
                    ],
                },
            },
        )

    def bfs_paths(self, start: str, target_types: set[str], max_depth: int) -> list[dict[str, Any]]:
        if start not in self.entities_by_id:
            return []
        found: dict[str, dict[str, Any]] = {}
        queue = deque([(start, [start], [])])
        visited = {(start, 0)}
        while queue:
            node, nodes, edge_path = queue.popleft()
            depth = len(edge_path)
            node_type = (self.entities_by_id.get(node) or {}).get("entity_type")
            if node != start and (not target_types or node_type in target_types) and node_type not in found:
                found[node_type] = {
                    "target": node,
                    "target_type": node_type,
                    "length": depth,
                    "nodes": nodes,
                    "edge_relation_sequence": [step["relation"] for step in edge_path],
                    "edges": edge_path,
                }
            if depth >= max_depth:
                continue
            for nxt, edge, direction in self.adjacency.get(node, []):
                state = (nxt, depth + 1)
                if state in visited:
                    continue
                visited.add(state)
                edge_step = {
                    "edge_id": edge.get("edge_id"),
                    "from": node,
                    "to": nxt,
                    "relation": edge.get("relation"),
                    "direction": direction,
                    "confidence": edge.get("confidence"),
                }
                queue.append((nxt, [*nodes, nxt], [*edge_path, edge_step]))
        return list(found.values())

    def hero_composite_path(self, start: str | None) -> dict[str, Any]:
        if start != HERO_COMPLAINT_ID:
            return {"nodes": [], "relation_sequence": [], "steps": []}
        building_id = self.event_to_building.get(start)
        if not building_id:
            return {"nodes": [], "relation_sequence": [], "steps": []}
        permits = self.building_to_permits.get(building_id, [])
        selected_permit = None
        selected_party = None
        selected_party_edge = None
        for permit_id in permits:
            party_edges = [item for item in self.permit_to_parties.get(permit_id, []) if item[1] == "contractor"]
            if not party_edges:
                party_edges = self.permit_to_parties.get(permit_id, [])
            if party_edges:
                selected_permit = permit_id
                selected_party, _, selected_party_edge = party_edges[0]
                break
        if not selected_permit and permits:
            selected_permit = permits[0]
        parcel_id = self.building_to_parcel.get(building_id)
        resolves_edge = next((e for e in self.edges_by_src.get(start, []) if e.get("relation") == "resolves_to"), None)
        permit_edge = next(
            (
                e
                for e in self.edges_by_src.get(building_id, [])
                if e.get("relation") == "subject_of_permit" and e.get("dst_ref") == selected_permit
            ),
            None,
        )
        building_edge = next(
            (
                e
                for e in self.edges_by_src.get(parcel_id, [])
                if e.get("relation") == "has_building" and e.get("dst_ref") == building_id
            ),
            None,
        )
        steps = []
        if resolves_edge:
            steps.append({"from": start, "to": building_id, "relation": "resolves_to", "direction": "forward", "edge": resolves_edge})
        if permit_edge:
            steps.append({"from": building_id, "to": selected_permit, "relation": "subject_of_permit", "direction": "forward", "edge": permit_edge})
        if selected_party_edge and selected_party:
            steps.append(
                {
                    "from": selected_permit,
                    "to": selected_party,
                    "relation": selected_party_edge.get("relation"),
                    "direction": "forward",
                    "edge": selected_party_edge,
                }
            )
        if building_edge and parcel_id:
            steps.append({"from": building_id, "to": parcel_id, "relation": "has_building", "direction": "inverse", "edge": building_edge})
        nodes = [node for node in (start, building_id, selected_permit, selected_party, parcel_id) if node]
        return {
            "nodes": nodes,
            "relation_sequence": [step["relation"] for step in steps],
            "steps": steps,
        }

    def parties_by_role(self, edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in edges:
            party = self.entities_by_id.get(edge.get("dst_ref"))
            if not party:
                continue
            role = edge.get("role") or edge.get("relation")
            grouped[role].append({"party": entity_summary(party), "edge": edge_summary(edge)})
        return {key: value for key, value in sorted(grouped.items())}

    def legacy_slug_absent(self, records: list[dict[str, Any]]) -> bool:
        return LEGACY_COMPLAINT_SLUG not in json.dumps(records, sort_keys=True)

    def apply_nim_narration(self, bundle: dict[str, Any], nim: dict[str, Any]) -> None:
        endpoint = (nim.get("endpoint") or "").strip()
        model = (nim.get("model") or "").strip()
        if not endpoint or not model:
            bundle["warnings"].append("NIM narration requested but endpoint/model was incomplete; deterministic answer retained.")
            return
        url = endpoint.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = f"{url}/v1/chat/completions"
        facts = "\n".join(f"- {fact}" for fact in bundle.get("answer_facts", []))
        request_payload = {
            "model": model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Narrate only from the provided deterministic facts. Do not add counts, sources, or claims.",
                },
                {"role": "user", "content": facts},
            ],
        }
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(request_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            text = payload["choices"][0]["message"]["content"]
            bundle["llm_narration"] = {"enabled": True, "model": model, "text": text}
        except (urllib.error.URLError, KeyError, IndexError, TimeoutError, ValueError) as exc:
            bundle["warnings"].append(f"NIM narration failed; deterministic answer retained: {exc}")


def sample_queries() -> list[dict[str, Any]]:
    return [
        {"query_type": "parcel_profile", "bbl": HERO_BBL},
        {"query_type": "building_profile", "bin": HERO_BIN},
        {"query_type": "complaint_search", "canonical_type": CANONICAL_CODE_91_TYPE},
        {"query_type": "complaint_search", "resolution_method": "exact_bin"},
        {"query_type": "permit_search", "source_dataset": "dob_now_filings"},
        {"query_type": "permit_search", "source_dataset": "dob_permit_issuance"},
        {"query_type": "party_search", "confidence_tier": "high_license_number"},
        {"query_type": "party_search", "confidence_tier": "low_name_hash"},
        {
            "query_type": "reachability",
            "start_ref": HERO_COMPLAINT_ID,
            "target_types": ["building", "permit", "party", "parcel"],
            "max_depth": 4,
        },
    ]


def query_catalog() -> dict[str, Any]:
    return {
        "task": TASK_LABEL,
        "spine_naming": {
            "a5": SPINE_LABEL,
            "input": INPUT_LABEL,
            "operator_query_slice": "A5-D1 / a5·D1",
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "truth_policy": "Counts and graph facts are computed by deterministic retrieval over canonical a4·D2 artifacts.",
        "queries": [
            {
                "query_type": "parcel_profile",
                "inputs": ["bbl"],
                "plan": ["Parcel by canonical BBL ID", "has_building", "subject_of_permit", "resolves_to inverse", "permit party edges"],
            },
            {
                "query_type": "building_profile",
                "inputs": ["bin"],
                "plan": ["Building by canonical BIN ID", "has_building inverse", "subject_of_permit", "resolves_to inverse", "permit party edges"],
            },
            {
                "query_type": "complaint_search",
                "inputs": ["canonical_type", "resolution_method"],
                "plan": ["Filter canonical DOB complaint Events", "resolves_to Building", "Parcel and Permit context"],
            },
            {
                "query_type": "permit_search",
                "inputs": ["source_dataset"],
                "plan": ["Filter canonical Permits by source refs", "group provenance", "Building/Parcel/Party context"],
            },
            {
                "query_type": "party_search",
                "inputs": ["confidence_tier"],
                "plan": ["Filter Party by uniform policy", "Permit/Building/Parcel reachability"],
            },
            {
                "query_type": "reachability",
                "inputs": ["start_ref", "target_types", "max_depth"],
                "plan": ["BFS over canonical edges", "preserve relation names", "preserve confidence-bearing edge provenance"],
            },
        ],
    }


def load_optional_queries(path: Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    payload = read_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("queries"), list):
        return payload["queries"]
    raise ValueError(f"Query file must contain a list or a dict with queries[]: {path}")


def build_readme(report: dict[str, Any], summary: dict[str, Any], output_dir: Path) -> str:
    gates = report.get("gates", [])
    status = report.get("status", "FAIL")
    key_checks = report.get("key_query_checks", {})
    return "\n".join(
        [
            "# A5-D1 Operator Query",
            "",
            BOUNDARY_STATEMENT,
            "",
            "## Naming",
            "",
            f"- {SPINE_LABEL}.",
            f"- {INPUT_LABEL}, consumed here as frozen canonical input.",
            "- A5-D1 / a5·D1 is the operator-query slice over the enriched district graph.",
            "",
            "## Status",
            "",
            f"- A5-D1 status: {status}",
            f"- A4-D2 status consumed: {report.get('a4_d2_status_consumed')}",
            f"- A2 preflight consumed: {report.get('a2_preflight_consumed')}",
            f"- A4 regression consumed: {report.get('a4_regression_consumed')}",
            f"- Output directory: {output_dir.as_posix()}",
            "",
            "## District Counts",
            "",
            f"- Entities: {summary.get('entity_counts_by_type', {})}",
            f"- Edges: {summary.get('edge_counts_by_relation', {})}",
            f"- Attached source rows after dedupe: {summary.get('attached_source_rows_after_dedupe', {})}",
            "",
            "## Key Query Checks",
            "",
            *[f"- {name}: {'PASS' if passed else 'FAIL'}" for name, passed in key_checks.items()],
            "",
            "## Gates",
            "",
            *[f"- {gate['gate_id']}: {'PASS' if gate['passed'] else 'FAIL'}" for gate in gates],
            "",
            "## Known Limitations",
            "",
            "- This is a deterministic operator-query read-model, not a generic chatbot.",
            "- The optional NIM layer is narration only; it does not compute counts or graph facts.",
            "- Results are bounded to the current harvested district subset.",
            "",
            "## Next Recommended Fold-In",
            "",
            "- Exercise the action-core policy layer against these evidence bundles, then decide which operator actions need external systems.",
            "",
        ]
    )


def build_hero_briefing(
    parcel_result: dict[str, Any],
    building_result: dict[str, Any],
    reachability_result: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    parcel_bundle = parcel_result["evidence_bundle"]
    building_bundle = building_result["evidence_bundle"]
    reach_bundle = reachability_result["evidence_bundle"]
    briefing = {
        "task": TASK_LABEL,
        "briefing_id": "hero_operator_briefing",
        "boundary_statement": BOUNDARY_STATEMENT,
        "subject": {
            "parcel": HERO_PARCEL_ID,
            "building": HERO_BUILDING_ID,
            "complaint": HERO_COMPLAINT_ID,
        },
        "questions_answered": {
            "what_is_this_parcel_building": [
                *parcel_bundle.get("answer_facts", [])[:2],
                *building_bundle.get("answer_facts", [])[:2],
            ],
            "dob_activity_attached": parcel_bundle.get("counts", {}).get("source_rows", {}),
            "complaints_resolved_to_building": building_bundle.get("counts", {}).get("linked_dob_complaints"),
            "permits_and_parties_connected": {
                "permits": building_bundle.get("counts", {}).get("linked_permits"),
                "parties": building_bundle.get("counts", {}).get("linked_parties"),
            },
            "strongest_evidence_path": reach_bundle.get("hero_composite_path", {}),
            "confidence_provenance_boundary": {
                "boundary_statement": BOUNDARY_STATEMENT,
                "confidence_summary": reach_bundle.get("confidence_summary", []),
                "provenance_summary": reach_bundle.get("provenance_summary", []),
            },
            "operator_review_next": [
                "Review the exact-BIN complaint evidence for the hero building.",
                "Review the permit party roles connected through subject_of_permit and performed_by/involves_party edges.",
                "Treat all counts as subset counts until a full DOB harvest is run.",
            ],
        },
        "evidence_bundle_refs": [
            parcel_result["query_id"],
            building_result["query_id"],
            reachability_result["query_id"],
        ],
    }
    counts = parcel_bundle.get("counts", {}).get("source_rows", {})
    path = reach_bundle.get("hero_composite_path", {})
    markdown = "\n".join(
        [
            "# A5-D1 Hero Operator Briefing",
            "",
            BOUNDARY_STATEMENT,
            "",
            f"Parcel: `{HERO_PARCEL_ID}`",
            f"Building: `{HERO_BUILDING_ID}`",
            f"Hero complaint: `{HERO_COMPLAINT_ID}`",
            "",
            "## What This Is",
            "",
            f"- Parcel `{HERO_BBL}` resolves to `{HERO_PARCEL_ID}`.",
            f"- Building `{HERO_BIN}` resolves to `{HERO_BUILDING_ID}` and is linked to the parcel.",
            "",
            "## DOB Activity",
            "",
            f"- DOB Permit Issuance source rows: {counts.get('dob_permit_issuance')}",
            f"- DOB NOW filing source rows: {counts.get('dob_now_filings')}",
            f"- DOB complaint events: {counts.get('dob_complaints')}",
            "",
            "## Strongest Evidence Path",
            "",
            f"- Relation sequence: {path.get('relation_sequence', [])}",
            f"- Nodes: {path.get('nodes', [])}",
            "",
            "## Confidence And Provenance Boundary",
            "",
            f"- Confidence: {reach_bundle.get('confidence_summary', [])}",
            f"- Provenance: {reach_bundle.get('provenance_summary', [])}",
            "",
            "## Operator Review Next",
            "",
            "- Review the exact-BIN complaint evidence for the hero building.",
            "- Review connected permit parties and roles before turning this into an action.",
            "- Keep the subset boundary visible in any downstream operator-facing view.",
            "",
        ]
    )
    return briefing, markdown


def gate_result(gate_id: str, name: str, passed: bool, details: list[str] | None = None, checked: int = 1) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "name": name,
        "passed": bool(passed),
        "checked": checked,
        "failed": 0 if passed else 1,
        "details": details or [],
    }


def output_texts(output_dir: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".md"}:
            try:
                texts[path.relative_to(output_dir).as_posix()] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
    return texts


def run_gates(
    input_dir: Path,
    output_dir: Path,
    graph: DistrictGraph,
    input_hashes_before: dict[str, str],
    input_hashes_after: dict[str, str],
    harness_report: dict[str, Any],
    input_summary: dict[str, Any],
    query_results: list[dict[str, Any]],
    hero_briefing: dict[str, Any],
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    harness_text = json.dumps(harness_report)
    input_boundary_sources = [
        harness_text,
        json.dumps(input_summary),
        (input_dir / "README.md").read_text(encoding="utf-8") if (input_dir / "README.md").exists() else "",
        (input_dir / "district_cut_manifest.json").read_text(encoding="utf-8")
        if (input_dir / "district_cut_manifest.json").exists()
        else "",
    ]
    precond_passed = (
        input_dir.exists()
        and (input_dir / "harness_report_a5.json").exists()
        and harness_report.get("a5_status") == "PASS"
        and harness_report.get("a2_preflight_status") == "PASS"
        and harness_report.get("a4_regression_status") == "PASS"
        and any(BOUNDARY_STATEMENT in source for source in input_boundary_sources)
    )
    gates.append(
        gate_result(
            "A5D1-PRECOND",
            "Frozen a4·D2 input is green and bounded",
            precond_passed,
            [] if precond_passed else ["input directory, green statuses, or subset boundary was missing"],
        )
    )

    entity_counts = graph.entity_counts()
    edge_counts = graph.edge_counts()
    load_passed = (
        all(entity_counts.get(key) == value for key, value in EXPECTED_ENTITY_COUNTS.items())
        and all(edge_counts.get(key) == value for key, value in EXPECTED_EDGE_COUNTS.items())
        and len(graph.projection_nodes_df) == EXPECTED_ENTITY_COUNTS["total"]
        and len(graph.projection_edges_df) == EXPECTED_EDGE_COUNTS["total"]
    )
    gates.append(
        gate_result(
            "A5D1-LOAD",
            "Canonical and projection artifacts load with expected counts",
            load_passed,
            [] if load_passed else [f"entities={entity_counts}", f"edges={edge_counts}"],
            checked=4,
        )
    )

    texts = output_texts(output_dir)
    combined_text = "\n".join(texts.values())
    bad_naming_phrases = [
        "A5 " + "DOB enrichment",
        "DOB enrichment is " + "A5",
        "DOB district enrichment is " + "A5",
        "A6 " + "operator query",
        "operator query is " + "A6",
    ]
    naming_passed = (
        not any(phrase in combined_text for phrase in bad_naming_phrases)
        and ("A5-D1" in combined_text or "a5·D1" in combined_text)
        and SPINE_LABEL in combined_text
        and INPUT_LABEL in combined_text
    )
    gates.append(
        gate_result(
            "A5D1-NAMING",
            "Mission Control naming remains unambiguous",
            naming_passed,
            [] if naming_passed else ["naming text missing or collision phrase found"],
        )
    )

    boundary_required = [
        "README.md",
        "a5d1_manifest.json",
        "a5d1_harness_report.json",
        "sample_query_results.json",
        "hero_operator_briefing.json",
        "hero_operator_briefing.md",
    ]
    evidence_files = sorted((output_dir / "evidence_bundles").glob("*.json"))
    boundary_missing = [
        rel
        for rel in boundary_required
        if rel not in texts or BOUNDARY_STATEMENT not in texts[rel]
    ]
    boundary_missing.extend(
        f"evidence_bundles/{path.name}" for path in evidence_files if BOUNDARY_STATEMENT not in path.read_text(encoding="utf-8")
    )
    gates.append(
        gate_result(
            "A5D1-BOUNDARY",
            "Subset boundary appears in every human-facing/count artifact",
            not boundary_missing,
            boundary_missing,
            checked=len(boundary_required) + len(evidence_files),
        )
    )

    by_type = {result["query_type"]: [] for result in query_results}
    for result in query_results:
        by_type.setdefault(result["query_type"], []).append(result)
    parcel_bundle = by_type["parcel_profile"][0]["evidence_bundle"]
    parcel_counts = parcel_bundle.get("counts", {})
    parcel_source = parcel_counts.get("source_rows", {})
    parcel_passed = (
        parcel_bundle.get("parcel", {}).get("canonical_id") == HERO_PARCEL_ID
        and any(b.get("canonical_id") == HERO_BUILDING_ID for b in parcel_bundle.get("linked_buildings", []))
        and parcel_source.get("dob_permit_issuance") == 1
        and parcel_source.get("dob_now_filings") == 12
        and parcel_source.get("dob_complaints") == 9
        and BOUNDARY_STATEMENT in parcel_bundle.get("boundary_statement", "")
    )
    gates.append(
        gate_result(
            "A5D1-PARCEL-PROFILE",
            "Hero parcel profile resolves expected source-row counts",
            parcel_passed,
            [] if parcel_passed else [f"counts={parcel_counts}"],
        )
    )

    building_bundle = by_type["building_profile"][0]["evidence_bundle"]
    building_passed = (
        building_bundle.get("building", {}).get("canonical_id") == HERO_BUILDING_ID
        and (building_bundle.get("parent_parcel") or {}).get("canonical_id") == HERO_PARCEL_ID
        and building_bundle.get("counts", {}).get("linked_permits", 0) > 0
        and building_bundle.get("counts", {}).get("linked_dob_complaints", 0) > 0
        and building_bundle.get("counts", {}).get("linked_parties", 0) > 0
    )
    gates.append(
        gate_result(
            "A5D1-BUILDING-PROFILE",
            "Hero building profile reaches parcel, permits, complaints, and parties",
            building_passed,
            [] if building_passed else [f"counts={building_bundle.get('counts', {})}"],
        )
    )

    complaint_bundles = [result["evidence_bundle"] for result in by_type.get("complaint_search", [])]
    type_bundle = next((b for b in complaint_bundles if b.get("input", {}).get("canonical_type") == CANONICAL_CODE_91_TYPE), {})
    method_bundle = next((b for b in complaint_bundles if b.get("input", {}).get("resolution_method") == "exact_bin"), {})
    complaint_passed = (
        type_bundle.get("counts", {}).get("matching_complaints", 0) >= 1
        and method_bundle.get("counts", {}).get("resolution_method_counts", {}).get("exact_bin") == EXPECTED_SOURCE_ROWS["dob_complaints"]
        and LEGACY_COMPLAINT_SLUG not in combined_text
    )
    gates.append(
        gate_result(
            "A5D1-COMPLAINT-SEARCH",
            "Complaint filters use canonical category and exact-BIN resolution",
            complaint_passed,
            [] if complaint_passed else ["canonical complaint type, exact-BIN count, or legacy slug check failed"],
        )
    )

    permit_bundles = [result["evidence_bundle"] for result in by_type.get("permit_search", [])]
    now_bundle = next((b for b in permit_bundles if normalize_dataset(b.get("input", {}).get("source_dataset")) == "dob_now_filings"), {})
    issuance_bundle = next((b for b in permit_bundles if normalize_dataset(b.get("input", {}).get("source_dataset")) == "dob_permit_issuance"), {})
    permit_passed = (
        now_bundle.get("counts", {}).get("matching_attached_source_rows") == EXPECTED_SOURCE_ROWS["dob_now_filings"]
        and issuance_bundle.get("counts", {}).get("matching_attached_source_rows") == EXPECTED_SOURCE_ROWS["dob_permit_issuance"]
        and now_bundle.get("counts", {}).get("unique_merged_permit_entities") == EXPECTED_ENTITY_COUNTS["permit"]
        and issuance_bundle.get("counts", {}).get("unique_merged_permit_entities") == EXPECTED_ENTITY_COUNTS["permit"]
    )
    gates.append(
        gate_result(
            "A5D1-PERMIT-SEARCH",
            "Permit search distinguishes source rows from merged permit entities",
            permit_passed,
            [] if permit_passed else [f"now={now_bundle.get('counts', {})}", f"issuance={issuance_bundle.get('counts', {})}"],
        )
    )

    party_bundles = [result["evidence_bundle"] for result in by_type.get("party_search", [])]
    high_bundle = next((b for b in party_bundles if b.get("input", {}).get("confidence_tier") == "high_license_number"), {})
    low_bundle = next((b for b in party_bundles if b.get("input", {}).get("confidence_tier") == "low_name_hash"), {})
    party_passed = (
        high_bundle.get("counts", {}).get("matching_parties") == EXPECTED_PARTY_TIERS["high_license_number"]
        and low_bundle.get("counts", {}).get("matching_parties") == EXPECTED_PARTY_TIERS["low_name_hash"]
        and "strong key" in json.dumps(high_bundle)
        and "lower-confidence source-derived party identity" in json.dumps(low_bundle)
    )
    gates.append(
        gate_result(
            "A5D1-PARTY-CONFIDENCE",
            "Party search preserves license/name-hash confidence tiers",
            party_passed,
            [] if party_passed else [f"high={high_bundle.get('counts', {})}", f"low={low_bundle.get('counts', {})}"],
        )
    )

    reach_bundle = by_type["reachability"][0]["evidence_bundle"]
    sequence = reach_bundle.get("hero_composite_path", {}).get("relation_sequence", [])
    reach_passed = (
        HERO_COMPLAINT_ID in reach_bundle.get("hero_composite_path", {}).get("nodes", [])
        and HERO_BUILDING_ID in reach_bundle.get("hero_composite_path", {}).get("nodes", [])
        and "resolves_to" in sequence
        and "subject_of_permit" in sequence
        and any(rel in sequence for rel in ("performed_by", "involves_party"))
        and "has_building" in sequence
    )
    gates.append(
        gate_result(
            "A5D1-REACHABILITY",
            "Hero complaint reaches building, permit, party, and parcel",
            reach_passed,
            [] if reach_passed else [f"sequence={sequence}"],
        )
    )

    nim_passed = all(
        isinstance(result["evidence_bundle"].get("answer_facts"), list)
        and "llm_narration" in result["evidence_bundle"]
        for result in query_results
    )
    gates.append(
        gate_result(
            "A5D1-NIM-OPTIONAL",
            "Default deterministic run succeeds without NIM",
            nim_passed,
            [] if nim_passed else ["one or more evidence bundles lacks deterministic facts or narration envelope"],
        )
    )

    no_mutation_passed = input_hashes_before == input_hashes_after
    gates.append(
        gate_result(
            "A5D1-NO-MUTATION",
            "Frozen a4·D2 input artifacts remain byte-stable",
            no_mutation_passed,
            [] if no_mutation_passed else ["input artifact hash changed during A5-D1 run"],
            checked=len(input_hashes_before),
        )
    )
    return gates


def write_output_hashes(output_dir: Path) -> None:
    hashes = {}
    for path in sorted(p for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"):
        hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(
        output_dir / "SHA256SUMS.json",
        {
            "task": TASK_LABEL,
            "boundary_statement": BOUNDARY_STATEMENT,
            "generated_at": utc_now(),
            "hashes": hashes,
        },
    )


def run_a5d1(
    input_dir: Path,
    output_dir: Path,
    query_file: Path | None = None,
    nim: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    input_hashes_before = hash_tree(input_dir)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "evidence_bundles").mkdir(parents=True, exist_ok=True)
    (output_dir / "scenario_traces").mkdir(parents=True, exist_ok=True)

    harness_report = read_json(input_dir / "harness_report_a5.json")
    input_summary = read_json(input_dir / "a5_enrichment_summary.json")
    graph = DistrictGraph(input_dir)

    queries = sample_queries() + load_optional_queries(query_file)
    query_results: list[dict[str, Any]] = []
    for index, query in enumerate(queries, start=1):
        query_id = stable_query_id(index, query)
        result = graph.query(query, query_id, nim=nim)
        query_results.append(result)
        write_json(output_dir / "evidence_bundles" / f"{query_id}.json", result["evidence_bundle"])

    parcel_result = next(r for r in query_results if r["query_type"] == "parcel_profile")
    building_result = next(r for r in query_results if r["query_type"] == "building_profile")
    reachability_result = next(r for r in query_results if r["query_type"] == "reachability")
    hero_briefing, hero_markdown = build_hero_briefing(parcel_result, building_result, reachability_result)

    manifest = {
        "task": TASK_LABEL,
        "operator_query_slice": "A5-D1 / a5·D1",
        "spine_naming": {
            "a5": SPINE_LABEL,
            "input": INPUT_LABEL,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "input_snapshot": "a5_district_v1",
        "input_artifact_semantic_label": "a4·D2 DOB district enrichment",
        "input_directory": input_dir.as_posix(),
        "output_directory": output_dir.as_posix(),
        "generated_at": utc_now(),
        "input_file_hashes_before": input_hashes_before,
        "query_ids": [result["query_id"] for result in query_results],
        "required_artifacts": [
            "README.md",
            "a5d1_manifest.json",
            "a5d1_harness_report.json",
            "query_catalog.json",
            "sample_queries.json",
            "sample_query_results.json",
            "hero_operator_briefing.json",
            "hero_operator_briefing.md",
            "evidence_bundles/",
            "scenario_traces/",
            "SHA256SUMS.json",
        ],
    }

    write_json(output_dir / "query_catalog.json", query_catalog())
    write_json(output_dir / "sample_queries.json", {"task": TASK_LABEL, "boundary_statement": BOUNDARY_STATEMENT, "queries": queries})
    write_json(
        output_dir / "sample_query_results.json",
        {
            "task": TASK_LABEL,
            "boundary_statement": BOUNDARY_STATEMENT,
            "results": query_results,
        },
    )
    write_json(output_dir / "hero_operator_briefing.json", hero_briefing)
    (output_dir / "hero_operator_briefing.md").write_text(hero_markdown, encoding="utf-8")
    write_json(
        output_dir / "scenario_traces" / "hero_reachability_trace.json",
        {
            "task": TASK_LABEL,
            "boundary_statement": BOUNDARY_STATEMENT,
            "trace": reachability_result["evidence_bundle"].get("hero_composite_path"),
        },
    )
    write_json(output_dir / "a5d1_manifest.json", manifest)

    input_hashes_after = hash_tree(input_dir)
    preliminary_report = {
        "task": TASK_LABEL,
        "operator_query_slice": "A5-D1 / a5·D1",
        "spine_naming": {
            "a5": SPINE_LABEL,
            "input": INPUT_LABEL,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "status": "PENDING",
        "a4_d2_status_consumed": harness_report.get("a5_status"),
        "a2_preflight_consumed": harness_report.get("a2_preflight_status"),
        "a4_regression_consumed": harness_report.get("a4_regression_status"),
        "key_query_checks": {},
        "gates": [],
    }
    write_json(output_dir / "a5d1_harness_report.json", preliminary_report)
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# A5-D1 Operator Query",
                "",
                BOUNDARY_STATEMENT,
                "",
                "## Naming",
                "",
                f"- {SPINE_LABEL}.",
                f"- {INPUT_LABEL}, consumed here as frozen canonical input.",
                "- A5-D1 / a5·D1 is the operator-query slice over the enriched district graph.",
                "",
                "## Status",
                "",
                "- A5-D1 status: PENDING",
                "",
            ]
        ),
        encoding="utf-8",
    )
    gates = run_gates(
        input_dir=input_dir,
        output_dir=output_dir,
        graph=graph,
        input_hashes_before=input_hashes_before,
        input_hashes_after=input_hashes_after,
        harness_report=harness_report,
        input_summary=input_summary,
        query_results=query_results,
        hero_briefing=hero_briefing,
    )
    key_query_checks = {
        "parcel_profile": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-PARCEL-PROFILE"),
        "building_profile": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-BUILDING-PROFILE"),
        "complaint_search": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-COMPLAINT-SEARCH"),
        "permit_search": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-PERMIT-SEARCH"),
        "party_confidence": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-PARTY-CONFIDENCE"),
        "reachability": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-REACHABILITY"),
        "boundary_statement": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-BOUNDARY"),
        "no_mutation": next(g["passed"] for g in gates if g["gate_id"] == "A5D1-NO-MUTATION"),
    }
    status = "PASS" if all(g["passed"] for g in gates) else "FAIL"
    report = {
        "task": TASK_LABEL,
        "operator_query_slice": "A5-D1 / a5·D1",
        "spine_naming": {
            "a5": SPINE_LABEL,
            "input": INPUT_LABEL,
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "status": status,
        "exit_code": 0 if status == "PASS" else 1,
        "input_snapshot": "a5_district_v1",
        "a4_d2_status_consumed": harness_report.get("a5_status"),
        "a2_preflight_consumed": harness_report.get("a2_preflight_status"),
        "a4_regression_consumed": harness_report.get("a4_regression_status"),
        "output_directory": output_dir.as_posix(),
        "hero": {
            "parcel_bbl": HERO_BBL,
            "building_bin": HERO_BIN,
            "complaint": HERO_COMPLAINT_ID,
        },
        "loaded_counts": {
            "entities": graph.entity_counts(),
            "edges": graph.edge_counts(),
        },
        "key_query_checks": key_query_checks,
        "gates": gates,
    }
    write_json(output_dir / "a5d1_harness_report.json", report)
    readme = build_readme(report, input_summary, output_dir)
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    write_output_hashes(output_dir)
    return report


def run_a5d1_gate(input_dir: str, output_dir: str) -> dict:
    """Build A5-D1 outputs and return the harness report."""
    return run_a5d1(Path(input_dir), Path(output_dir))


def print_final_report(report: dict[str, Any]) -> None:
    checks = report.get("key_query_checks", {})
    lines = [
        f"A5-D1 Operator Query: {report.get('status')}",
        f"Input snapshot: {report.get('input_snapshot')}",
        f"A4-D2 status consumed: {report.get('a4_d2_status_consumed')}",
        f"A2 preflight consumed: {report.get('a2_preflight_consumed')}",
        f"A4 regression consumed: {report.get('a4_regression_consumed')}",
        f"Output directory: {report.get('output_directory')}",
        f"Hero parcel: {HERO_BBL}",
        f"Hero building: {HERO_BIN}",
        f"Hero complaint: {HERO_COMPLAINT_ID}",
        "",
        "Key query checks:",
        f"- parcel profile: {'PASS' if checks.get('parcel_profile') else 'FAIL'}",
        f"- building profile: {'PASS' if checks.get('building_profile') else 'FAIL'}",
        f"- complaint search: {'PASS' if checks.get('complaint_search') else 'FAIL'}",
        f"- permit search: {'PASS' if checks.get('permit_search') else 'FAIL'}",
        f"- party confidence: {'PASS' if checks.get('party_confidence') else 'FAIL'}",
        f"- reachability: {'PASS' if checks.get('reachability') else 'FAIL'}",
        f"- boundary statement: {'PASS' if checks.get('boundary_statement') else 'FAIL'}",
        f"- no mutation: {'PASS' if checks.get('no_mutation') else 'FAIL'}",
    ]
    failed = [gate for gate in report.get("gates", []) if not gate.get("passed")]
    if failed:
        lines.extend(["", "Failed gates:"])
        lines.extend(f"- {gate['gate_id']}: {gate.get('details')}" for gate in failed)
    print("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_LABEL)
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-gates", action="store_true", help="Build outputs and run A5-D1 gates.")
    parser.add_argument("--query-file", default=None)
    parser.add_argument("--no-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args(argv)

    nim = {
        "disabled": args.no_nim or not args.nim_endpoint,
        "endpoint": args.nim_endpoint,
        "model": args.nim_model,
    }
    if not args.run_gates and not args.query_file:
        args.run_gates = True
    report = run_a5d1(
        Path(args.input_dir),
        Path(args.output_dir),
        query_file=Path(args.query_file) if args.query_file else None,
        nim=nim,
    )
    print_final_report(report)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    sys.exit(main())
