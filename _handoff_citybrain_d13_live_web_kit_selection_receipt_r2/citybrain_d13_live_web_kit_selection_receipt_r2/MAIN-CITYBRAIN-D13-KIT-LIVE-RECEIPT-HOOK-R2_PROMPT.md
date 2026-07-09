# MAIN-CITYBRAIN-D13-KIT-LIVE-RECEIPT-HOOK-R2

Wire the Kit extension side to receive web-originated selection events and emit a live extension receipt.

Allowed implementation:
- local file watcher or localhost listener inside the Kit extension
- bounded local bridge only

Required proof:
- Kit/Composer app starts.
- CityBrain extension loads.
- A web-originated selection event is received by live extension code.
- Extension emits a receipt with payload hash and no-action boundary.
- Process cleanup is recorded.

Output:
`KIT_LIVE_RECEIPT_HOOK_REPORT.json`
`KIT_EXTENSION_LIVE_RECEIPT_LOG.jsonl`
`KIT_PROCESS_CLEANUP_REPORT.json`
