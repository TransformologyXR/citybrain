# Spark VSS Command Wrapper Checklist — R6E

- [ ] command path known
- [ ] command executable by runner context
- [ ] input mode known: stdin or JSON file
- [ ] output mode known: stdout or JSON file
- [ ] timeout configured
- [ ] stderr captured safely
- [ ] non-zero exit handled as partial/fail
- [ ] secrets redacted
- [ ] output JSON parseable
- [ ] output classified as `model_generated_narrative`
- [ ] no candidate-event mutation
