# Vendored parser notes

Source: [schadocalex/gbx-py](https://github.com/schadocalex/gbx-py), vendored before
this refresh. The repository does not record an exact upstream revision for the
original copy. No wholesale parser upgrade was performed.

## 2026-09-14: independent embedded ZIP buffers

`ACompressedZip` stored the most recently parsed ZIP buffer on its shared
Construct adapter. Parsing A, then B, then serializing A could write B's ZIP
bytes into A. Opening the ZIP in append mode also caused destructor warnings
when buffers were replaced.

The adapter now opens each archive from its own `BytesIO` in read mode and
serializes that archive's buffer. Embedded-archive editing is outside the current
converter workflow. The converter closes these handles after use.
Regression: `test_embedded_zip_buffers_are_per_map` in `tests/test_pipeline.py`.

For map UID/CRC handling in the first-party converter, the formula was checked
against [GBX.NET CGameCtnChallenge.ComputeCrc32](https://github.com/BigBang1112/gbx-net/blob/master/Src/GBX.NET/Engines/Game/CGameCtnChallenge.cs)
and reproduced the bundled template's existing CRC before applying it to new IDs.
