# MAIN-CITYBRAIN-D8-WEB-BRAIN-SURFACE-STORY-QUEUE-R3

Patch the web control room so the default page is a story queue, not a source-record gallery.

Default above-the-fold requirements:
- headline: "CityBrain story queue" or equivalent human wording
- show two primary stories:
  - Wood Lane access review
  - NYC MVC cascade review
- each card shows city, place, tension, intelligence beat, review status, and boundary
- no raw fixture IDs or packet IDs in default card text
- no repeated boilerplate per card

Prohibited default UI patterns:
- wall of 20+ records
- first section is dataset inventory
- "London records: 10 / Chicago records: 5 / Helsinki records: 12" as the main story
- repeating governance boilerplate inside every card
- raw technical IDs outside collapsed technical details

Produce:
- patched web source
- `WEB_BRAIN_SURFACE_PATCH_REPORT.json`
- `NO_RECORD_GALLERY_AUDIT.json`
- `DEFAULT_UI_QUEUE_RENDER_ASSERTIONS.json`
