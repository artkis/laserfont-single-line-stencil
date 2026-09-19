# LaserFont — Single-Line Stencil Font for Laser Cutting & CNC

LaserFont is an original single-line stencil font for small part IDs cut directly into sheet metal. Version 2 uses fewer separate cutting paths, two bridges per enclosed counter, and smooth cubic Bézier curves while keeping letters and numbers recognizable.

Designed by **Artkis**. The font is open source under the **SIL Open Font License 1.1**; the supporting utility code uses the **MIT License**. See [Licensing](LICENSING.md).

![LaserFont alphabet and number specimen](examples/laserfont2-preview.png)

## What it provides

- Uppercase **A-Z**, **0-9**, hyphen and space. Lowercase input maps to uppercase shapes.
- **20 mm actual cap height** in the master geometry. The tools scale uniformly to other heights.
- **One cutting centerline**, without filled letter outlines or parallel outline contours.
- **Two uncut bridge gaps per counter**. `B` and `8` each have two counters, so they have four gaps in total.
- Nominal **3 mm centerline gaps at 20 mm height**; some glyphs use wider gaps. Gaps scale with the lettering.
- Exact cubic Bézier master geometry, plus an alternative made of real circular arcs and lines for software that handles polylines more reliably.
- An AutoCAD SHX display font and AutoLISP tools that generate permanent geometry without requiring a font on the receiving machine.

The drawing is intended for **single-line through-cutting**, rather than filled text, engraving, or marking. Other CNC uses require a suitable on-path operation and a tool that can reproduce the details.

## Why fewer paths and smoother curves?

A separate cut path can require another stop, repositioning move and pierce. LaserFont prioritizes fewer disconnected paths while preserving the bridges and readable character shapes. Rounded transitions also avoid many abrupt changes in direction.

