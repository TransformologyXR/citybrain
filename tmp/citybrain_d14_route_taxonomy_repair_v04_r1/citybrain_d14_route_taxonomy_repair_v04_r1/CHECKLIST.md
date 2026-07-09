# Checklist

- [ ] Read v0.3 audit and remaining ambiguity report.
- [ ] Create `ROUTE_TAXONOMY_V04_ANCHOR_SET.json` from the 21 v0.3 disagreement rows with canonical labels.
- [ ] Create `ROUTE_TAXONOMY_V04_DECISION_TREE.md` with first-match rules.
- [ ] Create `ROUTE_TAXONOMY_V04_CONTRACT.json` with closed labels only.
- [ ] Relabel the full 150-row corpus under v0.4.
- [ ] Apply anchor rows deterministically; log them as adjudicated anchors, not double-label candidates.
- [ ] Export a new blind double-label sample from non-anchor rows only, stratified by route/persona.
- [ ] Stop for independent labels.
- [ ] Do not run Split/Seal R3.
- [ ] Do not open router preflight/training.
