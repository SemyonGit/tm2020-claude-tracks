"""Ballistic jump estimate for TM2020, from constants fitted by fit_air.py.

Not a simulator: no air control, no rotation, no collision. Answers "roughly where
does a car launched at speed X / angle Y land?" so designs start in the right range.
Final word is always an in-game test drive.

Usage: python jump.py <speed_kmh> [launch_deg=0] [drop_blocks=0] [car=CarSport]
  drop_blocks > 0: landing is lower than takeoff (in 8 m block heights)
"""
import sys

BLOCK_XZ = 32.0  # m per grid cell horizontally
BLOCK_Y = 8.0    # m per grid cell vertically

# Fitted 2026-10-28 (issues #9, #12): 3690 Kacky ghosts + 253 TMX replays, 6326 free flights
# (reactor + mid-air body collisions excluded), hold-out by map. CarSport hold-out error:
# median 0.66 m / p90 2.0 m (≤1.5 s flights), median 2.9 m / p90 10.1 m (>1.5 s).
GRAVITY = {"CarSport": 25.08, "CarSnow": 40.78, "CarRally": 40.83, "CarDesert": 40.90}
# Horizontal deceleration in air (m/s^2) at speed (km/h); linear interpolation.
DRAG = {
    "CarSport": [(50, 0.61), (150, 1.43), (250, 2.17), (350, 2.99), (475, 3.78), (675, 5.55)],
    "CarSnow": [(150, 0.28)], "CarRally": [(150, 0.14), (250, 0.18)], "CarDesert": [(150, 0.2)],
}


def drag(car, kmh):
    pts = DRAG[car]
    if kmh <= pts[0][0] or len(pts) == 1:
        return pts[0][1]
    for (a, da), (b, db) in zip(pts, pts[1:]):
        if kmh <= b:
            return da + (db - da) * (kmh - a) / (b - a)
    return pts[-1][1]


def simulate(kmh, deg=0.0, drop_blocks=0.0, car="CarSport", dt=0.001):
    import math
    v = kmh / 3.6
    vh, vy = v * math.cos(math.radians(deg)), v * math.sin(math.radians(deg))
    x = y = t = 0.0
    peak = 0.0
    target = -drop_blocks * BLOCK_Y
    while True:
        vh = max(0.0, vh - drag(car, vh * 3.6) * dt)
        vy -= GRAVITY[car] * dt
        x += vh * dt
        y += vy * dt
        t += dt
        peak = max(peak, y)
        if vy < 0 and y <= target:
            return {"airtime_s": t, "distance_m": x, "distance_blocks": x / BLOCK_XZ,
                    "peak_m": peak, "peak_blocks": peak / BLOCK_Y,
                    "landing_kmh": math.hypot(vh, vy) * 3.6, "landing_h_kmh": vh * 3.6}
        if t > 30:
            raise RuntimeError("no landing within 30 s")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    r = simulate(float(a[0]), float(a[1]) if len(a) > 1 else 0,
                 float(a[2]) if len(a) > 2 else 0, a[3] if len(a) > 3 else "CarSport")
    for k, v in r.items():
        print(f"{k:16s} {v:8.2f}")
