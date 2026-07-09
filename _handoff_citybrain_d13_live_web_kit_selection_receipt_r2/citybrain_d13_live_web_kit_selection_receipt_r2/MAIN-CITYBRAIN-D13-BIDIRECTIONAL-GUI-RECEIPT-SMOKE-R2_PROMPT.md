# MAIN-CITYBRAIN-D13-BIDIRECTIONAL-GUI-RECEIPT-SMOKE-R2

Run the live bidirectional smoke.

Cases:
1. Wood Lane / EV access selected in web → Kit receives and resolves same selection.
2. NYC MVC candidate context selected in web → Kit receives and resolves same selection.
3. Kit-originated pick/selection for a bound entity → web receives and updates selected item receipt.

Do not count pure file-spool read/write as PASS. It may support diagnostics only.

Output:
`BIDIRECTIONAL_GUI_RECEIPT_SMOKE_REPORT.json`

Statuses:
- `PASS_BIDIRECTIONAL_GUI_RECEIPT_SMOKE`
- `PARTIAL_ONLY_WEB_TO_KIT_LIVE_RECEIPT`
- `PARTIAL_ONLY_KIT_TO_WEB_LIVE_RECEIPT`
- `PARTIAL_LOG_ONLY_NO_GUI_RECEIPTS`
- `FAIL_BIDIRECTIONAL_GUI_RECEIPT_BOUNDARY_OR_PARITY`
