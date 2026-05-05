# TM2020 Claude Tracks – Cross-Session Context

Last updated: 2026-05-05

---

## What This Project Is

Growing library of AI-generated TM2020 tracks across 10 categories.
- **Claude Web (claude.ai):** designs tracks as JSON + optional SVG preview
- **User:** saves JSON to `tracks/{category}/{name}/`
- **Claude Code:** converts, commits, auto-deploys to TM2020

GitHub: https://github.com/SemyonGit/tm2020-claude-tracks
Local: `C:\Users\semyo\Documents\tm2020-claude-tracks`

---

## Pipeline Status

| Component | Status |
|-----------|--------|
| JSON → .Map.Gbx (converter/build.py) | ✅ Works — map loads in TM2020 |
| Block names (`RoadTech*` prefix, no `Stadium`) | ✅ Verified via real editor saves |
| Y_OFFSET=8 (JSON y=1 → GBX y=9) | ✅ Confirmed via template.Map.Gbx |
| Chunks 0x03043062/68/69 dropped | ✅ Required — block-count dependent |
| Auto-deploy to TM2020 Maps folder | ✅ Works when folder exists |
| Block placement / rotations | ⚠️ Empirically derived — needs in-game verification |
| Block connectivity (blocks join seamlessly) | ⚠️ Unverified — no completed in-game test yet |

---

## Current BLOCK_MAP (converter/build.py)

```python
BLOCK_MAP = {
    # Start / Finish / Checkpoint
    "StadiumRoadMainStart":          "RoadTechStart",
    "StadiumRoadMainFinish":         "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":   "RoadTechCheckpoint",
    "Checkpoint":                    "RoadTechStraight",  # via isWaypoint flag

    # Straight
    "StadiumRoadMainStraight":       "RoadTechStraight",

    # Curves — all mapped to 1×1 Curve1 (JSON uses 1-cell-per-block grid)
    "StadiumRoadMainCurve1Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve1Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve2Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve2In":       "RoadTechCurve1",
    "StadiumRoadMainCurve2Out":      "RoadTechCurve1",
    "StadiumRoadMainCurve3Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve3Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve4Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve4Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve5Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve5Left":     "RoadTechCurve1",

    # Chicanes — inline in JSON (no x/z offset); Straight keeps geometry intact
    "StadiumRoadMainChicaneRight":   "RoadTechStraight",
    "StadiumRoadMainChicaneLeft":    "RoadTechStraight",
    "StadiumRoadMainChicaneX2Right": "RoadTechChicaneX2Right",  # explicit 2-cell
    "StadiumRoadMainChicaneX2Left":  "RoadTechChicaneX2Left",
    "StadiumRoadMainChicaneX3Right": "RoadTechChicaneX3Right",
    "StadiumRoadMainChicaneX3Left":  "RoadTechChicaneX3Left",

    # Banking — no matching 1-cell block; fallback to Straight
    "StadiumRoadMainBankRight":      "RoadTechStraight",
    "StadiumRoadMainBankLeft":       "RoadTechStraight",
    "StadiumRoadMainTiltStraight":   "RoadTechTiltStraight",

    # Slopes — JSON delta = +1 y/cell → SlopeBase (NOT SlopeBase2)
    "StadiumRoadMainSlope1Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope1Down":     "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Down":     "RoadTechSlopeBase",

    # Special
    "StadiumRoadMainHole":           "RoadTechHole",
    "StadiumRoadMainPenalty":        "RoadTechPenalty",
    "StadiumRoadMainPenaltyDirt":    "RoadTechPenaltyDirt",
    "StadiumRoadMainPenaltyIce":     "RoadTechPenaltyIce",
    "StadiumRoadMainTurbo":          "RoadTechSpecialTurbo",
    "StadiumRoadMainNarrowCenter":   "RoadTechNarrowCenter",
    "StadiumRoadMainNarrowSide":     "RoadTechNarrowSide",

    # Walls — no RoadTech equivalent; fallback to Straight
    "StadiumRoadMainWallLeft":       "RoadTechStraight",
    "StadiumRoadMainWallRight":      "RoadTechStraight",
}
```

---

