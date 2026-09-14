# Testpaket vom 14. September 2026

Diese fünf Maps sind gebaut und durch den GBX-Parser geprüft. **Der aktuelle
Test in Trackmania steht noch aus.** Die vier Steigungsmodelle sind experimentell.

| Datei | Zweck |
|---|---|
| [Calibration-Flat-Turns.Map.Gbx](flat_turns/Calibration-Flat-Turns.Map.Gbx) | 20 Blöcke, zwei Links- und zwei Rechtskurven, zwei Checkpoints |
| [Calibration-Slope-N.Map.Gbx](slope_n/Calibration-Slope-N.Map.Gbx) | 11 Blöcke, Auffahrt/Abfahrt in JSON-Richtung 0 (-z) |
| [Calibration-Slope-E.Map.Gbx](slope_e/Calibration-Slope-E.Map.Gbx) | 11 Blöcke, Auffahrt/Abfahrt in JSON-Richtung 1 (+x) |
| [Calibration-Slope-S.Map.Gbx](slope_s/Calibration-Slope-S.Map.Gbx) | 11 Blöcke, Auffahrt/Abfahrt in JSON-Richtung 2 (+z) |
| [Calibration-Slope-W.Map.Gbx](slope_w/Calibration-Slope-W.Map.Gbx) | 11 Blöcke, Auffahrt/Abfahrt in JSON-Richtung 3 (-x) |

Die `.Map.Gbx`-Dateien in `Documents/Trackmania/Maps/My Maps` kopieren, zuerst
Flat-Turns öffnen und dann die vier Steigungstests fahren. Vollständige
Prüfpunkte und Rückmeldetabelle: [NEXT_STEPS.md](../../tools/NEXT_STEPS.md).

Jede Map hat ein `*.design.json` als Quelle und eine daraus berechnete `.json`.
Alle fünf lassen sich ohne automatische Kopie ins Spiel neu erzeugen:

```powershell
.\.venv\Scripts\python.exe tools/build_test_pack.py --include-slopes
```

Die Ausgaben landen in `build/test-pack/`. Die Zeitstempel in den Designquellen
sind fest, damit Wiederholungsbuilds dieselben Dateien erzeugen. Die Namen und
Map-IDs unterscheiden sich pro Test. Es wurde keine Author Time erfunden.
