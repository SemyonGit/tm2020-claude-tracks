# kontext.md — current project state

*Read this first in every session. Current state only; history is in `docs/log/sessions.md`,
plans and decisions in `docs/ROADMAP.md`, tasks in GitHub Issues.*
Last updated: 2026-10-28

## Goal
A Kacky map designed by Claude: brutally hard, every obstacle intentional, every jump
predicted before it is built (issue #20).

## What works

| Area | Status | Where |
|---|---|---|
| Design path → connected block list | ✅ | `compose.py`, `track_lib/` |
| JSON → `.Map.Gbx` (gbxpy) | ✅ loads in TM2020 | `converter/build.py` |
| Start/Finish facing, all 4 headings | ✅ fixed from corpus data, ⏳ drive Compass (#4) | `build.py tm2020_dir` |
| Unique map UID + name per track | ✅ in file, ⏳ in-game check (#21) | `build.py map_uid` |
| Offline start→finish check after every build | ✅ | `tools/verify_track.py` |
| Replay/ghost telemetry → CSV | ✅ 3,943 ghosts parsed, 0 failures | `tools/ghost_probe/` (.NET 10) |
| Map blocks/items → CSV (world frame) | ✅ 740/740 maps | `ghost_probe map` |
| Air physics (gravity + drag) | ✅ hold-out validated | `tools/physics/jump.py` |
| Ground acceleration per surface | ✅ Asphalt/Dirt/Ice/Grass; ❌ Plastic | `tools/physics/ground.py` |
| Kacky jump table | ✅ 17,407 jumps | `docs/jump_table.md` |
| Learned block shapes (footprint + exits) | 🔧 1-cell good, multi-cell partly | `track_lib/data/learned_blocks.json` |
| Live editor bridges (tm2020-mcp, tm-control-mcp) | ⬜ not installed yet (#2) | home PC |

## Verified blocks (composer segments)
start, straight, checkpoint, finish, curve_right, curve_left (driven in-game).
slope_up / slope_down: unverified (#5).

## Key facts (measured, not assumed)

**Grid / directions**
- Grid cell = 32 m × 8 m × 32 m. World y = (grid y − 8) × 8 → `Y_OFFSET = 8`; ground grid y = 9.
- RoadTech forward by stored dir: **North=+Z, East=−X, South=−Z, West=+X**
  (231 Start blocks in 737 Kacky maps, 0 exceptions). Exits rotate N→E→S→W as (x,z)→(−z,x).
- Our JSON headings: 0=N travel −z, 1=E +x, 2=S +z, 3=W −x.
  - Start/Finish dir = `(rot + 2) % 4`
  - Straights/checkpoints: `STRAIGHT_DIR_MAP = (2,1,0,3)`
  - Curves: `CURVE_RIGHT_DIR_MAP = (3,0,1,2)`, `CURVE_LEFT_DIR_MAP = (0,1,2,3)`
  - All checked by `tests/test_directions.py` against the measured geometry.
- Curve1 open sides: North {−X,+Z}, East {−X,−Z}, South {+X,−Z}, West {+X,+Z}.
- Ghost spawn = start-block corner + (16, ~2, 16) m.

**Air physics** (6,326 free flights, hold-out by map)
- CarSport gravity **25.08 m/s²**; Snow/Rally/Desert ≈ **40.8 m/s²**.
- CarSport horizontal drag: 0.6 m/s² @50 km/h → 1.4 @150 → 2.2 @250 → 3.0 @350 → 3.8 @475 → 5.6 @675.
  Snow/Rally ≈ 0.1–0.3.
- Error: ≤1.5 s flights median 0.66 m (p90 2.0); >1.5 s median 2.9 m (p90 10.1).
- Excluded from "free flight": reactor (ground-mode bits 0x7C), slow-mo (`sim_coef` ≠ 255),
  mid-air body collisions (accel spike > 60 m/s²). Collisions, not air control or Kacky
  bugs, caused the large long-flight errors.

**Ground** (full gas, straight, flat)
- CarSport Asphalt accel shows gear steps: 15.8 m/s² <100 km/h, ~10.5 to 200, ~7 to 400, ~5 to 600.
- From standstill: 2 blocks → 145 km/h, 10 → 272, 20 → 361 (`ground.py`).
- Data above ~600 km/h too thin; predictions stop there.

**Kacky**
- Top takeoff blocks are walls/structures, not road: DecoWallBasePillar, DecoWallBase,
  StructureBase, PlatformTechBase, StructureSupportDeadend.
- ~1.7% of WR jumps launch from stadium scenery outside the 48×48 grid (can't be placed).
- Some Kacky maps are driven on the baked stadium floor (`Grass`, not in the block list).

**File format**
- Ghost samples every 50 ms: position, rotation, velocity, inputs, gear, rpm, ground contact,
  per-wheel material (keeps its last value in the air), suspension, ground-mode byte.
- Turbo byte meaning unclear (#13); `0x80` treated as turbo, `0x02` is not.
- GBX.NET 2.4.5 throws in chunk 0x0304303D (lightmap cache) on our maps + some Kacky maps
  → read with `SafeSkippableChunks + IgnoreExceptionsInBody`.
- Vendored gbxpy must not parse the same map twice in one process (ZipFile GC warning).

## Data sources (public, no login)
- trackmania.exchange API: maps + replays (`tools/physics/download_tmx.py`, `tools/vocab/download_tmx_maps.py`)
- kacky.gg API: official Kacky event map UIDs (`api.kacky.gg/v1/events/{id}/maps?limit=1000`)
- trackmania.io: map file URLs + top ghosts (`tools/physics/download_kacky.py`)
- Corpora are NOT committed (≈2 GB); scripts rebuild them.

## Known issues
- #4, #21: need one drive of `tracks/beginner/compass/Compass.Map.Gbx`.
- #5: slopes unverified.
- Map header author = template creator's account (zone "World|Asia|Bhutan").
- `tracks/speedtech/silvercut/Silvercut.Map.Gbx` is a stale build with no start block;
  its JSON uses placeholder blocks and refuses to build.
- Multi-cell footprints are inconsistent across directions for some blocks (#15).

## Next
- Home: #2 install bridges → #3 smoke test → drive Compass (#4, #21) → #5 slopes.
- Anywhere: #15 footprints with the TMX road corpus, #13 turbo bits, #12 remaining air-control question.
