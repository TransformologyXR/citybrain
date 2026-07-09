# Founder Evidence-Inline Story Cards

Reading the card is the review.

## One site with permit, access, building, and infrastructure signals

Card type: Cross-domain story card

Several review signals circle one primary synthetic site: permit or inspection status, building-site context, access interruption, and nearby infrastructure context.

What signals are connected?
- Permit or inspection status is attached to the primary synthetic site.
- Building-site context also points to that primary site.
- Access interruption is linked to the same site for review.
- Infrastructure is nearby corridor context, not the same site.

Primary site: Primary synthetic site
Nearby context: Nearby infrastructure context is corridor context only; it is not treated as the same site.
Source depth: 8 inline source notes are shown for One site with permit, access, building, and infrastructure signals.

Evidence shown on the card:

- Source note: Permit/inspection status attaches to the primary site.
  - Source ref: seed-r3-expanded:permit_inspection_delay:001
  - Source class: synthetic gold
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.
- Source note: Building/site context confirms the same primary site is in the review scope.
  - Source ref: seed-r3-expanded:building_compliance:001
  - Source class: synthetic gold
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.
- Source note: Mobility access interruption participates through the repaired direct evidence packet evidence.
  - Source ref: seed-r3-expanded:mobility_access:001
  - Source class: synthetic gold
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.
- Source note: A complaint-like compliance candidate provides review context, not an official finding.
  - Source ref: seed-r3-expanded:building_compliance:003
  - Source class: synthetic challenge
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Primary synthetic site
  - Outcome: Need more before deciding; the source is only a candidate signal.
- Source note: Inspection delay remains review evidence and cannot be treated as action authority.
  - Source ref: seed-r3-expanded:permit_inspection_delay:003
  - Source class: synthetic challenge
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.
- Source note: Infrastructure context is linked as a corridor/impact edge, not as the same site entity.
  - Source ref: seed-r3-expanded:asset_infrastructure:001
  - Source class: synthetic gold
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Nearby infrastructure corridor candidate
  - Outcome: Context only; useful to watch, not enough for a same-site claim.
- Source note: evidence review should downgrade or hold when map view, freshness, or identity evidence is weak.
  - Source ref: seed-r3-expanded:mobility_access:011
  - Source class: synthetic challenge
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: UNKNOWN - geometry reference exists but no plain place label was found.
  - Outcome: Need more before deciding; the evidence is weak or stale.
- Source note: review summary and map view review can show evidence and limitations, not control or action.
  - Source ref: seed-r3-expanded:asset_infrastructure:016
  - Source class: synthetic scenario
  - Freshness: UNKNOWN - this story row has sequence order but no recent timestamp field.
  - Place/entity: Nearby infrastructure corridor candidate
  - Outcome: Ignore for now or hold; the card lacks enough data.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Need More Before Deciding
What one piece of evidence would change your decision? A recent source note with a plain place label and a human-readable reason for the link.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site - source note inlined

Card type: Single-family/example card

Building concern near a site is shown as a review-only signal with its source note visible on the card.

Place/entity: Primary synthetic site
Source depth: THIN - one inline source note is shown for Building concern near a site - source note inlined.

Evidence shown on the card:

- Source note: Building concern near a site source shows building perception candidate. Observed details: family adapter: adapter:building compliance perception candidate, overlay kind: building perception overlay, priority tier: static high.
  - Source ref: source_record:sensor:near_alpha:2026-07-07
  - Source class: replay source record
  - Freshness: 2026-07-07T02:16:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Need more before deciding; outcome detail is limited.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A named source note explaining the observed building concern and the conflict.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Permit or inspection delay - source note inlined

Card type: Single-family/example card

Permit or inspection delay is shown as a review-only signal with its source note visible on the card.

Place/entity: Primary synthetic site
Source depth: THIN - one inline source note is shown for Permit or inspection delay - source note inlined.

Evidence shown on the card:

- Source note: Permit or inspection delay source shows permit inspection delay. Observed details: family adapter: adapter:permit inspection delay, overlay kind: permit inspection timeline overlay, priority tier: static medium.
  - Source ref: source_record:permit:alpha:2026-07-01
  - Source class: replay source record
  - Freshness: 2026-07-07T03:16:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A recent permit or inspection status note with a plain site label.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Infrastructure or city asset concern - source note inlined

Card type: Single-family/example card

Infrastructure or city asset concern is shown as a review-only signal with its source note visible on the card.

Place/entity: Nearby infrastructure corridor candidate
Source depth: THIN - one inline source note is shown for Infrastructure or city asset concern - source note inlined.

