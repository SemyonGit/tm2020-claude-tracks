# Ghost sample bytes: what we know (issue #13)

TM2020 ghosts store a `CSceneVehicleVis` sample every 50 ms. GBX.NET 2.4.5 decodes position,
rotation, velocity, speed, inputs, gear, rpm, per-wheel material/dampers, and exposes the
raw bytes below. Evidence comes from the official Kacky corpus (3,690 top-5 ghosts), by
matching samples to the block under the car (`tools/physics/jumps.py:block_under`).

## `isTurbo` byte (CSV column `turbo`)

Values seen: 0, 2, 3, 5, 130, 131, 133. Bits 0x08–0x40 never set.

| Bit | Meaning | Status | Evidence |
|---|---|---|---|
| **0x80** | **turbo active** | ✅ confirmed | Set on ≈97% of ground samples on `*SpecialTurbo` blocks, ≈87% on `*SpecialTurbo2`, ≈7% elsewhere (turbo outlasts the pad) |
| 0x04 | sliding / drifting? | 🟡 hypothesis | 6.6% of samples; mean brake 0.38 vs 0.05, \|steer\| 0.69 vs 0.39, higher speed |
| 0x02 | normal grip? | 🟡 hypothesis | 89% of samples; never set together with 0x04; absent at low speed (median 89 vs 205 km/h) and under heavy braking |
| 0x01 | unknown | ❓ | 69% of samples; only weak correlation with gas (0.90 vs 0.78) and speed |

GBX.NET's own `IsTurbo` uses mask `0x82` and therefore reports turbo on ~90% of all samples.
Use `turbo & 0x80` instead.

## `groundMode` byte (CSV column `gmode`)

Decoded by GBX.NET (`CSceneVehicleVis.EntRecordDelta`):

| Bit | Meaning |
|---|---|
| 0x01 | wheels in ground contact (`IsGroundContact`) |
| 0x04 | reactor ground mode |
| 0x08 / 0x10 | reactor up / down |
| 0x20 / 0x40 | reactor boost level 1 / 2 |

Reactor bits (`& 0x7C`) are set on 5.7% of airborne Kacky samples and 3.9% of TMX samples;
those samples are excluded from the free-flight fit.

## Other notes

- `simulationTimeCoef` (`sim_coef`): 255 = normal speed; other values = slow-motion.
- Per-wheel material keeps its last value while airborne. Don't use it to detect flight.
- `PlayerModel` is empty on 2020–2022 ghosts (only CarSport existed then).
- Material index → name: `tools/physics/materials.py` (from GBX.NET `CPlugSurface.chunkl`).

## Open
- Confirm 0x02/0x04 against per-wheel slip (`SlipCoef` bits are in the sample, not exported yet).
- Meaning of 0x01.
- Water, fragile, no-steering, cruise-control states: not seen in these bytes yet.
