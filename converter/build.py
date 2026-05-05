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

# ─── Koordinatensystem ─────────────────────────────────────────────────────────
# TM2020-Stadium-Maps haben den Editor-Boden bei y=8; Bodenblöcke liegen also
# auf y=9 mit isGround=True (verifiziert via template.Map.Gbx: RoadTechStart
# bei y=9). Unsere JSONs nutzen y=1 als Bodenebene (TMNF-Konvention), daher
# Offset +8 beim Schreiben.
Y_OFFSET = 8
GROUND_Y_JSON = 1  # JSON-y, bei dem ein Block direkt auf dem Editor-Boden steht

# ─── Block-Mapping ─────────────────────────────────────────────────────────────
# Unsere JSON-IDs → echte TM2020-Block-Namen.
#
# Verifizierte Namen (aus realen TM2020-Editor-Saves geparst):
#   • template.Map.Gbx           → RoadTechStart, RoadTechFinish
#   • every platform block.Gbx   → vollständiger RoadTech-Katalog (148 Namen)
#   • jantronix wurst.Gbx        → RoadBump*-Set, zeigt Footprint-Verhalten:
#       RoadBumpCurve1            = 1×1 Zelle  (Slalom: dir wechselt jede Zelle)
#       RoadBumpCurve2            = 2×2 Zellen (Platzierung 2 Zellen versetzt)
#       RoadBumpSlopeBase         = +1 y pro Zelle in Fahrtrichtung
#       RoadBumpSlopeBase2        = +2 y pro Zelle (steiler)
#
# Footprint-Regel:
# Unsere JSONs verwenden ein 1-Zelle-pro-Block-Raster (jeder Block = 1 Grid-
# Cell, +1 y pro Slope-Schritt). Mehr-Zellen-Blöcke (Curve2..5, ChicaneX2/X3,
# SlopeBase2, Loops) würden mit dem Folgeblock kollidieren ("Blöcke liegen
# ineinander"). Daher mappen Curve2..5 und Chicane{Left,Right} per Default auf
# RoadTechCurve1 (1×1) und Slope2 auf RoadTechSlopeBase (+1 y/Zelle). Wer
# explizit Mehr-Zellen-Geometrie will, kann die expliziten IDs ChicaneX2/X3
# bzw. RoadTechCurve2..5 / SlopeBase2 direkt nutzen — dann muss aber das JSON
# entsprechend lückig platziert sein.
#
# Rotation: JSON 0/1/2/3 → North/East/South/West (TM2020-Konvention).

BLOCK_MAP: dict[str, str] = {
    # Start / Finish / Checkpoint
    "StadiumRoadMainStart":          "RoadTechStart",
    "StadiumRoadMainFinish":         "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":   "RoadTechCheckpoint",
    "Checkpoint":                    "RoadTechStraight",  # Checkpoint via isWaypoint-Flag

    # Straight
    "StadiumRoadMainStraight":       "RoadTechStraight",

    # Curves — alle auf 1×1-Curve1 mappen (JSON-Layout = 1 Zelle pro Block)
    "StadiumRoadMainCurve1Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve1Left":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve2Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve2In":       "RoadTechCurve1",
    "StadiumRoadMainCurve2Out":      "RoadTechCurve1",
    "StadiumRoadMainCurve3Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve3Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve4Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve4Left":     "RoadTechCurve1",
    "StadiumRoadMainCurve5Right":    "RoadTechCurve1",
    "StadiumRoadMainCurve5Left":     "RoadTechCurve1",

    # Chicanes — JSON-Layout platziert sie in gerader Linie (kein x/z-Versatz),
    # also In-Line-Jog-Visual ohne Richtungsänderung. Curve1 würde Anschluss-
    # Faces falsch ausrichten; daher Straight (Strecken-Geometrie bleibt heil).
    # Explizite X2/X3-IDs landen auf den echten Mehr-Zellen-Chicanes.
    "StadiumRoadMainChicaneRight":   "RoadTechStraight",
    "StadiumRoadMainChicaneLeft":    "RoadTechStraight",
    "StadiumRoadMainChicaneX2Right": "RoadTechChicaneX2Right",
    "StadiumRoadMainChicaneX2Left":  "RoadTechChicaneX2Left",
    "StadiumRoadMainChicaneX3Right": "RoadTechChicaneX3Right",
    "StadiumRoadMainChicaneX3Left":  "RoadTechChicaneX3Left",

    # Banking — kein passendes 1-Zelle-Banking; Fallback auf Straight.
    # Wer echtes TiltStraight (gebankter Straight) will, ID direkt nutzen.
    "StadiumRoadMainBankRight":      "RoadTechStraight",
    "StadiumRoadMainBankLeft":       "RoadTechStraight",
    "StadiumRoadMainTiltStraight":   "RoadTechTiltStraight",

    # Slopes — JSON-Delta = +1 y/Zelle ⇒ SlopeBase (NICHT SlopeBase2).
    "StadiumRoadMainSlope1Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope1Down":     "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Down":     "RoadTechSlopeBase",

    # Special — alle 1-Zelle-Footprint
    "StadiumRoadMainHole":           "RoadTechHole",
    "StadiumRoadMainPenalty":        "RoadTechPenalty",
    "StadiumRoadMainPenaltyDirt":    "RoadTechPenaltyDirt",
    "StadiumRoadMainPenaltyIce":     "RoadTechPenaltyIce",
    "StadiumRoadMainTurbo":          "RoadTechSpecialTurbo",
    "StadiumRoadMainNarrowCenter":   "RoadTechNarrowCenter",
    "StadiumRoadMainNarrowSide":     "RoadTechNarrowSide",

    # Walls — kein passendes RoadTech-Pendant; Fallback auf Straight
    "StadiumRoadMainWallLeft":       "RoadTechStraight",
    "StadiumRoadMainWallRight":      "RoadTechStraight",
}

