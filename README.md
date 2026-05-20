# Ts does not work it has like 67 errors

# TM2020 Claude Tracks

> All tracks in this repository are designed by [Claude](https://claude.ai) (Anthropic).  
> No manual block placement — pure AI design.

---

## How It Works

```
Claude (claude.ai)          → designs track as JSON + SVG preview
User                        → saves JSON to tracks/{category}/{name}/
Claude Code (this session)  → converts, commits, deploys to TM2020
```

1. User commissions a track (style, difficulty, creativity, category)
2. Claude (Web) designs the layout and generates `.json` + optional SVG preview
3. User saves the JSON to the correct folder
4. Claude Code converts → `.Map.Gbx`, commits to GitHub, deploys to TM2020

---

## Track Categories

| Folder | Style | Description |
|--------|-------|-------------|
| `speedtech` | Precision | Tight lines, banking, chicanes |
| `fullspeed` | Full throttle | No braking, pure flow |
| `tech` | Technical | Complex blocks, maximum control |
| `dirt` | Off-road | Gravel, drifts, terrain |
| `rally` | Rally | Long curves, hills, nature |
| `stunts` | Stunt | Loops, wall-rides, jumps |
| `ice` | Ice | Slippery surface, no grip |
| `fun` | Fun | Varied, accessible to all |
| `lol` | LOL | Chaotic, absurd, surprising |
| `beginner` | Beginner | Wide, forgiving, educational |

---

## Difficulty Scale

| Level | Label | Audience |
|-------|-------|----------|
| 1 | Beginner | First laps |
| 2 | Medium | Casual players |
| 3 | Hard | Experienced drivers |
| 4 | Expert | Competitive |
| 5 | Brutal | Top 1% |

---

## Setup

```powershell
git clone https://github.com/SemyonGit/tm2020-claude-tracks
cd tm2020-claude-tracks
py -3.12 -m pip install -r converter/requirements.txt
```

See [converter/setup.md](converter/setup.md) for full setup including the required template map.

---

## File Structure Per Track

```
tracks/speedtech/silvercut/
├── silvercut.json           ← Claude (Web) output — block data
├── silvercut.Map.Gbx        ← Built by Claude Code — ready to play
└── silvercut_preview.svg    ← Layout preview (optional)
```

---

## Tools

| File | Purpose |
|------|---------|
| `converter/build.py` | JSON → .Map.Gbx converter |
| `converter/setup.md` | Setup instructions |
| `tools/track_schema.json` | JSON schema for all track files |
| `tools/claude_code_agent.md` | Claude Code instructions and role definition |

---

*Generated with Claude · Anthropic · [claude.ai](https://claude.ai)*
