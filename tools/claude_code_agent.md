# Claude Code – TM2020 Track Agent

Diese Datei enthält die Anweisungen für Claude Code, damit es vollautomatisch
Tracks konvertiert, committed und in den richtigen Ordner legt.

---

## Wann Claude Code verwendet wird

Claude Code übernimmt alles **nach** der Track-Generierung durch Claude (Chat):
1. Track-JSON validieren
2. JSON → .Map.Gbx konvertieren
3. Preview-SVG generieren
4. Commit + Push zu GitHub
5. .Map.Gbx in TM2020-Maps-Ordner kopieren

---

## Befehle

### Neuen Track verarbeiten
```bash
claude "Verarbeite den neuen Track in tracks/speedtech/razorline.json: 
validiere, konvertiere, erstelle Preview, committe zu GitHub"
```

### Ganzen Batch verarbeiten
```bash
claude "Verarbeite alle .json Dateien in tracks/ die noch keine .Map.Gbx haben"
```

### Track-Statistiken updaten
```bash
claude "Update die README.md mit der aktuellen Track-Anzahl pro Kategorie"
```

---

## Claude Code System Prompt (für CLAUDE.md)

```
Du bist ein TM2020 Track Build Agent. Deine Aufgaben:

1. VALIDIEREN: Prüfe track.json gegen tools/track_schema.json
2. KONVERTIEREN: Führe converter/build.py aus
3. PREVIEW: Generiere eine SVG-Vorschau der Strecke
4. GIT: git add, commit mit Message "🏎️ Add [trackname] ([category] | Difficulty [X]/5)", push
5. DEPLOY: Kopiere .Map.Gbx nach ~/Documents/ManiaPlanet/Maps/My Maps/

Arbeite immer in dieser Reihenfolge. Melde Fehler sofort.
Commit-Format: "🏎️ Add {name} ({category} | Difficulty {d}/5 | Creativity {c}/5)"
```

---

## CLAUDE.md (Repo-Root)

Erstelle eine `CLAUDE.md` im Repo-Root damit Claude Code den Kontext kennt:

```markdown
# TM2020 Claude Tracks – Claude Code Context

## Projekt
Automatisierte TM2020-Track-Generierung via Claude AI.

## Stack
- Python 3.x (Konverter)
- GBX-Format (Trackmania Map Format)
- GitHub (Versionskontrolle)

## Wichtige Pfade
- Track-JSON: tracks/{category}/{name}.json
- Output: tracks/{category}/{name}.Map.Gbx  
- TM2020 Maps: ~/Documents/ManiaPlanet/Maps/My Maps/
- Block-Katalog: catalog/blocks.json

## Workflow
Siehe tools/claude_code_agent.md

## Nie anfassen
- catalog/blocks.json (nur Claude Chat darf das updaten)
- tools/track_schema.json (Schema bleibt stabil)
```
