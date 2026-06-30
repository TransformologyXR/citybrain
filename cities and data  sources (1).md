Yes — treat each city as a **donor package**, not as the “one city” for the demo. The strongest set now looks like:

**NYC, London, Helsinki, Amsterdam / Netherlands, Dubai**
plus top three additional donor cities: **Singapore, Chicago, Melbourne**.

The idea is to harvest each city for what it is best at, then normalize everything into the same **CityBrain canonical schema**.

# 0. Cross-city base layers we can use everywhere

These are not city-specific, but they make every city usable.

| Layer                         | Sources                                      | What we can use it for                                                                                                                                                                                                                                  |
| ----------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Open map / transport / places | **Overture Maps**, OpenStreetMap / Geofabrik | Roads, places, buildings, admin divisions, transportation graph, stable IDs, POIs, global base layer. Overture explicitly positions itself as free open map data with stable IDs and location grounding for AI systems. ([Overture Maps Foundation][1]) |
| Building footprints / heights | Microsoft Global ML Building Footprints      | Fill building gaps, generate 3D massing, estimate floor area, assign occupancy and energy archetypes. Microsoft’s dataset includes global building footprints and height estimates from imagery. ([GitHub][2])                                          |
| Population / occupancy priors | WorldPop                                     | Day/night demand, pedestrian priors, evacuation demand, vulnerable-population overlays, service demand. WorldPop provides open high-resolution population distribution data, including 100m gridded estimates. ([hub.worldpop.org][3])                  |
| Weather / climate stress      | ERA5 / Open-Meteo                            | Heatwaves, rainfall, wind, humidity, flood triggers, energy-demand drivers. ERA5 provides hourly global weather/climate reanalysis from 1940 onward. ([Climate Data Store][4])                                                                          |

These become the **global substrate**. City-specific data then adds operational truth.

---

# 1. New York City — strongest “full urban operating system” donor

NYC is probably the richest single-city dataset for a CityBrain demo because it has geometry, buildings, land use, emergency response, 311, permits, traffic, transit, collisions, energy, water and inspections.

| Harvest layer                        | What exists                                                                                                                                    | What we can do with it                                                                                                                          |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 3D city / buildings                  | NYC 3D Building Model and NYC 3D Model by Community District. The model represents every building in NYC present in 2014. ([NYC Open Data][5]) | Build a semantic OpenUSD city scene; attach every building to graph IDs; run 3D emergency, energy, shadow, evacuation and inspection scenarios. |
| Parcels / land use                   | PLUTO gives extensive land-use and geographic data at tax-lot level, with 70+ fields. ([NYC Open Data][6])                                     | Create parcel → building → owner/use/zoning graph; link complaints, permits, energy, collisions and emergency response to lots.                 |
| Elevation / flood geometry           | NYC 1-foot DEM from LiDAR ground returns. ([NYC Open Data][7])                                                                                 | Flood exposure, drainage/stormwater modelling, evacuation routing, low-lying road/building risk.                                                |
| 311 service requests                 | 311 Service Requests from 2020 to Present. ([NYC Open Data][8])                                                                                | Citizen-report ingestion, issue clustering, agency routing, SLA prediction, duplicate detection, complaint-to-action workflows.                 |
| Building permits / filings           | DOB NOW Build job application filings and DOB permit-related datasets. ([NYC Open Data][9])                                                    | Construction lifecycle, permit-compliance reasoning, construction-impact scenarios, violation prediction.                                       |
| DOB complaints / housing enforcement | DOB complaints and HPD building-related datasets. ([NYC Open Data][10])                                                                        | Building-risk graph: complaint → building → permit → inspection → enforcement priority.                                                         |
| Traffic speeds                       | DOT Traffic Speeds. ([NYC Open Data][11])                                                                                                      | Congestion state, incident detection, speed-drop profiles, emergency route ETA, traffic simulation calibration.                                 |
| Traffic counts                       | Historical traffic volume counts. ([NYC Open Data][12])                                                                                        | SUMO calibration, arterial demand, peak/off-peak profiles, road-capacity constraints.                                                           |
| Collisions                           | Motor Vehicle Collisions / crash records. ([NYC Open Data][13])                                                                                | Road-safety risk, crash hot spots, vulnerable-user analytics, pre-positioning response assets.                                                  |
| EMS dispatch                         | EMS Incident Dispatch Data generated by EMS computer-aided dispatch. ([NYC Open Data][14])                                                     | Response-time modelling, ambulance dispatch optimisation, congestion impact on emergency response.                                              |
| Fire dispatch                        | Fire Incident Dispatch Data generated by FDNY CAD systems. ([NYC Open Data][15])                                                               | Fire-station coverage, mobilisation modelling, response optimisation, building-risk linkage.                                                    |
| Taxi / FHV trips                     | NYC TLC trip records.                                                                                                                          | Origin-destination demand, land-use activity signatures, airport/downtown/nightlife behaviour templates.                                        |
| Subway OD                            | MTA subway origin-destination ridership.                                                                                                       | Transit load, station crowding, disruption response, crowd/evacuation simulation.                                                               |
| Building energy/water                | NYC Building Energy and Water Data Disclosure for Local Law 84. ([NYC Open Data][16])                                                          | Building benchmarking, heatwave demand stress, retrofit prioritisation, water/energy risk.                                                      |
| Public events                        | Permitted events datasets.                                                                                                                     | Event impact: crowding, road closures, sanitation, emergency access, transit demand.                                                            |
| Health inspections                   | Restaurant inspection results.                                                                                                                 | Inspection prioritisation, complaint-to-risk scoring, public-health operations.                                                                 |
| Waste / sanitation                   | DSNY and sanitation-related datasets.                                                                                                          | Waste-routing, event sanitation, 311 cleanliness complaints, depot optimisation.                                                                |

