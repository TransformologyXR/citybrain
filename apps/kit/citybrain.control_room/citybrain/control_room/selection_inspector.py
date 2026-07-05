from __future__ import annotations


NO_ACTION_CANNOT_CLAIM = [
    "not a certified physical twin",
    "not measurement-grade geometry",
    "not an official affected asset/building determination",
    "not live monitoring",
    "not dispatch, routing/control, enforcement, ticket/case creation, or automated action",
    "not a legal/certified finding",
]


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _entity_label(entity_ref: str) -> str:
    parts = entity_ref.split(":")
    if len(parts) >= 3:
        kind = parts[-2].replace("_", " ")
        name = parts[-1].replace("-", " ").replace("_", " ")
        return f"{kind}: {name}"
    return entity_ref.replace("_", " ").replace("-", " ")


def _source_roots(bundle: dict) -> list[dict]:
    refs = []
    seen = set()
    for packet_name in ("one_truth", "evidence", "review", "limitations", "track_d", "overlays"):
        for ref in bundle.get(packet_name, {}).get("source_root_refs", []):
            key = ref.get("key") or ref.get("root")
            if key and key not in seen:
                refs.append(ref)
                seen.add(key)
    return refs


def _option_packet_sample(bundle: dict) -> list[dict]:
    packets = bundle.get("track_d", {}).get("packets", [])
    sample = []
    for packet in packets[:4]:
        sample.append(
            {
                "panel_packet_id": packet.get("panel_packet_id"),
                "option_role": packet.get("option_role"),
                "eligibility_state": packet.get("eligibility_state"),
                "guardrail_result": packet.get("guardrail_result"),
                "execution_state": packet.get("execution_state"),
                "no_execution": packet.get("no_execution"),
                "evidence_refs": packet.get("evidence_refs", []),
                "limitation_refs": packet.get("limitation_refs", []),
            }
        )
    return sample


def visible_text_from_card(card: dict) -> str:
    lines = [
        "CityBrain Spatial Cockpit",
        "Review only. No action has been taken. execution_state = not_executed.",
        f"Selected entity: {card.get('entity_label')} ({card.get('entity_ref')})",
        f"Selected prim path: {card.get('prim_path')}",
        f"Packet hash: {card.get('packet_hash')}",
    ]
    if card.get("event_id"):
        lines.append(f"Event id: {card.get('event_id')} | event_state={card.get('event_state')}")
        lines.append(f"Event target prim path: {card.get('target_prim_path')}")
        if card.get("citation_refs"):
            lines.append(f"Citations/provenance refs: {', '.join(card.get('citation_refs', []))}")
    lines.extend([f"What this is: {card.get('what_it_is')}", "What supports this:"])
    for item in card.get("evidence", {}).get("source_records", []):
        lines.append(f"- {item}")
    for item in card.get("citations", []):
        lines.append(f"- citation: {item.get('key')} - {item.get('root')}")
    lines.append("Knowns / summary:")
    for item in card.get("knowns", []):
        lines.append(f"- {item}")
    lines.append("Unknowns / limitations:")
    for item in card.get("unknowns_limitations", []):
        lines.append(f"- {item}")
    lines.append("What this does not prove:")
    for item in card.get("cannot_claim", []):
        lines.append(f"- {item}")
    review = card.get("review_state", {})
    lines.append(
        "Review state: "
        f"{review.get('review_state_ref')} | "
        f"Track D authoritative={review.get('track_d_authoritative')} | "
        f"approved proposal created={review.get('approved_proposal_created')}"
    )
    overlay = card.get("overlay", {})
    lines.append(
        "Overlay state: "
        f"{overlay.get('overlay_state')} | "
        f"claim_label={overlay.get('claim_label')} | "
        f"limitation_ref={overlay.get('limitation_ref')}"
    )
    no_action = card.get("no_action_state", {})
    lines.append(
        "NoActionState: "
        f"no_action_taken={no_action.get('no_action_taken')} | "
        f"execution_state={no_action.get('execution_state')}"
    )
    return "\n".join(lines)


