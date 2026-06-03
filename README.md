# 🏎️ TM2020 Claude Tracks

AI-designed TM2020 tracks. Claude (chat) designs at the **path level**; a
connector-composer expands that into exact block coordinates; the converter
writes a spielfertige `.Map.Gbx`. No block is placed by hand.

## Pipeline

```
Claude chat            high-level design (segments, no coordinates)
   ↓  design.json
compose.py             walks connectors → exact x/y/z/dir   (track_lib/)
   ↓  track.json       (tools/track_schema.json compliant)
   ↓  validate()       connectivity + overlap + waypoint check
converter/build.py     track.json → .Map.Gbx                (gbx-py)
   ↓
TM2020 Maps folder  +  git commit
```

Two independent safety nets:
- **composer** makes coordinates correct by construction (no hand-walked grid math).
- **build.py fail-loud**: any block id without a real, verified mapping aborts the
  build instead of silently substituting a straight. (This is what corrupted
  ~half of the first track, `silvercut`.)

## Authoring a track (design level)

```json
{
  "meta": {"name": "Proofcut", "category": "speedtech", "difficulty": 2},
  "settings": {"environment": "Stadium", "mood": "Day"},
  "origin": {"x": 16, "y": 1, "z": 20, "heading": 1},
  "path": [
    {"seg": "start"}, {"seg": "straight", "count": 4}, {"seg": "curve_right"},
    {"seg": "checkpoint"}, {"seg": "curve_right"}, {"seg": "finish"}
  ]
}
```

```
py -3.12 compose.py design.json track.json
py -3.12 converter/build.py track.json
```

## Verified segment vocabulary

`start, straight, checkpoint, finish, curve_right, slope_up, slope_down`
(all verified against a real map). `curve_left` exists but is **unverified** —
the composer warns when used. Multi-cell blocks (Curve2–5, real chicanes,
PlatformTech for Kacky) are NOT yet in the vocabulary: they need footprint +
connector data extracted from a reference map first.

## Layout

```
track_lib/          design-side layer
  blocks.py         segment metadata: footprint + cursor advance
  composer.py       design → connected schema JSON
  validator.py      connectivity / overlap / waypoint checks
compose.py          CLI: design.json → track.json (+validate)
converter/
  build.py          track.json → .Map.Gbx (fail-loud block resolution)
  gbxpy/            vendored gbx-py (schadocalex)
  template.Map.Gbx
tools/track_schema.json
tracks/{category}/{name}/
```
