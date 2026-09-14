#!/usr/bin/env python3
"""
TM2020 Track Converter — JSON → .Map.Gbx (direkt, kein Umweg über TMNF).

Nutzt das vendored gbx-py (converter/gbxpy/) zum Lesen eines TM2020-Map-Templates,
ersetzt die Block-Liste mit den JSON-Daten und schreibt eine fertige .Map.Gbx.

Beispiele
---------
    python converter/build.py tracks/speedtech/proofcut/proofcut.json
    python converter/build.py tracks/speedtech/proofcut/proofcut.json --dry-run
    python converter/build.py tracks/ --batch
    python converter/build.py track.json --no-deploy
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

# Vendored gbx-py liegt neben diesem Skript
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from construct import Container  # noqa: E402
from gbxpy import parse_file, parse_bytes, generate_file  # noqa: E402

sys.path.insert(0, str(ROOT.parent))
from track_lib.blocks import BLOCK_SPECS  # noqa: E402
from track_lib.files import atomic_write  # noqa: E402
from track_lib.validator import GRID_SIZE, validate  # noqa: E402

# ─── Konfiguration ─────────────────────────────────────────────────────────────

TEMPLATE = ROOT / "template.Map.Gbx"

TM2020_MAP_DIRS = [
    Path.home() / "Documents" / "Trackmania" / "Maps" / "My Maps",
]
if os.environ.get('OneDrive'):
    TM2020_MAP_DIRS.append(Path(os.environ['OneDrive']) / 'Documents' / 'Trackmania' / 'Maps' / 'My Maps')

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
# Historical name/geometry observations recorded before this refresh:
#   • template.Map.Gbx           → RoadTechStart, RoadTechFinish
#   • every platform block.Gbx   → vollständiger RoadTech-Katalog (148 Namen)
#   • jantronix wurst.Gbx        → RoadBump*-Set, zeigt Footprint-Verhalten:
#       RoadBumpCurve1            = 1×1 Zelle  (Slalom: dir wechselt jede Zelle)
#       RoadBumpCurve2            = 2×2 Zellen (Platzierung 2 Zellen versetzt)
#       RoadBumpSlopeBase         = +1 y pro Zelle in Fahrtrichtung
#       RoadBumpSlopeBase2        = +2 y pro Zelle (steiler)
#
# This dictionary records name aliases, not proof of usable geometry.
# PLACEHOLDER_IDS are blocked by resolve_block(). The validator accepts only
# the explicitly modelled single-cell vocabulary in track_lib/blocks.py.
# Multi-cell names stay here for future reference-map calibration.

BLOCK_MAP: dict[str, str] = {
    # Start / Finish / Checkpoint
    "StadiumRoadMainStart":          "RoadTechStart",
    "StadiumRoadMainFinish":         "RoadTechFinish",
    "StadiumRoadMainCheckpointIn":   "RoadTechCheckpoint",
    "Checkpoint":                    "RoadTechCheckpoint",

    # Straight
    "StadiumRoadMainStraight":       "RoadTechStraight",

    # Curve1 is supported; the historical Curve2-5 aliases below are BLOCKED.
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

    # Historical plain chicane placeholders are BLOCKED. X2/X3 have real names
    # but still need connector metadata before the validator can accept them.
    "StadiumRoadMainChicaneRight":   "RoadTechStraight",
    "StadiumRoadMainChicaneLeft":    "RoadTechStraight",
    "StadiumRoadMainChicaneX2Right": "RoadTechChicaneX2Right",
    "StadiumRoadMainChicaneX2Left":  "RoadTechChicaneX2Left",
    "StadiumRoadMainChicaneX3Right": "RoadTechChicaneX3Right",
    "StadiumRoadMainChicaneX3Left":  "RoadTechChicaneX3Left",

    # Banking: historical straight substitutions are BLOCKED; tilt geometry is not modelled.
    "StadiumRoadMainBankRight":      "RoadTechStraight",
    "StadiumRoadMainBankLeft":       "RoadTechStraight",
    "StadiumRoadMainTiltStraight":   "RoadTechTiltStraight",

    # Provisional one-level slopes; misleading Slope2 substitutions are BLOCKED.
    "StadiumRoadMainSlope1Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope1Down":     "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Up":       "RoadTechSlopeBase",
    "StadiumRoadMainSlope2Down":     "RoadTechSlopeBase",

    # Special names: historical dirt/ice/narrow straight substitutions are BLOCKED.
    "StadiumRoadMainHole":           "RoadTechHole",
    "StadiumRoadMainPenalty":        "RoadTechPenalty",
    "StadiumRoadMainPenaltyDirt":    "RoadTechStraight",
    "StadiumRoadMainPenaltyIce":     "RoadTechStraight",
    "StadiumRoadMainTurbo":          "RoadTechSpecialTurbo",
    "StadiumRoadMainNarrowCenter":   "RoadTechStraight",
    "StadiumRoadMainNarrowSide":     "RoadTechStraight",

    # Historical wall-to-straight substitutions are BLOCKED.
    "StadiumRoadMainWallLeft":       "RoadTechStraight",
    "StadiumRoadMainWallRight":      "RoadTechStraight",

    # Catalog-backed name aliases (191 PNGs); NOT verified connector geometry.

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
STRAIGHT_DIR_MAP    = (2, 1, 0, 3)   # straight/checkpoint; Start/Finish add 180 degrees
CURVE_RIGHT_DIR_MAP = (3, 0, 1, 2)   # *Right / *In  curves (TMNF-right turn)
CURVE_LEFT_DIR_MAP  = (0, 1, 2, 3)   # *Left  / *Out curves (TMNF-left  turn)


# ─── Block construction ────────────────────────────────────────────────────────

PLACEHOLDER_IDS = {
    "StadiumRoadMainChicaneRight", "StadiumRoadMainChicaneLeft",
    "StadiumRoadMainBankRight", "StadiumRoadMainBankLeft",
    "StadiumRoadMainWallLeft", "StadiumRoadMainWallRight",
    "StadiumRoadMainNarrowCenter", "StadiumRoadMainNarrowSide",
    "StadiumRoadMainPenaltyDirt", "StadiumRoadMainPenaltyIce",
    "StadiumRoadMainCurve2Right", "StadiumRoadMainCurve2Left",
    "StadiumRoadMainCurve2In", "StadiumRoadMainCurve2Out",
    "StadiumRoadMainCurve3Right", "StadiumRoadMainCurve3Left",
    "StadiumRoadMainCurve4Right", "StadiumRoadMainCurve4Left",
    "StadiumRoadMainCurve5Right", "StadiumRoadMainCurve5Left",
    "StadiumRoadMainSlope2Up", "StadiumRoadMainSlope2Down",
}


def resolve_block(json_id: str) -> str:
    if json_id in PLACEHOLDER_IDS:
        raise ValueError(
            f"{json_id!r} maps to a placeholder block - built geometry "
            f"would differ from the design. Refusing to build. Use a "
            f"verified block or add a real, tested mapping.")
    if json_id not in BLOCK_MAP:
        raise ValueError(f"{json_id!r} is not in BLOCK_MAP. Refusing to guess.")
    return BLOCK_MAP[json_id]


def is_waypoint_block(json_id: str) -> bool:
    return any(token in json_id for token in ("Start", "Finish", "Checkpoint"))


def tm2020_dir(json_id: str, json_rot: int) -> str:
    """Map a supported single-cell travel heading to GBX orientation.

    Start/Finish use a 180-degree flip; Checkpoint follows the straight map.
    Curves encode open faces. Down slopes are handled by build().
    """
    if type(json_rot) is not int or json_rot not in range(4):
        raise ValueError('rotation must be an integer from 0 to 3')
    rot = json_rot
    # 1. Preserve the Start/Finish correction recorded in June 2026.
    if is_waypoint_block(json_id):
        base = STRAIGHT_DIR_MAP[rot]
        if "Start" in json_id or "Finish" in json_id:
            return DIR_NAMES[(base + 2) % 4]
        return DIR_NAMES[base]
    # 2. True corner curves: pick the curve map by Right/Left/In/Out suffix.
    if "Curve" in json_id:
        if json_id.endswith("Right") or json_id.endswith("In"):
            return DIR_NAMES[CURVE_RIGHT_DIR_MAP[rot]]
        if json_id.endswith("Left") or json_id.endswith("Out"):
            return DIR_NAMES[CURVE_LEFT_DIR_MAP[rot]]
    # 3. Everything else: face the driving direction.
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


# Build and CLI

def header_chunk(data, chunk_id):
    for entry, chunk in zip(data.header.entries, data.header.data):
        if entry.id == chunk_id:
            return chunk
    return None


def close_map(data) -> None:
    embedded = data.body.get(0x03043054)
    if embedded and embedded.get('embeddedData'):
        embedded.embeddedData.zip.close()


def track_uid(track: dict) -> str:
    # Stable for the same named layout; changes when the actual geometry changes.
    identity = {key: track[key] for key in ('settings', 'blocks', 'checkpoints')}
    identity['name'] = track['meta']['name']
    identity['author'] = track['meta']['author']
    raw = json.dumps(identity, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest()[:20]).decode('ascii').rstrip('=')


def update_map_metadata(data, track: dict) -> str:
    name, uid = track['meta']['name'], track_uid(track)
    body = find_blocks_chunk(data)
    header = header_chunk(data, 0x03043003)
    if header is None:
        raise ValueError('template is missing the map-info header')
    for chunk in (body, header):
        chunk.mapName = name
        chunk.mapInfo.id = uid
    # Keep the template's real game-account author. A GitHub login is not a
    # Trackmania account ID. meta.author participates only in the project UID.
    xml_chunk = header_chunk(data, 0x03043005)
    if xml_chunk is not None:
        xml = ET.fromstring(xml_chunk.xml)
        ident = xml.find('ident')
        if ident is None:
            raise ValueError('template XML has no ident element')
        ident.set('name', name)
        ident.set('uid', uid)
        desc = xml.find('desc')
        if desc is not None:
            desc.set('validated', '0')
        xml_chunk.xml = ET.tostring(xml, encoding='unicode')
    # GBX.NET CGameCtnChallenge.ComputeCrc32: hash bytes as uppercase hex + UID.
    password = data.body.get(0x03043029)
    if password is not None:
        password_hex = int(password.passwordHash).to_bytes(16, 'little').hex().upper()
        password.crc32 = zlib.crc32(f'0x{password_hex}???{uid}'.encode('ascii'))
    return uid


def block_signature(block):
    return (block.name, block.coords.x, block.coords.y, block.coords.z,
            str(block.dir), block.flags.isWaypoint, block.flags.isGround)


def build(json_path: Path, deploy: bool = True, dry_run: bool = False,
          force: bool = False, *, allow_unverified: bool = False,
          maps_dir: Path | None = None, output_dir: Path | None = None) -> Path | None:
    if force:
        raise ValueError('--force no longer bypasses invalid geometry; use --allow-unverified only for modelled slopes')
    json_path = Path(json_path)
    track = json.loads(json_path.read_text(encoding='utf-8'))
    if isinstance(track, dict) and 'path' in track and 'blocks' not in track:
        raise ValueError('design input: run compose.py first')
    problems = validate(track, allow_unverified=allow_unverified)
    if problems:
        raise ValueError('validation failed:\n' + '\n'.join(problems))
    name = track['meta']['name']
    print(f'{name}: {len(track["blocks"])} blocks, {len(track["checkpoints"])} checkpoints')
    block_instances = []
    warned = set()
    for block in track['blocks']:
        block_id = block['id']
        spec = BLOCK_SPECS[block_id]
        if not spec['verified'] and block_id not in warned:
            print(f'WARNING: {block_id} is UNVERIFIED in-game')
            warned.add(block_id)
        down = spec['kind'] == 'slope_down'
        low_y = block['y'] - int(down)
        rotation = block['rotation']
        direction = (DIR_NAMES[(STRAIGHT_DIR_MAP[rotation] + 2) % 4] if down
                     else tm2020_dir(block_id, rotation))
        block_instances.append(make_block(
            name=resolve_block(block_id), x=block['x'], y=low_y + Y_OFFSET,
            z=block['z'], dir_name=direction, is_waypoint=spec['waypoint'],
            is_ground=low_y == GROUND_Y_JSON,
        ))
    if dry_run:
        for i, inst in enumerate(block_instances):
            print(f'[{i:3d}] {inst.name:30s} ({inst.coords.x},{inst.coords.y},{inst.coords.z}) {inst.dir}')
        return None
    if not TEMPLATE.is_file():
        raise ValueError(f'missing template: {TEMPLATE}; see converter/setup.md')
    destination = Path(maps_dir) if maps_dir else find_tm2020_maps_dir()
    if deploy and maps_dir and not destination.is_dir():
        raise ValueError(f'maps directory does not exist: {destination}')
    data = parse_file(str(TEMPLATE), recursive=False)
    try:
        if data.get('_errors'):
            raise ValueError(f'template parse errors: {data._errors}')
        chunk = find_blocks_chunk(data)
        if chunk is None:
            raise ValueError('template has no block chunk')
        if tuple(chunk.size[key] for key in ('x', 'y', 'z')) != GRID_SIZE:
            raise ValueError('template size differs from the supported 48 x 40 x 48 grid')
        if chunk.decoration.id != '48x48Screen155Day':
            raise ValueError('template decoration differs from the supported Stadium / Day template')
        chunk.Blocks = block_instances
        uid = update_map_metadata(data, track)
        strip_block_dependent_chunks(data)
        raw = generate_file(data)
        check = parse_bytes(raw, recursive=False)
        try:
            if check.get('_errors'):
                raise ValueError(f'generated GBX parse errors: {check._errors}')
            if [block_signature(b) for b in find_blocks_chunk(check).Blocks] != [block_signature(b) for b in block_instances]:
                raise ValueError('generated GBX block round-trip mismatch')
            if header_chunk(check, 0x03043003).mapInfo.id != uid:
                raise ValueError('generated GBX UID mismatch')
        finally:
            close_map(check)
    finally:
        close_map(data)
    out_path = (Path(output_dir) if output_dir else json_path.parent) / f'{name}.Map.Gbx'
    atomic_write(out_path, raw)
    print(f'Built {out_path} (UID {uid}); in-game validation still required')
    if deploy:
        if destination:
            dest = destination / out_path.name
            if dest.resolve() != out_path.resolve():
                atomic_write(dest, raw)
            print(f'Copied to {dest}')
        else:
            print('Trackmania Maps folder not found; copy manually or use --maps-dir.')
    return out_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='TM2020 JSON to GBX converter')
    parser.add_argument('input', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='validate and print blocks without writing')
    parser.add_argument('--no-deploy', action='store_true')
    parser.add_argument('--maps-dir', type=Path, help='explicit Trackmania Maps folder (e.g. OneDrive or WSL)')
    parser.add_argument('--output-dir', type=Path, help='write GBX files here instead of next to the input')
    parser.add_argument('--batch', action='store_true', help='build low-level JSON files, excluding *.design.json')
    parser.add_argument('--allow-unverified', action='store_true', help='allow modelled slopes for calibration')
    parser.add_argument('--force', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.input.exists() or (args.batch and not args.input.is_dir()) or (not args.batch and not args.input.is_file()):
        print(f'ERROR: input must be an existing {"directory" if args.batch else "file"}: {args.input}', file=sys.stderr)
        return 1
    files = (sorted(f for f in args.input.rglob('*.json') if not f.name.endswith('.design.json'))
             if args.batch else [args.input])
    if not files:
        print('ERROR: no track JSON files found', file=sys.stderr)
        return 1
    failed = 0
    outputs = set()
    for path in files:
        try:
            # Two tracks with the same name must not silently overwrite each other
            # when using a shared output/deploy folder in batch mode.
            track = json.loads(path.read_text(encoding='utf-8'))
            name = track.get('meta', {}).get('name') if isinstance(track, dict) else None
            destination = args.output_dir or path.parent
            key = (str(destination.resolve()), str(name).casefold())
            deploy_key = ('deploy', str(name).casefold())
            if key in outputs or (not args.no_deploy and deploy_key in outputs):
                raise ValueError(f'duplicate output map name: {name}')
            build(path, deploy=not args.no_deploy, dry_run=args.dry_run,
                  force=args.force, allow_unverified=args.allow_unverified,
                  maps_dir=args.maps_dir, output_dir=args.output_dir)
            outputs.update((key, deploy_key))
        except Exception as exc:
            print(f'ERROR: {path}: {exc}', file=sys.stderr)
            failed += 1
    if args.batch:
        print(f'Batch: {len(files) - failed} ok, {failed} failed; design files excluded')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
