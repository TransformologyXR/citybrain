# Checklist

- [ ] Keep each lane bounded and data-first.
- [ ] Record source URL, license, access method, timestamp, file sizes, hashes, and attribution requirements.
- [ ] Do not download huge citywide datasets unless the prompt explicitly authorizes it.
- [ ] Prefer 500–2,000 semantic records, one neighborhood, or one small tile/clip bundle.
- [ ] Every landed dataset must have a README, manifest, hash manifest, validation report, and limitation ledger.
- [ ] Every output must preserve review-only/no-action boundaries.
- [ ] Metropolis/VSS lanes must distinguish: DATA_READY, STACK_READY, SAMPLE_OUTPUT_READY, and NOT_RUN.
- [ ] If credentials/API keys are needed and absent, fail honestly with AUTH_MISSING, not PASS.
