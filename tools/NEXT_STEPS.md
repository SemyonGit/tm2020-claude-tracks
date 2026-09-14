# Was als Nächstes kommt

Stand: 14. September 2026. Das Ziel bleibt eine Kacky-Map. Der nächste konkrete
Schritt ist **das Steigungsmodell im Spiel prüfen**.

## 1. Flache Basis kurz bestätigen

`tracks/_validation/flat_turns/Calibration-Flat-Turns.Map.Gbx` in deinen
Trackmania-Ordner `Maps/My Maps` kopieren und im Editor öffnen.

- Zeigt der Start entlang der Strecke?
- Lassen sich beide Linkskurven und beide Rechtskurven ohne Lücke durchfahren?
- Werden beide Checkpoints ausgelöst? Funktioniert Respawn am Checkpoint?
- Kannst du das Finish aus der vorgesehenen Richtung erreichen?
- Erscheint der neue Mapname im Editor und in der Auswahl?

Erst dann ist die neue Pipeline auch in deinem aktuellen Spielstand bestätigt.

## 2. Die vier Steigungstests fahren

Die Dateien `Calibration-Slope-N/E/S/W.Map.Gbx` liegen in den entsprechenden
Unterordnern von `tracks/_validation/`. Jeder Test enthält Start, Anlauf,
eine Steigung nach oben, einen erhöhten Abschnitt mit Checkpoint, eine Steigung
nach unten und das Finish.

Die Buchstaben beziehen sich auf die **JSON-Fahrtrichtung**: N=-z, E=+x, S=+z,
W=-x. Sie sind keine direkte Beschriftung der GBX-Blockrotation.

Prüfe bei allen vier Maps die Übergänge unten/oben, die Fahrbahnanschlüsse,
den Start, den Checkpoint mit Respawn und das Finish. Wenn ein Übergang nicht
passt, im Editor von oben und von der Seite fotografieren. Zusätzlich die Map
nach deiner manuellen Korrektur speichern; diese Datei ist die beste Referenz.

Deine Rückmeldung kann so aussehen:

| Map | Start | Auffahrt | Abfahrt | Checkpoint/Respawn | Finish | Screenshot/Referenz |
|---|---|---|---|---|---|---|
| Flat-Turns | offen | entfällt | entfällt | offen | offen | |
| Slope-N | offen | offen | offen | offen | offen | |
| Slope-E | offen | offen | offen | offen | offen | |
| Slope-S | offen | offen | offen | offen | offen | |
| Slope-W | offen | offen | offen | offen | offen | |

Diese Tabelle enthält bewusst noch keine Testergebnisse. Nach erfolgreicher
Prüfung die Ergebnisse und den Spiel-Build dokumentieren. Erst dann die
`verified`-Flags der Steigungen ändern. Ein grüner Python-Test genügt dafür nicht.

## 3. Grössere Kurven und echte Schikanen vermessen

Bisher genannte Referenzdateien liegen nicht im Repository:
`test_kurven.Map.Gbx`, `test_slopes.Map.Gbx`, `jantronix wurst.Map.Gbx` und
`every platform block.Map.Gbx`. Falls du sie noch lokal hast, werden sie für
den nächsten Schritt benötigt. Geeignet sind auch kleine, selbst gebaute Maps
mit genau einem neuen Element und jeweils einer geraden Ein-/Ausfahrt.

Zuerst `RoadTechCurve2`, danach `RoadTechChicaneX2Left/Right`. Pro Element
Eintritt, Austritt, Höhenunterschied, belegte Rasterzellen und Rotation in allen
vier Richtungen erfassen. Exporthilfe:

```powershell
.\.venv\Scripts\python.exe tools/inspect_map.py "C:\Pfad\Referenz.Map.Gbx" --output build/referenz.blocks.json
```

Der Export liefert Platzierungsdaten. Er kann die Anschlussgeometrie nicht
automatisch aus einer beliebigen Blockliste beweisen. Referenzmap, Screenshots
und Fahrtest gehören zusammen.

## 4. Silvercut und Razorline neu entwerfen

Silvercut hat falsche Richtungen und Start/Finish auf derselben Zelle.
Razorline hat keinen Start, Lücken und nicht unterstützte Schikanen.
Die vorhandenen Dateien dienen als Historie und Fehlerbeispiele.

Neue Versionen zuerst als `*.design.json` mit belegten Segmenten entwerfen.
Eine flache Übungsvariante ist bereits jetzt möglich. Die ursprünglich
versprochene Speedtech-Geometrie benötigt die grösseren Kurven und Schikanen aus
Schritt 3. Schwierigkeit und Zielzeit nach Fahrtests beurteilen.

## 5. Den ersten Kacky-Prototyp bauen

Nach den durchgehenden Strecken kommen gezielt ein Sprung oder ein
Präzisionshindernis sowie die nötigen PlatformTech-Blöcke. Dafür braucht der
Composer ein erweitertes Modell für getrennte Ein-/Ausgänge, Freiraum und
absichtliche Sprünge. Die aktuelle lückenlose Einzelpfadprüfung kann keine
Kacky-Sprünge, Landungen oder physikalische Machbarkeit bewerten.

Ein kleines, mehrfach testbares Hindernis ist der nächste Kacky-Meilenstein.
Ein kompletter schwieriger Kurs kommt nach diesem Nachweis.
