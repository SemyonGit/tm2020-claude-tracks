#!/usr/bin/env python3
"""
TM2020 Track Converter — JSON → .Map.Gbx (direkt, kein Umweg über TMNF).

Nutzt das vendored gbx-py (converter/gbxpy/) zum Lesen eines TM2020-Map-Templates,
ersetzt die Block-Liste mit den JSON-Daten und schreibt eine fertige .Map.Gbx.

Beispiele
---------
    python converter/build.py tracks/speedtech/silvercut/silvercut.json
    python converter/build.py tracks/speedtech/silvercut/silvercut.json --dry-run
    python converter/build.py tracks/ --batch
    python converter/build.py track.json --no-deploy
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

# Vendored gbx-py liegt neben diesem Skript
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from construct import Container  # noqa: E402
from gbxpy import parse_file, generate_file  # noqa: E402

# ─── Konfiguration ─────────────────────────────────────────────────────────────

TEMPLATE = ROOT / "template.Map.Gbx"

TM2020_MAP_DIRS = [
    Path.home() / "Documents" / "Trackmania" / "Maps" / "My Maps",
    Path.home() / "Documents" / "ManiaPlanet" / "Maps" / "My Maps",
    # Windows-Pfade falls Codespaces/WSL aus Linux mounted /mnt/c
    Path("/mnt/c/Users") / (Path.home().name) / "Documents" / "Trackmania" / "Maps" / "My Maps",
]

# ─── Block-Mapping ─────────────────────────────────────────────────────────────
# Unsere JSON-IDs → echte TM2020-Block-Namen.
#
# Verifizierte Namen (aus realen TM2020-Editor-Saves geparst):
#   • Template.Map.Gbx     →  RoadTechStart, RoadTechFinish
#   • jantronix wurst.Gbx  →  RoadBumpStart/Finish/Checkpoint/Straight/Curve1/
#                             Curve2/SlopeBase/SlopeBase2/SpecialTurbo,
#                             TrackWallStraightPillar, TrackWallCurve1Pillar,
#                             TrackWallCurve2Pillar, TrackWallDeadendRoundPillar
#
# Muster: kein "Stadium"-Prefix. Schema = Road{Type}{Suffix}. Type für die
# Standard-Tarmac-Strecke ist "Tech" (von RoadTechStart/Finish im Template
# bestätigt); übrige Suffixe sind analog zum vollständig geparsten RoadBump-Set
# abgeleitet. Chicane/Bank/Wall haben in den geparsten Maps kein eindeutiges
# Pendant — fallen vorerst auf Curve1/Straight zurück.

BLOCK_MAP: dict[str, str] = {
    "StadiumRoadMainStraight":      "RoadTechStraight",
    "StadiumRoadMainStart":         "RoadTechStart",
    "StadiumRoadMainFinish":        "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":  "RoadTechCheckpoint",
    "StadiumRoadMainCurve1Right":   "RoadTechCurve1",
    "StadiumRoadMainCurve1Left":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Right":   "RoadTechCurve2",
    "StadiumRoadMainCurve2Left":    "RoadTechCurve2",
    "StadiumRoadMainCurve3Right":   "RoadTechCurve3",
    "StadiumRoadMainCurve3Left":    "RoadTechCurve3",
    "StadiumRoadMainChicaneRight":  "RoadTechCurve1",
    "StadiumRoadMainChicaneLeft":   "RoadTechCurve1",
    "StadiumRoadMainBankRight":     "RoadTechStraight",
    "StadiumRoadMainBankLeft":      "RoadTechStraight",
    "StadiumRoadMainSlope1Up":      "RoadTechSlopeBase",
    "StadiumRoadMainSlope1Down":    "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Up":      "RoadTechSlopeBase2",
    "StadiumRoadMainSlope2Down":    "RoadTechSlopeBase2",
    "StadiumRoadMainWallLeft":      "RoadTechStraight",
    "StadiumRoadMainWallRight":     "RoadTechStraight",
    "StadiumRoadMainTurbo":         "RoadTechSpecialTurbo",
}

DIR_NAMES = ("North", "East", "South", "West")


# ─── Block-Konstruktion ────────────────────────────────────────────────────────

def resolve_block(json_id: str) -> str:
    return BLOCK_MAP.get(json_id, json_id)


def is_waypoint_block(json_id: str) -> bool:
    return any(token in json_id for token in ("Start", "Finish", "Checkpoint"))


def make_block(name: str, x: int, y: int, z: int, rotation: int,
               is_waypoint: bool = False, is_ground: bool = True) -> Container:
    """Baut einen GbxBlockInstance Container für gbx-py."""
    flags = Container(
        u04=0,
        isFree=False,
        isGhost=False,
        blockVariantIndex=0,
        isWaypoint=is_waypoint,
        hasU05=False,
        hasObsolete0=False,
        hasU06=False,
        u02a=False,
        isSkinnable=False,
        isPillar=False,
        isClip=False,
        isGround=is_ground,
        mobilVariantIndex=0,
        mobilIndex=0,
    )
    return Container(
        name=name,
        dir=DIR_NAMES[rotation & 3],
        coords=Container(x=int(x), y=int(y), z=int(z)),
        flags=flags,
        skinParams=None,
        u05=None,
        waypointParams=None,
        obsolete0=None,
        u06=None,
    )


# ─── Template / Output ─────────────────────────────────────────────────────────

BLOCKS_CHUNK_ID = 0x0304301F

# Skippable Chunks, deren Array-Längen via get_chunk(...).Blocks an die
# Block-Anzahl gekoppelt sind. Sobald wir die Block-Liste austauschen,
# stimmen ihre internen Array-Längen nicht mehr — gbx-py kann sie dann
# nicht mehr serialisieren (SelectError "no subconstruct matched").
# Da alle drei skippable und rein kosmetisch sind (Difficulty-Farben,
# Lightmap-Qualität, Macroblock-Indizes), entfernen wir sie vor dem
# Schreiben. TM2020 lädt die Map auch ohne diese Chunks problemlos.
BLOCK_DEPENDENT_CHUNKS = (0x03043062, 0x03043068, 0x03043069)


def find_blocks_chunk(data) -> Container | None:
    body = data.body
    if BLOCKS_CHUNK_ID in body:
        return body[BLOCKS_CHUNK_ID]
    return None


def strip_block_dependent_chunks(data) -> list[int]:
    body = data.body
    dropped = []
    for cid in BLOCK_DEPENDENT_CHUNKS:
        if cid in body:
            del body[cid]
            dropped.append(cid)
    return dropped


def find_tm2020_maps_dir() -> Path | None:
    for d in TM2020_MAP_DIRS:
        if d.exists():
            return d
    return None


# ─── Build ─────────────────────────────────────────────────────────────────────

def build(json_path: Path, deploy: bool = True, dry_run: bool = False) -> Path | None:
    track = json.loads(json_path.read_text(encoding="utf-8"))
    meta = track.get("meta", {})
    name = meta.get("name", json_path.stem)
    blocks_in = track.get("blocks", [])
    cps = set(track.get("checkpoints", []))

    print(f"🏎️  {name}  |  {meta.get('category','?')}  |  "
          f"D{meta.get('difficulty','?')}/5  C{meta.get('creativity','?')}/5")

    block_instances = []
    for i, b in enumerate(blocks_in):
        json_id = b["id"]
        real = resolve_block(json_id)
        is_wp = (i in cps) or is_waypoint_block(json_id)
        inst = make_block(
            name=real,
            x=b["x"], y=b["y"], z=b["z"],
            rotation=b.get("rotation", 0),
            is_waypoint=is_wp,
        )
        block_instances.append(inst)

    print(f"📦 {len(block_instances)} Blöcke "
          f"(Checkpoints: {sum(1 for inst in block_instances if inst.flags.isWaypoint)})")

    if dry_run:
        print("\n🔍 Dry-Run — Block-Liste:")
        for i, inst in enumerate(block_instances):
            wp = " ★" if inst.flags.isWaypoint else ""
            print(f"  [{i:3d}] {inst.name:32s} "
                  f"@ ({inst.coords.x:3d},{inst.coords.y:3d},{inst.coords.z:3d}) "
                  f"dir={inst.dir}{wp}")
        return None

    if not TEMPLATE.exists():
        print(f"\n❌ Kein TM2020-Template gefunden: {TEMPLATE}")
        print("   → siehe converter/setup.md (How to create template.Map.Gbx).")
        sys.exit(1)

    data = parse_file(str(TEMPLATE))
    chunk = find_blocks_chunk(data)
    if chunk is None:
        print(f"❌ Template enthält keinen Blocks-Chunk ({hex(BLOCKS_CHUNK_ID)}).")
        sys.exit(1)

    chunk.Blocks = block_instances
    if "mapName" in chunk:
        chunk.mapName = name

    dropped = strip_block_dependent_chunks(data)
    if dropped:
        print(f"🗑  Drop blockabhängige Chunks: "
              f"{', '.join(f'0x{c:08X}' for c in dropped)}")

    out_path = json_path.parent / f"{name}.Map.Gbx"
    out_path.write_bytes(generate_file(data))
    print(f"✅ {out_path}")

    if deploy:
        target = find_tm2020_maps_dir()
        if target:
            dest = target / out_path.name
            shutil.copy2(out_path, dest)
            print(f"🎮 Deployed: {dest}")
        else:
            print("⚠ TM2020 Maps-Ordner nicht gefunden — manuell kopieren.")

    return out_path


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="TM2020 Track Converter (gbx-py direct)")
    ap.add_argument("input", help="Pfad zur track.json oder Ordner (mit --batch)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur Block-Liste anzeigen, nichts schreiben")
    ap.add_argument("--no-deploy", action="store_true",
                    help="Nicht in TM2020-Maps-Ordner kopieren")
    ap.add_argument("--batch", action="store_true",
                    help="Eingabe ist ein Ordner — alle *.json rekursiv bauen")
    args = ap.parse_args()

    target = Path(args.input)
    if not target.exists():
        print(f"❌ Nicht gefunden: {target}")
        sys.exit(1)

    if args.batch:
        files = sorted(target.rglob("*.json"))
        print(f"📂 Batch: {len(files)} JSONs in {target}\n")
        ok = fail = 0
        for f in files:
            print(f"— {f.relative_to(target)}")
            try:
                build(f, deploy=not args.no_deploy, dry_run=args.dry_run)
                ok += 1
            except SystemExit:
                fail += 1
            except Exception as e:
                print(f"  ❌ {type(e).__name__}: {e}")
                fail += 1
            print()
        print(f"━━━ Fertig: {ok} ok, {fail} fehlgeschlagen ━━━")
    else:
        build(target, deploy=not args.no_deploy, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
