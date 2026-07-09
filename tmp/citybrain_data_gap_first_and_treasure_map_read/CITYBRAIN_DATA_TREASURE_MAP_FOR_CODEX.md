# CityBrain Data Treasure Map for Codex

Generated: 2026-07-01
Purpose: Give Codex a traversal map for data-readiness, starting with data gaps and then high-value bounded pilots.
Boundary: This is a scout / landing guide only. Do not make production, public API, live monitoring, autonomous alerting, dispatch, enforcement, legal/certified, or identity/biometric claims.

## 0. Run order

1. DATA-GAP-LEDGER-AND-PRIORITY-MATRIX — run first.
2. HELSINKI-SEMANTIC-TWIN-PILOT-DATA-LANDING — strongest immediate Kit / visual-object-to-graph lane.
3. METROPOLIS-VSS-DATA-READINESS-SCOUT — readiness only; do not build VSS until corpus/runtime/EvidenceBundle mapping exists.
4. CAMERA-VIDEO-DONOR-SOURCE-SCOUT — Singapore first, Chicago as fallback, private/demo clips only if clearly labelled.
5. MOBILITY-ACCESS-OPTION-SET-GAP-BACKFILL-SCOUT — inspect M04/M05 baseline/abstain fields; do not fabricate.
6. MOBILITY-TEMPORAL-AND-SIMULATION-DATA-SCOUT — strengthen do-nothing and tradeoff moments.
7. WEB-KIT-DEMO-ASSET-DATA-BUNDLE — package only what the current Web+Kit surface needs.
8. DATA-READINESS-CLOSEOUT — produce recommendation matrix.

## 1. Immediate gap ledger

| Gap | Why it matters | Current likely status | First scout result wanted |
|---|---|---|---|
| Semantic visual-object identity | Kit needs pick visual object -> graph entity | Best source is Helsinki semantic 3D | 500-2,000 buildings + CityGML/CityJSON sample + USD sidecar |
| Video corpus for VSS/Metropolis | No video means no credible vision-AI lane | Weak / fixture only | List licensed public/demo sources + sample frames/clips + constraints |
| D8 M04 do-nothing baseline | Anti-action-bias moment | Partial unless field exists | Inspect certified option sets, classify present/missing |
| D8 M05 abstain/no-safe-option | Trust moment | Partial unless field exists | Inspect option_set_outcome presence, classify present/missing |
| Mobility temporal / simulation basis | Needed for convincing counterfactual/tradeoffs | Context fixtures exist, but maybe weak | Identify speed/count/ETA/time-series sources and attach caveats |
| Cross-city similar-case quality | “City remembers” moment needs substance | Similar cases exist | Enrich case packets: why matched, reviewed action, result/limitation |
| Web+Kit runtime bundle completeness | Live surface needs one truth | In progress | one_truth_index coverage matrix and missing render homes |
| Data licensing / attribution | External demo must cite sources | Mixed | machine-readable source/attribution ledger |

## 2. Helsinki semantic twin pilot — priority 1

### Why
Helsinki has an official semantic 3D city information model and a visual reality mesh. Use semantic buildings as identity truth and mesh only as visual backdrop.

### Official sources to traverse
- HRI Helsinki 3D models: https://hri.fi/data/en_GB/dataset/helsingin-3d-kaupunkimalli
- Helsinki 3D page: https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d
- Helsinki WFS endpoint: https://kartta.hel.fi/3d/citydb-wfs/wfs
- Helsinki 3D viewer/download service: https://kartta.hel.fi/3d/
- Kalasatama CityGML ZIP: https://3d.hel.ninja/data/citygml/Helsinki3D_CityGML_Kalasatama_20190326.zip

### Codex first commands / probes
- Fetch WFS capabilities:
  curl -L "https://kartta.hel.fi/3d/citydb-wfs/wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities" -o HELSINKI_WFS_CAPABILITIES.xml
- Count/describe bldg:Building type from capabilities.
- Fetch small sample with Count/StartIndex if supported. If WFS output format is CityGML only, do not force JSON; save XML/GML and parse identifiers.
- Download Kalasatama CityGML ZIP only if size and network are acceptable.

### Desired artifacts
- HELSINKI_SOURCE_INDEX.json
- HELSINKI_WFS_CAPABILITIES.xml
- HELSINKI_BUILDING_SAMPLE.gml or .xml
- HELSINKI_BUILDING_ID_SAMPLE.json
- HELSINKI_USD_PRIM_BINDING_SIDECAR.json
- HELSINKI_LIMITATIONS.md

### Acceptance
- At least one semantic building sample with stable identifier fields (GMLID/RATU/VTJ_PRT/internal ID where present).
- Coordinate system captured: ETRS-GK25 / EPSG:3879, N2000 height if confirmed.
- License captured: CC BY 4.0 where applicable.
- No claim that reality mesh objects are canonical entities.

## 3. Singapore / VSS / Metropolis video readiness — priority 2

### Why
The “eyes” lane needs actual video/images and output-to-EvidenceBundle mapping. Metropolis/VSS does not create data; it processes media.

### Sources to traverse
- Data.gov.sg Traffic Images dataset: https://data.gov.sg/datasets/d_6cdb6b405b25aaaacbaf7689bcc6fae0/view
- Data.gov.sg LTA agency datasets: https://data.gov.sg/datasets?agencies=Land+Transport+Authority+%28LTA%29
- Data.gov.sg status page: https://status.data.gov.sg/
- LTA DataMall: https://datamall.lta.gov.sg/content/datamall/en.html
- LTA DataMall Traffic Images v2 endpoint from guide: https://datamall2.mytransport.sg/ltaodataservice/Traffic-Imagesv2

