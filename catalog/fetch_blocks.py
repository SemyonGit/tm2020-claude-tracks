"""Rebuild image indexes locally; optionally download an explicit list of names."""
import argparse
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from track_lib.files import atomic_write

BASE = 'https://images.mania-exchange.com/ix/originalblocks/5/'
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


def indexes(image_dir: Path):
    names = []
    for path in sorted(image_dir.glob('*.png')):
        if not path.read_bytes().startswith(PNG_SIGNATURE):
            raise ValueError(f'not a PNG image: {path}')
        names.append(path.stem)
    if not names:
        raise ValueError('no local block images; refusing to overwrite the catalog with an empty list')
    grouped = {}
    for name in names:
        group = next((p for p in ('RoadTech', 'TrackWall') if name.startswith(p)), 'Other')
        grouped.setdefault(group, []).append(name)
    return names, grouped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='check indexes without changing files')
    parser.add_argument('--download', action='store_true', help='download only explicitly listed candidates')
    parser.add_argument('--names-file', type=Path, help='JSON array of candidate block names')
    args = parser.parse_args(argv)
    try:
        if args.download:
            if args.check or args.names_file is None:
                raise ValueError('--download requires --names-file and cannot be combined with --check')
            names = json.loads(args.names_file.read_text(encoding='utf-8'))
            if not isinstance(names, list) or not names or any(not isinstance(n, str) or not re.fullmatch(r'[A-Za-z0-9_]+', n) for n in names):
                raise ValueError('names file must be a nonempty array of alphanumeric block names')
            for name in sorted(set(names)):
                path = ROOT / 'block_images' / f'{name}.png'
                if path.exists():
                    continue
                try:
                    request = urllib.request.Request(BASE + name + '.png', headers={'User-Agent': 'tm2020-claude-tracks/catalog'})
                    with urllib.request.urlopen(request, timeout=15) as response:
                        data = response.read()
                except urllib.error.HTTPError as exc:
                    if exc.code == 404:
                        print(f'No image: {name}')
                        continue
                    raise
                if not data.startswith(PNG_SIGNATURE):
                    raise ValueError(f'server did not return a PNG for {name}')
                atomic_write(path, data)
        elif args.names_file is not None:
            raise ValueError('--names-file requires --download')
        names, grouped = indexes(ROOT / 'block_images')
        for filename, value in (('blocks.json', names), ('blocks_grouped.json', grouped)):
            path = ROOT / filename
            if args.check:
                if not path.exists() or json.loads(path.read_text(encoding='utf-8')) != value:
                    raise ValueError(f'outdated catalog: {path}; run without --check to rebuild')
            else:
                atomic_write(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))
        print(f'{len(names)} image-backed names; geometry support is defined separately in track_lib/blocks.py')
        return 0
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
