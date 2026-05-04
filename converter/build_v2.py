#!/usr/bin/env python3
"""
TM2020 Track Converter – v2
JSON → .Challenge.Gbx (via pygbx) → .Map.Gbx (via NationsConverterCLI)

Getestet und verifiziert gegen pygbx STADIUM_BLOCKS.
Alle Block-Namen sind auf echte TMNF-Block-Namen gemappt.

Verwendung:
    python build.py tracks/speedtech/silvercut/silvercut.json
    python build.py tracks/speedtech/silvercut/silvercut.json --dry-run
    python build.py tracks/speedtech/silvercut/silvercut.json --no-deploy
"""

import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import lzo
from pygbx import Gbx
from pygbx.stadium_blocks import STADIUM_BLOCKS

# ─── Pfade ────────────────────────────────────────────────────────────────────

# Template .Challenge.Gbx (TMNF-Format) – liegt im converter/ Ordner
TEMPLATE_PATH = Path(__file__).parent / "template.Challenge.Gbx"

# NationsConverterCLI – passe diesen Pfad an!
NATIONS_CONVERTER = Path(r"C:\Users\DEIN-USER\Downloads\NationsConverterCLI\NationsConverterCLI.exe")

# TM2020 Maps-Ordner (automatische Erkennung)
TM2020_DIRS = [
    Path.home() / "Documents" / "Trackmania" / "Maps" / "My Maps",
    Path.home() / "Documents" / "ManiaPlanet" / "Maps" / "My Maps",
]

# ─── Block-Mapping ────────────────────────────────────────────────────────────
# Unsere JSON-Namen → echte STADIUM_BLOCKS Namen (verifiziert gegen pygbx 0.3)

BLOCK_MAP = {
    # Basis
    "StadiumRoadMainStraight":      "StadiumRoadMain",
    "StadiumRoadMainStart":         "StadiumRoadMainStartLine",
    "StadiumRoadMainFinish":        "StadiumRoadMainFinishLine",
    "StadiumRoadMainCheckpointIn":  "StadiumRoadMainCheckpoint",

    # Kurven
    "StadiumRoadMainCurve1Right":   "StadiumRoadMainGTCurve2",
    "StadiumRoadMainCurve1Left":    "StadiumRoadMainGTCurve2",
    "StadiumRoadMainCurve2Right":   "StadiumRoadMainGTCurve3",
    "StadiumRoadMainCurve2Left":    "StadiumRoadMainGTCurve3",
    "StadiumRoadMainCurve3Right":   "StadiumRoadMainGTCurve4",
    "StadiumRoadMainCurve3Left":    "StadiumRoadMainGTCurve4",

    # Chicanen
    "StadiumRoadMainChicaneRight":  "StadiumCircuitBase",
    "StadiumRoadMainChicaneLeft":   "StadiumCircuitBase",

    # Neigung / Bank
    "StadiumRoadMainBankRight":     "StadiumRoadMainFWTilt",
    "StadiumRoadMainBankLeft":      "StadiumRoadMainFWTilt",
    "StadiumRoadMainSlope1Up":      "StadiumRoadMainSlopeBase",
    "StadiumRoadMainSlope1Down":    "StadiumRoadMainSlopeBase",
    "StadiumRoadMainSlope2Up":      "StadiumRoadMainSlopeBase2",
    "StadiumRoadMainSlope2Down":    "StadiumRoadMainSlopeBase2",

    # Wand / Plattform
    "StadiumRoadMainWallLeft":      "StadiumPlatformRoad",
    "StadiumRoadMainWallRight":     "StadiumPlatformRoad",

    # Turbo
    "StadiumRoadMainTurbo":         "StadiumRoadMainTurbo",

    # Passthrough (Name ist bereits korrekt)
    "StadiumRoadMain":              "StadiumRoadMain",
    "StadiumRoadMainStartLine":     "StadiumRoadMainStartLine",
    "StadiumRoadMainFinishLine":    "StadiumRoadMainFinishLine",
    "StadiumRoadMainCheckpoint":    "StadiumRoadMainCheckpoint",
    "StadiumRoadMainGTCurve2":      "StadiumRoadMainGTCurve2",
    "StadiumRoadMainGTCurve3":      "StadiumRoadMainGTCurve3",
    "StadiumRoadMainGTCurve4":      "StadiumRoadMainGTCurve4",
    "StadiumCircuitBase":           "StadiumCircuitBase",
    "StadiumRoadMainSlopeBase":     "StadiumRoadMainSlopeBase",
    "StadiumRoadMainSlopeBase2":    "StadiumRoadMainSlopeBase2",
    "StadiumPlatformRoad":          "StadiumPlatformRoad",
}

