"""Compose a design into validated coordinates: python compose.py design.json out.json."""
import argparse
import json
from pathlib import Path
import sys

from track_lib.composer import compose
from track_lib.files import atomic_write


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('design', type=Path)
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('--allow-unverified', action='store_true', help='allow modelled slopes for calibration')
    args = parser.parse_args(argv)
    try:
        design = json.loads(args.design.read_text(encoding='utf-8'))
        track = compose(design, allow_unverified=args.allow_unverified)
        for warning in track.pop('_warnings', []):
            print(f'WARNING: {warning}')
        default_name = (args.design.name.removesuffix('.design.json') + '.json'
                        if args.design.name.endswith('.design.json')
                        else args.design.stem + '.track.json')
        output = args.output or args.design.with_name(default_name)
        if output.resolve() == args.design.resolve():
            raise ValueError('output must not overwrite the design input')
        atomic_write(output, (json.dumps(track, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))
        print(f'{len(track["blocks"])} blocks, {len(track["checkpoints"])} checkpoints -> {output}')
        return 0
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
