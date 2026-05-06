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

    # Banking — RoadTechBank* does not exist; fallback to Straight. TiltStraight uses real block.
    "StadiumRoadMainBankRight":      "RoadTechStraight",
    "StadiumRoadMainBankLeft":       "RoadTechStraight",
    "StadiumRoadMainTiltStraight":   "RoadTechTiltStraight",

    # Slopes — JSON-Delta = +1 y/Zelle ⇒ SlopeBase (NICHT SlopeBase2).
    "StadiumRoadMainSlope1Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope1Down":     "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Down":     "RoadTechSlopeBase",

    # Special — RoadTechHole/Penalty exist; PenaltyDirt/Ice/Narrow* do not (fallback to Straight)
    "StadiumRoadMainHole":           "RoadTechHole",
    "StadiumRoadMainPenalty":        "RoadTechPenalty",
    "StadiumRoadMainPenaltyDirt":    "RoadTechStraight",
    "StadiumRoadMainPenaltyIce":     "RoadTechStraight",
    "StadiumRoadMainTurbo":          "RoadTechSpecialTurbo",
    "StadiumRoadMainNarrowCenter":   "RoadTechStraight",
    "StadiumRoadMainNarrowSide":     "RoadTechStraight",

    # Walls — no RoadTech wall variant in catalog; fall back to Straight
    "StadiumRoadMainWallLeft":       "RoadTechStraight",
    "StadiumRoadMainWallRight":      "RoadTechStraight",

    # ─── Catalog-verified explicit aliases (from 191-PNG catalog) ───

    # Curve
    "StadiumRoadMainCurve2":                                "RoadTechCurve2",
    "StadiumRoadMainCurve3":                                "RoadTechCurve3",
    "StadiumRoadMainCurve4":                                "RoadTechCurve4",
    "StadiumRoadMainCurve5":                                "RoadTechCurve5",

    # Slope
    "StadiumRoadMainCheckpointSlopeDown":                   "RoadTechCheckpointSlopeDown",
    "StadiumRoadMainCheckpointSlopeUp":                     "RoadTechCheckpointSlopeUp",
    "StadiumRoadMainChicaneX2SlopeLeft":                    "RoadTechChicaneX2SlopeLeft",
    "StadiumRoadMainChicaneX2SlopeRight":                   "RoadTechChicaneX2SlopeRight",
    "StadiumRoadMainChicaneX3SlopeLeft":                    "RoadTechChicaneX3SlopeLeft",
    "StadiumRoadMainChicaneX3SlopeRight":                   "RoadTechChicaneX3SlopeRight",
    "StadiumRoadMainSlopeBase2":                            "RoadTechSlopeBase2",
    "StadiumRoadMainSlopeBase2x1":                          "RoadTechSlopeBase2x1",
    "StadiumRoadMainSlopeEnd2x1":                           "RoadTechSlopeEnd2x1",
    "StadiumRoadMainSlopeHole":                             "RoadTechSlopeHole",
    "StadiumRoadMainSlopePenalty":                          "RoadTechSlopePenalty",
    "StadiumRoadMainSlopeStart2x1":                         "RoadTechSlopeStart2x1",
    "StadiumRoadMainSlopeStraight":                         "RoadTechSlopeStraight",
    "StadiumRoadMainSlopeUBottom":                          "RoadTechSlopeUBottom",
    "StadiumRoadMainSlopeUBottomInGround":                  "RoadTechSlopeUBottomInGround",
    "StadiumRoadMainSlopeUBottomX2":                        "RoadTechSlopeUBottomX2",
    "StadiumRoadMainSlopeUBottomX2InGround":                "RoadTechSlopeUBottomX2InGround",
    "StadiumRoadMainSlopeUTop":                             "RoadTechSlopeUTop",
    "StadiumRoadMainSlopeUTopX2":                           "RoadTechSlopeUTopX2",
    "StadiumRoadMainSpecialBoost2SlopeDown":                "RoadTechSpecialBoost2SlopeDown",
    "StadiumRoadMainSpecialBoost2SlopeUp":                  "RoadTechSpecialBoost2SlopeUp",
    "StadiumRoadMainSpecialBoostSlopeDown":                 "RoadTechSpecialBoostSlopeDown",
    "StadiumRoadMainSpecialBoostSlopeUp":                   "RoadTechSpecialBoostSlopeUp",
    "StadiumRoadMainSpecialCruiseSlope":                    "RoadTechSpecialCruiseSlope",
    "StadiumRoadMainSpecialFragileSlope":                   "RoadTechSpecialFragileSlope",
    "StadiumRoadMainSpecialNoBrakeSlope":                   "RoadTechSpecialNoBrakeSlope",
    "StadiumRoadMainSpecialNoEngineSlope":                  "RoadTechSpecialNoEngineSlope",
    "StadiumRoadMainSpecialNoSteeringSlope":                "RoadTechSpecialNoSteeringSlope",
    "StadiumRoadMainSpecialResetSlope":                     "RoadTechSpecialResetSlope",
    "StadiumRoadMainSpecialSlowMotionSlope":                "RoadTechSpecialSlowMotionSlope",
    "StadiumRoadMainSpecialTurbo2SlopeDown":                "RoadTechSpecialTurbo2SlopeDown",
    "StadiumRoadMainSpecialTurbo2SlopeUp":                  "RoadTechSpecialTurbo2SlopeUp",
    "StadiumRoadMainSpecialTurboRouletteSlopeDown":         "RoadTechSpecialTurboRouletteSlopeDown",
    "StadiumRoadMainSpecialTurboRouletteSlopeUp":           "RoadTechSpecialTurboRouletteSlopeUp",
    "StadiumRoadMainSpecialTurboSlopeDown":                 "RoadTechSpecialTurboSlopeDown",
    "StadiumRoadMainSpecialTurboSlopeUp":                   "RoadTechSpecialTurboSlopeUp",

    # Branch
    "StadiumRoadMainBranchCross":                           "RoadTechBranchCross",
    "StadiumRoadMainBranchCurve3Left":                      "RoadTechBranchCurve3Left",
    "StadiumRoadMainBranchCurve3Right":                     "RoadTechBranchCurve3Right",
    "StadiumRoadMainBranchStraightX4Left":                  "RoadTechBranchStraightX4Left",
    "StadiumRoadMainBranchStraightX4Right":                 "RoadTechBranchStraightX4Right",
    "StadiumRoadMainBranchTShaped":                         "RoadTechBranchTShaped",
    "StadiumRoadMainBranchToDiagLeft":                      "RoadTechBranchToDiagLeft",
    "StadiumRoadMainBranchToDiagRight":                     "RoadTechBranchToDiagRight",
    "StadiumRoadMainBranchYShaped2X3":                      "RoadTechBranchYShaped2X3",
    "StadiumRoadMainBranchYShaped2X3SlopeDown":             "RoadTechBranchYShaped2X3SlopeDown",
    "StadiumRoadMainBranchYShaped2X3SlopeUp":               "RoadTechBranchYShaped2X3SlopeUp",

    # Diag
    "StadiumRoadMainDiagLeftCheckpoint":                    "RoadTechDiagLeftCheckpoint",
    "StadiumRoadMainDiagLeftLoop11X":                       "RoadTechDiagLeftLoop11X",
    "StadiumRoadMainDiagLeftLoop6X":                        "RoadTechDiagLeftLoop6X",
    "StadiumRoadMainDiagLeftMultilap":                      "RoadTechDiagLeftMultilap",
    "StadiumRoadMainDiagLeftPenalty":                       "RoadTechDiagLeftPenalty",
    "StadiumRoadMainDiagLeftRampLow":                       "RoadTechDiagLeftRampLow",
    "StadiumRoadMainDiagLeftStartCurve1In":                 "RoadTechDiagLeftStartCurve1In",
    "StadiumRoadMainDiagLeftStartCurve1Out":                "RoadTechDiagLeftStartCurve1Out",
    "StadiumRoadMainDiagLeftStartCurve2In":                 "RoadTechDiagLeftStartCurve2In",
    "StadiumRoadMainDiagLeftStartCurve2Out":                "RoadTechDiagLeftStartCurve2Out",
    "StadiumRoadMainDiagLeftStartStraightX2":               "RoadTechDiagLeftStartStraightX2",
    "StadiumRoadMainDiagLeftStraightX2":                    "RoadTechDiagLeftStraightX2",
    "StadiumRoadMainDiagRightCheckpoint":                   "RoadTechDiagRightCheckpoint",
    "StadiumRoadMainDiagRightHole":                         "RoadTechDiagRightHole",
    "StadiumRoadMainDiagRightLoop11X":                      "RoadTechDiagRightLoop11X",
    "StadiumRoadMainDiagRightLoop6X":                       "RoadTechDiagRightLoop6X",
    "StadiumRoadMainDiagRightMultilap":                     "RoadTechDiagRightMultilap",
    "StadiumRoadMainDiagRightPenalty":                      "RoadTechDiagRightPenalty",
    "StadiumRoadMainDiagRightRampLow":                      "RoadTechDiagRightRampLow",
    "StadiumRoadMainDiagRightStartCurve1In":                "RoadTechDiagRightStartCurve1In",
    "StadiumRoadMainDiagRightStartCurve1Out":               "RoadTechDiagRightStartCurve1Out",
    "StadiumRoadMainDiagRightStartCurve2In":                "RoadTechDiagRightStartCurve2In",
    "StadiumRoadMainDiagRightStartCurve2Out":               "RoadTechDiagRightStartCurve2Out",
    "StadiumRoadMainDiagRightStartStraightX2":              "RoadTechDiagRightStartStraightX2",
    "StadiumRoadMainDiagRightStraightX2":                   "RoadTechDiagRightStraightX2",
    "StadiumRoadMainDiagSwitchCurve1In":                    "RoadTechDiagSwitchCurve1In",
    "StadiumRoadMainDiagSwitchCurve1Out":                   "RoadTechDiagSwitchCurve1Out",
    "StadiumRoadMainDiagSwitchCurve2In":                    "RoadTechDiagSwitchCurve2In",
    "StadiumRoadMainDiagSwitchCurve2Out":                   "RoadTechDiagSwitchCurve2Out",
    "StadiumRoadMainDiagSwitchStraightX1":                  "RoadTechDiagSwitchStraightX1",
    "StadiumRoadMainDiagSwitchStraightX2":                  "RoadTechDiagSwitchStraightX2",
    "StadiumRoadMainSpecialBoost2DiagLeft":                 "RoadTechSpecialBoost2DiagLeft",
    "StadiumRoadMainSpecialBoost2DiagRight":                "RoadTechSpecialBoost2DiagRight",
    "StadiumRoadMainSpecialBoostDiagLeft":                  "RoadTechSpecialBoostDiagLeft",
    "StadiumRoadMainSpecialBoostDiagRight":                 "RoadTechSpecialBoostDiagRight",
    "StadiumRoadMainSpecialCruiseDiagLeft":                 "RoadTechSpecialCruiseDiagLeft",
    "StadiumRoadMainSpecialCruiseDiagRight":                "RoadTechSpecialCruiseDiagRight",
    "StadiumRoadMainSpecialFragileDiagLeft":                "RoadTechSpecialFragileDiagLeft",
    "StadiumRoadMainSpecialFragileDiagRight":               "RoadTechSpecialFragileDiagRight",
    "StadiumRoadMainSpecialNoBrakeDiagLeft":                "RoadTechSpecialNoBrakeDiagLeft",
    "StadiumRoadMainSpecialNoBrakeDiagRight":               "RoadTechSpecialNoBrakeDiagRight",
    "StadiumRoadMainSpecialNoEngineDiagLeft":               "RoadTechSpecialNoEngineDiagLeft",
    "StadiumRoadMainSpecialNoEngineDiagRight":              "RoadTechSpecialNoEngineDiagRight",
    "StadiumRoadMainSpecialNoSteeringDiagLeft":             "RoadTechSpecialNoSteeringDiagLeft",
    "StadiumRoadMainSpecialNoSteeringDiagRight":            "RoadTechSpecialNoSteeringDiagRight",
    "StadiumRoadMainSpecialResetDiagLeft":                  "RoadTechSpecialResetDiagLeft",
    "StadiumRoadMainSpecialResetDiagRight":                 "RoadTechSpecialResetDiagRight",
    "StadiumRoadMainSpecialSlowMotionDiagLeft":             "RoadTechSpecialSlowMotionDiagLeft",
    "StadiumRoadMainSpecialSlowMotionDiagRight":            "RoadTechSpecialSlowMotionDiagRight",
    "StadiumRoadMainSpecialTurbo2DiagLeft":                 "RoadTechSpecialTurbo2DiagLeft",
    "StadiumRoadMainSpecialTurbo2DiagRight":                "RoadTechSpecialTurbo2DiagRight",
    "StadiumRoadMainSpecialTurboDiagLeft":                  "RoadTechSpecialTurboDiagLeft",
    "StadiumRoadMainSpecialTurboDiagRight":                 "RoadTechSpecialTurboDiagRight",
    "StadiumRoadMainSpecialTurboRouletteDiagLeft":          "RoadTechSpecialTurboRouletteDiagLeft",
    "StadiumRoadMainSpecialTurboRouletteDiagRight":         "RoadTechSpecialTurboRouletteDiagRight",

    # Special
    "StadiumRoadMainSpecialBoost":                          "RoadTechSpecialBoost",
    "StadiumRoadMainSpecialBoost2":                         "RoadTechSpecialBoost2",
    "StadiumRoadMainSpecialCruise":                         "RoadTechSpecialCruise",
    "StadiumRoadMainSpecialFragile":                        "RoadTechSpecialFragile",
    "StadiumRoadMainSpecialNoBrake":                        "RoadTechSpecialNoBrake",
    "StadiumRoadMainSpecialNoEngine":                       "RoadTechSpecialNoEngine",
    "StadiumRoadMainSpecialNoSteering":                     "RoadTechSpecialNoSteering",
    "StadiumRoadMainSpecialReset":                          "RoadTechSpecialReset",
    "StadiumRoadMainSpecialSlowMotion":                     "RoadTechSpecialSlowMotion",
    "StadiumRoadMainSpecialTurbo2":                         "RoadTechSpecialTurbo2",
    "StadiumRoadMainSpecialTurboRoulette":                  "RoadTechSpecialTurboRoulette",

    # TiltCurve
    "StadiumRoadMainTiltCurve1":                            "RoadTechTiltCurve1",
    "StadiumRoadMainTiltCurve1DownLeft":                    "RoadTechTiltCurve1DownLeft",
    "StadiumRoadMainTiltCurve1DownRight":                   "RoadTechTiltCurve1DownRight",
    "StadiumRoadMainTiltCurve1Out":                         "RoadTechTiltCurve1Out",
    "StadiumRoadMainTiltCurve1UpLeft":                      "RoadTechTiltCurve1UpLeft",
    "StadiumRoadMainTiltCurve1UpRight":                     "RoadTechTiltCurve1UpRight",
    "StadiumRoadMainTiltCurve2":                            "RoadTechTiltCurve2",
    "StadiumRoadMainTiltCurve2DownLeft":                    "RoadTechTiltCurve2DownLeft",
    "StadiumRoadMainTiltCurve2DownRight":                   "RoadTechTiltCurve2DownRight",
    "StadiumRoadMainTiltCurve2Out":                         "RoadTechTiltCurve2Out",
    "StadiumRoadMainTiltCurve2UpLeft":                      "RoadTechTiltCurve2UpLeft",
    "StadiumRoadMainTiltCurve2UpRight":                     "RoadTechTiltCurve2UpRight",
    "StadiumRoadMainTiltCurve3":                            "RoadTechTiltCurve3",
    "StadiumRoadMainTiltCurve3Out":                         "RoadTechTiltCurve3Out",
    "StadiumRoadMainTiltCurve4":                            "RoadTechTiltCurve4",
    "StadiumRoadMainTiltCurve4Out":                         "RoadTechTiltCurve4Out",
    "StadiumRoadMainTiltTransition2DownLeftCurveIn":        "RoadTechTiltTransition2DownLeftCurveIn",
    "StadiumRoadMainTiltTransition2DownRightCurveIn":       "RoadTechTiltTransition2DownRightCurveIn",
    "StadiumRoadMainTiltTransition2UpLeftCurveIn":          "RoadTechTiltTransition2UpLeftCurveIn",
    "StadiumRoadMainTiltTransition2UpRightCurveIn":         "RoadTechTiltTransition2UpRightCurveIn",

    # TiltTransition
    "StadiumRoadMainTiltTransition1DownLeft":               "RoadTechTiltTransition1DownLeft",
    "StadiumRoadMainTiltTransition1DownRight":              "RoadTechTiltTransition1DownRight",
    "StadiumRoadMainTiltTransition1UpLeft":                 "RoadTechTiltTransition1UpLeft",
    "StadiumRoadMainTiltTransition1UpRight":                "RoadTechTiltTransition1UpRight",
    "StadiumRoadMainTiltTransition2DownLeft":               "RoadTechTiltTransition2DownLeft",
    "StadiumRoadMainTiltTransition2DownRight":              "RoadTechTiltTransition2DownRight",
    "StadiumRoadMainTiltTransition2Up1LeftChicane":         "RoadTechTiltTransition2Up1LeftChicane",
    "StadiumRoadMainTiltTransition2Up1RightChicane":        "RoadTechTiltTransition2Up1RightChicane",
    "StadiumRoadMainTiltTransition2UpLeft":                 "RoadTechTiltTransition2UpLeft",
    "StadiumRoadMainTiltTransition2UpRight":                "RoadTechTiltTransition2UpRight",

    # TiltSwitch
    "StadiumRoadMainTiltSwitchLeft":                        "RoadTechTiltSwitchLeft",
    "StadiumRoadMainTiltSwitchRight":                       "RoadTechTiltSwitchRight",

    # Tilt
    "StadiumRoadMainCheckpointTiltLeft":                    "RoadTechCheckpointTiltLeft",
    "StadiumRoadMainCheckpointTiltRight":                   "RoadTechCheckpointTiltRight",
    "StadiumRoadMainChicaneX2TiltLeft":                     "RoadTechChicaneX2TiltLeft",
    "StadiumRoadMainChicaneX2TiltRight":                    "RoadTechChicaneX2TiltRight",
    "StadiumRoadMainChicaneX3TiltLeft":                     "RoadTechChicaneX3TiltLeft",
    "StadiumRoadMainChicaneX3TiltRight":                    "RoadTechChicaneX3TiltRight",
    "StadiumRoadMainSpecialBoost2TiltLeft":                 "RoadTechSpecialBoost2TiltLeft",
    "StadiumRoadMainSpecialBoost2TiltRight":                "RoadTechSpecialBoost2TiltRight",
    "StadiumRoadMainSpecialBoostTiltLeft":                  "RoadTechSpecialBoostTiltLeft",
    "StadiumRoadMainSpecialBoostTiltRight":                 "RoadTechSpecialBoostTiltRight",
    "StadiumRoadMainSpecialCruiseTilt":                     "RoadTechSpecialCruiseTilt",
    "StadiumRoadMainSpecialFragileTilt":                    "RoadTechSpecialFragileTilt",
    "StadiumRoadMainSpecialNoBrakeTilt":                    "RoadTechSpecialNoBrakeTilt",
    "StadiumRoadMainSpecialNoEngineTilt":                   "RoadTechSpecialNoEngineTilt",
    "StadiumRoadMainSpecialNoSteeringTilt":                 "RoadTechSpecialNoSteeringTilt",
    "StadiumRoadMainSpecialResetTilt":                      "RoadTechSpecialResetTilt",
    "StadiumRoadMainSpecialSlowMotionTilt":                 "RoadTechSpecialSlowMotionTilt",
    "StadiumRoadMainSpecialTurbo2TiltLeft":                 "RoadTechSpecialTurbo2TiltLeft",
    "StadiumRoadMainSpecialTurbo2TiltRight":                "RoadTechSpecialTurbo2TiltRight",
    "StadiumRoadMainSpecialTurboRouletteTiltLeft":          "RoadTechSpecialTurboRouletteTiltLeft",
    "StadiumRoadMainSpecialTurboRouletteTiltRight":         "RoadTechSpecialTurboRouletteTiltRight",
    "StadiumRoadMainSpecialTurboTiltLeft":                  "RoadTechSpecialTurboTiltLeft",
    "StadiumRoadMainSpecialTurboTiltRight":                 "RoadTechSpecialTurboTiltRight",
    "StadiumRoadMainTiltHole":                              "RoadTechTiltHole",
    "StadiumRoadMainTiltPenalty":                           "RoadTechTiltPenalty",

    # Wall
    "StadiumWallToRoadTech":                                "TrackWallToRoadTech",

    # Misc
    "StadiumRoadMainMultilap":                              "RoadTechMultilap",
    "StadiumRoadMainRampLow":                               "RoadTechRampLow",
}

