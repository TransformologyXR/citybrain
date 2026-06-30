"""
TXR City Brain — a4 Graph Projection Gate
=========================================

Enforces the corrected a4 plan: the semantic graph is a *projection* of the
canonical entities/edges (the read/execution model), NOT a second schema built
from raw tables. It runs a2 first (canonical must be green — "if this fails, no
graph"), then adds graph-specific gates:

  DISTRICT       district boundary is explicit; no out-of-district leakage
  A4-UNIQUE      all entity ids unique (no silent dedupe)
  A4-VOCAB       projection uses ONLY canonical EntityType / Relation vocabulary
                 — catches a TaxLot / HAS_PERMIT fork
  A4-NODE-FID    projection nodes ↔ canonical entities 1:1 (no extra/missing)
  A4-EDGE-FID    projection edges ↔ canonical edges 1:1 (same src,dst,relation)
  A4-CONF        projection edges preserve canonical confidence (the 0.70 / 0.95
                 survive the projection — they are the point of L2)
  A4-TRAVERSAL   from the hero complaint, the projection reaches the full cascade
                 neighbourhood with the right relations (the "graph is correct"
                 target — what a4 builds against, on CPU now / cuGraph later)

The gate validates Codex's projection AGAINST the canonical truth, so the GPU
swap later changes only performance, never the schema.

Usage:
    rep = run_a4_gate(entities, edges, proj_nodes, proj_edges, manifest)
    sys.exit(rep.exit_code)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, field

from txr_citybrain_schema_v1 import Relation, EntityType, EventCategory
from txr_citybrain_harness import (
    GateResult, HarnessReport, run_harness, print_report, good_stub,
)

_CANON_RELATIONS = {r.value for r in Relation}
_CANON_TYPES = {t.value for t in EntityType}


# ─────────────────────────────────────────────────────────────────────────────
# District manifest
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DistrictManifest:
    """Explicit district boundary for the scoped cut (Step 0). `member_ids` is the
    set of canonical_ids declared in-district — the graph is built ONLY over these."""
    name: str
    boundary_desc: str               # e.g. "Manhattan tax block 1060 (Midtown West)"
    member_ids: set                  # canonical_ids in scope


# ─────────────────────────────────────────────────────────────────────────────
# Reference projector — what a faithful projection looks like.
# Codex can use this directly; the gates validate ANY projection against canonical.
# ─────────────────────────────────────────────────────────────────────────────

def project_canonical(entity_dicts, edge_dicts):
    """Canonical entities/edges -> graph read-model (nodes, edges). Pure projection:
    node = {id, type}; edge = {src, dst, relation, confidence}. No new vocabulary,
    no re-resolution. This is the only legitimate way to build the a4 graph."""
    nodes = [{"id": e["canonical_id"], "type": e["entity_type"]} for e in entity_dicts]
    edges = []
    for g in edge_dicts:
        conf = g.get("confidence")
        edges.append({
            "src": g["src_ref"], "dst": g["dst_ref"], "relation": g["relation"],
            "role": g.get("role"),
            "confidence": (conf or {}).get("score") if conf else None,
        })
    return nodes, edges


# ─────────────────────────────────────────────────────────────────────────────
# a4 gates
# ─────────────────────────────────────────────────────────────────────────────

def _gate_district(entity_dicts, edge_dicts, manifest):
    details, leaked = [], 0
    if not manifest or not manifest.name or not manifest.boundary_desc:
        return GateResult("DISTRICT", "Explicit district boundary", "a4", False, 1, 1,
                          ["no district manifest / boundary declared"])
    if not manifest.member_ids:
        return GateResult("DISTRICT", "Explicit district boundary", "a4", False, 1, 1,
                          ["district manifest has empty member set"])
    for e in entity_dicts:
        if e["canonical_id"] not in manifest.member_ids:
            leaked += 1
            if len(details) < 4:
                details.append(f"out-of-district entity leaked: {e['canonical_id']}")
    for g in edge_dicts:
        for end in ("src_ref", "dst_ref"):
            if g[end] not in manifest.member_ids:
                leaked += 1
                if len(details) < 4:
                    details.append(f"out-of-district edge endpoint leaked: {g[end]}")
    return GateResult("DISTRICT", f"District: {manifest.name}", "a4",
                      leaked == 0, len(entity_dicts) + (2 * len(edge_dicts)), leaked, details)


def _gate_unique(entity_dicts):
    seen, dupes, details = set(), 0, []
    for e in entity_dicts:
        cid = e["canonical_id"]
        if cid in seen:
            dupes += 1
            if len(details) < 4:
                details.append(f"duplicate entity id: {cid}")
        seen.add(cid)
    return GateResult("A4-UNIQUE", "Entity ids unique", "a4",
                      dupes == 0, len(entity_dicts), dupes, details)


def _gate_vocab(proj_nodes, proj_edges):
    """The fork-catcher. Every projection node type and edge relation MUST be in the
    canonical vocabulary — no TaxLot, no HAS_PERMIT."""
    bad, details = 0, []
    for n in proj_nodes:
        if n.get("type") not in _CANON_TYPES:
            bad += 1
            if len(details) < 4:
                details.append(f"non-canonical node type '{n.get('type')}' ({n.get('id')})")
    for e in proj_edges:
        if e.get("relation") not in _CANON_RELATIONS:
            bad += 1
            if len(details) < 4:
                details.append(f"non-canonical relation '{e.get('relation')}' "
                               f"({e.get('src')} -> {e.get('dst')})")
    return GateResult("A4-VOCAB", "Canonical vocabulary only", "a4",
                      bad == 0, len(proj_nodes) + len(proj_edges), bad, details)


def _gate_node_fidelity(entity_dicts, proj_nodes):
    canon = {e["canonical_id"] for e in entity_dicts}
    proj = {n["id"] for n in proj_nodes}
    missing, extra = canon - proj, proj - canon
    details = ([f"missing node: {m}" for m in list(missing)[:3]] +
               [f"extra node (not canonical): {x}" for x in list(extra)[:3]])
    return GateResult("A4-NODE-FID", "Nodes ↔ canonical entities 1:1", "a4",
                      not missing and not extra, len(canon),
                      len(missing) + len(extra), details)


def _edge_key(e, src="src", dst="dst", rel="relation"):
    return (e[src], e[dst], e[rel])


def _gate_edge_fidelity(edge_dicts, proj_edges):
    canon = {(g["src_ref"], g["dst_ref"], g["relation"]) for g in edge_dicts}
    proj = {_edge_key(e) for e in proj_edges}
    missing, extra = canon - proj, proj - canon
    details = ([f"missing edge: {m}" for m in list(missing)[:3]] +
               [f"extra edge (not canonical): {x}" for x in list(extra)[:3]])
    return GateResult("A4-EDGE-FID", "Edges ↔ canonical edges 1:1", "a4",
                      not missing and not extra, len(canon),
                      len(missing) + len(extra), details)


def _gate_conf_preserved(edge_dicts, proj_edges):
    canon_conf = {}
    for g in edge_dicts:
        c = g.get("confidence")
        canon_conf[(g["src_ref"], g["dst_ref"], g["relation"])] = (c or {}).get("score") if c else None
    proj_conf = {_edge_key(e): e.get("confidence") for e in proj_edges}
    mism, details = 0, []
    for k, cv in canon_conf.items():
        pv = proj_conf.get(k, "MISSING")
        if pv == "MISSING":
            continue  # caught by edge-fidelity
        if (cv is None) != (pv is None) or (cv is not None and pv is not None and abs(cv - pv) > 1e-6):
            mism += 1
            if len(details) < 4:
                details.append(f"confidence drift {k[2]} ({k[0]}→{k[1]}): canon={cv} proj={pv}")
    return GateResult("A4-CONF", "Projection preserves confidence", "a4",
                      mism == 0, len(canon_conf), mism, details)


def _is_dob_complaint_event(entity):
    if entity.get("entity_type") != "event" or entity.get("category") != EventCategory.incident.value:
        return False
    if ":dob_complaint:" in entity.get("canonical_id", ""):
        return True
    if "complaint" in (entity.get("type") or ""):
        return True
    if (entity.get("ext") or {}).get("nyc.dob_complaint_category"):
        return True
    for provenance in entity.get("provenance", []) or []:
        dataset = provenance.get("source_dataset") or ""
        if "dob" in dataset and "complaint" in dataset:
            return True
    return False


def _gate_traversal(entity_dicts, proj_nodes, proj_edges):
    """From the hero complaint, the projection must reach the full cascade
    neighbourhood with the right relations. This is the 'graph is correct' target."""
    # find the construction-complaint event
    hero = next(
        (e for e in entity_dicts if e.get("canonical_id") == "event:us-nyc:dob_complaint:1366080"),
        None,
    )
    if hero is None:
        hero = next((e for e in entity_dicts if _is_dob_complaint_event(e)), None)
    if hero is None:
        return GateResult("A4-TRAVERSAL", "Hero cascade reachable", "a4", False, 1, 1,
                          ["no construction-complaint event to start traversal"])
    adj = defaultdict(list)
    for e in proj_edges:
        adj[e["src"]].append((e["dst"], e["relation"]))
        adj[e["dst"]].append((e["src"], e["relation"]))  # neighbourhood = undirected reach
    seen, rels, stack = set(), set(), [hero["canonical_id"]]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for nb, rel in adj[n]:
            rels.add(rel)
            if nb not in seen:
                stack.append(nb)
    types_reached = {n["type"] for n in proj_nodes if n["id"] in seen}
    need_types = {"building", "permit", "party", "parcel"}
    need_rels = {"resolves_to", "subject_of_permit", "performed_by"}
    miss_t, miss_r = need_types - types_reached, need_rels - rels
    ok = not miss_t and not miss_r
    details = []
    if miss_t:
        details.append(f"cascade did not reach entity types: {sorted(miss_t)}")
    if miss_r:
        details.append(f"cascade missing relations: {sorted(miss_r)}")
    if ok:
        details.append(f"{hero['canonical_id']} → reached {sorted(types_reached)} "
                       f"via {sorted(need_rels & rels)} ✓")
    return GateResult("A4-TRAVERSAL", "Hero cascade reachable", "a4", ok, 1,
                      0 if ok else 1, details)


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_a4_gate(
    entity_dicts,
    edge_dicts,
    proj_nodes,
    proj_edges,
    manifest,
    *,
    a2_entity_dicts=None,
    a2_edge_dicts=None,
) -> HarnessReport:
    # 1) canonical must be green first — "if this fails, no graph"
    """Run A2 on canonical output first, then validate the bounded district cut.

    The default remains backwards compatible: if a2_* is omitted, A2 runs on the
    same entities/edges as the projection. District builders can pass the full
    A2-green canonical layer via a2_* while projecting a tighter local graph.
    """
    a2_entities = a2_entity_dicts if a2_entity_dicts is not None else entity_dicts
    a2_edges = a2_edge_dicts if a2_edge_dicts is not None else edge_dicts
    a2 = run_harness(a2_entities, a2_edges)
    if not a2.all_green:
        a2.results.append(GateResult("A4-PRECOND", "Canonical green before graph", "a4",
                                     False, 1, 1, ["a2 not green — no graph is built"]))
        return a2
    # 2) a4 graph gates
    results = list(a2.results)
    results.append(GateResult("A4-PRECOND", "Canonical green before graph", "a4",
                              True, 1, 0, ["a2 passed before projection build"]))
    results.append(_gate_district(entity_dicts, edge_dicts, manifest))
    results.append(_gate_unique(entity_dicts))
    results.append(_gate_vocab(proj_nodes, proj_edges))
    results.append(_gate_node_fidelity(entity_dicts, proj_nodes))
    results.append(_gate_edge_fidelity(edge_dicts, proj_edges))
    results.append(_gate_conf_preserved(edge_dicts, proj_edges))
    results.append(_gate_traversal(entity_dicts, proj_nodes, proj_edges))
    return HarnessReport(results)


def print_a4(report, title):
    # reuse a2's printer for tiers, then print the a4 tier
    print_report(report, title)
    a4 = [r for r in report.results if r.tier == "a4"]
    if a4:
        print("  TIER 3 — a4 GRAPH PROJECTION")
        for r in a4:
            tag = "GREEN" if r.passed else " RED "
            mark = "✓" if r.passed else "✗"
            print(f"    [{tag}] {mark} {r.gate_id:<14} {r.name:<34} ({r.checked - r.failed}/{r.checked} ok)")
            for d in r.details:
                print(f"             ↳ {d}")
        a4_green = all(r.passed for r in a4)
        print(f"  a4 graph: {'GREEN' if a4_green else 'RED'}")


# ─────────────────────────────────────────────────────────────────────────────
# Demo: faithful projection (green) vs drifted projection (the fork → red)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ents, edgs = good_stub()
    manifest = DistrictManifest(
        name="MN-block-1060",
        boundary_desc="Manhattan tax block 1060 (Midtown West, 425 W 50th hero district)",
        member_ids={e["canonical_id"] for e in ents},
    )

    print("a4 GRAPH GATE — proving the projection cannot fork from canonical\n")

    # FAITHFUL projection
    nodes, p_edges = project_canonical(ents, edgs)
    print_a4(run_a4_gate(ents, edgs, nodes, p_edges, manifest),
             "FAITHFUL projection (canonical vocabulary, confidences preserved)")

    # DRIFTED projection: the exact fork we are preventing
    bad_nodes = [dict(n) for n in nodes]
    bad_edges = [dict(e) for e in p_edges]
    for n in bad_nodes:                      # rename parcel node type -> TaxLot
        if n["type"] == "parcel":
            n["type"] = "TaxLot"
    for e in bad_edges:                      # rename subject_of_permit -> HAS_PERMIT
        if e["relation"] == "subject_of_permit":
            e["relation"] = "HAS_PERMIT"
        if e["relation"] == "affects":       # drop a resolution confidence
            e["confidence"] = None
    bad_nodes.append({"id": "taxlot:raw:1010607502", "type": "TaxLot"})  # extra raw node

    print_a4(run_a4_gate(ents, edgs, bad_nodes, bad_edges, manifest),
             "DRIFTED projection (TaxLot/HAS_PERMIT fork, dropped confidence, raw node)")

    print("\nThe a4 gate runs a2 first (no graph if canonical is red), then fails on ANY\n"
          "drift from canonical vocabulary, node/edge identity, or confidence. CPU now,\n"
          "cuGraph later — the gate is identical; only the executor changes.")