Evidence shown on the card:

- Source note: Infrastructure or city asset concern source shows asset infrastructure issue. Observed details: family adapter: adapter:city asset infrastructure issue, overlay kind: asset issue map view overlay, priority tier: static medium.
  - Source ref: source_record:asset:infrastructure:fixture
  - Source class: derived fixture
  - Freshness: 2026-07-07T04:16:00Z
  - Place/entity: Nearby infrastructure corridor candidate
  - Outcome: Need more before deciding; review is required.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Need More Before Deciding
What one piece of evidence would change your decision? A source note that clarifies whether the asset is at the site or only nearby.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Access interruption - source note inlined

Card type: Single-family/example card

Access interruption is shown as a review-only signal with its source note visible on the card.

Place/entity: Primary synthetic site
Source depth: THIN - one inline source note is shown for Access interruption - source note inlined.

Evidence shown on the card:

- Source note: Access interruption source shows mobility access interruption. Observed details: family adapter: adapter:mobility access interruption, overlay kind: route access constraint, priority tier: static medium.
  - Source ref: source_record:inspection:alpha:2026-06-30
  - Source class: replay source record
  - Freshness: 2026-07-07T01:16:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Watch this, with limits; it is reviewable but not action authority.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A fresh access note showing whether the interruption is still present.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site - positive packet baseline

Card type: Single-family/example card

This diagnostic card tests positive packet baseline behavior for a building concern near a site.

Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
Source depth: THIN - one inline source note is shown for Building concern near a site - positive packet baseline.

Evidence shown on the card:

- Source note: Positive baseline card: source refs are source:v1_1:building_compliance_perception_candidate:atlas, diff:v2_5:building_compliance_perception_candidate:long_history; actual outcome was sufficient for review, expected sufficient for review, match matched direct evidence review harness.
  - Source ref: founder-probe-r2-01
  - Source class: replay
  - Freshness: UNKNOWN - this review card has source refs but no direct observation timestamp.
  - Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
  - Outcome: Watch this, with limits; it is reviewable but not action authority.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A plain source note that explains why the baseline should be watched.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site - negative no data

Card type: Single-family/example card

This diagnostic card tests negative no data behavior for a building concern near a site.

Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
Source depth: THIN - one inline source note is shown for Building concern near a site - negative no data.

Evidence shown on the card:

- Source note: No-data diagnostic card: source refs are source:v1_1:building_compliance_perception_candidate:atlas, diff:v2_5:building_compliance_perception_candidate:long_history; actual outcome stayed limited or abstained, expected abstain no data, match matched challenge boundary.
  - Source ref: founder-probe-r2-02
  - Source class: replay
  - Freshness: UNKNOWN - this review card has source refs but no direct observation timestamp.
  - Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
  - Outcome: Ignore for now or hold; the card lacks enough data.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Need More Before Deciding
What one piece of evidence would change your decision? A concrete source note with a named place and observation time.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site - stale freshness

Card type: Single-family/example card

This diagnostic card tests stale freshness behavior for a building concern near a site.

Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
Source depth: THIN - one inline source note is shown for Building concern near a site - stale freshness.

Evidence shown on the card:

- Source note: Stale-freshness diagnostic card: source refs are source:v1_1:building_compliance_perception_candidate:atlas, diff:v2_5:building_compliance_perception_candidate:long_history; actual outcome was PASS LIMITED OR ABSTAIN, expected a freshness downgrade, match matched challenge boundary.
  - Source ref: founder-probe-r2-03
  - Source class: replay
  - Freshness: UNKNOWN - this diagnostic card intentionally tests stale or missing freshness evidence.
  - Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
  - Outcome: Ignore for now or hold; the card lacks enough data.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Need More Before Deciding
What one piece of evidence would change your decision? A fresh source note or a clear reason the older note still matters.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site - contradiction pair

Card type: Single-family/example card

This diagnostic card tests contradiction pair behavior for a building concern near a site.

Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
Source depth: THIN - one inline source note is shown for Building concern near a site - contradiction pair.

Evidence shown on the card:

- Source note: Contradiction diagnostic card: source refs are source:v1_1:building_compliance_perception_candidate:atlas, diff:v2_5:building_compliance_perception_candidate:long_history; actual outcome found a conflict, expected a downgrade, match matched direct evidence review harness.
  - Source ref: founder-probe-r2-04
  - Source class: replay
  - Freshness: UNKNOWN - this review card has source refs but no direct observation timestamp.
  - Place/entity: UNKNOWN - no plain place or entity label was found in the source artifact.
  - Outcome: Need more before deciding; two claims conflict.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Need More Before Deciding
