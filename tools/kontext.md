# TM2020 Claude Tracks – Project Context
*Single source of truth. Updated after every session. Read this first.*

---

## Long-Term Goal 🎯
**Generate a Kacky-style map with Claude.**
Kacky = brutally hard, precision-based, one wrong move = restart.
Intentional AI design (not random) is our advantage over neural networks.

Milestone path:
- ✅ Pipeline works (JSON → .Map.Gbx loads in TM2020)
- 🔧 Block placement correct (currently fixing)
- ⬜ Full block catalog mapped (Advanced Editor blocks)
- ⬜ First fully connected drivable track
- ⬜ First brutal track (D5/5)
- ⬜ Kacky map

---

## GitHub Repo
https://github.com/SemyonGit/tm2020-claude-tracks
Local: C:\Users\semyo\Documents\tm2020-claude-tracks

---

## Roles
| Who | Does what |
|-----|-----------|
| **Claude Chat** (claude.ai) | Creative track design, JSON generation, SVG preview, long-term vision |
| **Claude Code** (VSCode/Codespaces, Opus 4.7) | Convert, fix bugs, parse maps, commit, deploy – never designs tracks |
| **User** | Saves JSON from chat to correct folder, reviews in TM2020, provides reference maps |

Claude Chat and Claude Code are separate sessions – kontext.md is the bridge.

---

## Pipeline
```
Claude Chat (claude.ai)
    ↓  designs track → generates JSON + SVG preview
User saves JSON to tracks/{category}/{name}/{name}.json
    ↓
Claude Code runs:
    PYTHONIOENCODING=utf-8 py -3.12 converter/build.py tracks/{category}/{name}/{name}.json
    ↓
.Map.Gbx → auto-copied to C:\Users\semyo\Documents\Trackmania\Maps\My Maps\
    ↓
User opens TM2020 and plays
    ↓
Claude Code commits: git add . && git commit -m "🏎️ ..." && git push
```

---

## Current Pipeline Status
| Component | Status |
|-----------|--------|
| JSON → .Map.Gbx (file created) | ✅ Works |
| Map loads in TM2020 | ✅ Works |
| Block names (RoadTech* prefix) | ✅ Verified |
| Y_OFFSET=8 | ✅ Confirmed |
| Block placement / rotations | ✅ Fixed |
| Curves connecting to straights | ✅ Fixed + verified |
| Down slopes (dir flip + y offset) | ✅ Fixed (2026-05-06) |
| Full block catalog | ✅ 120 blocks verified (catalog/blocks.json) |
| Kacky-style blocks | ⬜ Pending |

---

## Tech Stack
- **Python 3.12** – always use `py -3.12`
- **gbx-py** vendored in `converter/gbxpy/` (schadocalex/gbx-py)
- **construct** – `pip install construct`
- **Always prefix PowerShell with:** `$env:PYTHONIOENCODING = "utf-8"`
- **Claude Code:** `claude --dangerously-skip-permissions --model claude-opus-4-7 --max-turns 30`

---

## Folder Structure
```
tm2020-claude-tracks/
├── CLAUDE.md
├── README.md
├── converter/
│   ├── build.py                  ← Main converter (JSON → .Map.Gbx)
│   ├── gbxpy/                    ← Vendored gbx-py
│   ├── template.Map.Gbx          ← Empty TM2020 map (base for writing)
│   └── setup.md
├── tools/
│   ├── track_schema.json         ← JSON schema for all tracks
│   ├── kontext.md                ← THIS FILE
│   ├── claude_code_agent.md
│   └── Pictures/                 ← Visual references (editor screenshots)
└── tracks/
    ├── _reference/               ← Real TM2020 maps for parsing/analysis
    │   ├── test_kurven.Map.Gbx        ← User-built curve reference ✅
    │   ├── test_straights.Map.Gbx     ⬜ TODO: build and add
    │   ├── test_slopes.Map.Gbx        ⬜ TODO: build and add
    │   └── test_chicanes.Map.Gbx      ⬜ TODO: build and add
    ├── speedtech/silvercut/      ← First generated track
    ├── fullspeed/
    ├── dirt/
    ├── rally/
    ├── stunts/
    ├── fun/
    ├── lol/
    ├── beginner/
    ├── tech/
    └── ice/
```

---

## Track Categories
| Folder | Style | Difficulty range |
|--------|-------|-----------------|
| speedtech | Precision, banked curves, chicanes | 1–5 |
| fullspeed | No braking, flow | 1–5 |
| tech | Complex blocks, max control | 1–5 |
| dirt | Offroad, drifts | 1–5 |
| rally | Long curves, hills | 1–5 |
| stunts | Loops, wall-rides, jumps | 1–5 |
| ice | No grip, sliding | 1–5 |
| fun | Mixed, for everyone | 1–3 |
| lol | Chaotic, absurd | 1–3 |
| beginner | Wide, forgiving | 1–2 |

