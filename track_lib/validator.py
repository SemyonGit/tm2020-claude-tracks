"""Validate a schema track dict by re-walking its geometry.

Catches the failure class that hand-authored coordinates fall into:
gaps (block N+1 not at block N's exit), overlaps (two blocks share a cell),
and bad waypoint structure (missing start/finish, dangling checkpoint indices).
Does NOT check the BLOCK_MAP — that lie is the converter's fail-loud job.
"""
from __future__ import annotations
from .blocks import HEADING_VEC, advance, classify


def validate(track: dict) -> list[str]:
    problems: list[str] = []
    blocks = track.get("blocks", [])
    if not blocks:
        return ["no blocks"]

    occupied: dict[tuple[int, int, int], int] = {}
    cursor = (blocks[0]["x"], blocks[0]["y"], blocks[0]["z"])
    heading = blocks[0].get("rotation", 0) & 3

    for i, b in enumerate(blocks):
        cell = (b["x"], b["y"], b["z"])
        if cell in occupied:
            problems.append(f"[{i}] overlap: cell {cell} already used by block {occupied[cell]}")
        occupied[cell] = i
        if cell != cursor:
            problems.append(f"[{i}] gap: block at {cell} but path expected {cursor}")
            cursor = cell  # resync so we report one gap, not a cascade
        kind = classify(b["id"])
        _, cursor, heading = advance(kind, cursor, heading)

    ids = [b["id"] for b in blocks]
    if sum("Start" in x for x in ids) != 1:
        problems.append("must have exactly one Start block")
    if sum("Finish" in x for x in ids) != 1:
        problems.append("must have exactly one Finish block")
    for c in track.get("checkpoints", []):
        if not (0 <= c < len(blocks)):
            problems.append(f"checkpoint index {c} out of range")
    return problems
