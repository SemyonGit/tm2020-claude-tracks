"""Compose + validate a high-level design into a schema-compliant track.json.

Usage:  py -3.12 compose.py design.json [out.json]
The output feeds the existing converter/build.py unchanged.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from track_lib.composer import compose
from track_lib.validator import validate

def main():
    if len(sys.argv) < 2:
        print("usage: compose.py design.json [out.json]"); sys.exit(2)
    design = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    track = compose(design)
    for w in track.get("_warnings", []):
        print("⚠ ", w)
    problems = validate(track)
    if problems:
        print("❌ Validator failed:")
        for p in problems: print("   " + p)
        sys.exit(1)
    track.pop("_warnings", None)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(sys.argv[1]).with_name(
        track["meta"]["name"].lower() + ".json")
    out.write_text(json.dumps(track, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ {len(track['blocks'])} blocks, {len(track['checkpoints'])} CP, connected → {out}")

if __name__ == "__main__":
    main()
