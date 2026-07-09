import json, math, urllib.request
from pathlib import Path
cards=json.loads(Path('packages/fixtures/london_mobility_source_records/source_record_bundle.json').read_text())['cards']
req=urllib.request.Request('https://api.tfl.gov.uk/Road/all/Disruption', headers={'User-Agent':'CityBrain local story probe/1.0'})
with urllib.request.urlopen(req, timeout=20) as r:
    disruptions=json.load(r)
print('disruptions', len(disruptions))
def dist(a,b,c,d):
    R=6371
    p1=math.radians(a); p2=math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(x), math.sqrt(1-x))
rows=[]
for dis in disruptions[:1000]:
    g=dis.get('geography') or {}; coords=g.get('coordinates') or []
    if len(coords)<2: continue
    lon, lat=coords[0], coords[1]
    for card in cards:
        f=card['evidence_fields']; d=dist(float(f['latitude']),float(f['longitude']),lat,lon)
        if d<3:
            rows.append((round(d,2), dis.get('id'), dis.get('severity'), dis.get('category'), dis.get('location'), card['external_record_id'], card['title'], card['evidence_fields'].get('borough')))
for r in sorted(rows)[:30]:
    print(r)
