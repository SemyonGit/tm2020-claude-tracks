"""Shared loader: per-map grid block index from `ghost_probe map` CSVs."""
import csv, glob, os, pickle
from collections import defaultdict

DIRS = ("North", "East", "South", "West")


def load_corpus(bdir, cache=True):
    """Return list of maps; each map = (uid, blocks) with blocks = list of
    (name, gx, gy, gz, dir, variant). Grid blocks only. Pickled next to the CSVs."""
    pk = os.path.join(bdir, "_grid.pickle")
    if cache and os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    maps = []
    for f in sorted(glob.glob(os.path.join(bdir, "*.blocks.csv"))):
        rows = []
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["kind"] == "block" and r["dir"] in DIRS:
                rows.append((r["name"], int(r["gx"]), int(r["gy"]), int(r["gz"]), r["dir"], r["variant"]))
        maps.append((os.path.basename(f).split(".")[0], rows))
    if cache:
        pickle.dump(maps, open(pk, "wb"))
    return maps


def origin_index(rows):
    occ = defaultdict(list)
    for name, x, y, z, d, v in rows:
        occ[(x, y, z)].append(name)
    return occ
