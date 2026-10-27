"""Fit TM2020 airborne physics from replay telemetry CSVs (tools/ghost_probe output).

Airborne segment = consecutive samples with ground==0, normal sim speed, no turbo.
Trims edge samples (contact/takeoff transients), differentiates velocity, then
least-squares fits  a = g_vec - k_lin*v - k_quad*|v|*v  per axis.
Usage: python fit_air.py <telemetry-dir>
"""
import csv, glob, sys
import numpy as np

TRIM = 2        # samples dropped at each end of a segment
MIN_LEN = 8     # min airborne samples (0.4 s) to use a segment


def load(path):
    rows = list(csv.DictReader(open(path)))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]} if rows else None


def segments(d):
    # turbo byte: GBX.NET masks 0x82, but 0x02 is set on ~80% of airborne samples, so only
    # 0x80 is treated as turbo (assumption, not verified).
    turbo = (d["turbo"].astype(int) & 0x80) != 0
    air = (d["ground"] == 0) & (d["sim_coef"] == 255) & ~turbo
    i, n = 0, len(air)
    while i < n:
        if air[i]:
            j = i
            while j < n and air[j]:
                j += 1
            if j - i >= MIN_LEN:
                yield slice(i + TRIM, j - TRIM)
            i = j
        else:
            i += 1


def main(tdir):
    V, A, files, nseg = [], [], 0, 0
    for f in sorted(glob.glob(f"{tdir}/*.csv")):
        if f.endswith("_index.csv"):
            continue
        d = load(f)
        if d is None:
            continue
        files += 1
        for s in segments(d):
            t = d["t_ms"][s] / 1000
            v = np.stack([d["vx"][s], d["vy"][s], d["vz"][s]], 1)
            if len(t) < 3 or np.any(np.diff(t) <= 0):
                continue
            a = np.diff(v, axis=0) / np.diff(t)[:, None]
            vm = (v[1:] + v[:-1]) / 2
            V.append(vm); A.append(a); nseg += 1
    V, A = np.concatenate(V), np.concatenate(A)
    # robust: drop samples with collisions (huge accel spikes)
    ok = np.linalg.norm(A, axis=1) < 80
    V, A = V[ok], A[ok]
    sp = np.linalg.norm(V, axis=1)
    print(f"files={files} segments={nseg} samples={len(V)} ({len(V)*0.05:.0f} s airborne)")
    print(f"speed range {sp.min()*3.6:.0f}-{sp.max()*3.6:.0f} km/h, median {np.median(sp)*3.6:.0f}")

    # model 1: constant gravity only
    print("\n[1] a = g (mean):", np.round(A.mean(0), 2), " median ay:", round(float(np.median(A[:, 1])), 2))
    # model 2: gravity + linear + quadratic drag (shared coefficients, all axes)
    X = np.zeros((len(V) * 3, 3 + 2)); y = A.reshape(-1)
    for ax in range(3):
        X[ax::3, ax] = 1                      # g component on this axis
        X[ax::3, 3] = -V[:, ax]               # linear drag
        X[ax::3, 4] = -sp * V[:, ax]          # quadratic drag
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    print("[2] g=", np.round(coef[:3], 3), " k_lin=", round(coef[3], 5), " k_quad=", round(coef[4], 6))
    print("    residual RMS", round(float(np.sqrt((res**2).mean())), 2), "m/s^2  vs raw RMS",
          round(float(np.sqrt(((y - y.mean())**2).mean())), 2))
    # speed-binned vertical accel + horizontal decel: shows whether drag is real
    print("\n speed bin km/h | n | mean ay | horiz decel (along v_h)")
    vh = V[:, [0, 2]]; ah = A[:, [0, 2]]; vhn = np.linalg.norm(vh, axis=1)
    along = np.where(vhn > 1, (ah * vh).sum(1) / np.maximum(vhn, 1e-6), np.nan)
    for lo in range(0, 1000, 100):
        m = (sp * 3.6 >= lo) & (sp * 3.6 < lo + 100)
        if m.sum() > 50:
            print(f"  {lo:4d}-{lo+100:<4d} | {m.sum():6d} | {A[m,1].mean():7.2f} | {np.nanmean(along[m]):7.2f}")



def per_segment(tdir, vehicle=None):
    """Robust gravity: slope of vy(t) per clean segment (R^2 > 0.995), then median."""
    index = {r["file"]: r.get("vehicle", "") for r in csv.DictReader(open(f"{tdir}/_index.csv"))}
    slopes, drags = [], []
    for f in sorted(glob.glob(f"{tdir}/*.csv")):
        name = f.replace("\\", "/").rsplit("/", 1)[-1]
        if name == "_index.csv" or (vehicle and index.get(name) != vehicle):
            continue
        d = load(f)
        if d is None:
            continue
        for s in segments(d):
            t = d["t_ms"][s] / 1000
            if len(t) < 6:
                continue
            vy = d["vy"][s]
            p = np.polyfit(t, vy, 1)
            r2 = 1 - ((vy - np.polyval(p, t))**2).sum() / max(((vy - vy.mean())**2).sum(), 1e-9)
            vh = np.hypot(d["vx"][s], d["vz"][s])
            if r2 > 0.995:
                slopes.append(p[0])
                drags.append((np.polyfit(t, vh, 1)[0], vh.mean()))
    slopes = np.array(slopes)
    print(f"\n=== vehicle: {vehicle or 'all'}")
    if len(slopes) < 5:
        print("    too few clean segments"); return
    h, e = np.histogram(slopes, bins=np.arange(-60, 0, 2))
    print("    histogram (m/s^2: count):", ", ".join(f"{e[i]:.0f}:{c}" for i, c in enumerate(h) if c >= 5))
    print(f"\n[3] clean segments: {len(slopes)}")
    print(f"    gravity median {np.median(slopes):.2f}  IQR {np.percentile(slopes,25):.2f}..{np.percentile(slopes,75):.2f} m/s^2")
    dr = np.array(drags)
    for lo, hi in [(0, 150), (150, 250), (250, 350), (350, 1000)]:
        m = (dr[:, 1] * 3.6 >= lo) & (dr[:, 1] * 3.6 < hi)
        if m.sum() >= 5:
            print(f"    horiz dv/dt @ {lo}-{hi} km/h: median {np.median(dr[m,0]):.2f} m/s^2 (n={m.sum()})")


if __name__ == "__main__":
    main(sys.argv[1])
    for v in ("CarSport", "CarSnow", "CarRally", "CarDesert"):
        per_segment(sys.argv[1], v)
