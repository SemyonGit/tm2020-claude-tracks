"""Compose a connected track from a high-level path. No raw coordinates by hand.

Design input (small, human/LLM-authored):
{
  "meta": {...}, "settings": {...},
  "origin": {"x": 10, "y": 1, "z": 20, "heading": 1},   # optional
  "path": [
    {"seg": "start"},
    {"seg": "straight", "count": 4},
    {"seg": "curve_right"},
    {"seg": "checkpoint"},
    {"seg": "finish"}
  ]
}
Output: a tools/track_schema.json-compliant track dict (absolute blocks + checkpoints),
guaranteed connected because every cell is placed at the previous cell's exit.
"""
from __future__ import annotations
import datetime as _dt
from .blocks import SEGMENTS, advance

DEFAULT_ORIGIN = {"x": 16, "y": 1, "z": 20, "heading": 1}


def compose(design: dict) -> dict:
    origin = {**DEFAULT_ORIGIN, **design.get("origin", {})}
    cursor = (origin["x"], origin["y"], origin["z"])
    heading = origin["heading"] & 3

    blocks: list[dict] = []
    checkpoints: list[int] = []
    warnings: list[str] = []

    for step in design["path"]:
        seg = step["seg"]
        if seg not in SEGMENTS:
            raise ValueError(f"unknown segment {seg!r}. Known: {sorted(SEGMENTS)}")
        spec = SEGMENTS[seg]
        if not spec["verified"]:
            warnings.append(f"segment {seg!r} is UNVERIFIED — test in-game before trusting")
        for _ in range(step.get("count", 1)):
            emit_rot, new_cursor, new_heading = advance(spec["kind"], cursor, heading)
            blocks.append({
                "id": spec["id"],
                "x": cursor[0], "y": cursor[1], "z": cursor[2],
                "rotation": emit_rot, "flags": 0,
            })
            if spec["waypoint"] and seg == "checkpoint":
                checkpoints.append(len(blocks) - 1)
            cursor, heading = new_cursor, new_heading

    meta = {
        "name": "Untitled", "author": "SemyonGit", "category": "speedtech",
        "difficulty": 3, "creativity": 3, "generated_by": "Claude (Anthropic)",
        "generated_at": _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        **design.get("meta", {}),
    }
    return {
        "meta": meta,
        "settings": design.get("settings", {"environment": "Stadium", "mood": "Day"}),
        "blocks": blocks,
        "checkpoints": checkpoints,
        "sections": design.get("sections", []),
        "_warnings": warnings,
    }
