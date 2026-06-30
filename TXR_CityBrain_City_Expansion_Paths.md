# TXR City Brain — City Expansion Paths

**Status date:** 2026-06-28  
**Scope:** NYC, London, Chicago, Barcelona  
**Purpose:** Define each city’s current cartridge, available expansions, next gates, and boundaries.

## Operating rule

```text
one city = one CITY-CORE cartridge
each flow = one CITY-FLOW-SUBCARTRIDGE mounted onto that core
{CITY}-F{FLOW}X-D{DAY}; X = extension on an accepted city core
```

## Executive matrix

| City | Core status | Accepted cartridge(s) | Available expansion(s) | Best next gate |
|---|---|---|---|---|
| NYC | Accepted city core | Flow 2 + Flow 3 | F1X, F4X, F5X, F6X readiness contracts | NYC-F4X-D2 |
| London | Accepted city core | Flow 2 + F3X + F4X + F5X | F6X/F7X future candidates | A9/G1 snapshot or NYC-F4X-D2 |
| Chicago | Accepted city core | Flow 1 + Flow 7 | F2X/F3X/F4X scouts green | CHI-F2X-D2 |
| Barcelona | Candidate city core | None accepted yet | D1/D1A green; all-flow D1/D2 contracts generated; F4/F7 readiness 4/4 | BARC-F4-D3 + BARC-F7-D3 |

## Standard expansion pattern

```text
D1  scout / readiness / source ledger
D2  source landing + identity/geography/join hardening
D3  flow EvidenceBundles
D4  live/replay NIM + face route
D5  hero package
D6  accepted flow-extension snapshot
```

## NYC

Current cartridge: accepted city core with Flow 2 construction/compliance and Flow 3 incident/context/operator-review accepted. Flow 3 is accepted with full-source inputs and stage limitations.

Available expansions: F1X, F4X, F5X, F6X. Recommended order: NYC-F4X-D2, NYC-F1X-D2, NYC-F5X-D2, NYC-F6X-D2.

## London

Current cartridge: accepted Flow 2 city core through D13C + LON-HERO, with UPRN/TOID/USRN/PLD identity, Local Plan context, enforcement-identity slice, live face/NIM conventions and limitations.

Accepted mounted expansions: LON-F3X, LON-F4X, and LON-F5X are accepted through `LON-FLOWX-D6` as flow-extension snapshots.

Gate ledger:

1. `LON-F3X-D2` — `PASS_SOURCE_LANDING_JOIN_HARDENING`
2. `LON-F4X-D1` — `PASS_SOURCE_SCOUT`
3. `LON-F4X-D2` — `PASS_SOURCE_LANDING_JOIN_HARDENING`
4. `LON-F5X-D1` — `PASS_SOURCE_SCOUT`
5. `LON-F5X-D2` — `PASS_SOURCE_LANDING_JOIN_HARDENING`
6. `LON-FLOWX-D3` — `PASS_EVIDENCEBUNDLES`
7. `LON-FLOWX-D4` — `PASS_LIVE_REPLAY_FACE_ROUTE_PROOF`
8. `LON-FLOWX-D5` — `PASS_HERO_FREEZE_PACKAGE`
9. `LON-FLOWX-D6` — `PASS_ACCEPTED_EXTENSION_SNAPSHOT`

Outputs: `outputs/lon_flowx_expansion_path_d2_to_d6/`; landing: `data_landing/lon_flowx_official_sources_v1/`.

Boundary: London F3X/F4X/F5X are review-only context sub-cartridges. They do not perform emergency command, fire dispatch, mobility routing, utility control, public-safety instruction, health determination, legal planning determination, or certified affected-asset claims.

## Chicago

Current cartridge: accepted Flow 1 + Flow 7 through CHI-F1F7-D5, with capped/windowed limitations.

Available expansions: CHI-F2X-D1 high with identity blockers; CHI-F4X-D1 high with key-protected live feeds; CHI-F3X-D1 medium-high context only. Recommended order: CHI-F2X-D2, CHI-F4X-D2, CHI-F3X-D2.

## Barcelona

Current cartridge: candidate city core only. BARC-D1 and BARC-D1A passed with source limitations. Flow 4 readiness is 4/4 and Flow 7 readiness is 4/4. BARC Expansion D1/D2 All Flows is green as a contract package, not an accepted cartridge.

Available expansions: BARC-D2 identity/geography spine first, then all flow D1/D2 contracts before any D3-D6 work. D1/D2 coverage now exists for F1, F2, F3, F4, F5, F6, and F7.

Recommended Barcelona order:

1. BARC-D2 candidate identity/geography spine
2. BARC-F1-D1/D2 through BARC-F7-D1/D2 all-flow contracts
3. BARC-F4-D3 and BARC-F7-D3 first dual-flow EvidenceBundles
4. Move passing flows through D4, D5, and D6 only after source and boundary gates remain green

Current D3-D6 priority: BARC-F4, BARC-F7, BARC-F1, BARC-F3, BARC-F2, BARC-F5, BARC-F6.

## Cross-city priority queue

1. CHI-F2X-D2
2. BARC-F4-D3 / BARC-F7-D3
3. NYC-F4X-D2
4. CHI-F4X-D2
5. A9/G1 application snapshot

## Management boundaries

- Do not label a D1 scout as an accepted flow cartridge.
- Do not transfer acceptance from a city core to a new flow.
- Carry forward every source limitation from the city core into the mounted flow.
- Keep Platform v1 mechanics separate from city/flow expansion work.
