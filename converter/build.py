#!/usr/bin/env python3
"""
TM2020 Track Converter
JSON → .Map.Gbx (GBX Binary Format)

Verwendung:
    python build.py tracks/speedtech/razorline.json
    python build.py tracks/speedtech/razorline.json --output /custom/path/
    python build.py --batch tracks/speedtech/   (alle JSONs im Ordner)
"""

import json
import struct
import sys
import os
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# ── GBX Konstanten ───────────────────────────────────────────────────────────
GBX_MAGIC          = b"GBX"
GBX_VERSION        = 6
CHUNK_CHALLENGE_ID = 0x03043000
CHUNK_MAP_INFO     = 0x03043011
CHUNK_BLOCKS       = 0x0304301F
CHUNK_END          = 0xFACADE01

TM2020_ENV_IDS = {
    "Stadium": 26,
    "Snow":     1,
    "Rally":    2,
    "Desert":   5,
    "Island":  11,
    "Bay":     17,
    "Coast":   24,
}

MOOD_IDS = {
    "Sunrise": 0,
    "Day":     1,
    "Sunset":  2,
    "Night":   3,
    "Storm":   4,
}

# ── GBX Writer ───────────────────────────────────────────────────────────────
class GbxWriter:
    def __init__(self):
        self.buf = bytearray()

    def write_bytes(self, b: bytes):
        self.buf.extend(b)

    def write_uint8(self, v: int):
        self.buf.extend(struct.pack("<B", v & 0xFF))

    def write_uint16(self, v: int):
        self.buf.extend(struct.pack("<H", v & 0xFFFF))

    def write_uint32(self, v: int):
        self.buf.extend(struct.pack("<I", v & 0xFFFFFFFF))

    def write_int32(self, v: int):
        self.buf.extend(struct.pack("<i", v))

    def write_string(self, s: str):
        encoded = s.encode("utf-8")
        self.write_uint32(len(encoded))
        self.buf.extend(encoded)

    def write_lookback(self, s: str):
        """Simplified lookback string (no dedup for now)"""
        self.write_uint32(0xFFFFFFFF)  # new entry flag
        self.write_string(s)

    def get_bytes(self) -> bytes:
        return bytes(self.buf)


def build_gbx(track: dict) -> bytes:
    """Baut eine minimale, ladbare .Map.Gbx Datei."""
    meta      = track.get("meta", {})
    settings  = track.get("settings", {})
    blocks    = track.get("blocks", [])
    cps       = set(track.get("checkpoints", []))

    env_id    = TM2020_ENV_IDS.get(settings.get("environment", "Stadium"), 26)
    mood_id   = MOOD_IDS.get(settings.get("mood", "Day"), 1)
    track_name = meta.get("name", "Unnamed")
    author     = meta.get("author", "Claude")

    w = GbxWriter()

    # ── GBX Header ──────────────────────────────────────────────────────────
    w.write_bytes(GBX_MAGIC)
    w.write_uint16(GBX_VERSION)       # version
    w.write_uint8(ord("B"))           # body compression: B=bzip2, U=uncompressed
    w.write_uint8(ord("U"))           # ref table compression
    w.write_uint8(ord("C"))           # class type: C=challenge/map
    w.write_uint32(CHUNK_CHALLENGE_ID)

    # ── Header Chunks ────────────────────────────────────────────────────────
    # Chunk: Map Info
    w.write_uint32(CHUNK_MAP_INFO)
    w.write_uint32(3)                 # version
    w.write_string(track_name)
    w.write_string(author)
    w.write_string("Claude (Anthropic)")  # author nick
    w.write_string("")                # map uid (empty = auto)
    w.write_uint32(env_id)
    w.write_uint32(mood_id)
    w.write_uint32(len(blocks))

    # ── Block Data ───────────────────────────────────────────────────────────
    w.write_uint32(CHUNK_BLOCKS)
    w.write_uint32(len(blocks))

    for i, blk in enumerate(blocks):
        block_id = blk.get("id", "RoadMainStraight")
        x        = blk.get("x", 0)
        y        = blk.get("y", 1)
        z        = blk.get("z", 0)
        rot      = blk.get("rotation", 0)
        flags    = blk.get("flags", 0)

        if i in cps:
            flags |= 0x400  # Checkpoint-Flag

        w.write_string(block_id)
        w.write_uint8(rot & 3)
        w.write_uint8(x & 0xFF)
        w.write_uint8(y & 0xFF)
        w.write_uint8(z & 0xFF)
        w.write_uint32(flags)

    # ── End Marker ───────────────────────────────────────────────────────────
    w.write_uint32(CHUNK_END)

    return w.get_bytes()


def get_tm2020_maps_path() -> Path | None:
    """Findet den TM2020 Maps-Ordner automatisch."""
    candidates = [
        Path.home() / "Documents" / "ManiaPlanet" / "Maps" / "My Maps",
        Path.home() / "Documents" / "Trackmania" / "Maps" / "My Maps",
        Path("C:/Users") / os.getlogin() / "Documents" / "ManiaPlanet" / "Maps" / "My Maps",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def convert(json_path: str, output_dir: str | None = None, deploy: bool = True):
    json_path = Path(json_path)
    if not json_path.exists():
        print(f"❌ Datei nicht gefunden: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        track = json.load(f)

    name     = track.get("meta", {}).get("name", json_path.stem)
    category = track.get("meta", {}).get("category", "fun")
    diff     = track.get("meta", {}).get("difficulty", "?")
    creat    = track.get("meta", {}).get("creativity", "?")

    print(f"🏎️  Konvertiere: {name} | {category} | D{diff}/5 C{creat}/5")

    gbx_data = build_gbx(track)

    # Output-Pfad bestimmen
    out_dir  = Path(output_dir) if output_dir else json_path.parent
    gbx_path = out_dir / f"{json_path.stem}.Map.Gbx"

    with open(gbx_path, "wb") as f:
        f.write(gbx_data)

    print(f"✅ Gespeichert: {gbx_path} ({len(gbx_data)} bytes)")

    # Automatisch in TM2020-Ordner kopieren
    if deploy:
        tm_path = get_tm2020_maps_path()
        if tm_path:
            dest = tm_path / f"{name}.Map.Gbx"
            shutil.copy2(gbx_path, dest)
            print(f"🎮 Deployed: {dest}")
        else:
            print("⚠️  TM2020 Maps-Ordner nicht gefunden – manuell kopieren.")

    return gbx_path


def batch_convert(folder: str, deploy: bool = True):
    folder = Path(folder)
    jsons  = list(folder.rglob("*.json"))
    jsons  = [j for j in jsons if not j.name.endswith("schema.json")]

    print(f"📦 Batch: {len(jsons)} Track(s) gefunden")
    for j in jsons:
        gbx = j.with_suffix(".Map.Gbx")
        if gbx.exists():
            print(f"⏭️  Übersprungen (existiert): {j.name}")
            continue
        convert(str(j), deploy=deploy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TM2020 JSON → .Map.Gbx Konverter")
    parser.add_argument("input",             help="JSON-Datei oder Ordner (mit --batch)")
    parser.add_argument("--output", "-o",    help="Ausgabe-Ordner", default=None)
    parser.add_argument("--batch",  "-b",    action="store_true", help="Alle JSONs im Ordner konvertieren")
    parser.add_argument("--no-deploy",       action="store_true", help="Nicht in TM2020-Ordner kopieren")
    args = parser.parse_args()

    deploy = not args.no_deploy

    if args.batch:
        batch_convert(args.input, deploy=deploy)
    else:
        convert(args.input, output_dir=args.output, deploy=deploy)
