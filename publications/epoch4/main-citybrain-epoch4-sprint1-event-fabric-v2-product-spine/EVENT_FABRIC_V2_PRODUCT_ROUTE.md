# Event Fabric V2 Product Route

Local/replay route: source record -> deterministic EventEnvelopeV2 -> CER-backed resolution -> current state -> query response -> WATCH admission -> CHECK/BRIEF/spatial handoff. No live monitoring, official truth, alerting, dispatch, control, or enforcement is created.
