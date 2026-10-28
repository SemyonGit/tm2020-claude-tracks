"""Declared gaps: composer + validator + verify_track accept them, undeclared gaps fail."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "physics"))
from track_lib.composer import compose  # noqa: E402
from track_lib.validator import validate  # noqa: E402
from plan_jumps import plan  # noqa: E402

DESIGN = json.loads((ROOT / "tracks/stunts/droptest/droptest.design.json").read_text(encoding="utf-8"))


def test_declared_gaps_validate():
    track = compose(DESIGN)
    assert [j["cells"] for j in track["jumps"]] == [1, 3]
    assert validate(track) == []


def test_undeclared_gap_fails():
    track = compose(DESIGN)
    track.pop("jumps")
    assert any("gap" in p for p in validate(track))


def test_droptest_predictions_clear_the_gaps():
    results = plan(compose(DESIGN))
    assert [r["verdict"] for _, r in results] == ["ok", "ok"]
    assert 250 < results[0][1]["takeoff_kmh"] < 300  # ground model sanity
