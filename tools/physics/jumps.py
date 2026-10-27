"""Extract jumps (airborne segments) and pair them with takeoff/landing blocks.

Inputs: telemetry dir from ghost_probe (with _index.csv), blocks dir from
`ghost_probe map` (one {mapUid}.blocks.csv per map).
Output: jumps.csv — one row per jump: map, takeoff/landing block, speed, angle,
distance, height change, airtime. Usage: python jumps.py <telemetry> <blocks> <out.csv>
"""
import csv, math, os, sys
from collections import Counter, defaultdict

MIN_AIR = 4        # samples (0.2 s): shorter = bumps, not jumps
CELL, LAYER = 32.0, 8.0
FREE_RADIUS = 24.0  # m: free block/item counts as "under the car" within this horizontal distance
MAP_SIZE = 48 * CELL  # m: standard 48x48 stadium grid
GROUND_Y = 14.0     # m: below this with no block = stadium floor (baked Grass, not in the block list)


def load_blocks(path):
    grid, free = defaultdict(list), []
    for r in csv.DictReader(open(path)):
        if r["kind"] == "block":
            grid[(int(r["gx"]), int(r["gz"]))].append((float(r["y"]), r["name"]))
        else:
            free.append((float(r["x"]), float(r["y"]), float(r["z"]), r["name"], r["kind"]))
    return grid, free


def block_under(grid, free, x, y, z):
    """Highest grid block at/below the car in its column, else nearest free block/item below."""
    best = None
    for by, name in grid.get((int(x // CELL), int(z // CELL)), []):
        if by <= y + 2 and (best is None or by > best[0]):
            best = (by, name)
    if best and y - best[0] < 3 * LAYER:
        return best[1]
    # Multi-cell blocks (ramps, slopes, big curves) are stored only at their origin cell:
    # fall back to the nearest origin within 2 cells that sits below the car.
    cx, cz = int(x // CELL), int(z // CELL)
    cand = [(math.hypot((gx + 0.5) * CELL - x, (gz + 0.5) * CELL - z), name)
            for gx in range(cx - 2, cx + 3) for gz in range(cz - 2, cz + 3)
            for by, name in grid.get((gx, gz), []) if by <= y + 2 and y - by < 3 * LAYER]
    if cand:
        return min(cand)[1]
    near =[(math.hypot(fx - x, fz - z), name) for fx, fy, fz, name, _ in free
            if fy <= y + 2 and y - fy < 3 * LAYER and math.hypot(fx - x, fz - z) < FREE_RADIUS]
    if near:
        return min(near)[1]
    if not (0 <= x < MAP_SIZE and 0 <= z < MAP_SIZE):
        return "OutsideMap"  # stadium scenery beyond the grid (stands, hills): not in the map file
    return "StadiumGround" if y < GROUND_Y else "?"


def main(tdir, bdir, out):
    index = list(csv.DictReader(open(f"{tdir}/_index.csv")))
    rows, cache = [], {}
    for g in index:
        bpath = f"{bdir}/{g['map_uid']}.blocks.csv"
        if not os.path.exists(bpath):
            continue
        if bpath not in cache:
            cache = {bpath: load_blocks(bpath)}
        grid, free = cache[bpath]
        d = list(csv.DictReader(open(f"{tdir}/{g['file']}")))
        f = lambda r, k: float(r[k])
        i = 0
        while i < len(d):
            if d[i]["ground"] == "0" and i > 0:
                j = i
                while j < len(d) and d[j]["ground"] == "0":
                    j += 1
                if j - i >= MIN_AIR and j < len(d):
                    a, b = d[i - 1], d[j]  # last ground sample, first ground sample
                    vh = math.hypot(f(a, "vx"), f(a, "vz"))
                    rows.append({
                        "map_uid": g["map_uid"], "ghost": g["file"], "vehicle": g.get("vehicle", ""),
                        "t_s": f(a, "t_ms") / 1000,
                        "takeoff": block_under(grid, free, f(a, "x"), f(a, "y"), f(a, "z")),
                        "landing": block_under(grid, free, f(b, "x"), f(b, "y"), f(b, "z")),
                        "speed_kmh": round(f(a, "speed_kmh"), 1),
                        "angle_deg": round(math.degrees(math.atan2(f(a, "vy"), vh)), 1),
                        "dist_m": round(math.hypot(f(b, "x") - f(a, "x"), f(b, "z") - f(a, "z")), 1),
                        "dy_m": round(f(b, "y") - f(a, "y"), 1),
                        "air_s": round((f(b, "t_ms") - f(a, "t_ms")) / 1000, 2),
                        "gas": round(sum(f(r, "gas") for r in d[i:j]) / (j - i), 2),
                    })
                i = j
            else:
                i += 1
    if not rows:
        sys.exit("no jumps found (are map UIDs in _index.csv matched by blocks/*.blocks.csv?)")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"{len(rows)} jumps from {len({r['ghost'] for r in rows})} ghosts → {out}")
    print("\nTop takeoff blocks:")
    for name, n in Counter(r["takeoff"] for r in rows).most_common(15):
        js = [r for r in rows if r["takeoff"] == name]
        med = lambda k: sorted(x[k] for x in js)[len(js) // 2]
        print(f"  {n:5d}  {name:45s} speed {med('speed_kmh'):6.0f} km/h  angle {med('angle_deg'):5.1f}°  "
              f"dist {med('dist_m') / CELL:4.1f} blocks  air {med('air_s'):.2f}s")


if __name__ == "__main__":
    main(*sys.argv[1:4])