---

## JSON Schema (track.json)
```json
{
  "meta": {
    "name": "Silvercut",
    "author": "SemyonGit",
    "category": "speedtech",
    "difficulty": 3,
    "creativity": 3,
    "target_at": "00:55.000",
    "generated_by": "Claude (Anthropic)",
    "generated_at": "2026-05-05T00:00:00Z"
  },
  "settings": { "environment": "Stadium", "mood": "Day" },
  "blocks": [
    { "id": "StadiumRoadMainStart", "x": 10, "y": 1, "z": 20, "rotation": 0 }
  ],
  "checkpoints": [5, 12, 20],
  "sections": [
    { "name": "Launch", "description": "...", "block_range": [0, 5], "trap": "..." }
  ]
}
```

**JSON rotation convention:** 0=North, 1=East, 2=South, 3=West (matches TM2020 dir)

---

## Current BLOCK_MAP (converter/build.py)
```python
BLOCK_MAP = {
    "StadiumRoadMainStraight":      "RoadTechStraight",
    "StadiumRoadMainStart":         "RoadTechStart",
    "StadiumRoadMainFinish":        "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":  "RoadTechCheckpoint",
    "StadiumRoadMainCurve1Right":   "RoadTechCurve1",
    "StadiumRoadMainCurve1Left":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Right":   "RoadTechCurve2",
    "StadiumRoadMainCurve2Left":    "RoadTechCurve2",
    "StadiumRoadMainCurve3Right":   "RoadTechCurve3",
    "StadiumRoadMainCurve3Left":    "RoadTechCurve3",
    "StadiumRoadMainChicaneRight":  "RoadTechCurve1",   # placeholder
    "StadiumRoadMainChicaneLeft":   "RoadTechCurve1",   # placeholder
    "StadiumRoadMainBankRight":     "RoadTechStraight",  # placeholder
    "StadiumRoadMainBankLeft":      "RoadTechStraight",  # placeholder
    "StadiumRoadMainSlope2Up":      "RoadTechSlopeBase2",
    "StadiumRoadMainSlope2Down":    "RoadTechSlopeBase2",
    "StadiumRoadMainWallLeft":      "RoadTechStraight",  # placeholder
    "StadiumRoadMainWallRight":     "RoadTechStraight",  # placeholder
    "StadiumRoadMainTurbo":         "RoadTechSpecialTurbo",
}
```

---

## Known Technical Details
- gbx-py is vendored (pip package only delivers LZO binding, not parser)
- Chunks 0x03043062, 0x03043068, 0x03043069 dropped before write (block-count dependent)
- `$env:PYTHONIOENCODING = "utf-8"` always needed on Windows (emoji in print)
- template.Map.Gbx: ground blocks at y=9 → Y_OFFSET=8 (json y=1 + 8 = 9)
- TM2020 Simple Editor = RoadTech* blocks (yellow bordered platform style)
- TM2020 Advanced Editor = more block types, different naming

## Direction / Rotation Convention (VERIFIED)

**Slope blocks:** dir = direction the HIGH end faces. For dir=West: West face at TM2020_y+1, East face at TM2020_y.
- Up slopes going West (rot=3): dir=West, TM2020_y = json_y + Y_OFFSET ✓
- Down slopes going West (rot=3): dir=East, TM2020_y = json_y - 1 + Y_OFFSET ✓
  (json_y = road surface at entry/high end; block origin = low end = json_y-1)

**Curve blocks (both Right and Left use the same TM2020 block: RoadTechCurve1):**
dir encoding → which two faces are open:
  dir=North(0) → W+N | dir=East(1) → S+W | dir=South(2) → S+E | dir=West(3) → E+N

CURVE_RIGHT_DIR_MAP = (3,0,1,2): VERIFIED via silvercut 4-corner rectangle.
  CurveRight with JSON rot = car's approach direction → result = counterclockwise turn (left from car POV).
CURVE_LEFT_DIR_MAP  = (0,1,2,3): Theoretically correct (same block, clockwise turn from car POV).
  Not yet tested with actual Left-curve JSON.

STRAIGHT_DIR_MAP = (2,1,0,3): JSON rot → TM2020 dir. JSON z-axis is flipped vs TM2020:
  rot=0("North")→TM2020 South, rot=1("East")→TM2020 East, rot=2("South")→TM2020 North, rot=3("West")→TM2020 West.

---

