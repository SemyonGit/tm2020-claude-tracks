# TM2020 Claude Tracks – Projekt Kontext

## Was dieses Projekt ist
Vollautomatisierte TM2020-Track-Generierung via Claude AI.
- Claude (claude.ai Projekt) designt Tracks als JSON
- converter/build.py wandelt JSON → .Map.Gbx (TM2020 Spieldatei)
- Claude Code (Opus 4.7) automatisiert Konvertierung + Git

## GitHub Repo
https://github.com/SemyonGit/tm2020-claude-tracks
Lokal: C:\Users\semyo\Documents\tm2020-claude-tracks

## Ordnerstruktur
```
tm2020-claude-tracks/
├── CLAUDE.md                          ← Kontext für Claude Code
├── README.md
├── converter/
│   ├── build.py                       ← Haupt-Konverter (JSON → .Map.Gbx)
│   ├── gbxpy/                         ← Vendored gbx-py Library (schadocalex)
│   ├── template.Map.Gbx               ← Leere TM2020-Map als Basis
│   └── setup.md
├── tools/
│   ├── track_schema.json              ← JSON-Schema für Tracks
│   ├── claude_code_agent.md
│   └── Pictures/                      ← Screenshots (z.B. test_kurven.png)
└── tracks/
    ├── speedtech/
    │   └── silvercut/
    │       ├── silvercut.json
    │       └── silvercut.Map.Gbx
    ├── fullspeed/
    ├── dirt/
    ├── rally/
    ├── stunts/
    ├── fun/
    ├── lol/
    ├── beginner/
    ├── tech/
    └── ice/
```

## Tech Stack
- Python 3.12 (py -3.12)
- gbx-py (vendored, schadocalex/gbx-py) – GBX Read/Write für TM2020
- construct (pip install construct)
- Claude Code Opus 4.7

## Converter starten
```powershell
# Dry-Run
PYTHONIOENCODING=utf-8 py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json --dry-run

# Echte Datei
PYTHONIOENCODING=utf-8 py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json

# Batch
PYTHONIOENCODING=utf-8 py -3.12 converter/build.py tracks/speedtech/ --batch
```

## Claude Code starten
```powershell
cd C:\Users\semyo\Documents\tm2020-claude-tracks
claude --dangerously-skip-permissions --model claude-opus-4-7 --max-turns 30
```

## Aktueller Stand der Pipeline
JSON → .Map.Gbx funktioniert technisch. Map lädt in TM2020.

## Aktuelle Probleme (noch zu fixen)
1. **Block-Koordinaten/Rotationen falsch** – Blöcke verbinden sich nicht korrekt
   - Kurven schliessen nicht richtig an Geraden an
   - Rotationen (dir 0-3) werden möglicherweise falsch übersetzt
   
2. **Block-Namen noch nicht vollständig verifiziert**
   - Echte TM2020 Block-Namen haben kein "Stadium" Prefix
   - Schema: Road{Type}{Suffix} (z.B. RoadTechStraight, RoadTechCurve1)
   - Chicane/Bank/Wall haben noch keine echten TM2020-Pendants

## Bisheriges Block-Mapping (in converter/build.py)
```python
BLOCK_MAP = {
    "StadiumRoadMainStraight":      "RoadTechStraight",
    "StadiumRoadMainStart":         "RoadTechStart",
    "StadiumRoadMainFinish":        "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":  "RoadTechCheckpoint",
    "StadiumRoadMainCurve1Right":   "RoadTechCurve1",
    "StadiumRoadMainCurve1Left":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Right":   "RoadTechCurve2",
    "StadiumRoadMainCurve2Left":    "RoadTechCurve2",
    "StadiumRoadMainCurve3Right":   "RoadTechCurve3",
    "StadiumRoadMainCurve3Left":    "RoadTechCurve3",
    "StadiumRoadMainChicaneRight":  "RoadTechCurve1",  # Placeholder
    "StadiumRoadMainChicaneLeft":   "RoadTechCurve1",  # Placeholder
    "StadiumRoadMainBankRight":     "RoadTechStraight", # Placeholder
    "StadiumRoadMainBankLeft":      "RoadTechStraight", # Placeholder
    "StadiumRoadMainSlope2Up":      "RoadTechSlopeBase2",
    "StadiumRoadMainSlope2Down":    "RoadTechSlopeBase2",
    "StadiumRoadMainWallLeft":      "RoadTechStraight",  # Placeholder
    "StadiumRoadMainWallRight":     "RoadTechStraight",  # Placeholder
    "StadiumRoadMainTurbo":         "RoadTechSpecialTurbo",
}
```

## Verfügbare echte TM2020 Maps zum Parsen
```
C:\Users\semyo\Documents\Trackmania\Maps\My Maps\jantronix wurst.Map.Gbx   (291 Blöcke)
C:\Users\semyo\Documents\Trackmania\Maps\My Maps\test_kurven.Map.Gbx       (selbst gebaut, Kurven!)
C:\Users\semyo\Documents\Trackmania\Maps\Downloaded\every platform block.Map.Gbx
```

## Screenshot der test_kurven Map
```
C:\Users\semyo\Documents\tm2020-claude-tracks\tools\Pictures\
```
(Zeigt eine einfache S-Kurven-Strecke mit kleinen Kurven = RoadTechCurve1)

## Nächste Aufgabe (was du tun sollst)
1. Schau dir das Bild in tools/Pictures/ an
2. Parse test_kurven.Map.Gbx:
```powershell
py -3.12 -c "
import sys
sys.path.insert(0, 'converter')
from gbxpy.parser import parse_file
data = parse_file('C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx')
chunk = data.body[0x0304301F]
for i, b in enumerate(chunk.Blocks):
    print(f'{i:2d}. {b.blockName:35s} x={b.coord.x:3d} y={b.coord.y:3d} z={b.coord.z:3d} dir={b.dir}')
"
```
3. Verstehe wie Kurven/Koordinaten/Rotationen in TM2020 wirklich funktionieren
4. Fixe converter/build.py komplett (Koordinaten-Mapping + Rotationen)
5. Teste mit silvercut.json → sollte eine zusammenhängende Strecke ergeben
6. Committe: "🔧 Fix block placement from visual + parsed test_kurven"

## Bekannte technische Details
- gbx-py ist gevendored (pip-Paket liefert nur LZO-Binding)
- Chunk 0x03043062/68/69 werden vor dem Schreiben gedropt (block-count dependent)
- PYTHONIOENCODING=utf-8 nötig wegen Emoji in print-Statements
- data_size wird von gbx-py korrekt gehandelt (kein manueller Offset mehr)
- Template.Map.Gbx hat y=8 für Bodenblöcke

## Referenz-Repos (falls nötig)
- gbx-py: https://github.com/schadocalex/gbx-py
- GBX.NET: https://github.com/BigBang1112/gbx-net
- TMTrackNN: https://github.com/donadigo/TMTrackNN
- NationsConverter: https://github.com/BigBang1112/nations-converter
