"""Predict every declared jump in a composed track (track["jumps"]), toward issue #19.

For each gap: take-off speed = full-gas ground model over the run-up (from the start spawn,
or from the previous landing at landing speed); flight = air model (jump.py) with the
declared drop. Reports where the car lands relative to the start of the landing strip.
Assumptions (state them in the test plan): CarSport, tech road (Asphalt), straight run-ups
at full gas, flat take-off (0°), horizontal speed kept on landing.

Usage: python plan_jumps.py <track.json> [--write]   (--write stores predictions in the JSON)
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ground import speed_after, load_table  # noqa: E402
from jump import simulate, BLOCK_XZ, BLOCK_Y  # noqa: E402

SAFE_MARGIN_M = 8.0   # land at least this far past the strip edge, else flag as tight


def plan(track):
    blocks, jumps = track["blocks"], track.get("jumps", [])
    table = load_table()
    ref_index, ref_offset, v0 = 0, 0.5, 0.0  # spawn = centre of start cell, standing
    out = []
    for j in sorted(jumps, key=lambda j: j["before_block"]):
        take = j["before_block"] - 1
        # run-up: from reference point to the far edge of the take-off cell
        runup_m = ((take - ref_index) + 1 - ref_offset) * BLOCK_XZ
        curves = [b["id"] for b in blocks[ref_index:take + 1] if "Curve" in b["id"]]
        v_take, t_run, capped = speed_after(runup_m, "Asphalt", v0, "CarSport", table)
        flight = simulate(v_take, 0.0, j["drop"], "CarSport")
        margin = flight["distance_m"] - j["cells"] * BLOCK_XZ
        res = {
            "takeoff_block": take, "runup_m": round(runup_m, 1), "takeoff_kmh": round(v_take, 1),
            "air_s": round(flight["airtime_s"], 2), "distance_m": round(flight["distance_m"], 1),
            "distance_blocks": round(flight["distance_m"] / BLOCK_XZ, 2),
            "landing_margin_m": round(margin, 1), "landing_kmh": round(flight["landing_kmh"], 1),
            "verdict": "short" if margin < 0 else "tight" if margin < SAFE_MARGIN_M else "ok",
            "warnings": (["run-up has curves: full-gas assumption optimistic"] if curves else [])
                        + (["speed beyond reliable ground data"] if capped else []),
        }
        out.append((j, res))
        # next reference: landing point, horizontal speed kept
        ref_index = j["before_block"]
        ref_offset = margin / BLOCK_XZ
        v0 = flight["landing_h_kmh"]  # vertical speed is absorbed on landing
    return out


def main(path, write=False):
    track = json.loads(Path(path).read_text(encoding="utf-8"))
    results = plan(track)
    if not results:
        print("no declared jumps"); return
    print(f"{'jump':>4} {'run-up':>8} {'takeoff':>9} {'air':>6} {'flies':>8} {'gap':>5} {'margin':>8}  verdict")
    for j, r in results:
        print(f"{j['before_block']:>4} {r['runup_m']:>6.0f} m {r['takeoff_kmh']:>5.0f} km/h {r['air_s']:>4.2f}s "
              f"{r['distance_blocks']:>5.2f} bl {j['cells']:>3} bl {r['landing_margin_m']:>+6.1f} m  {r['verdict']}"
              + ("  ⚠ " + "; ".join(r["warnings"]) if r["warnings"] else ""))
        j["predicted"] = r
    if write:
        Path(path).write_text(json.dumps(track, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"predictions written → {path}")


if __name__ == "__main__":
    main(sys.argv[1], "--write" in sys.argv[2:])
