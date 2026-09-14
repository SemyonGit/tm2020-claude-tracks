"""Export the actual block names, GBX coordinates and orientations from a map."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from converter.build import close_map, find_blocks_chunk, header_chunk, parse_file
from track_lib.files import atomic_write


def inspect(path: Path) -> dict:
    data = parse_file(str(path), recursive=False)
    if '_error' in data:
        raise ValueError(data._error)
    try:
        if data.get('_errors'):
            raise ValueError(f'GBX parse errors: {data._errors}')
        chunk = find_blocks_chunk(data)
        if chunk is None:
            raise ValueError('map does not contain block chunk 0x0304301F')
        header = header_chunk(data, 0x03043003)
        return {
            'source': path.name, 'name': chunk.mapName, 'uid': chunk.mapInfo.id,
            'header_name': header.mapName if header else None,
            'size': {k: chunk.size[k] for k in ('x', 'y', 'z')},
            'coordinate_system': 'raw GBX coordinates; y includes the template offset',
            'warnings': data.get('_warns', []),
            'blocks': [
                {'index': i, 'name': b.name, **{k: b.coords[k] for k in ('x', 'y', 'z')},
                 'dir': str(b.dir), 'ground': b.flags.isGround, 'waypoint': b.flags.isWaypoint}
                for i, b in enumerate(chunk.Blocks) if b.flags != -1
            ],
        }
    finally:
        close_map(data)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect(args.map)
        text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        if args.output:
            if args.map.resolve() == args.output.resolve():
                raise ValueError('output must not overwrite the input map')
            atomic_write(args.output, text.encode('utf-8'))
            print(f'{len(result["blocks"])} blocks -> {args.output}')
        else:
            print(text, end='')
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