Friendess identifies excessive nodes and micro-segments as one possible cause of slow or paused processing in CypCut, and discusses Bézier transitions when addressing sharp-corner behavior. This supports the design direction; it does not establish a cycle-time improvement for this font. See the [FSCUT2000C manual, sections 6.3 and 6.4, printed page 59](https://d.fscut.com/wordpress-fscut/2022/12/FSCUT2000CUser-ManualV3.1.pdf).

The master uses tangent-continuous **G1 joins** within connected paths. It is **not universally G2 curvature-continuous**: curvature can still change at joins, and tight radii can still require deceleration. Rounded returns in `M`, `N`, `V`, `W` and `1` remain tight and warrant particular attention in a motion test. Bézier geometry alone does not guarantee smooth machine motion if CAM turns it into short line segments.

## Measured design comparison

For one occurrence of every character in `ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-`, compared with the earlier three-bridge design:

| Geometric measure | Earlier design | Version 2 |
|---|---:|---:|
| Separate open paths | 94 | **67** |
| Approximate total centerline length | 1,654.0 mm | 1,687.0 mm |

This is **28.72% fewer geometric paths**, with approximately **2.00% more centerline length**. It is not a measurement of actual pierces, travel, cutting time or lens life. Those depend on CAM sequencing, piercing settings, machine motion and the material. Some characters retain additional strokes because removing them made the letter harder to read.

The comparison is recorded in [comparison-metrics.json](comparison-metrics.json); the glyph source identifies its individual path counts and bridge locations. The [geometry report](validation/geometry-report.json) records the release checks and their limits.

## AutoCAD quick start

Download [LASER2.lsp](cad/LASER2.lsp). Save a copy of your drawing, then use `APPLOAD` to load the LISP file.

| Command | Input | Result |
|---|---|---|
| `LASER2` | Type an ID, height, insertion point and rotation | New exact Bézier/line geometry |
| `LASEROUT2` | Select existing `laserfont2` TEXT or plain single-line MTEXT | Replaces accepted labels with exact Bézier/line geometry |
| `LASERPOLY2` | Select existing `laserfont2` TEXT or plain single-line MTEXT | Replaces accepted labels with fitted circular-arc/line LWPOLYLINE paths |

`LASERPOLY2` is an alternative text conversion command. It does not convert arbitrary existing splines or a previous `LASEROUT2` result.

The default height is **20 drawing units**. In a millimetre drawing that is 20 mm; these commands do not change the drawing's units or scale other objects. One `UNDO` reverses a completed command batch.

For editable text, place [laserfont2.shx](cad/laserfont2.shx) in an AutoCAD font or support search folder, then create a text style that uses it. Reload AutoCAD if its font list has not refreshed. Convert the final IDs to geometry before sending the drawing to another machine.

Conversion supports left-baseline TEXT and plain, single-line MTEXT. Unsupported formatting, wrapped text, mirrored text, non-unit width factors, oblique or elevated text, and locked-layer labels are skipped and retained. Position, rotation, height, layer and applicable appearance values are preserved for accepted labels.

## Choose the output geometry

**Exact master:** `LASER2` and `LASEROUT2` produce one open cubic DXF `SPLINE` for each curved or mixed path, or a `LINE` for a single straight path. The master control points are preserved.

**Arc/line alternative:** `LASERPOLY2` produces open zero-width `LWPOLYLINE` paths containing real circular arcs through their bulge values. The arcs approximate the Bézier master; they are not the exact original curves. The fitting target is **0.02 mm at 20 mm cap height**. Error scales with lettering height. The [geometry report](validation/geometry-report.json) gives the checked deviation and the method's limits for this release.

The fitted output can contain many circular arcs within one path. The reduction in disconnected paths does not establish a reduction in every CAM interpolation block.

**Display font:** SHX does not store native cubic Bézier curves. `laserfont2.shx` is a display approximation, not the cutting master. Use the supplied conversion commands to recover the master or fitted arc geometry. **Do not use `TXTEXP` to derive the cutting paths from the SHX preview.**

## CAM and machine check

The font geometry and AutoCAD behavior have been checked separately from the machine process. **Import in the actual CypCut version, actual pierce count, cycle time, cut quality, bridge strength and optical effects remain unverified.** No laser power, speed, lead-in, pierce delay or controller parameter is configured by this project.

Before production, use a small sample in the intended material:

1. Import at the correct units and scale; confirm the measured cap height.
2. Keep every stroke open and follow the centerline. Do not automatically close the stencil gaps or apply closed-outline kerf compensation.
3. Confirm that CAM retains curves, does not duplicate strokes and does not add unwanted lead-ins near a bridge.
4. Check readability, actual starts/pierces, motion and the remaining metal at the bridges. A 3 mm centerline gap is not a guaranteed 3 mm finished ligament after kerf and piercing.
5. Compare elapsed time against a baseline using the same material and process settings.

## Generate an ID without AutoCAD

Install Python 3, then install the DXF generator dependencies:

```console
python -m pip install ezdxf pillow
python generate_laserfont2.py --text "ID-A01" --height 20 --output ID-A01.dxf
```

The output contains permanent geometry, not text objects. The exact Bézier glyph definitions are in `glyphs-v2.json`; `build_glyphs.py` regenerates them using the Python standard library. `fit_polyline.py` builds the fitted arc data. [The AutoCAD notes](cad/README.md) describe the CAD build route.

## Contributing

Useful improvements include fewer independent paths, clearer character pairs, gentler curvature transitions and evidence from real CAM imports. Preserve the bridge count, open paths and intended character identity. Include the glyph changes, geometry checks, preview and measured machine results when available. Do not present a geometric reduction as a proven reduction in cutting time.

The glyphs were designed as original construction geometry. No proprietary font glyph outlines were copied into the project.

## License

Font design, glyph data, SHX/SHP fonts and embedded glyph tables: **[SIL Open Font License 1.1](OFL.txt)**. No Reserved Font Names are declared.

General utility code, excluding the embedded font data: **[MIT](LICENSE-MIT.txt)**. The precise component split is in [LICENSING.md](LICENSING.md). Documents and manufactured parts created with the font do not become subject to the OFL merely because the font was used.
