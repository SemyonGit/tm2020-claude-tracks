# Converter Setup

## 1. Dependencies

```powershell
py -3.12 -m pip install -r converter/requirements.txt
```

`gbx-py` (pip) only installs the LZO binding (`gbx.lzo`). The actual parser and
structures are vendored as `converter/gbxpy/` (source: https://github.com/schadocalex/gbx-py).
Do not replace or upgrade `converter/gbxpy/` via pip.

## 2. TM2020 Map Template

The converter does not build from scratch — it opens an empty TM2020 template,
replaces the block list, and writes it back.

**One-time setup:**
1. Launch TM2020 → **Track Editor** → **New Map**
2. Choose Stadium environment, place **nothing**, save immediately as `template`
3. Copy the file from:
   ```
   C:/Users/semyo/Documents/Trackmania/Maps/My Maps/template.Map.Gbx
   ```
4. Place it at:
   ```
   converter/template.Map.Gbx
   ```

Without this file the build fails with a clear error. `--dry-run` works without it.

## 3. Usage

Always set encoding first in PowerShell:
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

```powershell
# Single track
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json

# Dry-run (validate only, no output written)
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json --dry-run

# Skip auto-deploy to TM2020 folder
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json --no-deploy

# Build all tracks under tracks/ recursively
py -3.12 converter/build.py tracks --batch
```

Output: `{name}.Map.Gbx` written next to the input JSON.
If `C:/Users/semyo/Documents/Trackmania/Maps/My Maps/` exists, the file is auto-deployed there (unless `--no-deploy`).

## 4. Parsing Existing Maps (for reference/debugging)

```powershell
$env:PYTHONIOENCODING = "utf-8"
py -3.12 -c "
import sys
sys.path.insert(0, 'converter')
from gbxpy.parser import parse_file
data = parse_file('C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx')
chunk = data.body[0x0304301F]
for i, b in enumerate(chunk.Blocks):
    print(f'{i:2d}. {b.blockName:35s} x={b.coord.x:3d} y={b.coord.y:3d} z={b.coord.z:3d} dir={b.dir}')
"
```

## 5. Extending the Block Map

In `converter/build.py` → `BLOCK_MAP`. Key = JSON block ID, value = real TM2020 block name.
Unknown IDs are passed through as-is.