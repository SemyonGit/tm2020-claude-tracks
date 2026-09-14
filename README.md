# TM2020 Claude Tracks

Trackmania-2020-Strecken aus einem beschriebenen Streckenverlauf erzeugen.
Langfristiges Ziel: eine bewusst entworfene Kacky-Map.

**Stand: 14. September 2026.** Die Pipeline erzeugt und prüft GBX-Dateien.
Die sechs flachen Grundsegmente wurden laut Projektprotokoll im Juni im Spiel
getestet. Die neu gebauten Dateien und die Steigungen benötigen einen aktuellen
Test in Trackmania. Ein erfolgreicher Dateibuild ist keine Fahrbarkeitsgarantie.

## Direkt weiterarbeiten

1. [Setup](converter/setup.md) ausführen.
2. [Testpaket](tracks/_validation/README.md) im Spiel prüfen.
3. Ergebnisse gemäss [nächsten Schritten](tools/NEXT_STEPS.md) zurückgeben.

Den vollständigen Review findest du in [PROJECT_REVIEW.md](tools/PROJECT_REVIEW.md).
Der aktuelle Kontext für die nächste Chat-/Coding-Session steht in
[kontext.md](tools/kontext.md).

## Pipeline

`*.design.json` beschreibt Segmente. `compose.py` berechnet Positionen und
Eingangsrichtungen. Schema und Validator prüfen die unterstützte Geometrie.
`converter/build.py` erzeugt eine `.Map.Gbx`, synchronisiert Name und Map-ID und
liest die Datei zur Kontrolle wieder ein. Anschliessend folgt der Test im Spiel.

```powershell
$env:PYTHONIOENCODING = "utf-8"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe compose.py tracks/speedtech/proofcut/proofcut.design.json
.\.venv\Scripts\python.exe converter/build.py tracks/speedtech/proofcut/proofcut.json --no-deploy
```

Linux/macOS: `.venv/bin/python` anstelle von `.\.venv\Scripts\python.exe`.

## Welche Blöcke funktionieren?

| Status | Segmente | Bedeutung |
|---|---|---|
| Im Juni als im Spiel geprüft dokumentiert | `start`, `straight`, `checkpoint`, `finish`, `curve_right`, `curve_left` | Flaches Modell mit einer Rasterzelle pro Block |
| Experimentell | `slope_up`, `slope_down` | Nur mit `--allow-unverified`; Höhenmodell noch im Spiel prüfen |
| Noch nicht unterstützt | Grössere Kurven, echte Schikanen, geneigte Übergänge, PlatformTech, Sprünge | Anschluss- und Platzbedarf fehlen |

Der Bildkatalog enthält **191 Namen: 190 RoadTech und 1 TrackWall**. Ein Bild oder
ein Eintrag in `BLOCK_MAP` belegt weder die Geometrie noch die korrekte Rotation.
Unbekannte Geometrie wird daher auch mit `--allow-unverified` abgelehnt.
`--force` kann diese Prüfungen nicht mehr umgehen.

## Dateien und Strecken

| Pfad | Zweck |
|---|---|
| `track_lib/` | Segmente, Composer, Schema- und Geometrieprüfung |
| `compose.py` | Design in Koordinaten umwandeln |
| `converter/build.py` | Koordinaten in eine GBX-Datei umwandeln |
| `converter/template.Map.Gbx` | Vorhandene Stadium-/Day-Vorlage, Raster 48 × 40 × 48 |
| `tools/design_schema.json` | Schema für neue Streckenentwürfe |
| `tools/track_schema.json` | Kompatibles Schema für die ausgegebenen Koordinaten |
| `tools/inspect_map.py` | Tatsächliche Namen, Positionen und Richtungen einer Referenzmap exportieren |
| `tools/build_test_pack.py` | Testpaket reproduzierbar neu bauen |
| `tests/`, `.github/workflows/tests.yml` | Regressionstests und Linux-/Windows-CI |
| `tracks/_validation/` | Fünf neue Kalibrierungsstrecken inklusive GBX-Dateien |
| `tracks/speedtech/proofcut/` | Bestehende 24-Block-Referenz; GBX mit korrigierten Metadaten neu gebaut |
| `tracks/speedtech/silvercut/`, `razorline/` | Historische, fehlerhafte Entwürfe; siehe jeweilige README |

Die Vorlage unterstützt derzeit **Stadium / Day**. Andere Umgebungen, Mood-
Werte und benutzerdefinierte Dekoration werden nicht stillschweigend ignoriert.
Zielzeiten (`target_at`) sind Planungsnotizen und werden nicht als gefahrene
Author Time oder Medaillenzeiten in die Map geschrieben.
