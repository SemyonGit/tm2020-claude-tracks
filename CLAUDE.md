# TM2020 Claude Tracks – Claude Code Context

## Project
AI-designed Trackmania 2020 tracks across 10 categories, building toward a Kacky map
(brutally hard, every jump predicted before it's built).

**Start every session by reading `tools/kontext.md`** (current state). Plans and decisions:
`docs/ROADMAP.md`. Tasks: GitHub Issues (labels `where:home` / `where:anywhere`).

## Roles
- **Claude Code** designs, composes, builds, verifies, analyses data, commits. One session
  can do the whole loop. Designs only use verified blocks and must come with a test plan.
- **Claude Project (claude.ai)**, optional: brainstorming and concepts.
  Prompt: `tools/claude_project_prompt.md`.
- **User**: test drives in TM2020 (the final word on anything physical), reference maps,
  `where:home` tasks.

Never claim something works in-game until the user has driven it. Measured beats assumed:
check `tools/kontext.md` facts before reasoning about directions or physics.

## Stack
- Python 3.12 on Windows: `py -3.12`, prefix PowerShell with `$env:PYTHONIOENCODING = "utf-8"`
  (Linux/cloud: `python3`)
- Python deps: `pip install construct gbx-py pytest numpy` (`gbx-py` only provides LZO; the
  parser is vendored in `converter/gbxpy/`)
- .NET 10 SDK for `tools/ghost_probe/` (GBX.NET: ghost telemetry + map export)

## Key paths
```
compose.py, track_lib/               design path → connected block list
track_lib/data/learned_blocks.json   block footprints/exits learned from 740 real maps
converter/build.py                   JSON → .Map.Gbx, then verify_track, then deploy
converter/template.Map.Gbx           empty map used as build base
tools/verify_track.py                offline start→finish check (learned shapes)
tools/ghost_probe/                   C#: replays → CSV telemetry, maps → block CSV
tools/physics/                       air + ground model, jump table, downloaders
tools/vocab/                         block-shape learner, TMX map downloader
tools/track_schema.json              JSON schema (stable)
tests/                               pytest: directions + verifier regression
tracks/{category}/{name}/            {name}.design.json, {name}.json, {Name}.Map.Gbx
docs/                                ROADMAP, jump table, session log
```

## Workflow: a new track
1. Write `tracks/{category}/{name}/{name}.design.json` (segment path, verified segments only)
2. `py -3.12 compose.py tracks/.../{name}.design.json`
3. `py -3.12 converter/build.py tracks/.../{name}.json` → builds, runs verify_track, deploys
   to `C:/Users/semyo/Documents/Trackmania/Maps/My Maps/`
4. For jumps: size them with `tools/physics/jump.py` / `ground.py`; list the predictions
   in the test plan
5. Commit, push; label the issue `needs-ingame-test` until the user has driven it

## Workflow: physics / data
```
python tools/physics/download_kacky.py <dir>                                # or download_tmx.py
dotnet run --project tools/ghost_probe -- <dir>/replays <dir>/telemetry     # ghosts → CSV
dotnet run --project tools/ghost_probe -- map <dir>/maps <dir>/blocks       # maps → CSV
python tools/physics/holdout.py <telemetry>...                              # air fit + validation
python tools/physics/fit_ground.py tools/physics/ground_table.json <telemetry>...
python tools/physics/jumps.py <telemetry> <blocks> jumps.csv && python tools/physics/jump_table.py jumps.csv docs/jump_table.md
python tools/vocab/learn_blocks.py <blocks> track_lib/data/learned_blocks.json 15
```
Corpora live outside the repo (≈2 GB). Commit scripts and derived tables, not raw data.

## Before pushing
`py -3.12 -m pytest tests` must pass.

## Commit format
```
🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)
🔧 Fix …   🔬 Physics/data …   🧱 Block vocabulary …   ✅ Tests/verification …   📝 Docs …
```

## Categories
speedtech, fullspeed, tech, dirt, rally, stunts, ice, fun, lol, beginner

## JSON rotation convention
0 = North (travel −z), 1 = East (+x), 2 = South (+z), 3 = West (−x).
The mapping to TM2020 dirs lives in `converter/build.py` and is tested in `tests/test_directions.py`.

## Never modify
- `tools/track_schema.json`: the schema stays stable

## Cross-session continuity
After every session where something changed, update `tools/kontext.md` (current state only;
move anything historical to `docs/log/sessions.md`) and commit:
```
git add tools/kontext.md && git commit -m "📝 Update kontext.md"
```
