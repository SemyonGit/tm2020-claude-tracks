"""Speed after N blocks of full-gas straight driving, per surface (issue #11).

Uses the acceleration table from fit_ground.py (ground_table.json). Only speed bins with
≥ RELIABLE_N samples are used; above the last reliable bin the prediction is capped and
flagged. Flat ground only: slopes, boosters and steering are not modelled.

Usage:
  python ground.py <blocks> [surface=Asphalt] [v0_kmh=0] [car=CarSport]
  python ground.py --validate <telemetry-dir> [...]   # hold-out check on recorded runs
"""
import json, os, sys

TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ground_table.json")
BLOCK_XZ = 32.0
RELIABLE_N = 100


def load_table(path=TABLE):
    acc = json.load(open(path))["accel"]
    return {k: [(v, a) for v, a, n in rows if n >= RELIABLE_N] for k, rows in acc.items()}


def accel_at(rows, kmh):
    if kmh <= rows[0][0]:
        return rows[0][1]
    for (v0, a0), (v1, a1) in zip(rows, rows[1:]):
        if kmh <= v1:
            return a0 + (a1 - a0) * (kmh - v0) / (v1 - v0)
    return None  # beyond reliable data


def speed_after(dist_m, surface="Asphalt", v0_kmh=0.0, car="CarSport", table=None, dt=0.005):
    """Return (speed_kmh, seconds, capped) after driving dist_m at full gas."""
    rows = (table or load_table())[f"{car}|{surface}"]
    v, x, t, capped = v0_kmh / 3.6, 0.0, 0.0, False
    while x < dist_m:
        a = accel_at(rows, v * 3.6)
        if a is None:
            capped = True
            break
        v += a * dt
        x += v * dt
        t += dt
        if t > 120:
            break
    return v * 3.6, t, capped


def validate(tdirs):
    """Replay recorded full-gas straight runs (≥1 s) through the model; report end-speed error."""
    import csv
    import numpy as np
    from fit_air import load
    from materials import material
    table, errs = load_table(), {}
    for tdir in tdirs:
        for g in csv.DictReader(open(f"{tdir}/_index.csv")):
            d = load(f"{tdir}/{g['file']}")
            if d is None or "gmode" not in d:
                continue
            car = g.get("vehicle") or "CarSport"
            m = d["fl_mat"].astype(int)
            same = (m == d["fr_mat"]) & (m == d["rl_mat"]) & (m == d["rr_mat"])
            ok = (same & (d["ground"] == 1) & (d["gas"] >= 0.99) & (d["brake"] == 0)
                  & (np.abs(d["steer"]) < 0.05) & (np.abs(d["vy"]) < 1.0) & (d["sim_coef"] == 255)
                  & ((d["gmode"].astype(int) & 0x7C) == 0) & ((d["turbo"].astype(int) & 0x80) == 0))
            i, n = 0, len(ok)
            while i < n:
                if not ok[i]:
                    i += 1; continue
                j = i
                while j + 1 < n and ok[j + 1] and m[j + 1] == m[i]:
                    j += 1
                if d["t_ms"][j] - d["t_ms"][i] >= 1000:
                    key = f"{car}|{material(m[i])}"
                    if key in table and table[key]:
                        v0 = np.hypot(d["vx"][i], d["vz"][i]) * 3.6
                        v1 = np.hypot(d["vx"][j], d["vz"][j]) * 3.6
                        dist = np.sum(np.hypot(np.diff(d["x"][i:j + 1]), np.diff(d["z"][i:j + 1])))
                        pred, _, capped = speed_after(dist, material(m[i]), v0, car, table)
                        if not capped:
                            errs.setdefault(key, []).append((pred - v1, v1 - v0))
                i = j + 1
    for key, e in sorted(errs.items(), key=lambda kv: -len(kv[1])):
        e = np.array(e)
        if len(e) >= 10:
            print(f"{key:24s} n={len(e):5d}  end-speed error median {np.median(e[:,0]):+6.1f} km/h  "
                  f"|err| p50 {np.median(np.abs(e[:,0])):5.1f}  p90 {np.percentile(np.abs(e[:,0]),90):5.1f}  "
                  f"(median gain {np.median(e[:,1]):5.1f} km/h)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "--validate":
        validate(a[1:])
    else:
        v, t, capped = speed_after(float(a[0]) * BLOCK_XZ, a[1] if len(a) > 1 else "Asphalt",
                                   float(a[2]) if len(a) > 2 else 0.0, a[3] if len(a) > 3 else "CarSport")
        print(f"speed {v:6.1f} km/h after {float(a[0]):g} blocks, {t:.2f} s"
              + ("  (capped: beyond reliable data)" if capped else ""))
