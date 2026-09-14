"""Rebuild the committed calibration designs and maps without deploying to the game."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from converter.build import build
from track_lib.composer import compose
from track_lib.files import atomic_write


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-slopes', action='store_true', help='include the four UNVERIFIED slope maps')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build' / 'test-pack')
    args = parser.parse_args(argv)
    try:
        count = 0
        for path in sorted((ROOT / 'tracks' / '_validation').rglob('*.design.json')):
            slope = path.stem.startswith('slope_')
            if slope and not args.include_slopes:
                continue
            track = compose(json.loads(path.read_text(encoding='utf-8')), allow_unverified=slope)
            for warning in track.pop('_warnings', []):
                print(f'WARNING: {warning}')
            output = args.output_dir / path.name.replace('.design.json', '.json')
            atomic_write(output, (json.dumps(track, indent=2) + '\n').encode('utf-8'))
            build(output, deploy=False, allow_unverified=slope)
            count += 1
        print(f'{count} calibration maps built in {args.output_dir}')
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