**Best NYC demo:**
**“Urban Operations Agent”** — a construction complaint, road disruption and EMS/fire response delay all converge around one building/parcel. The CityBrain links 311, DOB, PLUTO, traffic speeds, EMS/FDNY dispatch and 3D building context into one evidence-backed action plan.

---

# 2. London — best UK-relevant resilience and transport operations donor

London is excellent for transport operations, emergency/fire response, household energy, road safety, air quality and flood/environment scenarios. It is also strategically relevant because the NVIDIA role is UK-based.

| Harvest layer                    | What exists                                                                                                                                                           | What we can do with it                                                                                        |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Live transport / multi-modal API | TfL Open Data and Unified API cover live feeds and data downloads across transport modes. TfL recommends the Unified API for live feeds. ([Transport for London][17]) | Live transport-state layer, route status, disruptions, station status, bus/tube/road operational view.        |
| Road disruptions                 | TfL active road disruptions and road-event data. ([Transport for London][17])                                                                                         | Roadworks/incident event stream, impact analysis, rerouting, construction-road interface.                     |
| Cycling network                  | TfL cycle-route data in JSON/KML with route metadata and status. ([Transport for London][17])                                                                         | Active-travel graph, cyclist safety, road-space planning, event/crowd diversion.                              |
| Fire incidents                   | London Fire Brigade Incident Records contain details of every incident attended since January 2009. ([London Datastore][18])                                          | Fire-risk analytics, incident patterns, building/road accessibility, response modelling.                      |
| Fire mobilisation                | LFB Mobilisation Records contain appliance deployments, station, and arrival times since January 2009. ([London Datastore][19])                                       | Fire-engine dispatch optimisation, station coverage, congestion impact on arrival time.                       |
| Household smart-meter energy     | Low Carbon London smart-meter dataset: 5,567 households, half-hour readings, ~167 million rows. ([London Datastore][20])                                              | Residential demand curves, heatwave electricity stress, demand-response scenarios, district energy behaviour. |
| Air quality                      | London Air Quality Network provides current pollution readings and modelling; LAQN has many monitoring sites across London. ([London Air][21])                        | Pollution exposure, traffic-air-quality coupling, vulnerable-population advisory, school/hospital risk.       |
| Road safety / collisions         | UK STATS19 / road safety open data gives detailed personal-injury collision records for Great Britain. ([GOV.UK][22])                                                 | Road safety hot spots, emergency response, vulnerable-user risk, intervention targeting.                      |
| Flood warnings / hydrology       | Environment Agency flood monitoring APIs can provide flood warning and river-level style data for England.                                                            | Flood-risk workflow, transport disruption, emergency rerouting, vulnerable assets.                            |
| Station / transit demand         | TfL and transport datasets can support station crowding and service-disruption narratives.                                                                            | Crowd flow, transit disruption, major-event response, emergency evacuation.                                   |
| Borough-level civic datasets     | London borough open data can add local 311-like service requests, planning, air-quality and public-realm data where available.                                        | Local service operations, complaint routing, public-realm maintenance.                                        |

**Best London demo:**
**“Resilient City Command”** — road disruption + fire mobilisation + air-quality spike + heat/energy demand. The CityBrain recommends emergency routing, public advice and asset/resource actions.

---

# 3. Helsinki — best semantic 3D digital-twin donor

Helsinki is one of the strongest **digital-twin / 3D semantic city** donors. It may not beat NYC on operational dataset variety, but it is excellent for showing a serious OpenUSD / semantic city-twin foundation.

