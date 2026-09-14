"""Check the supported single-cell path model, not driving physics or scenery."""
from __future__ import annotations

from .blocks import BLOCK_SPECS, advance
from .files import name_problem
from .schema import schema_errors

# Measured from converter/template.Map.Gbx, chunk 0x0304301F.
GRID_SIZE = (48, 40, 48)
Y_OFFSET = 8
START_ID = 'StadiumRoadMainStart'
FINISH_ID = 'StadiumRoadMainFinish'
CHECKPOINT_IDS = {'StadiumRoadMainCheckpointIn', 'Checkpoint'}


def validate(track: dict, *, allow_unverified: bool = False) -> list[str]:
    problems = schema_errors(track, 'track')
    if problems:
        return problems
    problem = name_problem(track['meta']['name'])
    if problem:
        problems.append(problem)
    settings = track['settings']
    if settings.get('environment', 'Stadium') != 'Stadium' or settings.get('mood', 'Day') != 'Day':
        problems.append('only Stadium / Day is supported by the bundled template')
    if settings.get('decoration', 'Stadium') not in ('Stadium', ''):
        problems.append('custom decoration is not implemented')
    blocks = track['blocks']
    if not blocks:
        return problems + ['no blocks']

    occupied: dict[tuple[int, int, int], int] = {}
    cursor = None
    heading = None
    for i, block in enumerate(blocks):
        cell = (block['x'], block['y'], block['z'])
        rotation = block['rotation']
        spec = BLOCK_SPECS.get(block['id'])
        if spec is None:
            problems.append(f'[{i}] {block["id"]}: no connector/footprint model')
            cursor = heading = None
            continue
        if not spec['verified'] and not allow_unverified:
            problems.append(f'[{i}] {block["id"]}: unverified; use --allow-unverified only for in-game calibration')
        if block.get('flags', 0) != 0:
            problems.append(f'[{i}] nonzero flags are not implemented')
        low_y = block['y'] - (spec['kind'] == 'slope_down')
        high_y = block['y'] + (spec['kind'] == 'slope_up')
        if not (0 <= block['x'] < GRID_SIZE[0] and 0 <= block['z'] < GRID_SIZE[2]
                and 1 <= low_y and high_y + Y_OFFSET < GRID_SIZE[1]):
            problems.append(f'[{i}] outside template grid {GRID_SIZE} (JSON ground y=1)')
        # Conservative vertical occupancy for the provisional slope model.
        for y in range(low_y, high_y + 1):
            occupied_cell = (cell[0], y, cell[2])
            if occupied_cell in occupied:
                problems.append(f'[{i}] overlap: cell {occupied_cell} already used by block {occupied[occupied_cell]}')
            occupied[occupied_cell] = i
        if cursor is not None and cell != cursor:
            problems.append(f'[{i}] gap: block at {cell} but path expected {cursor}')
        if heading is not None and rotation != heading:
            problems.append(f'[{i}] rotation {rotation} does not match incoming heading {heading}')
        _, cursor, heading = advance(spec['kind'], cell, rotation)

    ids = [b['id'] for b in blocks]
    if ids.count(START_ID) != 1 or ids[0] != START_ID:
        problems.append('must have exactly one Start block, at index 0')
    if ids.count(FINISH_ID) != 1 or ids[-1] != FINISH_ID:
        problems.append('must have exactly one Finish block, at the last index')
    expected = [i for i, block_id in enumerate(ids) if block_id in CHECKPOINT_IDS]
    checkpoints = track['checkpoints']
    if len(set(checkpoints)) != len(checkpoints):
        problems.append('duplicate checkpoint indices')
    if sorted(checkpoints) != expected:
        problems.append(f'checkpoint indices must match real checkpoint blocks: expected {expected}')
    for i, section in enumerate(track.get('sections', [])):
        if 'block_range' in section:
            first, last = section['block_range']
            if not 0 <= first <= last < len(blocks):
                problems.append(f'sections[{i}].block_range is outside the track or reversed')
    return problems
