# TM2020 Claude Tracks – Claude Code Context

## Projekt
Automatisierte TM2020-Track-Generierung via Claude AI (claude.ai Projekt).
Tracks werden von Claude (Chat) als JSON entworfen, Claude Code konvertiert und deployed.

## Stack
- Python 3.x (Konverter: converter/build.py)
- GBX-Binärformat (Trackmania Map Format)
- GitHub (Versionskontrolle + Archiv)

## Wichtige Pfade
```
catalog/blocks.json              → Vollständiger TM2020 Blockkatalog
tools/track_schema.json          → JSON-Schema für alle Track-Dateien
converter/build.py               → JSON → .Map.Gbx Konverter
converter/requirements.txt       → Python Dependencies
tracks/{category}/{name}.json    → Claude-generierte Track-Daten
tracks/{category}/{name}.Map.Gbx → Fertige Spieldatei (gitignored optional)
```

## TM2020 Maps-Ordner (Windows)
```
C:/Users/{USERNAME}/Documents/ManiaPlanet/Maps/My Maps/
```

## Workflow
1. Validiere JSON gegen tools/track_schema.json
2. Führe converter/build.py aus → .Map.Gbx
3. Generiere SVG-Preview (optional)
4. git add + commit + push
5. Kopiere .Map.Gbx in TM2020 Maps-Ordner

## Commit-Format
```
🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)
```

## Kategorien
speedtech, fullspeed, tech, dirt, rally, stunts, ice, fun, lol, beginner

## Nie verändern (nur Claude Chat)
- catalog/blocks.json
- tools/track_schema.json