| Harvest layer                      | What exists                                                                                                                                                                                      | What we can do with it                                                                                                 |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| 3D city model / digital twin       | Helsinki 3D city models are described as the city’s digital twin, combining information technology services, open data and constantly updating information. ([Helsingin kaupunki][23])           | Convert/represent semantic 3D assets in OpenUSD; show that buildings, terrain and urban objects map to graph entities. |
| Semantic city model + reality mesh | HRI notes two next-generation 3D models: a semantic city information model and a high-quality reality mesh model. ([Avoimen datan palvelu][24])                                                  | Demonstrate “visual twin + semantic twin” separation: pretty mesh for view, semantic model for reasoning.              |
| Open geospatial data               | Most map/geographic datasets maintained by Helsinki’s Urban Environment Division are made freely available. ([Helsingin kaupunki][25])                                                           | Roads, buildings, public spaces, urban assets, GIS layers, service areas.                                              |
| HRI open-data catalogue            | Helsinki Region Infoshare has hundreds of datasets, APIs and applications across maps, traffic/tourism, constructed environment, housing, government and services. ([Avoimen datan palvelu][26]) | General city graph enrichment: services, housing, traffic, environment, municipal assets.                              |
| Traffic measurements               | Helsinki traffic data includes motor traffic volume, speed and vehicle-type counts, in CSV, WFS/WMS and JSON API formats. ([Avoimen datan palvelu][27])                                          | Traffic-state generation, SUMO calibration, congestion/incident scenarios.                                             |
| Transit data                       | HSL offers open data via API services and data packages. ([HSL.fi][28])                                                                                                                          | Transit schedules, stops, routes, service disruption, station catchment modelling.                                     |
| Environmental data                 | HSY provides open environmental/geographic data and map services. ([hsy.fi][29])                                                                                                                 | Air quality, environmental monitoring, waste/water/environment layers depending on selected datasets.                  |
| Cycling / pedestrian data          | Helsinki-area open-data catalogues include cycling and pedestrian traffic datasets. ([avoindata.suomi.fi][30])                                                                                   | Active mobility, crowd/footfall, pedestrian/cycle safety.                                                              |
| Service-map style data             | Helsinki region public-service datasets can map schools, health, libraries, public facilities and amenities.                                                                                     | Vulnerable/public asset overlay, emergency planning, civic service navigation.                                         |

**Best Helsinki demo:**
**“Semantic 3D CityBrain”** — every visible object in the twin resolves to an entity in the graph, and live/synthetic traffic, transit, environmental and service data attach to those entities.

---

# 4. Amsterdam / Netherlands — best national open-geo + traffic + parking + API fabric

Amsterdam is useful, but I would treat it as **Amsterdam + Netherlands national data infrastructure**, not Amsterdam alone. The Netherlands gives you BAG, 3DBAG, PDOK, NDW and national transit feeds.

| Harvest layer                           | What exists                                                                                                                                                       | What we can do with it                                                                                               |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Amsterdam municipal data platform       | Data.amsterdam.nl is the municipality’s data foundation and central place for objective, reliable and current data about Amsterdam. ([Data Amsterdam][31])        | Municipal data hub, neighbourhood profiles, public-space data, policy and operational datasets.                      |
| Amsterdam APIs / geo-services           | Amsterdam’s API platform exposes DSO APIs and geo-services; API keys are becoming required for those APIs. ([api.data.amsterdam.nl][32])                          | Programmatic ingestion into CityBrain; structured municipal entity feeds; test API-key/partner-style access pattern. |
| Amsterdam open geodata                  | Amsterdam Maps Data publishes open geographic datasets. ([maps.amsterdam.nl][33])                                                                                 | Public-space assets, geospatial layers, urban features, spatial joins.                                               |
| 3D buildings: 3DBAG                     | 3DBAG is open data with up-to-date 3D building models for the Netherlands, generated from BAG building data and AHN height data. ([docs.3dbag.nl][34])            | Excellent 3D/OpenUSD source; building heights, LoD models, exposure modelling, energy/flood/shadow.                  |
| PDOK national geo datasets              | PDOK exposes national datasets including BAG addresses/buildings, BGT topography, BRK cadastre and other high-value datasets. ([pdok.nl][35])                     | Strong canonical entity layer: address, building, topography, cadastral references, roads, public space.             |
| Amsterdam real-time traffic             | Amsterdam has real-time traffic data refreshed every 5 minutes for car travel times on the main road network. ([Data.gov.nl][36])                                 | Congestion state, travel-time prediction, routing, event impact.                                                     |
| Netherlands NDW traffic                 | NDW is a national collaboration for collecting, managing and sharing traffic data; its open portal includes real-time and historical data. ([english.ndw.nu][37]) | High-frequency speed/flow/travel-time donor, traffic safety, roadworks, incident modelling.                          |
| Parking geometry                        | Amsterdam on-street parking spaces are available as WFS/WMS, including normal and special parking spaces. ([Data.gov.nl][38])                                     | Kerbside management, parking occupancy simulation, EV loading/unloading, enforcement workflows.                      |
| Public transport                        | Netherlands-wide GTFS feeds are available through OVapi / MobilityDatabase-style sources. ([Mobility Database][39])                                               | Transit network, multimodal routing, transit disruption, station accessibility.                                      |
| Roadworks / floating-car data ecosystem | Dutch road authorities have real-time roadworks / floating-car data initiatives, including Amsterdam / NDW use cases. ([DS4SSCC][40])                             | Roadworks-to-traffic impact, construction/routing scenarios, live mobility digital twin.                             |
| Energy / sustainability                 | Dutch national statistics and municipal sustainability datasets can support energy and emissions context.                                                         | District energy, building-efficiency, climate-planning overlays.                                                     |

