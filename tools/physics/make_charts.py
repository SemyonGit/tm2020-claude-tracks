"""README charts from the physics data (light + dark PNG variants for GitHub <picture>).

Usage: python make_charts.py <out-dir> <kacky-telemetry> <tmx-telemetry>
Reads ground_table.json and docs/jump_table.csv from the repo.
"""
import csv, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from holdout import clean_segments, fit, predict, is_test

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
THEMES = {
    "light": {"bg": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e3df",
              "s": ["#2a78d6", "#eb6834", "#1baf7a"]},
    "dark": {"bg": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "grid": "#33332f",
             "s": ["#3987e5", "#d95926", "#199e70"]},
}


def style(ax, t, title, xlabel, ylabel):
    fig = ax.figure
    fig.patch.set_facecolor(t["bg"]); ax.set_facecolor(t["bg"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["grid"])
    ax.tick_params(colors=t["ink2"], labelsize=9, length=0)
    ax.grid(True, color=t["grid"], linewidth=0.8); ax.set_axisbelow(True)
    ax.set_title(title, color=t["ink"], fontsize=12, loc="left", pad=12, fontweight="bold")
    ax.set_xlabel(xlabel, color=t["ink2"], fontsize=9); ax.set_ylabel(ylabel, color=t["ink2"], fontsize=9)


def save(fig, out, name, mode):
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"{name}-{mode}.png"), dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def main(out, tk, tt):
    os.makedirs(out, exist_ok=True)
    segs = list(clean_segments([tk, tt]))
    g_sport = [-s[5] for s in segs if s[1] == "CarSport"]
    g_other = [-s[5] for s in segs if s[1] != "CarSport"]
    model = fit([s for s in segs if not is_test(s[0])])
    test = [s for s in segs if is_test(s[0]) and s[1] == "CarSport"]
    pred_d, real_d = [], []
    for _, car, t, pos, vel, _ in test:
        p = predict(model[car], pos[0], vel[0], t[-1] - t[0])
        pred_d.append(np.hypot(*(p - pos[0])[[0, 2]])); real_d.append(np.hypot(*(pos[-1] - pos[0])[[0, 2]]))
    import json
    gt = json.load(open(os.path.join(HERE, "ground_table.json")))["accel"]["CarSport|Asphalt"]
    gt = [(v, a) for v, a, n in gt if n >= 100 and v < 620]
    jt = list(csv.DictReader(open(os.path.join(ROOT, "docs", "jump_table.csv"))))[:12]

    for mode, t in THEMES.items():
        # 1. two gravities
        fig, ax = plt.subplots(figsize=(7, 3.6))
        bins = np.arange(15, 50, 0.5)
        ax.hist(g_sport, bins=bins, color=t["s"][0], rwidth=0.85, label="CarSport")
        ax.hist(g_other, bins=bins, color=t["s"][1], rwidth=0.85, label="Snow / Rally / Desert")
        med_s, med_o = np.median(g_sport), np.median(g_other)
        ax.annotate(f"Stadium car\n{med_s:.1f} m/s²", (med_s, ax.get_ylim()[1] * 0.85), color=t["ink"],
                    fontsize=9, ha="left", xytext=(8, 0), textcoords="offset points")
        ax.annotate(f"Snow / Rally / Desert\n{med_o:.1f} m/s²", (med_o, ax.get_ylim()[1] * 0.25),
                    color=t["ink"], fontsize=9, ha="center", xytext=(0, 18), textcoords="offset points")
        ax.legend(frameon=False, labelcolor=t["ink2"], fontsize=8, loc="upper right")
        style(ax, t, f"Gravity measured from {len(g_sport) + len(g_other):,} free flights",
              "downward acceleration (m/s²)", "flights")
        save(fig, out, "gravity", mode)

        # 2. gear steps
        fig, ax = plt.subplots(figsize=(7, 3.4))
        v, a = zip(*gt)
        ax.step(v, a, where="mid", color=t["s"][0], linewidth=2)
        for x, y, lab in [(55, 15.8, "1st"), (150, 10.6, "2nd"), (300, 7.0, "3rd"), (470, 5.2, "4th+")]:
            ax.annotate(lab, (x, y), color=t["ink"], fontsize=9, xytext=(0, 7), textcoords="offset points", ha="center")
        ax.set_ylim(0, 18)
        style(ax, t, "Full-gas acceleration on tech road: the gearbox is visible",
              "speed (km/h)", "acceleration (m/s²)")
        save(fig, out, "gears", mode)

        # 3. prediction vs reality
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        lim = np.percentile(real_d, 99)
        ax.plot([0, lim], [0, lim], color=t["ink2"], linewidth=1, linestyle="--")
        ax.scatter(real_d, pred_d, s=9, color=t["s"][0], alpha=0.45, linewidths=0)
        ax.set_xlim(0, lim); ax.set_ylim(0, lim)
        ax.annotate("perfect prediction", (lim * 0.62, lim * 0.62), color=t["ink2"], fontsize=8,
                    rotation=40, xytext=(-6, 8), textcoords="offset points")
        style(ax, t, f"Jump distance: model vs replay\n({len(real_d):,} flights from maps the model never saw)",
              "real horizontal distance (m)", "predicted (m)")
        save(fig, out, "jump_accuracy", mode)

        # 4. Kacky takeoff blocks
        fig, ax = plt.subplots(figsize=(7, 4.2))
        names = [r["takeoff"] for r in jt][::-1]
        maps = [int(r["maps"]) for r in jt][::-1]
        ax.barh(names, maps, color=t["s"][0], height=0.7)
        for i, m in enumerate(maps):
            ax.annotate(str(m), (m, i), color=t["ink2"], fontsize=8, xytext=(4, -3), textcoords="offset points")
        ax.tick_params(axis="y", labelsize=8, labelcolor=t["ink"])
        ax.grid(axis="y", visible=False)
        style(ax, t, "Where Kacky world records take off", "number of official Kacky maps", "")
        save(fig, out, "kacky_takeoffs", mode)
    print("charts →", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
