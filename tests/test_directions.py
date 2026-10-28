"""Converter direction mapping vs geometry measured from real maps.

Measured facts (tm2020-mcp docs/tm2020-map-geometry.md + our Kacky corpus, 2026-10-28):
  RoadTechStart forward: North=+z, East=-x, South=-z, West=+x
  RoadTechCurve1 open sides: North={-x,+z} East={-x,-z} South={+x,-z} West={+x,+z}
JSON convention: heading 0=N travel -z, 1=E +x, 2=S +z, 3=W -x.
Run: python -m pytest tests  (or python tests/test_directions.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "converter"))
from build import tm2020_dir  # noqa: E402

TRAVEL = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}          # JSON heading → (dx, dz)
START_FORWARD = {"North": (0, 1), "East": (-1, 0), "South": (0, -1), "West": (1, 0)}
CURVE_OPEN = {"North": {(-1, 0), (0, 1)}, "East": {(-1, 0), (0, -1)},
              "South": {(1, 0), (0, -1)}, "West": {(1, 0), (0, 1)}}


def neg(v):
    return (-v[0], -v[1])


def test_start_and_finish_face_travel_direction():
    for rot in range(4):
        for block in ("StadiumRoadMainStart", "StadiumRoadMainFinish"):
            assert START_FORWARD[tm2020_dir(block, rot)] == TRAVEL[rot], (block, rot)


def test_curves_open_on_entry_and_exit_side():
    for rot in range(4):
        entry = neg(TRAVEL[rot])
        right_exit, left_exit = TRAVEL[(rot + 1) % 4], TRAVEL[(rot - 1) % 4]
        assert CURVE_OPEN[tm2020_dir("StadiumRoadMainCurve1Right", rot)] == {entry, right_exit}, rot
        assert CURVE_OPEN[tm2020_dir("StadiumRoadMainCurve1Left", rot)] == {entry, left_exit}, rot


if __name__ == "__main__":
    test_start_and_finish_face_travel_direction()
    test_curves_open_on_entry_and_exit_side()
    print("ok")
