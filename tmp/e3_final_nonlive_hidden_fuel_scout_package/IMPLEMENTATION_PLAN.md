# Implementation plan

## Preflight

1. Load latest Epoch 3 chain outputs if present:
   - foundation closeout
   - master execution R1
   - L2 historical label backfill
   - L2.R2 authority preflight
   - L2.R2 offline forecast experiment
   - hidden data scout master
2. Confirm no-model guard input state.
3. Confirm non-live assumption:
   - live operator fuel program not running
   - operator-paced fuel deferred
4. Build artifact-root inventory.

## Lane execution

Run lanes independently, but do not spawn new scouts.

### Lane A

Scan likely L4 case artifacts:
- brief packets
- review state files
- workflow/session summaries
- Watch items with review metadata
- limitations/decision rows with subject/context/outcome
- similar-case outputs

Classify content strength.

### Lane B

Join candidate CHECK reports to:
- Watch items
- Brief packets
- outcome/disposition records
- limitation rows
- later decisions

Report whether descriptive scorecard is feasible.

### Lane C

Scan workflow/review-state files for:
- hold
- abstain
- needs_more
- reviewed
- dismissed/confirmed where present
- session summaries
- notes

### Lane D

Scan Watch ranking traces for:
- item families
- rank position
- throttle/cap state
- exposure linkage
- surfaced/payload evidence
- queue repeats

Do not count as R3 fuel unless verified exposure linkage is present.

### Lane E

Scan for backtestable histories:
- event duration
- queue aging
- backlog clearance
- source freshness/staleness
- inspection delay
- violation resolution
- incident duration

### Lane F

Scan for identity/graph eval candidates:
- ambiguous addresses
- duplicate entities
- UPRN/address/parcel mismatches
- edge confidence cases
- spatial containment contradictions
- affected-asset candidates

## Track 0

Produce:
- final backlog
- no-model guard
- publication-home recommendation
- decision and ledger row
- hash manifest and LF report

## Acceptance

The package is accepted if it:
- does not produce training rows
- does not create models
- emits final scout outputs for all lanes
- emits a final backlog with priority and disposition
- recommends publication-home policy
- clearly states that no more pre-closeout scouts are needed unless a human explicitly reopens scouting
