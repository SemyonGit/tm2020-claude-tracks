"""Validate jump.py constants: replay each clean airborne segment from its first
sample and compare predicted vs recorded end position. Usage: python validate.py <telemetry-dir>"""
import csv, glob, math, sys
import numpy as np
from fit_air import load, segments
from jump import GRAVITY, drag

def predict(p0, v0, car, dur, dt=0.001):
    x, y, z = p0; vx, vy, vz = v0; t = 0.0
    while t < dur:
        vh = math.hypot(vx, vz)
        if vh > 1e-6:
            nh = max(0.0, vh - drag(car, vh * 3.6) * dt); vx *= nh / vh; vz *= nh / vh
        vy -= GRAVITY[car] * dt
        x += vx * dt; y += vy * dt; z += vz * dt; t += dt
    return np.array([x, y, z])

tdir = sys.argv[1]
index = {r["file"]: r["vehicle"] for r in csv.DictReader(open(f"{tdir}/_index.csv"))}
errs = {}
for f in sorted(glob.glob(f"{tdir}/*.csv")):
    name = f.replace("\\", "/").rsplit("/", 1)[-1]
    car = index.get(name)
    if name == "_index.csv" or car not in GRAVITY:
        continue
    d = load(f)
    for s in segments(d):
        t = d["t_ms"][s] / 1000
        if len(t) < 6:
            continue
        vy = d["vy"][s]; p = np.polyfit(t, vy, 1)
        if 1 - ((vy - np.polyval(p, t))**2).sum() / max(((vy - vy.mean())**2).sum(), 1e-9) < 0.995:
            continue
        i0, i1 = s.start, s.stop - 1
        p0 = [d[k][i0] for k in ("x", "y", "z")]; v0 = [d[k][i0] for k in ("vx", "vy", "vz")]
        real = np.array([d[k][i1] for k in ("x", "y", "z")])
        pred = predict(p0, v0, car, t[-1] - t[0])
        travelled = np.linalg.norm(real - np.array(p0))
        errs.setdefault(car, []).append((np.linalg.norm(pred - real), abs(pred[1] - real[1]), travelled, t[-1] - t[0]))
for car, e in errs.items():
    e = np.array(e)
    rel = e[:, 0] / np.maximum(e[:, 2], 1)
    print(f"{car:10s} n={len(e):3d} flight {np.median(e[:,3]):.2f}s median | end error median {np.median(e[:,0]):.2f} m "
          f"(p90 {np.percentile(e[:,0],90):.2f}) | vertical {np.median(e[:,1]):.2f} m | relative {np.median(rel)*100:.1f}%")
