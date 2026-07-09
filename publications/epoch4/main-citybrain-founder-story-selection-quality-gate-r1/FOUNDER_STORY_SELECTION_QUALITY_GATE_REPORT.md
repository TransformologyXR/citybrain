# Founder Story Selection Quality Gate R1

Status: `NOT_ENOUGH_FOUNDER_GRADE_STORIES_WITH_LIMITATIONS`

## Result

Do not run founder review on the current batch unless this gate passes.

## Acceptance Bar

- minimum_main_cards: `10`
- minimum_watch_or_review_worthy: `5`
- minimum_cross_domain_cards: `2`
- minimum_honest_abstain_or_ignore_cards: `2`
- maximum_need_more_cards_in_main: `3`

## Metrics

- candidate_count: `13`
- selected_main_candidate_count: `0`
- selected_watch_or_review_worthy_count: `0`
- selected_cross_domain_count: `0`
- selected_honest_abstain_or_ignore_count: `0`
- selected_need_more_count: `0`

## Blockers

- only 0 founder-grade main candidates; need 10
- only 0 watch/review-worthy candidates; need 5
- only 0 cross-domain candidates; need 2
- only 0 honest abstain/ignore candidates; need 2

## Classification Counts

- founder_reviewable_watch_candidate: `0`
- founder_reviewable_need_more_candidate: `0`
- diagnostic_boundary_case: `7`
- negative_abstain_case: `0`
- not_reviewable_due_to_missing_place: `4`
- not_reviewable_due_to_missing_freshness: `1`
- not_reviewable_due_to_thin_source_depth: `1`
- not_reviewable_due_to_no_human_readable_consequence: `0`

## Boundary

This gate only classifies and selects candidate cards. It does not run founder review, create fuel/training rows, mutate source truth, or claim product/client readiness.
