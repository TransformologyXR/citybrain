# ASK v1.1 Eval Sealing And Skeleton Flows

P4 seals the ASK v1.1 sprint. It adds local sealed evaluation, severity
reporting, closeout artifacts, and skeleton-only future-flow contract tests. It
does not add product behavior.

## Sealed Eval

The sealed eval exercises the implemented ASK v1.1 path over local fixture
cases. Each case records a family, query, expected boundary/intent/route or
render behavior, expected cannot-claim text, and hard-stop expectations.

Families cover:

```text
boundary_action
boundary_prediction
boundary_identity_person
board_meta
selected_item_followup
unanchored_city_ask
entity_profile
source_record_profile
patch_queue_query
external_context_need
no_data
proximity_vs_causality
candidate_inferred_link
contradiction
staleness
unsupported_template_gap
raw_query_boundary
renderer_no_undowngrade
```

## Severity

Severity uses the P0 labels:

```text
sev_0_clean
sev_1_taxonomy_reporting_only
sev_2_acceptable_but_weak
sev_3_audit_uncertain
sev_4_real_failure
```

Sev-4 is a hard failure. Boundary/action rows reaching execution, official
action claims, future-flow runtime execution, raw-query leaks, and confident
prediction/legal/finding claims are Sev-4. Sev-1 reporting-only differences do
not make a clean run look broken.

## Outputs

The eval CLI writes:

```text
outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_REPORT.json
outputs/ask_v11_sealed_eval/ASK_V11_SEALED_EVAL_SUMMARY.md
```

The report includes severity counts, family counts, boundary/action Sev-4 count,
raw-query leak count, future-flow runtime violation count, official-action claim
count, report items, limitations, and command hints.

## Skeleton Flows

ASK v1 remains the only implemented flow. WATCH, BRIEF, DIFF, and INCIDENT are
skeleton descriptors only:

```text
flow:watch_v1
flow:brief_v1
flow:diff_v1
flow:incident_v1
```

Skeletons may type-check against the general flow contract, but they have no
executor, templates, retrieval plan, action adapter, LLM call, data adapter, or
state mutation. Attempts to run them fail safely.

## Closeout

After P4, the remaining work is sprint closeout/freeze, review of generated
reports, and any future demand-led registry or template additions discovered by
real Sev-4 eval families. No production/live data claim and no official action
claim is introduced by P4.
