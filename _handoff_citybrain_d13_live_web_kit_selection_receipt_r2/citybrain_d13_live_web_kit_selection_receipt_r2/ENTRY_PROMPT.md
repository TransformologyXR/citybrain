# ENTRY PROMPT — MAIN-CITYBRAIN-D13-LIVE-WEB-KIT-SELECTION-RECEIPT-R2

Run this package after the log-only D13 seam result.

Goal: prove the live web ↔ Kit selection seam, not just file-spool parity.

Do not run D14. Do not change D11 operator-session state. Do not create fake operator sessions. Do not implement Open ASK. Do not create a second selection model.

## Required sequence

1. `MAIN-CITYBRAIN-D13-LIVE-SEAM-PREFLIGHT-R2`
2. `MAIN-CITYBRAIN-D13-LIVE-BRIDGE-TRANSPORT-CONTRACT-R2`
3. `MAIN-CITYBRAIN-D13-WEB-LIVE-RECEIPT-HOOK-R2`
4. `MAIN-CITYBRAIN-D13-KIT-LIVE-RECEIPT-HOOK-R2`
5. `MAIN-CITYBRAIN-D13-BIDIRECTIONAL-GUI-RECEIPT-SMOKE-R2`
6. `MAIN-CITYBRAIN-D13-BRIDGE-FORBIDDEN-COMMAND-NEGATIVE-R2`
7. `MAIN-CITYBRAIN-D13-ONE-TRUTH-LIVE-SEAM-PARITY-R2`
8. `MAIN-CITYBRAIN-D13-LIVE-SEAM-CLOSEOUT-R2`
9. `MAIN-CITYBRAIN-D13-LIVE-SEAM-MILESTONE-FREEZE-R2`

## Required PASS meaning

Only return `PASS_D13_LIVE_WEB_KIT_SELECTION_SEAM_WITH_LIMITATIONS` if all are true:

- Kit/Composer runtime launched and loaded the CityBrain extension in this run.
- Web cockpit runtime was served/opened in this run.
- Web → Kit selection event produced a live Kit extension receipt callback, not just a file-spool line.
- Kit → Web selection event produced a live web UI/DOM receipt, not just a file-spool line.
- One-truth payload parity passed for entity, evidence packet reference, limitations, and no-action/not-executed state.
- Forbidden/action-shaped bridge commands were rejected and logged with `not_executed`.
- No Kit process was left running unintentionally.

If any live receipt is missing, return a PARTIAL status with the exact missing receipt. Do not call log-only parity a live seam.
