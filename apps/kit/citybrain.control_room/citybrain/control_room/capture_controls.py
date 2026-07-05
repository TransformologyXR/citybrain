from __future__ import annotations

ALLOWED_COMMANDS = ['select', 'scrub', 'inspect', 'camera', 'capture', 'focus', 'highlight', 'clear_highlight']
FORBIDDEN_COMMANDS = ['execute', 'dispatch', 'route', 'enforce', 'approve', 'create_ticket', 'create_case', 'send_alert', 'publish_alert', 'control_signal', 'take_action', 'legal_find', 'certify_finding']


def classify_command(command: str) -> dict:
    if command in ALLOWED_COMMANDS:
        return {"command": command, "command_status": "accepted", "execution_state": "not_executed"}
    if command in FORBIDDEN_COMMANDS:
        return {
            "command": command,
            "command_status": "rejected",
            "reason": "review_only_boundary",
            "execution_state": "not_executed",
        }
    return {"command": command, "command_status": "rejected", "reason": "unknown_command", "execution_state": "not_executed"}
