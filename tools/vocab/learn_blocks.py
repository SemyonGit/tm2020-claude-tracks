"""Learn block footprints + connection exits from a map corpus (issues #14, #15).

Idea: blocks can't overlap, so cells around a block's origin that (almost) never hold
another block's origin belong to its footprint. Cells just outside the footprint that
usually DO hold a block are its connections (exits). Learned per (block, dir), grid
blocks only, on the origin's layer (dy=0) — vertical extent is not learned yet.

Usage: python learn_blocks.py <blocks-dir> <out.json> [min_samples=30]
Output: {"Name|Dir": {"n", "maps", "footprint": [[dx,dz],...], "exits": [[dx,dz,share],...],
         "consistent": footprint size agrees across directions}}
plus usage stats for every block name.
"""
import json, sys
from collections import Counter, defaultdict
from corpus import load_corpus, origin_index

W = 5              # search window (cells) around the origin
FOOT_RATIO = 0.5  # footprint cell: occupancy below 50% of the window's median occupancy
FOOT_ABS = 0.12    # ...and below 12% absolute
EXIT_MIN = 0.55    # exit: neighbour cell occupied in ≥55% of samples
MAX_FOOT = 25      # cells; bigger = flood fill leaked into empty space
DIRS = ("North", "East", "South", "West")
SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def rot(v, k):
    """Rotate (dx, dz) k quarter-turns North→East→South→West: (x, z) → (−z, x) (measured)."""
    x, z = v
    for _ in range(k % 4):
        x, z = -z, x
    return x, z


def learn(maps, min_samples):
    occ = defaultdict(Counter)        # (name, dir) -> Counter[(dx,dz)] occupied
    n, in_maps = Counter(), defaultdict(set)
    usage, usage_maps = Counter(), defaultdict(set)
    for uid, rows in maps:
        idx = origin_index(rows)
        for name, x, y, z, d, v in rows:
            usage[name] += 1
            usage_maps[name].add(uid)
            key = (name, d)
            n[key] += 1
            in_maps[key].add(uid)
            c = occ[key]
            for dx in range(-W, W + 1):
                for dz in range(-W, W + 1):
                    if (dx or dz) and (x + dx, y, z + dz) in idx:
                        c[(dx, dz)] += 1
    model = {}
    for key, cnt in n.items():
        if cnt < min_samples:
            continue
        share = {(dx, dz): occ[key][(dx, dz)] / cnt
                 for dx in range(-W, W + 1) for dz in range(-W, W + 1) if dx or dz}
        base = sorted(share.values())[len(share) // 2]
        thr = min(FOOT_ABS, FOOT_RATIO * base)
        foot, todo = {(0, 0)}, [(0, 0)]
        while todo:
            cx, cz = todo.pop()
            for nx, nz in ((cx + 1, cz), (cx - 1, cz), (cx, cz + 1), (cx, cz - 1)):
                if (nx, nz) not in foot and (nx, nz) in share and share[(nx, nz)] < thr:
                    foot.add((nx, nz)); todo.append((nx, nz))
        leaked = len(foot) > MAX_FOOT
        if leaked:
            foot = {(0, 0)}
        ring = {(fx + ox, fz + oz) for fx, fz in foot for ox, oz in ((1, 0), (-1, 0), (0, 1), (0, -1))} - foot
        exits = sorted(([dx, dz, round(share[(dx, dz)], 2)] for dx, dz in ring
                        if share.get((dx, dz), 0) >= EXIT_MIN), key=lambda e: -e[2])
        model[f"{key[0]}|{key[1]}"] = {
            "_side_share": {o: share[o] for o in SIDES},
            "n": cnt, "maps": len(in_maps[key]),
            "footprint": sorted([list(c) for c in foot]),
            "footprint_uncertain": leaked,
            "exits": exits,
        }
    # Cross-direction check: a block's footprint must have the same cell count in every
    # direction, with bounding-box width/depth swapped between North/South and East/West.
    by_name = defaultdict(dict)
    for key, m in model.items():
        name, d = key.split("|")
        xs = [c[0] for c in m["footprint"]]; zs = [c[1] for c in m["footprint"]]
        dims = (max(xs) - min(xs) + 1, max(zs) - min(zs) + 1)
        by_name[name][d] = (len(m["footprint"]), dims if d in ("North", "South") else dims[::-1],
                            m["footprint_uncertain"])
    for name, dirs in by_name.items():
        sizes = {(n, dims) for n, dims, leak in dirs.values()}
        ok = len(sizes) == 1 and not any(leak for *_, leak in dirs.values()) and len(dirs) >= 2
        for d in dirs:
            model[f"{name}|{d}"]["consistent"] = ok
    # One-cell blocks: pool all directions in the North frame (rotation about the single
    # cell is exact), so every direction gets the same, better-sampled exit set.
    for name, dirs in by_name.items():
        if not all(model[f"{name}|{d}"]["consistent"] and len(model[f"{name}|{d}"]["footprint"]) == 1
                   for d in dirs):
            continue
        pooled = defaultdict(list)
        for d in dirs:
            k = DIRS.index(d)
            for o, sh in model[f"{name}|{d}"]["_side_share"].items():
                pooled[rot(o, -k)].append(sh)
        canon = [o for o, v in pooled.items() if sum(v) / len(v) >= EXIT_MIN]
        for d in DIRS:
            k = DIRS.index(d)
            key = f"{name}|{d}"
            entry = model.setdefault(key, {"n": 0, "maps": 0, "footprint": [[0, 0]],
                                           "footprint_uncertain": False, "consistent": True})
            entry["exits"] = sorted([[*rot(o, k), round(sum(pooled[o]) / len(pooled[o]), 2)] for o in canon],
                                    key=lambda e: -e[2])
            entry["exits_pooled"] = True
    for m in model.values():
        m.pop("_side_share", None)
    stats = {name: {"count": c, "maps": len(usage_maps[name])}
             for name, c in usage.most_common()}
    return model, stats


def main(bdir, out, min_samples=30):
    maps = load_corpus(bdir)
    model, stats = learn(maps, min_samples)
    json.dump({"source": f"{len(maps)} maps", "min_samples": min_samples,
               "blocks": model, "usage": stats}, open(out, "w"), separators=(",", ":"))
    multi = sum(len(m["footprint"]) > 1 for m in model.values())
    cons = sum(m["consistent"] for m in model.values())
    print(f"{len(model)} (block, dir) learned from {len(maps)} maps; {multi} multi-cell; "
          f"{cons} consistent across directions; → {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30)
