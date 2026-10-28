"""Offline track verifier (issue #6): does the road connect start → finish?

Walks the grid from the start block using block shapes LEARNED from real maps
(track_lib/data/learned_blocks.json), not the converter's own assumptions, so it is an
independent check of build.py. One-cell blocks only for now; a direction that wasn't
learned is derived by rotating a learned one. Unknown blocks are reported, not guessed.

Usage: python tools/verify_track.py <file.Map.Gbx> [...]
Exit code 0 = all connected.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "converter"))
from gbxpy import parse_file  # noqa: E402
from build import find_blocks_chunk  # noqa: E402

MODEL = ROOT / "track_lib" / "data" / "learned_blocks.json"
DIRS = ("North", "East", "South", "West")
# Same 1-cell shape as another, well-learned block (rarely used in the Kacky corpus).
SHAPE_ALIAS = {"RoadTechCheckpoint": "RoadTechStraight"}


def rot(v, k):
    """Rotate a (dx, dz) offset k quarter-turns: North→East→South→West (measured)."""
    x, z = v
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def load_shapes():
    learned = json.load(open(MODEL))["blocks"]
    shapes = {}
    for key, m in learned.items():
        if len(m["footprint"]) == 1 and m["exits"]:
            name, d = key.split("|")
            shapes.setdefault(name, {})[d] = (m["n"], [tuple(e[:2]) for e in m["exits"]])
    return shapes


def exits_of(shapes, name, d):
    """Exits for (name, dir) and how we know: 'learned', 'rotated' or 'alias'."""
    how = "learned"
    if name not in shapes and name in SHAPE_ALIAS:
        name, how = SHAPE_ALIAS[name], "alias"
    by_dir = shapes.get(name)
    if not by_dir:
        return None, "unknown"
    if d in by_dir:
        return by_dir[d][1], how
    best = max(by_dir, key=lambda k: by_dir[k][0])  # most-sampled direction
    k = DIRS.index(d) - DIRS.index(best)
    return [rot(e, k) for e in by_dir[best][1]], "rotated" if how == "learned" else how


def verify(path, shapes):
    return verify_blocks(find_blocks_chunk(parse_file(str(path))).Blocks, shapes)


def verify_blocks(blocks, shapes, jumps=None):
    """blocks: gbxpy block containers (name, dir, coords).
    jumps: {takeoff_cell: landing_cell} for declared gaps (track["jumps"]); the walk
    may cross those, and the landing block must open back toward the takeoff."""
    jumps = jumps or {}
    cells, notes = {}, []
    for b in blocks:
        c = (int(b.coords.x), int(b.coords.y), int(b.coords.z))
        cells[c] = (b.name, str(b.dir))
    starts = [c for c, (n, _) in cells.items() if n.endswith("Start")]
    if len(starts) != 1:
        return False, [f"expected 1 start block, found {len(starts)}"]
    cur, prev, steps = starts[0], None, 0
    while True:
        name, d = cells[cur]
        ex, how = exits_of(shapes, name, d)
        if ex is None:
            return False, notes + [f"{name} at {cur}: shape unknown (not in learned model)"]
        if how != "learned":
            notes.append(f"{name} {d}: shape {how}")
        if name.endswith("Finish") and prev is not None:
            return True, notes + [f"reached finish after {steps} blocks"]
        nxt = [(cur[0] + dx, cur[1], cur[2] + dz) for dx, dz in ex]
        nxt = [n for n in nxt if n != prev]
        if not nxt:
            return False, notes + [f"{name} at {cur}: dead end"]
        n = nxt[0]
        if n not in cells and cur in jumps:
            land = jumps[cur]
            step = (n[0] - cur[0], n[2] - cur[2])  # unit travel vector at takeoff
            back, _ = exits_of(shapes, *cells[land]) if land in cells else (None, None)
            if land not in cells or back is None or (-step[0], -step[1]) not in back:
                return False, notes + [f"jump from {cur}: no landing block facing back at {land}"]
            notes.append(f"jump {cur} → {land}")
            prev, cur, steps = cur, land, steps + 1
            # pretend we arrived from the adjacent cell so the walk continues forward
            prev = (land[0] - step[0], land[1], land[2] - step[1])
            continue
        if n not in cells:
            return False, notes + [f"{name} {d} at {cur} exits to {n}, which is empty"]
        back, _ = exits_of(shapes, *cells[n])
        if back is not None and (cur[0] - n[0], cur[2] - n[2]) not in back:
            return False, notes + [f"{cells[n][0]} {cells[n][1]} at {n} has no exit back to {cur}"]
        prev, cur, steps = cur, n, steps + 1
        if steps > len(cells):
            return False, notes + ["loop without finish"]


def main(paths):
    shapes, ok_all = load_shapes(), True
    for p in paths:
        ok, notes = verify(Path(p), shapes)
        ok_all &= ok
        print(f"{'✅' if ok else '❌'} {Path(p).name}")
        for n in dict.fromkeys(notes):
            print(f"   {n}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main(sys.argv[1:])
