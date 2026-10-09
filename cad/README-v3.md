# LaserFont for AutoCAD — 3.0.4, 9 October 2026

Use **LASEROUT** to convert ordinary editable IDs into open cutting polylines
with one simple orientation arrow. **LASERFONT** sets up the text style and default
height. These are the two commands registered by the installer; LASEROUT is
the only conversion command.

## Install

Extract the complete release and run `cad/Install-LaserFont3.ps1` in PowerShell.
Use `-WhatIf` first to inspect its destinations. The installer adds the compiled
`laserfont3.shx`, LISP runtime and loader to the current user's AutoCAD 2023
Support folder and LASEROUT application bundle. It verifies backups and
installed file hashes, preserves the bundle's ProductCode and leaves older
SHX fonts intact.

Restart AutoCAD to use the updated bundle, or `APPLOAD` the installed
`LASEROUT.lsp` to refresh commands in an open drawing. The installer itself
does not send commands to AutoCAD, alter drawings or change registry security
settings or the Startup Suite.

## Type and convert an ID

1. Run `LASERFONT` to select the LaserFont3 text style and default height **5**.
2. Use normal AutoCAD `TEXT` or plain one-line `MTEXT` and type an ID such as
   `H3` or `I3`. No special insertion command or prefix is required.
3. Run `LASEROUT` and select the text.

The result contains fitted circular-arc/line `LWPOLYLINE` glyphs and one arrow.
Its stem and chevron are two open, zero-width paths, with no closed hole.
All paths are separate entities; `LASEROUT` creates no AutoCAD group.
No `UNGROUP` step is needed after conversion.
The cutting geometry needs no installed font on the receiving machine.

**Confirm conversion:** read the final command-line summary for the number of
text objects converted and skipped. Skipped labels remain editable text; the
command prints each reason above the summary. For a successful label, select
one path: it selects independently, and the Properties palette shows
**Polyline**, not Text or MText. Appearance alone is not the conversion check.

The default is **5 drawing units**, or 5 mm in a millimetre drawing. Conversion
preserves the selected label's existing height: a **2.5 mm label remains
2.5 mm**. Selecting the setup default does not resize existing text or the
drawing.

The converter accepts eligible text using `laserfont.shx`, `laserfont2.shx` or
`laserfont3.shx`. Bare text keeps its character baseline, height, rotation,
layer and applicable appearance properties. The arrow extends 0.9 times the
cap height to the left along the local baseline: 4.5 mm at height 5 or 2.25 mm
at height 2.5. Check that this space is inside the part and clear of cuts and
bends.

LaserFont3 text that already begins with one `~`, such as `~H3`, is also
accepted. The font displays this prefix as the arrow. Conversion preserves that
symbol baseline and creates one arrow, without shifting the characters
again. Doubled or embedded prefixes are rejected. The prefix is not part of
the ID.

SHX is a display approximation. Use `LASEROUT` for the cutting paths; do not
use `TXTEXP` or close the open stencil gaps.

## Read and move the complete label

On the intended outside face, **the arrow comes before the ID and points
toward the top of the readable lettering**: ↑ H3. It rotates with the label
and does not specify the assembly's global up direction.

At height 5, the arrow is 5 mm tall and 3 mm wide, with a 1.5 mm gap before
the character origin. All dimensions scale with the label height. The plain
arrow alone has mirror symmetry; read its position and direction together
with the ID when checking the viewing face.

The tool cannot determine which face of a part is outside. Place the label
from a verified outside-face view of the finished assembly. A readable label
on the wrong face still indicates a placement error.

Select the individual paths directly. When moving or rotating a complete
label, include its arrow and all character paths. This ungrouped output applies
to AutoCAD `LASEROUT`; the separate Python DXF exporter still creates groups.

## Supported input and Undo

Unsupported characters or formatting, wrapped or multiple-line MTEXT,
mirrored, oblique, width-scaled, elevated, non-WCS-XY, thick or locked-layer
text is skipped and retained. Bigfonts, vertical styles, MTEXT columns,
background masks and unsupported attachments are rejected.

For supported MTEXT, a temporary ordinary `EXPLODE` resolves the native TEXT
baseline. The original remains if that step fails. `TXTEXP` is never used.

Both arrow paths and all glyph paths must succeed before conversion commits. A
failure removes the current label's new geometry and retains its original
text. Cancellation follows the same rule. One `U`/`UNDO` reverses a completed
conversion batch and restores the original text.

The isolated native test harness disables automatic script-level Undo
grouping before checking routine-level Undo. The delivered routine does not
change the user's Undo settings.

## Verification

See [the native report](native-test-report-v3.json) for the tested version,
source hashes, command cases and saved-drawing checks. Results for an earlier
build do not verify a later command change. The Python geometry tests cover
glyph preservation, the arrow-and-ID arrangement, reflections and DXF reopening.

CAM import, physical cutting, kerf, piercing and human recognition require
separate checks. The mark does not establish assembly handedness or physical
readability. Use a saved drawing copy when checking conversion, individual path selection,
skipped input, cancellation and Undo with the intended text and UCS.

## Source and license

Run `python cad/build_cad3.py` from the repository root to rebuild
`cad/LASER3.lsp`. Run it with `--check` for byte-for-byte reproducibility.
The versioned filename identifies the implementation; it is not an insertion
command. The runtime includes its glyph and arrow data and needs no Python or
JSON files at runtime. Previous-version source files remain archival.

Copyright (c) 2026 Artkis. Glyph and orientation-arrow designs, data and SHP/SHX
fonts remain [OFL-1.1](../OFL.txt). The installer, runtime, builders and this
documentation use [MIT](../LICENSE-MIT.txt). Distribute both licenses with
the combined runtime.

Autodesk documents that [scripts form their own Undo group](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Customization/files/GUID-95BB6824-0700-4019-9672-E6B502659E9E.htm)
and recommends [Begin/End for routine-level Undo](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-AutoLISP/files/GUID-4481039B-77DA-4500-AE8B-3D2AD6951115.htm).
