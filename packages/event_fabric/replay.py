from __future__ import annotations

from pathlib import Path

from .log import read_event_log


def replay_events(path: Path) -> dict:
    events = sorted(read_event_log(path), key=lambda event: (event["event_time"], event["event_id"]))
    return {
        "status": "PASS",
        "event_count": len(events),
        "event_ids": [event["event_id"] for event in events],
        "events": events,
        "deterministic_order": True,
    }