CP_FLAG = 0x100  # Checkpoint-Flag

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def resolve_block(json_name: str) -> str | None:
    """Mappt JSON-Blockname auf echten STADIUM_BLOCKS Namen."""
    real = BLOCK_MAP.get(json_name, json_name)
    if real in STADIUM_BLOCKS:
        return real
    print(f"  ⚠ Unbekannter Block: '{json_name}' → '{real}' (nicht in STADIUM_BLOCKS)")
    return None


def get_tm2020_maps_dir() -> Path | None:
    for d in TM2020_DIRS:
        if d.exists():
            return d
    return None


def write_lookback_string(data: bytearray, s: str, store: list):
    """Schreibt einen LookbackString in den Buffer."""
    if s not in store:
        data.extend(struct.pack("I", 0x80000000))
        encoded = s.encode("utf-8")
        data.extend(struct.pack("I", len(encoded)))
        data.extend(encoded)
        store.append(s)
    else:
        idx = store.index(s)
        data.extend(struct.pack("I", 0x40000000 | (idx + 1)))


# ─── Haupt-Konverter ──────────────────────────────────────────────────────────

def build_challenge_gbx(track: dict, output_path: Path, dry_run: bool = False) -> bool:
    """Erstellt eine .Challenge.Gbx Datei aus track.json."""

    if not TEMPLATE_PATH.exists():
        print(f"❌ Template nicht gefunden: {TEMPLATE_PATH}")
        print("   Kopiere template.Challenge.Gbx in den converter/ Ordner.")
        return False

    meta   = track.get("meta", {})
    blocks = track.get("blocks", [])
    cps    = set(track.get("checkpoints", []))
    name   = meta.get("name", output_path.stem)

    print(f"📦 Verarbeite {len(blocks)} Blöcke...")

    # Block-Daten bauen
    block_data = bytearray()
    block_data.extend(struct.pack("I", len(blocks)))

    string_store: list[str] = []
    skipped = 0

    for i, blk in enumerate(blocks):
        real_name = resolve_block(blk.get("id", ""))
        if not real_name:
            skipped += 1
            continue

        x   = blk.get("x", 0)
        y   = blk.get("y", 1)
        z   = blk.get("z", 0)
        rot = blk.get("rotation", 0) & 3

        flags = blk.get("flags", 0)
        if i in cps:
            flags |= CP_FLAG

        write_lookback_string(block_data, real_name, string_store)
        block_data.extend(struct.pack("B", rot))
        block_data.extend(struct.pack("B", max(0, x)))
        block_data.extend(struct.pack("B", max(1, y)))
        block_data.extend(struct.pack("B", max(0, z)))
        block_data.extend(struct.pack("I", flags))

    if skipped:
        print(f"  ⚠ {skipped} Blöcke übersprungen (unbekannte IDs)")

    if dry_run:
        print(f"\n🔍 Dry-Run – kein Output geschrieben")
        print(f"   Blöcke: {len(blocks) - skipped}/{len(blocks)}")
        print(f"   Checkpoints: {len(cps)}")
        return True

    # Template laden und Block-Daten ersetzen
    gbx = Gbx(str(TEMPLATE_PATH))

    with open(TEMPLATE_PATH, "rb") as f:
        raw = bytearray(f.read())

    body = bytearray(gbx.data)

    # Blöcke einsetzen
    bi = gbx.positions["block_data"]
    if not bi.valid:
        print("❌ block_data Position ungültig im Template")
        return False
    body = body[: bi.pos] + block_data + body[bi.pos + bi.size :]

    # Map-Name einsetzen
    name_bytes = bytearray()
    name_bytes.extend(struct.pack("I", len(name)))
    name_bytes.extend(name.encode("utf-8"))

    mi = gbx.positions["map_name"]
    if mi.valid:
        body = body[: mi.pos] + name_bytes + body[mi.pos + mi.size :]

    # Body komprimieren
    compressed = lzo.compress(bytes(body), 1, False)

    # Grössen in Header patchen
    ds = gbx.positions["data_size"]
    raw[ds.pos : ds.pos + 4] = struct.pack("I", len(body))
    raw[ds.pos + 4 : ds.pos + 8] = struct.pack("I", len(compressed))
    raw = raw[: ds.pos + 8] + compressed

    # Track-Name im Header
    ti = gbx.positions["track_name"]
    if ti.valid:
        raw = raw[: ti.pos] + name_bytes + raw[ti.pos + ti.size :]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(raw)

    print(f"✅ .Challenge.Gbx gespeichert: {output_path}")
    return True


