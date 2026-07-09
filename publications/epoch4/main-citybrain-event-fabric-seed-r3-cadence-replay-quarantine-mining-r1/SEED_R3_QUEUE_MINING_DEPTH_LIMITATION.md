# Seed R3 Queue Mining Depth Limitation

- queue_depth = 1 unresolved + 1 quarantine per family
- classification = pipeline_proof_depth_1
- not_resolution_quality_signal = true
- requires_adapter_corpus_expansion_before_story_arc = true

This validates that the mining pipeline can classify and surface unresolved/quarantine queues. It does not provide statistically meaningful per-family resolution-quality signal.
