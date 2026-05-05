# Claude Code – TM2020 Track Agent

## Role
Claude Code handles everything **after** Claude (Web) has designed the track:
1. Validate the JSON against `tools/track_schema.json`
2. Convert JSON → `.Map.Gbx` via `converter/build.py`
3. Commit to GitHub
4. `.Map.Gbx` auto-deployed to TM2020 by the converter

Claude Code does **not** design tracks. That is Claude Web's job.

---

## Standard Workflow

```powershell
# 1. Validate
$env:PYTHONIOENCODING = "utf-8"
py -3.12 converter/build.py tracks/{category}/{name}/{name}.json --dry-run

# 2. Build
py -3.12 converter/build.py tracks/{category}/{name}/{name}.json

# 3. Commit
git add tracks/{category}/{name}/
git commit -m "🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)"
git push
```

---

## Converter Commands

```powershell
$env:PYTHONIOENCODING = "utf-8"

# Single track (builds + auto-deploys to TM2020)
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json

# Dry-run only (no file written, no deploy)
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json --dry-run

# Skip deploy
py -3.12 converter/build.py tracks/speedtech/silvercut/silvercut.json --no-deploy

# Batch — build all JSON files that don't yet have a .Map.Gbx
py -3.12 converter/build.py tracks --batch
```

---

## Parse an Existing Map (debugging / reference)

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

Reference maps available for parsing:
- `test_kurven.Map.Gbx` — 13-block S-curve, ground-truth for rotation debugging
- `jantronix wurst.Map.Gbx` — 291 blocks, real player-built track
- `every platform block.Map.Gbx` — block reference map

---

## Commit Format

```
🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)
```

Examples:
```
🏎️ Add silvercut (speedtech | D3/5 | C3/5)
🏎️ Add razorline (speedtech | D4/5 | C2/5)
```

---

## Track Folder Structure

```
tracks/{category}/{name}/
├── {name}.json            ← source of truth (Claude Web output)
├── {name}.Map.Gbx         ← built by Claude Code
└── {name}_preview.svg     ← optional layout preview
```

---

## Technical Reference

### Coordinate System
- JSON `y=1` = ground level → GBX `y=9` (Y_OFFSET = 8)
- `isGround=True` only when JSON y=1

### Rotation Convention
- JSON: 0=North, 1=East, 2=South, 3=West
- Matches TM2020 dir values directly

### Block Names
- All stadium road blocks use `RoadTech*` prefix (no `Stadium` prefix)
- Examples: `RoadTechStraight`, `RoadTechCurve1`, `RoadTechStart`

### GBX Chunks
- Block list: chunk `0x0304301F`
- Chunks `0x03043062`, `0x03043068`, `0x03043069` are dropped before writing (block-count dependent)

### Python Environment
- Always use `py -3.12`
- Always set `$env:PYTHONIOENCODING = "utf-8"` first in PowerShell
- `gbxpy` is vendored in `converter/gbxpy/` — do not replace via pip