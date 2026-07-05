export const allowedCommands = ["select", "scrub", "inspect", "camera", "capture", "focus", "highlight", "clear_highlight"];
export const forbiddenCommands = ["execute", "dispatch", "route", "enforce", "approve", "create_ticket", "create_case", "send_alert", "publish_alert", "control_signal", "take_action", "legal_find", "certify_finding"];

export function classifyCommand(command) {
  if (allowedCommands.includes(command)) return { command_status: "accepted", execution_state: "not_executed" };
  if (forbiddenCommands.includes(command)) return { command_status: "rejected", reason: "review_only_boundary", execution_state: "not_executed" };
  return { command_status: "rejected", reason: "unknown_command", execution_state: "not_executed" };
}
