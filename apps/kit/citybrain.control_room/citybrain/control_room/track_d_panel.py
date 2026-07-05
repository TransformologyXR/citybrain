from __future__ import annotations


class TrackDPanel:
    def __init__(self, bundle: dict):
        self.bundle = bundle

    def summary(self) -> dict:
        packets = self.bundle["track_d"].get("packets", [])
        return {
            "packet_count": len(packets),
            "eligible_packet_count": self.bundle["track_d"].get("eligible_packet_count"),
            "approved_proposal_created": self.bundle["track_d"].get("approved_proposal_created"),
            "execution_state": self.bundle["one_truth"].get("execution_state"),
            "track_d_authoritative": True,
        }