# ─── Rotation-Mapping ──────────────────────────────────────────────────────────
# JSON nutzt Kompass-Konvention: rot 0=North(-z) 1=East(+x) 2=South(+z) 3=West(-x).
# TM2020 hat invertierte Z-Achse: dir 0=North(+z) 1=East(+x) 2=South(-z) 3=West(-x).
# Verifiziert via test_kurven.Map.Gbx (manuell gebaut): Straights mit +z-Fahrt-
# richtung tragen dir=North; Slopes mit -x-Fahrtrichtung tragen dir=West.
#
# Für Curves gibt der dir-Index die Block-Rotation an (welche zwei Faces die
# Anschlüsse haben): dir=North → W+N, East → S+W, South → S+E, West → E+N.
# Empirisch aus silvercut.json (4 Eck-Curves) abgeleitet:
#   rot=1 (Auto fährt +x rein, +z raus) → W+N → dir=North
#   rot=2 (+z rein, -x raus)            → S+W → dir=East
#   rot=3 (-x rein, -z raus)            → E+S → dir=South
#   rot=0 (-z rein, +x raus)            → N+E → dir=West
# Spiegelbildlich für Left-Curves: Identity-Mapping.

DIR_NAMES = ("North", "East", "South", "West")  # TM2020 dir-int → Name

# Mapping: JSON rot (0..3) → TM2020 dir int (0..3)
STRAIGHT_DIR_MAP = (2, 1, 0, 3)      # für Straights/Start/Finish/Slope/Tilt
CURVE_RIGHT_DIR_MAP = (3, 0, 1, 2)   # für *Right / *In Curves
CURVE_LEFT_DIR_MAP = (0, 1, 2, 3)    # für *Left / *Out Curves (Spiegel)


# ─── Block-Konstruktion ────────────────────────────────────────────────────────

def resolve_block(json_id: str) -> str:
    return BLOCK_MAP.get(json_id, json_id)


def is_waypoint_block(json_id: str) -> bool:
    return any(token in json_id for token in ("Start", "Finish", "Checkpoint"))


def tm2020_dir(json_id: str, json_rot: int) -> str:
    """Übersetze JSON-Rotation in TM2020-dir-Namen.

    Curves brauchen ein anderes Mapping als gerade Blöcke, weil dir bei Curves
    die Block-Rotation kodiert (welche Faces verbunden sind), nicht die Fahrt-
    richtung. Nur echte Eck-Curves (StadiumRoadMain*Curve{N}{Right,Left,In,Out})
    bekommen die Curve-Maps; Chicanes/Straights/Slopes/Banks gehen den Straight-Pfad.
    """
    rot = json_rot & 3
    if "Curve" in json_id:
        if json_id.endswith("Right") or json_id.endswith("In"):
            return DIR_NAMES[CURVE_RIGHT_DIR_MAP[rot]]
        if json_id.endswith("Left") or json_id.endswith("Out"):
            return DIR_NAMES[CURVE_LEFT_DIR_MAP[rot]]
    return DIR_NAMES[STRAIGHT_DIR_MAP[rot]]


def make_block(name: str, x: int, y: int, z: int, dir_name: str,
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
        dir=dir_name,
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
        json_y = b["y"]
        inst = make_block(
            name=real,
            x=b["x"], y=json_y + Y_OFFSET, z=b["z"],
            dir_name=tm2020_dir(json_id, b.get("rotation", 0)),
            is_waypoint=is_wp,
            is_ground=(json_y == GROUND_Y_JSON),
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