## Reference Maps (for parsing)
```
Local My Maps:
  C:/Users/semyo/Documents/Trackmania/Maps/My Maps/jantronix wurst.Map.Gbx
  C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx

Downloaded:
  C:/Users/semyo/Documents/Trackmania/Maps/Downloaded/every platform block.Map.Gbx

Repo:
  tracks/_reference/test_kurven.Map.Gbx
```

Parse command:
```powershell
$env:PYTHONIOENCODING = "utf-8"
py -3.12 -c "
import sys
sys.path.insert(0, 'converter')
from gbxpy.parser import parse_file
data = parse_file('PATH_TO_MAP.Map.Gbx')
chunk = data.body[0x0304301F]
for i, b in enumerate(chunk.Blocks):
    print(f'{i:2d}. {b.blockName:35s} x={b.coord.x:3d} y={b.coord.y:3d} z={b.coord.z:3d} dir={b.dir}')
"
```

---

## Block Catalog (VERIFIED)
120 block names verified from mania-exchange image API (200=valid, 404=skip).
Images: `catalog/block_images/{BlockName}.png`
Full list: `catalog/blocks.json`
Script: `catalog/fetch_blocks.py`

Key groups confirmed in catalog:
- `RoadTech*` – Start, Finish, Checkpoint, Straight, Curve1-4, SlopeBase/2, SpecialTurbo/Boost/Boost2
- `RoadBump*` – same set as RoadTech
- `RoadDirt*` – same set
- `RoadIce*` – only Start, Straight, SpecialTurbo/Boost/Boost2 (no curves/checkpoints/finish!)
- `PlatformTech/Grass/Dirt/Ice*` – Base, Curve1-3, Slope, Loops, Start/Finish/Checkpoint (Kacky blocks!)
- `TrackWall*` – Straight, Curve1-4, SlopeBase/2, DeadendRound
- `DecoWall*` – Base, Curve1-4, SlopeBase, LoopStart/End

NOT in catalog (wrong names – now fall back to RoadTechStraight in build.py):
- RoadTechChicane* (no chicane block exists in RoadTech surface)
- RoadTechHole, RoadTechPenalty*, RoadTechNarrow*, RoadTechTiltStraight

Map viewer (no TM2020 needed): https://gbx.bigbang1112.cz/tool/map-viewer-engine
Upload any .Map.Gbx to view 3D layout in browser.

---

## test_kurven.Map.Gbx – Parsed Ground Truth
```
 0. RoadTechStart        x=16 y=9 z=21 dir=North
 1. RoadTechStraight     x=16 y=9 z=22 dir=North
 2. RoadTechCurve1       x=16 y=9 z=23 dir=East
 3. RoadTechCurve1       x=15 y=9 z=23 dir=West
 4. RoadTechCurve1       x=15 y=9 z=24 dir=South
 5. RoadTechCurve1       x=16 y=9 z=24 dir=North
 6. RoadTechStraight     x=16 y=9 z=25 dir=North
 7. RoadTechCurve1       x=16 y=9 z=26 dir=South
 8. RoadTechCurve1       x=17 y=9 z=26 dir=North
 9. RoadTechCurve1       x=17 y=9 z=27 dir=East
10. RoadTechCurve1       x=16 y=9 z=27 dir=West
11. RoadTechStraight     x=16 y=9 z=28 dir=North
12. RoadTechFinish       x=16 y=9 z=29 dir=North
```
Key insight: Curve dir encodes which two faces are open (not the travel direction).
See "Direction / Rotation Convention" section above for the full verified mapping.
CURVE_RIGHT_DIR_MAP = (3,0,1,2) verified correct for all 4 corners of silvercut.

---

## Commit Format
```
🏎️ Add {name} ({category} | D{d}/5 | C{c}/5)
🔧 Fix {what}
📝 Update {docs}
📦 Add {reference maps or assets}
```

---

## Next Steps (priority order)
1. ✅ Fix block rotation/direction mapping — curves verified, down slopes fixed
2. Test silvercut.Map.Gbx in TM2020: confirm hill works and track is drivable
3. Build reference maps in TM2020 editor and add to tracks/_reference/:
   - test_slopes.Map.Gbx (verify slope dir behavior empirically)
   - test_straights.Map.Gbx
   - test_chicanes.Map.Gbx
4. Test left curves (StadiumRoadMainCurve1Left) — CURVE_LEFT_DIR_MAP not yet empirically tested
5. ✅ Block catalog downloaded — 120 verified names in catalog/blocks.json + images
6. Expand BLOCK_MAP with PlatformTech* blocks (key for Kacky-style maps)
7. Generate first fully drivable connected track
8. Generate first D5/5 brutal track
9. Start working toward Kacky-style maps 🎯

---

## Cross-Session Rule
After every session where something changed:
Update this file (tools/kontext.md) and commit:
```
git add tools/kontext.md && git commit -m "📝 Update kontext.md" && git push
```
