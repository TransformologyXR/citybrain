# PROMPT — MAIN-CITYBRAIN-D6-DECISION-SUPPORT-GOLDEN-QUALITY-GATE-R1

You are Codex continuing CityBrain Track S after the option-set contract, runtime interface, and hero corridor action enum.

## Task

Create the decision-support golden quality gate R1.

Task name:

`MAIN-CITYBRAIN-D6-DECISION-SUPPORT-GOLDEN-QUALITY-GATE-R1`

Expected status on success:

`PASS_MAIN_CITYBRAIN_D6_DECISION_SUPPORT_GOLDEN_QUALITY_GATE_R1_WITH_LIMITATIONS`

Expected output root:

`outputs/main_citybrain_d6_decision_support_golden_quality_gate_r1/`

Expected runner:

`scripts/run_main_citybrain_d6_decision_support_golden_quality_gate_r1.py`

## Purpose

Create a discriminating quality gate for reviewed option sets.

This gate must test more than schema, hash, secrets, and boundary. It must catch bad decision support.

## Required golden scenarios

Create a small golden fixture suite with at least these cases:

1. `golden_options_available`
   - do-nothing baseline present
   - two review-safe candidate interventions
   - shared comparison axes
   - all execution states not_executed

2. `golden_no_safe_reviewed_option`
   - option_set_outcome = no_safe_reviewed_option
   - abstain/escalate option present
   - no forced intervention

3. `golden_dominated_option_flagged`
   - an option worse on all comparable axes is flagged as dominated

4. `golden_missing_do_nothing_rejected`
   - an otherwise valid option set missing baseline is rejected

5. `golden_missing_obvious_option_flagged`
   - fixture with known expected action enum member missing is flagged

6. `golden_inconsistent_tradeoff_axes_rejected`
   - options compare on incompatible axes/units and fail

7. `golden_track_d_boundary_preserved`
   - option set references Track D proposals without redefining lifecycle

8. `golden_unsafe_auto_execute_blocked`
   - auto-execute/dispatch/control-shaped option is blocked and logged

9. `golden_stale_scenario_state_flagged`
   - valid_as_of / scenario_state_ref staleness is detected

## Required checks

Produce quality checks for:

- baseline required
- abstain allowed
- dominated option detection
- missing obvious option detection
- comparison basis consistency
- stale scenario detection
- Track D lifecycle ownership
- D4Y relationship preservation
- unsafe action blocking
- no executed state
- no legal/certified claim
- no production/public API claim

## Expected files

- `MAIN_CITYBRAIN_D6_DECISION_SUPPORT_GOLDEN_QUALITY_GATE_R1_DECISION.json`
- `README.md`
- `INPUT_ARTIFACT_INDEX.json`
- `GOLDEN_OPTION_SET_FIXTURES.json`
- `GOLDEN_QUALITY_GATE_SPEC.json`
- `GOLDEN_QUALITY_GATE_RESULTS.json`
- `QUALITY_GATE_REGRESSION_SUMMARY.json`
- `NEGATIVE_TEST_RESULTS.json`
- `CLAIM_BOUNDARY_AUDIT.json`
- `NO_ACTION_BOUNDARY_AUDIT.json`
- `NO_MUTATION_AUDIT.json`
- `SECRET_AUDIT.json`
- `HASH_MANIFEST.json`
- `LOCAL_OPEN_INDEX.md`

## Validation

Pass only if:

- Golden fixtures are generated.
- Positive cases pass.
- Negative cases fail for the expected reasons.
- Dominated option is detected.
- Missing baseline is rejected.
- Unsafe auto-execute is blocked and logged.
- Stale scenario is flagged.
- Track D ownership is preserved.
- Boundary audits pass.
- Hash validation passes.
