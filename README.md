# 🏎️ TM2020 Claude Tracks

> **Alle Tracks in diesem Repository wurden von [Claude](https://claude.ai) (Anthropic) generiert.**  
> Kein manueller Block wurde platziert – reines AI-Design.

---

## Wie es funktioniert

1. Der Besitzer gibt Claude einen Track-Auftrag (Stil, Schwierigkeit, Kreativität)
2. Claude generiert eine strukturierte `.json`-Datei mit Blöcken, Positionen und Checkpoints
3. Das `converter`-Script wandelt die JSON in eine spielfertige `.Map.Gbx` um
4. Claude Code übernimmt Konvertierung und Commit automatisch

```
Claude (Sonnet / Opus)
    ↓  generiert
track.json
    ↓  converter/build.py
track.Map.Gbx
    ↓  Claude Code
GitHub + TM2020 Maps-Ordner
```

---

## Track-Kategorien

| Ordner | Stil | Beschreibung |
|--------|------|--------------|
| `speedtech` | 🔵 Präzision | Enge Linien, Bankkurven, Chicanen |
| `fullspeed` | 🔴 Gas geben | Kein Bremsen, Flow-Strecken |
| `tech` | 🟡 Technik | Komplexe Blöcke, maximale Kontrolle |
| `dirt` | 🟤 Offroad | Schotterpisten, Drifts, Gelände |
| `rally` | 🟢 Rally | Lange Kurven, Hügel, Natur |
| `stunts` | 🟣 Stunt | Loops, Wall-Rides, Sprünge |
| `ice` | ⚪ Eis | Rutschige Oberflächen, kein Grip |
| `fun` | 🟠 Fun | Abwechslungsreich, für alle |
| `lol` | 😂 LOL | Chaotisch, absurd, überraschend |
| `beginner` | 🟢 Einsteiger | Breit, verzeihend, lehrreich |

---

## Schwierigkeitsgrade

Jede Track-JSON enthält einen `difficulty`-Wert:

| Level | Label | Zielgruppe |
|-------|-------|------------|
| 1 | Beginner | Erste Runden |
| 2 | Medium | Gelegentliche Spieler |
| 3 | Hard | Erfahrene Fahrer |
| 4 | Expert | Competitive |
| 5 | Brutal | Top 1% |

---

## Track bauen (Setup)

### Einmalig
```bash
git clone https://github.com/DEIN-USERNAME/tm2020-claude-tracks
cd tm2020-claude-tracks
pip install -r converter/requirements.txt
```

### Neuen Track generieren
Gib Claude den Auftrag im Claude-Projekt, dann:
```bash
# Claude Code übernimmt das automatisch:
python converter/build.py tracks/speedtech/razorline.json
```

Die fertige `.Map.Gbx` landet automatisch in:
```
C:/Users/DEIN-USER/Documents/ManiaPlanet/Maps/My Maps/
```

---

## Dateistruktur pro Track

```
tracks/speedtech/razorline/
├── razorline.json        ← Claude Output (Block-Daten)
├── razorline.Map.Gbx     ← Fertige Spieldatei
└── razorline_preview.svg ← Streckenvorschau
```

---

## Tools

| Datei | Funktion |
|-------|----------|
| `converter/build.py` | JSON → .Map.Gbx Konverter |
| `converter/requirements.txt` | Python-Abhängigkeiten |
| `catalog/blocks.json` | Vollständiger TM2020 Blockkatalog |
| `tools/claude_code_agent.md` | Claude Code Anweisungen |
| `tools/track_schema.json` | JSON-Schema für Track-Dateien |

---

*Generiert mit Claude · Anthropic · [claude.ai](https://claude.ai)*