**Best Amsterdam / Netherlands demo:**
**“3D + Mobility + Kerbside Twin”** — 3DBAG buildings, Amsterdam parking/kerbside geometry, NDW traffic, transit GTFS and roadworks combine into a real operational mobility/urban-planning twin.

---

# 5. Dubai — best property / permit / Middle East smart-city narrative donor

Dubai should not be the only anchor, but it remains valuable because it aligns with your TXR / DM–DLD story and gives the demo Middle East/government relevance.

| Harvest layer                 | What exists                                                                                                                                                                                          | What we can do with it                                                                                 |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Unified open-data environment | Data.Dubai brings together official statistics, open/shared datasets and analytics tools for data-driven decision-making. ([Digital Dubai][41])                                                      | Source registry, provenance layer, Dubai scenario credibility, government-data narrative.              |
| DLD real-estate data          | Dubai Land Department open data includes transactions, rents, projects, valuations, land, building, unit, brokers and developers. ([Dubai Land Department][42])                                      | DM–DLD canonical graph: land → building → unit → project → developer → transaction/rent/valuation.     |
| Dubai Municipality open data  | DM lists building permits, demolition permits, building usages, floor-level info, building summary info, project applications, service transactions and related datasets. ([Dubai Municipality][43]) | Permit/compliance scenario, building lifecycle, inspection/document generation, municipal operations.  |
| Building-permit datasets      | Building-permit datasets are exposed via UAE/Dubai open-data channels such as Bayanat/Dubai Pulse. ([Bayanat][44])                                                                                   | Permit schema grounding, contractor/consultant workflows, construction compliance.                     |
| RTA GTFS                      | Dubai RTA GTFS feed is catalogued through Transitland, sourced from Dubai Pulse / RTA. ([Transitland][45])                                                                                           | Transit layer: metro/tram/bus routes/stops/schedules, accessibility, disruption scenarios.             |
| DEWA water production/supply  | Dubai Pulse exposes daily DEWA water production and daily water supply API datasets. ([Dubai Pulse][46])                                                                                             | Water-demand calibration, district water scenario, supply/demand stress, EPANET aggregate constraints. |
| DEWA annual statistics        | DEWA annual statistics provide power/water technical statistics. ([Bayanat][47])                                                                                                                     | Aggregate energy/water calibration, demand realism, utility KPIs.                                      |
| Dubai Police open data        | Dubai Police has an open-data portal; UAE open-data sources also point to traffic accidents, safety and law datasets. ([Dubai Police][48])                                                           | Public-safety schemas, accident categories, incident taxonomies, safety dashboards.                    |
| Traffic-accident data         | UAE/Bayanat search results include traffic accidents by type and cause. ([Bayanat][49])                                                                                                              | Accident-risk taxonomy, safety scenario, road-risk overlays.                                           |
| Dubai Here / GeoDubai concept | Dubai’s city mapping/digital-twin ecosystem validates the geometry + assets + services story.                                                                                                        | Use as conceptual alignment, but avoid claiming access to confidential systems.                        |

**Best Dubai demo:**
**“DM–DLD Urban Compliance Agent”** — parcel/building/unit/project/developer/permit/transaction data are resolved into one canonical entity graph, then a construction/inspection/road-impact scenario runs against it.

**Important boundary:** Dubai is excellent for real-estate, building, permit, transit and aggregate utility context, but detailed high-frequency traffic counts, live camera feeds and granular utility load curves are not as openly available as NYC/London/Singapore. Dubai should be a **premium scenario**, not the whole data foundation.

---

# 6. Additional top city #1 — Singapore

Singapore is one of the best “real-time smart-city API” donors, especially for transport, maps, weather, air quality and operational APIs.

| Harvest layer                              | What exists                                                                                                                                           | What we can do with it                                                                             |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| National open-data portal                  | Data.gov.sg has thousands of datasets from many government agencies, with APIs and real-time datasets. ([data.gov.sg][50])                            | Broad API-driven government data ingestion pattern.                                                |
| Transport APIs                             | LTA DataMall publishes static, dynamic and real-time land-transport datasets for developers, researchers and the public. ([DataMall][51])             | Traffic incidents, traffic images, bus arrivals, transport analytics, road-state event generation. |
| Traffic images                             | Data.gov.sg exposes LTA Traffic Images API. ([data.gov.sg][52])                                                                                       | Real camera-style visual donor, congestion/lighting/weather validation, Metropolis-style “eyes.”   |
| OneMap                                     | OneMap is Singapore’s authoritative national map platform, with search, reverse geocode, population and thematic APIs. ([OneMap][53])                 | Authoritative geocoding, address/entity grounding, amenity/service layers, demographic overlays.   |
| Weather / rainfall                         | Data.gov.sg real-time APIs include rainfall, PSI, PM2.5, humidity, wind and other NEA feeds; rainfall can be 5-minute readings. ([DataGovSG API][54]) | Flood triggers, heat/air-quality scenarios, weather-to-traffic/energy stress.                      |
| Air quality                                | NEA PM2.5 / PSI APIs. ([data.gov.sg][55])                                                                                                             | Public-health alerts, traffic pollution, outdoor activity guidance.                                |
| Demographics                               | OneMap and SingStat-style data can provide planning-area / subzone demographics. ([Urban Analytics Lab | Singapore][56])                              | Exposure, service demand, school/hospital/public facility planning.                                |
| Housing / construction / public facilities | HDB, BCA and other agency data via data.gov.sg.                                                                                                       | Housing estate scenarios, built-environment compliance, community services.                        |

