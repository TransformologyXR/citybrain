# MAIN-CITYBRAIN-D14-TAXONOMY-REPAIR-CLOSEOUT-R1

Close out the route taxonomy repair stage.

Required outputs:
- `D14_ROUTE_TAXONOMY_REPAIR_CLOSEOUT_DECISION.json`
- `D14_ROUTE_TAXONOMY_REPAIR_README.md`
- hash manifest
- local open index

Decision must state one of:
- `PAUSED_D14_ROUTE_TAXONOMY_V02_AWAITING_INDEPENDENT_DOUBLE_LABELS`
- `PASS_D14_ROUTE_TAXONOMY_V02_DOUBLE_LABEL_STABLE_READY_FOR_SPLIT_SEAL`
- `PAUSED_D14_ROUTE_TAXONOMY_V02_STILL_AMBIGUOUS`

If independent labels have not been supplied, do not adjudicate or seal. The correct status is paused awaiting labels.

If labels are supplied and disagreement >15%, do not train router.

If labels are supplied and disagreement <=15%, produce adjudication log and allow Split/Seal R3 to proceed in a separate step.

No real operator validation claim is allowed.
