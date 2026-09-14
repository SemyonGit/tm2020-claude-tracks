# Setup und Verwendung

Stand: 14. September 2026. Im Repository ist die benötigte Vorlage bereits vorhanden.
Die Befehle werden im Projektordner ausgeführt.

## Windows / PowerShell

```powershell
$env:PYTHONIOENCODING = "utf-8"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Eine Aktivierung der virtuellen Umgebung ist nicht nötig. Für reine Verwendung
ohne Tests genügt `-r converter/requirements.txt`.

## Linux / macOS

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Python 3.12 ist die getestete Version. `construct`, `gbx-py`, `jsonschema` und der
RFC-3339-Prüfer werden über die Requirements installiert. Das Paket `gbx-py`
liefert die LZO-Bindung; der eigentliche Parser liegt in `converter/gbxpy/`.
Lokale Parserkorrektur: [PATCHES.md](gbxpy/PATCHES.md).

## Eine Strecke bauen

```powershell
.\.venv\Scripts\python.exe compose.py tracks/speedtech/proofcut/proofcut.design.json
.\.venv\Scripts\python.exe converter/build.py tracks/speedtech/proofcut/proofcut.json --dry-run
.\.venv\Scripts\python.exe converter/build.py tracks/speedtech/proofcut/proofcut.json --no-deploy
```

`compose.py` überschreibt nie die Eingabedatei. Aus `name.design.json` wird
standardmässig `name.json`. Der Converter schreibt `{meta.name}.Map.Gbx` neben
diese Datei. Mit `--output-dir build/maps` lässt sich ein anderer Ausgabeordner
angeben. Bestehende Ausgaben derselben Strecke werden atomar ersetzt.

Ohne `--no-deploy` sucht der Converter in `Documents/Trackmania/Maps/My Maps`
und gegebenenfalls im OneDrive-Dokumentenordner. Für einen anderen Pfad:

```powershell
.\.venv\Scripts\python.exe converter/build.py tracks/speedtech/proofcut/proofcut.json --maps-dir "C:\Users\semyo\Documents\Trackmania\Maps\My Maps"
```

Der angegebene Ordner muss existieren. Der GitHub-Build kann nicht auf deinen
lokalen Trackmania-Ordner zugreifen.

## Testpaket

```powershell
.\.venv\Scripts\python.exe tools/build_test_pack.py --include-slopes
```

Die fünf Maps liegen danach in `build/test-pack/`. Dieser Befehl kopiert sie
nicht ins Spiel. Ohne `--include-slopes` wird nur die flache Testmap gebaut.
Die mitgelieferten GBX-Dateien und die Anleitung stehen unter
[tracks/_validation/](../tracks/_validation/README.md).

Einzelne Steigungstests benötigen `--allow-unverified` sowohl beim Composer als
auch beim Converter. Die Option erlaubt ausschliesslich das vorhandene
experimentelle Steigungsmodell.

## Batch und Fehlersuche

```powershell
.\.venv\Scripts\python.exe converter/build.py tracks/speedtech/proofcut --batch --no-deploy
.\.venv\Scripts\python.exe tools/inspect_map.py "C:\Pfad\test_slopes.Map.Gbx" --output build/test_slopes.blocks.json
.\.venv\Scripts\python.exe catalog/fetch_blocks.py --check
```

Batch baut alle Koordinaten-JSONs erneut, überspringt `*.design.json` und liefert
bei mindestens einem Fehler Exitcode 1. `tracks --batch` schlägt aktuell bewusst
fehl: Silvercut und Razorline sind alte ungültige Entwürfe, und Steigungen sind
standardmässig gesperrt. Für einen erfolgreichen Lauf einen konkreten gültigen
Streckenordner oder das Testpaket verwenden.

## Vorlage und Grenzen

Die mitgelieferte Vorlage enthält zwei Basisblöcke. Diese werden vollständig
ersetzt. Ihr Raster misst 48 × 40 × 48; JSON-y=1 entspricht GBX-y=9. Flache
Koordinaten müssen x/z=0–47 und y=1–31 einhalten. Steigungen benötigen innerhalb
dieses Bereichs auch Platz für ihr hohes Ende.

Die Account-Kennung des Template-Autors bleibt erhalten: Ein GitHub-Name ist
keine Trackmania-Account-Kennung. Name und Map-ID werden in Body, Header und XML
synchronisiert; die neue ID hängt vom benannten Layout ab. Thumbnail und weitere
Editorinformationen stammen weiterhin aus der Vorlage. Deshalb die fertige Map
im Editor öffnen, speichern, fahren und bei Bedarf validieren. Die Dateien
enthalten noch keine durch diese Überarbeitung gefahrene Author Time.
