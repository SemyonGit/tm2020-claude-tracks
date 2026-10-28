"""Compare a real drive with the jump predictions stored in a track JSON (issue #19).

Usage: python check_drive.py <replay-or-ghost.Gbx> <track.json>
Needs the .NET SDK (runs tools/ghost_probe on the replay). The track JSON must contain
predictions: python plan_jumps.py <track.json> --write
"""
import csv, io, json, math, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CELL, LAYER = 32.0, 8.0
HEADING = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}  # JSON heading → (dx, dz)


def telemetry(replay):
    out = subprocess.run(["dotnet", "run", "--project", str(ROOT / "tools" / "ghost_probe"), "--", str(replay)],
                         capture_output=True, text=True, check=True).stdout
    lines = out.splitlines()
    # one header per ghost in the file; the first ghost is the driver's run
    end = next((i for i in range(1, len(lines)) if lines[i].startswith("t_ms,")), len(lines))
    return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(io.StringIO("\n".join(lines[:end])))]


def flights(rows, min_s=0.3):
    res, i = [], 1
    while i < len(rows):
        if rows[i]["ground"] == 0:
            j = i
            while j < len(rows) and rows[j]["ground"] == 0:
                j += 1
            if j < len(rows) and (rows[j]["t_ms"] - rows[i - 1]["t_ms"]) / 1000 >= min_s:
                res.append((rows[i - 1], rows[j]))
            i = j
        i += 1
    return res


def main(replay, track_path):
    track = json.loads(Path(track_path).read_text(encoding="utf-8"))
    jumps = [j for j in track.get("jumps", []) if "predicted" in j]
    if not jumps:
        sys.exit("no predictions in track JSON: run plan_jumps.py --write first")
    fl = flights(telemetry(replay))
    print(f"{len(fl)} flights in the replay, {len(jumps)} predicted jumps\n")
    for k, j in enumerate(jumps):
        p, land = j["predicted"], track["blocks"][j["before_block"]]
        dx, dz = HEADING[land["rotation"] & 3]
        # near edge of the landing strip, in world metres (cell corner + offset along travel)
        edge = (land["x"] * CELL + (CELL if dx < 0 else 0 if dx > 0 else CELL / 2),
                land["z"] * CELL + (CELL if dz < 0 else 0 if dz > 0 else CELL / 2))
        takeoff_edge = (edge[0] - dx * j["cells"] * CELL, edge[1] - dz * j["cells"] * CELL)
        near = [(math.hypot(a["x"] - takeoff_edge[0], a["z"] - takeoff_edge[1]), a, b) for a, b in fl]
        near = [n for n in near if n[0] < CELL]  # took off within one cell of the edge
        if not near:
            print(f"jump {k + 1}: no flight starts near the take-off edge {takeoff_edge}\n"); continue
        _, a, b = min(near, key=lambda n: n[0])
        speed = math.hypot(a["vx"], a["vz"]) * 3.6
        margin = (b["x"] - edge[0]) * dx + (b["z"] - edge[1]) * dz
        print(f"jump {k + 1}: take-off {speed:6.1f} km/h (predicted {p['takeoff_kmh']})")
        print(f"        lands {margin:+6.1f} m past the strip edge (predicted {p['landing_margin_m']:+.1f} m)"
              f"  → error {margin - p['landing_margin_m']:+.1f} m")
        print(f"        airtime {(b['t_ms'] - a['t_ms']) / 1000:.2f} s (predicted {p['air_s']})\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
