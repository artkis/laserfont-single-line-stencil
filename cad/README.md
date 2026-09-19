# laserfont2 for AutoCAD

The separate `laserfont2.shx` font supports editable lettering. The standalone
`LASER2.lsp` generates permanent open cutting geometry from the original design.
Existing `laserfont` and `LASEROUT` files are not replaced.

## Create permanent lettering

1. Save a copy of the drawing.
2. Use `APPLOAD` to load `LASER2.lsp`.
3. Run `LASER2`, enter the ID, choose the height (default 20 drawing units), pick
   its left baseline insertion point, and choose a rotation (default 0).

Supported characters are A-Z, digits, hyphen, and space. Lowercase input uses the
uppercase shapes. In a millimetre drawing, the default actual cap height is 20 mm.
The routine does not change drawing units or scale the surrounding drawing.

The result is one open cubic `SPLINE` per connected curved/mixed path or one
`LINE` for a single straight path. It does not require a font on the laser PC.
One `UNDO` restores the command's changes.

## Convert editable laserfont2 text

Place `laserfont2.shx` in an AutoCAD font/support search folder, create a text
style using that file, and use normal AutoCAD text tools. Load `LASER2.lsp`, then
run `LASEROUT2` and select the IDs to replace with exact Bezier/line geometry.

The converter accepts left-baseline TEXT and plain single-line MTEXT. It
preserves position, rotation, height, layer and applicable appearance values.
Unsupported formatted, wrapped, mirrored, scaled-width, oblique, elevated or
locked-layer objects are skipped and retained. The original label is removed
only after all its new paths have been created successfully.

## Convert text to circular-arc polylines

Run `LASERPOLY2` and select eligible laserfont2 TEXT/MTEXT. This outputs one open,
zero-width `LWPOLYLINE` per connected stroke, using actual circular-arc bulges
and straight spans. It keeps the stencil gaps. It does not use `TXTEXP` or a
chain of tiny straight facets.

This route is a fitted approximation of the original Beziers, not an exact
Bezier representation. The supplied fit has a maximum sampled deviation of
0.01184 mm at cap height 20; the acceptance target is 0.02 mm at that height.
Deviation scales in proportion to text height. `LASEROUT2` remains available
when exact cubic SPLINE geometry is wanted. One `UNDO` restores a converted batch.

## Display versus cutting geometry

SHX cannot encode cubic Beziers natively. `laserfont2.shx` therefore uses a
controlled display approximation. Its conservative deviation bound is 0.0111 mm
at height 20, scaling with height. Do not use `TXTEXP` to derive cutting paths
from this display font. `LASER2` and `LASEROUT2` instead use the embedded original
Bezier controls, with no display tessellation.

The font has intentional stencil gaps. Do not join across gaps, close paths, or
apply closed-outline kerf offsets to this single-line lettering. Confirm the
actual CAM import retains the intended open paths and curve motion before
production. Native AutoCAD geometry tests are not a CypCut or machine test.

## Rebuild

`build_cad.py` uses the parent `glyphs-v2.json`, optional fitted
`glyphs-v2-polyline.json`, and the adjacent `runtime.lsp` to write the standalone
LISP and SHP source. Compile `laserfont2.shp` with AutoCAD's `COMPILE` command.
Python 3 and an AutoCAD installation with the COMPILE command are required to
rebuild. The delivered LISP runs without Python or external glyph files.

## License

Copyright (c) 2026 Artkis. The font designs, glyph data and SHP/SHX font are
licensed under the SIL Open Font License 1.1 (`OFL.txt` in the release root).
The builder and AutoLISP utility code are licensed under MIT (`LICENSE-MIT.txt` in the
release root). `LASER2.lsp` includes both: its marked embedded font-data section
is OFL-1.1, and its utility runtime is MIT. Keep both license notices when
redistributing that combined file.
