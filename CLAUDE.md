# TM2020 Claude Tracks – Coding-Kontext

Lies zuerst `tools/kontext.md`. Projektziel: gezielt entworfene TM2020-Strecken,
langfristig eine Kacky-Map. Entwürfe verwenden `*.design.json`; der Composer
berechnet die Koordinaten. Der Benutzer prüft das Ergebnis im Spiel.

## Arbeiten im Projekt

- Python 3.12. Unter Windows `py -3.12` zum Erstellen der `.venv`, danach
  `.\.venv\Scripts\python.exe`; unter Linux `.venv/bin/python`.
- Requirements und Befehle stehen in `converter/setup.md`.
- `tools/design_schema.json` ist das Eingabeformat für Entwürfe.
  `tools/track_schema.json` ist das Koordinatenformat. Änderungen daran müssen
  mit bestehenden gültigen Dateien kompatibel und durch Tests abgedeckt sein.
- `track_lib/blocks.py` ist die Quelle für unterstützte Anschlussgeometrie und
  deren Prüfstatus. `converter/build.py` enthält die Alias- und GBX-Rotationsdaten.
- Katalogbilder belegen nur Namen. Neue Blockgeometrie mit Referenzmaps prüfen.
- Steigungen bleiben unverified, bis die vier Kalibrierungsmaps im Spiel geprüft
  wurden. `--allow-unverified` ist eine ausdrückliche Kalibrierungsoption.
- Den vendored Parser nicht durch ein gleichnamiges pip-Paket ersetzen.
  Lokale Änderungen in `converter/gbxpy/PATCHES.md` dokumentieren.
- Vor einem Commit `python -m pytest -q` und den Katalogcheck ausführen.
- Gebaute GBX-Dateien mit Source-JSONs synchron halten. Durch den Parser
  bestätigte Dateien nicht als im Spiel getestet ausgeben.
- Nach relevanten Änderungen `tools/kontext.md` aktualisieren; offene Arbeiten
  und tatsächliche Testergebnisse nachvollziehbar halten.

Konkrete nächste Aufgabe: `tools/NEXT_STEPS.md`. Historische Referenzdateien in
lokalen Windows-Ordnern sind nicht automatisch in dieser Umgebung verfügbar.
