# MAIN-CITYBRAIN-D13-WEB-LIVE-RECEIPT-HOOK-R2

Wire the web cockpit side to receive Kit-originated selection events and expose a live DOM/UI receipt.

Allowed implementation:
- local-only polling, localhost endpoint, or file watcher surfaced through the dev server
- no public API
- no production claim
- no action semantics

Required proof:
- A Kit-originated selection event changes/updates a visible or testable web receipt element.
- The receipt must be observable in DOM capture.
- The receipt must preserve the same entity/evidence/limitations/no-action state.

Output:
`WEB_LIVE_RECEIPT_HOOK_REPORT.json`
`WEB_LIVE_RECEIPT_DOM_CAPTURE.html`
