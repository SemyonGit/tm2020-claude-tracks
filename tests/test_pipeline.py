import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from converter import build as converter
from track_lib.composer import compose
from track_lib.validator import validate


@pytest.fixture
def proofcut():
    return json.loads((ROOT / 'tracks/speedtech/proofcut/proofcut.json').read_text())


def run_cli(*args, cwd=ROOT):
    return subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True)


def write_json(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')
    return path


@pytest.mark.parametrize('path', sorted((ROOT / 'tracks').rglob('*.design.json')))
def test_committed_designs_match_coordinates(path):
    design = json.loads(path.read_text())
    slope = path.name.startswith('slope_')
    track = compose(design, allow_unverified=slope)
    track.pop('_warnings', None)
    assert track == json.loads(path.with_name(path.name.replace('.design.json', '.json')).read_text())


def test_wrong_rotation_does_not_pass(proofcut):
    proofcut['blocks'][5]['rotation'] = 3
    assert any('[5] rotation' in p for p in validate(proofcut))


@pytest.mark.parametrize('edit,expected', [
    (lambda t: t['blocks'][2].update(x=40), 'gap'),
    (lambda t: t['blocks'][2].update(x=16, z=20), 'overlap'),
    (lambda t: t['blocks'][1].update(rotation=8), 'rotation'),
    (lambda t: t['blocks'][1].update(x=48), 'outside template'),
    (lambda t: t['blocks'][1].update(y=32), 'outside template'),
    (lambda t: t['blocks'][1].update(flags=1), 'flags'),
    (lambda t: t['blocks'][1].update(id='StadiumRoadMainCurve2'), 'no connector'),
    (lambda t: t['blocks'][1].update(id='StadiumRoadMainSlope2Up'), 'no connector'),
    (lambda t: t['blocks'][0].update(id='StadiumRoadMainStraight'), 'Start'),
    (lambda t: t['blocks'][-1].update(id='StadiumRoadMainStraight'), 'Finish'),
    (lambda t: t.update(checkpoints=[1]), 'checkpoint indices'),
    (lambda t: t.update(checkpoints=[8, 8, 18]), 'duplicate checkpoint'),
    (lambda t: t.update(checkpoints=[999]), 'checkpoint indices'),
    (lambda t: t['meta'].update(generated_at='tomorrow'), 'date-time'),
    (lambda t: t['settings'].update(mood='Night'), 'Stadium / Day'),
    (lambda t: t['settings'].update(environment='Rally'), 'Stadium / Day'),
    (lambda t: t.update(sections=[{'block_range': [0, 100]}]), 'block_range'),
])
def test_invalid_tracks_are_rejected(proofcut, edit, expected):
    edit(proofcut)
    assert any(expected in p for p in validate(proofcut))


@pytest.mark.parametrize('name', ['../escape', 'bad/name', 'bad\\name', 'C:escape', 'CON', 'name.', ' name', ''])
def test_bad_output_names(proofcut, name):
    proofcut['meta']['name'] = name
    assert any('name' in p for p in validate(proofcut))


@pytest.mark.parametrize('value', [None, [], {}, {'blocks': []}])
def test_bad_track_structure_reports_errors(value):
    assert validate(value)


@pytest.mark.parametrize('edit', [
    lambda d: d['path'][1].update(count=0),
    lambda d: d['path'][1].update(count=-1),
    lambda d: d['path'][1].update(count=True),
    lambda d: d['path'][1].update(count=1.5),
    lambda d: d['path'][1].update(count=5000),
    lambda d: d['path'][1].update(seg='typo'),
    lambda d: d.update(origin={'heading': 5}),
    lambda d: d.update(origin={'x': '16'}),
    lambda d: d.update(path=[]),
])
def test_invalid_designs_fail_before_expansion(edit):
    design = {'meta': {'name': 'Fixture'}, 'path': [{'seg': 'start'}, {'seg': 'straight'}, {'seg': 'finish'}]}
    edit(design)
    with pytest.raises(ValueError):
        compose(design)


def test_start_and_finish_must_be_endpoints(proofcut):
    proofcut['blocks'][0]['id'], proofcut['blocks'][1]['id'] = proofcut['blocks'][1]['id'], proofcut['blocks'][0]['id']
    assert any('index 0' in p for p in validate(proofcut))
    proofcut['blocks'][-1]['id'], proofcut['blocks'][-2]['id'] = proofcut['blocks'][-2]['id'], proofcut['blocks'][-1]['id']
    assert any('last index' in p for p in validate(proofcut))


@pytest.mark.parametrize('heading', range(4))
def test_waypoint_and_curve_orientation_tables(heading):
    # Explicit expectations from the recorded June orientation fixes; not
    # generated from the implementation tables under test.
    assert converter.tm2020_dir('StadiumRoadMainStart', heading) == ['North', 'West', 'South', 'East'][heading]
    assert converter.tm2020_dir('StadiumRoadMainFinish', heading) == ['North', 'West', 'South', 'East'][heading]
    assert converter.tm2020_dir('StadiumRoadMainCheckpointIn', heading) == ['South', 'East', 'North', 'West'][heading]
    assert converter.tm2020_dir('StadiumRoadMainCurve1Right', heading) == ['West', 'North', 'East', 'South'][heading]
    assert converter.tm2020_dir('StadiumRoadMainCurve1Left', heading) == ['North', 'East', 'South', 'West'][heading]


@pytest.mark.parametrize('direction', 'nesw')
def test_slopes_need_opt_in_and_preserve_provisional_offsets(tmp_path, direction):
    source = ROOT / f'tracks/_validation/slope_{direction}/slope_{direction}.design.json'
    design = json.loads(source.read_text())
    with pytest.raises(ValueError, match='unverified'):
        compose(design)
    track = compose(design, allow_unverified=True)
    assert any('unverified' in p for p in validate(track))
    assert validate(track, allow_unverified=True) == []
    path = write_json(tmp_path / 'slope.json', track)
    with pytest.raises(ValueError, match='unverified'):
        converter.build(path, deploy=False)
    output = converter.build(path, deploy=False, allow_unverified=True)
    data = converter.parse_file(str(output), recursive=False)
    try:
        blocks = converter.find_blocks_chunk(data).Blocks
        assert blocks[3].coords.y == 9
        assert blocks[4].coords.y == 10
        assert blocks[7].coords.y == 9
        assert str(blocks[7].dir) == {'n': 'North', 'e': 'West', 's': 'South', 'w': 'East'}[direction]
        assert blocks[7].flags.isGround
    finally:
        converter.close_map(data)


def test_negative_slope_ground_is_rejected():
    design = {'meta': {'name': 'Underground'}, 'origin': {'y': 1}, 'path': [{'seg': 'start'}, {'seg': 'slope_down'}, {'seg': 'finish'}]}
    with pytest.raises(ValueError, match='outside template'):
        compose(design, allow_unverified=True)


def test_force_cannot_bypass_errors(tmp_path, proofcut):
    path = write_json(tmp_path / 'bad.json', proofcut)
    with pytest.raises(ValueError, match='no longer bypasses'):
        converter.build(path, deploy=False, force=True)
    assert not list(tmp_path.glob('*.Gbx'))


def test_unknown_geometry_stays_blocked_with_opt_in(proofcut):
    proofcut['blocks'][1]['id'] = 'StadiumRoadMainChicaneX2Right'
    assert any('no connector' in p for p in validate(proofcut, allow_unverified=True))


def test_gbx_metadata_and_blocks_round_trip(tmp_path, proofcut):
    proofcut['meta']['name'] = 'Proof & Test'
    path = write_json(tmp_path / 'track.json', proofcut)
    output = converter.build(path, deploy=False)
    data = converter.parse_file(str(output), recursive=False)
    template = converter.parse_file(str(converter.TEMPLATE), recursive=False)
    try:
        chunk = converter.find_blocks_chunk(data)
        header = converter.header_chunk(data, 0x03043003)
        assert not data._errors
        assert len(chunk.Blocks) == 24
        assert sum(b.flags.isWaypoint for b in chunk.Blocks) == 4
        assert chunk.mapName == header.mapName == 'Proof & Test'
        assert chunk.mapInfo.id == header.mapInfo.id == converter.track_uid(proofcut)
        assert chunk.mapInfo.id != converter.find_blocks_chunk(template).mapInfo.id
        assert chunk.mapInfo.author == converter.find_blocks_chunk(template).mapInfo.author
        ident = ET.fromstring(converter.header_chunk(data, 0x03043005).xml).find('ident')
        assert ident.get('name') == chunk.mapName
        assert ident.get('uid') == chunk.mapInfo.id
        assert data.body[0x03043029].crc32 == zlib.crc32(('0x' + '0' * 32 + '???' + chunk.mapInfo.id).encode())
        assert not set(converter.BLOCK_DEPENDENT_CHUNKS) & set(data.body)
    finally:
        converter.close_map(data)
        converter.close_map(template)
    raw = output.read_bytes()
    converter.build(path, deploy=False)
    assert output.read_bytes() == raw


def test_uid_ignores_timestamp_but_changes_with_layout(proofcut):
    uid = converter.track_uid(proofcut)
    proofcut['meta']['generated_at'] = '2026-09-14T12:00:00Z'
    assert converter.track_uid(proofcut) == uid
    proofcut['blocks'][2]['x'] += 1
    assert converter.track_uid(proofcut) != uid


def test_checkpoint_alias_is_a_real_gate(tmp_path, proofcut):
    proofcut['blocks'][8]['id'] = 'Checkpoint'
    path = write_json(tmp_path / 'alias.json', proofcut)
    output = converter.build(path, deploy=False)
    data = converter.parse_file(str(output), recursive=False)
    try:
        assert converter.find_blocks_chunk(data).Blocks[8].name == 'RoadTechCheckpoint'
    finally:
        converter.close_map(data)


def test_batch_skips_designs_and_returns_failure(tmp_path, proofcut):
    write_json(tmp_path / 'good.json', proofcut)
    write_json(tmp_path / 'ignored.design.json', {'not': 'a low-level track'})
    write_json(tmp_path / 'bad.json', {})
    result = run_cli('converter/build.py', tmp_path, '--batch', '--no-deploy', '--dry-run')
    assert result.returncode == 1
    assert '1 ok, 1 failed' in result.stdout
    assert not list(tmp_path.glob('*.Gbx'))
    (tmp_path / 'bad.json').unlink()
    result = run_cli('converter/build.py', tmp_path, '--batch', '--no-deploy', '--dry-run')
    assert result.returncode == 0
    assert '1 ok, 0 failed' in result.stdout


def test_duplicate_batch_output_names_fail(tmp_path, proofcut):
    write_json(tmp_path / 'one.json', proofcut)
    write_json(tmp_path / 'two.json', proofcut)
    result = run_cli('converter/build.py', tmp_path, '--batch', '--no-deploy')
    assert result.returncode == 1
    assert 'duplicate output map name' in result.stderr


def test_compose_does_not_overwrite_source(tmp_path):
    path = write_json(tmp_path / 'test.design.json', {'meta': {'name': 'Fixture'}, 'path': [{'seg': 'start'}, {'seg': 'finish'}]})
    before = path.read_bytes()
    result = run_cli('compose.py', path, path)
    assert result.returncode == 1
    assert path.read_bytes() == before


def test_missing_maps_dir_does_not_create_a_build(tmp_path, proofcut):
    path = write_json(tmp_path / 'track.json', proofcut)
    with pytest.raises(ValueError, match='maps directory'):
        converter.build(path, maps_dir=tmp_path / 'missing')
    assert not list(tmp_path.glob('*.Gbx'))


def test_legacy_tracks_remain_rejected():
    for name in ('silvercut', 'razorline'):
        track = json.loads((ROOT / f'tracks/speedtech/{name}/{name}.json').read_text())
        assert validate(track)


def test_embedded_zip_buffers_are_per_map():
    from construct import Bytes
    from gbxpy.gbx_structs import ACompressedZip
    def payload(name):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr(name, name)
        return buffer.getvalue()
    first, second = payload('first.txt'), payload('second.txt')
    adapter = ACompressedZip(Bytes(len(first)))
    map_a = adapter._decode(first, None, '')
    map_b = adapter._decode(second, None, '')
    try:
        assert adapter._encode(map_a, None, '') == first
        assert adapter._encode(map_b, None, '') == second
    finally:
        map_a.close()
        map_b.close()


def test_catalog_check_works_outside_repo(tmp_path):
    result = run_cli(ROOT / 'catalog/fetch_blocks.py', '--check', cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert '191' in result.stdout


@pytest.mark.parametrize('path', sorted((ROOT / 'tracks').rglob('*.design.json')))
def test_committed_gbx_is_reproducible(path, tmp_path):
    track_path = path.with_name(path.name.replace('.design.json', '.json'))
    output = converter.build(track_path, deploy=False, allow_unverified=path.name.startswith('slope_'), output_dir=tmp_path)
    assert output.read_bytes() == path.with_name(output.name).read_bytes()
