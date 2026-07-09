# Spark VSS Endpoint Checklist — R6E

- [ ] endpoint URL known
- [ ] endpoint reachable from runner host
- [ ] auth method known, secrets not written to artifacts
- [ ] health route available or bounded probe works
- [ ] timeout configured
- [ ] max response size configured
- [ ] response JSON parseable
- [ ] response includes `source_class=model_generated_narrative`
- [ ] response does not include detection, legal, identity, or action claims
- [ ] R7 readiness gate can be derived deterministically
