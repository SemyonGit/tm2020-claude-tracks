# Arbeitsablauf für Coding-Assistenten

Verbindlichen Projektkontext zuerst aus [kontext.md](kontext.md) und
[CLAUDE.md](../CLAUDE.md) lesen. Die ältere Trennung nach Chat-Modell und festen
Modellversionen ist für die Dateiformate nicht relevant.

1. Design und unterstützte Segmente prüfen.
2. `compose.py <name>.design.json` ausführen.
3. `converter/build.py <name>.json --dry-run` ausführen.
4. `converter/build.py <name>.json --no-deploy` ausführen.
5. `python -m pytest -q` und `python catalog/fetch_blocks.py --check` ausführen.
6. Quellen, erzeugte GBX-Dateien und aktuelle Kontextnotizen zusammen versionieren.
7. Spieltests klar vom technischen Build unterscheiden.

Die Befehle verwenden den Python-Interpreter aus der virtuellen Umgebung;
Details und Windows-Befehle stehen in [converter/setup.md](../converter/setup.md).

Zum Debuggen einer vorhandenen Map:

```powershell
.\.venv\Scripts\python.exe tools/inspect_map.py "C:\Pfad\Referenz.Map.Gbx" --output build/referenz.blocks.json
```

Der Parser verwendet `block.name`, `block.coords.x/y/z` und `block.dir`.
Frühere Befehle mit `blockName` oder `coord` waren für diesen vendored Parser
falsch. Ein Blocklistenexport allein liefert noch keine gemessenen Anschlüsse.

Neue Fähigkeiten ergänzen die expliziten Metadaten in `track_lib/blocks.py`,
die Rotation im Converter sowie passende Referenztests. Freie Aliasnamen oder
Bildkatalogeinträge sollen keine fehlende Geometrie ersetzen.
