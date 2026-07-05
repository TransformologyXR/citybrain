# Epoch 1 Data Freshness Reconciliation

| Source Family | Status | Basis | Boundary |
| --- | --- | --- | --- |
| Event Fabric replay fixtures | sample_replay | R7/Event Fabric branches | Replay fixtures are valid for local review, not live truth. |
| perception/media evidence sources | sample_replay | Push 5 / R7/R9 evidence paths | Replay/sample media only. |
| VSS narrative sidecars | deferred_live_source | Metropolis/VSS R6-R9 branches | VSS is not a fact source. |
| CER source records | fixture_only | Push 4 CER | Candidate entity evidence only. |
| CHECK/Authority reports | fixture_only | Push 2/4 CHECK | Authority envelopes are local fixtures. |
| spatial overlays | sample_replay | Push 5 Spatial UI | Overlay data is local/replay. |
| federation synthetic/Dubai pack | synthetic | Push 7 Federation | Synthetic/Dubai pack makes no real Dubai claim. |
| external/public/live sources | unknown_needs_refresh_policy | Track 0 / Data | No live current-truth guarantee. |