def convert_to_tm2020(challenge_path: Path, output_dir: Path) -> Path | None:
    """Ruft NationsConverterCLI auf um .Challenge.Gbx → .Map.Gbx."""

    if not NATIONS_CONVERTER.exists():
        print(f"⚠ NationsConverterCLI nicht gefunden: {NATIONS_CONVERTER}")
        print("  Download: https://github.com/BigBang1112/nations-converter/releases")
        print("  Passe NATIONS_CONVERTER in converter/build.py an.")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(NATIONS_CONVERTER),
        str(challenge_path.resolve()),
        "--output", str(output_dir),
        "--no-live",
    ]

    print(f"🔄 Konvertiere zu TM2020...")
    try:
        subprocess.run(cmd, check=True, cwd=NATIONS_CONVERTER.parent)
    except subprocess.CalledProcessError as e:
        print(f"❌ NationsConverterCLI fehlgeschlagen: {e}")
        return None

    # Output-Datei finden
    map_name = challenge_path.name.replace(".Challenge.Gbx", ".Map.Gbx")
    result = output_dir / map_name
    if result.exists():
        print(f"✅ .Map.Gbx erstellt: {result}")
        return result

    print(f"❌ Erwartete Ausgabe nicht gefunden: {result}")
    return None


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="TM2020 Track Converter v2")
    parser.add_argument("input",       help="Pfad zur track.json")
    parser.add_argument("--dry-run",   action="store_true", help="Nur prüfen, nicht schreiben")
    parser.add_argument("--no-deploy", action="store_true", help="Nicht in TM2020-Ordner kopieren")
    parser.add_argument("--output",    help="Ausgabe-Ordner (optional)")
    args = parser.parse_args()

    json_path = Path(args.input)
    if not json_path.exists():
        print(f"❌ Nicht gefunden: {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        track = json.load(f)

    name     = track.get("meta", {}).get("name", json_path.stem)
    category = track.get("meta", {}).get("category", "fun")
    diff     = track.get("meta", {}).get("difficulty", "?")
    creat    = track.get("meta", {}).get("creativity", "?")

    print(f"\n🏎️  {name}  |  {category}  |  D{diff}/5  C{creat}/5")
    print("─" * 50)

    out_dir = Path(args.output) if args.output else json_path.parent
    challenge_path = out_dir / f"{name}.Challenge.Gbx"

    # Schritt 1: JSON → .Challenge.Gbx
    ok = build_challenge_gbx(track, challenge_path, dry_run=args.dry_run)
    if not ok or args.dry_run:
        sys.exit(0 if args.dry_run else 1)

    # Schritt 2: .Challenge.Gbx → .Map.Gbx
    nc_output_dir = out_dir / "_nc_output"
    map_gbx = convert_to_tm2020(challenge_path, nc_output_dir)

    if not map_gbx:
        print("\n⚠ Konvertierung übersprungen – .Challenge.Gbx ist trotzdem verfügbar.")
        print("  Manuell konvertieren: NationsConverterCLI.exe", challenge_path)
        sys.exit(0)

    # Schritt 3: In TM2020-Ordner kopieren
    if not args.no_deploy:
        tm_dir = get_tm2020_maps_dir()
        if tm_dir:
            dest = tm_dir / map_gbx.name
            shutil.copy2(map_gbx, dest)
            print(f"🎮 Deployed: {dest}")
        else:
            print("⚠ TM2020 Maps-Ordner nicht gefunden – manuell kopieren.")

    print(f"\n✅ Fertig! '{name}' ist bereit zum Spielen.")


if __name__ == "__main__":
    main()