class SelectionInspector:
    def __init__(self, bundle: dict, overlay_manager):
        self.bundle = bundle
        self.overlay_manager = overlay_manager

    def inspect(self, entity_ref: str) -> dict:
        packet = self.overlay_manager.packet_for(entity_ref)
        return self._inspect_packet(entity_ref, packet, "entity_ref")

    def inspect_prim_path(self, prim_path: str) -> dict:
        packet = self.overlay_manager.packet_for_prim_path(prim_path)
        entity_ref = packet.get("entity_ref") if packet else prim_path
        return self._inspect_packet(entity_ref, packet, "prim_path")

    def inspect_first(self) -> dict:
        packet = self.overlay_manager.first_packet()
        entity_ref = packet.get("entity_ref") if packet else ""
        return self._inspect_packet(entity_ref, packet, "first_overlay")

    def _inspect_packet(self, entity_ref: str, packet: dict | None, selection_source: str) -> dict:
        evidence = self.bundle.get("evidence", {})
        scenario = self.bundle.get("scenario", {})
        review = self.bundle.get("review", {})
        limitations = self.bundle.get("limitations", {})
        one_truth = self.bundle.get("one_truth", {})
        track_d = self.bundle.get("track_d", {})
        overlay = packet or {}
        entity_label = overlay.get("entity_label") or _entity_label(entity_ref)
        overlay_evidence_refs = [
            item for item in _as_list(overlay.get("evidence_refs")) if item not in _as_list(overlay.get("entity_ref"))
        ]
        source_records = (
            _as_list(overlay.get("entity_ref"))
            + overlay_evidence_refs
            + evidence.get("candidate_observation_refs", [])
            + evidence.get("similar_case_refs", [])
            + evidence.get("cascade_refs", [])
        )
        knowns = [
            f"Scenario: {scenario.get('scenario_id')} ({scenario.get('scenario_state_ref')})",
            f"Hero spine: {scenario.get('hero_spine') or one_truth.get('hero_spine')}",
            f"Overlay packet source: kit_overlay_packets.json with state {overlay.get('overlay_state')}",
            "D7 observations are candidate observations, not findings.",
            "Track D remains authoritative; no approval or execution is created.",
        ]
        unknowns_limitations = []
        if overlay.get("limitation_ref"):
            unknowns_limitations.append(f"Selected overlay limitation ref: {overlay.get('limitation_ref')}")
        unknowns_limitations.extend(_as_list(overlay.get("limitation_refs")))
        unknowns_limitations.extend(limitations.get("limitations", []))
        overlay_review = overlay.get("review_state") or {}
        overlay_no_action = overlay.get("no_action_state") or {}
        card = {
            "schema_version": "citybrain.kit.entity_selection_card.r1",
            "selection_source": selection_source,
            "found": packet is not None,
            "entity_ref": entity_ref,
            "entity_label": entity_label,
            "what_it_is": overlay.get("what_it_is")
            or (
                f"CityBrain review/context overlay for {entity_label} "
                "inside the Mobility Access corridor package."
            ),
            "prim_path": overlay.get("prim_path"),
            "overlay": overlay,
            "source_scene": overlay.get("source_scene"),
            "packet_hash": overlay.get("packet_hash"),
            "event_id": overlay.get("event_id"),
            "event_type": overlay.get("event_type"),
            "event_state": overlay.get("event_state"),
            "target_prim_path": overlay.get("target_prim_path"),
            "citation_refs": _as_list(overlay.get("citation_refs")),
            "evidence": {
                "schema_version": evidence.get("schema_version"),
                "candidate_observation_count": evidence.get("candidate_observation_count"),
                "similar_case_count": evidence.get("similar_case_count"),
                "cascade_attachment_count": evidence.get("cascade_attachment_count"),
                "source_records": source_records,
                "claim_labels": evidence.get("claim_labels", []),
            },
            "citations": _source_roots(self.bundle),
            "knowns": knowns,
            "unknowns_limitations": unknowns_limitations,
            "cannot_claim": _as_list(overlay.get("cannot_claim")) or NO_ACTION_CANNOT_CLAIM,
            "review_state": {
                "schema_version": overlay_review.get("schema_version") or review.get("schema_version"),
                "review_state_ref": overlay_review.get("review_state_ref") or review.get("review_state_ref"),
                "track_d_authoritative": overlay_review.get("track_d_authoritative", review.get("track_d_authoritative")),
                "approved_proposal_created": overlay_review.get("approved_proposal_created", review.get("approved_proposal_created")),
                "execution_authority_created": overlay_review.get(
                    "execution_authority_created",
                    review.get("execution_authority_created"),
                ),
                "claim_labels": review.get("claim_labels", []),
            },
            "no_action_state": {
                "no_action_taken": overlay_no_action.get("no_action_taken", True),
                "execution_state": overlay_no_action.get("execution_state") or one_truth.get("execution_state"),
                "approved_proposal_created": overlay_no_action.get(
                    "approved_proposal_created",
                    track_d.get("approved_proposal_created"),
                ),
                "execution_authority_created": overlay_no_action.get(
                    "execution_authority_created",
                    review.get("execution_authority_created"),
                ),
            },
            "track_d_option_packet_sample": _option_packet_sample(self.bundle),
            "claim_labels_visible": True,
        }
        return {
            "entity_ref": entity_ref,
            "found": packet is not None,
            "overlay_packet": packet,
            "evidence_summary": {
                "candidate_observation_count": evidence.get("candidate_observation_count"),
                "similar_case_count": evidence.get("similar_case_count"),
            },
            "execution_state": one_truth.get("execution_state"),
            "claim_labels_visible": True,
            "inspection_card": card,
            "visible_text": visible_text_from_card(card),
        }
