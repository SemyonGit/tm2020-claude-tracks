# Projektkontext: TM2020 Claude Tracks

Aktualisiert: 14. September 2026. Diese Datei beschreibt den aktuellen Stand.
Ausführliche Befunde: [PROJECT_REVIEW.md](PROJECT_REVIEW.md).
Nächste praktische Arbeit: [NEXT_STEPS.md](NEXT_STEPS.md).

## Ziel und Arbeitsweise

SemyonGit möchte mit KI Trackmania-2020-Strecken bis hin zu einer Kacky-Map
entwerfen. Entwurf und technische Umsetzung können von Claude oder einem
anderen Assistenten stammen. `meta.generated_by` nennt den tatsächlichen
Generator. Semyon prüft Maps im Spiel und liefert Referenzen für neue Geometrie.

Quelle: `SemyonGit/tm2020-claude-tracks`, Basis dieser Überarbeitung:
`13d1dbe7d5d28238360f0d8a2fe931261eb3918c` vom 3. Juni 2026 UTC
(4. Juni in der Schweiz). Es gab zu Beginn nur `main`, keine PRs, Issues oder
CI-Läufe. Frühere Claude-Chats lagen nicht vor; Grundlage waren Repository und
Commit-Verlauf.

## Aktuelle Pipeline

1. High-Level-Design nach `tools/design_schema.json` erstellen.
2. `compose.py` berechnet ein `track.json` und prüft dessen Geometrie.
3. `converter/build.py` validiert erneut, schreibt GBX mit eigenem Namen/UID und
   liest die Ausgabe zur Kontrolle ein.
4. Map im aktuellen Spielstand öffnen, speichern, fahren und validieren.
5. Befunde und Änderungen in diesem Kontext dokumentieren.

Python 3.12; Requirements in `converter/requirements.txt` bzw.
`requirements-dev.txt`. Windows: `.\.venv\Scripts\python.exe` und
`$env:PYTHONIOENCODING = "utf-8"`; Linux: `.venv/bin/python`.

## Was belegt ist

| Bereich | Stand |
|---|---|
| Flache Einzelzellen | Start, Gerade, Checkpoint, Finish, Rechts- und Linkskurve; laut Juni-Protokoll im Spiel geprüft |
| Steigungen | `slope_up` und `slope_down` weiterhin experimentell; vier neue Kalibrierungsmaps |
| Dateipipeline | Schema, Rotation, Anschlüsse, Platzgrenzen, Belegung und Waypoints werden geprüft; GBX-Roundtrip |
| Katalog | 191 Bildnamen: 190 RoadTech, 1 TrackWall; kein vollständiger Advanced-Editor-Katalog |
| Mapping | 216 historische Alias-Einträge in `converter/build.py`; akzeptierte Geometrie ausschliesslich in `track_lib/blocks.py` |
| Testmaterial | Proofcut plus Flat-Turns und vier Steigungstests; aktuelle Spielprüfung noch offen |
| Alte Entwürfe | Silvercut und Razorline ungültig; unverändert als Historie erhalten |
| Grössere Blöcke/Kacky | Anschluss- und Platzbedarf noch nicht modelliert |

## Koordinaten und Orientierung

JSON-Fahrtrichtung: 0=N=-z, 1=E=+x, 2=S=+z, 3=W=-x.
Raster der Vorlage: x=48, y=40, z=48. JSON-y=1 ist GBX-y=9 (Offset +8).
Das ist kein direkter Gleichlauf zwischen JSON-Heading und GBX-`dir`.

- Gerade und Checkpoint: `(2, 1, 0, 3)`.
- Start/Finish: dazu 180 Grad; Korrektur aus Juni bleibt erhalten.
- Rechtskurve: `(3, 0, 1, 2)`.
- Linkskurve: `(0, 1, 2, 3)`.
- Abfahrt: provisorisch um 180 Grad gedreht; Ursprung eine y-Einheit unter dem
  Eingang. Noch kein neuer Fahrtest.

## Änderungen dieser Überarbeitung

- Echte Schema-Prüfung; eigenes Design-Schema; ungültige Counts und Headings
  werden abgewiesen. Generator-Metadaten sind nicht mehr auf Claude festgelegt.
- Validator prüft jede Blockrotation, Start am Anfang, Finish am Ende, echte
  Checkpoint-Indizes, Gridgrenzen, Sections und implementierte Flags.
- Unbekannte Geometrie wird nicht mehr als Gerade behandelt. `--force` umgeht
  keine Fehler. `--allow-unverified` ist nur für die zwei modellierten Steigungen.
- `Checkpoint` baut einen echten `RoadTechCheckpoint`.
- GBX-Name/UID in Body, Header und XML synchron; UID stabil je benanntem Layout;
  zugehöriger CRC wird angepasst. Echter Template-Account-Autor bleibt erhalten.
- Lokaler Parser-Patch: eingebettete ZIP-Puffer gehören jeweils zu ihrer Map.
- Batch überspringt Designs, liefert Fehlerstatus und erkennt kollidierende
  Ausgabenamen. Expliziter Maps-Ordner und Ausgabeordner sind möglich.
- Katalog wird aus vorhandenen PNGs reproduziert. Downloads nur noch über
  explizite Namenslisten; Netzwerkfehler ersetzen den Katalog nicht durch Leerlisten.
- Fünf neue Testmaps, Referenz-Export, Tests und Linux-/Windows-CI ergänzt.

## Noch offen

Die aktuelle Überarbeitung konnte Trackmania nicht ausführen. Fahrbarkeit,
Checkpoint-Respawn, Author Time und neue In-game-Validierung sind offen.
Thumbnail und einige Editorinformationen stammen weiterhin aus der Vorlage.
Die vorhandene Zellprüfung bewertet weder Fahrphysik noch beliebige Mehrzellen-
Blöcke, Dekoration oder absichtliche Sprünge.

Im Juni erwähnte Referenzmaps sind **nicht eingecheckt**. Alte lokale Pfade:
`C:/Users/semyo/Documents/Trackmania/Maps/My Maps/` und
`C:/Users/semyo/Documents/Trackmania/Maps/Downloaded/`.
Vor einer Verwendung müssen die jeweiligen Dateien tatsächlich vorliegen.

Als Nächstes Flat-Turns und Slope-N/E/S/W testen, Ergebnisse protokollieren,
danach Curve2 und ChicaneX2 vermessen. Keine `verified`-Flags aufgrund eines
reinen Python- oder GBX-Parser-Tests setzen.
