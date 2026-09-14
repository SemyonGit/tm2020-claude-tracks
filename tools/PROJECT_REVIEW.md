# Projektprüfung und Überarbeitung

**Datum:** 14. September 2026
**Repository:** [SemyonGit/tm2020-claude-tracks](https://github.com/SemyonGit/tm2020-claude-tracks)
**Ausgangsstand:** [13d1dbe](https://github.com/SemyonGit/tm2020-claude-tracks/commit/13d1dbe7d5d28238360f0d8a2fe931261eb3918c), 3. Juni 2026 UTC / 4. Juni Schweiz.

## Ergebnis

Das Projekt besitzt eine brauchbare Grundlage für kleine, flache Strecken.
Es ist noch kein allgemeiner Trackmania-Editor und noch kein Kacky-Generator.
Der Composer ist ein sinnvoller Fortschritt gegenüber handgerechneten
Blockpositionen. Seine bisherige Prüfung war aber deutlich weniger vollständig,
als README und Kontextdateien behaupteten.

Die Überarbeitung repariert reproduzierbare Fehler, liefert aktuelle Anleitungen
und fünf kleine Kalibrierungsmaps. Steigungen bleiben bis zum Fahrtest
experimentell. Die alten Entwürfe werden nicht als fertige Strecken ausgegeben.

## Prüfgrundlage

Geprüft wurden Repository-Struktur, vollständiger Commit-Verlauf, vorhandene
Branches, PRs/Issues/Actions, alle eigenen Python-Skripte, Schemata, Dokumentation,
Streckendaten und Katalogindizes. Vorlage und vorhandene Maps wurden geparst.
Beim vendored Parser lag der Schwerpunkt auf den tatsächlich verwendeten
Lese-/Schreibpfaden und GBX-Strukturen. Die 191 Katalog-PNGs wurden mit ihren
Namensindizes abgeglichen; sie ersetzen keine vermessenen Geometriereferenzen.

Am Ausgangsstand existierten nur `main`, keine PRs, keine Issues und keine
CI-Läufe. Der damalige Claude-Chat und die in den Notizen erwähnten lokalen
Referenzmaps waren nicht verfügbar. Historische Aussagen über Fahrtests wurden
als solche übernommen und nicht als neue Beobachtung ausgegeben.

## Befunde und Korrekturen

| Priorität | Befund im Ausgangsstand | Änderung / verbleibende Grenze |
|---|---|---|
| Hoch | Eine falsche Rotation bei Proofcut-Block 5 bestand den Validator ohne Fehler. | Jede Blockrotation muss jetzt zum eingehenden Anschluss passen. |
| Hoch | Unbekannte Blocktypen wurden von `classify()` pauschal als Gerade behandelt. | Geometrie wird nur für explizit modellierte IDs akzeptiert. Bild-/Namenseinträge reichen nicht. |
| Hoch | Start/Finish wurden nur gezählt; Checkpoint-Indizes nur auf Zahlenbereich geprüft. | Start zuerst, Finish zuletzt; Indizes müssen genau echte Checkpoint-Blöcke bezeichnen und eindeutig sein. |
| Hoch | Der Alias `Checkpoint` baute eine Gerade mit Flag. | Er baut jetzt einen echten `RoadTechCheckpoint`. |
| Hoch | Alle vorhandenen GBX-Maps hatten dieselbe Template-UID; der Headername blieb teilweise `Template`. | Name/UID in Body, Header und XML synchronisiert; CRC angepasst; reproduzierbare IDs je benanntem Layout. |
| Hoch | Keine echte Schema-Prüfung; Headings wurden per `& 3` normalisiert; negative Counts konnten verschwinden. | Schema-Prüfung für Design und Track, klare Eingabefehler, Mengenbegrenzung vor Expansion. |
| Hoch | Mehrzellen-/Steigungsannahmen und beliebige Flags konnten ungeprüft in Builds gelangen. | Nicht modellierte Geometrie/Flags gesperrt; Steigungen nur mit ausdrücklicher Kalibrierungsoption. |
| Mittel | Batch versuchte auch `*.design.json` zu bauen und meldete Exitcode 0 trotz Fehlern. | Designs ausgeschlossen; Exitcode 1 bei Fehlern; kollidierende Ausgabenamen erkannt. |
| Mittel | Freie Mapnamen wurden direkt als Dateipfad verwendet. | Portable Namen, kein Pfadausbruch, atomare Ausgaben; Composer überschreibt seine Quelle nicht. |
| Mittel | Ein gemeinsam genutzter ZIP-Puffer im Parser konnte nach mehreren Parse-Aufrufen die falschen eingebetteten Daten liefern. | Pro Map eigener Puffer; reproduzierbarer Regressionstest. |
| Mittel | Katalog-Skript führte beim Import Netzwerkaktionen aus, verschluckte Fehler und konnte Listen verkürzen. | Lokaler Indexaufbau als Standard; explizite Downloadliste; Fehler sichtbar; vorhandene Indizes nicht durch leere Ergebnisse ersetzt. |
| Mittel | Dokumentation nannte gleichzeitig 120 und 191 Blöcke, widersprüchliche Rotationen und Prüfstände. | README, Setup, Kontext und Arbeitsablauf neu gefasst; 191 Bildnamen, sechs geprüfte Grundsegmente, zwei experimentelle. |
| Mittel | Keine automatischen Tests oder CI. | 73 Regressionstests und Workflow für Python 3.12 unter Linux und Windows. |

Die CRC-Berechnung folgt dem veröffentlichten
[GBX.NET-Quellcode](https://github.com/BigBang1112/gbx-net/blob/master/Src/GBX.NET/Engines/Game/CGameCtnChallenge.cs).
Sie reproduzierte zunächst den vorhandenen Template-CRC. Die übernommenen
Orientierungstabellen wurden durch explizite Regressionserwartungen abgesichert;
es wurden keine neuen Spielbeobachtungen daraus abgeleitet.

## Stand der Strecken

| Strecke | Technischer Stand | Im Spiel noch zu tun |
|---|---|---|
| Proofcut | 24 Blöcke, 2 Checkpoints; Koordinaten erhalten, GBX-Metadaten korrigiert | Aktuellen Neubuild öffnen und fahren |
| Flat-Turns | Neue 20-Block-Testmap mit Links-/Rechtskurven und 2 Checkpoints | Start, beide Kurventypen, Checkpoints/Respawn, Finish prüfen |
| Slope-N/E/S/W | Vier neue Maps mit je 11 Blöcken und 1 Checkpoint | Auffahrt und Abfahrt in jeder Richtung bestätigen oder korrigierte Referenz liefern |
| Silvercut | Falsche Richtungen, Start/Finish auf derselben Zelle, gesperrte Curve2-Platzhalter | Später als Composer-Design neu entwerfen |
| Razorline | Kein Start, mehrere Lücken, gesperrte Kurven/Schikanen, Platzhalter-Autor | Nach Vermessung echter Schikanen neu entwerfen |

Der alte Validator meldete bei Silvercut bereits 11 und bei Razorline 14
Probleme. Diese Zahlen stammen aus dem Ausgangsstand; der strengere neue
Validator berichtet zusätzliche Fehlerarten. Beide historischen JSON-Dateien
bleiben unverändert als Diagnosematerial erhalten.

## Neue und erneuerte Dateien

- **Einstieg und Übergabe:** `README.md`, `converter/setup.md`, `CLAUDE.md`,
  `tools/claude_code_agent.md`, `tools/kontext.md`, dieser Review und `NEXT_STEPS.md`.
- **Pipeline:** `compose.py`, `track_lib/blocks.py`, `composer.py`, `validator.py`,
  neue Module `schema.py`/`files.py`, `converter/build.py`.
- **Formate:** neues `tools/design_schema.json`; im bestehenden Track-Schema ist
  `generated_by` jetzt ein nicht leerer Text. Bestehende Claude-Metadaten bleiben
  gültig; neue Dateien können ihre tatsächliche Herkunft nennen.
- **Werkzeuge:** `tools/inspect_map.py`, `tools/build_test_pack.py`,
  überarbeitetes `catalog/fetch_blocks.py`.
- **Qualitätsprüfung:** `tests/test_pipeline.py`, gepinnte direkte Dependencies,
  `requirements-dev.txt`, `.github/workflows/tests.yml`.
- **Maps:** fünf Kalibrierungsdesigns mit Koordinaten-JSON und GBX, dazu der
  erneuerte Proofcut-Build. Historische Strecken erhielten klare Statusnotizen.
- **Parser:** gezielter ZIP-Patch, dokumentiert in `converter/gbxpy/PATCHES.md`.

## Durchgeführte Prüfung

Lokal unter **Linux mit Python 3.12.14: 73 Tests bestanden**. Dazu gehören:
Rotation-/Waypoint-Fehler, Grenzen und Eingabetypen, fehlerhafte Altstrecken,
Batch-Fehlercodes, Pfadbehandlung, Steigungs-Opt-in, GBX-Namen/UID/CRC, voneinander
unabhängige ZIP-Puffer und bytegleiche Wiederholungsbuilds aller sechs aktuellen
Design-/GBX-Paare.

Das Fünf-Map-Testpaket wurde vollständig gebaut, die Referenz-Exporthilfe
aufgerufen und der Katalogcheck bestanden. Git-Diffs wurden auf Whitespacefehler
geprüft. Die CI ist für Linux und Windows eingerichtet; den Status einer
konkreten Revision zeigt GitHub Actions.

**Nicht hier ausgeführt:** Trackmania starten, die neuen Maps fahren,
Checkpoint-Respawn beurteilen oder Author Times einfahren. Thumbnail und weitere
Editorinformationen werden noch aus der Vorlage übernommen. Der Editor sollte
die endgültigen Maps speichern und validieren.

## Nächste Entscheidung

Zuerst Flat-Turns und die vier Steigungsmaps testen. Danach die Steigungsdaten
bestätigen oder korrigieren. Anschliessend die Anschlussgeometrie für Curve2
und echte Schikanen erheben. Erst mit dieser Grundlage die beabsichtigten
Speedtech- und später Kacky-Strecken bauen.

Befehle, Dateinamen und Rückmeldetabelle: [NEXT_STEPS.md](NEXT_STEPS.md).
