"""Hold-out fit + validation of the air model (issue #9).

Splits by MAP (80/20, deterministic hash), fits gravity + horizontal drag per car on the
train maps, then replays every clean test flight through the model and reports the
end-position error for short and long flights separately.
Usage: python holdout.py <telemetry-dir> [<telemetry-dir> ...]
"""
import csv, glob, hashlib, math, sys
from collections import defaultdict
import numpy as np
from fit_air import load, segments

R2_MIN = 0.995
SPIKE = 60.0  # m/s^2 deviation from the flight's median accel = body collision (wheels in air)
SPEED_BINS = [0, 100, 200, 300, 400, 550, 800]


def car_of(v):
    return v or "CarSport"  # pre-2023 ghosts have no model id: only CarSport existed


def clean_segments(tdirs):
    """Yield (map_uid, car, t, pos, vel) for each airborne segment with a clean vy(t) line."""
    for tdir in tdirs:
        for g in csv.DictReader(open(f"{tdir}/_index.csv")):
            d = load(f"{tdir}/{g['file']}")
            if d is None:
                continue
            for s in segments(d):
                t = d["t_ms"][s] / 1000
                if len(t) < 6 or np.any(np.diff(t) <= 0):
                    continue
                vy = d["vy"][s]
                p = np.polyfit(t, vy, 1)
                if 1 - ((vy - np.polyval(p, t))**2).sum() / max(((vy - vy.mean())**2).sum(), 1e-9) < R2_MIN:
                    continue
                pos = np.stack([d["x"][s], d["y"][s], d["z"][s]], 1)
                vel = np.stack([d["vx"][s], d["vy"][s], d["vz"][s]], 1)
                a = np.diff(vel, axis=0) / np.diff(t)[:, None]
                if np.linalg.norm(a - np.median(a, axis=0), axis=1).max() > SPIKE:
                    continue  # hit something mid-air: not a free flight
                yield g["map_uid"], car_of(g.get("vehicle", "")), t, pos, vel, p[0]


def is_test(map_uid):
    return int(hashlib.md5(map_uid.encode()).hexdigest(), 16) % 5 == 0


def fit(segs):
    """Per car: median vy slope = gravity; median horizontal dv/dt per speed bin = drag."""
    g, drag = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for _, car, t, pos, vel, slope in segs:
        g[car].append(-slope)
        vh = np.hypot(vel[:, 0], vel[:, 2])
        k = np.polyfit(t, vh, 1)[0]
        b = np.searchsorted(SPEED_BINS, vh.mean() * 3.6) - 1
        drag[car][b].append(-k)
    model = {}
    for car in g:
        pts = [((SPEED_BINS[b] + SPEED_BINS[b + 1]) / 2, float(np.median(v)), len(v))
               for b, v in sorted(drag[car].items()) if len(v) >= 10 and b + 1 < len(SPEED_BINS)]
        model[car] = {"g": float(np.median(g[car])), "n": len(g[car]), "drag": pts}
    return model


def drag_at(pts, kmh):
    if not pts:
        return 0.0
    if kmh <= pts[0][0]:
        return pts[0][1]
    for (a, da, _), (b, db, _) in zip(pts, pts[1:]):
        if kmh <= b:
            return da + (db - da) * (kmh - a) / (b - a)
    return pts[-1][1]


def predict(m, p0, v0, dur, dt=0.002):
    x, y, z = p0; vx, vy, vz = v0; t = 0.0
    while t < dur:
        vh = math.hypot(vx, vz)
        if vh > 1e-6:
            nh = max(0.0, vh - drag_at(m["drag"], vh * 3.6) * dt); vx *= nh / vh; vz *= nh / vh
        vy -= m["g"] * dt
        x += vx * dt; y += vy * dt; z += vz * dt; t += dt
    return np.array([x, y, z])


def main(tdirs):
    segs = list(clean_segments(tdirs))
    train = [s for s in segs if not is_test(s[0])]
    test = [s for s in segs if is_test(s[0])]
    print(f"clean flights: {len(segs)}  train {len(train)}  test {len(test)} "
          f"(maps: {len({s[0] for s in train})} / {len({s[0] for s in test})})")
    model = fit(train)
    for car, m in sorted(model.items(), key=lambda kv: -kv[1]["n"]):
        print(f"\n{car}: g = {m['g']:.2f} m/s^2 (n={m['n']})")
        print("  drag (km/h → m/s^2): " + ", ".join(f"{c:.0f}→{d:.2f} (n={n})" for c, d, n in m["drag"]))
    print("\nHold-out error (end position after the flight):")
    rows = defaultdict(list)
    for _, car, t, pos, vel, _ in test:
        if car not in model:
            continue
        dur = t[-1] - t[0]
        err = np.linalg.norm(predict(model[car], pos[0], vel[0], dur) - pos[-1])
        dist = np.linalg.norm(pos[-1] - pos[0])
        rows[(car, "long >1.5s" if dur > 1.5 else "short ≤1.5s")].append((err, err / max(dist, 1), dur))
    for (car, kind), e in sorted(rows.items()):
        e = np.array(e)
        print(f"  {car:10s} {kind:12s} n={len(e):5d}  median {np.median(e[:,0]):5.2f} m  "
              f"p90 {np.percentile(e[:,0],90):6.2f} m  relative {np.median(e[:,1])*100:4.1f}%  "
              f"flight {np.median(e[:,2]):.2f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
