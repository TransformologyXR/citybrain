# TXR City Brain - City Core / Flow Sub-Cartridge Model

**Status:** Operating model update
**Purpose:** Replace "one city = one cartridge" with a reusable city-core plus flow expansion slots.

## Decision

Stop treating each new city-flow pair as a fresh city build.

The platform now slots work as:

```text
one city = one city core cartridge
each flow = one flow sub-cartridge mounted onto that city core
```

NYC, London, and Chicago should not be rebuilt from zero when a new flow is added. Their accepted identity, geography, source ledgers, evidence style, face routes, NIM routes, and claim boundaries become the reusable city core. New work should add only the flow-specific sources, joins, EvidenceBundles, replay/live proof, and hero/freeze gates.

## Slot Types

### CITY-CORE

- Native IDs
- Geography and boundaries
- Source ledger
- Base evidence style
- Face/NIM route conventions
- Accepted limitations

### CITY-FLOW-SUBCARTRIDGE

- Extra flow-specific sources
- Flow-specific joins
- Flow-specific EvidenceBundles
- Flow-specific replay/live proof
- Flow-specific hero/freeze gate

## Naming Convention

Use:

```text
{CITY}-F{FLOW}X-D{DAY}
```

The `X` means extension on an already-existing accepted city core, not a fresh city build.

Examples:

| Name | Meaning |
|---|---|
| `CHI-F2X-D1` | Chicago Flow 2 expansion scout |
| `CHI-F3X-D1` | Chicago Flow 3 expansion scout |
| `LON-F3X-D1` | London Flow 3 expansion scout |
| `NYC-F4X-D1` | NYC Flow 4 expansion scout |

## Current Accepted Flow Coverage

| City core | Accepted / planned flow coverage | Notes |
|---|---|---|
| NYC | Flow 2 + Flow 3 accepted | Flow 3 accepted with full-source inputs and stage limitations in `f3_nyc_d9full_flow3_accepted_snapshot`. |
| London | Flow 2 accepted; `LON-F3X-D1` source scout green | D13C + LON-HERO form the accepted London core; Flow 3 source/API scout passed, but London Flow 3 is not accepted yet. |
| Chicago | Flow 1 + Flow 7 accepted | CHI-F1F7-D5 accepted with capped-source limitations and explicit no-overclaim boundaries. |
| Singapore | Flow 4 planned / authenticated API proof blocked | SG-D1 exists as a source/API scout, but authenticated live API proof is not the accepted Flow 4 gate. |
| Barcelona | New scout candidate | Treat as a fresh city-core candidate until a native-ID/geography/source-ledger core exists. |

## London Expansion Potential

London has a strong accepted Flow 2 core and unusually good source coverage for Flow 3, Flow 4, and Flow 5. The next London work should be flow sub-cartridges, not a third full London build.

### `LON-F3X-D1` - London Resilience / Fire-Incident Context Expansion

**Current gate:** `PASS_SOURCE_SCOUT`.

**Artifacts:** `outputs/lon_f3x_d1_london_resilience_fire_incident_context_scout/`.

**Next gate:** `LON-F3X-D2` official LFB schema/sample landing and join-map hardening.

**Candidate strength:** very high.

**Mounts onto:** accepted London Flow 2 core: UPRN / TOID / USRN, PLD planning corpus, Local Plan context, enforcement-identity slice, live face, live NIM, and accepted limitations.

**Extra sources:**

- London Fire Brigade incident records
- London Fire Brigade mobilisation records
- TfL disruptions / arrivals / line status
- London Air Quality Network
- Environment Agency flood warnings / water levels where relevant to incident context

**Flow boundary:**

- Review-only incident / affected-context briefing.
- Not emergency command.
- Not fire dispatch.
- Not operational public-safety instruction.

**Why this is strongest:** LFB incident and mobilisation records provide an official incident/resource context; TfL provides realtime/status mobility context; London Air and EA flood data add environmental context. This is the cleanest London expansion because it reuses London's accepted identity and evidence style while adding a new incident/context layer.

### `LON-F4X-D1` - London Mobility / Environment Expansion

**Candidate strength:** very high.

**Extra sources:**

- TfL Unified API
- Live arrivals / line status / disruptions
- London Air Quality Network
- EV / charging context already partly used in London Flow 2
- Event/crowd sources if found and bounded

**Flow boundary:**

- Mobility/environment context and review planning only.
- No public-order claim.
- No crowd-control instruction.
- No emergency dispatch or operational command claim.

### `LON-F5X-D1` - London Flood / Climate Risk Context Expansion

**Candidate strength:** high.

**Extra sources:**

- Environment Agency flood-monitoring API
- Flood warnings / flood alerts
- Flood areas
- Water levels and flows
- London flood-risk layers
- London air/emissions/noise context
- Energy/smart-meter sample datasets if bounded

**Flow boundary:**

- Risk context, not certified infrastructure failure propagation.
- No utility-control claim.
- No emergency-response claim.

## London Recommendation

Run / continue these London extension scouts:

1. `LON-F3X-D2` - LFB schema/sample landing and join-map hardening after the green D1 scout
2. `LON-F4X-D1` - mobility/environment
3. `LON-F5X-D1` - flood/climate risk

Do not reopen the London core unless the flow scout proves a missing core dependency. The success condition for each scout is a bounded source ledger, join map, EvidenceBundle contract, replay/live proof plan, and explicit freeze gate.

## Source Verification Notes

- [London Datastore - LFB incident records](https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy) says the dataset covers every LFB-attended incident since 1 January 2009.
- [London Datastore - LFB mobilisation records](https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65) says the dataset covers every pumping-appliance mobilisation to an incident since January 2009.
- [TfL Unified API documentation](https://tfl.gov.uk/info-for/open-data-users/api-documentation) says the Unified API provides realtime and status information across transport modes in one consistent API.
- [London Air Quality Network API](https://www.londonair.org.uk/Londonair/API/) says London air-quality information is available in structured XML/JSON feeds.
- [Environment Agency flood-monitoring API reference](https://environment.data.gov.uk/flood-monitoring/doc/reference) documents current flood warnings, flood areas, and related flood-monitoring endpoints; [api.gov.uk](https://www.api.gov.uk/ea/flood-monitoring/) also describes monitored water levels and flows.