### Codex first probes
- Try data.gov open traffic image endpoint first. If it returns deprecated/redirect, record exactly.
- If DataMall requires AccountKey, do not bypass; write `API_KEY_REQUIRED`.
- Save 3-10 image URLs or metadata rows if available.
- Do not run face/person identity inference.

### Desired artifacts
- VIDEO_SOURCE_INDEX.json
- SINGAPORE_TRAFFIC_IMAGE_SAMPLE.json
- IMAGE_LICENSE_AND_PRIVACY_NOTES.md
- VSS_METROPOLIS_READINESS_MATRIX.json
- EVIDENCEBUNDLE_MAPPING_DRAFT.json

### Acceptance
- A source can produce image/video-like content OR is clearly marked blocked by API key/terms.
- Privacy/identity boundary explicitly present.
- Output schema to CityBrain candidate observation is drafted.

## 4. Chicago similar-case + sensor/fusion donor — priority 3

### Why
Chicago is strong for similar-case memory and civic/sensor fusion, with real building violations, 311 requests, and Array of Things metadata.

### Sources to traverse
- Building Code Violations: https://data.cityofchicago.org/Buildings/Bldg-Code-Violations/e9ic-ry4z
- 311 Service Requests: https://data.cityofchicago.org/Service-Requests/311-Service-Requests/v6vf-nfxy
- Array of Things project: https://arrayofthings.github.io/
- Array of Things Locations: https://data.cityofchicago.org/Environment-Sustainable-Development/Array-of-Things-Locations/6rq2-yx28
- Chicago Data Portal: https://data.cityofchicago.org/

### Codex first probes
- Use Socrata API with $limit=5 for each dataset.
- Extract fields: address/location/date/status/violation code/inspection or request type.
- Build one similar-case packet with why-match fields.

### Desired artifacts
- CHICAGO_SOURCE_INDEX.json
- CHICAGO_CASE_SAMPLE.json
- CHICAGO_SIMILAR_CASE_PACKET_DRAFT.json
- CHICAGO_LIMITATIONS.md

### Acceptance
- At least one case packet with source refs and caveats.
- No enforcement/legal claims; historical/public data only.

## 5. NYC post-D8 target — park, do not build now

### Why
NYC is rich enough for a thick construction/compliance storyline, but it is not the current certified D8 spine. It should be parked as post-D8 intelligence expansion.

### Sources to catalog only
- NYC Open Data: https://opendata.cityofnewyork.us/
- PLUTO: https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks
- DOB Permit Issuance: https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a
- Motor Vehicle Collisions - Crashes: https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95
- EMS Incident Dispatch Data: https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj
- NYC 3D Model by Community District: https://www.nyc.gov/content/planning/pages/resources/datasets/nyc-3d-model
- NYC 3-D Building Model: https://data.cityofnewyork.us/City-Government/3-D-Building-Model/tnru-abg2

### Acceptance
- Catalog only. Do not build NYC construction hero until D8 Web+Kit surface is alive.

## 6. London resilient city candidate — scout later

### Sources
- TfL Unified API: https://tfl.gov.uk/info-for/open-data-users/unified-api
- TfL API documentation / road disruptions: https://tfl.gov.uk/info-for/open-data-users/api-documentation
- LFB Incident Records: https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy
- LFB Mobilisation Records: https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65
- London Air Quality Network API: https://www.londonair.org.uk/Londonair/API/
- LAQN API help: https://api.erg.ic.ac.uk/airquality/help

### Acceptance
- Scout only until a coherent LFB + TfL + LAQN narrative is selected.

## 7. Melbourne time-scrub candidate — scout later

### Sources
- Pedestrian counting system (search in City of Melbourne Open Data).
- On-street Parking Bay Sensors: https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/
- On-street Parking Bay Sensors API: https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/api/
- On-street Parking Bays: https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bays/

### Acceptance
- Use for time-scrub if live/near-live or historical hourly readings are easy to land.

## 8. Dubai/Makani/DLD candidate — scout only for now

### Sources
- DLD Open Data: https://dubailand.gov.ae/en/open-data/
- DLD Real Estate Data: https://dubailand.gov.ae/en/open-data/real-estate-data/
- DLD API Gateway: https://dubailand.gov.ae/en/eservices/api-gateway/
- Dubai Municipality / Makani Open Data: https://www.dm.gov.ae/open-data2/
- Data.Dubai: https://www.digitaldubai.ae/apps-services/details/data.dubai

### Acceptance
- Treat DLD/Makani as strategic, but likely blocked by API/captcha/paywall for live use. Use official export only if accessible.

## 9. What Codex should avoid

- Do not download 177GB Helsinki OBJ mesh tiles.
- Do not claim VSS/Metropolis without input media and output mapping.
- Do not use private/commercial APIs as canonical government truth unless marked third-party.
- Do not backfill M04/M05 by inventing fields.
- Do not mutate certified bundles to make UI pass.
- Do not make production/security/auth/RBAC claims.

## 10. First Codex prompt to run

Run `DATA-GAP-LEDGER-AND-PRIORITY-MATRIX` first. It should produce:
- DATA_GAP_LEDGER.json
- DATA_SOURCE_PRIORITY_MATRIX.json
- SOURCE_ACCESS_STATUS.json
- LICENSE_AND_ATTRIBUTION_LEDGER.json
- BLOCKERS_AND_DEFERRED_DATASETS.md
- NEXT_DATA_LANDING_RECOMMENDATION.md

