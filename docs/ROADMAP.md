# Roadmap

**Goal:** a Kacky map designed by Claude: brutally hard, every obstacle intentional,
every jump predicted before it's built (#20).

Tasks live in [GitHub Issues](https://github.com/SemyonGit/tm2020-claude-tracks/issues).
This file holds the *why* and the order. `tools/kontext.md` holds the current state.

## How we work

| Label | Meaning |
|---|---|
| `where:anywhere` | Runs without the game: work PC, cloud session, laptop |
| `where:home` | Needs TM2020 + Openplanet running on the home PC |
| `needs-ingame-test` | Only counts as done after a test drive |
| `track:*` | pipeline · physics · vocabulary · design |
| `phase-N` | Order. A phase can start before the previous one is fully done |

Home sessions are short: work through `needs-ingame-test` issues, save replays, done.
Everything else happens at work or in the cloud.

## Architecture (target)

```
Design (Claude) ──► composer (path → blocks) ──► build
                         ▲                         │  home:  bridge (tm2020-mcp) places + saves
     jump.py / jump table│                         │  away:  gbx-py writer (until #8 decides)
                         │                         ▼
     physics fit ◄── ghost_probe ◄── replays   verify_map_track (offline)
     (tools/physics)        ▲                      │
                            └──── test drive ◄─────┘
```

Three sources of truth, each measured rather than guessed:
- **Geometry**: block shapes and directions measured from real maps (tm2020-mcp corpus, #14, #15)
- **Physics**: gravity, drag, ground speed fitted from replay telemetry (#9, #11, #12)
- **Reality**: the test drive. Any model is wrong until a drive says otherwise.

## Phases

### Phase 0 – Setup (home)
- #2 Both Openplanet bridges running on the home PC

### Phase 1 – Prove the basics
| # | Task | Where |
|---|---|---|
| #3 | Bridge smoke test: game-built map, saved, verified | home |
| #4 | Bug?: Start/Finish backwards on N/S headings | home |
| #5 | Verify slopes | home |
| #6 | Offline `verify_map_track` as a second check | anywhere |
| #9 | Physics: full Kacky re-fit + hold-out validation | anywhere |

### Phase 2 – Restructure + measure
| # | Task | Where |
|---|---|---|
| #7 | Rewrite CLAUDE.md for new roles, trim kontext.md | anywhere |
| #8 | Decide: bridge-native building vs gbx-py | decision |
| #10 | Kacky jump table | anywhere |
| #11 | Ground model per surface | anywhere |
| #14 | Learn block connections + motifs from Kacky corpus | anywhere |
| #15 | Multi-cell block footprints | anywhere |

### Phase 3 – New mechanics
| # | Task | Where |
|---|---|---|
| #12 | Air control | anywhere |
| #13 | Decode turbo / ground-mode bytes | anywhere |
| #16 | Trick-surface track | home |
| #17 | Motif track (loop + reset) | home |

### Phase 4 – Off-grid + physics-designed jumps
| # | Task | Where |
|---|---|---|
| #18 | First free-block section | home |
| #19 | 5-jump micro-gauntlet designed with jump.py | home |

### Phase 5 – The goal
- #20 Kacky map

## Decisions so far

| Date | Decision | Why |
|---|---|---|
| 2026-10-27 | Plan on GitHub (Issues + this file), not a self-hosted site | Every session can reach it, nothing to keep running at home |
| 2026-10-27 | Physics from replay telemetry, not by decompiling the game | Legal, survives game updates, no game needed; first fit is ~2% median error |
| 2026-10-27 | kacky.gg + trackmania.io as the Kacky data source | All official maps + top ghosts, public, no login |
| 2026-10-27 | Jumps that use scenery outside the grid are excluded from design | Can't be placed or reproduced |

## Known risks

- **Physics model is approximate.** No air control or rotation yet; long flights are under-tested (#9, #12).
- **Building needs the home PC** once we go bridge-native (#8).
- **Unverified ghost bytes**: turbo / ground mode meaning is a guess (#13).
- **Kacky = platforms + free blocks.** Our block vocabulary is still road-only (#14, #15, #18).
