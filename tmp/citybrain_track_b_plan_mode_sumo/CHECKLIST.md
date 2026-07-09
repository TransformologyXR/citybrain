# Checklist

Before running:
- Confirm Track S closeout exists and is green.
- Confirm R2 certified-state handover exists and is green.
- Confirm shared hero scenario is used.
- Confirm Track D composition rules are consumed, not redefined.

For every step:
- Create a runner under `scripts/`.
- Create a new output root under `outputs/`.
- Produce a decision JSON.
- Produce `LOCAL_OPEN_INDEX.md`.
- Produce input artifact index.
- Produce validation report.
- Produce claim-boundary audit.
- Produce no-action audit.
- Produce no-mutation audit.
- Produce secret audit.
- Produce hash manifest.
- Preserve unresolved/quarantined contexts.
- Keep `execution_state = not_executed`.

- Confirm every produced option set validates against Track S.
- Confirm SUMO outputs are context only, not certified traffic truth.
- Confirm inverse dynamics is only recommended after a green scenario output.
