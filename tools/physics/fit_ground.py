"""Fit straight-line acceleration on the ground per surface (issue #11).

Sample filter: all 4 wheels on the same material, ground contact, full gas, no brake,
|steer| < 0.05, flat (|vy| < 1 m/s), normal sim speed, no reactor, no turbo-ish bits.
Acceleration a = d|v_h|/dt between consecutive samples, binned by speed.
Writes a per-(car, surface) acceleration table used by ground.py.
Usage: python fit_ground.py <out.json> <telemetry-dir> [<telemetry-dir> ...]
"""
import csv, json, sys
from collections import defaultdict
import numpy as np
from fit_air import load
from materials import material

BIN = 25  # km/h
MIN_N = 40


def car_of(v):
    return v or "CarSport"


def main(out, tdirs):
    acc = defaultdict(lambda: defaultdict(list))  # (car, surface) -> bin -> [a]
    for tdir in tdirs:
        for g in csv.DictReader(open(f"{tdir}/_index.csv")):
            d = load(f"{tdir}/{g['file']}")
            if d is None or "gmode" not in d:
                continue
            car = car_of(g.get("vehicle", ""))
            mats = np.stack([d["fl_mat"], d["fr_mat"], d["rl_mat"], d["rr_mat"]], 1).astype(int)
            same = (mats == mats[:, :1]).all(1)
            ok = (same & (d["ground"] == 1) & (d["gas"] >= 0.99) & (d["brake"] == 0)
                  & (np.abs(d["steer"]) < 0.05) & (np.abs(d["vy"]) < 1.0) & (d["sim_coef"] == 255)
                  & ((d["gmode"].astype(int) & 0x7C) == 0) & ((d["turbo"].astype(int) & 0x80) == 0))
            vh = np.hypot(d["vx"], d["vz"])
            t = d["t_ms"] / 1000
            for i in range(len(t) - 1):
                if ok[i] and ok[i + 1] and mats[i, 0] == mats[i + 1, 0] and 0 < t[i + 1] - t[i] < 0.1:
                    a = (vh[i + 1] - vh[i]) / (t[i + 1] - t[i])
                    kmh = (vh[i] + vh[i + 1]) / 2 * 3.6
                    acc[(car, material(mats[i, 0]))][int(kmh // BIN)].append(a)
    table = {}
    for (car, surf), bins in sorted(acc.items()):
        rows = [[b * BIN + BIN / 2, round(float(np.median(v)), 3), len(v)]
                for b, v in sorted(bins.items()) if len(v) >= MIN_N]
        if len(rows) >= 3:
            table[f"{car}|{surf}"] = rows
    json.dump({"bin_kmh": BIN, "min_n": MIN_N, "accel": table}, open(out, "w"), indent=1)
    for k, rows in table.items():
        n = sum(r[2] for r in rows)
        # top speed: first bin (above 100 km/h) where median accel <= 0.2 m/s^2
        top = next((r[0] for r in rows if r[0] > 100 and r[1] <= 0.2), None)
        a0 = rows[0][1]
        print(f"{k:28s} n={n:7d}  accel@{rows[0][0]:.0f}km/h {a0:5.2f} m/s²  "
              f"range {rows[0][0]:.0f}-{rows[-1][0]:.0f} km/h  top≈{top or '>' + str(int(rows[-1][0]))}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