# ─── Rotation Mapping ──────────────────────────────────────────────────────────
# JSON uses TMNF compass convention (rot index → car heading vector):
#   rot 0 = facing TMNF-N → car heads -z
#   rot 1 = facing TMNF-E → car heads +x
#   rot 2 = facing TMNF-S → car heads +z
#   rot 3 = facing TMNF-W → car heads -x
#
# TM2020 has flipped z-axis (verified from test_kurven.Map.Gbx where
# straight blocks heading +z all carry dir=North):
#   dir=North(0) = +z  | dir=East(1)  = +x
#   dir=South(2) = -z  | dir=West(3)  = -x
#
# So for straights/slopes/start/finish, JSON rot R → TM2020 dir
#   {2, 1, 0, 3}[R]   (mirror of Z, X stays, the only swap is N↔S).
#
# For 1×1 curves, the dir field encodes which TWO cell faces are open
# (entry and exit). Verified opening pairs from test_kurven curve cells:
#   dir=North → {W, N} | dir=East → {S, W}
#   dir=South → {S, E} | dir=West → {E, N}
#
# A "Right" curve in JSON = TMNF-right turn = (R+1)%4 new heading.
# A "Left"  curve in JSON = TMNF-left  turn = (R-1)%4 new heading.
# (TMNF-right is geometrically a TM2020-LEFT turn because the z-axis is flipped,
# but the openings calculation gives the same answer either way.)
#
# All three maps below are derived analytically AND verified by parsing
# test_kurven.Map.Gbx (8 curve cells, all match):
#   cell (16,23) East   cell (15,23) West   cell (15,24) South   cell (16,24) North
#   cell (16,26) South  cell (17,26) North  cell (17,27) East    cell (16,27) West