## Direction / Rotation Mapping (converter/build.py)

JSON rotation: 0=North, 1=East, 2=South, 3=West

```python
DIR_NAMES           = ("North", "East", "South", "West")
STRAIGHT_DIR_MAP    = (2, 1, 0, 3)   # for straights, start, finish, slopes, tilt
CURVE_RIGHT_DIR_MAP = (3, 0, 1, 2)   # for *Right and *In curves
CURVE_LEFT_DIR_MAP  = (0, 1, 2, 3)   # for *Left and *Out curves (mirror)
```

**Status:** Empirically derived from silvercut.json — NOT yet verified in TM2020.
Fix using test_kurven ground-truth data below.

---

## Ground-Truth Reference: test_kurven.Map.Gbx

Manually built S-curve (13 blocks), parsed 2026-05-05.
Path: `C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx`

```
 0. RoadTechStart     x=16 y=9 z=21 dir=North
 1. RoadTechStraight  x=16 y=9 z=22 dir=North
 2. RoadTechCurve1    x=16 y=9 z=23 dir=East
 3. RoadTechCurve1    x=15 y=9 z=23 dir=West
 4. RoadTechCurve1    x=15 y=9 z=24 dir=South
 5. RoadTechCurve1    x=16 y=9 z=24 dir=North
 6. RoadTechStraight  x=16 y=9 z=25 dir=North
 7. RoadTechCurve1    x=16 y=9 z=26 dir=South
 8. RoadTechCurve1    x=17 y=9 z=26 dir=North
 9. RoadTechCurve1    x=17 y=9 z=27 dir=East
10. RoadTechCurve1    x=16 y=9 z=27 dir=West
11. RoadTechStraight  x=16 y=9 z=28 dir=North
12. RoadTechFinish    x=16 y=9 z=29 dir=North
```

Key insights:
- Track flows in +z direction → dir=North for all straights/start/finish
- Curves form a 2×2 pattern (4 blocks per chicane: two 90° turns back-to-back)
- Screenshot in `tools/Pictures/` shows the S-curve layout

Parse command:
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

---

## Reference Maps Available

```
C:/Users/semyo/Documents/Trackmania/Maps/My Maps/jantronix wurst.Map.Gbx   (291 blocks, real player track)
C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx        (13 blocks, S-curve reference)
C:/Users/semyo/Documents/Trackmania/Maps/Downloaded/every platform block.Map.Gbx
```

---

## Existing Tracks

| Track | Category | Blocks | Status |
|-------|----------|--------|--------|
| silvercut | speedtech | 37 | JSON ✅, .Map.Gbx built, in-game connectivity unverified |
| razorline | speedtech | 14 | JSON only, not yet converted |

---

## Known Issues

1. **Block connectivity unverified** — silvercut.Map.Gbx loads but blocks may not join correctly in-game
2. **Rotation maps unverified** — STRAIGHT_DIR_MAP and curve maps need field testing vs test_kurven
3. **Walls/Banking fall back to Straight** — no visual effect currently
4. **catalog/blocks.json** — referenced but does not exist in repo

---

## Key Technical Facts

- **Python:** always `py -3.12`, always `$env:PYTHONIOENCODING = "utf-8"` first
- **gbxpy:** vendored in `converter/gbxpy/` — do NOT replace via pip
- **Template:** `converter/template.Map.Gbx` required (empty TM2020 map, created once in editor)
- **Blocks chunk:** `0x0304301F`
- **Chunks dropped:** `0x03043062`, `0x03043068`, `0x03043069`
- **Y_OFFSET = 8** — JSON y=1 → GBX y=9, `isGround=True` only when JSON y=1
- **Maps folder:** `C:/Users/semyo/Documents/Trackmania/Maps/My Maps/`

---

## Next Steps

1. Load silvercut.Map.Gbx in TM2020 → check if blocks connect visually
2. If broken: fix direction maps using test_kurven as reference
3. Commit fix: `🔧 Fix block placement from visual + parsed test_kurven`
4. Convert razorline.json
5. Build track library across all 10 categories

---

## Commit Format
```
🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)
📝 Update kontext.md
🔧 Fix {description}
```
