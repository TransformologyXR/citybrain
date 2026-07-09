# Learned Component Registry Snapshot Spec

The snapshot proves what Epoch 3 actually created.

Allowed entry:

- `forecast.permit_stall_v0.r1`
- `component_kind=forecast_model`
- `status=experimental`
- `consuming_surfaces=[]`
- `frozen_replay_only=true`
- `release_ledger_row=null`
- no product surface

Forbidden entries:

- ranker
- operator-facing forecast
- product forecast surface
- counterfactual learner
- case-memory learner
- dynamic investigation
- cross-city learned transfer

Output: `E3_LEARNED_COMPONENT_REGISTRY_SNAPSHOT.json`.