**Best Singapore demo:**
**“Real-Time Transport + Environment AI Agent”** — live-style traffic image/event + rainfall/air-quality/weather + OneMap geospatial context + routing recommendation.

---

# 7. Additional top city #2 — Chicago

Chicago is excellent for **municipal operations + sensors + permits/violations + energy + public safety**.

| Harvest layer                                       | What exists                                                                                                                                           | What we can do with it                                                                        |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| City open-data portal                               | Chicago Data Portal includes 311 service requests and broad civic datasets. ([Chicago][57])                                                           | Civic operations, service requests, complaint routing, SLA prediction.                        |
| Building permits / violations                       | Chicago has building permit, inspection and violation records searchable through city systems and datasets. ([City of Chicago][58])                   | Building compliance graph, inspection optimisation, enforcement prioritisation.               |
| Energy benchmarking                                 | Chicago Energy Benchmarking covers municipal, commercial and residential buildings larger than 50,000 sq ft under the city ordinance. ([Chicago][59]) | Building energy risk, retrofit prioritisation, emissions/heatwave scenario.                   |
| Traffic crashes                                     | Chicago Data Portal includes traffic crash datasets.                                                                                                  | Road safety, collision hot spots, emergency-response risk.                                    |
| CTA transit data                                    | CTA publishes static GTFS, real-time Bus Tracker / Train Tracker APIs and service alert data. ([CTA][60])                                             | Transit state, disruption scenarios, multimodal movement.                                     |
| Divvy bike trips                                    | Divvy trips include origin, destination and timestamps. ([Data.gov][61])                                                                              | Cycling demand, micromobility, active-transport flows.                                        |
| Array of Things                                     | AoT is an urban measurement system with programmable sensor nodes and local analytics such as vehicle counting. ([Array of Things][62])               | Multi-sensor city observability, environmental/sound/traffic sensing, sensor-to-graph fusion. |
| Air quality sensors                                 | Open Air Chicago is a citywide network of 277 air sensors for PM2.5 and NO2. ([City of Chicago][63])                                                  | Hyperlocal air-quality monitoring, environmental justice, school/hospital exposure.           |
| Crime / public safety                               | Chicago has rich public-safety and crime datasets.                                                                                                    | Safety-risk maps, response planning, event/security scenarios.                                |
| Public assets / roads / bike racks / traffic counts | Chicago transportation GIS and open data can add road assets and city infrastructure.                                                                 | Asset graph enrichment, maintenance/inspection routing.                                       |

**Best Chicago demo:**
**“Civic Service + Sensor Fusion Brain”** — 311 complaints, building violations, energy benchmarking, air-quality sensors and transit/traffic data combine into an evidence-backed inspection and public-health action plan.

---

# 8. Additional top city #3 — Melbourne

Melbourne is not as broad as NYC, but it is very strong for **pedestrian/crowd, parking, transport and urban sensor behaviour**.

| Harvest layer                             | What exists                                                                                                                                        | What we can do with it                                                                  |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| City open data                            | City of Melbourne says its open datasets cover real-time pedestrian counters, available parking bays and urban datasets. ([City of Melbourne][64]) | Smart-city sensor ingestion pattern, public-realm operations.                           |
| Pedestrian counts                         | Hourly pedestrian counts from sensors since 2009, updated monthly. ([CoM Open Data Portal][65])                                                    | Crowd-flow donor, event surge curves, station/public-space footfall, pedestrian safety. |
| Pedestrian sensor locations               | Sensor locations include status, location and directional information. ([Data.Vic][66])                                                            | Map sensors to streets/places; generate camera/sensor placements.                       |
| Parking sensors                           | In-ground parking bay sensors record vehicle arrival/departure and occupancy status with spatial coordinates. ([CoM Open Data Portal][67])         | Kerbside occupancy, parking search traffic, enforcement, delivery/loading management.   |
| Parking bays geometry                     | On-street parking bay geometry and bay data. ([CoM Open Data Portal][68])                                                                          | Kerbside digital twin, curb allocation, parking/EV/loading scenarios.                   |
| Microclimate sensors                      | City datasets include historical microclimate readings and sound sensor data. ([data.gov.au][69])                                                  | Heat, comfort, noise, crowd/environment correlations.                                   |
| Traffic counts                            | Victorian transport open data includes traffic volume at signal locations, aggregated into 15-minute periods. ([Open Data Victoria][70])           | Traffic simulation calibration, congestion patterns, road/intersection state.           |
| Public transport GTFS / GTFS-RT           | Victoria provides static GTFS schedule and GTFS-Realtime for metro trains, trams and buses. ([Open Data Victoria][71])                             | Transit state, disruption/crowding, tram/train/bus scenarios.                           |
| Road crash data                           | Victorian road crash datasets date back to 1987. ([catalogue.data.infrastructure.gov.au][72])                                                      | Safety analytics, pedestrian/cyclist risk, intervention targeting.                      |
| City assets / POIs / population forecasts | Melbourne datasets include places of interest and population forecasts. ([data.gov.au][69])                                                        | Service demand, event planning, public-space operations.                                |

