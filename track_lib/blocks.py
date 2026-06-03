"""Block metadata: how each segment occupies the grid and advances the path cursor.

Coordinate convention (matches tools/track_schema.json):
  rotation/heading 0=N 1=E 2=S 3=W ; travel vectors below ; +y = up.
Only blocks whose geometry is verified against a real TM2020 map live in
VERIFIED. Everything else is UNVERIFIED and must not be emitted silently.
"""
from __future__ import annotations

HEADING_VEC: dict[int, tuple[int, int, int]] = {
    0: (0, 0, -1),   # North
    1: (1, 0, 0),    # East
    2: (0, 0, 1),    # South
    3: (-1, 0, 0),   # West
}
HEADING_NAME = {0: "N", 1: "E", 2: "S", 3: "W"}

# Segment alias -> (json block id, kind, is_waypoint, verified)
SEGMENTS: dict[str, dict] = {
    "start":      {"id": "StadiumRoadMainStart",        "kind": "straight",   "waypoint": True,  "verified": True},
    "straight":   {"id": "StadiumRoadMainStraight",     "kind": "straight",   "waypoint": False, "verified": True},
    "checkpoint": {"id": "StadiumRoadMainCheckpointIn", "kind": "straight",   "waypoint": True,  "verified": True},
    "finish":     {"id": "StadiumRoadMainFinish",       "kind": "straight",   "waypoint": True,  "verified": True},
    "curve_right":{"id": "StadiumRoadMainCurve1Right",  "kind": "curve_right","waypoint": False, "verified": True},
    "curve_left": {"id": "StadiumRoadMainCurve1Left",   "kind": "curve_left", "waypoint": False, "verified": False},
    "slope_up":   {"id": "StadiumRoadMainSlope1Up",     "kind": "slope_up",   "waypoint": False, "verified": True},
    "slope_down": {"id": "StadiumRoadMainSlope1Down",   "kind": "slope_down", "waypoint": False, "verified": True},
}


def advance(kind: str, cursor: tuple[int, int, int], heading: int):
    """Return (emit_rotation, new_cursor, new_heading) for one segment cell."""
    x, y, z = cursor
    if kind == "straight":
        nh = heading
        dx, dy, dz = HEADING_VEC[heading]
        return heading, (x + dx, y + dy, z + dz), nh
    if kind == "curve_right":
        nh = (heading + 1) % 4
        dx, dy, dz = HEADING_VEC[nh]
        return heading, (x + dx, y + dy, z + dz), nh
    if kind == "curve_left":
        nh = (heading - 1) % 4
        dx, dy, dz = HEADING_VEC[nh]
        return heading, (x + dx, y + dy, z + dz), nh
    if kind == "slope_up":
        dx, dy, dz = HEADING_VEC[heading]
        return heading, (x + dx, y + 1 + dy, z + dz), heading
    if kind == "slope_down":
        dx, dy, dz = HEADING_VEC[heading]
        return heading, (x + dx, y - 1 + dy, z + dz), heading
    raise ValueError(f"unknown segment kind: {kind!r}")


def classify(json_id: str) -> str:
    """Infer the cursor-advance kind from a raw JSON block id (for the validator)."""
    if "Slope" in json_id and "Down" in json_id:
        return "slope_down"
    if "Slope" in json_id and "Up" in json_id:
        return "slope_up"
    if "Curve" in json_id and (json_id.endswith("Right") or json_id.endswith("In")):
        return "curve_right"
    if "Curve" in json_id and (json_id.endswith("Left") or json_id.endswith("Out")):
        return "curve_left"
    return "straight"
