import urllib.request, os, time, json

BASE = 'https://images.mania-exchange.com/ix/originalblocks/5/'
OUT = 'catalog/block_images'
os.makedirs(OUT, exist_ok=True)

surfaces = ['Road', 'Platform', 'Track', 'Stadium', 'Deco']
types    = ['Tech', 'Bump', 'Dirt', 'Ice', 'Rally', 'Grass',
            'Wall', 'Circuit', 'Pillar', 'Special']
variants = [
    'Base','Straight','Start','Finish','StartFinish','Checkpoint',
    'Curve1','Curve2','Curve3','Curve4',
    'Curve1In','Curve1Out','Curve2In','Curve2Out',
    'SlopeBase','SlopeBase2','SlopeBase3',
    'Slope1','Slope2','Slope3',
    'ChicaneLeft','ChicaneRight',
    'BankLeft','BankRight','FWTilt',
    'WallLeft','WallRight',
    'SpecialTurbo','SpecialBoost','SpecialBoost2','SpecialSlowmo',
    'Loop','LoopEnd','LoopStart',
    'DiagLeft','DiagRight',
    'Pillar','StraightPillar','Curve1Pillar','Curve2Pillar',
    'DeadendRound','DeadendRoundPillar',
    'GTCurve2','GTCurve3','GTCurve4',
]
known = [
    'RoadTechStart','RoadTechFinish','RoadTechStraight','RoadTechCheckpoint',
    'RoadTechCurve1','RoadTechCurve2','RoadTechCurve3',
    'RoadTechSlopeBase','RoadTechSlopeBase2','RoadTechSpecialTurbo',
    'RoadBumpStart','RoadBumpFinish','RoadBumpCheckpoint','RoadBumpStraight',
    'RoadBumpCurve1','RoadBumpCurve2','RoadBumpSlopeBase','RoadBumpSlopeBase2',
    'RoadBumpSpecialTurbo','PlatformTechBase',
    'TrackWallStraightPillar','TrackWallCurve1Pillar','TrackWallCurve2Pillar',
    'TrackWallDeadendRoundPillar','StadiumCircuitBase','StadiumRoadMain',
]
candidates = set(known)
for s in surfaces:
    for t in types:
        for v in variants:
            candidates.add(f'{s}{t}{v}')
        candidates.add(f'{s}{t}')

found = []
total = len(candidates)
print(f'Probing {total} candidate names...')
for i, name in enumerate(sorted(candidates)):
    url = BASE + name + '.png'
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        r = urllib.request.urlopen(req, timeout=5)
        if r.status == 200:
            data = r.read()
            with open(f'{OUT}/{name}.png','wb') as f:
                f.write(data)
            found.append(name)
            print(f'✅ {name}')
        time.sleep(0.05)
    except Exception as e:
        pass

with open('catalog/blocks.json','w') as f:
    json.dump(sorted(found), f, indent=2)
print(f'\nFound {len(found)} blocks → catalog/blocks.json')
