# LaserFont3 orientation labels for AutoCAD

`LASER3.lsp` adds a required orientation key before each ID while retaining the
original laserfont2 glyphs. It defines separate `LASER3`, `LASEROUT3` and
`LASERPOLY3` commands. Existing v2 files and commands are unchanged.

On the intended outside face, the key comes before the ID: **long arm left,
base below, short arm right**. The small bevel belongs at the lower left. This
cue also works with IDs whose letters and digits alone can look plausible
from the back. The tool cannot determine which face of a part is outside;
the label must be placed in a verified outside-face view.

## Create a new label

1. Save a copy of the drawing and `APPLOAD` the supplied `LASER3.lsp`.
2. Run `LASER3` and enter the ID (A-Z, 0-9, hyphen and spaces).
3. Choose the cap height, default **5 drawing units**.
4. Pick the **left baseline of the key**, then choose a rotation.

In a millimetre drawing at height 5, the key is 5 mm tall and 3 mm wide. The
text origin is 4.5 mm to the right of the insertion point, leaving a 1.5 mm
gap from the key's rightmost point to the text origin. Drawing units are not
changed. Initial spaces in an ID add their normal spacing after that origin.

The key is exactly one open, zero-width `LWPOLYLINE`, with five vertices and
straight spans. Glyphs are permanent open `LINE` or exact cubic `SPLINE`
geometry. The command does not require a font installed on the cutting PC.
There is no option to omit the key.

## Convert existing editable text

Use `LASEROUT3` for original Bezier/line glyph geometry or `LASERPOLY3` for the
existing fitted circular-arc/line glyph geometry. Select eligible TEXT or plain
single-line MTEXT using **laserfont2.shx**. There is no new SHX display font.

Conversions preserve the existing glyph baseline, height, rotation, layer and
applicable appearance values. The required key extends **4.5 mm left of the
old text origin at height 5** (0.9 times cap height at other sizes), measured
along the label's local baseline. Check that space before conversion. The key
does not move the existing glyphs or other drawing geometry.

All v2 conversion restrictions remain: unsupported characters/formatting,
wrapped or multiple-line MTEXT, mirrored, oblique, width-scaled, elevated,
non-WCS-XY, thick or locked-layer text is skipped. Bigfonts, vertical styles,
MTEXT columns, background masks and unsupported attachments are rejected.
MTEXT uses a temporary ordinary `EXPLODE` to resolve its native baseline; the
source is retained if that resolution fails. `TXTEXP` is never used.

## Keep the key and ID together

Each completed label is an AutoCAD `GROUP` named from its key entity handle.
Group selection must be enabled (`PICKSTYLE` 1 or 3) when moving labels; the
routine does not change this setting. Grouping is a selection aid, not a lock:
ungrouping or editing a member can separate the cue from the ID. Move, rotate
and copy the complete label. Do not mirror it independently of its part.

The key, glyphs and group must all succeed before a label commits. A failure
removes that label's newly created geometry and retains its original text.
Commands request one Undo group for a manual insertion or converted batch.
The isolated Core Console test did not verify one-step Undo: it reported an
open group at the script-level `U` command. Check Undo in a saved drawing copy;
do not assume this behavior is qualified. Grouping uses the native
`ACAD_GROUP` dictionary and does not require an ActiveX application object.

## Verification limits

The v3 build has deterministic source checks and unchanged v2 glyph tables.
Isolated **AutoCAD Core Console 2023** tests cover native H3/I3 geometry,
5-unit keys, rotation, exact and fitted TEXT conversions, group membership,
and rollback after injected group/glyph failures. The manual `LASER3` command
also accepts its default height of 5. See
[the v3 native report](native-test-report-v3.json) for the recorded results and
limits. The Undo test remains unresolved; v2 reports do not qualify v3.

Verify a saved drawing copy before production: insertion and conversion at
height 5 and a rotated angle; key/ID grouping; skipped input retention;
cancel/UNDO behavior; WCS/MTEXT handling; and actual CAM import of the open
key and glyph paths. Inspect the outside-face view and its back-face mirror.
The key is a visual orientation cue, not proof of assembly handedness or
machine readability. Do not close the key or join across stencil gaps.

## Rebuild and license

Run `python cad/build_cad3.py` from the repository root. Only `cad/LASER3.lsp`
is written. Run `python cad/build_cad3.py --check` for a read-only byte-for-byte
reproducibility check. The generated file contains both exact and fitted v2
glyph tables and the geometry from `orientation-key.json`; it needs no JSON
or Python installation at runtime.

Copyright (c) 2026 Artkis. Embedded glyph and orientation-key designs/data
remain [OFL-1.1](../OFL.txt); the builder, runtime and this documentation use
[MIT](../LICENSE-MIT.txt). Distribute both license files with `LASER3.lsp`.

The grouping implementation uses Autodesk's documented
[GROUP DXF data](https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DXF/files/GUID-5F1372C4-37C8-4056-9303-EE1715F58E67.htm)
in the named `ACAD_GROUP` dictionary.
