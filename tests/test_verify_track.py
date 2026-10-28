"""verify_track: committed maps connect; a known-broken map is rejected."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_track import load_shapes, verify  # noqa: E402

SHAPES = load_shapes()


def test_compass_connects():
    ok, notes = verify(ROOT / "tracks/beginner/compass/Compass.Map.Gbx", SHAPES)
    assert ok, notes


def test_proofcut_connects():
    ok, notes = verify(ROOT / "tracks/speedtech/proofcut/Proofcut.Map.Gbx", SHAPES)
    assert ok, notes


def test_backwards_start_is_rejected():
    # Proofcut as built before the 2026-06-03 start/finish fix: spawn faced away.
    ok, notes = verify(Path(__file__).parent / "data/proofcut_backwards_start.Map.Gbx", SHAPES)
    assert not ok and "empty" in notes[-1], notes