**Best Melbourne demo:**
**“Crowd + Kerbside + Transit Operations”** — pedestrian counts, parking occupancy, tram/train data, traffic counts and event/weather context drive a public-realm operating agent.

---

# 9. How I would use each city in the final demo portfolio

| City                        | Use as                                                 | Why                                                                                               |
| --------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| **NYC**                     | Master operational-city donor                          | Richest cross-domain stack: 3D buildings, parcels, 311, permits, traffic, EMS/fire, energy/water. |
| **London**                  | UK resilience / emergency / energy donor               | Strong relevance to UK role; excellent TfL, LFB, smart-meter and air-quality data.                |
| **Helsinki**                | Semantic 3D digital twin donor                         | Best for showing serious city-model semantics and OpenUSD-style digital twin thinking.            |
| **Amsterdam / Netherlands** | 3D + traffic + kerbside donor                          | 3DBAG, PDOK/BAG, NDW traffic, Amsterdam APIs and parking geometry.                                |
| **Dubai**                   | Middle East / DM–DLD / real-estate-government scenario | Strong for property, building, permit, DLD/DM entity graph and your personal story.               |
| **Singapore**               | Real-time smart-city API and traffic-camera donor      | Best for live transport APIs, authoritative map API, weather, rainfall and air quality.           |
| **Chicago**                 | Municipal sensor + civic operations donor              | 311, permits/violations, energy benchmarking, Array of Things and air sensors.                    |
| **Melbourne**               | Crowd / pedestrian / parking sensor donor              | Excellent long-term footfall, kerbside and transport sensor data.                                 |

# 10. My recommended harvest order

For the first build, I would not try to ingest all eight cities. I would harvest in this order:

1. **NYC core graph pack** — 3D buildings, PLUTO, 311, DOB, traffic, EMS/fire, collisions, energy/water.
2. **London resilience pack** — TfL, LFB, smart meters, air quality, road safety.
3. **Helsinki or Amsterdam 3D pack** — Helsinki semantic 3D or Netherlands 3DBAG/PDOK.
4. **Singapore perception/API pack** — LTA traffic images/incidents + OneMap + rainfall/air quality.
5. **Dubai DM–DLD pack** — DLD real estate + DM building/permit data + RTA GTFS + DEWA aggregates.
6. **Chicago/Melbourne specialist packs** — Chicago for civic/sensor/energy; Melbourne for crowd/kerbside.

The clean demo message becomes:

**Real city behaviours from the world’s best open-data cities, normalized into one CityBrain schema, then replayed through NVIDIA-accelerated simulation, graph reasoning, optimisation and operator agents.**

