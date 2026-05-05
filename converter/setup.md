# Converter Setup

## 1. Dependencies

```bash
pip install -r converter/requirements.txt
```

`gbx-py` liefert nur das LZO-Binding (`gbx.lzo`) — die eigentliche
Bibliothek (Parser, Strukturen) ist als `converter/gbxpy/` im Repo gevendort
(Original: https://github.com/schadocalex/gbx-py).

## 2. TM2020-Map-Template

Das Skript baut die Map nicht aus dem Nichts, sondern öffnet ein leeres
TM2020-Template, ersetzt die Block-Liste und schreibt es zurück.

**Einmalig nötig:** eine leere TM2020-Map als Template anlegen.

1. TM2020 starten → **Track Editor** → **New Map**.
2. Stadium-Umgebung wählen, **nichts** platzieren, sofort speichern als `template`.
3. Datei aus dem Maps-Ordner kopieren:
   - Windows: `Documents/Trackmania/Maps/My Maps/template.Map.Gbx`
4. Ablegen unter:
   ```
   converter/template.Map.Gbx
   ```

Solange diese Datei fehlt, schlägt der Build mit einer klaren Fehlermeldung
fehl. `--dry-run` funktioniert auch ohne Template.

## 3. Verwendung

```bash
# Einzelne Map
python converter/build.py tracks/speedtech/silvercut/silvercut.json

# Nur prüfen, kein Output
python converter/build.py tracks/speedtech/silvercut/silvercut.json --dry-run

# Nicht automatisch in TM2020-Ordner kopieren
python converter/build.py track.json --no-deploy

# Alle Tracks unter tracks/ rekursiv bauen
python converter/build.py tracks --batch
```

Output: `<name>.Map.Gbx` neben der Eingabe-JSON. Wenn ein TM2020-Maps-Ordner
gefunden wird (`Documents/Trackmania/Maps/My Maps`), wird dort automatisch
deployed (außer mit `--no-deploy`).

## 4. Block-Mapping erweitern

In `converter/build.py` → `BLOCK_MAP`. Schlüssel = JSON-ID, Wert = echter
TM2020 Stadium-Blockname. Unbekannte IDs werden 1:1 durchgereicht.