What one piece of evidence would change your decision? A human-readable tie-breaker explaining which conflicting claim to trust.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Access interruption examples

Card type: Single-family/example card

Access interruption examples are shown with two local sample notes.

Place/entity: Primary synthetic site
Source depth: 2 inline source notes are shown for Access interruption examples.

Evidence shown on the card:

- Source note: Access Constraint example: Seed R3 mobility access gold adapter event
  - Source ref: seed-r3-expanded:mobility_access:001
  - Source class: synthetic gold
  - Freshness: 2026-07-08T13:07:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Need more before deciding; outcome detail is limited.
- Source note: Transit Disruption example: Seed R3 mobility access dirty_source adapter event
  - Source ref: seed-r3-expanded:mobility_access:002
  - Source class: synthetic dirty source
  - Freshness: 2026-07-08T13:14:00Z
  - Place/entity: UNKNOWN - geometry reference exists but no plain place label was found.
  - Outcome: Need more before deciding; outcome detail is limited.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A real source note with a human place label would change trust for access interruption.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Building concern near a site examples

Card type: Single-family/example card

Building concern near a site examples are shown with two local sample notes.

Place/entity: Primary synthetic site
Source depth: 2 inline source notes are shown for Building concern near a site examples.

Evidence shown on the card:

- Source note: Site Condition example: Seed R3 building compliance gold adapter event
  - Source ref: seed-r3-expanded:building_compliance:001
  - Source class: synthetic gold
  - Freshness: 2026-07-08T16:27:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Need more before deciding; outcome detail is limited.
- Source note: Inspection Due example: Seed R3 building compliance dirty_source adapter event
  - Source ref: seed-r3-expanded:building_compliance:002
  - Source class: synthetic dirty source
  - Freshness: 2026-07-08T16:34:00Z
  - Place/entity: UNKNOWN - geometry reference exists but no plain place label was found.
  - Outcome: Need more before deciding; outcome detail is limited.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A real source note with a human place label would change trust for building concern near a site.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Permit or inspection delay examples

Card type: Single-family/example card

Permit or inspection delay examples are shown with two local sample notes.

Place/entity: Primary synthetic site
Source depth: 2 inline source notes are shown for Permit or inspection delay examples.

Evidence shown on the card:

- Source note: Permit Wait example: Seed R3 permit inspection delay gold adapter event
  - Source ref: seed-r3-expanded:permit_inspection_delay:001
  - Source class: synthetic gold
  - Freshness: 2026-07-08T19:47:00Z
  - Place/entity: Primary synthetic site
  - Outcome: Need more before deciding; outcome detail is limited.
- Source note: Inspection Backlog example: Seed R3 permit inspection delay dirty_source adapter event
  - Source ref: seed-r3-expanded:permit_inspection_delay:002
  - Source class: synthetic dirty source
  - Freshness: 2026-07-08T19:54:00Z
  - Place/entity: UNKNOWN - geometry reference exists but no plain place label was found.
  - Outcome: Need more before deciding; outcome detail is limited.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A real source note with a human place label would change trust for permit or inspection delay.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.

## Infrastructure or city asset concern examples

Card type: Single-family/example card

Infrastructure or city asset concern examples are shown with two local sample notes.

Place/entity: Nearby infrastructure corridor candidate
Source depth: 2 inline source notes are shown for Infrastructure or city asset concern examples.

Evidence shown on the card:

- Source note: Service Asset example: Seed R3 asset infrastructure gold adapter event
  - Source ref: seed-r3-expanded:asset_infrastructure:001
  - Source class: synthetic gold
  - Freshness: 2026-07-08T23:07:00Z
  - Place/entity: Nearby infrastructure corridor candidate
  - Outcome: Need more before deciding; outcome detail is limited.
- Source note: Facility Context example: Seed R3 asset infrastructure dirty_source adapter event
  - Source ref: seed-r3-expanded:asset_infrastructure:002
  - Source class: synthetic dirty source
  - Freshness: 2026-07-08T23:14:00Z
  - Place/entity: Nearby infrastructure corridor candidate
  - Outcome: Need more before deciding; outcome detail is limited.

Your call:
- [ ] Watch this
- [ ] Ignore for now
- [ ] Need more before deciding
Suggested starting point: Watch This
What one piece of evidence would change your decision? A real source note with a human place label would change trust for infrastructure or city asset concern.
Usefulness: 1 2 3 4 5
Readability: 1 2 3 4 5
Trust: 1 2 3 4 5

Founder-internal diagnostic only. No session result, fuel, training, external validation, product readiness, or customer readiness.
