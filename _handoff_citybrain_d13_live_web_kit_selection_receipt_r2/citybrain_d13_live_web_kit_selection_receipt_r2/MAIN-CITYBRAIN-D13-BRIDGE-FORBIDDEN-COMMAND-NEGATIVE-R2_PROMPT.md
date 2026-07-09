# MAIN-CITYBRAIN-D13-BRIDGE-FORBIDDEN-COMMAND-NEGATIVE-R2

Re-run bridge negative tests across the live transport path.

Forbidden commands:
- execute
- dispatch
- route
- enforce
- approve
- create case
- certify finding
- publish alert
- take action

Expected:
- rejected
- logged
- execution_state remains `not_executed`
- no official case/ticket/dispatch/route/control artifact created

Output:
`D13_LIVE_BRIDGE_FORBIDDEN_COMMAND_NEGATIVE_TESTS.json`