DIR_NAMES = ("North", "East", "South", "West")  # TM2020 dir int → name

# JSON rot (0..3) → TM2020 dir int (0..3)
STRAIGHT_DIR_MAP    = (2, 1, 0, 3)   # straights, start, finish, slopes, tilt, chicanes
CURVE_RIGHT_DIR_MAP = (3, 0, 1, 2)   # *Right / *In  curves (TMNF-right turn)
CURVE_LEFT_DIR_MAP  = (0, 1, 2, 3)   # *Left  / *Out curves (TMNF-left  turn)


# ─── Block construction ────────────────────────────────────────────────────────

def resolve_block(json_id: str) -> str:
    return BLOCK_MAP.get(json_id, json_id)


def is_waypoint_block(json_id: str) -> bool:
    return any(token in json_id for token in ("Start", "Finish", "Checkpoint"))


def tm2020_dir(json_id: str, json_rot: int) -> str:
    """Translate JSON rotation (0..3) to TM2020 dir name.

    Curve cells need a different map than straights because dir encodes
    *which two faces are open* (entry+exit), not heading direction.

    Detection: only true 1×1 corner curves get the curve maps. Block IDs
    must contain "Curve" AND end in Right/Left/In/Out. Everything else
    (chicanes, slopes, banks, straights, branches, tilt-transitions) uses
    the straight map. New IDs without R/L suffix fall through to straight,
    which is fine for non-corner blocks.
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
        rot = b.get("rotation", 0)

        is_down_slope = "Slope" in json_id and "Down" in json_id
        if is_down_slope:
            # Down slopes: the car enters at the HIGH end and exits LOW.
            # The block origin (y) is the LOW end; HIGH end = y+1 in the dir direction.
            # So dir must point toward HIGH = opposite of travel direction.
            # json_y in the JSON is the entry (high) road surface → TM2020 y = json_y - 1 + Y_OFFSET.
            raw_dir = STRAIGHT_DIR_MAP[rot & 3]
            dir_name = DIR_NAMES[(raw_dir + 2) % 4]
            tm2020_y = (json_y - 1) + Y_OFFSET
            is_ground_val = (json_y - 1 == GROUND_Y_JSON)
        else:
            dir_name = tm2020_dir(json_id, rot)
            tm2020_y = json_y + Y_OFFSET
            is_ground_val = (json_y == GROUND_Y_JSON)

        inst = make_block(
            name=real,
            x=b["x"], y=tm2020_y, z=b["z"],
            dir_name=dir_name,
            is_waypoint=is_wp,
            is_ground=is_ground_val,
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
