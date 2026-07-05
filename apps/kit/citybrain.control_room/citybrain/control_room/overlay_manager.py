from __future__ import annotations


ALLOWED_OVERLAY_STATES = {
    "candidate_event",
    "evidence_marker",
    "limitation_marker",
    "review_context",
    "review_state",
    "selected_entity",
    "uncertainty_marker",
}

FORBIDDEN_OVERLAY_TERMS = (
    "certified affected asset",
    "confirmed violation",
    "legal finding",
    "dispatch",
    "action",
    "measurement-grade",
)


class OverlayManager:
    def __init__(self, bundle: dict):
        self.bundle = bundle
        packets = list(bundle["overlays"].get("packets", []))
        try:
            from .scene_prim_selection_registry import overlay_packets_for_registry

            packets.extend(overlay_packets_for_registry())
        except Exception:
            pass
        try:
            from .event_overlay_registry import overlay_packets_for_event_registry

            packets.extend(overlay_packets_for_event_registry())
        except Exception:
            pass
        try:
            from .real_scene_review_loop_registry import overlay_packets_for_real_scene_review_loop

            packets.extend(overlay_packets_for_real_scene_review_loop())
        except Exception:
            pass
        self.lookup = {packet["entity_ref"]: packet for packet in packets}
        self.prim_lookup = {
            packet["prim_path"]: packet
            for packet in packets
            if packet.get("prim_path")
        }
        self.packets = packets

    def entity_refs(self) -> list[str]:
        return sorted(self.lookup)

    def prim_paths(self) -> list[str]:
        return sorted(self.prim_lookup)

    def packet_for(self, entity_ref: str) -> dict | None:
        return self.lookup.get(entity_ref)

    def packet_for_prim_path(self, prim_path: str) -> dict | None:
        return self.prim_lookup.get(prim_path)

    def first_packet(self) -> dict | None:
        refs = self.entity_refs()
        return self.lookup.get(refs[0]) if refs else None

    def overlay_rows(self) -> list[dict]:
        rows = []
        for packet in self.packets:
            rows.append(
                {
                    "entity_ref": packet.get("entity_ref"),
                    "prim_path": packet.get("prim_path"),
                    "overlay_state": packet.get("overlay_state"),
                    "claim_label": packet.get("claim_label"),
                    "limitation_ref": packet.get("limitation_ref"),
                    "allowed_semantics": True,
                }
            )
        return rows

    def contract(self) -> dict:
        rows = self.overlay_rows()
        forbidden_hits = []
        for row in rows:
            text = " ".join(str(value).lower() for value in row.values())
            for term in FORBIDDEN_OVERLAY_TERMS:
                if term in text:
                    forbidden_hits.append({"term": term, "row": row})
        return {
            "schema_version": "citybrain.kit.overlay_manager_contract.r1",
            "allowed_overlay_types": sorted(ALLOWED_OVERLAY_STATES),
            "forbidden_overlay_semantics": list(FORBIDDEN_OVERLAY_TERMS),
            "overlay_packet_count": len(rows),
            "rows": rows,
            "forbidden_semantic_hits": forbidden_hits,
            "status": "PASS" if not forbidden_hits else "FAIL",
            "execution_state": self.bundle["one_truth"].get("execution_state"),
        }

    def smoke_report(self) -> dict:
        rows = self.overlay_rows()
        all_review = all(
            row.get("claim_label") == "not_executed"
            and str(row.get("overlay_state", "")).startswith("review")
            for row in rows
        )
        contract = self.contract()
        return {
            "schema_version": "citybrain.kit.overlay_manager_smoke.r1",
            "status": "PASS" if rows and all_review and contract["status"] == "PASS" else "FAIL",
            "overlay_packet_count": len(rows),
            "entity_refs_resolve": all(row.get("entity_ref") in self.lookup for row in rows),
            "prim_paths_resolve": all(row.get("prim_path") in self.prim_lookup for row in rows),
            "review_context_only": all_review,
            "forbidden_semantic_hits": contract["forbidden_semantic_hits"],
            "execution_state": self.bundle["one_truth"].get("execution_state"),
        }

    def projection_summary(self) -> dict:
        return {
            "scenario_state_ref": self.bundle["one_truth"]["scenario_state_ref"],
            "execution_state": self.bundle["one_truth"]["execution_state"],
            "overlay_packet_count": len(self.lookup),
            "prim_path_count": len(self.prim_lookup),
        }
