# MAIN-CITYBRAIN-D13-LIVE-BRIDGE-TRANSPORT-CONTRACT-R2

Write/refresh the live bridge transport contract without creating a second selection model.

Contract requirements:
- The web cockpit selection contract remains authoritative.
- Transport carries selection payloads only.
- Transport must include:
  - direction: `web_to_kit` or `kit_to_web`
  - selection_id
  - entity_id
  - evidence_packet_ref
  - limitations_ref or limitations hash
  - execution_state / no_action state
  - source runtime bundle hash/ref
  - payload hash
  - timestamp
- Receipts must include:
  - received_by: `kit_extension` or `web_ui`
  - original payload hash
  - receipt timestamp
  - rendering/selection state observed
  - no action taken
- Forbidden/action-shaped commands are rejected at bridge boundary.

Output:
`LIVE_WEB_KIT_SELECTION_BRIDGE_CONTRACT_R2.json`