[1]: https://overturemaps.org/?utm_source=chatgpt.com "Home - Overture Maps Foundation"
[2]: https://github.com/microsoft/globalmlbuildingfootprints?utm_source=chatgpt.com "microsoft/GlobalMLBuildingFootprints: Worldwide building ..."
[3]: https://hub.worldpop.org/project/categories?id=3&utm_source=chatgpt.com "WorldPop :: Population Counts"
[4]: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?utm_source=chatgpt.com "ERA5 hourly data on single levels from 1940 to present"
[5]: https://data.cityofnewyork.us/City-Government/3-D-Building-Model/tnru-abg2?utm_source=chatgpt.com "3-D Building Model - NYC Open Data -"
[6]: https://data.cityofnewyork.us/City-Government/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks?utm_source=chatgpt.com "Primary Land Use Tax Lot Output (PLUTO) - NYC Open Data -"
[7]: https://data.cityofnewyork.us/City-Government/1-foot-Digital-Elevation-Model-DEM-/dpc8-z3jc?utm_source=chatgpt.com "1 foot Digital Elevation Model (DEM) | NYC Open Data"
[8]: https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9?utm_source=chatgpt.com "311 Service Requests from 2020 to Present | NYC Open Data"
[9]: https://data.cityofnewyork.us/Housing-Development/DOB-NOW-Build-Job-Application-Filings/w9ak-ipjd?utm_source=chatgpt.com "DOB NOW: Build – Job Application Filings | NYC Open Data"
[10]: https://data.cityofnewyork.us/Housing-Development/Buildings-Subject-to-HPD-Jurisdiction/kj4p-ruqc?utm_source=chatgpt.com "Buildings Subject to HPD Jurisdiction | NYC Open Data"
[11]: https://data.cityofnewyork.us/Transportation/DOT-Traffic-Speeds/i4gi-tjb9?utm_source=chatgpt.com "DOT Traffic Speeds - NYC Open Data -"
[12]: https://data.cityofnewyork.us/api/views/5tqd-u88y/rows.xml?accessType=DOWNLOAD&utm_source=chatgpt.com "https://data.cityofnewyork.us/api/views/5tqd-u88y/rows.xml ..."
[13]: https://data.cityofnewyork.us/api/views/63us-eqtq/rows.csv?accessType=DOWNLOAD&utm_source=chatgpt.com "Download - NYC Open Data -"
[14]: https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj?utm_source=chatgpt.com "EMS Incident Dispatch Data | NYC Open Data"
[15]: https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data/8m42-w767?utm_source=chatgpt.com "Fire Incident Dispatch Data | NYC Open Data"
[16]: https://data.cityofnewyork.us/Environment/NYC-Building-Energy-and-Water-Data-Disclosure-for-/5zyy-y8am?utm_source=chatgpt.com "NYC Building Energy and Water Data Disclosure for Local ..."
[17]: https://tfl.gov.uk/info-for/open-data-users/our-open-data?utm_source=chatgpt.com "Our open data - London"
[18]: https://data.london.gov.uk/dataset/london-fire-brigade-incident-records-em8xy?utm_source=chatgpt.com "London Fire Brigade Incident Records | London Datastore"
[19]: https://data.london.gov.uk/dataset/london-fire-brigade-mobilisation-records-24r65?utm_source=chatgpt.com "London Fire Brigade Mobilisation Records | London Datastore"
[20]: https://data.london.gov.uk/dataset/smartmeter-energy-consumption-data-in-london-households-vqm0d/?utm_source=chatgpt.com "SmartMeter Energy Consumption Data in London Households"
[21]: https://www.londonair.org.uk/?utm_source=chatgpt.com "London Air Quality Network"
[22]: https://www.gov.uk/government/statistical-data-sets/road-safety-open-data?utm_source=chatgpt.com "Road safety open data"
[23]: https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/helsinki-3d?utm_source=chatgpt.com "Helsinki 3D"
[24]: https://hri.fi/data/en_GB/dataset/helsingin-3d-kaupunkimalli?utm_source=chatgpt.com "3D models of Helsinki"
[25]: https://www.hel.fi/en/decision-making/information-on-helsinki/maps-and-geospatial-data/make-better-use-of-geospatial-data/open-geographic-data?utm_source=chatgpt.com "Open geographic data | City of Helsinki"
[26]: https://hri.fi/en_gb/?utm_source=chatgpt.com "Helsinki Region Infoshare - Open data service"
[27]: https://hri.fi/data/en_GB/dataset/liikennemaarat-helsingissa?utm_source=chatgpt.com "Traffic data from Helsinki"
[28]: https://www.hsl.fi/en/hsl/open-data?utm_source=chatgpt.com "HSL's open data"
[29]: https://www.hsy.fi/en/environmental-information/open-data/?utm_source=chatgpt.com "Open data"
[30]: https://avoindata.suomi.fi/data/en_GB/dataset/?_res_format_limit=0&groups=liikenne&page=1&q=&sort=title_string+asc&utm_source=chatgpt.com "Open data for vehicles - Avoindata.fi - Suomi.fi"
[31]: https://data.amsterdam.nl/?utm_source=chatgpt.com "Data en Informatie: Home - Gemeente Amsterdam"
[32]: https://api.data.amsterdam.nl/?utm_source=chatgpt.com "API's en Geo-webservices - Gemeente Amsterdam"
[33]: https://maps.amsterdam.nl/open_geodata/?utm_source=chatgpt.com "Maps Data - Maps Amsterdam"
[34]: https://docs.3dbag.nl/en/?utm_source=chatgpt.com "Overview - 3DBAG"
[35]: https://www.pdok.nl/datasets?utm_source=chatgpt.com "Datasets"
[36]: https://data.overheid.nl/en/dataset/kdrditpuogy4wq?utm_source=chatgpt.com "Realtime verkeersdata - Data overheid - Overheid.nl"
[37]: https://english.ndw.nu/?utm_source=chatgpt.com "National Road Traffic Data Portal: Stronger together, cheaper ..."
[38]: https://data.overheid.nl/en/dataset/d6rmg5cdgbfp2q?utm_source=chatgpt.com "Parkeervakken | Data overheid - Overheid.nl"
[39]: https://mobilitydatabase.org/feeds/gtfs/mdb-1077?utm_source=chatgpt.com "OVapi, Netherlands aggregate GTFS Schedule Feed"
[40]: https://www.ds4sscc.eu/tfds?utm_source=chatgpt.com "Traffic Flow Data Space"
[41]: https://www.digitaldubai.ae/apps-services/details/data.dubai?utm_source=chatgpt.com "Data.Dubai Platform"
[42]: https://dubailand.gov.ae/en/open-data/real-estate-data/?utm_source=chatgpt.com "Dubai Land Department - Real Estate Data"
[43]: https://www.dm.gov.ae/open-data2/?utm_source=chatgpt.com "Open Data"
[44]: https://bayanat.ae/en/Datasets/Dataset-info?id=ZN_6NIbITFwGRoSP9vHhmK2S0xEZU-IrHvN-zVGM-Gg&utm_source=chatgpt.com "Dubai Municipality - Building Permits"
[45]: https://www.transit.land/feeds/f-dubai~rta?utm_source=chatgpt.com "GTFS feed: Road and Transport Authority (RTA)"
[46]: https://gslb.dubaipulse.gov.ae/data/dewa-consumption/dewa_water_production_mig-open-api?utm_source=chatgpt.com "Dataset - dewa_water_production_mig-open-api"
[47]: https://bayanat.ae/en/Datasets/Dataset-info?id=3v6CQ8dDZepn7ikeSnd_ymTz3EScrAD6TgeE5IoywiM&utm_source=chatgpt.com "The Opendata Portal - dewa annual statistics"
[48]: https://www.dubaipolice.gov.ae/app/home/opendata?utm_source=chatgpt.com "Open Data"
[49]: https://bayanat.ae/Datasets/Dataset-info?id=JTnLbjyziy3qJgsZtjN2iCkiYADfRRIdiinHA25jl40&utm_source=chatgpt.com "Dataset Info | The Opendata Portal"
[50]: https://data.gov.sg/?utm_source=chatgpt.com "Singapore Open Data Portal"
[51]: https://datamall.lta.gov.sg/content/datamall/en.html?utm_source=chatgpt.com "DataMall | Land Transport Authority (LTA)"
[52]: https://data.gov.sg/datasets?formats=API&sort=relevancy&utm_source=chatgpt.com "data.gov.sg"
[53]: https://www.onemap.gov.sg/apidocs/?utm_source=chatgpt.com "OneMap API Documentation"
[54]: https://datagovsg-api.readthedocs.io/?utm_source=chatgpt.com "datagovsg_api API Reference — datagovsg_api documentation"
[55]: https://data.gov.sg/datasets/d_e1058d6974c877257e32048ab128ad83/view?utm_source=chatgpt.com "PM2.5 (API) | NEA"
[56]: https://ual.sg/project/open-urban-data-singapore/?utm_source=chatgpt.com "Guide to open urban data in Singapore"
[57]: https://data.cityofchicago.org/?utm_source=chatgpt.com "Chicago Data Portal - City of Chicago"
[58]: https://www.chicago.gov/city/en/depts/bldgs/provdrs/inspect/svcs/building_violationsonline.html?utm_source=chatgpt.com "Search Building Department Records"
[59]: https://data.cityofchicago.org/Environment-Sustainable-Development/Chicago-Energy-Benchmarking/xq83-jr8c?utm_source=chatgpt.com "Chicago Energy Benchmarking - Chicago Data Portal"
[60]: https://www.transitchicago.com/data/?utm_source=chatgpt.com "Open Data from the CTA"
[61]: https://catalog.data.gov/dataset/divvy-trips?utm_source=chatgpt.com "City of Chicago - Divvy Trips"
[62]: https://arrayofthings.github.io/?utm_source=chatgpt.com "Array of Things"
[63]: https://www.chicago.gov/city/en/depts/cdph/supp_info/Environment/open-air-chicago.html?utm_source=chatgpt.com "Open Air Chicago"
[64]: https://www.melbourne.vic.gov.au/open-data?utm_source=chatgpt.com "Open data"
[65]: https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-counting-system-monthly-counts-per-hour/?utm_source=chatgpt.com "Pedestrian Counting System (counts per hour)"
[66]: https://discover.data.vic.gov.au/dataset/pedestrian-counting-system-sensor-locations?utm_source=chatgpt.com "Pedestrian Counting System - Sensor Locations - Dataset"
[67]: https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bay-sensors/?utm_source=chatgpt.com "On-street Parking Bay Sensors - CoM Open Data Portal"
[68]: https://data.melbourne.vic.gov.au/explore/dataset/on-street-parking-bays/?utm_source=chatgpt.com "On-street Parking Bays - CoM Open Data Portal"
[69]: https://www.data.gov.au/data/dataset/?_groups_limit=0&_license_id_limit=0&_tags_limit=0&organization=city-of-melbourne-open-data&res_format=JSON&utm_source=chatgpt.com "236 datasets found"
[70]: https://opendata.transport.vic.gov.au/dataset/?utm_source=chatgpt.com "Data Collection"
[71]: https://opendata.transport.vic.gov.au/dataset/gtfs-realtime?utm_source=chatgpt.com "GTFS Realtime - Data Collection"
[72]: https://catalogue.data.infrastructure.gov.au/dataset/?groups=vicroads&utm_source=chatgpt.com "DITRDCSA Data Catalogue - Dataset"
