# TM2020 Claude Tracks – Claude Code Context

## Project
Growing library of AI-generated TM2020 tracks across 10 categories.
Claude (Web) designs tracks as JSON. Claude Code converts, commits, and deploys.

## Roles
- **Claude Web (claude.ai):** creative design, JSON generation, SVG preview — never executed here
- **Claude Code (this session):** convert, fix bugs, commit, deploy — never design tracks
- **User:** saves JSON from Claude Web to the correct folder, reviews results in TM2020

## Stack
- Python 3.12 — always use `py -3.12`
- Always prefix Python commands with: `$env:PYTHONIOENCODING = "utf-8"`
- gbx-py vendored in `converter/gbxpy/` (source: schadocalex/gbx-py)
- `construct` library (`pip install construct`)
- Claude Code Opus 4.7 in VSCode

## Key Paths
```
tools/track_schema.json          → JSON schema for all track files
converter/build.py               → JSON → .Map.Gbx converter
converter/gbxpy/                 → vendored gbx-py library
converter/template.Map.Gbx       → empty TM2020 map used as build base
tracks/{category}/{name}/        → one folder per track
  {name}.json                    → Claude-generated track data
  {name}.Map.Gbx                 → built game file
  {name}_preview.svg             → layout preview (optional)
```

## TM2020 Maps Folder (Windows)
```
C:/Users/semyo/Documents/Trackmania/Maps/My Maps/
```

## Reference Maps for Parsing
```
C:/Users/semyo/Documents/Trackmania/Maps/My Maps/jantronix wurst.Map.Gbx   (291 blocks)
C:/Users/semyo/Documents/Trackmania/Maps/My Maps/test_kurven.Map.Gbx        (13 blocks, S-curve reference)
C:/Users/semyo/Documents/Trackmania/Maps/Downloaded/every platform block.Map.Gbx
```

## Workflow
1. Validate JSON against `tools/track_schema.json`
2. Run `converter/build.py` → `.Map.Gbx`
3. `git add + commit + push`
4. `.Map.Gbx` auto-deployed to TM2020 Maps folder by converter

## Commit Format
```
🏎️ Add {name} ({category} | D{difficulty}/5 | C{creativity}/5)
```

## Categories
speedtech, fullspeed, tech, dirt, rally, stunts, ice, fun, lol, beginner

## Current Pipeline Status
- JSON → .Map.Gbx loads in TM2020 ✅
- Block names verified: `RoadTech*` prefix (no `Stadium` prefix) ✅
- Y_OFFSET=8 confirmed correct (JSON y=1 → GBX y=9) ✅
- Chunks 0x03043062/68/69 dropped before writing (block-count dependent) ✅
- Block placement / rotations: fix in progress (test_kurven.Map.Gbx is ground-truth reference)

## JSON Rotation Convention
- 0 = North, 1 = East, 2 = South, 3 = West

## Never Modify (Claude Web only)
- `tools/track_schema.json` — schema stays stable

## Cross-Session Continuity
After EVERY session where something changed (new fix, new discovery, new block mapping,
pipeline change, anything relevant):

Update `tools/kontext.md` to reflect the latest project state.
This file is the single source of truth for cross-session continuity.
It is read at the start of every new Claude Code session.

Always include in kontext.md:
- Current pipeline status (what works, what doesn't)
- Latest BLOCK_MAP
- Latest fixes and discoveries
- Current known issues
- Next steps

After updating kontext.md always commit:
```
git add tools/kontext.md && git commit -m "📝 Update kontext.md"
```
