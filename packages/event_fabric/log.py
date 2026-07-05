from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .contracts import validate_event_envelope


def append_event(path: Path, event: dict) -> dict:
    validated = validate_event_envelope(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(validated, sort_keys=True) + "\n")
    return validated


def read_event_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(validate_event_envelope(json.loads(line)))
    return events


def write_event_log(path: Path, events: Iterable[dict]) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = [validate_event_envelope(event) for event in events]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for event in validated:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return validated
